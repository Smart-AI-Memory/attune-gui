import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const SIDECAR_PORT = parseInt(process.env.SIDECAR_PORT || '8765', 10)
const UI_PORT = parseInt(process.env.PORT || '5173', 10)

export default defineConfig({
  plugins: [react()],
  server: {
    port: UI_PORT,
    proxy: {
      '/api': `http://127.0.0.1:${SIDECAR_PORT}`,
    },
  },
  build: {
    outDir: 'dist',
  },
})
