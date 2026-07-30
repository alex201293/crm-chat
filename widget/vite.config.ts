import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'CRMChat',
      fileName: () => 'chat.js',
      formats: ['iife'], // Single file, self-executing
    },
    outDir: 'dist',
    minify: 'terser',
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
  define: {
    'process.env.NODE_ENV': '"production"',
  },
});
