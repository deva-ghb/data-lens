"""Vessel calls, and where each assignment's work happens.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vessel_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vessel_name", sa.String(length=80), nullable=False),
        sa.Column("berth_zone_id", sa.Integer(), nullable=False),
        sa.Column("arrives_at", sa.DateTime(), nullable=False),
        sa.Column("departs_at", sa.DateTime(), nullable=False),
        sa.Column("moves_planned", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["berth_zone_id"], ["zones.id"], name=op.f("fk_vessel_calls_berth_zone_id_zones")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vessel_calls")),
    )
    with op.batch_alter_table("vessel_calls") as batch_op:
        batch_op.create_index(batch_op.f("ix_vessel_calls_berth_zone_id"), ["berth_zone_id"])
        batch_op.create_index(batch_op.f("ix_vessel_calls_arrives_at"), ["arrives_at"])
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(sa.Column("zone_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_assignments_zone_id_zones"), "zones", ["zone_id"], ["id"]
        )
        batch_op.create_index(batch_op.f("ix_assignments_zone_id"), ["zone_id"])


def downgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_index(batch_op.f("ix_assignments_zone_id"))
        batch_op.drop_constraint(batch_op.f("fk_assignments_zone_id_zones"), type_="foreignkey")
        batch_op.drop_column("zone_id")
    op.drop_table("vessel_calls")
