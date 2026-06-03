import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("X-API-Key", "bomatic-dev-key");

  // Forward JWT if present in cookie
  const token = request.cookies.get("bomatic_token")?.value;
  if (token) {
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  return NextResponse.next({
    request: { headers: requestHeaders },
  });
}

export const config = {
  matcher: ["/api/:path*"],
};
