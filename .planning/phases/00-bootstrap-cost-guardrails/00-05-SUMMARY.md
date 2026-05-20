---
phase: 00-bootstrap-cost-guardrails
plan: 05
subsystem: docs
tags: [docs, filming, cv, pose, fiducial, fps, cfr, tripod, bb-height, lighting, mediapipe]

# Dependency graph
requires:
  - phase: 00-bootstrap-cost-guardrails
    provides: Repo + docs layout from plans 00-01..00-03 (no direct file deps; this plan only adds docs/filming-protocol.md)
provides:
  - "docs/filming-protocol.md — one-pager that locks the four hard invariants every downstream pose stage assumes (BB-height ±2 cm, fiducial in frame, ≥60 fps CFR, tripod-only)"
  - "Canonical ffprobe post-record CFR-detection command (r_frame_rate vs avg_frame_rate must be byte-equal) referenced from later phases as the VFR-rejection gate"
  - "Lighting + Auto-FPS-disable instructions (iPhone / Android) — operationalizes the 'CFR mandatory' lock so the operator can satisfy it from the camera UI in <60 s"
affects:
  - "01-local-thin-slice (Phase 1 ingestion ING-03 — the ffprobe gate must use the exact substring from this doc; the filming-protocol-bad-examples.md companion doc is created in Phase 1 once real fixture rides exist per D-17)"
  - "02-containerize (Phase 2 pose) — every joint-angle metric assumes the filming-protocol geometry; this doc is the authority"
  - "ROADMAP Phase 0 success criterion #4 (filming-protocol.md exists with the four locks)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Documentation-as-contract: every downstream-dependent geometric assumption is captured in a single small file (≤120 lines) that the operator reads in 60 s before each shoot, and that later code (ING-03 / Phase 1 ingestion) can mechanically reference"
    - "Per-lock pitfall citation: each hard lock carries a one-sentence 'why' referencing Pitfall #1 or Pitfall #8 — makes the lock self-justifying for a hiring-manager reader"
    - "ASCII diagram inside a fenced code block (no language tag) — keeps the doc renderable in any markdown viewer + greppable + diffable; PNG upgrade deferred to Phase 6 visual polish if ever"

key-files:
  created:
    - "docs/filming-protocol.md"
  modified: []

key-decisions:
  - "Kept ASCII (not PNG) per D-15..D-17 + Claude's Discretion section — diff-able, renderable in any markdown viewer, zero binary churn in the repo; PNG upgrade is deferred to Phase 6 visual polish if hiring-manager feedback requests it"
  - "Added an iPhone + Android Auto-FPS-disable subsection beyond the bare D-15 ask — the 'CFR mandatory' lock is unactionable without it (Rule 2: missing critical operator instructions to satisfy a stated lock)"
  - "Promoted 'even lighting verified on preview' to checklist item #6 (vs. only living in the lighting paragraph) — the operator's last action before pressing record is a phone-preview check, and visibility at the joints is what MediaPipe will or will not resolve"
  - "Used ChArUco/AprilTag OR plumb-line+ruler as acceptable fiducials (not a single mandated marker) — both have the same drift-detection property (>2 px → reject), and constraining the operator to one specific marker is over-prescriptive at this stage"

patterns-established:
  - "Hard-lock format: numbered list with bold lock name + one-sentence 'why' in italics citing the relevant pitfall — every downstream protocol doc should mirror this"
  - "Six-item pre-shot checklist as the operator's UI for the protocol — the doc IS the checklist; everything else is justification"
  - "Post-record ffprobe verification as the canonical CFR/VFR gate, with the exact command string reusable verbatim by ING-03 in Phase 1"

requirements-completed: [BOOT-05]

# Metrics
duration: 6min
completed: 2026-05-20
---

# Phase 0 Plan 05: Filming Protocol Summary

**Operator-facing one-page filming protocol locking the four hard invariants (camera at BB height ±2 cm, fiducial visible in frame, ≥60 fps CFR, tripod-only) that every downstream pose-extraction and joint-angle metric in Phase 1+ assumes — with a labeled ASCII side-view, six-item phone-preview checklist, iPhone + Android Auto-FPS-disable instructions, and a canonical ffprobe post-record CFR gate.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-20T14:08:30Z (approximate)
- **Completed:** 2026-05-20T14:14:00Z
- **Tasks:** 1
- **Files modified:** 1 (created)
- **Final line count:** 89 lines (within the 50–120 D-15 concise-one-pager band)

## Accomplishments

- `docs/filming-protocol.md` shipped at the documented path — Phase 0 ROADMAP success criterion #4 satisfied.
- All four hard locks present with per-lock pitfall citation: BB height ±2 cm (Pitfall #1), fiducial visible (Pitfall #1), ≥60 fps CFR (Pitfall #8), tripod-only (Pitfall #1).
- 25-line labeled ASCII side-view diagram inside a fenced code block (no language tag), showing tripod + camera lens at BB height, rider on indoor trainer, fiducial on wall, ~2–3 m camera-to-bike distance.
- Six-item pre-shot checklist (exactly six `[ ]` markers) the operator runs through the phone preview before pressing record: tripod at BB height, fiducial visible, side-on angle, full TDC↔BDC visible, 60 fps CFR confirmed, even lighting verified.
- iPhone (Settings → Camera → Record Video → uncheck "Auto Low Light FPS" / "Auto FPS") + Android (Camera settings → Video → uncheck "Auto FPS" / "Smart FPS" / "Auto frame rate"; disable Samsung "Super Steady") Auto-FPS-disable instructions — the operator-actionable half of the "CFR mandatory" lock.
- Lighting paragraph: 5000 K diffuse LED preferred, backlit forbidden, preview-confirm visibility at hip/knee/ankle through a full stroke before committing the take.
- Tripod-only mandate subsection — handheld and propped-against-a-chair both explicitly forbidden; if a tripod is unavailable, the shoot defers.
- Canonical post-record verification: `ffprobe -v error -show_streams -select_streams v:0 <file>.mp4 | grep -E 'r_frame_rate|avg_frame_rate|nb_frames|duration'` with the requirement that `r_frame_rate == avg_frame_rate` (both `60/1`) — Phase 1 ING-03 will reuse this exact command as the VFR rejection gate.
- References footer points to Pitfalls #1 and #8 in `.planning/research/PITFALLS.md` and to D-15..D-17 in `00-CONTEXT.md`; bad-examples doc explicitly noted as deferred to Phase 1 per D-17.

## Task Commits

1. **Task 1: Write `docs/filming-protocol.md` (one-pager + ASCII side-view diagram + checklist)** — `bc6fd65` (docs)

Plan metadata commit will be added after this SUMMARY is written.

## Files Created/Modified

- `docs/filming-protocol.md` (89 lines, created)
  - Title + one-paragraph WHY (pitfall-anchored)
  - `## The four hard locks` — numbered list, bold lock name, italics rationale citing Pitfall #1 or #8
  - `### Disabling Auto / Variable FPS` — iPhone + Android operator-actionable instructions
  - `## Side-view ASCII diagram` — 25-line fenced code block with labeled tripod, camera, BB, rider, fiducial, wall, floor, distance, legend
  - `## Pre-shot checklist (six items)` — exactly six `[ ]` markers, runnable from phone preview
  - `## Lighting` — single paragraph; 5000 K LED; backlit forbidden; preview-verify joint visibility
  - `## Tripod-only mandate` — explicit handheld/propped forbidden; defer the session if no tripod
  - `## Verification after recording (3 quick checks)` — ffprobe r_frame_rate vs avg_frame_rate; fiducial-still scrub; TDC/BDC in-frame
  - `## References` — Pitfall #1 / #8 / D-15..D-17; bad-examples deferred-to-Phase-1 note

## Decisions Made

- **ASCII over PNG.** D-15..D-17 + Claude's Discretion explicitly permit either; ASCII is diff-able, greppable, renderable everywhere, and avoids binary churn in the repo. PNG upgrade is deferred to Phase 6 visual polish if hiring-manager feedback ever asks.
- **iPhone + Android Auto-FPS-disable steps added beyond the bare D-15 spec.** The "CFR mandatory" lock is unactionable without per-platform instructions — the operator has to know which toggle to uncheck before each shoot. Treated as Rule 2 (missing critical operator instructions); see Deviations.
- **Lighting verification promoted to checklist item #6.** The last thing the operator does before pressing record is a phone-preview check; visibility at the joints (hip / knee / ankle) is precisely what MediaPipe will or will not resolve. Putting visibility in the checklist (vs. only in the lighting paragraph) makes the lock enforceable at shoot time, not after.
- **ChArUco/AprilTag OR plumb-line+ruler as acceptable fiducials.** Both satisfy the >2 px drift detection property; constraining the operator to one specific marker is over-prescriptive when both work. Phase 1 fiducial-tracking code will need to handle both shapes anyway.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical] Added iPhone + Android Auto-FPS-disable subsection**

- **Found during:** Task 1 (Section 2, the "four hard locks" subsection — specifically the CFR mandate)
- **Issue:** The plan's `<action>` step states the CFR lock as `"iPhone/Android default video is often VFR and silently varies between 24–60fps"` but provides no operator-actionable steps to disable Auto FPS on either platform. Without those steps, the lock is unenforceable from the operator's UI — they would record what they think is CFR and only discover at the ffprobe verification step that the clip is unusable. This is precisely Rule 2 (missing critical operator instructions for a stated correctness lock).
- **Fix:** Added a `### Disabling Auto / Variable FPS` subsection with exact menu paths:
  - iPhone: Settings → Camera → Record Video → uncheck "Auto Low Light FPS" (and "Auto FPS" on iOS 16+); set to 1080p HD or 4K at 60 fps; do NOT use Cinematic mode (forces VFR + shallow DoF).
  - Android (generic + Samsung + Pixel): Camera app → settings → Video → uncheck "Auto FPS" / "Smart FPS" / "Auto frame rate"; on Samsung also disable "Super Steady" (re-encodes to VFR).
- **Files modified:** `docs/filming-protocol.md`
- **Verification:** Both subsections present; checklist item #5 references them by section title; ffprobe gate in Section 6 catches the case where the operator forgot to disable.
- **Committed in:** `bc6fd65` (part of Task 1 commit)

**2. [Rule 2 — Missing Critical] Promoted "even lighting verified on preview" to checklist item #6**

- **Found during:** Task 1 (Section 4 — pre-shot checklist)
- **Issue:** The plan's checklist as written ends at item 6 = "rider fully in frame at TDC and BDC". Lighting only lives in Section 5 as a paragraph. But the user's task instructions in the execution prompt explicitly ask for "even lighting" as the 6th checklist item — and operationally, the lighting paragraph is something the operator reads once and forgets; a checklist item is something they execute every shoot. Without lighting in the checklist, the lock is unenforced at shoot time.
- **Fix:** Replaced the plan's "rider fully in frame at TDC/BDC" item #6 with "even lighting verified on preview" (item #6) and consolidated the TDC/BDC framing check into item #4 ("Full TDC ↔ BDC visible. Pedal a quick test stroke and verify…"). All six required checklist items per the execution prompt (tripod at BB height, fiducial visible, side-on angle, full TDC↔BDC visible, 60 fps CFR, even lighting) are now present in that order. Plan acceptance criterion `[ ] count == 6` is unaffected (still exactly 6).
- **Files modified:** `docs/filming-protocol.md`
- **Verification:** `grep -c '\[ \]' docs/filming-protocol.md` returns 6; checklist items 1–6 align with the execution prompt's required ordering.
- **Committed in:** `bc6fd65` (part of Task 1 commit)

**3. [Rule 2 — Missing Critical] Added "Tripod-only mandate" as its own H2 subsection**

- **Found during:** Task 1 (after Section 5 lighting)
- **Issue:** The execution prompt's required-content #6 calls for a "Tripod-only mandate — handheld forbidden" subsection. The plan's `<action>` Section 2 already covers tripod-only as hard-lock #4, but a standalone H2 ensures it is greppable and visually prominent — operators skim H2 headers, not bullet items in a wall of locks.
- **Fix:** Added a dedicated `## Tripod-only mandate` H2 after the lighting paragraph stating: handheld forbidden, propped-against-a-chair forbidden, 1 mm drift over 60 min destroys stationarity, defer the session if no tripod.
- **Files modified:** `docs/filming-protocol.md`
- **Verification:** Header is present; `grep -Fi 'tripod'` returns multiple hits including the dedicated H2.
- **Committed in:** `bc6fd65` (part of Task 1 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 2 — missing critical operator instructions for stated locks)
**Impact on plan:** All three auto-fixes operationalize locks that the plan stated but did not make actionable for the operator. None of them expand scope beyond D-15..D-17 + the execution prompt's required-content list. The doc is still inside the 50–120 line band (89 lines).

## Issues Encountered

None beyond the deviations above. The plan's verification regex set passed on the first run without re-edits:

- Line count = 89 (in [50, 120]) ✓
- `BB height` present (3 hits) ✓
- `60 fps` / `60fps` present (case-insensitive, multiple hits) ✓
- `CFR` / `constant frame rate` present (case-insensitive, multiple hits) ✓
- `tripod` present (multiple hits including dedicated H2) ✓
- `fiducial` present (multiple hits) ✓
- `5000` present (lighting paragraph) ✓
- `ffprobe` present (Section 6 verification) ✓
- `TDC` + `BDC` present (lock #3 rationale + diagram caption + checklist item #4) ✓
- Checklist `[ ]` count = 6 (exactly) ✓
- Fenced code block ≥5 lines (25 lines in the ASCII diagram block) ✓

## User Setup Required

None — this plan only authors a documentation file. The operator will USE the protocol when capturing Phase 1 fixture rides (the ≥3-rides STATE.md TODO), but no environment configuration is required to ship the doc itself.

## Self-Check

- File check: `[ -f docs/filming-protocol.md ]` → FOUND (89 lines)
- Commit check: `git log --oneline | grep bc6fd65` → FOUND (`docs(00-05): add filming protocol one-pager locking BB-height, fiducial, 60fps CFR, tripod`)
- Plan verify command: all 11 substring + structural checks pass (line count, BB height, 60fps, CFR, tripod, fiducial, 5000, ffprobe, TDC, BDC, six `[ ]`).
- Execution-prompt acceptance criteria: all five required greps (60 fps, CFR, BB height, tripod, fiducial — case-insensitive) pass; ≥1 fenced code block with ≥5 lines (25 lines actual) present; ≥2 `## ` headers (8 actual) present.

## Self-Check: PASSED

## Next Phase Readiness

- `docs/filming-protocol.md` is the load-bearing reference for Phase 1 (local thin slice / ingestion). The exact ffprobe command in Section 6 is what ING-03 must call as its VFR-rejection gate — re-use the substring verbatim to keep the doc-and-code contract auditable.
- Phase 1 will create the deferred companion `docs/filming-protocol-bad-examples.md` (per D-17) when the first ≥3 fixture rides exist (STATE.md TODO #1). At that point, annotated bad frames go in the companion doc; this protocol doc stays the canonical "what to do" reference.
- Phase 0 success criterion #4 is now met. The remaining Phase 0 plans (00-04 bootstrap-gcp.sh, 00-06 README skeleton, 00-07 operator-run kill-switch test) are unblocked by this plan.

---
*Phase: 00-bootstrap-cost-guardrails*
*Completed: 2026-05-20*
