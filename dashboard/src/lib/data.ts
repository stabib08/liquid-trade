import fs from "node:fs";
import path from "node:path";
import type { Report } from "./types";

// The report JSON is produced by the Python pipeline and copied to public/data.
// Read at build time (this is a static server component) — no runtime fetch.
export function loadReport(): Report {
  const p = path.join(process.cwd(), "public", "data", "report.json");
  return JSON.parse(fs.readFileSync(p, "utf8")) as Report;
}
