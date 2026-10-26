---
doc: scope
status: approved
---

# PatchPilot

PatchPilot is a small AI-assisted Python bug-repair demo that takes one known failing example through a proposed patch and a test result.

## The Unique Kernel
PatchPilot makes a repair inspectable and bounded: it shows the original failure, a candidate AI repair, patch validation, and the verification result, while applying changes only to a controlled demo copy.

## Who It's For
Python developers and QA automation engineers who spend time reproducing bugs, investigating failed tests, and correcting small defects. Beginners and people debugging unfamiliar code can find the manual reproduce, inspect, edit, and rerun cycle especially repetitive.

## The Core Loop
The user supplies a small Python example with a reproducible bug. PatchPilot analyzes the example and failure, proposes a repair using a real AI model when configured, validates and applies the patch in a controlled demo workspace, runs the relevant tests, and reports whether the repair passed.

## Inspiration & Identity
No visual references or aesthetic direction have been chosen. The experience should make the repair and its evidence understandable; detailed presentation choices belong in the PRD.

## Why This Matters to the Learner
The learner wants to build a small, working MVP and learn how to build AI applications and integrate AI models, while using their QA testing experience in a real end-to-end example.

## What "Working" Looks Like
A short demo starts with one deliberately buggy Python function and its automated test. The baseline run fails; PatchPilot shows and validates a proposed repair, applies it only in the demo workspace, reruns the targeted test within a configured time limit, and reports pass or failure. Patch validation checks that the change stays within the allowed file and patch boundaries. A passing targeted test is evidence that the repair works for this example, not a guarantee of correctness. An invalid patch, test failure, or timeout is reported as unverified or failed. The original source remains unchanged. Any predefined or mock repair must be clearly identified as such; it must not be presented as AI-generated.

## The POC Boundary
Build and demonstrate one complete workflow around one deliberately buggy Python function and its targeted automated test. Preserve the original source, restrict edits to a controlled demo workspace, and run only the selected test command with a configured time limit. Make the pass or fail result visible. Use a real model for the repair when a practical free setup is feasible. If real-model access is unavailable, the end-to-end workflow must still be demonstrable with a clearly labeled predefined or mock repair; never describe that repair as AI-generated.

## Later
Broader project support, more bug types and test suites, and a more complete user experience can follow after this single workflow is proven.

## Explicitly Cut
- Autonomous edits to real or production repositories: the MVP is limited to a controlled demo workspace.
- Deployment: the workflow can be demonstrated locally and deployment is not needed to prove it.
- A guarantee that every proposed repair is correct: the tool reports verification evidence, including failure.
