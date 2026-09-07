import { NextRequest, NextResponse } from "next/server";
import { routeMockQuery } from "../mockData";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const message = body.message || "";

    const backendUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL;

    // If backend URL is provided and not pointing to localhost, try forwarding
    if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 4000);

        const upstreamRes = await fetch(`${backendUrl}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        if (upstreamRes.ok) {
          const upstreamData = await upstreamRes.json();
          return NextResponse.json(upstreamData);
        }
      } catch (upstreamErr) {
        console.warn("Backend proxy failed, falling back to smart demo mock engine:", upstreamErr);
      }
    }

    // Default standalone demo mode on Vercel
    const mockResponse = routeMockQuery(message);
    return NextResponse.json(mockResponse);
  } catch (error: any) {
    console.error("API Chat route error:", error);
    const fallback = routeMockQuery("Plan a 3-day trip to Da Nang next week");
    return NextResponse.json(fallback);
  }
}
