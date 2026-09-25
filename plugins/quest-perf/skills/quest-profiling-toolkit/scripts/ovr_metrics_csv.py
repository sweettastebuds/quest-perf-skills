#!/usr/bin/env python3
"""OVR Metrics Tool CSV analyzer for Meta Quest 2 / 3 / 3S captures.

Stdlib only, Python 3.10+.

Usage:
    python ovr_metrics_csv.py <capture.csv> [--hz 72] [--window-min 5] [--json]
                              [--segment-column NAME] [--keep-warmup]

What it reports (all figures come from the CSV itself):
  * p50 / p95 / p99 of app GPU time (``app_gpu_time_microseconds``) and of the
    per-row frame interval derived from ``average_frame_rate`` (1e6 / fps).
    CSV rows are ~1 Hz interval averages (quest.md Q1-010), so these are
    percentiles over per-second rows, NOT per-frame values. Use Perfetto for
    frame-level pacing.
  * Stale frames per minute and the maximum stale frames in any 60 s window
    (Performance Analytics uses 60 s windows, QUEST-GF2-013).
  * Both candidate "hitch rate" definitions, because Meta's "hitches below 3%"
    rule does not define its denominator (QUEST-GF1-003, QUEST-GF2-012):
      A = stale frames / rendered frames
      B = rows (seconds) with stale_frames_consecutive >= 4 / all rows
  * Dips below 65 fps at 72 Hz (the only published dip tolerance, Q1-090).
  * CPU/GPU utilisation, levels and clocks per minute; phase_sync_mode and
    extra_latency_mode passed through raw (their values are undefined by Meta,
    QUEST-GF2-002).
  * Thermal drift between the first and last --window-min minutes: battery or
    sensor temperature when present, plus power_level_state, levels, clocks,
    render_scale, FPS, app GPU time and stale rate.
  * Per-segment summaries when the capture carries AppendCsvDebugString text
    (Q1-020). Meta documents that the string lands in the last CSV column but
    not that column's header name, so the analyzer uses a header containing
    "debug", a --segment-column you name, or any trailing field beyond the
    header.

Parsing rules (quest.md section 12):
  * Columns are matched by header name, never by position (Q1-012). Names are
    case-folded; spaces and hyphens become underscores; "celsius" is accepted
    for Meta's misspelt "celcius".
  * Unit suffixes are normalised: _microseconds / _milliseconds / _seconds are
    converted to microseconds (Q1-013).
  * Negative values are missing. 999 and 9999 are placeholders and are missing
    in every column except *_microseconds and the timestamp, where they are
    plausible measurements (Q1-017).
  * Leading rows whose eye_buffer_width is 0 are warm-up rows and are excluded
    unless --keep-warmup is given (QUEST-GF1-008).
  * app_gpu_time_microseconds values at 65535 are flagged as possibly clamped
    (Q1-018, community report, verify on device).
  * Rows whose metric columns are all empty (extra rows written by calling
    AppendCsvDebugString faster than 1 Hz, Q1-020) only update the segment.

Exit codes: 0 ok, 2 unreadable or unrecognised CSV.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

CLAMP_US = 65535  # Q1-018 [community]
PLACEHOLDERS = {999.0, 9999.0}  # Q1-017
DIP_FPS_AT_72 = 65.0  # Q1-090, 72 Hz only
CONSEC_HITCH = 4  # QUEST-GF1-003 "four or more consecutive missed frames"
CONSEC_NOTICE = 2  # QUEST-GF2-012 "two or three" in a row are noticed

TIME_UNITS = OrderedDict(
    [("_microseconds", 1.0), ("_milliseconds", 1000.0), ("_seconds", 1e6), ("_us", 1.0), ("_ms", 1000.0)]
)

# key -> (list of base names, is_time)
SPECS: dict[str, tuple[list[str], bool]] = {
    "fps": (["average_frame_rate", "fps"], False),
    "refresh": (["display_refresh_rate"], False),
    "app_gpu_us": (["app_gpu_time"], True),
    "tw_gpu_us": (["timewarp_gpu_time"], True),
    "stale": (["stale_frame_count", "stale_frames"], False),
    "stale_consec": (["stale_frames_consecutive", "max_consecutive_stale_frames"], False),
    "early": (["early_frame_count"], False),
    "tear": (["screen_tear_count"], False),
    "max_repeated": (["max_repeated_frames"], False),
    "skipped": (["skipped_frames"], False),
    "shader_hitches": (["shader_hitches"], False),
    "cpu_level": (["cpu_level"], False),
    "gpu_level": (["gpu_level"], False),
    "cpu_mhz": (["cpu_frequency_mhz"], False),
    "gpu_mhz": (["gpu_frequency_mhz"], False),
    "mem_mhz": (["mem_frequency_mhz"], False),
    "cpu_util": (["cpu_utilization_percentage"], False),
    "gpu_util": (["gpu_utilization_percentage"], False),
    "pls": (["power_level_state"], False),
    "batt_temp_c": (["battery_temperature_celcius"], False),
    "sensor_temp_c": (["sensor_temperature_celcius"], False),
    "power_w": (["power_wattage"], False),
    "battery_pct": (["battery_level_percentage"], False),
    "render_scale": (["render_scale"], False),
    "eye_w": (["eye_buffer_width"], False),
    "eye_h": (["eye_buffer_height"], False),
    "foveation_level": (["foveation_level"], False),
    "dynres_pct": (["dynres_recommendation_percentage"], False),
    "phase_sync": (["phase_sync_mode"], False),
    "extra_latency": (["extra_latency_mode"], False),
    "pred_us": (["average_prediction"], True),
    "icfl_mean_us": (["icfl_mean"], True),
    "slice_headroom_mean_us": (["slice_headroom_mean"], True),
    "app_pss_mb": (["app_pss_mb"], False),
    "app_gpu_physical_mb": (["app_gpu_physical_mb"], False),
}
TIME_KEYS = ["time_stamp", "timestamp", "time"]
CORE_KEYS = ("fps", "app_gpu_us", "stale")  # at least one must exist


class FormatError(Exception):
    pass


def norm(name: str) -> str:
    s = name.strip().strip(chr(0xFEFF)).lower()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.replace("celsius", "celcius")


def pct(values: list[float], p: float) -> float | None:
    """Linear-interpolation percentile (same as statistics.quantiles 'inclusive')."""
    if not values:
        return None
    v = sorted(values)
    if len(v) == 1:
        return v[0]
    k = (len(v) - 1) * p / 100.0
    lo = math.floor(k)
    hi = math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def rnd(x, n=2):
    return None if x is None else round(x, n)


class Capture:
    def __init__(self, path: Path, segment_column: str | None, keep_warmup: bool):
        self.path = path
        self.notes: list[str] = []
        try:
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as e:
            raise FormatError(f"cannot read {path}: {e}") from e
        rows = list(csv.reader(raw.splitlines()))
        rows = [r for r in rows if any(c.strip() for c in r)]
        if len(rows) < 2:
            raise FormatError(f"{path}: fewer than 2 non-empty lines; not an OVR Metrics CSV")
        self.header_raw = rows[0]
        self.header = [norm(h) for h in rows[0]]
        self.index = {}
        for i, h in enumerate(self.header):
            self.index.setdefault(h, i)
        self.cols: dict[str, tuple[int, float, str]] = {}  # key -> (col idx, factor, header name)
        for key, (bases, is_time) in SPECS.items():
            hit = self._resolve(bases, is_time)
            if hit:
                self.cols[key] = hit
        self.time_idx = next((self.index[k] for k in TIME_KEYS if k in self.index), None)
        if not any(k in self.cols for k in CORE_KEYS):
            shown = ", ".join(self.header_raw[:12])
            raise FormatError(
                f"{path}: unrecognised header. Expected OVR Metrics Tool columns such as "
                f"'average_frame_rate', 'app_gpu_time_microseconds' or 'stale_frame_count'. "
                f"First columns seen: {shown}"
            )
        if self.time_idx is None:
            self.notes.append("No 'Time Stamp' column: assuming one row per 1000 ms.")
        # segment column
        self.seg_idx = None
        if segment_column:
            n = norm(segment_column)
            if n not in self.index:
                raise FormatError(f"{path}: --segment-column {segment_column!r} not in header")
            self.seg_idx = self.index[n]
        else:
            for i, h in enumerate(self.header):
                if "debug" in h:
                    self.seg_idx = i
                    break
        self.metric_idx = sorted({c[0] for c in self.cols.values()})
        self._build(rows[1:], keep_warmup)

    def _resolve(self, bases: list[str], is_time: bool):
        for b in bases:
            if is_time:
                for suf, f in TIME_UNITS.items():
                    if b + suf in self.index:
                        return (self.index[b + suf], f, self.header_raw[self.index[b + suf]])
                if b in self.index:
                    self.notes.append(f"Column '{b}' has no unit suffix; assuming microseconds.")
                    return (self.index[b], 1.0, self.header_raw[self.index[b]])
            elif b in self.index:
                return (self.index[b], 1.0, self.header_raw[self.index[b]])
        return None

    def _val(self, row: list[str], idx: int, factor: float, is_us: bool):
        if idx >= len(row):
            return None
        s = row[idx].strip()
        if not s:
            return None
        try:
            v = float(s)
        except ValueError:
            return None
        if math.isnan(v) or v < 0:
            self.dropped += 1
            return None
        if not is_us and v in PLACEHOLDERS:
            self.dropped += 1
            return None
        return v * factor

    def _scan_placeholders(self, row: list[str]) -> None:
        """Count placeholder (999/9999) and negative values in every column (Q1-017)."""
        for i, h in enumerate(self.header):
            if i >= len(row) or i == self.time_idx or i == self.seg_idx or h.endswith("_microseconds"):
                continue
            s = row[i].strip()
            if not s:
                continue
            try:
                v = float(s)
            except ValueError:
                continue
            if v < 0 or v in PLACEHOLDERS:
                self.placeholders[self.header_raw[i]] += 1

    def _build(self, body: list[list[str]], keep_warmup: bool):
        self.dropped = 0
        self.placeholders: Counter = Counter()
        self.data: list[dict] = []
        seg = None
        ncols = len(self.header)
        auto_seg = self.seg_idx is None
        last_t = None
        for n, row in enumerate(body):
            # segment text
            text = None
            if self.seg_idx is not None and self.seg_idx < len(row):
                text = row[self.seg_idx].strip() or None
            elif auto_seg and len(row) > ncols:
                text = ",".join(row[ncols:]).strip() or None
            if text:
                seg = text
            has_metric = any(i < len(row) and row[i].strip() for i in self.metric_idx)
            if not has_metric:
                continue
            if self.time_idx is not None and self.time_idx < len(row):
                try:
                    t = float(row[self.time_idx])
                except ValueError:
                    t = (last_t + 1000.0) if last_t is not None else 1000.0
            else:
                t = (last_t + 1000.0) if last_t is not None else 1000.0
            last_t = t
            self._scan_placeholders(row)
            rec = {"t": t, "segment": seg}
            for key, (idx, f, hname) in self.cols.items():
                is_us = SPECS[key][1] or norm(hname).endswith("_microseconds")
                rec[key] = self._val(row, idx, f, is_us)
            self.data.append(rec)
        if not self.data:
            raise FormatError(f"{self.path}: header recognised but no data rows")
        self.data.sort(key=lambda r: r["t"])
        # eye buffer 0 in early rows -> missing / warm-up (QUEST-GF1-008)
        self.warmup_rows = 0
        if "eye_w" in self.cols:
            nz = [i for i, r in enumerate(self.data) if r.get("eye_w")]
            if nz and nz[0] > 0 and not keep_warmup:
                self.warmup_rows = nz[0]
                self.data = self.data[nz[0]:]
            for r in self.data:
                if r.get("eye_w") == 0:
                    r["eye_w"] = None
        if not self.data:
            raise FormatError(f"{self.path}: no data rows after warm-up")
        # per-row interval (s)
        ts = [r["t"] for r in self.data]
        diffs = [b - a for a, b in zip(ts, ts[1:]) if b > a]
        med = sorted(diffs)[len(diffs) // 2] if diffs else 1000.0
        for i, r in enumerate(self.data):
            d = (ts[i] - ts[i - 1]) if i > 0 else med
            r["dt"] = (d if d > 0 else med) / 1000.0
        self.row_interval_ms = med

    def series(self, key: str, rows: list[dict] | None = None) -> list[float]:
        rows = self.data if rows is None else rows
        return [r[key] for r in rows if r.get(key) is not None]


def refresh_hz(cap: Capture, override: float | None) -> tuple[float, str]:
    if override:
        return override, "--hz"
    rr = cap.series("refresh")
    if rr:
        return float(Counter(round(x) for x in rr).most_common(1)[0][0]), "display_refresh_rate (mode)"
    cap.notes.append("No display_refresh_rate column and no --hz; assuming 72 Hz.")
    return 72.0, "assumed"


def stale_window_max(rows: list[dict], window_ms: float = 60000.0) -> float | None:
    pts = [(r["t"], r["stale"]) for r in rows if r.get("stale") is not None]
    if not pts:
        return None
    best = 0.0
    j = 0
    acc = 0.0
    for i in range(len(pts)):
        while j < len(pts) and pts[j][0] < pts[i][0] + window_ms:
            acc += pts[j][1]
            j += 1
        best = max(best, acc)
        acc -= pts[i][1]
    return best


def dip_episodes(rows: list[dict], threshold: float) -> tuple[int, int]:
    below = 0
    episodes = 0
    prev = False
    for r in rows:
        f = r.get("fps")
        cur = f is not None and f < threshold
        below += cur
        if cur and not prev:
            episodes += 1
        prev = cur
    return below, episodes


def summarize(cap: Capture, rows: list[dict], hz: float) -> dict:
    budget_us = 1e6 / hz
    dur_s = sum(r["dt"] for r in rows)
    out: dict = {"rows": len(rows), "duration_min": rnd(dur_s / 60.0, 2)}
    gpu = cap.series("app_gpu_us", rows)
    if gpu:
        out["app_gpu_time_ms"] = {
            "source": cap.cols["app_gpu_us"][2],
            "mean": rnd(mean(gpu) / 1000, 3),
            "p50": rnd(pct(gpu, 50) / 1000, 3),
            "p95": rnd(pct(gpu, 95) / 1000, 3),
            "p99": rnd(pct(gpu, 99) / 1000, 3),
            "max": rnd(max(gpu) / 1000, 3),
            "rows_over_budget": sum(1 for g in gpu if g > budget_us),
            "rows_at_65535_clamp": sum(1 for g in gpu if g >= CLAMP_US),
        }
    fps = [f for f in cap.series("fps", rows) if f > 0]
    if fps:
        iv = [1e6 / f for f in fps]
        out["frame_interval_ms_from_fps"] = {
            "source": cap.cols["fps"][2] + " (1e6/fps per row)",
            "mean_fps": rnd(mean(fps), 2),
            "min_fps": rnd(min(fps), 2),
            "p50": rnd(pct(iv, 50) / 1000, 3),
            "p95": rnd(pct(iv, 95) / 1000, 3),
            "p99": rnd(pct(iv, 99) / 1000, 3),
        }
    stale = cap.series("stale", rows)
    if stale:
        total = sum(stale)
        rendered = sum((r["fps"] or 0) * r["dt"] for r in rows if r.get("fps") is not None)
        consec = cap.series("stale_consec", rows)
        out["stale"] = {
            "total": rnd(total, 0),
            "per_minute": rnd(total / (dur_s / 60.0), 2) if dur_s > 0 else None,
            "max_in_any_60s_window": rnd(stale_window_max(rows), 0),
            "rows_with_stale": sum(1 for s in stale if s > 0),
        }
        out["hitch_rate"] = {
            "A_stale_over_rendered_frames_pct": rnd(100.0 * total / rendered, 3) if rendered else None,
            "B_rows_with_consecutive_ge4_pct": rnd(100.0 * sum(1 for c in consec if c >= CONSEC_HITCH) / len(consec), 3)
            if consec
            else None,
            "rows_with_consecutive_ge2": sum(1 for c in consec if c >= CONSEC_NOTICE) if consec else None,
            "max_consecutive_stale": rnd(max(consec), 0) if consec else None,
            "note": "Meta's 'hitches below 3%' has no published denominator; both A and B are reported.",
        }
    for key, label in (
        ("shader_hitches", "shader_hitches"),
        ("max_repeated", "max_repeated_frames"),
        ("skipped", "skipped_frames"),
        ("early", "early_frame_count"),
        ("tear", "screen_tear_count"),
    ):
        s = cap.series(key, rows)
        if s:
            out.setdefault("other_counters", {})[label] = {
                "sum": rnd(sum(s), 0),
                "max": rnd(max(s), 0),
                "rows_nonzero": sum(1 for x in s if x > 0),
            }
    if round(hz) == 72 and fps:
        below, eps = dip_episodes(rows, DIP_FPS_AT_72)
        out["dips_below_65fps_at_72hz"] = {"rows": below, "episodes": eps}
    for key in ("phase_sync", "extra_latency"):
        s = cap.series(key, rows)
        if s:
            out.setdefault("timing_mode_raw", {})[cap.cols[key][2]] = {
                str(int(k) if float(k).is_integer() else k): v for k, v in sorted(Counter(s).items())
            }
    return out


WINDOW_METRICS = [
    ("batt_temp_c", "battery_temperature_celcius"),
    ("sensor_temp_c", "sensor_temperature_celcius"),
    ("pls", "power_level_state"),
    ("cpu_level", "cpu_level"),
    ("gpu_level", "gpu_level"),
    ("cpu_mhz", "cpu_frequency_MHz"),
    ("gpu_mhz", "gpu_frequency_MHz"),
    ("mem_mhz", "mem_frequency_MHz"),
    ("cpu_util", "cpu_utilization_percentage"),
    ("gpu_util", "gpu_utilization_percentage"),
    ("render_scale", "render_scale"),
    ("dynres_pct", "dynres_recommendation_percentage"),
    ("foveation_level", "foveation_level"),
    ("eye_w", "eye_buffer_width"),
    ("power_w", "power_wattage"),
    ("fps", "average_frame_rate"),
]


def window_stats(cap: Capture, rows: list[dict]) -> dict:
    d: dict = {"rows": len(rows)}
    for key, label in WINDOW_METRICS:
        s = cap.series(key, rows)
        if s:
            d[label] = {"mean": rnd(mean(s), 3), "min": rnd(min(s), 3), "max": rnd(max(s), 3)}
    gpu = cap.series("app_gpu_us", rows)
    if gpu:
        d["app_gpu_time_ms"] = {"p50": rnd(pct(gpu, 50) / 1000, 3), "p95": rnd(pct(gpu, 95) / 1000, 3)}
    st = cap.series("stale", rows)
    dur = sum(r["dt"] for r in rows)
    if st and dur > 0:
        d["stale_per_minute"] = rnd(sum(st) / (dur / 60.0), 2)
    return d


def drift(cap: Capture, window_min: float) -> dict:
    t0, t1 = cap.data[0]["t"], cap.data[-1]["t"]
    span_ms = t1 - t0
    w = window_min * 60000.0
    res: dict = {"window_min": window_min}
    if span_ms < 2 * w:
        w = span_ms / 2.0
        res["warning"] = (
            f"Capture spans {span_ms / 60000:.1f} min, shorter than 2 x {window_min} min; "
            f"comparing first and last halves. Thermal soaks need 20-30 min."
        )
    first = [r for r in cap.data if r["t"] - t0 < w]
    last = [r for r in cap.data if t1 - r["t"] < w]
    a, b = window_stats(cap, first), window_stats(cap, last)
    res["first"], res["last"] = a, b
    deltas: dict = {}
    for label in [lbl for _, lbl in WINDOW_METRICS] + ["app_gpu_time_ms", "stale_per_minute"]:
        va, vb = a.get(label), b.get(label)
        if va is None or vb is None:
            continue
        if isinstance(va, dict):
            k = "mean" if "mean" in va else "p95"
            va, vb = va[k], vb[k]
        delta = vb - va
        deltas[label] = {
            "first": va,
            "last": vb,
            "delta": rnd(delta, 3),
            "direction": "up" if delta > 0 else ("down" if delta < 0 else "flat"),
        }
    res["deltas"] = deltas
    if "battery_temperature_celcius" in deltas:
        res["thermal_signal"] = "battery_temperature_celcius"
    elif "sensor_temperature_celcius" in deltas:
        res["thermal_signal"] = "sensor_temperature_celcius"
    else:
        res["thermal_signal"] = "none (no temperature column); read level/clock/FPS drift"
    pls = cap.series("pls")
    if pls:
        res["power_level_state_max"] = rnd(max(pls), 0)
        first_hot = next((r for r in cap.data if (r.get("pls") or 0) >= 1), None)
        res["first_power_save_at_min"] = rnd((first_hot["t"] - t0) / 60000.0, 2) if first_hot else None
    return res


def per_minute(cap: Capture) -> list[dict]:
    t0 = cap.data[0]["t"]
    buckets: "OrderedDict[int, list[dict]]" = OrderedDict()
    for r in cap.data:
        buckets.setdefault(int((r["t"] - t0) // 60000), []).append(r)
    table = []
    for m, rows in buckets.items():
        row = {"minute": m, "rows": len(rows)}
        for key, label in (
            ("fps", "fps"),
            ("cpu_util", "cpu_util"),
            ("gpu_util", "gpu_util"),
            ("cpu_level", "cpu_L"),
            ("gpu_level", "gpu_L"),
            ("cpu_mhz", "cpu_MHz"),
            ("gpu_mhz", "gpu_MHz"),
            ("batt_temp_c", "batt_C"),
        ):
            s = cap.series(key, rows)
            if s:
                if key in ("cpu_level", "gpu_level"):
                    lo, hi = min(s), max(s)
                    row[label] = f"{lo:g}" if lo == hi else f"{lo:g}-{hi:g}"
                else:
                    row[label] = rnd(mean(s), 1)
        pls = cap.series("pls", rows)
        if pls:
            row["PLS_max"] = rnd(max(pls), 0)
        st = cap.series("stale", rows)
        if st:
            row["stale"] = rnd(sum(st), 0)
        g = cap.series("app_gpu_us", rows)
        if g:
            row["gpu_ms_p95"] = rnd(pct(g, 95) / 1000, 2)
        table.append(row)
    return table


def analyze(path: Path, hz: float | None = None, window_min: float = 5.0,
            segment_column: str | None = None, keep_warmup: bool = False) -> dict:
    cap = Capture(path, segment_column, keep_warmup)
    hz_v, hz_src = refresh_hz(cap, hz)
    report: dict = OrderedDict()
    report["file"] = str(path)
    report["columns_in_header"] = len(cap.header)
    report["columns_used"] = {k: v[2] for k, v in sorted(cap.cols.items())}
    report["refresh_hz"] = hz_v
    report["refresh_source"] = hz_src
    report["frame_budget_ms"] = rnd(1000.0 / hz_v, 3)
    report["row_interval_ms_median"] = cap.row_interval_ms
    report["warmup_rows_dropped"] = cap.warmup_rows
    report["placeholder_or_negative_values_dropped"] = cap.dropped
    report["placeholder_or_negative_values_by_column"] = dict(cap.placeholders.most_common())
    report["caveat"] = (
        "Rows are ~1 Hz interval averages (Q1-010): percentiles are over per-second rows, not frames. "
        "A single-frame hitch is invisible here; use Perfetto for frame-level pacing."
    )
    report["overall"] = summarize(cap, cap.data, hz_v)
    segs = OrderedDict()
    for r in cap.data:
        if r["segment"] is not None:
            segs.setdefault(r["segment"], []).append(r)
    if segs:
        report["segments"] = {name: summarize(cap, rows, hz_v) for name, rows in segs.items()}
    report["per_minute"] = per_minute(cap)
    report["drift"] = drift(cap, window_min)
    report["notes"] = cap.notes
    return report


def fmt(v) -> str:
    return "-" if v is None else f"{v:g}" if isinstance(v, float) else str(v)


def print_text(rep: dict) -> None:
    o = rep["overall"]
    print(f"File: {rep['file']}")
    print(f"Header columns: {rep['columns_in_header']}   refresh: {rep['refresh_hz']:g} Hz ({rep['refresh_source']})"
          f"   budget: {rep['frame_budget_ms']} ms   row interval: {rep['row_interval_ms_median']:g} ms")
    print(f"Rows: {o['rows']}  duration: {o['duration_min']} min  warm-up rows dropped: {rep['warmup_rows_dropped']}"
          f"  placeholder/negative values dropped in analyzed columns: {rep['placeholder_or_negative_values_dropped']}")
    print(f"NOTE: {rep['caveat']}")
    if rep["placeholder_or_negative_values_by_column"]:
        cols = ", ".join(f"{k} x{v}" for k, v in rep["placeholder_or_negative_values_by_column"].items())
        print(f"NOTE: placeholder (999/9999) or negative values treated as missing: {cols}")
    for n in rep["notes"]:
        print(f"NOTE: {n}")
    print()
    if "app_gpu_time_ms" in o:
        g = o["app_gpu_time_ms"]
        print(f"App GPU time ms [{g['source']}]: mean {fmt(g['mean'])}  p50 {fmt(g['p50'])}  p95 {fmt(g['p95'])}"
              f"  p99 {fmt(g['p99'])}  max {fmt(g['max'])}  rows>budget {g['rows_over_budget']}"
              f"  rows at 65535 clamp {g['rows_at_65535_clamp']}")
    else:
        print("App GPU time: column not present")
    if "frame_interval_ms_from_fps" in o:
        f = o["frame_interval_ms_from_fps"]
        print(f"Frame interval ms [{f['source']}]: p50 {fmt(f['p50'])}  p95 {fmt(f['p95'])}  p99 {fmt(f['p99'])}"
              f"  mean fps {fmt(f['mean_fps'])}  min fps {fmt(f['min_fps'])}")
    print("App CPU time: no CPU frame-time column in the OVR Metrics CSV; use Perfetto or logcat CPU&GPU - App.")
    if "stale" in o:
        s = o["stale"]
        h = o["hitch_rate"]
        print(f"Stale frames: total {fmt(s['total'])}  per minute {fmt(s['per_minute'])}"
              f"  max in any 60 s window {fmt(s['max_in_any_60s_window'])}  rows with stale {s['rows_with_stale']}")
        print(f"Hitch rate A (stale / rendered frames): {fmt(h['A_stale_over_rendered_frames_pct'])} %"
              f"   B (rows with stale_frames_consecutive >= 4): {fmt(h['B_rows_with_consecutive_ge4_pct'])} %"
              f"   rows with consecutive >= 2: {fmt(h['rows_with_consecutive_ge2'])}"
              f"   max consecutive: {fmt(h['max_consecutive_stale'])}")
    if "dips_below_65fps_at_72hz" in o:
        d = o["dips_below_65fps_at_72hz"]
        print(f"Dips below 65 fps at 72 Hz (Q1-090): {d['rows']} rows in {d['episodes']} episodes")
    for name, c in o.get("other_counters", {}).items():
        print(f"{name}: sum {fmt(c['sum'])}  max {fmt(c['max'])}  rows nonzero {c['rows_nonzero']}")
    for name, dist in o.get("timing_mode_raw", {}).items():
        print(f"{name} (raw value: rows): {dist}")
    if "segments" in rep:
        print("\nSegments (AppendCsvDebugString):")
        for name, s in rep["segments"].items():
            g = s.get("app_gpu_time_ms", {})
            st = s.get("stale", {})
            print(f"  [{name}] rows {s['rows']}  gpu p95 {fmt(g.get('p95'))}  p99 {fmt(g.get('p99'))}"
                  f"  stale/min {fmt(st.get('per_minute'))}  max stale/60s {fmt(st.get('max_in_any_60s_window'))}")
    print("\nPer minute:")
    cols = ["minute", "rows", "fps", "stale", "gpu_ms_p95", "cpu_util", "gpu_util", "cpu_L", "gpu_L",
            "cpu_MHz", "gpu_MHz", "PLS_max", "batt_C"]
    cols = [c for c in cols if any(c in r for r in rep["per_minute"])]
    print("  " + "  ".join(f"{c:>10}" for c in cols))
    for r in rep["per_minute"]:
        print("  " + "  ".join(f"{fmt(r.get(c)):>10}" for c in cols))
    d = rep["drift"]
    print(f"\nDrift, first vs last {d['window_min']} min (thermal signal: {d['thermal_signal']}):")
    if "warning" in d:
        print(f"  WARNING: {d['warning']}")
    for label, x in d["deltas"].items():
        print(f"  {label:<36} {fmt(x['first']):>10} -> {fmt(x['last']):>10}  delta {fmt(x['delta']):>9}  {x['direction']}")
    if "power_level_state_max" in d:
        print(f"  power_level_state max {fmt(d['power_level_state_max'])}; first SAVE/DANGER at minute "
              f"{fmt(d['first_power_save_at_min'])}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze an OVR Metrics Tool CSV (Quest 2/3/3S).")
    ap.add_argument("csv", type=Path, help="OVR Metrics CSV from .../CapturedMetrics/")
    ap.add_argument("--hz", type=float, default=None, help="refresh rate override (default: display_refresh_rate)")
    ap.add_argument("--window-min", type=float, default=5.0, help="drift window in minutes (default 5)")
    ap.add_argument("--segment-column", default=None, help="header of the AppendCsvDebugString column, if known")
    ap.add_argument("--keep-warmup", action="store_true", help="keep leading rows with eye_buffer_width = 0")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    a = ap.parse_args(argv)
    try:
        rep = analyze(a.csv, a.hz, a.window_min, a.segment_column, a.keep_warmup)
    except FormatError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        print_text(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
