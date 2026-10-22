/** Test doubles, not a browser: no CSS/layout, browser CORS or FileList testing. */
import { readFile } from "node:fs/promises";
import vm from "node:vm";
import { ApiAdapter } from "../api_adapter.js";
import { MockAdapter } from "../mock_api.js";
import { ARTIFACT_TYPES, assertAnalysis, assertHistory, assertVerification } from "../contracts.js";
import { inspectUploads } from "../input_preview.js";
import { BASELINE_POINTS, waveformPoints } from "../waveform.js";

class Element {
  constructor() { Object.assign(this, { children: [], listeners: new Map(), attributes: {}, style: {}, className: "", _text: "", files: [], value: "", disabled: false, hidden: false }); }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  get firstElementChild() { return this.children[0] || null; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this._text = ""; this.children = [...nodes]; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  dispatchEvent(event) { return this.listeners.get(event.type)?.(event); }
  focus() { this.focused = true; }
}

export async function dashboard() {
  const root = new URL("../", import.meta.url);
  const html = await readFile(new URL("index.html", root), "utf8");
  const nodes = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], new Element()]));
  const node = id => nodes.get(id);
  node("analyze-button").append(new Element(), new Element());
  node("adapter-mode").value = "mock";
  node("mock-scenario").value = "accepted";
  node("api-url").value = "http://127.0.0.1:8000";
  const document = {
    getElementById: node,
    createElement: () => new Element(),
    querySelectorAll: selector => selector === ".case-item"
      ? node("case-list").children.filter(item => item.className.split(" ").includes("case-item")) : [],
  };
  class BrowserFormData extends FormData {
    constructor(form) {
      super();
      if (form) for (const field of ["ecg", "report"]) {
        if (!node(`${field}-file`).disabled) for (const file of node(`${field}-file`).files) this.append(field, file, file.name);
      }
    }
  }
  class Transfer {
    constructor() { this.files = []; this.items = { add: file => this.files.push(file) }; }
  }
  const localFetch = async url => {
    const target = url instanceof URL ? url : new URL(url, root);
    const bytes = await readFile(target);
    return { ok: true, json: async () => JSON.parse(bytes.toString("utf8")), blob: async () => new Blob([bytes]) };
  };
  const context = vm.createContext({ document, ApiAdapter, MockAdapter: class extends MockAdapter {
    constructor() { super({ fetcher: localFetch }); }
  }, ARTIFACT_TYPES, assertAnalysis, assertHistory, assertVerification, inspectUploads,
  BASELINE_POINTS, waveformPoints, fetch: localFetch, FormData: BrowserFormData, File, Blob, DataTransfer: Transfer, Event, URL });
  const source = (await readFile(new URL("app.js", root), "utf8")).replace(/^import .*;\r?\n/gm, "");
  vm.runInContext(source, context);
  return {
    node,
    click: id => node(id).listeners.get("click")(),
    submit: () => node("analysis-form").listeners.get("submit")({ preventDefault() {} }),
    state: () => vm.runInContext("active", context),
    plot: preview => { context.testPreview = preview; vm.runInContext("plot(testPreview)", context); },
    setAdapter: adapter => { context.testAdapter = adapter; vm.runInContext("adapter = testAdapter", context); },
    connect: () => vm.runInContext("connect()", context),
  };
}
