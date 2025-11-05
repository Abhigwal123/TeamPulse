import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react({
    include: '**/*.{jsx,js}',
  })],
  esbuild: {
    loader: 'jsx',
    include: /src\/.*\.jsx?$/,
    exclude: [],
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.js': 'jsx',
      },
    },
  },
  build: {
    // Use inline source maps instead of eval for CSP compliance
    sourcemap: 'inline',
  },
  server: {
    proxy: {
      // Proxy API requests to backend (optional - can use direct URL too)
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  // Configure to minimize eval usage in development
  css: {
    devSourcemap: false,
  },
  // Use classic mode for React Fast Refresh to avoid eval issues
  define: {
    // Ensure we're in development mode
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
  },
})

