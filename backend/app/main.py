from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.knowledge import admin_router as knowledge_admin_router
from app.api.knowledge import router as knowledge_router
from app.api.tickets import admin_router as tickets_admin_router
from app.api.tickets import router as tickets_router
from app.api.users import router as users_router
from app.core.config import get_settings
from app.core.limiter import limiter

settings = get_settings()

app = FastAPI(title=settings.app_name)

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

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(knowledge_router)
app.include_router(knowledge_admin_router)
app.include_router(ai_router)
app.include_router(tickets_router)
app.include_router(tickets_admin_router)
