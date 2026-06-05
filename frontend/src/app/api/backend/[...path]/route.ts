/**
 * Authenticated BFF proxy to FastAPI — keeps API_SECRET_KEY server-side only.
 * Browser calls /api/backend/* ; this route forwards to the Python backend.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

function backendUrl(pathSegments: string[], search: string): string {
  const path = pathSegments.join("/");
  const base = `${BACKEND_URL}/api/${path}`;
  return search ? `${base}?${search}` : base;
}

function authHeaders(): Record<string, string> {
  const key =
    process.env.API_SECRET_KEY ||
    process.env.SECRET_KEY ||
    process.env.NEXT_PUBLIC_API_KEY;
  const headers: Record<string, string> = {};
  if (key) {
    headers.Authorization = `Bearer ${key}`;
  }
  return headers;
}

async function forward(
  request: NextRequest,
  pathSegments: string[],
  method: string,
): Promise<Response> {
  const search = request.nextUrl.searchParams.toString();
  const target = backendUrl(pathSegments, search);
  const isStream = pathSegments.at(-1) === "stream";
  const isDownload = pathSegments.includes("download");

  const headers: Record<string, string> = {
    ...authHeaders(),
  };

  if (!isDownload && !isStream) {
    headers["Content-Type"] = "application/json";
  }
  if (isStream) {
    headers.Accept = "text/event-stream";
  }

  const init: RequestInit = {
    method,
    headers,
    signal: request.signal,
  };

  if (method === "POST" || method === "PUT" || method === "PATCH") {
    const body = await request.text();
    if (body) {
      init.body = body;
    }
  }

  const response = await fetch(target, init);

  if (isStream) {
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  if (isDownload) {
    const blob = await response.blob();
    return new Response(blob, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/zip",
        "Content-Disposition":
          response.headers.get("Content-Disposition") ||
          'attachment; filename="generated-app.zip"',
      },
    });
  }

  const text = await response.text();
  let data: unknown = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  return NextResponse.json(data, { status: response.status });
}

type RouteContext = { params: { path: string[] } };

export async function GET(request: NextRequest, context: RouteContext) {
  return forward(request, context.params.path, "GET");
}

export async function POST(request: NextRequest, context: RouteContext) {
  return forward(request, context.params.path, "POST");
}
