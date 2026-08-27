import { useCallback, useEffect, useState } from "react";

import { getErrorMessage, graphSyncApi } from "../api/client";
import type { GraphOutboxEvent, GraphSyncStatus } from "../types";
import { Modal } from "./Modal";

interface GraphSyncModalProps {
  initialStatus: GraphSyncStatus | null;
  onClose: () => void;
  onStatusChange: (status: GraphSyncStatus) => void;
}

const eventTypeLabels: Record<GraphOutboxEvent["aggregate_type"], string> = {
  card: "카드",
  topic: "주제",
  problem: "문제",
  note: "노트",
};

const dateTimeFormatter = new Intl.DateTimeFormat("ko-KR", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function formatDateTime(value: string | null): string {
  return value ? dateTimeFormatter.format(new Date(value)) : "-";
}

export function GraphSyncModal({
  initialStatus,
  onClose,
  onStatusChange,
}: GraphSyncModalProps) {
  const [syncStatus, setSyncStatus] = useState<GraphSyncStatus | null>(initialStatus);
  const [failedEvents, setFailedEvents] = useState<GraphOutboxEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [retryingEventId, setRetryingEventId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadSyncData = useCallback(async (background = false) => {
    if (background) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);
    try {
      const [nextStatus, nextFailedEvents] = await Promise.all([
        graphSyncApi.status(),
        graphSyncApi.failedEvents(),
      ]);
      setSyncStatus(nextStatus);
      setFailedEvents(nextFailedEvents);
      onStatusChange(nextStatus);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [onStatusChange]);

  useEffect(() => {
    let ignore = false;
    Promise.all([graphSyncApi.status(), graphSyncApi.failedEvents()])
      .then(([nextStatus, nextFailedEvents]) => {
        if (ignore) return;
        setSyncStatus(nextStatus);
        setFailedEvents(nextFailedEvents);
        onStatusChange(nextStatus);
      })
      .catch((loadError: unknown) => {
        if (!ignore) setError(getErrorMessage(loadError));
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [onStatusChange]);

  const retryEvent = async (eventId: number) => {
    setRetryingEventId(eventId);
    setError(null);
    setNotice(null);
    try {
      await graphSyncApi.retry(eventId);
      setNotice("재처리 이벤트를 만들었습니다.");
      await loadSyncData(true);
    } catch (retryError) {
      setError(getErrorMessage(retryError));
    } finally {
      setRetryingEventId(null);
    }
  };

  const openCount = (syncStatus?.pending_count ?? 0) + (syncStatus?.processing_count ?? 0);
  const statusTone = syncStatus?.failed_count
    ? "error"
    : !syncStatus?.worker_enabled
      ? "paused"
      : openCount > 0
        ? "working"
        : "ready";
  const statusLabel = statusTone === "error"
    ? "확인이 필요합니다"
    : statusTone === "paused"
      ? "작업자 꺼짐"
      : statusTone === "working"
        ? "동기화 중"
        : "동기화 정상";

  return (
    <Modal
      title="그래프 동기화"
      onClose={onClose}
      headerAction={(
        <button
          className="graph-sync-refresh"
          type="button"
          aria-label="동기화 상태 새로고침"
          title="새로고침"
          disabled={loading || refreshing}
          onClick={() => void loadSyncData(true)}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 6v5h-5M4 18v-5h5" />
            <path d="M18.5 9A7 7 0 0 0 6.4 6.4L4 9m16 6-2.4 2.6A7 7 0 0 1 5.5 15" />
          </svg>
        </button>
      )}
    >
      <div className="graph-sync-panel" aria-busy={loading}>
        {error && <p className="graph-sync-feedback is-error" role="alert">{error}</p>}
        {notice && <p className="graph-sync-feedback is-success" role="status">{notice}</p>}

        {loading && !syncStatus ? (
          <div className="graph-sync-skeleton" aria-label="동기화 상태 불러오는 중">
            <div />
            <div />
          </div>
        ) : syncStatus ? (
          <>
            <section className={`graph-sync-overview is-${statusTone}`}>
              <div className="graph-sync-state">
                <span aria-hidden="true" />
                <div>
                  <small>현재 상태</small>
                  <strong>{statusLabel}</strong>
                </div>
              </div>
              <dl className="graph-sync-counts">
                <div>
                  <dt>대기</dt>
                  <dd>{syncStatus.pending_count}</dd>
                </div>
                <div>
                  <dt>처리 중</dt>
                  <dd>{syncStatus.processing_count}</dd>
                </div>
                <div>
                  <dt>완료</dt>
                  <dd>{syncStatus.completed_count}</dd>
                </div>
                <div className={syncStatus.failed_count > 0 ? "is-error" : ""}>
                  <dt>실패</dt>
                  <dd>{syncStatus.failed_count}</dd>
                </div>
              </dl>
              <div className="graph-sync-times">
                <span>최근 완료 <strong>{formatDateTime(syncStatus.last_completed_at)}</strong></span>
                {syncStatus.oldest_open_created_at && (
                  <span>가장 오래된 대기 <strong>{formatDateTime(syncStatus.oldest_open_created_at)}</strong></span>
                )}
              </div>
            </section>

            <section className="graph-sync-failures">
              <div className="graph-sync-section-heading">
                <h3>실패 이벤트</h3>
                <span>{syncStatus.failed_count}개</span>
              </div>
              {failedEvents.length === 0 ? (
                <div className="graph-sync-empty">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="m5 12 4 4L19 6" />
                  </svg>
                  <strong>실패한 이벤트가 없습니다.</strong>
                </div>
              ) : (
                <div className="graph-sync-event-list">
                  {failedEvents.map((event) => (
                    <article key={event.id} className="graph-sync-event">
                      <div className="graph-sync-event-main">
                        <div>
                          <span className="graph-sync-event-type">
                            {eventTypeLabels[event.aggregate_type]} #{event.aggregate_id}
                          </span>
                          <small>이벤트 {event.id} · 시도 {event.attempt_count}회 · {formatDateTime(event.created_at)}</small>
                        </div>
                        <button
                          className="button button--danger-ghost button--compact"
                          type="button"
                          disabled={retryingEventId !== null}
                          onClick={() => void retryEvent(event.id)}
                        >
                          {retryingEventId === event.id ? "재처리 중…" : "재처리"}
                        </button>
                      </div>
                      {event.last_error && <code>{event.last_error}</code>}
                    </article>
                  ))}
                </div>
              )}
            </section>
          </>
        ) : null}
      </div>
    </Modal>
  );
}
