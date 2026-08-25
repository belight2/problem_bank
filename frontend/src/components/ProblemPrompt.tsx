import { FILL_BLANK_MARKER } from "../problemTypes";
import type { Problem } from "../types";

interface ProblemPromptProps {
  problem: Pick<Problem, "problem_type" | "question">;
}

export function ProblemPrompt({ problem }: ProblemPromptProps) {
  if (problem.problem_type !== "fill_blank") return <>{problem.question}</>;

  const [before, after] = problem.question.split(FILL_BLANK_MARKER);
  return (
    <>
      {before}
      <span className="fill-blank-gap">
        <span className="sr-only">빈칸</span>
      </span>
      {after}
    </>
  );
}
