export const dynamic = "force-dynamic";

export async function GET() {
  const encoder = new TextEncoder();

  const simulatedEvents = [
    { service: "Parser", level: "info", message: "Dispatched incoming user query to LLM classifier", duration: 85 },
    { service: "NIM LLM", level: "step", message: "DeepSeek-R1 CoT reasoning: Target location = 'Đà Nẵng', Temporal span = 72h", duration: 240 },
    { service: "MCP:weather", level: "info", message: "Fetching ERA5 atmospheric reanalysis + ECMWF 0.1° wind vectors", duration: 190 },
    { service: "Qdrant", level: "info", message: "Vector search: 12 indoor backup candidates indexed (NeMo Embed)", duration: 38 },
    { service: "Orchestrator", level: "step", message: "Weather Constraint Check: Temperature 31.5°C, Rain probability 12%", duration: 110 },
    { service: "Intelligence", level: "success", message: "Tourism Agent solved 3-day routing with 100% weather compliance", duration: 380 },
    { service: "NeMo Guardrails", level: "info", message: "Content moderation check: Safe (Domain: Tourism & Meteorology)", duration: 42 },
    { service: "Pipeline", level: "success", message: "Response streamed to client via WebSocket / REST channel", duration: 15 },
    { service: "MCP:place", level: "info", message: "Resolved POI coordinates: Son Tra (16.0825, 108.2750), Cham Museum (16.0604, 108.2227)", duration: 64 },
    { service: "Orchestrator", level: "warn", message: "Detected wind shear spike (>10 m/s) in Ba Na Hills altitude", duration: 140 },
    { service: "NIM LLM", level: "step", message: "Re-ranking afternoon stops to sheltered indoor museums", duration: 215 },
  ];

  let eventIndex = 0;

  const stream = new ReadableStream({
    start(controller) {
      // Send initial connect log
      const initEntry = {
        id: `init-${Date.now()}`,
        ts: Date.now(),
        level: "success",
        service: "Monitor",
        message: "Connected to Weatherise Multi-Agent Live Pipeline SSE Stream"
      };
      controller.enqueue(encoder.encode(`data: ${JSON.stringify(initEntry)}\n\n`));

      const interval = setInterval(() => {
        try {
          const sample = simulatedEvents[eventIndex % simulatedEvents.length];
          eventIndex++;

          const entry = {
            id: `evt-${Date.now()}-${eventIndex}`,
            ts: Date.now(),
            level: sample.level,
            service: sample.service,
            message: sample.message,
            duration: sample.duration
          };

          controller.enqueue(encoder.encode(`data: ${JSON.stringify(entry)}\n\n`));

          // Also send periodic ping
          if (eventIndex % 4 === 0) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "ping" })}\n\n`));
          }
        } catch (err) {
          clearInterval(interval);
        }
      }, 2500);

      // Clean up on cancel
      return () => clearInterval(interval);
    }
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
    },
  });
}
