<script lang="ts">
    import { get } from "svelte/store";
    import { _ } from "svelte-i18n";
    import {
        Chart,
        DoughnutController,
        ArcElement,
        LineController,
        LineElement,
        PointElement,
        LinearScale,
        CategoryScale,
        Filler,
        Legend,
        Tooltip,
    } from "chart.js";
    Chart.register(
        DoughnutController,
        ArcElement,
        LineController,
        LineElement,
        PointElement,
        LinearScale,
        CategoryScale,
        Filler,
        Legend,
        Tooltip,
    );
    import { api, type SpendingByCategory, type TimeseriesPoint } from "$lib/api/client";

    const COLORS = [
        "#1a1a2e",
        "#e74c3c",
        "#3498db",
        "#2ecc71",
        "#f39c12",
        "#9b59b6",
        "#1abc9c",
        "#e67e22",
        "#34495e",
        "#e91e63",
    ];

    function toISODate(d: Date): string {
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

    let spending: SpendingByCategory[] = $state([]);
    let timeseries: TimeseriesPoint[] = $state([]);
    let loading = $state(true);
    let error = $state("");
    let since = $state(toISODate(monthStart));
    let until = $state(toISODate(now));

    async function load() {
        loading = true;
        error = "";
        try {
            [spending, timeseries] = await Promise.all([
                api.analytics.spending(since || undefined, until || undefined),
                api.analytics.timeseries(since || undefined, until || undefined),
            ]);
        } catch (e) {
            error = get(_)("analytics.failedToLoad", { values: { error: String(e) } });
        } finally {
            loading = false;
        }
    }

    $effect(() => {
        load();
    });

    // --- Derived values ---

    let totalSpent = $derived(spending.reduce((sum, s) => sum + s.total_spent, 0));
    let totalItems = $derived(spending.reduce((sum, s) => sum + s.item_count, 0));
    let spendingWithPrice = $derived(spending.filter((s) => s.total_spent > 0));

    let tsCategories = $derived([...new Set(timeseries.map((d) => d.category))]);
    let tsDates = $derived([...new Set(timeseries.map((d) => d.date))].sort());

    // --- Center-text plugin for doughnut charts ---

    function makeCenterTextPlugin(line1: string, line2: string) {
        return {
            id: "centerText",
            afterDraw(chart: Chart) {
                const {
                    ctx,
                    chartArea: { top, bottom, left, right },
                } = chart;
                const cx = (left + right) / 2;
                const cy = (top + bottom) / 2;
                ctx.save();
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillStyle = "#1a1a2e";
                ctx.font = "bold 20px sans-serif";
                ctx.fillText(line1, cx, cy - 8);
                ctx.fillStyle = "#999";
                ctx.font = "11px sans-serif";
                ctx.fillText(line2, cx, cy + 10);
                ctx.restore();
            },
        };
    }

    // --- Line chart dataset builder ---

    function buildLineDatasets(
        data: TimeseriesPoint[],
        dates: string[],
        categories: string[],
        getValue: (p: TimeseriesPoint) => number,
    ) {
        return categories.map((cat, i) => ({
            label: cat,
            data: dates.map((date) => {
                const pt = data.find((d) => d.date === date && d.category === cat);
                return pt ? getValue(pt) : 0;
            }),
            borderColor: COLORS[i % COLORS.length],
            backgroundColor: COLORS[i % COLORS.length] + "22",
            tension: 0.3,
            pointRadius: 3,
            fill: true,
        }));
    }

    // --- Canvas refs ---

    let itemsDonutCanvas: HTMLCanvasElement | undefined = $state();
    let spendingDonutCanvas: HTMLCanvasElement | undefined = $state();
    let itemsLineCanvas: HTMLCanvasElement | undefined = $state();
    let spendingLineCanvas: HTMLCanvasElement | undefined = $state();

    // Items donut
    $effect(() => {
        if (!itemsDonutCanvas || !spending.length) return;
        const chart = new Chart(itemsDonutCanvas, {
            type: "doughnut",
            data: {
                labels: spending.map((s) => s.category),
                datasets: [
                    {
                        data: spending.map((s) => s.item_count),
                        backgroundColor: spending.map((_, i) => COLORS[i % COLORS.length]),
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                cutout: "60%",
                responsive: true,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) =>
                                ` ${ctx.label}: ${ctx.raw} (${(((ctx.raw as number) / totalItems) * 100).toFixed(0)}%)`,
                        },
                    },
                },
            },
            plugins: [makeCenterTextPlugin(String(totalItems), get(_)("analytics.itemsLabel"))],
        });
        return () => chart.destroy();
    });

    // Spending donut
    $effect(() => {
        if (!spendingDonutCanvas || !spendingWithPrice.length) return;
        const chart = new Chart(spendingDonutCanvas, {
            type: "doughnut",
            data: {
                labels: spendingWithPrice.map((s) => s.category),
                datasets: [
                    {
                        data: spendingWithPrice.map((s) => s.total_spent),
                        backgroundColor: spendingWithPrice.map((_, i) => COLORS[i % COLORS.length]),
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                cutout: "60%",
                responsive: true,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) =>
                                ` ${ctx.label}: €${(ctx.raw as number).toFixed(2)} (${(((ctx.raw as number) / totalSpent) * 100).toFixed(0)}%)`,
                        },
                    },
                },
            },
            plugins: [
                makeCenterTextPlugin(`€${totalSpent.toFixed(0)}`, get(_)("analytics.totalSpent")),
            ],
        });
        return () => chart.destroy();
    });

    // Items over time
    $effect(() => {
        if (!itemsLineCanvas || !tsDates.length) return;
        const chart = new Chart(itemsLineCanvas, {
            type: "line",
            data: {
                labels: tsDates,
                datasets: buildLineDatasets(timeseries, tsDates, tsCategories, (p) => p.item_count),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
                },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
            },
        });
        return () => chart.destroy();
    });

    // Spending over time
    $effect(() => {
        if (!spendingLineCanvas || !tsDates.length) return;
        const chart = new Chart(spendingLineCanvas, {
            type: "line",
            data: {
                labels: tsDates,
                datasets: buildLineDatasets(
                    timeseries,
                    tsDates,
                    tsCategories,
                    (p) => p.total_spent,
                ),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (v) => `€${v}` },
                    },
                },
            },
        });
        return () => chart.destroy();
    });
</script>

<h1 class="mt-0">{$_("nav.analytics")}</h1>

<div class="flex gap-4 mb-6 flex-wrap">
    <label class="flex flex-col gap-1 text-[0.85rem] text-gray-500">
        {$_("analytics.from")}
        <input type="date" bind:value={since} class="p-2 border border-gray-300 rounded-md" />
    </label>
    <label class="flex flex-col gap-1 text-[0.85rem] text-gray-500">
        {$_("analytics.to")}
        <input type="date" bind:value={until} class="p-2 border border-gray-300 rounded-md" />
    </label>
</div>

{#if loading}
    <p>{$_("common.loading")}</p>
{:else if error}
    <p class="text-[#e74c3c]">{error}</p>
{:else if spending.length === 0}
    <p class="text-center text-gray-500 my-12">{$_("analytics.empty")}</p>
{:else}
    <!-- Donut charts -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
        <div class="bg-white rounded-xl p-6 shadow-sm">
            <h3 class="text-center text-sm font-semibold text-gray-600 mt-0 mb-4">
                {$_("analytics.itemsByCategory")}
            </h3>
            <div class="relative h-56">
                <canvas bind:this={itemsDonutCanvas}></canvas>
            </div>
        </div>

        <div class="bg-white rounded-xl p-6 shadow-sm">
            <h3 class="text-center text-sm font-semibold text-gray-600 mt-0 mb-4">
                {$_("analytics.spendingByCategory")}
            </h3>
            {#if spendingWithPrice.length === 0}
                <p class="text-center text-gray-400 text-sm my-8">{$_("analytics.noPrices")}</p>
            {:else}
                <div class="relative h-56">
                    <canvas bind:this={spendingDonutCanvas}></canvas>
                </div>
            {/if}
        </div>
    </div>

    <!-- Line charts -->
    {#if tsDates.length > 0}
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div class="bg-white rounded-xl p-6 shadow-sm">
                <h3 class="text-sm font-semibold text-gray-600 mt-0 mb-4">
                    {$_("analytics.itemsOverTime")}
                </h3>
                <div class="relative h-56">
                    <canvas bind:this={itemsLineCanvas}></canvas>
                </div>
            </div>
            <div class="bg-white rounded-xl p-6 shadow-sm">
                <h3 class="text-sm font-semibold text-gray-600 mt-0 mb-4">
                    {$_("analytics.spendingOverTime")}
                </h3>
                <div class="relative h-56">
                    <canvas bind:this={spendingLineCanvas}></canvas>
                </div>
            </div>
        </div>
    {/if}
{/if}
