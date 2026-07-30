import type { FeedbackItem } from "@/lib/data";

// ponytail: a server component. It is a list with no controls, so it needs no
// "use client", no state and none of figures.tsx's period machinery.

export function FeedbackList({ items }: { items: FeedbackItem[] }) {
  // The RPC already returns newest first; re-sorting here keeps that true even
  // if the read path ever changes.
  const rows = [...items].sort((a, b) => b.created_at.localeCompare(a.created_at));

  return (
    <div className="bg-gray-50 rounded-md p-6 border border-gray-200">
      <div className="flex items-center justify-between mb-4 gap-4">
        <h3 className="text-sm font-bold text-gray-900">Feedback</h3>
        <span className="text-xs text-gray-400 tabular-nums">{rows.length} total</span>
      </div>
      {rows.length === 0 ? (
        <p className="text-xs text-gray-400">Nobody has sent anything yet</p>
      ) : (
        <div className="space-y-3 max-h-[36rem] overflow-y-auto pr-1">
          {rows.map((r) => (
            <div key={r.id} className="border-b border-gray-100 pb-3 last:border-0 last:pb-0">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
                <span className="font-medium text-gray-900">{r.name || "Anonymous"}</span>
                {r.email && <span className="text-gray-500">{r.email}</span>}
                <span className="text-gray-400 tabular-nums ml-auto">
                  {r.created_at.slice(0, 16).replace("T", " ")}
                </span>
                {r.country && <span className="text-gray-400">{r.country}</span>}
              </div>
              <p className="mt-1.5 text-sm text-gray-700 whitespace-pre-wrap break-words">
                {r.message}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
