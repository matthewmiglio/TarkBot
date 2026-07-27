// Browser half of the tracking. Mirrors wow_fishbot's lib/analytics, minus
// FingerprintJS: a localStorage UUID is the same number for our purposes and
// costs no dependency.
// ponytail: swap in a fingerprint library only if cross-browser dedupe matters.

const VISITOR_KEY = "analytics_visitor_id";
const SESSION_KEY = "analytics_session_id";
const SESSION_TS_KEY = "analytics_session_ts";
const SESSION_TIMEOUT = 30 * 60 * 1000;

function uuid(): string {
  return crypto.randomUUID();
}

export function getVisitorId(): string {
  let id = localStorage.getItem(VISITOR_KEY);
  if (!id) {
    id = uuid();
    localStorage.setItem(VISITOR_KEY, id);
  }
  return id;
}

export function getSessionId(): string {
  const now = Date.now();
  const lastTs = localStorage.getItem(SESSION_TS_KEY);
  const existing = localStorage.getItem(SESSION_KEY);

  const alive = existing && lastTs && now - parseInt(lastTs, 10) < SESSION_TIMEOUT;
  const id = alive ? existing : uuid();

  localStorage.setItem(SESSION_KEY, id);
  localStorage.setItem(SESSION_TS_KEY, String(now));
  return id;
}

function isLocal(): boolean {
  return ["localhost", "127.0.0.1"].includes(window.location.hostname);
}

async function post(kind: "view" | "download", path: string, referrer: string | null) {
  if (typeof window === "undefined" || isLocal()) return;
  try {
    await fetch("/api/analytics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        kind,
        path,
        referrer,
        visitor_id: getVisitorId(),
        session_id: getSessionId(),
        ua: navigator.userAgent,
      }),
      keepalive: true, // the download click navigates away mid-request
    });
  } catch {
    // Analytics never breaks the page.
  }
}

export function trackPageView(path?: string) {
  return post("view", path ?? window.location.pathname, document.referrer || null);
}

export function trackDownload() {
  return post("download", "/download", document.referrer || null);
}
