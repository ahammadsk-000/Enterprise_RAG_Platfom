// CodeMirror extensions: language by file type, native spellcheck, and
// dictionary + document-word autocomplete (Tier A + B).

import { autocompletion, completeAnyWord, type CompletionContext } from "@codemirror/autocomplete";
import { html } from "@codemirror/lang-html";
import { javascript } from "@codemirror/lang-javascript";
import { json } from "@codemirror/lang-json";
import { markdown } from "@codemirror/lang-markdown";
import { type Extension } from "@codemirror/state";
import { EditorView } from "@codemirror/view";

import { COMMON_WORDS } from "@/lib/wordlist";

function languageFor(title: string, mime: string): Extension[] {
  const name = title.toLowerCase();
  if (mime.includes("markdown") || name.endsWith(".md")) return [markdown()];
  if (mime.includes("html") || name.endsWith(".html") || name.endsWith(".htm")) return [html()];
  if (mime.includes("json") || name.endsWith(".json")) return [json()];
  if (/\.(js|jsx|ts|tsx|mjs)$/.test(name)) return [javascript({ typescript: /\.tsx?$/.test(name) })];
  return [];
}

// Suggest common English words whose prefix matches the token before the cursor.
function dictionarySource(context: CompletionContext) {
  const word = context.matchBefore(/[A-Za-z]+/);
  if (!word || (word.from === word.to && !context.explicit)) return null;
  const prefix = word.text.toLowerCase();
  if (prefix.length < 2) return null;
  const options = COMMON_WORDS.filter((w) => w.startsWith(prefix) && w !== prefix)
    .slice(0, 20)
    .map((label) => ({ label, type: "text" }));
  if (options.length === 0) return null;
  return { from: word.from, options };
}

// Native browser spellcheck (red squiggles + right-click corrections).
const spellcheck = EditorView.contentAttributes.of({
  spellcheck: "true",
  autocorrect: "on",
  autocapitalize: "on",
});

export function editorExtensions(title: string, mime: string): Extension[] {
  return [
    ...languageFor(title, mime),
    spellcheck,
    autocompletion({ override: [dictionarySource, completeAnyWord] }),
    EditorView.lineWrapping,
  ];
}
