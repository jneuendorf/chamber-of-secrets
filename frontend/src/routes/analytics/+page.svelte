<script lang="ts">
import {
    CategoryScale,
    Chart,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PointElement,
    Tooltip,
} from 'chart.js'
import { get } from 'svelte/store'
import { _ } from 'svelte-i18n'

import {
    ApiError,
    api,
    type Category,
    type RestockOverviewResponse,
    type SpendingByCategory,
    type TimeseriesPoint,
} from '$lib/api/client'
import DrillDownDonut from '$lib/components/DrillDownDonut.svelte'
import Modal from '$lib/components/Modal.svelte'
import {
    aggregateTimeseriesToParents,
    aggregateToParents,
    buildCategoryMaps,
    getItemSlices as getItemSlicesUtil,
    getSpendingSlices as getSpendingSlicesUtil,
    UNCATEGORIZED,
} from '$lib/utils/analytics'

Chart.register(
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Filler,
    Legend,
    Tooltip,
)

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
    '#e91e63',
]


function toISODate(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const now = new Date()
const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)

let spending: SpendingByCategory[] = $state([])
let timeseries: TimeseriesPoint[] = $state([])
let categories: Category[] = $state([])
let restockOverview: RestockOverviewResponse | null = $state(null)

let restockOpen = $state(false)
let restockSort: 'urgency' | 'missing' | 'name' = $state('urgency')

let loading = $state(true)
let error = $state('')
let since = $state(toISODate(monthStart))
let until = $state(toISODate(now))

async function load() {
    loading = true
    error = ''
    try {
        ;[spending, timeseries, categories, restockOverview] = await Promise.all([
            api.analytics.spending(since || undefined, until || undefined),
            api.analytics.timeseries(since || undefined, until || undefined),
            api.categories.list(),
            api.analytics.restockOverview(),
        ])
    } catch (e) {
        const detail = e instanceof ApiError ? e.detail : String(e)
        error = get(_)('analytics.failedToLoad', { values: { error: detail } })
    } finally {
        loading = false
    }
}

$effect(() => {
    load()
})

function fmtQty(value: number): string {
    return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

function fmtMaybe(value: number | null): string {
    return value == null ? '—' : fmtQty(value)
}

let sortedRestockRows = $derived.by(() => {
    const rows = restockOverview?.rows ?? []
    const copy = [...rows]

    if (restockSort === 'missing') {
        copy.sort((a, b) =>
            b.missing_to_target === a.missing_to_target
                ? Number(b.below_min) - Number(a.below_min)
                : b.missing_to_target - a.missing_to_target,
        )
        return copy
    }

    if (restockSort === 'name') {
        copy.sort((a, b) => a.name.localeCompare(b.name))
        return copy
    }

    copy.sort((a, b) =>
        Number(b.below_min) === Number(a.below_min)
            ? b.missing_to_target - a.missing_to_target
            : Number(b.below_min) - Number(a.below_min),
    )
    return copy
})

function displayCategory(name: string): string {
    return name === UNCATEGORIZED ? get(_)('analytics.uncategorized') : name
}

let catMaps = $derived(buildCategoryMaps(categories))

let parentSpending = $derived(aggregateToParents(spending, catMaps.byName, catMaps.byId))
let parentTimeseries = $derived(aggregateTimeseriesToParents(timeseries, catMaps.byName, catMaps.byId))

let parentSpendingWithPrice = $derived(parentSpending.filter((s) => s.total_spent > 0))

let childTsCategories = $derived([...new Set(timeseries.map((d) => d.category))])
let childTsDates = $derived([...new Set(timeseries.map((d) => d.date))].sort())

let parentTsCategories = $derived([...new Set(parentTimeseries.map((d) => d.category))])
let parentTsDates = $derived([...new Set(parentTimeseries.map((d) => d.date))].sort())

function getItemSlices(parentKey: string | null) {
    return getItemSlicesUtil(parentKey, spending, parentSpending, catMaps.byName, catMaps.byId, displayCategory)
}

function getSpendingSlices(parentKey: string | null) {
    return getSpendingSlicesUtil(parentKey, spending, parentSpendingWithPrice, catMaps.byName, catMaps.byId, displayCategory)
}

function buildLineDatasets(
    data: TimeseriesPoint[],
    dates: string[],
    categoriesForLines: string[],
    getValue: (p: TimeseriesPoint) => number,
) {
    return categoriesForLines.map((cat, i) => ({
        label: displayCategory(cat),
        data: dates.map((date) => {
            const pt = data.find((d) => d.date === date && d.category === cat)
            return pt ? getValue(pt) : 0
        }),
        borderColor: COLORS[i % COLORS.length],
        backgroundColor: `${COLORS[i % COLORS.length]}22`,
        tension: 0.3,
        pointRadius: 3,
        fill: true,
    }))
}

let childItemsLineCanvas: HTMLCanvasElement | undefined = $state()
let parentItemsLineCanvas: HTMLCanvasElement | undefined = $state()
let spendingLineCanvas: HTMLCanvasElement | undefined = $state()

$effect(() => {
    if (!childItemsLineCanvas || !childTsDates.length) { return }
    const chart = new Chart(childItemsLineCanvas, {
        type: 'line',
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
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { size: 11 }, color: '#e5e7eb' },
                },
            },
            scales: {
                x: {
                    ticks: { color: '#d1d5db' },
                    grid: { color: 'rgba(209, 213, 219, 0.15)' },
                },
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, color: '#d1d5db' },
                    grid: { color: 'rgba(209, 213, 219, 0.15)' },
                },
            },
        },
    })
    return () => chart.destroy()
})

$effect(() => {
    if (!parentItemsLineCanvas || !parentTsDates.length) { return }
    const chart = new Chart(parentItemsLineCanvas, {
        type: 'line',
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
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { size: 11 }, color: '#e5e7eb' },
                },
            },
            scales: {
                x: {
                    ticks: { color: '#d1d5db' },
                    grid: { color: 'rgba(209, 213, 219, 0.15)' },
                },
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, color: '#d1d5db' },
                    grid: { color: 'rgba(209, 213, 219, 0.15)' },
                },
            },
        },
    })
    return () => chart.destroy()
})

$effect(() => {
    if (!spendingLineCanvas || !childTsDates.length) { return }
    const chart = new Chart(spendingLineCanvas, {
        type: 'line',
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
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { size: 11 }, color: '#e5e7eb' },
                },
            },
            scales: {
                x: {
                    ticks: { color: '#d1d5db' },
                    grid: { color: 'rgba(209, 213, 219, 0.15)' },
                },
                y: {
                    beginAtZero: true,
                    ticks: { callback: (v) => `€${v}`, color: '#d1d5db' },
                    grid: { color: 'rgba(209, 213, 219, 0.15)' },
                },
            },
        },
    })
    return () => chart.destroy()
})
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
        {$_("analytics.totalUnitsToBuy")}:
        <strong>{fmtQty(restockOverview?.total_missing_quantity ?? 0)}</strong>
    </div>
    <button type="button" class="restock-btn" onclick={() => (restockOpen = true)}>{$_("analytics.restockOverview")}</button>
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
            <h2>{$_("analytics.sectionItems")}</h2>
            <div class="stack">
                <DrillDownDonut
                    title={$_("analytics.itemsByCategory")}
                    getSlices={getItemSlices}
                    formatTotal={(t) => String(t)}
                    centerLabel={$_("analytics.itemsLabel")}
                    formatTooltip={(label, value, pct) =>
                        ` ${label}: ${value} (${pct}%)`}
                />

                {#if childTsDates.length > 0}
                    <div class="card">
                        <h3>{$_("analytics.childCategories")} — {$_("analytics.itemsOverTime")}</h3>
                        <div class="chart-wrap">
                            <canvas bind:this={childItemsLineCanvas}></canvas>
                        </div>
                    </div>
                {/if}

                {#if parentTsDates.length > 0}
                    <div class="card">
                        <h3>{$_("analytics.parentCategories")} — {$_("analytics.itemsOverTime")}</h3>
                        <div class="chart-wrap">
                            <canvas bind:this={parentItemsLineCanvas}></canvas>
                        </div>
                    </div>
                {/if}
            </div>
        </section>

        <section class="pane">
            <h2>{$_("analytics.sectionSpending")}</h2>
            <div class="stack">
                <DrillDownDonut
                    title={$_("analytics.spendingByCategory")}
                    getSlices={getSpendingSlices}
                    formatTotal={(t) => `€${t.toFixed(0)}`}
                    centerLabel={$_("analytics.totalSpent")}
                    formatTooltip={(label, value, pct) =>
                        ` ${label}: €${value.toFixed(2)} (${pct}%)`}
                />

                {#if childTsDates.length > 0}
                    <div class="card">
                        <h3>{$_("analytics.spendingOverTime")}</h3>
                        <div class="chart-wrap">
                            <canvas bind:this={spendingLineCanvas}></canvas>
                        </div>
                    </div>
                {/if}
            </div>
        </section>
    </div>
{/if}

<Modal
    open={restockOpen}
    title={$_("analytics.restockOverview")}
    onclose={() => (restockOpen = false)}
    width="min(1200px, 100%)"
>
    <div class="kpis">
        <div class="kpi">
            <div class="kpi-label">{$_("analytics.totalUnitsToBuy")}</div>
            <div class="kpi-value">
                {fmtQty(restockOverview?.total_missing_quantity ?? 0)}
            </div>
        </div>
        <div class="kpi">
            <div class="kpi-label">{$_("analytics.productsNeedingRestock")}</div>
            <div class="kpi-value">
                {restockOverview?.total_products_needing_restock ?? 0}
            </div>
        </div>
    </div>

    <div class="controls">
        <label>
            {$_("analytics.sortBy")}
            <select bind:value={restockSort}>
                <option value="urgency">{$_("analytics.sortUrgency")}</option>
                <option value="missing">{$_("analytics.sortMissing")}</option>
                <option value="name">{$_("analytics.sortName")}</option>
            </select>
        </label>
    </div>

    <div class="restock-layout">
        <section class="panel">
            <h3>{$_("analytics.productsNeedingRestock")}</h3>
            {#if !restockOverview || sortedRestockRows.length === 0}
                <p class="muted">{$_("analytics.noRestockNeeded")}</p>
            {:else}
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>{$_("analytics.colProduct")}</th>
                                <th>{$_("analytics.colCategory")}</th>
                                <th>{$_("analytics.colStock")}</th>
                                <th>{$_("analytics.colTarget")}</th>
                                <th>{$_("analytics.colMin")}</th>
                                <th>{$_("analytics.colMissing")}</th>
                                <th>{$_("analytics.colUrgent")}</th>
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
            <h3>{$_("analytics.childTotals")}</h3>
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

            <h3 class="mt">{$_("analytics.parentTotals")}</h3>
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
</Modal>

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
        border: 1px solid #4b5563;
        border-radius: 0.4rem;
        background: #111827;
        color: #f3f4f6;
        color-scheme: dark;
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
        border: 1px solid #5b4f3a;
        background: #2f2a22;
        color: #f3f4f6;
        border-radius: 0.5rem;
        padding: 0.45rem 0.85rem;
        font-weight: 600;
        cursor: pointer;
    }

    .summary-text {
        color: #d1d5db;
        font-size: 0.9rem;
    }

    .error {
        color: #e74c3c;
    }

    .empty {
        text-align: center;
        color: #9ca3af;
        margin: 3rem 0;
    }

    .pane {
        background: #2f2a22;
        border: 1px solid #5b4f3a;
        border-radius: 1rem;
        padding: 1rem 1.25rem;
    }

    .pane h2 {
        margin: 0 0 1rem;
        font-size: 1rem;
        color: #f3f4f6;
    }

    .stack {
        display: grid;
        gap: 1rem;
    }

    .card {
        background: #26221b;
        border: 1px solid #4f4534;
        border-radius: 0.8rem;
        padding: 1rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }

    .card h3 {
        margin: 0 0 0.8rem;
        font-size: 0.9rem;
        color: #d1d5db;
    }

    .chart-wrap {
        position: relative;
        height: 14rem;
    }

    .muted {
        color: #9ca3af;
        font-size: 0.9rem;
        margin: 1rem 0;
    }

    .kpis {
        display: grid;
        grid-template-columns: repeat(2, minmax(180px, 1fr));
        gap: 0.75rem;
        margin-bottom: 0.75rem;
    }

    .kpi {
        border: 1px solid #4f4534;
        border-radius: 0.6rem;
        padding: 0.7rem;
        background: #26221b;
    }

    .kpi-label {
        font-size: 0.78rem;
        color: #9ca3af;
    }

    .kpi-value {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f3f4f6;
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
        color: #d1d5db;
    }

    .controls select {
        border: 1px solid #5b4f3a;
        border-radius: 0.5rem;
        padding: 0.35rem 0.45rem;
        background: #26221b;
        color: #f3f4f6;
    }

    .restock-layout {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 0.75rem;
    }

    .panel {
        border: 1px solid #4f4534;
        border-radius: 0.7rem;
        padding: 0.75rem;
        background: #26221b;
    }

    .panel h3 {
        margin: 0 0 0.55rem;
        font-size: 0.95rem;
        color: #e5e7eb;
    }

    .mt {
        margin-top: 1rem;
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
        border-bottom: 1px solid #374151;
        white-space: nowrap;
        color: #e5e7eb;
    }

    th {
        background: #2f2a22;
        color: #d1d5db;
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
        border-bottom: 1px solid #374151;
        font-size: 0.85rem;
        color: #e5e7eb;
    }

    @media (max-width: 900px) {
        .restock-layout {
            grid-template-columns: 1fr;
        }
    }
</style>
