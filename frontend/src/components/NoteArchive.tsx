import type { Concept, Note } from "../types";

interface NoteArchiveProps {
  notes: Note[];
  concepts: Concept[];
  loading: boolean;
  loaded: boolean;
  onOpen: (note: Note) => void;
  onEdit: (note: Note) => void;
  onDelete: (note: Note) => void;
  onCreate: () => void;
}

const noteDateFormatter = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

function getNoteExcerpt(content: string) {
  const plainText = content
    .replace(/```[\s\S]*?```/g, " 코드 ")
    .replace(/[`#>*_[\]~-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return plainText.length > 150 ? `${plainText.slice(0, 150)}…` : plainText;
}

export function NoteArchive({
  notes,
  concepts,
  loading,
  loaded,
  onOpen,
  onEdit,
  onDelete,
  onCreate,
}: NoteArchiveProps) {
  return (
    <>
      <div className="section-heading content-section-heading">
        <div>
          <p className="eyebrow">Study notes</p>
          <h2>공부 노트</h2>
        </div>
        <span>{notes.length}개</span>
      </div>

      {loading ? (
        <div className="note-grid" aria-label="노트 불러오는 중">
          {[1, 2].map((item) => <div className="note-skeleton" key={item} />)}
        </div>
      ) : !loaded ? (
        <div className="empty-state empty-state--compact">
          <span className="empty-index" aria-hidden="true">!</span>
          <h3>노트를 불러오지 못했어요</h3>
        </div>
      ) : notes.length > 0 ? (
        <div className="note-grid">
          {notes.map((note, index) => (
            <article className="note-card" key={note.id}>
              <button className="note-open" type="button" onClick={() => onOpen(note)}>
                <div className="note-card-meta">
                  <span className="note-index">{String(index + 1).padStart(2, "0")}</span>
                  <span className="topic-badge">{note.topic_name ?? "카드 전체"}</span>
                  {note.concept_ids.map((conceptId) => {
                    const concept = concepts.find((item) => item.id === conceptId);
                    return concept ? (
                      <span className="concept-badge" key={concept.id}>{concept.name}</span>
                    ) : null;
                  })}
                </div>
                <h3>{note.title}</h3>
                <p>{getNoteExcerpt(note.content_markdown)}</p>
                <span className="note-date">
                  {noteDateFormatter.format(new Date(note.updated_at))}
                </span>
              </button>
              <div className="note-card-actions">
                <button type="button" onClick={() => onEdit(note)}>수정</button>
                <button className="text-danger" type="button" onClick={() => onDelete(note)}>
                  삭제
                </button>
                <button className="open-label" type="button" onClick={() => onOpen(note)}>
                  열기
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <span className="empty-index" aria-hidden="true">N</span>
          <h3>첫 공부 노트를 작성해 보세요</h3>
          <button className="button button--primary" type="button" onClick={onCreate}>
            노트 만들기
          </button>
        </div>
      )}
    </>
  );
}
