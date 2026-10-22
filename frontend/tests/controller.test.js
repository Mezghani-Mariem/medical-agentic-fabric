import { test } from "node:test";
import assert from "node:assert/strict";
import { dashboard } from "./dom_harness.mjs";
import { BASELINE_POINTS } from "../waveform.js";

test("controller loads samples, all scenarios, history and tamper flow (DOM doubles)", async () => {
  const ui = await dashboard();
  await ui.click("sample-button"); await ui.submit();
  assert.equal(ui.node("signal-count").textContent, "720 points");
  assert.equal(ui.node("prediction-label").textContent, "demo_class_A");
  assert.equal(ui.node("confidence-fill").style.width, "91%");
  assert.equal(ui.node("validation-badge").textContent, "ACCEPTED");
  assert.equal(ui.node("artifact-rows").children.length, 8);
  assert.match(ui.node("artifact-completeness").textContent, /8\/8/);
  assert.equal(ui.node("timeline").children.length, 8);
  await ui.click("verify-button");
  assert.equal(ui.node("integrity-badge").textContent, "VALID");
  await ui.click("tamper-button"); await ui.click("verify-button");
  assert.equal(ui.node("integrity-badge").textContent, "MODIFIED");
  assert.equal(ui.node("validation-badge").textContent, "ACCEPTED");
  for (const [scenario, status, integrity] of [["low-confidence", "REVIEW_REQUIRED", "VALID"],
    ["poor-quality", "REVIEW_REQUIRED", "VALID"], ["missing-artifact", "REJECTED", "MISSING"],
    ["integrity-failure", "REJECTED", "MODIFIED"]]) {
    ui.node("mock-scenario").value = scenario; await ui.submit();
    assert.equal(ui.node("validation-badge").textContent, status);
    await ui.click("verify-button");
    assert.equal(ui.node("integrity-badge").textContent, integrity);
  }
  assert.equal(ui.node("case-list").children.length, 5);
  await ui.node("case-list").children.at(-1).listeners.get("click")();
  assert.equal(ui.node("validation-badge").textContent, "ACCEPTED");
});

test("controller plot handles extreme and malformed previews without throwing", async () => {
  const ui = await dashboard();
  ui.plot({ count: 2, values: [-1e308, 1e308] });
  assert.equal(ui.node("signal-line").attributes.points, "0,145 800,25");
  for (const preview of [null, {}, { count: 2, values: [NaN, 1] }, { count: 1, values: [1, 2] },
    { count: "2", values: [1, 2] }, { count: 1, values: "1" }]) {
    assert.doesNotThrow(() => ui.plot(preview));
    assert.equal(ui.node("signal-line").attributes.points, BASELINE_POINTS);
    assert.equal(ui.node("signal-count").textContent, "Aucun aperçu");
  }
});

test("controller rejects incomplete ACCEPTED response before replacing displayed case", async () => {
  const ui = await dashboard();
  await ui.click("sample-button"); await ui.submit();
  const before = ui.state();
  const incomplete = structuredClone(before); incomplete.artifacts = [];
  ui.setAdapter({ mode: "mock", analyze: async () => incomplete });
  await ui.submit();
  assert.equal(ui.state(), before);
  assert.match(ui.node("feedback").textContent, /incomplète/);
  assert.equal(ui.node("artifact-rows").children.length, 8);
  assert.equal(ui.node("analyze-button").disabled, false);
});

test("partial REJECTED metadata is displayed as incomplete and never manufactured", async () => {
  const ui = await dashboard();
  await ui.click("sample-button"); await ui.submit();
  const data = structuredClone(ui.state()); data.validation.status = "REJECTED";
  data.artifacts = data.artifacts.slice(0, 2);
  ui.setAdapter({ mode: "mock", analyze: async () => data, history: async () => ({ case_id: data.case_id, events: [] }) });
  await ui.submit();
  assert.equal(ui.node("validation-badge").textContent, "REJECTED");
  assert.match(ui.node("artifact-completeness").textContent, /INCOMPLET.*2\/8/);
  assert.equal(ui.node("artifact-rows").children.length, 2);
  data.artifacts = []; await ui.submit();
  assert.match(ui.node("artifact-completeness").textContent, /INCOMPLET.*0\/8/);
  assert.equal(ui.node("verify-button").disabled, true);
});

test("controller errors clear green integrity and restore request controls", async () => {
  const ui = await dashboard();
  await ui.click("sample-button"); await ui.submit(); await ui.click("verify-button");
  const data = ui.state();
  ui.setAdapter({ mode: "api", verify: async () => ({ case_id: data.case_id, overall_status: "VALID", checks: [] }) });
  await ui.click("verify-button");
  assert.equal(ui.node("integrity-badge").textContent, "UNVERIFIABLE");
  ui.setAdapter({ mode: "api", verify: async () => { throw new Error("Service offline"); } });
  await ui.click("verify-button");
  assert.equal(ui.node("integrity-badge").textContent, "UNVERIFIABLE");
  assert.equal(ui.node("verify-button").disabled, false);
});

test("duplicate submissions are blocked and invalid files preserve the previous case", async () => {
  const ui = await dashboard(); await ui.click("sample-button");
  await Promise.all([ui.submit(), ui.submit()]);
  assert.equal(ui.node("case-list").children.length, 1);
  const before = ui.state();
  ui.node("ecg-file").files = [new File(["\nsignal\n1\n"], "invalid.csv")];
  await ui.submit();
  assert.equal(ui.state(), before);
  assert.match(ui.node("feedback").textContent, /signal/);
  assert.equal(ui.node("analyze-button").disabled, false);
});
