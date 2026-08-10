import "server-only";

// The dashboard's whole data layer. Reads the two Tarkbot_ tables straight off
// PostgREST with the service key, server-side only, so no key ever reaches the
// browser and both tables can keep RLS on with no policies.
// ponytail: no @supabase/supabase-js and no /api/db proxy — the page is a
// server component, so it can just fetch. Add a proxy when a client component
// needs to query on its own.

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

export type ViewEvent = {
  ts: string;
  path: string;
  referrer: string | null;
  visitor_id: string | null;
  session_id: string | null;
  country: string | null;
  city: string | null;
};

export type DownloadEvent = {
  ts: string;
  visitor_id: string | null;
  referrer: string | null;
  country: string | null;
};

// ponytail: one flat read of each table, capped. Tarkbot's traffic is nowhere
// near this. Move to a Postgres aggregate (like fishbot's get_* RPCs) when the
// cap starts truncating rather than when it looks big.
const ROW_CAP = 50_000;

async function table<T>(name: string, columns: string): Promise<T[]> {
  if (!SUPABASE_URL || !SERVICE_KEY) return [];
  const url =
    `${SUPABASE_URL}/rest/v1/${encodeURIComponent(name)}` +
    `?select=${columns}&order=ts.desc&limit=${ROW_CAP}`;
  try {
    const res = await fetch(url, {
      headers: { apikey: SERVICE_KEY, Authorization: `Bearer ${SERVICE_KEY}` },
      cache: "no-store",
    });
    if (!res.ok) {
      console.error(`read ${name} failed`, res.status, await res.text());
      return [];
    }
    return (await res.json()) as T[];
  } catch (e) {
    console.error(`read ${name} threw`, e);
    return [];
  }
}

export type FeedbackItem = {
  id: number;
  created_at: string;
  name: string | null;
  email: string | null; // already masked by the RPC — ma*******04@gmail.com
  message: string;
  page: string | null;
  country: string | null;
};

// The raw email never leaves Postgres: tarkbot_feedback_masked() does the
// masking and the ordering, so the dashboard only ever sees the masked form.
export async function getFeedback(): Promise<FeedbackItem[]> {
  if (!SUPABASE_URL || !SERVICE_KEY) return [];
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/tarkbot_feedback_masked`, {
      method: "POST",
      headers: {
        apikey: SERVICE_KEY,
        Authorization: `Bearer ${SERVICE_KEY}`,
        "Content-Type": "application/json",
      },
      body: "{}",
      cache: "no-store",
    });
    if (!res.ok) {
      console.error("read feedback failed", res.status, await res.text());
      return [];
    }
    return (await res.json()) as FeedbackItem[];
  } catch (e) {
    console.error("read feedback threw", e);
    return [];
  }
}

export type ErrorReport = {
  id: number;
  ts: string;
  machine_id: string;
  version: string | null;
  error: { type?: string; message?: string; traceback?: string } | null;
  before_screenshot_id: string | null;
  after_screenshot_id: string | null;
  // Signed at read time; null when the app never finished uploading that half.
  before_url: string | null;
  after_url: string | null;
};

const SCREENSHOTS = "Tarkbot_screenshots";
const SIGNED_FOR = 60 * 60; // seconds, long enough for a dashboard left open

/** Signed urls for screenshot ids, keyed by "<id>.png". One request for the lot. */
async function signScreenshots(ids: string[]): Promise<Map<string, string>> {
  const urls = new Map<string, string>();
  if (!ids.length || !SUPABASE_URL || !SERVICE_KEY) return urls;
  try {
    // The bucket is private, so the browser cannot fetch these on its own and the service key
    // must not be handed to it either. Signing them here is the only way the pictures render.
    const res = await fetch(`${SUPABASE_URL}/storage/v1/object/sign/${SCREENSHOTS}`, {
      method: "POST",
      headers: {
        apikey: SERVICE_KEY,
        Authorization: `Bearer ${SERVICE_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ expiresIn: SIGNED_FOR, paths: ids.map((id) => `${id}.png`) }),
      cache: "no-store",
    });
    if (!res.ok) {
      console.error("sign screenshots failed", res.status, await res.text());
      return urls;
    }
    for (const row of (await res.json()) as { path: string; signedURL: string | null }[]) {
      // A report whose upload never landed signs as an error, and is simply left without a url.
      if (row.signedURL) {
        urls.set(
          row.path,
          row.signedURL.startsWith("http") ? row.signedURL : `${SUPABASE_URL}/storage/v1${row.signedURL}`,
        );
      }
    }
  } catch (e) {
    console.error("sign screenshots threw", e);
  }
  return urls;
}

export async function getErrors(): Promise<ErrorReport[]> {
  const rows = await table<Omit<ErrorReport, "before_url" | "after_url">>(
    "Tarkbot_errors",
    "id,ts,machine_id,version,error,before_screenshot_id,after_screenshot_id",
  );
  const ids = rows.flatMap((r) => [r.before_screenshot_id, r.after_screenshot_id]).filter(
    (id): id is string => Boolean(id),
  );
  const urls = await signScreenshots(ids);
  return rows.map((r) => ({
    ...r,
    before_url: (r.before_screenshot_id && urls.get(`${r.before_screenshot_id}.png`)) || null,
    after_url: (r.after_screenshot_id && urls.get(`${r.after_screenshot_id}.png`)) || null,
  }));
}

export async function getAnalytics() {
  const [views, downloads] = await Promise.all([
    table<ViewEvent>(
      "Tarkbot_analytics_events",
      "ts,path,referrer,visitor_id,session_id,country,city",
    ),
    table<DownloadEvent>("Tarkbot_downloads", "ts,visitor_id,referrer,country"),
  ]);
  return { views, downloads, configured: Boolean(SUPABASE_URL && SERVICE_KEY) };
}
