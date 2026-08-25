"""Add problem study statistics and idempotent study sessions."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_0007"
down_revision: str | Sequence[str] | None = "20260825_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(
            sa.Column(
                "presented_count",
                sa.Integer(),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "correct_count",
                sa.Integer(),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "incorrect_count",
                sa.Integer(),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_problems_study_counts_nonnegative",
            "presented_count >= 0 AND correct_count >= 0 AND incorrect_count >= 0",
        )

    op.create_table(
        "study_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("problem_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_study_sessions_card_id",
        "study_sessions",
        ["card_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_study_sessions_card_id", table_name="study_sessions")
    op.drop_table("study_sessions")

    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_constraint(
            "ck_problems_study_counts_nonnegative",
            type_="check",
        )
        batch_op.drop_column("incorrect_count")
        batch_op.drop_column("correct_count")
        batch_op.drop_column("presented_count")
