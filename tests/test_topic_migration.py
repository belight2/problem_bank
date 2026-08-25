import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATIONS_DIR = Path(__file__).parent.parent / "alembic" / "versions"


def load_migration(filename: str) -> ModuleType:
    path = MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_migration(connection: sa.Connection, filename: str, direction: str) -> None:
    module = load_migration(filename)
    module.op = Operations(MigrationContext.configure(connection))
    getattr(module, direction)()


def test_topic_migration_backfills_and_downgrade_restores_strings() -> None:
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        run_migration(
            connection,
            "20260824_0001_create_cards_and_problems.py",
            "upgrade",
        )
        connection.execute(
            sa.text("INSERT INTO cards (id, title) VALUES (1, '자격증'), (2, 'SQLD')")
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO problems (id, card_id, topic, question)
                VALUES
                    (1, 1, 'Database', 'Q1'),
                    (2, 1, 'Database', 'Q2'),
                    (3, 1, 'database', 'Q3'),
                    (4, 2, 'Database', 'Q4')
                """
            )
        )
        run_migration(
            connection,
            "20260824_0002_add_problem_types.py",
            "upgrade",
        )
        run_migration(
            connection,
            "20260825_0003_normalize_topics.py",
            "upgrade",
        )
        run_migration(
            connection,
            "20260825_0004_add_fill_blank_problem_type.py",
            "upgrade",
        )

        connection.execute(
            sa.text(
                """
                UPDATE problems
                SET problem_type = 'fill_blank', question = '핵심 개념은 [빈칸]이다.'
                WHERE id = 1
                """
            )
        )

        migrated_problems = connection.execute(
            sa.text(
                """
                SELECT problems.id, problems.problem_type, topics.card_id, topics.name
                FROM problems
                JOIN topics ON topics.id = problems.topic_id
                ORDER BY problems.id
                """
            )
        ).all()
        assert migrated_problems == [
            (1, "fill_blank", 1, "Database"),
            (2, "short_answer", 1, "Database"),
            (3, "short_answer", 1, "database"),
            (4, "short_answer", 2, "Database"),
        ]
        assert connection.scalar(sa.text("SELECT count(*) FROM topics")) == 3

        inspector = sa.inspect(connection)
        assert "topic" not in {column["name"] for column in inspector.get_columns("problems")}
        assert "topic_id" in {column["name"] for column in inspector.get_columns("problems")}
        assert any(
            constraint["column_names"] == ["card_id", "name"]
            for constraint in inspector.get_unique_constraints("topics")
        )
        assert any(
            foreign_key["constrained_columns"] == ["card_id", "topic_id"]
            and foreign_key["referred_columns"] == ["card_id", "id"]
            for foreign_key in inspector.get_foreign_keys("problems")
        )

        run_migration(
            connection,
            "20260825_0004_add_fill_blank_problem_type.py",
            "downgrade",
        )
        assert (
            connection.scalar(sa.text("SELECT problem_type FROM problems WHERE id = 1"))
            == "short_answer"
        )

        run_migration(
            connection,
            "20260825_0003_normalize_topics.py",
            "downgrade",
        )

        restored_problems = connection.execute(
            sa.text("SELECT id, topic FROM problems ORDER BY id")
        ).all()
        assert restored_problems == [
            (1, "Database"),
            (2, "Database"),
            (3, "database"),
            (4, "Database"),
        ]
        inspector = sa.inspect(connection)
        assert "topics" not in inspector.get_table_names()
        assert "topic_id" not in {column["name"] for column in inspector.get_columns("problems")}

    engine.dispose()
