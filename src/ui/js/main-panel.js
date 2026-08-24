"use strict";
import { $, state, esc, labelOf, api, toast, CLS } from "./state.js";
import { renderCategoriaNav, renderDatasetNav, renderContratoNav, renderFiles, renderIndicators } from "./sidebar.js";

const ENUMS = {
  "calculation.shape": ["ratio", "segmented_ratio", "count_difference", "external_catalog_sum", "precomputed_table"],
  "calculation.aggregation": ["count_distinct", "sum", "precomputed"],
  "target.operator": [">=", "<="],
  "quality_gates.checks.type": ["not_null", "in_set"],
};
const attrPath = (path) => esc(JSON.stringify(path));
const normPath = (path) => path.filter((p) => typeof p !== "number").join(".");
export const isInmsPath = (p) => /(^|\/)inms-\d+([.-]|$)/.test(p);
const FAMILY_FILE_RE = /(^|\/)(categorias|datasets|dados_contratuais|ajuste_inms|desconto_regulat[oó]rio)\.yaml$/;
export const isFamilyFile = (p) => isInmsPath(p) || FAMILY_FILE_RE.test(p);

export function isDirty() { if (state.mode !== "file") return state.formDirty; return state.current !== null && $("#editor").value !== state.original; }
export function renderDirty() {
  const dirty = isDirty();
  $("#dirty").classList.toggle("hidden", !dirty);
  $("#form-dirty").classList.toggle("hidden", state.mode === "file" || !state.formDirty);
  $("#save").disabled = !dirty;
}
export function showEditor() {
  $("#empty").classList.add("hidden");
  $("#form-wrap").classList.add("hidden"); $("#form-wrap").classList.remove("flex");
  $("#editor-wrap").classList.remove("hidden"); $("#editor-wrap").classList.add("flex");
}
export function showForm() {
  $("#empty").classList.add("hidden");
  $("#editor-wrap").classList.add("hidden"); $("#editor-wrap").classList.remove("flex");
  $("#form-wrap").classList.remove("hidden"); $("#form-wrap").classList.add("flex");
}

/* ---------------- generic nested-doc form model (path = array of string|number keys) ---------------- */
function scalarField(key, path, value) {
  const lbl = esc(labelOf(key));
  const attr = attrPath(path);
  if (typeof value === "boolean") return `<label class="${CLS.check}"><input type="checkbox" data-path='${attr}' data-coerce="bool" class="w-auto" ${value ? "checked" : ""}> ${lbl}</label>`;
  const enums = ENUMS[normPath(path)];
  if (enums) return `<label class="${CLS.label}">${lbl}<select data-path='${attr}' class="${CLS.input}">` + enums.map((o) => `<option value="${esc(o)}"${o === String(value) ? " selected" : ""}>${esc(o)}</option>`).join("") + `</select></label>`;
  if (typeof value === "number") return `<label class="${CLS.label}">${lbl}<input type="number" step="any" data-path='${attr}' data-coerce="number" value="${esc(value)}" class="${CLS.input}"></label>`;
  if (key === "descricao") return `<label class="${CLS.label}">${lbl}<textarea data-path='${attr}' rows="3" class="${CLS.textarea}">${esc(value)}</textarea></label>`;
  return `<label class="${CLS.label}">${lbl}<input data-path='${attr}' value="${esc(value)}" class="${CLS.input}"></label>`;
}
function renderChildren(obj, path) { let html = ""; for (const [k, v] of Object.entries(obj)) html += renderNode(k, [...path, k], v); return html; }
function renderNode(key, path, value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return renderArray(key, path, value);
  if (typeof value === "object") return `<details class="${CLS.card}" open><summary class="${CLS.cardSummary}">${esc(labelOf(key))}</summary><div class="${CLS.cardBody}">${renderChildren(value, path)}</div></details>`;
  return scalarField(key, path, value);
}
function renderArray(key, path, value) {
  if (value.length === 0) return `<div class="${CLS.muted}">${esc(labelOf(key))} — none</div>`;
  if (typeof value[0] !== "object") return `<label class="${CLS.label}">${esc(labelOf(key))}<input data-path='${attrPath(path)}' data-coerce="list" value="${esc(value.join(", "))}" class="${CLS.input}"></label>`;
  let html = `<div class="${CLS.listLabel}">${esc(labelOf(key))}</div>`;
  value.forEach((item, i) => { html += `<div class="${CLS.card}"><div class="${CLS.cardHead}"><strong>${i + 1}</strong><button type="button" class="${CLS.remove}" data-remove='${attrPath([...path, i])}'>×</button></div><div class="${CLS.cardBody}">${renderChildren(item, [...path, i])}</div></div>`; });
  html += `<button type="button" class="${CLS.add}" data-add='${attrPath(path)}'>+ Add ${esc(labelOf(key))}</button>`;
  return html;
}
function walkTarget(root, path) { let cur = root; for (let i = 0; i < path.length - 1; i++) cur = cur[path[i]]; return { parent: cur, key: path[path.length - 1] }; }
function coerce(el, kind) { if (kind === "bool") return !!el.checked; if (kind === "number") { const v = el.value; return v === "" ? undefined : Number(v); } if (kind === "list") return el.value.split(",").map((s) => s.trim()).filter(Boolean); return el.value; }
function defaultItem(key) { if (key === "checks") return { type: "not_null", column: "" }; if (key === "categories") return { name: "", numerator_filter: { column: "", equals: "" }, denominator_filter: { column: "", equals: "" }, step_points: 0 }; return {}; }
function addItem(root, path) { const { parent, key } = walkTarget(root, path); if (!Array.isArray(parent[key])) parent[key] = []; parent[key].push(defaultItem(path[path.length - 1])); }
function removeItem(root, path) { const { parent, key } = walkTarget(root, path); if (typeof key === "number") parent.splice(key, 1); else delete parent[key]; }
function markFormDirty() { state.formDirty = true; renderDirty(); }
function wireForm(root, container, rerender) {
  for (const el of container.querySelectorAll("[data-path]")) {
    const path = JSON.parse(el.dataset.path);
    const evt = el.tagName === "SELECT" || el.type === "checkbox" ? "change" : "input";
    el.addEventListener(evt, () => { const { parent, key } = walkTarget(root, path); parent[key] = coerce(el, el.dataset.coerce); markFormDirty(); });
  }
  for (const b of container.querySelectorAll("[data-add]")) { const path = JSON.parse(b.dataset.add); b.addEventListener("click", () => { addItem(root, path); rerender(); markFormDirty(); }); }
  for (const b of container.querySelectorAll("[data-remove]")) { const path = JSON.parse(b.dataset.remove); b.addEventListener("click", () => { removeItem(root, path); rerender(); markFormDirty(); }); }
}

/* ---------------- INMS form ---------------- */
function renderForm() {
  const d = state.indicator; if (!d) return;
  $("#form-file").textContent = `${d.key} · ${d.orgao}`;
  let html = `<section class="${CLS.step}"><h2 class="${CLS.stepHeading}">1 · Contract (shared)</h2>`;
  if (d.shared) html += `<p class="${CLS.hint}">Lives in <code>${esc(d.shared.path)}</code>. Applies to all ${d.segments.length || 0} segments.</p>` + renderChildren(d.shared.config, ["shared", "config"]);
  else html += `<p class="${CLS.muted}">No shared contract file.</p>`;
  html += `</section><section class="${CLS.step}"><h2 class="${CLS.stepHeading}">2 · Segments — ${esc(d.orgao)}</h2>`;
  if (d.segments.length === 0) html += `<p class="${CLS.muted}">No segments for this agency.</p>`;
  d.segments.forEach((seg, i) => { html += `<div class="${CLS.card}"><div class="${CLS.cardHead}"><strong>${esc(seg.category)}</strong><code class="${CLS.dim}">${esc(seg.path)}</code></div><div class="${CLS.cardBody}">${renderChildren(seg.config, ["segments", i, "config"])}</div></div>`; });
  html += `</section>`;
  $("#form").innerHTML = html;
  wireForm(d, $("#form"), renderForm);
}

/* ---------------- Categorias form ---------------- */
function renderCategoriaForm() {
  const d = state.categoria; if (!d) return;
  $("#form-file").textContent = `Categorias · ${d.orgao}`;
  let html = `<p class="${CLS.hint}">Lives in <code>${esc(d.path)}</code>.</p>`;
  const cats = d.config.categorias || {};
  for (const [catKey, cat] of Object.entries(cats)) {
    html += `<details class="${CLS.card}" open><summary class="${CLS.cardSummary}">${esc(catKey)} — ${esc(cat.label || "")}</summary><div class="${CLS.cardBody}">`;
    html += `<label class="${CLS.label}">Label<input data-path='${attrPath(["config", "categorias", catKey, "label"])}' value="${esc(cat.label ?? "")}" class="${CLS.input}"></label>`;
    for (const [inmsKey, entry] of Object.entries(cat.inms || {})) html += renderCategoriaInmsEntry(catKey, inmsKey, entry);
    html += `</div></details>`;
  }
  $("#form").innerHTML = html;
  wireForm(d, $("#form"), renderCategoriaForm);
  wireCategoriaModeControls();
}
function renderCategoriaInmsEntry(catKey, inmsKey, entry) {
  const base = ["config", "categorias", catKey, "inms", inmsKey];
  const isGrupo = entry.mode === "grupo_executor";
  const filterKind = "catch_all_contains" in entry ? "catch_all_contains" : "in_values";
  let html = `<div class="${CLS.card}"><div class="${CLS.cardHead}"><strong>${esc(inmsKey)}</strong></div><div class="${CLS.cardBody}">`;
  html += `<label class="${CLS.label}">Mode<select data-mode-path='${attrPath(base)}' class="${CLS.input}">` +
    `<option value="grupo_executor"${isGrupo ? " selected" : ""}>Filtered by Grupo executor</option>` +
    `<option value="whole_indicator"${!isGrupo ? " selected" : ""}>Whole indicator (no filter)</option>` +
    `</select></label>`;
  if (isGrupo) {
    html += `<label class="${CLS.label}">Filter type<select data-filter-path='${attrPath(base)}' class="${CLS.input}">` +
      `<option value="in_values"${filterKind === "in_values" ? " selected" : ""}>Match any of these values</option>` +
      `<option value="catch_all_contains"${filterKind === "catch_all_contains" ? " selected" : ""}>Contains this text</option>` +
      `</select></label>`;
    if (filterKind === "in_values") html += `<label class="${CLS.label}">Values (comma-separated)<input data-path='${attrPath([...base, "in_values"])}' data-coerce="list" value="${esc((entry.in_values || []).join(", "))}" class="${CLS.input}"></label>`;
    else html += `<label class="${CLS.label}">Contains<input data-path='${attrPath([...base, "catch_all_contains"])}' value="${esc(entry.catch_all_contains ?? "")}" class="${CLS.input}"></label>`;
  }
  html += `</div></div>`;
  return html;
}
function wireCategoriaModeControls() {
  for (const el of $("#form").querySelectorAll("[data-mode-path]")) {
    const path = JSON.parse(el.dataset.modePath);
    el.addEventListener("change", () => {
      const { parent, key } = walkTarget(state.categoria, path); const entry = parent[key];
      entry.mode = el.value;
      if (el.value === "whole_indicator") { delete entry.in_values; delete entry.catch_all_contains; }
      else if (!("in_values" in entry) && !("catch_all_contains" in entry)) entry.in_values = [];
      markFormDirty(); renderCategoriaForm();
    });
  }
  for (const el of $("#form").querySelectorAll("[data-filter-path]")) {
    const path = JSON.parse(el.dataset.filterPath);
    el.addEventListener("change", () => {
      const { parent, key } = walkTarget(state.categoria, path); const entry = parent[key];
      if (el.value === "in_values") { delete entry.catch_all_contains; entry.in_values = []; }
      else { delete entry.in_values; entry.catch_all_contains = ""; }
      markFormDirty(); renderCategoriaForm();
    });
  }
}

/* ---------------- Datasets form ---------------- */
function renderDatasetForm() {
  const d = state.dataset; if (!d) return;
  $("#form-file").textContent = `Datasets · ${d.path}`;
  let html = `<p class="${CLS.hint}">Lives in <code>${esc(d.path)}</code>. Alias → CSV file + parsing options.</p>`;
  for (const [alias, entry] of Object.entries(d.datasets)) {
    html += `<div class="${CLS.card}"><div class="${CLS.cardHead}"><strong>${esc(alias)}</strong><button type="button" class="${CLS.remove}" data-remove-alias="${esc(alias)}">×</button></div><div class="${CLS.cardBody}">`;
    html += `<label class="${CLS.label}">File<input data-alias="${esc(alias)}" data-field="file" value="${esc(entry.file ?? "")}" class="${CLS.input}"></label>`;
    html += `<label class="${CLS.label}">Delimiter<input data-alias="${esc(alias)}" data-field="delimiter" value="${esc(entry.delimiter ?? ";")}" class="${CLS.input}"></label>`;
    html += `<label class="${CLS.label}">Encoding<input data-alias="${esc(alias)}" data-field="encoding" value="${esc(entry.encoding ?? "utf-8-sig")}" class="${CLS.input}"></label>`;
    html += `</div></div>`;
  }
  html += `<button type="button" class="${CLS.add}" id="add-dataset">+ Add dataset</button>`;
  $("#form").innerHTML = html;
  for (const el of $("#form").querySelectorAll("[data-alias]")) el.addEventListener("input", () => { d.datasets[el.dataset.alias][el.dataset.field] = el.value; markFormDirty(); });
  for (const b of $("#form").querySelectorAll("[data-remove-alias]")) b.addEventListener("click", () => { delete d.datasets[b.dataset.removeAlias]; markFormDirty(); renderDatasetForm(); });
  $("#add-dataset").addEventListener("click", () => {
    const alias = window.prompt("New dataset alias:");
    if (!alias || d.datasets[alias]) return;
    d.datasets[alias] = { file: "", delimiter: ";", encoding: "utf-8-sig" };
    markFormDirty(); renderDatasetForm();
  });
}

/* ---------------- Contrato form ---------------- */
const CONTRATO_SECTIONS = [["dados_contratuais", "Dados contratuais"], ["ajuste_inms", "Ajuste NMS"], ["desconto_regulatorio", "Desconto regulatório"]];
function renderContratoForm() {
  const d = state.contrato; if (!d) return;
  $("#form-file").textContent = "Contract constants";
  let html = "";
  for (const [key, title] of CONTRATO_SECTIONS) { const entry = d[key]; html += `<section class="${CLS.step}"><h2 class="${CLS.stepHeading}">${esc(title)}</h2><p class="${CLS.hint}">Lives in <code>${esc(entry.path)}</code>.</p>${renderChildren(entry.config, [key, "config"])}</section>`; }
  $("#form").innerHTML = html;
  wireForm(d, $("#form"), renderContratoForm);
}

/* ---------------- open / save ---------------- */
export async function guardDiscard() { if (!isDirty()) return true; return window.confirm("Discard unsaved changes?"); }
export async function openFile(path) { if (path === state.current || !(await guardDiscard())) return; const data = await api(`/api/file?path=${encodeURIComponent(path)}`); state.mode = "file"; state.current = path; state.original = data.content; $("#editor").value = data.content; $("#current-file").textContent = path; showEditor(); renderFiles(); renderDirty(); }
export async function openIndicator(key, orgao) { if (!(await guardDiscard())) return; const doc = await api(`/api/indicator?key=${encodeURIComponent(key)}&orgao=${encodeURIComponent(orgao)}`); state.mode = "indicator"; state.indicator = doc; state.indicatorKey = key; state.formDirty = false; showForm(); renderForm(); renderIndicators(); renderDirty(); }
export async function openCategoria(orgao) { if (state.mode === "categoria" && state.categoria && state.categoria.orgao === orgao) return; if (!(await guardDiscard())) return; const doc = await api(`/api/categoria?orgao=${encodeURIComponent(orgao)}`); state.mode = "categoria"; state.categoria = doc; state.formDirty = false; showForm(); renderCategoriaForm(); renderCategoriaNav(); renderDirty(); }
export async function openDataset() { if (state.mode === "dataset" || !(await guardDiscard())) return; const doc = await api("/api/datasets"); state.mode = "dataset"; state.dataset = doc; state.formDirty = false; showForm(); renderDatasetForm(); renderDatasetNav(); renderDirty(); }
export async function openContrato() { if (state.mode === "contrato" || !(await guardDiscard())) return; const doc = await api("/api/contrato"); state.mode = "contrato"; state.contrato = doc; state.formDirty = false; showForm(); renderContratoForm(); renderContratoNav(); renderDirty(); }
export async function save() { if (state.mode === "indicator") return saveIndicator(); if (state.mode === "categoria") return saveCategoria(); if (state.mode === "dataset") return saveDataset(); if (state.mode === "contrato") return saveContrato(); if (!state.current) return; const data = await api("/api/file", { method: "PUT", body: JSON.stringify({ path: state.current, content: $("#editor").value }) }); state.original = $("#editor").value; renderDirty(); toast(data.backup ? `Saved. Backup: ${data.backup}` : "Saved."); }
async function saveIndicator() { if (!state.indicator) return; const data = await api("/api/indicator", { method: "PUT", body: JSON.stringify(state.indicator) }); state.formDirty = false; renderDirty(); toast(data.saved ? "Indicator saved." : "Saved."); }
async function saveCategoria() { if (!state.categoria) return; const data = await api("/api/categoria", { method: "PUT", body: JSON.stringify(state.categoria) }); state.formDirty = false; renderDirty(); toast(data.saved ? "Categorias saved." : "Saved."); }
async function saveDataset() { if (!state.dataset) return; const data = await api("/api/datasets", { method: "PUT", body: JSON.stringify(state.dataset) }); state.formDirty = false; renderDirty(); toast(data.saved ? "Datasets saved." : "Saved."); }
async function saveContrato() { if (!state.contrato) return; const data = await api("/api/contrato", { method: "PUT", body: JSON.stringify(state.contrato) }); state.formDirty = false; renderDirty(); toast(data.saved ? "Contract constants saved." : "Saved."); }

/* ---------------- warnings panel (floating card, scroll-to + highlight target) ---------------- */
const WARNING_CODE_LABEL = { in_values_unmatched: "Valor não reconhecido", outros_leftover: "Caiu em \"outros\"" };
function findFieldByPath(container, path) {
  const target = JSON.stringify(path);
  for (const el of container.querySelectorAll("[data-path]")) if (JSON.stringify(JSON.parse(el.dataset.path)) === target) return el;
  return null;
}
function highlightTargetField(path) {
  requestAnimationFrame(() => {
    const el = findFieldByPath($("#form"), path);
    if (!el) return;
    let node = el; while (node && node !== $("#form")) { if (node.tagName === "DETAILS") node.open = true; node = node.parentElement; }
    const card = el.closest(".rounded-lg") || el;
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.classList.add("warning-highlight", "outline-2", "outline-warn", "outline-offset-2");
    setTimeout(() => card.classList.remove("warning-highlight", "outline-2", "outline-warn", "outline-offset-2"), 1900);
  });
}
async function openWarningTarget(target) {
  if (target.family !== "categorias") return;
  if (!(await guardDiscard())) return;
  await openCategoria(target.orgao);
  highlightTargetField(target.path);
}
function warningRowHtml(w, i) {
  const clickable = !!w.target;
  const tag = clickable ? "button" : "div";
  const base = "flex w-full items-center gap-2 border-b border-line px-2.5 py-2 text-left text-xs last:border-b-0";
  const extra = clickable ? ` type="button" class="${base} cursor-pointer hover:bg-[#21304a]" data-warning-jump="${i}"` : ` class="${base} cursor-default text-[#8e9bb0]"`;
  return `<${tag}${extra}><span class="flex-none rounded-full bg-[#3a2c0f] px-2 py-0.5 text-[10px] font-bold whitespace-nowrap text-warn">${esc(WARNING_CODE_LABEL[w.code] || "Aviso")}</span><span class="flex-1 leading-snug">${esc(w.message)}</span>${clickable ? '<span class="flex-none text-accent">→</span>' : ""}</${tag}>`;
}
export function renderWarningsPanel(warnings) {
  const panel = $("#warnings-panel");
  state.warnings = warnings;
  const show = warnings.length > 0 && !state.warningsDismissed;
  panel.classList.toggle("hidden", !show);
  if (!show) return;
  panel.innerHTML = `<div class="sticky top-0 flex items-center justify-between border-b border-line bg-[#151f2f] px-2.5 py-2 text-xs font-bold text-warn"><span>Warnings (${warnings.length})</span><button type="button" class="warnings-close cursor-pointer border-0 bg-transparent px-1 text-base text-inherit" aria-label="Dismiss">×</button></div>` + warnings.map(warningRowHtml).join("");
  panel.querySelector(".warnings-close").addEventListener("click", () => { state.warningsDismissed = true; panel.classList.add("hidden"); });
  for (const el of panel.querySelectorAll("[data-warning-jump]")) el.addEventListener("click", () => { const w = warnings[Number(el.dataset.warningJump)]; if (w.target) openWarningTarget(w.target).catch(e => toast(e.message)); });
}
