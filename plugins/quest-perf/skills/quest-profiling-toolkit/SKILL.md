---
name: quest-profiling-toolkit
description: "Exact commands and output formats for Quest profiling tools: OVR Metrics Tool (overlay, CSV columns), VrApi/XrPerformanceManager logcat, MQDH and Perfetto traces, RenderDoc Meta Fork, ovrgpuprofiler, simpleperf, gpumeminfo, the Runtime Optimizer, and debug setprops that pin levels or disable foveation. Ships a Python OVR Metrics CSV analyzer (p50/p95/p99, stale frames per minute, thermal drift) and an ADB helper. Use to run a capture, pin levels, or parse a CSV/trace; for what a symptom means, start at quest-triage."
---

# Quest profiling toolkit

How to run each Quest profiling tool, what its output looks like, and how to
keep the measurement itself from lying. Applies to Quest 2 (XR2 Gen 1,
Adreno 650) and Quest 3/3S (XR2 Gen 2, Adreno 740), any Unity 2021.3 to 6.x
URP project, GLES and Vulkan unless a line says otherwise. Goal: both.
Throughput fixes need a clean A/B; consistency fixes need a long, unpinned,
segmented capture. All sources accessed 2026-09-24.

## When to use / when not

Use when the task is:

- "how do I capture", "OVR Metrics CSV", "parse this CSV", "stale frames per minute", "thermal drift over 30 minutes"
- "ovrgpuprofiler command", "read this surface line", "Perfetto trace", "ATrace", "metavr"
- "RenderDoc Meta Fork settings", "setprop", "pin CPU/GPU level", "turn off foveation", "simulate thermal"
- simpleperf for IL2CPP hotspots, `gpumeminfo`, the Quest Runtime Optimizer

Do not use for:

- What a symptom means, or CPU vs GPU vs pacing routing: `quest-perf:quest-triage`.
- What an Adreno counter means and its healthy range, Snapdragon Profiler, Adreno Offline Compiler: `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
- Unity Profiler, ProfilerMarker, FrameTimingManager, Frame Debugger, in-app stats hooks (XRDisplaySubsystem, OVRPlugin perf metrics): `unity-perf:unity-profiling-workflow`.
- GLES capture caveats and the GLES-vs-Vulkan A/B protocol: `gles3-perf:gles-vs-vulkan`.
- Level/clock tables, throttling stages and the soak protocol's interpretation: `quest-perf:quest-levels-thermal`.
- Stale-frame causes, FrameSync, `phase_sync_mode` meaning: `quest-perf:quest-frame-pacing`.
- Store VRCs and Performance Analytics as requirements: `quest-perf:quest-budgets-tiers`.

## Diagnose first

Pick the tool by the question; run the cheapest one that answers it
(quest.md section 1 tool order: CSV/logcat, then Perfetto, then GPU tools).

| Question | Tool | Command |
|---|---|---|
| Average FPS, stale rate, levels, drift over a session | OVR Metrics CSV + analyzer | `python scripts/quest_adb.py csv-on`, play, `python scripts/quest_adb.py pull-csv --out run01`, `python scripts/ovr_metrics_csv.py run01/<file>.csv` |
| Per-second pacing, clocks, render-thread time, layers | VrApi logcat | `adb logcat -s VrApi,XrPerformanceManager` (Q1-027) |
| Why did the level change or not apply | clock log | `adb shell setprop debug.oculus.clockStateLogLevel 1` (Q1-036) |
| Which thread, which frame, blocking waits | Perfetto | MQDH, or `metavr perf capture --mode standard --app <pkg> --duration 10000 -o t.pftrace` (Q1-049) |
| GPU cost per surface, Load/Store waste | ovrgpuprofiler | `adb shell ovrgpuprofiler -e <pkg>`, restart app, `-t2 -l`, then `-d` (Q1-067, Q1-068) |
| Per-draw cost, bytes, shader stats | RenderDoc Meta Fork | Performance Counter Viewer, Tile Timeline (Q1-058) |
| IL2CPP C++ hotspots | simpleperf | see Fix 9 (Q1-096) |
| GPU memory per process | gpumeminfo | `adb shell gpumeminfo -p $(pidof <pkg>)` (Q1-095) |
| Automated CPU/GPU-bound classification in editor | Runtime Optimizer | Window > Meta > Tools > Quest Runtime Optimizer (Q1-092) |

Preconditions to check before trusting any number (script it):

```
python scripts/quest_adb.py props-snapshot --out run01   # which debug.oculus.* props are live (Q1-077)
python scripts/quest_adb.py csv log-state                # OVR Metrics config as JSON in logcat (Q1-003)
adb shell ovrgpuprofiler -i                              # detailed mode must be OFF for timing runs (Q1-067)
```

Also confirm, in the capture metadata: casting off (Q1-041), HUD off for
soaks (Q1-002), dynamic resolution and dynamic foveation off for A/B
(Q2-039, A3-052), headset on battery (Q2-064), cold or warm run labelled
(Q1-011), OVR Metrics tool version from
`adb shell dumpsys package com.oculus.ovrmonitormetricsservice` (Q1-001).

Read [references/logcat-fields.md](references/logcat-fields.md) when you need
the meaning of any token in the VrApi line or the XrPerformanceManager line.

## Key numbers

| Number | Value | Applies to | Source |
|---|---|---|---|
| Frame budget | 13888 us at 72 Hz, 11111 us at 90 Hz, 8333 us at 120 Hz | Quest 2/3/3S | Q1-089 [doc] |
| CSV row cadence | ~1000 ms; each row averages the previous interval; cannot show a single-frame hitch | Quest 2/3/3S | Q1-010 [doc]+[measured] |
| CSV header width | 89 (2023 Quest 2), 134 (Jan 2026 Quest 3), 129 (Aug 2026 Quest 3) columns | tool-version dependent | Q1-012 [measured] |
| `app_gpu_time_microseconds` clamp | 65535 us claimed (16-bit) | device not stated | Q1-018 [community] [verify on device] |
| Placeholders | 9999, 999, negatives appear in real CSVs | Quest 2/3 | Q1-017 [measured] |
| ovrgpuprofiler detailed mode cost | about 10% of GPU render time | Quest 2/3/3S | Q1-067, A3-029 [doc] |
| ovrgpuprofiler real-time limit | at most 30 metrics at once | Quest 2/3/3S | Q1-066 [doc] |
| ovrgpuprofiler metric count | 47 (Meta example) vs 72/78 (paper, Quest 3/3S) vs 81 (community, Quest 3) | varies by device/runtime (Q1-C8) | Q1-065, Q1-076 |
| RenderDoc Meta Fork | v68.18, needs Horizon OS 68+; up to 48 vs 59 draw metrics (Q1-C2) | Quest 2/3/3S | Q1-057, Q1-058 [doc] |
| Vulkan shader stats guidance | texture read groups below 15; any scratch memory = poor performance | Vulkan | Q1-063 [doc] |
| Dip tolerance | one-off dip of a couple of seconds OK if above 65 fps and not cyclic; none published for 90/120 Hz | 72 Hz | Q1-090 [doc] |
| Store field windows | Performance Analytics aggregates stale frames and utilisation per ~60 s | Store apps | QUEST-GF2-013 [doc] |
| Runtime Optimizer target | 14.2 ms (about 70 FPS) vs the 13.9 ms 72 Hz budget (Q1-C6) | Unity 2022.3+, HzOS v78+ | Q1-092 [doc] |
| Default eye buffer | 1440x1584 (Quest 2), 1680x1760 (Quest 3/3S) | `debug.oculus.textureWidth/Height` | Q1-080 [doc]; Q1-C4 |
| Headroom rule | 70% CPU / 80% GPU / hitches under 3% (the 3% is in the blog recap only; the talk captions never say it, QUEST-GF2-012; no denominator published): owned by `quest-perf:quest-triage` | Quest 2/3 | QUEST-GF1-003, QUEST-GF2-012 |
| Tool overheads | HUD, CSV recording, ovrgpuprofiler real-time mode: no published number; measure with an on/off A/B | all | quest.md Gaps |

## Fixes, ranked by payoff ÷ effort

Here a "fix" repairs the measurement. A wrong capture sends every downstream
skill after the wrong bottleneck.

### 1. Record soaks as CSV with the Basic preset, HUD off, casting off

- Change: `python scripts/quest_adb.py csv-on` (the `ENABLE_CSV` broadcast, Q1-003); leave the overlay off (`csv overlay-off`); pick the Basic preset (Advanced adds overhead meant for isolated GPU hunts, Q1-006); turn MQDH Casting off (Q1-041). Run 20-30 minutes on a scripted route, unpinned.
- Effect: removes the HUD's own layer and GPU draw and casting cost from the data; no published size for either, so the effect on mean vs variance is unmeasured [verify on device].
- Cost: no live feedback in the headset.
- Tags: `Quest 2` `Quest 3/3S` `GLES` `Vulkan` `Unity 2021.3-6.x`. Goal: Consistency (enables it), Throughput.

### 2. Pin levels and remove foveation/compositor noise for A/B timing; unpin for soaks

- Change: `python scripts/quest_adb.py isolate-gpu --cpu 4 --gpu 4 --skip-ms 60000` = `debug.oculus.cpuLevel 4`, `debug.oculus.gpuLevel 4`, `debug.oculus.foveation.dynamic 0`, `debug.oculus.foveation.level 0`, and `COMPOSITOR_SKIP_RENDERING --ei milliseconds 60000` so TW=0 and `App=` is app-only (A3-051, Q2-039). Disable dynamic resolution in the build (A3-052). Reboot to undo (`quest_adb.py reset --yes`, Q1-077).
- Effect: removes clock-scaling and foveation variance between A and B runs, so small content deltas become visible. Pinned levels still throttle when hot: watch `PLS` (A3-051).
- Side effects: never run a thermal or consistency soak pinned, it hides the runtime behaviour (Q1-079). With dynamic resolution off, GPU L5 is unavailable (A3-052 note).
- Tags: `Quest 2` `Quest 3/3S` `GLES` `Vulkan`. Goal: Throughput.

### 3. Always turn ovrgpuprofiler detailed mode off

- Change: `adb shell ovrgpuprofiler -d` (or `quest_adb.py gpu-trace --disable`) after every trace; check with `-i` before timing runs.
- Effect: a headset left in detailed mode inflates every later GPU number by about 10% (Q1-067) and distorts level behaviour in thermal runs (A3-029).
- Cost: none.
- Tags: `Quest 2` `Quest 3/3S`. Goal: Throughput, Consistency.

### 4. Put the Unity package in MQDH ATrace Apps

- Change: MQDH > Perfetto settings > ATrace Apps = `com.company.app`. Unity emits only ATrace events; without it the trace has no Unity markers (Q1-044). Custom `ProfilerMarker` scopes need a Development Build (Q1-045).
- Effect: none on the app; turns an empty trace into a usable one.
- Cost: custom markers need a Development Build, which changes timing (Q1-045).
- Tags: `Unity 2021.3-6.x` `Quest 2` `Quest 3/3S`. Goal: Consistency (frame-level pacing lives here).

### 5. Segment the CSV from the app

`AppendCsvDebugString` writes into the last CSV column (Q1-020); call it at
segment boundaries, never every frame (faster than 1 Hz adds empty-metric
rows). Signature checked in Meta XR Core SDK v85 (`OVRMetricsToolSDK`, global
namespace, `bool AppendCsvDebugString(string)`, Q1-019). Needs the OVR Metrics
service on the headset: QA/dev builds only.

```csharp
// Unity 2021.3+ with Meta XR Core SDK (v85 checked). Dev/QA builds only.
using UnityEngine;
using UnityEngine.SceneManagement;

public sealed class OvrMetricsSegmentTag : MonoBehaviour
{
    void OnEnable()  { SceneManager.sceneLoaded += OnSceneLoaded; }
    void OnDisable() { SceneManager.sceneLoaded -= OnSceneLoaded; }

    void OnSceneLoaded(Scene scene, LoadSceneMode mode) => Tag("scene:" + scene.name);

    // Call from gameplay code at boundaries: combat start, cutscene, tier change.
    public static void Tag(string segment)
    {
#if UNITY_ANDROID && !UNITY_EDITOR && (DEVELOPMENT_BUILD || QUEST_PERF_QA)
        if (!OVRMetricsToolSDK.Instance.AppendCsvDebugString(segment))
            Debug.LogWarning("OVR Metrics: " + OVRMetricsToolSDK.Instance.GetError());
#endif
    }
}
```

- Effect: per-segment p95/p99 and stale counts in the analyzer (Q1-094 method).
- Cost: needs the OVR Metrics service on the headset. Calls faster than 1 Hz add empty-metric rows (Q1-020).
- Tags: `Unity 2021.3+` `Meta XR Core SDK` `Quest 2` `Quest 3/3S`. Goal: Consistency.

### 6. Separate cold and warm runs

- Change: label the first run after install as cold; play the level once before judging (fresh installs compile shaders on first run, Q1-011). For scripted cold starts: `metavr perf capture --launch` (Q1-049).
- Effect: cold-run hitches stop polluting throughput numbers; warm-run data stops hiding PSO hitches. Fix owner for those hitches: `unity-perf:unity-shader-hitches`.
- Tags: `Quest 2` `Quest 3/3S` `GLES` `Vulkan`. Goal: Consistency.

### 7. Script traces with metavr instead of hand-built Perfetto configs

- Change: `python scripts/quest_adb.py perfetto --app <pkg> --mode gpu --duration-ms 10000 -o run01/t.pftrace --flags gpu-render-stage xr-runtime` (forwards to `metavr perf capture`, Q1-049). Analyse with `metavr perf analyze-trace --focus frames --json-out`. The raw CLI recipe (`--legacy-cli`, Q1-048) is from 2021 and may use stale data-source names.
- Effect: repeatable captures; keep traces short, a small buffer drops data silently (Q1-043).
- Cost: needs the metavr CLI (npx or installer). A small buffer silently drops data (Q1-043).
- Tags: `Quest 2` `Quest 3/3S`. Goal: Consistency.

### 8. Configure RenderDoc Meta Fork for a tiler

- Change: timer query per render pass, "Disable TimeWarp on replay", replay optimisation Fastest (Q1-059); capture Development Builds (Q1-060).
- Effect: per-draw timer queries on Adreno do not measure per-draw cost; per-pass does.
- Cost: Development Build required. Store builds need root for JDWP on API 34+ (Q1-060).
- Tags: `Quest 2` `Quest 3/3S` `HzOS 68+`; shader stats and validation `Vulkan` only. Goal: Throughput.

### 9. Simpleperf for IL2CPP CPU hotspots

```
# Build: IL2CPP, Development Build, "Debugging (Full)" symbols (Q1-096)
python <ndk>/simpleperf/binary_cache_builder.py -lib <symbols dir>
python <ndk>/simpleperf/app_profiler.py --disable_adb_root --ndk_path <ndk> --app <pkg> -r "-g --duration 30 -e cpu-cycles,cache-misses"
python <ndk>/simpleperf/report_html.py
```

- `cache-misses` separates memory-bound job code from ALU-bound code. Alternative on HzOS v51+: Perfetto callstack sampling with symbol folders (Q1-047), which can sample release builds.
- Effect: none on the shipped app. It locates CPU hotspots so the fix targets average main/worker time. It measures a Development Build, whose timing differs from release (Q1-045), so confirm the final numbers on a non-dev build with the CSV.
- Cost: Development Build + 'Debugging (Full)' symbols (the page asks for development builds, Q1-096). Simpleperf has no C# call graphs, only IL2CPP C++ (ts-simpleperf page).
- Tags: `IL2CPP` `Quest 2` `Quest 3/3S`. Goal: Throughput.

### 10. Quest Runtime Optimizer for a first automated split

- Change: Asset Store package; Window > Meta > Tools > Quest Runtime Optimizer. Quick Perf (green under 80%, yellow 80-95%, red over 95% of 14.2 ms), Bottleneck Analysis (about 25 s; Texture, Fragment, Setup, Vertex, Vertex Fetch), What If? (about 200 ms per GameObject, up to 200). Exports `.roz` (ZIP of Perfetto trace, screenshots, JSON) (Q1-092, Q1-093).
- Side effects: adds `ENABLE_RUNTIME_OPTIMIZER` and forces a Development Build, so turn it off for release candidates. Known issues: rare kernel panics on OS v78; dynamic objects unsupported. What If? can report negative GPU time for an object that hid costlier geometry. Its 14.2 ms "green" misses vsync at 72 Hz (Q1-C6): re-judge against 13.9 ms.
- Tags: `Unity ≥ 2022.3` (not 2021.3) `HzOS v78+` `Quest 2` `Quest 3/3S`. Goal: Throughput.

### 11. gpumeminfo next to the memory columns

- Change: `python scripts/quest_adb.py gpumeminfo <pkg> -l`; pair with CSV `app_gpu_physical_MB`, `app_gpu_virtual_MB`, `app_gpu_allocated_percentage` (Q1-095). Limits: `quest-perf:quest-budgets-tiers`.
- Effect: shows the GPU-memory trend behind low-memory kills and streaming hitches (variance). Average frame time does not change.
- Cost: none; a one-shot shell command. Needs the process running.
- Tags: `Quest 2` `Quest 3/3S`. Goal: Consistency (low-memory kills, streaming hitches).

### Scripts and references

Run from the skill folder; Python 3.10+, stdlib only. `-s` is forwarded to
metavr as `-d`.

- `scripts/ovr_metrics_csv.py` - analyzer. `python scripts/ovr_metrics_csv.py <csv> [--hz 72] [--window-min 5] [--json] [--segment-column NAME] [--keep-warmup]`. Reports p50/p95/p99 of `app_gpu_time_microseconds` and of the frame interval derived from `average_frame_rate` (both over 1 Hz rows, not frames); stale total, per minute and max in any 60 s window; hitch rate A (stale ÷ rendered frames) and B (rows with `stale_frames_consecutive` ≥ 4 ÷ rows), because the 3% rule has no published denominator (QUEST-GF2-012); dips under 65 fps at 72 Hz; `shader_hitches`, `max_repeated_frames`, `skipped_frames`; raw `phase_sync_mode`/`extra_latency_mode`; a per-minute table of FPS, stale, GPU p95, CPU/GPU utilisation, levels, clocks, PLS, battery temperature; first-vs-last-window drift with direction; per-segment summaries. The CSV has no app CPU time column: use logcat `CPU&GPU - App` or Perfetto. Exit 2 on an unrecognised file.
- `scripts/quest_adb.py` - ADB helper, `--dry-run` prints commands without a device. Subcommands: `pin-levels`, `refresh-rate`, `foveation`, `subsampled`, `compositor-skip`, `isolate-gpu`, `thermal-sim`, `appsw-debug`, `csv`, `csv-on`, `pull-csv`, `logcat`, `clocklog`, `gpu-metrics`, `gpu-realtime`, `gpu-trace`, `gpumeminfo`, `perfetto`, `vrruntime` (forwards to `metavr device vrruntime`), `props-snapshot`, `reset`. `python scripts/quest_adb.py --help` lists options. Capture subcommands write `props-snapshot.txt` beside their output.
- `scripts/make_synthetic_ovr_csv.py` and `scripts/test_ovr_metrics_csv.py` - synthetic 129-column capture and the analyzer's tests: `python -m unittest discover -s scripts -p "test_*.py" -v`.

References, read when needed:

- [references/ovr-metrics-csv-columns.md](references/ovr-metrics-csv-columns.md) - read when a CSV column is unfamiliar, a header differs from the one you expect, or a value looks like garbage.
- [references/ovrgpuprofiler.md](references/ovrgpuprofiler.md) - read before running ovrgpuprofiler or reading a surface line (Load/Store rule, multiview counting).
- [references/renderdoc-meta-fork.md](references/renderdoc-meta-fork.md) - read before a RenderDoc capture, or to find a per-draw metric or shader stat.
- [references/perfetto-mqdh.md](references/perfetto-mqdh.md) - read before configuring MQDH/Perfetto, writing trace SQL, or using metavr.
- [references/setprops.md](references/setprops.md) - read before setting any debug property or broadcast; lists every documented one with its source.
- [references/logcat-fields.md](references/logcat-fields.md) - read when parsing the VrApi line.

## Verify

- Measurement repeatability: two identical pinned runs (Fix 2) of the same
  scripted route. No published noise figure exists; their p50 GPU-time
  difference is your noise floor. Treat any A/B delta below it as no change.
- Soak: 20-30 min unpinned CSV (Q1-094; Q2-060 soak conditions: fixed ambient,
  battery above 50%, unplugged). The analyzer's drift section should show
  `battery_temperature_celcius` (or clocks/levels if no temperature) and
  `stale_per_minute` first vs last 5 min; `first_power_save_at_min` gives when
  `power_level_state` left 0. Interpretation: `quest-perf:quest-levels-thermal`.
- Perfetto: at least 20 s of steady play for p95/p99 of `PlayerLoop` dur
  (Q1-055).
- ovrgpuprofiler real-time counters should be stable on a steady scene;
  unstable counters mean the scene has not settled (Q1-066).
- After detailed mode, `ovrgpuprofiler -i` reports it off, and app GPU time
  drops back by roughly the ~10% overhead (Q1-067) [verify on device].
- Render-scale or dynres tests actually applied: logcat `SF=` changes (Q1-033).
- FFR override actually applied: logcat `Fov=` shows the level without `D`
  (Q1-081).

## Pitfalls and myths

- **"GPU% says 35% headroom."** At half rate `GPU%` under-reports: Meta's
  example `FPS=36/72, GPU%=0.65, App=18.05ms` needs a 23% GPU cut, not 35%.
  Judge with `App` time vs budget (Q1-089 / Q2-031, os-missed-frames).
- **"PlayerLoop over 11.1 ms = stale frame."** Meta's own agent SQL does this;
  it hard-codes 90 Hz and confuses CPU frame time with compositor staleness.
  Use `Stale`/`stale_frame_count` (Q1-054, Q1-C7). Under extra-latency mode
  `Stale` = refresh with steady FPS is not a failure (quest.md triage map).
- **Parsing the CSV by column position.** Headers change per tool version
  (Q1-012); the doc stat list is behind real files (Q1-C9).
- **Percentiles from the CSV are frame percentiles.** They are percentiles of
  1 Hz interval averages (Q1-010). For single-frame spikes use Perfetto GPU
  render-stage tracks, also for anything near the 65535 us clamp (Q1-018).
- **Hard-coding ovrgpuprofiler metric IDs.** IDs are list positions and vary
  by device and runtime (Q1-065, Q1-C8). Resolve names with `-m` each time.
- **Adding both eye surfaces.** On Quest 2 and Quest 3/3S one surface line
  covers both views; the page's generic "add both" sentence is for the
  original Quest (Q1-071, A3-034, Q1-C11).
- **Counting Preempt as app cost.** It is compositor preemption (A3-031);
  whether to subtract it is unpublished (Q1-070). `App=` can also include
  preemption (Q2-040).
- **FrameTimingManager GPU time on Quest.** Unity 6.0+ docs mark XR on Vulkan
  and GLES partial, no GPU time (Q1-106); `Unity.XR.Oculus.Stats.PerfMetrics`
  returns zeros under OpenXR (Q1-099). Owner: `unity-perf:unity-profiling-workflow`.
- **Snapdragon Profiler as the Quest GPU tool.** Treat as unsupported on Quest
  unless proven on your OS build (A3-067); Meta's tool list omits it (A3-057).
  Owner: `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
- **`Temp=` as the thermal signal.** It is legacy from phone VR; use `PLS` /
  `power_level_state` (Q1-016).
- **PhaseSync idle as headroom on current OS.** FrameSync replaced Phase Sync
  from v203; whether the marker survives is unverified (QX-C4). Use
  `slice_headroom_*`, `icfl_*` and stale counts.
- **Perfetto GPU counters need `ovrgpuprofiler -r` running.** True in 2021;
  current MQDH has a GPU Metrics checkbox. Unresolved (ARM-C18): confirm in
  your trace.
- **The VrApi line is VrApi-only.** The 2025 logcat page still documents it
  for OpenXR (`SP=` via `XR_KHR_android_thread_settings`), but no page says
  a Unity OpenXR build prints it (Q1-037, ARM-C19): check with
  `adb logcat -s VrApi` [verify on device].
- **Undocumented props from forum or QA recipes.** `debug.oculus.headlock`
  (G2-010) is on no Meta page; `metavr` flag properties are unpublished
  (Q1-083). Use the CLI.
- **The Stats Definition Guide as current.** It is undated and partly
  pre-2023; the core 5-7 CPU limit is historical (Q1-023).
- **Profiling while charging.** Charging raises sustained clocks on Meta VR
  Glasses; Quest behaviour is unverified, so run thermal captures on battery
  or record the charging state (Q2-064).
- **Dev-build timing as final numbers.** Development Builds carry profiler
  hooks; find hotspots there, confirm numbers on a non-dev build with the CSV
  (Q1-045).

Open items for this skill (no public source; measure): meaning of the
undefined CSV columns (`shader_hitches`, `max_repeated_frames`,
`skipped_frames`, `slice_*`, `icfl_*`, `app_frame_throttle`); Perfetto XR
runtime and GPU counter track names (enumerate with
`SELECT DISTINCT name FROM counter_track`, Q1-056, A3-045); ARM-C18; ARM-C19.

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc] (Q1-001 to Q1-005, Q1-008, Q1-020, A3-049)
- https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ [doc] (Q1-006, Q1-010, Q1-011, Q1-089, Q1-090)
- https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ [doc] (Q1-007, Q1-016, Q1-023, Q1-025)
- https://developers.meta.com/horizon/downloads/package/ovr-metrics-tool-sdk/ [doc] (QUEST-GF1-006)
- https://github.com/elliot170802/Practicas_AR_TSIC/tree/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/Util [doc] (SDK source mirror; Q1-019, Q1-022)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc] (Q1-028 to Q1-037, Q2-068, Q2-069)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat/ [doc] (Q1-027, Q1-035, Q1-039)
- https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ [doc] (Q2-031; Q1-089 half-rate example)
- https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ [doc] (Q1-040 to Q1-043, A3-047)
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ [doc] (Q1-043 to Q1-047, A3-045, A1-084)
- https://developers.meta.com/horizon/blog/how-to-run-a-perfetto-trace-on-oculus-quest-or-quest-2/ [doc] (Q1-048, A3-046; 2021)
- https://github.com/meta-quest/agentic-tools [doc] (Meta-published; Q1-049 to Q1-055, Q1-083)
- https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ [doc] (QUEST-GF1-003, QUEST-GF1-005)
- https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ [doc] (QUEST-GF2-010, QUEST-GF2-012; auto-captions)
- https://developers.meta.com/horizon/resources/publish-performance-analytics/ [doc] (QUEST-GF2-013)
- https://developers.meta.com/horizon/documentation/unity/unity-quest-runtime-optimizer/ [doc] (Q1-092, Q1-093)
- https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ [doc] (Q1-057)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ [doc] (Q1-058, A3-035)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ [doc] (Q1-059, A3-042)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-capture/ [doc] (Q1-060)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc] (Q1-061, A3-043)
- https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ [doc] (Q1-062, A3-036 to A3-041)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ [doc] (Q1-063)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-ai-tools/ [doc] (Q1-064, A3-044)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc] (Q1-065 to Q1-073, A3-027 to A3-034)
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc] (G2-009)
- https://github.com/tommy-xr/functor/blob/HEAD/.claude/skills/oculus-profiling/SKILL.md [community] (Q1-065 binary path, Q1-074) and [measured] (Q1-075)
- https://arxiv.org/abs/2509.10703 [community] (Q1-076)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc] (Q1-077 to Q1-082)
- https://developers.meta.com/horizon/documentation/unity/os-fixed-foveated-rendering/ [doc] (Q1-081)
- https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ [doc] (Q3-028, Q3-045)
- https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ [doc] (Q2-039, A3-051)
- https://developers.meta.com/horizon/blog/how-to-obtain-stable-gpu-measurements-on-quest/ [doc] (Q2-039, Q2-040; 2021)
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc] (A3-052)
- https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ [doc] (Q2-014)
- https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ and https://developers.meta.com/horizon/documentation/unity/unity-asw/ [doc] (Q3-074)
- https://developers.meta.com/horizon/essentials/thermal/ [doc] (Q2-060)
- https://developers.meta.com/horizon/documentation/unity/optimize-performance/ [doc] (Q2-064)
- https://developers.meta.com/horizon/documentation/unity/ts-gpumeminfo/ [doc] (Q1-095)
- https://developers.meta.com/horizon/documentation/unity/ts-simpleperf/ [doc] (Q1-096)
- https://developers.meta.com/horizon/resources/developer-tools/ [doc] (A3-057, A3-067)
- https://docs.unity3d.com/6000.0/Documentation/Manual/frame-timing-manager.html [doc] (Q1-106)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/api/Unity.XR.Oculus.Stats.PerfMetrics.html [doc] (Q1-099)
- CSV captures: https://github.com/batunii/Arjuna/blob/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_142600.csv , https://github.com/DemoySegment/CubemapRendering/blob/HEAD/Demo/com.DefaultCompany.lakedemo%23UnityPlayerActivity-20260102_033328.csv , https://github.com/Raiduy/GAS-publication-figures/blob/main/Raw%20Data/Gym%20Class/com.IRLStudios.GymClass-20231015_201503.csv [measured] (Q1-009, Q1-012 to Q1-017, QUEST-GF1-008, QUEST-GF2-002)
- https://github.com/Grizfreak/network-data [community] (Q1-018)
