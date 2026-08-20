// Pure shaping helpers: raw rows in, chart-ready numbers out. No React, no
// fetch, no env, so `node src/lib/derive.check.ts` can exercise them directly.

export type Period = "1d" | "10d" | "60d" | "all";

export const PERIODS: { key: Period; label: string }[] = [
  { key: "1d", label: "1 Day" },
  { key: "10d", label: "10 Days" },
  { key: "60d", label: "60 Days" },
  { key: "all", label: "All Time" },
];

const PERIOD_DAYS: Record<Period, number | null> = {
  "1d": 1,
  "10d": 10,
  "60d": 60,
  all: null,
};

/** Rows newer than the period's cutoff. `now` is injectable so the check is deterministic. */
export function withinPeriod<T extends { ts: string }>(
  rows: T[],
  period: Period,
  now: number = Date.now(),
): T[] {
  const days = PERIOD_DAYS[period];
  if (days === null) return rows;
  const cutoff = now - days * 24 * 60 * 60 * 1000;
  return rows.filter((r) => new Date(r.ts).getTime() >= cutoff);
}

/** Count per UTC day for the last `days` days, zero-filled so gaps show as gaps. */
export function perDay<T extends { ts: string }>(
  rows: T[],
  days: number,
  now: number = Date.now(),
): { day: string; count: number }[] {
  const counts = new Map<string, number>();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now - i * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    counts.set(d, 0);
  }
  for (const row of rows) {
    const d = row.ts.slice(0, 10);
    if (counts.has(d)) counts.set(d, counts.get(d)! + 1);
  }
  return Array.from(counts, ([day, count]) => ({ day, count }));
}

/** Distinct non-null values of one field. */
export function distinct<T>(rows: T[], field: keyof T): number {
  const seen = new Set<unknown>();
  for (const row of rows) {
    const v = row[field];
    if (v !== null && v !== undefined && v !== "") seen.add(v);
  }
  return seen.size;
}

/** Descending [label, count] pairs, ties broken by label so the order is stable. */
export function tally<T>(
  rows: T[],
  label: (row: T) => string | null,
): { label: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const key = label(row);
    if (key === null) continue;
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return Array.from(counts, ([label, count]) => ({ label, count })).sort(
    (a, b) => b.count - a.count || a.label.localeCompare(b.label),
  );
}

/**
 * Descending [label, total] pairs, summing a value per label rather than counting rows.
 *
 * The same shape and the same tie-break as tally, so BarList draws either without knowing which
 * it was handed. tally answers "how often", this answers "how much".
 */
export function sumBy<T>(
  rows: T[],
  label: (row: T) => string | null,
  value: (row: T) => number,
): { label: string; count: number }[] {
  const totals = new Map<string, number>();
  for (const row of rows) {
    const key = label(row);
    if (key === null) continue;
    totals.set(key, (totals.get(key) || 0) + value(row));
  }
  return Array.from(totals, ([label, count]) => ({ label, count })).sort(
    (a, b) => b.count - a.count || a.label.localeCompare(b.label),
  );
}

/** Roubles as the game writes them: thin-spaced thousands and the symbol. */
export function roubles(n: number): string {
  return `${Math.round(n).toLocaleString("en-GB").replace(/,/g, " ")} ₽`;
}

/**
 * Referrer URL to a source name. Null means "don't count this": internal
 * navigation and localhost are noise, not traffic.
 */
export function categorizeSource(url: string | null | undefined): string | null {
  if (!url) return "(direct)";
  const u = url.toLowerCase();

  if (u.startsWith("/")) return null;
  if (u.includes("localhost") || u.includes("127.0.0.1")) return null;

  // AI assistants first: gemini.google.com would otherwise be swallowed by Google.
  if (u.includes("chatgpt.com")) return "ChatGPT";
  if (u.includes("claude.ai")) return "Claude";
  if (u.includes("gemini.google.com")) return "Gemini";
  if (u.includes("copilot.microsoft.com")) return "Copilot";
  if (u.includes("perplexity.ai")) return "Perplexity";

  if (u.includes("google.")) return "Google";
  if (u.includes("bing.com")) return "Bing";
  if (u.includes("duckduckgo.com")) return "DuckDuckGo";
  if (u.includes("search.brave.com")) return "Brave";
  if (u.includes("yandex.") || u.includes("ya.ru")) return "Yandex";
  if (u.includes("ecosia.org")) return "Ecosia";
  if (u.includes("yahoo.com")) return "Yahoo";

  if (u.includes("reddit.com")) return "Reddit";
  if (u.includes("discord.com") || u.includes("discord.gg")) return "Discord";
  if (u.includes("youtube.com")) return "YouTube";
  if (u.includes("twitch.tv")) return "Twitch";
  if (u.includes("github.com")) return "GitHub";
  if (u.includes("twitter.com") || u.includes("x.com") || u.includes("t.co")) return "X / Twitter";
  if (u.includes("facebook.com") || u.includes("instagram.com")) return "Meta";
  if (u.includes("steamcommunity.com")) return "Steam";

  return "Other";
}

/** Query and fragment stripped, trailing slash gone. Null drops API noise. */
export function normalizePath(path: string): string | null {
  let base = path.split("?")[0].split("#")[0];
  try {
    base = decodeURIComponent(base);
  } catch {
    // A malformed escape is still a path; keep the raw one.
  }
  base = base.toLowerCase().replace(/\/+$/, "") || "/";
  if (base.startsWith("/api/")) return null;
  return base;
}
