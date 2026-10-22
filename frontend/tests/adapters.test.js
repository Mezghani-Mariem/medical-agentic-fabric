// Optional dependency-free browser contract tests. Python tests require no Node.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { webcrypto } from "node:crypto";
import { ApiAdapter } from "../api_adapter.js";
import { MockAdapter } from "../mock_api.js";
import { assertAnalysis, assertHistory, assertVerification } from "../contracts.js";
import { inspectUploads, signalPreview } from "../input_preview.js";

const fixture = JSON.parse(await readFile(new URL("../fixtures/demo_case.json", import.meta.url), "utf8"));
const mock = () => new MockAdapter({ fetcher: async () => ({ ok: true, json: async () => structuredClone(fixture) }), uuid: () => webcrypto.randomUUID() });

test("all mock scenarios respect the wire contracts and real adapter method names", async () => {
  for (const [scenario, status, integrity] of [["accepted", "ACCEPTED", "VALID"], ["low-confidence", "REVIEW_REQUIRED", "VALID"], ["poor-quality", "REVIEW_REQUIRED", "VALID"], ["missing-artifact", "REJECTED", "MISSING"], ["integrity-failure", "REJECTED", "MODIFIED"]]) {
    const adapter = mock();
    const data = assertAnalysis(await adapter.analyze(null, scenario));
    assert.equal(data.validation.status, status);
    assert.equal(data.artifacts.length, 8);
    assert.equal(data.ledger_mode, "MOCK");
    assert(data.artifacts.every(item => item.tx_id.startsWith("MOCK-")));
    assertHistory(await adapter.history(data.case_id), data.case_id);
    assert.deepEqual(await adapter.getCase(data.case_id), data);
    assert.equal(assertVerification(await adapter.verify(data.case_id), data).overall_status, integrity);
  }
});
test("mock tamper is explicit; snapshots cannot mutate adapter state", async () => {
  const adapter = mock();
  const data = await adapter.analyze(null);
  data.prediction.label = "changed client copy";
  assert.notEqual((await adapter.getCase(data.case_id)).prediction.label, data.prediction.label);
  const original = await adapter.getCase(data.case_id);
  adapter.simulateTamper(data.case_id);
  assert.equal(assertVerification(await adapter.verify(data.case_id), original).overall_status, "MODIFIED");
  assert.equal((await adapter.getCase(data.case_id)).validation.status, "ACCEPTED");
  assert((await adapter.history(data.case_id)).events.some(item => item.stage === "demo_tamper"));
  await assert.rejects(adapter.getCase("unknown"), /inconnu/);
});
test("API adapter uses exact endpoints, methods and multipart fields", async () => {
  const calls = [];
  const adapter = new ApiAdapter("http://localhost:8000/", { fetcher: async (url, options) => {
    calls.push({ url, options }); return { ok: true, json: async () => ({ ok: true }) };
  } });
  const form = new FormData();
  form.append("ecg", new Blob(["signal\n1\n"]), "ecg.csv");
  form.append("report", new Blob(["synthetic"]), "report.txt");
  await adapter.analyze(form); await adapter.getCase("id"); await adapter.history("id"); await adapter.verify("id");
  assert.deepEqual(calls.map(item => [item.url, item.options.method || "GET"]), [
    ["http://localhost:8000/api/analyze", "POST"], ["http://localhost:8000/api/cases/id", "GET"],
    ["http://localhost:8000/api/cases/id/history", "GET"], ["http://localhost:8000/api/cases/id/verify", "POST"],
  ]);
  assert.equal(calls[0].options.body, form);
  assert.deepEqual([...form.keys()], ["ecg", "report"]);
  assert.equal(calls[0].options.headers["Content-Type"], undefined);
});
test("API errors never silently fall back to mocks", async () => {
  const api = payload => new ApiAdapter("http://localhost:8000", { fetcher: payload });
  await assert.rejects(api(async () => { throw new TypeError("offline"); }).verify("id"), /API inaccessible/);
  await assert.rejects(api(async () => ({ ok: false, status: 422, json: async () => ({ detail: [{ msg: "invalid" }] }) })).analyze(null), /HTTP 422.*invalid/);
  await assert.rejects(api(async () => ({ ok: false, status: 500, json: async () => { throw new Error("HTML"); } })).history("id"), /non JSON/);
  const timeoutApi = new ApiAdapter("http://localhost:8000", { timeout: 5, fetcher: async (_url, options) => new Promise((_resolve, reject) => options.signal.addEventListener("abort", () => reject(Object.assign(new Error("aborted"), { name: "AbortError" })))) });
  await assert.rejects(timeoutApi.getCase("id"), /délai/);
  for (const url of ["file:///tmp", "javascript:alert(1)", "http://user:pass@localhost", "http://localhost?secret=1"]) assert.throws(() => new ApiAdapter(url));
});
test("incomplete, contradictory or mismatched verification cannot show VALID", () => {
  assert.throws(() => assertVerification({ case_id: fixture.case_id, overall_status: "VALID", checks: [] }, fixture), /incomplète/);
  const checks = fixture.artifacts.map(item => ({ artifact_id: item.artifact_id, status: "VALID", expected_sha256: item.sha256, actual_sha256: item.sha256 }));
  checks[0].actual_sha256 = "0".repeat(64);
  assert.throws(() => assertVerification({ case_id: fixture.case_id, overall_status: "VALID", checks }, fixture), /empreintes/);
  assert.throws(() => assertAnalysis(fixture, webcrypto.randomUUID()), /différent/);
  assert.throws(() => assertAnalysis({ ...fixture, ledger_mode: "fabric" }), /ledger_mode/);
  assert.throws(() => assertHistory([], fixture.case_id), /historique/);
});
test("raw signal preview accepts standard CSV; no medical prediction is derived", async () => {
  assert.deepEqual(signalPreview('sample,signal,note\r\n0,".1","ligne\r\nlongue"\r\n1,-2e-1,ok\r\n'), { count: 2, values: [0.1, -0.2] });
  const valid = await readFile(new URL("../../samples/ecg_valid.csv", import.meta.url), "utf8");
  assert.equal(signalPreview(valid).count, 720);
  for (const csv of ["signal\nNaN\n", "value\n1\n", "signal\n", "signal\n1_0\n", 'signal\n"1\n', "signal,x\n1\n"]) assert.throws(() => signalPreview(csv));
});
test("browser upload checks reject invalid, binary, empty and oversized files", async () => {
  const file = (name, data) => ({ name, size: new TextEncoder().encode(data).length, arrayBuffer: async () => new TextEncoder().encode(data).buffer });
  const ecg = file("ecg.csv", "signal\n1\n"), report = file("report.txt", "Synthétique");
  assert.equal((await inspectUploads(ecg, report)).count, 1);
  await assert.rejects(inspectUploads(null, report), /Choisissez/);
  await assert.rejects(inspectUploads(file("bad.exe", "x"), report), /extension/);
  await assert.rejects(inspectUploads(ecg, file("report.txt", "")), /vides/);
  await assert.rejects(inspectUploads(ecg, file("report.txt", "bad\x00")), /binaire/);
  await assert.rejects(inspectUploads({ ...ecg, size: 2 * 1024 * 1024 + 1 }, report), /2 Mio/);
  await assert.rejects(inspectUploads(ecg, { ...report, size: 64 * 1024 + 1 }), /64 Kio/);
  await assert.rejects(inspectUploads({ ...ecg, arrayBuffer: async () => new Uint8Array([255]).buffer }, report), /UTF-8/);
});
