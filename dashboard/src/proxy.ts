import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Basic auth over the whole dashboard. This is business data on a public URL,
// so it fails closed: with no credentials configured, nothing gets in.
// (`proxy.ts` is Next 16's rename of `middleware.ts`.)

const USER = process.env.DASHBOARD_USER;
const PASSWORD = process.env.DASHBOARD_PASSWORD;

function challenge(body: string) {
  return new NextResponse(body, {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Tarkbot Dashboard"' },
  });
}

export function proxy(request: NextRequest) {
  if (!USER || !PASSWORD) {
    return new NextResponse(
      "Dashboard auth is not configured. Set DASHBOARD_USER and DASHBOARD_PASSWORD.",
      { status: 503 },
    );
  }

  const header = request.headers.get("authorization");
  if (!header?.startsWith("Basic ")) return challenge("Authentication required");

  let decoded: string;
  try {
    decoded = atob(header.slice("Basic ".length));
  } catch {
    return challenge("Bad credentials");
  }

  // Split on the first colon only: passwords may contain colons, usernames may not.
  const sep = decoded.indexOf(":");
  const user = decoded.slice(0, sep);
  const password = decoded.slice(sep + 1);

  if (sep === -1 || user !== USER || password !== PASSWORD) {
    return challenge("Bad credentials");
  }
  return NextResponse.next();
}

export const config = {
  // Everything except Next's own assets and the favicon, which would otherwise
  // each throw their own auth prompt.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
