"use client";

import { useMemo, useState } from "react";
import type { ViewEvent, DownloadEvent, SnipeRow } from "@/lib/data";
import {
  PERIODS, categorizeSource, distinct, normalizePath, perDay, roubles, sumBy, tally, withinPeriod,
} from "@/lib/derive";
import type { Period } from "@/lib/derive";

// ─── shared chrome ───────────────────────────────────────────────────────────

function Card({
  title, children, tabs,
}: {
  title: string;
  children: React.ReactNode;
  tabs?: { period: Period; onChange: (p: Period) => void };
}) {
  return (
    <div className="bg-gray-50 rounded-md p-6 border border-gray-200">
      <div className="flex items-center justify-between mb-4 gap-4">
        <h3 className="text-sm font-bold text-gray-900">{title}</h3>
        {tabs && (
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {PERIODS.map((t) => (
              <button
                key={t.key}
                onClick={() => tabs.onChange(t.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  tabs.period === t.key
                    ? "bg-gray-200 text-indigo-500"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}

function BarList({
  rows, color = "bg-indigo-500", empty = "Nothing in this period", format = String,
}: {
  rows: { label: string; count: number }[];
  color?: string;
  empty?: string;
  // A count fits in the narrow column at the end; a sum of roubles does not. Callers that
  // pass one also pass the formatter that shortens it.
  format?: (n: number) => string;
}) {
  const max = Math.max(...rows.map((r) => r.count), 1);
  if (rows.length === 0) return <p className="text-xs text-gray-400">{empty}</p>;
  return (
    <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
      {rows.map((r) => (
        <div key={r.label} className="flex items-center gap-3">
          <span className="text-xs text-gray-500 w-32 truncate" title={r.label}>
            {r.label}
          </span>
          <div className="flex-1 h-6 bg-gray-100 rounded overflow-hidden">
            <div className={`h-full rounded ${color}`} style={{ width: `${(r.count / max) * 100}%` }} />
          </div>
          <span className="text-xs font-medium text-gray-500 w-16 text-right tabular-nums">
            {format(r.count)}
          </span>
        </div>
      ))}
    </div>
  );
}

function Columns({
  data, color = "bg-indigo-500", unit,
}: {
  data: { day: string; count: number }[];
  color?: string;
  unit: string;
}) {
  const [hovered, setHovered] = useState<number | null>(null);
  const max = Math.max(...data.map((d) => d.count), 1);
  const total = data.reduce((s, d) => s + d.count, 0);

  return (
    <>
      <div className="flex gap-2">
        <div className="flex flex-col justify-between items-end pr-1 h-32">
          {[max, Math.round(max / 2), 0].map((n, i) => (
            <span key={i} className="text-[10px] text-gray-400 leading-none">{n}</span>
          ))}
        </div>
        <div className="flex-1 flex items-end gap-px h-32 relative">
          {data.map((d, i) => (
            <div
              key={d.day}
              className="flex-1 flex flex-col justify-end h-full relative"
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              {hovered === i && (
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                  {d.day} · {d.count} {unit}
                </div>
              )}
              <div
                className={`w-full rounded-t transition-colors ${hovered === i ? "bg-indigo-400" : color}`}
                style={{ height: `${Math.max((d.count / max) * 100, 2)}%` }}
              />
            </div>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-gray-400">
          {data[0]?.day} → {data.at(-1)?.day}
        </span>
        <span className="text-sm font-bold text-gray-900">{total} {unit}</span>
      </div>
    </>
  );
}

// ─── figures ─────────────────────────────────────────────────────────────────

export function SummaryTiles({ views, downloads }: { views: ViewEvent[]; downloads: DownloadEvent[] }) {
  const tiles = useMemo(() => {
    const last7 = perDay(views, 7).reduce((s, d) => s + d.count, 0);
    const visitors = distinct(views, "visitor_id");
    const downloaders = distinct(downloads, "visitor_id");
    return [
      { label: "Page views", value: views.length, sub: `${last7} in 7 days` },
      { label: "Unique visitors", value: visitors, sub: `${distinct(views, "session_id")} sessions` },
      { label: "Downloads", value: downloads.length, sub: `${downloaders} unique` },
      {
        // Visitors who downloaded, not downloads per visitor, so a visitor who
        // grabs three builds cannot push this past 100%.
        label: "Download rate",
        value: visitors ? `${((downloaders / visitors) * 100).toFixed(1)}%` : "—",
        sub: `${withinPeriod(views, "60d").length} views in 60 days`,
      },
    ];
  }, [views, downloads]);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
      {tiles.map((t) => (
        <div key={t.label} className="bg-gray-50 rounded-md p-6 border border-gray-200">
          <p className="text-xs uppercase tracking-wider text-gray-400">{t.label}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{t.value}</p>
          <p className="mt-1 text-xs text-gray-400">{t.sub}</p>
        </div>
      ))}
    </div>
  );
}

export function ViewsOverTime({ views }: { views: ViewEvent[] }) {
  const data = useMemo(() => perDay(views, 30), [views]);
  return (
    <Card title="Page Views · Last 30 Days">
      <Columns data={data} unit="views" />
    </Card>
  );
}

export function DownloadsOverTime({ downloads }: { downloads: DownloadEvent[] }) {
  const data = useMemo(() => perDay(downloads, 30), [downloads]);
  return (
    <Card title="Downloads · Last 30 Days">
      <Columns data={data} color="bg-green-500" unit="downloads" />
    </Card>
  );
}

export function TrafficSources({ views }: { views: ViewEvent[] }) {
  const [period, setPeriod] = useState<Period>("all");
  const rows = useMemo(
    () => tally(withinPeriod(views, period), (e) => categorizeSource(e.referrer)),
    [views, period],
  );
  return (
    <Card title="Traffic Sources" tabs={{ period, onChange: setPeriod }}>
      <BarList rows={rows} color="bg-green-500" empty="No traffic in this period" />
    </Card>
  );
}

export function PagePopularity({ views }: { views: ViewEvent[] }) {
  const [period, setPeriod] = useState<Period>("all");
  const rows = useMemo(
    () => tally(withinPeriod(views, period), (e) => normalizePath(e.path)),
    [views, period],
  );
  return (
    <Card title="Page Popularity" tabs={{ period, onChange: setPeriod }}>
      <BarList rows={rows} />
    </Card>
  );
}

export function ViewsByCountry({ views }: { views: ViewEvent[] }) {
  const [period, setPeriod] = useState<Period>("all");
  const rows = useMemo(
    () => tally(withinPeriod(views, period), (e) => e.country || "(unknown)"),
    [views, period],
  );
  return (
    <Card title="Views by Country" tabs={{ period, onChange: setPeriod }}>
      <BarList rows={rows} color="bg-amber-500" empty="No located views in this period" />
    </Card>
  );
}

export function DownloadSources({ downloads }: { downloads: DownloadEvent[] }) {
  const [period, setPeriod] = useState<Period>("all");
  const rows = useMemo(
    () => tally(withinPeriod(downloads, period), (d) => categorizeSource(d.referrer)),
    [downloads, period],
  );
  return (
    <Card title="Where Downloaders Came From" tabs={{ period, onChange: setPeriod }}>
      <BarList rows={rows} color="bg-green-500" empty="No downloads in this period" />
    </Card>
  );
}

export function ActivityFeed({ views, downloads }: { views: ViewEvent[]; downloads: DownloadEvent[] }) {
  const feed = useMemo(() => {
    const rows = [
      ...views.map((v) => ({ ts: v.ts, kind: "view" as const, what: v.path, where: v.city || v.country })),
      ...downloads.map((d) => ({ ts: d.ts, kind: "download" as const, what: "downloaded a build", where: d.country })),
    ];
    return rows.sort((a, b) => b.ts.localeCompare(a.ts)).slice(0, 60);
  }, [views, downloads]);

  return (
    <Card title="Recent Activity">
      {feed.length === 0 ? (
        <p className="text-xs text-gray-400">Nothing yet</p>
      ) : (
        <div className="space-y-1 max-h-96 overflow-y-auto pr-1">
          {feed.map((r, i) => (
            <div key={i} className="flex items-center gap-3 text-xs py-1 border-b border-gray-100 last:border-0">
              <span
                className={`size-1.5 rounded-full shrink-0 ${r.kind === "download" ? "bg-green-500" : "bg-indigo-400"}`}
              />
              <span className="text-gray-400 w-36 shrink-0 tabular-nums">
                {r.ts.slice(0, 16).replace("T", " ")}
              </span>
              <span className="text-gray-700 truncate flex-1">{r.what}</span>
              <span className="text-gray-400 shrink-0">{r.where || ""}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ─── snipe data ──────────────────────────────────────────────────────────────
// One row per item the flea sniper bought, straight off Tarkbot_snipes. The question these
// four answer, in order: how much is being bought, what is being bought, what is worth
// buying, and whether any of it is still happening.

export function SnipeTiles({ snipes }: { snipes: SnipeRow[] }) {
  const tiles = useMemo(() => {
    const spent = snipes.reduce((s, r) => s + r.price, 0);
    const margin = snipes.reduce((s, r) => s + r.margin, 0);
    const last7 = perDay(snipes, 7).reduce((s, d) => s + d.count, 0);
    return [
      { label: "Items bought", value: snipes.length, sub: `${last7} in 7 days` },
      {
        label: "Machines sniping",
        value: distinct(snipes, "machine_id"),
        sub: `${distinct(snipes, "item")} different items`,
      },
      { label: "Roubles spent", value: roubles(spent), sub: `${roubles(spent / (snipes.length || 1))} a buy` },
      {
        // What the traders will pay for all of it, less what it cost. The bot's own definition
        // of profit, added up across everyone rather than across one run.
        label: "Margin bought",
        value: roubles(margin),
        sub: snipes.length ? `${roubles(margin / snipes.length)} a buy` : "nothing bought yet",
      },
    ];
  }, [snipes]);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
      {tiles.map((t) => (
        <div key={t.label} className="bg-gray-50 rounded-md p-6 border border-gray-200">
          <p className="text-xs uppercase tracking-wider text-gray-400">{t.label}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{t.value}</p>
          <p className="mt-1 text-xs text-gray-400">{t.sub}</p>
        </div>
      ))}
    </div>
  );
}

export function TopItems({ snipes }: { snipes: SnipeRow[] }) {
  const [period, setPeriod] = useState<Period>("all");
  const rows = useMemo(
    () => tally(withinPeriod(snipes, period), (s) => s.item),
    [snipes, period],
  );
  return (
    <Card title="Most Bought Items" tabs={{ period, onChange: setPeriod }}>
      <BarList rows={rows} empty="Nothing bought in this period" />
    </Card>
  );
}

export function ItemsByMargin({ snipes }: { snipes: SnipeRow[] }) {
  const [period, setPeriod] = useState<Period>("all");
  const rows = useMemo(
    () => sumBy(withinPeriod(snipes, period), (s) => s.item, (s) => s.margin),
    [snipes, period],
  );
  return (
    <Card title="Margin by Item" tabs={{ period, onChange: setPeriod }}>
      {/* Thousands, not roubles: the column at the end of a bar has room for "1 240k" and
          none for "1 240 000 ₽". The tiles above carry the exact totals. */}
      <BarList
        rows={rows}
        color="bg-green-500"
        empty="Nothing bought in this period"
        format={(n) => `${Math.round(n / 1000).toLocaleString("en-GB")}k`}
      />
    </Card>
  );
}

export function BuysOverTime({ snipes }: { snipes: SnipeRow[] }) {
  const data = useMemo(() => perDay(snipes, 30), [snipes]);
  return (
    <Card title="Items Bought · Last 30 Days">
      <Columns data={data} color="bg-amber-500" unit="buys" />
    </Card>
  );
}
