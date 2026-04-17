import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: ['babel-plugin-react-compiler'],
      },
    }),
  ],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      'recharts': fileURLToPath(new URL('./node_modules/recharts/es6/index.js', import.meta.url))
    }
  },

  server: {
    port: 3000,
    allowedHosts: [
      'handy-waters-diary-liz.trycloudflare.com',
      'josue-ungreedy-unphysically.ngrok-free.dev',
      'gilads-macbook-pro.taila610c4.ts.net'
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/consensus': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/portfolio': {
        target: 'http://localhost:5001',
        changeOrigin: true
      }
    }
  },

  build: {
    outDir: '../static/dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['react', 'react-dom', 'marked', 'dompurify']
        }
      }
    }
  }
})
