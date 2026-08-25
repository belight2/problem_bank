import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
} from "react";

import {
  getErrorMessage,
  problemApi,
  randomStudySettingsApi,
} from "../api/client";
import { problemTypeLabels } from "../problemTypes";
import type { Card, Problem, ProblemType, Topic } from "../types";
import { Modal } from "./Modal";
import { ProblemPrompt } from "./ProblemPrompt";

interface RandomStudyModalProps {
  card: Card;
  topics: Topic[];
  onClose: () => void;
}

type StudyStage = "setup" | "loading" | "study" | "complete";
type StudyScope = "all" | "topic";
type GradeResult = "correct" | "incorrect" | "ungraded";

interface StudyConfiguration {
  problemCount: number;
  topicId?: number;
}

function isAutomaticallyGraded(problemType: ProblemType) {
  return problemType === "multiple_choice" || problemType === "true_false";
}

export function RandomStudyModal({ card, topics, onClose }: RandomStudyModalProps) {
  const allScopeId = useId();
  const topicScopeId = useId();
  const topicSelectId = useId();
  const countId = useId();
  const answerId = useId();
  const userAnswerId = useId();
  const responseName = useId();
  const questionRef = useRef<HTMLHeadingElement>(null);
  const requestController = useRef<AbortController | null>(null);

  const [stage, setStage] = useState<StudyStage>("loading");
  const [scope, setScope] = useState<StudyScope>("all");
  const [topicId, setTopicId] = useState<number | "">(topics[0]?.id ?? "");
  const [count, setCount] = useState("");
  const [requestedCount, setRequestedCount] = useState(0);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswer, setUserAnswer] = useState("");
  const [showAnswer, setShowAnswer] = useState(false);
  const [results, setResults] = useState<Record<number, GradeResult>>({});
  const [error, setError] = useState<string | null>(null);

  const currentProblem = problems[currentIndex] ?? null;
  const currentResult = currentProblem ? (results[currentProblem.id] ?? null) : null;
  const selectedTopic =
    scope === "topic" ? topics.find((topic) => topic.id === topicId) : undefined;
  const automaticGrading = currentProblem
    ? isAutomaticallyGraded(currentProblem.problem_type)
    : false;
  const responseOptions = currentProblem
    ? currentProblem.problem_type === "multiple_choice"
      ? (currentProblem.choices ?? [])
      : currentProblem.problem_type === "true_false"
        ? ["O", "X"]
        : null
    : null;
  const automaticGradingReady =
    automaticGrading && Boolean(currentProblem?.answer) && Boolean(responseOptions?.length);
  const gradeResults = Object.values(results);
  const correctCount = gradeResults.filter((result) => result === "correct").length;
  const incorrectCount = gradeResults.filter((result) => result === "incorrect").length;
  const ungradedCount = gradeResults.filter((result) => result === "ungraded").length;

  useEffect(() => {
    if (stage === "study") questionRef.current?.focus();
  }, [currentIndex, stage]);

  const resetCurrentAnswer = () => {
    setUserAnswer("");
    setShowAnswer(false);
    setError(null);
  };

  const loadProblemSet = useCallback(async (
    configuration: StudyConfiguration,
    saveSettings: boolean,
  ) => {
    const configuredTopic = configuration.topicId === undefined
      ? undefined
      : topics.find((topic) => topic.id === configuration.topicId);
    if (configuration.topicId !== undefined && !configuredTopic) {
      setScope("all");
      setTopicId(topics[0]?.id ?? "");
      setCount(String(configuration.problemCount));
      setStage("setup");
      setError("저장된 주제를 찾을 수 없습니다.");
      return;
    }

    setScope(configuredTopic ? "topic" : "all");
    setTopicId(configuredTopic?.id ?? topics[0]?.id ?? "");
    setCount(String(configuration.problemCount));

    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setStage("loading");
    setError(null);

    try {
      const result = await problemApi.random(card.id, {
        count: configuration.problemCount,
        topicId: configuredTopic?.id,
        signal: controller.signal,
      });
      if (result.length === 0) {
        setStage("setup");
        setError(
          configuredTopic
            ? `‘${configuredTopic.name}’ 주제에 등록된 문제가 없습니다.`
            : "이 카드에 등록된 문제가 없습니다.",
        );
        return;
      }

      if (saveSettings) {
        await randomStudySettingsApi.save(
          card.id,
          {
            problem_count: configuration.problemCount,
            topic_id: configuredTopic?.id ?? null,
          },
          controller.signal,
        );
      }

      setProblems(result);
      setRequestedCount(configuration.problemCount);
      setCurrentIndex(0);
      setResults({});
      setUserAnswer("");
      setShowAnswer(false);
      setError(null);
      setStage("study");
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") return;
      setStage("setup");
      setError(getErrorMessage(requestError));
    }
  }, [card.id, topics]);

  useEffect(() => {
    const initialize = async () => {
      requestController.current?.abort();
      const controller = new AbortController();
      requestController.current = controller;
      setStage("loading");
      setError(null);

      try {
        const savedSettings = await randomStudySettingsApi.get(card.id, controller.signal);
        if (savedSettings === null) {
          setStage("setup");
          return;
        }
        await loadProblemSet(
          {
            problemCount: savedSettings.problem_count,
            topicId: savedSettings.topic_id ?? undefined,
          },
          false,
        );
      } catch (requestError) {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setStage("setup");
        setError(getErrorMessage(requestError));
      }
    };

    void initialize();
    return () => requestController.current?.abort();
  }, [card.id, loadProblemSet]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsedCount = Number(count);
    if (!Number.isInteger(parsedCount) || parsedCount < 1 || parsedCount > 100) {
      setError("문제 개수는 1부터 100 사이의 정수로 입력해 주세요.");
      return;
    }
    if (scope === "topic" && !selectedTopic) {
      setError("문제를 가져올 주제를 선택해 주세요.");
      return;
    }

    void loadProblemSet(
      {
        problemCount: parsedCount,
        topicId: selectedTopic?.id,
      },
      true,
    );
  };

  const recordResult = (result: GradeResult) => {
    if (!currentProblem) return;
    setResults((current) => ({ ...current, [currentProblem.id]: result }));
  };

  const handleAutomaticGrade = () => {
    if (!currentProblem || !automaticGradingReady) return;
    if (!userAnswer) {
      setError("답을 선택해 주세요.");
      return;
    }

    setError(null);
    setShowAnswer(true);
    recordResult(userAnswer === currentProblem.answer ? "correct" : "incorrect");
  };

  const handleRevealForManualGrade = () => {
    if (!userAnswer.trim()) {
      setError("내 답안을 입력해 주세요.");
      return;
    }
    setError(null);
    setShowAnswer(true);
  };

  const handleSkipAutomaticGrade = () => {
    setShowAnswer(true);
    setError(null);
    recordResult("ungraded");
  };

  const handleNext = () => {
    if (currentResult === null) return;
    if (currentIndex >= problems.length - 1) {
      setStage("complete");
      return;
    }
    resetCurrentAnswer();
    setCurrentIndex((current) => current + 1);
  };

  const handleChangeSettings = () => {
    requestController.current?.abort();
    setStage("setup");
    setProblems([]);
    setCurrentIndex(0);
    setResults({});
    resetCurrentAnswer();
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
                    setTopicId((current) => current || topics[0]?.id || "");
                  }}
                />
                <span>
                  <strong>주제 선택</strong>
                </span>
              </label>
            </div>
          </fieldset>

          <label className="field" htmlFor={topicSelectId}>
            <span>주제</span>
            <select
              id={topicSelectId}
              value={topicId}
              onChange={(event) =>
                setTopicId(event.target.value ? Number(event.target.value) : "")
              }
              disabled={scope !== "topic"}
              required={scope === "topic"}
            >
              {topics.map((topic) => (
                <option key={topic.id} value={topic.id}>{topic.name}</option>
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
              <span>{selectedTopic?.name || "카드 전체"}</span>
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
            <div className="study-problem-meta">
              <span className="topic-badge">{currentProblem.topic_name}</span>
              <span className="problem-type-badge">
                {problemTypeLabels[currentProblem.problem_type]}
              </span>
            </div>
            <h3 ref={questionRef} className="study-question" tabIndex={-1}>
              <ProblemPrompt problem={currentProblem} />
            </h3>

            {responseOptions ? (
              <fieldset className="study-response-options">
                <legend>내 답</legend>
                <div className="study-choice-grid">
                  {responseOptions.map((option, index) => (
                    <label key={`${index}-${option}`}>
                      <input
                        type="radio"
                        name={responseName}
                        value={option}
                        checked={userAnswer === option}
                        onChange={(event) => setUserAnswer(event.target.value)}
                        disabled={currentResult !== null || !automaticGradingReady}
                      />
                      <span>
                        {currentProblem.problem_type === "multiple_choice" && (
                          <small>{index + 1}</small>
                        )}
                        {option}
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ) : (
              <label className="field study-response-field" htmlFor={userAnswerId}>
                <span>내 답</span>
                {currentProblem.problem_type === "essay" ? (
                  <textarea
                    id={userAnswerId}
                    value={userAnswer}
                    onChange={(event) => setUserAnswer(event.target.value)}
                    placeholder="생각한 답을 직접 작성해 주세요."
                    rows={5}
                    disabled={showAnswer || currentResult !== null}
                  />
                ) : (
                  <input
                    id={userAnswerId}
                    value={userAnswer}
                    onChange={(event) => setUserAnswer(event.target.value)}
                    placeholder={
                      currentProblem.problem_type === "fill_blank"
                        ? "빈칸에 들어갈 개념을 입력해 주세요."
                        : "생각한 답을 입력해 주세요."
                    }
                    disabled={showAnswer || currentResult !== null}
                  />
                )}
              </label>
            )}

            {automaticGrading && !automaticGradingReady && currentResult === null && (
              <p className="study-notice study-notice--inside" role="alert">
                이 문제는 정답 또는 선택지가 없어 자동 채점할 수 없습니다. 문제를 수정해 주세요.
              </p>
            )}

            {error && <p className="form-error study-form-error" role="alert">{error}</p>}

            {showAnswer && (
              <div className="study-answer" id={answerId}>
                <span>{automaticGrading ? "정답" : "기준 답안 · 해설"}</span>
                <p>{currentProblem.answer || "등록된 기준 답안이나 해설이 없습니다."}</p>
              </div>
            )}

            {currentResult && (
              <div className={`study-grade-result study-grade-result--${currentResult}`} role="status">
                <strong>
                  {currentResult === "correct"
                    ? "정답입니다"
                    : currentResult === "incorrect"
                      ? "오답입니다"
                      : "채점에서 제외했습니다"}
                </strong>
              </div>
            )}
          </article>

          <div className="study-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={handleChangeSettings}
            >
              설정 변경
            </button>
            {currentResult ? (
              <button className="button button--primary" type="button" onClick={handleNext}>
                {currentIndex === problems.length - 1 ? "채점 결과 보기" : "다음 문제"}
              </button>
            ) : automaticGrading ? (
              automaticGradingReady ? (
                <button className="button button--primary" type="button" onClick={handleAutomaticGrade}>
                  채점하기
                </button>
              ) : (
                <button className="button button--secondary" type="button" onClick={handleSkipAutomaticGrade}>
                  채점 제외
                </button>
              )
            ) : showAnswer ? (
              <>
                <button className="button button--danger-ghost" type="button" onClick={() => recordResult("incorrect")}>
                  오답으로 기록
                </button>
                <button className="button button--primary" type="button" onClick={() => recordResult("correct")}>
                  정답으로 기록
                </button>
              </>
            ) : (
              <button className="button button--secondary" type="button" onClick={handleRevealForManualGrade}>
                답안 확인
              </button>
            )}
          </div>
        </section>
      )}

      {stage === "complete" && (
        <div className="study-complete" aria-live="polite">
          <span className="empty-index" aria-hidden="true">✓</span>
          <h3>{problems.length}개 문제 채점을 마쳤어요</h3>
          <div className="study-result-summary" aria-label="채점 결과 요약">
            <div><strong>{correctCount}</strong><span>정답</span></div>
            <div><strong>{incorrectCount}</strong><span>오답</span></div>
            <div><strong>{ungradedCount}</strong><span>채점 제외</span></div>
          </div>
          <div className="study-actions">
            <button className="button button--ghost" type="button" onClick={handleChangeSettings}>
              설정 변경
            </button>
            <button
              className="button button--primary"
              type="button"
              onClick={() => void loadProblemSet(
                {
                  problemCount: requestedCount,
                  topicId: selectedTopic?.id,
                },
                false,
              )}
            >
              같은 설정으로 다시 뽑기
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
