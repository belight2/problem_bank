"""Add the fill-blank problem type."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_0004"
down_revision: str | Sequence[str] | None = "20260825_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FOUR_PROBLEM_TYPES = "problem_type IN ('short_answer', 'essay', 'multiple_choice', 'true_false')"
FIVE_PROBLEM_TYPES = (
    "problem_type IN ('short_answer', 'essay', 'multiple_choice', 'true_false', 'fill_blank')"
)


def upgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_constraint("ck_problems_problem_type", type_="check")
        batch_op.create_check_constraint("ck_problems_problem_type", FIVE_PROBLEM_TYPES)


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_constraint("ck_problems_problem_type", type_="check")

    op.execute(
        sa.text(
            """
            UPDATE problems
            SET problem_type = 'short_answer'
            WHERE problem_type = 'fill_blank'
            """
        )
    )

    with op.batch_alter_table("problems") as batch_op:
        batch_op.create_check_constraint("ck_problems_problem_type", FOUR_PROBLEM_TYPES)
