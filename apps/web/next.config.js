/** @type {import('next').NextConfig} */
const externalApiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL;
const hasExternalApi =
  Boolean(externalApiUrl) &&
  !externalApiUrl.includes("localhost") &&
  !externalApiUrl.includes("127.0.0.1");

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (!hasExternalApi) {
      // In Vercel standalone demo mode, Next.js App Router API route handlers handle requests directly
      return [];
    }
    return [
      // Health proxy
      { source: "/health", destination: `${externalApiUrl}/health` },
      // Monitor SSE stream
      { source: "/api/monitor/stream", destination: `${externalApiUrl}/api/monitor/stream` },
      { source: "/api/monitor/logs", destination: `${externalApiUrl}/api/monitor/logs` },
      // Chat + WebSocket
      { source: "/api/:path*", destination: `${externalApiUrl}/api/:path*` },
      { source: "/ws", destination: `${externalApiUrl}/ws` },
    ];
  },
};

module.exports = nextConfig;
