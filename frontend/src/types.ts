export interface Card {
  id: number;
  profile_id: number;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Profile {
  id: number;
  display_name: string;
  timezone: string;
  daily_goal: number;
  is_configured: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfileInput {
  display_name: string;
  timezone: string;
  daily_goal: number;
}

export interface DashboardWeakTopic {
  card_id: number;
  card_title: string;
  topic_id: number;
  topic_name: string;
  problem_count: number;
  graded_count: number;
  accuracy_rate: number;
}

export interface DashboardCard {
  card_id: number;
  card_title: string;
  problem_count: number;
  note_count: number;
  workbook_count: number;
  completed_session_count: number;
  correct_count: number;
  incorrect_count: number;
  accuracy_rate: number;
  unresolved_wrong_answer_count: number;
}

export interface DashboardRecentStudy {
  session_id: string;
  card_id: number;
  card_title: string;
  workbook_id: number | null;
  workbook_title: string | null;
  attempt_number: number;
  problem_count: number;
  correct_count: number;
  incorrect_count: number;
  ungraded_count: number;
  completed_at: string;
}

export interface Dashboard {
  profile: Profile;
  card_count: number;
  topic_count: number;
  problem_count: number;
  note_count: number;
  workbook_count: number;
  completed_session_count: number;
  correct_count: number;
  incorrect_count: number;
  accuracy_rate: number;
  unresolved_wrong_answer_count: number;
  today_studied_count: number;
  weak_topics: DashboardWeakTopic[];
  cards: DashboardCard[];
  recent_studies: DashboardRecentStudy[];
}

export interface GraphSyncStatus {
  worker_enabled: boolean;
  pending_count: number;
  processing_count: number;
  completed_count: number;
  failed_count: number;
  superseded_count: number;
  oldest_open_created_at: string | null;
  last_completed_at: string | null;
}

export type GraphOutboxStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "superseded";

export interface GraphOutboxEvent {
  id: number;
  aggregate_type: "card" | "topic" | "problem" | "note" | "concept";
  aggregate_id: string;
  event_type: "upsert" | "delete";
  status: GraphOutboxStatus;
  attempt_count: number;
  available_at: string;
  locked_at: string | null;
  processed_at: string | null;
  last_error: string | null;
  created_at: string;
}

export interface GraphRetryResult {
  superseded_event_id: number;
  retry_event: GraphOutboxEvent;
}

export type KnowledgeGraphNodeType =
  | "card"
  | "topic"
  | "problem"
  | "note"
  | "concept"
  | "misconception"
  | "unknown";

export interface KnowledgeGraphNode {
  id: string;
  iri: string;
  type: KnowledgeGraphNodeType;
  label: string;
  external_id: number | null;
  presented_count: number | null;
  correct_count: number | null;
  incorrect_count: number | null;
  // 개념 노드 전용 숙련도(DB 집계). 다른 타입 노드에서는 null.
  attempted: boolean | null;
  problem_count: number | null;
  mastery_score: number | null;
}

export interface KnowledgeGraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  predicate: string;
  label: string;
}

export interface KnowledgeGraph {
  card_id: number;
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  truncated: boolean;
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

export interface Concept {
  id: number;
  profile_id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConceptInput {
  name: string;
  description: string | null;
}

export type ConceptRelationType =
  | "broader"
  | "prerequisite"
  | "related"
  | "contrasts"
  | "confused_with";

export interface ConceptRelation {
  id: number;
  source_concept_id: number;
  source_concept_name: string;
  target_concept_id: number;
  target_concept_name: string;
  relation_type: ConceptRelationType;
  created_at: string;
}

export interface ConceptRelationInput {
  source_concept_id: number;
  target_concept_id: number;
  relation_type: ConceptRelationType;
}

export interface Note {
  id: number;
  card_id: number;
  topic_id: number | null;
  topic_name: string | null;
  title: string;
  content_markdown: string;
  concept_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface NoteInput {
  topic_id: number | null;
  title: string;
  content_markdown: string;
  concept_ids: number[];
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
  source_note_id: number | null;
  source_note_title: string | null;
  primary_concept_id: number | null;
  supporting_concept_ids: number[];
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
  source_note_id: number | null;
  primary_concept_id: number | null;
  supporting_concept_ids: number[];
}

export interface RandomProblemSet {
  session_id: string | null;
  problems: Problem[];
}

export interface StudyResultInput {
  problem_id: number;
  result: "correct" | "incorrect" | "ungraded";
  submitted_answer: string | null;
}

export type WrongAnswerStatus = "needs_review" | "reviewing" | "resolved";

export interface WrongAnswer {
  id: number;
  card_id: number;
  problem_id: number;
  status: WrongAnswerStatus;
  last_submitted_answer: string | null;
  memo: string | null;
  last_incorrect_at: string;
  created_at: string;
  updated_at: string;
  problem: Problem;
}

export interface WrongAnswerInput {
  status?: WrongAnswerStatus;
  memo?: string | null;
}

export interface WrongAnswerStudyRequest {
  problemId?: number;
  problemCount: number;
}

export interface WorkbookAttempt {
  id: string;
  attempt_number: number;
  status: "in_progress" | "completed";
  correct_count: number;
  incorrect_count: number;
  ungraded_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface Workbook {
  id: number;
  card_id: number;
  title: string;
  topic_id: number | null;
  topic_name: string | null;
  preset_id: number | null;
  preset_name: string | null;
  problem_count: number;
  requested_problem_count: number;
  selection_mode: RandomStudySelectionMode;
  incorrect_rate_threshold: number;
  minimum_attempt_count: number;
  incorrect_count_threshold: number;
  attempts: WorkbookAttempt[];
  created_at: string;
  updated_at: string;
}

export interface WorkbookInput {
  title: string | null;
  topic_id: number | null;
  preset_id: number | null;
  problem_count: number;
  selection_mode: RandomStudySelectionMode;
  incorrect_rate_threshold: number;
  minimum_attempt_count: number;
  incorrect_count_threshold: number;
}

export interface WorkbookStudy {
  workbook: Workbook;
  session_id: string;
  problems: Problem[];
}

export interface WorkbookStudyRequest {
  workbookId: number;
  mode: "retry" | "regenerate";
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
