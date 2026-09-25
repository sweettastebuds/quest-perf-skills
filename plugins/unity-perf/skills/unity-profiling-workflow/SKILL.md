---
name: unity-profiling-workflow
description: "Profiling a Unity app on Quest 2/3/3S with Unity's tools: Profiler attached to a development build, reading XR.WaitForGPU and Gfx.WaitForPresent correctly, custom ProfilerMarkers, FrameTimingManager, in-app XR stats (XRDisplaySubsystem, OVRPlugin perf metrics, the OpenXR 1.18 ms-to-seconds change), Frame Debugger, Project Auditor, Profileable builds, dev-build overhead. Use when reading a Unity Profiler capture from Quest or instrumenting code for on-device measurement. Unknown bottleneck: quest-perf:quest-triage; OVR Metrics, Perfetto, ovrgpuprofiler: quest-perf:quest-profiling-toolkit."
---

# Unity profiling workflow on Quest

Goal: **measurement** that serves both goals. Throughput work needs the frame
classified (main thread vs render thread vs GPU) before anything is changed.
Consistency work needs release-build p95/p99 and hitch attribution over 20-30
minute sessions, not a single dev-build frame. Scope: Quest 2 (XR2 Gen 1,
Adreno 650) and Quest 3/3S (XR2 Gen 2, Adreno 740). Unity 2021.3 LTS
(URP 12) to 6.6 (URP 17.x), OpenXR plugin 1.x or Oculus XR plugin 4.x, Vulkan
primary and GLES legacy.

## When to use / when not

Use when:
- You are reading a Unity Profiler capture from a headset: "what does `XR.WaitForGPU` mean", "main thread waits on `Gfx.WaitForPresentOnGfxThread`", `WaitForJobGroupID`, "which marker is the hitch".
- You are adding `ProfilerMarker`s, `ProfilerRecorder` HUDs/loggers, `FrameTimingManager` reads, or `XRDisplaySubsystem` / `OVRPlugin.GetPerfMetrics*` telemetry.
- In-app GPU times jumped 1000x after an OpenXR plugin upgrade (1.18.0-pre.2 unit change; this skill is the sole owner).
- Deciding dev build vs release build vs Profileable Shell, headless `.raw` capture, Profile Analyzer A/B, Project Auditor pre-pass, Frame Debugger vs on-device tools.

When not:
- Bottleneck unknown and no tool chosen yet, headroom rules, camera-off / render-scale test: `quest-perf:quest-triage`.
- Running OVR Metrics CSV, Perfetto, ovrgpuprofiler, RenderDoc Meta Fork, simpleperf, gpumeminfo, setprops, Runtime Optimizer: `quest-perf:quest-profiling-toolkit`.
- What an Adreno counter means: `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
- Fixing what the capture found: GC/physics/UI/jobs `unity-perf:unity-cpu-scripting`; draw calls and SetPass `unity-perf:unity-draw-calls-batching`; first-use shader hitch `unity-perf:unity-shader-hitches`; load/stream spikes `unity-perf:unity-memory-assets`; pass count and load/store `unity-perf:unity-render-graph-tiling`.
- Stale frames, PhaseSync/FrameSync, OpenXR Latency Optimization choice: `quest-perf:quest-frame-pacing`.
- Levels, throttling, long-session thermal protocol: `quest-perf:quest-levels-thermal`.
- Upgrade regressions in general: `unity-perf:unity-upgrade-risks`.

## Diagnose first

1. **Connect the Profiler to a Development Build** (U5-084). Build Settings / Build Profile: Development Build + Autoconnect Profiler. In the Profiler target list pick `AndroidProfiler(ADB@127.0.0.1:34999)`. If it does not appear:
   ```sh
   adb forward tcp:34999 localabstract:Unity-<bundle id>
   ```
   Open firewall ports 54998-55511. On Unity 6.6, set Player > Managed Code Variant = **Instrumented**: the default Release variant removes the Render Graph Viewer connection and RG profiling samplers from Development Builds (U1-030), and probably also user `ProfilerMarker`s (inference from U5-079/U5-018, [verify on device]).
2. **Pin CPU/GPU levels** for any timing comparison, because clocks move under dynamic levels (U5-087, Q1-079). Commands are owned by `quest-perf:quest-profiling-toolkit`; the short form is `adb shell setprop debug.oculus.cpuLevel 4` and `adb shell setprop debug.oculus.gpuLevel 4`. Reboot to unpin before any consistency soak.
3. **Classify each slow frame** in Timeline view, main thread first (U5-081, U5-082):
   - `XR.WaitForGPU` on the main thread longer than one frame budget: **GPU-bound**. It is wait time, not CPU cost.
   - Frame over budget while `XR.WaitForGPU` is short: **CPU-bound**. Then check which thread: main thread busy in `PlayerLoop` scripts, or main thread blocked in `Gfx.WaitForRenderThread` (render thread is the long pole).
   - Render thread in `Gfx.WaitForPresentOnGfxThread`: inside `Gfx.PresentFrame` means GPU-bound; inside `Camera.Render` means CPU/render-thread-bound.
   - `WaitForJobGroupID` / `Semaphore.WaitForSignal` on the main thread: jobs completed too early or the worker pool is saturated.
   - Under OpenXR "Prioritize Input Polling" (Meta's recommendation) the wait sits at frame start (`xrWaitFrame` before simulation) rather than in present (U5-093). Do not count it, or PhaseSync idle, as wasted time (Q1-051). Unity's OpenXR default is Prioritize Rendering (U5-092), where the wait stays in present; check the project's setting before reading wait placement (conflict U5-C2, resolved for Quest in favour of Input Polling; `quest-perf:quest-frame-pacing` owns the choice).
4. **Confirm with a release-build number.** Dev-build timings locate the cost; the final number comes from a non-development build with OVR Metrics CSV (Q1-045) or the in-app logger in Fix 4.

Full marker list, meaning and owning skill: read
[references/profiler-markers.md](references/profiler-markers.md) whenever a
marker name in a capture is not covered above, or when writing Perfetto SQL
against Unity thread and slice names.

## Key numbers

| Number | Meaning | Applies to | Source |
|---|---|---|---|
| 13.9 / 11.1 / 8.3 ms | Frame budget at 72 / 90 / 120 Hz; the threshold for "`XR.WaitForGPU` longer than one frame" | `Quest 2` `Quest 3/3S` | Q2-009 [doc] |
| 1-4 ms | Normal PhaseSync idle at the start of `PlayerLoop`; near 0 ms means the budget is used up | `Quest 2` `Quest 3/3S` `OpenXR`; FrameSync builds (v203+) unverified | Q1-051 [doc] |
| 4 frames (GPU 3) | FrameTimingManager result latency | `Unity 2021.3-6.6` | U5-090, Q1-106 [doc] |
| Partial | FrameTimingManager on XR, Vulkan and GLES: no render-thread or GPU frame time; `cpuMainThreadFrameTime` usable | `Unity ≥ 6000.0` docs; 2022.3 docs have no XR row (Q1-C10) | Q1-106 [doc] |
| 6000.6.0b1 | FrameTimingManager reports GPU times from OpenXR devices; unverified on Quest (X-C3) | `Unity ≥ 6000.6` `OpenXR` | U1-057 [doc] [verify on device] |
| seconds | `XRDisplaySubsystem` time unit per Unity's API docs | `Unity 2021.3-6.6` | Q1-097 [doc] |
| ms, then seconds | `GPUAppLastFrameTime` / `GPUCompositorLastFrameTime` were written in ms before OpenXR 1.18.0-pre.2 (2026-06-16), seconds from it: a 1000x error across the upgrade | `OpenXR plugin` | U5-091, Q3-060 [doc] |
| 34999; 54998-55511 | Profiler ADB port; Unity profiler port range (firewall) | all | U5-084 [doc] |
| 16 MB (Editor 256 MB) | Player profiler buffer default (`-profiler-maxusedmemory`); raise for long captures | all | U5-086 [doc] |
| 1 Hz | OVR Metrics CSV row cadence; `AppendCsvDebugString` more often than 1 Hz adds rows with empty metric columns | `Quest 2` `Quest 3/3S` | Q1-020 [doc] |
| OVRPlugin 1.30+ | Needed for `OVRPlugin.GetPerfMetrics*`; clock/level enums 10-13 deprecated in 1.68.0 | `Meta XR Core SDK` (v85 checked) | Q1-101 [doc] |
| 0 | Every value from `Unity.XR.Oculus.Stats.PerfMetrics` under the OpenXR runtime | `Oculus XR 4.5.x` on `OpenXR` | Q1-099 [doc] |
| 300 frames | Per-variant capture length for Profile Analyzer A/B; a working choice, not a published threshold | all | U5-088 [doc] |
| no published number | Development-build or Profiler overhead on Quest; measure with the dev vs non-dev A/B in Verify | all | Q1-045, U5-087 |
| no published number | Release-build `ProfilerRecorder` overhead | all | U5-080; measure logger on vs off in OVR Metrics |

## Fixes, ranked by payoff ÷ effort

"Fix" here means a change to how you measure. Each one prevents a wrong
optimisation (wasted throughput work) or makes p95/p99 visible (consistency).

### 1. Read the wait markers as waits

What: before optimising anything, classify frames with the rules in Diagnose
first step 3. `XR.WaitForGPU` is the most commonly misread marker: a 6 ms
`XR.WaitForGPU` on the main thread is GPU time, and no script optimisation
moves it (U5-081). Persistent misses lock the app into rendering every other
frame, so a CPU-side change can look like it does nothing until the frame fits.
Hand the classified frame to `quest-perf:quest-triage` for routing.
Effect: prevents CPU work on a GPU-bound frame (average) and separates the
spike thread (variance). Cost: none.
Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` `Vulkan` `GLES`. Goal: Throughput, Consistency.

### 2. Profile at pinned levels; ship-number from non-dev builds

What: pin levels for every A/B (Diagnose step 2). Treat dev-build timings as
relative: Profiler overhead inflates draw and submission timings, and
boundary/compositor GPU preemptions add GPU noise (U5-087). Take the final
number from a non-development build with OVR Metrics CSV (Q1-045). Known
dev-build distortions:
- GLES + Multiview + Oculus XR 4.4.0 (6000.0.33f1): continuous `GL_INVALID_OPERATION` logging costs CPU; filter logcat or confirm on a non-dev build (G2-057, UUM-102876, Closed Won't Fix, [community]). `GLES`.
- Meta's `OVRMetricsCore` frame-time metrics are `developmentOnly`; a release build shows only memory and count metrics (Q1-022).
- The Runtime Optimizer forces a Development Build (owned by `quest-perf:quest-profiling-toolkit`).
Effect: removes clock-scaling noise from averages; stops dev-build artefacts
being "fixed". Cost: two builds per measurement.
Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6`. Goal: Throughput, Consistency.

### 3. Instrument with ProfilerMarker, not Deep Profiling

What: wrap hot systems in `ProfilerMarker` (integer ID, works in jobs,
compiled out of Release builds) instead of `Profiler.BeginSample` (passes the
string) or Deep Profiling, which is much slower, exaggerates small frequent
methods and can run out of memory on device (U5-079, U5-085). For GC.Alloc
sites use CPU module > Call Stacks, including worker threads (U5-012).
```csharp
// Unity 2021.3+. Markers show in the Unity Profiler and, in Development builds,
// in Perfetto via ATrace (Q1-045, U5-097).
using Unity.Profiling;
using UnityEngine;

public sealed class EnemyDirector : MonoBehaviour
{
    static readonly ProfilerMarker s_Tick  = new ProfilerMarker(ProfilerCategory.Scripts, "Game.EnemyDirector.Tick");
    static readonly ProfilerMarker s_Paths = new ProfilerMarker(ProfilerCategory.Scripts, "Game.EnemyDirector.Paths");

    void Update()
    {
        using (s_Tick.Auto())
        {
            using (s_Paths.Auto()) { /* path requests */ }
            /* rest of tick */
        }
    }
}
```
Unity 6.6: markers are `[Conditional]`, and the default Managed Code Variant
is Release, so set Player > Managed Code Variant = Instrumented (or Checked)
for profiling builds; Release also drops the Render Graph Viewer connection and
RG profiling samplers from Development Builds (U5-018 / U1-030; marker loss is
an inference, [verify on device]).
Effect: attribution of p99 spikes to named systems without distorting the
frame. Cost: minutes per system.
Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` `Unity ≥ 6000.6` (variant). Goal: Consistency, Throughput.

### 4. Log release-build frame stats in-app (with the OpenXR unit fix)

What: a Release player cannot use the Profiler, but `ProfilerRecorder`
("Main Thread", "GC Reserved Memory") works there (U5-080), and
`XRDisplaySubsystem` gives app/compositor GPU time and dropped frames when the
provider fills them (U5-091, Q1-097). Log them per frame into a preallocated
buffer and write the CSV only on pause/quit, so the logger adds no file I/O or
GC during the run.

Unit handling: the API contract is seconds. OpenXR plugin versions before
1.18.0-pre.2 wrote app and compositor GPU time in ms (Q3-060). Put the
logger in an asmdef and add a Version Define: resource
`com.unity.xr.openxr`, expression `[1.0.0,1.18.0)`, define
`OPENXR_GPU_TIME_IN_MS`. How the expression orders package pre-releases
(1.18.0-pre.1 is ms, 1.18.0-pre.2 is seconds) is not documented; on a
1.18.0-pre.x plugin set the define by hand. The runtime check below flags a
value over 1.0 in seconds mode, which can only be ms.

Run: copy [scripts/QuestFrameStatsLogger.cs](scripts/QuestFrameStatsLogger.cs)
into an asmdef in Assets (the one carrying the Version Define) and add it to one
GameObject in the first scene. Build, run the session, then
`adb pull /sdcard/Android/data/<pkg>/files/framestats_*.csv`. The script
preallocates `capacity` rows (216000 = 120 Hz x 30 min), logs `Main Thread`
and `GC Reserved Memory` recorders, FrameTimingManager columns behind
`UNITY_2022_3_OR_NEWER`, and `XRDisplaySubsystem` app/compositor GPU time and
dropped-frame count through `GpuToMs` (seconds x 1000, or pass-through under
`OPENXR_GPU_TIME_IN_MS`, with a one-time warning when a seconds-mode value
exceeds 1.0). It logs a one-time `caps` line of which stats the provider fills,
and writes the CSV on pause, disable or quit. Untested on device.
Other stats APIs, in short (full matrix and the `OVRPlugin.PerfMetrics` enum
in [references/profiler-markers.md](references/profiler-markers.md)):
`OVRPlugin.GetPerfMetricsFloat` works under OpenXR (check
`IsPerfMetricsSupported` per metric; units unstated, compare with OVR Metrics)
(Q1-101); Oculus `Stats.PerfMetrics` returns 0 and `GetAppPerfStats` returns
empty under OpenXR (Q1-099, Q1-104); `XRStats` is deprecated from 6000.3
(Q1-098); `XR_META_performance_metrics` counters must not drive adaptive
quality, which belongs to `quest-perf:quest-resolution-foveation` (Q1-103).

Effect: release-build p95/p99 of main-thread and app GPU time, and dropped
frames, over a full session. Cost: about 7 MB of rows at the default capacity
(32-byte row x 216000); overhead unpublished, see Key numbers.
Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` (FTM columns `Unity ≥ 2022.3`) `OpenXR` `Vulkan` `GLES`. Goal: Consistency, Throughput.

### 5. Tag OVR Metrics CSV rows with game state

What: call `OVRMetricsToolSDK.Instance.AppendCsvDebugString(...)` at segment
boundaries (scene loaded, combat start, cutscene), never per frame (A3-050,
Q1-020). The CSV analyser in `quest-perf:quest-profiling-toolkit` splits its
report by that column.
```csharp
// Requires Meta XR Core SDK. QUEST_META_CORE_SDK: add as a Version Define on
// com.meta.xr.sdk.core in your asmdef, and reference the assembly that contains
// OVRMetricsToolSDK in your Meta XR SDK version (check the package's asmdefs)
// [verify on device]; or use a Scripting Define Symbol if your code has no asmdef.
#if QUEST_META_CORE_SDK
public static class PerfSegment
{
    public static void Mark(string segment)
    {
        var sdk = OVRMetricsToolSDK.Instance;
        if (sdk != null) sdk.AppendCsvDebugString(segment); // at boundaries only (<= 1 Hz)
    }
}
#endif
```
Effect: per-segment p95 and stale counts instead of a session average that
hides the bad scene. Cost: a few calls.
Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` `Meta XR Core SDK`. Goal: Consistency.

### 6. Headless `.raw` capture for rare hitches

What: a hitch that shows once in ten minutes is lost in a live Profiler
session. Start a Development player with the capture arguments via the
`-e unity` intent extra (U5-086, U5-033):
```sh
adb shell "am start -n <pkg>/com.unity3d.player.UnityPlayerActivity -e unity '-profiler-enable -profiler-log-file /sdcard/Android/data/<pkg>/files/hitch.raw -profiler-capture-frame-count 5000 -profiler-maxusedmemory 268435456'"
adb pull /sdcard/Android/data/<pkg>/files/hitch.raw .
```
`adb shell` joins its arguments and runs them through the device shell, so the
whole `am start` line is one remote string and the profiler flags are single-quoted
inside it. PowerShell and cmd quote differently from sh: the outer double quotes
must reach adb unchanged.
GameActivity builds (the default for new Unity 6 projects; OpenXR 1.16.0-pre.2+
adds a Meta Quest validation rule requiring it on Unity 6.0+, U5-026) use a
different activity class, e.g. `UnityPlayerGameActivity`; check
`adb shell dumpsys package <pkg>`.
Whether `-e unity` is honoured on your build is [verify on device];
`-profiler-maxusedmemory` takes bytes (268435456 = 256 MB) (U5-086). Open the `.raw` in the
Profiler and search first for the known-hitch markers (`AssetBundle.asset`,
`AsyncUploadManager.AsyncBufferResized`, `Rigidbody.SetKinematic`,
`Animation.AddClip`, `Shader.CreateGPUProgram`, `GC.Collect`) (U5-101, G3-002).
Effect: catches p99/p99.9 spikes. Cost: dev build, one run.
Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6`. Goal: Consistency.

### 7. A/B with Profile Analyzer, not single frames

What: Window > Package Manager > `com.unity.performance.profile-analyzer`
(1.4.0, Unity 2021.3+). Load two captures of identical content at pinned
levels, at least 300 frames each (working choice), and compare marker median
and distribution (U5-088). Unity 6.6's Profiler adds per-frame screenshots,
which tie a spike to what was on screen (U5-100).
Effect: stops single-frame noise being read as a win or a regression (variance),
and makes median shifts visible (average). Cost: two captures per A/B.
Tags: `Unity 2021.3-6.6`. Goal: Throughput, Consistency.

### 8. Run Project Auditor before profiling

What: static pre-pass for costly code patterns and settings. Package on
2021.3 (1.1.0), 2022.3 (2.0.0) and 6.0-6.3 (3.1.1); built into the Editor
from 6.4; 6.5 flags obsolete APIs; 6.6 adds a URP Settings Analyzer whose
rule set was not inspected for Quest rules (HDR, MSAA, Tile-Only), so do not
treat a clean report as a Quest settings audit (U1-056 / U5-099 / U2-096). The
Quest settings audit is `unity-perf:unity-urp-settings`.
Effect: finds code and settings problems before any capture (average). It does
not measure device timing. Cost: minutes; no runtime cost.
Tags: `Unity 2021.3-6.6`. Goal: Throughput.

### 9. Use the right tool for render inspection

What: the Frame Debugger is not supported on Meta/Oculus devices, only the
mock HMD (U1-058). Use it in the Editor for batch-break reasons, which are
CPU-side and largely device-independent; it cannot show multiview output,
tile passes or foveation (X-C2). On device use the Render Graph Viewer
(Window > Analysis > Render Graph Viewer, connects to a Development Build from
6.3; 6.6 needs the Checked or Instrumented variant) or RenderDoc Meta Fork
(`quest-perf:quest-profiling-toolkit`).
Effect: prevents chasing device-only rendering questions in a tool that cannot
show them. Cost: none in the Editor; on 6.6 a Checked or Instrumented build for
the RG Viewer.
Tags: `Unity 2021.3-6.6` (Frame Debugger, Editor only) `Unity ≥ 6000.3` `URP 17+` (RG Viewer on device) `Quest 2` `Quest 3/3S`. Goal: Throughput.

### 10. Profile near-shipping code with Profileable Shell

What: Unity 6.6 adds an Android Profileable Shell build setting so Perfetto
and simpleperf can profile release builds without Development Build overhead
(U5-098 / U1-057). Before 6.6, `<profileable android:shell="true"/>` in a
custom manifest is not Unity-documented [verify on device]. Perfetto markers
from `ProfilerMarker` still need a Development build (Q1-045); callstack
sampling of stripped builds needs symbol folders (Q1-047). In Perfetto the
Unity render thread is `UnityGfxDeviceW` (Q1-050 lists it as `UnityGfx`), not
Android's `RenderThread` (A1-052 [community]).
Effect: Perfetto and simpleperf timings without Development Build distortion
(average and variance). Cost: no `ProfilerMarker` slices, because those need a
Development build (Q1-045).
Tags: `Unity ≥ 6000.6` `Quest 2` `Quest 3/3S`. Goal: Throughput, Consistency.

## Verify

- **Classification**: after a GPU-side fix on a frame classified GPU-bound, `XR.WaitForGPU` shrinks by about the GPU saving and OVR Metrics app GPU time drops by the same order; main-thread script time is unchanged. If `XR.WaitForGPU` did not move, the frame was not GPU-bound. Pinned levels, same route, 2-5 minutes per build.
- **Dev-build overhead**: build the same commit as Development and non-Development; compare p50 app CPU/GPU time in OVR Metrics at pinned levels over 5 minutes. The delta is your dev-build tax; no published number exists (Q1-045, U5-087).
- **Logger**: first-run logcat shows the `caps` line. `app_gpu_ms` should sit within the range of OVR Metrics `app_gpu_time_microseconds`/1000 for the same segment (CSV rows are 1 Hz averages, Q1-010). A ~1000x mismatch means the unit define is wrong. Then soak 20-30 minutes unpinned and read p95/p99 of `main_ms` and `app_gpu_ms` and the growth of `dropped_raw`.
- **6.6 FTM GPU (X-C3)**: log `ftm_gpu_ms` on a 6.6 Quest build; if nonzero, compare with OVR Metrics GPU time. Record the result per device and API.
- **XRDisplaySubsystem fill (Q1-097)**: record the `caps` line per device, plugin version and API.
- **Markers**: in a 6.6 Development Build with variant Release vs Instrumented, check whether your `Game.*` markers appear (U5-018 inference).
- **A/B**: Profile Analyzer median and upper-quartile of the target marker move in the expected direction over ≥ 300 frames; confirm the p95 change in a release-build CSV.

## Pitfalls and myths

- **"`XR.WaitForGPU` is CPU cost, optimise scripts."** It is the main thread waiting on the GPU (U5-081).
- **"Gfx.WaitForPresent means GPU-bound."** Only inside `Gfx.PresentFrame`; inside `Camera.Render` the render thread is the limit (U5-082).
- **"FrameTimingManager gives GPU time on Quest."** Not on XR before 6.6 (Partial, Q1-106); 6.6 is unverified (X-C3). Profiler Highlights uses FrameTiming, so it probably cannot classify XR frames [verify on device] (U5-096). The 2022.3 page shows no XR row, which is likely a doc gap (Q1-C10).
- **Comparing in-app GPU times across OpenXR 1.18.0-pre.2** without normalising: 1000x (Q3-060). A home-made dynamic-resolution controller reading these values breaks the same way. The OVR Metrics CSV is not affected: it is written by the OVR Metrics service (Outline decision 49).
- **"All XRDisplaySubsystem stats work on Quest."** Only what the provider fills; no published list (Q1-097).
- **Oculus PerfMetrics / GetAppPerfStats in an OpenXR build**: zeros or empty, no error (Q1-099, Q1-104).
- **Using `XR_META_performance_metrics` to drive quality**: the spec says not to (Q1-103).
- **Deep Profiling on Quest**: slow, memory-hungry, skews small methods (U5-085).
- **Profiling at dynamic levels**: clock changes masquerade as regressions (U5-087). Log `OnXrPerformanceChangeNotification` (OpenXR 1.11+) next to frame times so throttling is not read as a code regression (U5-094).
- **Frame Debugger for device rendering questions** (multiview, tiles, foveation): not supported on device (U1-058, X-C2).
- **"Disable Multithreaded Rendering to see the full render cost"** (Meta's debugging advice, U3-001 / U5-083): fine for a debug capture, but never ship with it off and never compare those timings with a shipping build (`unity-perf:unity-cpu-scripting`).
- **Perfetto `RenderThread` is Unity's render thread**: it is Android HWUI; watch `UnityGfxDeviceW` (A1-052).
- **Calling `AppendCsvDebugString` every frame** breaks the 1 Hz CSV cadence (Q1-020).
- **Memory from `Profiler.GetRuntimeMemorySizeLong` in release**: excludes graphics memory; memory workflow is `unity-perf:unity-memory-assets`.

## Sources

All accessed 2026-09-24.

- https://docs.unity3d.com/6000.6/Documentation/Manual/VRFrameTiming.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Profiling.ProfilerMarker.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Profiling.ProfilerRecorder.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/android-profile-on-an-android-device.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-deep-profiling.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-command-line-arguments.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/performance-track-garbage-collection.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/android-thread-configuration.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/android-application-entries-game-activity-requirements.html [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-profiler-tool/ [doc]
- https://developers.meta.com/horizon/documentation/unity/tools-unityprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ [doc]
- https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ [doc]
- https://packages.unity.com/com.unity.performance.profile-analyzer [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/frame-timing-manager.html [doc]
- https://docs.unity3d.com/6000.0/Documentation/Manual/frame-timing-manager.html [doc]
- https://docs.unity3d.com/2022.3/Documentation/Manual/frame-timing-manager.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html [doc]
- https://docs.unity3d.com/6000.0/Documentation/Manual/ProfilerHighlights.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/ScriptReference/XR.XRDisplaySubsystem.TryGetDroppedFrameCount.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/ScriptReference/XR.XRStats.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/api/Unity.XR.Oculus.Stats.PerfMetrics.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/api/Unity.XR.Oculus.Stats.AdaptivePerformance.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/project-configuration.html [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc]
- https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/OVRPlugin.cs [doc] (SDK source mirror)
- https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/Util/OVRMetricsCore.cs [doc] (SDK source mirror)
- https://github.com/Fb-dtalker/UnityMetaMRC/blob/HEAD/OVRMrclibUnloadLog.log [community]
- https://github.com/KhronosGroup/OpenXR-Docs/blob/main/specification/sources/chapters/extensions/meta/meta_performance_metrics.adoc [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ [doc]
- https://github.com/meta-quest/agentic-tools [doc] (Meta-published agent skill: hz-perfetto-debug)
- https://discussions.unity.com/t/android-thread-configuration-render/1731103 [community]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc]
- https://unity.com/releases/editor/whats-new/6000.6.0b1 [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc]
- https://discussions.unity.com/t/unity-64-and-development-build-deprecation-and-managed-code-variants/1721546 [doc] (Unity staff post)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity64.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html [doc]
- https://packages.unity.com/com.unity.project-auditor [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html [doc]
- https://issuetracker.unity.com/api/v1.0/issues/14139 [community] (UUM-102876)
- https://docs.unity3d.com/6000.0/Documentation/Manual/assembly-definition-includes.html [doc] (Version Defines syntax; web check)
