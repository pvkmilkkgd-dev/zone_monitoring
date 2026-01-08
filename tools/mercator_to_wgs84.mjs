#!/usr/bin/env node
// Convert GeoJSON coordinates from EPSG:3857 (WebMercator meters) to WGS84 lon/lat.
// Usage:
//   node tools/mercator_to_wgs84.mjs input.geojson output.geojson
import fs from "fs";
import path from "path";

const R = 6378137;

function m2lon(x) {
  return (x / R) * (180 / Math.PI);
}

function m2lat(y) {
  return (2 * Math.atan(Math.exp(y / R)) - Math.PI / 2) * (180 / Math.PI);
}

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

function convert(input) {
  if (!input || typeof input !== "object") return input;
  if (input.type === "FeatureCollection") {
    return {
      ...input,
      features: (input.features || []).map((f) => ({
        ...f,
        geometry: convertGeometry(f.geometry),
      })),
    };
  }
  if (input.type === "Feature") {
    return {
      ...input,
      geometry: convertGeometry(input.geometry),
    };
  }
  if (input.type && input.coordinates) {
    return convertGeometry(input);
  }
  throw new Error("Unsupported GeoJSON structure");
}

function main() {
  const [inputPath, outputPath] = process.argv.slice(2);
  if (!inputPath || !outputPath) {
    console.error("Usage: node tools/mercator_to_wgs84.mjs <input.geojson> <output.geojson>");
    process.exit(1);
  }
  const src = path.resolve(process.cwd(), inputPath);
  const dst = path.resolve(process.cwd(), outputPath);

  const raw = fs.readFileSync(src, "utf-8");
  const parsed = JSON.parse(raw);
  const converted = convert(parsed);
  fs.writeFileSync(dst, JSON.stringify(converted, null, 2), "utf-8");
  console.log("Converted:", src, "->", dst);
}

main();
