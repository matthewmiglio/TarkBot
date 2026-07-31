import { execSync } from "node:child_process";

// Kept out of site.ts on purpose: this imports node:child_process, and site.ts is
// safe to pull into a client component. Server-only callers import from here.

/**
 * A date out of a file's git history, rather than out of the clock.
 * `new Date()` at build time would claim a fresh edit on every deploy, which
 * trains crawlers to ignore the field.
 *
 * `first` reads the commit that added the file instead of the newest one.
 */
function gitDate(path: string, first = false): Date {
  try {
    const range = first ? "--diff-filter=A --reverse" : "-1";
    const iso = execSync(`git log ${range} --format=%cI -- ${path}`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    })
      .trim()
      .split("\n")[0];
    if (iso) return new Date(iso);
  } catch {
    // No git in the build image, or a shallow clone with no history for the file.
  }
  return new Date();
}

/** Home page dates, shared by the sitemap and the WebPage JSON-LD node. */
export const HOME_MODIFIED = gitDate("src/app/page.tsx");
export const HOME_PUBLISHED = gitDate("src/app/page.tsx", true);
