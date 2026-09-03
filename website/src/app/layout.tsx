import type { Metadata, Viewport } from "next";
import { Barlow_Semi_Condensed, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AnalyticsTracker } from "./analytics-tracker";
import { homeGraph, serialize } from "@/lib/jsonld";
import { DESCRIPTION, SITE_NAME, SITE_URL, TAGLINE } from "@/lib/site";

// Bahnschrift SemiCondensed is what the app uses and Windows ships it, but it is
// not a web font. Barlow Semi Condensed is the same DIN-condensed register.
const condensed = Barlow_Semi_Condensed({
  variable: "--font-condensed",
  weight: ["300", "400", "500", "600"],
  subsets: ["latin"],
});

const mono = JetBrains_Mono({
  variable: "--font-mono-stack",
  subsets: ["latin"],
});

// Static, not generateMetadata: from Next 15.2 a generateMetadata that touches
// cookies/headers/uncached fetch gets its tags streamed into <body>, where
// HTML-only scrapers (and plenty of link unfurlers) never see them.
export const metadata: Metadata = {
  // Makes every relative OG/canonical URL below resolve absolutely.
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — ${TAGLINE}`,
    template: `%s | ${SITE_NAME}`,
  },
  description: DESCRIPTION,
  applicationName: SITE_NAME,
  keywords: [
    "Tarkbot",
    "Escape From Tarkov",
    "flea market bot",
    "Tarkov flea market",
    "Tarkov selling bot",
    "Tarkov flea sniper",
    "Tarkov hideout bot",
    "Tarkov crafting bot",
    "Tarkov gym bot",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    locale: "en_US",
    url: "/",
    title: `${SITE_NAME} — ${TAGLINE}`,
    description: DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} — ${TAGLINE}`,
    description: DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
    // Lets Google and the AI Overviews quote the full text and a large image
    // instead of a truncated snippet.
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },
  // Set these in the Vercel project when the properties are claimed; unset means
  // the tag is simply omitted.
  verification: {
    google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION,
    other: process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION
      ? { "msvalidate.01": process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION }
      : {},
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0d0e0d",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${condensed.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans">
        {/* Server-rendered so it is in the HTML source, and escaped by serialize()
            so no string value can close the tag early. Never next/script. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: serialize(homeGraph()) }}
        />
        <AnalyticsTracker />
        {children}
      </body>
    </html>
  );
}
