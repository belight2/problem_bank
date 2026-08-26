from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import DatabaseSession
from app.api.routes.problems import choose_weighted_problems, ensure_card_exists
from app.models.problem import Problem
from app.models.study_session import StudySession
from app.models.wrong_answer import WrongAnswer, WrongAnswerStatus
from app.schemas.problem import RandomProblemSetRead
from app.schemas.wrong_answer import WrongAnswerRead, WrongAnswerUpdate

router = APIRouter(prefix="/cards/{card_id}/wrong-answers", tags=["wrong-answers"])


def wrong_answer_load_options() -> tuple:
    return (
        selectinload(WrongAnswer.problem).selectinload(Problem.topic),
        selectinload(WrongAnswer.problem).selectinload(Problem.source_note),
    )


def get_wrong_answer_or_404(
    card_id: int,
    problem_id: int,
    db: Session,
) -> WrongAnswer:
    statement = (
        select(WrongAnswer)
        .options(*wrong_answer_load_options())
        .where(
            WrongAnswer.card_id == card_id,
            WrongAnswer.problem_id == problem_id,
        )
    )
    wrong_answer = db.scalar(statement)
    if wrong_answer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wrong answer not found",
        )
    return wrong_answer


@router.get("", response_model=list[WrongAnswerRead])
def list_wrong_answers(
    card_id: int,
    db: DatabaseSession,
    review_status: WrongAnswerStatus | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[WrongAnswer]:
    ensure_card_exists(card_id, db)
    status_order = case(
        (WrongAnswer.status == WrongAnswerStatus.NEEDS_REVIEW.value, 0),
        (WrongAnswer.status == WrongAnswerStatus.REVIEWING.value, 1),
        else_=2,
    )
    statement = (
        select(WrongAnswer)
        .options(*wrong_answer_load_options())
        .where(WrongAnswer.card_id == card_id)
    )
    if review_status is not None:
        statement = statement.where(WrongAnswer.status == review_status.value)
    statement = (
        statement.order_by(
            status_order,
            WrongAnswer.last_incorrect_at.desc(),
            WrongAnswer.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.post("/study", response_model=RandomProblemSetRead)
def create_wrong_answer_study_set(
    card_id: int,
    db: DatabaseSession,
    problem_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> dict[str, str | None | list[Problem]]:
    ensure_card_exists(card_id, db)
    statement = (
        select(Problem)
        .join(WrongAnswer, WrongAnswer.problem_id == Problem.id)
        .options(selectinload(Problem.topic), selectinload(Problem.source_note))
        .where(Problem.card_id == card_id)
    )
    if problem_id is None:
        statement = statement.where(WrongAnswer.status != WrongAnswerStatus.RESOLVED.value)
    else:
        statement = statement.where(Problem.id == problem_id)

    eligible_problems = list(db.scalars(statement).all())
    selected_problems = choose_weighted_problems(eligible_problems, limit)
    if not selected_problems:
        return {"session_id": None, "problems": []}

    session_id = str(uuid4())
    for problem in selected_problems:
        problem.presented_count += 1
    db.add(
        StudySession(
            id=session_id,
            card_id=card_id,
            problem_ids=[problem.id for problem in selected_problems],
        )
    )
    db.commit()
    return {"session_id": session_id, "problems": selected_problems}


@router.patch("/{problem_id}", response_model=WrongAnswerRead)
def update_wrong_answer(
    card_id: int,
    problem_id: int,
    payload: WrongAnswerUpdate,
    db: DatabaseSession,
) -> WrongAnswer:
    wrong_answer = get_wrong_answer_or_404(card_id, problem_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(wrong_answer, field, value.value if isinstance(value, WrongAnswerStatus) else value)
    db.commit()
    db.refresh(wrong_answer)
    return wrong_answer
