<script lang="ts">
	import { get } from 'svelte/store';
	import { _ } from 'svelte-i18n';
	import BarcodeScanner from '$lib/components/BarcodeScanner.svelte';
	import { api, type EANLookupResult } from '$lib/api/client';

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
		try {
			lookupResult = await api.products.lookupEAN(code);
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
			// Create or find the product
			const product = await api.products.create({
				ean: lookupResult.ean,
				name: lookupResult.name ?? get(_)('scan.unknownProduct'),
				brand: lookupResult.brand,
				image_url: lookupResult.image_url
			});
			// Create the transaction
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
</script>

<h1 class="mt-0">{$_('scan.title')}</h1>

<BarcodeScanner onScan={handleScan} />

{#if loading}
	<p class="text-center my-4">{$_('scan.lookingUp')}</p>
{/if}

{#if lookupError}
	<p class="text-center my-4 text-[#e74c3c]">{lookupError}</p>
{/if}

{#if lookupResult}
	<div class="bg-white rounded-xl p-6 mt-6 shadow-sm">
		{#if lookupResult.image_url}
			<img src={lookupResult.image_url} alt={lookupResult.name ?? $_('scan.product')} class="max-w-[120px] rounded-lg float-right ml-4" />
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
					<select bind:value={transactionType} class="px-2 py-2 border border-gray-300 rounded-md text-base">
						<option value="in">{$_('scan.addToInventory')}</option>
						<option value="out">{$_('scan.removeFromInventory')}</option>
					</select>
				</label>
				<label class="flex flex-col gap-1 text-sm text-[#555]">
					{$_('scan.quantity')}
					<input type="number" bind:value={quantity} min="0.01" step="0.01" class="px-2 py-2 border border-gray-300 rounded-md text-base" />
				</label>
				<label class="flex flex-col gap-1 text-sm text-[#555]">
					{$_('scan.unitPrice')}
					<input type="number" bind:value={unitPrice} min="0" step="0.01" placeholder={$_('scan.pricePlaceholder')} class="px-2 py-2 border border-gray-300 rounded-md text-base" />
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
			<p class="text-center my-4 text-[#27ae60] font-semibold">{$_('scan.addedSuccess')}</p>
		{/if}
	</div>
{/if}
