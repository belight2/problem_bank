import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  cardApi,
  conceptApi,
  dashboardApi,
  getErrorMessage,
  graphSyncApi,
  noteApi,
  problemApi,
  profileApi,
  topicApi,
  workbookApi,
  wrongAnswerApi,
} from "./api/client";
import { CardFormModal } from "./components/CardFormModal";
import { CardDashboard } from "./components/CardDashboard";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { ConceptManagementModal } from "./components/ConceptManagementModal";
import { GraphSyncModal } from "./components/GraphSyncModal";
import { KnowledgeGraphModal } from "./components/KnowledgeGraphModal";
import { NoteArchive } from "./components/NoteArchive";
import { NoteDetailModal } from "./components/NoteDetailModal";
import { NoteFormModal } from "./components/NoteFormModal";
import { ProblemFormModal } from "./components/ProblemFormModal";
import { ProblemOptions } from "./components/ProblemOptions";
import { ProblemPrompt } from "./components/ProblemPrompt";
import { ProfileFormModal } from "./components/ProfileFormModal";
import { RandomStudyModal } from "./components/RandomStudyModal";
import { TopicManagementModal } from "./components/TopicManagementModal";
import { WorkbookArchive } from "./components/WorkbookArchive";
import { WrongAnswerArchive } from "./components/WrongAnswerArchive";
import { LOW_SAMPLE_THRESHOLD, masteryColor } from "./lib/mastery";
import { problemTypeLabels } from "./problemTypes";
import {
  getCardHash,
  getLibraryHash,
  navigateToHash,
  parseHashRoute,
  replaceHash,
  type CardContentView,
} from "./routing";
import type {
  Card,
  CardInput,
  Concept,
  Dashboard,
  GraphSyncStatus,
  Note,
  NoteInput,
  Problem,
  ProblemInput,
  Profile,
  ProfileInput,
  Topic,
  Workbook,
  WorkbookStudyRequest,
  WrongAnswer,
  WrongAnswerInput,
  ConceptStudyRequest,
  DashboardWeakConcept,
  WrongAnswerStudyRequest,
} from "./types";

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

const activityDateFormatter = new Intl.DateTimeFormat("ko-KR", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function App() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileEditorOpen, setProfileEditorOpen] = useState(false);
  const [graphSyncOpen, setGraphSyncOpen] = useState(false);
  const [knowledgeGraphOpen, setKnowledgeGraphOpen] = useState(false);
  const [graphSyncStatus, setGraphSyncStatus] = useState<GraphSyncStatus | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [cards, setCards] = useState<Card[]>([]);
  const [cardsLoading, setCardsLoading] = useState(true);
  const [appError, setAppError] = useState<string | null>(null);
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [conceptsLoading, setConceptsLoading] = useState(false);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [weakConcepts, setWeakConcepts] = useState<DashboardWeakConcept[]>([]);
  const [problemsLoading, setProblemsLoading] = useState(false);
  const [notes, setNotes] = useState<Note[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [wrongAnswers, setWrongAnswers] = useState<WrongAnswer[]>([]);
  const [wrongAnswersLoading, setWrongAnswersLoading] = useState(false);
  const [workbooks, setWorkbooks] = useState<Workbook[]>([]);
  const [workbooksLoading, setWorkbooksLoading] = useState(false);
  const [cardContentLoaded, setCardContentLoaded] = useState(false);
  const [contentView, setContentView] = useState<CardContentView>("dashboard");
  const [routeRevision, setRouteRevision] = useState(0);
  const cardContentRequestId = useRef(0);

  const [cardEditor, setCardEditor] = useState<Card | null | undefined>(undefined);
  const [problemEditor, setProblemEditor] = useState<Problem | null | undefined>(undefined);
  const [sourceNoteForProblem, setSourceNoteForProblem] = useState<Note | null>(null);
  const [noteEditor, setNoteEditor] = useState<Note | null | undefined>(undefined);
  const [noteViewer, setNoteViewer] = useState<Note | null>(null);
  const [cardToDelete, setCardToDelete] = useState<Card | null>(null);
  const [problemToDelete, setProblemToDelete] = useState<Problem | null>(null);
  const [noteToDelete, setNoteToDelete] = useState<Note | null>(null);
  const [randomStudyOpen, setRandomStudyOpen] = useState(false);
  const [wrongAnswerStudy, setWrongAnswerStudy] = useState<WrongAnswerStudyRequest | null>(null);
  const [conceptStudy, setConceptStudy] = useState<ConceptStudyRequest | null>(null);
  const [workbookStudy, setWorkbookStudy] = useState<WorkbookStudyRequest | null>(null);
  const [activeStudySessionId, setActiveStudySessionId] = useState<string | null>(null);
  const [resumeStudySessionId, setResumeStudySessionId] = useState<string | null>(null);
  const [topicManagerOpen, setTopicManagerOpen] = useState(false);
  const [topicManagerDescription, setTopicManagerDescription] = useState<string | null>(null);
  const [conceptManagerOpen, setConceptManagerOpen] = useState(false);

  const selectedCard = useMemo(
    () => cards.find((card) => card.id === selectedCardId) ?? null,
    [cards, selectedCardId],
  );

  const loadCards = useCallback(async () => {
    setCardsLoading(true);
    setAppError(null);
    try {
      const result = await cardApi.list();
      setCards(result);
      setSelectedCardId((current) =>
        current !== null && result.some((card) => card.id === current) ? current : null,
      );
    } catch (error) {
      setAppError(getErrorMessage(error));
    } finally {
      setCardsLoading(false);
    }
  }, []);

  const loadDashboard = useCallback(async () => {
    setDashboardLoading(true);
    try {
      setDashboard(await dashboardApi.get());
    } catch (error) {
      setAppError(getErrorMessage(error));
    } finally {
      setDashboardLoading(false);
    }
  }, []);

  const loadCardContent = useCallback(async (cardId: number) => {
    const requestId = ++cardContentRequestId.current;
    setCardContentLoaded(false);
    setTopicsLoading(true);
    setConceptsLoading(true);
    setProblemsLoading(true);
    setNotesLoading(true);
    setWrongAnswersLoading(true);
    setWorkbooksLoading(true);
    setAppError(null);
    try {
      const [
        loadedTopics,
        loadedConcepts,
        loadedProblems,
        loadedNotes,
        loadedWrongAnswers,
        loadedWorkbooks,
        loadedWeakConcepts,
      ] = await Promise.all([
          topicApi.list(cardId),
          conceptApi.listForCard(cardId),
          problemApi.list(cardId),
          noteApi.list(cardId),
          wrongAnswerApi.list(cardId),
          workbookApi.list(cardId),
          conceptApi.cardWeakConcepts(cardId),
        ]);
      if (requestId !== cardContentRequestId.current) return;
      setTopics(loadedTopics);
      setConcepts(loadedConcepts);
      setProblems(loadedProblems);
      setNotes(loadedNotes);
      setWrongAnswers(loadedWrongAnswers);
      setWorkbooks(loadedWorkbooks);
      setWeakConcepts(loadedWeakConcepts);
      setCardContentLoaded(true);
    } catch (error) {
      if (requestId !== cardContentRequestId.current) return;
      setAppError(getErrorMessage(error));
    } finally {
      if (requestId === cardContentRequestId.current) {
        setTopicsLoading(false);
        setConceptsLoading(false);
        setProblemsLoading(false);
        setNotesLoading(false);
        setWrongAnswersLoading(false);
        setWorkbooksLoading(false);
      }
    }
  }, []);

  const clearCardState = useCallback(() => {
    cardContentRequestId.current += 1;
    setAppError(null);
    setSelectedCardId(null);
    setTopics([]);
    setConcepts([]);
    setProblems([]);
    setWeakConcepts([]);
    setNotes([]);
    setWrongAnswers([]);
    setWorkbooks([]);
    setTopicsLoading(false);
    setConceptsLoading(false);
    setProblemsLoading(false);
    setNotesLoading(false);
    setWrongAnswersLoading(false);
    setWorkbooksLoading(false);
    setCardContentLoaded(false);
    setTopicManagerOpen(false);
    setTopicManagerDescription(null);
    setConceptManagerOpen(false);
    setKnowledgeGraphOpen(false);
    setRandomStudyOpen(false);
    setWrongAnswerStudy(null);
    setWorkbookStudy(null);
    setActiveStudySessionId(null);
    setResumeStudySessionId(null);
    setContentView("dashboard");
    setNoteEditor(undefined);
    setNoteViewer(null);
    setSourceNoteForProblem(null);
  }, []);

  useEffect(() => {
    let ignore = false;

    profileApi
      .get()
      .then(async (loadedProfile) => {
        if (ignore) return;
        setProfile(loadedProfile);
        if (!loadedProfile.is_configured) {
          setCardsLoading(false);
          setDashboardLoading(false);
          return;
        }
        const [loadedCards, loadedDashboard] = await Promise.all([
          cardApi.list(),
          dashboardApi.get(),
        ]);
        if (ignore) return;
        setCards(loadedCards);
        setDashboard(loadedDashboard);
      })
      .catch((error: unknown) => {
        if (ignore) return;
        setAppError(getErrorMessage(error));
      })
      .finally(() => {
        if (!ignore) {
          setProfileLoading(false);
          setCardsLoading(false);
          setDashboardLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    const handleHashChange = () => setRouteRevision((current) => current + 1);
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  /* eslint-disable react-hooks/set-state-in-effect -- URL 해시를 화면 상태로 동기화하는 라우팅 효과입니다. */
  useEffect(() => {
    if (profileLoading || cardsLoading || !profile?.is_configured) return;

    const route = parseHashRoute(window.location.hash);
    if (route.page === "library") {
      if (selectedCardId !== null) {
        clearCardState();
        void loadDashboard();
      }
      return;
    }

    if (!cards.some((card) => card.id === route.cardId)) {
      replaceHash(getLibraryHash());
      if (selectedCardId !== null) clearCardState();
      return;
    }

    setContentView(route.view);
    if (selectedCardId !== route.cardId) {
      setTopics([]);
      setConcepts([]);
      setProblems([]);
      setNotes([]);
      setWrongAnswers([]);
      setWorkbooks([]);
      setSelectedCardId(route.cardId);
      setAppError(null);
      window.scrollTo({ top: 0, behavior: "auto" });
      void loadCardContent(route.cardId);
    }

    if (route.studySessionId) {
      setActiveStudySessionId(route.studySessionId);
      if (!randomStudyOpen && !wrongAnswerStudy && !conceptStudy && !workbookStudy) {
        setResumeStudySessionId(route.studySessionId);
        setRandomStudyOpen(true);
      }
    } else if (activeStudySessionId !== null) {
      setRandomStudyOpen(false);
      setWrongAnswerStudy(null);
      setConceptStudy(null);
      setWorkbookStudy(null);
      setActiveStudySessionId(null);
      setResumeStudySessionId(null);
    }
  }, [
    activeStudySessionId,
    cards,
    cardsLoading,
    clearCardState,
    conceptStudy,
    loadCardContent,
    loadDashboard,
    profile?.is_configured,
    profileLoading,
    randomStudyOpen,
    routeRevision,
    selectedCardId,
    workbookStudy,
    wrongAnswerStudy,
  ]);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (!profile?.is_configured) return;
    let ignore = false;
    graphSyncApi
      .status()
      .then((status) => {
        if (!ignore) setGraphSyncStatus(status);
      })
      .catch(() => {
        if (!ignore) setGraphSyncStatus(null);
      });
    return () => {
      ignore = true;
    };
  }, [profile?.is_configured]);

  const handleProfileSubmit = async (input: ProfileInput) => {
    const updated = await profileApi.update(input);
    setProfile(updated);
    setProfileEditorOpen(false);
    await Promise.all([loadCards(), loadDashboard()]);
  };

  useEffect(() => {
    const handleButtonPress = (event: PointerEvent) => {
      if (navigator.maxTouchPoints === 0 || typeof navigator.vibrate !== "function") return;
      const target = event.target instanceof Element
        ? event.target.closest<HTMLButtonElement>("button:not(:disabled)")
        : null;
      if (target) navigator.vibrate(8);
    };

    document.addEventListener("pointerdown", handleButtonPress, { passive: true });
    return () => document.removeEventListener("pointerdown", handleButtonPress);
  }, []);

  const handleCardSubmit = async (input: CardInput) => {
    if (cardEditor) {
      const updated = await cardApi.update(cardEditor.id, input);
      setCards((current) => current.map((card) => (card.id === updated.id ? updated : card)));
    } else {
      const created = await cardApi.create(input);
      setCards((current) => [created, ...current]);
    }
    setCardEditor(undefined);
    void loadDashboard();
  };

  const handleProblemSubmit = async (input: ProblemInput) => {
    if (!selectedCard) return;
    if (problemEditor) {
      const updated = await problemApi.update(selectedCard.id, problemEditor.id, input);
      setProblems((current) =>
        current.map((problem) => (problem.id === updated.id ? updated : problem)),
      );
      setWrongAnswers((current) =>
        current.map((wrongAnswer) =>
          wrongAnswer.problem_id === updated.id
            ? { ...wrongAnswer, problem: updated }
            : wrongAnswer,
        ),
      );
      setProblemEditor(undefined);
      setSourceNoteForProblem(null);
    } else {
      const created = await problemApi.create(selectedCard.id, input);
      setProblems((current) => [created, ...current]);
    }
  };

  const handleNoteSubmit = async (input: NoteInput) => {
    if (!selectedCard) return;
    if (noteEditor) {
      const updated = await noteApi.update(selectedCard.id, noteEditor.id, input);
      setNotes((current) =>
        current
          .map((note) => (note.id === updated.id ? updated : note))
          .sort((a, b) => b.updated_at.localeCompare(a.updated_at)),
      );
      setProblems((current) =>
        current.map((problem) =>
          problem.source_note_id === updated.id
            ? { ...problem, source_note_title: updated.title }
            : problem,
        ),
      );
      setWrongAnswers((current) =>
        current.map((wrongAnswer) =>
          wrongAnswer.problem.source_note_id === updated.id
            ? {
                ...wrongAnswer,
                problem: { ...wrongAnswer.problem, source_note_title: updated.title },
              }
            : wrongAnswer,
        ),
      );
    } else {
      const created = await noteApi.create(selectedCard.id, input);
      setNotes((current) => [created, ...current]);
    }
    setNoteEditor(undefined);
  };

  const handleTopicCreated = (topic: Topic) => {
    setTopics((current) => [...current, topic].sort((a, b) => a.id - b.id));
  };

  const handleCreateTopicForNote = async (name: string) => {
    if (!selectedCard) throw new Error("선택된 카드가 없습니다.");
    const created = await topicApi.create(selectedCard.id, { name });
    handleTopicCreated(created);
    return created;
  };

  const handleTopicUpdated = (topic: Topic) => {
    setTopics((current) =>
      current.map((currentTopic) => (currentTopic.id === topic.id ? topic : currentTopic)),
    );
    setProblems((current) =>
      current.map((problem) =>
        problem.topic_id === topic.id
          ? { ...problem, topic_name: topic.name }
          : problem,
      ),
    );
    setNotes((current) =>
      current.map((note) =>
        note.topic_id === topic.id
          ? { ...note, topic_name: topic.name }
          : note,
      ),
    );
    setWrongAnswers((current) =>
      current.map((wrongAnswer) =>
        wrongAnswer.problem.topic_id === topic.id
          ? {
              ...wrongAnswer,
              problem: { ...wrongAnswer.problem, topic_name: topic.name },
            }
          : wrongAnswer,
      ),
    );
  };

  const handleTopicDeleted = (topicId: number) => {
    setTopics((current) => current.filter((topic) => topic.id !== topicId));
    setNotes((current) =>
      current.map((note) =>
        note.topic_id === topicId
          ? { ...note, topic_id: null, topic_name: null }
          : note,
      ),
    );
  };

  const handleProblemStatisticsChanged = (updatedProblems: Problem[]) => {
    const updatesById = new Map(
      updatedProblems.map((problem) => [problem.id, problem]),
    );
    setProblems((current) =>
      current.map((problem) => {
        const updated = updatesById.get(problem.id);
        return updated
          ? {
              ...problem,
              presented_count: updated.presented_count,
              correct_count: updated.correct_count,
              incorrect_count: updated.incorrect_count,
            }
          : problem;
      }),
    );
    if (selectedCardId !== null) {
      setWrongAnswersLoading(true);
      wrongAnswerApi
        .list(selectedCardId)
        .then(setWrongAnswers)
        .catch((error: unknown) => setAppError(getErrorMessage(error)))
        .finally(() => setWrongAnswersLoading(false));
    }
  };

  const handleWrongAnswerUpdate = async (problemId: number, input: WrongAnswerInput) => {
    if (!selectedCard) return;
    const updated = await wrongAnswerApi.update(selectedCard.id, problemId, input);
    setWrongAnswers((current) =>
      current.map((wrongAnswer) =>
        wrongAnswer.problem_id === problemId ? updated : wrongAnswer,
      ),
    );
  };

  const refreshWorkbooks = useCallback(() => {
    if (selectedCardId === null) return;
    setWorkbooksLoading(true);
    workbookApi
      .list(selectedCardId)
      .then(setWorkbooks)
      .catch((error: unknown) => setAppError(getErrorMessage(error)))
      .finally(() => setWorkbooksLoading(false));
  }, [selectedCardId]);

  const handleDeleteWorkbook = async (workbook: Workbook) => {
    if (!selectedCard) return;
    await workbookApi.remove(selectedCard.id, workbook.id);
    setWorkbooks((current) => current.filter((item) => item.id !== workbook.id));
  };

  const openWrongAnswerStudy = (problemId?: number) => {
    const unresolvedCount = wrongAnswers.filter((item) => item.status !== "resolved").length;
    setWrongAnswerStudy({
      problemId,
      problemCount: problemId === undefined ? Math.max(unresolvedCount, 1) : 1,
    });
  };

  const openConceptStudy = (conceptId: number, conceptName: string) => {
    setConceptStudy({ conceptId, conceptName, problemCount: 20 });
  };

  const openWrongAnswerNote = (noteId: number) => {
    const note = notes.find((candidate) => candidate.id === noteId);
    if (note) setNoteViewer(note);
  };

  const handleDeleteCard = async () => {
    if (!cardToDelete) return;
    await cardApi.remove(cardToDelete.id);
    setCards((current) => current.filter((card) => card.id !== cardToDelete.id));
    if (selectedCardId === cardToDelete.id) {
      clearCardState();
      replaceHash(getLibraryHash());
    }
    setCardToDelete(null);
    void loadDashboard();
  };

  const handleDeleteProblem = async () => {
    if (!selectedCard || !problemToDelete) return;
    await problemApi.remove(selectedCard.id, problemToDelete.id);
    setProblems((current) => current.filter((problem) => problem.id !== problemToDelete.id));
    setWrongAnswers((current) =>
      current.filter((wrongAnswer) => wrongAnswer.problem_id !== problemToDelete.id),
    );
    setProblemToDelete(null);
  };

  const handleDeleteNote = async () => {
    if (!selectedCard || !noteToDelete) return;
    await noteApi.remove(selectedCard.id, noteToDelete.id);
    setNotes((current) => current.filter((note) => note.id !== noteToDelete.id));
    setProblems((current) =>
      current.map((problem) =>
        problem.source_note_id === noteToDelete.id
          ? { ...problem, source_note_id: null, source_note_title: null }
          : problem,
      ),
    );
    setWrongAnswers((current) =>
      current.map((wrongAnswer) =>
        wrongAnswer.problem.source_note_id === noteToDelete.id
          ? {
              ...wrongAnswer,
              problem: {
                ...wrongAnswer.problem,
                source_note_id: null,
                source_note_title: null,
              },
            }
          : wrongAnswer,
      ),
    );
    setNoteToDelete(null);
  };

  const openCard = (cardId: number, view: CardContentView = "dashboard") => {
    navigateToHash(getCardHash(cardId, view));
  };

  const closeCard = () => {
    if (window.location.hash === getLibraryHash() || !window.location.hash) {
      if (selectedCardId !== null) {
        clearCardState();
        void loadDashboard();
      }
      return;
    }
    navigateToHash(getLibraryHash());
  };

  const openContentView = (view: CardContentView) => {
    if (selectedCardId === null) return;
    navigateToHash(getCardHash(selectedCardId, view));
  };

  const handleStudySessionStarted = useCallback((sessionId: string) => {
    if (selectedCardId === null) return;
    setActiveStudySessionId(sessionId);
    setResumeStudySessionId(null);
    navigateToHash(getCardHash(selectedCardId, contentView, sessionId));
  }, [contentView, selectedCardId]);

  const openProblemCreator = () => {
    if (!cardContentLoaded || topicsLoading) return;
    if (topics.length === 0) {
      setTopicManagerDescription("문제를 만들려면 먼저 주제가 필요해요.");
      setTopicManagerOpen(true);
      return;
    }
    setSourceNoteForProblem(null);
    setProblemEditor(null);
  };

  const handleConceptsChanged = (nextConcepts: Concept[]) => {
    const nextConceptIds = new Set(nextConcepts.map((concept) => concept.id));
    setConcepts(nextConcepts);
    setProblems((current) =>
      current.map((problem) => ({
        ...problem,
        primary_concept_id:
          problem.primary_concept_id !== null
          && nextConceptIds.has(problem.primary_concept_id)
            ? problem.primary_concept_id
            : null,
        supporting_concept_ids: problem.supporting_concept_ids.filter(
          (conceptId) => nextConceptIds.has(conceptId),
        ),
      })),
    );
    setNotes((current) =>
      current.map((note) => ({
        ...note,
        concept_ids: note.concept_ids.filter((conceptId) => nextConceptIds.has(conceptId)),
      })),
    );
    setWrongAnswers((current) =>
      current.map((wrongAnswer) => ({
        ...wrongAnswer,
        problem: {
          ...wrongAnswer.problem,
          primary_concept_id:
            wrongAnswer.problem.primary_concept_id !== null
            && nextConceptIds.has(wrongAnswer.problem.primary_concept_id)
              ? wrongAnswer.problem.primary_concept_id
              : null,
          supporting_concept_ids:
            wrongAnswer.problem.supporting_concept_ids.filter(
              (conceptId) => nextConceptIds.has(conceptId),
            ),
        },
      })),
    );
  };

  const openProblemCreatorFromNote = (note: Note) => {
    setNoteViewer(null);
    if (topics.length === 0) {
      setSourceNoteForProblem(note);
      setTopicManagerDescription("노트에서 문제를 만들려면 먼저 주제가 필요해요.");
      setTopicManagerOpen(true);
      return;
    }
    setSourceNoteForProblem(note);
    setProblemEditor(null);
  };

  const openProblemEditor = (problem: Problem) => {
    setSourceNoteForProblem(
      notes.find((note) => note.id === problem.source_note_id) ?? null,
    );
    setProblemEditor(problem);
  };

  const graphSyncTone = !graphSyncStatus
    ? "unknown"
    : graphSyncStatus.failed_count
      ? "error"
      : !graphSyncStatus.worker_enabled
        ? "paused"
        : (graphSyncStatus.pending_count + graphSyncStatus.processing_count) > 0
          ? "working"
          : "ready";

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={closeCard}>
          <span className="brand-mark" aria-hidden="true">PB</span>
          <strong>나의 문제 은행</strong>
        </button>
        {profile?.is_configured && (
          <div className="topbar-actions">
            <button
              className={`graph-sync-trigger is-${graphSyncTone}`}
              type="button"
              onClick={() => setGraphSyncOpen(true)}
              aria-label="그래프 동기화 상태 열기"
              title="그래프 동기화"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="6" cy="12" r="2.5" />
                <circle cx="18" cy="6" r="2.5" />
                <circle cx="18" cy="18" r="2.5" />
                <path d="m8.2 10.8 7.6-3.6M8.2 13.2l7.6 3.6" />
              </svg>
              <span aria-hidden="true" />
            </button>
            <button
              className="profile-button"
              type="button"
              onClick={() => setProfileEditorOpen(true)}
              aria-label="프로필 설정 열기"
            >
              <span aria-hidden="true">{profile.display_name.slice(0, 1)}</span>
              <strong>{profile.display_name}</strong>
            </button>
          </div>
        )}
      </header>

      <main>
        {appError && (
          <div className="status-banner" role="alert">
            <span>{appError}</span>
            <button
              type="button"
              onClick={() => {
                if (selectedCardId !== null) {
                  void loadCardContent(selectedCardId);
                } else if (profile === null) {
                  window.location.reload();
                } else {
                  void Promise.all([loadCards(), loadDashboard()]);
                }
              }}
            >
              다시 시도
            </button>
          </div>
        )}

        {selectedCard ? (
          <section className="card-detail">
            <button className="back-link" type="button" onClick={closeCard}>
              카드 목록으로
            </button>

            <div className="detail-hero">
              <div>
                <p className="eyebrow">
                  Study card · {problems.length} problems · {notes.length} notes · {workbooks.length} books
                </p>
                <h1>{selectedCard.title}</h1>
                {selectedCard.description && <p>{selectedCard.description}</p>}
              </div>
              <div className="detail-actions">
                <button
                  className="button button--ghost"
                  type="button"
                  onClick={() => setConceptManagerOpen(true)}
                  disabled={!cardContentLoaded || conceptsLoading}
                >
                  개념 관리
                </button>
                <button
                  className="button button--ghost knowledge-graph-open"
                  type="button"
                  onClick={() => setKnowledgeGraphOpen(true)}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="6" cy="12" r="2.5" />
                    <circle cx="18" cy="6" r="2.5" />
                    <circle cx="18" cy="18" r="2.5" />
                    <path d="m8.2 10.8 7.6-3.6M8.2 13.2l7.6 3.6" />
                  </svg>
                  지식 그래프
                </button>
                <button className="button button--ghost" type="button" onClick={() => setCardEditor(selectedCard)}>
                  카드 수정
                </button>
                <button className="button button--danger-ghost" type="button" onClick={() => setCardToDelete(selectedCard)}>
                  카드 삭제
                </button>
              </div>
            </div>

            <nav className="content-switch" aria-label="카드 콘텐츠">
              <button
                className={contentView === "dashboard" ? "is-active" : ""}
                type="button"
                aria-current={contentView === "dashboard" ? "page" : undefined}
                onClick={() => openContentView("dashboard")}
              >
                대시보드
              </button>
              <button
                className={contentView === "problems" ? "is-active" : ""}
                type="button"
                aria-current={contentView === "problems" ? "page" : undefined}
                onClick={() => openContentView("problems")}
              >
                문제 <span>{problems.length}</span>
              </button>
              <button
                className={contentView === "notes" ? "is-active" : ""}
                type="button"
                aria-current={contentView === "notes" ? "page" : undefined}
                onClick={() => openContentView("notes")}
              >
                노트 <span>{notes.length}</span>
              </button>
              <button
                className={contentView === "wrongAnswers" ? "is-active" : ""}
                type="button"
                aria-current={contentView === "wrongAnswers" ? "page" : undefined}
                onClick={() => openContentView("wrongAnswers")}
              >
                오답노트 <span>{wrongAnswers.length}</span>
              </button>
              <button
                className={contentView === "workbooks" ? "is-active" : ""}
                type="button"
                aria-current={contentView === "workbooks" ? "page" : undefined}
                onClick={() => openContentView("workbooks")}
              >
                문제집 <span>{workbooks.length}</span>
              </button>
            </nav>

            {contentView === "dashboard" ? (
              <CardDashboard
                topics={topics}
                concepts={concepts}
                weakConcepts={weakConcepts}
                onStartConceptStudy={openConceptStudy}
                problems={problems}
                notes={notes}
                workbooks={workbooks}
                wrongAnswers={wrongAnswers}
                loading={
                  topicsLoading
                  || problemsLoading
                  || notesLoading
                  || workbooksLoading
                  || wrongAnswersLoading
                }
                loaded={cardContentLoaded}
                onCreateProblem={openProblemCreator}
                onCreateNote={() => setNoteEditor(null)}
                onCreateWorkbook={() => setRandomStudyOpen(true)}
                onOpenProblems={() => openContentView("problems")}
                onOpenWorkbooks={() => openContentView("workbooks")}
                onOpenWrongAnswers={() => openContentView("wrongAnswers")}
              />
            ) : contentView === "problems" ? (
              <>
            <div className="problem-toolbar">
              <div className="toolbar-actions">
                <button
                  className="button button--ghost"
                  type="button"
                  onClick={() => {
                    setTopicManagerDescription(null);
                    setTopicManagerOpen(true);
                  }}
                  disabled={!cardContentLoaded || topicsLoading}
                >
                  주제 관리
                </button>
                <button
                  className="button button--secondary"
                  type="button"
                  onClick={() => setRandomStudyOpen(true)}
                  disabled={!cardContentLoaded || problemsLoading || problems.length === 0}
                >
                  새 문제집
                </button>
                <button
                  className="button button--primary"
                  type="button"
                  onClick={openProblemCreator}
                  disabled={!cardContentLoaded || topicsLoading}
                >
                  {cardContentLoaded && topics.length === 0
                    ? "주제 먼저 만들기"
                    : "새 문제"}
                </button>
              </div>
            </div>

            <div className="section-heading">
              <div>
                <p className="eyebrow">Question archive</p>
                <h2>전체 문제</h2>
              </div>
              <span>{problems.length}개</span>
            </div>

            {problemsLoading || topicsLoading ? (
              <div className="problem-list" aria-label="문제 불러오는 중">
                {[1, 2, 3].map((item) => <div className="problem-skeleton" key={item} />)}
              </div>
            ) : !cardContentLoaded ? (
              <div className="empty-state empty-state--compact">
                <span className="empty-index" aria-hidden="true">!</span>
                <h3>카드 내용을 불러오지 못했어요</h3>
              </div>
            ) : problems.length > 0 ? (
              <div className="problem-list">
                {problems.map((problem, index) => (
                  <article className="problem-item" key={problem.id}>
                    <div className="problem-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</div>
                    <div className="problem-content">
                      <div className="problem-meta">
                        <span className="topic-badge">{problem.topic_name}</span>
                        <span className="problem-type-badge">
                          {problemTypeLabels[problem.problem_type]}
                        </span>
                        {problem.primary_concept_id !== null && (() => {
                          const primaryConcept = concepts.find(
                            (concept) => concept.id === problem.primary_concept_id,
                          );
                          return primaryConcept ? (
                            <span className="concept-badge">{primaryConcept.name}</span>
                          ) : null;
                        })()}
                        <span className="problem-date">
                          {dateFormatter.format(new Date(problem.created_at))}
                        </span>
                        <span
                          className="problem-statistics"
                          aria-label={`출제 ${problem.presented_count}회, 정답 ${problem.correct_count}회, 오답 ${problem.incorrect_count}회`}
                        >
                          <span>출제 <strong>{problem.presented_count}</strong></span>
                          <span>정답 <strong>{problem.correct_count}</strong></span>
                          <span>오답 <strong>{problem.incorrect_count}</strong></span>
                        </span>
                      </div>
                      <p className="problem-question">
                        <ProblemPrompt problem={problem} />
                      </p>
                      <ProblemOptions problem={problem} />
                      <details className="answer-details">
                        <summary>정답 · 해설 보기</summary>
                        <p>{problem.answer || "등록된 정답이나 해설이 없습니다."}</p>
                      </details>
                    </div>
                    <div className="item-actions">
                      <button type="button" onClick={() => openProblemEditor(problem)}>수정</button>
                      <button className="text-danger" type="button" onClick={() => setProblemToDelete(problem)}>삭제</button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <span className="empty-index" aria-hidden="true">?</span>
                <h3>
                  {topics.length === 0
                    ? "문제를 만들기 전에 주제를 추가해 주세요"
                    : "첫 문제를 만들어 보세요"}
                </h3>
              </div>
            )}
              </>
            ) : contentView === "notes" ? (
              <>
                <div className="problem-toolbar note-toolbar">
                  <div className="toolbar-actions">
                    <button
                      className="button button--primary"
                      type="button"
                      onClick={() => setNoteEditor(null)}
                      disabled={!cardContentLoaded || notesLoading}
                    >
                      새 노트
                    </button>
                  </div>
                </div>
                <NoteArchive
                  notes={notes}
                  concepts={concepts}
                  loading={notesLoading || topicsLoading}
                  loaded={cardContentLoaded}
                  onOpen={setNoteViewer}
                  onEdit={setNoteEditor}
                  onDelete={setNoteToDelete}
                />
              </>
            ) : contentView === "wrongAnswers" ? (
              <WrongAnswerArchive
                wrongAnswers={wrongAnswers}
                loading={wrongAnswersLoading || problemsLoading || topicsLoading}
                loaded={cardContentLoaded}
                onUpdate={handleWrongAnswerUpdate}
                onStudy={openWrongAnswerStudy}
                onOpenNote={openWrongAnswerNote}
                onManageTopics={() => {
                  setTopicManagerDescription(null);
                  setTopicManagerOpen(true);
                }}
              />
            ) : (
              <WorkbookArchive
                workbooks={workbooks}
                loading={workbooksLoading}
                loaded={cardContentLoaded}
                onCreate={() => setRandomStudyOpen(true)}
                onStudy={setWorkbookStudy}
                onDelete={handleDeleteWorkbook}
              />
            )}
          </section>
        ) : (
          <section className="library-view">
            {profileLoading || dashboardLoading ? (
              <div className="dashboard-skeleton" aria-label="대시보드 불러오는 중">
                <div />
                <div />
                <div />
              </div>
            ) : profile?.is_configured && dashboard ? (
              <>
                <div className="dashboard-hero">
                  <div className="dashboard-welcome">
                    <p className="eyebrow">My study dashboard</p>
                    <h1>{profile.display_name}님,<br />오늘도 한 걸음 쌓아볼까요?</h1>
                    <p>저장한 문제와 학습 기록을 한눈에 확인할 수 있어요.</p>
                    <button
                      className="button button--primary"
                      type="button"
                      onClick={() => setCardEditor(null)}
                    >
                      새 카드 만들기
                    </button>
                  </div>
                  <div className="daily-goal-card">
                    <span>오늘의 학습</span>
                    <strong>
                      {dashboard.today_studied_count}
                      <small> / {profile.daily_goal}문제</small>
                    </strong>
                    <div
                      className="goal-progress"
                      role="progressbar"
                      aria-label="오늘의 학습 목표 달성률"
                      aria-valuemin={0}
                      aria-valuemax={profile.daily_goal}
                      aria-valuenow={Math.min(dashboard.today_studied_count, profile.daily_goal)}
                    >
                      <span
                        style={{
                          width: `${Math.min(
                            dashboard.today_studied_count / profile.daily_goal * 100,
                            100,
                          )}%`,
                        }}
                      />
                    </div>
                    <p>
                      {dashboard.today_studied_count >= profile.daily_goal
                        ? "오늘 목표를 달성했어요. 멋진 흐름이에요!"
                        : `${profile.daily_goal - dashboard.today_studied_count}문제 더 풀면 오늘 목표를 달성해요.`}
                    </p>
                  </div>
                </div>

                <div className="dashboard-stat-grid" aria-label="전체 학습 현황">
                  <article>
                    <span>공부 카드</span>
                    <strong>{dashboard.card_count}</strong>
                    <small>주제 {dashboard.topic_count}개</small>
                  </article>
                  <article>
                    <span>전체 문제</span>
                    <strong>{dashboard.problem_count}</strong>
                    <small>노트 {dashboard.note_count}개</small>
                  </article>
                  <article>
                    <span>문제집</span>
                    <strong>{dashboard.workbook_count}</strong>
                    <small>완료 {dashboard.completed_session_count}회</small>
                  </article>
                  <article>
                    <span>전체 정답률</span>
                    <strong>{dashboard.accuracy_rate}%</strong>
                    <small>정답 {dashboard.correct_count} · 오답 {dashboard.incorrect_count}</small>
                  </article>
                  <article>
                    <span>복습할 오답</span>
                    <strong>{dashboard.unresolved_wrong_answer_count}</strong>
                    <small>미해결 문제</small>
                  </article>
                  <article>
                    <span>오늘 학습</span>
                    <strong>{dashboard.today_studied_count}</strong>
                    <small>목표 {profile.daily_goal}문제</small>
                  </article>
                </div>

                <div className="dashboard-overview-grid">
                  <section className="dashboard-overview-panel">
                    <div className="dashboard-panel-heading">
                      <div>
                        <p className="eyebrow">Recent study</p>
                        <h2>최근 학습</h2>
                      </div>
                      <span>{dashboard.completed_session_count}회 완료</span>
                    </div>
                    {dashboard.recent_studies.length > 0 ? (
                      <div className="dashboard-activity-list">
                        {dashboard.recent_studies.map((study) => {
                          const gradedCount = study.correct_count + study.incorrect_count;
                          return (
                            <button
                              key={study.session_id}
                              type="button"
                              onClick={() => openCard(study.card_id)}
                            >
                              <span className="dashboard-activity-main">
                                <strong>{study.workbook_title ?? "개별 학습"}</strong>
                                <small>
                                  {study.card_title} · {activityDateFormatter.format(new Date(study.completed_at))}
                                </small>
                              </span>
                              <span className="dashboard-activity-score">
                                <strong>
                                  {gradedCount > 0
                                    ? `${study.correct_count} / ${gradedCount}`
                                    : "직접 채점"}
                                </strong>
                                <small>{study.problem_count}문제</small>
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="dashboard-panel-empty">완료한 학습이 없습니다.</p>
                    )}
                  </section>

                  <section className="dashboard-overview-panel">
                    <div className="dashboard-panel-heading">
                      <div>
                        <p className="eyebrow">Card overview</p>
                        <h2>카드별 현황</h2>
                      </div>
                      <span>{dashboard.card_count}개</span>
                    </div>
                    {dashboard.cards.length > 0 ? (
                      <div className="dashboard-card-summary-list">
                        {dashboard.cards.slice(0, 6).map((card) => (
                          <button
                            key={card.card_id}
                            type="button"
                            onClick={() => openCard(card.card_id)}
                          >
                            <span>
                              <strong>{card.card_title}</strong>
                              <small>
                                문제 {card.problem_count} · 문제집 {card.workbook_count} · 노트 {card.note_count}
                              </small>
                            </span>
                            <span>
                              <strong>
                                {card.correct_count + card.incorrect_count > 0
                                  ? `${card.accuracy_rate}%`
                                  : "-"}
                              </strong>
                              <small>오답 {card.unresolved_wrong_answer_count}</small>
                            </span>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <p className="dashboard-panel-empty">등록된 카드가 없습니다.</p>
                    )}
                  </section>
                </div>

                <section className="weak-topic-panel">
                  <div>
                    <p className="eyebrow">Focus next</p>
                    <h2>조금 더 살펴볼 주제</h2>
                  </div>
                  {dashboard.weak_topics.length > 0 ? (
                    <div className="weak-topic-list">
                      {dashboard.weak_topics.map((topic) => (
                        <button
                          className={
                            topic.accuracy_rate < 50
                              ? "is-critical"
                              : topic.accuracy_rate < 80
                                ? "is-watch"
                                : "is-stable"
                          }
                          key={topic.topic_id}
                          type="button"
                          onClick={() => openCard(topic.card_id)}
                        >
                          <span>{topic.card_title} · {topic.topic_name}</span>
                          <strong>{topic.accuracy_rate}%</strong>
                          <small>{topic.graded_count}회 채점 · 문제 {topic.problem_count}개</small>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="weak-topic-empty">
                      문제를 풀고 채점하면 정답률이 낮은 주제를 여기서 알려드려요.
                    </p>
                  )}
                </section>

                <section className="weak-topic-panel">
                  <div>
                    <p className="eyebrow">Weak concepts</p>
                    <h2>약한 개념</h2>
                  </div>
                  {dashboard.weak_concepts.length > 0 ? (
                    <div className="weak-concept-list">
                      {dashboard.weak_concepts.map((concept) => {
                        const percent = Math.round(concept.mastery_score * 100);
                        const lowSample = concept.graded_count < LOW_SAMPLE_THRESHOLD;
                        return (
                          <div className="weak-concept-item" key={concept.concept_id}>
                            <span
                              aria-hidden="true"
                              className="weak-concept-swatch"
                              style={{ backgroundColor: masteryColor(concept.mastery_score) }}
                            />
                            <span className="weak-concept-name">{concept.name}</span>
                            <strong>{lowSample ? "~" : ""}{percent}%</strong>
                            <small>
                              {concept.graded_count}회 채점 · 문제 {concept.problem_count}개
                            </small>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="weak-topic-empty">
                      문제에 개념을 연결하고 채점하면 약한 개념을 여기서 알려드려요.
                    </p>
                  )}
                </section>
              </>
            ) : null}

            <div className="section-heading library-heading">
              <div>
                <p className="eyebrow">My library</p>
                <h2>공부 카드</h2>
              </div>
              <span>{cards.length}개</span>
            </div>

            {cardsLoading ? (
              <div className="card-grid" aria-label="카드 불러오는 중">
                {[1, 2, 3].map((item) => <div className="card-skeleton" key={item} />)}
              </div>
            ) : cards.length > 0 ? (
              <div className="card-grid">
                {cards.map((card, index) => (
                  <article className="study-card" key={card.id}>
                    <button className="card-open" type="button" onClick={() => openCard(card.id)}>
                      <span className="card-index">{String(index + 1).padStart(2, "0")}</span>
                      <div>
                        <h3>{card.title}</h3>
                        {card.description && <p>{card.description}</p>}
                      </div>
                      <span className="card-date">{dateFormatter.format(new Date(card.updated_at))}</span>
                    </button>
                    <div className="card-actions">
                      <button type="button" onClick={() => setCardEditor(card)}>수정</button>
                      <button className="text-danger" type="button" onClick={() => setCardToDelete(card)}>삭제</button>
                      <button className="open-label" type="button" onClick={() => openCard(card.id)}>열기</button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state empty-state--library">
                <span className="empty-index" aria-hidden="true">01</span>
                <h3>아직 공부 카드가 없어요</h3>
                <button className="button button--primary" type="button" onClick={() => setCardEditor(null)}>
                  카드 만들기
                </button>
              </div>
            )}
          </section>
        )}
      </main>

      <footer>
        <span>Problem Bank</span>
      </footer>

      {profile && (!profile.is_configured || profileEditorOpen) && (
        <ProfileFormModal
          profile={profile}
          initialSetup={!profile.is_configured}
          onClose={() => setProfileEditorOpen(false)}
          onSubmit={handleProfileSubmit}
        />
      )}
      {graphSyncOpen && (
        <GraphSyncModal
          initialStatus={graphSyncStatus}
          onStatusChange={setGraphSyncStatus}
          onClose={() => setGraphSyncOpen(false)}
        />
      )}
      {knowledgeGraphOpen && selectedCard && (
        <KnowledgeGraphModal
          card={selectedCard}
          onClose={() => setKnowledgeGraphOpen(false)}
        />
      )}
      {cardEditor !== undefined && (
        <CardFormModal card={cardEditor} onClose={() => setCardEditor(undefined)} onSubmit={handleCardSubmit} />
      )}
      {problemEditor !== undefined && (
        <ProblemFormModal
          problem={problemEditor}
          topics={topics}
          concepts={concepts}
          sourceNote={sourceNoteForProblem}
          onClose={() => {
            setProblemEditor(undefined);
            setSourceNoteForProblem(null);
          }}
          onSubmit={handleProblemSubmit}
        />
      )}
      {noteEditor !== undefined && (
        <NoteFormModal
          note={noteEditor}
          topics={topics}
          concepts={concepts}
          onClose={() => setNoteEditor(undefined)}
          onCreateTopic={handleCreateTopicForNote}
          onSubmit={handleNoteSubmit}
        />
      )}
      {noteViewer && (
        <NoteDetailModal
          note={noteViewer}
          concepts={concepts}
          onClose={() => setNoteViewer(null)}
          onEdit={() => {
            setNoteEditor(noteViewer);
            setNoteViewer(null);
          }}
          onDelete={() => {
            setNoteToDelete(noteViewer);
            setNoteViewer(null);
          }}
          onCreateProblem={() => openProblemCreatorFromNote(noteViewer)}
        />
      )}
      {conceptManagerOpen && selectedCard && (
        <ConceptManagementModal
          card={selectedCard}
          concepts={concepts}
          onChanged={handleConceptsChanged}
          onClose={() => setConceptManagerOpen(false)}
        />
      )}
      {cardToDelete && (
        <ConfirmDialog
          title="카드를 삭제할까요?"
          message={`‘${cardToDelete.title}’ 카드 안의 주제와 문제, 노트도 모두 삭제됩니다. 이 작업은 되돌릴 수 없습니다.`}
          confirmLabel="카드 내용 삭제"
          onClose={() => setCardToDelete(null)}
          onConfirm={handleDeleteCard}
        />
      )}
      {problemToDelete && (
        <ConfirmDialog
          title="문제를 삭제할까요?"
          message="이 문제와 등록된 정답·해설이 함께 삭제됩니다."
          confirmLabel="문제 삭제"
          onClose={() => setProblemToDelete(null)}
          onConfirm={handleDeleteProblem}
        />
      )}
      {noteToDelete && (
        <ConfirmDialog
          title="노트를 삭제할까요?"
          message="노트에서 만든 문제는 유지되고 참고 노트 연결만 해제됩니다."
          confirmLabel="노트 삭제"
          onClose={() => setNoteToDelete(null)}
          onConfirm={handleDeleteNote}
        />
      )}
      {(randomStudyOpen || wrongAnswerStudy || conceptStudy || workbookStudy) && selectedCard && (
        <RandomStudyModal
          card={selectedCard}
          topics={topics}
          availableProblems={problems}
          onStatisticsChanged={handleProblemStatisticsChanged}
          onSessionStarted={handleStudySessionStarted}
          wrongAnswerStudy={wrongAnswerStudy ?? undefined}
          conceptStudy={conceptStudy ?? undefined}
          workbookStudy={workbookStudy ?? undefined}
          resumeSessionId={resumeStudySessionId ?? undefined}
          onWorkbooksChanged={refreshWorkbooks}
          onClose={() => {
            setRandomStudyOpen(false);
            setWrongAnswerStudy(null);
            setConceptStudy(null);
            setWorkbookStudy(null);
            setActiveStudySessionId(null);
            setResumeStudySessionId(null);
            navigateToHash(getCardHash(selectedCard.id, contentView));
          }}
        />
      )}
      {topicManagerOpen && selectedCard && (
        <TopicManagementModal
          card={selectedCard}
          topics={topics}
          description={topicManagerDescription ?? undefined}
          onCreated={handleTopicCreated}
          onUpdated={handleTopicUpdated}
          onDeleted={handleTopicDeleted}
          onClose={() => {
            setTopicManagerOpen(false);
            setTopicManagerDescription(null);
            if (sourceNoteForProblem && topics.length > 0) {
              setProblemEditor(null);
            } else if (sourceNoteForProblem) {
              setSourceNoteForProblem(null);
            }
          }}
        />
      )}
    </div>
  );
}

export default App;
