import sys
import os
import logging
from contextlib import asynccontextmanager

# Force the backend directory into the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, notebooks, notes, query, share, upload
from app.config import settings
from app.database import init_database
from app.services.rag_utils import rebuild_vector_store_from_db

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    Keep startup light so the API can boot even if model loading is slow.
    """
    logger.info("--- STARTUP: API booting with lazy model loading enabled ---")
    init_database()
    try:
        rebuild_vector_store_from_db()
    except Exception as exc:
        logger.warning(f"Vector store rebuild skipped during startup: {exc}")
    
    yield
    
    logger.info("--- SHUTDOWN: Cleaning up resources ---")

app = FastAPI(
    title="Document Analyzer API",
    description="Backend AI Context API with FAISS and RAG built for production",
    version="1.0.0",
    lifespan=lifespan  # Hooking the lifespan manager here
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled server error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(query.router)
app.include_router(notebooks.router)
app.include_router(notes.router)
app.include_router(share.router)
app.include_router(auth.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": settings.environment}
