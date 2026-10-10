<!--
    Streak flame (WL-5.4): grows with the day streak (`flameScale`) and flickers.
    Stand-in glyph; the Lottie flame from WL-5.5 hangs off `data-streak`.
-->
<script lang="ts">
    import { flameScale } from '$lib/progression'

    let { streak }: { streak: number } = $props()

    let scale = $derived(flameScale(streak))
</script>

{#if scale > 0}
    <span
        class="streak-flame"
        data-streak={streak}
        style="--flame-scale:{scale}"
        aria-hidden="true">🔥</span
    >
{/if}

<style>
    .streak-flame {
        display: inline-block;
        font-size: calc(1em * var(--flame-scale));
        line-height: 1;
        vertical-align: bottom;
        transform-origin: 50% 100%;
        animation: flicker 1.6s ease-in-out infinite alternate;
    }

    @keyframes flicker {
        from {
            transform: scale(1) rotate(-2deg);
        }
        to {
            transform: scale(1.06, 1.12) rotate(2deg);
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .streak-flame {
            animation: none;
        }
    }
</style>
