import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

// TODO [BACKEND/ENV]: Frontend API clients should read VITE_API_BASE_URL and
// VITE_MAPS_PROVIDER_KEY from environment variables. Never hard-code secrets;
// browser map keys must be domain-restricted. See BACKEND_HANDOFF.md.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/media': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
  },
})
