"""Video upload & pipeline management endpoints (Contract 08 §9)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import get_current_user
from app.db.models.schema import User, UserRole
from app.db.session import get_db_session
from app.modules.videos.schemas import (
    CancelPipelineResponse,
    VideoUploadCompleteRequest,
    VideoUploadCompleteResponse,
    VideoUploadInitRequest,
    VideoUploadInitResponse,
    VideoUploadPartRequest,
    VideoUploadPartResponse,
)
from app.modules.videos.service import VideoService

router = APIRouter(tags=["videos"])


def _require_admin(current_user: User) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Chỉ quản trị viên mới có quyền thực hiện.",
        )
    return current_user


# ── 9.1a Upload Init ──────────────────────────────────────────────────────────


@router.post(
    "/admin/videos/upload/init",
    response_model=VideoUploadInitResponse,
    status_code=status.HTTP_200_OK,
    summary="Khởi tạo phiên tải lên nhiều phần (Contract 08 §9.1a)",
)
async def init_video_upload(
    payload: VideoUploadInitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VideoUploadInitResponse:
    """Khởi tạo phiên multipart upload, tạo bản ghi video và 4 pipeline steps."""
    _require_admin(current_user)
    service = VideoService(db)
    return await service.init_upload(payload)


# ── 9.1b Presigned Part URL ───────────────────────────────────────────────────


@router.post(
    "/admin/videos/upload",
    response_model=VideoUploadPartResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy Presigned URL cho từng phần (Contract 08 §9.1b)",
)
async def get_presigned_part_url(
    payload: VideoUploadPartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VideoUploadPartResponse:
    """Cấp presigned URL có thời hạn ngắn để client tải trực tiếp part lên Amazon S3."""
    _require_admin(current_user)
    service = VideoService(db)
    return await service.get_presigned_part_url(payload)


# ── 9.1c Upload Complete ──────────────────────────────────────────────────────


@router.post(
    "/admin/videos/upload/complete",
    response_model=VideoUploadCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Hoàn tất tải lên & kích hoạt pipeline (Contract 08 §9.1c)",
)
async def complete_video_upload(
    payload: VideoUploadCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VideoUploadCompleteResponse:
    """Hoàn tất ghép tệp multipart trên S3, cập nhật raw_storage_url và kích hoạt pipeline."""
    _require_admin(current_user)
    service = VideoService(db)
    return await service.complete_upload(payload)


# ── 9.5 Pipeline Cancel ───────────────────────────────────────────────────────


@router.put(
    "/admin/pipeline/{video_id}/cancel",
    response_model=CancelPipelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy pipeline hoặc phiên tải lên (Contract 08 §9.5)",
)
async def cancel_pipeline(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CancelPipelineResponse:
    """Hủy phiên multipart S3 nếu đang tải lên và đưa trạng thái về uploaded."""
    _require_admin(current_user)
    service = VideoService(db)
    return await service.cancel_pipeline(video_id)
