<script lang="ts">
    import type { Snippet } from 'svelte'

    interface Props {
        open: boolean
        title?: string
        onclose: () => void
        width?: string
        children: Snippet
    }

    let {
        open,
        title,
        onclose,
        width = 'min(480px, 100%)',
        children,
    }: Props = $props()

    let backdrop: HTMLDivElement | undefined = $state()

    $effect(() => {
        if (open) { backdrop?.focus() }
    })

    function handleBackdrop(e: MouseEvent) {
        if (e.target === backdrop) { onclose() }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') { onclose() }
    }
</script>

{#if open}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="modal-backdrop"
        bind:this={backdrop}
        onclick={handleBackdrop}
        onkeydown={handleKeydown}
        role="dialog"
        aria-modal="true"
        tabindex="-1"
    >
        <div class="modal-panel" style:max-width={width}>
            {#if title}
                <div class="modal-header">
                    <h2>{title}</h2>
                    <button
                        type="button"
                        class="modal-close"
                        onclick={onclose}
                        aria-label="Close"
                    >
                        ✕
                    </button>
                </div>
            {/if}
            {@render children()}
        </div>
    </div>
{/if}

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        z-index: 9998;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
    }

    .modal-panel {
        width: 100%;
        max-height: calc(100vh - 2rem);
        overflow: auto;
        background: #2f2a22;
        border: 1px solid #5b4f3a;
        border-radius: 0.9rem;
        padding: 1rem;
        color: #e5e7eb;
    }

    .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.75rem;
    }

    .modal-header h2 {
        margin: 0;
        font-size: 1.1rem;
        color: #f3f4f6;
    }

    .modal-close {
        border: 1px solid #5b4f3a;
        background: #26221b;
        color: #f3f4f6;
        width: 2rem;
        height: 2rem;
        border-radius: 0.45rem;
        cursor: pointer;
        flex-shrink: 0;
    }

    .modal-close:hover {
        background: #3b3327;
    }
</style>
