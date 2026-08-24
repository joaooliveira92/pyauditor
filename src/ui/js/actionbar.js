"use strict";
import { $, state, api, toast, NEEDS_COMPETENCE, NEEDS_AGENCY, STRICT_STEPS, FINAL_MONTH_STEPS, CLS } from "./state.js";
import { isDirty, renderWarningsPanel } from "./main-panel.js";

function updateStepVisibility() {
  const step = $("#step").value;
  $("#competence-field").classList.toggle("hidden", !NEEDS_COMPETENCE.has(step));
  $("#agency-field").classList.toggle("hidden", !NEEDS_AGENCY.has(step));
  $("#strict-field").classList.toggle("hidden", !STRICT_STEPS.has(step));
  $("#final-month-field").classList.toggle("hidden", !FINAL_MONTH_STEPS.has(step));
  $("#force-field").classList.toggle("hidden", step !== "run");
  $("#clean-field").classList.toggle("hidden", step !== "run");
}

function renderSteps() {
  const el = $("#steps"); el.replaceChildren();
  for (const entry of state.steps) {
    const row = document.createElement("div");
    row.className = "flex items-center justify-between py-1";
    const label = document.createElement("span");
    label.textContent = `${entry.step} — ${entry.status}`;
    row.appendChild(label);
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "cursor-pointer rounded-md border border-line bg-[#182234] px-3 py-2 disabled:cursor-not-allowed disabled:opacity-45";
    retry.textContent = "Retry";
    retry.disabled = !!state.job;
    retry.onclick = () => startJob(entry.step, entry.payload).catch((e) => toast(e.message));
    row.appendChild(retry);
    el.appendChild(row);
  }
}

async function startJob(step, payload) {
  const data = await api("/api/pipeline", { method: "POST", body: JSON.stringify(payload) });
  state.job = data.job_id;
  state.steps.push({ id: data.job_id, step, payload, status: "running" });
  renderSteps();
  $("#run").disabled = true;
  $("#stop").classList.remove("hidden");
  $("#output").textContent = `Started: ${data.command}\n`;
  state.warningsDismissed = false;
  renderWarningsPanel([]);
  poll();
  state.poll = setInterval(poll, 900);
}

async function run() {
  if (isDirty()) { toast("Save or discard changes before running."); return; }
  const step = $("#step").value;
  const payload = { command: step };
  if (NEEDS_COMPETENCE.has(step)) {
    const competence = $("#competence").value;
    if (!competence) { toast("Choose a competence month."); return; }
    payload.competence = competence;
  }
  if (NEEDS_AGENCY.has(step)) payload.agency = $("#agency").value;
  if (STRICT_STEPS.has(step)) payload.strict = $("#strict").checked;
  if (FINAL_MONTH_STEPS.has(step)) payload.final_month = $("#final-month").checked;
  if (step === "run") { payload.force = $("#force").checked; payload.clean = $("#clean").checked; }
  await startJob(step, payload);
}

async function poll() {
  if (!state.job) return;
  try {
    const data = await api(`/api/pipeline/${state.job}`);
    $("#output").textContent = data.output || "Running...";
    $("#output").scrollTop = $("#output").scrollHeight;
    renderWarningsPanel(data.warnings || []);
    const entry = state.steps.find((s) => s.id === state.job);
    if (entry) entry.status = data.status;
    if (data.status !== "running") {
      clearInterval(state.poll); state.poll = null; state.job = null;
      $("#run").disabled = false;
      $("#stop").classList.add("hidden");
      toast(`Pipeline ${data.status}.`);
      renderSteps();
      loadHistory().catch(() => {});
    }
  } catch (e) {
    clearInterval(state.poll);
    $("#run").disabled = false;
    toast(e.message);
  }
}

async function stop() { if (!state.job) return; await api(`/api/pipeline/${state.job}`, { method: "DELETE" }); }

/* ---------------- run history (persisted server-side across reloads) ---------------- */
function fmtStarted(iso) { const d = new Date(iso); return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(); }
export async function loadHistory() { const data = await api("/api/pipeline"); state.history = data.jobs; renderHistory(); }
function renderHistory() {
  $("#history-count").textContent = state.history.length;
  const list = $("#history-list"); list.replaceChildren();
  for (const job of state.history) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = CLS.fileBtn + " mt-1 text-xs";
    b.textContent = `${job.status} · ${fmtStarted(job.started_at)} · ${job.command}`;
    b.title = job.command;
    b.onclick = () => viewHistoryJob(job.job_id).catch((e) => toast(e.message));
    list.appendChild(b);
  }
}
async function viewHistoryJob(jobId) { const data = await api(`/api/pipeline/${jobId}`); $("#output").textContent = data.output || "(no output)"; renderWarningsPanel(data.warnings || []); }

export function initActionbar() {
  $("#step").addEventListener("change", updateStepVisibility);
  $("#run").addEventListener("click", () => run().catch((e) => toast(e.message)));
  $("#stop").addEventListener("click", () => stop().catch((e) => toast(e.message)));
  updateStepVisibility();
  const d = new Date(); d.setMonth(d.getMonth() - 1);
  $("#competence").value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}
