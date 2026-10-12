import type { MetadataRoute } from "next";

import { absolute } from "@/lib/site";

// Vercel sets this to "preview" on every non-production deployment. Preview hosts
// get a blanket disallow so a *.vercel.app copy never competes with tarkbot.org.
const IS_PREVIEW = process.env.VERCEL_ENV === "preview";

// AI crawlers, all allowed, training bots included. A July 2026 study of 1,058
// domains (cloro.dev/research/ai-crawler-blocks) found sites blocking GPTBot got
// a median ~100x fewer ChatGPT citations, and blocking ClaudeBot or
// Google-Extended cut Perplexity and ChatGPT citations several times over. The
// page is a free tool's pitch, not content worth protecting, so a block buys
// nothing. The search bots are listed explicitly so the intent is on record.
const AI_SEARCH_BOTS = [
  "OAI-SearchBot",
  "ChatGPT-User",
  "Claude-SearchBot",
  "Claude-User",
  "PerplexityBot",
  "Google-Extended",
];
// To block training (only worth it if the writing itself ever becomes the
// product), add this list back to the rules below as `disallow: "/"`.
const AI_TRAINING_BOTS = ["GPTBot", "ClaudeBot", "CCBot", "Applebot-Extended"];

export default function robots(): MetadataRoute.Robots {
  if (IS_PREVIEW) {
    return { rules: { userAgent: "*", disallow: "/" } };
  }

  return {
    rules: [
      // /_next/static and /_next/image stay crawlable on purpose: Googlebot needs
      // the CSS and JS to render the page.
      { userAgent: "*", allow: "/", disallow: "/api/" },
      { userAgent: [...AI_SEARCH_BOTS, ...AI_TRAINING_BOTS], allow: "/", disallow: "/api/" },
      // Ignores robots.txt in practice; the middleware 403 is what actually stops
      // it. Listed anyway so the intent is on the record.
      { userAgent: "Bytespider", disallow: "/" },
    ],
    sitemap: absolute("/sitemap.xml"),
    host: absolute("/"),
  };
}
