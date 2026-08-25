"""Add problem types and choices."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260824_0002"
down_revision: str | Sequence[str] | None = "20260824_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(
            sa.Column(
                "problem_type",
                sa.String(length=32),
                server_default="short_answer",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("choices", sa.JSON(), nullable=True))
        batch_op.create_check_constraint(
            "ck_problems_problem_type",
            "problem_type IN ('short_answer', 'essay', 'multiple_choice', 'true_false')",
        )


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_constraint("ck_problems_problem_type", type_="check")
        batch_op.drop_column("choices")
        batch_op.drop_column("problem_type")
