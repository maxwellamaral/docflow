import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/upload': 'http://localhost:8000',
      '/pipeline': 'http://localhost:8000',
      '/download': 'http://localhost:8000',
    },
  },
})
