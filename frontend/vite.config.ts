import { sveltekit } from '@sveltejs/kit/vite'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    // Forward /api to the backend so mobile devices on the LAN can reach it
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
