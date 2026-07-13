<script lang="ts">
    import { tick } from 'svelte'
    import { get } from 'svelte/store'
    import { _ } from 'svelte-i18n'

    import {
        ApiError,
        api,
        type Category,
        type EANLookupResult,
        type Product,
        type Transaction,
    } from '$lib/api/client'
    import BarcodeScanner from '$lib/components/BarcodeScanner.svelte'
    import CategoryPicker from '$lib/components/CategoryPicker.svelte'
    import {
        buildProductPayload,
        clampQuantity,
        isPlausibleBarcode,
        parseLookupCategory,
    } from '$lib/utils/scan'

    // --- Scan / lookup state ---
    let lookupResult = $state<EANLookupResult | null>(null)
    let lookupError = $state('')
    let loading = $state(false)

    // Brief success toast after saving (auto-clears). When a transaction was
    // just recorded, undoTxnId enables one-tap undo (WL-4.2).
    let successToast = $state('')
    let undoTxnId = $state<number | null>(null)
    let toastTimer: ReturnType<typeof setTimeout> | undefined

    function showSuccessToast(message: string, txnId: number | null = null) {
        successToast = message
        undoTxnId = txnId
        clearTimeout(toastTimer)
        toastTimer = setTimeout(
            () => {
                successToast = ''
                undoTxnId = null
            },
            txnId ? 5000 : 2500,
        )
    }

    async function undoLastTransaction() {
        if (undoTxnId === null) {
            return
        }
        const id = undoTxnId
        undoTxnId = null
        try {
            await api.transactions.delete(id)
            showSuccessToast(get(_)('scan.undone'))
        } catch (e) {
            lookupError = get(_)('scan.failedToAdd', {
                values: { error: e instanceof ApiError ? e.detail : String(e) },
            })
        }
    }

    // First interactive element: add/remove mode toggle
    let transactionType = $state<'in' | 'out'>('in')

    // Mobile-friendly quantity controls
    let quantity = $state(1)

    // Optional price, prefilled from last transaction if available
    let unitPrice = $state<number | undefined>(undefined)

    // Manual barcode visibility: hidden by default, auto-shown on lookup failure
    let manualVisible = $state(false)

    // Manual product entry (WL-4.1): create a product with no Open Food Facts
    // match. Reuses the lookup-result card by treating lookupResult as an
    // editable draft. lastScannedCode seeds the EAN when entry is triggered
    // from a failed scan; blank for keyboard-free "add manually" (loose produce).
    let manualMode = $state(false)
    let lastScannedCode = $state('')
    let manualNameEl: HTMLInputElement | undefined = $state()

    // WL-4.6: opt-in contribute-back to Open Food Facts. Offered only when a
    // real (barcode-keyed) EAN missed OFF. Default off — never auto-submit.
    let contributeToOff = $state(false)
    let canContribute = $derived(
        manualMode && isPlausibleBarcode((lookupResult?.ean ?? '').trim()),
    )

    // Category suggestion + user override
    let categorySuggestionName = $state<string | null>(null)
    let matchedCategory: Category | null = $state(null)
    let categoryDismissed = $state(false)
    let categories = $state<Category[]>([])
    let selectedCategoryId = $state<number | 'none'>('none')
    let selectedCategory = $derived(
        selectedCategoryId !== 'none'
            ? (categories.find((c) => c.id === selectedCategoryId) ?? null)
            : null,
    )
    let scannerRestartSignal = $state(0)

    let manualNameValid = $derived(
        !manualMode || (lookupResult?.name ?? '').trim().length > 0,
    )

    async function enterManualMode(ean: string) {
        lookupError = ''
        lookupResult = { ean, name: '', brand: null, image_url: null, category: null }
        manualMode = true
        contributeToOff = false
        quantity = 1
        unitPrice = undefined
        categorySuggestionName = null
        matchedCategory = null
        categoryDismissed = false
        selectedCategoryId = 'none'
        await tick()
        manualNameEl?.focus()
        categories = await api.categories.list()
    }

    function decrementQuantity() {
        quantity = clampQuantity(quantity - 1)
    }

    function incrementQuantity() {
        quantity = clampQuantity(quantity + 1)
    }

    function updateQuantityFromInput(raw: string) {
        const parsed = Number(raw)
        quantity = clampQuantity(parsed)
    }

    async function resolveCategoryFromLookup(rawCategory: string | null | undefined) {
        categorySuggestionName = parseLookupCategory(rawCategory)
        matchedCategory = null
        categoryDismissed = false
        selectedCategoryId = 'none'

        categories = await api.categories.list()

        if (!categorySuggestionName) {
            return
        }

        matchedCategory =
            categories.find(
                (c) =>
                    c.name.trim().toLowerCase() ===
                    categorySuggestionName!.trim().toLowerCase(),
            ) ?? null

        if (matchedCategory) {
            selectedCategoryId = matchedCategory.id
        }
    }

    function dismissCategorySuggestion() {
        categoryDismissed = true
        categorySuggestionName = null
        matchedCategory = null
        selectedCategoryId = 'none'
    }

    function handleCategorySelect(cat: Category | null) {
        if (cat) {
            selectedCategoryId = cat.id
            categoryDismissed = false
        } else {
            selectedCategoryId = 'none'
        }
    }

    async function handleCategoryCreateAndSelect(name: string) {
        const created = await api.categories.create({ name })
        categories = [...categories, created]
        selectedCategoryId = created.id
        categoryDismissed = false
    }

    async function resolveCategoryForSave(): Promise<Category | null> {
        if (selectedCategoryId !== 'none') {
            return categories.find((c) => c.id === selectedCategoryId) ?? null
        }

        if (categoryDismissed || !categorySuggestionName) {
            return null
        }
        if (matchedCategory) {
            return matchedCategory
        }

        const created = await api.categories.create({ name: categorySuggestionName })
        matchedCategory = created
        categories = [...categories, created]
        return created
    }

    async function lookupLastUnitPriceByEAN(ean: string): Promise<number | undefined> {
        // Best effort:
        // 1) find existing product by EAN from product list
        // 2) fetch latest transactions for that product
        // 3) use first transaction with non-null unit_price (transactions are returned newest first)
        try {
            const products = await api.products.list()
            const existing = products.find((p: Product) => p.ean === ean)
            if (!existing) {
                return undefined
            }

            const txns = await api.transactions.list(existing.id)
            const priced = txns.find(
                (t: Transaction) => typeof t.unit_price === 'number',
            )
            return priced?.unit_price ?? undefined
        } catch {
            return undefined
        }
    }

    async function handleScan(code: string) {
        loading = true
        lookupError = ''
        lookupResult = null
        manualMode = false
        contributeToOff = false
        lastScannedCode = code
        quantity = 1
        unitPrice = undefined
        categorySuggestionName = null
        matchedCategory = null
        categoryDismissed = false
        selectedCategoryId = 'none'

        // Don't ask Open Food Facts about implausible codes — short/typo
        // barcodes only return placeholder junk. Treat like a not-found so the
        // user drops straight into manual entry with the number pre-filled.
        if (!isPlausibleBarcode(code)) {
            lookupError = get(_)('scan.notFound', { values: { code } })
            manualVisible = true
            loading = false
            return
        }

        try {
            const result = await api.products.lookupEAN(code)
            lookupResult = result

            // Prefill unit price from last scan/transaction of same product (if any)
            unitPrice = await lookupLastUnitPriceByEAN(result.ean)

            // Lightweight category extraction + local exact-name match
            await resolveCategoryFromLookup(result.category)
        } catch (e) {
            if (e instanceof ApiError && e.isNotFound) {
                lookupError = get(_)('scan.notFound', { values: { code } })
            } else {
                const detail = e instanceof ApiError ? e.detail : String(e)
                lookupError = get(_)('scan.lookupError', { values: { error: detail } })
            }
            manualVisible = true
        } finally {
            loading = false
        }
    }

    async function saveInventoryTransaction() {
        if (!lookupResult) {
            return
        }
        loading = true

        try {
            const products = await api.products.list()
            // Only dedup on a real EAN; blank-EAN manual products must not
            // collapse into one another.
            const existing = lookupResult.ean
                ? products.find((p: Product) => p.ean === lookupResult!.ean)
                : undefined

            const resolvedCategory = await resolveCategoryForSave()

            const product =
                existing ??
                (await api.products.create(
                    buildProductPayload(
                        lookupResult,
                        get(_)('scan.unknownProduct'),
                        resolvedCategory?.id ?? null,
                    ),
                ))

            if (
                existing &&
                selectedCategoryId !== 'none' &&
                existing.category_id !== selectedCategoryId
            ) {
                await api.products.update(existing.id, {
                    category_id: selectedCategoryId,
                })
            }

            const created = await api.transactions.create({
                product_id: product.id,
                type: transactionType,
                quantity,
                unit_price: unitPrice,
            })

            // WL-4.6: opt-in contribute-back — only for a freshly created,
            // barcode-keyed manual product. Best-effort: a rejection must not
            // fail the save the user already completed.
            if (!existing && contributeToOff && isPlausibleBarcode(product.ean ?? '')) {
                try {
                    await api.products.contribute(product.id)
                } catch {
                    /* non-fatal: product is stored locally regardless */
                }
            }

            showSuccessToast(
                get(_)(
                    transactionType === 'in'
                        ? 'scan.addedSuccess'
                        : 'scan.removedSuccess',
                ),
                created.id,
            )
            scannerRestartSignal += 1
            scanNext()
        } catch (e) {
            const detail = e instanceof ApiError ? e.detail : String(e)
            lookupError = get(_)('scan.failedToAdd', { values: { error: detail } })
        } finally {
            loading = false
        }
    }

    function dismissScannedItem() {
        lookupResult = null
        lookupError = ''
        manualMode = false
        contributeToOff = false
        quantity = 1
        unitPrice = undefined
        categorySuggestionName = null
        matchedCategory = null
        categoryDismissed = false
    }

    function scanNext() {
        dismissScannedItem()
        manualVisible = false
    }
</script>

<div class="scan-root">
    {#if successToast}
        <div class="success-toast">
            <span>{successToast}</span>
            {#if undoTxnId !== null}
                <button type="button" class="toast-undo" onclick={undoLastTransaction}>
                    {$_('scan.undo')}
                </button>
            {/if}
        </div>
    {/if}

    <!-- 1) First interactive element: mode toggle -->
    <div class="bg-bark-800 border border-bark-600 rounded-xl p-2 shadow-sm mb-4">
        <div class="grid grid-cols-2 gap-2">
            <button
                type="button"
                onclick={() => (transactionType = 'in')}
                class={`h-9 px-3 rounded-lg text-xs font-semibold transition inline-flex items-center justify-center gap-1.5 ${
                    transactionType === 'in'
                        ? 'bg-success-700 text-white'
                        : 'bg-ink-900 text-success-300 border border-success-900'
                }`}
                aria-pressed={transactionType === 'in' ? 'true' : 'false'}
            >
                <span aria-hidden="true">+</span>
                <span>{$_('scan.modeAdd')}</span>
            </button>
            <button
                type="button"
                onclick={() => (transactionType = 'out')}
                class={`h-9 px-3 rounded-lg text-xs font-semibold transition inline-flex items-center justify-center gap-1.5 ${
                    transactionType === 'out'
                        ? 'bg-danger-500 text-white'
                        : 'bg-ink-900 text-danger-200 border border-danger-900'
                }`}
                aria-pressed={transactionType === 'out' ? 'true' : 'false'}
            >
                <span aria-hidden="true">−</span>
                <span>{$_('scan.modeRemove')}</span>
            </button>
        </div>
    </div>
    <BarcodeScanner
        onScan={handleScan}
        bind:manualVisible
        restartSignal={scannerRestartSignal}
    />

    {#if !lookupResult && !loading && !lookupError}
        <button
            type="button"
            onclick={() => enterManualMode('')}
            class="w-full mt-6 p-2.5 text-sm text-ink-250 bg-bark-800 border border-bark-600 rounded-lg hover:text-ink-100 hover:border-bark-500"
        >
            {$_('scan.addManually')}
        </button>
    {/if}

    {#if loading}
        <p class="text-center my-4">{$_('scan.lookingUp')}</p>
    {/if}

    {#if lookupError}
        <div class="text-center my-4">
            <p class="text-danger-500">{lookupError}</p>
            <button
                type="button"
                onclick={() => enterManualMode(lastScannedCode)}
                class="w-full mt-3 p-2.5 text-sm text-ink-250 bg-bark-800 border border-bark-600 rounded-lg hover:text-ink-100 hover:border-bark-500"
            >
                {$_('scan.createManually')}
            </button>
        </div>
    {/if}

    {#if lookupResult}
        <div
            class="bg-bark-800 border border-bark-600 rounded-xl p-4 sm:p-6 mt-6 shadow-sm relative text-ink-100"
        >
            <button
                type="button"
                onclick={dismissScannedItem}
                class="absolute top-2 right-2 h-6 w-6 rounded-full bg-bark-850 text-ink-250 hover:bg-bark-900 hover:text-ink-100 border border-bark-650 inline-flex items-center justify-center"
                aria-label={$_('scan.dismissScanned')}
                title={$_('scan.dismissScanned')}
            >
                ✕
            </button>
            {#if lookupResult.image_url}
                <img
                    src={lookupResult.image_url}
                    alt={lookupResult.name ?? $_('scan.product')}
                    class="w-20 h-20 sm:w-24 sm:h-24 object-contain rounded-lg float-right ml-3 sm:ml-4 mb-2 mr-4"
                />
            {/if}

            {#if manualMode}
                <div class="flex flex-col gap-2">
                    <h2 class="mt-0 mb-0 text-base text-ink-250">
                        {$_('scan.manualTitle')}
                    </h2>
                    <input
                        type="text"
                        bind:this={manualNameEl}
                        bind:value={lookupResult.name}
                        placeholder={$_('scan.manualNamePlaceholder')}
                        class="px-2 py-2 border border-bark-600 bg-bark-850 text-ink-100 rounded-md text-base"
                    />
                    <input
                        type="text"
                        bind:value={lookupResult.brand}
                        placeholder={$_('scan.manualBrandPlaceholder')}
                        class="px-2 py-2 border border-bark-600 bg-bark-850 text-ink-100 rounded-md text-sm"
                    />
                    <input
                        type="url"
                        bind:value={lookupResult.image_url}
                        placeholder={$_('scan.manualImagePlaceholder')}
                        class="px-2 py-2 border border-bark-600 bg-bark-850 text-ink-100 rounded-md text-sm"
                    />
                    <input
                        type="text"
                        inputmode="numeric"
                        bind:value={lookupResult.ean}
                        placeholder={$_('scan.manualEanPlaceholder')}
                        class="px-2 py-2 border border-bark-600 bg-bark-850 text-ink-100 rounded-md text-sm font-mono"
                    />
                    {#if canContribute}
                        <label class="flex items-start gap-2 text-sm text-ink-200 mt-1">
                            <input
                                type="checkbox"
                                bind:checked={contributeToOff}
                                class="mt-0.5 h-4 w-4 shrink-0 accent-accent-700"
                            />
                            <span>
                                {$_('scan.contributeOff')}
                                <span class="block text-xs text-ink-400">
                                    {$_('scan.contributeOffHint')}
                                </span>
                            </span>
                        </label>
                    {/if}
                </div>
            {:else}
                <div>
                    <h2 class="mt-0 mb-1">
                        {lookupResult.name ?? $_('common.unknown')}
                    </h2>
                    {#if lookupResult.brand}
                        <p class="text-ink-250 m-0">{lookupResult.brand}</p>
                    {/if}
                    <p class="font-mono text-ink-400 text-[0.65rem]">
                        EAN: {lookupResult.ean}
                    </p>

                    {#if categorySuggestionName}
                        <div
                            class="m-0 mt-1 text-xs text-ink-250 flex items-center gap-2 flex-wrap"
                        >
                            <span>
                                {$_('scan.suggestedCategory')}
                                <strong>
                                    {matchedCategory
                                        ? matchedCategory.name
                                        : categorySuggestionName}
                                </strong>
                                {#if !matchedCategory}
                                    <span>{$_('scan.categoryNew')}</span>
                                {/if}
                            </span>
                            <button
                                type="button"
                                onclick={dismissCategorySuggestion}
                                class="h-5 w-5 rounded-full bg-bark-850 text-ink-250 hover:bg-bark-900 hover:text-ink-100 border border-bark-650 inline-flex items-center justify-center"
                                aria-label={$_('scan.dismissCategory')}
                                title={$_('scan.dismissCategory')}
                            >
                                ✕
                            </button>
                        </div>
                    {/if}
                </div>
            {/if}

            <div class="flex flex-col gap-4 mt-4 clear-both">
                <!-- Category picker (prominent, first action after scan) -->
                <div class="flex flex-col gap-1.5">
                    <span class="text-sm text-ink-200">
                        {$_('scan.categoryLabel')}
                        {#if !selectedCategory && !categorySuggestionName}
                            <span class="category-prompt">
                                — {$_('scan.categoryPrompt')}
                            </span>
                        {/if}
                    </span>
                    <CategoryPicker
                        {categories}
                        selected={selectedCategory}
                        onSelect={handleCategorySelect}
                        onCreateAndSelect={handleCategoryCreateAndSelect}
                    />
                </div>

                <!-- Mobile-friendly quantity stepper -->
                <label class="flex flex-col gap-2 text-sm text-ink-200">
                    <span>{$_('scan.quantity')}</span>

                    <div class="flex items-center gap-2">
                        <button
                            type="button"
                            onclick={decrementQuantity}
                            class="h-11 w-11 shrink-0 rounded-lg border border-bark-600 bg-bark-850 text-xl leading-none"
                            aria-label="Decrease quantity"
                        >
                            −
                        </button>

                        <input
                            type="number"
                            min="1"
                            step="1"
                            inputmode="numeric"
                            value={quantity}
                            oninput={(e) =>
                                updateQuantityFromInput(
                                    (e.currentTarget as HTMLInputElement).value,
                                )}
                            class="h-11 flex-1 text-center px-2 border border-bark-600 bg-bark-850 text-ink-100 rounded-md text-base"
                        />

                        <button
                            type="button"
                            onclick={incrementQuantity}
                            class="h-11 w-11 shrink-0 rounded-lg border border-bark-600 bg-bark-850 text-xl leading-none"
                            aria-label="Increase quantity"
                        >
                            +
                        </button>
                    </div>
                </label>

                <!-- Optional unit price, prefills from last txn -->
                <label class="flex flex-col gap-1 text-sm text-ink-200">
                    {$_('scan.unitPrice')}
                    <input
                        type="number"
                        bind:value={unitPrice}
                        min="0"
                        step="0.01"
                        inputmode="decimal"
                        placeholder={$_('scan.pricePlaceholder')}
                        class="px-2 py-2 border border-bark-600 bg-bark-850 text-ink-100 rounded-md text-base"
                    />
                </label>

                <button
                    type="button"
                    onclick={saveInventoryTransaction}
                    disabled={loading || !manualNameValid}
                    class="p-3 bg-accent-900 text-white border-0 rounded-lg text-base cursor-pointer disabled:opacity-50"
                >
                    {transactionType === 'in'
                        ? $_('scan.addBtn')
                        : $_('scan.removeBtn')}
                </button>
            </div>
        </div>
    {/if}
</div>

<style>
    .scan-root {
        width: 100%;
        max-width: 640px;
        margin-left: auto;
        margin-right: auto;
    }

    .category-prompt {
        color: var(--color-warning-500);
        font-style: italic;
    }

    .success-toast {
        background: var(--color-success-800);
        color: var(--color-success-100);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        text-align: center;
        padding: 0.5rem 1rem;
        border-radius: 0.75rem;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
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

    @keyframes toast-in {
        from {
            opacity: 0;
            transform: translateY(-0.5rem);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>
