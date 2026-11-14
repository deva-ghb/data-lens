"""Typed answers from the Decisions API.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_kind", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("questions_json", sa.JSON(), nullable=False),
        sa.Column("answers_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_decisions")),
    )
    with op.batch_alter_table("ai_decisions") as batch_op:
        batch_op.create_index(batch_op.f("ix_ai_decisions_subject_id"), ["subject_id"])


def downgrade() -> None:
    op.drop_table("ai_decisions")
