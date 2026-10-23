// Post metadata lives here; each long body lives in src/content/blog/<slug>.ts.
// A body entry is one paragraph, and one that starts with "## " is a subheading.
// ponytail: TS arrays rather than markdown, so there is no parser to add. Move to
// MDX when a post needs images, lists or links inside the text.

import { body as levelStrengthEnduranceFast } from "@/content/blog/level-strength-endurance-fast";
import { body as scavCaseLoot } from "@/content/blog/scav-case-loot";
import { body as fleaMarketUndercut } from "@/content/blog/flea-market-undercut";
import { body as fleaToTraderFlipping } from "@/content/blog/flea-to-trader-flipping";
import { body as hideoutPassiveIncome } from "@/content/blog/hideout-passive-income";
import { body as bitcoinFarmWorthIt } from "@/content/blog/bitcoin-farm-worth-it";
import { body as roublesStartOfWipe } from "@/content/blog/roubles-start-of-wipe";
import { body as profitableHideoutCrafts } from "@/content/blog/profitable-hideout-crafts";
import { body as waterCollector } from "@/content/blog/water-collector";
import { body as cantListOnFlea } from "@/content/blog/cant-list-on-flea";

export type Post = {
  slug: string;
  title: string;
  excerpt: string;
  date: string; // ISO yyyy-mm-dd
  image: string; // path under public/
  body: string[];
  cta: string; // the closing pitch, shown in a box that links to the home page
};

export const POSTS: Post[] = [
  {
    slug: "level-strength-endurance-fast",
    title: "How to level Strength and Endurance fast",
    excerpt:
      "Hideout gym reps raise Strength and Endurance with no raid risk. The catch is sitting through rep after rep of the skill check and hitting each one on time.",
    date: "2026-10-23",
    image: "/blog/tarkov2.webp",
    body: levelStrengthEnduranceFast,
    cta: "Tired of clicking 15 reps a set? Tarkbot's gym mode hits the skill check for you, timing each press to the moment the rings meet.",
  },
  {
    slug: "scav-case-loot",
    title: "What should you do with scav case loot?",
    excerpt:
      "Scav cases fill up fast with junk that's annoying to price and list one item at a time. A lot of it still sells on the flea for more than a trader pays.",
    date: "2026-10-23",
    image: "/blog/1a1jejrfg9h61.webp",
    body: scavCaseLoot,
    cta: "Let Tarkbot's sell mode empty your scav cases straight onto the flea. It picks each item, reads Tarkov's suggested price, undercuts it and lists it.",
  },
  {
    slug: "flea-market-undercut",
    title: "How to sell on the flea without being undercut constantly",
    excerpt:
      "Price a bit under the lowest comparable offer and pull listings that haven't sold. Most players skip that second step.",
    date: "2026-10-23",
    image: "/blog/FleaMarket.webp",
    body: fleaMarketUndercut,
    cta: "Tarkbot's sell mode undercuts automatically and cancels stale offers for you, so your slots stay full of offers that can actually sell.",
  },
  {
    slug: "flea-to-trader-flipping",
    title: "How to make money buying low and selling to traders",
    excerpt:
      "People list items on the flea for less than Therapist or Jaeger will pay. Buy them, walk them to the trader, and keep the difference.",
    date: "2026-10-23",
    image: "/blog/1821251121_2022-04-2711-28(0).png.96cc0b26f821ffd3ee75adfbee303890.webp",
    body: fleaToTraderFlipping,
    cta: "Don't search 77 items by hand. Tarkbot's snipe mode watches the list and buys any offer listed far enough under what a trader pays.",
  },
  {
    slug: "hideout-passive-income",
    title: "What's the best passive income in the hideout?",
    excerpt:
      "The bitcoin farm, moonshine, and crafts like fleece and Cordura pay out while you're offline, but only if you keep restarting them.",
    date: "2026-10-23",
    image: "/blog/zqLyS7WVqq6zYtXGfnXEya.webp",
    body: hideoutPassiveIncome,
    cta: "Tarkbot's craft mode collects finished crafts, restarts them and buys the missing ingredients for every craft you pick.",
  },
  {
    slug: "bitcoin-farm-worth-it",
    title: "Is the bitcoin farm worth it?",
    excerpt:
      "What the farm costs against what one bitcoin sells for, and roughly how long it takes to pay itself off.",
    date: "2026-10-23",
    image: "/blog/HVD4aa6WgAA0NF7.webp",
    body: bitcoinFarmWorthIt,
    cta: "Never let a finished bitcoin sit uncollected. Tarkbot's craft mode collects it for you, so the farm keeps producing.",
  },
  {
    slug: "roubles-start-of-wipe",
    title: "How do you make roubles at the start of a wipe?",
    excerpt:
      "Early on, money comes from scav runs, fast flea flips and cheap crafts. The stash fills up quicker than you can sell it.",
    date: "2026-10-23",
    image: "/blog/welcome-to-tarkov_feature.webp",
    body: roublesStartOfWipe,
    cta: "Turn a full stash into roubles without listing it yourself. Try Tarkbot's sell mode.",
  },
  {
    slug: "profitable-hideout-crafts",
    title: "Which hideout crafts actually make a profit?",
    excerpt:
      "Compare what the ingredients cost on the flea with what the output sells for. Some crafts lose money once you buy the ingredients.",
    date: "2026-10-23",
    image: "/blog/escape-from-tarkov-flea-market-guide.webp",
    body: profitableHideoutCrafts,
    cta: "Tarkbot's craft mode buys what each craft needs, but only under the price limit you set.",
  },
  {
    slug: "water-collector",
    title: "How do you keep the water collector running?",
    excerpt:
      "It needs a water filter in its slot, and filters run out. Forget to replace one and the collector sits idle.",
    date: "2026-10-23",
    image: "/blog/ss_ce1407465e6207a69dafd22e7e071097c4a56757.1920x1080.webp",
    body: waterCollector,
    cta: "Tarkbot's craft mode collects the water and buys a new filter when you're out.",
  },
  {
    slug: "cant-list-on-flea",
    title: "Why can't you list anything on the flea?",
    excerpt:
      "A quick explainer on the flea level requirement, found in raid items, offer slots and listing fees.",
    date: "2026-10-23",
    image: "/blog/MarketOfferCreation.webp",
    body: cantListOnFlea,
    cta: "Once you're unlocked, let Tarkbot's sell mode keep every offer slot full.",
  },
];

export function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}
