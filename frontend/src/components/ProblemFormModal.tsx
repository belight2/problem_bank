import {
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { getErrorMessage } from "../api/client";
import { FILL_BLANK_MARKER, problemTypeOptions } from "../problemTypes";
import type { Note, Problem, ProblemInput, ProblemType, Topic } from "../types";
import { MarkdownContent } from "./MarkdownContent";
import { Modal } from "./Modal";

interface ProblemFormModalProps {
  problem: Problem | null;
  topics: Topic[];
  sourceNote: Note | null;
  onClose: () => void;
  onSubmit: (input: ProblemInput) => Promise<void>;
}

type TrueFalseAnswer = "" | "O" | "X";
const DEFAULT_CHOICE_COUNT = 5;

function createEmptyChoices() {
  return Array.from({ length: DEFAULT_CHOICE_COUNT }, () => "");
}

function splitFillBlankQuestion(question: string): [string, string] {
  const markerIndex = question.indexOf(FILL_BLANK_MARKER);
  if (markerIndex < 0) return [question, ""];
  return [
    question.slice(0, markerIndex),
    question.slice(markerIndex + FILL_BLANK_MARKER.length),
  ];
}

export function ProblemFormModal({
  problem,
  topics,
  sourceNote,
  onClose,
  onSubmit,
}: ProblemFormModalProps) {
  const topicId = useId();
  const problemTypeId = useId();
  const questionId = useId();
  const shortAnswerId = useId();
  const essayAnswerId = useId();
  const trueFalseAnswerId = useId();
  const fillBlankAnswerId = useId();
  const fillBlankSentenceId = useId();
  const choiceInputBaseId = useId();
  const questionInputRef = useRef<HTMLTextAreaElement>(null);
  const fillBlankSentenceRef = useRef<HTMLTextAreaElement>(null);
  const initialChoices =
    problem?.problem_type === "multiple_choice" && problem.choices
      ? [...problem.choices]
      : createEmptyChoices();
  const initialCorrectChoiceIndex =
    problem?.problem_type === "multiple_choice" && problem.answer
      ? initialChoices.findIndex((choice) => choice === problem.answer)
      : -1;
  const [initialFillBlankBefore, initialFillBlankAfter] =
    problem?.problem_type === "fill_blank"
      ? splitFillBlankQuestion(problem.question)
      : ["", ""];

  const [selectedTopicId, setSelectedTopicId] = useState<number | "">(
    problem?.topic_id ?? sourceNote?.topic_id ?? "",
  );
  const [sourceNoteConnected, setSourceNoteConnected] = useState(
    Boolean(problem?.source_note_id || sourceNote),
  );
  const [problemType, setProblemType] = useState<ProblemType>(
    problem?.problem_type ?? "short_answer",
  );
  const [question, setQuestion] = useState(problem?.question ?? "");
  const [fillBlankBefore, setFillBlankBefore] = useState(initialFillBlankBefore);
  const [fillBlankAfter, setFillBlankAfter] = useState(initialFillBlankAfter);
  const [fillBlankSelectedText, setFillBlankSelectedText] = useState(
    problem?.problem_type === "fill_blank" ? (problem.answer ?? "") : "",
  );
  const [fillBlankSentence, setFillBlankSentence] = useState(
    problem?.problem_type === "fill_blank"
      ? `${initialFillBlankBefore}${problem.answer ?? ""}${initialFillBlankAfter}`
      : "",
  );
  const [fillBlankDesignated, setFillBlankDesignated] = useState(
    problem?.problem_type === "fill_blank" &&
      problem.question.includes(FILL_BLANK_MARKER),
  );
  const [fillBlankSelection, setFillBlankSelection] = useState<{
    start: number;
    end: number;
  } | null>(null);
  const [shortAnswer, setShortAnswer] = useState(
    problem?.problem_type === "short_answer" ? (problem.answer ?? "") : "",
  );
  const [essayAnswer, setEssayAnswer] = useState(
    problem?.problem_type === "essay" ? (problem.answer ?? "") : "",
  );
  const [choices, setChoices] = useState(initialChoices);
  const [completedChoices, setCompletedChoices] = useState(
    initialChoices.map((choice) => Boolean(choice.trim())),
  );
  const [correctChoiceIndex, setCorrectChoiceIndex] = useState<number | null>(
    initialCorrectChoiceIndex >= 0 ? initialCorrectChoiceIndex : null,
  );
  const [trueFalseAnswer, setTrueFalseAnswer] = useState<TrueFalseAnswer>(
    problem?.problem_type === "true_false" &&
      (problem.answer === "O" || problem.answer === "X")
      ? problem.answer
      : "",
  );
  const [fillBlankAnswer, setFillBlankAnswer] = useState(
    problem?.problem_type === "fill_blank" ? (problem.answer ?? "") : "",
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const updateChoice = (index: number, value: string) => {
    setChoices((current) =>
      current.map((choice, choiceIndex) => (choiceIndex === index ? value : choice)),
    );
  };

  const addChoice = () => {
    setChoices((current) => (current.length < 10 ? [...current, ""] : current));
    setCompletedChoices((current) =>
      current.length < 10 ? [...current, false] : current,
    );
  };

  const removeChoice = (index: number) => {
    if (choices.length <= 2) return;

    setChoices((current) => current.filter((_, choiceIndex) => choiceIndex !== index));
    setCompletedChoices((current) =>
      current.filter((_, choiceIndex) => choiceIndex !== index),
    );
    setCorrectChoiceIndex((current) => {
      if (current === null) return null;
      if (current === index) return null;
      return current > index ? current - 1 : current;
    });
  };

  const completeChoice = (index: number) => {
    const normalizedChoice = choices[index]?.trim() ?? "";
    if (!normalizedChoice) {
      setError(`선택지 ${index + 1} 내용을 입력해 주세요.`);
      return false;
    }

    setChoices((current) =>
      current.map((choice, choiceIndex) =>
        choiceIndex === index ? normalizedChoice : choice,
      ),
    );
    setCompletedChoices((current) =>
      current.map((isCompleted, choiceIndex) =>
        choiceIndex === index ? true : isCompleted,
      ),
    );
    setError(null);
    return true;
  };

  const editChoice = (index: number) => {
    setCompletedChoices((current) =>
      current.map((isCompleted, choiceIndex) =>
        choiceIndex === index ? false : isCompleted,
      ),
    );
    setCorrectChoiceIndex((current) => (current === index ? null : current));
    setError(null);
    requestAnimationFrame(() => {
      document.getElementById(`${choiceInputBaseId}-${index}`)?.focus();
    });
  };

  const selectCorrectChoice = (index: number) => {
    if (!completedChoices[index]) return;
    setCorrectChoiceIndex(index);
    setError(null);
  };

  const changeProblemType = (nextType: ProblemType) => {
    if (nextType === problemType) return;
    if (nextType === "fill_blank") {
      if (!fillBlankSentence && !fillBlankDesignated) {
        setFillBlankSentence(question);
      }
    } else if (problemType === "fill_blank") {
      setQuestion(
        fillBlankDesignated
          ? `${fillBlankBefore}${fillBlankSelectedText}${fillBlankAfter}`.trim()
          : fillBlankSentence.trim(),
      );
    }
    setProblemType(nextType);
    setError(null);
  };

  const updateFillBlankSelection = () => {
    const input = fillBlankSentenceRef.current;
    if (!input || input.selectionStart === input.selectionEnd) {
      setFillBlankSelection(null);
      return;
    }
    setFillBlankSelection({
      start: input.selectionStart,
      end: input.selectionEnd,
    });
  };

  const designateFillBlank = () => {
    if (!fillBlankSelection) {
      setError("빈칸으로 만들 단어나 문장을 선택해 주세요.");
      return;
    }

    const rawSelection = fillBlankSentence.slice(
      fillBlankSelection.start,
      fillBlankSelection.end,
    );
    const selectedText = rawSelection.trim();
    if (!selectedText) {
      setError("공백이 아닌 내용을 선택해 주세요.");
      return;
    }

    const leadingWhitespace = rawSelection.length - rawSelection.trimStart().length;
    const trailingWhitespace = rawSelection.length - rawSelection.trimEnd().length;
    const selectionStart = fillBlankSelection.start + leadingWhitespace;
    const selectionEnd = fillBlankSelection.end - trailingWhitespace;
    setFillBlankBefore(fillBlankSentence.slice(0, selectionStart));
    setFillBlankAfter(fillBlankSentence.slice(selectionEnd));
    setFillBlankSelectedText(selectedText);
    setFillBlankAnswer(selectedText);
    setFillBlankDesignated(true);
    setFillBlankSelection(null);
    setError(null);
  };

  const editFillBlank = () => {
    const replacement = fillBlankSelectedText || fillBlankAnswer.trim();
    const restoredSentence = `${fillBlankBefore}${replacement}${fillBlankAfter}`;
    const selectionStart = fillBlankBefore.length;
    setFillBlankSentence(restoredSentence);
    setFillBlankDesignated(false);
    setError(null);
    requestAnimationFrame(() => {
      const input = fillBlankSentenceRef.current;
      if (!input) return;
      input.focus();
      input.setSelectionRange(selectionStart, selectionStart + replacement.length);
      setFillBlankSelection({
        start: selectionStart,
        end: selectionStart + replacement.length,
      });
    });
  };

  const handleChoiceKeyDown = (
    event: KeyboardEvent<HTMLInputElement>,
    index: number,
  ) => {
    if (event.key === "Enter") {
      event.preventDefault();
      const choiceCompleted = completedChoices[index] || completeChoice(index);
      if (!choiceCompleted) return;
      requestAnimationFrame(() => {
        document.getElementById(`${choiceInputBaseId}-${index + 1}`)?.focus();
      });
      return;
    }
    if (event.key === " " && completedChoices[index]) {
      event.preventDefault();
      selectCorrectChoice(index);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSuccess(null);
    if (
      selectedTopicId === "" ||
      !topics.some((topic) => topic.id === selectedTopicId)
    ) {
      setError("주제를 선택해 주세요.");
      return;
    }

    let normalizedQuestion = question.trim();
    if (problemType === "fill_blank") {
      if (!fillBlankDesignated) {
        setError("문장에서 빈칸으로 만들 부분을 지정해 주세요.");
        return;
      }
      const normalizedBefore = fillBlankBefore.trim();
      const normalizedAfter = fillBlankAfter.trim();
      if (!normalizedBefore && !normalizedAfter) {
        setError("빈칸 앞이나 뒤 문장을 입력해 주세요.");
        return;
      }
      normalizedQuestion = `${normalizedBefore}${FILL_BLANK_MARKER}${normalizedAfter}`;
    } else if (!normalizedQuestion) {
      setError("문제 내용을 입력해 주세요.");
      return;
    }

    let normalizedChoices: string[] | null = null;
    let normalizedAnswer: string | null;

    if (problemType === "multiple_choice") {
      normalizedChoices = choices.map((choice) => choice.trim());
      if (
        normalizedChoices.length < 2 ||
        normalizedChoices.length > 10 ||
        normalizedChoices.some((choice) => !choice)
      ) {
        setError("객관식 선택지는 비어 있지 않게 2개부터 10개까지 입력해 주세요.");
        return;
      }
      if (new Set(normalizedChoices).size !== normalizedChoices.length) {
        setError("객관식 선택지는 서로 다르게 입력해 주세요.");
        return;
      }
      if (completedChoices.some((isCompleted) => !isCompleted)) {
        setError("모든 객관식 선택지를 완료해 주세요.");
        return;
      }
      if (
        correctChoiceIndex === null ||
        !completedChoices[correctChoiceIndex]
      ) {
        setError("완료한 객관식 선택지에서 정답을 선택해 주세요.");
        return;
      }
      normalizedAnswer = normalizedChoices[correctChoiceIndex] ?? null;
    } else if (problemType === "short_answer") {
      normalizedAnswer = shortAnswer.trim() || null;
    } else if (problemType === "essay") {
      normalizedAnswer = essayAnswer.trim() || null;
    } else if (problemType === "fill_blank") {
      normalizedAnswer = fillBlankAnswer.trim() || null;
    } else {
      if (!trueFalseAnswer) {
        setError("자동 채점을 위해 O/X 정답을 선택해 주세요.");
        return;
      }
      normalizedAnswer = trueFalseAnswer;
    }

    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        topic_id: selectedTopicId,
        question: normalizedQuestion,
        problem_type: problemType,
        choices: normalizedChoices,
        answer: normalizedAnswer,
        source_note_id: sourceNoteConnected
          ? (sourceNote?.id ?? problem?.source_note_id ?? null)
          : null,
      });
      if (!problem) {
        setQuestion("");
        setFillBlankBefore("");
        setFillBlankAfter("");
        setFillBlankSelectedText("");
        setFillBlankSentence("");
        setFillBlankDesignated(false);
        setFillBlankSelection(null);
        setShortAnswer("");
        setEssayAnswer("");
        setChoices(createEmptyChoices());
        setCompletedChoices(createEmptyChoices().map(() => false));
        setCorrectChoiceIndex(null);
        setTrueFalseAnswer("");
        setFillBlankAnswer("");
        setSaving(false);
        setSuccess("문제를 만들었습니다.");
        requestAnimationFrame(() => {
          if (problemType === "fill_blank") {
            fillBlankSentenceRef.current?.focus();
          } else {
            questionInputRef.current?.focus();
          }
        });
      }
    } catch (submitError) {
      setError(getErrorMessage(submitError));
      setSaving(false);
    }
  };

  return (
    <Modal
      title={problem ? "문제 수정" : "새 문제 만들기"}
      onClose={onClose}
      size="wide"
      closeDisabled={saving}
    >
      <form className="form-stack" onSubmit={handleSubmit}>
        {sourceNote && (
          <section className={`problem-source-note${sourceNoteConnected ? "" : " is-disconnected"}`}>
            <div className="problem-source-note-heading">
              <div>
                <span>참고 노트</span>
                <strong>{sourceNote.title}</strong>
              </div>
              <button
                className="button button--ghost button--compact"
                type="button"
                onClick={() => setSourceNoteConnected((current) => !current)}
                disabled={saving}
              >
                {sourceNoteConnected ? "연결 해제" : "다시 연결"}
              </button>
            </div>
            {sourceNoteConnected && (
              <MarkdownContent
                content={sourceNote.content_markdown}
                className="problem-source-note-content"
              />
            )}
          </section>
        )}

        <label className="field" htmlFor={topicId}>
          <span>주제</span>
          <select
            id={topicId}
            value={selectedTopicId}
            onChange={(event) =>
              setSelectedTopicId(event.target.value ? Number(event.target.value) : "")
            }
            disabled={saving}
            autoFocus
            required
          >
            <option value="">주제를 선택해 주세요.</option>
            {topics.map((topic) => (
              <option key={topic.id} value={topic.id}>
                {topic.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field" htmlFor={problemTypeId}>
          <span>문제 유형</span>
          <select
            id={problemTypeId}
            value={problemType}
            onChange={(event) => changeProblemType(event.target.value as ProblemType)}
            disabled={saving}
          >
            {problemTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        {problemType === "fill_blank" ? (
          <fieldset className="fill-blank-editor">
            <legend>빈칸 문장</legend>
            {fillBlankDesignated ? (
              <div className="fill-blank-preview-wrap">
                <div className="fill-blank-preview" aria-label="빈칸 문제 미리보기">
                  <span>{fillBlankBefore}</span>
                  <button
                    className="fill-blank-preview-gap"
                    type="button"
                    onClick={editFillBlank}
                    disabled={saving}
                    aria-label="빈칸 다시 지정"
                    title="빈칸 다시 지정"
                  >
                    빈칸
                  </button>
                  <span>{fillBlankAfter}</span>
                </div>
                <div className="fill-blank-compose-actions">
                  <span className="fill-blank-status fill-blank-status--ready">
                    빈칸 설정됨
                  </span>
                  <button
                    className="button button--ghost button--compact"
                    type="button"
                    onClick={editFillBlank}
                    disabled={saving}
                  >
                    다시 지정
                  </button>
                </div>
              </div>
            ) : (
              <div className="fill-blank-compose">
                <label className="field" htmlFor={fillBlankSentenceId}>
                  <span>문장</span>
                  <textarea
                    ref={fillBlankSentenceRef}
                    id={fillBlankSentenceId}
                    value={fillBlankSentence}
                    onChange={(event) => {
                      setFillBlankSentence(event.target.value);
                      setFillBlankSelection(null);
                    }}
                    onSelect={updateFillBlankSelection}
                    placeholder="문장을 작성하고 빈칸으로 만들 부분을 선택해 주세요."
                    rows={7}
                    disabled={saving}
                    required
                  />
                </label>
                <div className="fill-blank-compose-actions">
                  <span className="fill-blank-status">
                    {fillBlankSelection
                      ? `선택: ${fillBlankSentence.slice(fillBlankSelection.start, fillBlankSelection.end).trim()}`
                      : "빈칸으로 만들 부분을 선택하세요"}
                  </span>
                  <button
                    className="button button--secondary button--compact"
                    type="button"
                    onClick={designateFillBlank}
                    disabled={!fillBlankSelection || saving}
                  >
                    빈칸 지정
                  </button>
                </div>
              </div>
            )}
          </fieldset>
        ) : (
          <label className="field" htmlFor={questionId}>
            <span>문제</span>
            <textarea
              ref={questionInputRef}
              id={questionId}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="직접 풀어볼 문제를 입력해 주세요."
              rows={7}
              disabled={saving}
              required
            />
          </label>
        )}

        {problemType === "short_answer" && (
          <label className="field" htmlFor={shortAnswerId}>
            <span>
              기준 답안 또는 해설 <small>선택</small>
            </span>
            <input
              id={shortAnswerId}
              value={shortAnswer}
              onChange={(event) => setShortAnswer(event.target.value)}
              placeholder="한 줄로 확인할 답을 적어 주세요."
              disabled={saving}
            />
          </label>
        )}

        {problemType === "essay" && (
          <label className="field" htmlFor={essayAnswerId}>
            <span>
              기준 답안 또는 해설 <small>선택</small>
            </span>
            <textarea
              id={essayAnswerId}
              value={essayAnswer}
              onChange={(event) => setEssayAnswer(event.target.value)}
              placeholder="나중에 확인할 답이나 해설을 적어 주세요."
              rows={5}
              disabled={saving}
            />
          </label>
        )}

        {problemType === "multiple_choice" && (
          <fieldset className="choice-fieldset">
            <legend>선택지와 정답</legend>
            <div className="choice-editor-heading">
              <button
                className="button button--ghost button--compact"
                type="button"
                onClick={addChoice}
                disabled={choices.length >= 10 || saving}
              >
                선택지 추가 ({choices.length}/10)
              </button>
            </div>

            <div className="choice-editor-list">
              {choices.map((choice, index) => {
                const choiceInputId = `${choiceInputBaseId}-${index}`;
                const isCorrectAnswer = correctChoiceIndex === index;
                const isCompleted = completedChoices[index] ?? false;
                return (
                  <div
                    className={`choice-editor-row ${isCompleted ? "choice-editor-row--completed" : ""} ${isCorrectAnswer ? "choice-editor-row--correct" : ""}`}
                    key={index}
                  >
                    <label className="choice-input" htmlFor={choiceInputId}>
                      <span className="choice-input-heading">
                        <span>선택지 {index + 1}</span>
                        {isCorrectAnswer && <strong>정답</strong>}
                      </span>
                      <input
                        id={choiceInputId}
                        value={choice}
                        onChange={(event) => updateChoice(index, event.target.value)}
                        onClick={() => selectCorrectChoice(index)}
                        onKeyDown={(event) => handleChoiceKeyDown(event, index)}
                        placeholder={`선택지 ${index + 1} 내용을 입력해 주세요.`}
                        disabled={saving}
                        readOnly={isCompleted}
                        required
                        aria-label={`선택지 ${index + 1} 내용${isCorrectAnswer ? ", 현재 정답" : isCompleted ? ", 완료됨, 클릭하면 정답으로 지정" : ", 입력 후 엔터를 누르면 완료"}`}
                      />
                    </label>
                    <div className="choice-row-actions">
                      <button
                        className={`choice-lock ${isCompleted ? "choice-lock--edit" : "choice-lock--complete"}`}
                        type="button"
                        onClick={() =>
                          isCompleted ? editChoice(index) : completeChoice(index)
                        }
                        disabled={saving}
                        aria-label={`선택지 ${index + 1} ${isCompleted ? "수정" : "완료"}`}
                        title={isCompleted ? "수정" : "완료"}
                      >
                        {isCompleted ? "수정" : <span aria-hidden="true">✓</span>}
                      </button>
                      <button
                        className="choice-remove"
                        type="button"
                        onClick={() => removeChoice(index)}
                        disabled={choices.length <= 2 || saving}
                        aria-label={`선택지 ${index + 1} 삭제`}
                        title={`선택지 ${index + 1} 삭제`}
                      >
                        <span aria-hidden="true">×</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </fieldset>
        )}

        {problemType === "true_false" && (
          <label className="field" htmlFor={trueFalseAnswerId}>
            <span>정답</span>
            <select
              id={trueFalseAnswerId}
              value={trueFalseAnswer}
              onChange={(event) =>
                setTrueFalseAnswer(event.target.value as TrueFalseAnswer)
              }
              disabled={saving}
              required
            >
              <option value="">정답 선택</option>
              <option value="O">O</option>
              <option value="X">X</option>
            </select>
          </label>
        )}

        {problemType === "fill_blank" && (
          <label className="field" htmlFor={fillBlankAnswerId}>
            <span>
              기준 답안 또는 해설 <small>선택</small>
            </span>
            <input
              id={fillBlankAnswerId}
              value={fillBlankAnswer}
              onChange={(event) => setFillBlankAnswer(event.target.value)}
              placeholder="직접 채점할 때 확인할 핵심 개념을 적어 주세요."
              disabled={saving}
            />
          </label>
        )}

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        {success && (
          <p className="form-success" role="status">
            {success}
          </p>
        )}

        <div className="modal-actions">
          <button
            className="button button--ghost"
            type="button"
            onClick={onClose}
            disabled={saving}
          >
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
