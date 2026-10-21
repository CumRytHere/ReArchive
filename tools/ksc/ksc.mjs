#!/usr/bin/env node
// Compile one .ksy to Python with byte positions (--read-pos), without Java.
// Usage: node tools/ksc/ksc.mjs <spec.ksy> <out_dir>
// Writes <out_dir>/<id>.py with a header recording the compiler version and the
// SHA-256 of the source .ksy, so CI can regenerate and diff (D-003).
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { basename, join } from "node:path";
import { createRequire } from "node:module";
import yaml from "js-yaml";

const require = createRequire(import.meta.url);
// Since 0.11.0 the module exports the compiler object itself, not a constructor.
const compiler = require("kaitai-struct-compiler");

const [, , ksyPath, outDir] = process.argv;
if (!ksyPath || !outDir) {
  console.error("usage: ksc.mjs <spec.ksy> <out_dir>");
  process.exit(2);
}
const source = readFileSync(ksyPath);
const sha256 = createHash("sha256").update(source).digest("hex");
const spec = yaml.load(source.toString("utf8"));

// debugMode = --read-pos + --no-auto-read: every parsed field records start/end
// offsets in obj._debug, and the caller must invoke obj._read() explicitly.
const debugMode = true;
const files = await compiler.compile("python", spec, null, debugMode);

mkdirSync(outDir, { recursive: true });
for (const [name, body] of Object.entries(files)) {
  const header =
    `# GENERATED FILE - DO NOT EDIT.\n` +
    `# source: ${basename(ksyPath)}\n` +
    `# source-sha256: ${sha256}\n` +
    `# compiler: kaitai-struct-compiler ${compiler.version} (npm), python target, debug mode\n`;
  writeFileSync(join(outDir, name), header + body);
  console.log(`${join(outDir, name)}  ksy-sha256=${sha256}  ksc=${compiler.version}`);
}
