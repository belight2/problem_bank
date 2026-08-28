import { useId, useState, type ChangeEvent } from "react";

import { cardPackageApi, getErrorMessage } from "../api/client";
import type { Card, CardPackage, CardPackagePreview } from "../types";
import { Modal } from "./Modal";

interface CardImportModalProps {
  onClose: () => void;
  onImported: (card: Card) => void;
}

const MAX_PACKAGE_SIZE = 10 * 1024 * 1024;

export function CardImportModal({ onClose, onImported }: CardImportModalProps) {
  const fileInputId = useId();
  const [cardPackage, setCardPackage] = useState<CardPackage | null>(null);
  const [preview, setPreview] = useState<CardPackagePreview | null>(null);
  const [fileName, setFileName] = useState("");
  const [reading, setReading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    event.target.value = "";
    setCardPackage(null);
    setPreview(null);
    setFileName(file.name);
    setError(null);
    if (file.size > MAX_PACKAGE_SIZE) {
      setError("파일 크기는 10MB 이하여야 합니다.");
      return;
    }

    setReading(true);
    try {
      const parsed = JSON.parse(await file.text()) as CardPackage;
      const loadedPreview = await cardPackageApi.preview(parsed);
      setCardPackage(parsed);
      setPreview(loadedPreview);
    } catch (readError) {
      if (readError instanceof SyntaxError) {
        setError("올바른 카드 JSON 파일이 아닙니다.");
      } else {
        setError(getErrorMessage(readError));
      }
    } finally {
      setReading(false);
    }
  };

  const handleImport = async () => {
    if (!cardPackage || !preview) return;
    setImporting(true);
    setError(null);
    try {
      const result = await cardPackageApi.importPackage(cardPackage);
      onImported(result.card);
    } catch (importError) {
      setError(getErrorMessage(importError));
      setImporting(false);
    }
  };

  const busy = reading || importing;

  return (
    <Modal
      title="카드 불러오기"
      onClose={onClose}
      closeDisabled={busy}
    >
      <div className="card-import-stack">
        <label className="card-package-picker" htmlFor={fileInputId}>
          <input
            id={fileInputId}
            type="file"
            accept=".json,application/json"
            onChange={(event) => void handleFileChange(event)}
            disabled={busy}
          />
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5" />
            <path d="M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" />
          </svg>
          <strong>{reading ? "파일 확인 중…" : "카드 파일 선택"}</strong>
          <span>{fileName || ".pbcard.json 또는 .json"}</span>
        </label>

        {preview && (
          <section className="card-package-preview" aria-live="polite">
            <div className="card-package-preview-heading">
              <span>가져올 카드</span>
              <h3>{preview.title}</h3>
            </div>
            <dl className="card-package-summary">
              <div><dt>주제</dt><dd>{preview.summary.topic_count}</dd></div>
              <div><dt>문제</dt><dd>{preview.summary.problem_count}</dd></div>
              <div><dt>노트</dt><dd>{preview.summary.note_count}</dd></div>
              <div><dt>개념</dt><dd>{preview.summary.concept_count}</dd></div>
            </dl>
            {preview.reused_concept_count > 0 && (
              <p className="card-package-concept-status">
                기존 개념 {preview.reused_concept_count}개 연결 · 새 개념 {preview.new_concept_count}개
              </p>
            )}
          </section>
        )}

        {error && <p className="form-error" role="alert">{error}</p>}

        <div className="modal-actions">
          <button
            className="button button--ghost"
            type="button"
            onClick={onClose}
            disabled={busy}
          >
            취소
          </button>
          <button
            className="button button--primary"
            type="button"
            onClick={() => void handleImport()}
            disabled={!preview || busy}
          >
            {importing ? "불러오는 중…" : "새 카드로 불러오기"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
