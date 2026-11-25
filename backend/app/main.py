from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import register_handlers
from app.services.model_service import ModelService
from app.services.patient_repo import PatientRepo
from app.services.predictor import Predictor

log = logging.getLogger("emralert")


def build_state(app: FastAPI, settings: Settings) -> None:
    model = ModelService(settings.model_path, settings.model_metadata_path)
    app.state.model = model
    app.state.repo = None
    app.state.scores = None
    try:
        model.load()
        repo = PatientRepo(settings.patient_data_path)
        model.set_reference(repo.df)
        app.state.repo = repo
    except Exception:  # noqa: BLE001 - API stays up and reports "degraded" on /health
        log.exception("startup incomplete")
        return
    predictor = Predictor(model, settings)
    app.state.predictor = predictor
    feats = [PatientRepo.features(r) for _, r in repo.df.iterrows()]
    app.state.scores = predictor.score_all(feats, repo.df.index)
    log.info("scored %d patients, %d alerts", len(feats), int(app.state.scores["alert"].sum()))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        build_state(app, settings)
        yield

    app = FastAPI(
        title="Drug A EMR Alert API", version="1.0.0", lifespan=lifespan,
        description="Scores Disease X patients for likelihood of receiving Drug A and raises an EMR alert "
                    "when an eligible patient is unlikely to be treated.")
    app.state.settings = settings
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        log.info("%s %s -> %s %.1fms rid=%s", request.method, request.url.path, response.status_code,
                 (time.perf_counter() - t0) * 1000, request.state.request_id)
        return response

    register_handlers(app)
    app.include_router(router)
    return app


app = create_app()
