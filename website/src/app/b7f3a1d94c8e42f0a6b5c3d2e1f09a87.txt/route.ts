// IndexNow key file. The folder name IS the key, and the body has to be the same
// string: that pair is the whole ownership proof. Renaming one without the other
// silently breaks submission.
//
// ponytail: no post-publish webhook. One page that changes a few times a year
// does not need an automated ping; the curl in the README does it in one line.
// Add a route handler here if the site ever grows a publishing flow.

export const dynamic = "force-static";

const KEY = "b7f3a1d94c8e42f0a6b5c3d2e1f09a87";

export function GET() {
  return new Response(KEY, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
