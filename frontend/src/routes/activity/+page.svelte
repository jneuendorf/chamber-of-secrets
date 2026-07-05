<script lang="ts">
    import { get } from 'svelte/store'
    import { _ } from 'svelte-i18n'

    import {
        ApiError,
        api,
        type Category,
        type Product,
        type Transaction,
    } from '$lib/api/client'
    import Modal from '$lib/components/Modal.svelte'
    import Select from '$lib/components/Select.svelte'
    import { resolveIcon } from '$lib/utils/category'

    let transactions: Transaction[] = $state([])
    let products: Product[] = $state([])
    let categories: Category[] = $state([])
    let loading = $state(true)
    let error = $state('')
    let filterProductId: number | 'all' = $state('all')

    let productName = $derived(
        new Map(products.map((product) => [product.id, product.name])),
    )

    let filterItems = $derived([
        { value: 'all' as const, label: get(_)('activity.allProducts') },
        ...products.map((product) => ({
            value: product.id,
            label: product.name,
            icon: resolveIcon(product.category, categories),
        })),
    ])

    // --- Edit / delete state (WL-4.2) ---
    let editing: Transaction | null = $state(null)
    let editType: 'in' | 'out' = $state('in')
    let editQuantity = $state(1)
    let editPrice: number | undefined = $state(undefined)
    let deleting: Transaction | null = $state(null)

    async function loadProducts() {
        try {
            ;[products, categories] = await Promise.all([
                api.products.list(),
                api.categories.list(),
            ])
        } catch (e) {
            error = get(_)('activity.failedToLoad', {
                values: { error: e instanceof ApiError ? e.detail : String(e) },
            })
        }
    }

    async function loadTransactions(productId: number | 'all') {
        loading = true
        try {
            transactions = await api.transactions.list(
                productId === 'all' ? undefined : productId,
            )
        } catch (e) {
            error = get(_)('activity.failedToLoad', {
                values: { error: e instanceof ApiError ? e.detail : String(e) },
            })
        } finally {
            loading = false
        }
    }

    $effect(() => {
        loadProducts()
    })

    $effect(() => {
        loadTransactions(filterProductId)
    })

    function openEdit(txn: Transaction) {
        editing = txn
        editType = txn.type
        editQuantity = txn.quantity
        editPrice = txn.unit_price ?? undefined
    }

    async function saveEdit() {
        const txn = editing
        if (!txn) {
            return
        }
        editing = null
        try {
            const updated = await api.transactions.update(txn.id, {
                type: editType,
                quantity: editQuantity,
                unit_price: editPrice ?? null,
            })
            transactions = transactions.map((t) => (t.id === updated.id ? updated : t))
        } catch (e) {
            error = get(_)('activity.saveFailed', {
                values: { error: e instanceof ApiError ? e.detail : String(e) },
            })
        }
    }

    async function confirmDelete() {
        const txn = deleting
        if (!txn) {
            return
        }
        deleting = null
        try {
            await api.transactions.delete(txn.id)
            transactions = transactions.filter((t) => t.id !== txn.id)
        } catch (e) {
            error = get(_)('activity.deleteFailed', {
                values: { error: e instanceof ApiError ? e.detail : String(e) },
            })
        }
    }

    function formatWhen(iso: string): string {
        return new Date(iso).toLocaleString()
    }
</script>

<h1 class="mt-0">{$_('activity.title')}</h1>

<label class="mb-4 flex flex-col gap-1.5 text-sm text-ink-200 max-w-xs">
    {$_('activity.filterLabel')}
    <Select
        items={filterItems}
        value={filterProductId}
        onchange={(value) => (filterProductId = value)}
        class="rounded-lg border border-bark-600 bg-bark-850 px-3 py-2 text-ink-100"
    />
</label>

{#if loading}
    <p>{$_('common.loading')}</p>
{:else if error}
    <p class="text-danger-500">{error}</p>
{:else if transactions.length === 0}
    <p class="text-center text-ink-300 my-12">{$_('activity.empty')}</p>
{:else}
    <div class="flex flex-col gap-2">
        {#each transactions as txn (txn.id)}
            <div
                class="bg-bark-800 border border-bark-600 rounded-xl p-3 shadow-sm flex items-center gap-3"
            >
                <span
                    class="shrink-0 w-16 text-center text-xs font-semibold px-2 py-1 rounded-lg"
                    class:added={txn.type === 'in'}
                    class:removed={txn.type === 'out'}
                >
                    {txn.type === 'in' ? '+' : '−'}{txn.quantity}
                </span>
                <div class="flex-1 min-w-0">
                    <p class="m-0 text-ink-100 truncate">
                        {productName.get(txn.product_id) ??
                            $_('activity.unknownProduct')}
                    </p>
                    <p class="m-0 text-ink-400 text-xs">
                        {formatWhen(txn.transacted_at)}
                        {#if txn.unit_price != null}· {txn.unit_price}{/if}
                    </p>
                </div>
                <button
                    type="button"
                    onclick={() => openEdit(txn)}
                    class="shrink-0 px-2.5 py-1.5 text-xs rounded-lg border border-bark-600 bg-bark-850 text-ink-200 hover:text-ink-100"
                >
                    {$_('activity.edit')}
                </button>
                <button
                    type="button"
                    onclick={() => (deleting = txn)}
                    class="shrink-0 px-2.5 py-1.5 text-xs rounded-lg border border-danger-900 bg-ink-900 text-danger-200 hover:text-danger-100"
                >
                    {$_('activity.delete')}
                </button>
            </div>
        {/each}
    </div>
{/if}

<Modal
    open={editing !== null}
    title={$_('activity.editTitle')}
    onclose={() => (editing = null)}
>
    {#if editing}
        <div class="flex flex-col gap-4">
            <div class="grid grid-cols-2 gap-2">
                <button
                    type="button"
                    onclick={() => (editType = 'in')}
                    class={`h-9 rounded-lg text-xs font-semibold ${
                        editType === 'in'
                            ? 'bg-success-700 text-white'
                            : 'bg-ink-900 text-success-300 border border-success-900'
                    }`}
                >
                    {$_('activity.typeIn')}
                </button>
                <button
                    type="button"
                    onclick={() => (editType = 'out')}
                    class={`h-9 rounded-lg text-xs font-semibold ${
                        editType === 'out'
                            ? 'bg-danger-500 text-white'
                            : 'bg-ink-900 text-danger-200 border border-danger-900'
                    }`}
                >
                    {$_('activity.typeOut')}
                </button>
            </div>
            <label class="flex flex-col gap-1 text-sm text-ink-200">
                {$_('activity.quantity')}
                <input
                    type="number"
                    min="1"
                    step="1"
                    inputmode="numeric"
                    bind:value={editQuantity}
                    class="px-2 py-2 border border-bark-600 bg-bark-850 text-ink-100 rounded-md text-base"
                />
            </label>
            <label class="flex flex-col gap-1 text-sm text-ink-200">
                {$_('activity.price')}
                <input
                    type="number"
                    min="0"
                    step="0.01"
                    inputmode="decimal"
                    bind:value={editPrice}
                    class="px-2 py-2 border border-bark-600 bg-bark-850 text-ink-100 rounded-md text-base"
                />
            </label>
            <div class="flex justify-end gap-2">
                <button
                    type="button"
                    onclick={() => (editing = null)}
                    class="px-3 py-2 text-sm rounded-lg border border-bark-600 bg-bark-850 text-ink-200"
                >
                    {$_('common.cancel')}
                </button>
                <button
                    type="button"
                    onclick={saveEdit}
                    disabled={editQuantity <= 0}
                    class="px-3 py-2 text-sm rounded-lg border-0 bg-accent-900 text-white disabled:opacity-50"
                >
                    {$_('activity.save')}
                </button>
            </div>
        </div>
    {/if}
</Modal>

<Modal
    open={deleting !== null}
    title={$_('activity.delete')}
    onclose={() => (deleting = null)}
>
    <p class="mt-0 text-ink-200">{$_('activity.deleteConfirm')}</p>
    <div class="mt-4 flex justify-end gap-2">
        <button
            type="button"
            onclick={() => (deleting = null)}
            class="px-3 py-2 text-sm rounded-lg border border-bark-600 bg-bark-850 text-ink-200"
        >
            {$_('common.cancel')}
        </button>
        <button
            type="button"
            onclick={confirmDelete}
            class="px-3 py-2 text-sm rounded-lg border-0 bg-danger-500 text-white"
        >
            {$_('activity.delete')}
        </button>
    </div>
</Modal>

<style>
    .added {
        background: var(--color-success-900);
        color: var(--color-success-200);
    }

    .removed {
        background: var(--color-danger-900);
        color: var(--color-danger-200);
    }
</style>
