import type { components } from './schema'

/**
 * Wire types are **generated** from the backend's OpenAPI schema — never
 * hand-written. The Pydantic schemas are the single source of truth. `./schema`
 * is gitignored build output; every recipe that needs it depends on `just types`,
 * so it regenerates on demand.
 *
 * These aliases keep the import surface stable (`import type { Product }`) and
 * give the generated `*Read` names their domain names.
 */
type Schemas = components['schemas']

export type Product = Schemas['ProductWithStock']
export type Category = Schemas['CategoryRead']
export type EANLookupResult = Schemas['EANLookupResult']
export type AvatarConfig = Schemas['AvatarConfig']
export type Profile = Schemas['ProfileRead']
export type Transaction = Schemas['TransactionRead']
export type SpendingByCategory = Schemas['SpendingByCategory']
export type TimeseriesPoint = Schemas['TimeseriesPoint']
export type RestockOverviewRow = Schemas['RestockOverviewRow']
export type RestockGroupTotal = Schemas['RestockGroupTotal']
export type RestockOverviewResponse = Schemas['RestockOverviewResponse']

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

/** localStorage key for the active profile id (WL-5.1). Shared with `$lib/profiles`. */
export const ACTIVE_PROFILE_KEY = 'activeProfileId'

function activeProfileId(): number | null {
    if (typeof localStorage === 'undefined') {
        return null
    }
    const raw = localStorage.getItem(ACTIVE_PROFILE_KEY)
    return raw ? Number(raw) : null
}

export class ApiError extends Error {
    readonly status: number
    readonly detail: string

    constructor(status: number, statusText: string, detail?: string) {
        const msg = detail ?? `${status} ${statusText}`
        super(msg)
        this.name = 'ApiError'
        this.status = status
        this.detail = msg
    }

    get isNotFound() {
        return this.status === 404
    }
    get isConflict() {
        return this.status === 409
    }
    get isValidation() {
        return this.status === 422
    }
    get isServerError() {
        return this.status >= 500
    }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    })
    if (!response.ok) {
        let detail: string | undefined
        try {
            const body = await response.json()
            detail = body.detail
        } catch {
            // response body isn't JSON — fall through to statusText
        }
        throw new ApiError(response.status, response.statusText, detail)
    }
    // Cast needed: T is generic so TS can't prove undefined satisfies it,
    // but the only caller hitting 204 binds T = void.
    if (response.status === 204) {
        return undefined as T
    }
    return response.json()
}

function dateRange(since?: string, until?: string): string {
    const params = new URLSearchParams()
    if (since) {
        params.set('since', since)
    }
    if (until) {
        params.set('until', until)
    }
    const qs = params.toString()
    return qs ? `?${qs}` : ''
}

export const api = {
    products: {
        list: () => request<Product[]>('/products/'),
        get: (id: number) => request<Product>(`/products/${id}`),
        create: (data: Partial<Product>) =>
            request<Product>('/products/', {
                method: 'POST',
                body: JSON.stringify(data),
            }),
        update: (
            id: number,
            data: { category_id?: number | null; image_url?: string | null },
        ) =>
            request<Product>(`/products/${id}`, {
                method: 'PATCH',
                body: JSON.stringify(data),
            }),
        uploadImage: async (id: number, file: File): Promise<Product> => {
            const form = new FormData()
            form.append('file', file)
            const res = await fetch(`${API_BASE}/products/${id}/image`, {
                method: 'POST',
                body: form,
            })
            if (!res.ok) {
                let detail: string | undefined
                try {
                    detail = (await res.json()).detail
                } catch {
                    /* empty */
                }
                throw new ApiError(res.status, res.statusText, detail)
            }
            return res.json()
        },
        deleteImage: (id: number) =>
            request<void>(`/products/${id}/image`, { method: 'DELETE' }),
        lookupEAN: (ean: string) => request<EANLookupResult>(`/products/lookup/${ean}`),
        delete: (id: number) => request<void>(`/products/${id}`, { method: 'DELETE' }),
        merge: (sourceId: number, targetId: number) =>
            request<Product>('/products/merge', {
                method: 'POST',
                body: JSON.stringify({ source_id: sourceId, target_id: targetId }),
            }),
        contribute: (id: number) =>
            request<{ ok: boolean }>(`/products/${id}/contribute`, { method: 'POST' }),
    },
    transactions: {
        list: (productId?: number) =>
            request<Transaction[]>(
                `/transactions/${productId ? `?product_id=${productId}` : ''}`,
            ),
        create: (data: {
            product_id: number
            type: 'in' | 'out'
            quantity?: number
            unit_price?: number
            notes?: string
        }) =>
            // Attribute to the active profile (WL-5.1) without touching call sites.
            request<Transaction>('/transactions/', {
                method: 'POST',
                body: JSON.stringify({ profile_id: activeProfileId(), ...data }),
            }),
        update: (
            id: number,
            data: {
                type?: 'in' | 'out'
                quantity?: number
                unit_price?: number | null
                notes?: string | null
            },
        ) =>
            request<Transaction>(`/transactions/${id}`, {
                method: 'PATCH',
                body: JSON.stringify(data),
            }),
        delete: (id: number) =>
            request<void>(`/transactions/${id}`, { method: 'DELETE' }),
    },
    categories: {
        list: () => request<Category[]>('/categories/'),
        create: (data: {
            name: string
            parent_id?: number | null
            icon?: string | null
            restock_target?: number | null
            restock_min?: number | null
            restock_inherit?: boolean
        }) =>
            request<Category>('/categories/', {
                method: 'POST',
                body: JSON.stringify(data),
            }),
        update: (
            id: number,
            data: {
                name?: string
                parent_id?: number | null
                icon?: string | null
                restock_target?: number | null
                restock_min?: number | null
                restock_inherit?: boolean
            },
        ) =>
            request<Category>(`/categories/${id}`, {
                method: 'PATCH',
                body: JSON.stringify(data),
            }),
        delete: (id: number) =>
            request<void>(`/categories/${id}`, { method: 'DELETE' }),
    },
    profiles: {
        list: (includeArchived = false) =>
            request<Profile[]>(
                `/profiles/${includeArchived ? '?include_archived=true' : ''}`,
            ),
        create: (data: {
            name: string
            avatar_config?: AvatarConfig
            locale?: string
        }) =>
            request<Profile>('/profiles/', {
                method: 'POST',
                body: JSON.stringify(data),
            }),
        update: (
            id: number,
            data: {
                name?: string
                avatar_config?: AvatarConfig
                locale?: string | null
                is_archived?: boolean
            },
        ) =>
            request<Profile>(`/profiles/${id}`, {
                method: 'PATCH',
                body: JSON.stringify(data),
            }),
    },
    analytics: {
        spending: (since?: string, until?: string) =>
            request<SpendingByCategory[]>(
                `/analytics/spending${dateRange(since, until)}`,
            ),
        timeseries: (since?: string, until?: string) =>
            request<TimeseriesPoint[]>(
                `/analytics/timeseries${dateRange(since, until)}`,
            ),
        restockOverview: (includeAllProducts = false) =>
            request<RestockOverviewResponse>(
                `/analytics/restock-overview${includeAllProducts ? '?include_all_products=true' : ''}`,
            ),
    },
}
