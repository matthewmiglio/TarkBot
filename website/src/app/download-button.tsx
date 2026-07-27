"use client";

import { trackDownload } from "@/lib/analytics";

export const RELEASES_URL = "https://github.com/matthewmiglio/TarkBot/releases";
export const DISCORD_URL = "https://discord.gg/Vx4tdR3N8A";

export function DownloadButton({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <a
      href={RELEASES_URL}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => trackDownload()}
      className={className}
    >
      {children}
    </a>
  );
}
