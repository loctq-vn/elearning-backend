import os
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from app.adapters.storage import (
    S3StorageAdapter,
    StorageConnectionError,
    StorageKeyError,
    user_avatar_key,
    video_hls_master_key,
    video_hls_prefix,
    video_raw_key,
    video_thumbnail_key,
)
from app.core.config import Settings


def make_settings(**overrides: str) -> Settings:
    values = {
        "aws_region": "ap-southeast-1",
        "storage_endpoint_url": "https://s3.ap-southeast-1.amazonaws.com",
        "storage_access_key": "test-access-key",
        "storage_secret_key": "test-secret-key",
        "s3_bucket_name": "elearning-media",
    }
    values.update(overrides)
    return Settings(**values)


@patch("app.adapters.storage.boto3.client")
def test_check_connection_uses_configured_bucket(mock_client: Mock) -> None:
    client = mock_client.return_value

    S3StorageAdapter(make_settings()).check_connection()

    mock_client.assert_called_once_with(
        "s3",
        region_name="ap-southeast-1",
        endpoint_url="https://s3.ap-southeast-1.amazonaws.com",
        aws_access_key_id="test-access-key",
        aws_secret_access_key="test-secret-key",
    )
    client.head_bucket.assert_called_once_with(Bucket="elearning-media")


@patch("app.adapters.storage.boto3.client")
def test_check_connection_fails_with_actionable_error(mock_client: Mock) -> None:
    mock_client.return_value.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
        "HeadBucket",
    )

    with pytest.raises(StorageConnectionError, match="AccessDenied"):
        S3StorageAdapter(make_settings()).check_connection()


@patch("app.adapters.storage.uuid4", return_value=Mock(hex="healthcheck-id"))
@patch("app.adapters.storage.boto3.client")
def test_check_object_lifecycle_uploads_reads_and_deletes(
    mock_client: Mock,
    mock_uuid: Mock,
) -> None:
    del mock_uuid
    client = mock_client.return_value
    client.head_object.return_value = {"ContentLength": 32}
    client.get_object.return_value = {
        "Body": Mock(read=Mock(return_value=b"elearning-backend-s3-healthcheck"))
    }

    key = S3StorageAdapter(make_settings()).check_object_lifecycle()

    assert key == "healthchecks/healthcheck-id.txt"
    client.put_object.assert_called_once_with(
        Bucket="elearning-media",
        Key=key,
        Body=b"elearning-backend-s3-healthcheck",
        ContentType="text/plain",
    )
    client.head_object.assert_called_once_with(Bucket="elearning-media", Key=key)
    client.get_object.assert_called_once_with(Bucket="elearning-media", Key=key)
    client.delete_object.assert_called_once_with(Bucket="elearning-media", Key=key)


def test_check_connection_rejects_empty_bucket_name() -> None:
    with pytest.raises(StorageConnectionError, match="S3_BUCKET_NAME"):
        S3StorageAdapter(make_settings(s3_bucket_name="   ")).check_connection()


def test_storage_keys_use_the_canonical_prefixes() -> None:
    assert video_raw_key("video-123", "lecture.mp4") == (
        "videos/video-123/raw/lecture.mp4"
    )
    assert video_hls_prefix("video-123") == "hls/video-123"
    assert video_hls_master_key("video-123") == "hls/video-123/master.m3u8"
    assert video_thumbnail_key("video-123", "cover.webp") == (
        "thumbnails/videos/video-123/cover.webp"
    )
    assert user_avatar_key("user-123", "avatar.png") == "avatars/user-123/avatar.png"


@pytest.mark.parametrize("filename", ["", ".", "..", "../avatar.png", r"..\avatar.png"])
def test_storage_keys_reject_invalid_filenames(filename: str) -> None:
    with pytest.raises(StorageKeyError):
        user_avatar_key("user-123", filename)


def test_storage_keys_strip_nested_filename_paths() -> None:
    assert video_raw_key("video-123", r"uploads\lecture.mp4") == (
        "videos/video-123/raw/lecture.mp4"
    )


def test_public_url_prefers_cloudfront_domain() -> None:
    settings = make_settings(
        s3_public_base_url="https://bucket.s3.amazonaws.com",
        cloudfront_domain="https://cdn.example.com/",
    )

    assert S3StorageAdapter(settings).public_url(video_hls_master_key("video-123")) == (
        "https://cdn.example.com/hls/video-123/master.m3u8"
    )


def test_public_url_normalizes_scheme_when_missing() -> None:
    settings = make_settings(
        s3_public_base_url="",
        cloudfront_domain="d123456abcdef8.cloudfront.net",
    )
    assert S3StorageAdapter(settings).public_url("avatars/user-123/avatar.png") == (
        "https://d123456abcdef8.cloudfront.net/avatars/user-123/avatar.png"
    )


@patch("app.adapters.storage.boto3.client")
def test_upload_file_puts_object_and_returns_public_url(mock_client: Mock) -> None:
    client = mock_client.return_value
    settings = make_settings(
        cloudfront_domain="https://cdn.example.com",
    )
    adapter = S3StorageAdapter(settings)
    file_bytes = b"sample-bytes"
    key = "avatars/user-123/avatar.png"
    content_type = "image/png"

    url = adapter.upload_file(file_bytes=file_bytes, key=key, content_type=content_type)

    assert url == "https://cdn.example.com/avatars/user-123/avatar.png"
    client.put_object.assert_called_once_with(
        Bucket="elearning-media",
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )


@pytest.mark.integration
def test_real_s3_connection() -> None:
    if not os.environ.get("RUN_S3_INTEGRATION"):
        pytest.skip(
            "Set RUN_S3_INTEGRATION=1 to run against AWS S3"
        )
    S3StorageAdapter(Settings()).check_connection()
