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
  RandomStudySelectionMode,
  Topic,
} from "../types";
import { Modal } from "./Modal";
import { ProblemPrompt } from "./ProblemPrompt";

interface RandomStudyModalProps {
  card: Card;
  topics: Topic[];
  onStatisticsChanged: (problems: Problem[]) => void;
  onClose: () => void;
}

type StudyStage =
  | "loading"
  | "overview"
  | "settings"
  | "study"
  | "grading"
  | "complete";
type StudyScope = "all" | "topic";
type GradeResult = "correct" | "incorrect" | "ungraded";

interface StudyConfiguration {
  problemCount: number;
  topicId?: number;
  presetId: number | null;
  selectionMode: RandomStudySelectionMode;
  incorrectRateThreshold: number;
  minimumAttemptCount: number;
  incorrectCountThreshold: number;
}

function getSelectionSummary(configuration: StudyConfiguration) {
  if (configuration.selectionMode === "incorrect_rate") {
    return `오답률 ${configuration.incorrectRateThreshold}% 이상 · 최소 ${configuration.minimumAttemptCount}회`;
  }
  if (configuration.selectionMode === "incorrect_count") {
    return `오답 ${configuration.incorrectCountThreshold}회 이상`;
  }
  return "전체 문제";
}

function isAutomaticallyGraded(problemType: ProblemType) {
  return problemType === "multiple_choice" || problemType === "true_false";
}

export function RandomStudyModal({
  card,
  topics,
  onStatisticsChanged,
  onClose,
}: RandomStudyModalProps) {
  const allScopeId = useId();
  const topicScopeId = useId();
  const topicSelectId = useId();
  const countId = useId();
  const allProblemsId = useId();
  const incorrectRateId = useId();
  const incorrectCountId = useId();
  const incorrectRateThresholdId = useId();
  const minimumAttemptCountId = useId();
  const incorrectCountThresholdId = useId();
  const presetNameId = useId();
  const presetDescriptionId = useId();
  const userAnswerId = useId();
  const responseName = useId();
  const questionRef = useRef<HTMLHeadingElement>(null);
  const requestController = useRef<AbortController | null>(null);

  const [stage, setStage] = useState<StudyStage>("loading");
  const [scope, setScope] = useState<StudyScope>("all");
  const [topicId, setTopicId] = useState<number | "">(topics[0]?.id ?? "");
  const [count, setCount] = useState("10");
  const [selectionMode, setSelectionMode] = useState<RandomStudySelectionMode>("all");
  const [incorrectRateThreshold, setIncorrectRateThreshold] = useState("50");
  const [minimumAttemptCount, setMinimumAttemptCount] = useState("3");
  const [incorrectCountThreshold, setIncorrectCountThreshold] = useState("1");
  const [activePresetId, setActivePresetId] = useState<number | null>(null);
  const [savedConfiguration, setSavedConfiguration] = useState<StudyConfiguration>({
    problemCount: 10,
    presetId: null,
    selectionMode: "all",
    incorrectRateThreshold: 50,
    minimumAttemptCount: 3,
    incorrectCountThreshold: 1,
  });
  const [presets, setPresets] = useState<RandomStudyPreset[]>([]);
  const [editingPresetId, setEditingPresetId] = useState<number | null>(null);
  const [presetName, setPresetName] = useState("");
  const [presetDescription, setPresetDescription] = useState("");
  const [deleteArmed, setDeleteArmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [requestedCount, setRequestedCount] = useState(0);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [studySessionId, setStudySessionId] = useState<string | null>(null);
  const [submittingResults, setSubmittingResults] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [results, setResults] = useState<Record<number, GradeResult>>({});
  const [error, setError] = useState<string | null>(null);
  const [loadingMessage, setLoadingMessage] = useState("설정을 불러오는 중…");

  const activePreset = presets.find((preset) => preset.id === activePresetId) ?? null;
  const editingPreset = presets.find((preset) => preset.id === editingPresetId) ?? null;
  const selectedTopic =
    scope === "topic" ? topics.find((topic) => topic.id === topicId) : undefined;
  const currentProblem = problems[currentIndex] ?? null;
  const currentAnswer = currentProblem ? (answers[currentProblem.id] ?? "") : "";
  const responseOptions = currentProblem
    ? currentProblem.problem_type === "multiple_choice"
      ? (currentProblem.choices ?? [])
      : currentProblem.problem_type === "true_false"
        ? ["O", "X"]
        : null
    : null;
  const gradeResults = Object.values(results);
  const correctCount = gradeResults.filter((result) => result === "correct").length;
  const incorrectCount = gradeResults.filter((result) => result === "incorrect").length;
  const ungradedCount = gradeResults.filter((result) => result === "ungraded").length;
  const gradingComplete =
    problems.length > 0 && problems.every((problem) => results[problem.id] !== undefined);

  const applyConfiguration = useCallback((configuration: StudyConfiguration) => {
    const configuredTopic = configuration.topicId === undefined
      ? undefined
      : topics.find((topic) => topic.id === configuration.topicId);
    setScope(configuredTopic ? "topic" : "all");
    setTopicId(configuredTopic?.id ?? topics[0]?.id ?? "");
    setCount(String(configuration.problemCount));
    setActivePresetId(configuration.presetId);
    setSelectionMode(configuration.selectionMode);
    setIncorrectRateThreshold(String(configuration.incorrectRateThreshold));
    setMinimumAttemptCount(String(configuration.minimumAttemptCount));
    setIncorrectCountThreshold(String(configuration.incorrectCountThreshold));
    setSavedConfiguration(configuration);
  }, [topics]);

  const setDraftConfiguration = (configuration: StudyConfiguration) => {
    const configuredTopic = configuration.topicId === undefined
      ? undefined
      : topics.find((topic) => topic.id === configuration.topicId);
    setScope(configuredTopic ? "topic" : "all");
    setTopicId(configuredTopic?.id ?? topics[0]?.id ?? "");
    setCount(String(configuration.problemCount));
    setSelectionMode(configuration.selectionMode);
    setIncorrectRateThreshold(String(configuration.incorrectRateThreshold));
    setMinimumAttemptCount(String(configuration.minimumAttemptCount));
    setIncorrectCountThreshold(String(configuration.incorrectCountThreshold));
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
    const parsedRateThreshold = Number(incorrectRateThreshold);
    const parsedMinimumAttemptCount = Number(minimumAttemptCount);
    const parsedIncorrectCountThreshold = Number(incorrectCountThreshold);
    if (
      selectionMode === "incorrect_rate"
      && (!Number.isInteger(parsedRateThreshold)
        || parsedRateThreshold < 1
        || parsedRateThreshold > 100)
    ) {
      setError("오답률은 1부터 100 사이의 정수로 입력해 주세요.");
      return null;
    }
    if (
      selectionMode === "incorrect_rate"
      && (!Number.isInteger(parsedMinimumAttemptCount) || parsedMinimumAttemptCount < 1)
    ) {
      setError("최소 풀이 횟수는 1 이상의 정수로 입력해 주세요.");
      return null;
    }
    if (
      selectionMode === "incorrect_count"
      && (!Number.isInteger(parsedIncorrectCountThreshold) || parsedIncorrectCountThreshold < 1)
    ) {
      setError("오답 횟수는 1 이상의 정수로 입력해 주세요.");
      return null;
    }
    const normalizedRateThreshold = Number.isInteger(parsedRateThreshold)
      && parsedRateThreshold >= 1
      && parsedRateThreshold <= 100
      ? parsedRateThreshold
      : 50;
    const normalizedMinimumAttemptCount = Number.isInteger(parsedMinimumAttemptCount)
      && parsedMinimumAttemptCount >= 1
      ? parsedMinimumAttemptCount
      : 3;
    const normalizedIncorrectCountThreshold = Number.isInteger(parsedIncorrectCountThreshold)
      && parsedIncorrectCountThreshold >= 1
      ? parsedIncorrectCountThreshold
      : 1;
    return {
      problemCount: parsedCount,
      topicId: selectedTopic?.id,
      presetId: activePresetId,
      selectionMode,
      incorrectRateThreshold: normalizedRateThreshold,
      minimumAttemptCount: normalizedMinimumAttemptCount,
      incorrectCountThreshold: normalizedIncorrectCountThreshold,
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
            selectionMode: savedSettings.selection_mode,
            incorrectRateThreshold: savedSettings.incorrect_rate_threshold,
            minimumAttemptCount: savedSettings.minimum_attempt_count,
            incorrectCountThreshold: savedSettings.incorrect_count_threshold,
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
    setStudySessionId(null);
    setError(null);

    try {
      const savedSettings = await randomStudySettingsApi.save(
        card.id,
        {
          problem_count: configuration.problemCount,
          topic_id: configuredTopic?.id ?? null,
          preset_id: configuration.presetId,
          selection_mode: configuration.selectionMode,
          incorrect_rate_threshold: configuration.incorrectRateThreshold,
          minimum_attempt_count: configuration.minimumAttemptCount,
          incorrect_count_threshold: configuration.incorrectCountThreshold,
        },
        controller.signal,
      );
      const result = await problemApi.random(card.id, {
        count: savedSettings.problem_count,
        topicId: savedSettings.topic_id ?? undefined,
        selectionMode: savedSettings.selection_mode,
        incorrectRateThreshold: savedSettings.incorrect_rate_threshold,
        minimumAttemptCount: savedSettings.minimum_attempt_count,
        incorrectCountThreshold: savedSettings.incorrect_count_threshold,
        signal: controller.signal,
      });
      if (result.problems.length === 0 || result.session_id === null) {
        setStage("overview");
        setError(
          configuration.selectionMode !== "all"
            ? "설정한 출제 기준에 맞는 문제가 없습니다."
            : configuredTopic
              ? `‘${configuredTopic.name}’ 주제에 등록된 문제가 없습니다.`
              : "이 카드에 등록된 문제가 없습니다.",
        );
        return;
      }

      applyConfiguration({
        problemCount: savedSettings.problem_count,
        topicId: savedSettings.topic_id ?? undefined,
        presetId: savedSettings.preset_id,
        selectionMode: savedSettings.selection_mode,
        incorrectRateThreshold: savedSettings.incorrect_rate_threshold,
        minimumAttemptCount: savedSettings.minimum_attempt_count,
        incorrectCountThreshold: savedSettings.incorrect_count_threshold,
      });
      setProblems(result.problems);
      setStudySessionId(result.session_id);
      onStatisticsChanged(result.problems);
      setRequestedCount(savedSettings.problem_count);
      setCurrentIndex(0);
      setAnswers({});
      setResults({});
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
      selectionMode: preset.selection_mode,
      incorrectRateThreshold: preset.incorrect_rate_threshold,
      minimumAttemptCount: preset.minimum_attempt_count,
      incorrectCountThreshold: preset.incorrect_count_threshold,
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
        selection_mode: configuration.selectionMode,
        incorrect_rate_threshold: configuration.incorrectRateThreshold,
        minimum_attempt_count: configuration.minimumAttemptCount,
        incorrect_count_threshold: configuration.incorrectCountThreshold,
      };
      const savedPreset = editingPresetId === null
        ? await randomStudyPresetApi.create(card.id, input)
        : await randomStudyPresetApi.update(card.id, editingPresetId, input);
      const savedSettings = await randomStudySettingsApi.save(card.id, {
        problem_count: savedPreset.problem_count,
        topic_id: savedPreset.topic_id,
        preset_id: savedPreset.id,
        selection_mode: savedPreset.selection_mode,
        incorrect_rate_threshold: savedPreset.incorrect_rate_threshold,
        minimum_attempt_count: savedPreset.minimum_attempt_count,
        incorrect_count_threshold: savedPreset.incorrect_count_threshold,
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
        selectionMode: savedSettings.selection_mode,
        incorrectRateThreshold: savedSettings.incorrect_rate_threshold,
        minimumAttemptCount: savedSettings.minimum_attempt_count,
        incorrectCountThreshold: savedSettings.incorrect_count_threshold,
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
        selection_mode: editingPreset.selection_mode,
        incorrect_rate_threshold: editingPreset.incorrect_rate_threshold,
        minimum_attempt_count: editingPreset.minimum_attempt_count,
        incorrect_count_threshold: editingPreset.incorrect_count_threshold,
      });
      applyConfiguration({
        problemCount: savedSettings.problem_count,
        topicId: savedSettings.topic_id ?? undefined,
        presetId: editingPreset.id,
        selectionMode: savedSettings.selection_mode,
        incorrectRateThreshold: savedSettings.incorrect_rate_threshold,
        minimumAttemptCount: savedSettings.minimum_attempt_count,
        incorrectCountThreshold: savedSettings.incorrect_count_threshold,
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

  const updateCurrentAnswer = (answer: string) => {
    if (!currentProblem) return;
    setAnswers((current) => ({ ...current, [currentProblem.id]: answer }));
    setError(null);
  };

  const startBatchGrading = () => {
    const automaticResults: Record<number, GradeResult> = {};
    problems.forEach((problem) => {
      if (!isAutomaticallyGraded(problem.problem_type)) return;
      const answer = answers[problem.id] ?? "";
      automaticResults[problem.id] = problem.answer
        ? answer === problem.answer
          ? "correct"
          : "incorrect"
        : "ungraded";
    });
    setResults(automaticResults);
    setError(null);
    setStage("grading");
  };

  const handleNextAnswer = () => {
    if (!currentProblem || !currentAnswer.trim()) {
      setError("답을 입력하거나 선택해 주세요.");
      return;
    }
    if (currentIndex >= problems.length - 1) {
      startBatchGrading();
      return;
    }
    setError(null);
    setCurrentIndex((current) => current + 1);
  };

  const handlePreviousAnswer = () => {
    if (currentIndex === 0) return;
    setError(null);
    setCurrentIndex((current) => current - 1);
  };

  const recordManualResult = (problemId: number, result: GradeResult) => {
    setResults((current) => ({ ...current, [problemId]: result }));
  };

  const handleCompleteGrading = async () => {
    if (!gradingComplete || !studySessionId) return;
    setSubmittingResults(true);
    setError(null);
    try {
      const recorded = await problemApi.recordStudyResults(
        card.id,
        studySessionId,
        problems.map((problem) => ({
          problem_id: problem.id,
          result: results[problem.id] ?? "ungraded",
        })),
      );
      onStatisticsChanged(recorded.problems);
      setStage("complete");
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setSubmittingResults(false);
    }
  };

  const modalTitle = stage === "settings"
    ? "랜덤 문제 설정"
    : stage === "grading"
      ? "전체 문제 채점"
    : stage === "complete"
      ? "문제 묶음 완료"
      : "랜덤 문제 풀기";

  return (
    <Modal
      title={modalTitle}
      onClose={onClose}
      size="wide"
      headerAction={stage === "overview" ? (
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
      ) : undefined}
    >
      {stage === "overview" && (
        <section className="study-overview">
          <div className="study-config-grid">
            <div>
              <span>문제 범위</span>
              <strong>{selectedTopic?.name ?? "카드 전체"}</strong>
            </div>
            <div>
              <span>문제 개수</span>
              <strong>{count}개</strong>
            </div>
            <div>
              <span>출제 기준</span>
              <strong>{getSelectionSummary(savedConfiguration)}</strong>
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
                    {` · ${getSelectionSummary({
                      problemCount: preset.problem_count,
                      topicId: preset.topic_id ?? undefined,
                      presetId: preset.id,
                      selectionMode: preset.selection_mode,
                      incorrectRateThreshold: preset.incorrect_rate_threshold,
                      minimumAttemptCount: preset.minimum_attempt_count,
                      incorrectCountThreshold: preset.incorrect_count_threshold,
                    })}`}
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

            <fieldset className="selection-fieldset">
              <legend>출제 기준</legend>
              <div className="selection-options">
                <label htmlFor={allProblemsId}>
                  <input
                    id={allProblemsId}
                    type="radio"
                    name="selection-mode"
                    checked={selectionMode === "all"}
                    onChange={() => setSelectionMode("all")}
                  />
                  <span><strong>전체 문제</strong></span>
                </label>
                <label htmlFor={incorrectRateId}>
                  <input
                    id={incorrectRateId}
                    type="radio"
                    name="selection-mode"
                    checked={selectionMode === "incorrect_rate"}
                    onChange={() => setSelectionMode("incorrect_rate")}
                  />
                  <span><strong>오답률</strong></span>
                </label>
                <label htmlFor={incorrectCountId}>
                  <input
                    id={incorrectCountId}
                    type="radio"
                    name="selection-mode"
                    checked={selectionMode === "incorrect_count"}
                    onChange={() => setSelectionMode("incorrect_count")}
                  />
                  <span><strong>오답 횟수</strong></span>
                </label>
              </div>
            </fieldset>

            {selectionMode === "incorrect_rate" && (
              <div className="threshold-value-grid">
                <label className="field" htmlFor={incorrectRateThresholdId}>
                  <span>오답률 기준 (%)</span>
                  <input
                    id={incorrectRateThresholdId}
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={100}
                    step={1}
                    value={incorrectRateThreshold}
                    onChange={(event) => setIncorrectRateThreshold(event.target.value)}
                    required
                  />
                </label>
                <label className="field" htmlFor={minimumAttemptCountId}>
                  <span>최소 풀이 횟수</span>
                  <input
                    id={minimumAttemptCountId}
                    type="number"
                    inputMode="numeric"
                    min={1}
                    step={1}
                    value={minimumAttemptCount}
                    onChange={(event) => setMinimumAttemptCount(event.target.value)}
                    required
                  />
                </label>
              </div>
            )}

            {selectionMode === "incorrect_count" && (
              <label className="field threshold-single-field" htmlFor={incorrectCountThresholdId}>
                <span>오답 횟수 기준</span>
                <input
                  id={incorrectCountThresholdId}
                  type="number"
                  inputMode="numeric"
                  min={1}
                  step={1}
                  value={incorrectCountThreshold}
                  onChange={(event) => setIncorrectCountThreshold(event.target.value)}
                  required
                />
              </label>
            )}

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
              요청한 {requestedCount}개 중 제공 가능한 문제 {problems.length}개를 불러왔습니다.
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
                        checked={currentAnswer === option}
                        onChange={(event) => updateCurrentAnswer(event.target.value)}
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
                    value={currentAnswer}
                    onChange={(event) => updateCurrentAnswer(event.target.value)}
                    placeholder="생각한 답을 직접 작성해 주세요."
                    rows={5}
                  />
                ) : (
                  <input
                    id={userAnswerId}
                    value={currentAnswer}
                    onChange={(event) => updateCurrentAnswer(event.target.value)}
                    placeholder={
                      currentProblem.problem_type === "fill_blank"
                        ? "빈칸에 들어갈 개념을 입력해 주세요."
                        : "생각한 답을 입력해 주세요."
                    }
                  />
                )}
              </label>
            )}

            {error && <p className="form-error study-form-error" role="alert">{error}</p>}
          </article>

          <div className="study-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={handlePreviousAnswer}
              disabled={currentIndex === 0}
            >
              이전 문제
            </button>
            <button className="button button--primary" type="button" onClick={handleNextAnswer}>
              {currentIndex === problems.length - 1 ? "답안 제출" : "다음 문제"}
            </button>
          </div>
        </section>
      )}

      {stage === "grading" && (
        <section className="batch-grading" aria-live="polite">
          <div className="batch-grading-heading">
            <strong>전체 {problems.length}문제</strong>
            <span>{Object.keys(results).length} / {problems.length} 채점 완료</span>
          </div>

          <div className="batch-grading-list">
            {problems.map((problem, index) => {
              const automatic = isAutomaticallyGraded(problem.problem_type);
              const result = results[problem.id];
              return (
                <article className="batch-grade-card" key={problem.id}>
                  <div className="batch-grade-card-heading">
                    <span className="batch-grade-number">{String(index + 1).padStart(2, "0")}</span>
                    <div className="study-problem-meta">
                      <span className="topic-badge">{problem.topic_name}</span>
                      <span className="problem-type-badge">
                        {problemTypeLabels[problem.problem_type]}
                      </span>
                    </div>
                  </div>
                  <h3><ProblemPrompt problem={problem} /></h3>
                  <div className="batch-grade-answers">
                    <div>
                      <span>내 답</span>
                      <p>{answers[problem.id]}</p>
                    </div>
                    <div>
                      <span>{automatic ? "정답" : "기준 답안 · 해설"}</span>
                      <p>{problem.answer || "등록된 기준 답안이나 해설이 없습니다."}</p>
                    </div>
                  </div>

                  {automatic ? (
                    <div className={`study-grade-result study-grade-result--${result}`} role="status">
                      <strong>
                        {result === "correct"
                          ? "정답"
                          : result === "incorrect"
                            ? "오답"
                            : "채점 제외"}
                      </strong>
                    </div>
                  ) : (
                    <div className="manual-grade-actions" aria-label={`${index + 1}번 문제 직접 채점`}>
                      <button
                        className={result === "incorrect" ? "is-selected is-incorrect" : ""}
                        type="button"
                        onClick={() => recordManualResult(problem.id, "incorrect")}
                      >
                        오답
                      </button>
                      <button
                        className={result === "correct" ? "is-selected is-correct" : ""}
                        type="button"
                        onClick={() => recordManualResult(problem.id, "correct")}
                      >
                        정답
                      </button>
                    </div>
                  )}
                </article>
              );
            })}
          </div>

          <div className="study-actions batch-grading-actions">
            {error && <p className="form-error batch-grading-error" role="alert">{error}</p>}
            <button
              className="button button--ghost"
              type="button"
              onClick={() => {
                setCurrentIndex(problems.length - 1);
                setStage("study");
              }}
              disabled={submittingResults}
            >
              답안 수정
            </button>
            <button
              className="button button--primary"
              type="button"
              onClick={() => void handleCompleteGrading()}
              disabled={!gradingComplete || submittingResults}
            >
              {submittingResults ? "기록 중…" : "채점 완료"}
            </button>
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
