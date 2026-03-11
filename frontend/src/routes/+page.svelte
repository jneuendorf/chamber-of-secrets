<script lang="ts">
    import { _ } from "svelte-i18n";
    import { api, type Product } from "$lib/api/client";

    let products: Product[] = $state([]);
    let loading = $state(true);

    async function load() {
        try {
            products = await api.products.list();
        } catch {
            // API not available yet
        } finally {
            loading = false;
        }
    }

    $effect(() => {
        load();
    });

    let totalItems = $derived(products.reduce((sum, p) => sum + p.stock, 0));
    let categories = $derived(new Set(products.map((p) => p.category?.name).filter(Boolean)).size);
</script>

<h1 class="mt-0">{$_("dashboard.title")}</h1>

<div class="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-4 mb-8">
    <div class="bg-white rounded-xl p-6 text-center shadow-sm">
        <span class="block text-[2rem] font-bold text-[#1a1a2e]"
            >{loading ? "..." : products.length}</span
        >
        <span class="text-gray-500 text-sm">{$_("dashboard.products")}</span>
    </div>
    <div class="bg-white rounded-xl p-6 text-center shadow-sm">
        <span class="block text-[2rem] font-bold text-[#1a1a2e]"
            >{loading ? "..." : totalItems}</span
        >
        <span class="text-gray-500 text-sm">{$_("dashboard.totalItems")}</span>
    </div>
    <div class="bg-white rounded-xl p-6 text-center shadow-sm">
        <span class="block text-[2rem] font-bold text-[#1a1a2e]"
            >{loading ? "..." : categories}</span
        >
        <span class="text-gray-500 text-sm">{$_("dashboard.categories")}</span>
    </div>
</div>

<div class="flex gap-4 flex-wrap">
    <a href="/scan" class="action-btn">{$_("dashboard.scanItem")}</a>
    <a href="/inventory" class="action-btn secondary">{$_("dashboard.viewInventory")}</a>
    <a href="/analytics" class="action-btn secondary">{$_("dashboard.analytics")}</a>
</div>

<style>
    .action-btn {
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        background: #1a1a2e;
        color: white;
        transition: opacity 0.2s;
    }

    .action-btn:hover {
        opacity: 0.9;
    }

    .action-btn.secondary {
        background: white;
        color: #1a1a2e;
        border: 1px solid #d1d5db;
    }
</style>
