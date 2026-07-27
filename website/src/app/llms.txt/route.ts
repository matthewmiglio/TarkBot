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
the game window with template matching, picks an item, reads Tarkov's own suggested
price off the screen, undercuts it, and lists it on the flea market. It repeats until
stopped, and cancels offers that have not sold once the board stays full.

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
