<script lang="ts">
    /**
     * WL-5.7 — level-ups, unlocked rewards and earned badges, announced on
     * whatever route is open. Mounted once in the root layout; every page that
     * awards XP calls `refreshProfile()`, which feeds the stores read here.
     *
     * Design-agnostic like the rest of progression: plain text in a plain toast.
     * WL-5.5 replaces the presentation (fanfare, sound) without touching the
     * event logic here.
     */
    import { get } from 'svelte/store'
    import { _ } from 'svelte-i18n'

    import { api } from '$lib/api/client'
    import { levelUp, newAchievements, rewardsUnlockedBetween } from '$lib/progression'

    /** How long one message holds the toast before the next takes over. */
    const DISPLAY_MS = 4000

    // One movement can level you up, unlock two rewards and earn a badge at once,
    // so messages queue rather than overwrite each other.
    let queue = $state<string[]>([])

    function announce(...messages: string[]) {
        queue = [...queue, ...messages]
    }

    function dismiss() {
        queue = queue.slice(1)
    }

    $effect(() => {
        const crossing = $levelUp
        if (crossing == null) {
            return
        }
        // Cleared immediately: the store holds a transition, not a state, and
        // clearing it is what stops a later refresh from re-announcing.
        levelUp.set(null)
        announce(get(_)('celebrate.levelUp', { values: { level: crossing.to } }))

        // Fetched on the crossing rather than kept in a store: reward tiers are
        // household-wide, rarely change, and are only needed at this instant.
        api.rewards
            .list()
            .then((tiers) => {
                announce(
                    ...rewardsUnlockedBetween(crossing.from, crossing.to, tiers).map(
                        (tier) =>
                            get(_)('celebrate.rewardUnlocked', {
                                values: { reward: tier.description },
                            }),
                    ),
                )
            })
            .catch(() => {
                // A reward callout that can't load must not swallow the level-up.
            })
    })

    $effect(() => {
        const earned = $newAchievements
        if (earned.length === 0) {
            return
        }
        newAchievements.set([])
        announce(
            ...earned.map((key) =>
                get(_)('celebrate.badgeEarned', {
                    values: { name: get(_)(`achievement.${key}.name`) },
                }),
            ),
        )
    })

    $effect(() => {
        if (queue.length === 0) {
            return
        }
        const timer = setTimeout(dismiss, DISPLAY_MS)
        return () => clearTimeout(timer)
    })
</script>

{#if queue.length > 0}
    <div class="celebration" role="status" aria-live="polite">
        <span class="celebration-text">{queue[0]}</span>
        <button
            type="button"
            class="celebration-close"
            aria-label={$_('common.close')}
            onclick={dismiss}
        >
            ✕
        </button>
    </div>
{/if}

<style>
    /* Top-anchored on purpose: the chamber's own consume/undo toast owns the
       bottom of the screen, and these two can be on screen together. Offset
       below the nav (`--nav-offset` from the layout) so a 4-second toast never
       sits on top of the links. */
    .celebration {
        position: fixed;
        /* The 0.75rem gap also covers the slide-in, which starts 0.5rem higher. */
        top: calc(var(--nav-offset, 3.25rem) + 0.75rem);
        /* Centered by auto margins rather than `left: 50%`: with the latter the
           box can only ever be 50vw wide, so `max-width` never applies and the
           text wraps to a column on a phone. */
        left: 0;
        right: 0;
        margin-inline: auto;
        width: fit-content;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        max-width: min(90vw, 28rem);
        padding: 0.6rem 1rem;
        border-radius: 0.75rem;
        /* Indigo with light text in both themes, like the nav. */
        color-scheme: dark;
        background: var(--color-accent-900);
        color: var(--color-accent-100);
        border: 1px solid color-mix(in srgb, var(--color-gold) 55%, transparent);
        font-size: 0.9rem;
        font-weight: 600;
        text-align: center;
        z-index: 40;
        box-shadow: 0 2px 18px rgba(0, 0, 0, 0.65);
        animation: celebration-in 0.3s ease-out;
    }

    .celebration-text {
        min-width: 0;
    }

    .celebration-close {
        flex: 0 0 auto;
        background: transparent;
        color: inherit;
        border: 0;
        /* Kid-sized: WL-6.4 wants tap targets this big everywhere. */
        min-width: 2.75rem;
        min-height: 2.75rem;
        font-size: 0.9rem;
        line-height: 1;
        cursor: pointer;
        opacity: 0.8;
    }

    .celebration-close:hover {
        opacity: 1;
    }

    @keyframes celebration-in {
        from {
            opacity: 0;
            transform: translateY(-0.5rem);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .celebration {
            animation: none;
        }
    }
</style>
