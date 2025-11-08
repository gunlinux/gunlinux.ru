import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  build: {
    outDir: 'blog/static/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: 'blog/static/src/styles.css',
      output: {
        assetFileNames: (assetInfo) => {
          if (assetInfo.name.endsWith('.css')) {
            return 'css/bundle.css';
          }
          return '[name].[extname]';
        },
        entryFileNames: 'js/[name].js',
        chunkFileNames: 'js/[name].js'
      }
    },
    cssMinify: true,
    sourcemap: true,
  },
  publicDir: false, // We don't need a public directory for this Flask app
  server: {
    port: 3000,
    open: false,
  }
});
