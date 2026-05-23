import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
// The dev server proxies /api to the backend so the SPA avoids CORS entirely.
// Override the target with VITE_API_PROXY if the backend runs elsewhere.
export default defineConfig(function (_a) {
    var _b;
    var mode = _a.mode;
    var target = (_b = process.env.VITE_API_PROXY) !== null && _b !== void 0 ? _b : "http://localhost:8000";
    return {
        plugins: [react()],
        resolve: {
            alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
        },
        server: {
            port: 5173,
            proxy: {
                // ws: true so the streaming chat WebSocket upgrade is proxied to the backend.
                "/api": { target: target, changeOrigin: true, ws: true },
            },
        },
        build: { outDir: "dist", sourcemap: mode !== "production" },
    };
});
