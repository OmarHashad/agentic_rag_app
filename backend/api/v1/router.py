from fastapi import APIRouter
from backend.api.v1.endpoints import data, users, documents

router = APIRouter()
router.include_router(data.router)
router.include_router(users.router)
router.include_router(documents.router)
