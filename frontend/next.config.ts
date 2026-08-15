import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The dev overlay badge sits on top of the demo UI (bottom-left circle);
  // compile and runtime errors are still surfaced without it.
  devIndicators: false,
};

export default nextConfig;
