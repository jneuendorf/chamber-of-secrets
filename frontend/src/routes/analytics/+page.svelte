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
        type RestockOverviewResponse,
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
    let restockOverview: RestockOverviewResponse | null = $state(null);

    let restockOpen = $state(false);
    let restockSort: "urgency" | "missing" | "name" = $state("urgency");

    let loading = $state(true);
    let error = $state("");
    let since = $state(toISODate(monthStart));
    let until = $state(toISODate(now));

    async function load() {
        loading = true;
        error = "";
        try {
            [spending, timeseries, categories, restockOverview] = await Promise.all([
                api.analytics.spending(since || undefined, until || undefined),
                api.analytics.timeseries(since || undefined, until || undefined),
                api.categories.list(),
                api.analytics.restockOverview(),
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

    function fmtQty(value: number): string {
        return Number.isInteger(value) ? String(value) : value.toFixed(2);
    }

    function fmtMaybe(value: number | null): string {
        return value == null ? "—" : fmtQty(value);
    }

    let sortedRestockRows = $derived.by(() => {
        const rows = restockOverview?.rows ?? [];
        const copy = [...rows];

        if (restockSort === "missing") {
            copy.sort((a, b) =>
                b.missing_to_target === a.missing_to_target
                    ? Number(b.below_min) - Number(a.below_min)
                    : b.missing_to_target - a.missing_to_target,
            );
            return copy;
        }

        if (restockSort === "name") {
            copy.sort((a, b) => a.name.localeCompare(b.name));
            return copy;
        }

        copy.sort((a, b) =>
            Number(b.below_min) === Number(a.below_min)
                ? b.missing_to_target - a.missing_to_target
                : Number(b.below_min) - Number(a.below_min),
        );
        return copy;
    });

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

<div class="filters">
    <label class="date-field">
        {$_("analytics.from")}
        <input type="date" bind:value={since} />
    </label>
    <label class="date-field">
        {$_("analytics.to")}
        <input type="date" bind:value={until} />
    </label>
</div>

<div class="restock-summary">
    <div class="summary-text">
        Total units to buy:
        <strong>{fmtQty(restockOverview?.total_missing_quantity ?? 0)}</strong>
    </div>
    <button class="restock-btn" onclick={() => (restockOpen = true)}>Restock overview</button>
</div>

{#if loading}
    <p>{$_("common.loading")}</p>
{:else if error}
    <p class="error">{error}</p>
{:else if spending.length === 0}
    <p class="empty">{$_("analytics.empty")}</p>
{:else}
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section class="pane">
            <h2>Items / Categories</h2>
            <div class="stack">
                <div class="card">
                    <h3>Child Categories — {$_("analytics.itemsByCategory")}</h3>
                    <div class="chart-wrap">
                        <canvas bind:this={childItemsDonutCanvas}></canvas>
                    </div>
                </div>

                <div class="card">
                    <h3>Parent Categories — {$_("analytics.itemsByCategory")}</h3>
                    <div class="chart-wrap">
                        <canvas bind:this={parentItemsDonutCanvas}></canvas>
                    </div>
                </div>

                {#if childTsDates.length > 0}
                    <div class="card">
                        <h3>Child Categories — {$_("analytics.itemsOverTime")}</h3>
                        <div class="chart-wrap">
                            <canvas bind:this={childItemsLineCanvas}></canvas>
                        </div>
                    </div>
                {/if}

                {#if parentTsDates.length > 0}
                    <div class="card">
                        <h3>Parent Categories — {$_("analytics.itemsOverTime")}</h3>
                        <div class="chart-wrap">
                            <canvas bind:this={parentItemsLineCanvas}></canvas>
                        </div>
                    </div>
                {/if}
            </div>
        </section>

        <section class="pane">
            <h2>Spendings</h2>
            <div class="stack">
                <div class="card">
                    <h3>{$_("analytics.spendingByCategory")}</h3>
                    {#if childSpendingWithPrice.length === 0}
                        <p class="muted">{$_("analytics.noPrices")}</p>
                    {:else}
                        <div class="chart-wrap">
                            <canvas bind:this={spendingDonutCanvas}></canvas>
                        </div>
                    {/if}
                </div>

                {#if childTsDates.length > 0}
                    <div class="card">
                        <h3>{$_("analytics.spendingOverTime")}</h3>
                        <div class="chart-wrap">
                            <canvas bind:this={spendingLineCanvas}></canvas>
                        </div>
                    </div>
                {/if}

                <div class="card">
                    <h3>Parent Categories — {$_("analytics.spendingByCategory")}</h3>
                    {#if parentSpendingWithPrice.length === 0}
                        <p class="muted">{$_("analytics.noPrices")}</p>
                    {:else}
                        <ul class="parent-list">
                            {#each parentSpendingWithPrice as row}
                                <li>
                                    <span>{row.category}</span>
                                    <strong>€{row.total_spent.toFixed(2)}</strong>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </div>
            </div>
        </section>
    </div>
{/if}

{#if restockOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="restock-backdrop" onclick={() => (restockOpen = false)}>
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
        <div class="restock-modal" onclick={(e) => e.stopPropagation()}>
            <div class="restock-head">
                <h2>Restock overview</h2>
                <button class="icon-btn" onclick={() => (restockOpen = false)}>✕</button>
            </div>

            <div class="kpis">
                <div class="kpi">
                    <div class="kpi-label">Total units to buy</div>
                    <div class="kpi-value">
                        {fmtQty(restockOverview?.total_missing_quantity ?? 0)}
                    </div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Products needing restock</div>
                    <div class="kpi-value">
                        {restockOverview?.total_products_needing_restock ?? 0}
                    </div>
                </div>
            </div>

            <div class="controls">
                <label>
                    Sort by
                    <select bind:value={restockSort}>
                        <option value="urgency">Urgency</option>
                        <option value="missing">Missing quantity</option>
                        <option value="name">Name</option>
                    </select>
                </label>
            </div>

            <div class="restock-layout">
                <section class="panel">
                    <h3>Products needing restock</h3>
                    {#if !restockOverview || sortedRestockRows.length === 0}
                        <p class="muted">No restock-needed products right now.</p>
                    {:else}
                        <div class="table-wrap">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Product</th>
                                        <th>Category</th>
                                        <th>Stock</th>
                                        <th>Target</th>
                                        <th>Min</th>
                                        <th>Missing</th>
                                        <th>Urgent</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {#each sortedRestockRows as row (row.id)}
                                        <tr>
                                            <td>{row.name}</td>
                                            <td>{row.category_name}</td>
                                            <td>{fmtQty(row.current_stock)}</td>
                                            <td>{fmtMaybe(row.effective_target)}</td>
                                            <td>{fmtMaybe(row.effective_min)}</td>
                                            <td>{fmtQty(row.missing_to_target)}</td>
                                            <td>{row.below_min ? "⚠️" : "—"}</td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {/if}
                </section>

                <section class="panel">
                    <h3>Child category totals</h3>
                    <ul class="totals">
                        {#each restockOverview?.by_child_category ?? [] as g}
                            <li>
                                <span>{g.category_name}</span>
                                <strong
                                    >{fmtQty(g.total_missing_to_target)} · {g.affected_products}</strong
                                >
                            </li>
                        {/each}
                    </ul>

                    <h3 class="mt">Parent category totals</h3>
                    <ul class="totals">
                        {#each restockOverview?.by_parent_category ?? [] as g}
                            <li>
                                <span>{g.category_name}</span>
                                <strong
                                    >{fmtQty(g.total_missing_to_target)} · {g.affected_products}</strong
                                >
                            </li>
                        {/each}
                    </ul>
                </section>
            </div>
        </div>
    </div>
{/if}

<style>
    .filters {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 1.25rem;
    }

    .date-field {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        font-size: 0.85rem;
        color: #6b7280;
    }

    .date-field input {
        padding: 0.5rem;
        border: 1px solid #d1d5db;
        border-radius: 0.4rem;
    }

    .restock-summary {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        flex-wrap: wrap;
        margin-bottom: 1.5rem;
    }

    .restock-btn {
        border: 1px solid #d1d5db;
        background: #fff;
        color: #1a1a2e;
        border-radius: 0.5rem;
        padding: 0.45rem 0.85rem;
        font-weight: 600;
        cursor: pointer;
    }

    .summary-text {
        color: #4b5563;
        font-size: 0.9rem;
    }

    .error {
        color: #e74c3c;
    }

    .empty {
        text-align: center;
        color: #6b7280;
        margin: 3rem 0;
    }

    .pane {
        background: #fafafa;
        border: 1px solid #e5e7eb;
        border-radius: 1rem;
        padding: 1rem 1.25rem;
    }

    .pane h2 {
        margin: 0 0 1rem;
        font-size: 1rem;
        color: #1a1a2e;
    }

    .stack {
        display: grid;
        gap: 1rem;
    }

    .card {
        background: #fff;
        border-radius: 0.8rem;
        padding: 1rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }

    .card h3 {
        margin: 0 0 0.8rem;
        font-size: 0.9rem;
        color: #4b5563;
    }

    .chart-wrap {
        position: relative;
        height: 14rem;
    }

    .parent-list {
        list-style: none;
        margin: 0;
        padding: 0;
    }

    .parent-list li {
        display: flex;
        justify-content: space-between;
        padding: 0.45rem 0;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.9rem;
    }

    .muted {
        color: #9ca3af;
        font-size: 0.9rem;
        margin: 1rem 0;
    }

    .restock-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        z-index: 9998;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
    }

    .restock-modal {
        width: min(1200px, 100%);
        max-height: calc(100vh - 2rem);
        overflow: auto;
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 0.9rem;
        padding: 1rem;
    }

    .restock-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.75rem;
    }

    .restock-head h2 {
        margin: 0;
        font-size: 1.1rem;
        color: #1a1a2e;
    }

    .icon-btn {
        border: 0;
        background: #f3f4f6;
        width: 2rem;
        height: 2rem;
        border-radius: 0.45rem;
        cursor: pointer;
    }

    .kpis {
        display: grid;
        grid-template-columns: repeat(2, minmax(180px, 1fr));
        gap: 0.75rem;
        margin-bottom: 0.75rem;
    }

    .kpi {
        border: 1px solid #e5e7eb;
        border-radius: 0.6rem;
        padding: 0.7rem;
        background: #fafafa;
    }

    .kpi-label {
        font-size: 0.78rem;
        color: #6b7280;
    }

    .kpi-value {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-top: 0.1rem;
    }

    .controls {
        margin-bottom: 0.8rem;
    }

    .controls label {
        display: inline-flex;
        gap: 0.5rem;
        align-items: center;
        font-size: 0.85rem;
        color: #4b5563;
    }

    .controls select {
        border: 1px solid #d1d5db;
        border-radius: 0.5rem;
        padding: 0.35rem 0.45rem;
    }

    .restock-layout {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 0.75rem;
    }

    .panel {
        border: 1px solid #e5e7eb;
        border-radius: 0.7rem;
        padding: 0.75rem;
    }

    .panel h3 {
        margin: 0 0 0.55rem;
        font-size: 0.95rem;
        color: #374151;
    }

    .mt {
        margin-top: 1rem !important;
    }

    .table-wrap {
        overflow: auto;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.84rem;
    }

    th,
    td {
        text-align: left;
        padding: 0.45rem;
        border-bottom: 1px solid #f3f4f6;
        white-space: nowrap;
    }

    th {
        background: #fafafa;
        color: #6b7280;
        font-weight: 600;
        position: sticky;
        top: 0;
    }

    .totals {
        list-style: none;
        margin: 0;
        padding: 0;
    }

    .totals li {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        padding: 0.38rem 0;
        border-bottom: 1px solid #f3f4f6;
        font-size: 0.85rem;
    }

    @media (max-width: 900px) {
        .restock-layout {
            grid-template-columns: 1fr;
        }
    }
</style>
