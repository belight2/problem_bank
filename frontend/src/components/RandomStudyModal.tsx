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
  randomStudyPresetApi,
  randomStudySettingsApi,
} from "../api/client";
import { problemTypeLabels } from "../problemTypes";
import type {
  Card,
  Problem,
  ProblemType,
  RandomStudyPreset,
  Topic,
} from "../types";
import { Modal } from "./Modal";
import { ProblemPrompt } from "./ProblemPrompt";

interface RandomStudyModalProps {
  card: Card;
  topics: Topic[];
  onClose: () => void;
}

type StudyStage = "loading" | "overview" | "settings" | "study" | "complete";
type StudyScope = "all" | "topic";
type GradeResult = "correct" | "incorrect" | "ungraded";

interface StudyConfiguration {
  problemCount: number;
  topicId?: number;
  presetId: number | null;
}

function isAutomaticallyGraded(problemType: ProblemType) {
  return problemType === "multiple_choice" || problemType === "true_false";
}

export function RandomStudyModal({ card, topics, onClose }: RandomStudyModalProps) {
  const allScopeId = useId();
  const topicScopeId = useId();
  const topicSelectId = useId();
  const countId = useId();
  const presetNameId = useId();
  const presetDescriptionId = useId();
  const answerId = useId();
  const userAnswerId = useId();
  const responseName = useId();
  const questionRef = useRef<HTMLHeadingElement>(null);
  const requestController = useRef<AbortController | null>(null);

  const [stage, setStage] = useState<StudyStage>("loading");
  const [scope, setScope] = useState<StudyScope>("all");
  const [topicId, setTopicId] = useState<number | "">(topics[0]?.id ?? "");
  const [count, setCount] = useState("10");
  const [activePresetId, setActivePresetId] = useState<number | null>(null);
  const [savedConfiguration, setSavedConfiguration] = useState<StudyConfiguration>({
    problemCount: 10,
    presetId: null,
  });
  const [presets, setPresets] = useState<RandomStudyPreset[]>([]);
  const [editingPresetId, setEditingPresetId] = useState<number | null>(null);
  const [presetName, setPresetName] = useState("");
  const [presetDescription, setPresetDescription] = useState("");
  const [deleteArmed, setDeleteArmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [requestedCount, setRequestedCount] = useState(0);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswer, setUserAnswer] = useState("");
  const [showAnswer, setShowAnswer] = useState(false);
  const [results, setResults] = useState<Record<number, GradeResult>>({});
  const [error, setError] = useState<string | null>(null);
  const [loadingMessage, setLoadingMessage] = useState("설정을 불러오는 중…");

  const activePreset = presets.find((preset) => preset.id === activePresetId) ?? null;
  const editingPreset = presets.find((preset) => preset.id === editingPresetId) ?? null;
  const selectedTopic =
    scope === "topic" ? topics.find((topic) => topic.id === topicId) : undefined;
  const currentProblem = problems[currentIndex] ?? null;
  const currentResult = currentProblem ? (results[currentProblem.id] ?? null) : null;
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

  const applyConfiguration = useCallback((configuration: StudyConfiguration) => {
    const configuredTopic = configuration.topicId === undefined
      ? undefined
      : topics.find((topic) => topic.id === configuration.topicId);
    setScope(configuredTopic ? "topic" : "all");
    setTopicId(configuredTopic?.id ?? topics[0]?.id ?? "");
    setCount(String(configuration.problemCount));
    setActivePresetId(configuration.presetId);
    setSavedConfiguration(configuration);
  }, [topics]);

  const setDraftConfiguration = (configuration: StudyConfiguration) => {
    const configuredTopic = configuration.topicId === undefined
      ? undefined
      : topics.find((topic) => topic.id === configuration.topicId);
    setScope(configuredTopic ? "topic" : "all");
    setTopicId(configuredTopic?.id ?? topics[0]?.id ?? "");
    setCount(String(configuration.problemCount));
  };

  const getConfiguration = (): StudyConfiguration | null => {
    const parsedCount = Number(count);
    if (!Number.isInteger(parsedCount) || parsedCount < 1 || parsedCount > 100) {
      setError("문제 개수는 1부터 100 사이의 정수로 입력해 주세요.");
      return null;
    }
    if (scope === "topic" && !selectedTopic) {
      setError("문제를 가져올 주제를 선택해 주세요.");
      return null;
    }
    return {
      problemCount: parsedCount,
      topicId: selectedTopic?.id,
      presetId: activePresetId,
    };
  };

  useEffect(() => {
    if (stage === "study") questionRef.current?.focus();
  }, [currentIndex, stage]);

  useEffect(() => {
    const controller = new AbortController();
    requestController.current = controller;

    Promise.all([
      randomStudySettingsApi.get(card.id, controller.signal),
      randomStudyPresetApi.list(card.id, controller.signal),
    ])
      .then(([savedSettings, savedPresets]) => {
        setPresets(savedPresets);
        if (savedSettings) {
          const presetExists = savedPresets.some(
            (preset) => preset.id === savedSettings.preset_id,
          );
          applyConfiguration({
            problemCount: savedSettings.problem_count,
            topicId: savedSettings.topic_id ?? undefined,
            presetId: presetExists ? savedSettings.preset_id : null,
          });
        }
        setStage("overview");
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setStage("overview");
        setError(getErrorMessage(requestError));
      });

    return () => controller.abort();
  }, [applyConfiguration, card.id]);

  const resetCurrentAnswer = () => {
    setUserAnswer("");
    setShowAnswer(false);
    setError(null);
  };

  const loadProblemSet = async (configuration: StudyConfiguration) => {
    const configuredTopic = configuration.topicId === undefined
      ? undefined
      : topics.find((topic) => topic.id === configuration.topicId);
    if (configuration.topicId !== undefined && !configuredTopic) {
      setStage("overview");
      setError("선택한 주제를 찾을 수 없습니다.");
      return;
    }

    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setLoadingMessage("문제를 불러오는 중…");
    setStage("loading");
    setError(null);

    try {
      const savedSettings = await randomStudySettingsApi.save(
        card.id,
        {
          problem_count: configuration.problemCount,
          topic_id: configuredTopic?.id ?? null,
          preset_id: configuration.presetId,
        },
        controller.signal,
      );
      const result = await problemApi.random(card.id, {
        count: savedSettings.problem_count,
        topicId: savedSettings.topic_id ?? undefined,
        signal: controller.signal,
      });
      if (result.length === 0) {
        setStage("overview");
        setError(
          configuredTopic
            ? `‘${configuredTopic.name}’ 주제에 등록된 문제가 없습니다.`
            : "이 카드에 등록된 문제가 없습니다.",
        );
        return;
      }

      applyConfiguration({
        problemCount: savedSettings.problem_count,
        topicId: savedSettings.topic_id ?? undefined,
        presetId: savedSettings.preset_id,
      });
      setProblems(result);
      setRequestedCount(savedSettings.problem_count);
      setCurrentIndex(0);
      setResults({});
      setUserAnswer("");
      setShowAnswer(false);
      setError(null);
      setStage("study");
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") return;
      setStage("overview");
      setError(getErrorMessage(requestError));
    }
  };

  const handleStart = () => {
    const configuration = getConfiguration();
    if (configuration) void loadProblemSet(configuration);
  };

  const beginNewPreset = () => {
    setEditingPresetId(null);
    setPresetName("");
    setPresetDescription("");
    setDeleteArmed(false);
    setError(null);
  };

  const beginEditPreset = (preset: RandomStudyPreset) => {
    setEditingPresetId(preset.id);
    setPresetName(preset.name);
    setPresetDescription(preset.description ?? "");
    setDeleteArmed(false);
    setError(null);
    setDraftConfiguration({
      problemCount: preset.problem_count,
      topicId: preset.topic_id ?? undefined,
      presetId: preset.id,
    });
  };

  const openSettings = () => {
    setStage("settings");
    setError(null);
    if (activePreset) {
      beginEditPreset(activePreset);
    } else {
      beginNewPreset();
    }
  };

  const returnToOverview = () => {
    applyConfiguration(savedConfiguration);
    setStage("overview");
    setError(null);
  };

  const handleSavePreset = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const configuration = getConfiguration();
    const trimmedName = presetName.trim();
    if (!trimmedName) {
      setError("프리셋 이름을 입력해 주세요.");
      return;
    }
    if (!configuration) return;

    setBusy(true);
    setError(null);
    try {
      const input = {
        name: trimmedName,
        description: presetDescription.trim() || null,
        topic_id: configuration.topicId ?? null,
        problem_count: configuration.problemCount,
      };
      const savedPreset = editingPresetId === null
        ? await randomStudyPresetApi.create(card.id, input)
        : await randomStudyPresetApi.update(card.id, editingPresetId, input);
      const savedSettings = await randomStudySettingsApi.save(card.id, {
        problem_count: savedPreset.problem_count,
        topic_id: savedPreset.topic_id,
        preset_id: savedPreset.id,
      });

      setPresets((current) => {
        const exists = current.some((preset) => preset.id === savedPreset.id);
        return exists
          ? current.map((preset) => preset.id === savedPreset.id ? savedPreset : preset)
          : [...current, savedPreset];
      });
      applyConfiguration({
        problemCount: savedSettings.problem_count,
        topicId: savedSettings.topic_id ?? undefined,
        presetId: savedPreset.id,
      });
      setEditingPresetId(savedPreset.id);
      setStage("overview");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  };

  const handleApplyPreset = async () => {
    if (!editingPreset) return;
    setBusy(true);
    setError(null);
    try {
      const savedSettings = await randomStudySettingsApi.save(card.id, {
        problem_count: editingPreset.problem_count,
        topic_id: editingPreset.topic_id,
        preset_id: editingPreset.id,
      });
      applyConfiguration({
        problemCount: savedSettings.problem_count,
        topicId: savedSettings.topic_id ?? undefined,
        presetId: editingPreset.id,
      });
      setStage("overview");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  };

  const handleDeletePreset = async () => {
    if (!editingPreset) return;
    if (!deleteArmed) {
      setDeleteArmed(true);
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await randomStudyPresetApi.remove(card.id, editingPreset.id);
      setPresets((current) => current.filter((preset) => preset.id !== editingPreset.id));
      if (activePresetId === editingPreset.id) {
        applyConfiguration({ ...savedConfiguration, presetId: null });
      }
      beginNewPreset();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
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

  const modalTitle = stage === "settings"
    ? "랜덤 문제 설정"
    : stage === "complete"
      ? "문제 묶음 완료"
      : "랜덤 문제 풀기";

  return (
    <Modal title={modalTitle} onClose={onClose} size="wide">
      {stage === "overview" && (
        <section className="study-overview">
          <div className="study-overview-heading">
            <div>
              <span className="study-overview-label">사용할 설정</span>
              <h3>{activePreset?.name ?? "기본 설정"}</h3>
              {activePreset?.description && <p>{activePreset.description}</p>}
            </div>
            <button
              className="settings-gear"
              type="button"
              aria-label="랜덤 문제 설정 열기"
              title="설정"
              onClick={openSettings}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 15.25A3.25 3.25 0 1 0 12 8.75a3.25 3.25 0 0 0 0 6.5Z" />
                <path d="M19.4 13.5a7.8 7.8 0 0 0 0-3l1.7-1.3-2-3.4-2 .8a8 8 0 0 0-2.6-1.5L14.2 3h-4.1l-.3 2.1a8 8 0 0 0-2.6 1.5l-2-.8-2 3.4 1.7 1.3a7.8 7.8 0 0 0 0 3l-1.7 1.3 2 3.4 2-.8a8 8 0 0 0 2.6 1.5l.3 2.1h4.1l.3-2.1a8 8 0 0 0 2.6-1.5l2 .8 2-3.4-1.7-1.3Z" />
              </svg>
            </button>
          </div>

          <div className="study-config-grid">
            <div>
              <span>문제 범위</span>
              <strong>{selectedTopic?.name ?? "카드 전체"}</strong>
            </div>
            <div>
              <span>문제 개수</span>
              <strong>{count}개</strong>
            </div>
          </div>

          {error && <p className="form-error" role="alert">{error}</p>}

          <div className="study-start-actions">
            <button className="button button--ghost" type="button" onClick={onClose}>
              닫기
            </button>
            <button className="button button--primary" type="button" onClick={handleStart}>
              시작
            </button>
          </div>
        </section>
      )}

      {stage === "settings" && (
        <section className="preset-settings-layout">
          <aside className="preset-sidebar">
            <div className="preset-sidebar-heading">
              <strong>프리셋</strong>
              <button type="button" onClick={beginNewPreset}>새로 만들기</button>
            </div>
            <div className="preset-list">
              {presets.map((preset) => (
                <button
                  className={editingPresetId === preset.id ? "is-active" : ""}
                  type="button"
                  key={preset.id}
                  onClick={() => beginEditPreset(preset)}
                >
                  <span>{preset.name}</span>
                  <small>
                    {preset.topic_id === null
                      ? "카드 전체"
                      : topics.find((topic) => topic.id === preset.topic_id)?.name ?? "주제 없음"}
                    {` · ${preset.problem_count}개`}
                  </small>
                </button>
              ))}
              {presets.length === 0 && <p className="preset-empty">저장된 프리셋이 없습니다.</p>}
            </div>
          </aside>

          <form className="preset-editor" onSubmit={handleSavePreset}>
            <label className="field" htmlFor={presetNameId}>
              <span>이름</span>
              <input
                id={presetNameId}
                value={presetName}
                maxLength={100}
                onChange={(event) => setPresetName(event.target.value)}
                autoFocus
                required
              />
            </label>

            <label className="field" htmlFor={presetDescriptionId}>
              <span>설명</span>
              <textarea
                id={presetDescriptionId}
                value={presetDescription}
                onChange={(event) => setPresetDescription(event.target.value)}
                rows={3}
              />
            </label>

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
                  <span><strong>카드 전체</strong></span>
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
                  <span><strong>주제 선택</strong></span>
                </label>
              </div>
            </fieldset>

            <div className="preset-value-grid">
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
                  required
                />
              </label>
            </div>

            {error && <p className="form-error" role="alert">{error}</p>}

            <div className="preset-editor-actions">
              <div>
                {editingPreset && (
                  <button
                    className="button button--danger-ghost"
                    type="button"
                    onClick={() => void handleDeletePreset()}
                    disabled={busy}
                  >
                    {deleteArmed ? "정말 삭제" : "삭제"}
                  </button>
                )}
              </div>
              <div>
                <button
                  className="button button--ghost"
                  type="button"
                  onClick={returnToOverview}
                  disabled={busy}
                >
                  돌아가기
                </button>
                {editingPreset && (
                  <button
                    className="button button--secondary"
                    type="button"
                    onClick={() => void handleApplyPreset()}
                    disabled={busy}
                  >
                    이 프리셋 사용
                  </button>
                )}
                <button className="button button--primary" type="submit" disabled={busy}>
                  {busy ? "저장 중…" : editingPreset ? "변경 저장" : "프리셋 저장"}
                </button>
              </div>
            </div>
          </form>
        </section>
      )}

      {stage === "loading" && (
        <div className="study-loading" role="status" aria-live="polite">
          {loadingMessage}
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
            <button className="button button--ghost" type="button" onClick={openSettings}>
              설정
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
            <button className="button button--ghost" type="button" onClick={openSettings}>
              설정
            </button>
            <button
              className="button button--primary"
              type="button"
              onClick={() => {
                const configuration = getConfiguration();
                if (configuration) void loadProblemSet(configuration);
              }}
            >
              같은 설정으로 다시 풀기
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
