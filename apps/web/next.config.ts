import type { NextConfig } from "next";

const PROD_API = "https://asra-production.up.railway.app";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ??
      (process.env.VERCEL ? PROD_API : "http://127.0.0.1:8000"),
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME ?? "Findings",
  },
};

export default nextConfig;
