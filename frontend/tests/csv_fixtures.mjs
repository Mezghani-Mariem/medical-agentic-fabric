import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { inspectUploads } from "../input_preview.js";

export const cases = JSON.parse(await readFile(new URL("../../samples/csv_contract_cases.json", import.meta.url), "utf8")).cases;
export function fixtureBytes(item, field) {
  if (`${field}_hex` in item) return Buffer.from(item[`${field}_hex`], "hex");
  const value = `${field}_parts` in item
    ? item[`${field}_parts`].map(part => typeof part === "string" ? part : part.repeat.repeat(part.count)).join("")
    : item[field] ?? "Rapport entièrement synthétique.";
  return Buffer.from(value, "utf8");
}
export async function evaluate(item) {
  try {
    const preview = await inspectUploads(new File([fixtureBytes(item, "ecg")], "ecg.csv"), new File([fixtureBytes(item, "report")], "report.txt"));
    return { id: item.id, valid: true, points: preview.count };
  } catch { return { id: item.id, valid: false }; }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  console.log(JSON.stringify(await Promise.all(cases.map(evaluate))));
}
