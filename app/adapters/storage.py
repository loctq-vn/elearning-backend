"""Amazon S3 storage adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, settings


class StorageConnectionError(RuntimeError):
    """Raised when the configured object storage cannot be reached or used."""


class StorageKeyError(ValueError):
    """Raised when a storage key component is unsafe or invalid."""


def _safe_filename(filename: str) -> str:
    """Return a single safe filename component for an object key."""
    path_parts = filename.replace("\\", "/").split("/")
    if ".." in path_parts:
        raise StorageKeyError("filename must not contain parent-directory components")
    normalized = path_parts[-1].strip()
    if not normalized or normalized in {".", ".."}:
        raise StorageKeyError("filename must contain a non-empty file name")
    if any(ord(character) < 32 for character in normalized):
        raise StorageKeyError("filename must not contain control characters")
    return normalized


def video_raw_key(video_id: str, filename: str) -> str:
    """Build the key for an uploaded source video."""
    return f"videos/{video_id}/raw/{_safe_filename(filename)}"


def video_hls_prefix(video_id: str) -> str:
    """Build the prefix containing all HLS playlists and segments."""
    return f"hls/{video_id}"


def video_hls_master_key(video_id: str) -> str:
    """Build the key for the master HLS playlist."""
    return f"{video_hls_prefix(video_id)}/master.m3u8"


def video_thumbnail_key(video_id: str, filename: str) -> str:
    """Build the key for a video's thumbnail."""
    return f"thumbnails/videos/{video_id}/{_safe_filename(filename)}"


def course_thumbnail_key(course_id: str, filename: str) -> str:
    """Build the key for a course's cover thumbnail."""
    return f"thumbnails/courses/{course_id}/{_safe_filename(filename)}"


def instructor_avatar_key(instructor_id: str, filename: str) -> str:
    """Build the key for an instructor's avatar (distinct from user avatars)."""
    return f"avatars/instructors/{instructor_id}/{_safe_filename(filename)}"


def user_avatar_key(user_id: str, filename: str) -> str:
    """Build the key for a user's avatar."""
    return f"avatars/{user_id}/{_safe_filename(filename)}"


@dataclass(slots=True)
class S3StorageAdapter:
    """Small boundary around the S3 operations used by the application."""

    config: Settings

    def public_url(self, key: str) -> str:
        """Build the public/CDN URL for an object key."""
        base_url = (
            self.config.cloudfront_domain.strip()
            or self.config.s3_public_base_url.strip()
        )
        if not base_url:
            raise StorageConnectionError(
                "CLOUDFRONT_DOMAIN or S3_PUBLIC_BASE_URL must be configured"
            )
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        return f"{base_url.rstrip('/')}/{key.lstrip('/')}"

    def upload_file(self, file_bytes: bytes, key: str, content_type: str) -> str:
        """Upload raw bytes to S3 and return the public URL."""
        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        try:
            self._client().put_object(
                Bucket=bucket,
                Key=key,
                Body=file_bytes,
                ContentType=content_type,
            )
            return self.public_url(key)
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to upload file to S3 '{key}'{detail}"
            ) from exc

    def _client(self) -> Any:
        client_options: dict[str, str] = {"region_name": self.config.aws_region}
        if self.config.storage_endpoint_url:
            client_options["endpoint_url"] = self.config.storage_endpoint_url
        if self.config.storage_access_key and self.config.storage_secret_key:
            client_options["aws_access_key_id"] = self.config.storage_access_key
            client_options["aws_secret_access_key"] = self.config.storage_secret_key
        return boto3.client("s3", **client_options)

    def check_connection(self) -> None:
        """Verify credentials and access to the configured bucket."""
        if not self.config.s3_bucket_name.strip():
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        try:
            self._client().head_bucket(Bucket=self.config.s3_bucket_name.strip())
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to access S3 bucket '{self.config.s3_bucket_name.strip()}'{detail}"
            ) from exc

    def check_object_lifecycle(self) -> str:
        """Upload, inspect, read, and delete a temporary object."""
        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        key = f"healthchecks/{uuid4().hex}.txt"
        body = b"elearning-backend-s3-healthcheck"
        client = self._client()

        try:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType="text/plain",
            )
            metadata = client.head_object(Bucket=bucket, Key=key)
            if metadata.get("ContentLength") != len(body):
                raise StorageConnectionError(
                    f"S3 object check failed for '{key}': unexpected object size"
                )

            response = client.get_object(Bucket=bucket, Key=key)
            downloaded = response["Body"].read()
            if downloaded != body:
                raise StorageConnectionError(
                    f"S3 object check failed for '{key}': downloaded content differs"
                )
            return key
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to complete S3 object check for '{key}'{detail}"
            ) from exc
        finally:
            try:
                client.delete_object(Bucket=bucket, Key=key)
            except (BotoCoreError, ClientError) as exc:
                raise StorageConnectionError(
                    f"Unable to clean up S3 healthcheck object '{key}'"
                ) from exc


def check_s3_connection(config: Settings = settings) -> None:
    """Check the configured S3 bucket without exposing credentials."""
    S3StorageAdapter(config).check_connection()


if __name__ == "__main__":
    try:
        check_s3_connection()
        checked_key = S3StorageAdapter(settings).check_object_lifecycle()
    except StorageConnectionError as exc:
        print(f"S3 connection failed: {exc}")
        raise SystemExit(1) from exc
    print(
        "S3 connection and object lifecycle OK: "
        f"bucket '{settings.s3_bucket_name.strip()}', object '{checked_key}' deleted"
    )
