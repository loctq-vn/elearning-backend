from fastapi import FastAPI

from app.core.config import settings
from app.modules.analytics.router import router as analytics_router
from app.modules.ai.router import router as ai_router
from app.modules.auth.router import router as auth_router
from app.modules.categories.router import router as categories_router
from app.modules.courses.router import router as courses_router
from app.modules.exams.router import router as exams_router
from app.modules.instructors.router import router as instructors_router
from app.modules.lessons.router import router as lessons_router
from app.modules.notifications.router import router as notifications_router
from app.modules.notes.router import router as notes_router
from app.modules.orders.router import router as orders_router
from app.modules.progress.router import router as progress_router
from app.modules.questions.router import router as questions_router
from app.modules.transcripts.router import router as transcripts_router
from app.modules.users.router import router as users_router
from app.modules.videos.router import router as videos_router

app = FastAPI(title=settings.app_name, version="0.1.0")

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


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
