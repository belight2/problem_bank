import {
  commandsCtx,
  defaultValueCtx,
  Editor,
  editorViewCtx,
  rootCtx,
} from "@milkdown/kit/core";
import { listener, listenerCtx } from "@milkdown/kit/plugin/listener";
import {
  commonmark,
  toggleEmphasisCommand,
  toggleInlineCodeCommand,
  toggleStrongCommand,
} from "@milkdown/kit/preset/commonmark";
import {
  gfm,
  toggleStrikethroughCommand,
} from "@milkdown/kit/preset/gfm";
import { $markSchema, $remark } from "@milkdown/kit/utils";
import {
  Milkdown,
  MilkdownProvider,
  useEditor,
  useInstance,
} from "@milkdown/react";
import { useEffect, useRef, useState } from "react";

import {
  isNoteColor,
  NOTE_COLORS,
  remarkNoteColor,
  resolveNoteColor,
  type NoteColor,
} from "../lib/noteColor";

interface MarkdownEditorProps {
  initialMarkdown: string;
  onMarkdownChange: (markdown: string) => void;
}

const noteColorRemarkPlugin = $remark(
  "noteColor",
  () => remarkNoteColor,
);

const noteColorSchema = $markSchema("note_color", () => ({
  attrs: {
    color: {
      default: "green",
      validate: "string",
    },
  },
  parseDOM: [
    {
      tag: "span[data-note-color]",
      getAttrs: (element) => {
        if (!(element instanceof HTMLElement)) return false;
        const color = element.dataset.noteColor;
        return isNoteColor(color) ? { color } : false;
      },
    },
  ],
  toDOM: (mark) => {
    const color = isNoteColor(mark.attrs.color) ? mark.attrs.color : "green";
    return [
      "span",
      {
        "data-note-color": color,
        style: `color: ${resolveNoteColor(color)}`,
      },
      0,
    ];
  },
  parseMarkdown: {
    match: (node) => node.type === "noteColor",
    runner: (state, node, markType) => {
      const color = isNoteColor(node.color) ? node.color : "green";
      state.openMark(markType, { color });
      state.next(node.children);
      state.closeMark(markType);
    },
  },
  toMarkdown: {
    match: (mark) => mark.type.name === "note_color",
    runner: (state, mark) => {
      const color = isNoteColor(mark.attrs.color) ? mark.attrs.color : "green";
      state.withMark(mark, "noteColor", undefined, { color });
    },
  },
}));

const COLOR_LABELS: Record<NoteColor, string> = {
  green: "초록색",
  red: "빨간색",
  amber: "주황색",
};

type TextFormat = "bold" | "italic" | "strike" | "code";

const TEXT_FORMATS: Array<{
  format: TextFormat;
  label: string;
  content: string;
}> = [
  { format: "bold", label: "굵게", content: "B" },
  { format: "italic", label: "기울임", content: "I" },
  { format: "strike", label: "취소선", content: "S" },
  { format: "code", label: "인라인 코드", content: "<>" },
];

function TextColorToolbar() {
  const instance = useInstance();
  const [customColor, setCustomColor] = useState("#2563eb");

  const applyFormat = (format: TextFormat) => {
    if (instance[0]) return;

    instance[1]().action((ctx) => {
      const commands = ctx.get(commandsCtx);

      if (format === "bold") commands.call(toggleStrongCommand.key);
      if (format === "italic") commands.call(toggleEmphasisCommand.key);
      if (format === "strike") commands.call(toggleStrikethroughCommand.key);
      if (format === "code") commands.call(toggleInlineCodeCommand.key);

      ctx.get(editorViewCtx).focus();
    });
  };

  const applyColor = (color: NoteColor | null) => {
    if (instance[0]) return;

    instance[1]().action((ctx) => {
      const view = ctx.get(editorViewCtx);
      const markType = noteColorSchema.type(ctx);
      const { empty, from, to } = view.state.selection;
      let transaction = view.state.tr;

      if (empty) {
        transaction = transaction.removeStoredMark(markType);
        if (color) transaction = transaction.addStoredMark(markType.create({ color }));
      } else {
        transaction = transaction.removeMark(from, to, markType);
        if (color) transaction = transaction.addMark(from, to, markType.create({ color }));
      }

      view.dispatch(transaction);
      view.focus();
    });
  };

  return (
    <div className="markdown-editor-toolbar" role="toolbar" aria-label="텍스트 서식">
      {TEXT_FORMATS.map(({ format, label, content }) => (
        <button
          className={`text-format-button text-format-button--${format}`}
          type="button"
          key={format}
          aria-label={label}
          title={label}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => applyFormat(format)}
          disabled={instance[0]}
        >
          {content}
        </button>
      ))}
      <span className="markdown-editor-toolbar-divider" aria-hidden="true" />
      <button
        className="note-color-button note-color-button--reset"
        type="button"
        aria-label="글자색 지우기"
        title="글자색 지우기"
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => applyColor(null)}
        disabled={instance[0]}
      >
        A
      </button>
      {NOTE_COLORS.map((color) => (
        <button
          className={`note-color-button note-color-button--${color}`}
          type="button"
          key={color}
          aria-label={COLOR_LABELS[color]}
          title={COLOR_LABELS[color]}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => applyColor(color)}
          disabled={instance[0]}
        >
          A
        </button>
      ))}
      <input
        className="note-custom-color"
        type="color"
        value={customColor}
        aria-label="직접 글자색 선택"
        title="직접 글자색 선택"
        onChange={(event) => {
          const color = event.target.value;
          if (!isNoteColor(color)) return;
          setCustomColor(color);
          applyColor(color);
        }}
        disabled={instance[0]}
      />
    </div>
  );
}

function MarkdownEditorBody({
  initialMarkdown,
  onMarkdownChange,
}: MarkdownEditorProps) {
  const changeHandler = useRef(onMarkdownChange);

  useEffect(() => {
    changeHandler.current = onMarkdownChange;
  }, [onMarkdownChange]);

  useEditor(
    (root) =>
      Editor.make()
        .config((ctx) => {
          ctx.set(rootCtx, root);
          ctx.set(defaultValueCtx, initialMarkdown);
          ctx.get(listenerCtx).markdownUpdated((_ctx, markdown, previousMarkdown) => {
            if (markdown !== previousMarkdown) {
              changeHandler.current(markdown.trimEnd());
            }
          });
        })
        .use(noteColorRemarkPlugin)
        .use(noteColorSchema)
        .use(commonmark)
        .use(gfm)
        .use(listener),
    [initialMarkdown],
  );

  return <Milkdown />;
}

export function MarkdownEditor(props: MarkdownEditorProps) {
  return (
    <div className="markdown-editor">
      <MilkdownProvider>
        <TextColorToolbar />
        <MarkdownEditorBody {...props} />
      </MilkdownProvider>
    </div>
  );
}
