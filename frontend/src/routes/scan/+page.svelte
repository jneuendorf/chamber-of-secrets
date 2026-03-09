<script lang="ts">
	import { get } from 'svelte/store';
	import { _ } from 'svelte-i18n';
	import BarcodeScanner from '$lib/components/BarcodeScanner.svelte';
	import CategoryPicker from '$lib/components/CategoryPicker.svelte';
	import { api, type Category, type EANLookupResult } from '$lib/api/client';

	// --- Batch category state ---
	let categories: Category[] = $state([]);
	let batchCategory: Category | null = $state(null);
	let categoryPickerOpen = $state(false);
	let categorySuggestion: string | null = $state(null);

	async function loadCategories() {
		categories = await api.categories.list();
	}
	loadCategories();

	async function createAndSelectBatchCategory(name: string) {
		const cat = await api.categories.create({ name });
		categories = [...categories, cat];
		batchCategory = cat;
	}

	async function handleUpdateIcon(cat: Category, icon: string | null) {
		const updated = await api.categories.update(cat.id, { icon });
		categories = categories.map((c) => (c.id === updated.id ? updated : c));
		if (batchCategory?.id === updated.id) batchCategory = updated;
	}

	// Parse Open Food Facts category string → clean single name
	// e.g. "en:beverages, en:milks, Dairy, Plant-based foods" → "Plant-based foods"
	function parseSuggestedCategory(raw: string): string | null {
		const parts = raw
			.split(',')
			.map((s) => s.trim().replace(/^[a-z]{2}:/, ''))
			.filter(Boolean);
		if (parts.length === 0) return null;
		const name = parts[parts.length - 1];
		return name.charAt(0).toUpperCase() + name.slice(1);
	}

	function applyCategorySuggestion(result: EANLookupResult) {
		if (!result.category) return;
		const suggestion = parseSuggestedCategory(result.category);
		if (!suggestion) return;

		if (!batchCategory) {
			const match = categories.find(
				(c) => c.name.toLowerCase() === suggestion.toLowerCase()
			);
			if (match) {
				batchCategory = match;
				return;
			}
		}
		categorySuggestion = suggestion;
	}

	// --- Scan / lookup state ---
	let lookupResult: EANLookupResult | null = $state(null);
	let lookupError = $state('');
	let loading = $state(false);
	let added = $state(false);

	let quantity = $state(1);
	let unitPrice = $state<number | undefined>(undefined);
	let transactionType = $state<'in' | 'out'>('in');

	async function handleScan(code: string) {
		loading = true;
		lookupError = '';
		lookupResult = null;
		added = false;
		categorySuggestion = null;
		categoryPickerOpen = false;
		try {
			lookupResult = await api.products.lookupEAN(code);
			if (lookupResult) applyCategorySuggestion(lookupResult);
		} catch {
			lookupError = get(_)('scan.notFound', { values: { code } });
		} finally {
			loading = false;
		}
	}

	async function addToInventory() {
		if (!lookupResult) return;
		loading = true;
		try {
			const product = await api.products.create({
				ean: lookupResult.ean,
				name: lookupResult.name ?? get(_)('scan.unknownProduct'),
				brand: lookupResult.brand,
				image_url: lookupResult.image_url,
				category_id: batchCategory?.id ?? null
			});
			await api.transactions.create({
				product_id: product.id,
				type: transactionType,
				quantity,
				unit_price: unitPrice
			});
			added = true;
		} catch (e) {
			lookupError = get(_)('scan.failedToAdd', { values: { error: String(e) } });
		} finally {
			loading = false;
		}
	}

	function scanNext() {
		lookupResult = null;
		lookupError = '';
		added = false;
		categorySuggestion = null;
	}
</script>

<h1 class="mt-0">{$_('scan.title')}</h1>

<!-- Batch category selector -->
{#if categoryPickerOpen}
	<div class="bg-white rounded-xl p-4 shadow-sm mb-4">
		<div class="flex items-center justify-between mb-3">
			<span class="text-sm font-semibold text-gray-700">{$_('category.batchLabel')}</span>
			<button
				onclick={() => (categoryPickerOpen = false)}
				class="text-sm font-medium text-[#1a1a2e] px-3 py-1 rounded-lg bg-gray-100"
			>
				{$_('category.done')}
			</button>
		</div>
		<CategoryPicker
			{categories}
			selected={batchCategory}
			onSelect={(cat) => {
				batchCategory = cat;
				categoryPickerOpen = false;
			}}
			onCreateAndSelect={createAndSelectBatchCategory}
			onUpdateIcon={handleUpdateIcon}
		/>
	</div>
{:else}
	<button
		onclick={() => (categoryPickerOpen = true)}
		class="w-full flex items-center justify-between bg-white rounded-xl px-4 py-3 shadow-sm mb-4 text-left"
	>
		<span class="text-sm text-gray-500">{$_('category.batchLabel')}</span>
		<div class="flex items-center gap-2">
			{#if batchCategory}
				<span
					class="bg-[#e8e8ff] text-[#1a1a2e] px-3 py-0.5 rounded-full text-sm font-medium flex items-center gap-1"
				>
					{#if batchCategory.icon && !batchCategory.icon.startsWith('http') && !batchCategory.icon.startsWith('data:')}
						{batchCategory.icon}
					{/if}
					{batchCategory.name}
				</span>
			{:else}
				<span class="text-gray-400 text-sm">{$_('category.none')}</span>
			{/if}
			<span class="text-gray-400 text-xs">{$_('category.change')} ›</span>
		</div>
	</button>
{/if}

<BarcodeScanner onScan={handleScan} />

{#if loading}
	<p class="text-center my-4">{$_('scan.lookingUp')}</p>
{/if}

{#if lookupError}
	<p class="text-center my-4 text-[#e74c3c]">{lookupError}</p>
{/if}

<!-- Category suggestion from EAN lookup -->
{#if categorySuggestion && !categoryPickerOpen}
	<div class="flex items-center justify-between bg-[#f0f0ff] rounded-xl px-4 py-2 mt-3 text-sm">
		<span class="text-gray-600">
			{$_('scan.categorySuggestion')}: <strong>{categorySuggestion}</strong>
		</span>
		<div class="flex gap-2">
			<button
				onclick={async () => {
					const s = categorySuggestion!;
					const match = categories.find((c) => c.name.toLowerCase() === s.toLowerCase());
					if (match) {
						batchCategory = match;
					} else {
						await createAndSelectBatchCategory(s);
					}
					categorySuggestion = null;
				}}
				class="text-[#1a1a2e] font-medium px-2 py-0.5 rounded bg-[#e8e8ff]"
			>
				{$_('scan.applyCategory')}
			</button>
			<button onclick={() => (categorySuggestion = null)} class="text-gray-400 px-1">✕</button>
		</div>
	</div>
{/if}

{#if lookupResult}
	<div class="bg-white rounded-xl p-6 mt-6 shadow-sm">
		{#if lookupResult.image_url}
			<img
				src={lookupResult.image_url}
				alt={lookupResult.name ?? $_('scan.product')}
				class="max-w-[120px] rounded-lg float-right ml-4"
			/>
		{/if}
		<div>
			<h2 class="mt-0 mb-1">{lookupResult.name ?? $_('common.unknown')}</h2>
			{#if lookupResult.brand}
				<p class="text-gray-500 m-0">{lookupResult.brand}</p>
			{/if}
			<p class="font-mono text-gray-400 text-[0.85rem]">EAN: {lookupResult.ean}</p>
		</div>

		{#if !added}
			<div class="flex flex-col gap-3 mt-4 clear-both">
				<label class="flex flex-col gap-1 text-sm text-[#555]">
					{$_('scan.type')}
					<select
						bind:value={transactionType}
						class="px-2 py-2 border border-gray-300 rounded-md text-base"
					>
						<option value="in">{$_('scan.addToInventory')}</option>
						<option value="out">{$_('scan.removeFromInventory')}</option>
					</select>
				</label>
				<label class="flex flex-col gap-1 text-sm text-[#555]">
					{$_('scan.quantity')}
					<input
						type="number"
						bind:value={quantity}
						min="0.01"
						step="0.01"
						class="px-2 py-2 border border-gray-300 rounded-md text-base"
					/>
				</label>
				<label class="flex flex-col gap-1 text-sm text-[#555]">
					{$_('scan.unitPrice')}
					<input
						type="number"
						bind:value={unitPrice}
						min="0"
						step="0.01"
						placeholder={$_('scan.pricePlaceholder')}
						class="px-2 py-2 border border-gray-300 rounded-md text-base"
					/>
				</label>
				<button
					onclick={addToInventory}
					disabled={loading}
					class="p-3 bg-[#1a1a2e] text-white border-0 rounded-lg text-base cursor-pointer disabled:opacity-50"
				>
					{transactionType === 'in' ? $_('scan.addBtn') : $_('scan.removeBtn')}
				</button>
			</div>
		{:else}
			<div class="text-center my-4">
				<p class="text-[#27ae60] font-semibold mb-3">{$_('scan.addedSuccess')}</p>
				<button
					onclick={scanNext}
					class="px-6 py-2 bg-[#1a1a2e] text-white rounded-lg text-sm cursor-pointer"
				>
					{$_('scan.scanNext')}
				</button>
			</div>
		{/if}
	</div>
{/if}
