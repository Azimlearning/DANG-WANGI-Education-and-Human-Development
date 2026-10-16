// Builds the Kit into dist/<semver>/core.js (IIFE exposing window.Synapse) and dist/<semver>/manifest.json.
import { build } from "esbuild";
import { mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const manifestSource = readFileSync(resolve(here, "src/manifest.ts"), "utf-8");
const version = /KIT_VERSION = "([^"]+)"/.exec(manifestSource)?.[1];
if (!version) throw new Error("build: KIT_VERSION not found in src/manifest.ts");
const pkgVersion = JSON.parse(readFileSync(resolve(here, "package.json"), "utf-8")).version;
if (pkgVersion !== version) throw new Error(`build: package.json version ${pkgVersion} != KIT_VERSION ${version}`);

const outdir = resolve(here, "dist", version);
mkdirSync(outdir, { recursive: true });
await build({
  entryPoints: [resolve(here, "src/index.ts")],
  outfile: resolve(outdir, "core.js"),
  bundle: true,
  format: "iife",
  globalName: "__synapse_kit",
  footer: { js: "window.Synapse=__synapse_kit.Synapse;" },
  minify: true,
  target: "es2020",
  legalComments: "none",
});

// Load the entries through esbuild too, so the manifest comes from the same TypeScript the tests check.
const tmp = resolve(outdir, ".manifest.mjs");
await build({ entryPoints: [resolve(here, "src/manifest.ts")], outfile: tmp, bundle: true, format: "esm", target: "es2020" });
const { manifestEntries } = await import(tmp + "?t=" + Date.now());
const bundleBytes = statSync(resolve(outdir, "core.js")).size;
writeFileSync(
  resolve(outdir, "manifest.json"),
  JSON.stringify({ version, bundle: "core.js", components: manifestEntries }, null, 2) + "\n",
);
import("node:fs").then((fs) => fs.rmSync(tmp));
console.log(`kit ${version}: core.js ${bundleBytes} bytes, ${manifestEntries.length} manifest entries -> ${outdir}`);
