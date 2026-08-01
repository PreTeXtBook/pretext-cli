/**
 * A jing-compatible front end for the salve-annos validator in
 * `@pretextbook/schema` (the engine behind the pretext-tools VS Code extension).
 *
 * Core's `validate()` invokes its RELAX-NG engine as
 *
 *     <jing command> <schema.rng> <assembled-source.xml>
 *
 * and reads stdout as lines matching  ^.*?:(\d+):(\d+): (.*)$ , using the line
 * number and the message body.  Exit 0 means valid and 1 means the document has
 * messages.  Satisfying that contract is all it takes to stand in for jing, and
 * core then produces its usual consolidated report.
 *
 * Runs under Node and under Deno: nothing Node-only is imported at module
 * scope, and the package's `require("fs")` lives in a default file reader that
 * the `readFile` override below keeps out of the picture.  (The grammar
 * compiler *is* Node-locked, so it is imported dynamically, only on a cache
 * miss.)
 */
import { readFileSync, writeFileSync, mkdirSync, statSync } from "node:fs";
import { basename } from "node:path";
import { fileURLToPath } from "node:url";

// Kinds that RELAX-NG itself can express.  The others the package can report
// (duplicate-id, duplicate-label, dangling-reference) are the ground core
// covers with its "validation-plus" stylesheet, so including them here would
// double-report them in the consolidated report.
const SCHEMA_KINDS = new Set([
  "element-not-allowed",
  "attribute-not-allowed",
  "attribute-value-invalid",
  "choice-not-satisfied",
  "text-not-allowed",
  "unexpected-end",
  "well-formedness",
  "other",
]);

const [schemaPath, sourcePath] = process.argv.slice(2);
if (!schemaPath || !sourcePath) {
  console.error("usage: ptx-jing-shim <schema.rng> <source.xml>");
  process.exit(2);
}

/**
 * Report a failure of the validator itself as a message *in the report*.
 *
 * Exiting with a code above 1 would leave core logging a warning and then
 * treating the empty output as "no schema errors" -- a silent pass for a
 * document nothing actually checked.  A message on stdout is counted and
 * printed like any other, so the failure cannot be mistaken for success.
 */
function fail(message) {
  console.log(`${sourcePath}:1:1: error: the salve validator failed: ${message}`);
  process.exit(1);
}

/**
 * A salve grammar for the schema core asked us to use, compiled on first use
 * and cached beside this script.
 *
 * The grammar must come from the schema the CLI actually ships: the copy
 * bundled with `@pretextbook/schema` tracks the VS Code extension's schema,
 * which drifts from core's and then reports problems with valid documents.
 */
async function loadGrammarJson() {
  const cacheDir = new URL("grammars/", import.meta.url);
  const cacheFile = new URL(`${basename(schemaPath)}.json`, cacheDir);
  try {
    if (statSync(cacheFile).mtimeMs >= statSync(schemaPath).mtimeMs) {
      return readFileSync(cacheFile, "utf8");
    }
  } catch {
    // No cache yet (or it is older than the schema): compile below.
  }
  const { compileRngToJSON } = await import("@pretextbook/schema/compile");
  const { json } = await compileRngToJSON(schemaPath);
  try {
    mkdirSync(fileURLToPath(cacheDir), { recursive: true });
    writeFileSync(cacheFile, json);
  } catch {
    // A read-only install just means recompiling (~0.6s) on every run.
  }
  return json;
}

let validateDocument, loadGrammarFromJSON, grammarJson, source;
try {
  ({ validateDocument, loadGrammarFromJSON } = await import("@pretextbook/schema"));
} catch (e) {
  fail(`could not load @pretextbook/schema (${e}). Try \`pretext validate --engine salve\` again to reinstall it.`);
}
try {
  grammarJson = await loadGrammarJson();
} catch (e) {
  fail(`could not compile a grammar from ${schemaPath} (${e})`);
}
try {
  source = readFileSync(sourcePath, "utf8");
} catch (e) {
  fail(`could not read ${sourcePath} (${e})`);
}

const { diagnostics } = validateDocument(source, loadGrammarFromJSON(grammarJson), {
  uri: sourcePath,
  // Core hands over a single, already-assembled file and wants line numbers *of
  // that file*; both of these also keep the package from going out to disk.
  resolveXIncludes: false,
  readFile: () => undefined,
});

let count = 0;
for (const d of diagnostics) {
  if (d.code !== undefined && !SCHEMA_KINDS.has(String(d.code))) continue;
  // LSP positions are 0-based; jing's are 1-based.
  const line = d.range.start.line + 1;
  const column = d.range.start.character + 1;
  console.log(`${sourcePath}:${line}:${column}: error: ${d.message}`);
  count += 1;
}
process.exit(count > 0 ? 1 : 0);
