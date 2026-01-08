#!/usr/bin/env node
// Patch Russian regions GeoJSON with extra polygons converted from WebMercator to WGS84.
// Usage:
//   node tools/patch_ru_regions.mjs
// Helpers:
//   node tools/geojson_bbox.mjs backend/maps/ru/extra/luhansk.geojson
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(__filename), "..");
const MAIN_PATH = path.join(ROOT, "backend", "maps", "ru", "regions.geojson");
const EXTRA_DIR = path.join(ROOT, "backend", "maps", "ru", "extra");
const EXTRA_WGS_DIR = path.join(ROOT, "backend", "maps", "ru", "extra_wgs84");

const EXTRA_FILES = [
  { file: "crimea.geojson", name: "Республика Крым" },
  { file: "donetsk.geojson", name: "Донецкая Народная Республика" },
  { file: "luhansk.geojson", name: "Луганская Народная Республика" },
  { file: "kherson.geojson", name: "Херсонская область" },
  { file: "zaporizhzhia.geojson", name: "Запорожская область" },
];

const R = 6378137;
const m2lon = (x) => (x / R) * (180 / Math.PI);
const m2lat = (y) => (2 * Math.atan(Math.exp(y / R)) - Math.PI / 2) * (180 / Math.PI);

function convertCoords(coords) {
  if (!coords) return coords;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") {
    return [m2lon(coords[0]), m2lat(coords[1])];
  }
  return coords.map((c) => convertCoords(c));
}

function convertGeometry(geom) {
  if (!geom) return geom;
  return { ...geom, coordinates: convertCoords(geom.coordinates) };
}

function normalizeGeometry(data) {
  if (!data || typeof data !== "object") {
    throw new Error("Empty or invalid GeoJSON");
  }
  if (data.type === "FeatureCollection") {
    for (const f of data.features || []) {
      if (f?.geometry && f.geometry.type) return f.geometry;
    }
    throw new Error("FeatureCollection has no geometry");
  }
  if (data.type === "Feature") {
    if (data.geometry?.type) return data.geometry;
    throw new Error("Feature has no geometry");
  }
  if (data.type && data.coordinates) {
    return data;
  }
  throw new Error("Unsupported GeoJSON structure");
}

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function writeJson(p, obj) {
  fs.writeFileSync(p, JSON.stringify(obj, null, 2), "utf-8");
}

function ensureDir(p) {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

function tsSuffix() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return (
    now.getFullYear().toString() +
    pad(now.getMonth() + 1) +
    pad(now.getDate()) +
    "_" +
    pad(now.getHours()) +
    pad(now.getMinutes()) +
    pad(now.getSeconds())
  );
}

function visitCoords(coords, fn) {
  if (!coords) return;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") {
    fn(coords);
    return;
  }
  for (const c of coords) visitCoords(c, fn);
}

function featureBbox(feature) {
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  visitCoords(feature?.geometry?.coordinates, ([x, y]) => {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  });

  return { minX, maxX, minY, maxY, width: maxX - minX };
}

function geometryBbox(geom) {
  const dummy = { geometry: geom };
  return featureBbox(dummy);
}

function isLikelyWgs84(geom) {
  if (!geom) return false;
  const { minX, maxX, minY, maxY } = geometryBbox(geom);
  if (
    !Number.isFinite(minX) ||
    !Number.isFinite(maxX) ||
    !Number.isFinite(minY) ||
    !Number.isFinite(maxY)
  ) {
    return false;
  }
  return maxX <= 200 && minX >= -200 && maxY <= 90 && minY >= -90;
}

function normalizeAntimeridian(feature) {
  if (!feature?.geometry?.coordinates) return feature;
  const { width } = featureBbox(feature);
  if (!Number.isFinite(width) || width <= 180) return feature;

  const shift = (coords) => {
    if (!coords) return coords;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      const x = coords[0] < 0 ? coords[0] + 360 : coords[0];
      return [x, coords[1]];
    }
    return coords.map((c) => shift(c));
  };

  return {
    ...feature,
    geometry: {
      ...feature.geometry,
      coordinates: shift(feature.geometry.coordinates),
    },
  };
}

function main() {
  if (!fs.existsSync(MAIN_PATH)) throw new Error("Main GeoJSON not found: " + MAIN_PATH);
  ensureDir(EXTRA_WGS_DIR);

  const mainJson = readJson(MAIN_PATH);
  if (mainJson.type !== "FeatureCollection") {
    throw new Error("Main file is not a FeatureCollection");
  }

  // Remove old versions of target regions.
  mainJson.features = (mainJson.features || []).filter(
    (f) => !EXTRA_FILES.some((item) => (f.properties || {}).name === item.name),
  );

  const added = [];
  for (const item of EXTRA_FILES) {
    const srcPath = path.join(EXTRA_DIR, item.file);
    if (!fs.existsSync(srcPath)) {
      throw new Error("Missing extra file: " + srcPath);
    }
    const raw = readJson(srcPath);
    const geom = normalizeGeometry(raw);
    const convertedGeom = isLikelyWgs84(geom) ? geom : convertGeometry(geom);

    const feature = {
      type: "Feature",
      properties: {
        name: item.name,
        name_ru: item.name,
        "name:ru": item.name,
      },
      geometry: convertedGeom,
    };

    mainJson.features.push(feature);
    added.push(item.name);

    const wgsPath = path.join(EXTRA_WGS_DIR, item.file);
    writeJson(wgsPath, {
      type: "Feature",
      properties: feature.properties,
      geometry: feature.geometry,
    });
  }

  // Normalize antimeridian crossings for all features.
  mainJson.features = (mainJson.features || []).map((f) => normalizeAntimeridian(f));

  // Backup and save.
  const backupPath = path.join(ROOT, "backend", "maps", "ru", `regions.geojson.bak_${tsSuffix()}`);
  fs.copyFileSync(MAIN_PATH, backupPath);
  writeJson(MAIN_PATH, mainJson);

  console.log("Patched regions:", added.length, "added");
  for (const name of added) console.log("- " + name);
  console.log("Backup saved to:", backupPath);

  // Print bbox for added regions.
  for (const name of EXTRA_FILES.map((x) => x.name)) {
    const f = (mainJson.features || []).find((feat) => (feat.properties || {}).name === name);
    if (!f) {
      console.log(`[WARN] Feature not found for bbox: ${name}`);
      continue;
    }
    const { minX, maxX, minY, maxY } = featureBbox(f);
    console.log(
      `[BBox] ${name}: minX=${minX.toFixed(6)}, maxX=${maxX.toFixed(6)}, minY=${minY.toFixed(6)}, maxY=${maxY.toFixed(6)}`,
    );
  }
}

main();
