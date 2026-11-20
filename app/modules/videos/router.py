"""Video upload & pipeline management endpoints (Contract 08 §9)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.schemas import PaginatedResponse
from app.core.security import get_current_user
from app.db.models.schema import User, UserRole
from app.db.session import get_db_session
from app.modules.videos.schemas import (
    CancelPipelineResponse,
    RetryPipelineResponse,
    VideoPipelineStatusResponse,
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


# ── 9.2 Pipeline Status ───────────────────────────────────────────────────────


@router.get(
    "/admin/pipeline/{video_id}/status",
    response_model=VideoPipelineStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy trạng thái pipeline xử lý video (Contract 08 §9.2)",
)
async def get_pipeline_status(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VideoPipelineStatusResponse:
    """Trả về trạng thái tổng thể và chi tiết 4 bước pipeline của video."""
    _require_admin(current_user)
    service = VideoService(db)
    return await service.get_pipeline_status(video_id)


# ── 9.3 Pipeline List ─────────────────────────────────────────────────────────


@router.get(
    "/admin/pipeline",
    response_model=PaginatedResponse[VideoPipelineStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Danh sách video & trạng thái pipeline (Contract 08 §9.3)",
)
async def list_pipelines(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Số lượng mục mỗi trang"),
    status: str | None = Query(default=None, description="Lọc theo overall_status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[VideoPipelineStatusResponse]:
    """Danh sách video kèm pipeline status có hỗ trợ phân trang và bộ lọc."""
    _require_admin(current_user)
    service = VideoService(db)
    return await service.list_pipelines(page=page, page_size=page_size, status_filter=status)


# ── 9.4 Pipeline Retry ────────────────────────────────────────────────────────


@router.post(
    "/admin/pipeline/{video_id}/retry",
    response_model=RetryPipelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Xử lý lại pipeline step (Contract 08 §9.4)",
)
async def retry_pipeline_step(
    video_id: UUID,
    step: str = Query(..., description="Tên bước: upload, transcode, transcribe (hoặc stt), index"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> RetryPipelineResponse:
    """Yêu cầu chạy lại 1 bước cụ thể của pipeline mà không mất dữ liệu các bước trước."""
    _require_admin(current_user)
    service = VideoService(db)
    return await service.retry_pipeline(video_id, step)


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
