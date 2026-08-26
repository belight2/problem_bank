"""Add wrong-answer review records."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260826_0010"
down_revision: str | Sequence[str] | None = "20260826_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wrong_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="needs_review",
            nullable=False,
        ),
        sa.Column("last_submitted_answer", sa.Text(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column(
            "last_incorrect_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
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
            "status IN ('needs_review', 'reviewing', 'resolved')",
            name="ck_wrong_answers_status",
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("problem_id", name="uq_wrong_answers_problem_id"),
    )
    op.create_index(
        "ix_wrong_answers_card_id",
        "wrong_answers",
        ["card_id"],
        unique=False,
    )
    op.create_index(
        "ix_wrong_answers_card_id_status",
        "wrong_answers",
        ["card_id", "status"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO wrong_answers (
                card_id,
                problem_id,
                status,
                last_submitted_answer,
                memo,
                last_incorrect_at,
                created_at,
                updated_at
            )
            SELECT
                card_id,
                id,
                'needs_review',
                NULL,
                NULL,
                updated_at,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM problems
            WHERE incorrect_count > 0
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_wrong_answers_card_id_status", table_name="wrong_answers")
    op.drop_index("ix_wrong_answers_card_id", table_name="wrong_answers")
    op.drop_table("wrong_answers")
