"""Add the graph synchronization outbox."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0013"
down_revision: str | Sequence[str] | None = "20260826_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "graph_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=50), nullable=False),
        sa.Column("aggregate_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('upsert', 'delete')",
            name="ck_graph_outbox_event_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_graph_outbox_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_graph_outbox_attempt_count_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_graph_outbox_status_available_at_id",
        "graph_outbox",
        ["status", "available_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_graph_outbox_aggregate",
        "graph_outbox",
        ["aggregate_type", "aggregate_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_graph_outbox_aggregate", table_name="graph_outbox")
    op.drop_index(
        "ix_graph_outbox_status_available_at_id",
        table_name="graph_outbox",
    )
    op.drop_table("graph_outbox")
