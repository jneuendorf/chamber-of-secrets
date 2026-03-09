<script lang="ts">
	import { get } from 'svelte/store';
	import { _ } from 'svelte-i18n';
	import CategoryPicker from '$lib/components/CategoryPicker.svelte';
	import { api, type Category, type Product } from '$lib/api/client';

	let products: Product[] = $state([]);
	let categories: Category[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let editingId: number | null = $state(null);

	async function load() {
		try {
			[products, categories] = await Promise.all([api.products.list(), api.categories.list()]);
		} catch (e) {
			error = get(_)('inventory.failedToLoad', { values: { error: String(e) } });
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	async function assignCategory(product: Product, cat: Category | null) {
		editingId = null;
		try {
			const updated = await api.products.update(product.id, { category_id: cat?.id ?? null });
			products = products.map((p) => (p.id === product.id ? { ...p, ...updated, category: cat, stock: p.stock } : p));
		} catch (e) {
			error = get(_)('category.failedToSave', { values: { error: String(e) } });
		}
	}

	async function createAndAssign(product: Product, name: string) {
		try {
			const cat = await api.categories.create({ name });
			categories = [...categories, cat];
			await assignCategory(product, cat);
		} catch (e) {
			error = get(_)('category.failedToSave', { values: { error: String(e) } });
		}
	}

	async function handleUpdateIcon(cat: Category, icon: string | null) {
		const updated = await api.categories.update(cat.id, { icon });
		categories = categories.map((c) => (c.id === updated.id ? updated : c));
		// Refresh icon on any product that has this category
		products = products.map((p) =>
			p.category?.id === updated.id ? { ...p, category: updated } : p
		);
	}
</script>

<h1 class="mt-0">{$_('nav.inventory')}</h1>

{#if loading}
	<p>{$_('common.loading')}</p>
{:else if error}
	<p class="text-[#e74c3c]">{error}</p>
{:else if products.length === 0}
	<p class="text-center text-gray-500 my-12">
		{$_('inventory.empty')} <a href="/scan">{$_('inventory.scanCta')}</a>
	</p>
{:else}
	<div class="flex flex-col gap-3">
		{#each products as product (product.id)}
			<div class="bg-white rounded-xl p-4 shadow-sm">
				<div class="flex items-center gap-4">
					{#if product.image_url}
						<img
							src={product.image_url}
							alt={product.name}
							class="w-12 h-12 rounded-lg object-cover"
						/>
					{:else}
						<div
							class="w-12 h-12 rounded-lg bg-[#eee] flex items-center justify-center text-gray-400 text-xl"
						>
							?
						</div>
					{/if}
					<div class="flex-1 min-w-0">
						<h3 class="m-0 text-base">{product.name}</h3>
						{#if product.brand}
							<p class="m-0 text-gray-500 text-[0.85rem]">{product.brand}</p>
						{/if}
						<button
							onclick={() => (editingId = editingId === product.id ? null : product.id)}
							class="mt-1 flex items-center gap-1 text-left"
						>
							{#if product.category}
								<span class="bg-[#e8e8ff] text-[#1a1a2e] px-2 py-0.5 rounded text-xs">
									{product.category.name}
								</span>
							{:else}
								<span class="text-gray-400 text-xs">{$_('category.none')}</span>
							{/if}
							<span class="text-gray-400 text-xs">{$_('category.change')} ›</span>
						</button>
					</div>
					<div class="stock" class:low={product.stock <= 1} class:out={product.stock <= 0}>
						{product.stock}
					</div>
				</div>

				{#if editingId === product.id}
					<div class="mt-3 pt-3 border-t border-gray-100">
						<CategoryPicker
							{categories}
							selected={product.category}
							onSelect={(cat) => assignCategory(product, cat)}
							onCreateAndSelect={(name) => createAndAssign(product, name)}
							onUpdateIcon={handleUpdateIcon}
						/>
					</div>
				{/if}
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
