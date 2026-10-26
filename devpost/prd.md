---
doc: prd
status: approved
---

# PatchPilot — Product Requirements

PatchPilot is a local, single-dashboard tool for Python developers and QA automation engineers to inspect and verify one AI-assisted repair of a built-in Python bug.
Source: `scope.md > Who It's For`, `scope.md > The Unique Kernel`.

## The Core Journey

1. The user opens the PatchPilot dashboard and sees the built-in discount example: a 10% discount applied twice, making a price of 100 return 80 instead of the expected 90.
2. The user selects **Repair Demo Bug**. PatchPilot runs the baseline targeted test and displays the actual failure (actual `80`, expected `90`). The workflow shows the stages: Baseline Test, Analyze Bug, Propose Repair, Validate Patch, Apply to Demo Copy, and Verify with Tests.
3. If a real model is configured and returns a usable repair, PatchPilot labels it **AI-Generated**, shows the proposed change, checks that it stays within the allowed file and patch boundaries, applies it only to the controlled demo copy, and runs the targeted test.
4. If real-model access is not configured or unavailable, or generation fails before returning a patch, PatchPilot displays the reason and offers **Try Predefined Demo Repair**. It applies the predefined repair only after the user selects that action, labels it **Predefined Demo Repair — Not AI-Generated**, and runs the targeted test in a fresh demo copy.
5. If an AI-generated patch is returned but patch-boundary validation rejects it, PatchPilot labels it **AI-Generated — Patch Rejected**, displays the reason, does not apply it, and offers **Try Predefined Demo Repair** as a separate action. It does not switch automatically after an AI patch has been attempted.
6. If a boundary-valid AI-generated repair fails verification, PatchPilot labels it **AI-Generated — Verification Failed**, shows the actual failure, and keeps that attempt visible. If the targeted test times out, PatchPilot labels it **AI-Generated — Verification Failed (Test Timed Out)** and displays the timeout. Other verification failures follow the same explicit, user-controlled fallback rule.
7. If the user selects **Try Predefined Demo Repair**, PatchPilot creates or resets a demo copy from the original buggy source, labels the repair **Predefined Demo Repair — Not AI-Generated**, validates and applies it only to that copy, then reruns the targeted test with the configured timeout. The original AI attempt and its failure remain visible in the result history.
8. PatchPilot shows the actual targeted-test result. It reports a repair as passing only when that test actually passes. The user can reset the demo and run the example again. The original source remains unchanged.

Source: `scope.md > The Core Loop`, `scope.md > What "Working" Looks Like`, `scope.md > The POC Boundary`.

Any unavailable-provider result, returned patch-validation failure, or verification failure remains visible in the current workflow. Never convert it silently into a predefined-repair success. The user must choose **Try Predefined Demo Repair**; that action starts from a fresh or reset copy of the original buggy source and keeps the prior failure visible in the result history.

## Screens and Layout

The MVP has one dashboard with minimal navigation:

- Header: **PatchPilot — AI-Powered Python Bug Repair** and the description “Find, fix, and verify Python bugs in a controlled workspace.”
- Example panel: the discount scenario, sample function description, input `100`, expected result `90`, and **Repair Demo Bug** as the primary action. No project upload is required.
- Workflow indicator: the six stages listed in the core journey, each showing its current state, completion, or failure/timeout.
- Results area: original test failure, repair source label, proposed code change, patch-validation result, and actual final test output. The visible result history records exact provenance and reason per attempt: model unavailability or generation timeout before a patch is returned; an AI-generated patch that is rejected, fails verification, or times out; and any separately selected predefined repair. Keep each outcome distinct and preserve the AI attempt when a fallback follows.
- **Reset Demo** action: restores a clean demo copy so the example can be run again.

The happy path starts with one action. The optional predefined retry after an AI verification failure takes one additional action.

Source: `scope.md > What "Working" Looks Like`, `scope.md > The POC Boundary`.

## Look and Feel

Clean, professional, and polished, with minimal navigation, readable code blocks, and clear status indicators. Keep errors and repair-source labels prominent and understandable. No specific color palette or font has been chosen.

## Features and Behavior

### Built-In Discount Repair Workflow

- The only MVP example is a deterministic discount-calculation bug: for input price `100`, the buggy function returns `80`; the expected result is `90`.
- **Repair Demo Bug** starts the baseline test and then the repair workflow. Show progress and a visible status for every stage.
- Display the baseline test's actual result before the repair. Do not imply the baseline passes.
- When real AI produces a usable patch, label it **AI-Generated** and show the proposed change. Apply it only after patch-boundary validation succeeds, and only to the controlled demo copy.
- Patch-boundary validation checks that the patch stays within the permitted demo file and change boundaries. Passing that check permits the patch to proceed; it does not establish correctness.
- Run the selected targeted test after applying the patch to the demo copy. Display the real test result and output. A passing targeted test is evidence for this example, not a guarantee that the repair is universally correct.
- Keep the original source unchanged throughout the workflow.

### Clearly Labeled Predefined Fallback

- If a real model is not configured or unavailable, or generation fails before returning a patch, explain the reason and offer **Try Predefined Demo Repair**. Do not apply the predefined repair until the user selects it.
- Show the exact label **Predefined Demo Repair — Not AI-Generated**. Never describe or imply that this predefined repair came from an AI model.
- Validate and apply the fallback only to the controlled demo copy, then run the targeted test and display its actual result.
- If a boundary-valid AI-generated patch is applied but the targeted test fails, do not automatically replace that result. Show **AI-Generated — Verification Failed**, preserve the failure in the visible history, and offer **Try Predefined Demo Repair** as a separate action.
- If an AI-generated patch fails patch-boundary validation, show **AI-Generated — Patch Rejected**, explain why, do not apply it, and offer **Try Predefined Demo Repair** separately. Do not switch automatically after an AI patch has been returned.
- If the targeted test times out after an AI patch, show **AI-Generated — Verification Failed (Test Timed Out)** and display the timeout. Never count it as success. Keep the AI attempt visible and offer **Try Predefined Demo Repair** separately. Other verification failures follow the same user-controlled fallback rule.
- If the user chooses that action, use a fresh or reset demo copy for the predefined repair, show its exact label, and display the actual targeted-test result. Report success only if that test passes.
- The predefined repair is limited to the built-in discount example. It is not a repair path for arbitrary user-supplied code.

### Reset and Results

- **Reset Demo** returns the built-in example and demo copy to their starting state for another run.
- Show original failure, repair provenance, proposed patch, validation outcome, and actual targeted-test outcome in the results area.
- Do not replace a failed AI result in the history when the user later runs the predefined repair.

Source: `scope.md > The Unique Kernel`, `scope.md > What "Working" Looks Like`, `scope.md > The POC Boundary`.

## States and Boundaries

- **First use** — show the built-in example and the single primary action; do not require an upload, account, or GitHub authentication.
- **Baseline failure** — show actual `80` versus expected `90` from the targeted test.
- **Running** — show the current workflow stage; run only the selected targeted test with a configured time limit.
- **AI generation unavailable before a patch is returned** — explain whether the model was not configured, unavailable, or generation timed out; offer the clearly labeled predefined repair as a user action.
- **Provenance and reason history** — for each attempt, distinguish model unavailability or generation timeout before a patch is returned from an AI-generated patch that is rejected or fails verification. Preserve the precise reason and repair source label; never merge a failed AI attempt into the fallback result.
- **AI repair verified** — show **AI-Generated**, the validated patch, and the actual passing targeted-test result.
- **AI repair fails verification** — show **AI-Generated — Verification Failed**, the actual test failure, and keep it visible. Offer the separate predefined-repair action; do not switch automatically.
- **AI patch rejected** — show **AI-Generated — Patch Rejected**, display the patch-boundary failure, do not apply it, and offer the predefined repair as a separate user action.
- **AI test timeout** — show the exact label **AI-Generated — Verification Failed (Test Timed Out)** and display the timeout. Keep the AI attempt visible, never count it as success, and offer **Try Predefined Demo Repair** as a separate user action.
- **Other AI verification failure** — keep the actual failure visible with the AI attempt and offer the predefined repair as a separate user action. Never switch modes automatically after an AI patch has been attempted.
- **Predefined repair** — show **Predefined Demo Repair — Not AI-Generated**, validate and apply within the demo boundaries, then show the actual test result.
- **Test failure or timeout** — show the actual failure or timeout state and output available; do not report success. The configured time limit and exact execution controls are technical-spec decisions.
- **Reset** — restore a clean demo copy. Original source stays unchanged, and a previous AI verification failure remains visible if a predefined retry follows it.
- **Access and scope** — no arbitrary project upload, production-repository edits, deployment, or GitHub authentication in the MVP. The predefined fallback handles only the built-in discount bug.

Source: `scope.md > The POC Boundary`, `scope.md > Explicitly Cut`.

## Product Decisions

- The MVP uses one built-in discount bug: `100` should produce `90`, but the buggy version produces `80`. This keeps the example deterministic and understandable in a demo under two minutes.
- The first-use action is **Repair Demo Bug**; users do not upload a project for this MVP.
- Real AI repair is used when configured and usable. If model access is unavailable or generation fails before returning a patch, PatchPilot explains why and waits for the user to choose the clearly labeled predefined repair.
- Provider unavailability before a patch is returned and failures after an AI patch is returned all stay visible. The predefined fallback is never applied automatically; the user chooses it, and it starts from a fresh or reset copy of the original buggy source.
- The predefined repair is explicitly labeled, limited to the built-in bug, and never represented as AI-generated.
- Actual test outcomes determine success; a patch-validation pass or a generated patch alone is not success.
- A clean, professional, minimal dashboard with readable code and clear stage/status indicators is preferred.
- The local demo must not require paid services, GitHub authentication, or an uploaded repository.

## What We're Building

One dashboard and one repeatable workflow for the built-in discount bug: show the baseline failure, generate or clearly fall back to a repair, validate patch boundaries, apply only to a demo copy, run the targeted test, show provenance and actual results, and allow reset. Keep the original source unchanged and preserve AI test failures when a user separately tries the predefined repair.

## Deferred From the POC

- Arbitrary user project or repository input — the MVP proves one built-in example and its safety/verification path.
- Additional bug types, functions, or test suites — they are not needed to demonstrate this repair workflow.
- Multi-run history beyond the current workflow and its optional AI-failure/predefined-retry result — persistent history is not needed for a local demo.

## Possible Later Enhancements

Support additional small Python examples and broader project inputs after the controlled, single-example workflow has been proven. Consider richer repair history and reporting if users need to compare multiple attempts.

## Non-Goals

- Editing real or production repositories — edits stay in the controlled demo copy.
- Claiming every repair is correct — only the targeted test result is reported, as evidence for this example.
- Hiding or relabeling predefined repairs as AI-generated — provenance remains explicit.
- Deployment or mandatory paid model access — local demonstration and the labeled predefined fallback keep the MVP usable.

## Open Questions

- Which practical free real-model option, if any, fits the local demo? Resolve in `4-spec`; the labeled fallback keeps the product workflow demonstrable if real-model access is unavailable.
- What exact time limit and process boundary should the selected targeted-test run use? Resolve in `4-spec` before implementation.
