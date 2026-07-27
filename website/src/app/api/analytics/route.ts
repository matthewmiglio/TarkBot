import type { NextRequest } from "next/server";

// Server half of the tracking. Writes to Supabase over PostgREST with the
// service key, so the browser never holds a key and both tables can keep RLS on
// with no policies at all.
// ponytail: raw fetch instead of @supabase/supabase-js — it is one INSERT.

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

const TABLES = {
  view: "Tarkbot_analytics_events",
  download: "Tarkbot_downloads",
} as const;

function location(req: NextRequest) {
  return {
    city: req.headers.get("x-vercel-ip-city"),
    state: req.headers.get("x-vercel-ip-country-region"),
    country: req.headers.get("x-vercel-ip-country"),
  };
}

export async function POST(req: NextRequest) {
  if (!SUPABASE_URL || !SERVICE_KEY) {
    return Response.json({ error: "analytics not configured" }, { status: 503 });
  }

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "bad json" }, { status: 400 });
  }

  const kind = body.kind === "download" ? "download" : "view";
  const path = typeof body.path === "string" ? body.path : null;
  if (!path) return Response.json({ error: "path required" }, { status: 400 });

  const str = (v: unknown) => (typeof v === "string" ? v.slice(0, 1024) : null);
  const { city, state, country } = location(req);

  // Downloads carry no path/ua/city/state — the table only has the columns below.
  const row =
    kind === "download"
      ? {
          visitor_id: str(body.visitor_id),
          session_id: str(body.session_id),
          referrer: str(body.referrer),
          country,
        }
      : {
          path,
          referrer: str(body.referrer),
          visitor_id: str(body.visitor_id),
          session_id: str(body.session_id),
          ua: str(body.ua),
          city,
          state,
          country,
        };

  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/${encodeURIComponent(TABLES[kind])}`,
    {
      method: "POST",
      headers: {
        apikey: SERVICE_KEY,
        Authorization: `Bearer ${SERVICE_KEY}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify(row),
    },
  );

  if (!res.ok) {
    console.error("analytics insert failed", res.status, await res.text());
    return Response.json({ error: "insert failed" }, { status: 502 });
  }
  return Response.json({ success: true });
}
