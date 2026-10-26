---
doc: checklist
status: approved
---

# Build Checklist

Build mode: learn

Repository and usage limits: Inspect Git status before each build slice and preserve all unrelated untracked work. Do not blanket-stage files. Ask before staging/committing, pushing, publishing, or making any request that could incur paid API usage. Do not modify or uninstall existing Python installations. Before installing dependencies, inspect supported Python/package versions and use a project virtual environment; prefer Python 3.11–3.13 if the pinned dependencies do not support the available Python 3.14. If no suitable interpreter is installed, stop and ask before installing another Python version.

## Slices

- [ ] **1. The local discount demo reproduces and repairs the known bug safely**
  Becomes usable: A Windows user can launch the Streamlit dashboard, see the baseline result (actual 80, expected 90), run the clearly labeled predefined repair in a fresh workspace copy, and see the fixed targeted test pass.
  Why now: This provides an end-to-end, no-key working demo early and establishes workspace, hash-preservation, fixed-test, timeout, and configuration boundaries before adding a remote model.
  PRD ref: `prd.md > The Core Journey` (steps 1-2, 4, 8), `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > Reset and Results`
  Spec ref: `spec.md > Where It Runs and How Someone Tries It`, `spec.md > Components`, `spec.md > Data Model`, `spec.md > Fixed Test Runner`, `spec.md > Demo Workspace Manager`, `spec.md > Predefined Repair`, `spec.md > Configuration`
  Build: First inspect Python interpreters and package metadata for Python 3.11–3.14 compatibility. Create a project virtual environment with a supported installed interpreter (prefer 3.11–3.13 if the pins do not support 3.14); do not alter existing installations. Scaffold the project and pinned dependencies; implement the built-in buggy fixture and targeted test, Streamlit first-use dashboard, configuration and secret-free `.env.example`, fresh demo copies, SHA-256 preservation checks, fixed no-shell pytest runner with controlled child environment and timeout, and predefined repair through JSON/AST validation. Add a Windows README with exact setup and launch commands.
  Verify (mechanical): Before installing, report interpreter/package compatibility and inspect which dependencies are already present; install only the approved project pins into the virtual environment. Add automated tests proving: baseline fails with actual 80 versus expected 90; predefined repair passes the fixed test; each attempt receives a fresh workspace; original fixture SHA-256 is unchanged before/after; nonzero targeted-test exit is failure; and `TimeoutExpired` is reported as timeout/failure. Also verify the fixed argv, `shell=False`, controlled child environment with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, missing Gemini key fallback, `.env` ignore status, and placeholder-only `.env.example`. Do not count a UI walkthrough alone as verification.
  Learner check: Launch the local dashboard, run the built-in repair without a Gemini key, and confirm the baseline failure, predefined-repair label, final test result, and original-source protection are clear.
  Commit: `Build safe local discount demo` (ask first; no commit without explicit permission)

- [ ] **2. Gemini can propose a constrained repair and PatchPilot validates it**
  Becomes usable: With a configured API key, PatchPilot makes a genuine Gemini request, displays the AI-generated proposal, accepts only the required JSON shape and AST allowlist, and verifies an accepted patch with the fixed test; rejected output is not written.
  Why now: This adds the project’s real AI capability after the fixed local workflow is independently usable, keeping provider and validation failures distinguishable from the deterministic fallback.
  PRD ref: `prd.md > The Core Journey` (steps 3 and 5), `prd.md > Built-In Discount Repair Workflow`, `prd.md > Clearly Labeled Predefined Fallback`
  Spec ref: `spec.md > Stack`, `spec.md > Gemini Provider`, `spec.md > Patch Validator`, `spec.md > External Services and Dependencies`, `spec.md > Important Failure Modes`, `spec.md > Testing Strategy`
  Build: Add the provider interface, repair service, real configured Gemini Interactions API adapter with the documented JSON schema and request timeout, strict JSON parsing, exact AST/file-boundary allowlist validation, and local diff. Keep API keys out of code, UI, and logs; keep the selected provider/model configurable. Do not enable model tools or accept model-supplied commands, paths, or environment changes.
  Verify (mechanical): Test strict parsing and accepted/rejected AST forms; verify invalid model output is never written and API timeouts/errors are classified as pre-patch generation failures. Use the real Gemini integration only when valid credentials are configured and the request is confirmed not to incur paid usage; otherwise do not call the API, test the missing-key/quota status and explicit fallback action, and state that genuine AI generation was not exercised. Label genuine AI output only when returned by Gemini. Never count a stubbed response as AI output or report an AI repair successful unless the actual fixed targeted test passes.
  Learner check: If real credentials are available, run one AI attempt and inspect its label, proposal, validation status, and test output; otherwise review the clearly labeled no-key fallback and its displayed reason.
  Commit: `Add constrained Gemini repair provider` (ask first; no commit without explicit permission)

- [ ] **3. Failed AI attempts remain visible and fallback/reset behave as approved**
  Becomes usable: A rejected, failed, or timed-out returned AI patch remains visible until the user chooses **Try Predefined Demo Repair**; that retry starts from the original in a fresh copy and retains the AI failure in the same workflow. **Reset Demo** clears transient history and starts a clean run.
  Why now: This completes the approved user-controlled recovery branches and tests that success, provenance, history, reset, and source preservation stay accurate across the complete journey.
  PRD ref: `prd.md > The Core Journey` (steps 5-8), `prd.md > Clearly Labeled Predefined Fallback`, `prd.md > Reset and Results`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Workflow Coordinator`, `spec.md > Streamlit Dashboard`, `spec.md > Data Model`, `spec.md > Important Failure Modes`, `spec.md > Testing Strategy`
  Build: Complete state handling and visible attempt history for rejected AI patches, failed verification, generation/test timeouts, and explicit predefined retry; make Reset Demo clear only the current workflow’s transient history and start a clean run; ensure source-hash mismatch blocks success. Add workflow-branch, session-state/history, workspace-preservation, configuration, and timeout tests.
  Verify (mechanical): Run all automated tests. Cover a rejected returned patch, a validated patch whose test fails, a test timeout, an API timeout before patch return, and an unavailable-model case. Assert no failure is silently replaced: pre-patch unavailability and returned rejected/failed/timed-out AI attempts remain visible until the user chooses the explicit predefined retry; retry uses a fresh copy of the original and retains the prior result in the same workflow; Reset Demo clears transient history; a changed source hash blocks success; and no timeout/failure is reported as success. Start the app and complete the built-in fallback workflow.
  Learner check: Try the local workflow, inspect how each attempt is labeled, confirm reset clears the previous result, and report anything confusing or missing.
  Commit: `Complete repair recovery and reset flow` (ask first; no commit without explicit permission)

## Hands-on Checkpoints

- [ ] Early usable behavior explored — after slice 1, run the no-key predefined end-to-end path and provide feedback before the Gemini path is added.
- [ ] Final kick-the-tires exploration and feedback completed — after slice 3, run the app, try the core workflow and reset, and report issues or changes.

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence: [what actually happened; real document/test/code references; unfinished work if interrupted]
Route and stops: [actual paths and symbols; guided stops completed, or reference-only route]
Edit outcome: [tried/kept/reverted/declined/not applicable; verification if changed]
Reflection: [offered/answered/declined/already covered — personal answer belongs only in the ignored profile]
Activity mode: [live app and editor, explicit static fallback, focused alternative, prior practice, or recap]

## Revisions

- 2026-10-27: The learner clarified that missing-key, unavailable-provider, and pre-response generation failures must be shown before the user chooses the predefined repair. Updated the PRD/spec and fallback verification criteria; no fallback is applied automatically.
