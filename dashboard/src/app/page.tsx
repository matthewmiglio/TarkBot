import { getAnalytics, getErrors, getFeedback } from "@/lib/data";
import {
  ActivityFeed, DownloadSources, DownloadsOverTime, PagePopularity,
  SummaryTiles, TrafficSources, ViewsByCountry, ViewsOverTime,
} from "@/components/figures";
import { FeedbackList } from "@/components/feedback";
import { ErrorList } from "@/components/errors";

// Every figure reads from one server-side fetch, so the page is always fresh
// and the browser makes no data requests of its own.
export const dynamic = "force-dynamic";

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "traffic", label: "Traffic" },
  { id: "downloads", label: "Downloads" },
  { id: "activity", label: "Activity" },
  { id: "feedback", label: "Feedback" },
  { id: "errors", label: "Crashes" },
];

export default async function Page() {
  const [{ views, downloads, configured }, feedback, errors] = await Promise.all([
    getAnalytics(),
    getFeedback(),
    getErrors(),
  ]);

  return (
    <div className="min-h-screen bg-[#f9f9f7] flex flex-col text-gray-900">
      <header className="px-6 pt-5 pb-1">
        <h1 className="text-sm font-bold uppercase tracking-widest">
          Tarkbot <span className="text-gray-400">· Dashboard</span>
        </h1>
      </header>

      <nav className="sticky top-0 z-40 bg-[#f9f9f7]/90 backdrop-blur-sm border-b border-gray-200">
        <div className="px-6 py-2 flex gap-2 overflow-x-auto">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className="whitespace-nowrap px-3 py-1.5 rounded-sm text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
            >
              {s.label}
            </a>
          ))}
        </div>
      </nav>

      <div className="px-6 py-8 flex-1">
        {!configured && (
          <p className="mb-8 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            SUPABASE_URL / SUPABASE_SERVICE_KEY are not set, so every figure below is empty.
          </p>
        )}

        <section id="overview" className="mb-12 scroll-mt-14">
          <h2 className="text-sm font-bold uppercase tracking-widest mb-6 pb-2 border-b border-gray-200">
            Overview
          </h2>
          <SummaryTiles views={views} downloads={downloads} />
          <div className="mt-6">
            <ViewsOverTime views={views} />
          </div>
        </section>

        <section id="traffic" className="mb-12 scroll-mt-14">
          <h2 className="text-sm font-bold uppercase tracking-widest mb-6 pb-2 border-b border-gray-200">
            Traffic &amp; Acquisition
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TrafficSources views={views} />
            <PagePopularity views={views} />
          </div>
          <div className="mt-6">
            <ViewsByCountry views={views} />
          </div>
        </section>

        <section id="downloads" className="mb-12 scroll-mt-14">
          <h2 className="text-sm font-bold uppercase tracking-widest mb-6 pb-2 border-b border-gray-200">
            Downloads
          </h2>
          <DownloadsOverTime downloads={downloads} />
          <div className="mt-6">
            <DownloadSources downloads={downloads} />
          </div>
        </section>

        <section id="activity" className="mb-12 scroll-mt-14">
          <h2 className="text-sm font-bold uppercase tracking-widest mb-6 pb-2 border-b border-gray-200">
            Live Activity
          </h2>
          <ActivityFeed views={views} downloads={downloads} />
        </section>

        <section id="feedback" className="mb-12 scroll-mt-14">
          <h2 className="text-sm font-bold uppercase tracking-widest mb-6 pb-2 border-b border-gray-200">
            Feedback
          </h2>
          <FeedbackList items={feedback} />
        </section>

        <section id="errors" className="mb-12 scroll-mt-14">
          <h2 className="text-sm font-bold uppercase tracking-widest mb-6 pb-2 border-b border-gray-200">
            Crashes
          </h2>
          <ErrorList items={errors} />
        </section>
      </div>

      <footer className="px-6 py-6 border-t border-gray-200 text-xs text-gray-400">
        Reading Tarkbot_analytics_events, Tarkbot_downloads, Tarkbot_feedback and Tarkbot_errors.
        Screenshot links are signed for an hour and stop working after that; reload for fresh ones.
      </footer>
    </div>
  );
}
