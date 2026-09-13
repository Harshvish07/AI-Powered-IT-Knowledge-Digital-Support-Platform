import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits a minimal, self-contained server bundle (.next/standalone) with
  // only the production dependencies actually used, traced automatically —
  // this is what lets the production Docker image skip `npm install`
  // entirely and copy a small output instead of the full node_modules tree.
  // No effect on `next dev`.
  output: "standalone",
};

export default nextConfig;
