<!--
    Dedicated per-profile progress view (WL-5.4): avatar, level + XP bar, streak,
    and the full badge grid (earned and still-locked). Reached from the profile
    picker; a standalone route so a future nav redesign can place it freely.
-->
<script lang="ts">
    import { _ } from 'svelte-i18n'

    import { ApiError, api, type Profile } from '$lib/api/client'
    import Avatar from '$lib/components/Avatar.svelte'
    import { ACHIEVEMENT_KEYS, achievementGlyph, xpForLevel } from '$lib/progression'

    let { data }: { data: { id: number } } = $props()

    let profile = $state<Profile | null>(null)
    let loading = $state(true)
    let error = $state('')

    $effect(() => {
        loading = true
        // ponytail: no GET /profiles/{id} — reuse the list (a handful of rows).
        // include_archived so a direct link still resolves an archived profile.
        api.profiles
            .list(true)
            .then((profiles) => {
                profile = profiles.find((entry) => entry.id === data.id) ?? null
            })
            .catch((err: unknown) => {
                error = err instanceof ApiError ? err.detail : String(err)
            })
            .finally(() => {
                loading = false
            })
    })

    let level = $derived(profile?.level ?? 1)
    let xp = $derived(profile?.xp ?? 0)
    let levelFloor = $derived(xpForLevel(level))
    let nextLevel = $derived(xpForLevel(level + 1))
    let span = $derived(nextLevel - levelFloor)
    let pct = $derived(span > 0 ? Math.min(100, ((xp - levelFloor) / span) * 100) : 100)
    let remaining = $derived(Math.max(0, nextLevel - xp))

    let earned = $derived(new Set(profile?.achievements ?? []))
</script>

<svelte:head>
    <title
        >{profile
            ? $_('profile.progressTitle', { values: { name: profile.name } })
            : ''}</title
    >
</svelte:head>

<main class="mx-auto flex max-w-2xl flex-col gap-6 p-4 sm:p-6">
    <a href="/chamber" class="back-link">← {$_('profile.back')}</a>

    {#if loading}
        <p class="text-ink-300">{$_('common.loading')}</p>
    {:else if error}
        <p class="text-danger-300">{error}</p>
    {:else if !profile}
        <p class="text-ink-300">{$_('profile.notFound')}</p>
    {:else}
        <header class="flex items-center gap-4">
            <Avatar config={profile.avatar_config} size={72} />
            <div class="flex flex-col gap-1">
                <h1 class="text-2xl font-semibold text-ink-100">{profile.name}</h1>
                <span class="text-accent-300"
                    >{$_('profile.levelFull', { values: { level } })}</span
                >
            </div>
        </header>

        <section class="card">
            <div class="mb-2 flex items-baseline justify-between">
                <span class="text-sm text-ink-300"
                    >{$_('profile.xpTotal', { values: { xp } })}</span
                >
                <span class="text-sm text-ink-400"
                    >{$_('profile.xpToNext', {
                        values: { remaining, level: level + 1 },
                    })}</span
                >
            </div>
            <div
                class="xp-track"
                role="progressbar"
                aria-valuenow={Math.round(pct)}
                aria-valuemin={0}
                aria-valuemax={100}
            >
                <div class="xp-fill" style="width: {pct}%"></div>
            </div>
        </section>

        <section class="card flex items-center justify-between">
            <span class="text-ink-200">{$_('profile.dayStreak')}</span>
            <span class="text-lg font-semibold text-ink-100">
                🔥 {profile.current_streak}
                <span class="text-sm font-normal text-ink-400">
                    {profile.current_streak === 1
                        ? $_('profile.day')
                        : $_('profile.days')}
                </span>
            </span>
        </section>

        <section class="flex flex-col gap-3">
            <div class="flex items-baseline justify-between">
                <h2 class="text-lg font-semibold text-ink-100">
                    {$_('profile.badges')}
                </h2>
                <span class="text-sm text-ink-400"
                    >{$_('profile.badgesEarnedCount', {
                        values: { earned: earned.size, total: ACHIEVEMENT_KEYS.length },
                    })}</span
                >
            </div>
            <ul class="badge-grid">
                {#each ACHIEVEMENT_KEYS as key (key)}
                    {@const isEarned = earned.has(key)}
                    <li class="badge-card" class:locked={!isEarned}>
                        <span class="badge-glyph">{achievementGlyph(key)}</span>
                        <span class="badge-name">{$_(`achievement.${key}.name`)}</span>
                        <span class="badge-desc">
                            {isEarned
                                ? $_(`achievement.${key}.desc`)
                                : $_('profile.locked')}
                        </span>
                    </li>
                {/each}
            </ul>
        </section>
    {/if}
</main>

<style>
    .back-link {
        color: var(--color-ink-300);
        font-size: 0.9rem;
        width: fit-content;
    }

    .back-link:hover {
        color: var(--color-ink-100);
    }

    .card {
        background: var(--color-bark-850);
        border: 1px solid var(--color-bark-730);
        border-radius: 0.75rem;
        padding: 1rem;
    }

    .xp-track {
        height: 0.75rem;
        border-radius: 999px;
        background: var(--color-bark-700);
        overflow: hidden;
    }

    .xp-fill {
        height: 100%;
        border-radius: 999px;
        background: var(--color-accent-500);
        transition: width 0.4s ease-out;
    }

    .badge-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
        gap: 0.75rem;
    }

    .badge-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.35rem;
        text-align: center;
        background: var(--color-bark-850);
        border: 1px solid var(--color-bark-730);
        border-radius: 0.75rem;
        padding: 1rem 0.75rem;
    }

    .badge-card.locked {
        opacity: 0.45;
        filter: grayscale(1);
    }

    .badge-glyph {
        font-size: 2rem;
        line-height: 1;
    }

    .badge-name {
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--color-ink-100);
    }

    .badge-desc {
        font-size: 0.75rem;
        color: var(--color-ink-400);
    }
</style>
