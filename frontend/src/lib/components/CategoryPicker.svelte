<script lang="ts">
    import { _ } from "svelte-i18n";
    import type { Category } from "$lib/api/client";

    let {
        categories,
        selected,
        onSelect,
        onCreateAndSelect,
        onUpdateIcon,
    }: {
        categories: Category[];
        selected: Category | null;
        onSelect: (cat: Category | null) => void;
        onCreateAndSelect: (name: string) => Promise<void>;
        onUpdateIcon?: (cat: Category, icon: string | null) => Promise<void>;
    } = $props();

    let newName = $state("");
    let creating = $state(false);
    let editingIconId: number | null = $state(null);
    let editingIconValue = $state("");
    let savingIcon = $state(false);

    async function create() {
        const name = newName.trim();
        if (!name) return;
        creating = true;
        try {
            await onCreateAndSelect(name);
            newName = "";
        } finally {
            creating = false;
        }
    }

    function startEditIcon(cat: Category, e: Event) {
        e.stopPropagation();
        editingIconId = cat.id;
        editingIconValue = cat.icon ?? "";
    }

    async function saveIcon() {
        if (!onUpdateIcon) return;
        const cat = categories.find((c) => c.id === editingIconId);
        if (!cat) return;
        savingIcon = true;
        try {
            await onUpdateIcon(cat, editingIconValue.trim() || null);
            editingIconId = null;
        } finally {
            savingIcon = false;
        }
    }

    function isUrl(icon: string): boolean {
        return icon.startsWith("http") || icon.startsWith("data:");
    }
</script>

<div class="flex flex-wrap gap-2 mb-3">
    <button
        onclick={() => onSelect(null)}
        class="px-4 py-2 rounded-full text-sm font-medium border transition-colors {!selected
            ? 'bg-[#1a1a2e] text-white border-[#1a1a2e]'
            : 'bg-[#2f2a22] text-gray-200 border-[#5b4f3a] active:bg-[#26221b]'}"
    >
        {$_("category.none")}
    </button>
    {#each categories as cat (cat.id)}
        <button
            onclick={() => onSelect(cat)}
            class="px-4 py-2 rounded-full text-sm font-medium border transition-colors flex items-center gap-1.5 {selected?.id ===
            cat.id
                ? 'bg-[#1a1a2e] text-white border-[#1a1a2e]'
                : 'bg-[#2f2a22] text-gray-200 border-[#5b4f3a] active:bg-[#26221b]'}"
        >
            {#if cat.icon}
                {#if isUrl(cat.icon)}
                    <img src={cat.icon} alt="" class="w-4 h-4 rounded object-cover" />
                {:else}
                    <span class="leading-none">{cat.icon}</span>
                {/if}
            {/if}
            {cat.name}
            {#if onUpdateIcon}
                <span
                    role="button"
                    tabindex="0"
                    onclick={(e) => startEditIcon(cat, e)}
                    onkeydown={(e) => e.key === "Enter" && startEditIcon(cat, e)}
                    class="ml-0.5 text-xs opacity-40 hover:opacity-100"
                    title={$_("category.editIcon")}>✎</span
                >
            {/if}
        </button>
    {/each}
</div>

{#if editingIconId !== null && onUpdateIcon}
    {@const editCat = categories.find((c) => c.id === editingIconId)}
    {#if editCat}
        <div
            class="flex gap-2 mb-3 items-center bg-[#111827] border border-[#374151] rounded-lg px-3 py-2"
        >
            <span class="text-sm text-gray-300 shrink-0">{editCat.name}:</span>
            <input
                type="text"
                bind:value={editingIconValue}
                placeholder={$_("category.iconPlaceholder")}
                disabled={savingIcon}
                class="flex-1 min-w-0 px-2 py-1 border border-[#5b4f3a] bg-[#2f2a22] text-gray-100 rounded-md text-sm"
            />
            <button
                onclick={saveIcon}
                disabled={savingIcon}
                class="px-3 py-1 bg-[#1a1a2e] text-white rounded-md text-sm font-medium disabled:opacity-40 shrink-0"
            >
                {$_("category.save")}
            </button>
            <button onclick={() => (editingIconId = null)} class="text-gray-300 text-sm px-1"
                >✕</button
            >
        </div>
    {/if}
{/if}

<form
    class="flex gap-2"
    onsubmit={(e) => {
        e.preventDefault();
        create();
    }}
>
    <input
        type="text"
        bind:value={newName}
        placeholder={$_("category.newPlaceholder")}
        disabled={creating}
        class="flex-1 px-3 py-2 border border-[#5b4f3a] bg-[#2f2a22] text-gray-100 rounded-lg text-sm"
    />
    <button
        type="submit"
        disabled={!newName.trim() || creating}
        class="px-4 py-2 bg-[#1a1a2e] text-white rounded-lg text-sm font-medium disabled:opacity-40"
    >
        {$_("category.add")}
    </button>
</form>
