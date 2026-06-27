import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { sveltekit } from '@sveltejs/kit/vite'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// `just dev https` sets DEV_HTTPS=true so the dev server serves over TLS using
// the mkcert certs in ../certs. getUserMedia (camera scanning) only works in a
// secure context, so HTTPS is needed to test scanning on a phone over the LAN.
const httpsEnabled = process.env.DEV_HTTPS === 'true'

function devHttps() {
  if (!httpsEnabled) {
    return undefined
  }
  const key = fileURLToPath(new URL('../certs/key.pem', import.meta.url))
  const cert = fileURLToPath(new URL('../certs/cert.pem', import.meta.url))
  if (!existsSync(key) || !existsSync(cert)) {
    throw new Error(
      'DEV_HTTPS=true but ../certs/{cert,key}.pem are missing. Run `just certs` first.',
    )
  }
  return { key: readFileSync(key), cert: readFileSync(cert) }
}

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    https: devHttps(),
    // Forward /api to the backend so mobile devices on the LAN can reach it
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
