// One source for everything that has to agree across metadata, robots, sitemap,
// JSON-LD and llms.txt. Change a URL here or they drift apart silently.

export const SITE_URL = "https://tarkbot.org";
export const SITE_NAME = "Tarkbot";

// Lower-case "free" on purpose: `${SITE_NAME} — ${TAGLINE}` has to reproduce the
// existing <title> character for character. Retitling the page is a copy change.
export const TAGLINE = "free flea market seller for Escape From Tarkov";
export const DESCRIPTION =
  "Tarkbot reads your screen, prices your loot off Tarkov's own suggested price, undercuts it and lists it on the flea market. Free, open, no account.";

// The generated card from app/opengraph-image.tsx. Next serves it with a
// cache-busting query on the meta tag, but the bare route is a stable 200, so
// this is what JSON-LD points at.
export const OG_IMAGE = { path: "/opengraph-image", width: 1200, height: 630 };

export const REPO_URL = "https://github.com/matthewmiglio/TarkBot";
export const RELEASES_URL = `${REPO_URL}/releases`;
export const DISCORD_URL = "https://discord.gg/Vx4tdR3N8A";

// Knowledge-panel signals. Only profiles that actually exist and actually point
// back here — an invented sameAs is worse than a short list.
export const SAME_AS = [REPO_URL, DISCORD_URL];

// The demo embed on the home page. uploadDate and duration are read off the real
// YouTube watch page (241s, published 2026-07-27), not guessed: Google treats
// invented VideoObject dates as a structured-data violation. Re-read them if the
// video is ever replaced.
export const DEMO_VIDEO = {
  id: "vDr1qelr4RI",
  name: "Tarkbot demo: a full flea market selling run",
  description:
    "An unedited run of Tarkbot: item picked out of the stash, suggested price read off the screen, undercut, listed on the flea market, and straight on to the next one.",
  uploadDate: "2026-07-27T13:00:48-07:00",
  duration: "PT4M1S",
  get thumbnailUrl() {
    return `https://i.ytimg.com/vi/${this.id}/maxresdefault.jpg`;
  },
  get contentUrl() {
    return `https://www.youtube.com/watch?v=${this.id}`;
  },
  get embedUrl() {
    return `https://www.youtube-nocookie.com/embed/${this.id}`;
  },
} as const;

/** Absolute URL for a site-relative path. Every url/image in metadata and JSON-LD goes through this. */
export function absolute(path: string): string {
  return new URL(path, SITE_URL).toString();
}
