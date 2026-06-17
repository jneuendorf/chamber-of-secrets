<script lang="ts">
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
import { clampQuantity, parseLookupCategory } from '$lib/utils/scan'

// --- Scan / lookup state ---
let lookupResult: EANLookupResult | null = $state(null)
let lookupError = $state('')
let loading = $state(false)

// Brief success toast after saving (auto-clears)
let successToast = $state('')
let toastTimer: ReturnType<typeof setTimeout> | undefined

function showSuccessToast(message: string) {
    successToast = message
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => {
        successToast = ''
    }, 2500)
}

// First interactive element: add/remove mode toggle
let transactionType = $state<'in' | 'out'>('in')

// Mobile-friendly quantity controls
let quantity = $state(1)

// Optional price, prefilled from last transaction if available
let unitPrice = $state<number | undefined>(undefined)

// Manual barcode visibility: hidden by default, auto-shown on lookup failure
let manualVisible = $state(false)

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

    if (!categorySuggestionName) { return }

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

    if (categoryDismissed || !categorySuggestionName) { return null }
    if (matchedCategory) { return matchedCategory }

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
        if (!existing) { return undefined }

        const txns = await api.transactions.list(existing.id)
        const priced = txns.find((t: Transaction) => typeof t.unit_price === 'number')
        return priced?.unit_price ?? undefined
    } catch {
        return undefined
    }
}

async function handleScan(code: string) {
    loading = true
    lookupError = ''
    lookupResult = null
    quantity = 1
    unitPrice = undefined
    categorySuggestionName = null
    matchedCategory = null
    categoryDismissed = false
    selectedCategoryId = 'none'

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
    if (!lookupResult) { return }
    loading = true

    try {
        const products = await api.products.list()
        const existing = products.find((p: Product) => p.ean === lookupResult!.ean)

        const resolvedCategory = await resolveCategoryForSave()

        const product =
            existing ??
            (await api.products.create({
                ean: lookupResult.ean,
                name: lookupResult.name ?? get(_)('scan.unknownProduct'),
                brand: lookupResult.brand,
                image_url: lookupResult.image_url,
                category_id: resolvedCategory?.id ?? null,
            }))

        if (
            existing &&
            selectedCategoryId !== 'none' &&
            existing.category_id !== selectedCategoryId
        ) {
            await api.products.update(existing.id, { category_id: selectedCategoryId })
        }

        await api.transactions.create({
            product_id: product.id,
            type: transactionType,
            quantity,
            unit_price: unitPrice,
        })

        showSuccessToast(
            get(_)(
                transactionType === 'in'
                    ? 'scan.addedSuccess'
                    : 'scan.removedSuccess',
            ),
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
        <div class="success-toast">{successToast}</div>
    {/if}

    <!-- 1) First interactive element: mode toggle -->
    <div class="bg-[#2f2a22] border border-[#5b4f3a] rounded-xl p-2 shadow-sm mb-4">
        <div class="grid grid-cols-2 gap-2">
            <button
                type="button"
                onclick={() => (transactionType = "in")}
                class={`h-9 px-3 rounded-lg text-xs font-semibold transition inline-flex items-center justify-center gap-1.5 ${
                    transactionType === "in"
                        ? "bg-[#1f9d55] text-white"
                        : "bg-[#111827] text-[#86efac] border border-[#14532d]"
                }`}
                aria-pressed={transactionType === "in" ? "true" : "false"}
            >
                <span aria-hidden="true">+</span>
                <span>{$_("scan.modeAdd")}</span>
            </button>
            <button
                type="button"
                onclick={() => (transactionType = "out")}
                class={`h-9 px-3 rounded-lg text-xs font-semibold transition inline-flex items-center justify-center gap-1.5 ${
                    transactionType === "out"
                        ? "bg-[#e74c3c] text-white"
                        : "bg-[#111827] text-[#fca5a5] border border-[#7f1d1d]"
                }`}
                aria-pressed={transactionType === "out" ? "true" : "false"}
            >
                <span aria-hidden="true">−</span>
                <span>{$_("scan.modeRemove")}</span>
            </button>
        </div>
    </div>
    <BarcodeScanner onScan={handleScan} bind:manualVisible restartSignal={scannerRestartSignal} />

    {#if loading}
        <p class="text-center my-4">{$_("scan.lookingUp")}</p>
    {/if}

    {#if lookupError}
        <p class="text-center my-4 text-[#e74c3c]">{lookupError}</p>
    {/if}

    {#if lookupResult}
        <div
            class="bg-[#2f2a22] border border-[#5b4f3a] rounded-xl p-4 sm:p-6 mt-6 shadow-sm relative text-gray-100"
        >
            <button
                type="button"
                onclick={dismissScannedItem}
                class="absolute top-2 right-2 h-6 w-6 rounded-full bg-[#26221b] text-gray-300 hover:bg-[#201c16] hover:text-gray-100 border border-[#4f4534] inline-flex items-center justify-center"
                aria-label={$_("scan.dismissScanned")}
                title={$_("scan.dismissScanned")}
            >
                ✕
            </button>
            {#if lookupResult.image_url}
                <img
                    src={lookupResult.image_url}
                    alt={lookupResult.name ?? $_("scan.product")}
                    class="w-20 h-20 sm:w-24 sm:h-24 object-contain rounded-lg float-right ml-3 sm:ml-4 mb-2 mr-4"
                />
            {/if}

            <div>
                <h2 class="mt-0 mb-1">{lookupResult.name ?? $_("common.unknown")}</h2>
                {#if lookupResult.brand}
                    <p class="text-gray-300 m-0">{lookupResult.brand}</p>
                {/if}
                <p class="font-mono text-gray-400 text-[0.65rem]">EAN: {lookupResult.ean}</p>

                {#if categorySuggestionName}
                    <div class="m-0 mt-1 text-xs text-gray-300 flex items-center gap-2 flex-wrap">
                        <span>
                            Category:
                            <strong>
                                {matchedCategory ? matchedCategory.name : categorySuggestionName}
                            </strong>
                            {#if !matchedCategory}
                                <span>(new)</span>
                            {/if}
                        </span>
                        <button
                            type="button"
                            onclick={dismissCategorySuggestion}
                            class="h-5 w-5 rounded-full bg-[#26221b] text-gray-300 hover:bg-[#201c16] hover:text-gray-100 border border-[#4f4534] inline-flex items-center justify-center"
                            aria-label={$_("scan.dismissCategory")}
                            title={$_("scan.dismissCategory")}
                        >
                            ✕
                        </button>
                    </div>
                {/if}
            </div>

            <div class="flex flex-col gap-4 mt-4 clear-both">
                <!-- Category picker (prominent, first action after scan) -->
                <div class="flex flex-col gap-1.5">
                    <span class="text-sm text-gray-200">
                        {$_("scan.categoryLabel")}
                        {#if !selectedCategory && !categorySuggestionName}
                            <span class="category-prompt">
                                — {$_("scan.categoryPrompt")}
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
                <label class="flex flex-col gap-2 text-sm text-gray-200">
                    <span>{$_("scan.quantity")}</span>

                    <div class="flex items-center gap-2">
                        <button
                            type="button"
                            onclick={decrementQuantity}
                            class="h-11 w-11 shrink-0 rounded-lg border border-[#5b4f3a] bg-[#26221b] text-xl leading-none"
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
                            class="h-11 flex-1 text-center px-2 border border-[#5b4f3a] bg-[#26221b] text-gray-100 rounded-md text-base"
                        />

                        <button
                            type="button"
                            onclick={incrementQuantity}
                            class="h-11 w-11 shrink-0 rounded-lg border border-[#5b4f3a] bg-[#26221b] text-xl leading-none"
                            aria-label="Increase quantity"
                        >
                            +
                        </button>
                    </div>
                </label>

                <!-- Optional unit price, prefills from last txn -->
                <label class="flex flex-col gap-1 text-sm text-gray-200">
                    {$_("scan.unitPrice")}
                    <input
                        type="number"
                        bind:value={unitPrice}
                        min="0"
                        step="0.01"
                        inputmode="decimal"
                        placeholder={$_("scan.pricePlaceholder")}
                        class="px-2 py-2 border border-[#5b4f3a] bg-[#26221b] text-gray-100 rounded-md text-base"
                    />
                </label>

                <button
                    type="button"
                    onclick={saveInventoryTransaction}
                    disabled={loading}
                    class="p-3 bg-[#1a1a2e] text-white border-0 rounded-lg text-base cursor-pointer disabled:opacity-50"
                >
                    {transactionType === "in" ? $_("scan.addBtn") : $_("scan.removeBtn")}
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
        color: #f59e0b;
        font-style: italic;
    }

    .success-toast {
        background: #166534;
        color: #bbf7d0;
        text-align: center;
        padding: 0.5rem 1rem;
        border-radius: 0.75rem;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        animation: toast-in 0.3s ease-out;
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
