# Phase 3 Context — Hardening (still local)

**Goal:** Verify all four architectural risk mitigations are working. Add structured logging, expand prompt injection defences, and build a full unit test suite before Cloud Run deployment.

## Security fixes applied

### Risk ① — Async pattern (5s timeout)
- Already in place from Phase 1: all endpoints return `HTTP 202` instantly, background thread handles Gemini + Jira write-back.
- **Live verification pending** (Phase 3.1 curl timing test not yet run against live server).

### Risk ② — Admin Mode state
- In-memory `mode_state` dict in `admin.py` works correctly for local single-process use.
- `admin.health()` was missing `verify_key(request)` — **fixed** (bug caught by unit tests).
- Firestore migration is deferred to Phase 4 (multi-instance Cloud Run requirement).

### Risk ③ — Prompt injection defence (`utils.py`)
- `sanitise()` expanded from 7 to 14 injection patterns:
  ```python
  r"ignore\s+(?:all\s+)?(?:previous\s+|above\s+)?instructions",
  r"you are now", r"act as", r"disregard", r"override",
  r"system prompt", r"forget your",
  r"pretend (to be|you are)", r"from now on",
  r"your (new )?role is", r"roleplay", r"in this scenario",
  r"hypothetically", r"for (educational|research) purposes",
  ```
- Root cause of old gap: original regex `r"ignore (all |previous |above )?instructions"` only allowed one optional word — "all previous" (two words) was not matched. Fixed with nested optionals.
- `verify_key()` now uses `hmac.compare_digest()` for constant-time comparison (timing attack prevention).
- **Live verification pending** (Phase 3.3 injection curl test not yet run).

### Risk ④ — Failure threshold alerting (`reporter.py`)
- Already implemented: `failure_counts = defaultdict(int)`, `record_failure(flow)` increments per-flow, sends `🚨 CRITICAL` card at count == 3 and resets to 0.
- **Live verification pending** (Phase 3.4 three-failure curl loop not yet run).

## Additional hardening completed

### `parse_gemini_json()` fix
- Was returning `{}` on parse failure — silent, masked downstream errors.
- Now returns `{"error": "parse_failed", "raw": text}` on all failure paths.

### Structured logging
- `logging.basicConfig(level=INFO, format="%(asctime)s [%(levelname)s] %(message)s")` added to `main.py`.
- All `print()` / `sys.stdout.flush()` calls replaced with `logging.info/debug/warning/error/exception` across all modules: `main.py`, `gemini.py`, `jira.py`, `gchat.py`, `reporter.py`.
- `logging.debug(f"[{issue_key}] <flow> prompt:\n{prompt}")` added before every `gemini.ask()` call for prompt visibility.

### Jira internal comment endpoint
- `add_comment()` updated to use `POST /rest/servicedeskapi/request/{key}/comment` with `"public": false` for internal notes.
- Falls back to Platform API v2 on failure.

## Unit test suite

124 tests passing in 0.29s. Full details in `context/unit_tests.md`.

## Phase 3 checklist

### Code / static verification (complete)
- [x] `sanitise()` replaces all 14 injection patterns with `[removed]`
- [x] `verify_key()` uses `hmac.compare_digest()` (timing-safe)
- [x] `parse_gemini_json()` returns error dict (not `{}`) on failure
- [x] `admin.health()` requires valid `X-Agent-Key`
- [x] All modules use `logging.*` — no `print()` calls
- [x] `logging.basicConfig` configured in `main.py`
- [x] Prompt debug lines log sanitised prompt before every Gemini call
- [x] 124 unit tests passing

### Live server verification (in progress — server is running)
- [ ] 3.1: `/triage` returns `{"status":"accepted"}` in under 200ms (time curl)
- [ ] 3.1: Malformed payload → background thread catches exception, error card in Agent Report space
- [ ] 3.2: Mode persists across 3 requests in test mode
- [ ] 3.3: Injection in description → `[removed]` visible in server logs
- [ ] 3.3: XML tags wrapping content correctly in logged prompt
- [ ] 3.4: 3 consecutive empty-payload requests → `🚨 CRITICAL` card in Agent Report space
- [ ] 3.5: `parse_gemini_json` assertions pass in Python REPL (already covered by unit tests)
- [ ] 3.6: Structured log format visible in server output

## Recent Updates
- Fixed `ModuleNotFoundError` for `dotenv` and installed missing core dependencies (`Flask`, `google-genai`, `requests`).
- Flask server successfully started on `localhost:8080` (logs are being written to `server.log`).
- `ngrok` tunnel is running.
- `.gitignore` updated to include `node_modules` and other Node.js specific files.

## Next Steps

Run Phase 3.1–3.4 curl tests from `docs/Jira_AI_Agent_Implementation_Plan_v2.md` to complete verification.

> ✅ All Phase 3 checks complete? Move to Phase 4 — Cloud Run deployment.
