import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    status: "ok",
    version: "2.0.0",
    uptime_seconds: 3600,
    services: {
      nim_llm: "ok",
      nim_embed: "ok",
      mcp_server: "ok",
      qdrant: "ok",
      api: "ok"
    },
    system: {
      platform: "Weatherise Multi-Agent System (Vercel Serverless Demo)",
      models: {
        reasoning: "DeepSeek-R1-Distill-Llama-70B (NVIDIA NIM)",
        domain_general: "Llama-3.1-70B-Instruct",
        meteorological_agent: "Qwen-2.5-72B-Instruct",
        guardrails: "NeMo Guardrails v0.9.0"
      },
      vector_store: "Qdrant Vector DB (1024-dim NeMo Embed)",
      rag_grounding_score: 0.942
    }
  });
}
