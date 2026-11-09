"""Videos business services (Contract 08 §9, Spec 11 §3.3.1)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import PurePath
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.storage import (
    S3StorageAdapter,
    StorageConnectionError,
    video_raw_key,
)
from app.core.config import settings
from app.core.errors import AppError
from app.db.models.schema import VideoOverallStatus
from app.modules.videos.repository import VideoRepository
from app.modules.videos.schemas import (
    CancelPipelineResponse,
    VideoUploadCompleteRequest,
    VideoUploadCompleteResponse,
    VideoUploadInitRequest,
    VideoUploadInitResponse,
    VideoUploadPartRequest,
    VideoUploadPartResponse,
)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_MIME_PREFIX = "video/"


class VideoService:
    """Service orchestrating S3 direct multipart upload and video records."""

    def __init__(
        self,
        db: AsyncSession,
        storage: S3StorageAdapter | None = None,
    ) -> None:
        self.db = db
        self.repo = VideoRepository(db)
        self.storage = storage or S3StorageAdapter(settings)

    def _validate_video_format(self, filename: str, content_type: str) -> None:
        """Ensure file has a supported video extension and MIME type."""
        ext = PurePath(filename).suffix.lower()
        content_type_lower = content_type.strip().lower()

        is_valid_ext = ext in ALLOWED_EXTENSIONS
        is_valid_mime = content_type_lower.startswith(ALLOWED_MIME_PREFIX)

        if not is_valid_ext and not is_valid_mime:
            raise AppError(
                status_code=400,
                code="INVALID_FILE_FORMAT",
                message="Định dạng video không được hỗ trợ. Chỉ chấp nhận MP4, MOV, AVI, MKV, WEBM.",
            )

    async def init_upload(self, data: VideoUploadInitRequest) -> VideoUploadInitResponse:
        """Initialize or resume an S3 multipart upload session (Contract 08 §9.1a)."""
        # 1. Validate file size (max 5GB)
        if data.file_size > settings.upload_max_total_bytes:
            raise AppError(
                status_code=413,
                code="FILE_TOO_LARGE",
                message="Dung lượng video vượt quá giới hạn cho phép (tối đa 5GB).",
            )

        # 2. Validate video format
        self._validate_video_format(data.file_name, data.content_type)

        # 3. Verify lesson existence
        lesson = await self.repo.get_lesson(data.lesson_id)
        if not lesson:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message="Không tìm thấy bài giảng.",
            )

        part_size = settings.upload_recommended_part_bytes
        total_parts = max(1, math.ceil(data.file_size / part_size))

        # 4. Check for existing video record for resume capability
        existing_video = await self.repo.get_video_by_lesson_id(data.lesson_id)
        if (
            existing_video is not None
            and existing_video.overall_status == VideoOverallStatus.UPLOADING
        ):
            try:
                active = self.storage.find_active_multipart_upload(
                    f"videos/{existing_video.id}/raw/"
                )
            except StorageConnectionError as exc:
                raise AppError(
                    status_code=502,
                    code="STORAGE_ERROR",
                    message=f"Lỗi khi kiểm tra phiên lưu trữ S3: {exc}",
                ) from exc

            if active is not None:
                key, upload_id = active
                try:
                    parts_uploaded = self.storage.list_parts(key=key, upload_id=upload_id)
                except StorageConnectionError as exc:
                    raise AppError(
                        status_code=502,
                        code="STORAGE_ERROR",
                        message=f"Lỗi khi đọc danh sách phần đã tải: {exc}",
                    ) from exc

                return VideoUploadInitResponse(
                    video_id=existing_video.id,
                    upload_id=upload_id,
                    part_size=part_size,
                    total_parts=total_parts,
                    parts_uploaded=parts_uploaded,
                )

        # 5. New upload session
        video_id = existing_video.id if existing_video is not None else uuid4()
        key = video_raw_key(str(video_id), data.file_name)

        try:
            upload_id = self.storage.create_multipart_upload(
                key=key, content_type=data.content_type
            )
        except StorageConnectionError as exc:
            raise AppError(
                status_code=502,
                code="STORAGE_ERROR",
                message=f"Không thể khởi tạo phiên tải lên S3: {exc}",
            ) from exc

        video = await self.repo.create_or_update_video_for_upload(
            lesson_id=data.lesson_id,
            file_name=data.file_name,
            file_size=data.file_size,
            content_type=data.content_type,
            reuse_video_id=video_id,
        )
        await self.db.commit()

        return VideoUploadInitResponse(
            video_id=video.id,
            upload_id=upload_id,
            part_size=part_size,
            total_parts=total_parts,
            parts_uploaded=[],
        )

    async def get_presigned_part_url(self, data: VideoUploadPartRequest) -> VideoUploadPartResponse:
        """Generate presigned PUT URL for a specific part (Contract 08 §9.1b)."""
        video = await self.repo.get_video_by_id(data.video_id)
        if not video:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message="Không tìm thấy video.",
            )

        if video.overall_status != VideoOverallStatus.UPLOADING:
            raise AppError(
                status_code=400,
                code="INVALID_STATUS",
                message="Video không ở trạng thái tải lên.",
            )

        part_size = settings.upload_recommended_part_bytes
        total_parts = max(1, math.ceil(video.file_size_bytes / part_size))
        if data.part_number < 1 or data.part_number > total_parts:
            raise AppError(
                status_code=400,
                code="INVALID_PART_NUMBER",
                message=f"Số thứ tự phần không hợp lệ. Phải nằm trong khoảng 1 đến {total_parts}.",
            )

        key = video_raw_key(str(video.id), video.original_filename)
        expires_in = settings.upload_presigned_url_expire_seconds

        try:
            presigned_url = self.storage.generate_presigned_part_url(
                key=key,
                upload_id=data.upload_id,
                part_number=data.part_number,
                expires_in=expires_in,
            )
        except StorageConnectionError as exc:
            raise AppError(
                status_code=502,
                code="STORAGE_ERROR",
                message=f"Không thể cấp presigned URL cho part {data.part_number}: {exc}",
            ) from exc

        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

        return VideoUploadPartResponse(
            presigned_url=presigned_url,
            expires_at=expires_at,
        )

    async def complete_upload(
        self, data: VideoUploadCompleteRequest
    ) -> VideoUploadCompleteResponse:
        """Complete multipart upload, finalize raw_storage_url, and trigger pipeline (Contract 08 §9.1c)."""
        video = await self.repo.get_video_by_id(data.video_id)
        if not video:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message="Không tìm thấy video.",
            )

        if video.overall_status != VideoOverallStatus.UPLOADING:
            raise AppError(
                status_code=400,
                code="INVALID_STATUS",
                message="Video không ở trạng thái tải lên.",
            )

        part_size = settings.upload_recommended_part_bytes
        total_parts = max(1, math.ceil(video.file_size_bytes / part_size))

        received_parts = {item.part_number for item in data.parts}
        required_parts = set(range(1, total_parts + 1))
        if not required_parts.issubset(received_parts):
            missing = sorted(required_parts - received_parts)
            raise AppError(
                status_code=400,
                code="MISSING_PARTS",
                message=f"Chưa tải lên đầy đủ các phần của video. Các phần còn thiếu: {missing}",
            )

        key = video_raw_key(str(video.id), video.original_filename)
        parts_payload = [{"PartNumber": p.part_number, "ETag": p.etag} for p in data.parts]

        try:
            raw_storage_url = self.storage.complete_multipart_upload(
                key=key,
                upload_id=data.upload_id,
                parts=parts_payload,
            )
        except StorageConnectionError as exc:
            raise AppError(
                status_code=502,
                code="STORAGE_ERROR",
                message=f"Không thể hoàn tất ghép tệp trên S3: {exc}",
            ) from exc

        await self.repo.mark_upload_completed(video=video, raw_storage_url=raw_storage_url)
        await self.db.commit()

        return VideoUploadCompleteResponse(
            video_id=video.id,
            overall_status="uploaded",
            message="Tải lên video hoàn tất, đã đưa vào pipeline xử lý.",
        )

    async def cancel_pipeline(self, video_id: UUID) -> CancelPipelineResponse:
        """Cancel upload or active pipeline processing (Contract 08 §9.5)."""
        video = await self.repo.get_video_by_id(video_id)
        if not video:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message="Không tìm thấy video.",
            )

        # If currently uploading, abort in-progress multipart session on S3
        if video.overall_status == VideoOverallStatus.UPLOADING:
            try:
                active = self.storage.find_active_multipart_upload(f"videos/{video.id}/raw/")
                if active is not None:
                    key, upload_id = active
                    self.storage.abort_multipart_upload(key=key, upload_id=upload_id)
            except StorageConnectionError:
                pass  # Ignore cleanup errors when aborting

        await self.repo.mark_upload_cancelled(video=video)
        await self.db.commit()

        return CancelPipelineResponse(
            message="Đã hủy xử lý.",
            overall_status="uploaded",
        )
