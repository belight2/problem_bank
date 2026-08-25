import type { ProblemType } from "./types";

export const problemTypeLabels: Record<ProblemType, string> = {
  short_answer: "단답형",
  essay: "주관식",
  multiple_choice: "객관식",
  true_false: "O/X",
  fill_blank: "빈칸 추론",
};

export const FILL_BLANK_MARKER = "[빈칸]";

export const problemTypeOptions: Array<{
  value: ProblemType;
  label: string;
}> = [
  { value: "short_answer", label: problemTypeLabels.short_answer },
  { value: "essay", label: problemTypeLabels.essay },
  { value: "multiple_choice", label: problemTypeLabels.multiple_choice },
  { value: "true_false", label: problemTypeLabels.true_false },
  { value: "fill_blank", label: problemTypeLabels.fill_blank },
];
