<script lang="ts">
	import { api, type Product } from '$lib/api/client';

	let products: Product[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	async function load() {
		try {
			products = await api.products.list();
		} catch (e) {
			error = `Failed to load inventory: ${e}`;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});
</script>

<h1>Inventory</h1>

{#if loading}
	<p>Loading...</p>
{:else if error}
	<p class="error">{error}</p>
{:else if products.length === 0}
	<p class="empty">No items in inventory yet. <a href="/scan">Scan something!</a></p>
{:else}
	<div class="product-list">
		{#each products as product (product.id)}
			<div class="product-card">
				{#if product.image_url}
					<img src={product.image_url} alt={product.name} />
				{:else}
					<div class="no-image">?</div>
				{/if}
				<div class="details">
					<h3>{product.name}</h3>
					{#if product.brand}
						<p class="brand">{product.brand}</p>
					{/if}
					{#if product.category}
						<span class="category-tag">{product.category.name}</span>
					{/if}
				</div>
				<div class="stock" class:low={product.stock <= 1} class:out={product.stock <= 0}>
					{product.stock}
				</div>
			</div>
		{/each}
	</div>
{/if}

<style>
	h1 {
		margin-top: 0;
	}

	.error {
		color: #e74c3c;
	}

	.empty {
		text-align: center;
		color: #666;
		margin: 3rem 0;
	}

	.product-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.product-card {
		background: white;
		border-radius: 12px;
		padding: 1rem;
		display: flex;
		align-items: center;
		gap: 1rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.product-card img {
		width: 48px;
		height: 48px;
		border-radius: 8px;
		object-fit: cover;
	}

	.no-image {
		width: 48px;
		height: 48px;
		border-radius: 8px;
		background: #eee;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #999;
		font-size: 1.2rem;
	}

	.details {
		flex: 1;
	}

	.details h3 {
		margin: 0;
		font-size: 1rem;
	}

	.brand {
		margin: 0;
		color: #666;
		font-size: 0.85rem;
	}

	.category-tag {
		display: inline-block;
		background: #e8e8ff;
		color: #1a1a2e;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		margin-top: 0.25rem;
	}

	.stock {
		font-size: 1.5rem;
		font-weight: 700;
		color: #27ae60;
		min-width: 3rem;
		text-align: center;
	}

	.stock.low {
		color: #f39c12;
	}

	.stock.out {
		color: #e74c3c;
	}
</style>
