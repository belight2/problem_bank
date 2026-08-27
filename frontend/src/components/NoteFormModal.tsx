import {
  lazy,
  Suspense,
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { ApiError, getErrorMessage } from "../api/client";
import type { Concept, Note, NoteInput, Topic } from "../types";
import { EditorErrorBoundary } from "./EditorErrorBoundary";
import { Modal } from "./Modal";

const MarkdownEditor = lazy(() =>
  import("./MarkdownEditor").then((module) => ({ default: module.MarkdownEditor })),
);

interface NoteFormModalProps {
  note: Note | null;
  topics: Topic[];
  concepts: Concept[];
  onClose: () => void;
  onCreateTopic: (name: string) => Promise<Topic>;
  onSubmit: (input: NoteInput) => Promise<void>;
}

function getTopicErrorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 409) {
    return "같은 이름의 주제가 이미 있습니다.";
  }
  return getErrorMessage(error);
}

export function NoteFormModal({
  note,
  topics,
  concepts,
  onClose,
  onCreateTopic,
  onSubmit,
}: NoteFormModalProps) {
  const titleId = useId();
  const topicId = useId();
  const newTopicId = useId();
  const newTopicInputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState(note?.title ?? "");
  const [selectedTopicId, setSelectedTopicId] = useState<number | "">(
    note?.topic_id ?? "",
  );
  const [content, setContent] = useState(note?.content_markdown ?? "");
  const [selectedConceptIds, setSelectedConceptIds] = useState<number[]>(
    note?.concept_ids ?? [],
  );
  const [discardPending, setDiscardPending] = useState(false);
  const [topicCreatorOpen, setTopicCreatorOpen] = useState(false);
  const [newTopicName, setNewTopicName] = useState("");
  const [creatingTopic, setCreatingTopic] = useState(false);
  const [topicError, setTopicError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty = title !== (note?.title ?? "")
    || selectedTopicId !== (note?.topic_id ?? "")
    || content !== (note?.content_markdown ?? "")
    || selectedConceptIds.length !== (note?.concept_ids.length ?? 0)
    || selectedConceptIds.some((conceptId) => !note?.concept_ids.includes(conceptId));
  const busy = saving || creatingTopic;

  const requestClose = () => {
    if (busy) return;
    if (!dirty) {
      onClose();
      return;
    }
    setDiscardPending(true);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    if (!title.trim()) {
      setError("노트 제목을 입력해 주세요.");
      return;
    }
    if (!content.trim()) {
      setError("노트 내용을 입력해 주세요.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        title: title.trim(),
        topic_id: selectedTopicId || null,
        content_markdown: content.trim(),
        concept_ids: selectedConceptIds,
      });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
      setSaving(false);
    }
  };

  const openTopicCreator = () => {
    setTopicCreatorOpen(true);
    setTopicError(null);
    requestAnimationFrame(() => newTopicInputRef.current?.focus());
  };

  const handleCreateTopic = async () => {
    const name = newTopicName.trim();
    if (!name) {
      setTopicError("주제 이름을 입력해 주세요.");
      return;
    }

    setCreatingTopic(true);
    setTopicError(null);
    try {
      const created = await onCreateTopic(name);
      setSelectedTopicId(created.id);
      setNewTopicName("");
      setTopicCreatorOpen(false);
      setDiscardPending(false);
    } catch (createError) {
      setTopicError(getTopicErrorMessage(createError));
    } finally {
      setCreatingTopic(false);
    }
  };

  const handleTopicKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    void handleCreateTopic();
  };

  return (
    <Modal
      title={note ? "노트 수정" : "새 노트 만들기"}
      onClose={requestClose}
      closeDisabled={busy}
      size="wide"
    >
      <form className="form-stack note-form" onSubmit={handleSubmit}>
        <div className="note-form-meta">
          <label className="field" htmlFor={titleId}>
            <span>제목</span>
            <input
              id={titleId}
              value={title}
              maxLength={200}
              onChange={(event) => {
                setTitle(event.target.value);
                setDiscardPending(false);
              }}
              autoFocus
              required
            />
          </label>

          <div className="field">
            <div className="field-label-row">
              <label htmlFor={topicId}>주제 <small>선택</small></label>
              <button
                className="inline-field-action"
                type="button"
                onClick={topicCreatorOpen ? () => setTopicCreatorOpen(false) : openTopicCreator}
                disabled={saving || creatingTopic}
              >
                {topicCreatorOpen ? "닫기" : "+ 새 주제"}
              </button>
            </div>
            <select
              id={topicId}
              value={selectedTopicId}
              onChange={(event) => {
                setSelectedTopicId(event.target.value ? Number(event.target.value) : "");
                setDiscardPending(false);
              }}
            >
              <option value="">카드 전체</option>
              {topics.map((topic) => (
                <option key={topic.id} value={topic.id}>{topic.name}</option>
              ))}
            </select>
          </div>
        </div>

        <fieldset className="concept-link-fieldset concept-link-fieldset--note">
          <legend>설명하는 개념 <small>선택</small></legend>
          {concepts.length > 0 ? (
            <div className="concept-check-list">
              {concepts.map((concept) => {
                const checked = selectedConceptIds.includes(concept.id);
                return (
                  <label className={checked ? "is-selected" : ""} key={concept.id}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {
                        setSelectedConceptIds((current) =>
                          checked
                            ? current.filter((conceptId) => conceptId !== concept.id)
                            : [...current, concept.id],
                        );
                        setDiscardPending(false);
                      }}
                      disabled={busy}
                    />
                    <span>{concept.name}</span>
                  </label>
                );
              })}
            </div>
          ) : (
            <p className="concept-link-empty">카드에 등록된 개념이 없습니다.</p>
          )}
        </fieldset>

        {topicCreatorOpen && (
          <div className="note-topic-create" role="group" aria-label="새 주제 만들기">
            <label htmlFor={newTopicId}>새 주제</label>
            <div>
              <input
                ref={newTopicInputRef}
                id={newTopicId}
                value={newTopicName}
                onChange={(event) => {
                  setNewTopicName(event.target.value);
                  setTopicError(null);
                }}
                onKeyDown={handleTopicKeyDown}
                placeholder="예: 데이터베이스"
                maxLength={100}
                disabled={creatingTopic || saving}
              />
              <button
                className="button button--primary button--compact"
                type="button"
                onClick={() => void handleCreateTopic()}
                disabled={creatingTopic || saving}
              >
                {creatingTopic ? "추가 중…" : "추가"}
              </button>
            </div>
            {topicError && <p className="field-error" role="alert">{topicError}</p>}
          </div>
        )}

        <div className="note-editor-heading">
          <span>내용</span>
        </div>

        <EditorErrorBoundary
          fallback={(
            <label className="field markdown-editor-fallback">
              <span className="form-error" role="alert">
                편집기를 불러오지 못해 기본 입력 모드로 전환했습니다.
              </span>
              <textarea
                value={content}
                onChange={(event) => {
                  setContent(event.target.value);
                  setDiscardPending(false);
                }}
                rows={18}
                required
              />
            </label>
          )}
        >
          <Suspense
            fallback={(
              <div className="markdown-editor-loading" role="status">
                편집기 불러오는 중…
              </div>
            )}
          >
            <MarkdownEditor
              initialMarkdown={note?.content_markdown ?? ""}
              onMarkdownChange={(markdown) => {
                setContent(markdown);
                setDiscardPending(false);
              }}
            />
          </Suspense>
        </EditorErrorBoundary>

        {error && <p className="form-error" role="alert">{error}</p>}

        {discardPending ? (
          <div className="discard-confirm" role="alert">
            <span>저장하지 않은 변경사항을 버릴까요?</span>
            <div>
              <button
                className="button button--ghost button--compact"
                type="button"
                onClick={() => setDiscardPending(false)}
              >
                계속 작성
              </button>
              <button
                className="button button--danger button--compact"
                type="button"
                onClick={onClose}
              >
                변경 버리기
              </button>
            </div>
          </div>
        ) : (
          <div className="modal-actions">
            <button className="button button--ghost" type="button" onClick={requestClose}>
              취소
            </button>
            <button className="button button--primary" type="submit" disabled={busy}>
              {saving ? "저장 중…" : note ? "수정 저장" : "노트 만들기"}
            </button>
          </div>
        )}
      </form>
    </Modal>
  );
}
