/** Next.js API proxy to backend — forwards all requests to the FastAPI backend. */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  return proxyRequest(request, "GET");
}

export async function POST(request: NextRequest) {
  return proxyRequest(request, "POST");
}

async function proxyRequest(request: NextRequest, method: string): Promise<NextResponse> {
  const { searchParams } = new URL(request.url);
  const path = searchParams.get("path") || "";
  const targetUrl = `${BACKEND_URL}/api/${path}`;

  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    const fetchOptions: RequestInit = {
      method,
      headers,
    };

    if (method === "POST") {
      const body = await request.json().catch(() => ({}));
      fetchOptions.body = JSON.stringify(body);
    }

    const response = await fetch(targetUrl, fetchOptions);
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to proxy request to backend" },
      { status: 502 },
    );
  }
}
