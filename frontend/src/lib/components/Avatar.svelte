<!--
    Renders a profile avatar: a colored disc with the base part.

    `avatar_config.base` is a stable part id (e.g. "fox"), resolved to art here —
    an emoji stand-in today. WL-5.4 swaps this renderer for layered SVG parts and
    reads the config's `layers` key; stored profiles need no change.
-->
<script lang="ts">
    import type { AvatarConfig } from '$lib/api/client'
    import { AVATAR_PALETTE, avatarGlyph } from '$lib/profiles'

    interface Props {
        config?: AvatarConfig | null
        size?: number
    }

    let { config = null, size = 32 }: Props = $props()

    let glyph = $derived(avatarGlyph(config?.base))
    let color = $derived(config?.color ?? AVATAR_PALETTE[0])
</script>

<span
    class="avatar"
    style="--avatar-size: {size}px; --avatar-color: {color};"
    aria-hidden="true"
>
    {glyph}
</span>

<style>
    .avatar {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: var(--avatar-size);
        height: var(--avatar-size);
        border-radius: 50%;
        background: var(--avatar-color);
        font-size: calc(var(--avatar-size) * 0.6);
        line-height: 1;
        flex: 0 0 auto;
        box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.15);
    }
</style>
