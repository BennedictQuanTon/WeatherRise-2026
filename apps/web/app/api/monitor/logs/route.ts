import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const now = Date.now();
  const sampleLogs = [
    { id: "1", ts: now - 18000, level: "info", service: "Parser", message: "User query received: 'Plan a 3-day trip to Da Nang next week'" },
    { id: "2", ts: now - 16500, level: "step", service: "NIM LLM", message: "Intent classified as 'trip_planning', extracted entities: { location: 'Da Nang', days: 3 }", duration: 184 },
    { id: "3", ts: now - 15000, level: "info", service: "MCP:weather", message: "Querying Open-Meteo HighRes Grid (lat: 16.0544, lon: 108.2022)", duration: 210 },
    { id: "4", ts: now - 13200, level: "info", service: "Qdrant", message: "Dense + Sparse hybrid search on 48 Da Nang POIs (NeMo Embed)", duration: 45 },
    { id: "5", ts: now - 11000, level: "step", service: "Orchestrator", message: "Detected rain cluster (45% prob) on Day 2 afternoon. Activating Weather-Constraint Optimizer.", duration: 320 },
    { id: "6", ts: now - 8500, level: "success", service: "Intelligence", message: "Optimized itinerary generated: 14 stops sequenced with 0 weather conflicts", duration: 412 },
    { id: "7", ts: now - 6000, level: "info", service: "NeMo Guardrails", message: "Output safety validation passed (Safety score: 0.994)", duration: 68 },
    { id: "8", ts: now - 3000, level: "success", service: "Pipeline", message: "Synthesized final structured response. End-to-end latency: 1.24s" }
  ];

  return NextResponse.json({ logs: sampleLogs });
}
