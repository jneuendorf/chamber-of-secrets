<script lang="ts">
    import { _ } from 'svelte-i18n'

    import { hand } from '$lib/hand'
</script>

<!-- One button that toggles right ↔ left, like ThemeSwitcher. -->
<button
    type="button"
    onclick={() => hand.update((value) => (value === 'left' ? 'right' : 'left'))}
    aria-label={$_('hand.label', { values: { hand: $_(`hand.${$hand}`) } })}
    title={$_(`hand.${$hand}`)}
>
    {$hand === 'left' ? '👈' : '👉'}
</button>

<style>
    /* Matches ThemeSwitcher; lives in the always-dark nav. */
    button {
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 4px;
        padding: 0.125rem 0.375rem;
        font-size: 0.75rem;
        line-height: 1.5;
        cursor: pointer;
        transition: background 0.2s;
    }

    button:hover {
        background: rgba(255, 255, 255, 0.1);
    }
</style>
