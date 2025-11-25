import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Disabled in development to prevent map double-mount issues
  reactStrictMode: false,
};

export default nextConfig;
