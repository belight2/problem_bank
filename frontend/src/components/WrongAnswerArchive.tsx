import { useState } from "react";

import { getErrorMessage } from "../api/client";
import { problemTypeLabels } from "../problemTypes";
import type {
  WrongAnswer,
  WrongAnswerInput,
  WrongAnswerStatus,
} from "../types";
import { ProblemOptions } from "./ProblemOptions";
import { ProblemPrompt } from "./ProblemPrompt";

interface WrongAnswerArchiveProps {
  wrongAnswers: WrongAnswer[];
  loading: boolean;
  loaded: boolean;
  onUpdate: (problemId: number, input: WrongAnswerInput) => Promise<void>;
  onStudy: (problemId?: number) => void;
  onOpenNote: (noteId: number) => void;
  onManageTopics: () => void;
}

type StatusFilter = "all" | WrongAnswerStatus;

const statusLabels: Record<WrongAnswerStatus, string> = {
  needs_review: "복습 필요",
  reviewing: "복습 중",
  resolved: "해결",
};

const wrongAnswerDateFormatter = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

function getIncorrectRate(wrongAnswer: WrongAnswer) {
  const gradedCount = wrongAnswer.problem.correct_count + wrongAnswer.problem.incorrect_count;
  if (gradedCount === 0) return 0;
  return Math.round((wrongAnswer.problem.incorrect_count / gradedCount) * 100);
}

export function WrongAnswerArchive({
  wrongAnswers,
  loading,
  loaded,
  onUpdate,
  onStudy,
  onOpenNote,
  onManageTopics,
}: WrongAnswerArchiveProps) {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [expandedProblemId, setExpandedProblemId] = useState<number | null>(
    wrongAnswers[0]?.problem_id ?? null,
  );
  const [memoDrafts, setMemoDrafts] = useState<Record<number, string>>({});
  const [savingProblemId, setSavingProblemId] = useState<number | null>(null);
  const [savedProblemId, setSavedProblemId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const visibleWrongAnswers = filter === "all"
    ? wrongAnswers
    : wrongAnswers.filter((wrongAnswer) => wrongAnswer.status === filter);

  const countByStatus = (status: WrongAnswerStatus) =>
    wrongAnswers.filter((wrongAnswer) => wrongAnswer.status === status).length;

  const updateEntry = async (problemId: number, input: WrongAnswerInput) => {
    setSavingProblemId(problemId);
    setSavedProblemId(null);
    setError(null);
    try {
      await onUpdate(problemId, input);
      setSavedProblemId(problemId);
    } catch (updateError) {
      setError(getErrorMessage(updateError));
    } finally {
      setSavingProblemId(null);
    }
  };

  return (
    <>
      <div className="problem-toolbar wrong-answer-toolbar">
        <div className="toolbar-actions">
          <button
            className="button button--ghost"
            type="button"
            onClick={onManageTopics}
            disabled={loading}
          >
            주제 관리
          </button>
          <button
            className="button button--primary"
            type="button"
            onClick={() => onStudy()}
            disabled={loading || wrongAnswers.every((item) => item.status === "resolved")}
          >
            오답 다시 풀기
          </button>
        </div>
      </div>

      <div className="section-heading content-section-heading wrong-answer-heading">
        <div>
          <p className="eyebrow">Wrong answer archive</p>
          <h2>오답노트</h2>
        </div>
        <span>{wrongAnswers.length}개</span>
      </div>

      {wrongAnswers.length > 0 && (
        <div className="wrong-answer-filters" aria-label="오답노트 상태 필터">
          {([
            ["all", "전체", wrongAnswers.length],
            ["needs_review", "복습 필요", countByStatus("needs_review")],
            ["reviewing", "복습 중", countByStatus("reviewing")],
            ["resolved", "해결", countByStatus("resolved")],
          ] as const).map(([value, label, count]) => (
            <button
              className={filter === value ? "is-active" : ""}
              type="button"
              key={value}
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
            >
              {label} <span>{count}</span>
            </button>
          ))}
        </div>
      )}

      {error && <p className="form-error wrong-answer-error" role="alert">{error}</p>}

      {loading ? (
        <div className="wrong-answer-list" aria-label="오답노트 불러오는 중">
          {[1, 2].map((item) => <div className="problem-skeleton" key={item} />)}
        </div>
      ) : !loaded ? (
        <div className="empty-state empty-state--compact">
          <span className="empty-index" aria-hidden="true">!</span>
          <h3>오답노트를 불러오지 못했어요</h3>
        </div>
      ) : wrongAnswers.length === 0 ? (
        <div className="empty-state">
          <span className="empty-index" aria-hidden="true">0</span>
          <h3>아직 기록된 오답이 없어요</h3>
        </div>
      ) : visibleWrongAnswers.length === 0 ? (
        <div className="empty-state empty-state--compact">
          <span className="empty-index" aria-hidden="true">0</span>
          <h3>이 상태의 오답이 없어요</h3>
        </div>
      ) : (
        <div className="wrong-answer-list">
          {visibleWrongAnswers.map((wrongAnswer) => {
            const { problem } = wrongAnswer;
            const expanded = expandedProblemId === problem.id;
            const memo = memoDrafts[problem.id] ?? wrongAnswer.memo ?? "";
            const saving = savingProblemId === problem.id;
            return (
              <article
                className={`wrong-answer-item${expanded ? " is-expanded" : ""}`}
                key={wrongAnswer.id}
              >
                <button
                  className="wrong-answer-summary"
                  type="button"
                  aria-expanded={expanded}
                  onClick={() => setExpandedProblemId(expanded ? null : problem.id)}
                >
                  <span className="wrong-answer-summary-content">
                    <span className="wrong-answer-meta">
                      <span className={`wrong-answer-status wrong-answer-status--${wrongAnswer.status}`}>
                        {statusLabels[wrongAnswer.status]}
                      </span>
                      <span className="topic-badge">{problem.topic_name}</span>
                      <span className="problem-type-badge">
                        {problemTypeLabels[problem.problem_type]}
                      </span>
                    </span>
                    <strong className="wrong-answer-question">
                      <ProblemPrompt problem={problem} />
                    </strong>
                  </span>
                  <span className="wrong-answer-statistics">
                    <span>출제 <strong>{problem.presented_count}</strong></span>
                    <span>오답 <strong>{problem.incorrect_count}</strong></span>
                    <span>오답률 <strong>{getIncorrectRate(wrongAnswer)}%</strong></span>
                  </span>
                </button>

                {expanded && (
                <div className="wrong-answer-detail">
                  <div className="wrong-answer-detail-inner">
                    <div className="wrong-answer-answer-grid">
                      <div className="wrong-answer-answer wrong-answer-answer--incorrect">
                        <span>최근 제출 답</span>
                        <strong>{wrongAnswer.last_submitted_answer || "기록 없음"}</strong>
                      </div>
                      <div className="wrong-answer-answer wrong-answer-answer--correct">
                        <span>정답 · 기준 답안</span>
                        <strong>{problem.answer || "등록된 답안 없음"}</strong>
                      </div>
                    </div>

                    <ProblemOptions problem={problem} />

                    <div className="wrong-answer-reference-row">
                      <span>
                        최근 오답 {wrongAnswerDateFormatter.format(
                          new Date(wrongAnswer.last_incorrect_at),
                        )}
                      </span>
                      {problem.source_note_id !== null && (
                        <button
                          type="button"
                          onClick={() => onOpenNote(problem.source_note_id as number)}
                        >
                          {problem.source_note_title ?? "관련 노트"} 보기
                        </button>
                      )}
                    </div>

                    <label className="wrong-answer-memo">
                      <span>왜 틀렸는지</span>
                      <textarea
                        value={memo}
                        rows={4}
                        maxLength={10000}
                        placeholder="헷갈린 개념이나 다음에 확인할 내용을 적어 주세요."
                        onChange={(event) => {
                          setMemoDrafts((current) => ({
                            ...current,
                            [problem.id]: event.target.value,
                          }));
                          setSavedProblemId(null);
                        }}
                      />
                    </label>

                    <div className="wrong-answer-detail-actions">
                      <span
                        className={`wrong-answer-saved${savedProblemId === problem.id ? " is-visible" : ""}`}
                        role="status"
                      >
                        저장됨
                      </span>
                      <button
                        className="button button--ghost"
                        type="button"
                        onClick={() => void updateEntry(problem.id, { memo: memo.trim() || null })}
                        disabled={saving}
                      >
                        메모 저장
                      </button>
                      <button
                        className="button button--ghost"
                        type="button"
                        onClick={() => onStudy(problem.id)}
                        disabled={saving}
                      >
                        다시 풀기
                      </button>
                      {wrongAnswer.status === "needs_review" && (
                        <button
                          className="button button--secondary"
                          type="button"
                          onClick={() => void updateEntry(problem.id, { status: "reviewing" })}
                          disabled={saving}
                        >
                          복습 시작
                        </button>
                      )}
                      <button
                        className="button button--primary"
                        type="button"
                        onClick={() => void updateEntry(problem.id, {
                          status: wrongAnswer.status === "resolved"
                            ? "needs_review"
                            : "resolved",
                        })}
                        disabled={saving}
                      >
                        {wrongAnswer.status === "resolved" ? "복습 필요로 변경" : "해결 처리"}
                      </button>
                    </div>
                  </div>
                </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}
