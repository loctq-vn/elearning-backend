"""Notes endpoints — Doc 08 §7."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models.schema import User
from app.db.session import get_db_session
from app.modules.notes.schemas import (
    NoteCreateIn,
    NoteCreateOut,
    NoteDeleteResponse,
    NoteItemOut,
    NoteListResponse,
    NoteUpdateIn,
)
from app.modules.notes.service import NoteService

router = APIRouter(tags=["notes"])


@router.get(
    "/lessons/{lesson_id}/notes",
    response_model=NoteListResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem ghi chú của 1 bài giảng (§7.1)",
)
async def list_notes(
    lesson_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> NoteListResponse:
    """Lấy danh sách ghi chú của người dùng cho một bài giảng, sắp xếp theo timestamp tăng dần."""
    service = NoteService(db)
    return await service.list_notes(lesson_id, current_user)


@router.post(
    "/lessons/{lesson_id}/notes",
    response_model=NoteCreateOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo ghi chú tại mốc thời gian (§7.2)",
)
async def create_note(
    lesson_id: UUID,
    payload: NoteCreateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> NoteCreateOut:
    """Tạo ghi chú mới tại mốc thời gian video hiện tại."""
    service = NoteService(db)
    return await service.create_note(lesson_id, payload, current_user)


@router.put(
    "/notes/{note_id}",
    response_model=NoteItemOut,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật nội dung ghi chú (§7.3)",
)
async def update_note(
    note_id: UUID,
    payload: NoteUpdateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> NoteItemOut:
    """Cập nhật nội dung của một ghi chú đã tạo."""
    service = NoteService(db)
    return await service.update_note(note_id, payload, current_user)


@router.delete(
    "/notes/{note_id}",
    response_model=NoteDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Xóa ghi chú (§7.4)",
)
async def delete_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> NoteDeleteResponse:
    """Xóa một ghi chú đã tạo."""
    service = NoteService(db)
    return await service.delete_note(note_id, current_user)
