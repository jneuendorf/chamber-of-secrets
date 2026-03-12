<script lang="ts">
    import { locale } from "svelte-i18n";

    const locales = ["de", "en"] as const;
</script>

<div class="flex gap-1">
    {#each locales as lang}
        <button
            class:active={$locale === lang}
            onclick={() => ($locale = lang)}
            aria-label="Switch to {lang.toUpperCase()}"
        >
            {lang.toUpperCase()}
        </button>
    {/each}
</div>

<style>
    button {
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: #d1d5db;
        border-radius: 4px;
        padding: 0.125rem 0.5rem;
        font-size: 0.75rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    button:hover {
        background: rgba(255, 255, 255, 0.1);
        color: white;
    }

    button.active {
        background: rgba(255, 255, 255, 0.2);
        color: white;
        border-color: rgba(255, 255, 255, 0.6);
    }
</style>
