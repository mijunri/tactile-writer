import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/writer/',
  server: {
    port: 5173,
    proxy: {
      '/writer/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/writer/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
