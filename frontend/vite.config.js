import path from 'path';
import { fileURLToPath } from 'url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  envDir: '..',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // pdfjs-dist ships a web worker; Vite's pre-bundling needs it declared.
  optimizeDeps: {
    include: ['pdfjs-dist'],
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
    },
  },
});
