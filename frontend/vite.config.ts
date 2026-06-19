import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The UI dev server runs on :5173; the FastAPI backend on :8000. We proxy every
// /api/* request through to FastAPI so the browser sees a single origin (no CORS),
// exactly as when FastAPI served the page itself. `vite build` later emits static
// files we point FastAPI at — the proxy is a dev-only convenience.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
