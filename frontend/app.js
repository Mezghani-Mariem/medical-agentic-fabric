import { ApiAdapter } from "./api_adapter.js";
import { MockAdapter } from "./mock_api.js";
import { ARTIFACT_TYPES, assertAnalysis, assertHistory, assertVerification } from "./contracts.js";
import { inspectUploads } from "./input_preview.js";
import { BASELINE_POINTS, waveformPoints } from "./waveform.js";

const $ = id => document.getElementById(id);
const LABELS = { raw_ecg: "ECG brut", raw_report: "Rapport brut", processed: "Signal prétraité", features: "Caractéristiques", prediction: "Prédiction IA", validation: "Validation", explanation: "Explication", final: "Dossier final" };
const VALIDATION_LABELS = { ACCEPTED: "Contrôles de validation satisfaits", REVIEW_REQUIRED: "Revue humaine requise", REJECTED: "Dossier rejeté par les contrôles" };
let adapter = new MockAdapter();
let active = null;
let busy = false;
const cases = new Map();
const previews = new Map();

function el(tag, text = "", className = "") {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}
function tone(status) { return ["ACCEPTED", "VALID"].includes(status) ? "good" : ["REJECTED", "MODIFIED", "MISSING"].includes(status) ? "bad" : ["REVIEW_REQUIRED", "UNVERIFIABLE"].includes(status) ? "review" : "neutral"; }
function badge(node, status) { node.textContent = status; node.className = `badge ${tone(status)}`; }
function notify(message, error = false) {
  $("feedback").textContent = message;
  $("feedback").className = `feedback${error ? " error" : ""}`;
  $("feedback").hidden = false;
  if (error) $("feedback").focus();
}
function setBusy(value) {
  busy = value;
  for (const id of ["analyze-button", "sample-button", "ecg-file", "report-file", "adapter-mode", "api-url", "connect-button", "mock-scenario"]) $(id).disabled = value;
  for (const id of ["verify-button", "refresh-history", "tamper-button"]) $(id).disabled = value || !active;
  $("verify-button").disabled = value || !active?.artifacts.length;
  document.querySelectorAll(".case-item").forEach(node => { node.disabled = value; });
  $("analyze-button").firstElementChild.textContent = value ? "Traitement en cours…" : "Analyser le dossier";
  $("analysis-form").setAttribute("aria-busy", String(value));
}
function formatTime(value) {
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "medium" }) : value;
}
function plot(preview) {
  const values = preview?.values;
  const points = waveformPoints(values);
  if (!points || !Number.isSafeInteger(preview?.count) || preview.count < values.length) {
    $("signal-line").setAttribute("points", BASELINE_POINTS);
    $("signal-count").textContent = "Aucun aperçu";
    $("ecg-caption").textContent = preview
      ? "Aperçu indisponible : valeurs du signal ou nombre de points invalides."
      : "L’API ne fournit pas le signal. L’aperçu local n’est disponible qu’après un import dans cette session.";
    return;
  }
  $("signal-line").setAttribute("points", points);
  $("signal-count").textContent = `${preview.count.toLocaleString("fr-FR")} points`;
  $("ecg-caption").textContent = `${values.length} premiers points bruts affichés · Échelle visuelle automatique · Aucune interprétation clinique.`;
}

function renderArtifacts(checks = null) {
  const body = $("artifact-rows");
  body.replaceChildren();
  const lookup = new Map((checks || []).map(item => [item.artifact_id, item]));
  for (const artifact of active.artifacts) {
    const row = el("tr");
    const type = el("td");
    type.append(el("strong", LABELS[artifact.type] || artifact.type), el("code", artifact.artifact_id));
    const hash = el("td");
    hash.append(el("div", artifact.sha256, "hash-text"), el("small", `Parent : ${artifact.parent_id || "racine"}`));
    const check = lookup.get(artifact.artifact_id);
    if (check && check.status !== "VALID") {
      hash.append(el("small", `Attendue : ${check.expected_sha256 || "indisponible"}`), el("small", `Actuelle : ${check.actual_sha256 || "indisponible"}`));
    }
    const receipt = el("td");
    receipt.append(el("code", artifact.tx_id), el("small", artifact.storage_ref));
    const integrity = el("td");
    const pill = el("span");
    badge(pill, check?.status || "NON VÉRIFIÉ");
    integrity.append(pill);
    row.append(type, hash, receipt, integrity);
    body.append(row);
  }
  if (!active.artifacts.length) {
    const row = el("tr"), cell = el("td", "Aucun artefact retourné pour ce dossier.", "table-empty");
    cell.colSpan = 4; row.append(cell); body.append(row);
  }
  $("artifact-count").textContent = active.artifacts.length;
  $("artifact-completeness").textContent = active.artifacts.length === ARTIFACT_TYPES.length
    ? "MÉTADONNÉES 8/8 · STRUCTURE CONTRÔLÉE"
    : `INCOMPLET · ${active.artifacts.length}/8 MÉTADONNÉES`;
}
function renderCases() {
  $("case-list").replaceChildren();
  $("case-count").textContent = cases.size;
  for (const data of [...cases.values()].reverse()) {
    const button = el("button", "", `case-item${data.case_id === active?.case_id ? " selected" : ""}`);
    button.type = "button";
    button.disabled = busy;
    button.setAttribute("aria-label", `Ouvrir le dossier ${data.case_id}`);
    const top = el("span", "", "case-item-top");
    const pill = el("span"); badge(pill, data.validation.status);
    top.append(el("strong", data.prediction?.label || "Prédiction absente"), pill);
    button.append(top, el("code", data.case_id), el("small", `${data.ledger_mode} · ${data.artifacts.length} artefacts`));
    button.addEventListener("click", () => openCase(data.case_id));
    $("case-list").append(button);
  }
}
function renderCase(data) {
  active = data;
  cases.set(data.case_id, data);
  $("result-empty").hidden = true; $("result-content").hidden = false;
  const prediction = data.prediction;
  $("prediction-label").textContent = prediction?.label || "Prédiction absente";
  $("model-name").textContent = prediction ? `${prediction.model_name} · ${prediction.model_version}` : "—";
  $("confidence-value").textContent = prediction ? `${(prediction.confidence * 100).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %` : "—";
  $("confidence-fill").style.width = `${prediction ? prediction.confidence * 100 : 0}%`;
  badge($("validation-badge"), data.validation.status);
  $("validation-title").textContent = VALIDATION_LABELS[data.validation.status];
  $("validation-reasons").replaceChildren(...data.validation.reasons.map(reason => el("li", reason)));
  $("explanation").textContent = data.explanation;
  $("case-id").textContent = data.case_id;
  badge($("ledger-badge"), data.ledger_mode);
  badge($("integrity-badge"), "NON VÉRIFIÉ");
  $("mock-tamper-row").hidden = adapter.mode !== "mock";
  $("mock-notice").textContent = data.ledger_mode === "MOCK"
    ? "MOCK : preuve locale simulée, intégration Fabric non démontrée. Aucune preuve de transaction Fabric réelle."
    : "FABRIC : mode déclaré par le backend. Les identifiants ci-dessous proviennent du service connecté.";
  $("mock-notice").hidden = false;
  plot(previews.get(data.case_id));
  renderArtifacts(); renderCases();
  $("verify-button").disabled = busy || !data.artifacts.length;
  $("refresh-history").disabled = busy;
  $("tamper-button").disabled = busy;
}
async function loadHistory() {
  $("timeline").replaceChildren(el("li", "Chargement de l’historique…", "empty-text"));
  const id = active.case_id;
  try {
    const data = assertHistory(await adapter.history(id), id);
    $("timeline").replaceChildren();
    for (const event of data.events) {
      const item = el("li");
      item.append(el("strong", `${LABELS[event.stage] || event.stage} · ${event.status}`), el("small", formatTime(event.timestamp)), el("p", event.details));
      $("timeline").append(item);
    }
    if (!data.events.length) $("timeline").append(el("li", "Aucun événement retourné.", "empty-text"));
  } catch (error) {
    $("timeline").replaceChildren(el("li", `Historique indisponible : ${error.message}`, "empty-text"));
  }
}
async function openCase(id) {
  if (busy) return;
  setBusy(true);
  try { renderCase(assertAnalysis(await adapter.getCase(id), id)); await loadHistory(); }
  catch (error) { notify(error.message, true); }
  finally { setBusy(false); }
}
function clearResults() {
  active = null; cases.clear(); previews.clear();
  $("result-empty").hidden = false; $("result-content").hidden = true;
  badge($("validation-badge"), "EN ATTENTE"); badge($("integrity-badge"), "NON VÉRIFIÉ");
  $("artifact-count").textContent = "0";
  $("artifact-completeness").textContent = "AUCUN DOSSIER";
  const row = el("tr"), cell = el("td", "Les preuves apparaîtront après la première analyse.", "table-empty");
  cell.colSpan = 4; row.append(cell); $("artifact-rows").replaceChildren(row);
  $("case-list").replaceChildren(el("p", "Aucun dossier ouvert pour le moment.", "empty-text"));
  $("timeline").replaceChildren(el("li", "Sélectionnez un dossier pour consulter les étapes.", "empty-text"));
  $("case-count").textContent = "0";
  $("mock-tamper-row").hidden = true;
  plot(null); setBusy(false);
}
function connect() {
  if (busy) return;
  try {
    const mode = $("adapter-mode").value;
    const next = mode === "mock" ? new MockAdapter() : new ApiAdapter($("api-url").value.trim());
    adapter = next;
    clearResults();
    $("scenario-row").hidden = mode !== "mock";
    $("api-url").hidden = mode !== "api"; $("connect-button").hidden = mode !== "api";
    $("top-mode").textContent = mode === "mock" ? "Environnement de démonstration" : "API configurée · connexion non vérifiée";
    $("connection-description").textContent = mode === "mock" ? "Réponses simulées dans ce navigateur" : next.base;
    $("mock-notice").hidden = mode !== "mock";
    $("mock-notice").textContent = "MOCK : preuve locale simulée, intégration Fabric non démontrée. Aucune prédiction médicale n’est calculée.";
    notify(mode === "mock" ? "Mode MOCK activé. La session de démonstration est vide." : "Adresse API configurée. La connexion sera vérifiée lors d’une requête. Les fichiers seront envoyés uniquement au clic sur Analyser.");
  } catch (error) {
    $("adapter-mode").value = adapter.mode;
    $("api-url").hidden = adapter.mode !== "api";
    $("connect-button").hidden = adapter.mode !== "api";
    notify(error.message, true);
  }
}
$("adapter-mode").addEventListener("change", connect);
$("connect-button").addEventListener("click", connect);
$("api-url").addEventListener("keydown", event => { if (event.key === "Enter") { event.preventDefault(); connect(); } });
for (const [input, label, fallback] of [["ecg-file", "ecg-name", "Choisir un fichier ECG"], ["report-file", "report-name", "Choisir un rapport"]]) {
  $(input).addEventListener("change", () => { $(label).textContent = $(input).files[0]?.name || fallback; });
}

$("sample-button").addEventListener("click", async () => {
  if (busy) return;
  setBusy(true);
  try {
    const load = async (path, input, name, type) => {
      const response = await fetch(path);
      if (!response.ok) throw new Error("Fichiers de démonstration introuvables. Démarrez le serveur à la racine du projet.");
      const transfer = new DataTransfer();
      transfer.items.add(new File([await response.blob()], name, { type }));
      $(input).files = transfer.files; $(input).dispatchEvent(new Event("change"));
    };
    await Promise.all([load("../samples/ecg_valid.csv", "ecg-file", "ecg_valid.csv", "text/csv"), load("../samples/report_valid.txt", "report-file", "report_valid.txt", "text/plain")]);
    const preview = await inspectUploads($("ecg-file").files[0], $("report-file").files[0]);
    if (!active) plot(preview);
    notify("Fichiers synthétiques chargés. Choisissez un scénario puis lancez l’analyse.");
  } catch (error) { notify(error.message, true); }
  finally { setBusy(false); }
});

$("analysis-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (busy) return;
  if (adapter.mode === "api") {
    try {
      if (new ApiAdapter($("api-url").value.trim()).base !== adapter.base) {
        notify("L’adresse a été modifiée. Cliquez sur Connecter pour appliquer la nouvelle adresse avant l’analyse.", true);
        return;
      }
    } catch (error) { notify(error.message, true); return; }
  }
  // Capture FormData before disabling file controls (disabled fields are omitted).
  const form = new FormData($("analysis-form"));
  const ecg = $("ecg-file").files[0], report = $("report-file").files[0];
  const scenario = $("mock-scenario").value;
  setBusy(true); $("feedback").hidden = true;
  try {
    const preview = await inspectUploads(ecg, report);
    const data = assertAnalysis(await adapter.analyze(form, scenario));
    previews.set(data.case_id, preview);
    renderCase(data); await loadHistory();
    if (adapter.mode === "api") $("top-mode").textContent = "API connectée";
    notify(adapter.mode === "mock" ? "Dossier MOCK créé : prédiction, preuves et historique simulés. Aucun modèle ni registre réel exécuté." : "Analyse reçue du backend. Consultez les motifs de validation et les preuves.");
  } catch (error) {
    notify(`${error.message}${active ? " Le résultat affiché reste celui du dossier précédent." : ""}`, true);
  } finally { setBusy(false); }
});

$("verify-button").addEventListener("click", async () => {
  if (busy || !active) return;
  setBusy(true); badge($("integrity-badge"), "VÉRIFICATION…");
  // Clear old green checks while the next verification is pending.
  renderArtifacts();
  try {
    const verification = assertVerification(await adapter.verify(active.case_id), active);
    badge($("integrity-badge"), verification.overall_status);
    renderArtifacts(verification.checks);
    await loadHistory();
    notify(`${adapter.mode === "mock" ? "Vérification SIMULÉE" : "Vérification du backend"} : ${verification.overall_status}. ${verification.overall_status === "MODIFIED" ? "Une modification est signalée. La validation initiale reste affichée à titre historique." : "La validation initiale et le contrôle d’intégrité sont affichés séparément."}`, verification.overall_status !== "VALID");
  } catch (error) {
    badge($("integrity-badge"), "UNVERIFIABLE");
    renderArtifacts(active.artifacts.map(item => ({ artifact_id: item.artifact_id, status: "UNVERIFIABLE", expected_sha256: item.sha256, actual_sha256: null })));
    notify(error.message, true);
  } finally { setBusy(false); }
});
$("tamper-button").addEventListener("click", async () => {
  if (busy || !active || adapter.mode !== "mock") return;
  adapter.simulateTamper(active.case_id);
  badge($("integrity-badge"), "À REVÉRIFIER"); renderArtifacts();
  setBusy(true);
  try { await loadHistory(); notify("Modification simulée de processed. Cliquez sur Vérifier l’intégrité pour obtenir MODIFIED. Aucun fichier réel n’a changé."); }
  finally { setBusy(false); }
});
$("refresh-history").addEventListener("click", async () => {
  if (busy || !active) return;
  setBusy(true);
  try { await loadHistory(); } finally { setBusy(false); }
});
document.querySelectorAll(".nav-link").forEach(link => link.addEventListener("click", () => {
  document.querySelectorAll(".nav-link").forEach(item => item.classList.toggle("active", item === link));
}));
