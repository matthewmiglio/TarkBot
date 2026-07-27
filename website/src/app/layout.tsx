import type { Metadata } from "next";
import { Barlow_Semi_Condensed, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AnalyticsTracker } from "./analytics-tracker";

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

export const metadata: Metadata = {
  title: "Tarkbot — free flea market seller for Escape From Tarkov",
  description:
    "Tarkbot reads your screen, prices your loot off Tarkov's own suggested price, undercuts it and lists it on the flea market. Free, open, no account.",
  openGraph: {
    title: "Tarkbot",
    description:
      "Free screen-reading flea market seller for Escape From Tarkov. Reads the suggested price, undercuts it, lists the item, repeats.",
    type: "website",
  },
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
        <AnalyticsTracker />
        {children}
      </body>
    </html>
  );
}
