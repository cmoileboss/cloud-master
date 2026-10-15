import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.database import init_db, make_engine
from app.llm import LLMError, LLMService
from app.routes import documents, health
from app.storage import LocalStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def llm_error_response(request: Request, exc: LLMError):
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Assemble l'application. Les tests appellent cette fonction avec leurs propres paramètres."""
    settings = settings or Settings()
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(engine)
        yield
        engine.dispose()

    app = FastAPI(title="FFK — Convocations", lifespan=lifespan)

    # Services partagés, fournis aux routes par app/deps.py.
    app.state.engine = engine
    app.state.llm = LLMService(settings)
    app.state.storage = LocalStorage(settings.data_dir / "documents")

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
