// Copilot-style inline AI completion for CodeMirror 6.
// Shows a debounced LLM suggestion as gray "ghost text" after the cursor;
// Tab accepts it, Escape (or any edit) dismisses it.

import { Prec, StateEffect, StateField, type Extension } from "@codemirror/state";
import {
  Decoration,
  EditorView,
  ViewPlugin,
  type ViewUpdate,
  WidgetType,
  keymap,
} from "@codemirror/view";

interface Suggestion {
  text: string;
  from: number;
}

const setSuggestion = StateEffect.define<Suggestion | null>();

class GhostWidget extends WidgetType {
  constructor(readonly text: string) {
    super();
  }
  eq(other: GhostWidget) {
    return other.text === this.text;
  }
  toDOM() {
    const span = document.createElement("span");
    span.style.opacity = "0.45";
    span.style.fontStyle = "italic";
    span.textContent = this.text;
    return span;
  }
}

const suggestionField = StateField.define<Suggestion | null>({
  create: () => null,
  update(value, tr) {
    for (const e of tr.effects) if (e.is(setSuggestion)) return e.value;
    // Any edit or cursor move clears a pending suggestion.
    if (tr.docChanged || tr.selection) return null;
    return value;
  },
  provide: (field) =>
    EditorView.decorations.compute([field], (state) => {
      const s = state.field(field);
      if (!s || state.selection.main.head !== s.from) return Decoration.none;
      return Decoration.set([
        Decoration.widget({ widget: new GhostWidget(s.text), side: 1 }).range(s.from),
      ]);
    }),
});

function fetcherPlugin(fetchFn: (prefix: string) => Promise<string>) {
  return ViewPlugin.fromClass(
    class {
      timer: number | undefined;
      constructor(readonly view: EditorView) {}
      update(u: ViewUpdate) {
        if (!u.docChanged) return;
        window.clearTimeout(this.timer);
        this.timer = window.setTimeout(() => void this.fetch(), 500);
      }
      async fetch() {
        const { state } = this.view;
        const head = state.selection.main.head;
        if (!state.selection.main.empty) return;
        const prefix = state.doc.sliceString(Math.max(0, head - 2000), head);
        if (prefix.trim().length < 3) return;
        let text = "";
        try {
          text = (await fetchFn(prefix)).trim();
        } catch {
          return;
        }
        // Bail if the user kept typing/moved while we were fetching.
        if (!text || this.view.state.selection.main.head !== head) return;
        this.view.dispatch({ effects: setSuggestion.of({ text, from: head }) });
      }
      destroy() {
        window.clearTimeout(this.timer);
      }
    },
  );
}

const acceptKeymap = Prec.highest(
  keymap.of([
    {
      key: "Tab",
      run: (view) => {
        const s = view.state.field(suggestionField, false);
        if (!s || view.state.selection.main.head !== s.from) return false;
        view.dispatch({
          changes: { from: s.from, insert: s.text },
          selection: { anchor: s.from + s.text.length },
          effects: setSuggestion.of(null),
        });
        return true;
      },
    },
    {
      key: "Escape",
      run: (view) => {
        if (!view.state.field(suggestionField, false)) return false;
        view.dispatch({ effects: setSuggestion.of(null) });
        return true;
      },
    },
  ]),
);

export function aiCompletion(fetchFn: (prefix: string) => Promise<string>): Extension[] {
  return [suggestionField, fetcherPlugin(fetchFn), acceptKeymap];
}
