#!/usr/bin/env python3
"""Generate a synthetic OVR Metrics Tool CSV for testing ovr_metrics_csv.py.

Stdlib only, Python 3.10+. The header is the verbatim Aug 2026 Quest 3 header
recorded in research/quest.md Q1-012, with the abbreviated groups expanded as
QUEST-GF1-008 records them (cpu_utilization_percentage_core0..core7 and the
face/eye/hand tracking groups of five). That gives 129 columns.

The data is synthetic, not a measurement. It models:
  * 1 Hz rows, Time Stamp in ms starting at 1000 (Q1-010, QUEST-GF1-008)
  * warm-up rows with eye_buffer_width/height = 0 (QUEST-GF1-008)
  * placeholders: battery_current_now_milliamps = 9999, face-tracking latency
    = 999, avg_frag_inst_per_pixel negative (Q1-017)
  * a rising battery temperature, and CPU/GPU level and clock drops late in
    the session (a thermal-drift shape; the magnitudes are invented test
    values, not Quest data)
  * a few stale-frame bursts with stale_frames_consecutive >= 4
  * phase_sync_mode = 4 (the value seen in Aug 2026 captures, QUEST-GF2-002)

Usage:
    python make_synthetic_ovr_csv.py out.csv [--minutes 30] [--seed 7] [--debug-strings]

--debug-strings appends a trailing field (beyond the header) holding a
segment name every few minutes, imitating AppendCsvDebugString output (Q1-020).
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

_TRACK = [
    "overall_latency_milliseconds",
    "processing_latency_milliseconds",
    "frame_to_frame_latency_milliseconds",
    "frames_dropped",
    "frames_per_second",
]

HEADER: list[str] = (
    "Time Stamp,available_memory_MB,app_pss_MB,battery_level_percentage,battery_temperature_celcius,"
    "battery_current_now_milliamps,power_count_neg,power_count_pos,power_current,power_current_neg,"
    "power_current_pos,power_level_state,power_voltage,power_wattage,power_wattage_neg,power_wattage_pos,"
    "iad_millimeter,shader_hitches,cpu_level,gpu_level,cpu_frequency_MHz,gpu_frequency_MHz,mem_frequency_MHz,"
    "minimum_vsyncs,extra_latency_mode,phase_sync_mode,average_frame_rate,display_refresh_rate,"
    "average_prediction_microseconds,icfl_mean_microseconds,icfl_stdev_microseconds,"
    "slice_headroom_mean_microseconds,slice_headroom_stdev_microseconds,slice_gpu_start_delay_min_microseconds,"
    "slice_gpu_start_delay_max_microseconds,screen_tear_count,early_frame_count,stale_frame_count,"
    "direct_render_frame_count,total_layer_count,merged_layer_count,maximum_rotational_speed_degrees_per_second,"
    "eye_texture_scale_factor,foveation_mode,foveation_level,dynamic_foveation_enabled,"
    "eye_tracked_foveation_latency_milliseconds,symmetric_fov,eye_buffer_width,eye_buffer_height,"
    "swap_chain_width,swap_chain_height,front_buffer_width,front_buffer_height,app_gpu_time_microseconds,"
    "timewarp_gpu_time_microseconds,guardian_gpu_time_microseconds,local_dimming_enabled,cabc_enabled,"
    "temporal_dimming_enabled,temporal_dimming_gain,cpu_utilization_percentage"
).split(",") + [f"cpu_utilization_percentage_core{i}" for i in range(8)] + (
    "gpu_utilization_percentage,spacewarp_motion_vector_type,spacewarped_frames_per_second,"
    "extrapolation_factor_mean,extrapolation_factor_rms,data_extrapolation_factor_mean,"
    "data_extrapolation_factor_rms,app_vss_MB,app_rss_MB,app_uss_MB,app_dalvik_pss_MB,app_private_dirty_MB,"
    "app_private_clean_MB,app_gpu_physical_MB,app_gpu_virtual_MB,app_gpu_allocated_percentage,"
    "stale_frames_consecutive,max_repeated_frames,skipped_frames"
).split(",") + [f"{g}_tracking_{s}" for g in ("face", "eye", "hand") for s in _TRACK] + (
    "dynres_recommendation_percentage,dynres_recommendation_width,dynres_recommendation_height,"
    "app_frame_throttle,avg_vertices_per_frame,avg_fill_percentage,avg_inst_per_frag,avg_inst_per_vert,"
    "avg_frag_inst_per_pixel,avg_vert_inst_per_pixel,avg_textures_per_frag,percent_time_shading_frags,"
    "percent_time_shading_verts,percent_time_compute,percent_vertex_fetch_stall,percent_texture_fetch_stall,"
    "percent_texture_l1_miss,percent_texture_l2_miss,percent_texture_nearest_filtered,"
    "percent_texture_linear_filtered,percent_texture_anisotropic_filtered,vrshell_average_frame_rate,"
    "vrshell_gpu_time_microseconds,vrshell_and_guardian_gpu_time_microseconds,render_scale"
).split(",")

assert len(HEADER) == 129, len(HEADER)

WARMUP_ROWS = 2
# (start_second, length_seconds, stale_per_row, consecutive)
STALE_BURSTS = [(300, 3, 6, 4), (900, 2, 10, 6), (1500, 5, 8, 5)]
REFRESH = 72


def generate(path: Path, minutes: int = 30, seed: int = 7, debug_strings: bool = False) -> dict:
    """Write the CSV and return the ground truth the test checks against."""
    rng = random.Random(seed)
    n = minutes * 60
    truth = {"rows": n, "warmup_rows": WARMUP_ROWS, "app_gpu_us": [], "stale": [], "fps": [],
             "batt_temp": [], "gpu_level": [], "consec": [], "segments": {}}
    burst_rows = {}
    for start, length, per_row, consec in STALE_BURSTS:
        for s in range(start, start + length):
            burst_rows[s] = (per_row, consec)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(HEADER)
        for i in range(n):
            frac = i / max(1, n - 1)
            late = i >= n - 10 * 60  # last 10 minutes: level and clock drop
            row = {h: "0" for h in HEADER}
            row["Time Stamp"] = str(1000 * (i + 1))
            row["available_memory_MB"] = str(2900 - i // 60)
            row["app_pss_MB"] = str(1500 + i // 120)
            row["battery_level_percentage"] = str(max(5, 95 - i // 40))
            temp = round(30.0 + 8.0 * frac + rng.uniform(-0.1, 0.1), 1)
            row["battery_temperature_celcius"] = f"{temp}"
            row["battery_current_now_milliamps"] = "9999" if i % 97 == 0 else str(-1200 + rng.randint(-50, 50))
            row["power_level_state"] = "1" if i >= n - 3 * 60 else "0"
            row["power_voltage"] = "3900"
            row["power_wattage"] = f"{6.0 + 1.5 * frac:.2f}"
            row["shader_hitches"] = "1" if i in (5, 6) else "0"
            cpu_l, gpu_l = (3, 3) if late else (4, 4)
            row["cpu_level"], row["gpu_level"] = str(cpu_l), str(gpu_l)
            row["cpu_frequency_MHz"] = "1651" if late else "1920"
            row["gpu_frequency_MHz"] = "492" if late else "545"
            row["mem_frequency_MHz"] = "2092"
            row["minimum_vsyncs"] = "1"
            row["extra_latency_mode"] = "0"
            row["phase_sync_mode"] = "4"
            per_row, consec = burst_rows.get(i, (0, 0))
            fps = REFRESH - per_row if per_row else round(REFRESH - rng.choice([0, 0, 0, 0.1]), 2)
            row["average_frame_rate"] = f"{fps}"
            row["display_refresh_rate"] = str(REFRESH)
            row["average_prediction_microseconds"] = str(38000 + rng.randint(-500, 500))
            row["icfl_mean_microseconds"] = str(16500 + rng.randint(-200, 200))
            row["slice_headroom_mean_microseconds"] = str(1850 + rng.randint(-100, 100))
            row["stale_frame_count"] = str(per_row)
            row["stale_frames_consecutive"] = str(consec)
            row["max_repeated_frames"] = str(1 if per_row else 0)
            row["total_layer_count"] = "4"
            row["merged_layer_count"] = "4"
            row["eye_texture_scale_factor"] = "10"
            row["foveation_level"] = "2"
            warm = i < WARMUP_ROWS
            row["eye_buffer_width"] = "0" if warm else "1680"
            row["eye_buffer_height"] = "0" if warm else "1760"
            row["swap_chain_width"], row["swap_chain_height"] = "2016", "1760"
            row["front_buffer_width"], row["front_buffer_height"] = "4128", "2208"
            gpu_us = int(9000 + 2500 * frac + rng.gauss(0, 400))
            if i == 1200:
                gpu_us = 65535  # clamp probe (Q1-018)
            row["app_gpu_time_microseconds"] = str(gpu_us)
            row["timewarp_gpu_time_microseconds"] = str(1250 + rng.randint(-50, 50))
            cpu_u = 55 + 10 * frac + rng.uniform(-2, 2)
            row["cpu_utilization_percentage"] = f"{cpu_u:.1f}"
            for c in range(8):
                row[f"cpu_utilization_percentage_core{c}"] = f"{max(0.0, cpu_u + rng.uniform(-20, 20)):.1f}"
            row["gpu_utilization_percentage"] = f"{70 + 15 * frac + rng.uniform(-2, 2):.1f}"
            row["face_tracking_overall_latency_milliseconds"] = "999"
            row["avg_frag_inst_per_pixel"] = "-67"
            row["dynres_recommendation_percentage"] = "100"
            row["render_scale"] = "1.0"
            out = [row[h] for h in HEADER]
            seg = None
            if debug_strings and i % 600 == WARMUP_ROWS:
                seg = f"segment_{i // 600}"
                out.append(seg)
            w.writerow(out)
            if not warm:
                truth["app_gpu_us"].append(float(gpu_us))
                truth["stale"].append(float(per_row))
                truth["fps"].append(float(fps))
                truth["batt_temp"].append(temp)
                truth["gpu_level"].append(gpu_l)
                truth["consec"].append(consec)
    return truth


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write a synthetic OVR Metrics CSV (Aug 2026 header, 129 columns).")
    ap.add_argument("out", type=Path)
    ap.add_argument("--minutes", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--debug-strings", action="store_true")
    a = ap.parse_args(argv)
    t = generate(a.out, a.minutes, a.seed, a.debug_strings)
    print(f"wrote {a.out} ({t['rows']} rows, {len(HEADER)} columns)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
