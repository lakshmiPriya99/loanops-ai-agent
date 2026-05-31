import { NextRequest } from "next/server";

const apiBaseUrl =
  process.env.INTERNAL_API_URL ||
  (process.env.INTERNAL_API_HOSTPORT ? `http://${process.env.INTERNAL_API_HOSTPORT}` : "http://backend:5001");

function targetUrl(path: string[], search: string) {
  const cleanBase = apiBaseUrl.replace(/\/$/, "");
  const cleanPath = path.map(encodeURIComponent).join("/");
  return `${cleanBase}/api/${cleanPath}${search}`;
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const url = targetUrl(path, request.nextUrl.search);
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");

  const hasBody = !["GET", "HEAD"].includes(request.method);
  const response = await fetch(url, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    cache: "no-store"
  });

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
