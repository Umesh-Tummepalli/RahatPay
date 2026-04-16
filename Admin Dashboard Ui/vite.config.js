import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// ── Port Reference (AUTHORITATIVE) ────────────────────────────────────────────
// Module 1 — Registration & Admin  → http://localhost:8000
// Module 2 — Risk Engine & ML      → http://localhost:8002
// Module 3 — Triggers & Claims     → http://localhost:8003
// Admin Dashboard (this server)    → http://localhost:5000
// ─────────────────────────────────────────────────────────────────────────────

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5000,
    allowedHosts: true,
    proxy: {
      // ── Module 3 routes — MUST come before Module 1 catch-all ───────────────

      // Namespaced Module 3 prefix: /m3/* → http://localhost:8003/*
      // Used for: /m3/admin/claims/live, /m3/admin/claims/{id}/override, etc.
      '/m3': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/m3/, ''),
      },

      // Module 3 trigger polling feed
      '/api/triggers': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },

      // ── Module 2 routes ──────────────────────────────────────────────────────

      // Namespaced Module 2 prefix: /m2/* → http://localhost:8002/*
      // Used for: /m2/health, /m2/api/model/info, etc.
      '/m2': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/m2/, ''),
      },

      // Module 2 direct API routes (no prefix rewrite needed)
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
      '/api/model': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },

      // ── Module 1 catch-all — MUST come last ─────────────────────────────────
      // Module 1 — Registration & Admin → http://localhost:8000

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
