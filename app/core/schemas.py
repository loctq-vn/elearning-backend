"""Shared API response schemas and pagination helpers."""

from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Envelope for successful responses containing one resource."""

    model_config = ConfigDict(from_attributes=True)

    data: T
    message: str = "OK"


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for successful collection responses."""

    model_config = ConfigDict(from_attributes=True)

    data: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)


class PaginationParams(BaseModel):
    """Validated pagination query parameters shared by routers."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ErrorBody(BaseModel):
    """Standard machine-readable error payload."""

    code: str
    message: str
    details: dict[str, object] | None = None


class ErrorResponse(BaseModel):
    """Envelope for all API errors."""

    error: ErrorBody


def build_paginated_response(
    data: list[T],
    *,
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse[T]:
    """Build a paginated response with a consistent total-pages calculation."""

    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )
