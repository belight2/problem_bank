import { useState } from "react";

import { getErrorMessage } from "../api/client";
import { Modal } from "./Modal";

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel: string;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onClose,
  onConfirm,
}: ConfirmDialogProps) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setDeleting(true);
    setError(null);
    try {
      await onConfirm();
    } catch (confirmError) {
      setError(getErrorMessage(confirmError));
      setDeleting(false);
    }
  };

  return (
    <Modal
      title={title}
      description={message}
      onClose={onClose}
      closeDisabled={deleting}
    >
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="modal-actions">
        <button className="button button--ghost" type="button" onClick={onClose} disabled={deleting}>
          취소
        </button>
        <button className="button button--danger" type="button" onClick={handleConfirm} disabled={deleting}>
          {deleting ? "삭제 중…" : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
