// The snipe endpoint: what it stores, what it turns away, and what it quietly cleans up.
//
// Needs the site running and the service key in the environment, so:
//   npx next dev
//   node --env-file=.env.local tests/test-snipe-endpoint.mjs
// Point it somewhere else with TARKBOT_SNIPE_URL=https://www.tarkbot.org/api/snipe to smoke test
// a deploy. There is only one Supabase project, so this writes real rows and deletes them again
// on the way out; the machine ids below exist to be recognisable and cleanable.
import assert from "node:assert/strict";

const ENDPOINT = process.env.TARKBOT_SNIPE_URL ?? "http://localhost:3000/api/snipe";
const { SUPABASE_URL, SUPABASE_SERVICE_KEY } = process.env;
const TABLE = "Tarkbot_snipes";

// Valid uuids, reserved for this test. Fixed rather than random so a run that dies half way
// still leaves rows the next run knows how to sweep up. The 9000 group is this test's; the
// crash report test owns the 8000 one.
const MACHINES = Array.from(
  { length: 8 },
  (_, i) => `00000000-0000-4000-9000-${String(i).padStart(12, "0")}`,
);

const keyed = (extra = {}) => ({
  apikey: SUPABASE_SERVICE_KEY,
  Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
  ...extra,
});

/** Drop every row this test has ever made. */
async function sweep() {
  await fetch(`${SUPABASE_URL}/rest/v1/${TABLE}?machine_id=in.(${MACHINES.join(",")})`, {
    method: "DELETE",
    headers: keyed(),
  });
}

/** The rows one test machine has, newest first. */
async function rowsFor(machine) {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/${TABLE}?select=*&machine_id=eq.${machine}&order=ts.desc`,
    { headers: keyed() },
  );
  return res.json();
}

const post = (body) =>
  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });

const buy = (machine, extra = {}) => ({
  machine_id: machine,
  version: "v0.0.0-test",
  item: "Salewa first aid kit",
  price: 41_000,
  trader_value: 52_000,
  ...extra,
});

assert.ok(SUPABASE_URL && SUPABASE_SERVICE_KEY, "run with --env-file=.env.local");
await sweep();

// ── the happy path, and the column the app is not allowed to send ────────────
{
  const res = await post(buy(MACHINES[0]));
  assert.equal(res.status, 200, await res.text());
  assert.deepEqual(await res.json(), { success: true });

  const [row] = await rowsFor(MACHINES[0]);
  assert.ok(row, "the buy did not land");
  assert.equal(row.item, "Salewa first aid kit");
  assert.equal(row.price, 41_000);
  assert.equal(row.trader_value, 52_000);
  assert.equal(row.version, "v0.0.0-test");
  // The whole reason margin is a generated column: it cannot disagree with its two inputs.
  assert.equal(row.margin, 11_000, "margin must be trader_value - price, computed by Postgres");
  assert.ok(row.ip_hash, "the rate limiter needs an ip hash on every row");
}

// A margin sent by the caller is ignored rather than believed.
{
  const res = await post(buy(MACHINES[1], { margin: 999_999 }));
  assert.equal(res.status, 200, await res.text());
  const [row] = await rowsFor(MACHINES[1]);
  assert.equal(row.margin, 11_000, "a margin in the body must not reach the table");
}

// ── the item name, the one field a caller writes freely ──────────────────────
{
  const res = await post(
    // A newline, a zero width space, a tab, and a right-to-left override, spelled out
    // rather than pasted in so they are visible to whoever reads this next.
    buy(MACHINES[2], { item: "  Salewa\n\u200bfirst   aid\tkit\u202e  " }),
  );
  assert.equal(res.status, 200, await res.text());
  const [row] = await rowsFor(MACHINES[2]);
  assert.equal(row.item, "Salewa first aid kit", "controls and invisibles must be scrubbed");
}
{
  // Angle brackets stay: React escapes on render, and real names carry punctuation.
  const res = await post(buy(MACHINES[3], { item: "5.45x39mm BT <gzh>" }));
  assert.equal(res.status, 200, await res.text());
  const [row] = await rowsFor(MACHINES[3]);
  assert.equal(row.item, "5.45x39mm BT <gzh>", "legitimate punctuation must survive");
}
{
  const res = await post(buy(MACHINES[4], { item: "x".repeat(500) }));
  assert.equal(res.status, 200, await res.text());
  const [row] = await rowsFor(MACHINES[4]);
  assert.equal(row.item.length, 120, "a long name is clamped, not rejected");
}

// ── everything that must be refused ──────────────────────────────────────────
const refused = [
  ["not json at all", "bad json", 400],
  [buy(MACHINES[0], { machine_id: "nope" }), "machine_id must be a uuid", 400],
  [buy(MACHINES[0], { item: "" }), "item required", 400],
  [buy(MACHINES[0], { item: "\n\n" }), "item required", 400],
  [buy(MACHINES[0], { item: 42 }), "item required", 400],
  [buy(MACHINES[0], { price: -1 }), "price must be a whole number of roubles", 400],
  [buy(MACHINES[0], { price: 4.5 }), "price must be a whole number of roubles", 400],
  [buy(MACHINES[0], { price: "41000" }), "price must be a whole number of roubles", 400],
  [buy(MACHINES[0], { price: 2_000_000_000 }), "price must be a whole number of roubles", 400],
  [buy(MACHINES[0], { trader_value: null }), "trader_value must be a whole number of roubles", 400],
  // A sniper that paid more than a trader pays did not snipe anything.
  [buy(MACHINES[0], { price: 60_000 }), "trader_value must not be under price", 400],
];
for (const [body, message, status] of refused) {
  const res = await post(body);
  assert.equal(res.status, status, `${message}: got ${res.status}`);
  assert.deepEqual(await res.json(), { error: message });
}
{
  const res = await post(JSON.stringify(buy(MACHINES[0], { item: "x".repeat(5000) })));
  assert.equal(res.status, 413);
  assert.deepEqual(await res.json(), { error: "payload too large" });
}

// Nothing refused may have left a row behind.
{
  const stored = await rowsFor(MACHINES[0]);
  assert.equal(stored.length, 1, `only the happy path should have stored, found ${stored.length}`);
}

await sweep();
console.log(`snipe endpoint at ${ENDPOINT}: all checks passed`);

// The rate limit is not exercised here on purpose: it counts rows per ip per hour, so tripping
// it would mean writing 300 rows and then leaving every later run of this test throttled for an
// hour. Check it by hand against a dev server if it ever needs proving.
