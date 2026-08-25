"""Add named random study presets."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_0006"
down_revision: str | Sequence[str] | None = "20260825_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "random_study_presets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
            name="ck_random_study_presets_problem_count",
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "card_id",
            "name",
            name="uq_random_study_presets_card_id_name",
        ),
    )
    op.create_index(
        "ix_random_study_presets_topic_id",
        "random_study_presets",
        ["topic_id"],
        unique=False,
    )

    with op.batch_alter_table("random_study_settings") as batch_op:
        batch_op.add_column(sa.Column("preset_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_random_study_settings_preset_id_random_study_presets",
            "random_study_presets",
            ["preset_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_random_study_settings_preset_id",
            ["preset_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("random_study_settings") as batch_op:
        batch_op.drop_index("ix_random_study_settings_preset_id")
        batch_op.drop_constraint(
            "fk_random_study_settings_preset_id_random_study_presets",
            type_="foreignkey",
        )
        batch_op.drop_column("preset_id")

    op.drop_index(
        "ix_random_study_presets_topic_id",
        table_name="random_study_presets",
    )
    op.drop_table("random_study_presets")
