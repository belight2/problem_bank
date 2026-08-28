from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.dependencies import CurrentProfile, DatabaseSession
from app.models.card import Card
from app.models.concept import Concept
from app.models.note import Note
from app.models.problem import Problem
from app.models.study_session import StudySession
from app.models.topic import Topic
from app.models.workbook import Workbook
from app.models.wrong_answer import WrongAnswer, WrongAnswerStatus
from app.schemas.dashboard import (
    DashboardCardRead,
    DashboardRead,
    RecentStudyRead,
    WeakConceptRead,
    WeakTopicRead,
)
from app.services.concept_mastery import compute_concept_mastery

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def scalar_count(db: DatabaseSession, statement) -> int:
    return int(db.scalar(statement) or 0)


@router.get("", response_model=DashboardRead)
def get_dashboard(profile: CurrentProfile, db: DatabaseSession) -> DashboardRead:
    profile_cards = Card.profile_id == profile.id
    card_count = scalar_count(db, select(func.count(Card.id)).where(profile_cards))
    topic_count = scalar_count(
        db,
        select(func.count(Topic.id)).join(Card).where(profile_cards),
    )
    note_count = scalar_count(
        db,
        select(func.count(Note.id)).join(Card).where(profile_cards),
    )
    workbook_count = scalar_count(
        db,
        select(func.count(Workbook.id)).join(Card).where(profile_cards),
    )
    completed_session_count = scalar_count(
        db,
        select(func.count(StudySession.id))
        .join(Card)
        .where(profile_cards, StudySession.completed_at.is_not(None)),
    )
    unresolved_wrong_answer_count = scalar_count(
        db,
        select(func.count(WrongAnswer.id))
        .join(Card)
        .where(
            profile_cards,
            WrongAnswer.status != WrongAnswerStatus.RESOLVED.value,
        ),
    )

    problem_summary = db.execute(
        select(
            func.count(Problem.id),
            func.coalesce(func.sum(Problem.correct_count), 0),
            func.coalesce(func.sum(Problem.incorrect_count), 0),
        )
        .join(Card)
        .where(profile_cards)
    ).one()
    problem_count = int(problem_summary[0])
    correct_count = int(problem_summary[1])
    incorrect_count = int(problem_summary[2])
    graded_count = correct_count + incorrect_count
    accuracy_rate = round(correct_count * 100 / graded_count) if graded_count else 0

    local_timezone = ZoneInfo(profile.timezone)
    today = datetime.now(local_timezone).date()
    local_start = datetime.combine(today, time.min, tzinfo=local_timezone)
    utc_start = local_start.astimezone(UTC)
    utc_end = (local_start + timedelta(days=1)).astimezone(UTC)
    today_sessions = db.scalars(
        select(StudySession)
        .join(Card)
        .where(
            profile_cards,
            StudySession.completed_at >= utc_start,
            StudySession.completed_at < utc_end,
        )
    ).all()
    today_studied_count = sum(len(session.results or []) for session in today_sessions)

    topic_rows = db.execute(
        select(
            Card.id,
            Card.title,
            Topic.id,
            Topic.name,
            func.count(Problem.id),
            func.coalesce(func.sum(Problem.correct_count), 0),
            func.coalesce(func.sum(Problem.incorrect_count), 0),
        )
        .join(Topic, Topic.card_id == Card.id)
        .join(Problem, Problem.topic_id == Topic.id)
        .where(profile_cards)
        .group_by(Card.id, Card.title, Topic.id, Topic.name)
    ).all()
    weak_topics: list[WeakTopicRead] = []
    for row in topic_rows:
        topic_correct = int(row[5])
        topic_incorrect = int(row[6])
        topic_graded = topic_correct + topic_incorrect
        if topic_graded == 0:
            continue
        weak_topics.append(
            WeakTopicRead(
                card_id=int(row[0]),
                card_title=str(row[1]),
                topic_id=int(row[2]),
                topic_name=str(row[3]),
                problem_count=int(row[4]),
                graded_count=topic_graded,
                accuracy_rate=round(topic_correct * 100 / topic_graded),
            )
        )
    weak_topics.sort(key=lambda item: (item.accuracy_rate, -item.graded_count))

    concept_rows = db.execute(
        select(Concept.id, Concept.name).where(Concept.profile_id == profile.id)
    ).all()
    concept_names = {int(row[0]): str(row[1]) for row in concept_rows}
    weak_concepts: list[WeakConceptRead] = [
        WeakConceptRead(
            concept_id=mastery.concept_id,
            name=concept_names.get(mastery.concept_id, ""),
            mastery_score=mastery.mastery_score,
            correct_count=mastery.correct_count,
            incorrect_count=mastery.incorrect_count,
            graded_count=mastery.graded_count,
            problem_count=mastery.problem_count,
        )
        for mastery in compute_concept_mastery(db, concept_names.keys()).values()
        if mastery.attempted and mastery.mastery_score is not None
    ]
    weak_concepts.sort(
        key=lambda item: (item.mastery_score, -item.graded_count, item.concept_id)
    )

    problem_by_card = (
        select(
            Problem.card_id.label("card_id"),
            func.count(Problem.id).label("problem_count"),
            func.coalesce(func.sum(Problem.correct_count), 0).label("correct_count"),
            func.coalesce(func.sum(Problem.incorrect_count), 0).label("incorrect_count"),
        )
        .group_by(Problem.card_id)
        .subquery()
    )
    note_by_card = (
        select(Note.card_id.label("card_id"), func.count(Note.id).label("note_count"))
        .group_by(Note.card_id)
        .subquery()
    )
    workbook_by_card = (
        select(
            Workbook.card_id.label("card_id"),
            func.count(Workbook.id).label("workbook_count"),
        )
        .group_by(Workbook.card_id)
        .subquery()
    )
    completed_by_card = (
        select(
            StudySession.card_id.label("card_id"),
            func.count(StudySession.id).label("completed_session_count"),
        )
        .where(StudySession.completed_at.is_not(None))
        .group_by(StudySession.card_id)
        .subquery()
    )
    wrong_by_card = (
        select(
            WrongAnswer.card_id.label("card_id"),
            func.count(WrongAnswer.id).label("wrong_answer_count"),
        )
        .where(WrongAnswer.status != WrongAnswerStatus.RESOLVED.value)
        .group_by(WrongAnswer.card_id)
        .subquery()
    )
    card_rows = db.execute(
        select(
            Card.id,
            Card.title,
            func.coalesce(problem_by_card.c.problem_count, 0),
            func.coalesce(note_by_card.c.note_count, 0),
            func.coalesce(workbook_by_card.c.workbook_count, 0),
            func.coalesce(completed_by_card.c.completed_session_count, 0),
            func.coalesce(problem_by_card.c.correct_count, 0),
            func.coalesce(problem_by_card.c.incorrect_count, 0),
            func.coalesce(wrong_by_card.c.wrong_answer_count, 0),
        )
        .outerjoin(problem_by_card, problem_by_card.c.card_id == Card.id)
        .outerjoin(note_by_card, note_by_card.c.card_id == Card.id)
        .outerjoin(workbook_by_card, workbook_by_card.c.card_id == Card.id)
        .outerjoin(completed_by_card, completed_by_card.c.card_id == Card.id)
        .outerjoin(wrong_by_card, wrong_by_card.c.card_id == Card.id)
        .where(profile_cards)
        .order_by(Card.updated_at.desc(), Card.id.desc())
    ).all()
    dashboard_cards: list[DashboardCardRead] = []
    for row in card_rows:
        card_correct = int(row[6])
        card_incorrect = int(row[7])
        card_graded = card_correct + card_incorrect
        dashboard_cards.append(
            DashboardCardRead(
                card_id=int(row[0]),
                card_title=str(row[1]),
                problem_count=int(row[2]),
                note_count=int(row[3]),
                workbook_count=int(row[4]),
                completed_session_count=int(row[5]),
                correct_count=card_correct,
                incorrect_count=card_incorrect,
                accuracy_rate=round(card_correct * 100 / card_graded) if card_graded else 0,
                unresolved_wrong_answer_count=int(row[8]),
            )
        )

    recent_rows = db.execute(
        select(StudySession, Card.id, Card.title, Workbook.id, Workbook.title)
        .join(Card, Card.id == StudySession.card_id)
        .outerjoin(Workbook, Workbook.id == StudySession.workbook_id)
        .where(profile_cards, StudySession.completed_at.is_not(None))
        .order_by(StudySession.completed_at.desc())
        .limit(6)
    ).all()
    recent_studies = [
        RecentStudyRead(
            session_id=session.id,
            card_id=int(card_id),
            card_title=str(card_title),
            workbook_id=int(workbook_id) if workbook_id is not None else None,
            workbook_title=str(workbook_title) if workbook_title is not None else None,
            attempt_number=session.attempt_number,
            problem_count=len(session.problem_ids),
            correct_count=session.result_count("correct"),
            incorrect_count=session.result_count("incorrect"),
            ungraded_count=session.result_count("ungraded"),
            completed_at=session.completed_at,
        )
        for session, card_id, card_title, workbook_id, workbook_title in recent_rows
        if session.completed_at is not None
    ]

    return DashboardRead(
        profile=profile,
        card_count=card_count,
        topic_count=topic_count,
        problem_count=problem_count,
        note_count=note_count,
        workbook_count=workbook_count,
        completed_session_count=completed_session_count,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        accuracy_rate=accuracy_rate,
        unresolved_wrong_answer_count=unresolved_wrong_answer_count,
        today_studied_count=today_studied_count,
        weak_topics=weak_topics[:3],
        weak_concepts=weak_concepts[:5],
        cards=dashboard_cards,
        recent_studies=recent_studies,
    )
