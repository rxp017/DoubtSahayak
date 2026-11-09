import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, /api/* is proxied to the local FastAPI backend (port 8000).
// In production on Vercel, /api/ask is served by api/ask.py (serverless).
// If the backend lives elsewhere (e.g. Render), set VITE_API_URL to its URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
