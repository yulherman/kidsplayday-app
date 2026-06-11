"""add country column to users

Revision ID: f3b2c8a4d6e1
Revises: e2f5a8b1c4d9
Create Date: 2026-06-11 09:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3b2c8a4d6e1"
down_revision: Union[str, None] = "e2f5a8b1c4d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("country", sa.String(2), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "country")
