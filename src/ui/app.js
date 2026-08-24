"use strict";
const $ = (s) => document.querySelector(s);
const state = { files: [], current: null, original: "", job: null, poll: null, steps: [], mode: "file", indicators: [], indicator: null, indicatorKey: "", formDirty: false };
const NEEDS_COMPETENCE = new Set(["measure", "report", "consolidate", "split", "run"]);
const NEEDS_AGENCY = new Set(["bootstrap", "measure", "report", "split", "run"]);
const STRICT_STEPS = new Set(["measure", "split"]);
const FINAL_MONTH_STEPS = new Set(["report", "consolidate"]);
const toast = (message) => { const el = $("#toast"); el.textContent = message; el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 2200); };
async function api(path, options = {}) { const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options }); const body = await r.json().catch(() => ({ error: `HTTP ${r.status}` })); if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`); return body; }
function isDirty() { if (state.mode === "indicator") return state.formDirty; return state.current !== null && $("#editor").value !== state.original; }
function renderDirty() { const dirty = isDirty(); $("#dirty").classList.toggle("hidden", !dirty); $("#form-dirty").classList.toggle("hidden", state.mode !== "indicator" || !state.formDirty); $("#save").disabled = !dirty; }
function showEditor() { $("#empty").classList.add("hidden"); $("#form-wrap").classList.add("hidden"); $("#editor-wrap").classList.remove("hidden"); }
function showForm() { $("#empty").classList.add("hidden"); $("#editor-wrap").classList.add("hidden"); $("#form-wrap").classList.remove("hidden"); }

/* ---------------- INMS form model ---------------- */
const ENUMS = {
  "calculation.shape": ["ratio", "segmented_ratio", "count_difference", "external_catalog_sum", "precomputed_table"],
  "calculation.aggregation": ["count_distinct", "sum", "precomputed"],
  "target.operator": [">=", "<="],
  "quality_gates.checks.type": ["not_null", "in_set"],
};
const esc = (v) => String(v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const labelOf = (k) => String(k || "").replace(/_/g, " ").replace(/\b[a-z]/g, (c) => c.toUpperCase());
const normPath = (p) => p.replace(/\.\d+\./g, ".");
const isInmsPath = (p) => /(^|\/)inms-\d+([.-]|$)/.test(p);

function scalarField(key, path, value) {
  const lbl = esc(labelOf(key));
  if (typeof value === "boolean") return `<label class="check"><input type="checkbox" data-path="${path}" data-coerce="bool" ${value ? "checked" : ""} onchange="setField('${path}',this)"> ${lbl}</label>`;
  const enums = ENUMS[normPath(path)];
  if (enums) return `<label>${lbl}<select data-path="${path}" onchange="setField('${path}',this)">` + enums.map((o) => `<option value="${esc(o)}"${o === String(value) ? " selected" : ""}>${esc(o)}</option>`).join("") + `</select></label>`;
  if (typeof value === "number") return `<label>${lbl}<input type="number" step="any" data-path="${path}" data-coerce="number" value="${esc(value)}" oninput="setField('${path}',this)"></label>`;
  return `<label>${lbl}<input data-path="${path}" value="${esc(value)}" oninput="setField('${path}',this)"></label>`;
}
function renderChildren(obj, path) { let html = ""; for (const [k, v] of Object.entries(obj)) html += renderNode(k, path ? `${path}.${k}` : k, v); return html; }
function renderNode(key, path, value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return renderArray(key, path, value);
  if (typeof value === "object") return `<details class="card" open><summary>${esc(labelOf(key))}</summary><div class="card-body">${renderChildren(value, path)}</div></details>`;
  return scalarField(key, path, value);
}
function renderArray(key, path, value) {
  if (value.length === 0) return `<div class="muted">${esc(labelOf(key))} — none</div>`;
  if (typeof value[0] !== "object") return `<label>${esc(labelOf(key))}<input data-path="${path}" data-coerce="list" value="${esc(value.join(", "))}" oninput="setField('${path}',this)"></label>`;
  let html = `<div class="list-label">${esc(labelOf(key))}</div>`;
  value.forEach((item, i) => { html += `<div class="card"><div class="card-head"><strong>${i + 1}</strong><button type="button" class="remove" data-remove="${path}.${i}">×</button></div><div class="card-body">${renderChildren(item, `${path}.${i}`)}</div></div>`; });
  html += `<button type="button" class="add" data-add="${path}">+ Add ${esc(labelOf(key))}</button>`;
  return html;
}
function walkTarget(keys) { let cur = state.indicator; for (let i = 0; i < keys.length - 1; i++) { const k = /^\d+$/.test(keys[i]) ? Number(keys[i]) : keys[i]; cur = cur[k]; } const last = keys[keys.length - 1]; return { parent: cur, key: /^\d+$/.test(last) ? Number(last) : last }; }
function coerce(el, kind) { if (kind === "bool") return !!el.checked; if (kind === "number") { const v = el.value; return v === "" ? undefined : Number(v); } if (kind === "list") return el.value.split(",").map((s) => s.trim()).filter(Boolean); return el.value; }
function setField(path, el) { const { parent, key } = walkTarget(path.split(".")); parent[key] = coerce(el, el.dataset.coerce); markFormDirty(); }
function defaultItem(key) { if (key === "checks") return { type: "not_null", column: "" }; if (key === "categories") return { name: "", numerator_filter: { column: "", equals: "" }, denominator_filter: { column: "", equals: "" }, step_points: 0 }; return {}; }
function addItem(path) { const { parent, key } = walkTarget(path.split(".")); if (!Array.isArray(parent[key])) parent[key] = []; parent[key].push(defaultItem(key)); }
function removeItem(path) { const { parent, key } = walkTarget(path.split(".")); if (typeof key === "number") parent.splice(key, 1); else delete parent[key]; }
function markFormDirty() { state.formDirty = true; renderDirty(); }
function renderForm() {
  const d = state.indicator; if (!d) return;
  $("#form-file").textContent = `${d.key} · ${d.orgao}`;
  let html = `<section class="step"><h2>1 · Contract (shared)</h2>`;
  if (d.shared) html += `<p class="hint">Lives in <code>${esc(d.shared.path)}</code>. Applies to all ${d.segments.length || 0} segments.</p>` + renderChildren(d.shared.config, "shared.config");
  else html += `<p class="muted">No shared contract file.</p>`;
  html += `</section><section class="step"><h2>2 · Segments — ${esc(d.orgao)}</h2>`;
  if (d.segments.length === 0) html += `<p class="muted">No segments for this agency.</p>`;
  d.segments.forEach((seg, i) => { html += `<div class="card segment"><div class="card-head"><strong>${esc(seg.category)}</strong><code class="dim">${esc(seg.path)}</code></div><div class="card-body">${renderChildren(seg.config, `segments.${i}.config`)}</div></div>`; });
  html += `</section>`;
  $("#form").innerHTML = html;
  for (const b of $("#form").querySelectorAll("[data-add]")) b.addEventListener("click", () => { addItem(b.dataset.add); renderForm(); markFormDirty(); });
  for (const b of $("#form").querySelectorAll("[data-remove]")) b.addEventListener("click", () => { removeItem(b.dataset.remove); renderForm(); markFormDirty(); });
}

/* ---------------- files + indicator list ---------------- */
async function loadFiles() { const data = await api("/api/files"); state.files = data.files; $("#workspace").textContent = ` · ${data.workspace}`; renderFiles(); }
async function loadIndicators() { state.indicators = await api("/api/indicators"); renderIndicators(); }
function renderFiles() { const q = $("#filter").value.toLowerCase(); const nav = $("#files"); nav.replaceChildren(); for (const path of state.files.filter((x) => !isInmsPath(x) && x.toLowerCase().includes(q))) { const b = document.createElement("button"); b.type = "button"; b.className = "file" + (path === state.current && state.mode === "file" ? " active" : ""); b.textContent = path; b.title = path; b.onclick = () => openFile(path); nav.appendChild(b); } }
function renderIndicators() { const q = $("#filter").value.toLowerCase(); const nav = $("#indicator-nav"); nav.replaceChildren(); for (const ind of state.indicators) { if (!ind.key.toLowerCase().includes(q) && !(ind.name || "").toLowerCase().includes(q)) continue; const det = document.createElement("details"); det.open = state.indicatorKey === ind.key; const sum = document.createElement("summary"); sum.textContent = `${ind.key} · ${ind.name || "unnamed"}`; det.appendChild(sum); for (const org of ind.orgaos) { const b = document.createElement("button"); b.type = "button"; b.className = "file" + (state.mode === "indicator" && state.indicator && state.indicator.key === ind.key && state.indicator.orgao === org ? " active" : ""); b.textContent = org; const dim = document.createElement("span"); dim.className = "file-dim"; dim.textContent = ind.segments.filter((s) => s.orgao === org).map((s) => s.category).join(", "); b.appendChild(dim); b.onclick = () => openIndicator(ind.key, org); det.appendChild(b); } nav.appendChild(det); } }
async function guardDiscard() { if (!isDirty()) return true; return window.confirm("Discard unsaved changes?"); }

/* ---------------- open / save ---------------- */
async function openFile(path) { if (path === state.current || !(await guardDiscard())) return; const data = await api(`/api/file?path=${encodeURIComponent(path)}`); state.mode = "file"; state.current = path; state.original = data.content; $("#editor").value = data.content; $("#current-file").textContent = path; showEditor(); renderFiles(); renderDirty(); }
async function openIndicator(key, orgao) { if (!(await guardDiscard())) return; const doc = await api(`/api/indicator?key=${encodeURIComponent(key)}&orgao=${encodeURIComponent(orgao)}`); state.mode = "indicator"; state.indicator = doc; state.indicatorKey = key; state.formDirty = false; showForm(); renderForm(); renderIndicators(); renderDirty(); }
async function save() { if (state.mode === "indicator") return saveIndicator(); if (!state.current) return; const data = await api("/api/file", { method: "PUT", body: JSON.stringify({ path: state.current, content: $("#editor").value }) }); state.original = $("#editor").value; renderDirty(); toast(data.backup ? `Saved. Backup: ${data.backup}` : "Saved."); }
async function saveIndicator() { if (!state.indicator) return; const data = await api("/api/indicator", { method: "PUT", body: JSON.stringify(state.indicator) }); state.formDirty = false; renderDirty(); toast(data.saved ? "Indicator saved." : "Saved."); }

/* ---------------- pipeline ---------------- */
function updateStepVisibility() { const step = $("#step").value; $("#competence-field").classList.toggle("hidden", !NEEDS_COMPETENCE.has(step)); $("#agency-field").classList.toggle("hidden", !NEEDS_AGENCY.has(step)); $("#strict-field").classList.toggle("hidden", !STRICT_STEPS.has(step)); $("#final-month-field").classList.toggle("hidden", !FINAL_MONTH_STEPS.has(step)); $("#force-field").classList.toggle("hidden", step !== "run"); $("#clean-field").classList.toggle("hidden", step !== "run"); }
function renderSteps() { const el = $("#steps"); el.replaceChildren(); for (const entry of state.steps) { const row = document.createElement("div"); row.className = "check"; row.style.justifyContent = "space-between"; const label = document.createElement("span"); label.textContent = `${entry.step} — ${entry.status}`; row.appendChild(label); const retry = document.createElement("button"); retry.type = "button"; retry.textContent = "Retry"; retry.disabled = !!state.job; retry.onclick = () => startJob(entry.step, entry.payload).catch(e => toast(e.message)); row.appendChild(retry); el.appendChild(row); } }
async function startJob(step, payload) { const data = await api("/api/pipeline", { method: "POST", body: JSON.stringify(payload) }); state.job = data.job_id; state.steps.push({ id: data.job_id, step, payload, status: "running" }); renderSteps(); $("#run").disabled = true; $("#stop").classList.remove("hidden"); $("#output").textContent = `Started: ${data.command}\n`; poll(); state.poll = setInterval(poll, 900); }
async function run() { if (isDirty()) { toast("Save or discard changes before running."); return; } const step = $("#step").value; const payload = { command: step }; if (NEEDS_COMPETENCE.has(step)) { const competence = $("#competence").value; if (!competence) { toast("Choose a competence month."); return; } payload.competence = competence; } if (NEEDS_AGENCY.has(step)) payload.agency = $("#agency").value; if (STRICT_STEPS.has(step)) payload.strict = $("#strict").checked; if (FINAL_MONTH_STEPS.has(step)) payload.final_month = $("#final-month").checked; if (step === "run") { payload.force = $("#force").checked; payload.clean = $("#clean").checked; } await startJob(step, payload); }
async function poll() { if (!state.job) return; try { const data = await api(`/api/pipeline/${state.job}`); $("#output").textContent = data.output || "Running..."; $("#output").scrollTop = $("#output").scrollHeight; const entry = state.steps.find(s => s.id === state.job); if (entry) entry.status = data.status; if (data.status !== "running") { clearInterval(state.poll); state.poll = null; state.job = null; $("#run").disabled = false; $("#stop").classList.add("hidden"); toast(`Pipeline ${data.status}.`); renderSteps(); } } catch (e) { clearInterval(state.poll); $("#run").disabled = false; toast(e.message); } }
async function stop() { if (!state.job) return; await api(`/api/pipeline/${state.job}`, { method: "DELETE" }); }
$("#editor").addEventListener("input", renderDirty); $("#filter").addEventListener("input", () => { renderFiles(); renderIndicators(); }); $("#save").addEventListener("click", () => save().catch(e => toast(e.message))); $("#reload").addEventListener("click", async () => { if (await guardDiscard()) { state.current = null; state.indicator = null; state.mode = "file"; await loadFiles(); await loadIndicators(); toast("File list reloaded."); } }); $("#step").addEventListener("change", updateStepVisibility); $("#run").addEventListener("click", () => run().catch(e => toast(e.message))); $("#stop").addEventListener("click", () => stop().catch(e => toast(e.message))); window.addEventListener("beforeunload", e => { if (isDirty()) { e.preventDefault(); e.returnValue = ""; } });
updateStepVisibility(); const d = new Date(); d.setMonth(d.getMonth() - 1); $("#competence").value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; Promise.all([loadFiles(), loadIndicators()]).catch(e => toast(e.message));