import type { MetadataRoute } from "next";

import { absolute } from "@/lib/site";

// Vercel sets this to "preview" on every non-production deployment. Preview hosts
// get a blanket disallow so a *.vercel.app copy never competes with tarkbot.org.
const IS_PREVIEW = process.env.VERCEL_ENV === "preview";

// AI crawlers split in two, and the useful policy is different for each half.
// Search/citation bots send traffic back and are allowed. Training scrapers take
// the text and send nothing, so they are blocked. Flip either list to change the
// policy; nothing else reads it.
const AI_SEARCH_BOTS = [
  "OAI-SearchBot",
  "ChatGPT-User",
  "Claude-SearchBot",
  "Claude-User",
  "PerplexityBot",
  "Google-Extended",
];
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
      { userAgent: AI_SEARCH_BOTS, allow: "/", disallow: "/api/" },
      { userAgent: AI_TRAINING_BOTS, disallow: "/" },
      // Ignores robots.txt in practice; the middleware 403 is what actually stops
      // it. Listed anyway so the intent is on the record.
      { userAgent: "Bytespider", disallow: "/" },
    ],
    sitemap: absolute("/sitemap.xml"),
    host: absolute("/"),
  };
}
