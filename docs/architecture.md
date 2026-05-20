# Architecture

A local Python pipeline + a Streamlit dashboard. One MediaPipe pose model under the hood; everything else is classical signal processing and statistics.

## Mermaid

```mermaid
flowchart TB
    subgraph IN[" Inputs "]
        V["🎞 Video file<br/>mp4/mov/avi"]
        F["📊 FIT file<br/>(optional)"]
        M[("MediaPipe model<br/>pose_landmarker_full.task<br/>~9 MB, downloaded on first run")]
    end

    subgraph UI[" viewer/app.py  ·  Streamlit "]
        UPL["File uploaders<br/>+ sidebar settings"]
        KPI["KPI tiles<br/>Frames · FPS · Strokes ·<br/>Cadence · Power · Alignment ·<br/>Pose quality"]
        DASH["HTML component (iframe)<br/>&lt;video&gt; + &lt;canvas&gt; overlay +<br/>Plotly multi-axis chart<br/>(JS rAF loop syncs playhead<br/>and redraws skeleton)"]
        TABS["Tabs: Strokes · Correlations ·<br/>Diagnostics · Keypoints · Telemetry"]
    end

    subgraph PIPE[" lib/vision/  ·  Pipeline modules "]
        POSE["pose.py<br/>extract_pose<br/>OpenCV decode →<br/>MediaPipe Tasks → flat<br/>Polars DataFrame"]
        SMOO["smoothing.py<br/>One-Euro filter<br/>+ visibility gate"]
        ANGL["angles.py<br/>knee · hip · elbow ·<br/>shoulder · ankle · trunk"]
        STRO["strokes.py<br/>scipy.signal.find_peaks<br/>→ per-stroke table"]
        FITP["fit.py<br/>garmin-fit-sdk →<br/>Polars DataFrame"]
        ALN["align.py<br/>cross-correlate<br/>pose-cadence vs FIT-cadence<br/>→ offset_ms + score"]
        CORR["correlations.py<br/>per-stroke fusion +<br/>Pearson r / n / p / 95% CI"]
    end

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

    classDef node fill:#e8f4f8,stroke:#2b7fd0,color:#1a1d21
    class V,F,M,UPL,KPI,DASH,TABS,POSE,SMOO,ANGL,STRO,FITP,ALN,CORR node
```

## ASCII

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
                          ▼
   ┌────────────────────────────────────────────────────────┐
   │  lib/vision/  (pure Python pipeline)                    │
   │                                                          │
   │    pose.py          ──┐                                  │
   │    MediaPipe + OpenCV │                                  │
   │                       ▼                                  │
   │                   smoothing.py     fit.py                │
   │                   One-Euro +      garmin-fit-sdk         │
   │                   visibility        │                    │
   │                       │              │                   │
   │                       ▼              │                   │
   │                   angles.py          │                   │
   │                   knee/hip/elbow/    │                   │
   │                   shoulder/ankle     │                   │
   │                       │              │                   │
   │                       ▼              │                   │
   │                   strokes.py         │                   │
   │                   scipy.signal       │                   │
   │                   find_peaks         │                   │
   │                       │              │                   │
   │                       └──────┬───────┘                   │
   │                              ▼                            │
   │                          align.py                         │
   │                          cross-correlate                  │
   │                          pose × FIT cadence               │
   │                              │                            │
   │                              ▼                            │
   │                       correlations.py                     │
   │                       per-stroke fuse +                   │
   │                       Pearson r/n/p/CI                    │
   │                              │                            │
   │                              ▼                            │
   │                       AnalysisBundle                      │
   └──────────────────────────────────────────────────────────┘
```

## Notes

- **The two halves of the pipeline are decoupled.** `pose.py` doesn't know FIT exists; `fit.py` doesn't know about pose. They meet at `align.py` and `correlations.py`.
- **One-Euro smoothing runs after pose extraction**, not inside MediaPipe, so the smoothing parameters stay tunable without retraining anything.
- **The HTML component is a single iframe** containing both the `<video>` element and the Plotly chart, so a single JS `requestAnimationFrame` loop can read `vid.currentTime` and update the chart playhead + the skeleton canvas in lockstep. Streamlit's stock widgets don't expose video time, which is why we build a custom component.
- **Only one ML model in the system**: MediaPipe Pose Landmarker (`pose_landmarker_full.task`, BlazePose architecture). Everything downstream — smoothing, angles, strokes, alignment, correlations — is classical signal processing and statistics.
