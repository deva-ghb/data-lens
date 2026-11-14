"""Photos on near-miss and hazard reports.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("near_misses", "hazard_reports"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("photo_key", sa.String(length=255), nullable=True))


def downgrade() -> None:
    for table in ("near_misses", "hazard_reports"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("photo_key")
