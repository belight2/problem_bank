"""Add Markdown notes and optional problem source notes."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260826_0009"
down_revision: str | Sequence[str] | None = "20260825_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_card_id", "notes", ["card_id"], unique=False)
    op.create_index("ix_notes_topic_id", "notes", ["topic_id"], unique=False)

    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column("source_note_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_problems_source_note_id_notes",
            "notes",
            ["source_note_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_problems_source_note_id",
            ["source_note_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_index("ix_problems_source_note_id")
        batch_op.drop_constraint(
            "fk_problems_source_note_id_notes",
            type_="foreignkey",
        )
        batch_op.drop_column("source_note_id")

    op.drop_index("ix_notes_topic_id", table_name="notes")
    op.drop_index("ix_notes_card_id", table_name="notes")
    op.drop_table("notes")
