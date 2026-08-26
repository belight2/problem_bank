import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  cardApi,
  getErrorMessage,
  noteApi,
  problemApi,
  topicApi,
  workbookApi,
  wrongAnswerApi,
} from "./api/client";
import { CardFormModal } from "./components/CardFormModal";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { NoteArchive } from "./components/NoteArchive";
import { NoteDetailModal } from "./components/NoteDetailModal";
import { NoteFormModal } from "./components/NoteFormModal";
import { ProblemFormModal } from "./components/ProblemFormModal";
import { ProblemOptions } from "./components/ProblemOptions";
import { ProblemPrompt } from "./components/ProblemPrompt";
import { RandomStudyModal } from "./components/RandomStudyModal";
import { TopicManagementModal } from "./components/TopicManagementModal";
import { WorkbookArchive } from "./components/WorkbookArchive";
import { WrongAnswerArchive } from "./components/WrongAnswerArchive";
import { problemTypeLabels } from "./problemTypes";
import type {
  Card,
  CardInput,
  Note,
  NoteInput,
  Problem,
  ProblemInput,
  Topic,
  Workbook,
  WorkbookStudyRequest,
  WrongAnswer,
  WrongAnswerInput,
  WrongAnswerStudyRequest,
} from "./types";

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

function App() {
  const [cards, setCards] = useState<Card[]>([]);
  const [cardsLoading, setCardsLoading] = useState(true);
  const [appError, setAppError] = useState<string | null>(null);
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [problemsLoading, setProblemsLoading] = useState(false);
  const [notes, setNotes] = useState<Note[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [wrongAnswers, setWrongAnswers] = useState<WrongAnswer[]>([]);
  const [wrongAnswersLoading, setWrongAnswersLoading] = useState(false);
  const [workbooks, setWorkbooks] = useState<Workbook[]>([]);
  const [workbooksLoading, setWorkbooksLoading] = useState(false);
  const [cardContentLoaded, setCardContentLoaded] = useState(false);
  const [contentView, setContentView] = useState<
    "problems" | "notes" | "wrongAnswers" | "workbooks"
  >("problems");
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
  const [workbookStudy, setWorkbookStudy] = useState<WorkbookStudyRequest | null>(null);
  const [topicManagerOpen, setTopicManagerOpen] = useState(false);

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

  const loadCardContent = useCallback(async (cardId: number) => {
    const requestId = ++cardContentRequestId.current;
    setCardContentLoaded(false);
    setTopicsLoading(true);
    setProblemsLoading(true);
    setNotesLoading(true);
    setWrongAnswersLoading(true);
    setWorkbooksLoading(true);
    setAppError(null);
    try {
      const [
        loadedTopics,
        loadedProblems,
        loadedNotes,
        loadedWrongAnswers,
        loadedWorkbooks,
      ] = await Promise.all([
          topicApi.list(cardId),
          problemApi.list(cardId),
          noteApi.list(cardId),
          wrongAnswerApi.list(cardId),
          workbookApi.list(cardId),
        ]);
      if (requestId !== cardContentRequestId.current) return;
      setTopics(loadedTopics);
      setProblems(loadedProblems);
      setNotes(loadedNotes);
      setWrongAnswers(loadedWrongAnswers);
      setWorkbooks(loadedWorkbooks);
      setCardContentLoaded(true);
    } catch (error) {
      if (requestId !== cardContentRequestId.current) return;
      setAppError(getErrorMessage(error));
    } finally {
      if (requestId === cardContentRequestId.current) {
        setTopicsLoading(false);
        setProblemsLoading(false);
        setNotesLoading(false);
        setWrongAnswersLoading(false);
        setWorkbooksLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let ignore = false;

    cardApi
      .list()
      .then((result) => {
        if (ignore) return;
        setCards(result);
      })
      .catch((error: unknown) => {
        if (ignore) return;
        setAppError(getErrorMessage(error));
      })
      .finally(() => {
        if (!ignore) setCardsLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, []);

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

  const openWrongAnswerNote = (noteId: number) => {
    const note = notes.find((candidate) => candidate.id === noteId);
    if (note) setNoteViewer(note);
  };

  const handleDeleteCard = async () => {
    if (!cardToDelete) return;
    await cardApi.remove(cardToDelete.id);
    setCards((current) => current.filter((card) => card.id !== cardToDelete.id));
    if (selectedCardId === cardToDelete.id) {
      cardContentRequestId.current += 1;
      setSelectedCardId(null);
      setTopics([]);
      setProblems([]);
      setNotes([]);
      setWrongAnswers([]);
      setWorkbooks([]);
      setTopicsLoading(false);
      setProblemsLoading(false);
      setNotesLoading(false);
      setWrongAnswersLoading(false);
      setWorkbooksLoading(false);
      setCardContentLoaded(false);
    }
    setCardToDelete(null);
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

  const openCard = (cardId: number) => {
    setTopics([]);
    setProblems([]);
    setNotes([]);
    setWrongAnswers([]);
    setWorkbooks([]);
    setTopicsLoading(true);
    setProblemsLoading(true);
    setNotesLoading(true);
    setWrongAnswersLoading(true);
    setWorkbooksLoading(true);
    setCardContentLoaded(false);
    setAppError(null);
    setSelectedCardId(cardId);
    setContentView("problems");
    window.scrollTo({ top: 0, behavior: "smooth" });
    void loadCardContent(cardId);
  };

  const closeCard = () => {
    cardContentRequestId.current += 1;
    setAppError(null);
    setSelectedCardId(null);
    setTopics([]);
    setProblems([]);
    setNotes([]);
    setWrongAnswers([]);
    setWorkbooks([]);
    setTopicsLoading(false);
    setProblemsLoading(false);
    setNotesLoading(false);
    setWrongAnswersLoading(false);
    setWorkbooksLoading(false);
    setCardContentLoaded(false);
    setTopicManagerOpen(false);
    setRandomStudyOpen(false);
    setWrongAnswerStudy(null);
    setWorkbookStudy(null);
    setContentView("problems");
    setNoteEditor(undefined);
    setNoteViewer(null);
    setSourceNoteForProblem(null);
  };

  const openProblemCreator = () => {
    if (!cardContentLoaded || topicsLoading) return;
    if (topics.length === 0) {
      setTopicManagerOpen(true);
      return;
    }
    setSourceNoteForProblem(null);
    setProblemEditor(null);
  };

  const openProblemCreatorFromNote = (note: Note) => {
    setNoteViewer(null);
    if (topics.length === 0) {
      setSourceNoteForProblem(note);
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

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={closeCard}>
          <span className="brand-mark" aria-hidden="true">PB</span>
          <strong>나의 문제 은행</strong>
        </button>
      </header>

      <main>
        {appError && (
          <div className="status-banner" role="alert">
            <span>{appError}</span>
            <button
              type="button"
              onClick={() =>
                selectedCardId === null
                  ? void loadCards()
                  : void loadCardContent(selectedCardId)
              }
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
                className={contentView === "problems" ? "is-active" : ""}
                type="button"
                aria-current={contentView === "problems" ? "page" : undefined}
                onClick={() => setContentView("problems")}
              >
                문제 <span>{problems.length}</span>
              </button>
              <button
                className={contentView === "notes" ? "is-active" : ""}
                type="button"
                aria-current={contentView === "notes" ? "page" : undefined}
                onClick={() => setContentView("notes")}
              >
                노트 <span>{notes.length}</span>
              </button>
              <button
                className={contentView === "wrongAnswers" ? "is-active" : ""}
                type="button"
                aria-current={contentView === "wrongAnswers" ? "page" : undefined}
                onClick={() => setContentView("wrongAnswers")}
              >
                오답노트 <span>{wrongAnswers.length}</span>
              </button>
              <button
                className={contentView === "workbooks" ? "is-active" : ""}
                type="button"
                aria-current={contentView === "workbooks" ? "page" : undefined}
                onClick={() => setContentView("workbooks")}
              >
                문제집 <span>{workbooks.length}</span>
              </button>
            </nav>

            {contentView === "problems" ? (
              <>
            <div className="problem-toolbar">
              <div className="toolbar-actions">
                <button
                  className="button button--ghost"
                  type="button"
                  onClick={() => setTopicManagerOpen(true)}
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
                <button
                  className="button button--primary"
                  type="button"
                  onClick={openProblemCreator}
                  disabled={!cardContentLoaded || topicsLoading}
                >
                  {topics.length === 0 ? "주제 만들기" : "문제 만들기"}
                </button>
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
                  loading={notesLoading || topicsLoading}
                  loaded={cardContentLoaded}
                  onOpen={setNoteViewer}
                  onEdit={setNoteEditor}
                  onDelete={setNoteToDelete}
                  onCreate={() => setNoteEditor(null)}
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
                onManageTopics={() => setTopicManagerOpen(true)}
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
            <div className="library-hero">
              <div>
                <p className="eyebrow">Personal study archive</p>
                <h1>배운 것을<br />내 문제로 남기세요.</h1>
              </div>
              <div className="hero-note">
                <button className="button button--primary" type="button" onClick={() => setCardEditor(null)}>
                  카드 만들기
                </button>
              </div>
            </div>

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

      {cardEditor !== undefined && (
        <CardFormModal card={cardEditor} onClose={() => setCardEditor(undefined)} onSubmit={handleCardSubmit} />
      )}
      {problemEditor !== undefined && (
        <ProblemFormModal
          problem={problemEditor}
          topics={topics}
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
          onClose={() => setNoteEditor(undefined)}
          onCreateTopic={handleCreateTopicForNote}
          onSubmit={handleNoteSubmit}
        />
      )}
      {noteViewer && (
        <NoteDetailModal
          note={noteViewer}
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
      {(randomStudyOpen || wrongAnswerStudy || workbookStudy) && selectedCard && (
        <RandomStudyModal
          card={selectedCard}
          topics={topics}
          availableProblems={problems}
          onStatisticsChanged={handleProblemStatisticsChanged}
          wrongAnswerStudy={wrongAnswerStudy ?? undefined}
          workbookStudy={workbookStudy ?? undefined}
          onWorkbooksChanged={refreshWorkbooks}
          onClose={() => {
            setRandomStudyOpen(false);
            setWrongAnswerStudy(null);
            setWorkbookStudy(null);
          }}
        />
      )}
      {topicManagerOpen && selectedCard && (
        <TopicManagementModal
          card={selectedCard}
          topics={topics}
          onCreated={handleTopicCreated}
          onUpdated={handleTopicUpdated}
          onDeleted={handleTopicDeleted}
          onClose={() => {
            setTopicManagerOpen(false);
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
