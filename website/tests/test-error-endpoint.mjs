// The crash report endpoint: what it accepts, what it turns away, and that the upload url it
// hands back actually takes a file.
//
// Needs the site running and the service key in the environment, so:
//   npx next dev
//   node --env-file=.env.local tests/test-error-endpoint.mjs
// Point it somewhere else with TARKBOT_ERROR_URL=https://tarkbot.org/api/error to smoke test a
// deploy. There is only one Supabase project, so this writes real rows and deletes them again
// on the way out; the machine ids below exist to be recognisable and cleanable.
import assert from "node:assert/strict";

const ENDPOINT = process.env.TARKBOT_ERROR_URL ?? "http://localhost:3000/api/error";
const { SUPABASE_URL, SUPABASE_SERVICE_KEY } = process.env;
const TABLE = "Tarkbot_errors";
const BUCKET = "Tarkbot_screenshots";

// Valid uuids, reserved for this test. Fixed rather than random so a run that dies half way
// still leaves rows the next run knows how to sweep up.
const MACHINES = Array.from(
  { length: 16 },
  (_, i) => `00000000-0000-4000-8000-${String(i).padStart(12, "0")}`,
);

const keyed = (extra = {}) => ({
  apikey: SUPABASE_SERVICE_KEY,
  Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
  ...extra,
});

/** Drop every row and object this test has ever made. Also resets the per-ip rate limit,
 *  since these are the only reports a local run produces. */
async function sweep() {
  const list = MACHINES.join(",");
  const rows = await fetch(
    `${SUPABASE_URL}/rest/v1/${TABLE}?select=before_screenshot_id,after_screenshot_id` +
      `&machine_id=in.(${list})`,
    { headers: keyed() },
  ).then((r) => r.json());

  const ids = rows.flatMap((r) => [r.before_screenshot_id, r.after_screenshot_id]).filter(Boolean);
  if (ids.length) {
    await fetch(`${SUPABASE_URL}/storage/v1/object/${BUCKET}`, {
      method: "DELETE",
      headers: keyed({ "Content-Type": "application/json" }),
      body: JSON.stringify({ prefixes: ids.map((id) => `${id}.png`) }),
    });
  }
  await fetch(`${SUPABASE_URL}/rest/v1/${TABLE}?machine_id=in.(${list})`, {
    method: "DELETE",
    headers: keyed(),
  });
  return rows.length;
}

const post = (body) =>
  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });

const report = (machine_id, extra = {}) => ({
  machine_id,
  version: "0.0.0-test",
  error: { type: "RuntimeError", message: "flea did not open", traceback: "line one\nline two" },
  ...extra,
});

async function main() {
  assert.ok(SUPABASE_URL && SUPABASE_SERVICE_KEY, "run with --env-file=.env.local");

  try {
    await fetch(ENDPOINT, { method: "HEAD" });
  } catch {
    console.error(`cannot reach ${ENDPOINT}. Is the site running? (npx next dev)`);
    process.exit(1);
  }

  console.log(`swept ${await sweep()} leftover rows`);

  // Rejections first: none of these insert anything, so they cost no rate-limit budget.
  assert.equal((await post(report("not-a-uuid"))).status, 400, "malformed machine_id");
  assert.equal((await post({ error: { a: 1 } })).status, 400, "missing machine_id");
  assert.equal((await post(report(MACHINES[0], { error: null }))).status, 400, "missing error");
  assert.equal((await post("{oh dear")).status, 400, "unparseable json");

  // Anything over 64KB is refused before it is even parsed. The pictures do not come this way,
  // so nothing legitimate is anywhere near this size.
  const huge = JSON.stringify(report(MACHINES[0], { error: { traceback: "x".repeat(70_000) } }));
  assert.ok(huge.length > 64 * 1024, "the oversized case really is oversized");
  assert.equal((await post(huge)).status, 413, "oversized body");
  console.log("ok - rejects malformed, incomplete and oversized reports");

  // A good report: a row, and two distinct single-use upload urls.
  const res = await post(report(MACHINES[1]));
  assert.equal(res.status, 200, `a valid report should be accepted, got ${res.status}`);
  const body = await res.json();
  assert.match(body.before.id, /^[0-9a-f-]{36}$/, "before id is a uuid");
  assert.match(body.after.id, /^[0-9a-f-]{36}$/, "after id is a uuid");
  assert.notEqual(body.before.id, body.after.id, "the two screenshots get their own ids");
  for (const half of ["before", "after"]) {
    assert.ok(body[half].upload_url?.includes("token="), `${half} url carries a token`);
  }
  console.log("ok - a valid report stores a row and signs two upload urls");

  // That url has to actually take a file, otherwise the app has nowhere to put the screenshot.
  const png = Buffer.from("not really a png, but the bucket only checks the declared type");
  const put = await fetch(body.before.upload_url, {
    method: "PUT",
    headers: { "Content-Type": "image/png" },
    body: png,
  });
  assert.ok(put.ok, `signed upload url rejected the file: ${put.status} ${await put.text()}`);
  console.log("ok - the signed url accepts an upload");

  // The row has to name the objects, or a screenshot in the bucket belongs to nobody.
  const [row] = await fetch(
    `${SUPABASE_URL}/rest/v1/${TABLE}?select=*&machine_id=eq.${MACHINES[1]}`,
    { headers: keyed() },
  ).then((r) => r.json());
  assert.ok(row, "the report reached the table");
  assert.equal(row.before_screenshot_id, body.before.id);
  assert.equal(row.after_screenshot_id, body.after.id);
  assert.equal(row.error.type, "RuntimeError", "the traceback survived as jsonb");
  assert.ok(row.ip_hash?.length === 64, "the caller was recorded as a sha256, not an ip");
  console.log("ok - the row points at both screenshots and stores the error as jsonb");

  // Rate limit. The endpoint allows 10 an hour per caller and one is already spent above, so
  // the tenth of these is the last one through.
  let limited = 0;
  for (let i = 2; i < 14; i++) {
    if ((await post(report(MACHINES[i]))).status === 429) limited++;
  }
  assert.ok(limited > 0, "a caller past the hourly limit should start getting 429s");
  console.log(`ok - rate limited after the hourly allowance (${limited} of 12 refused)`);

  console.log(`cleaned up ${await sweep()} rows`);
  console.log("\nall good");
}

main().catch(async (err) => {
  await sweep().catch(() => {});
  console.error(err);
  process.exit(1);
});
