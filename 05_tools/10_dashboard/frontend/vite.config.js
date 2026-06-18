import { defineConfig } from 'vite';

export default defineConfig({
  base: '/static/',
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:9988',
        changeOrigin: true,
      },
    },
  },
});
