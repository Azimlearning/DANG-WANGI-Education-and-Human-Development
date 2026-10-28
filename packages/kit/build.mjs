// Builds the Kit into dist/<semver>/core.js (IIFE exposing a frozen window.Synapse) and dist/<semver>/manifest.json.
//
// Hard constraint 6: a behaviour change bumps the Kit semver. This build enforces it: kit-lock.json (committed) records the SHA-256 of
// each released version's bundle. Building a locked version whose bytes differ FAILS, naming the fix (bump KIT_VERSION and
// package.json). A new version is added to the lock by this build; `--relock` replaces a version's entry and is for an UNRELEASED
// version only (a visible, deliberate act that shows in the diff of kit-lock.json). The manifest carries the bundle hash so the
// delivery gate can tell a stale Kit from the current one.
import { build } from "esbuild";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const relock = process.argv.includes("--relock");
const manifestSource = readFileSync(resolve(here, "src/manifest.ts"), "utf-8");
const version = /KIT_VERSION = "([^"]+)"/.exec(manifestSource)?.[1];
if (!version) throw new Error("build: KIT_VERSION not found in src/manifest.ts");
const pkgVersion = JSON.parse(readFileSync(resolve(here, "package.json"), "utf-8")).version;
if (pkgVersion !== version) throw new Error(`build: package.json version ${pkgVersion} != KIT_VERSION ${version}`);

const outdir = resolve(here, "dist", version);
mkdirSync(outdir, { recursive: true });
const coreFile = resolve(outdir, "core.js");
await build({
  entryPoints: [resolve(here, "src/index.ts")],
  outfile: coreFile,
  bundle: true,
  format: "iife",
  globalName: "__synapse_kit",
  // Defined once, non-writable and non-configurable: generated code can neither replace nor redefine the Kit (kit-guardian S4).
  footer: {
    // Order matters: freeze the intrinsics first, then publish the Kit, so no generated script ever sees a patchable built-in.
    // The unit tests that load this bundle into the test runner's own realm set the flag below; a page cannot, because the Kit is
    // the first script it loads (the verifier requires that) so nothing of the page's has run yet.
    js: 'if(!window.__SYNAPSE_NO_LOCKDOWN__)__synapse_kit.lockdown();Object.defineProperty(window,"Synapse",{value:__synapse_kit.Synapse,writable:false,configurable:false,enumerable:true});',
  },
  minify: true,
  target: "es2020",
  legalComments: "none",
});
const bundle = readFileSync(coreFile);
const bundleSha256 = createHash("sha256").update(bundle).digest("hex");

const lockFile = resolve(here, "kit-lock.json");
const lock = existsSync(lockFile) ? JSON.parse(readFileSync(lockFile, "utf-8")) : {};
if (lock[version] && lock[version] !== bundleSha256 && !relock) {
  rmSync(coreFile);
  console.error(
    `build: Kit ${version} is locked at ${lock[version].slice(0, 12)} but this build is ${bundleSha256.slice(0, 12)}.\n` +
      `The Kit's behaviour changed without a version bump. Bump KIT_VERSION in src/manifest.ts and version in package.json.\n` +
      `(For an unreleased version only: pnpm --filter @synapse/kit build --relock)`,
  );
  process.exit(1);
}
if (lock[version] !== bundleSha256) {
  lock[version] = bundleSha256;
  writeFileSync(lockFile, JSON.stringify(Object.fromEntries(Object.entries(lock).sort()), null, 2) + "\n");
}

// Load the entries through esbuild too, so the manifest comes from the same TypeScript the tests check.
const tmp = resolve(outdir, ".manifest.mjs");
await build({ entryPoints: [resolve(here, "src/manifest.ts")], outfile: tmp, bundle: true, format: "esm", target: "es2020" });
// A bare absolute path is not a valid import specifier on Windows ("c:" reads as a URL scheme), so go through a file URL.
const { manifestEntries, APPARATUS } = await import(pathToFileURL(tmp).href + "?t=" + Date.now());
rmSync(tmp);
writeFileSync(
  resolve(outdir, "manifest.json"),
  JSON.stringify({ version, bundle: "core.js", bundleSha256, components: manifestEntries, apparatus: APPARATUS }, null, 2) + "\n",
);
console.log(`kit ${version}: core.js ${bundle.length} bytes sha256 ${bundleSha256.slice(0, 12)}, ${manifestEntries.length} manifest entries -> ${outdir}`);
