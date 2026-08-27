import random
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import DatabaseSession
from app.models.card import Card
from app.models.graph_outbox import GraphOutboxEventType
from app.models.note import Note
from app.models.problem import Problem
from app.models.study_session import StudySession
from app.models.topic import Topic
from app.models.wrong_answer import WrongAnswer, WrongAnswerStatus
from app.schemas.problem import (
    ProblemCreate,
    ProblemRead,
    ProblemUpdate,
    RandomProblemSetRead,
    StudyResultsRead,
    StudyResultsWrite,
)
from app.services.concepts import set_problem_concepts
from app.services.graph_outbox import enqueue_problem_event

router = APIRouter(prefix="/cards/{card_id}/problems", tags=["problems"])


def ensure_card_exists(card_id: int, db: Session) -> None:
    if db.get(Card, card_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")


def get_problem_or_404(card_id: int, problem_id: int, db: Session) -> Problem:
    statement = (
        select(Problem)
        .options(
            selectinload(Problem.topic),
            selectinload(Problem.source_note),
            selectinload(Problem.concept_links),
        )
        .where(
            Problem.id == problem_id,
            Problem.card_id == card_id,
        )
    )
    problem = db.scalar(statement)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    return problem


def get_topic_for_card_or_404(card_id: int, topic_id: int, db: Session) -> Topic:
    statement = select(Topic).where(Topic.id == topic_id, Topic.card_id == card_id)
    topic = db.scalar(statement)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    return topic


def get_optional_source_note(
    card_id: int,
    source_note_id: int | None,
    db: Session,
) -> Note | None:
    if source_note_id is None:
        return None
    note = db.scalar(select(Note).where(Note.id == source_note_id, Note.card_id == card_id))
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


def calculate_problem_weight(problem: Problem) -> float:
    graded_count = problem.correct_count + problem.incorrect_count
    mistake_rate = (problem.incorrect_count + 1) / (graded_count + 2)
    exposure_bonus = 2 / (problem.presented_count + 1)
    return 1 + (6 * mistake_rate) + exposure_bonus


def choose_weighted_problems(problems: list[Problem], limit: int) -> list[Problem]:
    pool = list(problems)
    selected: list[Problem] = []
    while pool and len(selected) < limit:
        weights = [calculate_problem_weight(problem) for problem in pool]
        chosen = random.choices(pool, weights=weights, k=1)[0]
        selected.append(chosen)
        pool.remove(chosen)
    return selected


@router.post("", response_model=ProblemRead, status_code=status.HTTP_201_CREATED)
def create_problem(card_id: int, payload: ProblemCreate, db: DatabaseSession) -> Problem:
    ensure_card_exists(card_id, db)
    topic = get_topic_for_card_or_404(card_id, payload.topic_id, db)
    source_note = get_optional_source_note(card_id, payload.source_note_id, db)
    problem = Problem(
        card_id=card_id,
        topic=topic,
        source_note=source_note,
        **payload.model_dump(
            exclude={
                "source_note_id",
                "primary_concept_id",
                "supporting_concept_ids",
            }
        ),
    )
    db.add(problem)
    db.flush()
    set_problem_concepts(
        db,
        problem,
        primary_concept_id=payload.primary_concept_id,
        supporting_concept_ids=payload.supporting_concept_ids,
    )
    db.flush()
    enqueue_problem_event(db, problem)
    db.commit()
    db.refresh(problem)
    return problem


@router.get("", response_model=list[ProblemRead])
def list_problems(
    card_id: int,
    db: DatabaseSession,
    topic_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Problem]:
    ensure_card_exists(card_id, db)
    statement = (
        select(Problem)
        .options(
            selectinload(Problem.topic),
            selectinload(Problem.source_note),
            selectinload(Problem.concept_links),
        )
        .where(Problem.card_id == card_id)
    )
    if topic_id is not None:
        statement = statement.where(Problem.topic_id == topic_id)

    statement = statement.order_by(Problem.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(statement).all())


@router.post("/random", response_model=RandomProblemSetRead)
def get_random_problems(
    card_id: int,
    db: DatabaseSession,
    topic_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 1,
    selection_mode: Literal["all", "incorrect_rate", "incorrect_count"] = "all",
    incorrect_rate_threshold: Annotated[int, Query(ge=1, le=100)] = 50,
    minimum_attempt_count: Annotated[int, Query(ge=1)] = 3,
    incorrect_count_threshold: Annotated[int, Query(ge=1)] = 1,
) -> dict[str, str | None | list[Problem]]:
    ensure_card_exists(card_id, db)
    statement = (
        select(Problem)
        .options(
            selectinload(Problem.topic),
            selectinload(Problem.source_note),
            selectinload(Problem.concept_links),
        )
        .where(Problem.card_id == card_id)
    )
    if topic_id is not None:
        statement = statement.where(Problem.topic_id == topic_id)

    if selection_mode == "incorrect_rate":
        graded_count = Problem.correct_count + Problem.incorrect_count
        statement = statement.where(
            graded_count >= minimum_attempt_count,
            Problem.incorrect_count * 100 >= graded_count * incorrect_rate_threshold,
        )
    elif selection_mode == "incorrect_count":
        statement = statement.where(Problem.incorrect_count >= incorrect_count_threshold)

    eligible_problems = list(db.scalars(statement).all())
    selected_problems = choose_weighted_problems(eligible_problems, limit)
    if not selected_problems:
        return {"session_id": None, "problems": []}

    session_id = str(uuid4())
    for problem in selected_problems:
        problem.presented_count += 1
        enqueue_problem_event(db, problem)
    db.add(
        StudySession(
            id=session_id,
            card_id=card_id,
            problem_ids=[problem.id for problem in selected_problems],
        )
    )
    db.commit()
    return {"session_id": session_id, "problems": selected_problems}


@router.post("/random/{session_id}/results", response_model=StudyResultsRead)
def record_study_results(
    card_id: int,
    session_id: str,
    payload: StudyResultsWrite,
    db: DatabaseSession,
) -> dict[str, str | list[Problem]]:
    ensure_card_exists(card_id, db)
    session = db.scalar(
        select(StudySession)
        .where(
            StudySession.id == session_id,
            StudySession.card_id == card_id,
        )
        .with_for_update()
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    submitted_problem_ids = {result.problem_id for result in payload.results}
    expected_problem_ids = set(session.problem_ids)
    if submitted_problem_ids != expected_problem_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Results must include every problem in the study session",
        )

    problems = list(
        db.scalars(
            select(Problem)
            .options(
                selectinload(Problem.topic),
                selectinload(Problem.source_note),
                selectinload(Problem.concept_links),
            )
            .where(
                Problem.card_id == card_id,
                Problem.id.in_(expected_problem_ids),
            )
        ).all()
    )
    if len(problems) != len(expected_problem_ids):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A problem in the study session no longer exists",
        )
    if session.completed_at is not None:
        return {"status": "already_recorded", "problems": problems}

    result_by_problem_id = {result.problem_id: result.result for result in payload.results}
    submitted_answer_by_problem_id = {
        result.problem_id: result.submitted_answer for result in payload.results
    }
    wrong_answers_by_problem_id = {
        wrong_answer.problem_id: wrong_answer
        for wrong_answer in db.scalars(
            select(WrongAnswer)
            .where(
                WrongAnswer.card_id == card_id,
                WrongAnswer.problem_id.in_(expected_problem_ids),
            )
            .with_for_update()
        ).all()
    }
    completed_at = datetime.now(UTC)
    for problem in problems:
        result = result_by_problem_id[problem.id]
        statistics_changed = False
        if result == "correct":
            problem.correct_count += 1
            statistics_changed = True
        elif result == "incorrect":
            problem.incorrect_count += 1
            statistics_changed = True
            wrong_answer = wrong_answers_by_problem_id.get(problem.id)
            if wrong_answer is None:
                wrong_answer = WrongAnswer(
                    card_id=card_id,
                    problem_id=problem.id,
                )
                db.add(wrong_answer)
            wrong_answer.status = WrongAnswerStatus.NEEDS_REVIEW.value
            wrong_answer.last_submitted_answer = submitted_answer_by_problem_id[problem.id]
            wrong_answer.last_incorrect_at = completed_at
        if statistics_changed:
            enqueue_problem_event(db, problem)

    session.results = [result.model_dump() for result in payload.results]
    session.completed_at = completed_at
    db.commit()
    return {"status": "recorded", "problems": problems}


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
    changes = payload.model_dump(exclude_unset=True)
    try:
        final_state = ProblemCreate.model_validate(
            {
                "topic_id": problem.topic_id,
                "question": problem.question,
                "problem_type": problem.problem_type,
                "choices": problem.choices,
                "answer": problem.answer,
                "source_note_id": problem.source_note_id,
                "primary_concept_id": problem.primary_concept_id,
                "supporting_concept_ids": problem.supporting_concept_ids,
            }
            | changes
        )
    except ValidationError as error:
        validation_errors = [
            {**validation_error, "loc": ("body", *validation_error["loc"])}
            for validation_error in error.errors()
        ]
        raise RequestValidationError(validation_errors) from error

    topic = get_topic_for_card_or_404(card_id, final_state.topic_id, db)
    source_note = get_optional_source_note(card_id, final_state.source_note_id, db)
    for field, value in final_state.model_dump(
        exclude={
            "source_note_id",
            "primary_concept_id",
            "supporting_concept_ids",
        }
    ).items():
        setattr(problem, field, value)
    problem.topic = topic
    problem.source_note = source_note
    set_problem_concepts(
        db,
        problem,
        primary_concept_id=final_state.primary_concept_id,
        supporting_concept_ids=final_state.supporting_concept_ids,
    )

    db.flush()
    enqueue_problem_event(db, problem)
    db.commit()
    db.refresh(problem)
    return problem


@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem(card_id: int, problem_id: int, db: DatabaseSession) -> Response:
    problem = get_problem_or_404(card_id, problem_id, db)
    enqueue_problem_event(db, problem, GraphOutboxEventType.DELETE)
    db.delete(problem)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
