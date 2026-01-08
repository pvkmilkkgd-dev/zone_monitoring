const fs = require("fs");

const file = process.argv[2] || "regions.geojson";
const fc = JSON.parse(fs.readFileSync(file, "utf8"));

function walkCoords(coords, cb) {
  if (!Array.isArray(coords)) return;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") return cb(coords);
  for (const c of coords) walkCoords(c, cb);
}

function bboxFeature(geom) {
  let minX = +Infinity, minY = +Infinity, maxX = -Infinity, maxY = -Infinity;
  walkCoords(geom.coordinates, ([x, y]) => {
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  });
  return { minX, minY, maxX, maxY, w: maxX - minX, h: maxY - minY };
}

const LIMITS = { lonMin: 10, lonMax: 200, latMin: 40, latMax: 90 };

const bad = [];
for (const f of fc.features) {
  const name = f.properties?.name || f.properties?.NAME || "(no name)";
  const b = bboxFeature(f.geometry);
  const out =
    b.minX < LIMITS.lonMin || b.maxX > LIMITS.lonMax || b.minY < LIMITS.latMin || b.maxY > LIMITS.latMax;

  if (out) bad.push({ name, bbox: b });
}

console.log(`Features: ${fc.features.length}`);
console.log(`Out of limits: ${bad.length}`);
for (const r of bad) {
  const b = r.bbox;
  console.log(
    `${r.name}: lon[${b.minX.toFixed(3)}..${b.maxX.toFixed(3)}], lat[${b.minY.toFixed(3)}..${b.maxY.toFixed(3)}]`
  );
}
