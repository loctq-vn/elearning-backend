"""add server defaults for user account fields.

Revision ID: 7f2c9d1e4a10
Revises: 45ba51cef6db
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7f2c9d1e4a10"
down_revision: str | Sequence[str] | None = "45ba51cef6db"


def upgrade() -> None:
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("student", "admin", name="user_role"),
        server_default=sa.text("'student'::user_role"),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "is_verified",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "is_locked",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("student", "admin", name="user_role"),
        server_default=None,
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "is_verified",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "is_locked",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )
