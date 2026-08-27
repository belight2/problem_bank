import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import { getErrorMessage, knowledgeGraphApi } from "../api/client";
import type { Card, KnowledgeGraph, KnowledgeGraphNodeType } from "../types";
import { Modal } from "./Modal";

interface KnowledgeGraphModalProps {
  card: Card;
  onClose: () => void;
}

const nodeTypeLabels: Record<KnowledgeGraphNodeType, string> = {
  card: "카드",
  topic: "주제",
  problem: "문제",
  note: "노트",
  concept: "개념",
  misconception: "오개념",
  unknown: "기타",
};

const KnowledgeGraphCanvas = lazy(() =>
  import("./KnowledgeGraphCanvas").then((module) => ({
    default: module.KnowledgeGraphCanvas,
  })),
);

export function KnowledgeGraphModal({ card, onClose }: KnowledgeGraphModalProps) {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    knowledgeGraphApi
      .get(card.id, controller.signal)
      .then((result) => {
        setGraph(result);
      })
      .catch((loadError: unknown) => {
        if (controller.signal.aborted) return;
        setGraph(null);
        setError(getErrorMessage(loadError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [card.id, reloadKey]);

  const nodeCounts = useMemo(() => {
    const counts = new Map<KnowledgeGraphNodeType, number>();
    graph?.nodes.forEach((node) => {
      counts.set(node.type, (counts.get(node.type) ?? 0) + 1);
    });
    return Array.from(counts.entries()).filter(([, count]) => count > 0);
  }, [graph]);

  const reload = () => {
    setLoading(true);
    setError(null);
    setReloadKey((current) => current + 1);
  };
  const hasRelations = (graph?.edges.length ?? 0) > 0;

  return (
    <Modal
      title="지식 그래프"
      onClose={onClose}
      size="wide"
      headerAction={(
        <button
          className={`knowledge-graph-refresh ${loading ? "is-loading" : ""}`}
          type="button"
          aria-label="지식 그래프 새로고침"
          title="새로고침"
          disabled={loading}
          onClick={reload}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 6v5h-5M4 18v-5h5" />
            <path d="M18.5 9A7 7 0 0 0 6.4 6.4L4 9m16 6-2.4 2.6A7 7 0 0 1 5.5 15" />
          </svg>
        </button>
      )}
    >
      <div className="knowledge-graph-panel" aria-busy={loading}>
        <div className="knowledge-graph-card-name">
          <span>현재 카드</span>
          <strong>{card.title}</strong>
        </div>

        {loading ? (
          <div className="knowledge-graph-skeleton" aria-label="지식 그래프 불러오는 중">
            <div className="knowledge-graph-skeleton-node is-left" />
            <div className="knowledge-graph-skeleton-node is-center" />
            <div className="knowledge-graph-skeleton-node is-right" />
            <span className="knowledge-graph-skeleton-edge is-left" />
            <span className="knowledge-graph-skeleton-edge is-right" />
          </div>
        ) : error ? (
          <div className="knowledge-graph-state is-error" role="alert">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v6M12 17h.01" />
            </svg>
            <strong>그래프를 불러오지 못했습니다.</strong>
            <p>{error}</p>
            <button className="button button--ghost" type="button" onClick={reload}>
              다시 시도
            </button>
          </div>
        ) : graph && !hasRelations ? (
          <div className="knowledge-graph-state is-empty">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="6" cy="12" r="2.5" />
              <circle cx="18" cy="6" r="2.5" />
              <circle cx="18" cy="18" r="2.5" />
              <path d="m8.2 10.8 7.6-3.6M8.2 13.2l7.6 3.6" />
            </svg>
            <strong>연결된 지식이 없습니다.</strong>
          </div>
        ) : graph ? (
          <>
            <div className="knowledge-graph-summary">
              <div>
                <span>노드</span>
                <strong>{graph.nodes.length}</strong>
              </div>
              <div>
                <span>관계</span>
                <strong>{graph.edges.length}</strong>
              </div>
              <div className="knowledge-graph-node-types" aria-label="노드 유형별 개수">
                {nodeCounts.map(([type, count]) => (
                  <span key={type} className={`is-${type}`}>
                    {nodeTypeLabels[type]} {count}
                  </span>
                ))}
              </div>
            </div>

            {graph.truncated && (
              <p className="knowledge-graph-limit-notice" role="status">
                관계가 많아 일부만 표시됩니다.
              </p>
            )}

            <Suspense fallback={<div className="knowledge-graph-canvas-shell is-loading" />}>
              <KnowledgeGraphCanvas graph={graph} />
            </Suspense>
          </>
        ) : null}
      </div>
    </Modal>
  );
}
