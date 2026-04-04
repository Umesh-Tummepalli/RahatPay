import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5000,
    allowedHosts: true,
    proxy: {
      // Module 3 — Triggers & Claims Engine (port 8003), must come before /admin
      '/admin/claims': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      // Module 2 — Risk Engine & Premium Calculator (port 8002)
      '/api/premium': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      '/api/baseline': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      '/api/zones': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      '/api/seasonal': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      // Module 2 health
      '/m2/health': {
        target: 'http://localhost:8002',
        rewrite: (path) => path.replace(/^\/m2/, ''),
        changeOrigin: true,
      },
      // Module 3 health
      '/m3/health': {
        target: 'http://localhost:8003',
        rewrite: (path) => path.replace(/^\/m3/, ''),
        changeOrigin: true,
      },
      // Module 1 — Registration & Policy (port 8000), catch-all for admin routes
      '/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/rider': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/tiers': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/premium': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
