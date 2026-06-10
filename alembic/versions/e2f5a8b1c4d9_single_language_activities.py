"""single language activities — replace dual _uk/_en columns with single fields + language

Revision ID: e2f5a8b1c4d9
Revises: d7a4f1e8b9c3
Create Date: 2026-06-10 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f5a8b1c4d9"
down_revision: Union[str, None] = "d7a4f1e8b9c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new single-language columns (nullable first, populate, then set NOT NULL)
    op.add_column("activities", sa.Column("title", sa.String(300), nullable=True))
    op.add_column("activities", sa.Column("short_description", sa.String(220), nullable=True))
    op.add_column("activities", sa.Column("description", sa.Text, nullable=True))
    op.add_column("activities", sa.Column("instructions", sa.Text, nullable=True))
    op.add_column("activities", sa.Column("language", sa.String(10), server_default="uk", nullable=False))

    # Copy existing data from _uk columns (existing data was Ukrainian)
    op.execute(
        "UPDATE activities SET "
        "title = title_uk, "
        "short_description = short_description_uk, "
        "description = description_uk, "
        "instructions = instructions_uk, "
        "language = 'uk'"
    )

    # Make content columns NOT NULL
    op.alter_column("activities", "title", nullable=False)
    op.alter_column("activities", "description", nullable=False)
    op.alter_column("activities", "instructions", nullable=False)

    # Drop old dual-language columns
    for col in [
        "title_uk", "title_en",
        "short_description_uk", "short_description_en",
        "description_uk", "description_en",
        "instructions_uk", "instructions_en",
    ]:
        op.drop_column("activities", col)


def downgrade() -> None:
    # Restore dual-language columns (content goes back to both _uk and _en)
    op.add_column("activities", sa.Column("title_uk", sa.String(300), nullable=True))
    op.add_column("activities", sa.Column("title_en", sa.String(300), nullable=True))
    op.add_column("activities", sa.Column("short_description_uk", sa.String(220), nullable=True))
    op.add_column("activities", sa.Column("short_description_en", sa.String(220), nullable=True))
    op.add_column("activities", sa.Column("description_uk", sa.Text, nullable=True))
    op.add_column("activities", sa.Column("description_en", sa.Text, nullable=True))
    op.add_column("activities", sa.Column("instructions_uk", sa.Text, nullable=True))
    op.add_column("activities", sa.Column("instructions_en", sa.Text, nullable=True))

    op.execute(
        "UPDATE activities SET "
        "title_uk = title, title_en = title, "
        "short_description_uk = short_description, short_description_en = short_description, "
        "description_uk = description, description_en = description, "
        "instructions_uk = instructions, instructions_en = instructions"
    )

    for col in ["title_uk", "title_en", "description_uk", "description_en",
                "instructions_uk", "instructions_en"]:
        op.alter_column("activities", col, nullable=False)

    op.drop_column("activities", "language")
    op.drop_column("activities", "instructions")
    op.drop_column("activities", "description")
    op.drop_column("activities", "short_description")
    op.drop_column("activities", "title")
