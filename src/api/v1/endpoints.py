from fastapi import APIRouter

from src.api.v1.posting import category, content

router = APIRouter(prefix="/v1", tags=["posting-agent"])

router.include_router(category.router)
router.include_router(content.router)