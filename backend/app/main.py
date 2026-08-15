from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.attendance import router as attendance_router
from app.api.chat import router as chat_router
from app.api.docflow import router as docflow_router
from app.api.documents import router as documents_router
from app.api.payments import router as payments_router
from app.auth.router import router as auth_router
from app.config import get_settings
from app.db import init_db
from app.schemas import HealthOut

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Module routers (notifications, admin) are wired here in later sessions.
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(payments_router)
app.include_router(attendance_router)
app.include_router(docflow_router)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok", app=settings.app_name)
