<script lang="ts">
	import { get } from 'svelte/store';
	import { _ } from 'svelte-i18n';
	import { api, type Product } from '$lib/api/client';

	let products: Product[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	async function load() {
		try {
			products = await api.products.list();
		} catch (e) {
			error = get(_)('inventory.failedToLoad', { values: { error: String(e) } });
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});
</script>

<h1 class="mt-0">{$_('nav.inventory')}</h1>

{#if loading}
	<p>{$_('common.loading')}</p>
{:else if error}
	<p class="text-[#e74c3c]">{error}</p>
{:else if products.length === 0}
	<p class="text-center text-gray-500 my-12">{$_('inventory.empty')} <a href="/scan">{$_('inventory.scanCta')}</a></p>
{:else}
	<div class="flex flex-col gap-3">
		{#each products as product (product.id)}
			<div class="bg-white rounded-xl p-4 flex items-center gap-4 shadow-sm">
				{#if product.image_url}
					<img src={product.image_url} alt={product.name} class="w-12 h-12 rounded-lg object-cover" />
				{:else}
					<div class="w-12 h-12 rounded-lg bg-[#eee] flex items-center justify-center text-gray-400 text-xl">?</div>
				{/if}
				<div class="flex-1">
					<h3 class="m-0 text-base">{product.name}</h3>
					{#if product.brand}
						<p class="m-0 text-gray-500 text-[0.85rem]">{product.brand}</p>
					{/if}
					{#if product.category}
						<span class="inline-block bg-[#e8e8ff] text-[#1a1a2e] px-2 py-0.5 rounded text-xs mt-1">{product.category.name}</span>
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
