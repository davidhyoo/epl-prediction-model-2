import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    // A plain Node environment keeps the suite fast and avoids jsdom's
    // ESM/CJS interop issues in this toolchain. The one component test renders
    // to static markup with react-dom/server, so no DOM is required.
    environment: "node",
    globals: true,
    include: ["tests/**/*.test.{ts,tsx}", "src/**/*.test.{ts,tsx}"],
  },
  resolve: {
    alias: {
      "@": path.resolve(process.cwd(), "./src"),
    },
  },
});
