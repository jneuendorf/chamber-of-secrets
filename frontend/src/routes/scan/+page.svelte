<script lang="ts">
    import { get } from "svelte/store";
    import { _ } from "svelte-i18n";
    import BarcodeScanner from "$lib/components/BarcodeScanner.svelte";
    import { api, type EANLookupResult, type Product, type Transaction } from "$lib/api/client";

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

        try {
            const result = await api.products.lookupEAN(code);
            lookupResult = result;

            // Prefill unit price from last scan/transaction of same product (if any)
            unitPrice = await lookupLastUnitPriceByEAN(result.ean);
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
                    category_id: null,
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

    function scanNext() {
        lookupResult = null;
        lookupError = "";
        added = false;
        // keep chosen mode as user preference for the next scan
        quantity = 1;
        unitPrice = undefined;
    }
</script>

<div class="scan-shell">
    <!-- 1) First interactive element: mode toggle -->
    <div class="scan-mode-toggle bg-white rounded-xl p-2 shadow-sm mb-4">
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
</div>

<BarcodeScanner onScan={handleScan} bind:manualVisible />

{#if loading}
    <p class="text-center my-4">{$_("scan.lookingUp")}</p>
{/if}

{#if lookupError}
    <p class="text-center my-4 text-[#e74c3c]">{lookupError}</p>
{/if}

{#if lookupResult}
    <div class="bg-white rounded-xl p-4 sm:p-6 mt-6 shadow-sm">
        {#if lookupResult.image_url}
            <img
                src={lookupResult.image_url}
                alt={lookupResult.name ?? $_("scan.product")}
                class="w-20 h-20 sm:w-24 sm:h-24 object-contain rounded-lg float-right ml-3 sm:ml-4 mb-2"
            />
        {/if}

        <div>
            <h2 class="mt-0 mb-1">{lookupResult.name ?? $_("common.unknown")}</h2>
            {#if lookupResult.brand}
                <p class="text-gray-500 m-0">{lookupResult.brand}</p>
            {/if}
            <p class="font-mono text-gray-400 text-[0.65rem]">EAN: {lookupResult.ean}</p>
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
                <p class="text-[#27ae60] font-semibold mb-3">{$_("scan.addedSuccess")}</p>
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

<style>
    .scan-shell {
        width: 100%;
    }

    .scan-mode-toggle {
        width: 100%;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
</style>
