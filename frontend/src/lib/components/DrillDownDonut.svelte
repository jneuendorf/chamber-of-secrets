<script lang="ts">
    import {
        ArcElement,
        Chart,
        DoughnutController,
        Legend,
        Tooltip,
    } from 'chart.js'
    import { _ } from 'svelte-i18n'

    Chart.register(DoughnutController, ArcElement, Legend, Tooltip)

    export type Slice = {
        label: string
        value: number
        key: string
        drillable: boolean
    }

    interface Props {
        title: string
        getSlices: (parentKey: string | null) => Slice[]
        formatTotal: (total: number) => string
        centerLabel: string
        formatTooltip: (label: string, value: number, pct: string) => string
    }

    let { title, getSlices, formatTotal, centerLabel, formatTooltip }: Props =
        $props()

    const COLORS = [
        '#e74c3c',
        '#3498db',
        '#2ecc71',
        '#f39c12',
        '#9b59b6',
        '#1abc9c',
        '#e67e22',
        '#e91e63',
        '#34495e',
        '#1a1a2e',
    ]

    let stack: { key: string; label: string }[] = $state([])
    let direction: 'forward' | 'back' = $state('forward')

    let level = $derived(stack.length)
    let currentKey = $derived(
        stack.length > 0 ? stack[stack.length - 1].key : null,
    )
    let currentSlices = $derived(getSlices(currentKey))
    let currentTotal = $derived(
        currentSlices.reduce((sum, s) => sum + s.value, 0),
    )

    function drillIn(key: string, label: string) {
        direction = 'forward'
        stack = [...stack, { key, label }]
    }

    function goBack() {
        direction = 'back'
        stack = stack.slice(0, -1)
    }

    let canvas: HTMLCanvasElement | undefined = $state()

    $effect(() => {
        if (!canvas || currentSlices.length === 0) { return }

        const slices = currentSlices
        const total = currentTotal
        const totalFormatted = formatTotal(total)
        const cLabel = centerLabel
        const fTooltip = formatTooltip

        const chart = new Chart<'doughnut'>(canvas, {
            type: 'doughnut',
            data: {
                labels: slices.map((s) =>
                    s.drillable ? `${s.label} ›` : s.label,
                ),
                datasets: [
                    {
                        data: slices.map((s) => s.value),
                        backgroundColor: slices.map(
                            (_, i) => COLORS[i % COLORS.length],
                        ),
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                cutout: '60%',
                responsive: true,
                maintainAspectRatio: false,
                onHover: (_event, elements) => {
                    if (!canvas) { return }
                    canvas.style.cursor =
                        elements.length > 0 &&
                        slices[elements[0].index]?.drillable
                            ? 'pointer'
                            : 'default'
                },
                onClick: (_event, elements) => {
                    if (elements.length === 0) { return }
                    const slice = slices[elements[0].index]
                    if (slice?.drillable) { drillIn(slice.key, slice.label) }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            font: { size: 11 },
                            color: '#e5e7eb',
                        },
                        onClick: (_e, legendItem, legend) => {
                            const idx = legendItem.index!
                            if (slices[idx]?.drillable) {
                                drillIn(slices[idx].key, slices[idx].label)
                            } else {
                                Chart.defaults.plugins.legend.onClick.call(
                                    legend,
                                    _e,
                                    legendItem,
                                    legend,
                                )
                            }
                        },
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const label = (ctx.label as string).replace(
                                    /\s›$/,
                                    '',
                                )
                                const pct = (
                                    ((ctx.raw as number) / total) *
                                    100
                                ).toFixed(0)
                                return fTooltip(
                                    label,
                                    ctx.raw as number,
                                    pct,
                                )
                            },
                        },
                    },
                },
            },
            plugins: [
                {
                    id: 'centerText',
                    afterDraw(chart: Chart) {
                        const {
                            ctx,
                            chartArea: { top, bottom, left, right },
                        } = chart
                        const cx = (left + right) / 2
                        const cy = (top + bottom) / 2
                        ctx.save()
                        ctx.textAlign = 'center'
                        ctx.textBaseline = 'middle'
                        ctx.fillStyle = '#f3f4f6'
                        ctx.font = 'bold 20px sans-serif'
                        ctx.fillText(totalFormatted, cx, cy - 8)
                        ctx.fillStyle = '#d1d5db'
                        ctx.font = '11px sans-serif'
                        ctx.fillText(cLabel, cx, cy + 10)
                        ctx.restore()
                    },
                },
            ],
        })

        return () => chart.destroy()
    })
</script>

<div class="card">
    <div class="drill-header">
        {#if stack.length > 0}
            <button type="button" class="drill-back" onclick={goBack}>
                ‹
            </button>
            <h3>{stack[stack.length - 1].label}</h3>
        {:else}
            <h3>{title}</h3>
        {/if}
    </div>
    <div class="drill-viewport">
        {#key level}
            <div
                class="drill-panel"
                class:slide-right={direction === 'forward' && level > 0}
                class:slide-left={direction === 'back'}
            >
                {#if currentSlices.length === 0}
                    <p class="empty-msg">{$_('analytics.empty')}</p>
                {:else}
                    <canvas bind:this={canvas}></canvas>
                {/if}
            </div>
        {/key}
    </div>
</div>

<style>
    .card {
        background: #26221b;
        border: 1px solid #4f4534;
        border-radius: 0.8rem;
        padding: 1rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }

    .drill-header {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        margin-bottom: 0.6rem;
    }

    .drill-header h3 {
        margin: 0;
        font-size: 0.9rem;
        color: #d1d5db;
    }

    .drill-back {
        background: none;
        border: none;
        color: #3498db;
        font-size: 1.4rem;
        font-weight: 600;
        cursor: pointer;
        padding: 0 0.2rem;
        line-height: 1;
    }

    .drill-back:hover {
        color: #5dade2;
    }

    .drill-viewport {
        position: relative;
        overflow: hidden;
        height: 16rem;
    }

    .drill-panel {
        width: 100%;
        height: 100%;
    }

    .empty-msg {
        color: #9ca3af;
        font-size: 0.9rem;
        text-align: center;
        padding-top: 5rem;
    }

    .slide-right {
        animation: slideRight 0.28s ease-out;
    }

    .slide-left {
        animation: slideLeft 0.28s ease-out;
    }

    @keyframes slideRight {
        from {
            transform: translateX(40%);
            opacity: 0.15;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideLeft {
        from {
            transform: translateX(-40%);
            opacity: 0.15;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
</style>
