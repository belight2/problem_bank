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


class WeakConceptRead(BaseModel):
    concept_id: int
    name: str
    # 그래프 히트맵과 동일한 라플라스 스무딩 숙련도(0~1).
    # 프론트는 색·%를 이 값으로 계산해 그래프와 일치시킨다.
    mastery_score: float
    correct_count: int
    incorrect_count: int
    graded_count: int
    problem_count: int


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
    weak_concepts: list[WeakConceptRead]
    cards: list[DashboardCardRead]
    recent_studies: list[RecentStudyRead]
