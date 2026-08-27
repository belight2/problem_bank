"""Add reusable concepts and learning resource concept links."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0015"
down_revision: str | Sequence[str] | None = "20260827_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "concepts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_key", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "name_key",
            name="uq_concepts_profile_id_name_key",
        ),
    )
    op.create_index("ix_concepts_profile_id", "concepts", ["profile_id"], unique=False)

    op.create_table(
        "card_concepts",
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("card_id", "concept_id"),
    )
    op.create_table(
        "problem_concepts",
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('primary', 'supporting')",
            name="ck_problem_concepts_role",
        ),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("problem_id", "concept_id"),
    )
    op.create_index(
        "uq_problem_concepts_one_primary",
        "problem_concepts",
        ["problem_id"],
        unique=True,
        postgresql_where=sa.text("role = 'primary'"),
        sqlite_where=sa.text("role = 'primary'"),
    )
    op.create_table(
        "note_concepts",
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("note_id", "concept_id"),
    )
    op.create_table(
        "concept_relations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_concept_id", sa.Integer(), nullable=False),
        sa.Column("target_concept_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_concept_id <> target_concept_id",
            name="ck_concept_relations_distinct_concepts",
        ),
        sa.CheckConstraint(
            "relation_type IN ('broader', 'prerequisite', 'related', 'contrasts', 'confused_with')",
            name="ck_concept_relations_type",
        ),
        sa.ForeignKeyConstraint(
            ["source_concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_concept_id",
            "target_concept_id",
            "relation_type",
            name="uq_concept_relations_source_target_type",
        ),
    )
    op.create_index(
        "ix_concept_relations_source_concept_id",
        "concept_relations",
        ["source_concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_concept_relations_target_concept_id",
        "concept_relations",
        ["target_concept_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_concept_relations_target_concept_id",
        table_name="concept_relations",
    )
    op.drop_index(
        "ix_concept_relations_source_concept_id",
        table_name="concept_relations",
    )
    op.drop_table("concept_relations")
    op.drop_table("note_concepts")
    op.drop_index("uq_problem_concepts_one_primary", table_name="problem_concepts")
    op.drop_table("problem_concepts")
    op.drop_table("card_concepts")
    op.drop_index("ix_concepts_profile_id", table_name="concepts")
    op.drop_table("concepts")
