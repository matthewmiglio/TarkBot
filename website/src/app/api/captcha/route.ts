import type { NextRequest } from "next/server";
import { createHash, randomUUID } from "node:crypto";

// A screenshot of every flea SECURITY CHECK captcha the sniper runs into: a row here, and the png
// straight into a private bucket. Same service-key-server-side approach as /api/snipe, so the
// open-source app ships no key and both the table and the bucket keep RLS on with no policies.
//
// The png does not travel through this function. A lossless 1440p screen is about 4.5MB and
// Vercel rejects request bodies at 4.5MB before route code runs, so this hands back one
// single-use signed upload url and the app puts the bytes directly at Supabase, which caps them
// with the bucket's file_size_limit (25MB, png only). Rate limiting still bites because there is
// no way to get an upload url without passing it first.
// ponytail: raw fetch instead of @supabase/supabase-js, one select, one insert, one sign.

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;
const SALT = process.env.ERROR_REPORT_SALT ?? "";

const TABLE = "Tarkbot_captchas";
const BUCKET = "Tarkbot_captchas";
const MAX_BODY = 4 * 1024; // machine_id and version; the image goes elsewhere
// A captcha ends the run, so a real machine sends a handful an hour at most.
const RATE_LIMIT = 20;
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

export async function POST(req: NextRequest) {
  if (!SUPABASE_URL || !SERVICE_KEY) {
    return Response.json({ error: "captcha reporting not configured" }, { status: 503 });
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

  const ipHash = callerHash(req);

  // Rate limit in Postgres, not memory: serverless instances come and go, so an in-process counter
  // protects nothing. machine_id would be theatre, the client picks it.
  // ponytail: rotating ips still get through; the bucket's size cap bounds each upload.
  const since = new Date(Date.now() - WINDOW_MS).toISOString();
  const recent = await fetch(
    `${SUPABASE_URL}/rest/v1/${TABLE}?select=id&ip_hash=eq.${ipHash}` +
      `&ts=gt.${encodeURIComponent(since)}&limit=${RATE_LIMIT}`,
    { headers: keyed() },
  );
  if (recent.ok && ((await recent.json()) as unknown[]).length >= RATE_LIMIT) {
    return Response.json({ error: "too many reports" }, { status: 429 });
  }

  const imageId = randomUUID();
  const insert = await fetch(`${SUPABASE_URL}/rest/v1/${TABLE}`, {
    method: "POST",
    headers: keyed({ "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify({
      machine_id: machineId,
      version: typeof body.version === "string" ? body.version.slice(0, 64) : null,
      image_id: imageId,
      ip_hash: ipHash,
    }),
  });
  if (!insert.ok) {
    console.error("captcha insert failed", insert.status, await insert.text());
    return Response.json({ error: "could not save" }, { status: 502 });
  }

  const sign = await fetch(
    `${SUPABASE_URL}/storage/v1/object/upload/sign/${BUCKET}/${imageId}.png`,
    // Storage refuses an empty body when the content type says json, so send it an empty object.
    { method: "POST", headers: keyed({ "Content-Type": "application/json" }), body: "{}" },
  );
  if (!sign.ok) {
    // The row is already down, so it just has no picture.
    console.error("captcha sign upload failed", sign.status, await sign.text());
    return Response.json({ error: "could not sign upload" }, { status: 502 });
  }
  const { url } = (await sign.json()) as { url: string };

  return Response.json({
    success: true,
    id: imageId,
    upload_url: `${SUPABASE_URL}/storage/v1${url}`,
  });
}
