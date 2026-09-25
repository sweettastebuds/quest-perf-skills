# OVR Metrics Tool CSV: column map and quirks

Applies to: Quest 2, Quest 3/3S; any engine; OVR Metrics Tool Report Mode.
All findings accessed 2026-09-24. IDs refer to `research/quest.md`.

## File location and naming

| Item | Value | ID |
|---|---|---|
| Directory | `/sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/` | Q1-008, A3-049 |
| One file per | app launch | Q1-008 |
| 2023 name | `<package>-YYYYMMDD_HHMMSS.csv` | Q1-009 [measured] |
| 2026 name | `<package>#<Activity>-YYYYMMDD_HHMMSS.csv` (escape `#` as `%23` in URLs) | Q1-009 [measured] |
| Row cadence | about 1 per 1000 ms; `Time Stamp` = ms since recording start; each row averages the prior interval | Q1-010 [doc]+[measured] |
| Tool version | not in the file; read `adb shell dumpsys package com.oculus.ovrmonitormetricsservice` and record it | Q1-001, QUEST-GF1-006 |

## Header versions

Parse by name, never by position (Q1-012 [measured]).

| Capture | Device | Columns |
|---|---|---|
| Oct 2023 (Gym Class) | Quest 2 | 89 |
| Jan 2026 (Unity sample) | Quest 3 | 134 |
| Aug 2026 (Passthrough Camera API samples) | Quest 3 | 129 |

2023 to 2026 changes (Q1-012): `sensor_temperature_celcius` and the `screen_*`
columns dropped; `shader_hitches`, `phase_sync_mode`, ICFL and slice-headroom
columns, layer counts, `max_repeated_frames`, `skipped_frames`,
`app_gpu_*_MB`, `dynres_*` and `app_frame_throttle` added. The Jan 2026 file
also has `average_prediction_milliseconds` and `cfl_min/max_micro|milliseconds`,
which Aug 2026 lacks. No capture had a debug-string column header.

Doc list vs reality (conflict Q1-C9): the stat list on the OVR Metrics page
(Jun 2026, Q1-005) still says `average_prediction_milliseconds` and omits about
50 columns; the Aug 2026 CSV uses `average_prediction_microseconds`. Parse by
header and normalise by unit suffix.

## Unit suffixes (Q1-013)

`_MB`, `_microseconds`, `_milliseconds`, `_percentage`, `_MHz`, `_celcius`
(Meta's spelling, match it exactly), `_milliamps`. `ovr_metrics_csv.py`
converts `_milliseconds` to microseconds.

## Aug 2026 header, expanded (Q1-012 + QUEST-GF1-008)

Group by group, in file order. [C] = consistency signal, [T] = throughput signal (Q1-014, Q1-015).

| Group | Columns | Use |
|---|---|---|
| Time | `Time Stamp` | row time, ms |
| Memory | `available_memory_MB`, `app_pss_MB` | PSS trend (limits: `quest-perf:quest-budgets-tiers`) |
| Battery / power | `battery_level_percentage`, `battery_temperature_celcius`, `battery_current_now_milliamps`, `power_count_neg`, `power_count_pos`, `power_current`, `power_current_neg`, `power_current_pos`, `power_level_state`, `power_voltage`, `power_wattage`, `power_wattage_neg`, `power_wattage_pos` | thermal drift; `power_level_state` 0 NORMAL, 1 SAVE, 2 DANGER (Q1-016) |
| Misc | `iad_millimeter`, `shader_hitches` | `shader_hitches` [C], undefined by Meta |
| Levels / clocks | `cpu_level`, `gpu_level`, `cpu_frequency_MHz`, `gpu_frequency_MHz`, `mem_frequency_MHz` | [T] and thermal |
| Timing mode | `minimum_vsyncs`, `extra_latency_mode`, `phase_sync_mode` | [C]; `phase_sync_mode` values undefined (QUEST-GF2-002) |
| Rate | `average_frame_rate`, `display_refresh_rate` | FPS per row |
| Latency | `average_prediction_microseconds`, `icfl_mean_microseconds`, `icfl_stdev_microseconds`, `slice_headroom_mean_microseconds`, `slice_headroom_stdev_microseconds`, `slice_gpu_start_delay_min_microseconds`, `slice_gpu_start_delay_max_microseconds` | [C] |
| Pacing counters | `screen_tear_count`, `early_frame_count`, `stale_frame_count`, `direct_render_frame_count` | [C] |
| Layers | `total_layer_count`, `merged_layer_count` | compositor cost |
| Head motion | `maximum_rotational_speed_degrees_per_second` | context |
| Resolution / foveation | `eye_texture_scale_factor`, `foveation_mode`, `foveation_level`, `dynamic_foveation_enabled`, `eye_tracked_foveation_latency_milliseconds`, `symmetric_fov`, `eye_buffer_width`, `eye_buffer_height`, `swap_chain_width`, `swap_chain_height`, `front_buffer_width`, `front_buffer_height` | [T] |
| GPU time | `app_gpu_time_microseconds`, `timewarp_gpu_time_microseconds`, `guardian_gpu_time_microseconds` | [T] |
| Display | `local_dimming_enabled`, `cabc_enabled`, `temporal_dimming_enabled`, `temporal_dimming_gain` | context |
| Utilisation | `cpu_utilization_percentage`, `cpu_utilization_percentage_core0` ... `cpu_utilization_percentage_core7`, `gpu_utilization_percentage` | [T] |
| SpaceWarp | `spacewarp_motion_vector_type`, `spacewarped_frames_per_second`, `extrapolation_factor_mean`, `extrapolation_factor_rms`, `data_extrapolation_factor_mean`, `data_extrapolation_factor_rms` | AppSW (`quest-perf:quest-appsw`) |
| Process memory | `app_vss_MB`, `app_rss_MB`, `app_uss_MB`, `app_dalvik_pss_MB`, `app_private_dirty_MB`, `app_private_clean_MB`, `app_gpu_physical_MB`, `app_gpu_virtual_MB`, `app_gpu_allocated_percentage` | pair with `gpumeminfo` (Q1-095) |
| Stall counters | `stale_frames_consecutive`, `max_repeated_frames`, `skipped_frames` | [C]; last two undefined |
| Tracking (x3) | `face_tracking_`, `eye_tracking_`, `hand_tracking_` + `overall_latency_milliseconds`, `processing_latency_milliseconds`, `frame_to_frame_latency_milliseconds`, `frames_dropped`, `frames_per_second` | hand-tracking cost A/B (`quest-perf:quest-mr-costs`) |
| Dynamic resolution | `dynres_recommendation_percentage`, `dynres_recommendation_width`, `dynres_recommendation_height`, `app_frame_throttle` | [T]; `app_frame_throttle` undefined |
| GPU counters (need ovrgpuprofiler support on in the tool, Q1-007) | `avg_vertices_per_frame`, `avg_fill_percentage`, `avg_inst_per_frag`, `avg_inst_per_vert`, `avg_frag_inst_per_pixel`, `avg_vert_inst_per_pixel`, `avg_textures_per_frag`, `percent_time_shading_frags`, `percent_time_shading_verts`, `percent_time_compute`, `percent_vertex_fetch_stall`, `percent_texture_fetch_stall`, `percent_texture_l1_miss`, `percent_texture_l2_miss`, `percent_texture_nearest_filtered`, `percent_texture_linear_filtered`, `percent_texture_anisotropic_filtered` | interpretation: `arm-mobile-hw-perf:xr2-gpu-counters-sdp` |
| Shell | `vrshell_average_frame_rate`, `vrshell_gpu_time_microseconds`, `vrshell_and_guardian_gpu_time_microseconds` | system overhead |
| Scale | `render_scale` | [T] |

`avg_fill_percentage` = 100 means each eye pixel was touched once on average;
system overlays add to it (Q1-007).

## Columns with no published definition (known unknown)

`shader_hitches`, `max_repeated_frames`, `skipped_frames`, `slice_headroom_*`,
`slice_gpu_start_delay_*`, `icfl_*` (CSV form), `app_frame_throttle`,
`eye_texture_scale_factor` (Q1-014, Q1-015, quest.md Gaps). The logcat fields
`CFL` and `ICFLp95` are defined (Q1-033). Method to pin one down
[verify on device]: provoke the event (for `shader_hitches`, put a
never-rendered material on screen) and watch the column move in a 1 Hz CSV.

`phase_sync_mode`: `4` in all 979 rows of three Aug 2026 Quest 3 captures,
`1` in a Jan 2026 Quest 3 capture; absent in Oct 2023 (QUEST-GF2-002
[measured]). `4` probably marks FrameSync on v203+; unconfirmed. The analyzer
passes the raw values through. Meaning: `quest-perf:quest-frame-pacing`.

Sample values seen in the Jan 2026 Quest 3 Unity capture (Q1-014, Q1-015
[measured]): `shader_hitches` = 1, ICFL mean about 16534 µs, slice headroom
mean about 1853 µs, eye buffer 1680x1760, swap chain 2016x1760, front buffer
4128x2208, `eye_texture_scale_factor` = 10, 4 layers all merged.

## Garbage and placeholder values (Q1-017, Q1-018, QUEST-GF1-008)

| Value | Where seen | Treatment |
|---|---|---|
| 9999 | `battery_current_now_milliamps` (2023 Quest 2) | missing |
| 999 | face-tracking latency with the feature off (2026) | missing |
| -67 | `avg_frag_inst_per_pixel` (Jan 2026 Quest 3) | negatives missing |
| 0 | `eye_buffer_width/height` in the first rows (Aug 2026 Quest 3) | warm-up; drop leading rows |
| 65535 | `app_gpu_time_microseconds`, claimed 16-bit clamp | flag; use Perfetto for spikes ([community], Q1-018) |

`ovr_metrics_csv.py` does not apply the 999/9999 rule to `_microseconds`
columns, where those are plausible measurements.

## Segment tagging (Q1-020)

`OVRMetricsToolSDK.Instance.AppendCsvDebugString(string)` writes text into
the last CSV column. Calling it more often than 1 Hz adds rows with empty
metric columns. Call it at segment boundaries only. The header name of that
column is not documented; the analyzer accepts a header containing `debug`,
`--segment-column NAME`, or a trailing field beyond the header.
