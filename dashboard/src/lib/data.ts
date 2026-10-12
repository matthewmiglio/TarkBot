import "server-only";

// The dashboard's whole data layer. Reads the Tarkbot_ tables straight off
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

export type SnipeRow = {
  ts: string;
  machine_id: string;
  version: string | null;
  item: string;
  price: number;
  trader_value: number;
  // Generated in Postgres as trader_value - price, so it can never disagree with the two
  // numbers it comes from. The app does not send it.
  margin: number;
};

// ponytail: this is the one table that will outgrow ROW_CAP first, since it is a row per
// purchase rather than a row per visit. When it does, the cap silently drops the oldest rows
// and "all time" quietly stops being all time. Move it to a Postgres aggregate then.
export async function getSnipes(): Promise<SnipeRow[]> {
  return table<SnipeRow>(
    "Tarkbot_snipes",
    "ts,machine_id,version,item,price,trader_value,margin",
  );
}

export type CaptchaRow = { ts: string; machine_id: string; image_id: string };
export type RecentCaptcha = CaptchaRow & { url: string | null };

const CAPTCHA_BUCKET = "Tarkbot_captchas";
const RECENT_CAPTCHAS = 10;
const SIGNED_FOR = 60 * 60; // seconds, long enough for a dashboard left open

/**
 * Every captcha row (for the chart and the reporter tally) plus the newest ten with a signed url.
 *
 * The bucket is private, so the browser cannot fetch an image without a signed url, and the
 * service key must never reach it. /pull-captcha-images empties the bucket, so an older row's
 * image is often gone: it signs as an error and comes back with url null.
 */
export async function getCaptchas(): Promise<{ rows: CaptchaRow[]; recent: RecentCaptcha[] }> {
  const rows = await table<CaptchaRow>("Tarkbot_captchas", "ts,machine_id,image_id");
  const newest = rows.slice(0, RECENT_CAPTCHAS); // table() orders by ts desc
  const urls = new Map<string, string>();
  if (newest.length && SUPABASE_URL && SERVICE_KEY) {
    try {
      const res = await fetch(`${SUPABASE_URL}/storage/v1/object/sign/${CAPTCHA_BUCKET}`, {
        method: "POST",
        headers: {
          apikey: SERVICE_KEY,
          Authorization: `Bearer ${SERVICE_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          expiresIn: SIGNED_FOR,
          paths: newest.map((r) => `${r.image_id}.png`),
        }),
        cache: "no-store",
      });
      if (res.ok) {
        for (const s of (await res.json()) as { path: string; signedURL: string | null }[]) {
          if (s.signedURL) {
            urls.set(
              s.path,
              s.signedURL.startsWith("http") ? s.signedURL : `${SUPABASE_URL}/storage/v1${s.signedURL}`,
            );
          }
        }
      } else {
        console.error("sign captchas failed", res.status, await res.text());
      }
    } catch (e) {
      console.error("sign captchas threw", e);
    }
  }
  return {
    rows,
    recent: newest.map((r) => ({ ...r, url: urls.get(`${r.image_id}.png`) ?? null })),
  };
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
