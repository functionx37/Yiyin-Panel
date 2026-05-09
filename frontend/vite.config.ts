import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/yiyin/',
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/yiyin/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
