<script lang="ts">
    import { get } from "svelte/store";
    import { _ } from "svelte-i18n";
    import BarcodeScanner from "$lib/components/BarcodeScanner.svelte";
    import {
        api,
        type Category,
        type EANLookupResult,
        type Product,
        type Transaction,
    } from "$lib/api/client";

    // --- Scan / lookup state ---
    let lookupResult: EANLookupResult | null = $state(null);
    let lookupError = $state("");
    let loading = $state(false);
    let added = $state(false);

    // First interactive element: add/remove mode toggle
    let transactionType = $state<"in" | "out">("in");

    // Mobile-friendly quantity controls
    let quantity = $state(1);

    // Optional price, prefilled from last transaction if available
    let unitPrice = $state<number | undefined>(undefined);

    // Manual barcode visibility: hidden by default, auto-shown on lookup failure
    let manualVisible = $state(false);

    // Lightweight category auto-match from fetched lookup category text
    let categorySuggestionName = $state<string | null>(null);
    let matchedCategory: Category | null = $state(null);
    let categoryDismissed = $state(false);

    function clampQuantity(value: number): number {
        if (!Number.isFinite(value)) return 1;
        return Math.max(1, Math.round(value));
    }

    function decrementQuantity() {
        quantity = clampQuantity(quantity - 1);
    }

    function incrementQuantity() {
        quantity = clampQuantity(quantity + 1);
    }

    function updateQuantityFromInput(raw: string) {
        const parsed = Number(raw);
        quantity = clampQuantity(parsed);
    }

    function parseLookupCategory(raw: string | null | undefined): string | null {
        if (!raw) return null;
        const parts = raw
            .split(",")
            .map((p) => p.trim())
            .filter(Boolean)
            .map((p) => p.replace(/^[a-z]{2}:/i, ""))
            .filter(Boolean);

        if (parts.length === 0) return null;

        const candidate = parts[parts.length - 1].trim();
        if (!candidate) return null;

        return candidate.charAt(0).toUpperCase() + candidate.slice(1);
    }

    async function resolveCategoryFromLookup(rawCategory: string | null | undefined) {
        categorySuggestionName = parseLookupCategory(rawCategory);
        matchedCategory = null;
        categoryDismissed = false;

        if (!categorySuggestionName) return;

        const categories = await api.categories.list();
        matchedCategory =
            categories.find(
                (c) => c.name.trim().toLowerCase() === categorySuggestionName!.trim().toLowerCase(),
            ) ?? null;
    }

    function dismissCategorySuggestion() {
        categoryDismissed = true;
        categorySuggestionName = null;
        matchedCategory = null;
    }

    async function resolveCategoryForSave(): Promise<Category | null> {
        if (categoryDismissed || !categorySuggestionName) return null;
        if (matchedCategory) return matchedCategory;

        const created = await api.categories.create({ name: categorySuggestionName });
        matchedCategory = created;
        return created;
    }

    async function lookupLastUnitPriceByEAN(ean: string): Promise<number | undefined> {
        // Best effort:
        // 1) find existing product by EAN from product list
        // 2) fetch latest transactions for that product
        // 3) use first transaction with non-null unit_price (transactions are returned newest first)
        try {
            const products = await api.products.list();
            const existing = products.find((p: Product) => p.ean === ean);
            if (!existing) return undefined;

            const txns = await api.transactions.list(existing.id);
            const priced = txns.find((t: Transaction) => typeof t.unit_price === "number");
            return priced?.unit_price ?? undefined;
        } catch {
            return undefined;
        }
    }

    async function handleScan(code: string) {
        loading = true;
        lookupError = "";
        lookupResult = null;
        added = false;
        unitPrice = undefined;
        categorySuggestionName = null;
        matchedCategory = null;
        categoryDismissed = false;

        try {
            const result = await api.products.lookupEAN(code);
            lookupResult = result;

            // Prefill unit price from last scan/transaction of same product (if any)
            unitPrice = await lookupLastUnitPriceByEAN(result.ean);

            // Lightweight category extraction + local exact-name match
            await resolveCategoryFromLookup(result.category);
        } catch {
            lookupError = get(_)("scan.notFound", { values: { code } });
            manualVisible = true; // show manual input when fetch fails
        } finally {
            loading = false;
        }
    }

    async function saveInventoryTransaction() {
        if (!lookupResult) return;
        loading = true;

        try {
            const products = await api.products.list();
            const existing = products.find((p: Product) => p.ean === lookupResult!.ean);

            const product =
                existing ??
                (await api.products.create({
                    ean: lookupResult.ean,
                    name: lookupResult.name ?? get(_)("scan.unknownProduct"),
                    brand: lookupResult.brand,
                    image_url: lookupResult.image_url,
                    category_id: (await resolveCategoryForSave())?.id ?? null,
                }));

            await api.transactions.create({
                product_id: product.id,
                type: transactionType,
                quantity,
                unit_price: unitPrice,
            });

            added = true;
        } catch (e) {
            lookupError = get(_)("scan.failedToAdd", { values: { error: String(e) } });
        } finally {
            loading = false;
        }
    }

    function dismissScannedItem() {
        lookupResult = null;
        lookupError = "";
        added = false;
        quantity = 1;
        unitPrice = undefined;
        categorySuggestionName = null;
        matchedCategory = null;
        categoryDismissed = false;
    }

    function scanNext() {
        dismissScannedItem();
    }
</script>

<div class="scan-root">
    <!-- 1) First interactive element: mode toggle -->
    <div class="bg-white rounded-xl p-2 shadow-sm mb-4">
        <div class="grid grid-cols-2 gap-2">
            <button
                type="button"
                onclick={() => (transactionType = "in")}
                class={`h-9 px-3 rounded-lg text-xs font-semibold transition inline-flex items-center justify-center gap-1.5 ${
                    transactionType === "in"
                        ? "bg-[#1f9d55] text-white"
                        : "bg-emerald-50 text-[#166534] border border-emerald-200"
                }`}
                aria-pressed={transactionType === "in"}
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
                        : "bg-red-50 text-[#c0392b] border border-red-200"
                }`}
                aria-pressed={transactionType === "out"}
            >
                <span aria-hidden="true">−</span>
                <span>{$_("scan.modeRemove")}</span>
            </button>
        </div>
    </div>
    <BarcodeScanner onScan={handleScan} bind:manualVisible />

    {#if loading}
        <p class="text-center my-4">{$_("scan.lookingUp")}</p>
    {/if}

    {#if lookupError}
        <p class="text-center my-4 text-[#e74c3c]">{lookupError}</p>
    {/if}

    {#if lookupResult}
        <div class="bg-white rounded-xl p-4 sm:p-6 mt-6 shadow-sm relative">
            {#if !added}
                <button
                    type="button"
                    onclick={dismissScannedItem}
                    class="absolute top-2 right-2 h-6 w-6 rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700 border border-gray-200 inline-flex items-center justify-center"
                    aria-label={$_("scan.dismissScanned")}
                    title={$_("scan.dismissScanned")}
                >
                    ✕
                </button>
            {/if}
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
                    <p class="text-gray-500 m-0">{lookupResult.brand}</p>
                {/if}
                <p class="font-mono text-gray-400 text-[0.65rem]">EAN: {lookupResult.ean}</p>

                {#if categorySuggestionName}
                    <div class="m-0 mt-1 text-xs text-gray-500 flex items-center gap-2 flex-wrap">
                        <span>
                            Category:
                            <strong>
                                {matchedCategory ? matchedCategory.name : categorySuggestionName}
                            </strong>
                            {#if !matchedCategory}
                                <span>(new)</span>
                            {/if}
                        </span>
                        {#if !added}
                            <button
                                type="button"
                                onclick={dismissCategorySuggestion}
                                class="h-5 w-5 rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700 border border-gray-200 inline-flex items-center justify-center"
                                aria-label={$_("scan.dismissCategory")}
                                title={$_("scan.dismissCategory")}
                            >
                                ✕
                            </button>
                        {/if}
                    </div>
                {/if}
            </div>

            {#if !added}
                <div class="flex flex-col gap-4 mt-4 clear-both">
                    <!-- 3) Mobile-friendly quantity stepper -->
                    <label class="flex flex-col gap-2 text-sm text-[#555]">
                        <span>{$_("scan.quantity")}</span>

                        <div class="flex items-center gap-2">
                            <button
                                type="button"
                                onclick={decrementQuantity}
                                class="h-11 w-11 shrink-0 rounded-lg border border-gray-300 bg-gray-100 text-xl leading-none"
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
                                class="h-11 flex-1 text-center px-2 border border-gray-300 rounded-md text-base"
                            />

                            <button
                                type="button"
                                onclick={incrementQuantity}
                                class="h-11 w-11 shrink-0 rounded-lg border border-gray-300 bg-gray-100 text-xl leading-none"
                                aria-label="Increase quantity"
                            >
                                +
                            </button>
                        </div>
                    </label>

                    <!-- 4) Optional unit price, prefills from last txn -->
                    <label class="flex flex-col gap-1 text-sm text-[#555]">
                        {$_("scan.unitPrice")}
                        <input
                            type="number"
                            bind:value={unitPrice}
                            min="0"
                            step="0.01"
                            inputmode="decimal"
                            placeholder={$_("scan.pricePlaceholder")}
                            class="px-2 py-2 border border-gray-300 rounded-md text-base"
                        />
                    </label>

                    <button
                        onclick={saveInventoryTransaction}
                        disabled={loading}
                        class="p-3 bg-[#1a1a2e] text-white border-0 rounded-lg text-base cursor-pointer disabled:opacity-50"
                    >
                        {transactionType === "in" ? $_("scan.addBtn") : $_("scan.removeBtn")}
                    </button>
                </div>
            {:else}
                <div class="text-center my-4">
                    <p class="text-[#27ae60] font-semibold mb-3">
                        {transactionType === "in"
                            ? $_("scan.addedSuccess")
                            : $_("scan.removedSuccess")}
                    </p>
                    <button
                        onclick={scanNext}
                        class="px-6 py-2 bg-[#1a1a2e] text-white rounded-lg text-sm cursor-pointer"
                    >
                        {$_("scan.scanNext")}
                    </button>
                </div>
            {/if}
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
</style>
