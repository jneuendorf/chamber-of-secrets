<script lang="ts">
	import { api, type SpendingByCategory } from '$lib/api/client';

	let spending: SpendingByCategory[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let since = $state('');
	let until = $state('');

	async function load() {
		loading = true;
		try {
			spending = await api.analytics.spending(since || undefined, until || undefined);
		} catch (e) {
			error = `Failed to load analytics: ${e}`;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	let totalSpent = $derived(spending.reduce((sum, s) => sum + s.total_spent, 0));
	let maxSpent = $derived(Math.max(...spending.map((s) => s.total_spent), 1));
</script>

<h1>Analytics</h1>

<div class="filters">
	<label>
		From
		<input type="date" bind:value={since} onchange={load} />
	</label>
	<label>
		To
		<input type="date" bind:value={until} onchange={load} />
	</label>
</div>

{#if loading}
	<p>Loading...</p>
{:else if error}
	<p class="error">{error}</p>
{:else if spending.length === 0}
	<p class="empty">No spending data yet. Add items with prices to see analytics.</p>
{:else}
	<div class="summary">
		<div class="total-card">
			<span class="total-value">{totalSpent.toFixed(2)}</span>
			<span class="total-label">Total spent</span>
		</div>
	</div>

	<div class="chart">
		{#each spending as item (item.category)}
			<div class="bar-row">
				<span class="bar-label">{item.category}</span>
				<div class="bar-track">
					<div class="bar-fill" style="width: {(item.total_spent / maxSpent) * 100}%">
						{item.total_spent.toFixed(2)}
					</div>
				</div>
				<span class="bar-count">{item.item_count} items</span>
			</div>
		{/each}
	</div>
{/if}

<style>
	h1 {
		margin-top: 0;
	}

	.filters {
		display: flex;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.filters label {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		font-size: 0.85rem;
		color: #666;
	}

	.filters input {
		padding: 0.5rem;
		border: 1px solid #ddd;
		border-radius: 6px;
	}

	.error {
		color: #e74c3c;
	}

	.empty {
		text-align: center;
		color: #666;
		margin: 3rem 0;
	}

	.summary {
		margin-bottom: 2rem;
	}

	.total-card {
		background: white;
		border-radius: 12px;
		padding: 1.5rem;
		text-align: center;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.total-value {
		display: block;
		font-size: 2.5rem;
		font-weight: 700;
		color: #1a1a2e;
	}

	.total-value::before {
		content: '\20AC';
		font-size: 1.5rem;
		vertical-align: super;
	}

	.total-label {
		color: #666;
	}

	.chart {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.bar-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.bar-label {
		min-width: 100px;
		font-size: 0.9rem;
		text-align: right;
	}

	.bar-track {
		flex: 1;
		background: #eee;
		border-radius: 6px;
		overflow: hidden;
	}

	.bar-fill {
		background: #1a1a2e;
		color: white;
		padding: 0.4rem 0.75rem;
		border-radius: 6px;
		font-size: 0.85rem;
		white-space: nowrap;
		min-width: fit-content;
	}

	.bar-count {
		font-size: 0.8rem;
		color: #999;
		min-width: 60px;
	}
</style>
