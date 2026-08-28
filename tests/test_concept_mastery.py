from collections.abc import Sequence

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.models.card import Card
from app.models.concept import Concept, ProblemConcept
from app.models.problem import Problem
from app.models.profile import Profile
from app.models.topic import Topic
from app.schemas.knowledge_graph import KnowledgeGraphNodeRead, KnowledgeGraphRead
from app.services.concept_mastery import (
    ConceptMastery,
    apply_concept_mastery,
    compute_concept_mastery,
)


@pytest.fixture
def session_factory(
    test_session_factory: sessionmaker[Session],
) -> sessionmaker[Session]:
    return test_session_factory


def _make_base(session_factory: sessionmaker[Session]) -> tuple[int, int, int]:
    with session_factory() as session:
        profile = Profile(display_name="테스트")
        session.add(profile)
        session.flush()
        card = Card(profile_id=profile.id, title="정보처리기사")
        session.add(card)
        session.flush()
        topic = Topic(card_id=card.id, name="데이터베이스")
        session.add(topic)
        session.commit()
        return profile.id, card.id, topic.id


def _add_concept(
    session_factory: sessionmaker[Session],
    *,
    profile_id: int,
    card_id: int,
    topic_id: int,
    name: str,
    problems: Sequence[tuple[str, int, int]],
) -> int:
    """problems: (role, correct_count, incorrect_count) 리스트."""
    with session_factory() as session:
        concept = Concept(profile_id=profile_id, name=name, name_key=name)
        session.add(concept)
        session.flush()
        for role, correct, incorrect in problems:
            problem = Problem(
                card_id=card_id,
                topic_id=topic_id,
                question=f"{name} 문제",
                problem_type="short_answer",
                correct_count=correct,
                incorrect_count=incorrect,
            )
            session.add(problem)
            session.flush()
            session.add(
                ProblemConcept(problem_id=problem.id, concept_id=concept.id, role=role)
            )
        session.commit()
        return concept.id


def test_graded_zero_is_unattempted(session_factory: sessionmaker[Session]) -> None:
    profile_id, card_id, topic_id = _make_base(session_factory)
    concept_id = _add_concept(
        session_factory,
        profile_id=profile_id,
        card_id=card_id,
        topic_id=topic_id,
        name="정규화",
        problems=[("primary", 0, 0)],
    )

    with session_factory() as session:
        result = compute_concept_mastery(session, [concept_id])

    mastery = result[concept_id]
    assert mastery.problem_count == 1
    assert mastery.graded_count == 0
    assert mastery.attempted is False
    assert mastery.mastery_score is None


def test_single_correct_uses_smoothing(session_factory: sessionmaker[Session]) -> None:
    profile_id, card_id, topic_id = _make_base(session_factory)
    concept_id = _add_concept(
        session_factory,
        profile_id=profile_id,
        card_id=card_id,
        topic_id=topic_id,
        name="트랜잭션",
        problems=[("primary", 1, 0)],
    )

    with session_factory() as session:
        mastery = compute_concept_mastery(session, [concept_id])[concept_id]

    assert mastery.attempted is True
    # 라플라스 스무딩: (1+1)/(1+2) = 0.666..., 1.0이 아니다.
    assert mastery.mastery_score is not None
    assert abs(mastery.mastery_score - 2 / 3) < 1e-9


def test_primary_only_ignores_supporting(
    session_factory: sessionmaker[Session],
) -> None:
    profile_id, card_id, topic_id = _make_base(session_factory)
    concept_id = _add_concept(
        session_factory,
        profile_id=profile_id,
        card_id=card_id,
        topic_id=topic_id,
        name="인덱스",
        problems=[("primary", 2, 0), ("supporting", 0, 9)],
    )

    with session_factory() as session:
        mastery = compute_concept_mastery(session, [concept_id])[concept_id]

    # supporting 문제(오답 9)는 무시되어야 한다.
    assert mastery.problem_count == 1
    assert mastery.correct_count == 2
    assert mastery.incorrect_count == 0


def test_concept_without_primary_problem_is_absent(
    session_factory: sessionmaker[Session],
) -> None:
    profile_id, card_id, topic_id = _make_base(session_factory)
    concept_id = _add_concept(
        session_factory,
        profile_id=profile_id,
        card_id=card_id,
        topic_id=topic_id,
        name="락",
        problems=[("supporting", 3, 1)],
    )

    with session_factory() as session:
        result = compute_concept_mastery(session, [concept_id])

    assert concept_id not in result


def test_multiple_concepts_aggregate_independently(
    session_factory: sessionmaker[Session],
) -> None:
    profile_id, card_id, topic_id = _make_base(session_factory)
    first = _add_concept(
        session_factory,
        profile_id=profile_id,
        card_id=card_id,
        topic_id=topic_id,
        name="정규화",
        problems=[("primary", 3, 1), ("primary", 1, 2)],
    )
    second = _add_concept(
        session_factory,
        profile_id=profile_id,
        card_id=card_id,
        topic_id=topic_id,
        name="트랜잭션",
        problems=[("primary", 0, 4)],
    )

    with session_factory() as session:
        result = compute_concept_mastery(session, [first, second])

    assert result[first].problem_count == 2
    assert result[first].correct_count == 4
    assert result[first].incorrect_count == 3
    assert result[second].correct_count == 0
    assert result[second].incorrect_count == 4


def test_empty_ids_returns_empty(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        assert compute_concept_mastery(session, []) == {}


def test_apply_mastery_enriches_and_grays_unmatched() -> None:
    graph = KnowledgeGraphRead(
        card_id=1,
        nodes=[
            KnowledgeGraphNodeRead(
                id="c1", iri="c1", type="concept", label="정규화", external_id=1
            ),
            KnowledgeGraphNodeRead(
                id="p1",
                iri="p1",
                type="problem",
                label="문제",
                external_id=11,
                correct_count=3,
                incorrect_count=2,
            ),
            KnowledgeGraphNodeRead(
                id="c2", iri="c2", type="concept", label="stale", external_id=999
            ),
        ],
        edges=[],
        truncated=False,
    )
    mastery = {
        1: ConceptMastery(
            concept_id=1, problem_count=2, correct_count=3, incorrect_count=1
        )
    }

    apply_concept_mastery(graph, mastery)

    nodes = {node.id: node for node in graph.nodes}
    # 매칭된 개념: 집계 반영.
    assert nodes["c1"].attempted is True
    assert nodes["c1"].problem_count == 2
    assert nodes["c1"].correct_count == 3
    assert nodes["c1"].mastery_score is not None
    # DB에 없는 stale 개념 노드: 회색(미평가), 크래시 없음.
    assert nodes["c2"].attempted is False
    assert nodes["c2"].problem_count == 0
    assert nodes["c2"].mastery_score is None
    # 개념이 아닌 노드는 손대지 않는다(Fuseki가 준 문제 노드 카운트 유지).
    assert nodes["p1"].correct_count == 3
    assert nodes["p1"].attempted is None
