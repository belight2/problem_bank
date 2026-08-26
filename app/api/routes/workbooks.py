from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import DatabaseSession
from app.api.routes.problems import (
    choose_weighted_problems,
    ensure_card_exists,
    record_study_results,
)
from app.models.problem import Problem
from app.models.random_study_preset import RandomStudyPreset
from app.models.study_session import StudySession
from app.models.topic import Topic
from app.models.workbook import Workbook
from app.schemas.problem import StudyResultsRead, StudyResultsWrite
from app.schemas.workbook import (
    WorkbookAttemptRead,
    WorkbookCreate,
    WorkbookRead,
    WorkbookRegenerate,
    WorkbookStudyRead,
    WorkbookUpdate,
)

router = APIRouter(prefix="/cards/{card_id}/workbooks", tags=["workbooks"])


def workbook_load_options() -> tuple:
    return (
        selectinload(Workbook.topic),
        selectinload(Workbook.preset),
        selectinload(Workbook.attempts),
    )


def get_workbook_or_404(card_id: int, workbook_id: int, db: Session) -> Workbook:
    workbook = db.scalar(
        select(Workbook)
        .options(*workbook_load_options())
        .where(Workbook.id == workbook_id, Workbook.card_id == card_id)
    )
    if workbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workbook not found",
        )
    return workbook


def serialize_attempt(attempt: StudySession) -> WorkbookAttemptRead:
    return WorkbookAttemptRead(
        id=attempt.id,
        attempt_number=attempt.attempt_number,
        status="completed" if attempt.completed_at is not None else "in_progress",
        correct_count=attempt.result_count("correct"),
        incorrect_count=attempt.result_count("incorrect"),
        ungraded_count=attempt.result_count("ungraded"),
        created_at=attempt.created_at,
        completed_at=attempt.completed_at,
    )


def serialize_workbook(workbook: Workbook) -> WorkbookRead:
    attempts = sorted(workbook.attempts, key=lambda item: item.attempt_number, reverse=True)
    return WorkbookRead(
        id=workbook.id,
        card_id=workbook.card_id,
        title=workbook.title,
        topic_id=workbook.topic_id,
        topic_name=workbook.topic_name,
        preset_id=workbook.preset_id,
        preset_name=workbook.preset_name,
        problem_count=workbook.problem_count,
        requested_problem_count=workbook.requested_problem_count,
        selection_mode=workbook.selection_mode,
        incorrect_rate_threshold=workbook.incorrect_rate_threshold,
        minimum_attempt_count=workbook.minimum_attempt_count,
        incorrect_count_threshold=workbook.incorrect_count_threshold,
        attempts=[serialize_attempt(attempt) for attempt in attempts],
        created_at=workbook.created_at,
        updated_at=workbook.updated_at,
    )


def validate_workbook_references(card_id: int, payload: WorkbookCreate, db: Session) -> None:
    if payload.topic_id is not None:
        topic = db.scalar(
            select(Topic.id).where(Topic.id == payload.topic_id, Topic.card_id == card_id)
        )
        if topic is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    if payload.preset_id is not None:
        preset = db.scalar(
            select(RandomStudyPreset.id).where(
                RandomStudyPreset.id == payload.preset_id,
                RandomStudyPreset.card_id == card_id,
            )
        )
        if preset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem book preset not found",
            )


def select_workbook_problems(
    card_id: int,
    payload: WorkbookCreate,
    db: Session,
) -> list[Problem]:
    statement = (
        select(Problem)
        .options(selectinload(Problem.topic), selectinload(Problem.source_note))
        .where(Problem.card_id == card_id)
    )
    if payload.topic_id is not None:
        statement = statement.where(Problem.topic_id == payload.topic_id)
    if payload.selection_mode == "incorrect_rate":
        graded_count = Problem.correct_count + Problem.incorrect_count
        statement = statement.where(
            graded_count >= payload.minimum_attempt_count,
            Problem.incorrect_count * 100
            >= graded_count * payload.incorrect_rate_threshold,
        )
    elif payload.selection_mode == "incorrect_count":
        statement = statement.where(
            Problem.incorrect_count >= payload.incorrect_count_threshold
        )
    return choose_weighted_problems(
        list(db.scalars(statement).all()),
        payload.problem_count,
    )


def create_attempt(workbook: Workbook, db: Session) -> tuple[StudySession, list[Problem]]:
    problems = list(
        db.scalars(
            select(Problem)
            .options(selectinload(Problem.topic), selectinload(Problem.source_note))
            .where(
                Problem.card_id == workbook.card_id,
                Problem.id.in_(workbook.problem_ids),
            )
        ).all()
    )
    problems_by_id = {problem.id: problem for problem in problems}
    if len(problems_by_id) != len(workbook.problem_ids):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="문제집에 포함된 문제 중 삭제된 문제가 있습니다.",
        )
    ordered_problems = [problems_by_id[problem_id] for problem_id in workbook.problem_ids]
    last_attempt_number = db.scalar(
        select(func.max(StudySession.attempt_number)).where(
            StudySession.workbook_id == workbook.id
        )
    )
    attempt = StudySession(
        id=str(uuid4()),
        card_id=workbook.card_id,
        workbook_id=workbook.id,
        attempt_number=(last_attempt_number or 0) + 1,
        problem_ids=workbook.problem_ids,
    )
    for problem in ordered_problems:
        problem.presented_count += 1
    workbook.attempts.append(attempt)
    return attempt, ordered_problems


def create_workbook_record(
    card_id: int,
    payload: WorkbookCreate,
    db: Session,
) -> tuple[Workbook, StudySession, list[Problem]]:
    validate_workbook_references(card_id, payload, db)
    selected_problems = select_workbook_problems(card_id, payload, db)
    if not selected_problems:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="설정한 출제 기준에 맞는 문제가 없습니다.",
        )
    workbook = Workbook(
        card_id=card_id,
        title=payload.title or f"{datetime.now().strftime('%Y-%m-%d')} 문제집",
        topic_id=payload.topic_id,
        preset_id=payload.preset_id,
        problem_ids=[problem.id for problem in selected_problems],
        requested_problem_count=payload.problem_count,
        selection_mode=payload.selection_mode,
        incorrect_rate_threshold=payload.incorrect_rate_threshold,
        minimum_attempt_count=payload.minimum_attempt_count,
        incorrect_count_threshold=payload.incorrect_count_threshold,
    )
    db.add(workbook)
    db.flush()
    attempt, ordered_problems = create_attempt(workbook, db)
    db.commit()
    return workbook, attempt, ordered_problems


def study_response(
    card_id: int,
    workbook_id: int,
    session_id: str,
    problems: list[Problem],
    db: Session,
) -> WorkbookStudyRead:
    workbook = get_workbook_or_404(card_id, workbook_id, db)
    return WorkbookStudyRead(
        workbook=serialize_workbook(workbook),
        session_id=session_id,
        problems=problems,
    )


@router.get("", response_model=list[WorkbookRead])
def list_workbooks(
    card_id: int,
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[WorkbookRead]:
    ensure_card_exists(card_id, db)
    workbooks = db.scalars(
        select(Workbook)
        .options(*workbook_load_options())
        .where(Workbook.card_id == card_id)
        .order_by(Workbook.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [serialize_workbook(workbook) for workbook in workbooks]


@router.post("", response_model=WorkbookStudyRead, status_code=status.HTTP_201_CREATED)
def create_workbook(
    card_id: int,
    payload: WorkbookCreate,
    db: DatabaseSession,
) -> WorkbookStudyRead:
    ensure_card_exists(card_id, db)
    workbook, attempt, problems = create_workbook_record(card_id, payload, db)
    return study_response(card_id, workbook.id, attempt.id, problems, db)


@router.get("/{workbook_id}", response_model=WorkbookRead)
def get_workbook(
    card_id: int,
    workbook_id: int,
    db: DatabaseSession,
) -> WorkbookRead:
    return serialize_workbook(get_workbook_or_404(card_id, workbook_id, db))


@router.patch("/{workbook_id}", response_model=WorkbookRead)
def update_workbook(
    card_id: int,
    workbook_id: int,
    payload: WorkbookUpdate,
    db: DatabaseSession,
) -> WorkbookRead:
    workbook = get_workbook_or_404(card_id, workbook_id, db)
    workbook.title = payload.title
    db.commit()
    return serialize_workbook(get_workbook_or_404(card_id, workbook_id, db))


@router.delete("/{workbook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workbook(
    card_id: int,
    workbook_id: int,
    db: DatabaseSession,
) -> Response:
    workbook = get_workbook_or_404(card_id, workbook_id, db)
    db.delete(workbook)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{workbook_id}/attempts", response_model=WorkbookStudyRead)
def start_workbook_attempt(
    card_id: int,
    workbook_id: int,
    db: DatabaseSession,
) -> WorkbookStudyRead:
    workbook = get_workbook_or_404(card_id, workbook_id, db)
    attempt, problems = create_attempt(workbook, db)
    db.commit()
    return study_response(card_id, workbook.id, attempt.id, problems, db)


@router.post(
    "/{workbook_id}/attempts/{session_id}/results",
    response_model=StudyResultsRead,
)
def record_workbook_results(
    card_id: int,
    workbook_id: int,
    session_id: str,
    payload: StudyResultsWrite,
    db: DatabaseSession,
) -> dict[str, str | list[Problem]]:
    get_workbook_or_404(card_id, workbook_id, db)
    attempt = db.scalar(
        select(StudySession.id).where(
            StudySession.id == session_id,
            StudySession.card_id == card_id,
            StudySession.workbook_id == workbook_id,
        )
    )
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workbook attempt not found",
        )
    return record_study_results(card_id, session_id, payload, db)


@router.post(
    "/{workbook_id}/regenerate",
    response_model=WorkbookStudyRead,
    status_code=status.HTTP_201_CREATED,
)
def regenerate_workbook(
    card_id: int,
    workbook_id: int,
    payload: WorkbookRegenerate,
    db: DatabaseSession,
) -> WorkbookStudyRead:
    source = get_workbook_or_404(card_id, workbook_id, db)
    create_payload = WorkbookCreate(
        title=payload.title or f"{source.title} · 새 문제집",
        topic_id=source.topic_id,
        preset_id=source.preset_id,
        problem_count=source.requested_problem_count,
        selection_mode=source.selection_mode,
        incorrect_rate_threshold=source.incorrect_rate_threshold,
        minimum_attempt_count=source.minimum_attempt_count,
        incorrect_count_threshold=source.incorrect_count_threshold,
    )
    workbook, attempt, problems = create_workbook_record(card_id, create_payload, db)
    return study_response(card_id, workbook.id, attempt.id, problems, db)
