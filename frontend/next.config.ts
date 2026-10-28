import type { NextConfig } from "next";

const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  reactStrictMode: true,
  // hide the Next.js dev-tools "N" badge; it overlaps the bottom navigation while testing
  devIndicators: false,
  // API keys live only on the backend; the browser talks to it through this proxy.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
      { source: "/admin/:path*", destination: `${BACKEND}/admin/:path*` },
      { source: "/admin", destination: `${BACKEND}/admin` },
    ];
  },
  async headers() {
    return [{ source: "/sw.js", headers: [{ key: "Cache-Control", value: "no-cache" }] }];
  },
  allowedDevOrigins: ["*.local", "192.168.*.*", "10.*.*.*", "*.trycloudflare.com"],
};

export default config;
