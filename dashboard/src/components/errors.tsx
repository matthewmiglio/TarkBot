import type { ErrorReport } from "@/lib/data";

// Crash reports from the desktop app, newest first, each with the screen either side of the
// failure. The pictures are the point: they are lossless pngs, so the fix for "nothing matched"
// is usually to open one full size and crop the control out of it as a new reference image.
//
// ponytail: a server component and a native <details> for the traceback. No "use client", no
// state, no accordion library. Plain <img> rather than next/image because these are signed urls
// on a Supabase host that would otherwise need a remotePatterns entry, and nothing here needs
// resizing.

function Shot({ label, url }: { label: string; url: string | null }) {
  if (!url) {
    return (
      <div className="flex-1">
        <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">{label}</div>
        <div className="h-64 rounded-sm border border-dashed border-gray-200 grid place-items-center text-xs text-gray-400">
          never uploaded
        </div>
      </div>
    );
  }
  return (
    <div className="flex-1 min-w-0">
      <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">{label}</div>
      <a href={url} target="_blank" rel="noreferrer" title={`Open the ${label} screenshot full size`}>
        {/* contain, not cover: a whole 1440p screen shrunk into this box is the point, and
            cropping it to a strip hides the part that failed. Dark backing so the letterboxing
            round a widescreen grab reads as deliberate. Click through for full size. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={url}
          alt={`${label} the crash`}
          className="h-64 w-full object-contain bg-gray-900 rounded-sm border border-gray-200 hover:border-gray-400 transition-colors"
        />
      </a>
    </div>
  );
}

export function ErrorList({ items }: { items: ErrorReport[] }) {
  const rows = [...items].sort((a, b) => b.ts.localeCompare(a.ts));
  const machines = new Set(rows.map((r) => r.machine_id)).size;

  return (
    <div className="bg-gray-50 rounded-md p-6 border border-gray-200">
      <div className="flex items-center justify-between mb-4 gap-4">
        <h3 className="text-sm font-bold text-gray-900">Crash reports</h3>
        <span className="text-xs text-gray-400 tabular-nums">
          {rows.length} from {machines} machine{machines === 1 ? "" : "s"}
        </span>
      </div>

      {rows.length === 0 ? (
        <p className="text-xs text-gray-400">Nothing has crashed yet</p>
      ) : (
        <div className="space-y-5 max-h-[48rem] overflow-y-auto pr-1">
          {rows.map((r) => (
            <div key={r.id} className="border-b border-gray-100 pb-5 last:border-0 last:pb-0">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
                <span className="font-medium text-gray-900">{r.error?.type ?? "Error"}</span>
                {/* Printed as sent: the version is the git tag, so it already carries its v,
                    and from source it is the word "dev". */}
                {r.version && <span className="text-gray-500">{r.version}</span>}
                {/* The first block is enough to tell reporters apart by eye, and the whole id
                    is on the title for when two of them start with the same characters. */}
                <span className="text-gray-400 font-mono" title={r.machine_id}>
                  {r.machine_id.slice(0, 8)}
                </span>
                <span className="text-gray-400 tabular-nums ml-auto">
                  {r.ts.slice(0, 16).replace("T", " ")}
                </span>
              </div>

              <p className="mt-1.5 text-sm text-gray-700 break-words">
                {r.error?.message || "no message"}
              </p>

              {r.error?.traceback && (
                <details className="mt-2">
                  <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700 w-fit">
                    Traceback
                  </summary>
                  <pre className="mt-2 text-[11px] leading-relaxed text-gray-600 bg-white border border-gray-200 rounded-sm p-3 overflow-x-auto whitespace-pre">
                    {r.error.traceback}
                  </pre>
                </details>
              )}

              <div className="mt-3 flex gap-3">
                <Shot label="before" url={r.before_url} />
                <Shot label="after" url={r.after_url} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
