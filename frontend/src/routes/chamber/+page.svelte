<script lang="ts">
    import { cubicOut } from 'svelte/easing'
    import { get } from 'svelte/store'
    import { _ } from 'svelte-i18n'

    import { ApiError, api, type Category, type Product } from '$lib/api/client'
    import ConsumeSheet, {
        type ConsumeCandidate,
    } from '$lib/components/ConsumeSheet.svelte'
    import Modal from '$lib/components/Modal.svelte'
    import { resolveRestockPolicy, stockStatus } from '$lib/utils/category'
    import { buildDots, type ChamberDot, visibleSlots } from '$lib/utils/chamber'

    let products: Product[] = $state([])
    let allCategories: Category[] = $state([])
    let loading = $state(true)
    let error = $state('')
    let statsOpen = $state(false)

    // Tap-to-consume sheet (WL-5.2)
    let sheetOpen = $state(false)
    let sheetCandidates = $state<ConsumeCandidate[]>([])

    // Slots consumed locally since the last load, keyed by product id. This
    // overlays server stock so the *exact* tapped dots vanish (not some other
    // slot) and a big pile refills from its reserve instead of gapping. Reset
    // on reload, where server stock already reflects the committed movements.
    let consumed = $state<Record<number, number[]>>({})

    // Toast with one-tap undo. A new consume replaces the previous toast (undo
    // targets the latest action only); an explicit ✕ dismisses it.
    let toastMsg = $state('')
    let pendingUndo = $state<{
        txnId: number
        productId: number
        slots: number[]
    } | null>(null)
    let toastTimer: ReturnType<typeof setTimeout> | undefined

    $effect(() => {
        Promise.all([api.products.list(), api.categories.list()])
            .then(([productList, categoryList]) => {
                products = productList
                allCategories = categoryList
            })
            .catch((err: unknown) => {
                error = err instanceof ApiError ? err.detail : String(err)
            })
            .finally(() => {
                loading = false
            })
    })

    let consumedMap = $derived(
        new Map(Object.entries(consumed).map(([id, slots]) => [Number(id), slots])),
    )
    let dots = $derived(buildDots(products, allCategories, consumedMap))

    function effectiveStock(product: Product): number {
        return product.stock - (consumed[product.id]?.length ?? 0)
    }

    let available = $derived(
        products.filter((product) => effectiveStock(product) > 0).length,
    )
    let needsRestock = $derived(
        products.filter((product) => {
            const cat =
                allCategories.find((category) => category.id === product.category_id) ??
                product.category ??
                null
            return (
                stockStatus(
                    effectiveStock(product),
                    resolveRestockPolicy(cat, allCategories),
                ) !== 'ok'
            )
        }).length,
    )
    let totalItems = $derived(
        products.reduce(
            (sum, product) => sum + Math.max(0, effectiveStock(product)),
            0,
        ),
    )

    function showToast(
        message: string,
        undo: { txnId: number; productId: number; slots: number[] } | null = null,
    ) {
        toastMsg = message
        pendingUndo = undo
        clearTimeout(toastTimer)
        toastTimer = setTimeout(
            () => {
                toastMsg = ''
                pendingUndo = null
            },
            undo ? 5000 : 2500,
        )
    }

    function dismissToast() {
        clearTimeout(toastTimer)
        toastMsg = ''
        pendingUndo = null
    }

    function openSheet(dot: ChamberDot) {
        const product = products.find((candidate) => candidate.id === dot.productId)
        if (!product) {
            return
        }
        const available = effectiveStock(product)
        if (available <= 0) {
            return
        }
        sheetCandidates = [
            {
                product,
                emoji: dot.emoji,
                isUrl: dot.isUrl,
                src: dot.src,
                slot: dot.slot,
                available,
            },
        ]
        sheetOpen = true
    }

    // The specific slots a consume of `quantity` should remove: the tapped slot
    // first, then the highest currently-visible slots, then reserve slots (when
    // quantity exceeds what's on screen). Guarantees `quantity` distinct slots.
    function slotsToConsume(
        product: Product,
        current: number[],
        tapped: number,
        quantity: number,
    ): number[] {
        const used = new Set(current)
        const chosen: number[] = []
        if (!used.has(tapped)) {
            chosen.push(tapped)
            used.add(tapped)
        }
        const topFirst = visibleSlots(product.stock, current).sort(
            (left, right) => right - left,
        )
        for (const slot of topFirst) {
            if (chosen.length >= quantity) {
                break
            }
            if (!used.has(slot)) {
                chosen.push(slot)
                used.add(slot)
            }
        }
        for (let slot = 0; chosen.length < quantity; slot++) {
            if (!used.has(slot)) {
                chosen.push(slot)
                used.add(slot)
            }
        }
        return chosen
    }

    async function consume(product: Product, slot: number, quantity: number) {
        sheetOpen = false
        const current = consumed[product.id] ?? []
        const qty = Math.max(1, Math.min(quantity, product.stock - current.length))
        if (qty <= 0) {
            return
        }
        const slots = slotsToConsume(product, current, slot, qty)
        consumed = { ...consumed, [product.id]: [...current, ...slots] }
        try {
            const txn = await api.transactions.create({
                product_id: product.id,
                type: 'out',
                quantity: qty,
            })
            showToast(
                get(_)('chamber.consumed', {
                    values: { name: product.name, count: qty },
                }),
                { txnId: txn.id, productId: product.id, slots },
            )
        } catch (err) {
            releaseSlots(product.id, slots)
            showToast(
                get(_)('chamber.consumeFailed', {
                    values: {
                        name: product.name,
                        error: err instanceof ApiError ? err.detail : String(err),
                    },
                }),
            )
        }
    }

    async function undoConsume() {
        if (!pendingUndo) {
            return
        }
        const { txnId, productId, slots } = pendingUndo
        pendingUndo = null
        try {
            await api.transactions.delete(txnId)
            releaseSlots(productId, slots)
            showToast(get(_)('chamber.undone'))
        } catch (err) {
            showToast(
                get(_)('chamber.undoFailed', {
                    values: {
                        error: err instanceof ApiError ? err.detail : String(err),
                    },
                }),
            )
        }
    }

    function releaseSlots(productId: number, slots: number[]) {
        const current = consumed[productId] ?? []
        consumed = {
            ...consumed,
            [productId]: current.filter((slot) => !slots.includes(slot)),
        }
    }

    // Vanish: scale down + fade + a little lift and spin. The dot's resting
    // transform is translate(-50%, -50%), so keep it here or the dot would jump.
    // ponytail: crumb/dust particles deferred to WL-5.5 (art pipeline).
    // biome-ignore lint/correctness/noUnusedVariables: used by the `out:poof` directive, which Biome's Svelte parser doesn't track
    function poof(_node: Element) {
        const reduce =
            typeof matchMedia !== 'undefined' &&
            matchMedia('(prefers-reduced-motion: reduce)').matches
        return {
            duration: reduce ? 0 : 320,
            easing: cubicOut,
            css: (t: number) => {
                const scale = 0.35 + t * 0.65
                const lift = (1 - t) * 14
                const spin = (1 - t) * 25
                return `opacity:${t}; transform: translate(-50%, -50%) translateY(-${lift}px) scale(${scale}) rotate(${spin}deg);`
            },
        }
    }
</script>

<div class="chamber-root">
    {#if loading}
        <p class="state-msg">{$_('common.loading')}</p>
    {:else if error}
        <p class="state-msg error-msg">{error}</p>
    {:else if products.length === 0}
        <div class="empty-state">
            <p class="empty-icon">🏚️</p>
            <p class="empty-text">{$_('chamber.empty')}</p>
            <a href="/scan" class="cta-link">{$_('chamber.scanCta')}</a>
        </div>
    {:else}
        <!-- Full-scene canvas: one tappable emoji per dot, 2D Gaussian piles -->
        <div class="scene-frame">
            <div class="scene">
                <div class="item-piles">
                    {#each dots as dot (dot.key)}
                        <button
                            type="button"
                            class="pile-dot"
                            style="left:{dot.x}%;top:{dot.y}%;z-index:{dot.z}"
                            title={dot.title}
                            aria-label={dot.title}
                            onclick={() => openSheet(dot)}
                            out:poof
                        >
                            {#if dot.isUrl}
                                <img src={dot.src} alt="" class="img-e" />
                            {:else}
                                {dot.emoji}
                            {/if}
                        </button>
                    {/each}
                </div>
            </div>
        </div>
    {/if}
</div>

<!-- Consume toast with undo -->
{#if toastMsg}
    <div class="consume-toast">
        <span>{toastMsg}</span>
        {#if pendingUndo}
            <button type="button" class="toast-undo" onclick={undoConsume}>
                {$_('chamber.undo')}
            </button>
        {/if}
        <button
            type="button"
            class="toast-close"
            aria-label={$_('common.close')}
            onclick={dismissToast}
        >
            ✕
        </button>
    </div>
{/if}

<ConsumeSheet
    open={sheetOpen}
    candidates={sheetCandidates}
    onconfirm={consume}
    onclose={() => (sheetOpen = false)}
/>

<!-- Floating stats toggle -->
{#if !loading && products.length > 0}
    <button
        type="button"
        class="stats-btn"
        onclick={() => (statsOpen = true)}
        title={$_('chamber.statsTitle')}
    >
        📜
    </button>
{/if}

<!-- Stats modal -->
<Modal
    open={statsOpen}
    title="📜 {$_('chamber.statsTitle')}"
    onclose={() => (statsOpen = false)}
    width="min(340px, 100%)"
>
    <table class="stats-table">
        <tbody>
            <tr>
                <td>{$_('chamber.available')}</td>
                <td class="stat-val">{available}</td>
            </tr>
            <tr>
                <td>{$_('chamber.required')}</td>
                <td class="stat-val" class:stat-depleted={needsRestock > 0}
                    >{needsRestock}</td
                >
            </tr>
            <tr>
                <td>{$_('chamber.totalStock')}</td>
                <td class="stat-val">{totalItems}</td>
            </tr>
        </tbody>
    </table>
</Modal>

<style>
    /* ---- Root: full viewport canvas ---- */
    .chamber-root {
        min-height: calc(100vh - 3rem);
        min-height: calc(100dvh - 3rem);
        height: calc(100vh - 3rem);
        height: calc(100dvh - 3rem);
        overflow: hidden;
        position: relative;
        color: var(--color-accent-100);
    }

    .scene-frame {
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        height: 100%;
        width: auto;
        aspect-ratio: 3 / 2;
        max-width: 100%;
        overflow: hidden;
    }

    /* ---- Scene canvas ---- */
    .scene {
        position: relative;
        width: 100%;
        height: 100%;
        z-index: 1;
        background-image: url('/chamber-background.png');
        background-repeat: no-repeat;
        background-position: top center;
        background-size: auto 100%;
        background-clip: border-box;
    }

    /* ---- Item piles ---- */
    .item-piles {
        position: relative;
        width: 90%;
        height: 100%;
        left: 5%;
    }

    /* ---- Individual emoji dot (tappable) ---- */
    .pile-dot {
        position: absolute;
        transform: translate(-50%, -50%);
        line-height: 1;
        cursor: pointer;
        user-select: none;
        -webkit-touch-callout: none;
        background: none;
        border: 0;
        padding: 0;
        color: inherit;
        font-size: clamp(1.8rem, 5.4vh, 4.3rem);
        filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.8));
        transition: transform 0.12s ease-out;
    }

    .pile-dot:active {
        transform: translate(-50%, -50%) scale(0.85);
    }

    .img-e {
        width: clamp(1.8rem, 5.4vh, 4.3rem);
        height: clamp(1.8rem, 5.4vh, 4.3rem);
        object-fit: cover;
        border-radius: 6px;
        display: inline-block;
    }

    /* ---- State messages ---- */
    .state-msg {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        color: var(--color-accent-100);
        background: rgba(0, 0, 0, 0.6);
        padding: 1rem 1.5rem;
        border-radius: 8px;
    }

    .error-msg {
        color: var(--color-danger-300);
    }

    .empty-state {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
        background: rgba(0, 0, 0, 0.6);
        padding: 2.5rem 2rem;
        border-radius: 12px;
        border: 1px solid color-mix(in srgb, var(--color-gold) 20%, transparent);
    }

    .empty-icon {
        font-size: 3rem;
        margin: 0 0 0.5rem;
    }
    .empty-text {
        color: var(--color-ink-400);
        margin: 0 0 1rem;
    }

    .cta-link {
        display: inline-block;
        padding: 0.4rem 1.1rem;
        background: color-mix(in srgb, var(--color-gold) 12%, transparent);
        border: 1px solid color-mix(in srgb, var(--color-gold) 35%, transparent);
        border-radius: 6px;
        color: var(--color-warning-400);
        text-decoration: none;
        font-size: 0.85rem;
    }

    /* ---- Consume toast ---- */
    .consume-toast {
        position: fixed;
        left: 50%;
        bottom: 5rem;
        transform: translateX(-50%);
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: var(--color-success-800);
        color: var(--color-success-100);
        padding: 0.5rem 1rem;
        border-radius: 0.75rem;
        font-size: 0.875rem;
        font-weight: 600;
        z-index: 30;
        box-shadow: 0 2px 14px rgba(0, 0, 0, 0.6);
        animation: toast-in 0.3s ease-out;
    }

    .toast-undo {
        flex: 0 0 auto;
        background: var(--color-success-100);
        color: var(--color-success-900);
        border: 0;
        border-radius: 0.5rem;
        padding: 0.25rem 0.7rem;
        font-size: 0.8rem;
        font-weight: 700;
        cursor: pointer;
    }

    .toast-close {
        flex: 0 0 auto;
        background: transparent;
        color: var(--color-success-100);
        border: 0;
        padding: 0.1rem 0.3rem;
        font-size: 0.9rem;
        line-height: 1;
        cursor: pointer;
        opacity: 0.8;
    }

    .toast-close:hover {
        opacity: 1;
    }

    @keyframes toast-in {
        from {
            opacity: 0;
            transform: translate(-50%, 0.5rem);
        }
        to {
            opacity: 1;
            transform: translate(-50%, 0);
        }
    }

    /* ---- Stats button ---- */
    .stats-btn {
        position: fixed;
        bottom: 1.5rem;
        right: 1.5rem;
        width: 3rem;
        height: 3rem;
        font-size: 1.4rem;
        background: rgba(6, 4, 14, 0.88);
        border: 1px solid color-mix(in srgb, var(--color-gold) 45%, transparent);
        border-radius: 50%;
        cursor: pointer;
        z-index: 20;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 14px rgba(0, 0, 0, 0.6);
    }

    .stats-btn:hover {
        background: rgba(20, 12, 40, 0.95);
        border-color: color-mix(in srgb, var(--color-gold) 75%, transparent);
    }

    /* ---- Stats modal ---- */
    .stats-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }

    .stats-table td {
        padding: 0.28rem 0;
        color: var(--color-ink-250);
    }

    .stat-val {
        text-align: right;
        font-weight: 700;
        color: var(--color-accent-100);
    }

    .stat-depleted {
        color: var(--color-danger-300);
    }
</style>
