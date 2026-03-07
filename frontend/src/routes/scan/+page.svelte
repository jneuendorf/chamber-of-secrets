<script lang="ts">
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
			lookupError = `No product found for barcode: ${code}`;
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
				name: lookupResult.name ?? 'Unknown Product',
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
			lookupError = `Failed to add: ${e}`;
		} finally {
			loading = false;
		}
	}
</script>

<h1>Scan Item</h1>

<BarcodeScanner onScan={handleScan} />

{#if loading}
	<p class="status">Looking up...</p>
{/if}

{#if lookupError}
	<p class="error">{lookupError}</p>
{/if}

{#if lookupResult}
	<div class="result-card">
		{#if lookupResult.image_url}
			<img src={lookupResult.image_url} alt={lookupResult.name ?? 'Product'} />
		{/if}
		<div class="info">
			<h2>{lookupResult.name ?? 'Unknown'}</h2>
			{#if lookupResult.brand}
				<p class="brand">{lookupResult.brand}</p>
			{/if}
			<p class="ean">EAN: {lookupResult.ean}</p>
		</div>

		{#if !added}
			<div class="transaction-form">
				<label>
					Type
					<select bind:value={transactionType}>
						<option value="in">Add to inventory</option>
						<option value="out">Remove from inventory</option>
					</select>
				</label>
				<label>
					Quantity
					<input type="number" bind:value={quantity} min="0.01" step="0.01" />
				</label>
				<label>
					Unit price (optional)
					<input type="number" bind:value={unitPrice} min="0" step="0.01" placeholder="e.g. 1.99" />
				</label>
				<button onclick={addToInventory} disabled={loading}>
					{transactionType === 'in' ? 'Add to Inventory' : 'Remove from Inventory'}
				</button>
			</div>
		{:else}
			<p class="success">Added to inventory!</p>
		{/if}
	</div>
{/if}

<style>
	h1 {
		margin-top: 0;
	}

	.status,
	.error,
	.success {
		text-align: center;
		margin: 1rem 0;
	}

	.error {
		color: #e74c3c;
	}

	.success {
		color: #27ae60;
		font-weight: 600;
	}

	.result-card {
		background: white;
		border-radius: 12px;
		padding: 1.5rem;
		margin-top: 1.5rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.result-card img {
		max-width: 120px;
		border-radius: 8px;
		float: right;
		margin-left: 1rem;
	}

	.info h2 {
		margin: 0 0 0.25rem;
	}

	.brand {
		color: #666;
		margin: 0;
	}

	.ean {
		font-family: monospace;
		color: #999;
		font-size: 0.85rem;
	}

	.transaction-form {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-top: 1rem;
		clear: both;
	}

	.transaction-form label {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		font-size: 0.9rem;
		color: #555;
	}

	.transaction-form input,
	.transaction-form select {
		padding: 0.5rem;
		border: 1px solid #ddd;
		border-radius: 6px;
		font-size: 1rem;
	}

	.transaction-form button {
		padding: 0.75rem;
		background: #1a1a2e;
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 1rem;
		cursor: pointer;
	}

	.transaction-form button:disabled {
		opacity: 0.5;
	}
</style>
