"use strict";
import { $, state, api, toast, ORGAOS, CLS } from "./state.js";
/* Circular import: main-panel.js imports sidebar.js's nav renderers to
   refresh active-state highlighting after navigation. Safe here because
   nothing below calls these until a click fires, well after both modules
   finish evaluating. */
import { isFamilyFile, openFile, openIndicator, openCategoria, openDataset, openContrato } from "./main-panel.js";

function fileButton(text, { active, dim, onClick }) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = CLS.fileBtn + (active ? ` ${CLS.fileBtnActive}` : "");
  b.textContent = text;
  b.title = text;
  if (dim) { const s = document.createElement("span"); s.className = CLS.fileDim; s.textContent = dim; b.appendChild(s); }
  b.onclick = () => onClick().catch((e) => toast(e.message));
  return b;
}

export async function loadFiles() { const data = await api("/api/files"); state.files = data.files; $("#workspace").textContent = ` · ${data.workspace}`; renderFiles(); }
export async function loadIndicators() { const data = await api("/api/indicators"); state.indicators = data.indicators; renderIndicators(); }

export function renderFiles() {
  const q = $("#filter").value.toLowerCase();
  const nav = $("#files"); nav.replaceChildren();
  for (const path of state.files.filter((x) => !isFamilyFile(x) && x.toLowerCase().includes(q))) {
    nav.appendChild(fileButton(path, {
      active: path === state.current && state.mode === "file",
      onClick: () => openFile(path),
    }));
  }
}

export function renderIndicators() {
  const q = $("#filter").value.toLowerCase();
  const nav = $("#indicator-nav"); nav.replaceChildren();
  for (const ind of state.indicators) {
    if (!ind.key.toLowerCase().includes(q) && !(ind.name || "").toLowerCase().includes(q)) continue;
    const det = document.createElement("details");
    det.open = state.indicatorKey === ind.key;
    const sum = document.createElement("summary");
    sum.className = "block cursor-pointer truncate rounded-r border-l-2 border-l-transparent py-1.5 pr-2 pl-2.5 text-[13px] hover:bg-[#182234]";
    sum.textContent = `${ind.key} · ${ind.name || "unnamed"}`;
    sum.title = sum.textContent;
    det.appendChild(sum);
    for (const org of ind.orgaos) {
      const dim = ind.segments.filter((s) => s.orgao === org).map((s) => s.category).join(", ");
      det.appendChild(fileButton(org, {
        active: state.mode === "indicator" && state.indicator && state.indicator.key === ind.key && state.indicator.orgao === org,
        dim,
        onClick: () => openIndicator(ind.key, org),
      }));
    }
    nav.appendChild(det);
  }
}

export function renderCategoriaNav() {
  const nav = $("#categoria-nav"); nav.replaceChildren();
  for (const orgao of ORGAOS) {
    nav.appendChild(fileButton(orgao, {
      active: state.mode === "categoria" && state.categoria && state.categoria.orgao === orgao,
      onClick: () => openCategoria(orgao),
    }));
  }
}

export function renderDatasetNav() {
  const nav = $("#dataset-nav"); nav.replaceChildren();
  nav.appendChild(fileButton("datasets.yaml", { active: state.mode === "dataset", onClick: () => openDataset() }));
}

export function renderContratoNav() {
  const nav = $("#contrato-nav"); nav.replaceChildren();
  nav.appendChild(fileButton("Contract constants", { active: state.mode === "contrato", onClick: () => openContrato() }));
}
