import { execSync } from "node:child_process";
import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// One public route, so this is a list of one. It exists so the URL is declared
// with a real lastModified and so robots.ts has something to point at.
// priority and changeFrequency are omitted: Google ignores both.

/**
 * When the home page last actually changed, from git rather than from the clock.
 * `new Date()` at build time would claim a fresh edit on every deploy, which
 * trains crawlers to ignore the field.
 */
function lastChanged(path: string): Date {
  try {
    const iso = execSync(`git log -1 --format=%cI -- ${path}`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    if (iso) return new Date(iso);
  } catch {
    // No git in the build image, or a shallow clone with no history for the file.
  }
  return new Date();
}

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      lastModified: lastChanged("src/app/page.tsx"),
    },
  ];
}
