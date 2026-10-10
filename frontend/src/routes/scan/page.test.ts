/**
 * Scan flow integration (WL-6.5): the real page against a fake backend.
 * Barcodes go in through the manual field — same `handleScan` path as the camera.
 */
import { afterEach, beforeEach, describe, expect, spyOn, test } from 'bun:test'

import { render, screen, waitFor } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'

import { drainArrivals } from '$lib/arrivals'
import ScanPage from './+page.svelte'

const BUTTER = { id: 5, name: 'Butter', ean: '4008452010222', category_id: null }

type Route = (body: unknown) => Response
type Call = { method: string; path: string; body: unknown }

let routes: Record<string, Route>
let calls: Call[]

/** Route `fetch` by "METHOD /path?query"; anything unrouted is a 404. */
function fakeBackend(table: Record<string, Route>) {
    routes = table
    calls = []
    const fake = async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), 'http://localhost')
        const method = init?.method ?? 'GET'
        const path = url.pathname.replace(/^\/api/, '') + url.search
        const body = typeof init?.body === 'string' ? JSON.parse(init.body) : null
        calls.push({ method, path, body })
        const route = routes[`${method} ${path}`]
        return route
            ? route(body)
            : Response.json({ detail: 'Not found' }, { status: 404 })
    }
    // Cast: Bun's `fetch` type also carries `preconnect`.
    spyOn(globalThis, 'fetch').mockImplementation(fake as typeof fetch)
}

const ok = (data: unknown) => () => Response.json(data)
const posted = (method: string, path: string) =>
    calls.filter((call) => call.method === method && call.path === path)

async function scan(code: string) {
    const user = userEvent.setup()
    render(ScanPage)
    await user.click(screen.getByRole('button', { name: 'Enter barcode manually' }))
    await user.type(
        screen.getByPlaceholderText('Enter EAN / barcode'),
        `${code}{Enter}`,
    )
    return user
}

beforeEach(() => {
    fakeBackend({})
})

afterEach(() => {
    ;(globalThis.fetch as unknown as { mockRestore(): void }).mockRestore()
    drainArrivals()
})

describe('scan page', () => {
    test('a known product: prefilled price, stock-in, undo', async () => {
        fakeBackend({
            [`GET /products/lookup/${BUTTER.ean}`]: ok({
                ean: BUTTER.ean,
                name: 'Butter',
                brand: 'Weihenstephan',
                image_url: null,
                category: null,
                from_cache: true,
            }),
            [`GET /products/?ean=${BUTTER.ean}`]: ok([BUTTER]),
            'GET /transactions/?product_id=5': ok([{ id: 1, unit_price: 1.49 }]),
            'GET /categories/': ok([]),
            'POST /transactions/': ok({ id: 77 }),
            'DELETE /transactions/77': () => new Response(null, { status: 204 }),
        })
        const user = await scan(BUTTER.ean)

        await screen.findByText('Butter')
        await waitFor(() =>
            expect(
                (screen.getByPlaceholderText('e.g. 1.99') as HTMLInputElement).value,
            ).toBe('1.49'),
        )
        // No whole-catalog download just to find one product (WL-6.3).
        expect(posted('GET', '/products/')).toHaveLength(0)

        await user.click(screen.getByRole('button', { name: 'Add to Inventory' }))
        await screen.findByText('Added to inventory!')
        expect(posted('POST', '/transactions/')[0].body).toMatchObject({
            product_id: 5,
            type: 'in',
            quantity: 1,
            unit_price: 1.49,
        })
        expect(posted('POST', '/products/')).toHaveLength(0)
        // The scan queues an arrival for the chamber (WL-5.6).
        expect(drainArrivals()).toEqual(new Map([[5, 1]]))

        await user.click(screen.getByRole('button', { name: 'Undo' }))
        await waitFor(() =>
            expect(posted('DELETE', '/transactions/77')).toHaveLength(1),
        )
    })

    test('remove mode records a stock-out', async () => {
        fakeBackend({
            [`GET /products/lookup/${BUTTER.ean}`]: ok({
                ean: BUTTER.ean,
                name: 'Butter',
                brand: null,
                image_url: null,
                category: null,
                from_cache: true,
            }),
            [`GET /products/?ean=${BUTTER.ean}`]: ok([BUTTER]),
            'GET /transactions/?product_id=5': ok([]),
            'GET /categories/': ok([]),
            'POST /transactions/': ok({ id: 78 }),
        })
        const user = userEvent.setup()
        render(ScanPage)
        await user.click(screen.getByRole('button', { name: /Remove/ }))
        await user.click(screen.getByRole('button', { name: 'Enter barcode manually' }))
        await user.type(
            screen.getByPlaceholderText('Enter EAN / barcode'),
            `${BUTTER.ean}{Enter}`,
        )

        await user.click(
            await screen.findByRole('button', { name: 'Remove from Inventory' }),
        )
        await screen.findByText('Removed from inventory!')
        expect(posted('POST', '/transactions/')[0].body).toMatchObject({
            product_id: 5,
            type: 'out',
        })
        expect(drainArrivals().size).toBe(0) // only stock-ins fly into the chamber
    })

    test('an unknown barcode: create it by hand, then stock it', async () => {
        const code = '4001234567890'
        fakeBackend({
            [`GET /products/?ean=${code}`]: ok([]),
            'GET /categories/': ok([]),
            'POST /products/': (body) => Response.json({ id: 9, ...(body as object) }),
            'POST /transactions/': ok({ id: 79 }),
        })
        const user = await scan(code)

        await screen.findByText(`No product found for barcode: ${code}`)
        await user.click(screen.getByRole('button', { name: 'Create it yourself' }))
        const add = screen.getByRole('button', { name: 'Add to Inventory' })
        expect(add).toHaveProperty('disabled', true) // a name is required

        await user.type(screen.getByPlaceholderText('Product name'), 'Mystery jam')
        await user.click(add)
        await screen.findByText('Added to inventory!')
        expect(posted('POST', '/products/')[0].body).toMatchObject({
            name: 'Mystery jam',
            ean: code,
        })
        expect(posted('POST', '/transactions/')[0].body).toMatchObject({
            product_id: 9,
            type: 'in',
        })
    })

    test('an implausible code skips the lookup', async () => {
        await scan('123')
        await screen.findByText('No product found for barcode: 123')
        expect(calls.some((call) => call.path.startsWith('/products/lookup'))).toBe(
            false,
        )
    })
})
