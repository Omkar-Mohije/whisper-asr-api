import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.config import settings
from app.core.asr_engine import get_whisper_engine

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("whisper_asr_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Initializing %s v%s", settings.APP_NAME, settings.VERSION)
    dev, comp = settings.resolve_device_and_compute()
    logger.info("Default Whisper Configuration: Model=%s, Device=%s, ComputeType=%s",
                settings.WHISPER_MODEL_SIZE, dev, comp)

    # Clean temporary upload directory on startup
    if settings.TEMP_DIR.exists():
        for item in settings.TEMP_DIR.glob("*"):
            try:
                if item.is_file():
                    item.unlink()
            except Exception:
                pass

    yield

    # Clean up on shutdown
    logger.info("Shutting down %s...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static web UI assets
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include API Router
app.include_router(api_router, prefix="/api")


@app.get("/", include_in_schema=False)
async def serve_home():
    """Serves the interactive web app UI."""
    return FileResponse(static_path / "index.html")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Check server logs for details."}
    )
