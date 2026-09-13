import logging
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import RequestResponseEndpoint

from app.api.admin import router as admin_router
from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.knowledge import admin_router as knowledge_admin_router
from app.api.knowledge import router as knowledge_router
from app.api.tickets import admin_router as tickets_admin_router
from app.api.tickets import router as tickets_router
from app.api.users import router as users_router
from app.core.config import assert_production_safe, get_settings
from app.core.limiter import limiter
from app.core.logging_config import configure_logging, set_request_id

settings = get_settings()
configure_logging(settings)
assert_production_safe(settings)

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.state.limiter = limiter
# slowapi's handler is typed for RateLimitExceeded specifically, which mypy sees
# as narrower than Starlette's generic Exception-handler signature.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Every request gets a request id — reused from an incoming
    `X-Request-ID` header if a reverse proxy/load balancer already set one,
    otherwise generated here. Stored in a contextvar (app/core/logging_config.py)
    so every log line emitted while handling this request — from this
    middleware, a route, a service, anywhere — carries the same id without
    threading it through every function signature, and echoed back in the
    response header so a client (or the person filing a bug report) can quote
    it back for support/diagnostic purposes.
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(request_id)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """A minimal, uncontroversial baseline: this is a JSON API, not a page
    renderer, so it should never be framed or MIME-sniffed into executing as
    something else. This does not replace a real CSP (there's no HTML to
    scope one to) — see docs/testing.md's security review for what this
    platform does and does not do about transport/browser hardening.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    """Centralized handling for anything not already caught by a route's own
    try/except or by FastAPI's built-in HTTPException/validation handlers —
    i.e. genuine bugs and infrastructure failures. Logs the full exception
    server-side (with the request id, for correlation) and returns a clean,
    consistent JSON body that never includes the exception message, a
    traceback, a database error string, or an internal file path — only the
    request id, so the failure can be found in server-side logs afterward.
    `debug_detail` is included only when DEBUG=true, which itself can never
    be true in production (see assert_production_safe in app/core/config.py).
    """
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "Unhandled exception",
        extra={"request_id": request_id, "path": request.url.path, "method": request.method},
    )
    body: dict[str, str | None] = {
        "detail": "An unexpected error occurred. Please try again.",
        "request_id": request_id,
    }
    if settings.debug:
        body["debug_detail"] = str(exc)
    return JSONResponse(status_code=500, content=body)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(knowledge_router)
app.include_router(knowledge_admin_router)
app.include_router(ai_router)
app.include_router(tickets_router)
app.include_router(tickets_admin_router)
app.include_router(admin_router)
