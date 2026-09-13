"""Loopback UI. Strict Host/Origin checks, no CORS, per-launch mutation token."""

import os
import secrets
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .history import import_hermes


def default_app():
    from .service import Lab
    from .store import Store

    return create_app(Lab(Store(os.environ["AGENT_FIX_LAB_HOME"])))


def create_app(lab):
    app = FastAPI(title="Agent Fix Lab", docs_url=None, redoc_url=None, openapi_url=None)
    token = secrets.token_urlsafe(32)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )

    @app.middleware("http")
    async def boundary(request, call_next):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"error": "Cross-origin requests forbidden"}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"error": "Cross-site requests forbidden"}, status_code=403)
        if request.method not in ("GET", "HEAD"):
            if not secrets.compare_digest(request.headers.get("x-afl-token", ""), token):
                return JSONResponse({"error": "Invalid mutation token"}, status_code=403)
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 65536:
                    return JSONResponse({"error": "Request too large"}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ValueError)
    async def bad_value(request, exc):
        return JSONResponse({"error": str(exc)}, status_code=400)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"error": "Record not found"}, status_code=404)

    @app.exception_handler(OSError)
    async def failed_operation(request, exc):
        return JSONResponse(
            {"error": "Local file/process unavailable; inspect CLI diagnostics"}, status_code=400
        )

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (
            (Path(__file__).parent / "assets/index.html").read_text().replace("TOKEN_VALUE", token)
        )

    @app.get("/assets/{name}")
    def asset(name: str):
        if name not in ("app.js", "style.css", "interventions.js"):
            return Response(status_code=404)
        return Response(
            (Path(__file__).parent / "assets" / name).read_text(),
            media_type="text/javascript" if name.endswith(".js") else "text/css",
        )

    @app.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)

    @app.get("/interventions", response_class=HTMLResponse)
    def intervention_page():
        return (
            (Path(__file__).parent / "assets/interventions.html")
            .read_text()
            .replace("TOKEN_VALUE", token)
        )

    @app.get("/api/interventions")
    def intervention_list(offset: int = 0, limit: int = 10):
        from .interventions import listing

        return listing(lab, offset, limit)

    @app.get("/api/interventions/{identifier}")
    def intervention_detail(identifier: str):
        from .interventions import inspect

        return inspect(lab, identifier)

    @app.post("/api/interventions")
    def intervention_propose(body: dict):
        from .interventions import propose

        return propose(lab, body)

    @app.post("/api/interventions/{identifier}/evaluate")
    def intervention_evaluate(identifier: str, body: dict):
        from .interventions import evaluate

        if set(body) != {"candidate_digest", "reviewed"}:
            raise ValueError("Exact candidate digest and explicit review required")
        return evaluate(lab, identifier, body["candidate_digest"], reviewed=body["reviewed"])

    @app.post("/api/interventions/{identifier}/review")
    def intervention_review(identifier: str, body: dict):
        from .interventions import review

        if set(body) != {"candidate_digest", "evaluation_id", "decision", "note"}:
            raise ValueError("Exact evidence review fields required")
        return review(
            lab,
            identifier,
            body["evaluation_id"],
            body["candidate_digest"],
            body["decision"],
            body["note"],
        )

    @app.get("/api/cases")
    def cases(q: str = "", status: str | None = None):
        return lab.list_cases(q, status)

    @app.get("/api/corrections")
    def corrections():
        from .corrections import candidates

        return candidates(lab.store)

    @app.post("/api/corrections/{candidate_id}/review")
    def correction_review(candidate_id: str, body: dict):
        from .corrections import review

        if set(body) - {"decision", "note", "retracts"}:
            raise ValueError("Unexpected correction review fields")
        return review(
            lab.store, candidate_id, body["decision"], body["note"], retracts=body.get("retracts")
        )

    @app.get("/api/cases/{case_id}")
    def detail(case_id: str):
        return lab.detail(case_id)

    @app.get("/api/cases/{case_id}/export")
    def export(case_id: str):
        return lab.export(case_id)

    @app.post("/api/cases/{case_id}/annotations")
    def annotation(case_id: str, body: dict):
        if set(body) - {"text", "expected", "retracts"} or not isinstance(body.get("text"), str):
            raise ValueError("Expected text, optional expected and retracts")
        return lab.annotate(
            case_id, body["text"], body.get("expected"), retracts=body.get("retracts")
        )

    @app.post("/api/cases/{case_id}/baseline")
    def baseline(case_id: str, body: dict):
        return lab.baseline(case_id, body["logical_path"], body["baseline"], body["current"])

    @app.post("/api/recipes")
    def recipe(body: dict):
        if body.get("reviewed") is not True:
            raise ValueError("Review checkbox required; historical commands never auto-execute")
        return lab.add_recipe(body["recipe"], reviewed=True)

    @app.post("/api/recipes/{recipe_id}/run")
    def run(recipe_id: str):
        return lab.run(recipe_id)

    @app.post("/api/import")
    def import_current(body: dict):
        # Browser cannot choose arbitrary files or source identity.
        home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        if set(body) - {"after", "before", "session", "limit", "dry_run"}:
            raise ValueError("Unknown import fields")
        return import_hermes(
            lab.store,
            home / "state.db",
            source_id="local-hermes",
            before=body.get("before", time.time()),
            after=body.get("after", 0),
            session=body.get("session"),
            limit=body.get("limit", 100),
            dry_run=body.get("dry_run", False),
            cohort="dogfood",
        )

    return app
