"""Shared authentication dependencies and OpenAPI security metadata."""

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="JWT access token in the Authorization: Bearer <token> header.",
    auto_error=False,
)


def bearer_credentials(
    credentials: HTTPAuthorizationCredentials | None,
) -> HTTPAuthorizationCredentials | None:
    """Keep token extraction reusable by future authenticated routers."""

    return credentials
