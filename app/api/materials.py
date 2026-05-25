from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import HomeMaterial, User
from app.schemas.user import MaterialBatchUpdate

router = APIRouter(prefix="/materials", tags=["materials"])

DEFAULT_MATERIALS_CATALOG = {
    "crafts": [
        "paper", "cardboard", "crayons", "markers", "paint", "glue",
        "scissors (child-safe)", "tape", "stickers", "play dough",
        "popsicle sticks", "string", "buttons", "fabric scraps",
        "cotton balls", "pipe cleaners", "beads (large)",
    ],
    "kitchen": [
        "flour", "sugar", "baking soda", "vinegar", "food coloring",
        "rice", "pasta (dry)", "salt", "oil", "cookie cutters",
    ],
    "sports": [
        "ball", "jump rope", "hula hoop", "chalk", "bicycle",
        "scooter", "frisbee", "balloons",
    ],
    "outdoor": [
        "sand toys", "watering can", "magnifying glass", "bucket",
        "nature collection bag",
    ],
    "toys": [
        "building blocks", "lego", "puzzle", "board games",
        "dolls/figures", "cars/trucks", "play kitchen set",
    ],
}

DEFAULT_MATERIALS_CATALOG_UK = {
    "творчість": [
        "папір", "картон", "воскові олівці", "фломастери", "фарби", "клей",
        "ножиці (дитячі)", "скотч", "наліпки", "пластилін",
        "палички для поробок", "нитка", "ґудзики", "обрізки тканини",
        "ватні кульки", "синельний дріт", "намистини (великі)",
    ],
    "кухня": [
        "борошно", "цукор", "сода", "оцет", "харчовий барвник",
        "рис", "макарони (сухі)", "сіль", "олія", "форми для печива",
    ],
    "спорт": [
        "м'яч", "скакалка", "хулахуп", "крейда", "велосипед",
        "самокат", "фрізбі", "повітряні кульки",
    ],
    "вулиця": [
        "іграшки для піску", "лійка", "лупа", "відерце",
        "торбинка для знахідок у природі",
    ],
    "іграшки": [
        "кубики", "лего", "пазли", "настільні ігри",
        "ляльки/фігурки", "машинки/вантажівки", "іграшкова кухня",
    ],
}


@router.get("/catalog")
async def get_materials_catalog(lang: str = Query(default="en")):
    if lang.lower().startswith("uk"):
        return DEFAULT_MATERIALS_CATALOG_UK
    return DEFAULT_MATERIALS_CATALOG


@router.get("/")
async def get_user_materials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HomeMaterial).where(HomeMaterial.user_id == user.id, HomeMaterial.is_available.is_(True))
    )
    materials = result.scalars().all()
    return [{"name": m.material_name, "category": m.category} for m in materials]


@router.put("/")
async def update_materials(
    data: MaterialBatchUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(HomeMaterial).where(HomeMaterial.user_id == user.id))

    for mat in data.materials:
        db.add(HomeMaterial(
            user_id=user.id,
            material_name=mat.material_name,
            category=mat.category,
            is_available=mat.is_available,
        ))

    await db.flush()
    return {"status": "ok", "count": len(data.materials)}
