import type { MetadataRoute } from "next";

import { HOME_MODIFIED } from "@/lib/last-changed";
import { POSTS } from "@/lib/posts";
import { SITE_URL } from "@/lib/site";

// One public route, so this is a list of one. It exists so the URL is declared
// with a real lastModified and so robots.ts has something to point at.
// priority and changeFrequency are omitted: Google ignores both.

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      lastModified: HOME_MODIFIED,
    },
    { url: `${SITE_URL}/blog`, lastModified: POSTS[0].date },
    ...POSTS.map((p) => ({ url: `${SITE_URL}/blog/${p.slug}`, lastModified: p.date })),
  ];
}
