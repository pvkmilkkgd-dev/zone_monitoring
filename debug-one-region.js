// node debug-one-region.js backend/maps/ru/regions.geojson "Херсонская область"
const fs = require("fs");

const file = process.argv[2];
const target = process.argv[3];

const fc = JSON.parse(fs.readFileSync(file, "utf8"));

function walkCoords(coords, cb) {
  if (!Array.isArray(coords)) return;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") return cb(coords);
  for (const c of coords) walkCoords(c, cb);
}

function bboxGeom(geom) {
  let minX = +Infinity, minY = +Infinity, maxX = -Infinity, maxY = -Infinity;
  let points = 0;
  walkCoords(geom.coordinates, ([x, y]) => {
    points++;
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  });
  return { minX, minY, maxX, maxY, points };
}

const f = fc.features.find(x => (x.properties?.name || x.properties?.NAME) === target);
if (!f) {
  console.log("NOT FOUND:", target);
  process.exit(1);
}

const b = bboxGeom(f.geometry);
console.log("name:", target);
console.log("type:", f.geometry.type);
console.log("points:", b.points);
console.log(`bbox: lon[${b.minX}..${b.maxX}] lat[${b.minY}..${b.maxY}]`);

// покажем первые 6 точек (часто у заглушек их 5 — прямоугольник)
let first = [];
walkCoords(f.geometry.coordinates, (p) => {
  if (first.length < 6) first.push(p);
});
console.log("first points:", first);
