/** @type {import('next').NextConfig} */
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8088";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      // Health proxy
      { source: "/health", destination: `${API_URL}/health` },
      // Monitor SSE stream
      { source: "/api/monitor/stream", destination: `${API_URL}/api/monitor/stream` },
      { source: "/api/monitor/logs", destination: `${API_URL}/api/monitor/logs` },
      // Chat + WebSocket
      { source: "/api/:path*", destination: `${API_URL}/api/:path*` },
      { source: "/ws", destination: `${API_URL}/ws` },
    ];
  },
};

module.exports = nextConfig;
