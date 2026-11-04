import { test } from "node:test";
import assert from "node:assert/strict";
import { cases, evaluate } from "./csv_fixtures.mjs";

for (const item of cases) {
  test(`CSV content contract: ${item.id}`, async () => {
    const result = await evaluate(item);
    assert.equal(result.valid, item.valid, item.id);
    if (item.valid) assert.equal(result.points, item.points);
  });
}
