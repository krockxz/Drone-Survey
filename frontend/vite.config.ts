import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // Path resolution
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@features': path.resolve(__dirname, './src/features'),
      '@stores': path.resolve(__dirname, './src/stores'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@types': path.resolve(__dirname, './src/types'),
    },
  },
  
  // Development server configuration
  server: {
    port: 5173,
    host: true,
    proxy: {
      // Proxy API requests to backend
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      },
      // Proxy WebSocket connections
      '/socket.io': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        ws: true,
        secure: false,
      }
    }
  },
  
  // Build configuration
  build: {
    outDir: 'dist',
    sourcemap: true,
    // Optimize chunk sizes
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['@mantine/core', '@mantine/hooks'],
          maps: ['react-leaflet', 'leaflet'],
          charts: ['recharts', '@mantine/charts'],
        }
      }
    }
  },
  
  // Environment variables
  define: {
    // Ensure proper environment variable handling
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
  },
  
  // CSS configuration
  css: {
    modules: {
      localsConvention: 'camelCase',
    }
  }
})