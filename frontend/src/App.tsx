import { useCallback, useEffect, useMemo, useState } from "react";

import { cardApi, getErrorMessage, problemApi } from "./api/client";
import { CardFormModal } from "./components/CardFormModal";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { ProblemFormModal } from "./components/ProblemFormModal";
import { RandomStudyModal } from "./components/RandomStudyModal";
import type { Card, CardInput, Problem, ProblemInput } from "./types";

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
  const [problems, setProblems] = useState<Problem[]>([]);
  const [problemsLoading, setProblemsLoading] = useState(false);

  const [cardEditor, setCardEditor] = useState<Card | null | undefined>(undefined);
  const [problemEditor, setProblemEditor] = useState<Problem | null | undefined>(undefined);
  const [cardToDelete, setCardToDelete] = useState<Card | null>(null);
  const [problemToDelete, setProblemToDelete] = useState<Problem | null>(null);
  const [randomStudyOpen, setRandomStudyOpen] = useState(false);

  const selectedCard = useMemo(
    () => cards.find((card) => card.id === selectedCardId) ?? null,
    [cards, selectedCardId],
  );

  const topics = useMemo(
    () => [...new Set(problems.map((problem) => problem.topic))].sort((a, b) =>
      a.localeCompare(b, "ko"),
    ),
    [problems],
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

  const loadProblems = useCallback(async (cardId: number) => {
    setProblemsLoading(true);
    setAppError(null);
    try {
      setProblems(await problemApi.list(cardId));
    } catch (error) {
      setAppError(getErrorMessage(error));
    } finally {
      setProblemsLoading(false);
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
    if (selectedCardId === null) return;

    let ignore = false;
    problemApi
      .list(selectedCardId)
      .then((result) => {
        if (!ignore) setProblems(result);
      })
      .catch((error: unknown) => {
        if (!ignore) setAppError(getErrorMessage(error));
      })
      .finally(() => {
        if (!ignore) setProblemsLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [selectedCardId]);

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
    } else {
      const created = await problemApi.create(selectedCard.id, input);
      setProblems((current) => [created, ...current]);
    }
    setProblemEditor(undefined);
  };

  const handleDeleteCard = async () => {
    if (!cardToDelete) return;
    await cardApi.remove(cardToDelete.id);
    setCards((current) => current.filter((card) => card.id !== cardToDelete.id));
    if (selectedCardId === cardToDelete.id) setSelectedCardId(null);
    setCardToDelete(null);
  };

  const handleDeleteProblem = async () => {
    if (!selectedCard || !problemToDelete) return;
    await problemApi.remove(selectedCard.id, problemToDelete.id);
    setProblems((current) => current.filter((problem) => problem.id !== problemToDelete.id));
    setProblemToDelete(null);
  };

  const openCard = (cardId: number) => {
    setProblems([]);
    setProblemsLoading(true);
    setAppError(null);
    setSelectedCardId(cardId);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={() => setSelectedCardId(null)}>
          <span className="brand-mark" aria-hidden="true">PB</span>
          <span>
            <strong>나의 문제 은행</strong>
            <small>직접 만들고, 가볍게 반복하기</small>
          </span>
        </button>
        <button className="button button--primary button--compact" type="button" onClick={() => setCardEditor(null)}>
          새 카드
        </button>
      </header>

      <main>
        {appError && (
          <div className="status-banner" role="alert">
            <span>{appError}</span>
            <button
              type="button"
              onClick={() => selectedCardId === null ? void loadCards() : void loadProblems(selectedCardId)}
            >
              다시 시도
            </button>
          </div>
        )}

        {selectedCard ? (
          <section className="card-detail">
            <button className="back-link" type="button" onClick={() => setSelectedCardId(null)}>
              카드 목록으로
            </button>

            <div className="detail-hero">
              <div>
                <p className="eyebrow">Study card · {problems.length} problems</p>
                <h1>{selectedCard.title}</h1>
                <p>{selectedCard.description || "이 카드에 나만의 문제를 차곡차곡 쌓아 보세요."}</p>
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
              <p className="toolbar-note">문제를 관리하고, 원하는 개수만큼 무작위로 확인할 수 있어요.</p>
              <div className="toolbar-actions">
                <button
                  className="button button--secondary"
                  type="button"
                  onClick={() => setRandomStudyOpen(true)}
                  disabled={problemsLoading || problems.length === 0}
                >
                  랜덤 문제 풀기
                </button>
                <button className="button button--primary" type="button" onClick={() => setProblemEditor(null)}>
                  새 문제
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

            {problemsLoading ? (
              <div className="problem-list" aria-label="문제 불러오는 중">
                {[1, 2, 3].map((item) => <div className="problem-skeleton" key={item} />)}
              </div>
            ) : problems.length > 0 ? (
              <div className="problem-list">
                {problems.map((problem, index) => (
                  <article className="problem-item" key={problem.id}>
                    <div className="problem-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</div>
                    <div className="problem-content">
                      <div className="problem-meta">
                        <span className="topic-badge">{problem.topic}</span>
                        <span>{dateFormatter.format(new Date(problem.created_at))}</span>
                      </div>
                      <p className="problem-question">{problem.question}</p>
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
                <h3>첫 문제를 만들어 보세요</h3>
                <p>주제와 문제를 직접 적고 필요하면 정답이나 해설도 남겨 보세요.</p>
                <button className="button button--primary" type="button" onClick={() => setProblemEditor(null)}>
                  문제 만들기
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
                <p>시험이나 분야별로 카드를 만들고, 카드 안에 직접 만든 문제를 차곡차곡 쌓아 보세요.</p>
                <button className="button button--primary" type="button" onClick={() => setCardEditor(null)}>
                  첫 카드 만들기
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
                        <p>{card.description || "설명이 없는 카드입니다."}</p>
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
                <p>정보처리기사, 영어 단어, 네트워크처럼 공부할 대상을 카드로 만들어 보세요.</p>
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
        <span>채점 없이, 나만의 속도로.</span>
      </footer>

      {cardEditor !== undefined && (
        <CardFormModal card={cardEditor} onClose={() => setCardEditor(undefined)} onSubmit={handleCardSubmit} />
      )}
      {problemEditor !== undefined && (
        <ProblemFormModal
          problem={problemEditor}
          onClose={() => setProblemEditor(undefined)}
          onSubmit={handleProblemSubmit}
        />
      )}
      {cardToDelete && (
        <ConfirmDialog
          title="카드를 삭제할까요?"
          message={`‘${cardToDelete.title}’ 카드 안의 문제도 모두 삭제됩니다. 이 작업은 되돌릴 수 없습니다.`}
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
          onClose={() => setRandomStudyOpen(false)}
        />
      )}
    </div>
  );
}

export default App;
