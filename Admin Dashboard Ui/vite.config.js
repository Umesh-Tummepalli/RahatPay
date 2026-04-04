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
      '/admin/claims': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/rider': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/zones': {
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
      '/healthz': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
