import { ImageResponse } from "next/og";

import { SITE_NAME, TAGLINE } from "@/lib/site";

// The link preview card. Generated rather than a committed PNG so it cannot drift
// from the site's own wording, and static (no cookies/headers) so it is built once.
export const alt = `${SITE_NAME} — ${TAGLINE}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "0 90px",
          // Matches globals.css: base behind, ink on top, one hairline rule.
          background: "#0d0e0d",
          color: "#d8d7d2",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            fontSize: 26,
            letterSpacing: 10,
            textTransform: "uppercase",
            color: "#5c5f5c",
          }}
        >
          Free · Escape From Tarkov · Windows
        </div>
        <div style={{ fontSize: 104, marginTop: 34, lineHeight: 1.05 }}>
          It sells your loot
        </div>
        <div style={{ fontSize: 104, lineHeight: 1.05, color: "#8f928f" }}>
          while you do something else.
        </div>
        <div
          style={{
            display: "flex",
            height: 1,
            background: "#3b3d3b",
            margin: "48px 0 30px",
          }}
        />
        <div
          style={{
            fontSize: 34,
            letterSpacing: 14,
            textTransform: "uppercase",
            color: "#d8d7d2",
          }}
        >
          {SITE_NAME}
        </div>
      </div>
    ),
    size,
  );
}
