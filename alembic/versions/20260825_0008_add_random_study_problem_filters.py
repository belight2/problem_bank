"""Add random study problem filters."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_0008"
down_revision: str | Sequence[str] | None = "20260825_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def add_filter_columns(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(
            sa.Column(
                "selection_mode",
                sa.String(length=20),
                server_default="all",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "incorrect_rate_threshold",
                sa.Integer(),
                server_default="50",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "minimum_attempt_count",
                sa.Integer(),
                server_default="3",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "incorrect_count_threshold",
                sa.Integer(),
                server_default="1",
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            f"ck_{table_name}_selection_mode",
            "selection_mode IN ('all', 'incorrect_rate', 'incorrect_count')",
        )
        batch_op.create_check_constraint(
            f"ck_{table_name}_incorrect_rate_threshold",
            "incorrect_rate_threshold BETWEEN 1 AND 100",
        )
        batch_op.create_check_constraint(
            f"ck_{table_name}_minimum_attempt_count",
            "minimum_attempt_count >= 1",
        )
        batch_op.create_check_constraint(
            f"ck_{table_name}_incorrect_count_threshold",
            "incorrect_count_threshold >= 1",
        )


def drop_filter_columns(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(
            f"ck_{table_name}_incorrect_count_threshold",
            type_="check",
        )
        batch_op.drop_constraint(
            f"ck_{table_name}_minimum_attempt_count",
            type_="check",
        )
        batch_op.drop_constraint(
            f"ck_{table_name}_incorrect_rate_threshold",
            type_="check",
        )
        batch_op.drop_constraint(
            f"ck_{table_name}_selection_mode",
            type_="check",
        )
        batch_op.drop_column("incorrect_count_threshold")
        batch_op.drop_column("minimum_attempt_count")
        batch_op.drop_column("incorrect_rate_threshold")
        batch_op.drop_column("selection_mode")


def upgrade() -> None:
    add_filter_columns("random_study_settings")
    add_filter_columns("random_study_presets")


def downgrade() -> None:
    drop_filter_columns("random_study_presets")
    drop_filter_columns("random_study_settings")
