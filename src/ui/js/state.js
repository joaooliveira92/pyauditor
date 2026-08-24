"use strict";

export const $ = (s) => document.querySelector(s);

export const state = {
  files: [], current: null, original: "", job: null, poll: null, steps: [], mode: "file",
  indicators: [], indicator: null, indicatorKey: "", categoria: null, dataset: null, contrato: null,
  formDirty: false, warnings: [], warningsDismissed: false, history: [],
};

export const ORGAOS = ["MinC", "MTur"];
export const NEEDS_COMPETENCE = new Set(["measure", "report", "consolidate", "split", "run"]);
export const NEEDS_AGENCY = new Set(["bootstrap", "measure", "report", "split", "run"]);
export const STRICT_STEPS = new Set(["measure", "split"]);
export const FINAL_MONTH_STEPS = new Set(["report", "consolidate"]);

export const toast = (message) => {
  const el = $("#toast");
  el.textContent = message;
  el.classList.remove("opacity-0", "translate-y-2");
  el.classList.add("opacity-100", "translate-y-0");
  setTimeout(() => {
    el.classList.add("opacity-0", "translate-y-2");
    el.classList.remove("opacity-100", "translate-y-0");
  }, 2200);
};

export async function api(path, options = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const body = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
  return body;
}

export const esc = (v) => String(v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
export const labelOf = (k) => String(k || "").replace(/_/g, " ").split(" ").map((w) => w ? w[0].toUpperCase() + w.slice(1) : w).join(" ");

/* Reusable Tailwind class strings, kept in one place so nav rows, cards,
   and form fields stay visually consistent across sidebar/main-panel. */
export const CLS = {
  fileBtn: "block w-full cursor-pointer truncate rounded-r border-y-0 border-r-0 border-l-2 border-l-transparent bg-transparent py-1.5 pr-2 pl-2.5 text-left hover:bg-[#182234]",
  fileBtnActive: "border-l-accent bg-[#21304a]",
  fileDim: "block truncate text-[11px] text-[#8e9bb0]",
  card: "my-2 rounded-lg border border-line bg-panel",
  cardSummary: "cursor-pointer px-2.5 py-2 font-semibold",
  cardHead: "flex items-center justify-between px-2.5 py-2",
  cardBody: "px-3 py-2.5",
  label: "mt-2 mb-1 block text-xs text-[#8e9bb0]",
  input: "w-full rounded-md border border-line bg-[#0e1520] p-2.5 text-inherit",
  textarea: "w-full resize-y rounded-md border border-line bg-[#0e1520] p-2.5 text-inherit",
  check: "my-1.5 flex items-center gap-2",
  hint: "mb-3 text-xs leading-relaxed text-[#8e9bb0]",
  muted: "text-[#8e9bb0]",
  dim: "text-[11px] text-[#8e9bb0]",
  remove: "cursor-pointer border-0 bg-transparent px-1.5 text-base leading-none text-danger",
  add: "my-1 w-full rounded-md border border-dashed border-line bg-transparent py-1.5",
  listLabel: "mt-2 mb-1 text-xs text-[#8e9bb0]",
  step: "mb-3.5",
  stepHeading: "mb-1.5 text-sm font-semibold",
};
