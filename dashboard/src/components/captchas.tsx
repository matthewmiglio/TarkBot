import type { CaptchaRow, RecentCaptcha } from "@/lib/data";
import { cumulativePerDay, tally } from "@/lib/derive";

// The flea SECURITY CHECK captchas snipe mode photographs: how many have come in over time, who
// sends the most, and the newest ten images.
//
// ponytail: a server component and an inline svg polyline for the line chart. No chart library,
// no client state. Plain <img> rather than next/image because these are signed urls on a
// Supabase host that would otherwise need a remotePatterns entry.

const CARD = "bg-gray-50 rounded-md p-6 border border-gray-200";
const TITLE = "text-sm font-bold text-gray-900 mb-4";

function CumulativeLine({ rows }: { rows: CaptchaRow[] }) {
  const data = cumulativePerDay(rows);
  if (data.length === 0) return <p className="text-xs text-gray-400">No captchas yet</p>;
  const max = data.at(-1)!.count;
  // One point per day across a 100-wide box; a single day still draws as a flat line.
  const step = data.length > 1 ? 100 / (data.length - 1) : 100;
  const points = (data.length > 1 ? data : [data[0], data[0]])
    .map((d, i) => `${(i * step).toFixed(2)},${(40 - (d.count / max) * 38).toFixed(2)}`)
    .join(" ");
  return (
    <>
      <div className="flex gap-2">
        <div className="flex flex-col justify-between items-end pr-1 h-40">
          {[max, Math.round(max / 2), 0].map((n, i) => (
            <span key={i} className="text-[10px] text-gray-400 leading-none">{n}</span>
          ))}
        </div>
        <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="flex-1 h-40">
          <polyline
            points={points}
            fill="none"
            stroke="#6366f1"
            strokeWidth={2}
            vectorEffect="non-scaling-stroke"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-gray-400">
          {data[0].day} → {data.at(-1)!.day}
        </span>
        <span className="text-sm font-bold text-gray-900">{max} captchas</span>
      </div>
    </>
  );
}

function TopReporters({ rows }: { rows: CaptchaRow[] }) {
  const top = tally(rows, (r) => r.machine_id).slice(0, 3);
  if (top.length === 0) return <p className="text-xs text-gray-400">No reporters yet</p>;
  return (
    <ol className="space-y-2">
      {top.map((r) => (
        <li key={r.label} className="flex items-baseline justify-between gap-3 text-xs">
          <span className="font-mono text-gray-700 break-all">{r.label}</span>
          <span className="text-gray-500 tabular-nums whitespace-nowrap">{r.count}</span>
        </li>
      ))}
    </ol>
  );
}

function RecentGrid({ recent }: { recent: RecentCaptcha[] }) {
  if (recent.length === 0) return <p className="text-xs text-gray-400">No captchas yet</p>;
  return (
    <div className="grid grid-cols-5 gap-2">
      {recent.map((c) => {
        const when = c.ts.slice(0, 16).replace("T", " ");
        const label = `${when} · ${c.machine_id.slice(0, 8)}`;
        return c.url ? (
          <a key={c.image_id} href={c.url} target="_blank" rel="noreferrer" title={label}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={c.url}
              alt={`Captcha from ${label}`}
              className="aspect-square w-full object-cover bg-gray-900 rounded-sm border border-gray-200 hover:border-gray-400 transition-colors"
            />
          </a>
        ) : (
          // Already pulled out of the bucket by /pull-captcha-images, or the upload never landed.
          <div
            key={c.image_id}
            title={label}
            className="aspect-square w-full rounded-sm border border-dashed border-gray-200 grid place-items-center text-[10px] text-gray-400"
          >
            pulled
          </div>
        );
      })}
    </div>
  );
}

export function CaptchaPanel({ rows, recent }: { rows: CaptchaRow[]; recent: RecentCaptcha[] }) {
  return (
    <div className="space-y-6">
      <div className={CARD}>
        <h3 className={TITLE}>Images Over Time (cumulative)</h3>
        <CumulativeLine rows={rows} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className={CARD}>
          <h3 className={TITLE}>Top 3 Reporter IDs</h3>
          <TopReporters rows={rows} />
        </div>
        <div className={CARD}>
          <h3 className={TITLE}>Most Recent 10 Captchas</h3>
          <RecentGrid recent={recent} />
        </div>
      </div>
    </div>
  );
}
