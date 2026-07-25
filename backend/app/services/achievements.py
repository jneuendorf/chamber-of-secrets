"""Achievements — earned badges (WL-5.4).

Badges are *derived* from what already exists (transaction counts, `Profile.xp`,
streaks) — no feature keeps its own counter. Only the fact that a badge was
earned is stored, so re-checking is idempotent and adding a rule retro-awards it
on the next movement.

Names, descriptions and art live in the frontend catalog; the backend knows keys.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import InventoryTransaction, Profile, ProfileAchievement, level_for_xp

# Badge keys — mirror `achievement.*` in the locales and the frontend catalog.
# The numeric suffix is the threshold; check_progress inlines it at the use-site.
FIRST_SCAN = "first_scan"
STOCKED_50 = "stocked_50"
STREAK_7 = "streak_7"
LEVEL_5 = "level_5"
EXPLORER = "explorer"


def grant(db: Session, profile: Profile, key: str) -> bool:
    """Award a badge once. Returns True only the first time it is earned."""
    if any(earned.achievement_key == key for earned in profile.achievements):
        return False
    db.add(ProfileAchievement(profile_id=profile.id, achievement_key=key))
    return True


def check_progress(db: Session, profile: Profile) -> list[str]:
    """Grant every derivable badge the profile now qualifies for. Caller commits.

    # ponytail: one COUNT per movement — a few thousand rows on a home LAN. If it
    ever shows up, cache the count on the profile.
    """
    stocked = db.scalar(
        select(func.count())
        .select_from(InventoryTransaction)
        .where(
            InventoryTransaction.profile_id == profile.id,
            InventoryTransaction.type == "in",
        ),
    )
    stocked = stocked or 0

    qualifies = {
        FIRST_SCAN: stocked >= 1,
        STOCKED_50: stocked >= 50,
        STREAK_7: profile.longest_streak >= 7,
        LEVEL_5: level_for_xp(profile.xp) >= 5,
    }
    return [key for key, earned in qualifies.items() if earned and grant(db, profile, key)]
