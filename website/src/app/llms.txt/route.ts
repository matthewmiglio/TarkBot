import {
  DEMO_VIDEO,
  DESCRIPTION,
  DISCORD_URL,
  RELEASES_URL,
  REPO_URL,
  SITE_NAME,
  SITE_URL,
} from "@/lib/site";

// A Markdown map of the site for AI search engines, which read this in preference
// to scraping rendered HTML. One page, so it is short by definition.
// ponytail: no llms-full.txt. It would be a second copy of the page's body text
// with nothing keeping the two in sync, and there is only one page to read.

export const dynamic = "force-static";

const BODY = `# ${SITE_NAME}

> ${DESCRIPTION}

${SITE_NAME} is free, open-source Windows software for Escape From Tarkov. It reads
the game window with template matching and drives the mouse, and it has four modes in
one control panel:

- Flea selling: picks an item from the stash or a scav case, reads Tarkov's own
  suggested price off the screen, undercuts it, lists it on the flea market, and
  cancels stale offers when the board stays full.
- Flea sniping: walks a watchlist and buys any offer listed far enough under a
  trader's buy-back price to flip for a profit, skipping locked or dollar-priced offers.
- Hideout gym: runs the gym workout skill-check, timing each press to the moment the
  two rings meet.
- Hideout crafting: keeps several hideout crafts running, buying each missing
  ingredient off the flea, collecting finished output, and keeping the water collector
  filtered.

It works by reading pixels and moving the mouse. There is no memory reading, no
injection, no packet manipulation, no raid automation, no account, and no external
price API.

## Pages

- [${SITE_NAME}](${SITE_URL}): what it does, how it works, and the download link.

## Elsewhere

- [Source code](${REPO_URL}): the full Python source.
- [Downloads](${RELEASES_URL}): Windows installers, one per release.
- [Discord](${DISCORD_URL}): support and questions.
- [Demo video](${DEMO_VIDEO.contentUrl}): an unedited selling run.
`;

export function GET() {
  return new Response(BODY, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600, s-maxage=86400",
    },
  });
}
