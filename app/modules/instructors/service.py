"""Instructor business logic layer."""

from __future__ import annotations

from math import ceil
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.storage import S3StorageAdapter, instructor_avatar_key
from app.core.config import settings
from app.core.errors import AppError
from app.modules.instructors.repository import InstructorRepository
from app.modules.instructors.schemas import (
    AdminInstructorDetail,
    AdminInstructorItem,
    AdminInstructorListResponse,
    InstructorAssignedCourse,
    InstructorCreate,
    InstructorDeleteResponse,
    InstructorOption,
    InstructorUpdate,
)

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


class InstructorService:
    """Service handling instructor management logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InstructorRepository(db)
        self.storage = S3StorageAdapter(settings)

    # ── Public / Shared ───────────────────────────────────────────────────────

    async def list_options(self) -> list[InstructorOption]:
        """Fetch active instructors for dropdowns (§2.14f)."""
        instructors = await self.repo.list_options()
        return [
            InstructorOption(
                id=inst.id,
                name=inst.name,
                title=inst.title,
                avatar_url=inst.avatar_url,
            )
            for inst in instructors
        ]

    # ── Admin ─────────────────────────────────────────────────────────────────

    async def list_admin(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        status_filter: str = "all",
        search: str | None = None,
    ) -> AdminInstructorListResponse:
        """Fetch paginated instructors for admin portal (§2.14a)."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10

        rows, total = await self.repo.list_admin(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            search=search,
        )

        items = [
            AdminInstructorItem(
                id=inst.id,
                name=inst.name,
                title=inst.title,
                email=inst.email,
                phone=inst.phone,
                avatar_url=inst.avatar_url,
                courses_count=courses_count,
                is_active=inst.is_active,
                created_at=inst.created_at,
            )
            for inst, courses_count in rows
        ]

        total_pages = ceil(total / page_size) if total > 0 else 0

        return AdminInstructorListResponse(
            data=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_detail(self, instructor_id: UUID) -> AdminInstructorDetail:
        """Fetch full instructor details with assigned courses (§2.14b)."""
        instructor = await self.repo.get_by_id(instructor_id)
        if not instructor:
            raise AppError(
                status_code=404,
                code="INSTRUCTOR_NOT_FOUND",
                message="Không tìm thấy giảng viên yêu cầu.",
            )

        assigned_rows = await self.repo.get_assigned_courses(instructor_id)
        assigned_courses = [
            InstructorAssignedCourse(
                id=course.id,
                title=course.title,
                thumbnail_url=course.thumbnail_url,
                status=course.status.value if hasattr(course.status, "value") else str(course.status),
                enrolled_count=enrolled_count,
            )
            for course, enrolled_count in assigned_rows
        ]

        return AdminInstructorDetail(
            id=instructor.id,
            name=instructor.name,
            title=instructor.title,
            bio=instructor.bio,
            avatar_url=instructor.avatar_url,
            email=instructor.email,
            phone=instructor.phone,
            is_active=instructor.is_active,
            courses=assigned_courses,
            created_at=instructor.created_at,
            updated_at=instructor.updated_at,
        )

    async def _handle_avatar_upload(
        self, instructor_id: UUID, avatar_file: UploadFile
    ) -> str:
        """Validate and upload instructor avatar to S3."""
        content_type = avatar_file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_AVATAR_TYPES:
            raise AppError(
                status_code=400,
                code="INVALID_AVATAR_TYPE",
                message="Định dạng ảnh không hợp lệ. Chỉ chấp nhận JPEG, PNG hoặc WebP.",
            )

        content = await avatar_file.read()
        if len(content) > MAX_AVATAR_SIZE:
            raise AppError(
                status_code=400,
                code="FILE_TOO_LARGE",
                message="Kích thước ảnh đại diện không được vượt quá 5MB.",
            )

        key = instructor_avatar_key(str(instructor_id), avatar_file.filename or "avatar.jpg")
        return self.storage.upload_file(content, key, content_type)

    async def create(
        self,
        payload: InstructorCreate,
        avatar_file: UploadFile | None = None,
    ) -> AdminInstructorDetail:
        """Create a new instructor with optional avatar (§2.14c)."""
        instructor_id = uuid4()
        avatar_url: str | None = None

        if avatar_file and avatar_file.filename:
            avatar_url = await self._handle_avatar_upload(instructor_id, avatar_file)

        instructor = await self.repo.create(
            name=payload.name,
            title=payload.title,
            bio=payload.bio,
            email=payload.email,
            phone=payload.phone,
            is_active=payload.is_active,
            avatar_url=avatar_url,
        )
        await self.db.commit()
        await self.db.refresh(instructor)

        return AdminInstructorDetail(
            id=instructor.id,
            name=instructor.name,
            title=instructor.title,
            bio=instructor.bio,
            avatar_url=instructor.avatar_url,
            email=instructor.email,
            phone=instructor.phone,
            is_active=instructor.is_active,
            courses=[],
            created_at=instructor.created_at,
            updated_at=instructor.updated_at,
        )

    async def update(
        self,
        instructor_id: UUID,
        payload: InstructorUpdate,
        avatar_file: UploadFile | None = None,
    ) -> AdminInstructorDetail:
        """Update existing instructor details (§2.14d)."""
        instructor = await self.repo.get_by_id(instructor_id)
        if not instructor:
            raise AppError(
                status_code=404,
                code="INSTRUCTOR_NOT_FOUND",
                message="Không tìm thấy giảng viên yêu cầu.",
            )

        if payload.name is not None:
            instructor.name = payload.name.strip()
        if payload.title is not None:
            instructor.title = payload.title.strip()
        if payload.bio is not None:
            instructor.bio = payload.bio.strip() if payload.bio else None
        if payload.email is not None:
            instructor.email = payload.email.strip().lower() if payload.email else None
        if payload.phone is not None:
            instructor.phone = payload.phone.strip() if payload.phone else None
        if payload.is_active is not None:
            instructor.is_active = payload.is_active

        if avatar_file and avatar_file.filename:
            avatar_url = await self._handle_avatar_upload(instructor_id, avatar_file)
            instructor.avatar_url = avatar_url

        await self.db.commit()
        await self.db.refresh(instructor)

        return await self.get_detail(instructor_id)

    async def delete(self, instructor_id: UUID) -> InstructorDeleteResponse:
        """Delete or deactivate instructor (§2.14e)."""
        instructor = await self.repo.get_by_id(instructor_id)
        if not instructor:
            raise AppError(
                status_code=404,
                code="INSTRUCTOR_NOT_FOUND",
                message="Không tìm thấy giảng viên yêu cầu.",
            )

        # Check published courses
        published_count = await self.repo.count_published_courses(instructor_id)
        if published_count > 0:
            raise AppError(
                status_code=400,
                code="INSTRUCTOR_HAS_ACTIVE_COURSES",
                message="Không thể xóa giảng viên đang có khóa học xuất bản.",
            )

        # Check any courses
        total_courses = await self.repo.count_courses(instructor_id)
        if total_courses > 0:
            await self.repo.deactivate(instructor)
            await self.db.commit()
            return InstructorDeleteResponse(
                message="Giảng viên đang có khóa học liên kết. Đã chuyển trạng thái sang tạm ngưng (suspended).",
                instructor_id=instructor_id,
                deleted=False,
            )

        await self.repo.soft_delete(instructor)
        await self.db.commit()
        return InstructorDeleteResponse(
            message="Đã xóa giảng viên thành công.",
            instructor_id=instructor_id,
            deleted=True,
        )
