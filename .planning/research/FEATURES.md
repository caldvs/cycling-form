# Feature Research

**Domain:** Cycling form & performance analyzer — single-user, batch, indoor-trainer video + FIT telemetry, portfolio-grade
**Researched:** 2026-05-20
**Confidence:** HIGH on what commercial/research tools do; MEDIUM on which specific subset best signals "competence" to the target hiring manager (no JD text in context, only PROJECT.md's four-area mapping)

## Orientation: Three Audiences This Feature List Serves

This is not a generic feature inventory. Because the project is a portfolio piece, every feature is judged on three axes:

1. **Analytical legitimacy** — Does it produce a metric a coach/biomechanist would recognize?
2. **JD-bullet evidence** — Does it map to one of the four areas (CS, pose estimation, GCP ML, performance telemetry)?
3. **Resume legibility** — Can it be summarized in one bullet a non-technical hiring manager can read?

A feature that scores high on (1) but low on (2) and (3) (e.g. a beautiful saddle-pressure visualization without saddle-pressure data) is a trap. Conversely, "deployed pose inference on Cloud Run" hits (2) and (3) but only counts as (1) if the pose actually drives an insight downstream.

## Feature Landscape

### Table Stakes (Required for the JD Bullets to be Credibly Demonstrated)

These are non-negotiable: without them, the project either fails to demonstrate one of the four JD areas, or the analytical output is not credible.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Ingest single video + FIT file from local path** | Without ingestion the pipeline can't start. Single-user means no upload UI needed | LOW | Read video file (mp4/mov), parse FIT with `fitparse`. Validate basic preconditions (video has frames, FIT has records) and fail loudly otherwise |
| **Parse FIT to normalized timeseries (timestamp, power, cadence, speed, HR)** | "Sport/performance telemetry" JD bullet. Standard cycling data fields | LOW | `fitparse` is the de-facto Python library. Output a pandas DataFrame indexed by timestamp. Handle missing fields gracefully (HR optional, power optional) |
| **2D pose keypoint extraction per frame (knee, hip, ankle, shoulder, both sides)** | "Computer vision / pose estimation" JD bullet. Side-on indoor trainer is the easy case where 2D works | MEDIUM | MediaPipe Pose or MoveNet Thunder. MediaPipe Pose returns 33 landmarks including all needed joints. Run frame-by-frame, persist as parquet/csv |
| **Knee angle per frame (left + right)** | Single most-cited bike-fit metric in literature. Holmes method (25–30° at BDC static), 33–43° dynamic, max-extension 140–150°. If the project doesn't compute this it has failed the bike-fit credibility test | LOW | Angle between hip-knee and knee-ankle vectors. Trivial once keypoints exist |
| **Pedal stroke segmentation from video (no telemetry)** | Required by PROJECT.md ("without relying on the telemetry"). Demonstrates real CV work beyond library-call wrapping | MEDIUM | Detect ankle y-position oscillation, or track ankle/foot through its cyclic path. FFT or peak-detection on ankle vertical position. Each stroke = TDC→TDC interval. Validates that pose keypoints are usable signal, not just per-frame snapshots |
| **Video↔telemetry time alignment** | Without it, none of the correlations are meaningful. FIT records at 1Hz, video at 30/60fps — they need a shared clock | MEDIUM | Cross-correlate video-derived cadence against FIT cadence to find offset. Fallback: manual clapboard/marker frame. This is a non-trivial signal-processing problem and a good talking point |
| **Knee-over-pedal-spindle (KOPS) drift per stroke** | Named explicitly in PROJECT.md core value example. Classic bike-fit metric | LOW | At BDC frame (or forward-pedal frame), measure horizontal offset of knee from pedal/foot. Plot drift across the ride |
| **Hip rock / pelvis lateral travel** | Headline Retul/Leomo metric. Indicates saddle-too-high or core fatigue | MEDIUM | Track hip-keypoint y-position (or shoulder-to-hip vertical line) per stroke; compute peak-to-peak amplitude. Side-on view sees vertical hip rock but only limited lateral rock — note this limitation honestly |
| **Left/right asymmetry on knee angle and stroke timing** | Asymmetry is a standard pedaling metric (TrainingPeaks/WKO, Leomo DSS). Symmetry is what cyclists tune for | LOW | Compare per-stroke knee-angle range left vs right; report % difference. Note ANT+ power balance from FIT if available (most cycling power meters report this) |
| **Per-stroke aggregation (avg knee angle, avg power, avg cadence per stroke)** | The unit of analysis is the stroke, not the second. Without this, "per-stroke correlations" in the project's core value isn't real | MEDIUM | After alignment, group telemetry samples and pose frames by stroke index. Output one row per stroke |
| **Gear inference from cadence + speed** | Explicit PROJECT.md requirement and a smart-engineer signal. Formula is well-known: gear ratio = speed × 60 / (cadence × wheel circumference) | LOW | Compute ratio per record; cluster to discrete gears (k-means or rolling-mode). Indoor trainers complicate this (virtual speed) — be honest about applicability |
| **Persist processed data in BigQuery** | "GCP ML workloads" JD bullet. BigQuery is the obvious analytics store on GCP | LOW | One table per ride or partitioned by ride_id: telemetry, pose_frames, pose_strokes, correlations. Loadable via `pandas-gbq` or `google-cloud-bigquery` |
| **Pose inference deployed as Cloud Run service** | Explicit PROJECT.md requirement; "GCP ML workloads" JD bullet. The deployed-service story matters more than raw model accuracy | MEDIUM | Containerized FastAPI/Flask app wrapping MediaPipe. Input: video URL in GCS; output: keypoints written to GCS. Cloud Run handles autoscale-to-zero (fits budget) |
| **Correlation surfacing (top N pose-metric × telemetry-metric correlations)** | The PROJECT.md core value. Without this the project is a pipeline that produces graphs, not an analyzer | MEDIUM | Pearson/Spearman across per-stroke series; rank by \|r\|; threshold by sample size. Display "knee angle range drifted +8° while power dropped 12%" with confidence intervals |
| **Single-page web viewer or notebook dashboard** | Explicit PROJECT.md requirement. Hiring managers click before they read | MEDIUM | Streamlit or a Plotly Dash notebook are appropriate. Render: fused timeline (power, cadence, knee angle synced), top correlations list, a frame strip showing pose overlay |
| **Public README that maps JD bullets → code** | "Resume-legibility matters as much as technical depth" (PROJECT.md). Without this the work is invisible | LOW | A table in README: "Computer vision → src/pose/, GCP ML → infra/cloud_run/, …" with screenshots from the viewer |

### Differentiators (Resume-Impressiveness Beyond "I Followed a Tutorial")

These are where the project distinguishes itself from a generic pose-estimation portfolio. None are individually required; choose 2–4 to fully implement, mention others in the README as future work to show awareness without spending budget.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Temporal pose smoothing with One-Euro or Kalman filter** | Raw MediaPipe is jittery; smoothing is what separates demo code from production-thinking. Cheap signal of CV maturity | LOW | One-Euro filter has a clean Python implementation. Apply per-keypoint, configurable cutoff. Mention in README |
| **Confidence-weighted keypoint usage (drop low-conf frames, interpolate)** | Honest handling of pose-estimator uncertainty. Hiring managers in performance roles care about data quality | LOW | MediaPipe gives per-landmark visibility/presence. Threshold + linear interpolation. Surface "X% of frames had degraded pose quality" in the viewer |
| **Auto-detect side of bike (left/right facing) and rider region** | Removes a manual config step; demonstrates CV judgment (use hip-knee-ankle x-distribution to infer facing) | LOW | Run pose on first N frames, check median x-direction of foot relative to hip |
| **Bottom-Dead-Center / Top-Dead-Center detection per stroke** | Lets metrics be reported at biomechanically meaningful crank positions (industry-standard reference points). All commercial systems do this | MEDIUM | Detect via ankle/foot extremum y-positions, or crank tracking if visible. Use BDC frame for knee-angle-at-BDC and KOPS measurements |
| **Aerobic decoupling / efficiency factor (EF) calculation** | Adds a respected coaching metric (Friel, TrainingPeaks). Ties pose drift to a known performance index | LOW | EF = NP / avg HR per half. Compare halves. Already in TrainingPeaks/Athletica — fluent inclusion signals domain literacy |
| **Pedaling smoothness and torque effectiveness from FIT** | These are ANT+ standard fields many power meters record. Reading them shows you read the FIT spec, not just the basic fields | LOW | `fitparse` exposes these. Display when present, gracefully skip when absent |
| **Power-balance left/right from FIT cross-checked against pose-derived asymmetry** | Genuinely novel insight: "your power meter says 51/49 but your knee mechanics show 8° asymmetry." Two-source validation is a senior-engineer move | MEDIUM | Requires both pose asymmetry and FIT `left_right_balance`. Plot together |
| **Fatigue/form-drift detection (rolling-window metric drift over ride duration)** | Directly executes PROJECT.md's headline example: "knee drift correlates with power drop after minute 20." Research shows hip ROM decreases at MAP, knee power drops with fatigue — there is real signal here | MEDIUM | Rolling 5-min window of knee-angle range, KOPS, power. Detect breakpoints (PELT/ruptures library). Surface "form transition at minute 22" |
| **Environmental data fusion (temperature/humidity/wind via Open-Meteo)** | Explicit PROJECT.md requirement. For indoor-trainer rides the value is honest reporting ("indoor — env data not applied"); for outdoor rides via FIT GPS, attach historical weather | LOW | Open-Meteo historical-forecast API is free, no key required. For indoor v1 this is mostly a "feature is ready, no data to apply" line item — acknowledge honestly in viewer |
| **Annotated frame export (knee angle overlay, KOPS line, pose skeleton) at key strokes** | The visual that goes on the README/LinkedIn post. One screenshot does more recruiter work than a paragraph | LOW | OpenCV overlay on selected frames (peak power stroke, BDC frames, pre/post fatigue). Save as PNG to GCS, link in viewer |
| **CI/CD pipeline: GitHub Actions → Cloud Run deployment** | Demonstrates deploy-ops competence, not just dev. "GCP ML workloads" is broader than "I made an endpoint once" | MEDIUM | gcloud auth via workload identity federation, `gcloud run deploy` on merge to main. Worth one commit |
| **Reproducibility: pinned model versions + deterministic processing run-IDs** | Performance-science roles care about reproducibility (it's an academic-coded signal). Most portfolio projects skip this | LOW | Hash model weights; emit a run-manifest with input file hashes, library versions, model SHA. Store alongside outputs in BigQuery |
| **Per-stroke pose-overlay strip in the viewer (mini video frames stitched)** | Visceral demonstration that pose extraction worked. Recruiters scroll, they don't read | MEDIUM | Sample N frames per stroke, draw skeleton, lay out as a sprite strip. Streamlit can render this |
| **Sensitivity analysis: how much would knee angle change with +1cm saddle height?** | Goes beyond "here's a number" to "here's a number with bounds." Demonstrates statistical thinking | MEDIUM | Use a simple inverse-kinematics approximation, or Monte-Carlo perturbation of leg-length estimates. Don't oversell — frame as "approximate" |
| **Short written analysis (1–2 pages) of one real ride** | The narrative writeup is the part most portfolio projects skip and the one a hiring manager will most quote. Combines all features into a story | MEDIUM | A markdown doc in `/analysis/ride-01.md` reading like a coach's note: setup, observations, three findings with figures, limitations |

### Anti-Features (Deliberately Not Built for v1)

These are commonly-requested or obvious-seeming features that should be explicitly excluded. Each one carries either scope-creep risk, credibility risk, or both.

| Feature | Why Tempting | Why Don't Build | Alternative |
|---------|--------------|-----------------|-------------|
| **Coaching prescriptions ("raise saddle 5mm")** | The natural-feeling next step from a correlation | Crosses into medical/safety-claim territory; one bad prescription becomes a liability story. PROJECT.md explicitly rules this out | Surface the observation, let a human fitter act |
| **Multi-user accounts, auth, profiles** | "Real apps have users" instinct | Single-user is the project's purpose; auth is portfolio noise; doubles infra complexity (IAM, sessions, RBAC) for zero JD-bullet gain | Single local user; explicitly call out in README |
| **Real-time / live analysis during a ride** | Resume word "real-time" feels impressive | Adds streaming/latency complexity for zero gain on the four JD areas. Batch is what GCP excels at for ML on video | Batch-only, post-ride. The README states the streaming-extension path |
| **Training a custom pose model** | "I trained a CNN" sounds harder than "I called MediaPipe" | PROJECT.md explicitly rules out. Off-the-shelf is accurate enough for indoor side-on. Custom adds weeks for marginal gain | Use MediaPipe Pose / MoveNet Thunder. Discuss tradeoffs in README |
| **Outdoor video pose (helmet-cam, follow-cam, drone)** | More general = more impressive | View angles vary wildly outdoors; 2D pose breaks; massively expands scope. PROJECT.md rules out | Indoor side-on trainer only. Outdoor framing is "future work" |
| **Sport-mode beyond cycling (running, rowing, ski)** | Reusability is a software-architecture virtue | Each sport has different telemetry conventions, body mechanics, view angles. Diluting focus loses the cycling-domain-credibility signal | Cycling-only. Mention extensibility in architecture but don't build it |
| **Strava / TrainingPeaks API integration** | "It integrates with real services" | OAuth, rate limits, terms-of-service — high effort, marginal demo value. PROJECT.md rules out | Local file ingestion. Briefly note that a Strava activity-stream adapter would be straightforward |
| **Native mobile app or PWA** | Bike content lives on phones | UI is not the JD evaluation surface. A solid notebook or Streamlit page beats a half-built mobile app | Web/notebook viewer only |
| **3D pose estimation** | "3D" sounds harder than "2D" | Requires multi-view rig or monocular-3D models with high uncertainty; doesn't materially improve bike-fit metrics on side-on indoor view | 2D is the right tool. Mention 3D as future work; cite that Retul's 3D requires a hardware sensor bar |
| **Saddle-pressure mapping / IMU integration** | Industry tools (gebioMized, Leomo) have these | Requires hardware the user doesn't have. Faking it loses credibility | Acknowledge in the writeup that vision-only is one of three measurement modalities (vision/pressure/IMU) and document where vision is and isn't sufficient |
| **Generic computer-vision capabilities (face detection, object tracking, segmentation overlays)** | Easy MediaPipe wins to fill the page | Distracts from the bike-fit story. Hiring manager doesn't care that you can detect faces | Stay narrow: pose + cycling biomechanics |
| **Database UI / admin panel** | Common in dev portfolios | Single-user; BigQuery itself is the UI for ad-hoc inspection | Use BigQuery web console or `bq` CLI |
| **Generic "AI coach" LLM commentary on the ride** | LLM features are trendy | Adds a hallucination-risk feature that undercuts the rigor signal. PROJECT.md's "surface, do not prescribe" applies here too | A short hand-written analysis writeup is more credible |
| **Multi-camera or 360 video support** | More cameras = better data | Hardware unrealistic; multi-view fusion is its own research area | Single side-on camera. Document the limitation honestly |
| **Custom React/Vue dashboard from scratch** | Looks more impressive than Streamlit | Weeks of CSS for marginal narrative gain. Hiring manager values the analysis, not the framework choice | Streamlit, Plotly Dash, or a Jupyter notebook with widgets. README explains the choice |
| **General-purpose pose-quality benchmark / model comparison study** | Looks rigorous | Easy to spend a week comparing MediaPipe vs MoveNet vs MMPose and produce nothing actionable. Out of project scope | Pick one (MediaPipe Pose), justify in two README sentences, move on |

## Feature Categories

Grouping for the requirements/roadmap downstream consumer:

### A. Ingestion (table stakes)
- Local file path → video + FIT pair
- Validate inputs (frames exist, FIT records exist, durations approximately match)
- Upload to GCS for the Cloud Run pipeline to read

### B. Pose Extraction (table stakes + key differentiators)
- Per-frame 2D keypoints (MediaPipe Pose)
- **(diff)** Temporal smoothing (One-Euro filter)
- **(diff)** Confidence-weighted use / low-conf interpolation
- **(diff)** Auto-detect bike-side facing
- Persist as parquet to GCS

### C. Telemetry Parsing (table stakes + small diff)
- FIT → normalized DataFrame (power, cadence, speed, HR, time)
- Gear inference from cadence/speed (table stakes)
- **(diff)** Pedaling smoothness, torque effectiveness, L/R balance when present
- **(diff)** Environmental data fetch (Open-Meteo) — gracefully no-op for indoor

### D. Time Alignment (table stakes)
- Detect cadence from video (ankle/foot oscillation FFT)
- Cross-correlate with FIT cadence to derive offset
- Resample both to a common per-stroke index

### E. Per-Stroke Metrics (table stakes + diff)
- Pedal stroke segmentation from video alone
- Knee angle (instantaneous, per-stroke range, max extension)
- KOPS drift at BDC
- Hip rock amplitude
- Left/right asymmetry
- **(diff)** BDC/TDC detection
- **(diff)** Per-stroke aggregated telemetry (power, cadence, HR)

### F. Correlations (table stakes + diff)
- Pearson/Spearman pose × telemetry, ranked
- Sample-size and confidence thresholds
- **(diff)** Rolling-window fatigue detection
- **(diff)** Aerobic decoupling / EF
- **(diff)** Sensitivity / Monte-Carlo perturbation

### G. Storage (table stakes + diff)
- BigQuery: rides, telemetry, pose_frames, pose_strokes, correlations
- GCS: raw video, raw FIT, derived parquet, annotated frame PNGs
- **(diff)** Run manifest (input hashes, model SHA, lib versions) per analysis run

### H. Viewer / Dashboard (table stakes + diff)
- Fused timeline (power, cadence, knee angle on shared x-axis)
- Top correlations list with effect-size labels
- Per-stroke metric distributions
- **(diff)** Annotated frame strip / sprite of selected strokes
- **(diff)** Side-by-side pre/post fatigue frame comparison

### I. GCP Deployment (table stakes + diff)
- Pose inference on Cloud Run (containerized)
- BigQuery sink for processed data
- GCS for artifacts
- **(diff)** GitHub Actions CI/CD to Cloud Run

### J. Documentation / Portfolio (table stakes + diff)
- README with JD-bullet → code mapping table
- **(diff)** One-ride analysis writeup (markdown, 1–2 pages)
- **(diff)** Architecture diagram (a single PNG is fine)

## Feature Dependencies

```
[Ingestion]
    └── [FIT Parsing] ─────────────────────┐
    └── [Pose Extraction]                  │
            └── [Pose Smoothing]           │
            └── [Pedal Stroke Segmentation]│
                    └── [Time Alignment] ←─┘
                            └── [Per-Stroke Aggregation]
                                    └── [Per-Stroke Pose Metrics]
                                            ├── [Knee Angle / KOPS / Hip Rock]
                                            ├── [Asymmetry]
                                            └── [BDC/TDC Detection] (diff)
                                    └── [Correlations]
                                            ├── [Fatigue Detection] (diff)
                                            ├── [Efficiency Factor] (diff)
                                            └── [Environmental Fusion] (diff)
                                    └── [Storage: BigQuery]
                                            └── [Viewer / Dashboard]
                                                    └── [Annotated Frames] (diff)
                                                    └── [Writeup] (diff)

[Gear Inference] requires [FIT Parsing]
[Pose Cloud Run Service] is parallel to [Pose Extraction] — same logic, deployed
[GitHub Actions CI/CD] requires [Pose Cloud Run Service]
```

### Dependency Notes

- **Time Alignment is the linchpin.** Pedal-stroke detection from video AND FIT cadence must both exist before alignment can run. Alignment must succeed before any per-stroke aggregation (telemetry+pose) is meaningful. Schedule it early in roadmap.
- **Correlations depend on per-stroke aggregation.** Building correlation logic before per-stroke series exist is putting the cart before the horse. Per-second correlations are noisy and not the project's stated unit.
- **Cloud Run deployment is parallelizable** with the analysis pipeline once the pose-extraction function is stable. Don't block analytical iteration on infra readiness — develop locally, then dockerize.
- **The Viewer is downstream of everything** but should be sketched (paper/Figma) before pipeline work to anchor what data shapes the pipeline must produce.
- **Environmental fusion has no hard prerequisites** but has near-zero value for indoor rides (PROJECT.md's primary case) — implement it cheaply and stub gracefully.
- **Annotated frame strip depends on pose extraction + BDC detection.** If BDC detection is deferred, fall back to evenly-sampled frames within a stroke.

## MVP Definition

### Launch With (v1 — the demonstrable thin slice)

Each of the four JD areas must be represented. Below is the minimum set that lets a hiring manager see all four areas in one repo:

- [ ] **Ingest video + FIT from local path** — pipeline entry point
- [ ] **FIT → normalized DataFrame with gear inference** — telemetry area
- [ ] **MediaPipe pose extraction with One-Euro smoothing** — CV area, deployed locally
- [ ] **Pedal stroke segmentation from video** — proves CV produces usable temporal signal, not just per-frame snapshots
- [ ] **Video↔telemetry time alignment via cadence cross-correlation** — engineering signal of competence
- [ ] **Per-stroke aggregation of knee angle, KOPS, hip rock, asymmetry, power, cadence, HR**
- [ ] **Top-N correlations (Pearson) with confidence thresholds** — the core value
- [ ] **BigQuery sink + GCS artifact storage** — GCP area, schema visible in repo
- [ ] **Pose inference deployed as Cloud Run service** — GCP ML area, single most JD-resonant bullet
- [ ] **Streamlit (or notebook) viewer: fused timeline + correlations list + one annotated frame** — the visual
- [ ] **README with JD-bullet → code mapping table and one screenshot** — portfolio legibility

### Add After Core is Working (v1.x, choose 2–4)

The differentiators that have highest ratio of (resume signal) ÷ (effort given v1 in place):

- [ ] **One-ride written analysis (1–2 page markdown)** — highest leverage. Tells the story v1 produces
- [ ] **BDC/TDC detection** — sharpens every existing metric
- [ ] **Fatigue / rolling-window form drift detection** — directly executes the PROJECT.md headline example
- [ ] **Pedaling smoothness / torque effectiveness from FIT cross-checked against pose asymmetry** — the "two-source validation" story
- [ ] **GitHub Actions CI/CD to Cloud Run** — visible in the repo's Actions tab; cheap to add
- [ ] **Run manifest / reproducibility metadata** — performance-science-coded; cheap to add

### Future Consideration (defer indefinitely)

- [ ] **Aerobic decoupling / EF** — nice if HR data is rich, otherwise filler
- [ ] **Sensitivity analysis / inverse-kinematics saddle perturbation** — defer; high effort, easy to over-claim
- [ ] **Environmental data application (vs. just fetch)** — needs outdoor rides; v1 is indoor
- [ ] **Multi-ride trend analysis** — interesting but requires multiple rides; v1 is one ride
- [ ] **3D pose** — only if a clear bike-fit metric demands it, which v1 metrics don't
- [ ] **Saddle pressure / IMU integration** — requires hardware

## Feature Prioritization Matrix

User value here = resume signal × analytical legitimacy.

| Feature | Resume / Analytical Value | Implementation Cost | Priority |
|---------|---------------------------|---------------------|----------|
| FIT parsing + gear inference | HIGH | LOW | P1 |
| MediaPipe pose extraction | HIGH | LOW | P1 |
| Pedal stroke segmentation from video | HIGH | MEDIUM | P1 |
| Time alignment (video ↔ FIT) | HIGH | MEDIUM | P1 |
| Per-stroke knee/KOPS/hip-rock/asymmetry | HIGH | MEDIUM | P1 |
| Correlation surfacing | HIGH | MEDIUM | P1 |
| BigQuery sink | MEDIUM | LOW | P1 |
| Pose service on Cloud Run | HIGH | MEDIUM | P1 |
| Streamlit viewer (timeline + correlations) | HIGH | MEDIUM | P1 |
| README with JD-bullet mapping | HIGH | LOW | P1 |
| One-Euro pose smoothing | MEDIUM | LOW | P2 |
| BDC/TDC detection | MEDIUM | MEDIUM | P2 |
| One-ride markdown writeup | HIGH | MEDIUM | P2 |
| Fatigue / form drift detection | HIGH | MEDIUM | P2 |
| Annotated frame strip in viewer | MEDIUM | LOW | P2 |
| GitHub Actions CI/CD to Cloud Run | MEDIUM | MEDIUM | P2 |
| Run manifest / reproducibility | MEDIUM | LOW | P2 |
| Confidence-weighted keypoints | MEDIUM | LOW | P2 |
| Pedaling smoothness / torque effectiveness from FIT | MEDIUM | LOW | P2 |
| L/R balance cross-check (FIT vs pose) | HIGH | MEDIUM | P2 |
| Auto-detect bike-side facing | LOW | LOW | P3 |
| Aerobic decoupling / EF | LOW | LOW | P3 |
| Environmental fusion (Open-Meteo fetch) | LOW (indoor) | LOW | P3 |
| Sensitivity analysis (saddle perturbation) | MEDIUM | HIGH | P3 |

**Priority key:**
- **P1** — Must ship in v1; without it the JD-bullet story has a hole
- **P2** — Adds resume-distinguishing signal at reasonable cost; ship if time allows
- **P3** — Mention in README's "future work" but don't build unless trivial

## Competitor Feature Analysis

Used to calibrate what's table-stakes in the space — explicitly NOT used to chase feature parity (v1 is a portfolio piece, not a commercial product).

| Feature | Retul (in-shop) | Leomo (IMU) | MyVeloFit (AI app) | Bike Fast Fit (iOS) | Our Approach |
|---------|------------------|-------------|--------------------|--------------------|--------------|
| Marker-based pose | Yes (LED) | N/A (IMU) | No | No | No (markerless) |
| Markerless pose | No | N/A | Yes | Yes | Yes (MediaPipe) |
| 3D pose | Yes (sensor bar) | N/A | No (2D) | No (2D) | No (2D, side-on only) |
| Pedaling cycle metrics | Yes | Yes (DSS, pelvic rock) | Limited | Yes | Yes (knee, KOPS, hip rock, asymmetry) |
| Power meter integration | Optional | Yes | No | No | Yes (FIT file) |
| Environmental fusion | No | No | No | No | Yes (Open-Meteo, when applicable) |
| Per-stroke pose↔power correlation | No (separate analyses) | Limited | No | No | **Yes — primary value prop** |
| Coaching prescriptions | Yes (human fitter) | Yes (interpretive) | Yes (auto) | Yes (auto) | **No (anti-feature)** |
| Cloud deployment story | N/A | N/A | Cloud-based | iOS local | Yes (GCP, explicit) |
| PDF / written report | Yes | Yes | Yes | Yes | Markdown writeup (one ride) |

**Reading of the matrix:** The single feature where this project should differentiate analytically is **per-stroke pose↔telemetry correlation**, because no commercial tool does it well (most run the two analyses separately). That is also exactly what PROJECT.md declares as the core value — alignment is good. Everything else can be "competent execution of what the field considers standard," with credibility coming from explicit acknowledgment of what the project intentionally does NOT do (3D, prescriptions, multi-modality).

## Sources

- [Retul Fit — 3D motion capture and metrics](https://www.retul.com/retul-fit)
- [Slowtwitch: Retul vs. goniometer methodology discussion](https://www.slowtwitch.com/industry/retul-or-goniometer-it-alone/)
- [Leomo Type-R — DSS, pelvic rock, pelvic rotation metrics](https://www.leomo.io/pages/leomo-releases-type-r-with-a-special-discount-to-customers-located-in-eu-motion-analysis-for-athletes-coaches-and-fitters)
- [Hunter Allen: Introduction to Leomo TYPE-R motion analysis](https://www.hunterallenpowerblog.com/2017/07/An-Introduction-to-the-leomo-type-r.html)
- [Validity study: Leomo IMU vs optoelectronic camera for pedaling](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9322640/)
- [MyVeloFit — markerless AI bike fitting](https://www.myvelofit.com/insights/ai-bike-fit-motion-capture-fit/)
- [Bike Fast Fit Elite — smart recording, markerless tracking, PDF report](https://apps.apple.com/us/app/bike-fast-fit-elite/id1145619812)
- [FusionPose — MediaPipe + keypoint R-CNN for cyclist pose](https://www.sciencedirect.com/science/article/pii/S1474034625009073)
- [Cadence detection in road cycling using saddle motion + ML](https://www.mdpi.com/1424-8220/22/16/6140)
- [python-fitparse documentation](https://dtcooper.github.io/python-fitparse/api.html)
- [How to parse FIT files with Python — Denis Afanasyev](https://medium.com/@den.afanasjev/how-to-parse-fit-files-with-python-d74af8516768)
- [TrainingPeaks: Diagnosing pedaling asymmetry with WKO](https://www.trainingpeaks.com/coach-blog/diagnosing-correcting-pedaling-asymmetry-using-wko4/)
- [Hunter Allen: Introduction to L/R Power Data](https://www.hunterallenpowerblog.com/2015/11/balance-introduction-to-leftright-power.html)
- [gebioMized — saddle pressure mapping](https://www.gebiomized.us/saddle-pressure.html)
- [TrainingPeaks: Aerobic decoupling and efficiency factor](https://help.trainingpeaks.com/hc/en-us/articles/204071724-Aerobic-Decoupling-Pw-Hr-and-Pa-HR-and-Efficiency-Factor-EF)
- [Bike Fit Adviser — joint angle ranges in bike fitting](https://www.bikefitadviser.com/blog/not-basic-bike-fit-part-3-bike-fit-joint-angles)
- [Static vs dynamic knee angle methods — PubMed](https://pubmed.ncbi.nlm.nih.gov/32022807/)
- [Bike fitting biomechanics narrative review (2024)](https://www.researchgate.net/publication/381495046_Biomehanical_and_Postural_Evaluation_of_Optimal_Bike_Fit_for_non_Traumatic_Injury_Prevention_Among_Cyclists_A_Narrative_Review)
- [Impact of power output on muscle activation and 3D kinematics in pro cyclists](https://pmc.ncbi.nlm.nih.gov/articles/PMC7988189/)
- [Changes in muscle activity and kinematics during fatigue (cycling)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2905840/)
- [GPX Wind Analyzer — Open-Meteo historical weather for cycling](https://windgpx.netlify.app/)
- [MyWindsock — cycling weather API for performance analysis](https://mywindsock.com/page/api/)
- [One-Euro filter for pose smoothing](https://mohamedalirashad.github.io/FreeFaceMoCap/2021-12-25-filters-for-stability/)
- [DeepKalPose — Kalman filter for temporally consistent pose](https://arxiv.org/html/2404.16558v1)
- [Bicycle gear ratio / cadence / speed formula](https://cyclingroad.com/bicycle-gear-ratio-cadence-and-speed-calculator/)
- [Velogicfit — cycling analytics PDF reports](https://velogicfit.com/)
- [BikeLab FIT Analyzer — PDF reports with uncertainty bands](https://www.bikelabstudio.com/articles/how-to-read-fit-cycling-data-en.html)
- [Cycling Analytics — power curve, histograms, dashboards](https://www.cyclinganalytics.com/)
- [Shimano Connect Lab — power and force vector visualization](https://bike.shimano.com/products/apps/shimano-connect-lab.html)
- [Cyclemetry — telemetry video overlay tool (GitHub)](https://github.com/walkersutton/cyclemetry)
- [Telemetry Studio — pro cycling video overlay](https://telemetrystudio.com/)

---
*Feature research for: cycling form & performance analyzer (single-user, indoor-trainer video + FIT, portfolio-grade)*
*Researched: 2026-05-20*
