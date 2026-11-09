"""Videos request and response schemas (Contract 08 §9)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── 9.1a Upload Init ──────────────────────────────────────────────────────────


class VideoUploadInitRequest(BaseModel):
    lesson_id: UUID = Field(..., description="FK bài giảng cần gắn video")
    file_name: str = Field(
        ..., min_length=1, max_length=255, description="Tên file gốc (VD: 'bai_01_intro.mp4')"
    )
    file_size: int = Field(..., gt=0, description="Kích thước toàn bộ file (bytes), max 5GB")
    content_type: str = Field(
        ..., min_length=3, max_length=100, description="MIME type (VD: 'video/mp4')"
    )


class VideoUploadInitResponse(BaseModel):
    video_id: UUID = Field(..., description="PK video (trạng thái uploading)")
    upload_id: str = Field(..., description="Amazon S3 Multipart Upload ID")
    part_size: int = Field(
        ..., description="Kích thước mỗi phần (bytes, mặc định 52.428.800 = 50MB)"
    )
    total_parts: int = Field(..., description="Tổng số phần cần chia và tải lên")
    parts_uploaded: list[int] = Field(
        default_factory=list, description="Danh sách part number đã tải thành công"
    )


# ── 9.1b Presigned Part URL ───────────────────────────────────────────────────


class VideoUploadPartRequest(BaseModel):
    video_id: UUID = Field(..., description="PK video")
    upload_id: str = Field(..., min_length=1, description="Multipart Upload ID từ 9.1a")
    part_number: int = Field(
        ..., ge=1, le=10000, description="Số thứ tự phần (từ 1 đến total_parts)"
    )


class VideoUploadPartResponse(BaseModel):
    presigned_url: str = Field(
        ..., description="URL ký trước của Amazon S3 để FE gửi HTTP PUT trực tiếp"
    )
    expires_at: str = Field(..., description="Thời điểm hết hạn của presigned URL (ISO 8601)")


# ── 9.1c Upload Complete ──────────────────────────────────────────────────────


class UploadPartItem(BaseModel):
    part_number: int = Field(..., ge=1, description="Số thứ tự phần (1 .. total_parts)")
    etag: str = Field(
        ..., min_length=1, description="Giá trị ETag nhận được từ header response của Amazon S3"
    )


class VideoUploadCompleteRequest(BaseModel):
    video_id: UUID = Field(..., description="PK video")
    upload_id: str = Field(..., min_length=1, description="Multipart Upload ID")
    parts: list[UploadPartItem] = Field(
        ..., min_length=1, description="Danh sách các phần đã tải lên"
    )


class VideoUploadCompleteResponse(BaseModel):
    video_id: UUID = Field(..., description="PK video")
    overall_status: str = Field(..., description="Trạng thái chuyển sang 'uploaded'")
    message: str = Field(..., description="Thông điệp phản hồi")


# ── 9.5 Pipeline Cancel ───────────────────────────────────────────────────────


class CancelPipelineResponse(BaseModel):
    message: str = Field(..., description="Thông điệp kết quả hủy")
    overall_status: str = Field(..., description="Trạng thái tổng thể sau khi hủy")


# ── 9.2 Pipeline Step & Status ────────────────────────────────────────────────


class PipelineStepDetail(BaseModel):
    step: str = Field(..., description="Tên bước: upload, transcode, transcribe, index")
    status: str = Field(..., description="Trạng thái bước: pending, processing, completed, failed")
    progress: float | None = Field(None, description="% hoàn thành (0.0-100.0)")
    error_message: str | None = Field(None, description="Chi tiết lỗi nếu có")
    started_at: datetime | None = Field(None, description="Thời điểm bắt đầu")
    completed_at: datetime | None = Field(None, description="Thời điểm hoàn tất")


class VideoPipelineStatusResponse(BaseModel):
    video_id: UUID = Field(..., description="PK video")
    lesson_id: UUID = Field(..., description="FK bài giảng")
    lesson_title: str = Field(..., description="Tên bài giảng")
    steps: list[PipelineStepDetail] = Field(
        default_factory=list, description="Chi tiết 4 bước pipeline"
    )
    overall_status: str = Field(
        ..., description="uploading, uploaded, processing, completed, failed"
    )
    error_message: str | None = Field(None, description="Chi tiết lỗi nếu failed")
    started_at: datetime | None = Field(None, description="Thời điểm bắt đầu")
    completed_at: datetime | None = Field(None, description="Thời điểm hoàn tất")
