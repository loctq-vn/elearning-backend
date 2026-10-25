"""Course business logic layer."""

from __future__ import annotations

from math import ceil
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.storage import S3StorageAdapter, course_thumbnail_key
from app.core.config import settings
from app.core.errors import AppError
from app.db.models.schema import CourseStatus, User, UserRole
from app.modules.courses.repository import CourseRepository
from app.modules.courses.schemas import (
    CategorySimple,
    ChapterOut,
    CourseCreateResponse,
    CourseDeleteResponse,
    CourseDetail,
    CourseListItem,
    CourseListResponse,
    FeaturedCourse,
    InstructorProfileOut,
    LessonSummaryOut,
)

ALLOWED_THUMBNAIL_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_THUMBNAIL_SIZE = 5 * 1024 * 1024  # 5MB


class CourseService:
    """Service handling course catalog and admin operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CourseRepository(db)
        self.storage = S3StorageAdapter(settings)

    # ── Public ────────────────────────────────────────────────────────────────

    async def list_featured(self, limit: int = 10) -> list[FeaturedCourse]:
        """Fetch featured courses for homepage (§2.1)."""
        rows = await self.repo.list_featured(limit=limit)
        return [
            FeaturedCourse(
                id=course.id,
                title=course.title,
                thumbnail_url=course.thumbnail_url,
                price=course.price,
                original_price=None,
                rating_avg=None,
                enrolled_count=enrolled_count,
                banner_url=None,
                instructor_name=inst_name,
                instructor_avatar_url=inst_avatar,
            )
            for course, inst_name, inst_avatar, enrolled_count in rows
        ]

    async def list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 12,
        search: str | None = None,
        category_id: UUID | None = None,
        instructor_id: UUID | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        sort_by: str = "newest",
        status_filter: str | None = None,
        current_user: User | None = None,
    ) -> CourseListResponse:
        """Fetch paginated course list with filters (§2.3)."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 12

        is_admin = bool(current_user and current_user.role == UserRole.ADMIN)

        rows, total = await self.repo.list_paginated(
            page=page,
            page_size=page_size,
            search=search,
            category_id=category_id,
            instructor_id=instructor_id,
            price_min=price_min,
            price_max=price_max,
            sort_by=sort_by,
            status_filter=status_filter,
            is_admin=is_admin,
        )

        items = [
            CourseListItem(
                id=c.id,
                title=c.title,
                thumbnail_url=c.thumbnail_url,
                price=c.price,
                original_price=None,
                rating_avg=None,
                rating_count=None,
                enrolled_count=enrolled_count,
                category_name=cat_name,
                instructor_name=inst_name,
                instructor_avatar_url=inst_avatar,
                status=c.status.value if hasattr(c.status, "value") else str(c.status),
                created_at=c.created_at,
            )
            for c, cat_name, inst_name, inst_avatar, enrolled_count in rows
        ]

        total_pages = ceil(total / page_size) if total > 0 else 0

        return CourseListResponse(
            data=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_detail(
        self, course_id: UUID, current_user: User | None = None
    ) -> CourseDetail:
        """Fetch course details including structure and enrollment (§2.5)."""
        result = await self.repo.get_detail_with_relations(course_id)
        if not result:
            raise AppError(
                status_code=404,
                code="COURSE_NOT_FOUND",
                message="Không tìm thấy khóa học yêu cầu.",
            )

        course, category, instructor, enrolled_count = result

        # Check visibility
        is_admin = bool(current_user and current_user.role == UserRole.ADMIN)
        if course.status != CourseStatus.PUBLISHED and not is_admin:
            raise AppError(
                status_code=404,
                code="COURSE_NOT_FOUND",
                message="Không tìm thấy khóa học yêu cầu.",
            )

        # Check enrollment
        is_enrolled = False
        progress_percent: float | None = None
        if current_user:
            enrollment = await self.repo.get_enrollment(current_user.id, course_id)
            if enrollment:
                is_enrolled = True
                progress_percent = enrollment.progress_percent

        # Course chapters & lessons
        user_id = current_user.id if current_user else None
        chapters_data = await self.repo.get_course_structure(course_id, user_id=user_id)

        chapter_outs: list[ChapterOut] = []
        total_lessons = 0
        total_duration = 0

        for chap, lessons_info in chapters_data:
            lesson_outs: list[LessonSummaryOut] = []
            for lesson, is_completed, has_quiz, has_exercise in lessons_info:
                duration_int = int(round(lesson.duration_seconds or 0))
                total_duration += duration_int
                total_lessons += 1

                # Lock rule: if enrolled, all unlocked. If guest/not enrolled, unlock only trial lessons.
                is_locked = not is_enrolled and not lesson.is_trial_allowed

                lesson_outs.append(
                    LessonSummaryOut(
                        id=lesson.id,
                        title=lesson.title,
                        order=lesson.order_index,
                        duration=duration_int,
                        is_locked=is_locked,
                        is_completed=is_completed if is_enrolled else None,
                        has_quiz=has_quiz,
                        has_exercise=has_exercise,
                    )
                )

            chapter_outs.append(
                ChapterOut(
                    id=chap.id,
                    title=chap.title,
                    order=chap.order_index,
                    lessons=lesson_outs,
                )
            )

        cat_out = CategorySimple(id=category.id, name=category.name) if category else None
        inst_out = (
            InstructorProfileOut(
                id=instructor.id,
                name=instructor.name,
                title=instructor.title,
                bio=instructor.bio,
                avatar_url=instructor.avatar_url,
            )
            if instructor
            else None
        )

        return CourseDetail(
            id=course.id,
            title=course.title,
            description=course.description,
            thumbnail_url=course.thumbnail_url,
            price=course.price,
            original_price=None,
            rating_avg=None,
            rating_count=None,
            enrolled_count=enrolled_count,
            category=cat_out,
            instructor=inst_out,
            is_enrolled=is_enrolled,
            progress_percent=progress_percent,
            chapters=chapter_outs,
            total_lessons=total_lessons,
            total_duration=total_duration,
            status=course.status.value if hasattr(course.status, "value") else str(course.status),
            created_at=course.created_at,
            updated_at=course.updated_at,
        )

    # ── Admin ─────────────────────────────────────────────────────────────────

    async def _handle_thumbnail_upload(
        self, course_id: UUID, thumbnail: UploadFile
    ) -> str:
        """Validate and upload course cover image to S3."""
        content_type = thumbnail.content_type or "application/octet-stream"
        if content_type not in ALLOWED_THUMBNAIL_TYPES:
            raise AppError(
                status_code=400,
                code="INVALID_THUMBNAIL_TYPE",
                message="Định dạng ảnh thumbnail không hợp lệ. Chỉ chấp nhận JPEG, PNG hoặc WebP.",
            )

        content = await thumbnail.read()
        if len(content) > MAX_THUMBNAIL_SIZE:
            raise AppError(
                status_code=400,
                code="FILE_TOO_LARGE",
                message="Kích thước ảnh thumbnail không được vượt quá 5MB.",
            )

        key = course_thumbnail_key(str(course_id), thumbnail.filename or "cover.jpg")
        return self.storage.upload_file(content, key, content_type)

    async def create(
        self,
        *,
        title: str,
        description: str | None,
        category_id: UUID,
        instructor_id: UUID | None,
        price: int,
        status: str,
        thumbnail: UploadFile | None,
        created_by: UUID | None,
    ) -> CourseCreateResponse:
        """Create course (§2.9)."""
        course_status = CourseStatus(status.lower())

        if course_status == CourseStatus.PUBLISHED:
            # Cannot publish a newly created course without instructor, chapter, and lesson
            if not instructor_id:
                raise AppError(
                    status_code=409,
                    code="COURSE_NOT_READY_TO_PUBLISH",
                    message="Khóa học phải có giảng viên trước khi xuất bản.",
                )
            raise AppError(
                status_code=409,
                code="COURSE_NOT_READY_TO_PUBLISH",
                message="Khóa học phải có ít nhất một chương và một bài học trước khi xuất bản.",
            )

        course_id = uuid4()
        thumbnail_url: str | None = None
        if thumbnail and thumbnail.filename:
            thumbnail_url = await self._handle_thumbnail_upload(course_id, thumbnail)

        course = await self.repo.create(
            title=title,
            description=description,
            category_id=category_id,
            instructor_id=instructor_id,
            price=price,
            status=course_status,
            thumbnail_url=thumbnail_url,
            created_by=created_by,
        )
        await self.db.commit()
        await self.db.refresh(course)

        return CourseCreateResponse(
            id=course.id,
            title=course.title,
            status=course.status.value if hasattr(course.status, "value") else str(course.status),
            created_at=course.created_at,
        )

    async def update(
        self,
        course_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        category_id: UUID | None = None,
        instructor_id: UUID | None = None,
        price: int | None = None,
        status: str | None = None,
        thumbnail: UploadFile | None = None,
        current_user: User | None = None,
    ) -> CourseDetail:
        """Update existing course (§2.10)."""
        course = await self.repo.get_by_id(course_id)
        if not course:
            raise AppError(
                status_code=404,
                code="COURSE_NOT_FOUND",
                message="Không tìm thấy khóa học yêu cầu.",
            )

        # Check target status
        target_status = CourseStatus(status.lower()) if status else course.status
        effective_instructor_id = instructor_id if instructor_id is not None else course.instructor_id

        if target_status == CourseStatus.PUBLISHED and course.status != CourseStatus.PUBLISHED:
            # Validate publish readiness
            if not effective_instructor_id:
                raise AppError(
                    status_code=409,
                    code="COURSE_NOT_READY_TO_PUBLISH",
                    message="Khóa học phải có giảng viên trước khi xuất bản.",
                )
            chap_count, less_count = await self.repo.count_chapters_and_lessons(course_id)
            if chap_count < 1 or less_count < 1:
                raise AppError(
                    status_code=409,
                    code="COURSE_NOT_READY_TO_PUBLISH",
                    message="Khóa học phải có ít nhất một chương và một bài học trước khi xuất bản.",
                )

        if title is not None:
            course.title = title.strip()
        if description is not None:
            course.description = description.strip() if description else None
        if category_id is not None:
            course.category_id = category_id
        if instructor_id is not None:
            course.instructor_id = instructor_id
        if price is not None:
            course.price = price
        if status is not None:
            course.status = target_status

        if thumbnail and thumbnail.filename:
            thumbnail_url = await self._handle_thumbnail_upload(course_id, thumbnail)
            course.thumbnail_url = thumbnail_url

        await self.db.commit()
        await self.db.refresh(course)

        return await self.get_detail(course_id, current_user=current_user)

    async def delete(self, course_id: UUID) -> CourseDeleteResponse:
        """Soft delete course (§2.11)."""
        course = await self.repo.get_by_id(course_id)
        if not course:
            raise AppError(
                status_code=404,
                code="COURSE_NOT_FOUND",
                message="Không tìm thấy khóa học yêu cầu.",
            )

        # Check enrollments
        enrollment_count = await self.repo.count_enrollments(course_id)
        if enrollment_count > 0:
            raise AppError(
                status_code=409,
                code="COURSE_HAS_ENROLLMENTS",
                message="Không thể xóa khóa học đã có học viên đăng ký.",
            )

        await self.repo.soft_delete(course)
        await self.db.commit()

        return CourseDeleteResponse(
            message="Đã xóa khóa học thành công.",
            course_id=course_id,
        )
