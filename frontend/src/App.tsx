import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { cardApi, getErrorMessage, problemApi, topicApi } from "./api/client";
import { CardFormModal } from "./components/CardFormModal";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { ProblemFormModal } from "./components/ProblemFormModal";
import { ProblemOptions } from "./components/ProblemOptions";
import { ProblemPrompt } from "./components/ProblemPrompt";
import { RandomStudyModal } from "./components/RandomStudyModal";
import { TopicManagementModal } from "./components/TopicManagementModal";
import { problemTypeLabels } from "./problemTypes";
import type { Card, CardInput, Problem, ProblemInput, Topic } from "./types";

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
  const [cardContentLoaded, setCardContentLoaded] = useState(false);
  const cardContentRequestId = useRef(0);

  const [cardEditor, setCardEditor] = useState<Card | null | undefined>(undefined);
  const [problemEditor, setProblemEditor] = useState<Problem | null | undefined>(undefined);
  const [cardToDelete, setCardToDelete] = useState<Card | null>(null);
  const [problemToDelete, setProblemToDelete] = useState<Problem | null>(null);
  const [randomStudyOpen, setRandomStudyOpen] = useState(false);
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
    setAppError(null);
    try {
      const [loadedTopics, loadedProblems] = await Promise.all([
        topicApi.list(cardId),
        problemApi.list(cardId),
      ]);
      if (requestId !== cardContentRequestId.current) return;
      setTopics(loadedTopics);
      setProblems(loadedProblems);
      setCardContentLoaded(true);
    } catch (error) {
      if (requestId !== cardContentRequestId.current) return;
      setAppError(getErrorMessage(error));
    } finally {
      if (requestId === cardContentRequestId.current) {
        setTopicsLoading(false);
        setProblemsLoading(false);
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

  useEffect(() => {
    if (selectedCardId === null) return;

    const requestId = ++cardContentRequestId.current;
    Promise.all([topicApi.list(selectedCardId), problemApi.list(selectedCardId)])
      .then(([loadedTopics, loadedProblems]) => {
        if (requestId !== cardContentRequestId.current) return;
        setTopics(loadedTopics);
        setProblems(loadedProblems);
        setCardContentLoaded(true);
      })
      .catch((error: unknown) => {
        if (requestId !== cardContentRequestId.current) return;
        setAppError(getErrorMessage(error));
      })
      .finally(() => {
        if (requestId === cardContentRequestId.current) {
          setTopicsLoading(false);
          setProblemsLoading(false);
        }
      });

    return () => {
      cardContentRequestId.current += 1;
    };
  }, [loadCardContent, selectedCardId]);

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
      setProblemEditor(undefined);
    } else {
      const created = await problemApi.create(selectedCard.id, input);
      setProblems((current) => [created, ...current]);
    }
  };

  const handleTopicCreated = (topic: Topic) => {
    setTopics((current) => [...current, topic].sort((a, b) => a.id - b.id));
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
  };

  const handleTopicDeleted = (topicId: number) => {
    setTopics((current) => current.filter((topic) => topic.id !== topicId));
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
      setTopicsLoading(false);
      setProblemsLoading(false);
      setCardContentLoaded(false);
    }
    setCardToDelete(null);
  };

  const handleDeleteProblem = async () => {
    if (!selectedCard || !problemToDelete) return;
    await problemApi.remove(selectedCard.id, problemToDelete.id);
    setProblems((current) => current.filter((problem) => problem.id !== problemToDelete.id));
    setProblemToDelete(null);
  };

  const openCard = (cardId: number) => {
    setTopics([]);
    setProblems([]);
    setTopicsLoading(true);
    setProblemsLoading(true);
    setCardContentLoaded(false);
    setAppError(null);
    setSelectedCardId(cardId);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const closeCard = () => {
    cardContentRequestId.current += 1;
    setAppError(null);
    setSelectedCardId(null);
    setTopics([]);
    setProblems([]);
    setTopicsLoading(false);
    setProblemsLoading(false);
    setCardContentLoaded(false);
    setTopicManagerOpen(false);
    setRandomStudyOpen(false);
  };

  const openProblemCreator = () => {
    if (!cardContentLoaded || topicsLoading) return;
    if (topics.length === 0) {
      setTopicManagerOpen(true);
      return;
    }
    setProblemEditor(null);
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
                <p className="eyebrow">Study card · {problems.length} problems</p>
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
                  랜덤 문제 풀기
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
                      <button type="button" onClick={() => setProblemEditor(problem)}>수정</button>
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
          onClose={() => setProblemEditor(undefined)}
          onSubmit={handleProblemSubmit}
        />
      )}
      {cardToDelete && (
        <ConfirmDialog
          title="카드를 삭제할까요?"
          message={`‘${cardToDelete.title}’ 카드 안의 주제와 문제도 모두 삭제됩니다. 이 작업은 되돌릴 수 없습니다.`}
          confirmLabel="카드와 문제 삭제"
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
      {randomStudyOpen && selectedCard && (
        <RandomStudyModal
          card={selectedCard}
          topics={topics}
          onStatisticsChanged={handleProblemStatisticsChanged}
          onClose={() => setRandomStudyOpen(false)}
        />
      )}
      {topicManagerOpen && selectedCard && (
        <TopicManagementModal
          card={selectedCard}
          topics={topics}
          onCreated={handleTopicCreated}
          onUpdated={handleTopicUpdated}
          onDeleted={handleTopicDeleted}
          onClose={() => setTopicManagerOpen(false)}
        />
      )}
    </div>
  );
}

export default App;
