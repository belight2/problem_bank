export interface Card {
  id: number;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface CardInput {
  title: string;
  description: string | null;
}

export interface Topic {
  id: number;
  card_id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface TopicInput {
  name: string;
}

export type ProblemType =
  | "short_answer"
  | "essay"
  | "multiple_choice"
  | "true_false"
  | "fill_blank";

export interface Problem {
  id: number;
  card_id: number;
  topic_id: number;
  topic_name: string;
  question: string;
  problem_type: ProblemType;
  choices: string[] | null;
  answer: string | null;
  presented_count: number;
  correct_count: number;
  incorrect_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProblemInput {
  topic_id: number;
  question: string;
  problem_type: ProblemType;
  choices: string[] | null;
  answer: string | null;
}

export interface RandomProblemSet {
  session_id: string | null;
  problems: Problem[];
}

export interface StudyResultInput {
  problem_id: number;
  result: "correct" | "incorrect" | "ungraded";
}

export type RandomStudySelectionMode = "all" | "incorrect_rate" | "incorrect_count";

export interface RandomStudySettings {
  card_id: number;
  topic_id: number | null;
  preset_id: number | null;
  problem_count: number;
  selection_mode: RandomStudySelectionMode;
  incorrect_rate_threshold: number;
  minimum_attempt_count: number;
  incorrect_count_threshold: number;
  created_at: string;
  updated_at: string;
}

export interface RandomStudySettingsInput {
  topic_id: number | null;
  preset_id: number | null;
  problem_count: number;
  selection_mode: RandomStudySelectionMode;
  incorrect_rate_threshold: number;
  minimum_attempt_count: number;
  incorrect_count_threshold: number;
}

export interface RandomStudyPreset {
  id: number;
  card_id: number;
  name: string;
  description: string | null;
  topic_id: number | null;
  problem_count: number;
  selection_mode: RandomStudySelectionMode;
  incorrect_rate_threshold: number;
  minimum_attempt_count: number;
  incorrect_count_threshold: number;
  created_at: string;
  updated_at: string;
}

export interface RandomStudyPresetInput {
  name: string;
  description: string | null;
  topic_id: number | null;
  problem_count: number;
  selection_mode: RandomStudySelectionMode;
  incorrect_rate_threshold: number;
  minimum_attempt_count: number;
  incorrect_count_threshold: number;
}
