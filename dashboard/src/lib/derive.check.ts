// Self-check for derive.ts. No framework: node strips the types and runs it.
//   node src/lib/derive.check.ts
import assert from "node:assert/strict";
import {
  withinPeriod, perDay, distinct, tally, sumBy, roubles, categorizeSource, normalizePath,
} from "./derive.ts";

const NOW = Date.parse("2026-07-27T12:00:00Z");
const daysAgo = (n: number) => new Date(NOW - n * 86_400_000).toISOString();

const rows = [
  { ts: daysAgo(0), visitor_id: "a" },
  { ts: daysAgo(0), visitor_id: "a" },
  { ts: daysAgo(5), visitor_id: "b" },
  { ts: daysAgo(30), visitor_id: null },
  { ts: daysAgo(90), visitor_id: "c" },
];

// withinPeriod
assert.equal(withinPeriod(rows, "all", NOW).length, 5);
assert.equal(withinPeriod(rows, "1d", NOW).length, 2);
assert.equal(withinPeriod(rows, "10d", NOW).length, 3);
assert.equal(withinPeriod(rows, "60d", NOW).length, 4);

// perDay: zero-filled, and the 90-day-old row falls outside the window
const week = perDay(rows, 7, NOW);
assert.equal(week.length, 7);
assert.equal(week.at(-1)!.count, 2, "today has both of today's rows");
assert.equal(week.reduce((s, d) => s + d.count, 0), 3, "only rows inside 7 days count");
assert.ok(week[0].day < week.at(-1)!.day, "oldest day first");

// distinct ignores null and empty
assert.equal(distinct(rows, "visitor_id"), 3);

// tally sorts by count, then label
const t = tally(
  [{ k: "b" }, { k: "a" }, { k: "a" }, { k: "c" }, { k: null }],
  (r) => r.k,
);
assert.deepEqual(t, [
  { label: "a", count: 2 },
  { label: "b", count: 1 },
  { label: "c", count: 1 },
]);

// sumBy: same shape and tie-break as tally, but adding a value instead of counting rows
const buys = [
  { item: "Salewa", margin: 5_000 },
  { item: "Salewa", margin: 7_000 },
  { item: "Bandage", margin: 12_000 },
  { item: "Aluminium", margin: 12_000 },
];
assert.deepEqual(
  sumBy(buys, (b) => b.item, (b) => b.margin),
  [
    { label: "Salewa", count: 12_000 },
    { label: "Aluminium", count: 12_000 },
    { label: "Bandage", count: 12_000 },
  ],
  "sums per label, ties broken by label so the order is stable",
);
assert.deepEqual(sumBy([], (b: { item: string }) => b.item, () => 1), [], "no rows, no bars");
assert.deepEqual(
  sumBy(buys, (b) => (b.item === "Salewa" ? null : b.item), (b) => b.margin).map((r) => r.label),
  ["Aluminium", "Bandage"],
  "a null label drops the row, same as tally",
);

// roubles
assert.equal(roubles(0), "0 ₽");
assert.equal(roubles(41_000), "41 000 ₽", "thin spaces, the way the game writes them");
assert.equal(roubles(1_234_567), "1 234 567 ₽");
assert.equal(roubles(999.6), "1 000 ₽", "rounded, since a rouble has no fractions here");

// categorizeSource
assert.equal(categorizeSource(null), "(direct)");
assert.equal(categorizeSource(""), "(direct)");
assert.equal(categorizeSource("/features"), null, "internal nav is not traffic");
assert.equal(categorizeSource("http://localhost:3000/"), null, "dev traffic is not traffic");
assert.equal(categorizeSource("https://www.google.com/search?q=tarkbot"), "Google");
assert.equal(categorizeSource("https://gemini.google.com/app"), "Gemini", "AI beats Google");
assert.equal(categorizeSource("https://www.reddit.com/r/EscapefromTarkov/"), "Reddit");
assert.equal(categorizeSource("https://discord.gg/Vx4tdR3N8A"), "Discord");
assert.equal(categorizeSource("https://example.invalid/x"), "Other");

// normalizePath
assert.equal(normalizePath("/"), "/");
assert.equal(normalizePath("/Features/"), "/features");
assert.equal(normalizePath("/download?utm_source=reddit#top"), "/download");
assert.equal(normalizePath("/api/analytics"), null);
assert.equal(normalizePath("/%E2%9C%93"), "/✓");
assert.equal(normalizePath("/%zz"), "/%zz", "a bad escape is still a path");

console.log("derive.ts: all checks passed");
