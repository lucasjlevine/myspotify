import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,
  turbopack: {
    root: path.join(__dirname),
  },
  async rewrites() {
    const upstream = process.env.API_UPSTREAM || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${upstream}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
