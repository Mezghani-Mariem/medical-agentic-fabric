/** Same content rules as app/input_checks.py; backend checks remain authoritative. */
import { PREVIEW_POINTS } from "./waveform.js";

export const MAX_CSV_FIELD_CHARS = 131072;
const NUMBER = /^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/;
const CONTROL = /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/;
// Python str.strip(): JS trim() additionally strips U+FEFF and misses U+0085.
const PY_WHITESPACE = /^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g;
const strip = value => value.replace(PY_WHITESPACE, "");

function cleanText(text, name) {
  if (typeof text !== "string") throw new Error(`${name} : texte UTF-8 requis.`);
  text = text.replace(/^\ufeff/, ""); // exactly one BOM, like utf-8-sig
  if (!strip(text) || CONTROL.test(text)) throw new Error(`${name} : contenu vide, binaire ou caractères de contrôle interdits.`);
  return text;
}

function readCsv(text, onRow) {
  let row = [], field = "", fieldChars = 0, state = "start", nonempty = false;
  const append = char => {
    if (++fieldChars > MAX_CSV_FIELD_CHARS) throw new Error("ECG : champ CSV trop long (131 072 caractères maximum).");
    field += char;
  };
  const finishField = () => { row.push(field); field = ""; fieldChars = 0; state = "start"; };
  for (let i = 0; i < text.length;) {
    const char = String.fromCodePoint(text.codePointAt(i));
    i += char.length; // Unicode code points, as Python csv.reader counts
    if (state === "quoted") {
      if (char === '"') {
        if (text[i] === '"') { append('"'); i++; } else state = "closed";
      } else append(char);
      continue;
    }
    if (char === ",") { finishField(); nonempty = true; }
    else if (char === "\r" || char === "\n") {
      if (char === "\r" && text[i] === "\n") i++;
      if (nonempty || row.length || field) finishField();
      onRow(row); // [] before header is invalid; [] within data is ignored
      row = []; field = ""; fieldChars = 0; state = "start"; nonempty = false;
    } else if (state === "closed") { throw new Error("ECG : CSV mal formé après un guillemet."); }
    else if (char === '"' && state === "start") { state = "quoted"; nonempty = true; }
    else { append(char); state = "plain"; nonempty = true; }
  }
  if (state === "quoted") throw new Error("ECG : guillemet non fermé.");
  if (nonempty || row.length || field) { finishField(); onRow(row); }
}

export function signalPreview(text) {
  text = cleanText(text, "ECG");
  let header = null, signalIndex = -1, count = 0;
  const values = [];
  readCsv(text, row => {
    if (header === null) {
      header = row;
      signalIndex = row.indexOf("signal");
      if (signalIndex < 0 || new Set(row).size !== row.length || row.some(item => !strip(item))) {
        throw new Error("ECG : colonne exacte 'signal' requise, sans en-têtes vides ni doublons (CSV à virgules).");
      }
      return;
    }
    if (!row.length) return;
    if (row.length !== header.length) throw new Error("ECG : nombre de colonnes incohérent.");
    const cell = strip(row[signalIndex]);
    const value = Number(cell);
    if (!NUMBER.test(cell) || !Number.isFinite(value)) throw new Error("ECG : valeurs numériques finies requises dans la colonne signal.");
    count++;
    if (values.length < PREVIEW_POINTS) values.push(value);
  });
  if (!count) throw new Error("ECG : aucune valeur de signal.");
  return { values, count };
}

export async function inspectUploads(ecg, report) {
  if (!ecg || !report) throw new Error("Choisissez un ECG CSV et un rapport TXT, ou chargez les fichiers de démonstration.");
  if (!/\.csv$/i.test(ecg.name)) throw new Error("ECG : extension .csv requise.");
  if (!/\.txt$/i.test(report.name)) throw new Error("Rapport : extension .txt requise.");
  if (!ecg.size || !report.size) throw new Error("Les fichiers ne doivent pas être vides.");
  if (ecg.size > 2 * 1024 * 1024) throw new Error("ECG : taille supérieure à 2 Mio.");
  if (report.size > 64 * 1024) throw new Error("Rapport : taille supérieure à 64 Kio.");
  let ecgText, reportText;
  try {
    const buffers = await Promise.all([ecg.arrayBuffer(), report.arrayBuffer()]);
    // Preserve BOM here: cleanText removes it exactly once.
    ecgText = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(buffers[0]);
    reportText = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(buffers[1]);
  } catch { throw new Error("Les deux fichiers doivent être encodés en UTF-8."); }
  cleanText(reportText, "Rapport");
  return signalPreview(ecgText);
}
