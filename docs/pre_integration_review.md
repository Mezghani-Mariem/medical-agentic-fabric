# Pre-integration review of Mariem Mezghani’s delivery

**Historical review, superseded by the corrective verification pass.** The ECG overflow, CSV discrepancies and missing completeness guard described below have now been fixed in Mezghani’s modules, with maintained regression tests. See `docs/verification.md` for final executed results and `docs/contracts.md` for the explicit lineage policy. Browser screenshots and real colleague-module integration remain pending. The original findings below are retained as the record of what triggered the fixes.

Reviewed on **22 October 2026** against `01_Mariem_Mezghani.docx` and `04_Guide_Integration.docx` in the supplied Downloads paths. This review checks Mariem Mezghani’s scope. Application source, existing tests, and colleague-owned files were not modified. A review report and local audit probes under ignored `.qa/` were added.

The assigned code deliverables are present and the normal synthetic-data paths pass the available automated checks. This is suitable for handing the two Python modules and frontend to the team for integration testing. It is **not a complete visual or integrated-system sign-off**: the required real screenshots are missing, no browser is connected, and neither the colleagues’ backend nor their registry is installed here. The robustness findings below remain unfixed because this task requested a review.

## Findings and integration decisions

| Priority / category | Finding and reproduction | Consequence / next action |
| --- | --- | --- |
| P2, confirmed robustness defect | `frontend/app.js:49-51` subtracts the signal minimum from the maximum directly. `signal\n-1e308\n1e308\n` is accepted by Python and JS because both values are finite, but plotting generates `0,145 800,NaN`. | The SVG points are invalid for this input. Normalize with a numerically stable scale and check all output coordinates. This does not affect the supplied ordinary synthetic ECG. |
| P2, confirmed validation mismatch | JS `readCsv` skips leading blank lines; Python treats a leading blank line as an empty header. For `\nsignal\n0.1\n`, JS accepts one point and Python rejects. JS also accepts a 140,000-character extra CSV field, whereas Python’s current field limit rejects it. | A file can succeed in browser MOCK mode and receive HTTP 422 after switching to the backend. Align the checks or make the backend’s additional restrictions explicit in the upload guidance. Python remains authoritative. |
| P2, integration completeness gap | `frontend/contracts.js:20-30` checks each artifact’s shape but not the required eight types/count. An otherwise valid `ACCEPTED` response with `artifacts: []` passes `assertAnalysis`. Parent references are checked for existence, not for an acyclic lineage. | Mrabet must enforce the full eight-artifact pipeline and meaningful `artifacts_ok` values. Add an integration assertion for the eight types and coherent parents. A frontend completeness warning/guard is also advisable; this is beyond merely checking the frozen JSON shape. |
| Required agreement | The guide specifies `/history` but no response schema. The implementation requires `{case_id, events:[{timestamp,stage,status,details,...}]}`. | Mrabet must agree to this documented envelope or arrange a deliberate change in `assertHistory` / `loadHistory`. It cannot be claimed as an already frozen team contract. |
| Required agreement | The guide lists per-check verification statuses, but does not specify null hashes, completeness handling, or aggregate priority. The frontend requires one check per artifact and priority `MODIFIED > MISSING > UNVERIFIABLE > VALID`; missing file hashes are `null`. | Freeze these conventions with Mrabet and Abidi before integration. A different aggregation policy will deliberately display `UNVERIFIABLE` as a contract error. |
| Missing assigned evidence | The individual guide requests real captures of upload, result, history and detected modification. There are no such captures. | Execute the manual browser plan and save authentic captures. Keep the MOCK label visible on simulated demonstrations. |
| Optional demo coverage | There is no selectable `UNVERIFIABLE` MOCK scenario. | UI handling was checked using API-shaped stub responses and a failing request, but a fifth integrity scenario could make the demonstration easier. It is not evidence that the real registry failure path works. |

No critical issue was identified in the two Python modules for the specified synthetic-data rules. This statement is limited to the inspected code and executed tests; it does not certify clinical validity or production security.

## Requirement traceability

“Checked with DOM doubles” below means the unmodified controller was run with small in-memory substitutes for DOM nodes. It verifies data binding and event-handler logic, not actual browser rendering, CSS, browser upload semantics, accessibility, or CORS.

| Assigned requirement | Implementation / evidence | Review result |
| --- | --- | --- |
| Exact owned file locations | `frontend/index.html`, `style.css`, `app.js`; `app/input_checks.py`, `app/validation.py`; required test files and samples | Present |
| Plain HTML/CSS/JS, modest dependencies | No frontend framework, no npm dependencies; stdlib Python modules; pytest only for development | Implemented |
| `check_inputs(ecg_bytes, report_bytes)` | Exact required signature and `{valid,reasons,report_clean}` keys | Verified by pytest |
| ECG numeric `signal` CSV, UTF-8, empty/malformed input | Strict decoding, finite numeric values, column and row checks | Verified by pytest; JS mismatch documented above |
| File size limits | Inclusive 2,097,152 bytes ECG and 65,536 bytes report | Verified by pytest; confirm the byte counts with the team if “Mo/Ko” was intended as decimal units |
| Simple report pseudonymization | Structured Nom, Prénom/Prenom and Patient ID variants masked; repeated fields and LF/CRLF/CR tested | Verified by pytest; no free-text anonymization claimed |
| Exact `validate` signature and response | Parameters/defaults match guide; returns exactly `{status,reasons}` | Verified by source and pytest |
| Rejection precedence | Missing prediction, unavailable artifacts or failed integrity => `REJECTED` | Verified by pytest |
| Review threshold and quality | Bad/unknown quality or confidence below 0.75 => `REVIEW_REQUIRED`; exactly 0.75 accepted | Verified by pytest |
| Report used as context only | Nonempty context adds the specified unevaluated-coherence reason | Verified by pytest |
| Upload form and request state | `.csv` / `.txt`, readable error text, multipart fields `ecg` and `report`, controls disabled during work | Present; controller and transport checked programmatically; real browser pending |
| ECG display | Raw local values, total count, first 800 values at most, auto visual scale, no clinical units/time invented | Supplied sample checked with DOM doubles; overflow defect remains; visual review pending |
| Prediction, confidence, validation, explanation | Label/model/version, percentage and bar, all three constant statuses, reasons | Checked with DOM doubles; visual review pending |
| Case and ledger information | UUID, backend-provided `ledger_mode`, full artifact IDs/hashes/parents/storage refs/transaction IDs | Checked with fixtures/controller; no real ledger receipts tested |
| Eight-artifact demonstration | MOCK produces the eight expected types with linked parents | Verified programmatically; backend completeness not yet enforced/tested |
| Integrity verification | Required POST route; global and per-artifact statuses; expected/actual hashes for failures | VALID, MODIFIED, MISSING adapter scenarios tested; UNVERIFIABLE and failed/incomplete responses checked with DOM doubles |
| Processing history | GET history, per-case timeline, previous session-case selection and refresh | Checked with DOM doubles; format needs team agreement |
| Clear MOCK / real separation | Separate adapter modules; default MOCK; real requests do not fall back to fixtures | Verified by source, unit tests and HTTP stub |
| Synthetic examples and manual plan | Valid/invalid ECGs/reports, short ECG, `tests/test_ui_manual.md` | Present |
| Unit tests for invalid inputs / prediction failures | 89 Python cases and seven JS test groups | All pass in this review |
| README and handoff contracts | README, `docs/contracts.md`, `docs/api_example.json` | Present; API example matches fixture and Python decision |
| Real demonstration captures | Upload, result, history, detected change | Missing; browser unavailable |
| Scope isolation | No `main.py`, `orchestrator.py`, `preprocess.py`, `predict.py`, `hashing.py`, `registry.py`, models or blockchain implementation added | Respected |

## Checks actually executed

| Check | Result | What it does not prove |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q` | **89 passed** | Does not execute frontend in a browser or colleagues’ pipeline |
| `node --test frontend\tests\adapters.test.js` | **7 passed** | Uses controlled fetch responses, not a production backend |
| Temporary local static HTTP server | **12 resources returned HTTP 200**; page decoded as UTF-8; JS MIME types correct | Does not prove JS ran or layout is correct in a browser |
| Real `ApiAdapter` with native fetch against a temporary loopback HTTP stub | Four exact routes and methods, real multipart boundary, both named file parts, JSON guards, empty verify body and HTTP 404 passed | Stub returns fixtures; no FastAPI implementation, CORS browser policy, model, storage or Fabric tested |
| Unmodified `app.js` with DOM doubles | Sample load, normal ECG coordinates/count, prediction/confidence/status, eight table rows, timeline, prior-case selection, invalid CSV feedback, controls restored | Does not prove FileList/DataTransfer behavior or visual layout in an actual browser |
| Controller integrity response/error paths with DOM doubles | VALID to simulated MODIFIED; original validation retained; UNVERIFIABLE displayed; incomplete VALID and failed request cannot leave a green result | Does not read or hash a real remote file |
| Targeted edge probes | Plot overflow, CSV mismatch and empty-artifact acceptance reproduced | Findings remain unfixed |
| Browser inventory | `apps: []`, `browsers: []` | No visual interactions or screenshots could be executed |

The audit probes are local, ignored files: `.qa/review_probes.mjs`, `.qa/review_input_probes.py`, `.qa/review_static_http.py`. They can be rerun locally. They are not additional production modules or part of the regular test count. The nine passing probe groups are separate from the 89 pytest cases and seven JS test groups. Temporary servers were stopped after the checks.

## JSON and interface comparison

| Interface | Compared with guide | Result / constraint |
| --- | --- | --- |
| `check_inputs` | Two byte arguments; bool/list/string output | Matches |
| `validate` | Prediction, quality, default flags and context string; status/reasons output | Matches; additional malformed-input behavior is documented |
| Analyze upload | `POST /api/analyze`, multipart `ecg` + `report` | Matches; multipart Content-Type is generated by the browser/native fetch |
| Case retrieval | `GET /api/cases/{case_id}` | Matches; returns analysis envelope |
| History | `GET /api/cases/{case_id}/history` | Route matches; envelope is a proposal |
| Verify | `POST /api/cases/{case_id}/verify`, no required body | Matches |
| Analysis fields | `case_id`, `prediction`, `validation`, `explanation`, `artifacts`, `ledger_mode` | Matches |
| Prediction fields | `label`, `confidence`, `model_name`, `model_version` | Matches; confidence is a number in `[0,1]`, not percent |
| Validation constants | ACCEPTED / REVIEW_REQUIRED / REJECTED | Matches exactly |
| Artifact response fields | `artifact_id`, `type`, `sha256`, `parent_id`, `storage_ref`, `tx_id` | Matches; IDs must be actual UUIDs, not the illustrative word “uuid” |
| Ledger values | FABRIC / MOCK | Matches exactly; an API connection may legitimately return MOCK |
| Verify response/check fields | `case_id`, `overall_status`, `checks`; artifact ID, status, expected/actual hashes | Matches named fields; null values and aggregation are proposed additions |
| Missing prediction | Python rejects it; frontend supports `prediction:null` only for REJECTED | Explicit extension: agree with Mrabet; do not omit the key silently |
| Canonical hashing | Sorted UTF-8 JSON, compact separators, `ensure_ascii=False`; raw file hashes use original bytes | Documented correctly; production hashing is Abidi’s scope and was not tested here |

The frontend ignores extra response fields. It never translates the shared status constants and does not require the backend’s MOCK transaction IDs to use our demo prefix. The MOCK adapter itself always uses `MOCK-` receipts.

## Hardcoded values and limitations

| Value / behavior | Location | Assessment |
| --- | --- | --- |
| `demo_class_A`, confidence 0.91, low-confidence score 0.62, mock model/version | `frontend/fixtures/demo_case.json`, `frontend/mock_api.js` | Intentional fixture values, not inference from selected files |
| Dummy hashes and fixed template event date | `samples/generate_samples.py`, generated JSON fixtures | Intentional mock metadata. Hashes identify dummy strings, not uploaded files. Runtime MOCK events use the current timestamp. |
| Synthetic waveform, 720 samples | Sample generator / `ecg_valid.csv` | Intentional synthetic illustration |
| First 800 plotted values, SVG dimensions | `frontend/input_preview.js`, `frontend/app.js`, HTML | Explicit preview limit; not a full clinical waveform viewer |
| Threshold 0.75 / 75% marker | Python validator and dashboard | Required by V1; synchronize both if the team changes the rule |
| 2 MiB / 64 KiB | Python and browser checks | Intended upload limits; exact bytes documented |
| `http://127.0.0.1:8000` | HTML URL input | Editable service origin, not a working backend supplied in this delivery |
| 30-second deadline | `frontend/api_adapter.js` | Default configurable in adapter constructor; timeout message is hardcoded to 30 seconds even if a caller overrides the timeout |
| Session-only cases and previews | Controller / MOCK adapter maps | Intentional. Reload or reconnect clears the list; there is no backend case-list endpoint or UI to reopen an arbitrary UUID. GET case is used to revisit cases already in the session. |
| No direct Python calls from the static page | Architecture | Intentional scope separation: backend integration must execute `check_inputs` and `validate`. Browser MOCK only tests the display flow. |

## What Mariem Mrabet needs to connect

- [ ] Merge `app/input_checks.py` and `app/validation.py` into the shared package, preserving existing colleague files and package initialization.
- [ ] Call `check_inputs(ecg_bytes, report_bytes)` before preprocessing or registry writes. If invalid, return HTTP **422** with a readable JSON error. Enforce request/upload size limits at the HTTP boundary as appropriate; browser validation is bypassable.
- [ ] Pass **`report_clean`** to report-context/model/explanation steps. Keep original-byte hashing distinct from cleaned content; agree with Abidi about synthetic raw-report retention off chain.
- [ ] Run her own preprocessing/model and provide `prediction={label,confidence,model_name,model_version}` and `quality={valid,reasons}`. Enforce her 30-point signal minimum there; our format checker intentionally accepts `ecg_short.csv`.
- [ ] Call `validate(prediction, quality, artifacts_ok=actual_artifact_state, integrity_ok=actual_integrity_state, report_text=checked["report_clean"])`. The defaults are required by the shared signature but do not establish real integrity.
- [ ] Return the exact analysis envelope and all eight expected artifact types with coherent lineage, real storage references and registry receipts. Keep model confidence in `[0,1]`.
- [ ] Expose the four exact routes in the table above. Agree to the history envelope and verification conventions before merge. Use `prediction:null` for a missing-prediction rejection only after confirming that extension.
- [ ] Authorize frontend origin `http://127.0.0.1:5500` for GET/POST with CORS, or serve the frontend from FastAPI. Add `http://localhost:5500` only if the team uses that hostname too. Verify CORS in a real browser.
- [ ] Consider whether 30 seconds is sufficient for the completed analysis pipeline and configure the adapter accordingly.
- [ ] Retain her own `requirements.txt`; include/merge this delivery’s development dependency as desired. No FastAPI/model/Fabric dependency was added to Mezghani’s runtime modules.

## What Rimeh Abidi needs to connect

- [ ] Preserve `app.registry.record_artifact(record)` and `get_artifact(artifact_id)` and her `app/hashing.py` API. The frontend talks only to Mrabet’s REST endpoints.
- [ ] Return `{tx_id,ledger_mode}` from registration, with actual Fabric receipts only when Fabric was really used. MOCK must remain explicit.
- [ ] Preserve the full registry ArtifactRecord contract: `artifact_id`, `case_id`, `type`, `sha256`, `created_at`, `version`, `parent_id`, `storage_ref`, `created_by`. The frontend consumes the documented projection plus `tx_id`.
- [ ] Hash original ECG/report bytes and canonicalized derived JSON exactly as specified. Store medical content off chain; registry entries contain only agreed metadata/hashes.
- [ ] Make initial proof lookup available to Mrabet’s verify endpoint. That endpoint must compare stored files with the registry’s initial hashes and distinguish modified, missing and unverifiable evidence.
- [ ] Agree to null hashes and aggregate-status conventions; test absent registry/proof and absent files, not just mismatched hashes.
- [ ] Test a real off-chain file mutation and, separately, Fabric create/read transactions in the integrated environment. None of these real operations was demonstrated by the frontend mock.

## Manual browser verification still required

Start the dashboard from the project root:

```powershell
Set-Location 'C:\Users\Lenovo\Desktop\projet_tarek'
.\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1
```

Open **http://127.0.0.1:5500/frontend/** in a current Edge, Chrome or Firefox browser. Stop the server with Ctrl+C afterward.

1. Submit with no files, then with `ecg_invalid.csv` / `report_invalid.txt`: confirm readable errors, no new case and a reenabled button.
2. Load the supplied synthetic files and analyze with confidence-high selected. Check the waveform, 720-point count, demo label, 91%, model/version, ACCEPTED, reasons, explanation, UUID and MOCK disclaimer.
3. Inspect all eight artifact rows: full hashes, parent IDs, MOCK transactions and storage references. Confirm the table is usable at desktop and mobile widths.
4. Verify intact => VALID. Simulate modification, then reverify => MODIFIED with different expected/actual hashes for processed. The initial ACCEPTED validation remains historical and separate.
5. Analyze the other four scenarios. Check confidence-low/quality => REVIEW_REQUIRED, missing artifact => REJECTED and MISSING, integrity failure => REJECTED and MODIFIED. Reopen an earlier session case and refresh its timeline.
6. During a request, try a rapid second click and changing controls. Verify there is no duplicate case. Test keyboard navigation, focus indicators and announced errors. Reload: the local session clears.
7. Switch to API with no backend running and analyze: require an error, no silent mock data. After colleagues connect their service, repeat with the real backend and inspect the browser network panel for the exact routes, file fields, CORS and HTTP 422 handling.
8. After integration, modify an actual synthetic artifact on disk, then call verify again. Separately disconnect the ledger/proof source and require UNVERIFIABLE. These are different from the MOCK tamper button.
9. Save authentic upload, result, history and change-detection screenshots in `docs/captures/`. Do not label a MOCK capture as Fabric evidence.

The existing `tests/test_ui_manual.md` contains the expanded 22-step plan. Clinical AI accuracy and real Hyperledger Fabric operation remain **not tested**.
