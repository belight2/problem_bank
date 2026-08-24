import { useId, useState, type FormEvent } from "react";

import { getErrorMessage } from "../api/client";
import type { Problem, ProblemInput } from "../types";
import { Modal } from "./Modal";

interface ProblemFormModalProps {
  problem: Problem | null;
  onClose: () => void;
  onSubmit: (input: ProblemInput) => Promise<void>;
}

export function ProblemFormModal({
  problem,
  onClose,
  onSubmit,
}: ProblemFormModalProps) {
  const topicId = useId();
  const questionId = useId();
  const answerId = useId();
  const [topic, setTopic] = useState(problem?.topic ?? "");
  const [question, setQuestion] = useState(problem?.question ?? "");
  const [answer, setAnswer] = useState(problem?.answer ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!topic.trim() || !question.trim()) {
      setError("주제와 문제 내용을 모두 입력해 주세요.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        topic: topic.trim(),
        question: question.trim(),
        answer: answer.trim() || null,
      });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
      setSaving(false);
    }
  };

  return (
    <Modal
      title={problem ? "문제 수정" : "새 문제 만들기"}
      description="채점 없이 직접 읽고 답을 확인할 문제를 기록합니다."
      onClose={onClose}
      size="wide"
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field" htmlFor={topicId}>
          <span>주제</span>
          <input
            id={topicId}
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="예: 데이터베이스"
            maxLength={100}
            autoFocus
            required
          />
        </label>

        <label className="field" htmlFor={questionId}>
          <span>문제</span>
          <textarea
            id={questionId}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="직접 풀어볼 문제를 입력해 주세요."
            rows={7}
            required
          />
        </label>

        <label className="field" htmlFor={answerId}>
          <span>정답 또는 해설 <small>선택</small></span>
          <textarea
            id={answerId}
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            placeholder="나중에 확인할 답이나 해설을 적어 주세요."
            rows={5}
          />
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}

        <div className="modal-actions">
          <button className="button button--ghost" type="button" onClick={onClose} disabled={saving}>
            취소
          </button>
          <button className="button button--primary" type="submit" disabled={saving}>
            {saving ? "저장 중…" : problem ? "수정 저장" : "문제 만들기"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
