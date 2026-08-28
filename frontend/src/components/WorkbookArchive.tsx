import { useState } from "react";

import { getErrorMessage } from "../api/client";
import type { Workbook, WorkbookStudyRequest } from "../types";

interface WorkbookArchiveProps {
  workbooks: Workbook[];
  loading: boolean;
  loaded: boolean;
  onCreate: () => void;
  onStudy: (request: WorkbookStudyRequest) => void;
  onDelete: (workbook: Workbook) => Promise<void>;
}

const workbookDateFormatter = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function selectionLabel(workbook: Workbook) {
  if (workbook.selection_mode === "incorrect_rate") {
    return `오답률 ${workbook.incorrect_rate_threshold}% 이상 · 최소 ${workbook.minimum_attempt_count}회`;
  }
  if (workbook.selection_mode === "incorrect_count") {
    return `오답 ${workbook.incorrect_count_threshold}회 이상`;
  }
  return "전체 문제";
}

function attemptScore(attempt: Workbook["attempts"][number]) {
  const gradedCount = attempt.correct_count + attempt.incorrect_count;
  if (gradedCount === 0) return "채점 기록 없음";
  return `${attempt.correct_count} / ${gradedCount}`;
}

export function WorkbookArchive({
  workbooks,
  loading,
  loaded,
  onCreate,
  onStudy,
  onDelete,
}: WorkbookArchiveProps) {
  const [expandedId, setExpandedId] = useState<number | null>(workbooks[0]?.id ?? null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleteArmedId, setDeleteArmedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const deleteWorkbook = async (workbook: Workbook) => {
    if (deleteArmedId !== workbook.id) {
      setDeleteArmedId(workbook.id);
      return;
    }
    setDeletingId(workbook.id);
    setError(null);
    try {
      await onDelete(workbook);
      setDeleteArmedId(null);
    } catch (deleteError) {
      setError(getErrorMessage(deleteError));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <div className="problem-toolbar workbook-toolbar">
        <div className="toolbar-actions">
          <button
            className="button button--primary"
            type="button"
            onClick={onCreate}
            disabled={loading}
          >
            새 문제집
          </button>
        </div>
      </div>

      <div className="section-heading content-section-heading">
        <div>
          <p className="eyebrow">Problem book archive</p>
          <h2>문제집</h2>
        </div>
        <span>{workbooks.length}개</span>
      </div>

      {error && <p className="form-error workbook-error" role="alert">{error}</p>}

      {loading ? (
        <div className="workbook-list" aria-label="문제집 불러오는 중">
          {[1, 2].map((item) => <div className="problem-skeleton" key={item} />)}
        </div>
      ) : !loaded ? (
        <div className="empty-state empty-state--compact">
          <span className="empty-index" aria-hidden="true">!</span>
          <h3>문제집을 불러오지 못했어요</h3>
        </div>
      ) : workbooks.length === 0 ? (
        <div className="empty-state">
          <span className="empty-index" aria-hidden="true">01</span>
          <h3>아직 만든 문제집이 없어요</h3>
        </div>
      ) : (
        <div className="workbook-list">
          {workbooks.map((workbook) => {
            const expanded = workbook.id === expandedId;
            const latestAttempt = workbook.attempts[0];
            return (
              <article
                className={`workbook-item${expanded ? " is-expanded" : ""}`}
                key={workbook.id}
              >
                <button
                  className="workbook-summary"
                  type="button"
                  aria-expanded={expanded}
                  onClick={() => setExpandedId(expanded ? null : workbook.id)}
                >
                  <span className="workbook-summary-main">
                    <span className="workbook-kicker">
                      {workbook.topic_name ?? "카드 전체"} · {selectionLabel(workbook)}
                    </span>
                    <strong>{workbook.title}</strong>
                    <span>{workbookDateFormatter.format(new Date(workbook.created_at))}</span>
                  </span>
                  <span className="workbook-summary-stats">
                    <span><strong>{workbook.problem_count}</strong>문제</span>
                    <span><strong>{workbook.attempts.length}</strong>회 풀이</span>
                    <span>
                      최근 <strong>{latestAttempt ? attemptScore(latestAttempt) : "-"}</strong>
                    </span>
                  </span>
                </button>

                {expanded && (
                  <div className="workbook-detail">
                    <div className="workbook-attempt-heading">
                      <strong>풀이 이력</strong>
                      <span>최근 회차부터 표시됩니다.</span>
                    </div>
                    <div className="workbook-attempt-list">
                      {workbook.attempts.map((attempt) => (
                        <div className="workbook-attempt" key={attempt.id}>
                          <span className="workbook-attempt-number">
                            {attempt.attempt_number}회차
                          </span>
                          <span className={`workbook-attempt-status is-${attempt.status}`}>
                            {attempt.status === "completed" ? "완료" : "미완료"}
                          </span>
                          <span>{attemptScore(attempt)}</span>
                          <span>
                            {workbookDateFormatter.format(new Date(attempt.created_at))}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="workbook-actions">
                      <button
                        className="button button--ghost"
                        type="button"
                        onClick={() => onStudy({ workbookId: workbook.id, mode: "regenerate" })}
                        disabled={deletingId === workbook.id}
                      >
                        같은 설정으로 새 문제집
                      </button>
                      <button
                        className="button button--primary"
                        type="button"
                        onClick={() => onStudy({ workbookId: workbook.id, mode: "retry" })}
                        disabled={deletingId === workbook.id}
                      >
                        이 문제집 다시 풀기
                      </button>
                      <button
                        className="button button--danger-ghost"
                        type="button"
                        onClick={() => void deleteWorkbook(workbook)}
                        disabled={deletingId === workbook.id}
                      >
                        {deletingId === workbook.id
                          ? "삭제 중…"
                          : deleteArmedId === workbook.id
                            ? "한 번 더 눌러 삭제"
                            : "삭제"}
                      </button>
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
