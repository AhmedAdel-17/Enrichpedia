from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routes import process, articles


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Enrich Media API",
    description="Transform Facebook content into encyclopedic articles",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process.router, prefix="/api/process", tags=["Process"])
app.include_router(articles.router, prefix="/api/articles", tags=["Articles"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
