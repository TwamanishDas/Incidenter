# Collaboration Awareness (Step-by-Step Mode)

## Why this file exists

This file captures how the user wants to work going forward, so future sessions stay aligned.

## User preference (important)

- Do **not** push to production right now.
- Current focus is early phases (Phase 1 data foundation done; more phases pending).
- User is new to app development and needs **step-by-step guidance**.
- Keep explanations simple, practical, and incremental.
- Complete MVP first, then discuss versioning and release flow.
- Avoid heavy production architecture discussions unless explicitly requested.
- For every future step/phase execution, explicitly state:
  - `Phase`
  - `Step`
  - `Version/Tag` currently being worked on

## Working style to follow

1. Explain one step at a time.
2. For each step, provide:
   - Goal
   - Exact action
   - How to verify
   - What to do next
3. Avoid large “big bang” plans unless asked.
4. Use beginner-friendly language and examples.
5. Confirm completion of each step before moving ahead.

## Delivery plan (high level)

### Stage A: Finish MVP cleanly
- Confirm MVP feature checklist.
- Validate ingestion + incidents + scheduler behavior end-to-end.
- Fix only MVP-blocking defects.
- Add basic tests for current functionality.
- Freeze MVP scope.

### Stage B: Versioning basics (after MVP)
- Introduce simple semantic versioning:
  - `v0.x` for MVP iterations
  - `v1.0.0` when stable production-ready baseline exists
- Create release notes template.
- Tag code versions in git with clear change summaries.

### Stage C: Pre-production hardening (later)
- Persistence, security, reliability, observability, CI/CD.
- Staging validation and controlled rollout strategy.

## Immediate next-session behavior

When a session starts:
1. Start from current MVP status.
2. Propose only the next smallest task.
3. Help finish that task fully before introducing the next one.
4. In every execution update, include a short header like:
   - `Working: Phase <X> | Step <Y> | Version <Z>`

---

Maintainer note: This is a collaboration preference file, not a technical spec.
