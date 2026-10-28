from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import settings_api, work_items
from .config import settings
from .db import init_db
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    yield


app = FastAPI(title="ABAP Lifecycle Studio", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(work_items.router)
app.include_router(settings_api.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}
