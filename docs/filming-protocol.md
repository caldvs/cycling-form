# Filming Protocol for Vision

This protocol locks the geometry every downstream pose-and-correlation
stage depends on. The four hard invariants (camera at BB height, fiducial
in frame, 60fps, constant frame rate, tripod) are non-negotiable. A clip
that violates any of them is thrown out — re-shoot, do not "fix it in
post." Pitfall #1 (camera-rig sloppiness) and Pitfall #8 (FPS aliasing
and Variable Frame Rate) are why this document exists.

## The four hard locks

1. **Camera height = bottom-bracket (BB) height ±2 cm.** Mounted on a tripod, lens dead-level (not tilted up or down). _Why: a tilted camera introduces non-uniform foreshortening across the pedal stroke that biases hip + knee angles per-frame (Pitfall #1)._
2. **Fiducial visible in frame at all times.** A flat object of known dimension (printed ChArUco / AprilTag marker, OR a plumb-line + ruler) taped to the wall behind the trainer, in-plane with the drive-side crank, visible in every frame. _Why: if the fiducial drifts >2 px across the clip, the camera moved and every angle is wrong (Pitfall #1)._
3. **≥60 fps capture, constant frame rate (CFR), never VFR.** Use the device's "Cinematic" or "Manual 60fps" mode. _Why: at 80–95 rpm cadence, 30 fps aliases with the stroke rate and undercounts TDC/BDC; VFR breaks the time alignment between video frames and FIT records (Pitfall #8)._
4. **Tripod only — no handheld, no propped-against-a-chair.** Even a 1 mm camera drift over 60 minutes destroys the stationarity assumption. _Why: every downstream KOPS measurement is computed in camera-pixel space and assumes the camera is fixed (Pitfall #1)._

### Disabling Auto / Variable FPS

CFR is the default-OFF on most phones. Disable Auto FPS / Smart FPS before every shoot:

- **iPhone:** Settings → Camera → Record Video → uncheck **"Auto Low Light FPS"** (and **"Auto FPS"** on iOS 16+ where present). Then set Record Video to **1080p HD at 60 fps** (or **4K at 60 fps**). Do NOT use Cinematic mode (it forces VFR + shallow depth-of-field).
- **Android (Samsung / Pixel / generic):** Camera app → settings (gear icon) → Video → uncheck **"Auto FPS"** / **"Smart FPS"** / **"Auto frame rate"** (label varies by vendor). Set resolution to **FHD 1080p @ 60 fps**. On Samsung, also disable **"Super Steady"** (re-encodes to VFR).

After recording, verify CFR at ingest (see Section 6).

## Side-view ASCII diagram

```
                                  wall
                                   |
                                   |  ╔═══════╗
                                   |  ║ ←─────╫─── fiducial
                                   |  ║       ║   (plumb-line OR
                                   |  ║       ║    AprilTag marker)
                                   |  ╚═══════╝
                                   |
          tripod                   |
          ┌──────┐                 |              rider on
          │ cam  │═══════════════  | ◯ ←─── BB    indoor trainer
          │ ↕    │   level horiz.  | ╱ ╲          (side-on)
          └──────┘                 |╱   ╲
              │   ↑                |
              │   │                |
              │   │ camera lens = BB height ±2 cm
              │   │
              │   ▼
            ═════════════════ floor ═════════════════
              ↑                                       ↑
              └──────── ~2–3 m distance ──────────────┘
              (rider fully in frame from helmet to ankle at BDC)

LEGEND:  ◯ = bottom bracket   ↕ = camera adjustable height
         ║ = wall-mounted fiducial behind the rider
```

> Distance camera-to-bike is ~2–3 m so the rider's helmet (at peak of stroke) and the ankle (at BDC, full extension) both stay inside the frame. Use a 35 mm-equivalent or wider focal length — phones default to ~26 mm-equivalent on the main lens, which is fine.

## Pre-shot checklist (six items)

Run through these in the phone preview **before** pressing record:

1. [ ] **Tripod set at BB height.** Measure with a tape from the floor to the bottom-bracket centre; match the lens centre to within ±2 cm. (Handheld is forbidden — tripod only.)
2. [ ] **Fiducial visible in preview.** ChArUco / AprilTag / plumb-line + ruler, taped to the wall behind the trainer, in-plane with the drive-side crank, fully visible at TDC and BDC.
3. [ ] **Side-on angle.** Camera lens dead-level (phone grid + level overlay reads centred); rider perpendicular to the camera axis (no yaw — the drive-side crank arm should appear as a line, not a wedge, at 3-o'clock).
4. [ ] **Full TDC ↔ BDC visible.** Pedal a quick test stroke and verify the helmet (peak of stroke) and the ankle (full extension at BDC) both stay inside the frame.
5. [ ] **60 fps CFR confirmed.** Frame rate set to 60 fps (or 120 fps if conditions allow); Auto FPS / Smart FPS / Auto Low Light FPS DISABLED (see "Disabling Auto / Variable FPS" above).
6. [ ] **Even lighting verified on preview.** No backlight blowout behind the rider; no harsh shadow across the drive-side leg; pose-relevant joints (hip, knee, ankle) clearly resolved in the preview image.

## Lighting

Prefer diffuse 5000 K (daylight) LED from the camera side; avoid backlit setups (a window or bright light behind the rider washes out the rider silhouette and confuses MediaPipe's edge detection). A single ceiling LED panel above and slightly behind the camera is the cheapest acceptable setup. Mixed-temperature lighting (warm bedside lamp + cool window) is fine but reduces pose-estimator visibility scores at the joint extremes — verify on the phone preview that the drive-side hip, knee, and ankle remain visually distinct from the background through a full stroke before committing the take.

## Tripod-only mandate

Handheld is forbidden. A propped-against-a-chair or propped-on-a-box camera is forbidden. A 1 mm drift over a 60-minute ride destroys the stationarity assumption every downstream KOPS / hip-rock / asymmetry metric depends on. If a tripod is unavailable, the shoot does not happen — defer the session.

## Verification after recording (3 quick checks)

- Run `ffprobe -v error -show_streams -select_streams v:0 <file>.mp4 | grep -E 'r_frame_rate|avg_frame_rate|nb_frames|duration'`. The `r_frame_rate` and `avg_frame_rate` MUST be identical (e.g., both `60/1`). If they differ, the clip is VFR — reject it (Pitfall #8).
- Scrub the timeline by hand. The fiducial should be stationary frame-to-frame. If it drifts laterally, the tripod settled; throw the clip out (Pitfall #1).
- At TDC and BDC, the rider should be fully in frame. If the helmet or ankle clips out, re-frame and re-shoot.

## References

- `.planning/research/PITFALLS.md` §Pitfall #1 (camera-rig sloppiness)
- `.planning/research/PITFALLS.md` §Pitfall #8 (FPS aliasing + VFR)
- `.planning/phases/00-bootstrap-cost-guardrails/00-CONTEXT.md` §D-15..D-17

> NOTE: Bad-example annotated frames are explicitly NOT part of this document (D-17 defers them to Phase 1 when real fixture rides exist).
