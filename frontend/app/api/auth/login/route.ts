import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://localhost:8000";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const backendRes = await fetch(`${BACKEND}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await backendRes.json();

  if (!backendRes.ok) {
    return NextResponse.json(data, { status: backendRes.status });
  }

  const token: string = data.access_token;

  const response = NextResponse.json({ ok: true }, { status: 200 });
  response.cookies.set("bomatic_token", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 8, // 8 hours - matches jwt_expire_minutes
  });

  return response;
}
