from datetime import datetime

from pydantic import BaseModel

from app.schemas.profile import ProfileRead


class WeakTopicRead(BaseModel):
    card_id: int
    card_title: str
    topic_id: int
    topic_name: str
    problem_count: int
    graded_count: int
    accuracy_rate: int


class DashboardCardRead(BaseModel):
    card_id: int
    card_title: str
    problem_count: int
    note_count: int
    workbook_count: int
    completed_session_count: int
    correct_count: int
    incorrect_count: int
    accuracy_rate: int
    unresolved_wrong_answer_count: int


class RecentStudyRead(BaseModel):
    session_id: str
    card_id: int
    card_title: str
    workbook_id: int | None
    workbook_title: str | None
    attempt_number: int
    problem_count: int
    correct_count: int
    incorrect_count: int
    ungraded_count: int
    completed_at: datetime


class DashboardRead(BaseModel):
    profile: ProfileRead
    card_count: int
    topic_count: int
    problem_count: int
    note_count: int
    workbook_count: int
    completed_session_count: int
    correct_count: int
    incorrect_count: int
    accuracy_rate: int
    unresolved_wrong_answer_count: int
    today_studied_count: int
    weak_topics: list[WeakTopicRead]
    cards: list[DashboardCardRead]
    recent_studies: list[RecentStudyRead]
