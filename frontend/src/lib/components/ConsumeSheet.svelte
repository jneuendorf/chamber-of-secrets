<!--
    Tap-to-consume verification (WL-5.2). Emoji in the chamber are lossy — the
    same 🥛 can stand for several products — so a tap never consumes silently:
    it opens this sheet naming the item(s) under the tap. One candidate reads as
    a confirmation; several read as a chooser. Same list either way, so widening
    the tap hit-test to fill `candidates` (dense piles) needs no new UI.
    ponytail: hit-test today returns just the tapped dot, so length is always 1.
-->
<script lang="ts">
    import { _ } from 'svelte-i18n'

    import type { Product } from '$lib/api/client'
    import Modal from '$lib/components/Modal.svelte'

    export interface ConsumeCandidate {
        product: Product
        emoji: string
        isUrl: boolean
        src: string
        slot: number
        available: number
    }

    interface Props {
        open: boolean
        candidates: ConsumeCandidate[]
        onconfirm: (product: Product, slot: number, quantity: number) => void
        onclose: () => void
    }

    let { open, candidates, onconfirm, onclose }: Props = $props()

    // Chosen quantity per product, reset each time the sheet opens.
    let quantities = $state<Record<number, number>>({})
    $effect(() => {
        if (open) {
            quantities = Object.fromEntries(candidates.map((c) => [c.product.id, 1]))
        }
    })

    function qty(candidate: ConsumeCandidate): number {
        return quantities[candidate.product.id] ?? 1
    }

    function setQty(candidate: ConsumeCandidate, next: number) {
        quantities[candidate.product.id] = Math.max(
            1,
            Math.min(next, candidate.available),
        )
    }
</script>

<Modal {open} title={$_('chamber.consumeTitle')} {onclose} width="min(360px, 100%)">
    <ul class="flex flex-col gap-2">
        {#each candidates as candidate (candidate.product.id)}
            <li
                class="flex flex-col gap-3 rounded-lg border border-bark-600 bg-bark-850 p-3"
            >
                <div class="flex items-center gap-3">
                    <span class="shrink-0 text-3xl leading-none">
                        {#if candidate.isUrl}
                            <img
                                src={candidate.src}
                                alt=""
                                class="size-8 rounded object-cover"
                            />
                        {:else}
                            {candidate.emoji}
                        {/if}
                    </span>
                    <span class="min-w-0 flex-1">
                        <span class="block font-semibold text-ink-100">
                            {candidate.product.name}
                        </span>
                        <span class="block text-sm text-ink-400">
                            {$_('chamber.inStock', {
                                values: { count: candidate.available },
                            })}
                        </span>
                    </span>
                </div>

                <div class="flex items-center justify-end gap-2">
                    <button
                        type="button"
                        class="select-none rounded-md border border-bark-600 px-2 py-1 text-sm font-bold text-ink-300 disabled:opacity-40"
                        disabled={qty(candidate) >= candidate.available}
                        onclick={() => setQty(candidate, candidate.available)}
                    >
                        {$_('chamber.useAll')}
                    </button>

                    <div class="flex items-center gap-1">
                        <button
                            type="button"
                            class="size-8 select-none rounded-md border border-bark-600 bg-bark-800 text-lg font-bold text-ink-200 disabled:opacity-40"
                            aria-label={$_('chamber.decrease')}
                            disabled={qty(candidate) <= 1}
                            onclick={() => setQty(candidate, qty(candidate) - 1)}
                        >
                            −
                        </button>
                        <span
                            class="w-10 select-none text-center font-bold tabular-nums text-ink-100"
                        >
                            {qty(candidate)}
                        </span>
                        <button
                            type="button"
                            class="size-8 select-none rounded-md border border-bark-600 bg-bark-800 text-lg font-bold text-ink-200 disabled:opacity-40"
                            aria-label={$_('chamber.increase')}
                            disabled={qty(candidate) >= candidate.available}
                            onclick={() => setQty(candidate, qty(candidate) + 1)}
                        >
                            +
                        </button>
                    </div>

                    <button
                        type="button"
                        class="rounded-md bg-gold/20 px-3 py-1.5 text-sm font-bold text-warning-400 hover:bg-gold/30"
                        onclick={() =>
                            onconfirm(
                                candidate.product,
                                candidate.slot,
                                qty(candidate),
                            )}
                    >
                        {$_('chamber.useN', { values: { count: qty(candidate) } })}
                    </button>
                </div>
            </li>
        {/each}
    </ul>
</Modal>
