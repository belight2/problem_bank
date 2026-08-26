import type {
  Parent,
  PhrasingContent,
  Root,
  RootContent,
  Text,
} from "mdast";
import type { Handle, Options } from "mdast-util-to-markdown";
import type { Plugin } from "unified";

export const NOTE_COLORS = ["green", "red", "amber"] as const;

type PresetNoteColor = (typeof NOTE_COLORS)[number];
export type NoteColor = PresetNoteColor | `#${string}`;

const PRESET_COLOR_VALUES: Record<PresetNoteColor, string> = {
  green: "#16803c",
  red: "#dc2626",
  amber: "#b45309",
};

interface NoteColorNode extends Parent {
  type: "noteColor";
  color: NoteColor;
  children: PhrasingContent[];
  data: {
    hName: "span";
    hProperties: {
      "data-note-color": NoteColor;
      style: string;
    };
  };
}

declare module "mdast" {
  interface PhrasingContentMap {
    noteColor: NoteColorNode;
  }

  interface RootContentMap {
    noteColor: NoteColorNode;
  }
}

declare module "unified" {
  interface Data {
    toMarkdownExtensions?: Options[];
  }
}

const COLOR_START_PATTERN = /==\{(green|red|amber|#[0-9a-fA-F]{6})\}/g;

export function isNoteColor(value: unknown): value is NoteColor {
  return typeof value === "string" && (
    NOTE_COLORS.includes(value as PresetNoteColor)
    || /^#[0-9a-fA-F]{6}$/.test(value)
  );
}

export function resolveNoteColor(color: NoteColor) {
  if (color in PRESET_COLOR_VALUES) {
    return PRESET_COLOR_VALUES[color as PresetNoteColor];
  }
  return color.toLowerCase();
}

function text(value: string): Text {
  return { type: "text", value };
}

function colorNode(color: NoteColor, children: PhrasingContent[]): NoteColorNode {
  return {
    type: "noteColor",
    color,
    children,
    data: {
      hName: "span",
      hProperties: {
        "data-note-color": color,
        style: `color: ${resolveNoteColor(color)}`,
      },
    },
  };
}

function findClosingMarker(
  children: RootContent[],
  startIndex: number,
  startOffset: number,
) {
  for (let index = startIndex; index < children.length; index += 1) {
    const child = children[index];
    if (child?.type !== "text") continue;

    const offset = index === startIndex ? startOffset : 0;
    const markerOffset = child.value.indexOf("==", offset);
    if (markerOffset >= 0) {
      return { index, offset: markerOffset };
    }
  }
  return null;
}

function parseColorMarkers(children: RootContent[]) {
  const parsed: RootContent[] = [];
  let index = 0;
  let offset = 0;

  while (index < children.length) {
    const child = children[index];
    if (!child) break;

    if (child.type !== "text") {
      parsed.push(child);
      index += 1;
      offset = 0;
      continue;
    }

    COLOR_START_PATTERN.lastIndex = offset;
    const match = COLOR_START_PATTERN.exec(child.value);
    if (!match || !isNoteColor(match[1])) {
      const remaining = child.value.slice(offset);
      if (remaining) parsed.push(text(remaining));
      index += 1;
      offset = 0;
      continue;
    }

    const before = child.value.slice(offset, match.index);
    if (before) parsed.push(text(before));

    const contentOffset = match.index + match[0].length;
    const closing = findClosingMarker(children, index, contentOffset);
    if (!closing) {
      parsed.push(text(child.value.slice(match.index)));
      parsed.push(...children.slice(index + 1));
      break;
    }

    const colored: PhrasingContent[] = [];
    if (closing.index === index) {
      const value = child.value.slice(contentOffset, closing.offset);
      if (value) colored.push(text(value));
    } else {
      const firstValue = child.value.slice(contentOffset);
      if (firstValue) colored.push(text(firstValue));

      for (let childIndex = index + 1; childIndex < closing.index; childIndex += 1) {
        const nested = children[childIndex];
        if (nested) colored.push(nested as PhrasingContent);
      }

      const closingChild = children[closing.index];
      if (closingChild?.type === "text") {
        const lastValue = closingChild.value.slice(0, closing.offset);
        if (lastValue) colored.push(text(lastValue));
      }
    }

    if (colored.length > 0) {
      parsed.push(colorNode(match[1], colored));
    }

    const closingChild = children[closing.index];
    index = closing.index;
    offset = closing.offset + 2;
    if (closingChild?.type !== "text" || offset >= closingChild.value.length) {
      index += 1;
      offset = 0;
    }
  }

  return parsed;
}

function transformColorMarkers(node: RootContent | Root) {
  if (!("children" in node)) return;

  const parent = node as Parent;
  parent.children.forEach((child) => {
    transformColorMarkers(child as RootContent);
  });
  parent.children = parseColorMarkers(parent.children as RootContent[]);
}

const noteColorHandler: Handle = (node, _parent, state, info) => {
  const color = isNoteColor((node as NoteColorNode).color)
    ? (node as NoteColorNode).color
    : "green";
  const content = state.containerPhrasing(node as NoteColorNode, info);
  return `=={${color}}${content}==`;
};

export const remarkNoteColor: Plugin<[], Root> = function remarkNoteColorPlugin() {
  const extensions = this.data("toMarkdownExtensions") ?? [];
  this.data("toMarkdownExtensions", [
    ...extensions,
    { handlers: { noteColor: noteColorHandler } },
  ]);

  return (tree) => {
    transformColorMarkers(tree);
  };
};
