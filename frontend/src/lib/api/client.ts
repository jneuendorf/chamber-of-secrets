const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const response = await fetch(`${API_BASE}${path}`, {
		headers: { 'Content-Type': 'application/json' },
		...options
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
	type: 'in' | 'out';
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

function dateRange(since?: string, until?: string): string {
	const params = new URLSearchParams();
	if (since) params.set('since', since);
	if (until) params.set('until', until);
	const qs = params.toString();
	return qs ? `?${qs}` : '';
}

export const api = {
	products: {
		list: () => request<Product[]>('/products/'),
		get: (id: number) => request<Product>(`/products/${id}`),
		create: (data: Partial<Product>) =>
			request<Product>('/products/', { method: 'POST', body: JSON.stringify(data) }),
		update: (id: number, data: { category_id: number | null }) =>
			request<Product>(`/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
		lookupEAN: (ean: string) => request<EANLookupResult>(`/products/lookup/${ean}`)
	},
	transactions: {
		list: (productId?: number) =>
			request<Transaction[]>(`/transactions/${productId ? `?product_id=${productId}` : ''}`),
		create: (data: {
			product_id: number;
			type: 'in' | 'out';
			quantity?: number;
			unit_price?: number;
			notes?: string;
		}) => request<Transaction>('/transactions/', { method: 'POST', body: JSON.stringify(data) })
	},
	categories: {
		list: () => request<Category[]>('/categories/'),
		create: (data: { name: string; parent_id?: number; icon?: string }) =>
			request<Category>('/categories/', { method: 'POST', body: JSON.stringify(data) }),
		update: (id: number, data: { icon: string | null }) =>
			request<Category>(`/categories/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
	},
	analytics: {
		spending: (since?: string, until?: string) =>
			request<SpendingByCategory[]>(`/analytics/spending${dateRange(since, until)}`),
		timeseries: (since?: string, until?: string) =>
			request<TimeseriesPoint[]>(`/analytics/timeseries${dateRange(since, until)}`)
	}
};
