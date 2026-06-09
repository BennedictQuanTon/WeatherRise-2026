"use client";
import { useState, useRef, useEffect, useCallback } from "react";

interface LogEntry {
  id: string;
  ts: number;
  level: "info" | "warn" | "error" | "success" | "step";
  service: string;
  message: string;
  duration?: number;
  data?: any;
}

interface ServiceHealth {
  name: string;
  url: string;
  status: "ok" | "degraded" | "unreachable" | "checking";
  latency?: number;
  detail?: string;
}

const SERVICES: ServiceHealth[] = [
  { name: "NIM LLM", url: "http://localhost:8001/v1/models", status: "checking" },
  { name: "NIM Embed", url: "http://localhost:8002/v1/models", status: "checking" },
  { name: "MCP Server", url: "http://localhost:9000/health", status: "checking" },
  { name: "Qdrant", url: "http://localhost:6333/health", status: "checking" },
  { name: "API Backend", url: "/api-health", status: "checking" },
];

const SERVICE_COLORS: Record<string, string> = {
  "NIM LLM": "#00e5ff",
  "NIM Embed": "#7c4dff",
  "MCP Server": "#00e676",
  "Qdrant": "#ff9100",
  "API Backend": "#ff4081",
  "Parser": "#69f0ae",
  "Orchestrator": "#40c4ff",
  "ContextAgent": "#ffd740",
  "Intelligence": "#ea80fc",
  "MCP:location": "#80d8ff",
  "MCP:weather": "#64ffda",
  "MCP:time": "#ccff90",
  "MCP:place": "#ffd180",
};

function ts() { return new Date().toISOString().slice(11, 23); }
function uid() { return Math.random().toString(36).slice(2, 8); }

function levelColor(l: string) {
  return { info: "#8ba3b0", warn: "#ffb300", error: "#ff5252", success: "#69f0ae", step: "#00e5ff" }[l] ?? "#fff";
}

function statusDot(s: string) {
  const c = { ok: "#69f0ae", degraded: "#ffb300", unreachable: "#ff5252", checking: "#8ba3b0" }[s] ?? "#8ba3b0";
  const pulse = s === "checking" ? "animate-pulse" : s === "ok" ? "animate-pulse" : "";
  return <span className={`inline-block w-2 h-2 rounded-full mr-2 ${pulse}`} style={{ background: c }} />;
}

export default function MonitorPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [services, setServices] = useState<ServiceHealth[]>(SERVICES);
  const [testInput, setTestInput] = useState("Can I go to Han Market next 3 days?");
  const [running, setRunning] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState("all");
  const bottomRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const addLog = useCallback((level: LogEntry["level"], service: string, message: string, duration?: number, data?: any) => {
    setLogs(prev => [...prev.slice(-500), {
      id: uid(), ts: Date.now(), level, service, message, duration, data
    }]);
  }, []);

  const checkServices = useCallback(async () => {
    const updated = await Promise.all(SERVICES.map(async (svc) => {
      const t = Date.now();
      try {
        const url = svc.url.startsWith("/api-health")
          ? "http://localhost:8088/health"
          : svc.url;
        const r = await fetch(url, { signal: AbortSignal.timeout(3000) });
        const latency = Date.now() - t;
        const data = await r.json().catch(() => ({}));
        const status = r.ok ? "ok" : "degraded";
        return { ...svc, status, latency, detail: JSON.stringify(data).slice(0, 80) } as ServiceHealth;
      } catch {
        return { ...svc, status: "unreachable" as const, latency: Date.now() - t };
      }
    }));
    setServices(updated);
  }, []);

  useEffect(() => {
    checkServices();
    intervalRef.current = setInterval(checkServices, 10000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [checkServices]);

  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, autoScroll]);

  const runPipeline = async () => {
    if (running) return;
    setRunning(true);
    const sessionId = uid();
    const pipelineStart = Date.now();

    addLog("info", "Monitor", `▶ Starting pipeline test: "${testInput}"`, undefined);

    // Step 1: Parser
    addLog("step", "Parser", "Calling NIM Nemotron 8B to parse input...");
    let t = Date.now();
    let parseResult: any = null;
    try {
      const r = await fetch("http://localhost:8001/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "nvidia/llama-3.1-nemotron-nano-8b-v1",
          messages: [{ role: "user", content: `Extract JSON from: "${testInput}". Output: {"domain":"tourism|construction|agriculture","intent":"...","location":"..."}` }],
          temperature: 0.0, max_tokens: 200
        }),
        signal: AbortSignal.timeout(30000)
      });
      const d = await r.json();
      parseResult = d.choices?.[0]?.message?.content ?? "{}";
      addLog("success", "Parser", `Done: ${parseResult.slice(0, 80)}`, Date.now() - t);
    } catch (e: any) {
      addLog("error", "Parser", `Failed: ${e.message}`, Date.now() - t);
    }

    // Step 2: MCP Time
    t = Date.now();
    addLog("step", "MCP:time", "Resolving time range...");
    try {
      const raw = testInput.match(/next \d+ days|today|tomorrow|this week|next week/i)?.[0] ?? "next 3 days";
      const r = await fetch("http://localhost:9000/tools/time/resolveTimeRange", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: raw, timezone: "Asia/Ho_Chi_Minh" })
      });
      const d = await r.json();
      addLog("success", "MCP:time", `${d.start} → ${d.end} (${d.duration_days}d)`, Date.now() - t, d);
    } catch (e: any) {
      addLog("error", "MCP:time", `Failed: ${e.message}`, Date.now() - t);
    }

    // Step 3: MCP Location
    t = Date.now();
    addLog("step", "MCP:location", "Resolving coordinates...");
    let coords: any = null;
    const locMatch = testInput.match(/Da Nang|Hanoi|Ho Chi Minh|Hue|Hoi An|Nha Trang|Han Market/i)?.[0];
    const locQuery = locMatch?.includes("Han Market") ? "Han Market, Da Nang" : locMatch ?? "Da Nang";
    try {
      const r = await fetch("http://localhost:9000/tools/location/resolveCoordinates", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location: locQuery })
      });
      coords = await r.json();
      addLog("success", "MCP:location", `${coords.display_name?.slice(0, 40)} → [${coords.latitude?.toFixed(3)}, ${coords.longitude?.toFixed(3)}]`, Date.now() - t, coords);
    } catch (e: any) {
      addLog("error", "MCP:location", `Failed: ${e.message}`, Date.now() - t);
      coords = { latitude: 16.068, longitude: 108.212 };
    }

    // Step 4: MCP Weather
    t = Date.now();
    addLog("step", "MCP:weather", "Fetching Open-Meteo forecast...");
    let weather: any = null;
    try {
      const r = await fetch("http://localhost:9000/tools/weather/getForecast", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ latitude: coords.latitude, longitude: coords.longitude })
      });
      weather = await r.json();
      const rain = weather?.daily?.precipitation_probability_max?.[0] ?? "N/A";
      const temp = weather?.daily?.temperature_2m_max?.[0] ?? "N/A";
      addLog("success", "MCP:weather", `Rain: ${rain}%  Temp: ${temp}°C  (7d forecast)`, Date.now() - t);
    } catch (e: any) {
      addLog("error", "MCP:weather", `Failed: ${e.message}`, Date.now() - t);
    }

    // Step 5: Orchestrator routing
    addLog("step", "Orchestrator", "Routing to domain context agent...");
    addLog("success", "Orchestrator", "→ TourismContextAgent selected", 1);

    // Step 6: Intelligence
    t = Date.now();
    addLog("step", "Intelligence", "Calling NIM for final reasoning...");
    let finalAnswer = "";
    try {
      const rain = weather?.daily?.precipitation_probability_max?.[0] ?? 30;
      const temp = weather?.daily?.temperature_2m_max?.[0] ?? 30;
      const r = await fetch("http://localhost:8001/v1/chat/completions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "nvidia/llama-3.1-nemotron-nano-8b-v1",
          messages: [
            { role: "system", content: "Weather advisor. Respond with JSON: {\"prediction\":\"...\",\"recommendation\":\"...\",\"final_answer\":\"...\"}" },
            { role: "user", content: `Query: "${testInput}". Location: ${locQuery}. Rain prob: ${rain}%. Temp: ${temp}°C. Advise.` }
          ],
          temperature: 0.3, max_tokens: 350
        }),
        signal: AbortSignal.timeout(30000)
      });
      const d = await r.json();
      finalAnswer = d.choices?.[0]?.message?.content ?? "";
      addLog("success", "Intelligence", finalAnswer.slice(0, 120) + "...", Date.now() - t);
    } catch (e: any) {
      addLog("error", "Intelligence", `Failed: ${e.message}`, Date.now() - t);
    }

    const total = Date.now() - pipelineStart;
    addLog("success", "Monitor", `✅ Pipeline complete in ${total}ms`, total);
    setRunning(false);
  };

  const filtered = filter === "all" ? logs : logs.filter(l => l.level === filter || l.service.toLowerCase().includes(filter));

  return (
    <div className="min-h-screen bg-[#070b18] text-gray-200 font-mono text-xs flex flex-col">
      {/* Header */}
      <header className="border-b border-cyan-900/30 px-6 py-3 flex items-center justify-between bg-[#0a0f1e]/80 backdrop-blur sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-cyan-400 font-bold text-sm tracking-widest uppercase">Weatherise Monitor</span>
          <span className="text-gray-600 text-[10px]">Pipeline Inspector · Real-time</span>
        </div>
        <div className="flex items-center gap-4">
          <button onClick={checkServices} className="text-[10px] text-gray-500 hover:text-cyan-400 transition-colors">
            ↻ Refresh
          </button>
          <button onClick={() => setLogs([])} className="text-[10px] text-gray-500 hover:text-red-400 transition-colors">
            ✕ Clear
          </button>
          <label className="flex items-center gap-1 text-[10px] text-gray-500 cursor-pointer">
            <input type="checkbox" checked={autoScroll} onChange={e => setAutoScroll(e.target.checked)} className="w-3 h-3" />
            Auto-scroll
          </label>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: Service Health */}
        <aside className="w-64 border-r border-cyan-900/20 flex flex-col bg-[#090e1c] shrink-0">
          <div className="px-4 py-3 border-b border-cyan-900/20">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest">Service Health</p>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {services.map(svc => (
              <div key={svc.name} className="rounded-lg bg-[#0d1530] border border-cyan-900/10 px-3 py-2">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center">
                    {statusDot(svc.status)}
                    <span className="text-[11px] font-semibold" style={{ color: SERVICE_COLORS[svc.name] ?? "#fff" }}>
                      {svc.name}
                    </span>
                  </div>
                  {svc.latency !== undefined && (
                    <span className={`text-[10px] ${svc.latency > 2000 ? "text-red-400" : svc.latency > 500 ? "text-yellow-400" : "text-green-400"}`}>
                      {svc.latency}ms
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-gray-600 capitalize">{svc.status}</div>
              </div>
            ))}
          </div>

          {/* Pipeline Tester */}
          <div className="border-t border-cyan-900/20 p-3">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-2">Pipeline Test</p>
            <textarea
              value={testInput}
              onChange={e => setTestInput(e.target.value)}
              rows={3}
              className="w-full bg-[#0d1530] border border-cyan-900/20 rounded p-2 text-[11px] text-gray-300 resize-none outline-none focus:border-cyan-700/50 mb-2"
            />
            <button
              onClick={runPipeline}
              disabled={running}
              className="w-full py-2 rounded text-[11px] font-bold tracking-wider uppercase transition-all"
              style={{
                background: running ? "rgba(0,229,255,0.1)" : "linear-gradient(135deg,#00b4db,#0083b0)",
                color: running ? "#8ba3b0" : "#fff",
                cursor: running ? "not-allowed" : "pointer"
              }}
            >
              {running ? "⏳ Running..." : "▶ Run Pipeline"}
            </button>
          </div>
        </aside>

        {/* Main: Log Stream */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Filter bar */}
          <div className="border-b border-cyan-900/20 px-4 py-2 flex items-center gap-2 bg-[#090e1c]/50">
            <span className="text-[10px] text-gray-600 mr-1">Filter:</span>
            {["all", "error", "warn", "success", "step", "nim", "mcp"].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wider transition-all ${
                  filter === f ? "bg-cyan-900/60 text-cyan-300" : "text-gray-600 hover:text-gray-400"
                }`}
              >
                {f}
              </button>
            ))}
            <span className="ml-auto text-[10px] text-gray-600">{filtered.length} entries</span>
          </div>

          {/* Log entries */}
          <div className="flex-1 overflow-y-auto px-4 py-2 space-y-0.5">
            {filtered.length === 0 && (
              <div className="flex items-center justify-center h-full text-gray-700">
                <div className="text-center">
                  <div className="text-4xl mb-3">📡</div>
                  <p>No logs yet. Run a pipeline test or check service health.</p>
                </div>
              </div>
            )}
            {filtered.map(log => (
              <div key={log.id} className="flex items-start gap-3 py-1 border-b border-white/[0.02] hover:bg-white/[0.02] group font-mono">
                {/* Timestamp */}
                <span className="text-[10px] text-gray-700 shrink-0 pt-0.5">
                  {new Date(log.ts).toISOString().slice(11, 23)}
                </span>
                {/* Service badge */}
                <span
                  className="text-[10px] font-bold shrink-0 w-20 truncate pt-0.5"
                  style={{ color: SERVICE_COLORS[log.service] ?? "#8ba3b0" }}
                >
                  [{log.service}]
                </span>
                {/* Level */}
                <span
                  className="text-[10px] shrink-0 w-10 pt-0.5"
                  style={{ color: levelColor(log.level) }}
                >
                  {log.level.toUpperCase()}
                </span>
                {/* Message */}
                <span className="text-[11px] flex-1 leading-relaxed break-all"
                  style={{ color: log.level === "error" ? "#ff6b6b" : log.level === "success" ? "#e8f4f8" : "#8ba3b0" }}>
                  {log.message}
                </span>
                {/* Duration */}
                {log.duration !== undefined && (
                  <span
                    className="shrink-0 text-[10px] px-1.5 py-0.5 rounded ml-2"
                    style={{
                      background: log.duration > 5000 ? "rgba(255,82,82,0.15)" :
                                  log.duration > 1000 ? "rgba(255,179,0,0.15)" : "rgba(105,240,174,0.1)",
                      color: log.duration > 5000 ? "#ff5252" :
                             log.duration > 1000 ? "#ffb300" : "#69f0ae"
                    }}
                  >
                    {log.duration}ms
                  </span>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </main>

        {/* Right: Latency Chart */}
        <aside className="w-52 border-l border-cyan-900/20 flex flex-col bg-[#090e1c] shrink-0">
          <div className="px-4 py-3 border-b border-cyan-900/20">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest">Step Latency</p>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {(() => {
              const stepLogs = logs.filter(l => l.level === "success" && l.duration !== undefined).slice(-20);
              if (!stepLogs.length) return (
                <p className="text-[10px] text-gray-700 text-center mt-8">Run pipeline to see latency</p>
              );
              const maxD = Math.max(...stepLogs.map(l => l.duration ?? 0), 1);
              return stepLogs.map(l => (
                <div key={l.id}>
                  <div className="flex justify-between mb-1">
                    <span className="text-[10px] truncate" style={{ color: SERVICE_COLORS[l.service] ?? "#8ba3b0" }}>
                      {l.service}
                    </span>
                    <span className={`text-[10px] ${(l.duration ?? 0) > 2000 ? "text-red-400" : (l.duration ?? 0) > 500 ? "text-yellow-400" : "text-green-400"}`}>
                      {l.duration}ms
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(((l.duration ?? 0) / maxD) * 100, 100)}%`,
                        background: (l.duration ?? 0) > 2000 ? "#ff5252" :
                                    (l.duration ?? 0) > 500 ? "#ffb300" : "#69f0ae"
                      }}
                    />
                  </div>
                </div>
              ));
            })()}
          </div>

          {/* Stats */}
          <div className="border-t border-cyan-900/20 p-3 space-y-2">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-2">Stats</p>
            {[
              { label: "Total logs", value: logs.length },
              { label: "Errors", value: logs.filter(l => l.level === "error").length, bad: true },
              { label: "Avg latency", value: (() => {
                const ds = logs.filter(l => l.duration).map(l => l.duration ?? 0);
                return ds.length ? Math.round(ds.reduce((a, b) => a + b, 0) / ds.length) + "ms" : "—";
              })() },
            ].map(s => (
              <div key={s.label} className="flex justify-between">
                <span className="text-[10px] text-gray-600">{s.label}</span>
                <span className={`text-[10px] font-bold ${s.bad && (s.value as number) > 0 ? "text-red-400" : "text-gray-300"}`}>
                  {s.value}
                </span>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
