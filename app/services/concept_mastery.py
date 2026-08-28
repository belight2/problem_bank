from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.concept import ProblemConcept, ProblemConceptRole
from app.models.problem import Problem
from app.schemas.knowledge_graph import KnowledgeGraphRead

# graded_count가 이 값 미만이면 프론트에서 "표본 적음"으로 흐리게 표시하기 위한 기본 임계값.
# 실제 사용 데이터로 튜닝 대상(설계 문서의 열린 질문). 백엔드는 참고값만 노출하고
# 최종 표시는 프론트가 graded_count로 판단한다.
LOW_SAMPLE_THRESHOLD = 3


@dataclass(frozen=True)
class ConceptMastery:
    """개념 하나에 대해 primary로 연결된 문제들의 채점 집계."""

    concept_id: int
    problem_count: int
    correct_count: int
    incorrect_count: int

    @property
    def graded_count(self) -> int:
        return self.correct_count + self.incorrect_count

    @property
    def attempted(self) -> bool:
        return self.graded_count > 0

    @property
    def mastery_score(self) -> float | None:
        # 라플라스 스무딩: 표본이 작을 때 "1문제 1회 정답 = 100%" 같은 착시를 완화한다.
        # 미채점(attempted=False) 개념은 신호가 없으므로 None(프론트에서 회색).
        if not self.attempted:
            return None
        return (self.correct_count + 1) / (self.graded_count + 2)


def compute_concept_mastery(
    db: Session,
    concept_ids: Iterable[int],
) -> dict[int, ConceptMastery]:
    """개념별 숙련도를 DB에서 한 번의 group-by로 집계한다.

    - primary 역할로 연결된 문제만 집계한다(supporting은 v1에서 제외).
    - primary 문제가 하나도 없는 개념은 결과에 포함되지 않는다(호출측에서 미평가로 처리).
    """
    ids = {concept_id for concept_id in concept_ids if concept_id > 0}
    if not ids:
        return {}

    rows = db.execute(
        select(
            ProblemConcept.concept_id,
            func.count(Problem.id),
            func.coalesce(func.sum(Problem.correct_count), 0),
            func.coalesce(func.sum(Problem.incorrect_count), 0),
        )
        .join(Problem, Problem.id == ProblemConcept.problem_id)
        .where(
            ProblemConcept.concept_id.in_(ids),
            ProblemConcept.role == ProblemConceptRole.PRIMARY.value,
        )
        .group_by(ProblemConcept.concept_id)
    ).all()

    return {
        int(concept_id): ConceptMastery(
            concept_id=int(concept_id),
            problem_count=int(problem_count),
            correct_count=int(correct_count),
            incorrect_count=int(incorrect_count),
        )
        for concept_id, problem_count, correct_count, incorrect_count in rows
    }


def apply_concept_mastery(
    graph: KnowledgeGraphRead,
    mastery_by_concept_id: dict[int, ConceptMastery],
) -> None:
    """Fuseki에서 온 그래프의 개념 노드에 DB 집계 숙련도를 external_id로 LEFT join 병합한다.

    Fuseki가 노드 집합이고 DB가 보강이다. 매칭이 없으면(대응 DB 개념이 없거나 동기화 지연으로
    남은 stale 노드, 또는 primary 문제가 없는 개념) 해당 노드는 미평가(회색)로 둔다 -- 크래시 금지.
    """
    for node in graph.nodes:
        if node.type != "concept":
            continue

        mastery = (
            mastery_by_concept_id.get(node.external_id)
            if node.external_id is not None
            else None
        )
        if mastery is None:
            node.attempted = False
            node.problem_count = 0
            node.correct_count = None
            node.incorrect_count = None
            node.mastery_score = None
            continue

        node.attempted = mastery.attempted
        node.problem_count = mastery.problem_count
        node.correct_count = mastery.correct_count
        node.incorrect_count = mastery.incorrect_count
        node.mastery_score = mastery.mastery_score
