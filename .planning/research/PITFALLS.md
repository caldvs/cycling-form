# Pitfalls Research

**Domain:** Cycling pose + telemetry analyzer (CV + sport-telemetry data pipeline + GCP ML deployment, solo portfolio build)
**Researched:** 2026-05-20
**Confidence:** HIGH for GCP cost / portfolio / FIT-file traps (multiple authoritative sources). MEDIUM for pose-occlusion behavior on bikes (some peer-reviewed work, some inference from MediaPipe limitations). MEDIUM for VFR timing (well-documented in video tooling, less commonly discussed in pose-pipeline literature).

This document catalogues the specific ways this project can fail. It is opinionated: it treats the PROJECT.md "Out of Scope" decisions as already-made (no custom pose model, no real-time, no outdoor video, no multi-user). Where a pitfall would relitigate those decisions, the pitfall is reframed as "stay disciplined about the existing decision."

---

## Critical Pitfalls

### Pitfall 1: Side-view camera-rig sloppiness — "pose looks fine, geometry is junk"

**What goes wrong:**
The video is filmed from a phone propped on a chair that drifts during the ride, or angled 15° off true lateral, or zoomed such that the rider's hip leaves frame on a deep stroke. Pose keypoints land where they should in pixel space, but every downstream angle (knee, hip, KOPS — knee-over-pedal-spindle) is wrong by a varying amount frame-to-frame. The correlations published in the write-up are noise dressed up as signal.

**Why it happens:**
Indoor-trainer side-on shots look deceptively easy. The rider moves, but the bike's bottom bracket is bolted in place, so a developer assumes the camera-to-bike geometry is fixed. It isn't — phone tripods sag, the bike rocks laterally under hard efforts, and an "almost side-on" angle introduces foreshortening that biases hip and knee angles non-uniformly across the pedal stroke.

**How to avoid:**
- Define a one-page "filming protocol" doc as a deliverable: camera height = bottom-bracket height, distance specified, lens at 35mm-equivalent or wider, tripod-only (no handheld), reference object in frame for scale.
- Place a vertical and horizontal fiducial in-frame (a printed AR-style marker or simply a plumb line + ruler taped to the wall) and validate it appears stationary across the ride. If it moves >2px, throw the clip out or re-register.
- Compute joint angles as ratios/relative quantities where possible; report absolute angles only with stated uncertainty.
- For the v1 demo, use one carefully-shot reference clip and call out filming constraints in the README — do not pretend the pipeline is camera-agnostic.

**Warning signs:**
Knee-angle minima differ by >5° between left-leg and right-leg strokes on a symmetric rider. Reference fiducial drifts across the clip. Identical pedal positions across two strokes produce different keypoint coordinates by more than the model's nominal jitter.

**Phase to address:**
Phase 1 (data ingestion / capture protocol) — must be locked before any pose work.

---

### Pitfall 2: Leg-crossing occlusion silently corrupts the far-side leg

**What goes wrong:**
On a side-on shot the camera-side leg is fully visible, but the far-side leg passes behind the bike's frame, the crank, and the near leg for ~50% of every revolution. MediaPipe (and most 2D estimators) confidently emit landmark coordinates anyway — often interpolated, sometimes hallucinated to the wrong leg. Left/right asymmetry metrics — a headline output of the project — end up reflecting the model's occlusion behavior, not the rider's biomechanics.

**Why it happens:**
2D pose models output a fixed-arity landmark vector with no occlusion flag in MediaPipe's basic output; the per-landmark `visibility` score exists but is routinely ignored by tutorial code. The model was trained on people standing/walking with both legs visible, not on a person whose far leg is occluded for half of every cycle by a bike frame.

**How to avoid:**
- Treat the side-on view as a single-leg analyzer for v1. Report metrics only for the camera-side leg. State explicitly in the write-up that bilateral analysis would require a second camera or a 3D pose model.
- If bilateral metrics are non-negotiable, gate them on MediaPipe's `visibility` score (drop frames where far-side hip/knee/ankle visibility < threshold; tune threshold against the clip).
- Add a "visibility timeline" plot to the viewer so the reviewer can see which strokes had occluded frames suppressed.
- Do not present left/right asymmetry as a primary correlation unless visibility-gated frames remain >70% of the ride.

**Warning signs:**
Far-side leg "knee angle" tracks suspiciously closely with near-side knee angle (model is copying), or jumps discontinuously between strokes (model is guessing). MediaPipe visibility scores for far-side hip/knee fall below 0.5 for large fractions of the ride.

**Phase to address:**
Phase 2 (pose extraction) — gate metrics by visibility before any downstream computation.

---

### Pitfall 3: Video clock vs FIT clock alignment is treated as "set the start to zero and call it done"

**What goes wrong:**
The pipeline naively zeros both timelines on first sample. But the camera was started ~3 seconds before the rider clipped in, the FIT recording was auto-started by the head unit at first cadence detection, and the camera is on a phone whose clock drifts ~50ms per hour relative to the head unit's GPS-disciplined clock. After 60 minutes the pose-derived cadence is 2-4 seconds out of phase with telemetry cadence — enough to make "knee drift correlates with power drop" point at the wrong strokes.

**Why it happens:**
Two independent clocks recorded at different sampling rates from different vendor implementations. Indoor-mode FIT files have no GPS to anchor to wall-clock time. The "indoor" flag means timestamps are device-local and depend on the device's clock being set correctly. Camera files (especially phones) often record wall-clock at second-resolution in metadata while presentation timestamps are millisecond-resolution but in their own frame.

**How to avoid:**
- Pick one signal that exists in *both* streams and align on it. The natural choice: detect cadence (pedal stroke peaks) from video, detect cadence from FIT, run cross-correlation to find offset, then apply a linear correction (offset + drift slope) — a linear fit through the per-minute offsets, exactly as labstreaminglayer does for multi-device synchronization.
- Validate the alignment by checking that *another* signal aligns too — e.g., a known surge in power should land on a video frame where the rider visibly accelerates.
- Reject alignments where residual after linear fit exceeds 1 video frame; surface this to the user.
- Build the alignment step as its own unit-testable module with a synthetic test (generate two timelines with known offset+drift, confirm recovery).

**Warning signs:**
Cross-correlation peak is broad/flat instead of a sharp spike. Residual after offset correction grows linearly over the ride (indicates uncorrected drift). Two different fiducial events (cadence + power surge) imply different offsets.

**Phase to address:**
Phase 4 (time alignment) — explicit phase, do not bury this in glue code.

---

### Pitfall 4: GCP cost runaway from leaving inference services or scheduled jobs running

**What goes wrong:**
The Cloud Run pose-inference service is deployed with `--min-instances=1` "to avoid cold starts" during a demo. The developer moves on. Two months later the GCP bill is $40-$120 because that warm instance burned ~720 hours of vCPU + memory. Or worse: a Cloud Scheduler job calls the pipeline every hour against an empty bucket, hitting Cloud Run startup, BigQuery slot usage, and Cloud Storage operations 24×30 = 720 times monthly.

**Why it happens:**
GCP has no native hard spending cap. Budget alerts only notify — they do not act. Cloud Run with `min-instances ≥ 1` bills the full instance lifetime per second even with zero requests. The developer optimizes for a slick demo (no cold start) and forgets the cost model when the demo ends.

**How to avoid:**
- Default everything to `--min-instances=0`. Tolerate the 10-40 second first-request delay. Document it as a deliberate choice in the README.
- Set a project-level budget at $20/month with email alerts at 50%/90%/100%.
- Implement the Pub/Sub → Cloud Function "kill switch" that disables billing on the project when the cap is hit. This is the standard pattern for personal/student GCP projects and prevents a runaway loop from generating a $500 bill.
- Add a weekly recurring calendar reminder to check the billing dashboard for the first 8 weeks.
- For Cloud Scheduler jobs, prefer manual invocation during development; only schedule when you are actively iterating.

**Warning signs:**
Billing dashboard shows non-zero spend on a day you didn't touch the project. Cloud Run logs show requests during hours you weren't testing. BigQuery slot usage is non-zero with no queries you remember running.

**Phase to address:**
Phase 0 (project bootstrap) — kill switch and budget alerts must be in place **before** any Cloud Run deployment.

---

### Pitfall 5: Cloud Run cold start on a fat ML container — first call times out, demo fails

**What goes wrong:**
The hiring manager clicks the demo link from the README. The Cloud Run service has scaled to zero (correct, per Pitfall 4). The cold start has to (a) pull a 2.5GB Docker image containing MediaPipe + OpenCV + TensorFlow + a virtualenv that includes torch by accident, (b) load the pose model into memory, (c) initialize the FastAPI app. The HTTP request times out at 30s. The demo URL returns 5xx. The reviewer closes the tab.

**Why it happens:**
Standard `pip install -r requirements.txt` over a `python:3.11` base pulls in many MB of build tooling, dev headers, and transitive dependencies that bloat the image but don't affect runtime. Default Cloud Run request timeout is 5 minutes but client-side browser timeouts are often 30s. ML packages frequently pull torch as a transitive optional dep when you only wanted MediaPipe.

**How to avoid:**
- Multi-stage Docker build: build wheels in a builder stage, copy only the venv + model artifacts into a `python:3.11-slim` final stage.
- Audit `pip freeze` — explicitly exclude torch if not needed (MediaPipe Python uses TensorFlow Lite under the hood, not PyTorch).
- Pre-load the model at module import time so it's in memory once the container is healthy. Use Cloud Run's startup CPU boost flag.
- Bundle the model weights *inside* the image (not downloaded at startup). For MediaPipe this is small (~10MB). For MoveNet Thunder it's ~25MB. Both are fine in-image.
- Target image size under 500MB for the inference service.
- Add a `/warmup` endpoint and hit it from the viewer on page load, before the user submits a video. The pipeline's first real call then finds a warm instance.

**Warning signs:**
`docker images` shows the inference image >1GB. Cloud Run cold start logs show >20s between container start and "ready". First HTTP request from the viewer hangs longer than the network tab's timeout.

**Phase to address:**
Phase 5 (deployment) — image-size and cold-start budget must be acceptance criteria, not afterthoughts.

---

### Pitfall 6: Claiming the pipeline does things the code doesn't actually do

**What goes wrong:**
README and write-up say "fuses pose data with environmental conditions to surface fatigue correlations." Closer inspection shows: weather data is fetched but never joined to telemetry past a coarse ride-level average. Fatigue correlations are a single Pearson coefficient computed once on the whole ride. A reviewer with five minutes of curiosity opens the notebook, sees the gap, and writes the candidate off as someone who oversells.

**Why it happens:**
The developer wrote the README aspirationally at project start, never updated it as scope contracted. Or wrote it after the build and overcorrected toward impressive-sounding phrasing. Both look the same to a reviewer.

**How to avoid:**
- Write the README *last*, against the actual code paths.
- For every claim in the README, link to (a) the specific file/function that implements it, and (b) a test or notebook cell that exercises it on real data.
- Maintain a `CAPABILITIES.md` or "what this does / what this doesn't do" section. The "doesn't do" section is the most valuable signal of engineering maturity.
- Run the "skeptical reviewer" pass: open the README, pick the most impressive claim, try to find the line of code that delivers it, and time how long it takes. If >2 minutes, restructure.

**Warning signs:**
A phrase in the README cannot be traced to a specific module within 30 seconds. The verbs in the README are more ambitious than the verbs in the code (e.g., "predicts" when the code computes a correlation).

**Phase to address:**
Phase 7 (write-up / portfolio polish) — but seeded throughout: every PR should update README claims atomically.

---

### Pitfall 7: Letting the viewer framework eat the entire project

**What goes wrong:**
The "minimal viewer" requirement (per PROJECT.md) becomes a React + Vite + Tailwind + a charting library + a state-management library + a deployment to Vercel. Three weekends disappear into auth-shaped problems (even though auth is explicitly out of scope), responsive layout, and chart customization. Pose extraction is still using a hardcoded path to a single video file. The portfolio piece is now a frontend project with a CV stub attached.

**Why it happens:**
Frontends offer immediate visual feedback, which is psychologically rewarding. The data pipeline doesn't — it just produces parquet files. So the developer optimizes for the dopamine.

**How to avoid:**
- For v1, the viewer is a Jupyter notebook or a Streamlit app. Both render charts in <10 lines of code each and require zero JS toolchain.
- Set a strict viewer budget: ≤300 lines of code, ≤1 weekend of effort. If the budget is exceeded, the viewer is wrong, not the budget.
- The hiring story for this JD is *pipeline + ML deployment + telemetry engineering*. A bespoke React UI is not the story.
- Only graduate to a custom web frontend if you have time left after a working pipeline + notebook viewer.

**Warning signs:**
You spent more lines of code on the viewer than on pose extraction + alignment combined. You are debating Tailwind class names. You haven't run the pipeline end-to-end in a week because you've been on the viewer.

**Phase to address:**
Phase 6 (viewer) — explicit time-box, explicit "notebook first, web app only if time permits."

---

### Pitfall 8: Frame-rate vs cadence aliasing produces phantom rhythms

**What goes wrong:**
The video is shot at 30 fps. The rider cycles at 90 rpm = 1.5 strokes/sec, so each stroke spans 20 frames. Fine. Then the rider stands and spins out at 120 rpm = 2 strokes/sec, so each stroke spans 15 frames. Then 180 rpm sprint = 3 strokes/sec = 10 frames per stroke — borderline Nyquist for capturing top-dead-center precisely. Pose-derived cadence develops phantom harmonics or undercounts strokes. A 60 fps capture would have avoided this.

Additionally, phone cameras frequently record *variable frame rate* (VFR) video — actual frame intervals fluctuate, and `frame_index × (1/fps)` is wrong as a timestamp. Knee-angle-over-time plots get smeared.

**Why it happens:**
30 fps is the universal default — developers don't think about it. VFR is the iOS / many Android camera default; constant frame rate (CFR) requires deliberate choice. Pose-pipeline tutorials almost universally assume CFR.

**How to avoid:**
- Mandate 60 fps capture in the filming protocol doc (see Pitfall 1). On modern phones this costs nothing.
- Detect VFR explicitly at ingest using `ffprobe` (compare `r_frame_rate` to `avg_frame_rate`; if they differ meaningfully or if PTS deltas are non-uniform, flag VFR).
- If VFR is detected, either (a) reject the clip with a clear error, or (b) re-encode to CFR at ingest using ffmpeg with `-vsync cfr`, and document that this is a lossy normalization.
- Use ffmpeg's PTS extraction rather than `frame_index × 1/fps` for *every* per-frame timestamp; treat OpenCV's `CAP_PROP_POS_MSEC` as suspect.
- Validate cadence-detection against ground truth: hand-count strokes on a 30-second clip and compare.

**Warning signs:**
Detected cadence has spectral peaks at non-physical harmonics. Re-running pose on the same clip produces slightly different cadence (VFR + frame_index timing). `ffprobe -show_frames` shows non-uniform PTS deltas.

**Phase to address:**
Phase 1 (ingestion) — VFR detection — and Phase 2 (pose / stroke detection) — proper PTS-based timestamps.

---

## Moderate Pitfalls

### Pitfall 9: FIT-file edge cases break the parser silently

**What goes wrong:**
The parser handles the developer's own test file fine. Then a different ride breaks it: paused mid-ride (timestamps jump 15 minutes), multiple device records (HR strap connected mid-ride creates a second Record-message definition), power meter dropped out for 30 seconds (zeros vs nulls), the activity was actually two files appended after a "stopped device" recovery. The fitparse code crashes, or worse, silently produces a timeline with 15-minute gaps the rest of the pipeline doesn't notice.

**Why it happens:**
FIT files can contain multiple different definitions for record messages, which happens when sensors connect mid-ride or GPS acquires late. Paused rides emit Event messages (`event=timer`, `event_type=stop_all` / `start`) that must be honored to compute true elapsed vs. moving time. Recording rate is nominally 1Hz but smart-recording mode varies. Power=0 may mean "coasting" or "sensor dropped" depending on the device, and these have to be distinguished.

**How to avoid:**
- Treat FIT parsing as a separate phase with its own test suite. Include fixture files for: paused ride, dual-sensor (HR added mid-ride), power dropout, smart-recording variable rate, indoor (no GPS), outdoor (GPS present).
- Honor `event` messages to compute moving-time vs elapsed-time correctly. Do not assume Records are contiguous in time.
- Distinguish power=null (sensor not connected) from power=0 (coasting) from power=missing (sample skipped) — three different conditions, different downstream handling.
- Always read the FileId message first and reject (or branch on) anything that isn't `type=activity`.
- Use a known-good library (`fitparse` in Python) but wrap it with project-specific validators that warn on suspicious data.

**Warning signs:**
Elapsed-time and moving-time differ unexpectedly. Cadence and power timeseries have different lengths. The parser raises `UnexpectedEndOfFileError` or `FitParseError` on a file that another tool (Garmin Connect, FitFileViewer.com) opens fine.

**Phase to address:**
Phase 3 (telemetry parsing) — invest in fixture diversity early.

---

### Pitfall 10: Indoor "trainer mode" timing quirks are mistaken for bugs

**What goes wrong:**
The head unit was in trainer mode (no GPS). The FIT file's `local_timestamp` field is in device-local time and depends on the device clock being correct. The developer's head unit clock drifts because it hasn't seen GPS in weeks. The FIT timestamps are 47 seconds ahead of "real" wall-clock time, the video timestamps are wall-clock, and the pipeline silently misaligns by 47s.

Additionally, indoor activities have no GPS distance — `distance` is computed from speed (which comes from the trainer or a speed sensor on a wheel that isn't spinning vs. actual rolling). On a non-smart trainer, `speed` may be derived from cadence × an assumed gear, which is wrong, which makes "speed" telemetry semantically junk.

**Why it happens:**
The `indoor` flag's existence means downstream tools should treat indoor activities specially, but most generic FIT parsers do not. Speed from a wheel sensor on a stationary trainer reads zero; speed from a smart trainer reads the trainer's simulated speed (which is good); speed inferred from cadence on dumb trainers is meaningless.

**How to avoid:**
- Read the FileId / Session message and check the sport / sub-sport / `trainer` flag explicitly. Branch the pipeline.
- For indoor: do not use FIT's `speed` or `distance` as physical quantities; report them as "device-reported." Gear inference (which depends on speed) is unreliable on indoor rides unless the trainer is smart.
- Cross-validate FIT timestamps against video filesystem mtimes; if they differ by more than a few minutes and there's no GPS-disciplining, prefer the video clock for absolute time and the FIT clock for relative ordering.
- Surface a "this is an indoor ride, gear inference disabled" message in the output rather than producing bad gear data silently.

**Warning signs:**
Computed gear ratios fall outside the rider's actual cassette (e.g., 5.2 ratio when biggest gear is 4.5). Speed timeseries is constant or zero on a known-effortful section. FIT timestamps drift from video timestamps by tens of seconds.

**Phase to address:**
Phase 3 (telemetry parsing) and Phase 4 (alignment).

---

### Pitfall 11: Gear inference accuracy is overclaimed

**What goes wrong:**
The pipeline computes `gear_ratio = (speed / wheel_circumference) / cadence` and presents the resulting gear as ground truth. But: tire circumference is approximate (varies with pressure, wear, sidewall), speed on indoor trainers is simulated, the discretization to "53×17 vs 53×16" requires fractional rounding that the calculation isn't accurate enough to support, and a 1 rpm cadence-sensor error swings the inferred ratio by ~1%.

**Why it happens:**
The math looks clean: `C = 11.4 × V_g / R`. It's tempting to present a clean integer-cog answer. But error sources stack: tire circumference (1-2% error from pressure/wear), cadence sensor precision (±1 rpm), speed precision (±0.1 mph). On indoor smart trainers, the trainer's reported speed is itself derived from power × an internal model and is not a direct measurement of wheel rotation.

**How to avoid:**
- Report gear as a *probability distribution* over the rider's known cassette+chainring combinations, not a single answer. "Most likely 53×16 (62%), possibly 53×17 (28%)."
- Require the user to declare their wheel circumference and chainring/cassette teeth as config; do not assume defaults.
- For indoor rides, do not attempt gear inference unless using a smart trainer with proper speed simulation. State this limitation.
- Validate the inference on at least one ride where the actual gear is known (e.g., recorded by hand or with an electronic shifter that emits gear-position data).
- Frame the gear-inference output as "inferred gear (±1 cog)" everywhere it appears.

**Warning signs:**
Computed gear changes within a single stroke (impossible — riders don't shift mid-stroke). Inferred gears include impossible ratios. Multiple very-different gears get assigned within seconds of each other on a steady effort.

**Phase to address:**
Phase 3 (telemetry parsing / derived metrics).

---

### Pitfall 12: Weather API used wrong — wrong location, wrong time zone, or applied to an indoor ride

**What goes wrong:**
The pipeline geocodes "Boston" and fetches hourly weather for the ride. But the ride was on a trainer in a Boston basement at 68°F. The "temperature 92°F, humidity 88%" applied to the analysis is fiction. Or: the API returns UTC timestamps but the FIT file's `local_timestamp` is in the rider's local time; weather gets joined to the wrong hour of the day. Or: an outdoor ride's GPS track crosses three weather stations / grid cells and the pipeline picks one for the whole ride.

**Why it happens:**
OpenWeather/Visual Crossing default to UTC; FIT files use Garmin epoch (1989-12-31 UTC) and may include a local-timezone offset. Open-Meteo's historical-weather endpoint has hourly-resolution limits (≤7 days per request). Indoor rides should not get outdoor weather at all, but it's tempting to "just attach some weather data" to look thorough.

**How to avoid:**
- Never attach weather to indoor rides. Skip the lookup. Document the skip in the output.
- For outdoor rides: use the FIT file's `position_lat/long` (semicircles, convert with `× 180/2^31`) at multiple points along the ride; do not use a single reverse-geocoded city name.
- Normalize all timestamps to UTC inside the pipeline; convert to local time only at presentation.
- Cache weather responses on disk keyed by (lat-rounded, lon-rounded, hour) to avoid re-fetching during development and to make builds reproducible.
- Validate by manually checking one ride against a known external source (e.g., Weather Underground for a specific date/location).

**Warning signs:**
Indoor rides have weather data. Temperature is "0°F" or "999°F" (API error code passed through). The same ride run twice fetches weather twice instead of hitting cache.

**Phase to address:**
Phase 3 (telemetry enrichment).

---

### Pitfall 13: Region selection in GCP causes unnecessary latency or unexpected egress charges

**What goes wrong:**
The Cloud Run service is in `us-central1`, the BigQuery dataset in `EU`, the GCS bucket in `us-east1`. Every pipeline run causes cross-region egress on the video file (potentially 100-500MB) and on every BigQuery insert. Egress is billed per GB. The reviewer in Europe sees 400-700ms latency just to hit the inference endpoint.

**Why it happens:**
GCP regions are picked one-resource-at-a-time during the GCP console click-through and each defaults differently. There is no warning when you place resources in incompatible regions.

**How to avoid:**
- Decide a region at project bootstrap (Phase 0) and pin it everywhere. For a US developer applying to a US-located role: `us-central1` is the standard cheapest default.
- Create resources via Terraform or a documented `gcloud` script so the region is in version control, not in console muscle memory.
- Co-locate the GCS bucket, BigQuery dataset, and Cloud Run service in the same region. If the bucket must be multi-region, document why.
- For the deployed demo URL, accept the latency from the reviewer's region — do not over-engineer multi-region deployments for a portfolio piece.

**Warning signs:**
Billing dashboard shows "Network Egress" as a non-trivial line item. BigQuery jobs report "cross-region data transfer." Cloud Run logs show large request durations dominated by reading from GCS.

**Phase to address:**
Phase 0 (project bootstrap / infra setup).

---

### Pitfall 14: MLOps over-engineering — building Vertex Pipelines / a model registry / CI for model retraining

**What goes wrong:**
The developer reads about Vertex AI Pipelines, sets up a multi-stage pipeline orchestration, writes a CI workflow that retrains models on commit, configures a model registry, and adds a feature store. None of this is justified by the project — there is no custom model being trained (per PROJECT.md), there is no model-drift to monitor, there is one user. Three weekends disappear into MLOps infrastructure that exists to itself.

**Why it happens:**
MLOps reads like a strong resume signal. The GCP docs have extensive tutorials on Vertex Pipelines and the temptation is to demonstrate them. Solo developers without product pressure default to "what would a 50-person team need?" rather than "what does this project need?"

**How to avoid:**
- Re-read PROJECT.md "Out of Scope": **training a bespoke pose model** is explicitly out of scope. Without training, most of MLOps doesn't apply.
- Adopt the rule: every GCP service added needs a one-sentence justification in the README ("Cloud Run hosts the stateless pose inference function; BigQuery stores per-stroke features for ad-hoc query"). If the justification reads like marketing, cut the service.
- Reach for the smallest reasonable stack: GCS + Cloud Run + BigQuery. Add Cloud Scheduler only if there's a recurring job. Avoid Vertex Pipelines, Vertex Model Registry, Feature Store, Dataflow for v1.
- The hiring story is "I deployed an ML inference service on GCP and wired it to a telemetry pipeline," not "I built an MLOps platform."

**Warning signs:**
You are configuring Vertex AI without training a model. You have a `.github/workflows/retrain.yml` for a model you don't train. You can't explain in one sentence why a service is in the stack.

**Phase to address:**
Phase 5 (deployment) — discipline applied at architecture-decision time.

---

### Pitfall 15: Keypoint jitter masquerades as biomechanics

**What goes wrong:**
Pose keypoint coordinates jitter ±2-5 pixels frame to frame even on a stationary subject. Differentiating a position signal (computing velocity, acceleration, or angular rates) amplifies the noise. "Hip rock magnitude" or "knee angular velocity" turn into noise dressed up as signal. Reported metrics aren't reproducible run-to-run because some pose model internals are non-deterministic.

**Why it happens:**
Pose models output the maximum-likelihood landmark per frame independently; no temporal model. Sub-pixel accuracy is illusory at typical capture resolution. MediaPipe with `model_complexity=0` jitters more than `=2`. Numerical differentiation always amplifies high-frequency noise.

**How to avoid:**
- Apply temporal smoothing — One Euro filter is the standard for pose keypoints (low-lag, adaptive). Kalman filters work but are more setup for small wins on 2D pose.
- Use `model_complexity=1` or `=2` for MediaPipe Pose (slower, less jitter). Document the choice.
- Compute angles before smoothing rather than smoothing pixel coordinates and then computing angles — angles are more stable than raw landmark positions because they're scale-invariant.
- For per-stroke metrics, aggregate over the stroke (mean, min, max) rather than reporting instantaneous values.
- Pin model versions and seeds; document any non-determinism in the README so two runs of the same clip produce the same numbers.

**Warning signs:**
Knee angle plot looks like a noisy sine wave with high-frequency hash. Two runs on the same input produce numerically different outputs. Computed asymmetry magnitude is comparable to or smaller than the model's nominal landmark jitter.

**Phase to address:**
Phase 2 (pose extraction → feature smoothing).

---

## Minor Pitfalls

### Pitfall 16: Coordinate-system confusion (pixel space vs image space vs world space)

**What goes wrong:**
Code mixes (x, y) where x is "column from left" with (row, col) where row is "from top." Hip angle is measured assuming y-up but image coordinates are y-down, flipping the sign on every angle.

**How to avoid:**
- Pick a convention at the top of the pose module — explicit comment — and stick to it.
- Standard for this project: image-space (x right, y down) for raw landmarks; convert to math-space (y up) for any angle calculation, and document this transformation.
- Unit-test angle calculations against hand-computed examples on a synthetic image.

**Phase to address:**
Phase 2.

---

### Pitfall 17: Dropped video frames misinterpreted as motion freezing

**What goes wrong:**
The camera drops a few frames during recording (thermal throttling, storage hiccup). The pose pipeline processes the rest, but the position-time series has a 4-frame gap that gets misread as "the rider froze for 130ms."

**How to avoid:**
- Use PTS rather than frame index. Detect gaps in PTS deltas and represent them as missing data, not as additional samples.
- Interpolate position only across small gaps (e.g., ≤2 frames); flag larger gaps.

**Phase to address:**
Phase 2.

---

### Pitfall 18: Persisting raw video in BigQuery or large blobs in inappropriate stores

**What goes wrong:**
Tempted to put video metadata or pose keypoints (millions of rows × 33 landmarks × 60 fps × 30 min = 3.5M rows per ride) into BigQuery without thinking about storage tiers or partitioning.

**How to avoid:**
- Raw video and FIT files: GCS only.
- Pose features (per-stroke aggregates, not per-frame landmarks): BigQuery, partitioned by ride_id and clustered by ride_date.
- Per-frame landmarks if needed: parquet on GCS, queryable via BigLake or read directly into the notebook viewer. Do not insert per-frame keypoint streams into BigQuery row-by-row.

**Phase to address:**
Phase 3 / Phase 5.

---

### Pitfall 19: Single-clip overfitting in the demo

**What goes wrong:**
The whole pipeline is demonstrated on one carefully-chosen video + FIT pair. Every parameter (threshold, smoothing window, alignment offset bound) is implicitly tuned to that one clip. A second ride exposes the brittleness.

**How to avoid:**
- Collect at least 3 rides (different conditions: easy, hard, intervals) before declaring the pipeline working.
- Refuse to merge tuning changes to main without running against all fixture clips.

**Phase to address:**
Phase 6 (validation) / continuous throughout.

---

### Pitfall 20: Treating MediaPipe Pose's 3D landmarks as actually 3D

**What goes wrong:**
MediaPipe Pose returns z-coordinates that look 3D but are estimated from a single 2D camera with no actual depth information. Using z for "is the knee inside or outside the pedal spindle in the camera-axis direction" (the literal KOPS metric) introduces wildly unreliable depth estimates.

**How to avoid:**
- Use only x, y from MediaPipe for v1. Document this explicitly.
- KOPS in the v1 project is reframed as 2D projection — knee horizontal position relative to pedal/foot horizontal position in the camera plane. State this is an approximation of true 3D KOPS.
- Defer 3D analysis to a possible v2 that uses two cameras or a true 3D model (MMPose 3D, MotionBERT, etc.).

**Phase to address:**
Phase 2.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode the path to one video + FIT file | Skip building any ingestion UX | Pipeline doesn't generalize; reviewer can't try their own files | OK for v1 if README explicitly says "demo data only" and CLI accepts paths |
| Run pose inference locally on dev laptop, not on Cloud Run | Faster iteration on pose features | Resume loses the "deployed on GCP" talking point | Never — deployment is one of the four JD bullets and must be demonstrated |
| Use Jupyter notebook as the entire viewer | Trivial to build, renders charts in 10 lines | Less impressive than a hosted web demo | Acceptable for v1; only graduate if there's time |
| Skip One Euro / Kalman smoothing, report raw landmarks | Faster to ship | Noisy charts undermine credibility of correlation claims | Never for the public demo; OK during scratch dev |
| Skip the kill switch, rely on email budget alerts | Saves ~30 min of Pub/Sub + Cloud Function setup | Single runaway script can produce a $200 bill | Never for personal projects without corp credit card backstop |
| Use `min-instances=1` for "snappier demos" | No cold-start delay | ~$10-30/month per service for an idle container | Only during the active demo window (e.g., a known interview week); reset to 0 after |
| Commit FIT and video fixtures into the repo | Reviewers can clone-and-run | Repo bloat, possible privacy issues (HR data, GPS tracks on outdoor rides) | OK for synthetic fixtures only; real rides should be hosted on GCS with a public signed URL or omitted with sample data on request |
| Skip writing a filming protocol because "v1 only uses one camera setup" | Saves a half hour | Reviewer can't reproduce, future-you can't reproduce | Never — the protocol IS the deliverable for the data-engineering story |
| Compute correlation as a single Pearson over the whole ride | One line of code | Hides intra-ride dynamics; misleading | OK as one of multiple views; never as the only view |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FIT file (`fitparse`) | Iterating only `record` messages, ignoring `event`/`session`/`device_info` | Iterate all message types; honor `event=timer` for pause handling; read `device_info` for sensor-source attribution |
| MediaPipe Pose | Using default `static_image_mode=True` on a video (or vice versa) | Use `static_image_mode=False` for video so the temporal smoothing inside MediaPipe activates |
| OpenCV `VideoCapture` | Trusting `CAP_PROP_POS_MSEC` on VFR video | Use ffmpeg/ffprobe to extract real PTS; pass timestamps explicitly into the pose pipeline |
| Cloud Run | Sending large request bodies (video bytes) inline | Upload to GCS first, pass the GCS URI in the Cloud Run request; or use Cloud Run Jobs for batch |
| BigQuery | Streaming inserts of high-cardinality per-frame data | Batch write to parquet on GCS, load to BigQuery on completion; or use ELT — keep raw in GCS, materialize stroke-level aggregates in BQ |
| Weather APIs | Reverse-geocoding a single point at ride start to "Boston" then asking for "Boston weather" | Use the actual lat/lon (multiple points for long rides); skip entirely for indoor rides |
| GCS | Bucket in a different region than Cloud Run | Pin region in Terraform / setup script; verify on first deploy |
| FastAPI / Cloud Run | Listening on `localhost`, not on `0.0.0.0:$PORT` | Read `PORT` env var; bind to `0.0.0.0`; Cloud Run will not route traffic otherwise |
| Garmin epoch | Treating FIT timestamps as Unix epoch | FIT epoch is 1989-12-31 00:00:00 UTC; add 631065600s offset to convert to Unix |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Running pose inference on every video frame including idle/non-pedaling segments | Long inference time on rides with warmup/cooldown | Detect motion / pedaling segments first (cheap), pose only those | 30+ min rides with warmup; multiplies inference cost ~30% |
| Sending the whole video to Cloud Run in one request | Request timeout, memory OOM | Chunk video into N-second segments processed in parallel Cloud Run Jobs, or process locally and only deploy the model-serving function | Videos longer than ~10 min on default Cloud Run memory |
| Streaming inserts into BigQuery row-by-row from the pipeline | High latency, high cost per row | Batch into parquet → load via `bq load` | More than a few hundred rows per ride |
| Loading the MediaPipe model on every request | Each request pays 1-3s model load | Module-scope model instantiation, persist across requests | As soon as request rate is >1/min |
| Re-fetching the same weather data on every dev iteration | Slow iteration, API quota burn | Disk-cache keyed by (lat, lon, hour) | Day-2 of development |

(This project is single-user batch-only. "Breaks at 10k QPS" is not a relevant concern; the traps above are about dev-iteration speed and per-ride cost, which is the right scale to plan for.)

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Service-account key committed to public repo | GCP credential leak → bill explosion | Use Workload Identity / Application Default Credentials locally; never commit JSON keys; add `*.json` for known key-file patterns to `.gitignore` and run `git-secrets` or `truffleHog` pre-commit |
| GCS bucket made public for demo convenience | Anyone can upload, possibly causing storage costs; FIT files reveal home addresses (GPS), HR data, weight | Keep bucket private; generate short-lived signed URLs for demo access; or omit sample data from the public demo |
| Cloud Run service exposed without auth, doing expensive inference | Anyone can hit your inference endpoint and burn your quota | Use Cloud Run IAM (`--no-allow-unauthenticated`) + a per-invocation ID-token from the viewer; or accept the risk for demos and rely on the kill switch as backstop |
| FIT files from outdoor rides committed to the repo | GPS tracks reveal home address | Sanitize: strip lat/lon before commit, or use only indoor-trainer FIT files in fixtures |
| Embedding API keys (weather API, etc.) in the codebase | Free-tier keys get rate-limited; paid keys cost money | `.env` (gitignored) + Secret Manager for deployed services |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Viewer dumps all 50 charts at once | Reviewer skims, misses the headline | Lead with the top 3 correlations; "show more" reveals the rest |
| No "what is this chart" labels | Reviewer who doesn't know cycling biomechanics misreads | Each plot has a one-line plain-English caption: "Knee angle minimum per stroke. Lower = deeper compression. Coaches like ~110-120° at the bottom of the stroke." |
| Correlation reported without effect size or confidence | "r=0.3" reads as meaningful when it might be noise | Report r alongside n (number of strokes), p, and 95% CI; describe in words ("weak positive, plausibly chance") |
| Showing pose overlay on the original video at 60 fps | Distracting, doesn't aid interpretation | Single annotated "representative stroke" image + a stroke-aggregate plot; full overlay video as a "deep dive" link |
| Burying caveats in a footer | Reviewer scans and over-credits the work | State limitations inline next to the metric they affect ("Single-leg analysis — bilateral metrics not reliable in this view") |

---

## "Looks Done But Isn't" Checklist

- [ ] **Pose extraction:** Often missing visibility-gating — verify metrics drop occluded frames, not silently include them
- [ ] **Time alignment:** Often missing drift correction (only static offset applied) — verify residual after correction is bounded across the full ride length
- [ ] **FIT parsing:** Often missing pause/event handling — verify a paused ride produces correct elapsed/moving times
- [ ] **Telemetry:** Often missing distinguishment between sensor-dropout and zero-value — verify power=null vs power=0 are handled differently
- [ ] **Weather integration:** Often missing skip-on-indoor — verify indoor rides have no weather attached
- [ ] **Gear inference:** Often missing uncertainty bounds — verify output is a distribution or includes "±1 cog" framing
- [ ] **Cloud Run deployment:** Often missing kill switch — verify a deliberate cost-cap mechanism exists, not just an email alert
- [ ] **Cloud Run image:** Often >1GB — verify image size <500MB and document the multi-stage build
- [ ] **README:** Often aspirational — verify every claim links to a specific module + test
- [ ] **Repo hygiene:** Often has stale branches, commented-out experiment code, no `LICENSE`, no CI badge — verify the top of the README is recruiter-ready in <30s of scrolling
- [ ] **Reproducibility:** Often "works on my machine" — verify a fresh clone + `make demo` (or equivalent) runs the pipeline end-to-end on bundled fixture data
- [ ] **VFR detection:** Often missing — verify ingest rejects or normalizes VFR clips with a clear message
- [ ] **Region pinning:** Often inconsistent — verify all GCP resources are in the same region
- [ ] **Filming protocol:** Often absent — verify the repo contains a one-page protocol with camera placement specs
- [ ] **Capability statement:** Often missing — verify a "what this does NOT do" section exists in the README

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Runaway GCP bill | HIGH (money) | Disable billing on the project immediately; file billing-credit request to GCP support citing student/personal project (often successful for small amounts); kill switch should have prevented this |
| Misaligned video/FIT producing wrong correlations after publication | MEDIUM (reputation) | Pull the public demo; revise alignment with proper drift correction; re-publish with a changelog entry honestly describing the fix |
| Cloud Run cold start too slow during a live demo | LOW (deal with it in 60s) | Hit `/warmup` from the viewer on page load; if still cold during demo, talk through the architecture while waiting; have a pre-baked recorded video as fallback |
| Pose model jitter swamping signal | MEDIUM (rework) | Add One Euro filter + switch to `model_complexity=2`; rerun on fixtures; if still noisy, switch to MoveNet Thunder (stronger model, similar API surface) |
| FIT parser crashes on a real-world file | LOW (extend) | Capture the file as a fixture, add a failing test, fix the parser, repeat — this is normal long-tail work and should be expected |
| Reviewer finds an undelivered README claim | HIGH (reputation) | Acknowledge directly, fix in the next commit, never argue; the meta-skill of admitting limits is itself a hireable signal |
| Container image bloated to 2GB and pulling slowly | LOW (rebuild) | Multi-stage Dockerfile + python-slim base + audit `pip freeze`; usually 70% reduction within an evening |
| Custom-model rabbit-hole started by mistake | MEDIUM (sunk cost) | Stop. Re-read PROJECT.md "Out of Scope". Revert to off-the-shelf model. Keep the custom-model branch tagged for a v2 conversation if asked |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| #1 Camera-rig sloppiness | Phase 1 (capture protocol) | Reference fiducial appears stationary across clip; protocol doc exists in repo |
| #2 Far-leg occlusion | Phase 2 (pose extraction) | Far-leg metrics are visibility-gated; visibility timeline rendered in viewer |
| #3 Clock alignment | Phase 4 (alignment) | Synthetic-offset test recovers offset within tolerance; residual after fit < 1 frame |
| #4 GCP cost runaway | Phase 0 (bootstrap) | Budget exists, kill-switch Cloud Function deployed, weekly check reminder set |
| #5 Cold start / fat image | Phase 5 (deployment) | Image size <500MB; cold start <15s measured; `/warmup` endpoint exists |
| #6 Overclaimed README | Phase 7 (write-up) | Each claim linked to a module + test; "what it does NOT do" section present |
| #7 Viewer eats the project | Phase 6 (viewer) | Viewer LOC <300; notebook-first approach documented |
| #8 FPS/cadence aliasing + VFR | Phase 1 (ingestion) + Phase 2 | VFR detection at ingest; cadence validated against hand-counted ground truth |
| #9 FIT edge cases | Phase 3 (telemetry parsing) | Fixture suite includes ≥6 edge-case files; parser passes all |
| #10 Trainer-mode timing | Phase 3 + Phase 4 | Indoor flag honored; speed/distance treated as device-reported on indoor; cross-validation with video clock |
| #11 Gear inference accuracy | Phase 3 | Gear output is a distribution or carries ±1 cog framing; never produced for non-smart-trainer indoor rides |
| #12 Weather API misuse | Phase 3 | Indoor rides skipped; lat/lon used not city name; UTC normalization internal |
| #13 GCP region mismatch | Phase 0 | All resources in one region; documented in setup script |
| #14 MLOps over-engineering | Phase 5 | Each GCP service has a one-sentence README justification; no Vertex Pipelines / Model Registry / Feature Store without justification |
| #15 Keypoint jitter | Phase 2 | One Euro filter applied; metrics computed as stroke-aggregates not instantaneous |
| #16 Coordinate confusion | Phase 2 | Convention documented at top of pose module; angle calculations unit-tested |
| #17 Dropped frames | Phase 2 | PTS-based timestamps; gap detection raises warning |
| #18 Storage tier misuse | Phase 3 / Phase 5 | Raw artifacts in GCS; per-frame data in parquet; only aggregates in BigQuery |
| #19 Single-clip overfitting | Phase 6 (validation) | ≥3 rides in fixture set; CI runs against all |
| #20 Fake 3D KOPS | Phase 2 | Documentation states 2D approximation; MediaPipe z-coord not used |

---

## Sources

- [FusionPose: MediaPipe-based cyclist pose estimation, ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1474034625009073) — limitations of MediaPipe under cycling-frame occlusion, knee-angle accuracy bounds
- [YOLOv7 Pose vs MediaPipe in Human Pose Estimation, learnopencv](https://learnopencv.com/yolov7-pose-vs-mediapipe-in-human-pose-estimation/) — MediaPipe occlusion failure modes vs alternatives
- [Cloud Run pricing, Google Cloud](https://cloud.google.com/run/pricing) and [Cloud Run GPU best practices](https://docs.cloud.google.com/run/docs/configuring/services/gpu-best-practices) — pricing model that drives the cost-runaway pitfall
- [Optimize Python applications for Cloud Run](https://cloud.google.com/run/docs/tips/python) — image size, slim base, lazy loading
- [3 ways to optimize Cloud Run response times, Google Cloud Blog](https://cloud.google.com/blog/topics/developers-practitioners/3-ways-optimize-cloud-run-response-times) — cold start mitigations
- [Automated GCP Killswitch, Medium / Google Cloud Community](https://medium.com/google-cloud/how-to-avoid-a-massive-cloud-bill-41a76251caba) and [poweroff-google-cloud-cap-billing, GitHub](https://github.com/Cyclenerd/poweroff-google-cloud-cap-billing) — Pub/Sub → Cloud Function billing kill-switch pattern
- [FITfileR vignette](https://msmith.de/FITfileR/articles/FITfileR.html) and [Garmin FIT Cookbook](https://developer.garmin.com/fit/cookbook/decoding-activity-files/) — multi-definition records, pause handling, indoor flag semantics
- [Fit File Repair Tool manual](https://www.fitfilerepairtool.info/app/download/5777698335/Fit+File+Repair+Tool+User+Manual.pdf) — paused-ride and merge edge cases
- [Wrong GPS timestamp in FIT file, Garmin Forums](https://forums.garmin.com/sports-fitness/cycling/f/edge-830/239540/wrong-gps-timestamp-in-fit-file-delay) — real-world FIT timestamp drift
- [Automatic synchronization with your video, gpxoverlay.com](https://gpxoverlay.com/blog/automatic-synchronization-with-your-video) — video-vs-FIT alignment via shared signals (cadence, turn points)
- [Time Synchronization, labstreaminglayer docs](https://labstreaminglayer.readthedocs.io/info/time_synchronization.html) — linear-fit clock-drift correction technique
- [Application of video frame interpolation to single-camera gait analysis, Springer](https://link.springer.com/article/10.1007/s12283-023-00419-3) — frame-rate effects on pose-derived gait/cadence accuracy
- [Variable Frame Rate check, OpenCV forum](https://forum.opencv.org/t/vfr-variable-frame-rate-check/20612) and [VFR Detector, timebolt.io](https://www.timebolt.io/VFR-Detector) — VFR detection technique
- [Bicycle Gear Ratio, Cadence, and Speed Calculator, cyclingroad.com](https://cyclingroad.com/bicycle-gear-ratio-cadence-and-speed-calculator/) — gear-from-cadence-and-speed formula and its error sources
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) and [Date and Times in the Weather API, Visual Crossing](https://www.visualcrossing.com/resources/documentation/weather-api/date-and-times-in-the-weather-api/) — historical-lookup endpoint constraints, timezone handling
- [5 Critical Software Engineer Portfolio Mistakes, lyrid.io](https://www.lyrid.io/post/5-critical-software-engineer-portfolio-mistakes-that-junior-developers-are-making) — undocumented projects, over-engineering signal
- [The Great README Hunt, Medium](https://medium.com/local-llm-lab/the-great-readme-hunt-what-readme-best-practices-actually-signal-d9df9782b512) — README as a hiring signal
- [What do hiring managers see on my GitHub profile, Reczee Blog](https://www.reczee.com/blog/what-do-hiring-managers-see-on-my-github-profile) — repo-hygiene heuristics
- [Background and Foundations for ML in Production, dailydoseofds.com](https://www.dailydoseofds.com/mlops-crash-course-part-1/) — MLOps complexity / over-engineering risk for solo builders
- [Machine Learning: Off-the-shelf models or custom build, dlabs.ai](https://dlabs.ai/blog/machine-learning-off-the-shelf-models-or-custom-build-pros-and-cons/) — when off-the-shelf is the right answer (this project's case)

---
*Pitfalls research for: cycling pose + telemetry analyzer (solo GCP portfolio build)*
*Researched: 2026-05-20*
