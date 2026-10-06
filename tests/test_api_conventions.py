from fastapi import APIRouter, Query
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.schemas import ApiResponse, PaginationParams, build_paginated_response
from app.main import app


convention_router = APIRouter(prefix="/__test__")


@convention_router.get("/validation")
async def validation_endpoint(page: int = Query(ge=1)) -> dict[str, int]:
    return {"page": page}


@convention_router.get("/app-error")
async def app_error_endpoint() -> None:
    raise AppError(
        status_code=409,
        code="CONFLICT",
        message="Resource already exists",
        details={"field": ["already exists"]},
    )


app.include_router(convention_router)
client = TestClient(app)


def test_success_wrapper_and_pagination() -> None:
    response = ApiResponse(data={"id": "course-1"})
    page = build_paginated_response(
        ["a", "b", "c"],
        total=21,
        page=2,
        page_size=5,
    )

    assert response.model_dump() == {"data": {"id": "course-1"}, "message": "OK"}
    assert page.model_dump() == {
        "data": ["a", "b", "c"],
        "total": 21,
        "page": 2,
        "page_size": 5,
        "total_pages": 5,
    }
    assert PaginationParams().model_dump() == {"page": 1, "page_size": 20}


def test_validation_error_uses_common_format() -> None:
    response = client.get("/__test__/validation", params={"page": 0})

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Dữ liệu đầu vào không hợp lệ",
            "details": {"query.page": ["Input should be greater than or equal to 1"]},
        }
    }


def test_application_error_uses_common_format() -> None:
    response = client.get("/__test__/app-error")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "CONFLICT",
            "message": "Resource already exists",
            "details": {"field": ["already exists"]},
        }
    }


def test_not_found_error_uses_common_format() -> None:
    response = client.get("/__test__/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_openapi_exposes_common_schemas_and_bearer_jwt() -> None:
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()

    assert schema["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT access token in the Authorization: Bearer <token> header.",
    }
    assert {
        "ApiResponse",
        "PaginatedResponse",
        "ErrorBody",
        "ErrorResponse",
    }.issubset(schema["components"]["schemas"])
