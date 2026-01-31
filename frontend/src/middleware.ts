import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const LOGIN_COOKIE = "aura_logged_in";
const LOGIN_PATH = "/login";

/** Routes that require the user to be logged in (payment / wallet / profile). */
const protectedPaths = ["/wallet", "/checkout", "/profile"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = protectedPaths.some((p) => pathname === p || pathname.startsWith(p + "/"));
  if (!isProtected) return NextResponse.next();

  const loggedIn = request.cookies.get(LOGIN_COOKIE)?.value === "1";
  if (loggedIn) return NextResponse.next();

  const loginUrl = new URL(LOGIN_PATH, request.url);
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/wallet", "/wallet/:path*", "/checkout", "/checkout/:path*", "/profile", "/profile/:path*"],
};
