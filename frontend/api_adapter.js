/** Real REST adapter only. Never manufactures a prediction or ledger receipt. */
export class ApiAdapter {
  constructor(baseUrl, { fetcher = globalThis.fetch, timeout = 30000 } = {}) {
    const url = new URL(baseUrl);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
      throw new Error("URL API invalide : utiliser HTTP(S), sans identifiants, paramètres ni fragment.");
    }
    this.base = url.href.replace(/\/$/, "");
    this.fetcher = fetcher;
    this.timeout = timeout;
    this.mode = "api";
  }

  async request(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);
    try {
      const response = await this.fetcher(this.base + path, {
        ...options, headers: { Accept: "application/json" }, signal: controller.signal,
      });
      let data;
      try { data = await response.json(); }
      catch { throw new Error(`Le backend a renvoyé une réponse non JSON (HTTP ${response.status}).`); }
      if (!response.ok) {
        data = data && typeof data === "object" ? data : {};
        const detail = Array.isArray(data.detail)
          ? data.detail.map(item => typeof item === "string" ? item : item.msg || "Entrée invalide").join(" · ")
          : typeof data.detail === "string" ? data.detail
          : Array.isArray(data.reasons) ? data.reasons.join(" · ") : "Échec de la requête";
        throw new Error(`HTTP ${response.status} : ${detail}`);
      }
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("Le service n’a pas répondu dans le délai de 30 secondes.");
      if (error instanceof TypeError) throw new Error("API inaccessible. Vérifiez son adresse, son démarrage et la configuration CORS.");
      throw error;
    } finally { clearTimeout(timer); }
  }

  analyze(formData) { return this.request("/api/analyze", { method: "POST", body: formData }); }
  getCase(id) { return this.request(`/api/cases/${encodeURIComponent(id)}`); }
  history(id) { return this.request(`/api/cases/${encodeURIComponent(id)}/history`); }
  verify(id) { return this.request(`/api/cases/${encodeURIComponent(id)}/verify`, { method: "POST" }); }
}
