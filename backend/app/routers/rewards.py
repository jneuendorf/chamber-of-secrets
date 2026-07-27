from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile, ProfileReward, RewardTier, level_for_xp
from app.schemas import RewardTierCreate, RewardTierRead

router = APIRouter(prefix="/rewards", tags=["rewards"])


@router.get("/", response_model=list[RewardTierRead])
def list_rewards(db: Session = Depends(get_db)) -> list[RewardTier]:
    return db.query(RewardTier).order_by(RewardTier.level, RewardTier.id).all()


@router.post("/", response_model=RewardTierRead, status_code=201)
def create_reward(data: RewardTierCreate, db: Session = Depends(get_db)) -> RewardTier:
    reward = RewardTier(**data.model_dump())
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


@router.delete("/{reward_id}", status_code=204)
def delete_reward(reward_id: int, db: Session = Depends(get_db)) -> None:
    reward = db.get(RewardTier, reward_id)
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    db.delete(reward)  # profile_rewards cascade via the FK's ON DELETE CASCADE
    db.commit()


@router.post("/{reward_id}/redemption", status_code=204)
def redeem_reward(reward_id: int, profile_id: int, db: Session = Depends(get_db)) -> None:
    """Mark a reward redeemed for a profile (WL-5.4). Idempotent.

    Guards that the reward is actually unlocked (level reached) — the "only your
    own profile" rule is a client guard, not enforced here (login-less profiles)."""
    reward = db.get(RewardTier, reward_id)
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if level_for_xp(profile.xp) < reward.level:
        raise HTTPException(status_code=409, detail="Reward not unlocked yet")

    existing = (
        db.query(ProfileReward)
        .filter_by(profile_id=profile_id, reward_tier_id=reward_id)
        .first()
    )
    if existing:  # already redeemed — idempotent, nothing to do
        return
    db.add(ProfileReward(profile_id=profile_id, reward_tier_id=reward_id))
    db.commit()


@router.delete("/{reward_id}/redemption", status_code=204)
def unredeem_reward(reward_id: int, profile_id: int, db: Session = Depends(get_db)) -> None:
    """Undo a redemption (WL-5.4). Idempotent — a no-op if not redeemed."""
    db.query(ProfileReward).filter_by(
        profile_id=profile_id,
        reward_tier_id=reward_id,
    ).delete()
    db.commit()
