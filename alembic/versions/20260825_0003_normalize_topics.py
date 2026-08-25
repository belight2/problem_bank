"""Normalize problem topics into a topics table."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_0003"
down_revision: str | Sequence[str] | None = "20260824_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "id", name="uq_topics_card_id_id"),
        sa.UniqueConstraint("card_id", "name", name="uq_topics_card_id_name"),
    )
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column("topic_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            INSERT INTO topics (card_id, name)
            SELECT DISTINCT card_id, topic
            FROM problems
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE problems
            SET topic_id = (
                SELECT topics.id
                FROM topics
                WHERE topics.card_id = problems.card_id
                  AND topics.name = problems.topic
            )
            """
        )
    )

    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_index("ix_problems_card_id_topic")
        batch_op.alter_column("topic_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_problems_card_id_topic_id_topics",
            "topics",
            ["card_id", "topic_id"],
            ["card_id", "id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_problems_card_id_topic_id",
            ["card_id", "topic_id"],
            unique=False,
        )
        batch_op.drop_column("topic")


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column("topic", sa.String(length=100), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE problems
            SET topic = (
                SELECT topics.name
                FROM topics
                WHERE topics.id = problems.topic_id
            )
            """
        )
    )

    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_index("ix_problems_card_id_topic_id")
        batch_op.drop_constraint(
            "fk_problems_card_id_topic_id_topics",
            type_="foreignkey",
        )
        batch_op.alter_column(
            "topic",
            existing_type=sa.String(length=100),
            nullable=False,
        )
        batch_op.create_index(
            "ix_problems_card_id_topic",
            ["card_id", "topic"],
            unique=False,
        )
        batch_op.drop_column("topic_id")

    op.drop_table("topics")
