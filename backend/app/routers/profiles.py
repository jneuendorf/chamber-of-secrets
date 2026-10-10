from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InventoryTransaction, Profile
from app.schemas import PantryDexEntry, ProfileCreate, ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_profile_or_404(profile_id: int, db: Session) -> Profile:
    """Archived profiles count: a saved link or a device's stale picker id may
    still point at one. Shared by every router that takes a profile id."""
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/", response_model=list[ProfileRead])
def list_profiles(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[Profile]:
    query = db.query(Profile).order_by(Profile.created_at)
    if not include_archived:
        query = query.filter(Profile.is_archived.is_(False))
    return query.all()


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: int, db: Session = Depends(get_db)) -> Profile:
    return get_profile_or_404(profile_id, db)


@router.get("/{profile_id}/pantry-dex", response_model=list[PantryDexEntry])
def get_pantry_dex(profile_id: int, db: Session = Depends(get_db)) -> list[PantryDexEntry]:
    """Products this profile has stocked (WL-5.4), in the order they were first
    collected. Derived from attributed `in` movements, so nothing is stored."""
    get_profile_or_404(profile_id, db)
    first_collected = func.min(InventoryTransaction.transacted_at)
    rows = db.execute(
        select(
            InventoryTransaction.product_id,
            first_collected,
            func.count(InventoryTransaction.id),
        )
        .where(
            InventoryTransaction.profile_id == profile_id,
            InventoryTransaction.type == "in",
        )
        .group_by(InventoryTransaction.product_id)
        .order_by(first_collected, InventoryTransaction.product_id),
    ).all()
    return [
        PantryDexEntry(product_id=product_id, first_collected_at=first_at, times_stocked=times)
        for product_id, first_at, times in rows
    ]


@router.post("/", response_model=ProfileRead, status_code=201)
def create_profile(data: ProfileCreate, db: Session = Depends(get_db)) -> Profile:
    profile = Profile(**data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    db: Session = Depends(get_db),
) -> Profile:
    profile = get_profile_or_404(profile_id, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile
