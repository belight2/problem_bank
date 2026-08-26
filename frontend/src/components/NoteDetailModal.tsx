import type { Note } from "../types";
import { MarkdownContent } from "./MarkdownContent";
import { Modal } from "./Modal";

interface NoteDetailModalProps {
  note: Note;
  onClose: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onCreateProblem: () => void;
}

const noteDateFormatter = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

export function NoteDetailModal({
  note,
  onClose,
  onEdit,
  onDelete,
  onCreateProblem,
}: NoteDetailModalProps) {
  return (
    <Modal title={note.title} onClose={onClose} size="wide">
      <article className="note-detail">
        <div className="note-detail-meta">
          <span className="topic-badge">{note.topic_name ?? "카드 전체"}</span>
          <span>{noteDateFormatter.format(new Date(note.updated_at))}</span>
        </div>
        <MarkdownContent content={note.content_markdown} />
        <div className="note-detail-actions">
          <div>
            <button className="button button--danger-ghost" type="button" onClick={onDelete}>
              삭제
            </button>
          </div>
          <div>
            <button className="button button--ghost" type="button" onClick={onEdit}>
              수정
            </button>
            <button className="button button--primary" type="button" onClick={onCreateProblem}>
              문제 만들기
            </button>
          </div>
        </div>
      </article>
    </Modal>
  );
}
