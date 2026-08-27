"""Add the superseded graph outbox status."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0014"
down_revision: str | Sequence[str] | None = "20260827_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_graph_outbox_status",
        "graph_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "ck_graph_outbox_status",
        "graph_outbox",
        "status IN ('pending', 'processing', 'completed', 'failed', 'superseded')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_graph_outbox_status",
        "graph_outbox",
        type_="check",
    )
    op.execute(
        sa.text(
            "UPDATE graph_outbox SET status = 'failed' "
            "WHERE status = 'superseded'"
        )
    )
    op.create_check_constraint(
        "ck_graph_outbox_status",
        "graph_outbox",
        "status IN ('pending', 'processing', 'completed', 'failed')",
    )
