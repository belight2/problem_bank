import {
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { getErrorMessage, problemApi } from "../api/client";
import type { Card, Problem } from "../types";
import { Modal } from "./Modal";

interface RandomStudyModalProps {
  card: Card;
  topics: string[];
  onClose: () => void;
}

type StudyStage = "setup" | "loading" | "study" | "complete";
type StudyScope = "all" | "topic";

export function RandomStudyModal({ card, topics, onClose }: RandomStudyModalProps) {
  const allScopeId = useId();
  const topicScopeId = useId();
  const topicId = useId();
  const countId = useId();
  const answerId = useId();
  const questionRef = useRef<HTMLHeadingElement>(null);
  const requestController = useRef<AbortController | null>(null);

  const [stage, setStage] = useState<StudyStage>("setup");
  const [scope, setScope] = useState<StudyScope>("all");
  const [topic, setTopic] = useState(topics[0] ?? "");
  const [count, setCount] = useState("");
  const [requestedCount, setRequestedCount] = useState(0);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentProblem = problems[currentIndex] ?? null;
  const selectedTopic = scope === "topic" ? topic : undefined;

  useEffect(() => {
    return () => requestController.current?.abort();
  }, []);

  useEffect(() => {
    if (stage === "study") questionRef.current?.focus();
  }, [currentIndex, stage]);

  const loadProblemSet = async () => {
    const parsedCount = Number(count);
    if (!Number.isInteger(parsedCount) || parsedCount < 1 || parsedCount > 100) {
      setError("문제 개수는 1부터 100 사이의 정수로 입력해 주세요.");
      return;
    }
    if (scope === "topic" && !topic) {
      setError("문제를 가져올 주제를 선택해 주세요.");
      return;
    }

    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setStage("loading");
    setError(null);

    try {
      const result = await problemApi.random(card.id, {
        count: parsedCount,
        topic: selectedTopic,
        signal: controller.signal,
      });
      if (result.length === 0) {
        setStage("setup");
        setError(
          selectedTopic
            ? `‘${selectedTopic}’ 주제에 등록된 문제가 없습니다.`
            : "이 카드에 등록된 문제가 없습니다.",
        );
        return;
      }

      setProblems(result);
      setRequestedCount(parsedCount);
      setCurrentIndex(0);
      setShowAnswer(false);
      setStage("study");
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") return;
      setStage("setup");
      setError(getErrorMessage(requestError));
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void loadProblemSet();
  };

  const handleNext = () => {
    if (currentIndex >= problems.length - 1) {
      setStage("complete");
      return;
    }
    setCurrentIndex((current) => current + 1);
    setShowAnswer(false);
  };

  const handleChangeSettings = () => {
    setStage("setup");
    setProblems([]);
    setCurrentIndex(0);
    setShowAnswer(false);
    setError(null);
  };

  const modalTitle =
    stage === "setup"
      ? "랜덤 문제 설정"
      : stage === "complete"
        ? "문제 묶음 완료"
        : "랜덤 문제 풀기";

  return (
    <Modal
      title={modalTitle}
      description={`${card.title} · 채점 없이 문제와 답을 차례로 확인합니다.`}
      onClose={onClose}
      size="wide"
    >
      {stage === "setup" && (
        <form className="study-setup" onSubmit={handleSubmit}>
          <fieldset className="scope-fieldset">
            <legend>문제 범위</legend>
            <div className="scope-options">
              <label htmlFor={allScopeId}>
                <input
                  id={allScopeId}
                  type="radio"
                  name="study-scope"
                  checked={scope === "all"}
                  onChange={() => setScope("all")}
                />
                <span>
                  <strong>카드 전체</strong>
                  <small>모든 주제에서 무작위로 뽑습니다.</small>
                </span>
              </label>
              <label className={topics.length === 0 ? "is-disabled" : ""} htmlFor={topicScopeId}>
                <input
                  id={topicScopeId}
                  type="radio"
                  name="study-scope"
                  checked={scope === "topic"}
                  disabled={topics.length === 0}
                  onChange={() => {
                    setScope("topic");
                    setTopic((current) => current || topics[0] || "");
                  }}
                />
                <span>
                  <strong>주제 선택</strong>
                  <small>선택한 주제 안에서만 뽑습니다.</small>
                </span>
              </label>
            </div>
          </fieldset>

          <label className="field" htmlFor={topicId}>
            <span>주제</span>
            <select
              id={topicId}
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              disabled={scope !== "topic"}
              required={scope === "topic"}
            >
              {topics.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>

          <label className="field" htmlFor={countId}>
            <span>문제 개수</span>
            <input
              id={countId}
              type="number"
              inputMode="numeric"
              min={1}
              max={100}
              step={1}
              value={count}
              onChange={(event) => setCount(event.target.value)}
              placeholder="예: 10"
              autoFocus
              required
            />
            <small className="field-help">
              1~100개까지 설정할 수 있습니다. 문제가 부족하면 등록된 문제만 제공합니다.
            </small>
          </label>

          {error && <p className="form-error" role="alert">{error}</p>}

          <div className="modal-actions">
            <button className="button button--ghost" type="button" onClick={onClose}>
              취소
            </button>
            <button className="button button--primary" type="submit">
              문제 뽑기
            </button>
          </div>
        </form>
      )}

      {stage === "loading" && (
        <div className="study-loading" role="status" aria-live="polite">
          설정한 범위에서 문제를 뽑는 중…
        </div>
      )}

      {stage === "study" && currentProblem && (
        <section className="study-session" aria-live="polite">
          <div className="study-progress">
            <div>
              <strong>현재 {currentIndex + 1} / 전체 {problems.length}</strong>
              <span>{selectedTopic || "카드 전체"}</span>
            </div>
            <progress value={currentIndex + 1} max={problems.length}>
              {currentIndex + 1} / {problems.length}
            </progress>
          </div>

          {problems.length < requestedCount && (
            <p className="study-notice" role="status">
              요청한 {requestedCount}개 중 등록된 문제 {problems.length}개를 제공했습니다.
            </p>
          )}

          <article className="study-paper">
            <span className="topic-badge">{currentProblem.topic}</span>
            <h3 ref={questionRef} className="study-question" tabIndex={-1}>
              {currentProblem.question}
            </h3>

            <div className="study-answer" id={answerId} hidden={!showAnswer}>
              <span>정답 · 해설</span>
              <p>{currentProblem.answer || "등록된 정답이나 해설이 없습니다."}</p>
            </div>
          </article>

          <div className="study-actions">
            <button
              className="button button--secondary"
              type="button"
              aria-expanded={showAnswer}
              aria-controls={answerId}
              onClick={() => setShowAnswer((current) => !current)}
            >
              {showAnswer ? "정답 숨기기" : "정답 보기"}
            </button>
            <button className="button button--primary" type="button" onClick={handleNext}>
              {currentIndex === problems.length - 1 ? "문제 묶음 완료" : "다음 문제"}
            </button>
          </div>
        </section>
      )}

      {stage === "complete" && (
        <div className="study-complete" role="status" aria-live="polite">
          <span className="empty-index" aria-hidden="true">✓</span>
          <h3>{problems.length}개 문제를 모두 확인했어요</h3>
          <p>채점이나 점수는 저장하지 않았습니다. 같은 설정으로 새 문제 묶음을 다시 뽑을 수 있어요.</p>
          <div className="study-actions">
            <button className="button button--ghost" type="button" onClick={handleChangeSettings}>
              설정 변경
            </button>
            <button className="button button--primary" type="button" onClick={() => void loadProblemSet()}>
              같은 설정으로 다시 뽑기
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
