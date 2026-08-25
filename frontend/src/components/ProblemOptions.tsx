import type { Problem } from "../types";

interface ProblemOptionsProps {
  problem: Pick<Problem, "problem_type" | "choices">;
}

export function ProblemOptions({ problem }: ProblemOptionsProps) {
  if (problem.problem_type === "multiple_choice") {
    if (!problem.choices?.length) return null;

    return (
      <ol className="problem-options" aria-label="객관식 선택지">
        {problem.choices.map((choice, index) => (
          <li key={`${index}-${choice}`}>
            <span className="problem-option-marker" aria-hidden="true">
              {index + 1}
            </span>
            <span>{choice}</span>
          </li>
        ))}
      </ol>
    );
  }

  if (problem.problem_type === "true_false") {
    return (
      <ul className="problem-options problem-options--true-false" aria-label="O/X 선택지">
        <li>O</li>
        <li>X</li>
      </ul>
    );
  }

  return null;
}
