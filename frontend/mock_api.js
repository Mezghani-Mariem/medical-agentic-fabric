/** Browser-only response fixture adapter. No model, hashing service or ledger. */
const ARTIFACT_LABELS = {
  raw_ecg: "ECG reçu", raw_report: "Rapport reçu", processed: "Prétraitement simulé",
  features: "Caractéristiques simulées", prediction: "Prédiction simulée", validation: "Validation simulée",
  explanation: "Explication simulée", final: "Dossier final simulé",
};
const clone = value => structuredClone(value);

export class MockAdapter {
  constructor({ fetcher = globalThis.fetch, uuid = () => crypto.randomUUID() } = {}) {
    this.mode = "mock";
    this.fetcher = fetcher;
    this.uuid = uuid;
    this.cases = new Map();
    this.template = null;
  }

  async analyze(_formData, scenario = "accepted") {
    // The selected files NEVER enter a model: this is an explicitly canned API response.
    if (!this.template) {
      const response = await this.fetcher(new URL("./fixtures/demo_case.json", import.meta.url));
      if (!response.ok) throw new Error("La fixture MOCK ne peut pas être chargée. Servez la racine du projet par HTTP.");
      this.template = await response.json();
    }
    const data = clone(this.template);
    data.case_id = this.uuid();
    const timestamp = new Date().toISOString();
    let parent = null;
    for (const artifact of data.artifacts) {
      artifact.artifact_id = this.uuid();
      artifact.parent_id = parent;
      artifact.storage_ref = `data/cases/${data.case_id}/${artifact.artifact_id}.bin`;
      artifact.tx_id = `MOCK-${artifact.artifact_id}`;
      parent = artifact.artifact_id;
    }
    if (scenario === "low-confidence") {
      data.prediction.confidence = 0.62;
      data.validation = { status: "REVIEW_REQUIRED", reasons: ["Confiance inférieure au seuil de 75 % : revue humaine requise."] };
    } else if (scenario === "poor-quality") {
      data.validation = { status: "REVIEW_REQUIRED", reasons: ["Qualité du signal insuffisante : revue humaine requise (scénario simulé)."] };
    } else if (scenario === "missing-artifact") {
      data.validation = { status: "REJECTED", reasons: ["Artefact manquant (scénario simulé)."] };
    } else if (scenario === "integrity-failure") {
      data.validation = { status: "REJECTED", reasons: ["Intégrité compromise (scénario simulé)."] };
    } else if (scenario !== "accepted") { throw new Error("Scénario MOCK inconnu."); }
    if (!data.validation.reasons.includes("Cohérence texte/ECG non évaluée automatiquement")) {
      data.validation.reasons.push("Cohérence texte/ECG non évaluée automatiquement");
    }
    const events = data.artifacts.map(artifact => ({
      timestamp, stage: artifact.type, status: "MOCK", details: ARTIFACT_LABELS[artifact.type],
      artifact_id: artifact.artifact_id, tx_id: artifact.tx_id,
    }));
    this.cases.set(data.case_id, { data, events, scenario, tampered: scenario === "integrity-failure" });
    return clone(data);
  }

  get(id) {
    const entry = this.cases.get(id);
    if (!entry) throw new Error("Dossier MOCK inconnu dans cette session.");
    return entry;
  }
  async getCase(id) { return clone(this.get(id).data); }
  async history(id) { return { case_id: id, events: clone(this.get(id).events) }; }
  async verify(id) {
    const entry = this.get(id);
    const checks = entry.data.artifacts.map((artifact, index) => {
      const status = index === 2 && entry.scenario === "missing-artifact" ? "MISSING" : index === 2 && entry.tampered ? "MODIFIED" : "VALID";
      return { artifact_id: artifact.artifact_id, status, expected_sha256: artifact.sha256,
        actual_sha256: status === "MISSING" ? null : status === "MODIFIED" ? "0".repeat(64) : artifact.sha256 };
    });
    const overall_status = checks.some(item => item.status === "MISSING") ? "MISSING" : entry.tampered ? "MODIFIED" : "VALID";
    entry.events.push({ timestamp: new Date().toISOString(), stage: "verify", status: overall_status,
      details: "Réponse de vérification simulée ; aucun fichier ni registre consulté." });
    return { case_id: id, overall_status, checks };
  }
  simulateTamper(id) {
    const entry = this.get(id);
    entry.tampered = true;
    entry.scenario = "integrity-failure";
    entry.events.push({ timestamp: new Date().toISOString(), stage: "demo_tamper", status: "MOCK",
      details: "Modification simulée de l’artefact processed. Aucune modification de fichier réel." });
  }
}
