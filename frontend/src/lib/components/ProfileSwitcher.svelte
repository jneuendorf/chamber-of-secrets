<!--
    Netflix/Switch-style profile picker in the nav (WL-5.1). Login-less: pick a
    profile before scanning, or none. Reuses Modal rather than pulling in a new
    Bits UI primitive — a small picker sheet is all this needs.
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { _ } from 'svelte-i18n'

    import { api, type Profile } from '$lib/api/client'
    import {
        AVATAR_BASE_IDS,
        AVATAR_BASES,
        AVATAR_PALETTE,
        activeProfileId,
        defaultAvatarConfig,
    } from '$lib/profiles'
    import Avatar from './Avatar.svelte'
    import Modal from './Modal.svelte'

    let profiles = $state<Profile[]>([])
    let pickerOpen = $state(false)
    let creating = $state(false)
    let newName = $state('')
    let newBase = $state(AVATAR_BASE_IDS[0])
    let newColor = $state(AVATAR_PALETTE[0])
    let saving = $state(false)

    let active = $derived(
        profiles.find((profile) => profile.id === $activeProfileId) ?? null,
    )

    async function load() {
        profiles = await api.profiles.list()
        // Drop a stale selection (e.g. archived elsewhere) so mutations stay clean.
        if (
            $activeProfileId != null &&
            !profiles.some((profile) => profile.id === $activeProfileId)
        ) {
            activeProfileId.set(null)
        }
    }

    onMount(load)

    function select(id: number | null) {
        activeProfileId.set(id)
        pickerOpen = false
    }

    function startCreate() {
        const preset = defaultAvatarConfig()
        newName = ''
        newBase = preset.base
        newColor = preset.color
        creating = true
    }

    function onSubmit(event: SubmitEvent) {
        event.preventDefault()
        create()
    }

    async function create() {
        const name = newName.trim()
        if (!name || saving) {
            return
        }
        saving = true
        try {
            const profile = await api.profiles.create({
                name,
                avatar_config: { base: newBase, color: newColor },
            })
            profiles = [...profiles, profile]
            activeProfileId.set(profile.id)
            creating = false
            pickerOpen = false
        } finally {
            saving = false
        }
    }
</script>

<button
    type="button"
    class="switcher-trigger"
    onclick={() => (pickerOpen = true)}
    aria-label={$_('profile.pick')}
>
    {#if active}
        <Avatar config={active.avatar_config} size={26} />
        <span class="switcher-name">{active.name}</span>
    {:else}
        <span class="switcher-guest" aria-hidden="true">👤</span>
    {/if}
</button>

<Modal
    bind:open={pickerOpen}
    title={creating ? $_('profile.new') : $_('profile.pick')}
    onclose={() => {
        pickerOpen = false
        creating = false
    }}
>
    {#if creating}
        <form class="flex flex-col gap-3" onsubmit={onSubmit}>
            <input
                class="rounded-lg border border-bark-600 bg-bark-850 px-3 py-2 text-ink-100"
                placeholder={$_('profile.namePlaceholder')}
                bind:value={newName}
                maxlength="50"
            />

            <div class="flex flex-wrap gap-2">
                {#each AVATAR_BASE_IDS as baseId}
                    <button
                        type="button"
                        class="pick-tile"
                        class:selected={newBase === baseId}
                        onclick={() => (newBase = baseId)}
                        aria-label={AVATAR_BASES[baseId]}
                    >
                        {AVATAR_BASES[baseId]}
                    </button>
                {/each}
            </div>

            <div class="flex flex-wrap gap-2">
                {#each AVATAR_PALETTE as color}
                    <button
                        type="button"
                        class="pick-swatch"
                        class:selected={newColor === color}
                        style="background: {color};"
                        onclick={() => (newColor = color)}
                        aria-label={color}
                    ></button>
                {/each}
            </div>

            <div class="flex items-center gap-3 pt-1">
                <Avatar config={{ base: newBase, color: newColor }} size={40} />
                <button
                    type="submit"
                    class="ml-auto rounded-lg bg-accent-700 px-4 py-2 text-white disabled:opacity-50"
                    disabled={!newName.trim() || saving}
                >
                    {$_('profile.create')}
                </button>
            </div>
        </form>
    {:else}
        <ul class="flex flex-col gap-1">
            {#each profiles as profile (profile.id)}
                <li>
                    <button
                        type="button"
                        class="profile-row"
                        class:selected={profile.id === $activeProfileId}
                        onclick={() => select(profile.id)}
                    >
                        <Avatar config={profile.avatar_config} size={32} />
                        <span class="grow text-left">{profile.name}</span>
                        <span class="text-sm text-ink-300"
                            >{$_('profile.level', {
                                values: { level: profile.level },
                            })}</span
                        >
                    </button>
                </li>
            {/each}
            <li>
                <button
                    type="button"
                    class="profile-row"
                    class:selected={$activeProfileId == null}
                    onclick={() => select(null)}
                >
                    <span class="switcher-guest" aria-hidden="true">👤</span>
                    <span class="grow text-left">{$_('profile.none')}</span>
                </button>
            </li>
        </ul>

        <button
            type="button"
            class="mt-3 w-full rounded-lg border border-dashed border-bark-600 px-4 py-2 text-ink-200 hover:bg-bark-730"
            onclick={startCreate}
        >
            + {$_('profile.new')}
        </button>
    {/if}
</Modal>

<style>
    .switcher-trigger {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: var(--color-ink-250);
        border-radius: 999px;
        padding: 0.125rem 0.5rem 0.125rem 0.25rem;
        cursor: pointer;
        max-width: 9rem;
    }

    .switcher-trigger:hover {
        background: rgba(255, 255, 255, 0.1);
        color: white;
    }

    .switcher-name {
        font-size: 0.8rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .switcher-guest {
        font-size: 1.1rem;
        line-height: 1;
    }

    .profile-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        width: 100%;
        padding: 0.5rem;
        border-radius: 0.5rem;
        background: transparent;
        color: var(--color-ink-100);
        cursor: pointer;
    }

    .profile-row:hover {
        background: var(--color-bark-730);
    }

    .profile-row.selected {
        background: var(--color-bark-700);
        outline: 1px solid var(--color-accent-700);
    }

    .pick-tile {
        width: 2.25rem;
        height: 2.25rem;
        font-size: 1.2rem;
        border-radius: 0.5rem;
        border: 1px solid var(--color-bark-600);
        background: var(--color-bark-850);
        cursor: pointer;
    }

    .pick-tile.selected {
        outline: 2px solid var(--color-accent-700);
    }

    .pick-swatch {
        width: 1.75rem;
        height: 1.75rem;
        border-radius: 50%;
        border: 1px solid rgba(0, 0, 0, 0.2);
        cursor: pointer;
    }

    .pick-swatch.selected {
        outline: 2px solid white;
        outline-offset: 1px;
    }
</style>
