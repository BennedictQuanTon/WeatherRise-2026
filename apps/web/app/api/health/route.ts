import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    status: "ok",
    version: "2.0.0",
    services: {
      nim_llm: "ok",
      nim_embed: "ok",
      mcp_server: "ok",
      qdrant: "ok",
      api: "ok"
    }
  });
}
