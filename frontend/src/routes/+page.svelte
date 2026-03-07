<script lang="ts">
	import { api, type Product } from '$lib/api/client';

	let products: Product[] = $state([]);
	let loading = $state(true);

	async function load() {
		try {
			products = await api.products.list();
		} catch {
			// API not available yet
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	let totalItems = $derived(products.reduce((sum, p) => sum + p.stock, 0));
	let categories = $derived(new Set(products.map((p) => p.category?.name).filter(Boolean)).size);
</script>

<h1>Dashboard</h1>

<div class="stats">
	<div class="stat-card">
		<span class="stat-value">{loading ? '...' : products.length}</span>
		<span class="stat-label">Products</span>
	</div>
	<div class="stat-card">
		<span class="stat-value">{loading ? '...' : totalItems}</span>
		<span class="stat-label">Total Items</span>
	</div>
	<div class="stat-card">
		<span class="stat-value">{loading ? '...' : categories}</span>
		<span class="stat-label">Categories</span>
	</div>
</div>

<div class="quick-actions">
	<a href="/scan" class="action-btn">Scan Item</a>
	<a href="/inventory" class="action-btn secondary">View Inventory</a>
	<a href="/analytics" class="action-btn secondary">Analytics</a>
</div>

<style>
	h1 {
		margin-top: 0;
	}

	.stats {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 1rem;
		margin-bottom: 2rem;
	}

	.stat-card {
		background: white;
		border-radius: 12px;
		padding: 1.5rem;
		text-align: center;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.stat-value {
		display: block;
		font-size: 2rem;
		font-weight: 700;
		color: #1a1a2e;
	}

	.stat-label {
		color: #666;
		font-size: 0.9rem;
	}

	.quick-actions {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.action-btn {
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		text-decoration: none;
		font-weight: 600;
		background: #1a1a2e;
		color: white;
		transition: opacity 0.2s;
	}

	.action-btn:hover {
		opacity: 0.9;
	}

	.action-btn.secondary {
		background: white;
		color: #1a1a2e;
		border: 1px solid #ddd;
	}
</style>
