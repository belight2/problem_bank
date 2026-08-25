import { useId, useRef, useState, type FormEvent } from "react";

import { ApiError, getErrorMessage, topicApi } from "../api/client";
import type { Card, Topic } from "../types";
import { Modal } from "./Modal";

interface TopicManagementModalProps {
  card: Card;
  topics: Topic[];
  onCreated: (topic: Topic) => void;
  onUpdated: (topic: Topic) => void;
  onDeleted: (topicId: number) => void;
  onClose: () => void;
}

function getTopicErrorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 409) {
    if (error.message === "Topic is in use") {
      return "이 주제를 사용하는 문제가 있어 삭제할 수 없습니다.";
    }
    if (error.message === "Topic name already exists") {
      return "같은 이름의 주제가 이미 있습니다.";
    }
  }
  return getErrorMessage(error);
}

export function TopicManagementModal({
  card,
  topics,
  onCreated,
  onUpdated,
  onDeleted,
  onClose,
}: TopicManagementModalProps) {
  const createNameId = useId();
  const editNameBaseId = useId();
  const createInputRef = useRef<HTMLInputElement>(null);
  const listHeadingRef = useRef<HTMLHeadingElement>(null);

  const [newName, setNewName] = useState("");
  const [editingTopicId, setEditingTopicId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [updatingTopicId, setUpdatingTopicId] = useState<number | null>(null);
  const [deletingTopicId, setDeletingTopicId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const busy = creating || updatingTopicId !== null || deletingTopicId !== null;

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const name = newName.trim();
    if (!name) {
      setError("새 주제 이름을 입력해 주세요.");
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const created = await topicApi.create(card.id, { name });
      onCreated(created);
      setNewName("");
      requestAnimationFrame(() => createInputRef.current?.focus());
    } catch (createError) {
      setError(getTopicErrorMessage(createError));
    } finally {
      setCreating(false);
    }
  };

  const startEditing = (topic: Topic) => {
    setEditingTopicId(topic.id);
    setEditingName(topic.name);
    setDeleteTargetId(null);
    setError(null);
  };

  const handleUpdate = async (event: FormEvent<HTMLFormElement>, topic: Topic) => {
    event.preventDefault();
    const name = editingName.trim();
    if (!name) {
      setError("주제 이름을 입력해 주세요.");
      return;
    }
    if (name === topic.name) {
      setEditingTopicId(null);
      setError(null);
      return;
    }

    setUpdatingTopicId(topic.id);
    setError(null);
    try {
      const updated = await topicApi.update(card.id, topic.id, { name });
      onUpdated(updated);
      setEditingTopicId(null);
      setEditingName("");
    } catch (updateError) {
      setError(getTopicErrorMessage(updateError));
    } finally {
      setUpdatingTopicId(null);
    }
  };

  const handleDelete = async (topic: Topic) => {
    setDeletingTopicId(topic.id);
    setError(null);
    try {
      await topicApi.remove(card.id, topic.id);
      onDeleted(topic.id);
      setDeleteTargetId(null);
      requestAnimationFrame(() => listHeadingRef.current?.focus());
    } catch (deleteError) {
      setError(getTopicErrorMessage(deleteError));
    } finally {
      setDeletingTopicId(null);
    }
  };

  return (
    <Modal
      title="주제 관리"
      description={`${card.title} 카드에서 문제를 분류할 주제를 관리합니다.`}
      onClose={onClose}
      size="wide"
      closeDisabled={busy}
    >
      <form className="topic-create-form" onSubmit={handleCreate}>
        <label className="field" htmlFor={createNameId}>
          <span>새 주제 이름</span>
          <input
            ref={createInputRef}
            id={createNameId}
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder="예: 데이터베이스"
            maxLength={100}
            disabled={busy}
            autoFocus
            required
          />
        </label>
        <button className="button button--primary" type="submit" disabled={busy}>
          {creating ? "추가 중…" : "주제 추가"}
        </button>
      </form>

      {error && (
        <p className="form-error topic-manager-error" role="alert">
          {error}
        </p>
      )}

      <section className="topic-manager-section" aria-labelledby="topic-list-heading">
        <div className="topic-manager-heading">
          <h3 ref={listHeadingRef} id="topic-list-heading" tabIndex={-1}>
            등록된 주제
          </h3>
          <span>{topics.length}개</span>
        </div>

        {topics.length > 0 ? (
          <ul className="topic-manager-list">
            {topics.map((topic, index) => (
              <li className="topic-manager-item" key={topic.id}>
                {editingTopicId === topic.id ? (
                  <form
                    className="topic-edit-form"
                    onSubmit={(event) => void handleUpdate(event, topic)}
                  >
                    <label
                      className="sr-only"
                      htmlFor={`${editNameBaseId}-${topic.id}`}
                    >
                      {topic.name} 주제의 새 이름
                    </label>
                    <input
                      id={`${editNameBaseId}-${topic.id}`}
                      value={editingName}
                      onChange={(event) => setEditingName(event.target.value)}
                      maxLength={100}
                      disabled={busy}
                      autoFocus
                      required
                    />
                    <div className="topic-row-actions">
                      <button
                        type="button"
                        onClick={() => {
                          setEditingTopicId(null);
                          setEditingName("");
                          setError(null);
                        }}
                        disabled={busy}
                      >
                        취소
                      </button>
                      <button type="submit" disabled={busy}>
                        {updatingTopicId === topic.id ? "저장 중…" : "저장"}
                      </button>
                    </div>
                  </form>
                ) : deleteTargetId === topic.id ? (
                  <div
                    className="topic-delete-confirm"
                    role="group"
                    aria-label={`${topic.name} 주제 삭제 확인`}
                  >
                    <p>
                      <strong>{topic.name}</strong> 주제를 삭제할까요?
                      <small>사용 중인 주제는 삭제되지 않습니다.</small>
                    </p>
                    <div className="topic-row-actions">
                      <button
                        type="button"
                        onClick={() => {
                          setDeleteTargetId(null);
                          setError(null);
                        }}
                        disabled={busy}
                      >
                        취소
                      </button>
                      <button
                        className="text-danger"
                        type="button"
                        onClick={() => void handleDelete(topic)}
                        disabled={busy}
                      >
                        {deletingTopicId === topic.id ? "삭제 중…" : "삭제 확인"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="topic-manager-name">
                      <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                      <strong>{topic.name}</strong>
                    </div>
                    <div className="topic-row-actions">
                      <button
                        type="button"
                        onClick={() => startEditing(topic)}
                        disabled={busy}
                        aria-label={`${topic.name} 주제 이름 수정`}
                      >
                        수정
                      </button>
                      <button
                        className="text-danger"
                        type="button"
                        onClick={() => {
                          setDeleteTargetId(topic.id);
                          setEditingTopicId(null);
                          setError(null);
                        }}
                        disabled={busy}
                        aria-label={`${topic.name} 주제 삭제`}
                      >
                        삭제
                      </button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state empty-state--compact">
            <span className="empty-index" aria-hidden="true">#</span>
            <h3>첫 주제를 만들어 보세요</h3>
            <p>문제를 만들기 전에 분류할 주제가 하나 이상 필요합니다.</p>
          </div>
        )}
      </section>

      <div className="modal-actions">
        <button className="button button--ghost" type="button" onClick={onClose} disabled={busy}>
          닫기
        </button>
      </div>
    </Modal>
  );
}
