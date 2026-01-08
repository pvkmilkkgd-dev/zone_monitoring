#!/usr/bin/env node
// Quick bbox inspector for GeoJSON.
// Usage:
//   node tools/geojson_bbox.mjs path/to/file.geojson
import fs from "fs";
import path from "path";

function readJson(p) {
  const text = fs.readFileSync(p, "utf-8");
  return JSON.parse(text);
}

function visitCoords(coords, fn) {
  if (!coords) return;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") {
    fn(coords[0], coords[1]);
    return;
  }
  for (const c of coords) visitCoords(c, fn);
}

function collectBbox(obj) {
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  const mark = (x, y) => {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  };

  const walkFeature = (f) => {
    const g = f?.geometry;
    if (!g) return;
    visitCoords(g.coordinates, mark);
  };

  if (obj?.type === "FeatureCollection") {
    for (const f of obj.features || []) walkFeature(f);
  } else if (obj?.type === "Feature") {
    walkFeature(obj);
  } else if (obj?.type) {
    visitCoords(obj.coordinates, mark);
  }

  return { minX, minY, maxX, maxY };
}

function main() {
  const input = process.argv[2];
  if (!input) {
    console.error("Usage: node tools/geojson_bbox.mjs <file.geojson>");
    process.exit(1);
  }
  const fullPath = path.resolve(process.cwd(), input);
  if (!fs.existsSync(fullPath)) {
    console.error("File not found:", fullPath);
    process.exit(1);
  }

  const data = readJson(fullPath);
  const { minX, minY, maxX, maxY } = collectBbox(data);
  console.log("BBox:", [minX, minY, maxX, maxY].map((v) => v.toFixed(6)).join(", "));
  console.log("Range X:", (maxX - minX).toFixed(6));
  console.log("Range Y:", (maxY - minY).toFixed(6));
}

main();
