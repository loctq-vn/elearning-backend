"""create initial database schema.

Revision ID: 45ba51cef6db
Revises:
"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

from app.db.models import Base

revision: str = '45ba51cef6db'
down_revision: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(connection)



def downgrade() -> None:
    connection = op.get_bind()
    Base.metadata.drop_all(connection)
