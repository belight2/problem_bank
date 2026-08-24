from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import DatabaseSession
from app.models.card import Card
from app.models.problem import Problem
from app.schemas.problem import ProblemCreate, ProblemRead, ProblemUpdate

router = APIRouter(prefix="/cards/{card_id}/problems", tags=["problems"])


def ensure_card_exists(card_id: int, db: Session) -> None:
    if db.get(Card, card_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")


def get_problem_or_404(card_id: int, problem_id: int, db: Session) -> Problem:
    statement = select(Problem).where(
        Problem.id == problem_id,
        Problem.card_id == card_id,
    )
    problem = db.scalar(statement)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    return problem


@router.post("", response_model=ProblemRead, status_code=status.HTTP_201_CREATED)
def create_problem(card_id: int, payload: ProblemCreate, db: DatabaseSession) -> Problem:
    ensure_card_exists(card_id, db)
    problem = Problem(card_id=card_id, **payload.model_dump())
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


@router.get("", response_model=list[ProblemRead])
def list_problems(
    card_id: int,
    db: DatabaseSession,
    topic: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Problem]:
    ensure_card_exists(card_id, db)
    statement = select(Problem).where(Problem.card_id == card_id)
    if topic is not None:
        statement = statement.where(Problem.topic == topic.strip())

    statement = statement.order_by(Problem.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(statement).all())


@router.get("/random", response_model=list[ProblemRead])
def get_random_problems(
    card_id: int,
    db: DatabaseSession,
    topic: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 1,
) -> list[Problem]:
    ensure_card_exists(card_id, db)
    statement = select(Problem).where(Problem.card_id == card_id)
    if topic is not None:
        statement = statement.where(Problem.topic == topic.strip())

    statement = statement.order_by(func.random()).limit(limit)
    return list(db.scalars(statement).all())


@router.get("/{problem_id}", response_model=ProblemRead)
def get_problem(card_id: int, problem_id: int, db: DatabaseSession) -> Problem:
    return get_problem_or_404(card_id, problem_id, db)


@router.patch("/{problem_id}", response_model=ProblemRead)
def update_problem(
    card_id: int,
    problem_id: int,
    payload: ProblemUpdate,
    db: DatabaseSession,
) -> Problem:
    problem = get_problem_or_404(card_id, problem_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(problem, field, value)

    db.commit()
    db.refresh(problem)
    return problem


@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem(card_id: int, problem_id: int, db: DatabaseSession) -> Response:
    problem = get_problem_or_404(card_id, problem_id, db)
    db.delete(problem)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
