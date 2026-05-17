// Equivalence test for the per-turn auto-log.
//
// Two layers:
//   1) Pure-function tests for extractTurnText() over synthetic
//      AgentMessage[] arrays — covers user-only, mixed thinking+text,
//      tool calls between text, multi-assistant-message turns.
//   2) Integration: with DOTTY_BRAIN_DB_SNAPSHOT set, formatTurnLog +
//      storeMemory against a tmp copy must produce a row byte-identical
//      to what bridge.py /api/voice/memory_log would have written for
//      the same (now, id, user, assistant).

import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import Database from "better-sqlite3";

import { storeMemory, _resetForTests } from "../src/lib/brain_db.ts";
import {
  extractTurnText,
  formatTurnLog,
} from "../src/lib/turn_logger.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ORACLE = join(__dirname, "turn_log_oracle.py");

let failures = 0;

function assertEq(label: string, actual: unknown, expected: unknown): void {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a === e) {
    process.stdout.write(`  PASS  ${label}\n`);
    return;
  }
  process.stderr.write(
    `  FAIL  ${label}\n        expected: ${e}\n        actual:   ${a}\n`,
  );
  failures++;
}

// ---------------------------------------------------------------------
// Layer 1: extractTurnText() over synthetic AgentMessage[] shapes.
// ---------------------------------------------------------------------

function txt(text: string) {
  return { type: "text", text };
}
function think(thinking: string) {
  return { type: "thinking", thinking };
}
function toolCall(name: string) {
  return { type: "toolCall", id: "x", name, arguments: {} };
}
function userMsg(content: any) {
  return { role: "user", content, timestamp: 1 };
}
function assistantMsg(content: any[]) {
  return { role: "assistant", content, timestamp: 2 };
}

function testExtract(): void {
  process.stdout.write("Layer 1: extractTurnText\n");

  assertEq(
    "user string content + plain assistant text",
    extractTurnText([
      userMsg("Hi Dotty"),
      assistantMsg([txt("😊 Hello!")]),
    ]),
    { user: "Hi Dotty", assistant: "😊 Hello!" },
  );

  assertEq(
    "user content as array of TextContent",
    extractTurnText([
      userMsg([txt("What's "), txt("the weather?")]),
      assistantMsg([txt("Sunny.")]),
    ]),
    { user: "What's the weather?", assistant: "Sunny." },
  );

  assertEq(
    "skips thinking + toolCall, keeps text",
    extractTurnText([
      userMsg("Tell me about the cat"),
      assistantMsg([
        think("user wants cat info"),
        toolCall("memory_lookup"),
        txt("The cat is "),
        txt("called Mittens."),
      ]),
    ]),
    { user: "Tell me about the cat", assistant: "The cat is called Mittens." },
  );

  assertEq(
    "multiple assistant messages after user are concatenated",
    extractTurnText([
      userMsg("Story please"),
      assistantMsg([txt("Once upon a time")]),
      // a hypothetical second assistant message in the same prompt
      assistantMsg([txt(" — the end.")]),
    ]),
    { user: "Story please", assistant: "Once upon a time — the end." },
  );

  assertEq(
    "only the LAST user message in the transcript is logged",
    extractTurnText([
      userMsg("first prompt"),
      assistantMsg([txt("first reply")]),
      userMsg("second prompt"),
      assistantMsg([txt("second reply")]),
    ]),
    { user: "second prompt", assistant: "second reply" },
  );

  assertEq(
    "empty transcript",
    extractTurnText([]),
    { user: "", assistant: "" },
  );

  assertEq(
    "user with no assistant reply yet",
    extractTurnText([userMsg("ping")]),
    { user: "ping", assistant: "" },
  );

  assertEq(
    "assistant-only content (no user) returns empty",
    extractTurnText([assistantMsg([txt("hello?")])]),
    { user: "", assistant: "" },
  );
}

// ---------------------------------------------------------------------
// Layer 2: formatTurnLog + storeMemory round-trip vs Python oracle.
// ---------------------------------------------------------------------

interface OracleResult {
  ok: boolean;
  row?: {
    id: string;
    key: string;
    content: string;
    category: string;
    namespace: string;
    importance: number;
    created_at: string;
    updated_at: string;
    session_id: string | null;
  };
}

function callOracle(
  db: string,
  now: string,
  id: string,
  user: string,
  assistant: string,
): OracleResult {
  const out = execFileSync(
    "python3",
    [ORACLE, db, now, id, user, assistant],
    { encoding: "utf8" },
  );
  return JSON.parse(out.trim()) as OracleResult;
}

function readBack(dbPath: string, id: string) {
  const db = new Database(dbPath, { readonly: true, fileMustExist: true });
  try {
    return db.prepare(`
      SELECT id, key, content, category, namespace,
             importance, created_at, updated_at, session_id
      FROM memories WHERE id = ?
    `).get(id);
  } finally {
    db.close();
  }
}

interface IntegrationCase {
  label: string;
  user: string;
  assistant: string;
}

const INTEGRATION_CASES: IntegrationCase[] = [
  { label: "short_turn", user: "Hi Dotty", assistant: "😊 Hello there!" },
  {
    label: "trim_both_sides",
    user: "   hi   ",
    assistant: "   reply   ",
  },
  {
    label: "user_over_500_truncated",
    user: "u".repeat(600),
    assistant: "ok",
  },
  {
    label: "assistant_over_1000_truncated",
    user: "tell me a story",
    assistant: "a".repeat(1200),
  },
  {
    label: "assistant_empty_user_only",
    user: "hello",
    assistant: "",
  },
  {
    label: "emoji_codepoint_boundary_assistant",
    user: "emoji test",
    // 600 emoji codepoints = 1200 UTF-16 units. Python [:1000] keeps
    // 1000 codepoints; JS .slice(0,1000) splits a surrogate pair.
    assistant: "😊".repeat(600),
  },
];

function makeId(label: string): string {
  const hash = Buffer.from(label).toString("hex").padEnd(12, "0").slice(0, 12);
  return `aaaaaaaa-bbbb-4ccc-9ddd-${hash}`;
}

function makeNow(label: string): string {
  return `2026-05-18T01:00:00.${label.length.toString().padStart(3, "0")}Z`;
}

function testIntegration(snapshot: string): void {
  for (const c of INTEGRATION_CASES) {
    process.stdout.write(`\nCase: ${c.label}\n`);
    const tmp = mkdtempSync(join(tmpdir(), `dotty-turnlog-${c.label}-`));
    const tsDb = join(tmp, "ts.db");
    const oracleDb = join(tmp, "oracle.db");
    copyFileSync(snapshot, tsDb);
    copyFileSync(snapshot, oracleDb);
    try {
      const id = makeId(c.label);
      const now = makeNow(c.label);

      const content = formatTurnLog(c.user, c.assistant);
      _resetForTests();
      const ok = storeMemory({
        content,
        category: "conversation",
        namespace: "voice",
        importance: 0.3,
        sessionId: null,
        dbPath: tsDb,
        _now: now,
        _id: id,
      });
      _resetForTests();
      assertEq(`${c.label} storeMemory returned`, ok, true);

      const tsRow = readBack(tsDb, id);
      const oracle = callOracle(oracleDb, now, id, c.user, c.assistant);
      assertEq(`${c.label} oracle.ok`, oracle.ok, true);
      assertEq(`${c.label} row equality`, tsRow, oracle.row ?? null);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  }
}

function main(): void {
  // Layer 1 runs unconditionally — no db required.
  testExtract();

  const snapshot = process.env.DOTTY_BRAIN_DB_SNAPSHOT;
  if (!snapshot || !existsSync(snapshot)) {
    process.stdout.write(
      "\nLayer 2 SKIPPED (set DOTTY_BRAIN_DB_SNAPSHOT for the integration pass).\n",
    );
  } else {
    process.stdout.write(`\nLayer 2 snapshot: ${snapshot}\n`);
    testIntegration(snapshot);
  }

  process.stdout.write(`\n${failures === 0 ? "OK" : "FAIL"} — ${failures} failure(s)\n`);
  process.exit(failures === 0 ? 0 : 1);
}

main();
