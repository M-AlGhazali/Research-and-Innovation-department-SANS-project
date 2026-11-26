// Scenario playback along the saved profile of one scenarios/index.json record.
// profile rows are [distance_nm, altitude_ft, lon, lat]. Time and fuel grow in proportion to the distance flown,
// from 0 at brake release to the saved to10k totals at the 10,000 ft point.
export function playbackAt(record, t) {
  const {time_s: T, distance_nm: D, fuel_kg, co2_kg} = record.to10k, p = record.profile;
  const f = Math.min(Math.max(t / T, 0), 1), d = f * D;
  let i = 1;
  while (i < p.length - 1 && p[i][0] < d) i++;
  const a = p[i - 1], b = p[i], k = b[0] > a[0] ? Math.min(Math.max((d - a[0]) / (b[0] - a[0]), 0), 1) : 1;
  const lerp = j => a[j] + (b[j] - a[j]) * k;
  return {t: f * T, d, alt: lerp(1), lon: lerp(2), lat: lerp(3), fuel: fuel_kg * f, co2: co2_kg * f, done: f >= 1, from: a, to: b};
}
