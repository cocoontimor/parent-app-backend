import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// Assets are served by Django under STATIC_URL (/static/). In dev, django-vite
// loads them straight from this dev server (port 5173) with HMR; in prod they
// come from the built manifest in dist/.
export default defineConfig({
  plugins: [svelte()],
  base: '/static/',
  build: {
    manifest: true,
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: 'src/main.js',
    },
  },
  server: {
    port: 5173,
    origin: 'http://localhost:5173',
  },
})
