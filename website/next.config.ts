import type { NextConfig } from "next";

// Security and caching headers, plus a locked trailing-slash policy. Nothing here
// changes a rendered pixel; it is all response metadata.
// No CSP: the page embeds youtube-nocookie and a wrong policy breaks the iframe.

const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), browsing-topics=()",
  },
  // Two years, subdomains included, preload-list eligible. Submitting to
  // hstspreload.org is a separate one-time manual step.
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
];

const nextConfig: NextConfig = {
  // One canonical URL shape. Without this /  and // are both reachable and
  // crawlers treat them as duplicates.
  trailingSlash: false,
  poweredByHeader: false,

  // No Cache-Control rule for /_next/static: Next already serves it immutable in
  // production, and overriding it here breaks asset reloading in dev.
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;
