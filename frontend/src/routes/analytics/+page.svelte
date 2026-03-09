<script lang="ts">
	import { get } from 'svelte/store';
	import { _ } from 'svelte-i18n';
	import { Chart } from 'chart.js/auto';
	import { api, type SpendingByCategory, type TimeseriesPoint } from '$lib/api/client';

	const COLORS = [
		'#1a1a2e',
		'#e74c3c',
		'#3498db',
		'#2ecc71',
		'#f39c12',
		'#9b59b6',
		'#1abc9c',
		'#e67e22',
		'#34495e',
		'#e91e63'
	];

	function toISODate(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	const now = new Date();
	const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

	let spending: SpendingByCategory[] = $state([]);
	let timeseries: TimeseriesPoint[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let since = $state(toISODate(monthStart));
	let until = $state(toISODate(now));

	async function load() {
		loading = true;
		error = '';
		try {
			[spending, timeseries] = await Promise.all([
				api.analytics.spending(since || undefined, until || undefined),
				api.analytics.timeseries(since || undefined, until || undefined)
			]);
		} catch (e) {
			error = get(_)('analytics.failedToLoad', { values: { error: String(e) } });
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	// --- Donut chart helpers ---

	const DONUT_OUTER = 80;
	const DONUT_INNER = 52;
	const CX = 100;
	const CY = 100;

	function polar(cx: number, cy: number, r: number, deg: number): [number, number] {
		const rad = ((deg - 90) * Math.PI) / 180;
		return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
	}

	function donutPath(start: number, end: number): string {
		if (end - start >= 359.99) {
			const [ox1, oy1] = polar(CX, CY, DONUT_OUTER, 0);
			const [ox2, oy2] = polar(CX, CY, DONUT_OUTER, 180);
			const [ix1, iy1] = polar(CX, CY, DONUT_INNER, 180);
			const [ix2, iy2] = polar(CX, CY, DONUT_INNER, 0);
			return [
				`M ${ox1} ${oy1}`,
				`A ${DONUT_OUTER} ${DONUT_OUTER} 0 1 1 ${ox2} ${oy2}`,
				`A ${DONUT_OUTER} ${DONUT_OUTER} 0 1 1 ${ox1} ${oy1}`,
				`M ${ix1} ${iy1}`,
				`A ${DONUT_INNER} ${DONUT_INNER} 0 1 0 ${ix2} ${iy2}`,
				`A ${DONUT_INNER} ${DONUT_INNER} 0 1 0 ${ix1} ${iy1} Z`
			].join(' ');
		}
		const [ox1, oy1] = polar(CX, CY, DONUT_OUTER, start);
		const [ox2, oy2] = polar(CX, CY, DONUT_OUTER, end);
		const [ix1, iy1] = polar(CX, CY, DONUT_INNER, end);
		const [ix2, iy2] = polar(CX, CY, DONUT_INNER, start);
		const large = end - start > 180 ? 1 : 0;
		return [
			`M ${ox1} ${oy1}`,
			`A ${DONUT_OUTER} ${DONUT_OUTER} 0 ${large} 1 ${ox2} ${oy2}`,
			`L ${ix1} ${iy1}`,
			`A ${DONUT_INNER} ${DONUT_INNER} 0 ${large} 0 ${ix2} ${iy2} Z`
		].join(' ');
	}

	type Slice = { label: string; value: number; color: string; start: number; end: number; pct: number };

	function computeSlices(data: SpendingByCategory[], getValue: (s: SpendingByCategory) => number): Slice[] {
		const total = data.reduce((sum, s) => sum + getValue(s), 0);
		if (total === 0) return [];
		const gap = data.length > 1 ? 1.5 : 0;
		let angle = 0;
		return data.map((item, i) => {
			const value = getValue(item);
			const span = (value / total) * 360;
			const slice: Slice = { label: item.category, value, color: COLORS[i % COLORS.length], start: angle, end: angle + span - gap, pct: value / total };
			angle += span;
			return slice;
		});
	}

	let totalSpent = $derived(spending.reduce((sum, s) => sum + s.total_spent, 0));
	let totalItems = $derived(spending.reduce((sum, s) => sum + s.item_count, 0));
	let itemSlices = $derived(computeSlices(spending, (s) => s.item_count));
	// Spending donut only shows categories that have priced items
	let spendingSlices = $derived(computeSlices(spending.filter((s) => s.total_spent > 0), (s) => s.total_spent));

	// --- Line chart helpers ---

	function buildLineDatasets(
		data: TimeseriesPoint[],
		dates: string[],
		categories: string[],
		getValue: (p: TimeseriesPoint) => number
	) {
		return categories.map((cat, i) => ({
			label: cat,
			data: dates.map((date) => {
				const pt = data.find((d) => d.date === date && d.category === cat);
				return pt ? getValue(pt) : 0;
			}),
			borderColor: COLORS[i % COLORS.length],
			backgroundColor: COLORS[i % COLORS.length] + '22',
			tension: 0.3,
			pointRadius: 3,
			fill: true
		}));
	}

	let tsCategories = $derived([...new Set(timeseries.map((d) => d.category))]);
	let tsDates = $derived([...new Set(timeseries.map((d) => d.date))].sort());

	// Canvas refs and Chart instances
	let itemsCanvas: HTMLCanvasElement | undefined = $state();
	let spendingCanvas: HTMLCanvasElement | undefined = $state();
	let itemsChart: Chart | undefined;
	let spendingChart: Chart | undefined;

	$effect(() => {
		if (!itemsCanvas || !tsDates.length) return;
		itemsChart?.destroy();
		itemsChart = new Chart(itemsCanvas, {
			type: 'line',
			data: {
				labels: tsDates,
				datasets: buildLineDatasets(timeseries, tsDates, tsCategories, (p) => p.item_count)
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
				scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
			}
		});
		return () => itemsChart?.destroy();
	});

	$effect(() => {
		if (!spendingCanvas || !tsDates.length) return;
		spendingChart?.destroy();
		spendingChart = new Chart(spendingCanvas, {
			type: 'line',
			data: {
				labels: tsDates,
				datasets: buildLineDatasets(timeseries, tsDates, tsCategories, (p) => p.total_spent)
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
				scales: {
					y: {
						beginAtZero: true,
						ticks: { callback: (v) => `€${v}` }
					}
				}
			}
		});
		return () => spendingChart?.destroy();
	});
</script>

<h1 class="mt-0">{$_('nav.analytics')}</h1>

<div class="flex gap-4 mb-6 flex-wrap">
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
	<!-- Donut charts -->
	<div class="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
		<!-- Items by category -->
		<div class="bg-white rounded-xl p-6 shadow-sm">
			<h3 class="text-center text-sm font-semibold text-gray-600 mt-0 mb-4">
				{$_('analytics.itemsByCategory')}
			</h3>
			<svg viewBox="0 0 200 200" class="w-full max-w-[200px] mx-auto block">
				{#each itemSlices as slice}
					<path d={donutPath(slice.start, slice.end)} fill={slice.color} />
				{/each}
				<text x="100" y="95" text-anchor="middle" font-size="24" font-weight="bold" fill="#1a1a2e">{totalItems}</text>
				<text x="100" y="113" text-anchor="middle" font-size="11" fill="#999">{$_('analytics.itemsLabel')}</text>
			</svg>
			<div class="mt-4 flex flex-col gap-1.5">
				{#each itemSlices as slice}
					<div class="flex items-center gap-2 text-sm">
						<span class="w-3 h-3 rounded-sm shrink-0" style="background:{slice.color}"></span>
						<span class="flex-1 truncate text-gray-700">{slice.label}</span>
						<span class="text-gray-400 tabular-nums">{slice.value} ({(slice.pct * 100).toFixed(0)}%)</span>
					</div>
				{/each}
			</div>
		</div>

		<!-- Spending by category -->
		<div class="bg-white rounded-xl p-6 shadow-sm">
			<h3 class="text-center text-sm font-semibold text-gray-600 mt-0 mb-4">
				{$_('analytics.spendingByCategory')}
			</h3>
			{#if spendingSlices.length === 0}
				<p class="text-center text-gray-400 text-sm my-8">{$_('analytics.noPrices')}</p>
			{:else}
				<svg viewBox="0 0 200 200" class="w-full max-w-[200px] mx-auto block">
					{#each spendingSlices as slice}
						<path d={donutPath(slice.start, slice.end)} fill={slice.color} />
					{/each}
					<text x="100" y="95" text-anchor="middle" font-size="18" font-weight="bold" fill="#1a1a2e">€{totalSpent.toFixed(0)}</text>
					<text x="100" y="113" text-anchor="middle" font-size="11" fill="#999">{$_('analytics.totalSpent')}</text>
				</svg>
				<div class="mt-4 flex flex-col gap-1.5">
					{#each spendingSlices as slice}
						<div class="flex items-center gap-2 text-sm">
							<span class="w-3 h-3 rounded-sm shrink-0" style="background:{slice.color}"></span>
							<span class="flex-1 truncate text-gray-700">{slice.label}</span>
							<span class="text-gray-400 tabular-nums">€{slice.value.toFixed(2)} ({(slice.pct * 100).toFixed(0)}%)</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<!-- Line charts (only shown when there are multiple data points) -->
	{#if tsDates.length > 0}
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
			<div class="bg-white rounded-xl p-6 shadow-sm">
				<h3 class="text-sm font-semibold text-gray-600 mt-0 mb-4">{$_('analytics.itemsOverTime')}</h3>
				<div class="relative h-56">
					<canvas bind:this={itemsCanvas}></canvas>
				</div>
			</div>
			<div class="bg-white rounded-xl p-6 shadow-sm">
				<h3 class="text-sm font-semibold text-gray-600 mt-0 mb-4">{$_('analytics.spendingOverTime')}</h3>
				<div class="relative h-56">
					<canvas bind:this={spendingCanvas}></canvas>
				</div>
			</div>
		</div>
	{/if}
{/if}
