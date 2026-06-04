import { defineConfig } from "vite";

export default defineConfig({
  // Tauri expects a fixed port during dev
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
  // Build to dist/ for Tauri to bundle
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "esnext",
    rollupOptions: {
      input: {
        main: "src/index.html",
        overlay: "src/overlay.html",
      },
    },
  },
});
