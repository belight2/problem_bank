"""Add persistent random study settings."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_0005"
down_revision: str | Sequence[str] | None = "20260825_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "random_study_settings",
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("problem_count", sa.Integer(), nullable=False),
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
            "problem_count BETWEEN 1 AND 100",
            name="ck_random_study_settings_problem_count",
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("card_id"),
    )
    op.create_index(
        "ix_random_study_settings_topic_id",
        "random_study_settings",
        ["topic_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_random_study_settings_topic_id",
        table_name="random_study_settings",
    )
    op.drop_table("random_study_settings")
