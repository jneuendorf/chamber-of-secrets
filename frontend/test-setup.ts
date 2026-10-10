/**
 * `bun test` preload (WL-6.5): lets component tests import `.svelte` files and
 * render them into a DOM.
 *
 * - A Bun plugin compiles `.svelte` components and `.svelte.js/ts` rune modules
 *   with Svelte's own compiler (client output).
 * - happy-dom provides `document`/`window` for every test file.
 * - svelte-i18n starts synchronously in English, so rendered text is stable.
 *
 * `bun test --conditions browser` (see package.json) makes `svelte` resolve to
 * its client build — the default export is the server one, where `mount`
 * throws.
 */

import { afterEach } from 'bun:test'
import { readFileSync } from 'node:fs'
import { plugin } from 'bun'

import { GlobalRegistrator } from '@happy-dom/global-registrator'
import { compile, compileModule } from 'svelte/compiler'

// Keep Bun's own fetch API: tests stub `fetch` with `spyOn(globalThis, 'fetch')`
// and build replies with Bun's `Response`, which happy-dom would replace.
const { fetch, Response, Request, Headers, FormData } = globalThis
GlobalRegistrator.register({ url: 'http://localhost:5173/' })
Object.assign(globalThis, { fetch, Response, Request, Headers, FormData })

const typescript = new Bun.Transpiler({ loader: 'ts' })

plugin({
    name: 'svelte',
    setup(build) {
        build.onLoad({ filter: /\.svelte$/ }, ({ path }) => ({
            contents: compile(readFileSync(path, 'utf8'), {
                filename: path,
                generate: 'client',
            }).js.code,
            loader: 'js',
        }))
        // Rune modules (bits-ui ships `.svelte.js`); strip TS before compiling.
        build.onLoad({ filter: /\.svelte\.(js|ts)$/ }, ({ path }) => {
            const source = readFileSync(path, 'utf8')
            return {
                contents: compileModule(
                    path.endsWith('.ts') ? typescript.transformSync(source) : source,
                    { filename: path, generate: 'client' },
                ).js.code,
                loader: 'js',
            }
        })
    },
})

const { addMessages, init } = await import('svelte-i18n')
const { default: en } = await import('./src/lib/i18n/en.json')
addMessages('en', en)
init({ fallbackLocale: 'en', initialLocale: 'en' })

const { cleanup } = await import('@testing-library/svelte')
afterEach(() => {
    cleanup()
    localStorage.clear()
})
