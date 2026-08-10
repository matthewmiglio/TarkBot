import type { NextRequest } from "next/server";
import { createHash, randomUUID } from "node:crypto";

// Crash reports from the desktop app: a row here, and two screenshots straight into a private
// bucket. Same service-key-server-side approach as the analytics route, so the open-source app
// ships no key at all and both the table and the bucket keep RLS on with no policies.
//
// The screenshots do not travel through this function. A lossless png of a 1440p screen is
// 4.5MB and Vercel rejects request bodies at 4.5MB before route code runs, so anything bigger
// than a 1080p screen simply cannot arrive. Instead this hands back two single-use signed
// upload urls and the app puts the bytes directly at Supabase, which caps them itself via the
// bucket's file_size_limit. Rate limiting still bites because there is no way to get an upload
// url without passing it first.
// ponytail: raw fetch instead of @supabase/supabase-js, one insert and two signs.

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;
const SALT = process.env.ERROR_REPORT_SALT ?? "";

const TABLE = "Tarkbot_errors";
const BUCKET = "Tarkbot_screenshots";
const MAX_BODY = 64 * 1024; // the json only carries a traceback; the images go elsewhere
const RATE_LIMIT = 10; // reports per ip per hour
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

/** A single-use url the app can PUT one png at, or null if signing failed. */
async function signUpload(id: string) {
  const res = await fetch(
    `${SUPABASE_URL}/storage/v1/object/upload/sign/${BUCKET}/${id}.png`,
    // Storage refuses an empty body when the content type says json, so send it an empty object.
    { method: "POST", headers: keyed({ "Content-Type": "application/json" }), body: "{}" },
  );
  if (!res.ok) {
    console.error("sign upload failed", res.status, await res.text());
    return null;
  }
  const { url } = (await res.json()) as { url: string };
  return `${SUPABASE_URL}/storage/v1${url}`;
}

export async function POST(req: NextRequest) {
  if (!SUPABASE_URL || !SERVICE_KEY) {
    return Response.json({ error: "error reporting not configured" }, { status: 503 });
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
  if (body.error === null || body.error === undefined) {
    return Response.json({ error: "error required" }, { status: 400 });
  }

  const ipHash = callerHash(req);

  // Rate limit in Postgres rather than in memory: this runs on serverless instances that come
  // and go, so an in-process counter resets constantly and protects nothing. Limiting on
  // machine_id instead would be theatre, the client picks that value and can randomise it.
  // ponytail: rotating ips still get through; the bucket's size cap is the blast-radius bound.
  const since = new Date(Date.now() - WINDOW_MS).toISOString();
  const recent = await fetch(
    `${SUPABASE_URL}/rest/v1/${TABLE}?select=id&ip_hash=eq.${ipHash}` +
      `&ts=gt.${encodeURIComponent(since)}&limit=${RATE_LIMIT}`,
    { headers: keyed() },
  );
  if (recent.ok && ((await recent.json()) as unknown[]).length >= RATE_LIMIT) {
    return Response.json({ error: "too many reports" }, { status: 429 });
  }

  const before = randomUUID();
  const after = randomUUID();

  const insert = await fetch(`${SUPABASE_URL}/rest/v1/${TABLE}`, {
    method: "POST",
    headers: keyed({ "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify({
      machine_id: machineId,
      version: typeof body.version === "string" ? body.version.slice(0, 64) : null,
      error: body.error,
      before_screenshot_id: before,
      after_screenshot_id: after,
      ip_hash: ipHash,
    }),
  });
  if (!insert.ok) {
    console.error("error insert failed", insert.status, await insert.text());
    return Response.json({ error: "could not save" }, { status: 502 });
  }

  // The row is already down, so an upload that never happens just leaves it with no picture.
  const [beforeUrl, afterUrl] = await Promise.all([signUpload(before), signUpload(after)]);

  return Response.json({
    success: true,
    before: { id: before, upload_url: beforeUrl },
    after: { id: after, upload_url: afterUrl },
  });
}
