#!/usr/bin/env node
// PreToolUse guard: impide commits fuera de un hito estable del harness.
// Se dispara solo en Bash(git commit *). Multiplataforma (Node, sin dependencias).
//
// Deniega si: hay un requerimiento activo y el estado no es DOCUMENTATION/DONE,
// o seguridad está bloqueada, o las pruebas no pasan, o se intenta --no-verify.
// Permite si no hay estado de harness (commit manual normal).

import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const deny = (reason) => {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: reason,
      },
    })
  );
  process.exit(0);
};

const allow = () => process.exit(0);

let input = "";
try {
  input = readFileSync(0, "utf8");
} catch {
  allow();
}

let payload = {};
try {
  payload = JSON.parse(input || "{}");
} catch {
  allow();
}

const cmd = payload?.tool_input?.command ?? "";
if (!/\bgit\b[\s\S]*\bcommit\b/.test(cmd)) allow();

if (/--no-verify|(^|\s)-n(\s|$)/.test(cmd)) {
  deny("git commit --no-verify está prohibido por .claude/rules/git.md.");
}

const root = process.env.CLAUDE_PROJECT_DIR || payload.cwd || process.cwd();
const statePath = join(root, ".harness", "state.json");

if (!existsSync(statePath)) allow(); // sin harness activo: commit manual normal

let state;
try {
  state = JSON.parse(readFileSync(statePath, "utf8"));
} catch {
  allow();
}

const s = state.state;
const terminal = ["DONE", "BLOCKED", "HALTED_CYCLE_LIMIT"];
if (terminal.includes(s) && s !== "DONE") allow(); // requerimiento cerrado sin éxito: el humano decide

const commitable = ["DOCUMENTATION", "DONE"];
if (!commitable.includes(s)) {
  deny(
    `Harness en estado ${s}. Solo se commitea en DOCUMENTATION o DONE ` +
      `(HARNESS.md §7). Ejecuta /next hasta cerrar el ciclo.`
  );
}

if (state.security === "blocked") {
  deny("Hay hallazgos de seguridad critical/high abiertos. Ciérralos antes de commitear.");
}

if (state.tests && state.tests !== "pass") {
  deny(`Pruebas en estado "${state.tests}". Nunca se commitea con la suite en rojo (.claude/rules/git.md).`);
}

allow();
