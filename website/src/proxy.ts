import { NextResponse, type NextRequest } from "next/server";

// Bytespider ignores robots.txt, so the disallow in robots.ts is a statement of
// intent and this is the part that actually stops it.
// ponytail: a substring match on one user agent. If more scrapers need blocking,
// this becomes a list before it becomes anything cleverer.
const BLOCKED = /Bytespider/i;

export function proxy(request: NextRequest) {
  if (BLOCKED.test(request.headers.get("user-agent") ?? "")) {
    return new NextResponse("Forbidden", { status: 403 });
  }
  return NextResponse.next();
}

export const config = {
  // Everything except Next's own assets, which are not worth the check.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
