"""Amazon S3 storage adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import boto3
from botocore.client import Config
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
        base_url = self.config.cloudfront_domain.strip() or self.config.s3_public_base_url.strip()
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
            raise StorageConnectionError(f"Unable to upload file to S3 '{key}'{detail}") from exc

    def create_multipart_upload(self, key: str, content_type: str) -> str:
        """Initiate an S3 multipart upload and return the upload ID."""
        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        try:
            response = self._client().create_multipart_upload(
                Bucket=bucket,
                Key=key,
                ContentType=content_type,
            )
            return str(response["UploadId"])
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to create multipart upload for '{key}'{detail}"
            ) from exc

    def generate_presigned_part_url(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned URL for uploading a specific part."""
        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        try:
            return str(
                self._client().generate_presigned_url(
                    ClientMethod="upload_part",
                    Params={
                        "Bucket": bucket,
                        "Key": key,
                        "UploadId": upload_id,
                        "PartNumber": part_number,
                    },
                    ExpiresIn=expires_in,
                )
            )
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to generate presigned part URL for '{key}' part {part_number}{detail}"
            ) from exc

    def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> str:
        """Complete an S3 multipart upload and return the public URL."""
        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        sorted_parts = sorted(parts, key=lambda p: int(p["PartNumber"]))
        try:
            self._client().complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": sorted_parts},
            )
            return self.public_url(key)
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to complete multipart upload for '{key}'{detail}"
            ) from exc

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        """Abort an in-progress multipart upload and clean up stored parts."""
        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        try:
            self._client().abort_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
            )
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to abort multipart upload for '{key}'{detail}"
            ) from exc

    def list_parts(self, key: str, upload_id: str) -> list[int]:
        """List numbers of parts already uploaded for this multipart upload."""
        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        try:
            response = self._client().list_parts(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
            )
            return [int(part["PartNumber"]) for part in response.get("Parts", [])]
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(f"Unable to list parts for '{key}'{detail}") from exc

    def find_active_multipart_upload(self, key_prefix: str) -> tuple[str, str] | None:
        """Find an active in-progress multipart upload matching key_prefix (key, upload_id)."""
        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        try:
            response = self._client().list_multipart_uploads(
                Bucket=bucket,
                Prefix=key_prefix,
            )
            uploads = response.get("Uploads", [])
            if uploads:
                return str(uploads[0]["Key"]), str(uploads[0]["UploadId"])
            return None
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to check active multipart uploads for prefix '{key_prefix}'{detail}"
            ) from exc

    def download_file(self, key: str, destination_path: str | Any) -> None:
        """Download an S3 object directly to a local file path."""
        from pathlib import Path

        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._client().download_file(bucket, key, str(dest))
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(f"Unable to download S3 object '{key}'{detail}") from exc

    def upload_local_file(
        self,
        local_path: str | Any,
        key: str,
        content_type: str | None = None,
    ) -> str:
        """Upload a local file to S3 and return its public URL."""
        import mimetypes
        from pathlib import Path

        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        path = Path(local_path)
        if not path.is_file():
            raise StorageConnectionError(f"Local file does not exist: '{local_path}'")

        if content_type is None:
            if path.suffix.lower() == ".m3u8":
                content_type = "application/vnd.apple.mpegurl"
            elif path.suffix.lower() == ".ts":
                content_type = "video/mp2t"
            else:
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

        try:
            self._client().upload_file(
                str(path),
                bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            return self.public_url(key)
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to upload local file '{local_path}' to '{key}'{detail}"
            ) from exc

    def upload_directory(
        self,
        local_dir: str | Any,
        s3_prefix: str,
    ) -> list[str]:
        """Upload all files from a local directory to an S3 prefix."""
        from pathlib import Path

        dir_path = Path(local_dir)
        if not dir_path.is_dir():
            raise StorageConnectionError(f"Local directory does not exist: '{local_dir}'")

        uploaded_keys: list[str] = []
        normalized_prefix = s3_prefix.strip().strip("/")

        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            relative_path = file_path.relative_to(dir_path).as_posix()
            s3_key = f"{normalized_prefix}/{relative_path}"
            self.upload_local_file(file_path, s3_key)
            uploaded_keys.append(s3_key)

        return uploaded_keys

    def delete_prefix(self, s3_prefix: str) -> int:
        """Delete all objects matching s3_prefix. Returns count of deleted objects."""
        bucket = self.config.s3_bucket_name.strip()
        if not bucket:
            raise StorageConnectionError("S3_BUCKET_NAME must not be empty")

        normalized_prefix = s3_prefix.strip().strip("/")
        client = self._client()
        deleted_count = 0

        try:
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=normalized_prefix):
                contents = page.get("Contents", [])
                if not contents:
                    continue
                delete_items = [{"Key": obj["Key"]} for obj in contents]
                client.delete_objects(
                    Bucket=bucket,
                    Delete={"Objects": delete_items},
                )
                deleted_count += len(delete_items)
            return deleted_count
        except (BotoCoreError, ClientError) as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            detail = f" ({error_code})" if error_code else ""
            raise StorageConnectionError(
                f"Unable to delete objects for prefix '{s3_prefix}'{detail}"
            ) from exc

    def _client(self) -> Any:
        client_options: dict[str, Any] = {
            "region_name": self.config.aws_region,
            "config": Config(signature_version="s3v4"),
        }
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
