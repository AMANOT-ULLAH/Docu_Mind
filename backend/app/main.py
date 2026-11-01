from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api.documents import router
from app.db.database import init_db
from app.services import worker


@asynccontextmanager
async def lifespan(app):
    init_db()
    Path(config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    worker.requeue_unfinished()
    yield


app = FastAPI(title="DocuMind API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)