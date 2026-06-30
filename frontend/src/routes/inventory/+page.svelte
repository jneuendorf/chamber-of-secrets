<script lang="ts">
    import { get } from 'svelte/store'
    import { _ } from 'svelte-i18n'

    import { ApiError, api, type Category, type Product } from '$lib/api/client'
    import CategoryPicker from '$lib/components/CategoryPicker.svelte'
    import FuzzySearchOverlay from '$lib/components/FuzzySearchOverlay.svelte'
    import {
        resolveRestockPolicy,
        type StockStatus,
        stockStatus,
    } from '$lib/utils/category'

    let products: Product[] = $state([])
    let categories: Category[] = $state([])
    let loading = $state(true)
    let error = $state('')
    let editingId: number | null = $state(null)
    let searchOpen = $state(false)
    let uploadingId: number | null = $state(null)
    let cameraInput: HTMLInputElement | undefined = $state(undefined)
    let galleryInput: HTMLInputElement | undefined = $state(undefined)
    let totalItems = $derived(products.reduce((sum, p) => sum + p.stock, 0))

    function statusFor(product: Product): StockStatus {
        const cat =
            categories.find((category) => category.id === product.category_id) ??
            product.category ??
            null
        return stockStatus(product.stock, resolveRestockPolicy(cat, categories))
    }

    function selectProductFromSearch(item: unknown) {
        const product = item as Product
        editingId = product.id
        document
            .querySelector(`[data-product-id="${product.id}"]`)
            ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }

    async function load() {
        try {
            ;[products, categories] = await Promise.all([
                api.products.list(),
                api.categories.list(),
            ])
        } catch (e) {
            error = get(_)('inventory.failedToLoad', {
                values: { error: e instanceof ApiError ? e.detail : String(e) },
            })
        } finally {
            loading = false
        }
    }

    $effect(() => {
        load()
    })

    async function assignCategory(product: Product, cat: Category | null) {
        editingId = null
        try {
            const updated = await api.products.update(product.id, {
                category_id: cat?.id ?? null,
            })
            products = products.map((p) =>
                p.id === product.id
                    ? { ...p, ...updated, category: cat, stock: p.stock }
                    : p,
            )
        } catch (e) {
            error = get(_)('category.failedToSave', {
                values: { error: e instanceof ApiError ? e.detail : String(e) },
            })
        }
    }

    async function createAndAssign(product: Product, name: string) {
        try {
            const cat = await api.categories.create({ name })
            categories = [...categories, cat]
            await assignCategory(product, cat)
        } catch (e) {
            error = get(_)('category.failedToSave', {
                values: { error: e instanceof ApiError ? e.detail : String(e) },
            })
        }
    }

    function triggerCamera(productId: number) {
        uploadingId = productId
        cameraInput?.click()
    }

    function triggerGallery(productId: number) {
        uploadingId = productId
        galleryInput?.click()
    }

    async function handleImageSelected(e: Event) {
        const input = e.currentTarget as HTMLInputElement
        const file = input.files?.[0]
        if (!file || uploadingId === null) {
            return
        }

        const productId = uploadingId
        uploadingId = null
        input.value = ''

        try {
            const updated = await api.products.uploadImage(productId, file)
            products = products.map((p) =>
                p.id === productId ? { ...p, image_url: updated.image_url } : p,
            )
        } catch (e) {
            error = get(_)('inventory.uploadFailed', {
                values: {
                    error: e instanceof ApiError ? (e as ApiError).detail : String(e),
                },
            })
        }
    }

    async function handleUpdateIcon(cat: Category, icon: string | null) {
        const updated = await api.categories.update(cat.id, { icon })
        categories = categories.map((c) => (c.id === updated.id ? updated : c))
        // Refresh icon on any product that has this category
        products = products.map((p) =>
            p.category?.id === updated.id ? { ...p, category: updated } : p,
        )
    }
</script>

<input
    type="file"
    accept="image/*"
    capture="environment"
    class="hidden"
    bind:this={cameraInput}
    onchange={handleImageSelected}
/>
<input
    type="file"
    accept="image/*"
    class="hidden"
    bind:this={galleryInput}
    onchange={handleImageSelected}
/>

<div class="heading-row">
    <h1 class="mt-0">{$_('nav.inventory')} ({totalItems})</h1>
    <button
        type="button"
        class="search-indicator"
        title={$_('inventory.searchHint')}
        onclick={() => {
            searchOpen = true
        }}
    >
        <span class="search-indicator-icon" aria-hidden="true">⌕</span>
        {$_('common.searchIndicator')}
    </button>
</div>

{#if loading}
    <p>{$_('common.loading')}</p>
{:else if error}
    <p class="text-danger-500">{error}</p>
{:else if products.length === 0}
    <p class="text-center text-gray-500 my-12">
        {$_('inventory.empty')} <a href="/scan">{$_('inventory.scanCta')}</a>
    </p>
{:else}
    <FuzzySearchOverlay
        items={products}
        keys={['name', 'brand', 'ean', 'category.name']}
        getId={(item) => (item as Product).id}
        getLabel={(item) => (item as Product).name}
        getSecondaryLabel={(item) => {
            const p = item as Product
            const parts = [p.brand, p.category?.name].filter(Boolean)
            return parts.length ? parts.join(' · ') : null
        }}
        onSelect={selectProductFromSearch}
        placeholder={$_('inventory.searchPlaceholder')}
        noResultsText={$_('inventory.searchNoResults')}
        hintText={$_('inventory.searchHint')}
        bind:open={searchOpen}
    />

    <div class="flex flex-col gap-3">
        {#each products as product (product.id)}
            {@const stockState = statusFor(product)}
            <div
                class="bg-bark-800 border border-bark-600 rounded-xl p-4 shadow-sm"
                data-product-id={product.id}
            >
                <div class="flex items-center gap-4">
                    <div class="image-group">
                        <button
                            type="button"
                            class="image-btn"
                            title={$_(
                                product.image_url
                                    ? 'inventory.changeImage'
                                    : 'inventory.addImage',
                            )}
                            onclick={() => triggerGallery(product.id)}
                        >
                            {#if product.image_url}
                                <img
                                    src={product.image_url}
                                    alt={product.name}
                                    class="w-12 h-12 rounded-lg object-cover"
                                />
                            {:else}
                                <div
                                    class="w-12 h-12 rounded-lg bg-bark-850 border border-bark-650 flex items-center justify-center text-gray-300 text-xl"
                                >
                                    ?
                                </div>
                            {/if}
                        </button>
                        <button
                            type="button"
                            class="camera-btn"
                            title={$_('scanner.camera')}
                            onclick={() => triggerCamera(product.id)}
                        >
                            📷
                        </button>
                    </div>
                    <div class="flex-1 min-w-0">
                        <h3 class="m-0 text-base text-gray-100">{product.name}</h3>
                        {#if product.brand}
                            <p class="m-0 text-gray-300 text-[0.85rem]">
                                {product.brand}
                            </p>
                        {/if}
                        <button
                            type="button"
                            onclick={() =>
                                (editingId =
                                    editingId === product.id ? null : product.id)}
                            class="mt-1 flex items-center gap-1 text-left"
                        >
                            {#if product.category}
                                <span
                                    class="bg-bark-730 text-ink-100 px-2 py-0.5 rounded text-xs border border-bark-600"
                                >
                                    {product.category.name}
                                </span>
                            {:else}
                                <span class="text-gray-300 text-xs"
                                    >{$_('category.none')}</span
                                >
                            {/if}
                            <span class="text-gray-300 text-xs"
                                >{$_('category.change')} ›</span
                            >
                        </button>
                    </div>
                    <div
                        class="stock"
                        class:low={stockState === 'low'}
                        class:out={stockState === 'out'}
                    >
                        {product.stock}
                    </div>
                </div>

                {#if editingId === product.id}
                    <div class="mt-3 pt-3 border-t border-bark-650">
                        <CategoryPicker
                            {categories}
                            selected={product.category}
                            onSelect={(cat) => assignCategory(product, cat)}
                            onCreateAndSelect={(name) => createAndAssign(product, name)}
                            onUpdateIcon={handleUpdateIcon}
                        />
                    </div>
                {/if}
            </div>
        {/each}
    </div>
{/if}

<style>
    .heading-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }

    .search-indicator {
        font-size: 0.78rem;
        color: var(--color-ink-250);
        background: var(--color-ink-900);
        border: 1px solid var(--color-ink-700);
        border-radius: 999px;
        padding: 0.2rem 0.55rem;
        white-space: nowrap;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
    }

    .search-indicator:hover {
        background: var(--color-bark-800);
        color: var(--color-ink-100);
        border-color: var(--color-bark-600);
    }

    .search-indicator-icon {
        font-size: 0.85rem;
        line-height: 1;
    }

    .image-group {
        position: relative;
        flex-shrink: 0;
    }

    .image-btn {
        position: relative;
        cursor: pointer;
        border: none;
        padding: 0;
        background: none;
        border-radius: 0.5rem;
    }

    .camera-btn {
        display: none;
        position: absolute;
        bottom: -4px;
        right: -4px;
        width: 1.3rem;
        height: 1.3rem;
        border-radius: 50%;
        border: none;
        background: rgba(0, 0, 0, 0.75);
        font-size: 0.65rem;
        line-height: 1;
        cursor: pointer;
        align-items: center;
        justify-content: center;
        padding: 0;
    }

    @media (hover: none) {
        .camera-btn {
            display: flex;
        }
    }

    .stock {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--color-success-600);
        min-width: 3rem;
        text-align: center;
    }

    .stock.low {
        color: var(--color-warning-550);
    }

    .stock.out {
        color: var(--color-danger-500);
    }
</style>
