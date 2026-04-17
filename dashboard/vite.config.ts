import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Vite config is used only for `npm run dev` outside Docker. In Docker the
// dashboard is built with `npm run build` and served by nginx (see
// dashboard/nginx.conf) which proxies /api to the compose `api` service.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
