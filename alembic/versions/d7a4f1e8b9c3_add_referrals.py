"""add referral fields and premium_until

Revision ID: d7a4f1e8b9c3
Revises: c5d8e9f3a1b2
Create Date: 2026-06-08 14:30:00.000000
"""
import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d7a4f1e8b9c3"
down_revision: Union[str, None] = "c5d8e9f3a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _gen_code() -> str:
    # 8-char base32 (Crockford-ish, no padding) — readable and short
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(secrets.choice(alphabet) for _ in range(8))


def upgrade() -> None:
    op.add_column("users", sa.Column("referral_code", sa.String(length=12), nullable=True))
    op.add_column(
        "users",
        sa.Column("referred_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("premium_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_referred_by",
        "users",
        "users",
        ["referred_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_referral_code", "users", ["referral_code"], unique=True)

    bind = op.get_bind()
    user_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM users")).fetchall()]
    existing = set(
        row[0] for row in bind.execute(
            sa.text("SELECT referral_code FROM users WHERE referral_code IS NOT NULL")
        ).fetchall()
    )
    for uid in user_ids:
        code = _gen_code()
        while code in existing:
            code = _gen_code()
        existing.add(code)
        bind.execute(
            sa.text("UPDATE users SET referral_code = :code WHERE id = :uid"),
            {"code": code, "uid": uid},
        )


def downgrade() -> None:
    op.drop_index("ix_users_referral_code", table_name="users")
    op.drop_constraint("fk_users_referred_by", "users", type_="foreignkey")
    op.drop_column("users", "premium_until")
    op.drop_column("users", "referred_by_user_id")
    op.drop_column("users", "referral_code")
