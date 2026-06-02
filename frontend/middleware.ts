import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/api/auth/login", "/api/auth/logout"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always allow public paths through without any modification
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = request.cookies.get("bomatic_token")?.value;

  // Unauthenticated: redirect browser requests to /login
  // Pass API requests through with 401 (they handle errors themselves)
  if (!token) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.next();
    }
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Authenticated: inject both the static API key and the JWT
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("X-API-Key", "bomatic-dev-key");
  requestHeaders.set("Authorization", `Bearer ${token}`);

  return NextResponse.next({
    request: { headers: requestHeaders },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|fonts).*)"],
};
