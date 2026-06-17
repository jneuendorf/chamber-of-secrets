import { describe, expect, type Mock, spyOn, test } from 'bun:test'

import type { api as Api, ApiError as ApiErrorType } from './client.ts'

type ApiContext = {
    api: typeof Api
    ApiError: typeof ApiErrorType
    fetch: Mock<typeof globalThis.fetch>
}

async function withMockedApi(
    body: (ctx: ApiContext) => Promise<void>,
    response: Response = Response.json({}),
) {
    const fetchSpy = spyOn(globalThis, 'fetch').mockResolvedValue(response)
    try {
        const { api, ApiError } = await import('./client.ts')
        await body({ api, ApiError, fetch: fetchSpy })
    } finally {
        fetchSpy.mockRestore()
    }
}

function lastCall(fetchSpy: Mock<typeof globalThis.fetch>) {
    const calls = fetchSpy.mock.calls
    const [url, options] = calls[calls.length - 1]
    return { url: String(url), options }
}

describe('api.products', () => {
    test('list() calls GET /products/', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.products.list()
            expect(lastCall(fetch).url).toEndWith('/products/')
            expect(lastCall(fetch).options?.method).toBeUndefined()
        }))

    test('get(id) calls GET /products/:id', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.products.get(42)
            expect(lastCall(fetch).url).toEndWith('/products/42')
        }))

    test('create(data) calls POST /products/', () =>
        withMockedApi(async ({ api, fetch }) => {
            const data = { name: 'Milk', ean: '123' }
            await api.products.create(data)
            expect(lastCall(fetch).url).toEndWith('/products/')
            expect(lastCall(fetch).options?.method).toBe('POST')
            expect(JSON.parse(lastCall(fetch).options!.body as string)).toEqual(data)
        }))

    test('update(id, data) calls PATCH /products/:id', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.products.update(7, { category_id: 3 })
            expect(lastCall(fetch).url).toEndWith('/products/7')
            expect(lastCall(fetch).options?.method).toBe('PATCH')
            expect(JSON.parse(lastCall(fetch).options!.body as string)).toEqual({
                category_id: 3,
            })
        }))

    test('lookupEAN(ean) calls GET /products/lookup/:ean', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.products.lookupEAN('4006381333931')
            expect(lastCall(fetch).url).toEndWith('/products/lookup/4006381333931')
        }))
})

describe('api.transactions', () => {
    test('list() calls GET /transactions/', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.transactions.list()
            expect(lastCall(fetch).url).toEndWith('/transactions/')
        }))

    test('list(productId) appends query param', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.transactions.list(5)
            expect(lastCall(fetch).url).toEndWith('/transactions/?product_id=5')
        }))

    test('create(data) calls POST /transactions/', () =>
        withMockedApi(async ({ api, fetch }) => {
            const data = { product_id: 1, type: 'in' as const, quantity: 3 }
            await api.transactions.create(data)
            expect(lastCall(fetch).url).toEndWith('/transactions/')
            expect(lastCall(fetch).options?.method).toBe('POST')
            expect(JSON.parse(lastCall(fetch).options!.body as string)).toEqual(data)
        }))
})

describe('api.categories', () => {
    test('list() calls GET /categories/', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.categories.list()
            expect(lastCall(fetch).url).toEndWith('/categories/')
        }))

    test('create(data) calls POST /categories/', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.categories.create({ name: 'Dairy' })
            expect(lastCall(fetch).url).toEndWith('/categories/')
            expect(lastCall(fetch).options?.method).toBe('POST')
        }))

    test('update(id, data) calls PATCH /categories/:id', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.categories.update(2, { name: 'Beverages' })
            expect(lastCall(fetch).url).toEndWith('/categories/2')
            expect(lastCall(fetch).options?.method).toBe('PATCH')
        }))
})

describe('api.analytics', () => {
    test('spending() calls GET /analytics/spending', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.analytics.spending()
            expect(lastCall(fetch).url).toEndWith('/analytics/spending')
        }))

    test('spending(since, until) appends date range params', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.analytics.spending('2024-01-01', '2024-12-31')
            expect(lastCall(fetch).url).toContain('since=2024-01-01')
            expect(lastCall(fetch).url).toContain('until=2024-12-31')
        }))

    test('timeseries() calls GET /analytics/timeseries', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.analytics.timeseries()
            expect(lastCall(fetch).url).toEndWith('/analytics/timeseries')
        }))

    test('timeseries(since) appends only since param', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.analytics.timeseries('2024-06-01')
            expect(lastCall(fetch).url).toContain('since=2024-06-01')
            expect(lastCall(fetch).url).not.toContain('until=')
        }))

    test('restockOverview() calls GET /analytics/restock-overview', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.analytics.restockOverview()
            expect(lastCall(fetch).url).toEndWith('/analytics/restock-overview')
        }))

    test('restockOverview(true) appends include_all_products param', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.analytics.restockOverview(true)
            expect(lastCall(fetch).url).toContain('include_all_products=true')
        }))
})

describe('request error handling', () => {
    test('throws ApiError on non-ok response', () => {
        const errorResponse = new Response(
            JSON.stringify({ detail: 'Product not found' }),
            {
                status: 404,
                statusText: 'Not Found',
                headers: { 'Content-Type': 'application/json' },
            },
        )
        return withMockedApi(async ({ api, ApiError }) => {
            try {
                await api.products.list()
                expect(true).toBe(false)
            } catch (e) {
                expect(e).toBeInstanceOf(ApiError)
                const err = e as InstanceType<typeof ApiError>
                expect(err.status).toBe(404)
                expect(err.detail).toBe('Product not found')
                expect(err.isNotFound).toBe(true)
                expect(err.isServerError).toBe(false)
            }
        }, errorResponse)
    })

    test('falls back to statusText when body is not JSON', () => {
        const errorResponse = new Response('Internal Server Error', {
            status: 500,
            statusText: 'Internal Server Error',
        })
        return withMockedApi(async ({ api, ApiError }) => {
            try {
                await api.products.list()
                expect(true).toBe(false)
            } catch (e) {
                expect(e).toBeInstanceOf(ApiError)
                const err = e as InstanceType<typeof ApiError>
                expect(err.status).toBe(500)
                expect(err.detail).toBe('500 Internal Server Error')
                expect(err.isServerError).toBe(true)
                expect(err.isNotFound).toBe(false)
            }
        }, errorResponse)
    })

    test('isConflict returns true for 409', () => {
        const errorResponse = new Response(
            JSON.stringify({
                detail: 'Cannot delete category with assigned products.',
            }),
            {
                status: 409,
                statusText: 'Conflict',
                headers: { 'Content-Type': 'application/json' },
            },
        )
        return withMockedApi(async ({ api, ApiError }) => {
            try {
                await api.products.list()
                expect(true).toBe(false)
            } catch (e) {
                const err = e as InstanceType<typeof ApiError>
                expect(err.isConflict).toBe(true)
                expect(err.detail).toBe(
                    'Cannot delete category with assigned products.',
                )
            }
        }, errorResponse)
    })

    test('isValidation returns true for 422', () => {
        const errorResponse = new Response(
            JSON.stringify({ detail: 'restock_target must be >= restock_min' }),
            {
                status: 422,
                statusText: 'Unprocessable Entity',
                headers: { 'Content-Type': 'application/json' },
            },
        )
        return withMockedApi(async ({ api, ApiError }) => {
            try {
                await api.products.list()
                expect(true).toBe(false)
            } catch (e) {
                const err = e as InstanceType<typeof ApiError>
                expect(err.isValidation).toBe(true)
            }
        }, errorResponse)
    })

    test('includes Content-Type header', () =>
        withMockedApi(async ({ api, fetch }) => {
            await api.products.list()
            const headers = lastCall(fetch).options?.headers as Record<string, string>
            expect(headers['Content-Type']).toBe('application/json')
        }))
})
