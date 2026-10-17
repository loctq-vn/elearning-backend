from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.adapters.storage import S3StorageAdapter, StorageConnectionError
from app.core.config import settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.db.session import get_db_session
from app.modules.ai.router import router as ai_router
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.categories.router import router as categories_router
from app.modules.courses.router import router as courses_router
from app.modules.exams.router import router as exams_router
from app.modules.instructors.router import router as instructors_router
from app.modules.lessons.router import router as lessons_router
from app.modules.notes.router import router as notes_router
from app.modules.notifications.router import router as notifications_router
from app.modules.orders.router import router as orders_router
from app.modules.progress.router import router as progress_router
from app.modules.questions.router import router as questions_router
from app.modules.transcripts.router import router as transcripts_router
from app.modules.users.router import router as users_router
from app.modules.videos.router import router as videos_router

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API cho nền tảng học trực tuyến thông minh.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


def custom_openapi() -> dict[str, object]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = schema.setdefault("components", {})
    component_schemas = components.setdefault("schemas", {})
    component_schemas.update(
        {
            "ApiResponse": {
                "title": "ApiResponse",
                "type": "object",
                "required": ["data", "message"],
                "properties": {
                    "data": {"title": "Data"},
                    "message": {"type": "string", "default": "OK"},
                },
            },
            "PaginatedResponse": {
                "title": "PaginatedResponse",
                "type": "object",
                "required": ["data", "total", "page", "page_size", "total_pages"],
                "properties": {
                    "data": {"title": "Data", "type": "array", "items": {}},
                    "total": {"type": "integer", "minimum": 0},
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1},
                    "total_pages": {"type": "integer", "minimum": 0},
                },
            },
            "ErrorBody": {
                "title": "ErrorBody",
                "type": "object",
                "required": ["code", "message"],
                "properties": {
                    "code": {"type": "string", "example": "NOT_FOUND"},
                    "message": {"type": "string"},
                    "details": {"type": "object", "nullable": True},
                },
            },
            "ErrorResponse": {
                "title": "ErrorResponse",
                "type": "object",
                "required": ["error"],
                "properties": {
                    "error": {"$ref": "#/components/schemas/ErrorBody"},
                },
            },
        }
    )
    components.setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT access token in the Authorization: Bearer <token> header.",
    }
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

for module_router in (
    auth_router,
    users_router,
    instructors_router,
    categories_router,
    courses_router,
    lessons_router,
    videos_router,
    transcripts_router,
    ai_router,
    questions_router,
    exams_router,
    notes_router,
    progress_router,
    orders_router,
    notifications_router,
    analytics_router,
):
    app.include_router(module_router, prefix=settings.api_prefix)


@app.get(settings.api_prefix, tags=["system"])
async def api_root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "ok"}


@app.get("/health", tags=["system"])
async def health_check(db: AsyncSession = Depends(get_db_session)) -> JSONResponse:
    checks: dict[str, str] = {"api": "ok"}

    # 1. Check RDS database connection
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # 2. Check S3 storage connection
    try:
        storage = S3StorageAdapter(settings)
        storage.check_connection()
        checks["storage"] = "ok"
    except StorageConnectionError as exc:
        checks["storage"] = f"error: {exc}"
    except Exception as exc:
        checks["storage"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        content={"status": overall, "checks": checks},
        status_code=status_code,
    )

