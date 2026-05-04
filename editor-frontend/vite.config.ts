import { defineConfig } from "vite";
import { resolve } from "node:path";

const OUTPUT_DIR = resolve(__dirname, "../sidecar/attune_gui/static/editor");

// Vite emits `.vite/manifest.json` alongside the bundle. The Python
// route reads it to find the hashed filenames at request time. See
// `attune_gui.routes.editor_pages._read_manifest`.
export default defineConfig({
  build: {
    outDir: OUTPUT_DIR,
    emptyOutDir: true,
    target: "es2022",
    sourcemap: false,
    cssCodeSplit: false,
    manifest: true,
    rollupOptions: {
      input: { editor: resolve(__dirname, "src/main.ts") },
      output: {
        entryFileNames: "editor-[hash].js",
        chunkFileNames: "editor-[name]-[hash].js",
        assetFileNames: (asset) => {
          if (asset.name?.endsWith(".css")) return "editor-[hash][extname]";
          return "assets/[name]-[hash][extname]";
        },
      },
    },
  },
  esbuild: {
    legalComments: "none",
  },
});
