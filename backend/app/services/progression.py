"""Progression — XP and daily streaks (WL-5.3).

The single place XP is awarded. Everything else (levels, achievements, rewards)
*derives* from `Profile.xp` via `level_for_xp` — no feature keeps its own counter.
"""

from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Profile


# Flat per-event XP: stocking is the effortful act, using something up is the reward.
# ponytail: no combo/expiry bonuses — expiry isn't tracked yet, and WL-5.4 balances
# the curve once achievements exist.
XP_PER_EVENT = {"in": 10, "out": 2}


def award_transaction(profile: Profile, tx_type: str, today: date | None = None) -> None:
    """Award XP for a stock movement and roll the daily streak. Caller commits.

    # ponytail: not reversed when the movement is undone (WL-5.2) — a few XP for a
    mis-tap is cheaper than an award ledger; add one if XP ever buys something scarce.
    """
    profile.xp += XP_PER_EVENT.get(tx_type, 0)
    bump_streak(profile, today or date.today())


def bump_streak(profile: Profile, today: date) -> None:
    """Extend the streak on a consecutive day, restart it after a gap."""
    if profile.last_active_on == today:
        return

    consecutive = profile.last_active_on == today - timedelta(days=1)
    profile.current_streak = profile.current_streak + 1 if consecutive else 1
    profile.longest_streak = max(profile.longest_streak, profile.current_streak)
    profile.last_active_on = today
