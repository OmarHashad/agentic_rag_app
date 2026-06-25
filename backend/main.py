from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.v1.router import router as v1_router
from backend.storage.minio_client import get_minio_client, ensure_bucket_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = get_minio_client()
    ensure_bucket_exists(client)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)
