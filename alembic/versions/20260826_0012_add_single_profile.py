"""Add the local profile and attach cards to it."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260826_0012"
down_revision: str | Sequence[str] | None = "20260826_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=80), server_default="사용자", nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Seoul", nullable=False),
        sa.Column("daily_goal", sa.Integer(), server_default="20", nullable=False),
        sa.Column("is_configured", sa.Boolean(), server_default=sa.false(), nullable=False),
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
            "daily_goal BETWEEN 1 AND 100",
            name="ck_profiles_daily_goal",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO profiles (
                id, display_name, timezone, daily_goal, is_configured,
                created_at, updated_at
            ) VALUES (
                1, '사용자', 'Asia/Seoul', 20, false,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        )
    )
    op.add_column(
        "cards",
        sa.Column("profile_id", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_foreign_key(
        "fk_cards_profile_id_profiles",
        "cards",
        "profiles",
        ["profile_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_cards_profile_id", "cards", ["profile_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cards_profile_id", table_name="cards")
    op.drop_constraint(
        "fk_cards_profile_id_profiles",
        "cards",
        type_="foreignkey",
    )
    op.drop_column("cards", "profile_id")
    op.drop_table("profiles")
