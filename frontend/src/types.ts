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

export interface Problem {
  id: number;
  card_id: number;
  topic: string;
  question: string;
  answer: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProblemInput {
  topic: string;
  question: string;
  answer: string | null;
}
