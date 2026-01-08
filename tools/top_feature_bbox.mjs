import fs from "node:fs";

const path = process.argv[2];
if (!path) {
  console.error("Usage: node tools/top_feature_bbox.mjs <file.geojson>");
  process.exit(1);
}

const fc = JSON.parse(fs.readFileSync(path, "utf8"));

function walkCoords(g, cb) {
  if (!g) return;
  if (g.type === "Point") cb(g.coordinates);
  else if (g.type === "MultiPoint" || g.type === "LineString") g.coordinates.forEach(cb);
  else if (g.type === "MultiLineString" || g.type === "Polygon") g.coordinates.flat().forEach(cb);
  else if (g.type === "MultiPolygon") g.coordinates.flat(2).forEach(cb);
  else if (g.type === "GeometryCollection") g.geometries.forEach((gg) => walkCoords(gg, cb));
}

function bboxOfFeature(f) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  walkCoords(f.geometry, ([x, y]) => {
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  });
  return { minX, minY, maxX, maxY, w: maxX - minX, h: maxY - minY };
}

const rows = fc.features.map((f) => {
  const name =
    f.properties?.name ||
    f.properties?.NAME ||
    f.properties?.region ||
    f.properties?.NAME_1 ||
    f.id ||
    "???";
  const b = bboxOfFeature(f);
  return { name, ...b };
});

rows.sort((a, b) => b.w - a.w);
console.table(rows.slice(0, 20));
