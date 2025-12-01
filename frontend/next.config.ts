import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Disabled in development to prevent map double-mount issues
  reactStrictMode: false,
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    SERVER_API_BASE_URL: process.env.SERVER_API_BASE_URL,
  },
};

export default nextConfig;
