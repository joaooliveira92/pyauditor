"use strict";
import { $, state, toast } from "./js/state.js";
import { save, isDirty, renderDirty, guardDiscard } from "./js/main-panel.js";
import { loadFiles, loadIndicators, renderFiles, renderIndicators, renderCategoriaNav, renderDatasetNav, renderContratoNav } from "./js/sidebar.js";
import { initActionbar, loadHistory } from "./js/actionbar.js";

$("#editor").addEventListener("input", renderDirty);
$("#filter").addEventListener("input", () => { renderFiles(); renderIndicators(); });
$("#save").addEventListener("click", () => save().catch((e) => toast(e.message)));
$("#reload").addEventListener("click", async () => {
  if (!(await guardDiscard())) return;
  state.current = null; state.indicator = null; state.categoria = null; state.dataset = null; state.contrato = null; state.mode = "file";
  await loadFiles(); await loadIndicators();
  renderCategoriaNav(); renderDatasetNav(); renderContratoNav();
  toast("File list reloaded.");
});
window.addEventListener("beforeunload", (e) => { if (isDirty()) { e.preventDefault(); e.returnValue = ""; } });

initActionbar();
renderCategoriaNav(); renderDatasetNav(); renderContratoNav();
Promise.all([loadFiles(), loadIndicators(), loadHistory()]).catch((e) => toast(e.message));
