<script lang="ts">
	import { get } from 'svelte/store';
	import { _ } from 'svelte-i18n';
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
			error = get(_)('analytics.failedToLoad', { values: { error: String(e) } });
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

<h1 class="mt-0">{$_('nav.analytics')}</h1>

<div class="flex gap-4 mb-6">
	<label class="flex flex-col gap-1 text-[0.85rem] text-gray-500">
		{$_('analytics.from')}
		<input type="date" bind:value={since} onchange={load} class="p-2 border border-gray-300 rounded-md" />
	</label>
	<label class="flex flex-col gap-1 text-[0.85rem] text-gray-500">
		{$_('analytics.to')}
		<input type="date" bind:value={until} onchange={load} class="p-2 border border-gray-300 rounded-md" />
	</label>
</div>

{#if loading}
	<p>{$_('common.loading')}</p>
{:else if error}
	<p class="text-[#e74c3c]">{error}</p>
{:else if spending.length === 0}
	<p class="text-center text-gray-500 my-12">{$_('analytics.empty')}</p>
{:else}
	<div class="mb-8">
		<div class="bg-white rounded-xl p-6 text-center shadow-sm">
			<span class="total-value">{totalSpent.toFixed(2)}</span>
			<span class="text-gray-500">{$_('analytics.totalSpent')}</span>
		</div>
	</div>

	<div class="flex flex-col gap-3">
		{#each spending as item (item.category)}
			<div class="flex items-center gap-3">
				<span class="min-w-[100px] text-[0.9rem] text-right">{item.category}</span>
				<div class="flex-1 bg-[#eee] rounded-md overflow-hidden">
					<div class="bg-[#1a1a2e] text-white px-3 py-[0.4rem] rounded-md text-[0.85rem] whitespace-nowrap min-w-fit" style="width: {(item.total_spent / maxSpent) * 100}%">
						{item.total_spent.toFixed(2)}
					</div>
				</div>
				<span class="text-xs text-gray-400 min-w-[60px]">{$_('analytics.items', { values: { count: item.item_count } })}</span>
			</div>
		{/each}
	</div>
{/if}

<style>
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
</style>
