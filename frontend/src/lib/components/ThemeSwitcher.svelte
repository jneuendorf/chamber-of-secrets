<script lang="ts">
    import { _ } from 'svelte-i18n'

    import { nextPreference, themePreference } from '$lib/theme'

    const ICONS = { system: '🖥️', light: '☀️', dark: '🌙' }
</script>

<!-- One button that cycles system → light → dark: a single tap target, no menu. -->
<button
    type="button"
    onclick={() => themePreference.update(nextPreference)}
    aria-label={$_('theme.label', {
        values: { theme: $_(`theme.${$themePreference}`) },
    })}
    title={$_(`theme.${$themePreference}`)}
>
    {ICONS[$themePreference]}
</button>

<style>
    /* Matches LocaleSwitcher's buttons; lives in the always-dark nav. */
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
