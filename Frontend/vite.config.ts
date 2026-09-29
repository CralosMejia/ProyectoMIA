import { configDefaults, defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    passWithNoTests: true,
    exclude: [...configDefaults.exclude, 'e2e/**'],
    setupFiles: ['./src/test/setup.ts'],
  },
})
