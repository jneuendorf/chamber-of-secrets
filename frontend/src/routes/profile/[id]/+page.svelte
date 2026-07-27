<!--
    Dedicated per-profile progress view (WL-5.4): avatar, level + XP bar, streak,
    and the full badge grid (earned and still-locked). Reached from the profile
    picker; a standalone route so a future nav redesign can place it freely.
-->
<script lang="ts">
    import { _ } from 'svelte-i18n'

    import { ApiError, api, type Profile, type RewardTier } from '$lib/api/client'
    import Avatar from '$lib/components/Avatar.svelte'
    import { activeProfileId } from '$lib/profiles'
    import { ACHIEVEMENT_KEYS, achievementGlyph, xpForLevel } from '$lib/progression'

    let { data }: { data: { id: number } } = $props()

    let profile = $state<Profile | null>(null)
    let loading = $state(true)
    let error = $state('')

    // Rewards are household-wide config; edited from any profile page (WL-5.4).
    let rewards = $state<RewardTier[]>([])
    let newLevel = $state(2)
    let newDescription = $state('')
    let rewardError = $state('')

    $effect(() => {
        loading = true
        // ponytail: no GET /profiles/{id} — reuse the list (a handful of rows).
        // include_archived so a direct link still resolves an archived profile.
        Promise.all([api.profiles.list(true), api.rewards.list()])
            .then(([profiles, tiers]) => {
                profile = profiles.find((entry) => entry.id === data.id) ?? null
                rewards = tiers
            })
            .catch((err: unknown) => {
                error = err instanceof ApiError ? err.detail : String(err)
            })
            .finally(() => {
                loading = false
            })
    })

    async function addReward(event: SubmitEvent) {
        event.preventDefault()
        rewardError = ''
        try {
            await api.rewards.create({ level: newLevel, description: newDescription })
            rewards = await api.rewards.list()
            newDescription = ''
        } catch (err: unknown) {
            rewardError = err instanceof ApiError ? err.detail : String(err)
        }
    }

    async function removeReward(id: number) {
        rewardError = ''
        try {
            await api.rewards.delete(id)
            rewards = await api.rewards.list()
        } catch (err: unknown) {
            rewardError = err instanceof ApiError ? err.detail : String(err)
        }
    }

    // Redemption is per profile and only offered on your own page (WL-5.4).
    async function toggleRedeem(rewardId: number, redeemed: boolean) {
        rewardError = ''
        try {
            await (redeemed
                ? api.rewards.unredeem(rewardId, data.id)
                : api.rewards.redeem(rewardId, data.id))
            // Re-read the profile so its redeemed_rewards reflects the change.
            const profiles = await api.profiles.list(true)
            profile = profiles.find((entry) => entry.id === data.id) ?? profile
        } catch (err: unknown) {
            rewardError = err instanceof ApiError ? err.detail : String(err)
        }
    }

    let level = $derived(profile?.level ?? 1)
    let xp = $derived(profile?.xp ?? 0)
    let levelFloor = $derived(xpForLevel(level))
    let nextLevel = $derived(xpForLevel(level + 1))
    let span = $derived(nextLevel - levelFloor)
    let pct = $derived(span > 0 ? Math.min(100, ((xp - levelFloor) / span) * 100) : 100)
    let remaining = $derived(Math.max(0, nextLevel - xp))

    let earned = $derived(new Set(profile?.achievements ?? []))
    // Only the active profile may redeem its own rewards (login-less UX guard).
    let isOwnProfile = $derived($activeProfileId === data.id)
    let redeemedIds = $derived(new Set(profile?.redeemed_rewards ?? []))
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

        <section class="flex flex-col gap-3">
            <h2 class="text-lg font-semibold text-ink-100">{$_('profile.rewards')}</h2>
            <p class="text-sm text-ink-400">{$_('profile.rewardsHint')}</p>

            {#if rewards.length === 0}
                <p class="text-ink-300">{$_('profile.rewardsNone')}</p>
            {:else}
                <ul class="flex flex-col gap-2">
                    {#each rewards as reward (reward.id)}
                        {@const unlocked = level >= reward.level}
                        {@const redeemed = redeemedIds.has(reward.id)}
                        <li class="reward-row" class:locked={!unlocked}>
                            <span class="reward-tier">
                                {unlocked ? '🎁' : '🔒'}
                                {$_('profile.levelFull', {
                                    values: { level: reward.level },
                                })}
                            </span>
                            <span class="reward-desc">{reward.description}</span>
                            {#if unlocked && isOwnProfile}
                                <button
                                    type="button"
                                    class="reward-redeem"
                                    class:redeemed
                                    aria-pressed={redeemed}
                                    onclick={() => toggleRedeem(reward.id, redeemed)}
                                >
                                    {redeemed
                                        ? `✓ ${$_('profile.rewardRedeemed')}`
                                        : $_('profile.rewardRedeem')}
                                </button>
                            {:else if unlocked && redeemed}
                                <span class="reward-redeemed-tag"
                                    >✓ {$_('profile.rewardRedeemed')}</span
                                >
                            {/if}
                            <button
                                type="button"
                                class="reward-remove"
                                aria-label={$_('profile.rewardRemove')}
                                onclick={() => removeReward(reward.id)}>✕</button
                            >
                        </li>
                    {/each}
                </ul>
            {/if}

            <form class="reward-form" onsubmit={addReward}>
                <label class="sr-only" for="reward-level"
                    >{$_('profile.rewardLevel')}</label
                >
                <input
                    id="reward-level"
                    type="number"
                    min="2"
                    bind:value={newLevel}
                    class="reward-level-input"
                    aria-label={$_('profile.rewardLevel')}
                />
                <label class="sr-only" for="reward-desc"
                    >{$_('profile.rewardDescription')}</label
                >
                <input
                    id="reward-desc"
                    type="text"
                    bind:value={newDescription}
                    placeholder={$_('profile.rewardPlaceholder')}
                    class="reward-desc-input"
                    required
                />
                <button type="submit" class="reward-add"
                    >{$_('profile.rewardAdd')}</button
                >
            </form>
            {#if rewardError}
                <p class="text-sm text-danger-300">{rewardError}</p>
            {/if}
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

    .reward-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: var(--color-bark-850);
        border: 1px solid var(--color-bark-730);
        border-radius: 0.75rem;
        padding: 0.6rem 0.85rem;
    }

    .reward-row.locked {
        opacity: 0.55;
    }

    .reward-tier {
        flex-shrink: 0;
        font-weight: 600;
        color: var(--color-ink-100);
    }

    .reward-desc {
        flex: 1;
        color: var(--color-ink-300);
    }

    .reward-redeem {
        flex-shrink: 0;
        border: 1px solid var(--color-accent-500);
        border-radius: 999px;
        padding: 0.25rem 0.7rem;
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--color-accent-100);
    }

    .reward-redeem:hover {
        background: var(--color-bark-800);
    }

    .reward-redeem.redeemed {
        border-color: var(--color-success-600);
        color: var(--color-success-300);
    }

    .reward-redeemed-tag {
        flex-shrink: 0;
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--color-success-300);
    }

    .reward-remove {
        flex-shrink: 0;
        color: var(--color-ink-400);
        font-size: 1rem;
        line-height: 1;
    }

    .reward-remove:hover {
        color: var(--color-danger-300);
    }

    .reward-form {
        display: flex;
        gap: 0.5rem;
    }

    .reward-level-input,
    .reward-desc-input {
        background: var(--color-bark-850);
        border: 1px solid var(--color-bark-730);
        border-radius: 0.5rem;
        padding: 0.5rem 0.65rem;
        color: var(--color-ink-100);
    }

    .reward-level-input {
        width: 5rem;
    }

    .reward-desc-input {
        flex: 1;
    }

    .reward-add {
        background: var(--color-accent-500);
        color: var(--color-bark-900);
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
</style>
