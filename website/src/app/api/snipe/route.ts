import type { NextRequest } from "next/server";
import { createHash } from "node:crypto";

// One row per item the flea sniper buys, so the dashboard can answer what people actually snipe.
// Same shape as the crash report route next door: service key server side, RLS on with no
// policies, and an app that ships no key at all.
//
// The body is tiny and there is nothing to hand back, which is the whole difference from
// /api/error. No screenshots, no signed urls, no upload dance: a purchase is six small fields
// and a 200.
// ponytail: raw fetch instead of @supabase/supabase-js, one insert.

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;
const SALT = process.env.ERROR_REPORT_SALT ?? "";

const TABLE = "Tarkbot_snipes";
const MAX_BODY = 4 * 1024; // six fields and an item name; anything larger is not from the app
const NAME_LIMIT = 120; // the longest real Tarkov item name is about 60
const MAX_ROUBLES = 1_000_000_000; // the flea caps offers far below this; it is a sanity bound
// Purchases per ip per hour. Thirty times the crash route's, because buying is the normal case
// rather than the failure case: the run of 19 Aug bought 21 items in 12 minutes, so anything
// under about 100 would throttle a real night of sniping. 300 still bounds a flood.
const RATE_LIMIT = 300;
const WINDOW_MS = 60 * 60 * 1000;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function keyed(extra: Record<string, string> = {}) {
  return {
    apikey: SERVICE_KEY as string,
    Authorization: `Bearer ${SERVICE_KEY}`,
    ...extra,
  };
}

/** sha256 of the caller's ip, so the table is a rate-limit ledger and not a log of real ips. */
function callerHash(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0].trim() || "unknown";
  return createHash("sha256").update(`${ip}${SALT}`).digest("hex");
}

/**
 * The item name, made safe to store and to draw. The one field a caller writes freely.
 *
 * Control characters go first: a newline or a zero-width run inside a name is what breaks a bar
 * label on the dashboard, and it can never be part of a real item. Then runs of whitespace
 * collapse, so "Salewa   kit" and "Salewa kit" tally as one item instead of two.
 *
 * Deliberately no HTML escaping. The dashboard renders these through JSX text and title
 * attributes, both of which React escapes already, so escaping here would double-escape and
 * turn a legitimate name like "5.45x39mm BT" into something unreadable.
 */
function cleanName(value: unknown) {
  if (typeof value !== "string") return "";
  return value
    // Controls, then the invisibles: zero width space through right-to-left mark, the bidi
    // embeddings and overrides, and the line and paragraph separators. None can be part of a
    // real item name, and each of them wrecks a bar label on the dashboard in its own way. The
    // overrides earn their place: U+202E reverses everything drawn after it, so one of those in
    // a name reverses the rest of the row it is drawn in.
    // eslint-disable-next-line no-control-regex
    .replace(/[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2028\u2029\ufeff]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, NAME_LIMIT);
}

/** A whole number of roubles, or null if it is anything else. */
function roubles(value: unknown) {
  if (typeof value !== "number" || !Number.isInteger(value)) return null;
  if (value < 0 || value > MAX_ROUBLES) return null;
  return value;
}

export async function POST(req: NextRequest) {
  if (!SUPABASE_URL || !SERVICE_KEY) {
    return Response.json({ error: "snipe reporting not configured" }, { status: 503 });
  }

  // Read as text first: the size has to be judged before anything is parsed.
  const raw = await req.text();
  if (Buffer.byteLength(raw) > MAX_BODY) {
    return Response.json({ error: "payload too large" }, { status: 413 });
  }

  let body: Record<string, unknown>;
  try {
    body = JSON.parse(raw);
  } catch {
    return Response.json({ error: "bad json" }, { status: 400 });
  }

  const machineId = body.machine_id;
  if (typeof machineId !== "string" || !UUID.test(machineId)) {
    return Response.json({ error: "machine_id must be a uuid" }, { status: 400 });
  }

  const item = cleanName(body.item);
  if (!item) {
    return Response.json({ error: "item required" }, { status: 400 });
  }

  const price = roubles(body.price);
  if (price === null) {
    return Response.json({ error: "price must be a whole number of roubles" }, { status: 400 });
  }
  const traderValue = roubles(body.trader_value);
  if (traderValue === null) {
    return Response.json(
      { error: "trader_value must be a whole number of roubles" },
      { status: 400 },
    );
  }
  // The sniper only ever buys under trader value, so the other way round is a bug or a forgery,
  // and either way it would poison the margin figures the dashboard adds up.
  if (traderValue < price) {
    return Response.json({ error: "trader_value must not be under price" }, { status: 400 });
  }

  const ipHash = callerHash(req);

  // Rate limit in Postgres rather than in memory, the same reasoning as the crash route: this
  // runs on serverless instances that come and go, so an in-process counter protects nothing.
  // Limiting on machine_id would be theatre, since the client picks that value.
  const since = new Date(Date.now() - WINDOW_MS).toISOString();
  const recent = await fetch(
    `${SUPABASE_URL}/rest/v1/${TABLE}?select=id&ip_hash=eq.${ipHash}` +
      `&ts=gt.${encodeURIComponent(since)}&limit=${RATE_LIMIT}`,
    { headers: keyed() },
  );
  if (recent.ok && ((await recent.json()) as unknown[]).length >= RATE_LIMIT) {
    return Response.json({ error: "too many reports" }, { status: 429 });
  }

  // margin is not accepted from the caller. Postgres computes it as trader_value - price, so the
  // number on the dashboard cannot disagree with the two it comes from.
  const insert = await fetch(`${SUPABASE_URL}/rest/v1/${TABLE}`, {
    method: "POST",
    headers: keyed({ "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify({
      machine_id: machineId,
      version: typeof body.version === "string" ? body.version.slice(0, 64) : null,
      item,
      price,
      trader_value: traderValue,
      ip_hash: ipHash,
    }),
  });
  if (!insert.ok) {
    console.error("snipe insert failed", insert.status, await insert.text());
    return Response.json({ error: "could not save" }, { status: 502 });
  }

  return Response.json({ success: true });
}
