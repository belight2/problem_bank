from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.dependencies import CurrentProfile, DatabaseSession
from app.models.card import Card
from app.models.note import Note
from app.models.problem import Problem
from app.models.study_session import StudySession
from app.models.topic import Topic
from app.models.workbook import Workbook
from app.models.wrong_answer import WrongAnswer, WrongAnswerStatus
from app.schemas.dashboard import DashboardRead, WeakTopicRead

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
    )
