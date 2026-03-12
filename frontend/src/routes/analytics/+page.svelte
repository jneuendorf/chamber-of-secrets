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
    import {
        api,
        type Category,
        type SpendingByCategory,
        type TimeseriesPoint,
    } from "$lib/api/client";

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

    const UNCATEGORIZED = "Uncategorized";
    const NO_PARENT = "No parent";

    function toISODate(d: Date): string {
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

    let spending: SpendingByCategory[] = $state([]);
    let timeseries: TimeseriesPoint[] = $state([]);
    let categories: Category[] = $state([]);
    let loading = $state(true);
    let error = $state("");
    let since = $state(toISODate(monthStart));
    let until = $state(toISODate(now));

    async function load() {
        loading = true;
        error = "";
        try {
            [spending, timeseries, categories] = await Promise.all([
                api.analytics.spending(since || undefined, until || undefined),
                api.analytics.timeseries(since || undefined, until || undefined),
                api.categories.list(),
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

    type Agg = { category: string; total_spent: number; item_count: number };

    let categoryByName = $derived(new Map(categories.map((c) => [c.name, c])));
    let categoryById = $derived(new Map(categories.map((c) => [c.id, c])));

    function toParentLabel(childName: string): string {
        if (childName === UNCATEGORIZED) return UNCATEGORIZED;
        const child = categoryByName.get(childName);
        if (!child) return childName;
        if (child.parent_id == null) return NO_PARENT;
        const parent = categoryById.get(child.parent_id);
        return parent?.name ?? NO_PARENT;
    }

    function aggregateToParents(rows: SpendingByCategory[]): Agg[] {
        const m = new Map<string, Agg>();
        for (const row of rows) {
            const label = toParentLabel(row.category);
            const prev = m.get(label) ?? { category: label, total_spent: 0, item_count: 0 };
            prev.total_spent += row.total_spent;
            prev.item_count += row.item_count;
            m.set(label, prev);
        }
        return [...m.values()].sort((a, b) => b.total_spent - a.total_spent);
    }

    function aggregateTimeseriesToParents(rows: TimeseriesPoint[]): TimeseriesPoint[] {
        const m = new Map<string, TimeseriesPoint>();
        for (const row of rows) {
            const parentCategory = toParentLabel(row.category);
            const key = `${row.date}__${parentCategory}`;
            const prev = m.get(key) ?? {
                date: row.date,
                category: parentCategory,
                item_count: 0,
                total_spent: 0,
            };
            prev.item_count += row.item_count;
            prev.total_spent += row.total_spent;
            m.set(key, prev);
        }
        return [...m.values()].sort((a, b) =>
            a.date === b.date ? a.category.localeCompare(b.category) : a.date.localeCompare(b.date),
        );
    }

    let parentSpending = $derived(aggregateToParents(spending));
    let parentTimeseries = $derived(aggregateTimeseriesToParents(timeseries));

    let totalSpent = $derived(spending.reduce((sum, s) => sum + s.total_spent, 0));
    let totalItems = $derived(spending.reduce((sum, s) => sum + s.item_count, 0));

    let childSpendingWithPrice = $derived(spending.filter((s) => s.total_spent > 0));
    let parentSpendingWithPrice = $derived(parentSpending.filter((s) => s.total_spent > 0));

    let childTsCategories = $derived([...new Set(timeseries.map((d) => d.category))]);
    let childTsDates = $derived([...new Set(timeseries.map((d) => d.date))].sort());

    let parentTsCategories = $derived([...new Set(parentTimeseries.map((d) => d.category))]);
    let parentTsDates = $derived([...new Set(parentTimeseries.map((d) => d.date))].sort());

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

    function buildLineDatasets(
        data: TimeseriesPoint[],
        dates: string[],
        categoriesForLines: string[],
        getValue: (p: TimeseriesPoint) => number,
    ) {
        return categoriesForLines.map((cat, i) => ({
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

    let childItemsDonutCanvas: HTMLCanvasElement | undefined = $state();
    let parentItemsDonutCanvas: HTMLCanvasElement | undefined = $state();
    let spendingDonutCanvas: HTMLCanvasElement | undefined = $state();
    let childItemsLineCanvas: HTMLCanvasElement | undefined = $state();
    let parentItemsLineCanvas: HTMLCanvasElement | undefined = $state();
    let spendingLineCanvas: HTMLCanvasElement | undefined = $state();

    $effect(() => {
        if (!childItemsDonutCanvas || !spending.length) return;
        const chart = new Chart(childItemsDonutCanvas, {
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

    $effect(() => {
        if (!parentItemsDonutCanvas || !parentSpending.length) return;
        const parentTotalItems = parentSpending.reduce((sum, s) => sum + s.item_count, 0);
        const chart = new Chart(parentItemsDonutCanvas, {
            type: "doughnut",
            data: {
                labels: parentSpending.map((s) => s.category),
                datasets: [
                    {
                        data: parentSpending.map((s) => s.item_count),
                        backgroundColor: parentSpending.map((_, i) => COLORS[i % COLORS.length]),
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
                                ` ${ctx.label}: ${ctx.raw} (${(((ctx.raw as number) / parentTotalItems) * 100).toFixed(0)}%)`,
                        },
                    },
                },
            },
            plugins: [
                makeCenterTextPlugin(String(parentTotalItems), get(_)("analytics.itemsLabel")),
            ],
        });
        return () => chart.destroy();
    });

    $effect(() => {
        if (!spendingDonutCanvas || !childSpendingWithPrice.length) return;
        const chart = new Chart(spendingDonutCanvas, {
            type: "doughnut",
            data: {
                labels: childSpendingWithPrice.map((s) => s.category),
                datasets: [
                    {
                        data: childSpendingWithPrice.map((s) => s.total_spent),
                        backgroundColor: childSpendingWithPrice.map(
                            (_, i) => COLORS[i % COLORS.length],
                        ),
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

    $effect(() => {
        if (!childItemsLineCanvas || !childTsDates.length) return;
        const chart = new Chart(childItemsLineCanvas, {
            type: "line",
            data: {
                labels: childTsDates,
                datasets: buildLineDatasets(
                    timeseries,
                    childTsDates,
                    childTsCategories,
                    (p) => p.item_count,
                ),
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

    $effect(() => {
        if (!parentItemsLineCanvas || !parentTsDates.length) return;
        const chart = new Chart(parentItemsLineCanvas, {
            type: "line",
            data: {
                labels: parentTsDates,
                datasets: buildLineDatasets(
                    parentTimeseries,
                    parentTsDates,
                    parentTsCategories,
                    (p) => p.item_count,
                ),
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

    $effect(() => {
        if (!spendingLineCanvas || !childTsDates.length) return;
        const chart = new Chart(spendingLineCanvas, {
            type: "line",
            data: {
                labels: childTsDates,
                datasets: buildLineDatasets(
                    timeseries,
                    childTsDates,
                    childTsCategories,
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
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Pane: Categories -->
        <section class="bg-[#fafafa] rounded-2xl p-4 sm:p-6 border border-gray-200">
            <h2 class="text-base font-semibold text-[#1a1a2e] mt-0 mb-4">Items / Categories</h2>

            <div class="grid grid-cols-1 gap-6">
                <div class="bg-white rounded-xl p-6 shadow-sm">
                    <h3 class="text-center text-sm font-semibold text-gray-600 mt-0 mb-4">
                        Child Categories — {$_("analytics.itemsByCategory")}
                    </h3>
                    <div class="relative h-56">
                        <canvas bind:this={childItemsDonutCanvas}></canvas>
                    </div>
                </div>

                <div class="bg-white rounded-xl p-6 shadow-sm">
                    <h3 class="text-center text-sm font-semibold text-gray-600 mt-0 mb-4">
                        Parent Categories — {$_("analytics.itemsByCategory")}
                    </h3>
                    <div class="relative h-56">
                        <canvas bind:this={parentItemsDonutCanvas}></canvas>
                    </div>
                </div>

                {#if childTsDates.length > 0}
                    <div class="bg-white rounded-xl p-6 shadow-sm">
                        <h3 class="text-sm font-semibold text-gray-600 mt-0 mb-4">
                            Child Categories — {$_("analytics.itemsOverTime")}
                        </h3>
                        <div class="relative h-56">
                            <canvas bind:this={childItemsLineCanvas}></canvas>
                        </div>
                    </div>
                {/if}

                {#if parentTsDates.length > 0}
                    <div class="bg-white rounded-xl p-6 shadow-sm">
                        <h3 class="text-sm font-semibold text-gray-600 mt-0 mb-4">
                            Parent Categories — {$_("analytics.itemsOverTime")}
                        </h3>
                        <div class="relative h-56">
                            <canvas bind:this={parentItemsLineCanvas}></canvas>
                        </div>
                    </div>
                {/if}
            </div>
        </section>

        <!-- Pane: Spendings -->
        <section class="bg-[#fafafa] rounded-2xl p-4 sm:p-6 border border-gray-200">
            <h2 class="text-base font-semibold text-[#1a1a2e] mt-0 mb-4">Spendings</h2>

            <div class="grid grid-cols-1 gap-6">
                <div class="bg-white rounded-xl p-6 shadow-sm">
                    <h3 class="text-center text-sm font-semibold text-gray-600 mt-0 mb-4">
                        {$_("analytics.spendingByCategory")}
                    </h3>
                    {#if childSpendingWithPrice.length === 0}
                        <p class="text-center text-gray-400 text-sm my-8">
                            {$_("analytics.noPrices")}
                        </p>
                    {:else}
                        <div class="relative h-56">
                            <canvas bind:this={spendingDonutCanvas}></canvas>
                        </div>
                    {/if}
                </div>

                {#if childTsDates.length > 0}
                    <div class="bg-white rounded-xl p-6 shadow-sm">
                        <h3 class="text-sm font-semibold text-gray-600 mt-0 mb-4">
                            {$_("analytics.spendingOverTime")}
                        </h3>
                        <div class="relative h-56">
                            <canvas bind:this={spendingLineCanvas}></canvas>
                        </div>
                    </div>
                {/if}

                <div class="bg-white rounded-xl p-6 shadow-sm">
                    <h3 class="text-center text-sm font-semibold text-gray-600 mt-0 mb-4">
                        Parent Categories — {$_("analytics.spendingByCategory")}
                    </h3>
                    {#if parentSpendingWithPrice.length === 0}
                        <p class="text-center text-gray-400 text-sm my-8">
                            {$_("analytics.noPrices")}
                        </p>
                    {:else}
                        <ul class="m-0 p-0 list-none divide-y divide-gray-100">
                            {#each parentSpendingWithPrice as row}
                                <li class="py-2 flex items-center justify-between text-sm">
                                    <span class="text-gray-700">{row.category}</span>
                                    <span class="font-medium text-[#1a1a2e]"
                                        >€{row.total_spent.toFixed(2)}</span
                                    >
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </div>
            </div>
        </section>
    </div>
{/if}
