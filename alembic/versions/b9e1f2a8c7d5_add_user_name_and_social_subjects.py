"""add user name and apple subject

Revision ID: b9e1f2a8c7d5
Revises: 7c3fb1e9d2a4
Create Date: 2026-06-08 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b9e1f2a8c7d5"
down_revision: Union[str, None] = "7c3fb1e9d2a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("apple_subject", sa.String(length=255), nullable=True))
    op.create_index("ix_users_apple_subject", "users", ["apple_subject"], unique=True)
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
    op.drop_index("ix_users_apple_subject", table_name="users")
    op.drop_column("users", "apple_subject")
    op.drop_column("users", "name")
