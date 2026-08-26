import type {
  Card,
  CardInput,
  Dashboard,
  Note,
  NoteInput,
  Problem,
  ProblemInput,
  Profile,
  ProfileInput,
  RandomProblemSet,
  RandomStudyPreset,
  RandomStudyPresetInput,
  RandomStudySelectionMode,
  RandomStudySettings,
  RandomStudySettingsInput,
  StudyResultInput,
  Topic,
  TopicInput,
  WrongAnswer,
  WrongAnswerInput,
  Workbook,
  WorkbookInput,
  WorkbookStudy,
} from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

interface ApiErrorDetail {
  detail?: string | Array<{ msg?: string }>;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `요청을 처리하지 못했습니다. (${response.status})`;
    try {
      const body = (await response.json()) as ApiErrorDetail;
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((item) => item.msg).filter(Boolean).join(", ") || message;
      }
    } catch {
      // 서버가 JSON이 아닌 오류 응답을 보낸 경우 기본 메시지를 사용합니다.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const cardApi = {
  list: () => request<Card[]>("/cards?limit=100"),
  create: (input: CardInput) =>
    request<Card>("/cards", { method: "POST", body: JSON.stringify(input) }),
  update: (cardId: number, input: CardInput) =>
    request<Card>(`/cards/${cardId}`, { method: "PATCH", body: JSON.stringify(input) }),
  remove: (cardId: number) => request<void>(`/cards/${cardId}`, { method: "DELETE" }),
};

export const profileApi = {
  get: () => request<Profile>("/profile"),
  update: (input: ProfileInput) =>
    request<Profile>("/profile", { method: "PUT", body: JSON.stringify(input) }),
};

export const dashboardApi = {
  get: () => request<Dashboard>("/dashboard"),
};

export const topicApi = {
  list: (cardId: number) => request<Topic[]>(`/cards/${cardId}/topics`),
  create: (cardId: number, input: TopicInput) =>
    request<Topic>(`/cards/${cardId}/topics`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  update: (cardId: number, topicId: number, input: TopicInput) =>
    request<Topic>(`/cards/${cardId}/topics/${topicId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  remove: (cardId: number, topicId: number) =>
    request<void>(`/cards/${cardId}/topics/${topicId}`, { method: "DELETE" }),
};

export const noteApi = {
  list: (cardId: number) => request<Note[]>(`/cards/${cardId}/notes?limit=100`),
  get: (cardId: number, noteId: number, signal?: AbortSignal) =>
    request<Note>(`/cards/${cardId}/notes/${noteId}`, { signal }),
  create: (cardId: number, input: NoteInput) =>
    request<Note>(`/cards/${cardId}/notes`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  update: (cardId: number, noteId: number, input: NoteInput) =>
    request<Note>(`/cards/${cardId}/notes/${noteId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  remove: (cardId: number, noteId: number) =>
    request<void>(`/cards/${cardId}/notes/${noteId}`, { method: "DELETE" }),
};

export const problemApi = {
  list: (cardId: number, topicId?: number) => {
    const params = new URLSearchParams({ limit: "100" });
    if (topicId !== undefined) params.set("topic_id", String(topicId));
    return request<Problem[]>(`/cards/${cardId}/problems?${params.toString()}`);
  },
  random: (
    cardId: number,
    options: {
      count: number;
      topicId?: number;
      selectionMode: RandomStudySelectionMode;
      incorrectRateThreshold: number;
      minimumAttemptCount: number;
      incorrectCountThreshold: number;
      signal?: AbortSignal;
    },
  ) => {
    const params = new URLSearchParams({ limit: String(options.count) });
    if (options.topicId !== undefined) params.set("topic_id", String(options.topicId));
    params.set("selection_mode", options.selectionMode);
    params.set("incorrect_rate_threshold", String(options.incorrectRateThreshold));
    params.set("minimum_attempt_count", String(options.minimumAttemptCount));
    params.set("incorrect_count_threshold", String(options.incorrectCountThreshold));
    return request<RandomProblemSet>(`/cards/${cardId}/problems/random?${params.toString()}`, {
      method: "POST",
      signal: options.signal,
    });
  },
  recordStudyResults: (
    cardId: number,
    sessionId: string,
    results: StudyResultInput[],
  ) =>
    request<{
      status: "recorded" | "already_recorded";
      problems: Problem[];
    }>(
      `/cards/${cardId}/problems/random/${sessionId}/results`,
      {
        method: "POST",
        body: JSON.stringify({ results }),
      },
    ),
  create: (cardId: number, input: ProblemInput) =>
    request<Problem>(`/cards/${cardId}/problems`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  update: (cardId: number, problemId: number, input: ProblemInput) =>
    request<Problem>(`/cards/${cardId}/problems/${problemId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  remove: (cardId: number, problemId: number) =>
    request<void>(`/cards/${cardId}/problems/${problemId}`, { method: "DELETE" }),
};

export const wrongAnswerApi = {
  list: (cardId: number, signal?: AbortSignal) =>
    request<WrongAnswer[]>(`/cards/${cardId}/wrong-answers?limit=100`, { signal }),
  update: (cardId: number, problemId: number, input: WrongAnswerInput) =>
    request<WrongAnswer>(`/cards/${cardId}/wrong-answers/${problemId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  study: (
    cardId: number,
    options: { count: number; problemId?: number; signal?: AbortSignal },
  ) => {
    const params = new URLSearchParams({ limit: String(options.count) });
    if (options.problemId !== undefined) {
      params.set("problem_id", String(options.problemId));
    }
    return request<RandomProblemSet>(
      `/cards/${cardId}/wrong-answers/study?${params.toString()}`,
      { method: "POST", signal: options.signal },
    );
  },
};

export const workbookApi = {
  list: (cardId: number, signal?: AbortSignal) =>
    request<Workbook[]>(`/cards/${cardId}/workbooks?limit=100`, { signal }),
  create: (cardId: number, input: WorkbookInput, signal?: AbortSignal) =>
    request<WorkbookStudy>(`/cards/${cardId}/workbooks`, {
      method: "POST",
      body: JSON.stringify(input),
      signal,
    }),
  update: (cardId: number, workbookId: number, title: string) =>
    request<Workbook>(`/cards/${cardId}/workbooks/${workbookId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  remove: (cardId: number, workbookId: number) =>
    request<void>(`/cards/${cardId}/workbooks/${workbookId}`, { method: "DELETE" }),
  retry: (cardId: number, workbookId: number, signal?: AbortSignal) =>
    request<WorkbookStudy>(`/cards/${cardId}/workbooks/${workbookId}/attempts`, {
      method: "POST",
      signal,
    }),
  regenerate: (
    cardId: number,
    workbookId: number,
    title?: string,
    signal?: AbortSignal,
  ) =>
    request<WorkbookStudy>(`/cards/${cardId}/workbooks/${workbookId}/regenerate`, {
      method: "POST",
      body: JSON.stringify({ title: title || null }),
      signal,
    }),
  recordResults: (
    cardId: number,
    workbookId: number,
    sessionId: string,
    results: StudyResultInput[],
  ) =>
    request<{
      status: "recorded" | "already_recorded";
      problems: Problem[];
    }>(`/cards/${cardId}/workbooks/${workbookId}/attempts/${sessionId}/results`, {
      method: "POST",
      body: JSON.stringify({ results }),
    }),
};

export const randomStudySettingsApi = {
  get: (cardId: number, signal?: AbortSignal) =>
    request<RandomStudySettings | null>(`/cards/${cardId}/random-study-settings`, {
      signal,
    }),
  save: (
    cardId: number,
    input: RandomStudySettingsInput,
    signal?: AbortSignal,
  ) =>
    request<RandomStudySettings>(`/cards/${cardId}/random-study-settings`, {
      method: "PUT",
      body: JSON.stringify(input),
      signal,
    }),
};

export const randomStudyPresetApi = {
  list: (cardId: number, signal?: AbortSignal) =>
    request<RandomStudyPreset[]>(`/cards/${cardId}/random-study-presets`, { signal }),
  create: (
    cardId: number,
    input: RandomStudyPresetInput,
    signal?: AbortSignal,
  ) =>
    request<RandomStudyPreset>(`/cards/${cardId}/random-study-presets`, {
      method: "POST",
      body: JSON.stringify(input),
      signal,
    }),
  update: (
    cardId: number,
    presetId: number,
    input: RandomStudyPresetInput,
    signal?: AbortSignal,
  ) =>
    request<RandomStudyPreset>(
      `/cards/${cardId}/random-study-presets/${presetId}`,
      {
        method: "PUT",
        body: JSON.stringify(input),
        signal,
      },
    ),
  remove: (cardId: number, presetId: number) =>
    request<void>(`/cards/${cardId}/random-study-presets/${presetId}`, {
      method: "DELETE",
    }),
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) {
    return "API 서버에 연결할 수 없습니다. FastAPI가 실행 중인지 확인해 주세요.";
  }
  return "예상하지 못한 오류가 발생했습니다.";
}
