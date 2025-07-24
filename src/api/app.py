from fastapi import APIRouter

from src.api.v1 import endpoints

router = APIRouter(prefix="/api")

router.include_router(endpoints.router)