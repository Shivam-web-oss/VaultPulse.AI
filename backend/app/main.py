import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routes.chat import router as chat_router
from app.routes.collections import router as collections_router
from app.routes.conversations import router as conversations_router
from app.routes.upload import router as upload_router
from app.routes.auth import router as auth_router

load_dotenv()

app = FastAPI(title="VaultPulse.AI API", version="1.0.0")
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(conversations_router, prefix="/api")
app.include_router(collections_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "service": "vaultpulse-api"}
