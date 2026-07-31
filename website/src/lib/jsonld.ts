import { HOME_MODIFIED, HOME_PUBLISHED } from "./last-changed";
import {
  absolute,
  DEMO_VIDEO,
  DESCRIPTION,
  DISCORD_URL,
  OG_IMAGE,
  REPO_URL,
  SAME_AS,
  SITE_NAME,
  SITE_URL,
  TAGLINE,
} from "./site";

// One @graph for the whole page rather than a pile of separate scripts. Nodes get
// stable @id fragments and reference each other by @id, so Organization is
// described once and pointed at from everywhere else.

const ORGANIZATION = absolute("/#organization");
const WEBSITE = absolute("/#website");
const WEBPAGE = absolute("/#webpage");
const APP = absolute("/#software");
const VIDEO = absolute("/#demo-video");
const IMAGE = `${WEBPAGE}-image`;

export function homeGraph() {
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": ORGANIZATION,
        name: SITE_NAME,
        url: SITE_URL,
        description: DESCRIPTION,
        sameAs: SAME_AS,
        image: { "@id": IMAGE },
        // No logo: there is no square brand mark on disk, and Google would
        // rather have the field absent than the OG card cropped into one.
        contactPoint: {
          "@type": "ContactPoint",
          contactType: "customer support",
          url: DISCORD_URL,
          availableLanguage: "English",
        },
      },
      {
        // The node the WebPage's primaryImageOfPage points at. Without this the
        // reference dangles and the whole graph fails validation.
        "@type": "ImageObject",
        "@id": IMAGE,
        url: absolute(OG_IMAGE.path),
        contentUrl: absolute(OG_IMAGE.path),
        width: OG_IMAGE.width,
        height: OG_IMAGE.height,
        caption: `${SITE_NAME} — ${TAGLINE}`,
      },
      {
        "@type": "WebSite",
        "@id": WEBSITE,
        url: SITE_URL,
        name: SITE_NAME,
        description: DESCRIPTION,
        publisher: { "@id": ORGANIZATION },
        inLanguage: "en",
        // No SearchAction: the sitelinks searchbox was deprecated in Nov 2024 and
        // this site has no search to point it at anyway.
      },
      {
        "@type": "WebPage",
        "@id": WEBPAGE,
        url: SITE_URL,
        name: `${SITE_NAME} — ${TAGLINE}`,
        description: DESCRIPTION,
        isPartOf: { "@id": WEBSITE },
        about: { "@id": APP },
        mainEntity: { "@id": APP },
        primaryImageOfPage: { "@id": IMAGE },
        // Real git dates for page.tsx, not build time. See lib/last-changed.
        datePublished: HOME_PUBLISHED.toISOString(),
        dateModified: HOME_MODIFIED.toISOString(),
        inLanguage: "en",
      },
      {
        "@type": "SoftwareApplication",
        "@id": APP,
        name: SITE_NAME,
        description: DESCRIPTION,
        applicationCategory: "GameApplication",
        applicationSubCategory: "Automation",
        operatingSystem: "Windows",
        url: SITE_URL,
        downloadUrl: `${REPO_URL}/releases`,
        codeRepository: REPO_URL,
        programmingLanguage: "Python",
        author: { "@id": ORGANIZATION },
        publisher: { "@id": ORGANIZATION },
        // Free, and Google wants the price stated rather than implied.
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
          availability: "https://schema.org/InStock",
          url: `${REPO_URL}/releases`,
        },
        // Mirrors the "What it does" list on the page. No claim here that is not
        // already visible in the DOM.
        featureList: [
          "Sells from your stash or straight out of scav cases",
          "Reads Tarkov's own suggested price and undercuts it",
          "Waits for a free offer slot instead of failing",
          "Cancels stale offers when the board stays full",
          "Stops mid-pass, so Stop means stop",
          "Live stats for passes, items listed, prices read and failures",
          "Themeable control panel",
        ],
        // No aggregateRating: there are no reviews on the page to back one up.
      },
      {
        "@type": "VideoObject",
        "@id": VIDEO,
        name: DEMO_VIDEO.name,
        description: DEMO_VIDEO.description,
        thumbnailUrl: DEMO_VIDEO.thumbnailUrl,
        uploadDate: DEMO_VIDEO.uploadDate,
        duration: DEMO_VIDEO.duration,
        contentUrl: DEMO_VIDEO.contentUrl,
        embedUrl: DEMO_VIDEO.embedUrl,
        isPartOf: { "@id": WEBPAGE },
        publisher: { "@id": ORGANIZATION },
      },
    ],
  };
}

/**
 * JSON for a <script type="application/ld+json"> body.
 *
 * Every `<` is escaped, so no string value can close the script tag early and
 * inject markup. This is the standard guard and the reason JSON-LD is rendered
 * from a Server Component rather than through next/script.
 */
export function serialize(graph: unknown): string {
  return JSON.stringify(graph).replace(/</g, "\\u003c");
}
