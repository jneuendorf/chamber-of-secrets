<script lang="ts">
    import { _ } from "svelte-i18n";
    import Fuse from "fuse.js";
    import type { FuseOptionKey } from "fuse.js";
    import { onMount } from "svelte";

    type Fuseable = unknown;

    let {
        items,
        keys,
        getId,
        getLabel,
        getSecondaryLabel,
        onSelect,
        placeholder = $_("common.searchPlaceholder"),
        noResultsText = $_("common.noResults"),
        hintText = $_("common.searchHint"),
        maxResults = 12,
        open = $bindable(false),
    }: {
        items: Fuseable[];
        keys: FuseOptionKey<Fuseable>[];
        getId: (item: Fuseable) => string | number;
        getLabel: (item: Fuseable) => string;
        getSecondaryLabel?: (item: Fuseable) => string | null | undefined;
        onSelect: (item: Fuseable) => void;
        placeholder?: string;
        noResultsText?: string;
        hintText?: string;
        maxResults?: number;
        open?: boolean;
    } = $props();

    let query = $state("");
    let activeIndex = $state(0);

    let inputEl: HTMLInputElement | null = $state(null);
    let wasOpen = $state(false);

    const fuse = $derived(
        new Fuse(items, {
            keys,
            includeScore: true,
            threshold: 0.35,
            ignoreLocation: true,
            minMatchCharLength: 1,
        }),
    );

    const results = $derived.by(() => {
        const q = query.trim();
        if (!q) {
            return items.slice(0, maxResults);
        }
        return fuse.search(q, { limit: maxResults }).map((r) => r.item);
    });

    $effect(() => {
        const len = results.length;
        if (len === 0) {
            activeIndex = 0;
            return;
        }
        if (activeIndex >= len) activeIndex = len - 1;
        if (activeIndex < 0) activeIndex = 0;
    });

    function isHotkey(e: KeyboardEvent): boolean {
        const isK = e.key.toLowerCase() === "k";
        return isK && (e.ctrlKey || e.metaKey);
    }

    function closeOverlay() {
        open = false;
        query = "";
        activeIndex = 0;
    }

    $effect(() => {
        const currentlyOpen = open;
        if (currentlyOpen && !wasOpen) {
            query = "";
            activeIndex = 0;
            queueMicrotask(() => inputEl?.focus());
        } else if (!currentlyOpen && wasOpen) {
            query = "";
            activeIndex = 0;
        }
        wasOpen = currentlyOpen;
    });

    function choose(item: Fuseable) {
        onSelect(item);
        closeOverlay();
    }

    function onGlobalKeydown(e: KeyboardEvent) {
        if (isHotkey(e)) {
            e.preventDefault();
            open = !open;
            return;
        }

        if (!open) return;

        if (e.key === "Escape") {
            e.preventDefault();
            closeOverlay();
            return;
        }

        if (e.key === "ArrowDown") {
            e.preventDefault();
            if (results.length > 0) activeIndex = (activeIndex + 1) % results.length;
            return;
        }

        if (e.key === "ArrowUp") {
            e.preventDefault();
            if (results.length > 0)
                activeIndex = (activeIndex - 1 + results.length) % results.length;
            return;
        }

        if (e.key === "Enter") {
            e.preventDefault();
            const item = results[activeIndex];
            if (item) choose(item);
        }
    }

    onMount(() => {
        window.addEventListener("keydown", onGlobalKeydown);
        return () => window.removeEventListener("keydown", onGlobalKeydown);
    });
</script>

{#if open}
    <button
        type="button"
        class="fuzzy-overlay-backdrop"
        onclick={closeOverlay}
        aria-label={$_("common.close")}
    ></button>

    <div
        class="fuzzy-overlay-panel"
        role="dialog"
        aria-modal="true"
        aria-label={$_("common.search")}
        tabindex="-1"
    >
        <div class="fuzzy-overlay-input-wrap">
            <span class="fuzzy-overlay-icon" aria-hidden="true">⌕</span>
            <input
                bind:this={inputEl}
                type="text"
                bind:value={query}
                {placeholder}
                class="fuzzy-overlay-input"
                autocomplete="off"
                autocorrect="off"
                autocapitalize="off"
                spellcheck="false"
            />
            <button
                class="fuzzy-overlay-close"
                onclick={closeOverlay}
                aria-label={$_("common.close")}>Esc</button
            >
        </div>

        <div class="fuzzy-overlay-hint">{hintText}</div>

        {#if results.length === 0}
            <div class="fuzzy-overlay-empty">{noResultsText}</div>
        {:else}
            <ul class="fuzzy-overlay-list" role="listbox" aria-label={$_("common.searchResults")}>
                {#each results as item, index (getId(item))}
                    <li>
                        <button
                            class="fuzzy-overlay-item"
                            class:active={index === activeIndex}
                            onclick={() => choose(item)}
                            onmousemove={() => (activeIndex = index)}
                            role="option"
                            aria-selected={index === activeIndex}
                        >
                            <span class="primary">{getLabel(item)}</span>
                            {#if getSecondaryLabel}
                                {@const secondary = getSecondaryLabel(item)}
                                {#if secondary}
                                    <span class="secondary">{secondary}</span>
                                {/if}
                            {/if}
                        </button>
                    </li>
                {/each}
            </ul>
        {/if}
    </div>
{/if}

<style>
    .fuzzy-overlay-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.35);
        backdrop-filter: blur(1px);
        z-index: 70;
    }

    .fuzzy-overlay-panel {
        position: fixed;
        top: 12vh;
        left: 50%;
        transform: translateX(-50%);
        width: min(680px, calc(100vw - 2rem));
        background: #2f2a22;
        border: 1px solid #5b4f3a;
        border-radius: 14px;
        box-shadow:
            0 20px 40px rgba(15, 23, 42, 0.2),
            0 6px 14px rgba(15, 23, 42, 0.1);
        z-index: 80;
        overflow: hidden;
    }

    .fuzzy-overlay-input-wrap {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        border-bottom: 1px solid #5b4f3a;
        padding: 0.7rem 0.85rem;
    }

    .fuzzy-overlay-icon {
        color: #9ca3af;
        font-size: 0.95rem;
    }

    .fuzzy-overlay-input {
        border: none;
        outline: none;
        width: 100%;
        font-size: 0.98rem;
        color: #f3f4f6;
        background: transparent;
    }

    .fuzzy-overlay-close {
        border: 1px solid #5b4f3a;
        background: #26221b;
        color: #f3f4f6;
        border-radius: 0.45rem;
        padding: 0.2rem 0.5rem;
        font-size: 0.75rem;
        line-height: 1.2;
        cursor: pointer;
    }

    .fuzzy-overlay-hint {
        padding: 0.45rem 0.9rem 0.2rem;
        color: #9ca3af;
        font-size: 0.78rem;
    }

    .fuzzy-overlay-empty {
        padding: 1rem 0.9rem 1.1rem;
        color: #9ca3af;
        font-size: 0.9rem;
    }

    .fuzzy-overlay-list {
        list-style: none;
        margin: 0;
        padding: 0.35rem;
        max-height: min(55vh, 420px);
        overflow: auto;
    }

    .fuzzy-overlay-item {
        width: 100%;
        border: none;
        background: transparent;
        text-align: left;
        padding: 0.62rem 0.65rem;
        border-radius: 0.55rem;
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        cursor: pointer;
    }

    .fuzzy-overlay-item:hover,
    .fuzzy-overlay-item.active {
        background: #4a3f2f;
    }

    .fuzzy-overlay-item .primary {
        color: #f3f4f6;
        font-size: 0.92rem;
        font-weight: 500;
    }

    .fuzzy-overlay-item .secondary {
        color: #cbd5e1;
        font-size: 0.8rem;
    }
</style>
