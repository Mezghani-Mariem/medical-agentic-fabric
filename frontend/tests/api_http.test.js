/** Real HTTP transport to a fixture stub. No real model, backend or ledger. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { ApiAdapter } from "../api_adapter.js";
import { assertAnalysis, assertHistory, assertVerification } from "../contracts.js";

test("REAL adapter preserves contracts over native HTTP multipart transport", async () => {
  const load = async name => JSON.parse(await readFile(new URL(`../fixtures/${name}`, import.meta.url), "utf8"));
  const data = await load("demo_case.json"), history = await load("demo_history.json"), verify = await load("demo_verify.json");
  const calls = [];
  const server = createServer(async (request, response) => {
    const chunks = []; for await (const chunk of request) chunks.push(chunk);
    calls.push({ method: request.method, path: request.url, type: request.headers["content-type"], body: Buffer.concat(chunks).toString("utf8") });
    response.setHeader("Content-Type", "application/json");
    if (request.url === "/api/analyze" || request.url === `/api/cases/${data.case_id}`) response.end(JSON.stringify(data));
    else if (request.url === `/api/cases/${data.case_id}/history`) response.end(JSON.stringify(history));
    else if (request.url === `/api/cases/${data.case_id}/verify`) response.end(JSON.stringify(verify));
    else { response.statusCode = 404; response.end(JSON.stringify({ detail: "Unknown stub case" })); }
  });
  await new Promise((resolve, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolve); });
  try {
    const api = new ApiAdapter(`http://127.0.0.1:${server.address().port}`);
    const form = new FormData();
    form.append("ecg", new Blob(["signal\n1\n"]), "ecg.csv");
    form.append("report", new Blob(["Synthetic"]), "report.txt");
    assertAnalysis(await api.analyze(form));
    assertAnalysis(await api.getCase(data.case_id), data.case_id);
    assertHistory(await api.history(data.case_id), data.case_id);
    assertVerification(await api.verify(data.case_id), data);
    assert.deepEqual(calls.map(call => [call.method, call.path]), [["POST", "/api/analyze"], ["GET", `/api/cases/${data.case_id}`],
      ["GET", `/api/cases/${data.case_id}/history`], ["POST", `/api/cases/${data.case_id}/verify`]]);
    assert.match(calls[0].type, /^multipart\/form-data; boundary=/);
    assert.match(calls[0].body, /name="ecg"; filename="ecg.csv"/);
    assert.match(calls[0].body, /name="report"; filename="report.txt"/);
    assert.equal(calls[3].body, "");
    await assert.rejects(api.getCase("missing"), /HTTP 404/);
    data.artifacts = [];
    assert.throws(() => assertAnalysis(data), /incomplète/);
  } finally { await new Promise(resolve => server.close(resolve)); }
});
