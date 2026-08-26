"""Add persistent workbooks and workbook attempt results."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260826_0011"
down_revision: str | Sequence[str] | None = "20260826_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workbooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("preset_id", sa.Integer(), nullable=True),
        sa.Column("problem_ids", sa.JSON(), nullable=False),
        sa.Column("requested_problem_count", sa.Integer(), nullable=False),
        sa.Column("selection_mode", sa.String(length=20), server_default="all", nullable=False),
        sa.Column("incorrect_rate_threshold", sa.Integer(), server_default="50", nullable=False),
        sa.Column("minimum_attempt_count", sa.Integer(), server_default="3", nullable=False),
        sa.Column("incorrect_count_threshold", sa.Integer(), server_default="1", nullable=False),
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
            "selection_mode IN ('all', 'incorrect_rate', 'incorrect_count')",
            name="ck_workbooks_selection_mode",
        ),
        sa.CheckConstraint(
            "requested_problem_count BETWEEN 1 AND 100",
            name="ck_workbooks_requested_problem_count",
        ),
        sa.CheckConstraint(
            "incorrect_rate_threshold BETWEEN 1 AND 100",
            name="ck_workbooks_incorrect_rate_threshold",
        ),
        sa.CheckConstraint(
            "minimum_attempt_count >= 1",
            name="ck_workbooks_minimum_attempt_count",
        ),
        sa.CheckConstraint(
            "incorrect_count_threshold >= 1",
            name="ck_workbooks_incorrect_count_threshold",
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["preset_id"], ["random_study_presets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workbooks_card_id", "workbooks", ["card_id"], unique=False)
    op.create_index("ix_workbooks_preset_id", "workbooks", ["preset_id"], unique=False)
    op.create_index("ix_workbooks_topic_id", "workbooks", ["topic_id"], unique=False)

    op.add_column("study_sessions", sa.Column("workbook_id", sa.Integer(), nullable=True))
    op.add_column(
        "study_sessions",
        sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column("study_sessions", sa.Column("results", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_study_sessions_workbook_id_workbooks",
        "study_sessions",
        "workbooks",
        ["workbook_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_study_sessions_workbook_id",
        "study_sessions",
        ["workbook_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_study_sessions_workbook_id_attempt_number",
        "study_sessions",
        ["workbook_id", "attempt_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_study_sessions_workbook_id_attempt_number",
        "study_sessions",
        type_="unique",
    )
    op.drop_index("ix_study_sessions_workbook_id", table_name="study_sessions")
    op.drop_constraint(
        "fk_study_sessions_workbook_id_workbooks",
        "study_sessions",
        type_="foreignkey",
    )
    op.drop_column("study_sessions", "results")
    op.drop_column("study_sessions", "attempt_number")
    op.drop_column("study_sessions", "workbook_id")

    op.drop_index("ix_workbooks_topic_id", table_name="workbooks")
    op.drop_index("ix_workbooks_preset_id", table_name="workbooks")
    op.drop_index("ix_workbooks_card_id", table_name="workbooks")
    op.drop_table("workbooks")
