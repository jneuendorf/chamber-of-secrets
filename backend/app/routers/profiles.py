from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import ProfileCreate, ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/", response_model=list[ProfileRead])
def list_profiles(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[Profile]:
    query = db.query(Profile).order_by(Profile.created_at)
    if not include_archived:
        query = query.filter(Profile.is_archived.is_(False))
    return query.all()


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
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile
