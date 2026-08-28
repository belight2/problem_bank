import type { Concept, Note, Problem, Topic, Workbook, WrongAnswer } from "../types";

interface CardDashboardProps {
  topics: Topic[];
  concepts: Concept[];
  problems: Problem[];
  notes: Note[];
  workbooks: Workbook[];
  wrongAnswers: WrongAnswer[];
  loading: boolean;
  loaded: boolean;
  onCreateProblem: () => void;
  onCreateNote: () => void;
  onCreateWorkbook: () => void;
  onOpenProblems: () => void;
  onOpenWorkbooks: () => void;
  onOpenWrongAnswers: () => void;
}

const dashboardDateFormatter = new Intl.DateTimeFormat("ko-KR", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function accuracy(correctCount: number, incorrectCount: number) {
  const gradedCount = correctCount + incorrectCount;
  return gradedCount === 0 ? null : Math.round(correctCount * 100 / gradedCount);
}

export function CardDashboard({
  topics,
  concepts,
  problems,
  notes,
  workbooks,
  wrongAnswers,
  loading,
  loaded,
  onCreateProblem,
  onCreateNote,
  onCreateWorkbook,
  onOpenProblems,
  onOpenWorkbooks,
  onOpenWrongAnswers,
}: CardDashboardProps) {
  if (loading) {
    return (
      <div className="card-dashboard-skeleton" aria-label="카드 대시보드 불러오는 중">
        <div />
        <div />
        <div />
      </div>
    );
  }

  if (!loaded) {
    return (
      <div className="empty-state empty-state--compact">
        <span className="empty-index" aria-hidden="true">!</span>
        <h3>카드 현황을 불러오지 못했어요</h3>
      </div>
    );
  }

  const correctCount = problems.reduce((sum, problem) => sum + problem.correct_count, 0);
  const incorrectCount = problems.reduce((sum, problem) => sum + problem.incorrect_count, 0);
  const accuracyRate = accuracy(correctCount, incorrectCount);
  const completedAttempts = workbooks.reduce(
    (sum, workbook) => sum
      + workbook.attempts.filter((attempt) => attempt.status === "completed").length,
    0,
  );
  const unresolvedWrongAnswers = wrongAnswers.filter(
    (wrongAnswer) => wrongAnswer.status !== "resolved",
  ).length;
  const topicSummaries = topics.map((topic) => {
    const topicProblems = problems.filter((problem) => problem.topic_id === topic.id);
    const topicCorrect = topicProblems.reduce(
      (sum, problem) => sum + problem.correct_count,
      0,
    );
    const topicIncorrect = topicProblems.reduce(
      (sum, problem) => sum + problem.incorrect_count,
      0,
    );
    return {
      id: topic.id,
      name: topic.name,
      problemCount: topicProblems.length,
      gradedCount: topicCorrect + topicIncorrect,
      accuracyRate: accuracy(topicCorrect, topicIncorrect),
    };
  }).sort((first, second) => second.gradedCount - first.gradedCount);

  return (
    <div className="card-dashboard">
      <div className="card-dashboard-actions" aria-label="카드 빠른 작업">
        <button className="button button--primary" type="button" onClick={onCreateWorkbook}>
          새 문제집
        </button>
        <button className="button button--ghost" type="button" onClick={onCreateProblem}>
          새 문제
        </button>
        <button className="button button--ghost" type="button" onClick={onCreateNote}>
          새 노트
        </button>
      </div>

      <section className="card-dashboard-stat-grid" aria-label="카드 학습 현황">
        <article>
          <span>정답률</span>
          <strong>{accuracyRate === null ? "-" : `${accuracyRate}%`}</strong>
          <small>정답 {correctCount} · 오답 {incorrectCount}</small>
        </article>
        <article>
          <span>완료한 풀이</span>
          <strong>{completedAttempts}</strong>
          <small>문제집 {workbooks.length}개</small>
        </article>
        <article>
          <span>복습할 오답</span>
          <strong>{unresolvedWrongAnswers}</strong>
          <button type="button" onClick={onOpenWrongAnswers}>오답노트 보기</button>
        </article>
        <article>
          <span>학습 자료</span>
          <strong>{problems.length}</strong>
          <small>주제 {topics.length} · 개념 {concepts.length} · 노트 {notes.length}</small>
        </article>
      </section>

      <div className="card-dashboard-main-grid">
        <section className="card-dashboard-panel">
          <div className="card-dashboard-panel-heading">
            <div>
              <p className="eyebrow">Recent problem books</p>
              <h2>최근 문제집</h2>
            </div>
            <button type="button" onClick={onOpenWorkbooks}>전체 보기</button>
          </div>
          {workbooks.length > 0 ? (
            <div className="card-dashboard-workbooks">
              {workbooks.slice(0, 4).map((workbook) => {
                const latestAttempt = workbook.attempts[0];
                const gradedCount = latestAttempt
                  ? latestAttempt.correct_count + latestAttempt.incorrect_count
                  : 0;
                return (
                  <button type="button" key={workbook.id} onClick={onOpenWorkbooks}>
                    <span>
                      <strong>{workbook.title}</strong>
                      <small>
                        {dashboardDateFormatter.format(new Date(workbook.created_at))}
                      </small>
                    </span>
                    <span>
                      <strong>{workbook.problem_count}문제</strong>
                      <small>
                        {latestAttempt?.status === "completed"
                          ? `${latestAttempt.correct_count} / ${gradedCount}`
                          : "미완료"}
                      </small>
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="card-dashboard-panel-empty">
              <span>문제집 없음</span>
            </div>
          )}
        </section>

        <section className="card-dashboard-panel">
          <div className="card-dashboard-panel-heading">
            <div>
              <p className="eyebrow">Topic progress</p>
              <h2>주제별 현황</h2>
            </div>
            <button type="button" onClick={onOpenProblems}>문제 보기</button>
          </div>
          {topicSummaries.length > 0 ? (
            <div className="card-topic-progress-list">
              {topicSummaries.map((topic) => (
                <div key={topic.id}>
                  <div>
                    <strong>{topic.name}</strong>
                    <span>
                      {topic.accuracyRate === null ? "기록 없음" : `${topic.accuracyRate}%`}
                    </span>
                  </div>
                  <div className="card-topic-progress-track" aria-hidden="true">
                    <span style={{ width: `${topic.accuracyRate ?? 0}%` }} />
                  </div>
                  <small>문제 {topic.problemCount} · 채점 {topic.gradedCount}회</small>
                </div>
              ))}
            </div>
          ) : (
            <div className="card-dashboard-panel-empty">
              <span>등록된 주제 없음</span>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
