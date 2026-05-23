import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server proxies /api to the backend so the SPA avoids CORS entirely.
// Override the target with VITE_API_PROXY if the backend runs elsewhere.
export default defineConfig(({ mode }) => {
  const target = process.env.VITE_API_PROXY ?? "http://localhost:8000";
  return {
    plugins: [react()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": { target, changeOrigin: true },
      },
    },
    build: { outDir: "dist", sourcemap: mode !== "production" },
  };
});
