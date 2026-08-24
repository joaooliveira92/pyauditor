"use strict";
const $ = (s) => document.querySelector(s);
const state = { files: [], current: null, original: "", job: null, poll: null, steps: [], mode: "file", indicators: [], indicator: null, indicatorKey: "", categoria: null, dataset: null, contrato: null, formDirty: false, warnings: [], warningsDismissed: false, history: [] };
const ORGAOS = ["MinC", "MTur"];
const NEEDS_COMPETENCE = new Set(["measure", "report", "consolidate", "split", "run"]);
const NEEDS_AGENCY = new Set(["bootstrap", "measure", "report", "split", "run"]);
const STRICT_STEPS = new Set(["measure", "split"]);
const FINAL_MONTH_STEPS = new Set(["report", "consolidate"]);
const toast = (message) => { const el = $("#toast"); el.textContent = message; el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 2200); };
async function api(path, options = {}) { const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options }); const body = await r.json().catch(() => ({ error: `HTTP ${r.status}` })); if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`); return body; }
function isDirty() { if (state.mode !== "file") return state.formDirty; return state.current !== null && $("#editor").value !== state.original; }
function renderDirty() { const dirty = isDirty(); $("#dirty").classList.toggle("hidden", !dirty); $("#form-dirty").classList.toggle("hidden", state.mode === "file" || !state.formDirty); $("#save").disabled = !dirty; }
function showEditor() { $("#empty").classList.add("hidden"); $("#form-wrap").classList.add("hidden"); $("#editor-wrap").classList.remove("hidden"); }
function showForm() { $("#empty").classList.add("hidden"); $("#editor-wrap").classList.add("hidden"); $("#form-wrap").classList.remove("hidden"); }

/* ---------------- generic nested-doc form model (path = array of string|number keys) ---------------- */
const ENUMS = {
  "calculation.shape": ["ratio", "segmented_ratio", "count_difference", "external_catalog_sum", "precomputed_table"],
  "calculation.aggregation": ["count_distinct", "sum", "precomputed"],
  "target.operator": [">=", "<="],
  "quality_gates.checks.type": ["not_null", "in_set"],
};
const esc = (v) => String(v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const labelOf = (k) => String(k || "").replace(/_/g, " ").replace(/\b[a-z]/g, (c) => c.toUpperCase());
const normPath = (path) => path.filter((p) => typeof p !== "number").join(".");
const attrPath = (path) => esc(JSON.stringify(path));
const isInmsPath = (p) => /(^|\/)inms-\d+([.-]|$)/.test(p);
const FAMILY_FILE_RE = /(^|\/)(categorias|datasets|dados_contratuais|ajuste_inms|desconto_regulat[oó]rio)\.yaml$/;
const isFamilyFile = (p) => isInmsPath(p) || FAMILY_FILE_RE.test(p);

function scalarField(key, path, value) {
  const lbl = esc(labelOf(key));
  const attr = attrPath(path);
  if (typeof value === "boolean") return `<label class="check"><input type="checkbox" data-path='${attr}' data-coerce="bool" ${value ? "checked" : ""}> ${lbl}</label>`;
  const enums = ENUMS[normPath(path)];
  if (enums) return `<label>${lbl}<select data-path='${attr}'>` + enums.map((o) => `<option value="${esc(o)}"${o === String(value) ? " selected" : ""}>${esc(o)}</option>`).join("") + `</select></label>`;
  if (typeof value === "number") return `<label>${lbl}<input type="number" step="any" data-path='${attr}' data-coerce="number" value="${esc(value)}"></label>`;
  if (key === "descricao") return `<label>${lbl}<textarea data-path='${attr}' rows="3">${esc(value)}</textarea></label>`;
  return `<label>${lbl}<input data-path='${attr}' value="${esc(value)}"></label>`;
}
function renderChildren(obj, path) { let html = ""; for (const [k, v] of Object.entries(obj)) html += renderNode(k, [...path, k], v); return html; }
function renderNode(key, path, value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return renderArray(key, path, value);
  if (typeof value === "object") return `<details class="card" open><summary>${esc(labelOf(key))}</summary><div class="card-body">${renderChildren(value, path)}</div></details>`;
  return scalarField(key, path, value);
}
function renderArray(key, path, value) {
  if (value.length === 0) return `<div class="muted">${esc(labelOf(key))} — none</div>`;
  if (typeof value[0] !== "object") return `<label>${esc(labelOf(key))}<input data-path='${attrPath(path)}' data-coerce="list" value="${esc(value.join(", "))}"></label>`;
  let html = `<div class="list-label">${esc(labelOf(key))}</div>`;
  value.forEach((item, i) => { html += `<div class="card"><div class="card-head"><strong>${i + 1}</strong><button type="button" class="remove" data-remove='${attrPath([...path, i])}'>×</button></div><div class="card-body">${renderChildren(item, [...path, i])}</div></div>`; });
  html += `<button type="button" class="add" data-add='${attrPath(path)}'>+ Add ${esc(labelOf(key))}</button>`;
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
  let html = `<section class="step"><h2>1 · Contract (shared)</h2>`;
  if (d.shared) html += `<p class="hint">Lives in <code>${esc(d.shared.path)}</code>. Applies to all ${d.segments.length || 0} segments.</p>` + renderChildren(d.shared.config, ["shared", "config"]);
  else html += `<p class="muted">No shared contract file.</p>`;
  html += `</section><section class="step"><h2>2 · Segments — ${esc(d.orgao)}</h2>`;
  if (d.segments.length === 0) html += `<p class="muted">No segments for this agency.</p>`;
  d.segments.forEach((seg, i) => { html += `<div class="card segment"><div class="card-head"><strong>${esc(seg.category)}</strong><code class="dim">${esc(seg.path)}</code></div><div class="card-body">${renderChildren(seg.config, ["segments", i, "config"])}</div></div>`; });
  html += `</section>`;
  $("#form").innerHTML = html;
  wireForm(d, $("#form"), renderForm);
}

/* ---------------- Categorias form ---------------- */
function renderCategoriaForm() {
  const d = state.categoria; if (!d) return;
  $("#form-file").textContent = `Categorias · ${d.orgao}`;
  let html = `<p class="hint">Lives in <code>${esc(d.path)}</code>.</p>`;
  const cats = d.config.categorias || {};
  for (const [catKey, cat] of Object.entries(cats)) {
    html += `<details class="card" open><summary>${esc(catKey)} — ${esc(cat.label || "")}</summary><div class="card-body">`;
    html += `<label>Label<input data-path='${attrPath(["config", "categorias", catKey, "label"])}' value="${esc(cat.label ?? "")}"></label>`;
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
  let html = `<div class="card"><div class="card-head"><strong>${esc(inmsKey)}</strong></div><div class="card-body">`;
  html += `<label>Mode<select data-mode-path='${attrPath(base)}'>` +
    `<option value="grupo_executor"${isGrupo ? " selected" : ""}>Filtered by Grupo executor</option>` +
    `<option value="whole_indicator"${!isGrupo ? " selected" : ""}>Whole indicator (no filter)</option>` +
    `</select></label>`;
  if (isGrupo) {
    html += `<label>Filter type<select data-filter-path='${attrPath(base)}'>` +
      `<option value="in_values"${filterKind === "in_values" ? " selected" : ""}>Match any of these values</option>` +
      `<option value="catch_all_contains"${filterKind === "catch_all_contains" ? " selected" : ""}>Contains this text</option>` +
      `</select></label>`;
    if (filterKind === "in_values") html += `<label>Values (comma-separated)<input data-path='${attrPath([...base, "in_values"])}' data-coerce="list" value="${esc((entry.in_values || []).join(", "))}"></label>`;
    else html += `<label>Contains<input data-path='${attrPath([...base, "catch_all_contains"])}' value="${esc(entry.catch_all_contains ?? "")}"></label>`;
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
  let html = `<p class="hint">Lives in <code>${esc(d.path)}</code>. Alias → CSV file + parsing options.</p>`;
  for (const [alias, entry] of Object.entries(d.datasets)) {
    html += `<div class="card"><div class="card-head"><strong>${esc(alias)}</strong><button type="button" class="remove" data-remove-alias="${esc(alias)}">×</button></div><div class="card-body">`;
    html += `<label>File<input data-alias="${esc(alias)}" data-field="file" value="${esc(entry.file ?? "")}"></label>`;
    html += `<label>Delimiter<input data-alias="${esc(alias)}" data-field="delimiter" value="${esc(entry.delimiter ?? ";")}"></label>`;
    html += `<label>Encoding<input data-alias="${esc(alias)}" data-field="encoding" value="${esc(entry.encoding ?? "utf-8-sig")}"></label>`;
    html += `</div></div>`;
  }
  html += `<button type="button" class="add" id="add-dataset">+ Add dataset</button>`;
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
  for (const [key, title] of CONTRATO_SECTIONS) { const entry = d[key]; html += `<section class="step"><h2>${esc(title)}</h2><p class="hint">Lives in <code>${esc(entry.path)}</code>.</p>${renderChildren(entry.config, [key, "config"])}</section>`; }
  $("#form").innerHTML = html;
  wireForm(d, $("#form"), renderContratoForm);
}

/* ---------------- files + family navs ---------------- */
async function loadFiles() { const data = await api("/api/files"); state.files = data.files; $("#workspace").textContent = ` · ${data.workspace}`; renderFiles(); }
async function loadIndicators() { state.indicators = (await api("/api/indicators")).indicators; renderIndicators(); }
function renderFiles() { const q = $("#filter").value.toLowerCase(); const nav = $("#files"); nav.replaceChildren(); for (const path of state.files.filter((x) => !isFamilyFile(x) && x.toLowerCase().includes(q))) { const b = document.createElement("button"); b.type = "button"; b.className = "file" + (path === state.current && state.mode === "file" ? " active" : ""); b.textContent = path; b.title = path; b.onclick = () => openFile(path); nav.appendChild(b); } }
function renderIndicators() { const q = $("#filter").value.toLowerCase(); const nav = $("#indicator-nav"); nav.replaceChildren(); for (const ind of state.indicators) { if (!ind.key.toLowerCase().includes(q) && !(ind.name || "").toLowerCase().includes(q)) continue; const det = document.createElement("details"); det.open = state.indicatorKey === ind.key; const sum = document.createElement("summary"); sum.textContent = `${ind.key} · ${ind.name || "unnamed"}`; det.appendChild(sum); for (const org of ind.orgaos) { const b = document.createElement("button"); b.type = "button"; b.className = "file" + (state.mode === "indicator" && state.indicator && state.indicator.key === ind.key && state.indicator.orgao === org ? " active" : ""); b.textContent = org; const dim = document.createElement("span"); dim.className = "file-dim"; dim.textContent = ind.segments.filter((s) => s.orgao === org).map((s) => s.category).join(", "); b.appendChild(dim); b.onclick = () => openIndicator(ind.key, org); det.appendChild(b); } nav.appendChild(det); } }
function renderCategoriaNav() { const nav = $("#categoria-nav"); nav.replaceChildren(); for (const orgao of ORGAOS) { const b = document.createElement("button"); b.type = "button"; b.className = "file" + (state.mode === "categoria" && state.categoria && state.categoria.orgao === orgao ? " active" : ""); b.textContent = orgao; b.onclick = () => openCategoria(orgao).catch((e) => toast(e.message)); nav.appendChild(b); } }
function renderDatasetNav() { const nav = $("#dataset-nav"); nav.replaceChildren(); const b = document.createElement("button"); b.type = "button"; b.className = "file" + (state.mode === "dataset" ? " active" : ""); b.textContent = "datasets.yaml"; b.onclick = () => openDataset().catch((e) => toast(e.message)); nav.appendChild(b); }
function renderContratoNav() { const nav = $("#contrato-nav"); nav.replaceChildren(); const b = document.createElement("button"); b.type = "button"; b.className = "file" + (state.mode === "contrato" ? " active" : ""); b.textContent = "Contract constants"; b.onclick = () => openContrato().catch((e) => toast(e.message)); nav.appendChild(b); }
async function guardDiscard() { if (!isDirty()) return true; return window.confirm("Discard unsaved changes?"); }

/* ---------------- open / save ---------------- */
async function openFile(path) { if (path === state.current || !(await guardDiscard())) return; const data = await api(`/api/file?path=${encodeURIComponent(path)}`); state.mode = "file"; state.current = path; state.original = data.content; $("#editor").value = data.content; $("#current-file").textContent = path; showEditor(); renderFiles(); renderDirty(); }
async function openIndicator(key, orgao) { if (!(await guardDiscard())) return; const doc = await api(`/api/indicator?key=${encodeURIComponent(key)}&orgao=${encodeURIComponent(orgao)}`); state.mode = "indicator"; state.indicator = doc; state.indicatorKey = key; state.formDirty = false; showForm(); renderForm(); renderIndicators(); renderDirty(); }
async function openCategoria(orgao) { if (state.mode === "categoria" && state.categoria && state.categoria.orgao === orgao) return; if (!(await guardDiscard())) return; const doc = await api(`/api/categoria?orgao=${encodeURIComponent(orgao)}`); state.mode = "categoria"; state.categoria = doc; state.formDirty = false; showForm(); renderCategoriaForm(); renderCategoriaNav(); renderDirty(); }
async function openDataset() { if (state.mode === "dataset" || !(await guardDiscard())) return; const doc = await api("/api/datasets"); state.mode = "dataset"; state.dataset = doc; state.formDirty = false; showForm(); renderDatasetForm(); renderDatasetNav(); renderDirty(); }
async function openContrato() { if (state.mode === "contrato" || !(await guardDiscard())) return; const doc = await api("/api/contrato"); state.mode = "contrato"; state.contrato = doc; state.formDirty = false; showForm(); renderContratoForm(); renderContratoNav(); renderDirty(); }
async function save() { if (state.mode === "indicator") return saveIndicator(); if (state.mode === "categoria") return saveCategoria(); if (state.mode === "dataset") return saveDataset(); if (state.mode === "contrato") return saveContrato(); if (!state.current) return; const data = await api("/api/file", { method: "PUT", body: JSON.stringify({ path: state.current, content: $("#editor").value }) }); state.original = $("#editor").value; renderDirty(); toast(data.backup ? `Saved. Backup: ${data.backup}` : "Saved."); }
async function saveIndicator() { if (!state.indicator) return; const data = await api("/api/indicator", { method: "PUT", body: JSON.stringify(state.indicator) }); state.formDirty = false; renderDirty(); toast(data.saved ? "Indicator saved." : "Saved."); }
async function saveCategoria() { if (!state.categoria) return; const data = await api("/api/categoria", { method: "PUT", body: JSON.stringify(state.categoria) }); state.formDirty = false; renderDirty(); toast(data.saved ? "Categorias saved." : "Saved."); }
async function saveDataset() { if (!state.dataset) return; const data = await api("/api/datasets", { method: "PUT", body: JSON.stringify(state.dataset) }); state.formDirty = false; renderDirty(); toast(data.saved ? "Datasets saved." : "Saved."); }
async function saveContrato() { if (!state.contrato) return; const data = await api("/api/contrato", { method: "PUT", body: JSON.stringify(state.contrato) }); state.formDirty = false; renderDirty(); toast(data.saved ? "Contract constants saved." : "Saved."); }

/* ---------------- pipeline ---------------- */
function updateStepVisibility() { const step = $("#step").value; $("#competence-field").classList.toggle("hidden", !NEEDS_COMPETENCE.has(step)); $("#agency-field").classList.toggle("hidden", !NEEDS_AGENCY.has(step)); $("#strict-field").classList.toggle("hidden", !STRICT_STEPS.has(step)); $("#final-month-field").classList.toggle("hidden", !FINAL_MONTH_STEPS.has(step)); $("#force-field").classList.toggle("hidden", step !== "run"); $("#clean-field").classList.toggle("hidden", step !== "run"); }
function renderSteps() { const el = $("#steps"); el.replaceChildren(); for (const entry of state.steps) { const row = document.createElement("div"); row.className = "check"; row.style.justifyContent = "space-between"; const label = document.createElement("span"); label.textContent = `${entry.step} — ${entry.status}`; row.appendChild(label); const retry = document.createElement("button"); retry.type = "button"; retry.textContent = "Retry"; retry.disabled = !!state.job; retry.onclick = () => startJob(entry.step, entry.payload).catch(e => toast(e.message)); row.appendChild(retry); el.appendChild(row); } }
async function startJob(step, payload) { const data = await api("/api/pipeline", { method: "POST", body: JSON.stringify(payload) }); state.job = data.job_id; state.steps.push({ id: data.job_id, step, payload, status: "running" }); renderSteps(); $("#run").disabled = true; $("#stop").classList.remove("hidden"); $("#output").textContent = `Started: ${data.command}\n`; state.warningsDismissed = false; renderWarningsPanel([]); poll(); state.poll = setInterval(poll, 900); }
async function run() { if (isDirty()) { toast("Save or discard changes before running."); return; } const step = $("#step").value; const payload = { command: step }; if (NEEDS_COMPETENCE.has(step)) { const competence = $("#competence").value; if (!competence) { toast("Choose a competence month."); return; } payload.competence = competence; } if (NEEDS_AGENCY.has(step)) payload.agency = $("#agency").value; if (STRICT_STEPS.has(step)) payload.strict = $("#strict").checked; if (FINAL_MONTH_STEPS.has(step)) payload.final_month = $("#final-month").checked; if (step === "run") { payload.force = $("#force").checked; payload.clean = $("#clean").checked; } await startJob(step, payload); }
async function poll() { if (!state.job) return; try { const data = await api(`/api/pipeline/${state.job}`); $("#output").textContent = data.output || "Running..."; $("#output").scrollTop = $("#output").scrollHeight; renderWarningsPanel(data.warnings || []); const entry = state.steps.find(s => s.id === state.job); if (entry) entry.status = data.status; if (data.status !== "running") { clearInterval(state.poll); state.poll = null; state.job = null; $("#run").disabled = false; $("#stop").classList.add("hidden"); toast(`Pipeline ${data.status}.`); renderSteps(); loadHistory().catch(() => {}); } } catch (e) { clearInterval(state.poll); $("#run").disabled = false; toast(e.message); } }
async function stop() { if (!state.job) return; await api(`/api/pipeline/${state.job}`, { method: "DELETE" }); }

/* ---------------- run history (persisted server-side across reloads) ---------------- */
function fmtStarted(iso) { const d = new Date(iso); return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(); }
async function loadHistory() { state.history = (await api("/api/pipeline")).jobs; renderHistory(); }
function renderHistory() {
  $("#history-count").textContent = state.history.length;
  const list = $("#history-list"); list.replaceChildren();
  for (const job of state.history) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "file";
    b.textContent = `${job.status} · ${fmtStarted(job.started_at)} · ${job.command}`;
    b.title = job.command;
    b.onclick = () => viewHistoryJob(job.job_id).catch(e => toast(e.message));
    list.appendChild(b);
  }
}
async function viewHistoryJob(jobId) { const data = await api(`/api/pipeline/${jobId}`); $("#output").textContent = data.output || "(no output)"; renderWarningsPanel(data.warnings || []); }
$("#editor").addEventListener("input", renderDirty); $("#filter").addEventListener("input", () => { renderFiles(); renderIndicators(); }); $("#save").addEventListener("click", () => save().catch(e => toast(e.message))); $("#reload").addEventListener("click", async () => { if (await guardDiscard()) { state.current = null; state.indicator = null; state.categoria = null; state.dataset = null; state.contrato = null; state.mode = "file"; await loadFiles(); await loadIndicators(); renderCategoriaNav(); renderDatasetNav(); renderContratoNav(); toast("File list reloaded."); } }); $("#step").addEventListener("change", updateStepVisibility); $("#run").addEventListener("click", () => run().catch(e => toast(e.message))); $("#stop").addEventListener("click", () => stop().catch(e => toast(e.message))); window.addEventListener("beforeunload", e => { if (isDirty()) { e.preventDefault(); e.returnValue = ""; } });
updateStepVisibility(); const d = new Date(); d.setMonth(d.getMonth() - 1); $("#competence").value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; renderCategoriaNav(); renderDatasetNav(); renderContratoNav(); Promise.all([loadFiles(), loadIndicators(), loadHistory()]).catch(e => toast(e.message));


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
    const card = el.closest(".card") || el;
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.classList.add("warning-highlight");
    setTimeout(() => card.classList.remove("warning-highlight"), 1900);
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
  const extra = clickable ? ` type="button" class="warning-row warning-row-link" data-warning-jump="${i}"` : ` class="warning-row warning-row-inert"`;
  return `<${tag}${extra}><span class="warning-code">${esc(WARNING_CODE_LABEL[w.code] || "Aviso")}</span><span class="warning-msg">${esc(w.message)}</span>${clickable ? '<span class="warning-go">→</span>' : ""}</${tag}>`;
}
function renderWarningsPanel(warnings) {
  const panel = $("#warnings-panel");
  state.warnings = warnings;
  const show = warnings.length > 0 && !state.warningsDismissed;
  panel.classList.toggle("hidden", !show);
  if (!show) return;
  panel.innerHTML = `<div class="warnings-head"><span>Warnings (${warnings.length})</span><button type="button" class="warnings-close" aria-label="Dismiss">×</button></div>` + warnings.map(warningRowHtml).join("");
  panel.querySelector(".warnings-close").addEventListener("click", () => { state.warningsDismissed = true; panel.classList.add("hidden"); });
  for (const el of panel.querySelectorAll("[data-warning-jump]")) el.addEventListener("click", () => { const w = warnings[Number(el.dataset.warningJump)]; if (w.target) openWarningTarget(w.target).catch(e => toast(e.message)); });
}
