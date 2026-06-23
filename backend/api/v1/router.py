from fastapi import APIRouter
from backend.api.v1.endpoints import data

router = APIRouter()
router.include_router(data.router)
