# Vision — System Architecture

This is the architecture **as built today** (Phase 1 MVP — local pipeline + Streamlit viewer). The cloud half (GCS, BigQuery, Cloud Run Jobs, Workflows, Eventarc) is **planned for Phase 3–4** and is drawn dashed.

## Mermaid

```mermaid
flowchart TB
    %% ---------- Inputs ----------
    subgraph IN[" Inputs "]
        V["🎞 Video file<br/>mp4/mov/avi"]
        F["📊 FIT file<br/>(optional)"]
        M[("MediaPipe model<br/>pose_landmarker_full.task<br/>~9 MB, downloaded on first run")]
    end

    %% ---------- Streamlit UI ----------
    subgraph UI[" viewer/app.py  ·  Streamlit "]
        UPL["File uploaders<br/>+ sidebar settings"]
        KPI["KPI tiles<br/>Frames · FPS · Strokes ·<br/>Cadence · Power · Alignment ·<br/>Pose quality"]
        DASH["HTML component (iframe)<br/>&lt;video&gt; + &lt;canvas&gt; overlay +<br/>Plotly multi-axis chart<br/>(JS rAF loop syncs playhead<br/>and redraws skeleton)"]
        TABS["Tabs: Strokes · Correlations ·<br/>Diagnostics · Keypoints · Telemetry"]
    end

    %% ---------- Pipeline ----------
    subgraph PIPE[" lib/vision/  ·  Pipeline modules "]
        POSE["pose.py<br/>extract_pose<br/>OpenCV decode →<br/>MediaPipe Tasks → flat<br/>Polars DataFrame"]
        SMOO["smoothing.py<br/>One-Euro filter<br/>+ visibility gate"]
        ANGL["angles.py<br/>knee · hip · elbow ·<br/>shoulder · ankle · trunk"]
        STRO["strokes.py<br/>scipy.signal.find_peaks<br/>→ per-stroke table"]
        FITP["fit.py<br/>garmin-fit-sdk →<br/>Polars DataFrame"]
        ALN["align.py<br/>cross-correlate<br/>pose-cadence vs FIT-cadence<br/>→ offset_ms + score"]
        CORR["correlations.py<br/>per-stroke fusion +<br/>Pearson r / n / p / 95% CI"]
    end

    %% ---------- Future ----------
    subgraph FUT[" Phase 3+ — planned, not yet built "]
        GCS[("GCS buckets<br/>vision-raw / vision-derived")]
        BQ[("BigQuery dataset 'vision'<br/>rides · telemetry_raw ·<br/>pose_keypoints · stroke_features<br/>+ fused_timeline view")]
        CRJ["Cloud Run Jobs<br/>pose-job · fit-job ·<br/>feature-job · correlate-job<br/>(min-instances=0)"]
        WF["Cloud Workflows<br/>+ Eventarc<br/>(manifest.json trigger)"]
        VIEW["Streamlit on Cloud Run Service<br/>+ /warmup endpoint"]
    end

    %% ---------- Data flow ----------
    V --> UPL
    F --> UPL
    M -. first-run download .-> POSE

    UPL -- video bytes --> POSE
    UPL -- fit bytes --> FITP

    POSE --> SMOO --> ANGL --> STRO
    STRO --> ALN
    FITP --> ALN
    STRO --> CORR
    FITP --> CORR
    ALN --> CORR

    SMOO --> DASH
    ANGL --> DASH
    STRO --> DASH
    FITP --> DASH

    STRO --> KPI
    ALN --> KPI
    CORR --> TABS
    SMOO --> TABS
    FITP --> TABS

    %% Future flow (dashed)
    UPL -. "Phase 4: make upload" .-> GCS
    GCS -. "Eventarc on manifest" .-> WF
    WF -. invokes .-> CRJ
    CRJ -. reads .-> GCS
    CRJ -. writes .-> BQ
    BQ -. queries .-> VIEW

    %% Styling
    classDef built fill:#e8f4f8,stroke:#2b7fd0,color:#1a1d21
    classDef planned fill:#fff7e6,stroke:#d97706,color:#1a1d21,stroke-dasharray:4 3
    class V,F,M,UPL,KPI,DASH,TABS,POSE,SMOO,ANGL,STRO,FITP,ALN,CORR built
    class GCS,BQ,CRJ,WF,VIEW planned
```

## ASCII (terminal-friendly)

```
                    ┌──────────────────────────────────┐
                    │  Browser  ·  http://localhost:8501│
                    │                                   │
   ┌──────────┐     │  ┌─────────────────────────────┐ │
   │ video.mp4│────▶│  │ HTML component (iframe):    │ │
   ├──────────┤     │  │  <video>  +  <canvas>       │ │
   │activity. │────▶│  │  Plotly chart w/ playhead   │ │
   │  fit (?) │     │  │  JS rAF: skeleton + angles  │ │
   └──────────┘     │  └─────────────────────────────┘ │
                    │  KPIs · Tabs (Strokes, Corr, …)  │
                    └────────────┬─────────────────────┘
                                 │  uploaded bytes
                                 ▼
   ┌────────────────────────────────────────────────────────┐
   │  viewer/app.py  (Streamlit)                             │
   │  _run_pipeline(video_bytes, fit_bytes, ride_id, …)      │
   └──────────────────────┬─────────────────────────────────┘
                          │
                          ▼
   ┌────────────────────────────────────────────────────────┐
   │  lib/vision/  (pure Python pipeline)                    │
   │                                                          │
   │    pose.py          ──┐                                  │
   │    (MediaPipe +       │                                  │
   │     OpenCV)           ▼                                  │
   │                   smoothing.py     fit.py                │
   │                   (One-Euro +      (garmin-fit-          │
   │                   visibility)       sdk)                 │
   │                       │              │                   │
   │                       ▼              │                   │
   │                   angles.py          │                   │
   │                       │              │                   │
   │                       ▼              │                   │
   │                   strokes.py         │                   │
   │                   (scipy.signal      │                   │
   │                    find_peaks)       │                   │
   │                       │              │                   │
   │                       └──────┬───────┘                   │
   │                              ▼                            │
   │                          align.py                         │
   │                          (cross-correlate                 │
   │                           pose × FIT cadence)             │
   │                              │                            │
   │                              ▼                            │
   │                       correlations.py                     │
   │                       (per-stroke fuse +                  │
   │                        Pearson r/n/p/CI)                  │
   │                              │                            │
   │                              ▼                            │
   │                       AnalysisBundle                      │
   └─────────────────────────────────────────────────────────┘

   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
   PLANNED, NOT YET BUILT  (Phases 3–6)
   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─

   make upload ──▶ GCS  ──▶ Eventarc ──▶ Cloud Workflows
                                              │
                                              ▼
                              ┌────────────────┴────────────────┐
                              │   four Cloud Run Jobs:          │
                              │   pose-job · fit-job ·          │
                              │   feature-job · correlate-job   │
                              └────────────────┬────────────────┘
                                               ▼
                                         BigQuery (vision)
                                               │
                                               ▼
                                  Streamlit on Cloud Run Service
                                  (read-only, --min-instances=0)
```

## Notes

- **Blue boxes / solid arrows** are built and exercised by the test suite (`uv run pytest -q`).
- **Orange dashed boxes** are the Phase 3-5 cloud target. Nothing in the orange section runs today.
- **The two halves of the pipeline are deliberately decoupled** (`pose.py` knows nothing about FIT, and vice versa). This is the same shape Phase 4's Cloud Workflows will preserve — `pose-job` and `fit-job` run in parallel branches, joined by `feature-job` → `correlate-job`.
- **One-Euro smoothing happens after pose extraction, not inside MediaPipe** — keeps the smoothing tunable without retraining anything.
- **Time alignment is a pure SQL transform in Phase 3** (per-ride offset stored on the `rides` row, applied by the `fused_timeline` BigQuery view). The Phase 1 `align.py` is what computes that offset; in cloud, it would write it to the `rides` table and the view would do the join.
- **The HTML component is a single iframe** containing both the `<video>` and the Plotly chart so the JS `requestAnimationFrame` loop can read `vid.currentTime` and update both the chart playhead and the skeleton canvas in lockstep. Streamlit's stock widgets don't expose video time, so this is the only way to get the sync.
