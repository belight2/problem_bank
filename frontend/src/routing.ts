export const cardContentViews = [
  "dashboard",
  "problems",
  "notes",
  "wrongAnswers",
  "workbooks",
] as const;

export type CardContentView = (typeof cardContentViews)[number];

export type AppRoute =
  | { page: "library" }
  | {
      page: "card";
      cardId: number;
      view: CardContentView;
      studySessionId: string | null;
    };

const cardContentViewSet = new Set<string>(cardContentViews);

function decodeSegment(segment: string) {
  try {
    return decodeURIComponent(segment);
  } catch {
    return null;
  }
}

export function parseHashRoute(hash: string): AppRoute {
  const path = hash.replace(/^#\/?/, "");
  if (!path) return { page: "library" };

  const segments = path.split("/").filter(Boolean);
  if (segments[0] !== "cards") return { page: "library" };

  const cardId = Number(segments[1]);
  if (!Number.isInteger(cardId) || cardId < 1) return { page: "library" };

  const view = cardContentViewSet.has(segments[2] ?? "")
    ? segments[2] as CardContentView
    : "dashboard";
  const studySessionId = segments[3] === "study" && segments[4]
    ? decodeSegment(segments[4])
    : null;

  return { page: "card", cardId, view, studySessionId };
}

export function getLibraryHash() {
  return "#/";
}

export function getCardHash(
  cardId: number,
  view: CardContentView,
  studySessionId?: string | null,
) {
  const base = `#/cards/${cardId}/${view}`;
  return studySessionId ? `${base}/study/${encodeURIComponent(studySessionId)}` : base;
}

export function navigateToHash(hash: string) {
  window.location.assign(hash);
}

export function replaceHash(hash: string) {
  window.history.replaceState(null, "", hash);
}
