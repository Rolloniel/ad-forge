import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const apiKey = request.cookies.get("adforge_api_key");

  if (!apiKey?.value) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Protect all dashboard routes, but not /login, /health, /api, or static files
    "/((?!login|_next|favicon\\.ico|api).*)",
  ],
};
