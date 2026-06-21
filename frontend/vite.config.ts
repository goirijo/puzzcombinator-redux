import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// The UI dev server runs on :5173; the FastAPI backend on :8000. We proxy every
// /api/* request through to FastAPI so the browser sees a single origin (no CORS),
// exactly as when FastAPI served the page itself. `vite build` later emits static
// files we point FastAPI at — the proxy is a dev-only convenience.
// https://vite.dev/config/
//
// `test` configures Vitest (run with `npm test`). We use the jsdom environment because the
// pure modules under test import `@xyflow/react`, whose entry expects browser globals.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
})
