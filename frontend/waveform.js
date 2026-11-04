/** Display-only coordinates. Never preprocess or interpret the ECG medically. */
export const PREVIEW_POINTS = 800;
export const BASELINE_POINTS = "0,85 800,85";

export function waveformPoints(values) {
  if (!Array.isArray(values) || !values.length || values.length > PREVIEW_POINTS) return null;
  let scale = 0;
  for (const value of values) {
    if (typeof value !== "number" || !Number.isFinite(value)) return null;
    scale = Math.max(scale, Math.abs(value));
  }
  // Scale BEFORE subtraction: max - min can overflow for finite ±1e308.
  const scaled = values.map(value => scale ? value / scale : 0);
  let lo = 1, hi = -1;
  for (const value of scaled) { lo = Math.min(lo, value); hi = Math.max(hi, value); }
  const extent = hi - lo; // bounded by 2, including subnormal inputs
  const points = [];
  for (let index = 0; index < scaled.length; index++) {
    const x = index * 800 / Math.max(scaled.length - 1, 1);
    const y = extent ? 145 - (scaled[index] - lo) / extent * 120 : 85;
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    points.push(`${x},${Math.min(145, Math.max(25, y))}`);
  }
  return points.join(" ");
}
