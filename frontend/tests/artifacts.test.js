import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { assertAnalysis } from "../contracts.js";

const fixture = JSON.parse(await readFile(new URL("../fixtures/demo_case.json", import.meta.url), "utf8"));
const copy = () => structuredClone(fixture);
for (const status of ["ACCEPTED", "REVIEW_REQUIRED"]) {
  for (const count of [0, 1, 7]) {
    test(`${status} requires eight artifacts, not ${count}`, () => {
      const data = copy(); data.validation.status = status; data.artifacts = data.artifacts.slice(0, count);
      assert.throws(() => assertAnalysis(data), /incomplète/);
    });
  }
}
test("all eight types with two raw roots and reordered response are supported", () => {
  const data = copy(); data.artifacts[1].parent_id = null; data.artifacts.reverse();
  assert.equal(assertAnalysis(data), data);
});
test("a second independent raw root does not excuse a missing derived parent", () => {
  const data = copy(); data.artifacts[1].parent_id = null; data.artifacts[2].parent_id = null;
  assert.throws(() => assertAnalysis(data), /sans parent/);
});
test("partial REJECTED cases remain explicit and no artifacts are invented", () => {
  const data = copy(); data.validation.status = "REJECTED"; data.prediction = null;
  data.artifacts = data.artifacts.slice(0, 2);
  assert.equal(assertAnalysis(data).artifacts.length, 2);
  data.artifacts = [];
  assert.equal(assertAnalysis(data).artifacts.length, 0);
});
const mutations = {
  "unknown type": a => { a[0].type = "invented"; },
  "duplicate type": a => { a[1].type = a[0].type; },
  "invalid id": a => { a[0].artifact_id = "uuid"; },
  "duplicate id": a => { a[1].artifact_id = a[0].artifact_id; },
  "case-insensitive duplicate id": a => { a[1].artifact_id = a[0].artifact_id.toUpperCase(); },
  "self parent": a => { a[0].parent_id = a[0].artifact_id; },
  "cycle": a => { a[0].parent_id = a[1].artifact_id; },
  "dangling parent": a => { a[2].parent_id = "00000000-0000-0000-0000-000000000001"; },
  "derived root": a => { a[2].parent_id = null; },
  "backwards stage": a => { a[3].parent_id = a[4].artifact_id; },
  "invalid hash": a => { a[0].sha256 = "x"; },
  "empty receipt": a => { a[0].tx_id = ""; },
};
for (const [name, mutate] of Object.entries(mutations)) {
  test(`malformed artifact rejected: ${name}`, () => {
    const data = copy(); mutate(data.artifacts);
    assert.throws(() => assertAnalysis(data), /Contrat API/);
    data.validation.status = "REJECTED";
    assert.throws(() => assertAnalysis(data), /Contrat API/);
  });
}
