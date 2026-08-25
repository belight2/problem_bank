import { useId, useState, type FormEvent } from "react";

import { getErrorMessage } from "../api/client";
import type { Card, CardInput } from "../types";
import { Modal } from "./Modal";

interface CardFormModalProps {
  card: Card | null;
  onClose: () => void;
  onSubmit: (input: CardInput) => Promise<void>;
}

export function CardFormModal({ card, onClose, onSubmit }: CardFormModalProps) {
  const titleId = useId();
  const descriptionId = useId();
  const [title, setTitle] = useState(card?.title ?? "");
  const [description, setDescription] = useState(card?.description ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!title.trim()) {
      setError("카드 제목을 입력해 주세요.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim() || null,
      });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
      setSaving(false);
    }
  };

  return (
    <Modal
      title={card ? "카드 수정" : "새 카드 만들기"}
      onClose={onClose}
      closeDisabled={saving}
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field" htmlFor={titleId}>
          <span>카드 제목</span>
          <input
            id={titleId}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="예: 정보처리기사"
            maxLength={200}
            autoFocus
            required
          />
        </label>

        <label className="field" htmlFor={descriptionId}>
          <span>설명 <small>선택</small></span>
          <textarea
            id={descriptionId}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="이 카드에서 공부할 내용을 간단히 적어 주세요."
            rows={4}
          />
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}

        <div className="modal-actions">
          <button className="button button--ghost" type="button" onClick={onClose} disabled={saving}>
            취소
          </button>
          <button className="button button--primary" type="submit" disabled={saving}>
            {saving ? "저장 중…" : card ? "수정 저장" : "카드 만들기"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
