from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


def _would_create_cycle(db: Session, category_id: int, new_parent_id: int | None) -> bool:
    """Return True if assigning new_parent_id to category_id would introduce a cycle."""
    if new_parent_id is None:
        return False
    if new_parent_id == category_id:
        return True

    visited: set[int] = set()
    current_id: int | None = new_parent_id

    while current_id is not None:
        if current_id in visited:
            # Existing broken graph; treat as invalid for reassignment safety.
            return True
        if current_id == category_id:
            return True

        visited.add(current_id)
        current = db.get(Category, current_id)
        if current is None:
            # Missing parent row is treated as chain end.
            return False
        current_id = current.parent_id

    return False


@router.get("/", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryRead]:
    return db.query(Category).order_by(Category.name).all()  # type: ignore[return-value]


@router.post("/", response_model=CategoryRead, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)) -> CategoryRead:
    if data.parent_id is not None:
        parent = db.get(Category, data.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")

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

    payload = data.model_dump(exclude_unset=True)

    if "parent_id" in payload:
        new_parent_id = payload["parent_id"]
        if new_parent_id is not None:
            parent = db.get(Category, new_parent_id)
            if not parent:
                raise HTTPException(status_code=404, detail="Parent category not found")
        if _would_create_cycle(db, category_id=category_id, new_parent_id=new_parent_id):
            raise HTTPException(
                status_code=422,
                detail="Invalid parent assignment: category hierarchy cycle detected",
            )
        category.parent_id = new_parent_id

    if "name" in payload:
        name = payload["name"]
        if name is not None:
            category.name = name.strip()

    if "icon" in payload:
        category.icon = payload["icon"] or None

    if "restock_target" in payload:
        category.restock_target = payload["restock_target"]

    if "restock_min" in payload:
        category.restock_min = payload["restock_min"]

    if "restock_inherit" in payload:
        # bool already validated by schema when present
        category.restock_inherit = bool(payload["restock_inherit"])

    # Enforce effective local consistency when both are set on this category.
    if (
        category.restock_target is not None
        and category.restock_min is not None
        and category.restock_target < category.restock_min
    ):
        raise HTTPException(
            status_code=422,
            detail="restock_target must be greater than or equal to restock_min",
        )

    db.commit()
    db.refresh(category)
    return CategoryRead.model_validate(category, from_attributes=True)
