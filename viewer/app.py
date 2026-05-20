"""Streamlit analysis dashboard — pose x telemetry on one screen.

Layout (top to bottom, single viewport):
  1. Title strip
  2. Source row: video upload + optional FIT upload + ride_id + Run button
  3. KPI tile strip (frames, fps, strokes, mean cadence, mean power, alignment r)
  4. Main split: video player | multi-trace chart with playhead + stroke bands
  5. Tabs: Strokes | Correlations | Diagnostics | Raw keypoints | Telemetry

The video and the chart live inside one HTML component so a JS playhead can
sync to the video's currentTime — Streamlit's stock widgets don't expose that.
"""

from __future__ import annotations

import base64
import io
import json
import math
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import polars as pl
import streamlit as st
import streamlit.components.v1 as components
from vision.align import estimate_offset_ms
from vision.angles import compute_angles
from vision.correlations import (
    attach_per_stroke_angle_summary,
    correlate_metrics,
    per_stroke_telemetry,
)
from vision.fit import parse_fit
from vision.pose import PoseExtractResult, extract_pose
from vision.smoothing import smooth_keypoints
from vision.strokes import segment_strokes

st.set_page_config(
    page_title="Vision — Cycling Analysis",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Sidebar: pipeline tuning. -------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Pipeline")
    visibility_threshold = st.slider(
        "Visibility gate",
        min_value=0.0,
        max_value=0.9,
        value=0.0,
        step=0.05,
        help=(
            "MediaPipe outputs a per-landmark visibility score (0..1). "
            "Landmarks below this threshold are NaN'd before smoothing. "
            "Default 0 = no gating. Motion blur drops visibility, so >0.3 "
            "tends to blank most of the chart on real video."
        ),
    )
    signal_col = st.selectbox(
        "Stroke-detection signal",
        options=[
            "left_knee_angle",
            "right_knee_angle",
            "left_hip_angle",
            "right_hip_angle",
            "left_ankle_angle",
            "right_ankle_angle",
        ],
        index=0,
        help="Per-frame angle fed to scipy.signal.find_peaks for stroke segmentation.",
    )
    show_skeleton = st.checkbox(
        "Draw pose skeleton on video",
        value=True,
        help="Overlays the MediaPipe landmarks and joint angle labels.",
    )
    skeleton_side = st.radio(
        "Skeleton side",
        options=["Both", "Left", "Right"],
        index=0,
        horizontal=True,
        help=(
            "On a side-on indoor-trainer shot the far-side landmarks have low "
            "visibility (the bike frame occludes them). Pick the side facing "
            "the camera for a cleaner overlay."
        ),
    )
    alignment_mode = st.radio(
        "FIT time alignment",
        options=["Auto (if confident)", "Force 0 offset", "Manual"],
        index=0,
        help=(
            "Auto: cross-correlate pose-cadence x FIT-cadence; apply offset only "
            "if Pearson r ≥ 0.4. Force 0: assume both signals start at the same "
            "moment. Manual: enter the offset below."
        ),
    )
    manual_offset_s = 0
    if alignment_mode == "Manual":
        manual_offset_s = st.number_input(
            "Manual offset (s, applied to FIT)",
            min_value=-300, max_value=300, value=0, step=1,
        )
    st.divider()
    st.markdown(
        "**Sample data.** A 60-second synthetic FIT lives at "
        "`samples/sample-ride.fit`. Note: it has no real biomechanical "
        "relationship with any of your real videos — it just verifies the "
        "FIT pipeline runs."
    )

# --- Dashboard chrome CSS. -----------------------------------------------------
# Tight vertical padding so KPIs, video+chart, and tabs all fit in one viewport.
# 2.5rem top padding keeps the Streamlit toolbar from overlapping the title.
st.markdown(
    """
<style>
.block-container { padding-top: 2.5rem; padding-bottom: 0.5rem; max-width: 100%; }
[data-testid="stFileUploader"] section { padding: 0.25rem 0.5rem; }
[data-testid="stFileUploader"] small { display: none; }
[data-testid="stMetric"] {
    background: #f4f6f8;
    border: 1px solid #e1e4e8;
    border-radius: 8px;
    padding: 0.45rem 0.7rem;
}
[data-testid="stMetricValue"] { font-size: 1.15rem; }
[data-testid="stMetricLabel"] { font-size: 0.72rem; opacity: 0.7; }
div[data-baseweb="tab-list"] { gap: 1.5rem; border-bottom: 1px solid #e1e4e8; }
div[data-baseweb="tab"] { padding: 0.3rem 0.2rem; }
hr { margin: 0.5rem 0; }
details[data-testid="stExpander"] summary { padding: 0.25rem 0.5rem; }
</style>
""",
    unsafe_allow_html=True,
)


@dataclass(frozen=True)
class AnalysisBundle:
    raw: PoseExtractResult
    smoothed: pl.DataFrame
    angles: pl.DataFrame
    strokes: pl.DataFrame
    telemetry: pl.DataFrame
    offset_ms: int  # actually applied to telemetry/chart
    raw_offset_ms: int  # what cross-correlation suggested before clamping
    alignment_score: float
    alignment_mode: str
    per_stroke: pl.DataFrame
    correlations: pl.DataFrame
    video_bytes: bytes
    filename: str
    ride_id: str


ALIGNMENT_CONFIDENCE_THRESHOLD = 0.4


def _run_pipeline(
    video_bytes: bytes,
    fit_bytes: bytes | None,
    ride_id: str,
    *,
    visibility_threshold: float = 0.0,
    signal_col: str = "left_knee_angle",
    alignment_mode: str = "Auto (if confident)",
    manual_offset_s: int = 0,
) -> AnalysisBundle:
    tmpdir = Path(tempfile.mkdtemp(prefix="vision-viewer-"))
    video_path = tmpdir / "input.mp4"
    video_path.write_bytes(video_bytes)
    raw = extract_pose(video_path, ride_id=ride_id)
    smoothed = smooth_keypoints(
        raw.keypoints,
        min_cutoff_hz=1.0,
        beta=0.05,
        visibility_threshold=visibility_threshold,
    )
    angles = compute_angles(smoothed)
    strokes = segment_strokes(angles, signal_col=signal_col)

    telemetry: pl.DataFrame
    raw_offset_ms = 0
    alignment_score = 0.0
    offset_ms = 0
    if fit_bytes is not None:
        fit_path = tmpdir / "activity.fit"
        fit_path.write_bytes(fit_bytes)
        telemetry = parse_fit(fit_path)
        if not telemetry.is_empty() and not strokes.is_empty():
            raw_offset_ms, alignment_score = estimate_offset_ms(strokes, telemetry)
        if alignment_mode == "Auto (if confident)":
            offset_ms = raw_offset_ms if alignment_score >= ALIGNMENT_CONFIDENCE_THRESHOLD else 0
        elif alignment_mode == "Manual":
            offset_ms = manual_offset_s * 1000
        else:  # "Force 0 offset"
            offset_ms = 0
    else:
        telemetry = pl.DataFrame()

    per_stroke = per_stroke_telemetry(strokes, telemetry, offset_ms=offset_ms)
    per_stroke = attach_per_stroke_angle_summary(per_stroke, angles)
    correlations = correlate_metrics(per_stroke)
    return AnalysisBundle(
        raw=raw,
        smoothed=smoothed,
        angles=angles,
        strokes=strokes,
        telemetry=telemetry,
        offset_ms=offset_ms,
        raw_offset_ms=raw_offset_ms,
        alignment_score=alignment_score,
        alignment_mode=alignment_mode,
        per_stroke=per_stroke,
        correlations=correlations,
        video_bytes=video_bytes,
        filename="upload",
        ride_id=ride_id,
    )


SKELETON_LANDMARKS: tuple[str, ...] = (
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
)


def _build_dashboard_html(
    video_b64: str,
    keypoints: pl.DataFrame,
    angles: pl.DataFrame,
    strokes: pl.DataFrame,
    telemetry: pl.DataFrame,
    offset_ms: int,
    height_px: int,
    signal_col: str,
    fps: float,
    show_skeleton: bool,
    skeleton_side: str = "Both",
) -> str:
    """Self-contained HTML+JS: video element + skeleton overlay + Plotly chart."""
    knee_pts: list[dict[str, float]] = []
    if not angles.is_empty() and signal_col in angles.columns:
        sub = angles.select(["timestamp_ms", signal_col]).drop_nulls()
        knee_pts = [
            {"t": int(r["timestamp_ms"]) / 1000.0, "v": float(r[signal_col])}
            for r in sub.iter_rows(named=True)
        ]
    power_pts: list[dict[str, float]] = []
    cadence_pts: list[dict[str, float]] = []
    if not telemetry.is_empty():
        for r in telemetry.iter_rows(named=True):
            t_s = (int(r["timestamp_ms"]) + offset_ms) / 1000.0
            if r.get("power_w") is not None and not _isnan(r["power_w"]):
                power_pts.append({"t": t_s, "v": float(r["power_w"])})
            if r.get("cadence_rpm") is not None and not _isnan(r["cadence_rpm"]):
                cadence_pts.append({"t": t_s, "v": float(r["cadence_rpm"])})

    stroke_bands = [
        {
            "start": int(s["timestamp_start_ms"]) / 1000.0,
            "end": int(s["timestamp_end_ms"]) / 1000.0,
        }
        for s in strokes.iter_rows(named=True)
    ]

    # Per-frame skeleton lookup. Only the landmarks we draw, rounded to 3dp.
    frames_payload: dict[str, dict[str, list[float]]] = {}
    if show_skeleton and not keypoints.is_empty():
        skel_set = set(SKELETON_LANDMARKS)
        sub_k = keypoints.filter(pl.col("landmark_name").is_in(list(skel_set)))
        for r in sub_k.iter_rows(named=True):
            fk = str(int(r["frame_index"]))
            x, y = float(r["x"]), float(r["y"])
            if math.isnan(x) or math.isnan(y):
                continue
            frames_payload.setdefault(fk, {})[str(r["landmark_name"])] = [
                round(x, 3), round(y, 3),
            ]

    # Per-frame angle labels.
    angle_keys = (
        "left_knee_angle", "right_knee_angle",
        "left_hip_angle", "right_hip_angle",
        "left_elbow_angle", "right_elbow_angle",
        "left_shoulder_angle", "right_shoulder_angle",
        "left_ankle_angle", "right_ankle_angle",
    )
    frame_angles_payload: dict[str, dict[str, float]] = {}
    if show_skeleton and not angles.is_empty():
        present = [k for k in angle_keys if k in angles.columns]
        for r in angles.iter_rows(named=True):
            fk = str(int(r["frame_index"]))
            entry: dict[str, float] = {}
            for k in present:
                v = r[k]
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    continue
                entry[k] = round(float(v), 1)
            if entry:
                frame_angles_payload[fk] = entry

    payload = {
        "knee": knee_pts,
        "power": power_pts,
        "cadence": cadence_pts,
        "strokes": stroke_bands,
        "signal_label": signal_col.replace("_", " "),
        "frames": frames_payload,
        "frame_angles": frame_angles_payload,
        "fps": fps,
        "show_skeleton": show_skeleton,
        "skeleton_side": skeleton_side.lower(),
    }
    payload_json = json.dumps(payload)

    template = """
<!doctype html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#ffffff;color:#1a1d21;
             font-family:-apple-system,system-ui,sans-serif;overflow:hidden">
  <div style="display:grid;grid-template-columns:380px 1fr;gap:10px;height:__HEIGHT__px">
    <div style="position:relative;width:380px;height:__HEIGHT__px">
      <video id="vid" controls preload="metadata"
             style="width:100%;height:100%;background:#000;object-fit:contain;border-radius:8px"
             src="data:video/mp4;base64,__VIDEO_B64__"></video>
      <canvas id="overlay"
              style="position:absolute;top:0;left:0;width:100%;height:100%;
                     pointer-events:none;border-radius:8px"></canvas>
    </div>
    <div id="chart" style="height:__HEIGHT__px;border-radius:8px;overflow:hidden;
                            border:1px solid #e1e4e8"></div>
  </div>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <script>
    (function () {
      const payload = __PAYLOAD__;
      function fmtTime(s) {
        const m = Math.floor(s / 60);
        const sec = Math.floor(s % 60);
        return m + ':' + (sec < 10 ? '0' + sec : sec);
      }
      const traces = [];
      if (payload.knee.length) {
        traces.push({
          x: payload.knee.map(p => p.t),
          y: payload.knee.map(p => p.v),
          mode: 'lines',
          name: payload.signal_label + ' (°)',
          line: { color: '#2b7fd0', width: 2 },
          yaxis: 'y',
          connectgaps: false,
        });
      }
      if (payload.power.length) {
        traces.push({
          x: payload.power.map(p => p.t),
          y: payload.power.map(p => p.v),
          mode: 'lines',
          name: 'Power (W)',
          line: { color: '#d97706', width: 1.5 },
          yaxis: 'y2',
        });
      }
      if (payload.cadence.length) {
        traces.push({
          x: payload.cadence.map(p => p.t),
          y: payload.cadence.map(p => p.v),
          mode: 'lines',
          name: 'Cadence (rpm)',
          line: { color: '#16a34a', width: 1.2, dash: 'dot' },
          yaxis: 'y',
          visible: 'legendonly',
        });
      }

      // Stroke bands as translucent vertical rectangles (every other stroke).
      const shapes = [];
      payload.strokes.forEach((s, i) => {
        if (i % 2 === 0) {
          shapes.push({
            type: 'rect', xref: 'x', yref: 'paper',
            x0: s.start, x1: s.end, y0: 0, y1: 1,
            fillcolor: 'rgba(43,127,208,0.07)',
            line: { width: 0 }, layer: 'below',
          });
        }
      });
      shapes.push({
        type: 'line', xref: 'x', yref: 'paper',
        x0: 0, x1: 0, y0: 0, y1: 1,
        line: { color: '#dc2626', width: 2 },
      });
      const playheadIndex = shapes.length - 1;

      const xs = [].concat(
        payload.knee.map(p => p.t),
        payload.power.map(p => p.t),
        payload.cadence.map(p => p.t)
      );
      const tMax = xs.length ? Math.max.apply(null, xs) : 1;

      // Pre-bake tick labels in MM:SS so the axis reads like a video player.
      const tickStep = tMax > 120 ? 30 : tMax > 60 ? 15 : tMax > 20 ? 5 : 2;
      const tickVals = [];
      for (let s = 0; s <= tMax; s += tickStep) tickVals.push(s);
      const tickText = tickVals.map(fmtTime);

      const layout = {
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff',
        font: { color: '#1a1d21', size: 11 },
        margin: { t: 30, r: 60, b: 30, l: 50 },
        title: {
          text: payload.signal_label + ' vs power · stroke bands shaded · red line = playhead',
          font: { size: 12, color: '#374151' },
        },
        xaxis: {
          tickvals: tickVals, ticktext: tickText,
          range: [0, tMax],
          gridcolor: '#eef0f3', zerolinecolor: '#d1d5db',
        },
        yaxis: {
          title: { text: payload.signal_label + ' (°)', font: { color: '#2b7fd0' } },
          tickfont: { color: '#2b7fd0' },
          gridcolor: '#eef0f3', zerolinecolor: '#d1d5db',
        },
        yaxis2: {
          title: { text: 'Power (W)', font: { color: '#d97706' } },
          tickfont: { color: '#d97706' },
          overlaying: 'y', side: 'right',
          gridcolor: 'rgba(0,0,0,0)',
        },
        legend: { orientation: 'h', x: 0, y: -0.14, font: { size: 10 } },
        shapes: shapes,
        hovermode: 'x unified',
      };
      Plotly.newPlot('chart', traces, layout,
                     { displayModeBar: false, responsive: true });

      const vid = document.getElementById('vid');
      const canvas = document.getElementById('overlay');
      const ctx = canvas.getContext('2d');
      const frames = payload.frames || {};
      const frameAngles = payload.frame_angles || {};
      const fps = payload.fps || 30;
      const showSkel = payload.show_skeleton;
      const side = payload.skeleton_side || 'both';
      function sideOf(name) {
        if (name.startsWith('left_')) return 'left';
        if (name.startsWith('right_')) return 'right';
        return 'center';
      }
      function edgeAllowed(a, b) {
        if (side === 'both') return true;
        const sa = sideOf(a), sb = sideOf(b);
        // Single-side mode hides cross-body edges; only edges fully on the
        // chosen side render.
        return sa === side && sb === side;
      }
      function landmarkAllowed(name) {
        if (side === 'both') return true;
        return sideOf(name) === side;
      }

      const edges = [
        ['left_shoulder', 'right_shoulder'],
        ['left_shoulder', 'left_elbow'], ['left_elbow', 'left_wrist'],
        ['right_shoulder', 'right_elbow'], ['right_elbow', 'right_wrist'],
        ['left_shoulder', 'left_hip'], ['right_shoulder', 'right_hip'],
        ['left_hip', 'right_hip'],
        ['left_hip', 'left_knee'], ['left_knee', 'left_ankle'],
        ['right_hip', 'right_knee'], ['right_knee', 'right_ankle'],
        ['left_ankle', 'left_heel'], ['left_heel', 'left_foot_index'],
        ['right_ankle', 'right_heel'], ['right_heel', 'right_foot_index'],
      ];
      const dotLandmarks = [
        'left_shoulder', 'right_shoulder',
        'left_elbow', 'right_elbow', 'left_wrist', 'right_wrist',
        'left_hip', 'right_hip',
        'left_knee', 'right_knee',
        'left_ankle', 'right_ankle',
      ];

      function videoRegion() {
        const rect = vid.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const vw = vid.videoWidth, vh = vid.videoHeight;
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = rect.height + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        if (!vw || !vh) return null;
        const scale = Math.min(rect.width / vw, rect.height / vh);
        const drawW = vw * scale, drawH = vh * scale;
        return {
          w: rect.width, h: rect.height,
          scale: scale, drawW: drawW, drawH: drawH,
          offX: (rect.width - drawW) / 2,
          offY: (rect.height - drawH) / 2,
        };
      }

      function drawSkeleton() {
        const region = videoRegion();
        if (!region) return;
        ctx.clearRect(0, 0, region.w, region.h);
        if (!showSkel) return;

        const fIdx = Math.floor(vid.currentTime * fps);
        let frame = frames[String(fIdx)];
        if (!frame) {
          // Find nearest available frame within ±5.
          for (let d = 1; d <= 5 && !frame; d++) {
            frame = frames[String(fIdx + d)] || frames[String(fIdx - d)];
          }
        }
        if (!frame) return;

        function pt(name) {
          const p = frame[name];
          if (!p) return null;
          return [region.offX + p[0] * region.drawW, region.offY + p[1] * region.drawH];
        }

        ctx.strokeStyle = '#22c55e';
        ctx.lineWidth = 2;
        edges.forEach(([a, b]) => {
          if (!edgeAllowed(a, b)) return;
          const pa = pt(a), pb = pt(b);
          if (pa && pb) {
            ctx.beginPath();
            ctx.moveTo(pa[0], pa[1]);
            ctx.lineTo(pb[0], pb[1]);
            ctx.stroke();
          }
        });

        ctx.fillStyle = '#dc2626';
        dotLandmarks.forEach(name => {
          if (!landmarkAllowed(name)) return;
          const p = pt(name);
          if (p) {
            ctx.beginPath();
            ctx.arc(p[0], p[1], 4, 0, 2 * Math.PI);
            ctx.fill();
          }
        });

        const ang = frameAngles[String(fIdx)] || {};
        ctx.font = 'bold 11px -apple-system,system-ui,sans-serif';
        function lbl(loc, val, label) {
          if (val == null || isNaN(val)) return;
          if (!landmarkAllowed(loc)) return;
          const p = pt(loc);
          if (!p) return;
          const text = label + ' ' + Math.round(val) + '°';
          ctx.lineWidth = 3;
          ctx.strokeStyle = 'rgba(0,0,0,0.85)';
          ctx.strokeText(text, p[0] + 8, p[1] - 6);
          ctx.fillStyle = '#fef9c3';
          ctx.fillText(text, p[0] + 8, p[1] - 6);
        }
        lbl('left_knee', ang.left_knee_angle, 'L knee');
        lbl('right_knee', ang.right_knee_angle, 'R knee');
        lbl('left_hip', ang.left_hip_angle, 'L hip');
        lbl('right_hip', ang.right_hip_angle, 'R hip');
        lbl('left_elbow', ang.left_elbow_angle, 'L elb');
        lbl('right_elbow', ang.right_elbow_angle, 'R elb');
        lbl('left_shoulder', ang.left_shoulder_angle, 'L sh');
        lbl('right_shoulder', ang.right_shoulder_angle, 'R sh');
        lbl('left_ankle', ang.left_ankle_angle, 'L ank');
        lbl('right_ankle', ang.right_ankle_angle, 'R ank');
      }

      let rafId = null;
      function setPlayhead() {
        const t = vid.currentTime;
        const upd = {};
        upd['shapes[' + playheadIndex + '].x0'] = t;
        upd['shapes[' + playheadIndex + '].x1'] = t;
        Plotly.relayout('chart', upd);
      }
      function loop() {
        setPlayhead();
        drawSkeleton();
        rafId = requestAnimationFrame(loop);
      }
      vid.addEventListener('play', function () { if (!rafId) loop(); });
      vid.addEventListener('pause', function () {
        if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
        setPlayhead();
        drawSkeleton();
      });
      vid.addEventListener('seeked', function () { setPlayhead(); drawSkeleton(); });
      vid.addEventListener('loadedmetadata', function () { setPlayhead(); drawSkeleton(); });
      window.addEventListener('resize', drawSkeleton);
    })();
  </script>
</body></html>
"""
    return (
        template.replace("__HEIGHT__", str(height_px))
        .replace("__VIDEO_B64__", video_b64)
        .replace("__PAYLOAD__", payload_json)
    )


def _isnan(x: object) -> bool:
    return isinstance(x, float) and math.isnan(x)


# =====================================================================
# HEADER STRIP + HOW-TO EXPANDER
# =====================================================================
hdr_l, hdr_r = st.columns([5, 1])
with hdr_l:
    st.markdown("#### 🚴 Vision — Cycling Form & Performance")
with hdr_r:
    st.caption("Pipeline settings →")

with st.expander("How to read this dashboard", expanded=False):
    st.markdown(
        """
**KPI tiles** — at-a-glance pipeline stats. Hover any tile for a definition.

**Video + chart** — playback is synchronized. As the video plays, a red
vertical line on the chart marks where you are.

- **Blue line:** the chosen joint angle over time (default `left_knee_angle`).
  Up-and-down cycles = pedal strokes. Min ≈ TDC (knee most flexed), max ≈ BDC (knee most extended).
- **Orange line (right axis):** power in watts, from FIT (if uploaded).
- **Green dotted line:** cadence in rpm, from FIT — off by default, toggle in the legend.
- **Shaded bands:** every other detected pedal stroke, segmented from the joint angle by
  `scipy.signal.find_peaks`.

**The whole point:** correlate what your body is doing (left axis) with what the
bike is producing (right axis). E.g. *"knee extension drops in the last 5 strokes
as power rises"*.

**Skeleton overlay** — green segments + red dots are MediaPipe pose landmarks.
Joint angles (e.g. `L knee 96°`) are computed from the smoothed landmarks each
frame. Use the sidebar to hide it or restrict to one side of the body.

**Tabs**

- *Strokes* — one row per detected pedal revolution with cadence, duration, and (if FIT) mean power.
- *Correlations* — Pearson r + p-value + 95% CI between every pair of per-stroke metrics.
- *Diagnostics* — mean MediaPipe visibility per landmark. Below 0.3 ≈ unreliable.
- *Keypoints* — the smoothed pose landmark table for downstream analysis (Parquet download).
- *Telemetry* — the parsed FIT records.
"""
    )

# =====================================================================
# SOURCES + RUN — collapses once a video is loaded.
# =====================================================================
already_loaded = "bundle" in st.session_state
loaded_summary = ""
if already_loaded:
    fname = st.session_state.get("last_inputs", ("", ""))[0] or ""
    fit_label = st.session_state.get("last_inputs", ("", ""))[1] or "—"
    loaded_summary = f" · 🎞 {fname} · 📊 FIT: {fit_label}"

with st.expander(
    f"📁 Sources{loaded_summary}",
    expanded=not already_loaded,
):
    s1, s2, s3, s4 = st.columns([3, 3, 1, 1])
    with s1:
        video_upload = st.file_uploader(
            "Video (mp4/mov/avi)",
            type=["mp4", "mov", "avi"],
            help="The cycling video to analyze. MediaPipe Pose Landmarker runs on every frame.",
        )
    with s2:
        fit_upload = st.file_uploader(
            "FIT telemetry (optional)",
            type=["fit"],
            help=(
                "Garmin .fit file with per-second power/cadence/heart-rate. Unlocks the "
                "Correlations tab. Try samples/sample-ride.fit if you don't have one."
            ),
        )
    with s3:
        ride_id = st.text_input(
            "ride_id", value="upload",
            help="Tag every row written to Parquet with this identifier.",
        )
    with s4:
        st.write("")
        run_clicked = st.button(
            "Run analysis",
            use_container_width=True,
            help="Manual override — the pipeline auto-reruns on any input change.",
        )

if video_upload is None:
    st.info(
        "Upload a video to begin. Tip: the project ships a synthetic FIT at "
        "`samples/sample-ride.fit` — upload it next to your video to see the "
        "full pose x telemetry correlation pipeline run (otherwise the dashboard "
        "shows pose-only metrics)."
    )
    if "bundle" in st.session_state:
        del st.session_state["bundle"]
    st.stop()

current_filename = video_upload.name
fit_filename_current = fit_upload.name if fit_upload else None

# Any input change re-runs automatically; Run analysis is the manual override
# (useful for replaying with the same inputs after tweaking a sidebar value).
inputs_key = (
    current_filename,
    fit_filename_current,
    ride_id,
    visibility_threshold,
    signal_col,
    alignment_mode,
    manual_offset_s,
)
inputs_changed = st.session_state.get("last_inputs") != inputs_key

if run_clicked or inputs_changed:
    with st.spinner("Pose → smoothing → angles → strokes → alignment → correlations..."):
        bundle = _run_pipeline(
            video_bytes=video_upload.getvalue(),
            fit_bytes=fit_upload.getvalue() if fit_upload is not None else None,
            ride_id=ride_id,
            visibility_threshold=visibility_threshold,
            signal_col=signal_col,
            alignment_mode=alignment_mode,
            manual_offset_s=int(manual_offset_s),
        )
        st.session_state["bundle"] = bundle
        st.session_state["last_inputs"] = inputs_key
    st.rerun()

if "bundle" not in st.session_state:
    st.warning("Click **Run analysis** to process the uploaded video.")
    st.stop()

bundle = cast(AnalysisBundle, st.session_state["bundle"])

# =====================================================================
# KPI TILES
# =====================================================================
mean_cad = (
    float(bundle.strokes["cadence_rpm"].mean()) if not bundle.strokes.is_empty() else math.nan
)
mean_power = (
    float(bundle.per_stroke["mean_power_w"].mean())
    if not bundle.per_stroke.is_empty() and "mean_power_w" in bundle.per_stroke.columns
    else math.nan
)
if bundle.telemetry.is_empty():
    align_value = "no FIT"
    align_help = "Upload a .fit file to see alignment."
else:
    align_value = f"r={bundle.alignment_score:.2f} @ {bundle.offset_ms / 1000:+.1f}s"
    is_auto = bundle.alignment_mode == "Auto (if confident)"
    was_clamped = is_auto and bundle.offset_ms == 0 and bundle.raw_offset_ms != 0
    raw_s = bundle.raw_offset_ms / 1000
    if was_clamped:
        align_help = (
            f"Auto-alignment confidence too low (r={bundle.alignment_score:.2f}); "
            f"clamped from raw {raw_s:+.1f}s to 0. Switch sidebar to Manual to override."
        )
    else:
        align_help = f"Mode: {bundle.alignment_mode}. Raw cross-corr: {raw_s:+.1f}s."

# Pose quality = % of frames where the signal_col is non-NaN.
if bundle.angles.is_empty() or signal_col not in bundle.angles.columns:
    pose_quality = 0.0
else:
    valid = bundle.angles[signal_col].drop_nulls().to_numpy()
    n_valid = int((valid == valid).sum())  # filters out NaN (NaN != NaN)
    pose_quality = 100.0 * float(n_valid) / max(1, bundle.raw.frame_count)

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric(
    "Frames",
    f"{bundle.raw.frame_count:,}",
    help="Total video frames MediaPipe ran pose detection on.",
)
k2.metric(
    "FPS",
    f"{bundle.raw.fps:.1f}",
    help="Frames per second decoded from the video container.",
)
k3.metric(
    "Strokes",
    f"{bundle.strokes.height}",
    help="Pedal revolutions detected from peaks in the chosen joint-angle signal.",
)
k4.metric(
    "Cadence (pose)",
    f"{mean_cad:.0f} rpm" if not math.isnan(mean_cad) else "—",
    help="Mean stroke cadence derived from pose, in revolutions per minute.",
)
k5.metric(
    "Power",
    f"{mean_power:.0f} W" if not math.isnan(mean_power) else "—",
    help="Mean per-stroke power from FIT telemetry (— means no FIT uploaded or alignment failed).",
)
k6.metric("Alignment", align_value, help=align_help)
k7.metric(
    "Pose quality",
    f"{pose_quality:.0f}%",
    help="Share of video frames where the chosen joint angle is computable (non-NaN).",
)

# =====================================================================
# MAIN SPLIT VIEW
# =====================================================================
video_b64 = base64.b64encode(bundle.video_bytes).decode("ascii")
dashboard_html = _build_dashboard_html(
    video_b64=video_b64,
    keypoints=bundle.smoothed,
    angles=bundle.angles,
    strokes=bundle.strokes,
    telemetry=bundle.telemetry,
    offset_ms=bundle.offset_ms,
    height_px=320,
    signal_col=signal_col,
    fps=bundle.raw.fps,
    show_skeleton=show_skeleton,
    skeleton_side=skeleton_side,
)
components.html(dashboard_html, height=335, scrolling=False)

# =====================================================================
# TABS — STROKES / CORRELATIONS / DIAGNOSTICS / RAW / TELEMETRY
# =====================================================================
tab_strokes, tab_corr, tab_diag, tab_raw, tab_telem = st.tabs(
    ["Strokes", "Correlations", "Diagnostics", "Keypoints", "Telemetry"]
)

with tab_strokes:
    st.caption(
        "**One row per detected pedal revolution.** `cadence_rpm` is derived from "
        "pose (period between consecutive joint-angle peaks). `mean_knee_angle_min` "
        "≈ knee flexion at TDC; `_max` ≈ extension at BDC. `mean_power_w` / "
        "`mean_cadence_fit_rpm` / `mean_heart_rate_bpm` are averaged from FIT "
        "telemetry within each stroke window (only populated when FIT is uploaded)."
    )
    if bundle.per_stroke.is_empty():
        st.warning(
            "No strokes detected. Common causes: (1) the rider isn't visible in frame, "
            "(2) MediaPipe's visibility score is too low — turn the **Visibility gate** "
            "slider down (default already 0), or (3) the filming protocol "
            "(`docs/filming-protocol.md`) was violated. See the **Diagnostics** tab."
        )
    else:
        st.dataframe(bundle.per_stroke.to_pandas(), use_container_width=True, height=170)

with tab_corr:
    st.caption(
        "**Pearson r between every pair of per-stroke metrics.** "
        "`effect` follows Cohen's conventions (|r| ≥ 0.5 large, ≥ 0.3 medium). "
        "`p_value` < 0.05 means the correlation is statistically distinguishable from "
        "zero at one stroke level (no multiple-comparison correction applied — for real "
        "claims apply Bonferroni/BH). `ci_low`..`ci_high` is the 95% Fisher-z CI; "
        "intervals crossing zero are not significant."
    )
    if bundle.correlations.is_empty():
        st.info(
            "Correlations need both pose strokes and FIT telemetry. Upload a FIT file "
            "next to the video — `samples/sample-ride.fit` is a synthetic one you can "
            "use to verify the pipeline."
        )
    else:
        df_corr = bundle.correlations.to_pandas()
        df_corr["effect"] = df_corr["r"].abs().apply(
            lambda r: "large" if r >= 0.5 else "medium" if r >= 0.3 else "small"
        )
        st.dataframe(
            df_corr.style.format(
                {"r": "{:+.3f}", "p_value": "{:.4f}", "ci_low": "{:+.3f}", "ci_high": "{:+.3f}"}
            ),
            use_container_width=True,
            height=170,
        )

with tab_diag:
    st.caption(
        "**Mean MediaPipe visibility per major landmark across the whole video.** "
        "Visibility is MediaPipe's per-frame confidence that a landmark is visible "
        "in the image. Anything ≤ ~0.3 is unreliable — typical on a side-on shot "
        "where the bike frame occludes the far-side hip/knee/ankle. If the landmark "
        "feeding stroke detection is consistently low here, switch the sidebar's "
        "Stroke-detection signal to the other side."
    )
    if bundle.raw.keypoints.is_empty():
        st.warning("No pose detected at all — MediaPipe found no rider.")
    else:
        import plotly.express as px

        landmark_summary = (
            bundle.raw.keypoints.group_by("landmark_name")
            .agg(
                [
                    pl.col("visibility").mean().alias("mean_visibility"),
                    pl.col("visibility").min().alias("min_visibility"),
                    pl.col("visibility").max().alias("max_visibility"),
                ]
            )
            .sort("mean_visibility")
        )

        important = [
            "left_shoulder", "right_shoulder",
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
            "left_hip", "right_hip",
            "left_knee", "right_knee",
            "left_ankle", "right_ankle",
            "left_heel", "right_heel",
            "left_foot_index", "right_foot_index",
        ]
        focused = landmark_summary.filter(pl.col("landmark_name").is_in(important))
        fig = px.bar(
            focused.to_pandas(),
            x="mean_visibility",
            y="landmark_name",
            orientation="h",
            range_x=[0, 1],
        )
        fig.update_layout(
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font={"color": "#1a1d21", "size": 10},
            height=180,
            margin={"t": 4, "r": 20, "b": 24, "l": 110},
        )
        fig.update_traces(marker_color="#2b7fd0")
        fig.update_xaxes(gridcolor="#eef0f3", title=None)
        fig.update_yaxes(gridcolor="#eef0f3", title=None)
        st.plotly_chart(fig, use_container_width=True)

with tab_raw:
    st.caption(
        "**The smoothed pose landmark table** — one row per (frame, landmark), 33 "
        "MediaPipe landmarks per frame. `x`, `y` are normalized image coordinates "
        "in [0, 1] after One-Euro smoothing. Use the Parquet download for downstream "
        "analysis in pandas / Polars / BigQuery."
    )
    dl_col, _spacer = st.columns([1, 5])
    buf = io.BytesIO()
    bundle.smoothed.write_parquet(buf)
    dl_col.download_button(
        f"Download keypoints.parquet ({len(bundle.smoothed):,} rows)",
        data=buf.getvalue(),
        file_name=f"{bundle.ride_id}-keypoints.parquet",
        mime="application/octet-stream",
    )
    st.dataframe(bundle.smoothed.head(40).to_pandas(), use_container_width=True, height=140)

with tab_telem:
    st.caption(
        "**Per-second FIT records as decoded by garmin-fit-sdk.** `timestamp_ms` is "
        "milliseconds since the first record in the FIT file (offset BEFORE alignment "
        "is applied — the dashboard chart applies the alignment offset on the fly)."
    )
    if bundle.telemetry.is_empty():
        st.info("No FIT file uploaded.")
    else:
        st.dataframe(bundle.telemetry.head(40).to_pandas(), use_container_width=True, height=160)
