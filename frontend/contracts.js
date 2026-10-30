/** Wire guards. Shared keys are unchanged; history's proposed envelope is in docs/contracts.md. */
export const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SHA = /^[0-9a-f]{64}$/;
export const VALIDATIONS = ["ACCEPTED", "REVIEW_REQUIRED", "REJECTED"];
export const CHECK_STATUSES = ["VALID", "MODIFIED", "MISSING", "UNVERIFIABLE"];
export const ARTIFACT_TYPES = Object.freeze(["raw_ecg", "raw_report", "processed", "features", "prediction", "validation", "explanation", "final"]);
const text = value => typeof value === "string" && Boolean(value.trim());
const uuid = value => typeof value === "string" && UUID.test(value);
const key = value => value.toLowerCase();
function requireValue(condition, message) { if (!condition) throw new Error(`Contrat API invalide : ${message}. Voir docs/contracts.md.`); }

export function assertArtifacts(artifacts, requireComplete = true) {
  requireValue(Array.isArray(artifacts), "artifacts doit être une liste");
  const ids = new Map(), types = new Set();
  for (const a of artifacts) {
    requireValue(a && uuid(a.artifact_id) && !ids.has(key(a.artifact_id)), "artifact_id invalide ou dupliqué");
    requireValue(ARTIFACT_TYPES.includes(a.type) && !types.has(a.type), "type d’artefact inconnu ou dupliqué");
    requireValue(typeof a.sha256 === "string" && SHA.test(a.sha256), "empreinte SHA-256 incorrecte");
    requireValue(a.parent_id === null || uuid(a.parent_id), "parent_id incorrect");
    requireValue(text(a.storage_ref) && text(a.tx_id), "storage_ref et tx_id requis");
    ids.set(key(a.artifact_id), a); types.add(a.type);
  }
  for (const a of artifacts) {
    if (a.parent_id === null) {
      requireValue(a.type === "raw_ecg" || a.type === "raw_report", "artefact dérivé sans parent");
      continue;
    }
    const parent = ids.get(key(a.parent_id));
    requireValue(parent && key(parent.artifact_id) !== key(a.artifact_id), "parent_id absent ou auto-référence");
    // Causal order makes cycles impossible, regardless of array order. Two raw
    // input roots are allowed; no new field or single mandatory chain is imposed.
    requireValue(ARTIFACT_TYPES.indexOf(parent.type) < ARTIFACT_TYPES.indexOf(a.type), "lignée cyclique ou ordre causal des artefacts incohérent");
  }
  if (requireComplete) {
    const missing = ARTIFACT_TYPES.filter(type => !types.has(type));
    requireValue(!missing.length, `analyse incomplète : huit artefacts requis ; manquants : ${missing.join(", ")}`);
  }
  return artifacts;
}

export function assertAnalysis(data, expectedId = null) {
  requireValue(data && uuid(data.case_id), "case_id UUID requis");
  requireValue(!expectedId || key(expectedId) === key(data.case_id), "case_id différent du dossier demandé");
  requireValue(data.validation && VALIDATIONS.includes(data.validation.status), "statut de validation inconnu");
  requireValue(Array.isArray(data.validation.reasons) && data.validation.reasons.every(reason => typeof reason === "string"), "reasons doit être une liste de textes");
  const p = data.prediction;
  requireValue((p === null && data.validation.status === "REJECTED") ||
    (p && text(p.label) && typeof p.confidence === "number" && Number.isFinite(p.confidence) &&
      p.confidence >= 0 && p.confidence <= 1 && text(p.model_name) && text(p.model_version)), "schéma prediction incorrect");
  requireValue(typeof data.explanation === "string", "explanation doit être du texte");
  requireValue(["MOCK", "FABRIC"].includes(data.ledger_mode), "ledger_mode doit être MOCK ou FABRIC");
  assertArtifacts(data.artifacts, data.validation.status !== "REJECTED");
  return data;
}

export function assertHistory(data, caseId) {
  requireValue(data && data.case_id === caseId && Array.isArray(data.events), "historique attendu sous {case_id, events}");
  for (const event of data.events) {
    requireValue(event && text(event.timestamp) && Number.isFinite(Date.parse(event.timestamp)) &&
      text(event.stage) && text(event.status) && typeof event.details === "string", "événement d’historique incorrect");
  }
  return data;
}

export function assertVerification(data, analysis) {
  requireValue(data && data.case_id === analysis.case_id && CHECK_STATUSES.includes(data.overall_status), "résultat de vérification incorrect");
  requireValue(Array.isArray(data.checks), "checks doit être une liste");
  const ids = new Set(analysis.artifacts.map(item => item.artifact_id));
  const seen = new Set();
  for (const check of data.checks) {
    requireValue(check && ids.has(check.artifact_id) && !seen.has(check.artifact_id) && CHECK_STATUSES.includes(check.status), "contrôle inconnu ou dupliqué");
    requireValue(check.expected_sha256 === null || SHA.test(check.expected_sha256), "expected_sha256 incorrect");
    requireValue(check.actual_sha256 === null || SHA.test(check.actual_sha256), "actual_sha256 incorrect");
    const artifact = analysis.artifacts.find(item => item.artifact_id === check.artifact_id);
    requireValue(check.expected_sha256 === null || check.expected_sha256 === artifact.sha256, "empreinte initiale différente du dossier");
    if (check.status === "VALID") requireValue(SHA.test(check.expected_sha256) && check.expected_sha256 === check.actual_sha256, "VALID avec empreintes différentes ou absentes");
    if (check.status === "MODIFIED") requireValue(SHA.test(check.expected_sha256) && SHA.test(check.actual_sha256) && check.expected_sha256 !== check.actual_sha256, "MODIFIED sans différence d’empreintes");
    if (check.status === "MISSING") requireValue(check.actual_sha256 === null, "MISSING avec des octets supposés présents");
    seen.add(check.artifact_id);
  }
  requireValue(seen.size === ids.size && ids.size > 0, "vérification incomplète des artefacts");
  const statuses = data.checks.map(item => item.status);
  const aggregate = statuses.includes("MODIFIED") ? "MODIFIED" : statuses.includes("MISSING") ? "MISSING" : statuses.includes("UNVERIFIABLE") ? "UNVERIFIABLE" : "VALID";
  requireValue(data.overall_status === aggregate, "overall_status incohérent avec checks");
  return data;
}
