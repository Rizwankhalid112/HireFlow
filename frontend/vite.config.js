import path from 'path';
import { fileURLToPath } from 'url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/*
 * Vendor chunking.
 *
 * Everything used to land in one ~416 kB entry chunk, so changing a single
 * component invalidated React, Redux, Router and Query for every returning
 * visitor. These libraries move on their own release cadence — roughly never,
 * compared to the app — so they are split out and stay in the browser cache
 * across deploys.
 *
 * `pdfjs-dist` is deliberately absent: it is already lazily imported by
 * PreviewPane and naming it here would pull it back into the eager graph.
 */
const vendors = {
  'vendor-react': ['react', 'react-dom', 'react-router-dom'],
  'vendor-state': ['@reduxjs/toolkit', 'react-redux', '@tanstack/react-query'],
  'vendor-forms': ['react-hook-form', '@hookform/resolvers', 'zod'],
};

function manualChunks(id) {
  if (!id.includes('node_modules')) return undefined;

  return Object.keys(vendors).find((chunk) =>
    vendors[chunk].some((pkg) => id.includes(`node_modules/${pkg}/`)),
  );
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  envDir: '..',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: { output: { manualChunks } },
    // The entry is well under this now; the ceiling exists so a regression is
    // a build warning rather than something nobody notices.
    chunkSizeWarningLimit: 600,
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
