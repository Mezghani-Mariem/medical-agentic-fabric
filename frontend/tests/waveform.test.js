import { test } from "node:test";
import assert from "node:assert/strict";
import { waveformPoints } from "../waveform.js";

for (const values of [[-1e308, 1e308], [-Number.MAX_VALUE, Number.MAX_VALUE], [0, Number.MIN_VALUE],
  [-Number.MIN_VALUE, Number.MIN_VALUE], [1e308, 1e308], [0, 0], [1], [-42, 0, 42], Array(800).fill(0)]) {
  test(`stable waveform: ${values.length} points, first ${values[0]}`, () => {
    const result = waveformPoints(values);
    assert.equal(typeof result, "string");
    const coordinates = result.split(" ").map(point => point.split(",").map(Number));
    assert.equal(coordinates.length, values.length);
    assert(coordinates.every(([x, y]) => Number.isFinite(x) && Number.isFinite(y) && x >= 0 && x <= 800 && y >= 25 && y <= 145));
  });
}
for (const values of [null, undefined, [], [NaN], [Infinity], [-Infinity], ["1"], {}, "1", [null], Array(2), Array(801).fill(1)]) {
  test(`malformed waveform is unavailable: ${String(values).slice(0, 20)}`, () => {
    assert.equal(waveformPoints(values), null);
  });
}
test("ordinary waveform keeps endpoint scale and does not mutate samples", () => {
  const values = Object.freeze([-1, 0, 1]);
  assert.equal(waveformPoints(values), "0,145 400,85 800,25");
  assert.equal(waveformPoints([8, 8]), "0,85 800,85");
});
