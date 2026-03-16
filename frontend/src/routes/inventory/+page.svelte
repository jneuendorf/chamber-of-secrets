<script lang="ts">
    import { get } from "svelte/store";
    import { _ } from "svelte-i18n";
    import CategoryPicker from "$lib/components/CategoryPicker.svelte";
    import FuzzySearchOverlay from "$lib/components/FuzzySearchOverlay.svelte";
    import { api, type Category, type Product } from "$lib/api/client";

    let products: Product[] = $state([]);
    let categories: Category[] = $state([]);
    let loading = $state(true);
    let error = $state("");
    let editingId: number | null = $state(null);
    let searchOpen = $state(false);

    function selectProductFromSearch(item: unknown) {
        const product = item as Product;
        editingId = product.id;
        document
            .querySelector(`[data-product-id="${product.id}"]`)
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    async function load() {
        try {
            [products, categories] = await Promise.all([
                api.products.list(),
                api.categories.list(),
            ]);
        } catch (e) {
            error = get(_)("inventory.failedToLoad", { values: { error: String(e) } });
        } finally {
            loading = false;
        }
    }

    $effect(() => {
        load();
    });

    async function assignCategory(product: Product, cat: Category | null) {
        editingId = null;
        try {
            const updated = await api.products.update(product.id, { category_id: cat?.id ?? null });
            products = products.map((p) =>
                p.id === product.id ? { ...p, ...updated, category: cat, stock: p.stock } : p,
            );
        } catch (e) {
            error = get(_)("category.failedToSave", { values: { error: String(e) } });
        }
    }

    async function createAndAssign(product: Product, name: string) {
        try {
            const cat = await api.categories.create({ name });
            categories = [...categories, cat];
            await assignCategory(product, cat);
        } catch (e) {
            error = get(_)("category.failedToSave", { values: { error: String(e) } });
        }
    }

    async function handleUpdateIcon(cat: Category, icon: string | null) {
        const updated = await api.categories.update(cat.id, { icon });
        categories = categories.map((c) => (c.id === updated.id ? updated : c));
        // Refresh icon on any product that has this category
        products = products.map((p) =>
            p.category?.id === updated.id ? { ...p, category: updated } : p,
        );
    }
</script>

<div class="heading-row">
    <h1 class="mt-0">{$_("nav.inventory")}</h1>
    <button
        type="button"
        class="search-indicator"
        title={$_("inventory.searchHint")}
        onclick={() => {
            searchOpen = true;
        }}
    >
        <span class="search-indicator-icon" aria-hidden="true">⌕</span>
        {$_("common.searchIndicator")}
    </button>
</div>

{#if loading}
    <p>{$_("common.loading")}</p>
{:else if error}
    <p class="text-[#e74c3c]">{error}</p>
{:else if products.length === 0}
    <p class="text-center text-gray-500 my-12">
        {$_("inventory.empty")} <a href="/scan">{$_("inventory.scanCta")}</a>
    </p>
{:else}
    <FuzzySearchOverlay
        items={products}
        keys={["name", "brand", "ean", "category.name"]}
        getId={(item) => (item as Product).id}
        getLabel={(item) => (item as Product).name}
        getSecondaryLabel={(item) => {
            const p = item as Product;
            const parts = [p.brand, p.category?.name].filter(Boolean);
            return parts.length ? parts.join(" · ") : null;
        }}
        onSelect={selectProductFromSearch}
        placeholder={$_("inventory.searchPlaceholder")}
        noResultsText={$_("inventory.searchNoResults")}
        hintText={$_("inventory.searchHint")}
        bind:open={searchOpen}
    />

    <div class="flex flex-col gap-3">
        {#each products as product (product.id)}
            <div class="bg-white rounded-xl p-4 shadow-sm" data-product-id={product.id}>
                <div class="flex items-center gap-4">
                    {#if product.image_url}
                        <img
                            src={product.image_url}
                            alt={product.name}
                            class="w-12 h-12 rounded-lg object-cover"
                        />
                    {:else}
                        <div
                            class="w-12 h-12 rounded-lg bg-[#eee] flex items-center justify-center text-gray-400 text-xl"
                        >
                            ?
                        </div>
                    {/if}
                    <div class="flex-1 min-w-0">
                        <h3 class="m-0 text-base">{product.name}</h3>
                        {#if product.brand}
                            <p class="m-0 text-gray-500 text-[0.85rem]">{product.brand}</p>
                        {/if}
                        <button
                            onclick={() =>
                                (editingId = editingId === product.id ? null : product.id)}
                            class="mt-1 flex items-center gap-1 text-left"
                        >
                            {#if product.category}
                                <span
                                    class="bg-[#e8e8ff] text-[#1a1a2e] px-2 py-0.5 rounded text-xs"
                                >
                                    {product.category.name}
                                </span>
                            {:else}
                                <span class="text-gray-400 text-xs">{$_("category.none")}</span>
                            {/if}
                            <span class="text-gray-400 text-xs">{$_("category.change")} ›</span>
                        </button>
                    </div>
                    <div
                        class="stock"
                        class:low={product.stock <= 1}
                        class:out={product.stock <= 0}
                    >
                        {product.stock}
                    </div>
                </div>

                {#if editingId === product.id}
                    <div class="mt-3 pt-3 border-t border-gray-100">
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
        color: #6b7280;
        border: 1px solid #d1d5db;
        border-radius: 999px;
        padding: 0.2rem 0.55rem;
        background: #f9fafb;
        white-space: nowrap;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        cursor: pointer;
    }

    .search-indicator:hover {
        background: #f3f4f6;
    }

    .search-indicator-icon {
        font-size: 0.85rem;
        line-height: 1;
    }

    .stock {
        font-size: 1.5rem;
        font-weight: 700;
        color: #27ae60;
        min-width: 3rem;
        text-align: center;
    }

    .stock.low {
        color: #f39c12;
    }

    .stock.out {
        color: #e74c3c;
    }
</style>
