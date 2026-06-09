"use client";
import { useState, useRef, useEffect, useCallback } from "react";

interface LogEntry {
  id: string;
  ts: number;
  level: "info" | "warn" | "error" | "success" | "step";
  service: string;
  message: string;
  duration?: number;
}

interface SvcHealth {
  name: string;
  key: string;
  status: "ok" | "degraded" | "unreachable" | "checking";
  latency?: number;
}

const SVCS: SvcHealth[] = [
  { name: "NIM LLM", key: "nim_llm", status: "checking" },
  { name: "NIM Embed", key: "nim_embed", status: "checking" },
  { name: "MCP Server", key: "mcp_server", status: "checking" },
  { name: "Qdrant", key: "qdrant", status: "checking" },
  { name: "API Backend", key: "api", status: "checking" },
];

const SVC_COLORS: Record<string, string> = {
  "NIM LLM": "#00e5ff", "NIM Embed": "#7c4dff", "MCP Server": "#00e676",
  "Qdrant": "#ff9100", "API Backend": "#ff4081",
  "Parser": "#69f0ae", "Orchestrator": "#40c4ff", "Intelligence": "#ea80fc",
  "Pipeline": "#ffeb3b", "Monitor": "#b0bec5",
  "MCP:time": "#ccff90", "MCP:location": "#80d8ff",
  "MCP:weather": "#64ffda", "MCP:place": "#ffd180",
};

function levelColor(l: string) {
  return { info: "#546e7a", warn: "#ffb300", error: "#ff5252", success: "#e8f4f8", step: "#00e5ff" }[l] ?? "#fff";
}
function durationColor(ms: number) {
  return ms > 5000 ? "#ff5252" : ms > 1000 ? "#ffb300" : "#69f0ae";
}
function statusDot(s: string) {
  const c = { ok: "#69f0ae", degraded: "#ffb300", unreachable: "#ff5252", checking: "#546e7a" }[s] ?? "#546e7a";
  return <span className="inline-block w-2 h-2 rounded-full mr-1.5 animate-pulse" style={{ background: c }} />;
}

export default function MonitorPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [svcs, setSvcs] = useState<SvcHealth[]>(SVCS);
  const [filter, setFilter] = useState("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const [connected, setConnected] = useState(false);
  const [testInput, setTestInput] = useState("Can I go to Han Market next 3 days?");
  const [testing, setTesting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  // Push log entry
  const push = useCallback((entry: LogEntry) => {
    setLogs(prev => [...prev.slice(-800), entry]);
  }, []);

  // Connect to SSE stream from API
  useEffect(() => {
    const connect = () => {
      if (esRef.current) esRef.current.close();
      // Use same host, path proxied through Next.js
      const es = new EventSource("/api/monitor/stream");
      esRef.current = es;

      es.onopen = () => setConnected(true);
      es.onerror = () => {
        setConnected(false);
        setTimeout(connect, 3000); // reconnect
      };
      es.onmessage = (e) => {
        try {
          const entry = JSON.parse(e.data);
          if (entry.type === "ping") return;
          push(entry as LogEntry);
        } catch {}
      };
    };
    connect();
    return () => esRef.current?.close();
  }, [push]);

  // Check service health via API (avoid CORS — go through Next.js proxy)
  const checkHealth = useCallback(async () => {
    try {
      const r = await fetch("/health", { signal: AbortSignal.timeout(5000) });
      const d = await r.json();
      const t0 = Date.now();
      setSvcs(prev => prev.map(svc => {
        if (svc.key === "api") return { ...svc, status: "ok", latency: Date.now() - t0 };
        const s = d.services?.[svc.key];
        return { ...svc, status: s === "ok" ? "ok" : s ? "degraded" : "unreachable", latency: undefined };
      }));
    } catch {
      setSvcs(prev => prev.map(s => ({ ...s, status: s.key === "api" ? "unreachable" : s.status })));
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const t = setInterval(checkHealth, 8000);
    return () => clearInterval(t);
  }, [checkHealth]);

  // Autoscroll
  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, autoScroll]);

  // Inline pipeline test — goes through API (/api/chat) which is proxied
  const runTest = async () => {
    if (testing) return;
    setTesting(true);
    push({ id: Date.now().toString(), ts: Date.now(), level: "info", service: "Monitor", message: `▶ Manual test: "${testInput}"` });
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: testInput }),
      });
      const d = await r.json();
      push({ id: Date.now().toString(), ts: Date.now(), level: d.status === "success" ? "success" : "error", service: "Monitor", message: `Test done: ${d.final_answer?.slice(0, 80) ?? d.error}` });
    } catch (e: any) {
      push({ id: Date.now().toString(), ts: Date.now(), level: "error", service: "Monitor", message: `Test failed: ${e.message}` });
    }
    setTesting(false);
  };

  const filtered = filter === "all" ? logs : logs.filter(l =>
    l.level === filter || l.service.toLowerCase().includes(filter)
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#060b17] text-gray-300 font-mono text-xs">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-cyan-900/20 bg-[#060b17]/90 backdrop-blur px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : "bg-red-500"}`} />
          <span className="text-cyan-400 font-bold text-sm tracking-widest uppercase">Weatherise Monitor</span>
          <span className="text-gray-700 text-[10px]">Real-time Pipeline Inspector</span>
          <span className={`text-[10px] px-2 py-0.5 rounded-full ${connected ? "bg-emerald-900/40 text-emerald-400" : "bg-red-900/40 text-red-400"}`}>
            {connected ? "SSE Connected" : "Reconnecting..."}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <a href="/" className="text-[10px] text-gray-600 hover:text-cyan-400 transition-colors">← Chat</a>
          <button onClick={() => setLogs([])} className="text-[10px] text-gray-600 hover:text-red-400 transition-colors">✕ Clear</button>
          <label className="flex items-center gap-1 cursor-pointer text-[10px] text-gray-600">
            <input type="checkbox" checked={autoScroll} onChange={e => setAutoScroll(e.target.checked)} className="w-3 h-3" />
            Auto-scroll
          </label>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden" style={{ height: "calc(100vh - 48px)" }}>

        {/* Left: services + test */}
        <aside className="w-56 shrink-0 border-r border-cyan-900/15 flex flex-col bg-[#08101f]">
          {/* Health */}
          <div className="px-3 py-2.5 border-b border-cyan-900/15 text-[10px] text-gray-600 uppercase tracking-widest">Service Health</div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {svcs.map(s => (
              <div key={s.key} className="rounded-lg px-3 py-2 bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    {statusDot(s.status)}
                    <span className="text-[11px] font-semibold" style={{ color: SVC_COLORS[s.name] ?? "#8ba3b0" }}>{s.name}</span>
                  </div>
                  {s.latency !== undefined && (
                    <span className="text-[10px]" style={{ color: durationColor(s.latency) }}>{s.latency}ms</span>
                  )}
                </div>
                <div className="text-[10px] text-gray-700 mt-0.5 capitalize pl-3.5">{s.status}</div>
              </div>
            ))}
          </div>

          {/* Pipeline tester */}
          <div className="border-t border-cyan-900/15 p-3">
            <div className="text-[10px] text-gray-600 uppercase tracking-widest mb-2">Quick Test</div>
            <textarea
              value={testInput}
              onChange={e => setTestInput(e.target.value)}
              rows={3}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg p-2 text-[11px] text-gray-300 resize-none outline-none focus:border-cyan-900/60 mb-2 leading-relaxed"
            />
            <button onClick={runTest} disabled={testing}
              className="w-full py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all"
              style={{ background: testing ? "rgba(0,180,255,0.08)" : "rgba(0,100,200,0.4)", color: testing ? "#546e7a" : "#00e5ff", border: "1px solid rgba(0,180,255,0.2)", cursor: testing ? "not-allowed" : "pointer" }}>
              {testing ? "⏳ Running..." : "▶ Run Test"}
            </button>
            <p className="text-[10px] text-gray-700 mt-1.5 text-center">Logs appear in stream →</p>
          </div>
        </aside>

        {/* Center: log stream */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Filter bar */}
          <div className="border-b border-cyan-900/15 px-4 py-2 flex items-center gap-1.5 bg-[#07101e]/60 shrink-0">
            <span className="text-[10px] text-gray-700 mr-1">Filter:</span>
            {["all","step","success","error","warn","parser","intelligence","mcp","orchestrator"].map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wider transition-all ${filter === f ? "bg-cyan-900/50 text-cyan-300 border border-cyan-800/50" : "text-gray-700 hover:text-gray-400"}`}>
                {f}
              </button>
            ))}
            <span className="ml-auto text-[10px] text-gray-700">{filtered.length} entries</span>
          </div>

          {/* Logs */}
          <div className="flex-1 overflow-y-auto px-4 py-1">
            {filtered.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-gray-700 gap-3">
                <span className="text-4xl">📡</span>
                <p className="text-[11px]">{connected ? "Waiting for pipeline events..." : "Connecting to API stream..."}</p>
                <p className="text-[10px] text-gray-800">Send a message in the chat or run a Quick Test</p>
              </div>
            )}
            {filtered.map(log => (
              <div key={log.id} className="flex items-start gap-2 py-0.5 border-b border-white/[0.02] hover:bg-white/[0.015] group">
                <span className="text-[10px] text-gray-700 shrink-0 w-20 pt-px">{new Date(log.ts).toISOString().slice(11, 23)}</span>
                <span className="text-[10px] font-bold shrink-0 w-24 truncate pt-px" style={{ color: SVC_COLORS[log.service] ?? "#546e7a" }}>
                  [{log.service}]
                </span>
                <span className="text-[10px] shrink-0 w-12 pt-px" style={{ color: levelColor(log.level) }}>
                  {log.level.toUpperCase()}
                </span>
                <span className="flex-1 text-[11px] leading-relaxed break-all" style={{ color: log.level === "error" ? "#ef9a9a" : log.level === "success" ? "#e0e0e0" : "#78909c" }}>
                  {log.message}
                </span>
                {log.duration !== undefined && (
                  <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded ml-1 font-mono"
                    style={{ background: `${durationColor(log.duration)}15`, color: durationColor(log.duration) }}>
                    {log.duration}ms
                  </span>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </main>

        {/* Right: latency chart */}
        <aside className="w-48 shrink-0 border-l border-cyan-900/15 flex flex-col bg-[#08101f]">
          <div className="px-3 py-2.5 border-b border-cyan-900/15 text-[10px] text-gray-600 uppercase tracking-widest">Step Latency</div>
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {(() => {
              const withDur = logs.filter(l => l.level === "success" && l.duration !== undefined).slice(-15);
              if (!withDur.length) return <p className="text-[10px] text-gray-800 text-center mt-6">No data yet</p>;
              const max = Math.max(...withDur.map(l => l.duration ?? 0), 1);
              return withDur.map(l => (
                <div key={l.id}>
                  <div className="flex justify-between mb-1">
                    <span className="text-[10px] truncate" style={{ color: SVC_COLORS[l.service] ?? "#546e7a" }}>{l.service}</span>
                    <span className="text-[10px] font-mono" style={{ color: durationColor(l.duration ?? 0) }}>{l.duration}ms</span>
                  </div>
                  <div className="h-1 rounded-full bg-white/5">
                    <div className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(((l.duration ?? 0) / max) * 100, 100)}%`, background: durationColor(l.duration ?? 0) }} />
                  </div>
                </div>
              ));
            })()}
          </div>
          {/* Stats */}
          <div className="border-t border-cyan-900/15 p-3 space-y-2">
            <div className="text-[10px] text-gray-600 uppercase tracking-widest mb-1">Stats</div>
            {[
              { label: "Total events", value: logs.length },
              { label: "Errors", value: logs.filter(l => l.level === "error").length },
              { label: "Pipelines", value: logs.filter(l => l.service === "Pipeline" && l.level === "success").length },
            ].map(s => (
              <div key={s.label} className="flex justify-between">
                <span className="text-[10px] text-gray-700">{s.label}</span>
                <span className={`text-[10px] font-bold ${s.label === "Errors" && s.value > 0 ? "text-red-400" : "text-gray-300"}`}>{s.value}</span>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
