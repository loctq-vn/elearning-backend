"""Role-based access control and permission dependencies."""

from collections.abc import Sequence

from fastapi import Depends

from app.core.errors import AppError
from app.core.security import get_current_active_user
from app.db.models.schema import User, UserRole


class RoleChecker:
    """Dependency for requiring one of the allowed roles."""

    def __init__(self, allowed_roles: Sequence[UserRole] | Sequence[str]) -> None:
        self.allowed_roles = {
            role.value if isinstance(role, UserRole) else str(role) for role in allowed_roles
        }

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        user_role_value = (
            current_user.role.value
            if isinstance(current_user.role, UserRole)
            else str(current_user.role)
        )
        if user_role_value not in self.allowed_roles:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Bạn không có quyền thực hiện hành động này.",
            )
        return current_user


require_admin = RoleChecker([UserRole.ADMIN])
require_student = RoleChecker([UserRole.STUDENT])
require_authenticated = get_current_active_user
