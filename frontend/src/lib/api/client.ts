const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    return response.json();
}

// Products
export interface Product {
    id: number;
    ean: string | null;
    name: string;
    brand: string | null;
    category_id: number | null;
    image_url: string | null;
    created_at: string;
    stock: number;
    category: Category | null;
}

export interface Category {
    id: number;
    name: string;
    parent_id: number | null;
    icon: string | null;
    restock_target: number | null;
    restock_min: number | null;
    restock_inherit: boolean;
}

export interface EANLookupResult {
    ean: string;
    name: string | null;
    brand: string | null;
    image_url: string | null;
    category: string | null;
}

export interface Transaction {
    id: number;
    product_id: number;
    type: "in" | "out";
    quantity: number;
    unit_price: number | null;
    transacted_at: string;
    notes: string | null;
}

export interface SpendingByCategory {
    category: string;
    total_spent: number;
    item_count: number;
}

export interface TimeseriesPoint {
    date: string;
    category: string;
    item_count: number;
    total_spent: number;
}

export interface RestockOverviewRow {
    id: number;
    name: string;
    brand: string | null;
    category_id: number | null;
    category_name: string;
    current_stock: number;
    effective_target: number | null;
    effective_min: number | null;
    resolved_from_category_id: number | null;
    missing_to_target: number;
    below_min: boolean;
    needs_restock: boolean;
}

export interface RestockGroupTotal {
    category_id: number | null;
    category_name: string;
    total_missing_to_target: number;
    affected_products: number;
}

export interface RestockOverviewResponse {
    rows: RestockOverviewRow[];
    total_missing_quantity: number;
    total_products_needing_restock: number;
    by_child_category: RestockGroupTotal[];
    by_parent_category: RestockGroupTotal[];
}

function dateRange(since?: string, until?: string): string {
    const params = new URLSearchParams();
    if (since) params.set("since", since);
    if (until) params.set("until", until);
    const qs = params.toString();
    return qs ? `?${qs}` : "";
}

export const api = {
    products: {
        list: () => request<Product[]>("/products/"),
        get: (id: number) => request<Product>(`/products/${id}`),
        create: (data: Partial<Product>) =>
            request<Product>("/products/", { method: "POST", body: JSON.stringify(data) }),
        update: (id: number, data: { category_id: number | null }) =>
            request<Product>(`/products/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        lookupEAN: (ean: string) => request<EANLookupResult>(`/products/lookup/${ean}`),
    },
    transactions: {
        list: (productId?: number) =>
            request<Transaction[]>(`/transactions/${productId ? `?product_id=${productId}` : ""}`),
        create: (data: {
            product_id: number;
            type: "in" | "out";
            quantity?: number;
            unit_price?: number;
            notes?: string;
        }) =>
            request<Transaction>("/transactions/", { method: "POST", body: JSON.stringify(data) }),
    },
    categories: {
        list: () => request<Category[]>("/categories/"),
        create: (data: {
            name: string;
            parent_id?: number | null;
            icon?: string | null;
            restock_target?: number | null;
            restock_min?: number | null;
            restock_inherit?: boolean;
        }) => request<Category>("/categories/", { method: "POST", body: JSON.stringify(data) }),
        update: (
            id: number,
            data: {
                name?: string;
                parent_id?: number | null;
                icon?: string | null;
                restock_target?: number | null;
                restock_min?: number | null;
                restock_inherit?: boolean;
            },
        ) =>
            request<Category>(`/categories/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    },
    analytics: {
        spending: (since?: string, until?: string) =>
            request<SpendingByCategory[]>(`/analytics/spending${dateRange(since, until)}`),
        timeseries: (since?: string, until?: string) =>
            request<TimeseriesPoint[]>(`/analytics/timeseries${dateRange(since, until)}`),
        restockOverview: (includeAllProducts = false) =>
            request<RestockOverviewResponse>(
                `/analytics/restock-overview${includeAllProducts ? "?include_all_products=true" : ""}`,
            ),
    },
};
