import { useEffect, useId, useMemo, useState, type FormEvent } from "react";

import {
  ApiError,
  conceptApi,
  conceptRelationApi,
  getErrorMessage,
} from "../api/client";
import type {
  Card,
  Concept,
  ConceptRelation,
  ConceptRelationType,
} from "../types";
import { Modal } from "./Modal";

interface ConceptManagementModalProps {
  card: Card;
  concepts: Concept[];
  onChanged: (concepts: Concept[]) => void;
  onClose: () => void;
}

const relationOptions: Array<{ value: ConceptRelationType; label: string }> = [
  { value: "broader", label: "상위 개념" },
  { value: "prerequisite", label: "선수 개념" },
  { value: "related", label: "관련 개념" },
  { value: "contrasts", label: "비교 개념" },
  { value: "confused_with", label: "혼동 개념" },
];

const relationLabels = Object.fromEntries(
  relationOptions.map((option) => [option.value, option.label]),
) as Record<ConceptRelationType, string>;

function conceptErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) return error.message;
  return getErrorMessage(error);
}

export function ConceptManagementModal({
  card,
  concepts,
  onChanged,
  onClose,
}: ConceptManagementModalProps) {
  const nameId = useId();
  const descriptionId = useId();
  const reuseId = useId();
  const sourceId = useId();
  const relationTypeId = useId();
  const targetId = useId();
  const [view, setView] = useState<"concepts" | "relations">("concepts");
  const [allConcepts, setAllConcepts] = useState<Concept[]>([]);
  const [cardConcepts, setCardConcepts] = useState<Concept[]>(concepts);
  const [relations, setRelations] = useState<ConceptRelation[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [reuseConceptId, setReuseConceptId] = useState<number | "">("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [editingDescription, setEditingDescription] = useState("");
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [sourceConceptId, setSourceConceptId] = useState<number | "">("");
  const [targetConceptId, setTargetConceptId] = useState<number | "">("");
  const [relationType, setRelationType] = useState<ConceptRelationType>("related");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    Promise.all([conceptApi.list(), conceptRelationApi.list()])
      .then(([loadedConcepts, loadedRelations]) => {
        if (ignore) return;
        setAllConcepts(loadedConcepts);
        setRelations(loadedRelations);
      })
      .catch((loadError: unknown) => {
        if (!ignore) setError(conceptErrorMessage(loadError));
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, []);

  const cardConceptIds = useMemo(
    () => new Set(cardConcepts.map((concept) => concept.id)),
    [cardConcepts],
  );
  const reusableConcepts = allConcepts.filter(
    (concept) => !cardConceptIds.has(concept.id),
  );
  const cardRelations = relations.filter(
    (relation) =>
      cardConceptIds.has(relation.source_concept_id)
      && cardConceptIds.has(relation.target_concept_id),
  );

  const publishCardConcepts = (next: Concept[]) => {
    const sorted = [...next].sort((a, b) => a.name.localeCompare(b.name, "ko"));
    setCardConcepts(sorted);
    onChanged(sorted);
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("개념 이름을 입력해 주세요.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await conceptApi.create({
        name: name.trim(),
        description: description.trim() || null,
      });
      await conceptApi.attach(card.id, created.id);
      setAllConcepts((current) => [...current, created]);
      publishCardConcepts([...cardConcepts, created]);
      setName("");
      setDescription("");
    } catch (createError) {
      setError(conceptErrorMessage(createError));
    } finally {
      setBusy(false);
    }
  };

  const handleAttach = async () => {
    if (reuseConceptId === "") return;
    const concept = allConcepts.find((item) => item.id === reuseConceptId);
    if (!concept) return;
    setBusy(true);
    setError(null);
    try {
      await conceptApi.attach(card.id, concept.id);
      publishCardConcepts([...cardConcepts, concept]);
      setReuseConceptId("");
    } catch (attachError) {
      setError(conceptErrorMessage(attachError));
    } finally {
      setBusy(false);
    }
  };

  const startEditing = (concept: Concept) => {
    setEditingId(concept.id);
    setEditingName(concept.name);
    setEditingDescription(concept.description ?? "");
    setDeleteTargetId(null);
    setError(null);
  };

  const handleUpdate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (editingId === null || !editingName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await conceptApi.update(editingId, {
        name: editingName.trim(),
        description: editingDescription.trim() || null,
      });
      setAllConcepts((current) =>
        current.map((concept) => (concept.id === updated.id ? updated : concept)),
      );
      publishCardConcepts(
        cardConcepts.map((concept) => (concept.id === updated.id ? updated : concept)),
      );
      setEditingId(null);
    } catch (updateError) {
      setError(conceptErrorMessage(updateError));
    } finally {
      setBusy(false);
    }
  };

  const handleDetach = async (concept: Concept) => {
    setBusy(true);
    setError(null);
    try {
      await conceptApi.detach(card.id, concept.id);
      publishCardConcepts(cardConcepts.filter((item) => item.id !== concept.id));
    } catch (detachError) {
      setError(conceptErrorMessage(detachError));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (concept: Concept) => {
    setBusy(true);
    setError(null);
    try {
      await conceptApi.remove(concept.id);
      setAllConcepts((current) => current.filter((item) => item.id !== concept.id));
      setRelations((current) =>
        current.filter(
          (relation) =>
            relation.source_concept_id !== concept.id
            && relation.target_concept_id !== concept.id,
        ),
      );
      publishCardConcepts(cardConcepts.filter((item) => item.id !== concept.id));
      setDeleteTargetId(null);
    } catch (deleteError) {
      setError(conceptErrorMessage(deleteError));
    } finally {
      setBusy(false);
    }
  };

  const handleCreateRelation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (sourceConceptId === "" || targetConceptId === "") {
      setError("연결할 두 개념을 선택해 주세요.");
      return;
    }
    if (sourceConceptId === targetConceptId) {
      setError("서로 다른 개념을 선택해 주세요.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await conceptRelationApi.create({
        source_concept_id: sourceConceptId,
        target_concept_id: targetConceptId,
        relation_type: relationType,
      });
      setRelations((current) => [...current, created]);
      setTargetConceptId("");
    } catch (relationError) {
      setError(conceptErrorMessage(relationError));
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteRelation = async (relationId: number) => {
    setBusy(true);
    setError(null);
    try {
      await conceptRelationApi.remove(relationId);
      setRelations((current) => current.filter((relation) => relation.id !== relationId));
    } catch (deleteError) {
      setError(conceptErrorMessage(deleteError));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="개념 관리" onClose={onClose} size="wide" closeDisabled={busy}>
      <div className="concept-manager">
        <div className="concept-manager-tabs" role="tablist" aria-label="개념 관리 메뉴">
          <button
            className={view === "concepts" ? "is-active" : ""}
            type="button"
            role="tab"
            aria-selected={view === "concepts"}
            onClick={() => setView("concepts")}
          >
            카드 개념 <span>{cardConcepts.length}</span>
          </button>
          <button
            className={view === "relations" ? "is-active" : ""}
            type="button"
            role="tab"
            aria-selected={view === "relations"}
            onClick={() => setView("relations")}
          >
            개념 관계 <span>{cardRelations.length}</span>
          </button>
        </div>

        {error && <p className="form-error" role="alert">{error}</p>}

        {view === "concepts" ? (
          <>
            <form className="concept-create-form" onSubmit={handleCreate}>
              <label className="field" htmlFor={nameId}>
                <span>새 개념</span>
                <input
                  id={nameId}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={120}
                  placeholder="예: 데이터 정규화"
                  disabled={busy}
                  required
                />
              </label>
              <label className="field" htmlFor={descriptionId}>
                <span>설명 <small>선택</small></span>
                <input
                  id={descriptionId}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  maxLength={2000}
                  placeholder="개념을 짧게 정리해 주세요."
                  disabled={busy}
                />
              </label>
              <button className="button button--primary" type="submit" disabled={busy}>
                추가
              </button>
            </form>

            <div className="concept-reuse-row">
              <label className="field" htmlFor={reuseId}>
                <span>기존 개념 연결</span>
                <select
                  id={reuseId}
                  value={reuseConceptId}
                  onChange={(event) =>
                    setReuseConceptId(event.target.value ? Number(event.target.value) : "")
                  }
                  disabled={busy || loading || reusableConcepts.length === 0}
                >
                  <option value="">
                    {reusableConcepts.length > 0 ? "개념 선택" : "연결할 개념 없음"}
                  </option>
                  {reusableConcepts.map((concept) => (
                    <option key={concept.id} value={concept.id}>{concept.name}</option>
                  ))}
                </select>
              </label>
              <button
                className="button button--ghost"
                type="button"
                onClick={() => void handleAttach()}
                disabled={busy || reuseConceptId === ""}
              >
                연결
              </button>
            </div>

            {loading ? (
              <div className="concept-manager-loading" aria-label="개념 불러오는 중">
                <span /><span />
              </div>
            ) : cardConcepts.length > 0 ? (
              <ul className="concept-manager-list">
                {cardConcepts.map((concept) => (
                  <li key={concept.id}>
                    {editingId === concept.id ? (
                      <form className="concept-edit-form" onSubmit={handleUpdate}>
                        <input
                          value={editingName}
                          onChange={(event) => setEditingName(event.target.value)}
                          maxLength={120}
                          disabled={busy}
                          autoFocus
                          required
                        />
                        <input
                          value={editingDescription}
                          onChange={(event) => setEditingDescription(event.target.value)}
                          maxLength={2000}
                          placeholder="설명 없음"
                          disabled={busy}
                        />
                        <div>
                          <button type="button" onClick={() => setEditingId(null)} disabled={busy}>취소</button>
                          <button type="submit" disabled={busy}>저장</button>
                        </div>
                      </form>
                    ) : deleteTargetId === concept.id ? (
                      <div className="concept-delete-confirm" role="alert">
                        <span><strong>{concept.name}</strong>을 모든 카드에서 삭제할까요?</span>
                        <div>
                          <button type="button" onClick={() => setDeleteTargetId(null)} disabled={busy}>취소</button>
                          <button className="text-danger" type="button" onClick={() => void handleDelete(concept)} disabled={busy}>전체에서 삭제</button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="concept-manager-copy">
                          <strong>{concept.name}</strong>
                          <span>{concept.description || "설명 없음"}</span>
                        </div>
                        <div className="concept-manager-actions">
                          <button type="button" onClick={() => startEditing(concept)} disabled={busy}>수정</button>
                          <button type="button" onClick={() => void handleDetach(concept)} disabled={busy}>카드에서 해제</button>
                          <button className="text-danger" type="button" onClick={() => setDeleteTargetId(concept.id)} disabled={busy}>삭제</button>
                        </div>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="concept-manager-empty">등록된 개념이 없습니다.</div>
            )}
          </>
        ) : (
          <>
            <form className="concept-relation-form" onSubmit={handleCreateRelation}>
              <label className="field" htmlFor={sourceId}>
                <span>기준 개념</span>
                <select
                  id={sourceId}
                  value={sourceConceptId}
                  onChange={(event) => setSourceConceptId(event.target.value ? Number(event.target.value) : "")}
                  disabled={busy}
                  required
                >
                  <option value="">선택</option>
                  {cardConcepts.map((concept) => <option key={concept.id} value={concept.id}>{concept.name}</option>)}
                </select>
              </label>
              <label className="field" htmlFor={relationTypeId}>
                <span>관계</span>
                <select id={relationTypeId} value={relationType} onChange={(event) => setRelationType(event.target.value as ConceptRelationType)} disabled={busy}>
                  {relationOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </label>
              <label className="field" htmlFor={targetId}>
                <span>연결 개념</span>
                <select
                  id={targetId}
                  value={targetConceptId}
                  onChange={(event) => setTargetConceptId(event.target.value ? Number(event.target.value) : "")}
                  disabled={busy}
                  required
                >
                  <option value="">선택</option>
                  {cardConcepts.map((concept) => <option key={concept.id} value={concept.id}>{concept.name}</option>)}
                </select>
              </label>
              <button className="button button--primary" type="submit" disabled={busy || cardConcepts.length < 2}>연결</button>
            </form>

            {cardRelations.length > 0 ? (
              <ul className="concept-relation-list">
                {cardRelations.map((relation) => (
                  <li key={relation.id}>
                    <strong>{relation.source_concept_name}</strong>
                    <span>{relationLabels[relation.relation_type]}</span>
                    <strong>{relation.target_concept_name}</strong>
                    <button className="text-danger" type="button" onClick={() => void handleDeleteRelation(relation.id)} disabled={busy} aria-label="개념 관계 삭제">×</button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="concept-manager-empty">등록된 개념 관계가 없습니다.</div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
