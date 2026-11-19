"""Loopback-only local API for the React dashboard.

No remote authentication is offered by design: never deploy this service publicly.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .config import Settings
from .duplicates import find_duplicates
from .models import CleanSlateError, ScanResult
from .rules import RULES
from .scanner import scan
from .service import CleanupService


class ScanRequest(BaseModel):
    root: str = Field(min_length=1, max_length=4096)
    max_depth: int = Field(default=8, ge=0, le=30)


class CleanupRequest(BaseModel):
    scan_id: str
    candidate_ids: list[str] = Field(min_length=1, max_length=10_000)
    confirm_review: bool = False


class RestoreRequest(BaseModel):
    operation_id: str


class DuplicatesRequest(BaseModel):
    root: str = Field(min_length=1, max_length=4096)


class ScanSessions:
    """Short-lived, one-use server-issued scan receipts to prevent forged candidate paths."""

    def __init__(self, lifetime_seconds: int = 20 * 60):
        self.sessions: dict[str, tuple[float, ScanResult]] = {}
        self.lifetime_seconds = lifetime_seconds
        self.lock = threading.Lock()

    def put(self, result: ScanResult) -> str:
        with self.lock:
            self._expire()
            key = uuid.uuid4().hex
            self.sessions[key] = (time.monotonic(), result)
            return key

    def take(self, key: str) -> ScanResult:
        with self.lock:
            self._expire()
            item = self.sessions.pop(key, None)
            if item is None:
                raise CleanSlateError("Scan expired or already used. Start a new scan.")
            return item[1]

    def _expire(self) -> None:
        oldest = time.monotonic() - self.lifetime_seconds
        for key, (created, _) in list(self.sessions.items()):
            if created < oldest:
                del self.sessions[key]


def default_workspace() -> Path:
    projects = Path.home() / "Projects"
    return projects if projects.is_dir() else Path.cwd()


def create_app(*, data_dir: Path | None = None, ui_dir: Path | None = None) -> FastAPI:
    """App factory lets tests use isolated storage without altering user files."""
    settings = Settings.load(default_workspace(), data_dir=data_dir)
    service = CleanupService(settings.data_dir)
    sessions = ScanSessions()
    app = FastAPI(
        title="Clean Slate Local API", version=__version__,
        description="Local-only developer workspace cleaning. Never expose to the internet.",
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin:
                allowed = {
                    "http://localhost:5173", "http://127.0.0.1:5173",
                    f"http://{request.headers.get('host', '')}",
                }
                if origin not in allowed:
                    return JSONResponse({"detail": "Untrusted browser origin"}, status_code=403)
            if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
                return JSONResponse({"detail": "JSON content type required"}, status_code=415)
        return await call_next(request)

    @app.exception_handler(CleanSlateError)
    async def clean_slate_error(_request: Request, exc: CleanSlateError):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/api/meta")
    def meta() -> dict:
        return {
            "version": __version__, "default_workspace": str(default_workspace()),
            "data_dir": str(service.data_dir),
            "safety": "Files move into a private quarantine; nothing is permanently deleted.",
        }

    @app.get("/api/rules")
    def rules() -> list[dict]:
        return [
            {"id": rule.id, "label": rule.label, "category": rule.category,
             "ecosystems": sorted(rule.ecosystems), "risk": rule.risk,
             "explanation": rule.explanation}
            for rule in RULES
        ]

    @app.post("/api/scans")
    def start_scan(body: ScanRequest) -> dict:
        result = scan(Path(body.root), data_dir=service.data_dir, max_depth=body.max_depth)
        return {"scan_id": sessions.put(result), **result.to_dict()}

    @app.post("/api/cleanups")
    def clean(body: CleanupRequest) -> dict:
        result = sessions.take(body.scan_id)
        return service.cleanup(result, body.candidate_ids, confirm_review=body.confirm_review)

    @app.get("/api/history")
    def history(limit: int = 30) -> list[dict]:
        return service.journal.history(limit)

    @app.post("/api/restores")
    def restore(body: RestoreRequest) -> dict:
        return service.restore(body.operation_id)

    @app.post("/api/duplicates")
    def duplicates(body: DuplicatesRequest) -> dict:
        return find_duplicates(Path(body.root), data_dir=service.data_dir)

    # The production UI is optional; `npm run dev` always proxies /api to this app.
    directory = ui_dir or Path(os.environ.get(
        "CLEANSLATE_UI_DIR", str(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    ))
    if directory.is_dir():
        app.mount("/", StaticFiles(directory=directory, html=True), name="dashboard")
    else:
        @app.get("/")
        def frontend_instructions() -> dict:
            return {
                "message": "Local API is ready. Start the dashboard with cd frontend && npm run dev.",
                "api_docs": "/docs",
            }
    return app
