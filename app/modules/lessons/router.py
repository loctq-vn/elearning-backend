"""Chapter and Lesson endpoints (§2.12, §2.13)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import get_current_user
from app.db.models.schema import User, UserRole
from app.db.session import get_db_session
from app.modules.lessons.schemas import (
    ChapterCreate,
    ChapterDeleteResponse,
    ChapterItem,
    ChapterUpdate,
    CourseReorderRequest,
    LessonCreateResponse,
    LessonDeleteResponse,
    LessonDetailOut,
    ReorderResponse,
)
from app.modules.lessons.service import LessonService

router = APIRouter(tags=["lessons"])


def _require_admin(current_user: User) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Chỉ quản trị viên mới có quyền thực hiện.",
        )
    return current_user


# ── Chapters (§2.12) ──────────────────────────────────────────────────────────


@router.post(
    "/admin/courses/{course_id}/chapters",
    response_model=ChapterItem,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: thêm chương học vào khóa học (§2.12a)",
)
async def create_chapter(
    course_id: UUID,
    payload: ChapterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChapterItem:
    _require_admin(current_user)
    return await LessonService(db).create_chapter(course_id, payload)


@router.put(
    "/admin/chapters/{chapter_id}",
    response_model=ChapterItem,
    summary="Admin: sửa tên chương học (§2.12b)",
)
async def update_chapter(
    chapter_id: UUID,
    payload: ChapterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChapterItem:
    _require_admin(current_user)
    return await LessonService(db).update_chapter(chapter_id, payload)


@router.delete(
    "/admin/chapters/{chapter_id}",
    response_model=ChapterDeleteResponse,
    summary="Admin: xóa chương học và bài học bên trong (§2.12c)",
)
async def delete_chapter(
    chapter_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChapterDeleteResponse:
    _require_admin(current_user)
    return await LessonService(db).delete_chapter(chapter_id)


@router.put(
    "/admin/courses/{course_id}/reorder",
    response_model=ReorderResponse,
    summary="Admin: sắp xếp lại thứ tự chương và bài học (§2.12d)",
)
async def reorder_course(
    course_id: UUID,
    payload: CourseReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReorderResponse:
    _require_admin(current_user)
    return await LessonService(db).reorder_course(course_id, payload)


# ── Lessons (§2.13) ───────────────────────────────────────────────────────────


@router.post(
    "/admin/chapters/{chapter_id}/lessons",
    response_model=LessonCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: thêm bài học mới kèm tải lên video (§2.13a)",
)
async def create_lesson(
    chapter_id: UUID,
    title: str = Form(..., min_length=2, max_length=200, description="Tên bài học"),
    description: str | None = Form(None, description="Mô tả bài học"),
    order: int | None = Form(None, description="Thứ tự hiển thị"),
    is_trial_allowed: bool = Form(False, description="Cho phép học thử không cần mua"),
    video: UploadFile | None = File(None, description="Tệp video đính kèm (tùy chọn)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LessonCreateResponse:
    _require_admin(current_user)
    return await LessonService(db).create_lesson(
        chapter_id,
        title=title,
        description=description,
        order=order,
        is_trial_allowed=is_trial_allowed,
        video_file=video,
    )


@router.put(
    "/admin/lessons/{lesson_id}",
    response_model=LessonDetailOut,
    summary="Admin: cập nhật bài học (§2.13b)",
)
async def update_lesson(
    lesson_id: UUID,
    title: str | None = Form(None, min_length=2, max_length=200),
    description: str | None = Form(None),
    order: int | None = Form(None),
    is_trial_allowed: bool | None = Form(None),
    video: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LessonDetailOut:
    _require_admin(current_user)
    return await LessonService(db).update_lesson(
        lesson_id,
        title=title,
        description=description,
        order=order,
        is_trial_allowed=is_trial_allowed,
        video_file=video,
    )


@router.delete(
    "/admin/lessons/{lesson_id}",
    response_model=LessonDeleteResponse,
    summary="Admin: xóa bài học (§2.13c)",
)
async def delete_lesson(
    lesson_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LessonDeleteResponse:
    _require_admin(current_user)
    return await LessonService(db).delete_lesson(lesson_id)
