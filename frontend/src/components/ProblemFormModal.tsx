import { useId, useState, type FormEvent } from "react";

import { getErrorMessage } from "../api/client";
import { FILL_BLANK_MARKER, problemTypeOptions } from "../problemTypes";
import type { Problem, ProblemInput, ProblemType, Topic } from "../types";
import { Modal } from "./Modal";

interface ProblemFormModalProps {
  problem: Problem | null;
  topics: Topic[];
  onClose: () => void;
  onSubmit: (input: ProblemInput) => Promise<void>;
}

type TrueFalseAnswer = "" | "O" | "X";

export function ProblemFormModal({
  problem,
  topics,
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
  const choiceAnswerName = useId();
  const choiceInputBaseId = useId();
  const initialChoices =
    problem?.problem_type === "multiple_choice" && problem.choices
      ? [...problem.choices]
      : ["", ""];
  const initialCorrectChoiceIndex =
    problem?.problem_type === "multiple_choice" && problem.answer
      ? initialChoices.findIndex((choice) => choice === problem.answer)
      : -1;

  const [selectedTopicId, setSelectedTopicId] = useState<number | "">(
    problem?.topic_id ?? "",
  );
  const [problemType, setProblemType] = useState<ProblemType>(
    problem?.problem_type ?? "short_answer",
  );
  const [question, setQuestion] = useState(problem?.question ?? "");
  const [shortAnswer, setShortAnswer] = useState(
    problem?.problem_type === "short_answer" ? (problem.answer ?? "") : "",
  );
  const [essayAnswer, setEssayAnswer] = useState(
    problem?.problem_type === "essay" ? (problem.answer ?? "") : "",
  );
  const [choices, setChoices] = useState(initialChoices);
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

  const updateChoice = (index: number, value: string) => {
    setChoices((current) =>
      current.map((choice, choiceIndex) => (choiceIndex === index ? value : choice)),
    );
  };

  const addChoice = () => {
    setChoices((current) => (current.length < 10 ? [...current, ""] : current));
  };

  const removeChoice = (index: number) => {
    if (choices.length <= 2) return;

    setChoices((current) => current.filter((_, choiceIndex) => choiceIndex !== index));
    setCorrectChoiceIndex((current) => {
      if (current === null) return null;
      if (current === index) return null;
      return current > index ? current - 1 : current;
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (
      selectedTopicId === "" ||
      !topics.some((topic) => topic.id === selectedTopicId) ||
      !question.trim()
    ) {
      setError("주제를 선택하고 문제 내용을 입력해 주세요.");
      return;
    }

    const normalizedQuestion = question.trim();
    if (
      problemType === "fill_blank" &&
      normalizedQuestion.split(FILL_BLANK_MARKER).length - 1 !== 1
    ) {
      setError(`빈칸 추론 문장에는 ${FILL_BLANK_MARKER}을 정확히 한 번 넣어 주세요.`);
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
      if (correctChoiceIndex === null) {
        setError("자동 채점을 위해 객관식 정답을 선택해 주세요.");
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
      });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
      setSaving(false);
    }
  };

  return (
    <Modal
      title={problem ? "문제 수정" : "새 문제 만들기"}
      description="문제 유형에 맞는 답안과 채점 기준을 기록합니다."
      onClose={onClose}
      size="wide"
      closeDisabled={saving}
    >
      <form className="form-stack" onSubmit={handleSubmit}>
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
            onChange={(event) => setProblemType(event.target.value as ProblemType)}
            disabled={saving}
          >
            {problemTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field" htmlFor={questionId}>
          <span>{problemType === "fill_blank" ? "빈칸 문장" : "문제"}</span>
          <textarea
            id={questionId}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={
              problemType === "fill_blank"
                ? `예: 트랜잭션은 ${FILL_BLANK_MARKER}, 일관성, 격리성, 지속성을 보장한다.`
                : "직접 풀어볼 문제를 입력해 주세요."
            }
            rows={7}
            disabled={saving}
            required
          />
          {problemType === "fill_blank" && (
            <small className="field-help">
              핵심 개념이 들어갈 자리에 {FILL_BLANK_MARKER}을 정확히 한 번 넣어 주세요.
            </small>
          )}
        </label>

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
              <p>
                선택지를 2~10개 입력하고, 자동 채점할 정답을 선택지 왼쪽의 원으로
                선택하세요.
              </p>
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
                return (
                  <div className="choice-editor-row" key={index}>
                    <label className="choice-answer-picker">
                      <input
                        type="radio"
                        name={choiceAnswerName}
                        checked={correctChoiceIndex === index}
                        onChange={() => setCorrectChoiceIndex(index)}
                        disabled={saving}
                        required
                      />
                      <span className="sr-only">
                        선택지 {index + 1}
                        {choice.trim() ? `, ${choice.trim()}` : ""}을 정답으로 지정
                      </span>
                    </label>
                    <label className="choice-input" htmlFor={choiceInputId}>
                      <span>선택지 {index + 1}</span>
                      <input
                        id={choiceInputId}
                        value={choice}
                        onChange={(event) => updateChoice(index, event.target.value)}
                        placeholder={`선택지 ${index + 1} 내용을 입력해 주세요.`}
                        disabled={saving}
                        required
                      />
                    </label>
                    <button
                      className="choice-remove"
                      type="button"
                      onClick={() => removeChoice(index)}
                      disabled={choices.length <= 2 || saving}
                      aria-label={`선택지 ${index + 1} 삭제`}
                    >
                      삭제
                    </button>
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
