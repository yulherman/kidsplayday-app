"""add short_description columns to activities

Revision ID: 7c3fb1e9d2a4
Revises: 3aa9321c60af
Create Date: 2026-06-04 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7c3fb1e9d2a4"
down_revision: Union[str, None] = "3aa9321c60af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("short_description_uk", sa.String(length=220), nullable=True),
    )
    op.add_column(
        "activities",
        sa.Column("short_description_en", sa.String(length=220), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("activities", "short_description_en")
    op.drop_column("activities", "short_description_uk")
