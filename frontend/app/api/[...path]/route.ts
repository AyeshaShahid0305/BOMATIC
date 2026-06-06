import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = "http://localhost:8000";
const CONFIG_ERROR =
  "Server configuration error: BOMATIC_API_KEY is missing. Set BOMATIC_API_KEY in the frontend environment before starting the proxy.";

function buildBackendUrl(request: NextRequest, pathSegments: string[]) {
  const backendUrl = new URL(`${BACKEND_BASE_URL}/api/${pathSegments.map(encodeURIComponent).join("/")}`);
  backendUrl.search = request.nextUrl.search;
  return backendUrl;
}

async function proxyToBackend(
  request: NextRequest,
  context: { params: { path: string[] } },
) {
  const apiKey = process.env.BOMATIC_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { detail: CONFIG_ERROR },
      { status: 500 },
    );
  }

  const backendUrl = buildBackendUrl(request, context.params.path);
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  headers.delete("cookie");
  headers.delete("x-api-key");

  const token = request.cookies.get("bomatic_token")?.value;
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else {
    headers.delete("Authorization");
  }

  headers.set("X-API-Key", apiKey);

  const hasBody = !["GET", "HEAD"].includes(request.method);
  const backendResponse = await fetch(backendUrl, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    redirect: "manual",
  });

  const responseHeaders = new Headers(backendResponse.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("transfer-encoding");

  return new NextResponse(backendResponse.body, {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers: responseHeaders,
  });
}

export function GET(request: NextRequest, context: { params: { path: string[] } }) {
  return proxyToBackend(request, context);
}

export function POST(request: NextRequest, context: { params: { path: string[] } }) {
  return proxyToBackend(request, context);
}

export function PUT(request: NextRequest, context: { params: { path: string[] } }) {
  return proxyToBackend(request, context);
}

export function PATCH(request: NextRequest, context: { params: { path: string[] } }) {
  return proxyToBackend(request, context);
}

export function DELETE(request: NextRequest, context: { params: { path: string[] } }) {
  return proxyToBackend(request, context);
}

export function OPTIONS(request: NextRequest, context: { params: { path: string[] } }) {
  return proxyToBackend(request, context);
}

export function HEAD(request: NextRequest, context: { params: { path: string[] } }) {
  return proxyToBackend(request, context);
}
