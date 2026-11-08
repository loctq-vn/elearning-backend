"""Notes business logic layer (Doc 08 §7; BR-14)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.schema import User, UserRole
from app.modules.notes.repository import NoteRepository
from app.modules.notes.schemas import (
    NoteCreateIn,
    NoteCreateOut,
    NoteDeleteResponse,
    NoteItemOut,
    NoteListResponse,
    NoteUpdateIn,
)


class NoteService:
    """Service handling notes management and access control."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = NoteRepository(db)

    async def _check_lesson_access(self, lesson_id: UUID, current_user: User) -> None:
        """Verify lesson existence and user access rights (§2.7, §7.1)."""
        lesson = await self.repo.get_lesson(lesson_id)
        if not lesson:
            raise AppError(
                status_code=404,
                code="LESSON_NOT_FOUND",
                message="Bài học không tồn tại.",
            )

        is_admin = current_user.role == UserRole.ADMIN
        is_trial = lesson.is_trial_allowed
        is_enrolled = await self.repo.is_user_enrolled(lesson.course_id, current_user.id)

        if not (is_admin or is_trial or is_enrolled):
            raise AppError(
                status_code=403,
                code="NOT_ENROLLED",
                message="Vui lòng mua khóa học để truy cập.",
            )

    async def list_notes(self, lesson_id: UUID, current_user: User) -> NoteListResponse:
        """Fetch list of user's notes for a lesson sorted by timestamp ascending (§7.1)."""
        await self._check_lesson_access(lesson_id, current_user)
        notes = await self.repo.get_notes(lesson_id, current_user.id)
        return NoteListResponse(data=[NoteItemOut.model_validate(n) for n in notes])

    async def create_note(
        self, lesson_id: UUID, payload: NoteCreateIn, current_user: User
    ) -> NoteCreateOut:
        """Create a new note at a specific video timestamp (§7.2)."""
        await self._check_lesson_access(lesson_id, current_user)
        note = await self.repo.create_note(
            user_id=current_user.id,
            lesson_id=lesson_id,
            content=payload.content,
            timestamp=payload.timestamp,
        )
        return NoteCreateOut.model_validate(note)

    async def update_note(
        self, note_id: UUID, payload: NoteUpdateIn, current_user: User
    ) -> NoteItemOut:
        """Update content of an existing note (§7.3; BR-14)."""
        note = await self.repo.get_note_by_id(note_id)
        if not note:
            raise AppError(
                status_code=404,
                code="NOTE_NOT_FOUND",
                message="Ghi chú không tồn tại.",
            )

        # BR-14: Tính riêng tư của ghi chú cá nhân
        if note.user_id != current_user.id:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Bạn không có quyền chỉnh sửa ghi chú này.",
            )

        updated_note = await self.repo.update_note(note, payload.content)
        return NoteItemOut.model_validate(updated_note)

    async def delete_note(self, note_id: UUID, current_user: User) -> NoteDeleteResponse:
        """Delete an existing note (§7.4; BR-14)."""
        note = await self.repo.get_note_by_id(note_id)
        if not note:
            raise AppError(
                status_code=404,
                code="NOTE_NOT_FOUND",
                message="Ghi chú không tồn tại.",
            )

        # BR-14: Tính riêng tư của ghi chú cá nhân
        if note.user_id != current_user.id:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Bạn không có quyền xóa ghi chú này.",
            )

        await self.repo.delete_note(note)
        return NoteDeleteResponse(message="Đã xóa ghi chú.")
