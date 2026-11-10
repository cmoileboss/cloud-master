import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.database import init_db, make_engine
from app.llm import LLMError, LLMService
from app.routes import documents, health
from app.storage import LocalStorage, BlobStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ffk.app")


def llm_error_response(request: Request, exc: LLMError):
    logger.warning("llm_error path=%s status=%s message=%s", request.url.path, exc.status_code, exc.message)
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Assemble l'application. Les tests appellent cette fonction avec leurs propres paramètres."""
    settings = settings or Settings()
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("startup storage_dir=%s cors_origins=%s", settings.data_dir / "documents", settings.cors_origin_list)
        if not (settings.llm_base_url and settings.llm_model and settings.llm_api_key.get_secret_value()):
            logger.warning("llm_not_configured: renseignez LLM_BASE_URL, LLM_MODEL et LLM_API_KEY")
        init_db(engine)
        yield
        engine.dispose()
        logger.info("shutdown")

    app = FastAPI(title="FFK — Convocations", lifespan=lifespan)

    # Services partagés, fournis aux routes par app/deps.py.
    app.state.engine = engine
    app.state.llm = LLMService(settings)
    app.state.storage = LocalStorage(settings.data_dir / "documents")
    app.state.blob_storage = BlobStorage(settings.azure_storage_account_url, settings.azure_storage_container)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.add_exception_handler(LLMError, llm_error_response)
    app.include_router(health.router)
    app.include_router(documents.router)
    return app


app = create_app()
