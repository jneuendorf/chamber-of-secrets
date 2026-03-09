from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryRead]:
    return db.query(Category).order_by(Category.name).all()  # type: ignore[return-value]


@router.post("/", response_model=CategoryRead, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)) -> CategoryRead:
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category  # type: ignore[return-value]


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)
) -> CategoryRead:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    category.icon = data.icon or None
    db.commit()
    db.refresh(category)
    return CategoryRead.model_validate(category, from_attributes=True)
