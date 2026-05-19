# Vision — Cycling Form & Performance Analyzer

## What This Is

A portfolio project that ingests indoor cycling video alongside a ride's telemetry file (FIT/TCX), extracts pedal-stroke pose metrics with computer vision, fuses them with power/speed/cadence/gear data and environmental inputs, and surfaces correlations like "knee-over-pedal-spindle drift correlates with power drop after minute 20." It's built for one user (the project owner), but designed to demonstrate end-to-end production thinking — pose estimation pipeline + GCP ML deployment + sport telemetry data engineering — as resume evidence for an endurance-sport performance role.

## Core Value

Given a video of a ride and its FIT file, produce explainable per-stroke pose-vs-telemetry correlations that a cyclist could plausibly act on. Everything else (auth, multi-user, fancy UI) is optional — the analytical insight is the product.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Ingest a single indoor-trainer cycling video and its matching FIT file
- [ ] Extract per-frame body-pose keypoints from the video (knee, hip, ankle, shoulder; both sides)
- [ ] Detect pedal strokes from video (cadence and stroke phase) without relying on the telemetry
- [ ] Parse FIT files into a normalized telemetry timeseries (power, speed, cadence, heart rate, gear inference, elapsed time)
- [ ] Fetch matching environmental data (temperature, humidity, wind for outdoor rides) and attach to telemetry
- [ ] Time-align video pose data with telemetry on a shared clock
- [ ] Compute per-stroke pose metrics: knee angle range, knee-over-pedal-spindle drift, hip rock, asymmetry left vs right
- [ ] Surface correlations between pose metrics and performance metrics over the ride
- [ ] Deploy the pose-inference step as a GCP service (Cloud Run or Vertex endpoint) callable from a pipeline
- [ ] Persist processed telemetry + pose features in a queryable store (BigQuery)
- [ ] Provide a minimal viewer (single-page web app or notebook dashboard) that renders the fused timeline and top correlations
- [ ] Ship a public repo + write-up that makes the demonstrated capabilities legible to a hiring manager

### Out of Scope

- Multi-user accounts and auth — single-user analytical tool; auth is portfolio noise
- Real-time/live analysis during a ride — batch-only post-ride processing
- Outdoor video pose estimation (helmet-cam, drone, follow-cam) — indoor trainer view only for v1
- Native mobile app — web/notebook viewer only
- Coaching prescriptions ("change your saddle height by X mm") — surface correlations, don't prescribe; avoids medical/safety claims
- Training a bespoke pose model — use off-the-shelf (MediaPipe / MoveNet / MMPose) and focus engineering effort on the pipeline
- Sport-mode beyond cycling (running, rowing, ski) — keep scope tight for v1
- Strava / TrainingPeaks integration — local file ingestion is enough to demonstrate the JD bullets

## Context

- **Why this project exists:** Originated from a job description's "nice-to-have" list — likely a cycling/endurance-sport performance role. The JD names four areas: (1) CS/Engineering background, (2) computer vision / pose estimation, (3) GCP-based ML workloads, (4) sport/performance telemetry (power/speed/gear, environmental). This project is designed so each area maps to a concrete, demonstrable component.
- **Owner:** Solo developer building a portfolio piece. Working dir was empty as of project initialization on 2026-05-20.
- **Constraints implied by the JD:** Resume-legibility matters as much as technical depth. A finished, end-to-end thin slice beats a half-built deep specialization.
- **Telemetry note:** "Gear" is rarely directly recorded by power meters. It's typically inferred from cadence/speed ratio when wheel size is known. v1 will compute gear inference from cadence + speed; if a Di2/AXS gear-position file is available, prefer it.
- **Pose-estimation note:** Off-the-shelf 2D pose models (MediaPipe Pose, MoveNet Thunder, MMPose) are accurate enough for indoor-trainer side-on bike-fit metrics. Switching to a custom model adds risk without proportional value for v1.

## Constraints

- **Tech stack — pose:** Off-the-shelf 2D pose estimator (MediaPipe Pose or MoveNet Thunder) — chosen for accuracy/speed tradeoff and zero model-training cost
- **Tech stack — telemetry:** Python with `fitparse` (or equivalent) for FIT parsing — standard library for cycling FIT files
- **Tech stack — storage/compute:** Google Cloud Platform — Cloud Run for stateless inference, BigQuery for telemetry storage, Cloud Storage for video/FIT artifacts — directly maps to the "GCP-based ML workloads" JD bullet
- **Tech stack — language:** Python end-to-end — keeps pose + telemetry + GCP client code in one stack
- **Budget:** GCP free tier and small spend (target: under $20/month total). No GPU instances for v1; CPU inference acceptable for batch
- **Timeline:** Designed for ~4-8 weekends of focused work; favor end-to-end thin slice over deep specialization
- **Portfolio:** All work in a public repo; commits, README, and a short write-up are part of the deliverable

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Indoor-trainer video only for v1 | Side-on view gives clean pose; eliminates outdoor camera-rig complexity | — Pending |
| Off-the-shelf pose model, no training | Demonstrating pipeline integration is the JD-relevant skill; custom model would dilute focus | — Pending |
| GCP, not AWS or local-only | JD explicitly names GCP — concrete cloud talking points beat generic ones | — Pending |
| Cycling specifically (not running/rowing) | "Power/speed/gear telemetry" in the JD is a strong cycling signal; FIT-file ecosystem is mature | — Pending |
| Batch processing, not real-time | Cuts streaming/realtime complexity; analysis quality matters more than latency for this JD | — Pending |
| Surface correlations, do not prescribe | Avoid medical/safety claims; keeps the output honest and defensible | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-20 after initialization*
