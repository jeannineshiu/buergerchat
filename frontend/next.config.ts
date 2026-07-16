import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for the Docker runner stage.
  output: "standalone",
  // A stray lockfile in the user's home directory otherwise confuses
  // Turbopack's workspace-root inference.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
