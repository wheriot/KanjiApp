"use strict";

// Phone review page. Talks to the FastAPI server on this PC; all grading and
// scheduling happen there. Every server string is inserted with textContent;
// the one innerHTML (stroke_svg) is SVG the server renders from bundled KanjiVG data.

const $ = (id) => document.getElementById(id);
const el = {
  deck: $("deck"),
  progress: $("progress"),
  card: $("card"),
  prompt: $("prompt"),
  promptNote: $("prompt-note"),
  answerSide: $("answer-side"),
  verdict: $("verdict"),
  answer: $("answer"),
  answerNote: $("answer-note"),
  stroke: $("stroke"),
  sentence: $("sentence"),
  memory: $("memory"),
  message: $("message"),
  messageTitle: $("message-title"),
  messageBody: $("message-body"),
  messageSub: $("message-sub"),
  refresh: $("refresh"),
  controls: $("controls"),
};

const RATINGS = [
  [1, "Again", "again"],
  [2, "Hard", "hard"],
  [3, "Good", "good"],
  [4, "Easy", "easy"],
];

let state = null; // last /api/review response
let shownAt = 0; // when the current card appeared, for elapsed_ms
let reviewedThisVisit = 0;
let busy = false;

// -- server -----------------------------------------------------------------

async function api(path, body) {
  const options = body === undefined
    ? {}
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`Server replied ${res.status}`);
  return res.status === 204 ? null : res.json();
}

async function guarded(task) {
  if (busy) return;
  busy = true;
  setControlsDisabled(true);
  try {
    await task();
  } catch (err) {
    showMessage(
      "Can't reach your computer",
      "Check that the PC is awake, the Kanji web server is running, and Tailscale is on.",
      err instanceof TypeError ? "" : String(err.message || err), // TypeError = no connection
    );
  } finally {
    busy = false;
    setControlsDisabled(false);
  }
}

const load = () => guarded(async () => {
  state = await api("/api/review");
  render();
});

// -- rendering --------------------------------------------------------------

function render() {
  el.deck.textContent = state.deck_name;
  const left = state.summary.due + state.summary.new_available;
  el.progress.textContent = state.card ? `${left} left` : "";
  if (!state.card) {
    showDone(state.summary);
    return;
  }
  showCard(state.card, null, false);
  shownAt = Date.now();
  questionControls();
}

function showCard(card, verdict, revealed) {
  el.message.hidden = true;
  el.card.hidden = false;
  el.prompt.textContent = card.prompt;
  el.prompt.classList.toggle("big", [...card.prompt].length <= 4);
  el.promptNote.textContent = card.prompt_note;
  el.answerSide.hidden = !revealed;
  if (!revealed) return;

  el.verdict.hidden = verdict === null;
  if (!el.verdict.hidden) {
    el.verdict.textContent = verdict ? "Correct" : "Not quite";
    el.verdict.className = `verdict ${verdict ? "ok" : "bad"}`;
  }
  el.answer.textContent = card.answer;
  el.answerNote.textContent = card.answer_note;
  el.stroke.innerHTML = card.stroke_svg || "";
  setOptional(el.sentence, card.sentence ? `${card.sentence.japanese}\n${card.sentence.english}` : "");
  const memory = [card.components && `Parts: ${card.components}`, card.mnemonic].filter(Boolean);
  setOptional(el.memory, memory.join("\n"));
}

function showDone(summary) {
  clearControls();
  if (summary.limit_reached) {
    const held = [
      summary.capped_new && `${summary.capped_new} new`,
      summary.capped_due && `${summary.capped_due} due`,
    ].filter(Boolean).join(" and ");
    showMessage(
      "Daily limit reached",
      `${plural(summary.reviewed_today, "card")} studied today. ${held} held back for tomorrow.`,
      summary.resets_at ? `Limits reset in ${countdown(summary.resets_at)}.` : "",
    );
  } else if (summary.next_due) {
    showMessage(
      reviewedThisVisit ? `All done — ${plural(reviewedThisVisit, "card")} reviewed` : "All caught up",
      `Next review ${relative(summary.next_due)}.`,
      "",
    );
  } else {
    showMessage("Nothing to review", "Add kanji or vocab to this deck on your computer.", "");
  }
}

function showMessage(title, body, sub) {
  el.card.hidden = true;
  el.message.hidden = false;
  el.messageTitle.textContent = title;
  el.messageBody.textContent = body;
  el.messageSub.textContent = sub;
  el.progress.textContent = "";
  clearControls();
}

// -- controls ---------------------------------------------------------------

function questionControls() {
  const card = state.card;
  if (state.input_mode === "choose") {
    optionButtons(card.options, (option) => submit(option));
  } else if (state.input_mode === "type") {
    typeForm();
  } else {
    setControls("", [button("Show answer", "primary wide", reveal)]);
  }
}

function reveal() {
  showCard(state.card, null, true);
  setControls("cols-4", RATINGS.map(([value, label, tone]) =>
    button(label, `rating ${tone}`, () => rate(value))));
}

function optionButtons(options, onPick, result) {
  setControls("cols-2", options.map((option) => {
    let tone = "";
    if (result) {
      if (option === result.answer) tone = "correct";
      else if (option === result.picked) tone = "wrong";
    }
    const b = button(option, `${tone} ${[...option].length <= 3 ? "big" : ""}`, () => onPick(option));
    if (result) {
      b.disabled = true;
      b.dataset.locked = "1";
    }
    return b;
  }));
}

function typeForm() {
  const form = document.createElement("form");
  form.className = "type-form";
  const input = document.createElement("input");
  Object.assign(input, {
    type: "text",
    placeholder: "Reading in kana or romaji",
    autocomplete: "off",
    spellcheck: false,
    enterKeyHint: "go",
  });
  input.setAttribute("autocapitalize", "off");
  input.setAttribute("autocorrect", "off");
  input.setAttribute("aria-label", "Reading");
  const go = button("Check", "primary", null);
  go.type = "submit";
  form.append(input, go);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submit(input.value);
  });
  setControls("", [form]);
  input.focus();
}

function afterGrading(result, picked) {
  showCard(result.card, result.correct, true);
  const next = button("Continue", "primary wide", load);
  if (state.input_mode === "choose") {
    // only the right answer (and the wrong pick) stay, so Continue is never off-screen
    const shown = result.correct ? [picked] : [result.card.answer, picked];
    optionButtons(shown, () => {}, { answer: result.card.answer, picked });
    el.controls.append(next);
  } else {
    setControls("", [next]);
  }
}

// -- actions ----------------------------------------------------------------

const rate = (rating) => guarded(async () => {
  await api(`/api/review/${state.card.id}/rate`, { rating, elapsed_ms: Date.now() - shownAt });
  reviewedThisVisit += 1;
  state = await api("/api/review");
  render();
});

const submit = (response) => guarded(async () => {
  const result = await api(`/api/review/${state.card.id}/submit`, {
    response,
    elapsed_ms: Date.now() - shownAt,
  });
  reviewedThisVisit += 1;
  afterGrading(result, response);
});

// -- helpers ----------------------------------------------------------------

function button(label, classes, onClick) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = `btn ${classes}`.trim();
  b.textContent = label;
  if (onClick) b.addEventListener("click", onClick);
  return b;
}

function setControls(layout, children) {
  el.controls.className = `controls ${layout}`.trim();
  el.controls.replaceChildren(...children);
}

function clearControls() {
  setControls("", []);
}

function setControlsDisabled(disabled) {
  for (const b of el.controls.querySelectorAll("button")) {
    if (!b.dataset.locked) b.disabled = disabled;
  }
}

function setOptional(node, text) {
  node.textContent = text;
  node.hidden = !text;
}

function plural(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

function countdown(iso) {
  const seconds = Math.max(0, Math.floor((new Date(iso) - Date.now()) / 1000));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours) return `${hours}h ${minutes}m`;
  return minutes ? `${minutes}m` : "<1m";
}

function relative(iso) {
  const minutes = (new Date(iso) - Date.now()) / 60000;
  if (minutes <= 1.5) return "in a moment";
  if (minutes < 90) return `in about ${Math.round(minutes)} minutes`;
  const hours = minutes / 60;
  if (hours < 36) return `in about ${Math.round(hours)} hours`;
  return `in about ${Math.round(hours / 24)} days`;
}

// -- start ------------------------------------------------------------------

el.refresh.addEventListener("click", load);
document.addEventListener("visibilitychange", () => {
  // coming back to the app: refresh unless mid-card
  if (!document.hidden && !(state && state.card && el.message.hidden)) load();
});
load();
