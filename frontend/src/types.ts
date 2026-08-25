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
