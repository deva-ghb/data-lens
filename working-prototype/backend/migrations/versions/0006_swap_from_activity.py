"""Remember the activity a swap moves a worker from.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("swap_proposals") as batch_op:
        batch_op.add_column(sa.Column("from_activity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_swap_proposals_from_activity_id_activities"),
            "activities",
            ["from_activity_id"],
            ["id"],
        )
        batch_op.create_index(batch_op.f("ix_swap_proposals_from_activity_id"), ["from_activity_id"])


def downgrade() -> None:
    with op.batch_alter_table("swap_proposals") as batch_op:
        batch_op.drop_index(batch_op.f("ix_swap_proposals_from_activity_id"))
        batch_op.drop_constraint(
            batch_op.f("fk_swap_proposals_from_activity_id_activities"), type_="foreignkey"
        )
        batch_op.drop_column("from_activity_id")
