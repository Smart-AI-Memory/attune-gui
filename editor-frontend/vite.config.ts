import { defineConfig } from "vite";
import { resolve } from "node:path";

const OUTPUT_DIR = resolve(__dirname, "../sidecar/attune_gui/static/editor");

export default defineConfig({
  build: {
    outDir: OUTPUT_DIR,
    emptyOutDir: true,
    target: "es2022",
    sourcemap: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: resolve(__dirname, "src/main.ts"),
      output: {
        entryFileNames: "editor.js",
        chunkFileNames: "editor-[name].js",
        assetFileNames: (asset) => {
          if (asset.name?.endsWith(".css")) return "editor.css";
          return "assets/[name][extname]";
        },
      },
    },
  },
  esbuild: {
    legalComments: "none",
  },
});
