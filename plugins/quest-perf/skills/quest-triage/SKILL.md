---
name: quest-triage
description: "Entry point for any Meta Quest 2/3/3S Unity performance problem whose cause is unknown: low FPS, stutter, judder, hitches, \"is it CPU-bound or GPU-bound?\". Decides CPU main/render thread vs GPU vs pacing vs thermal vs memory with OVR Metrics, logcat and Meta's camera-off / render-scale test, then routes to the owning quest-, unity-, gles- or xr2- skill. Use first when no bottleneck has been identified."
---

# Quest triage: find the bottleneck, then hand off

Applies to Quest 2 (XR2 Gen 1, Adreno 650) and Quest 3/3S (XR2 Gen 2, Adreno 740), Unity 2021.3 LTS (URP 12) through 6.6 (URP 17), Vulkan and GLES, unless a line says otherwise. This skill decides *which* bottleneck you have. It does not fix it; each branch ends at the skill that owns the fix.

Reference files:
- Read [references/routing-table.md](references/routing-table.md) once the first split is done, or whenever a symptom does not fit the decision tree below. It maps every symptom and signal to one of the 33 skills, and holds the full signal-to-verdict map.

## When to use / when not

Use when:
- FPS is low, the image stutters or judders, or there are hitches, and nobody has yet shown *where* the time goes.
- Someone asks "CPU-bound or GPU-bound?", "why is it slow", "where do I start".
- A capture exists but has not been classified (main thread, render thread, GPU, pacing, thermal, memory).

Do not use when the bottleneck is already known. Go straight to the owner:
- How to run a tool, pin levels, or parse a CSV/trace: `quest-perf:quest-profiling-toolkit` (also owns the Quest Runtime Optimizer).
- Reading a Unity Profiler capture (`XR.WaitForGPU`, `ProfilerMarker`, FrameTimingManager): `unity-perf:unity-profiling-workflow`.
- Named GC, physics, UI or script spikes: `unity-perf:unity-cpu-scripting`.
- Stale frames with average frame time already in budget: `quest-perf:quest-frame-pacing`.
- Drops that grow over a session: `quest-perf:quest-levels-thermal`.
- Budget sizing per headset, store VRC rules: `quest-perf:quest-budgets-tiers`.

## Diagnose first

### 0. Make the capture trustworthy (2 minutes, always)

- Record with OVR Metrics Tool **Basic** preset, HUD off, CSV on; Advanced adds overhead that distorts results (Q1-006). CSV on by intent:
  `adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV`
- In parallel: `adb logcat -c; adb logcat -s VrApi,XrPerformanceManager` (one VrApi line per second, Q1-027/Q1-028).
- Casting and recording off. OS features such as casting override granted levels, so those captures are not comparable (A1-036, Q1-041).
- Dynamic resolution and dynamic foveation off while diagnosing; validate with them on afterwards (Q3-051).
- Play the level once before judging it: a fresh install compiles shaders on first run (Q1-011). Keep cold and warm runs as separate datasets.
- Record with every capture: refresh rate, `CPU4/GPU=a/b` levels plus MHz, `Lat=`, `PLS=`, `SF=`, device, OS build, Unity/URP version, graphics API (A1-085, Q1-030).
- For a CPU or GPU A/B, pin levels so DVFS does not swamp the difference (Q2-039, A1-085):
  `adb shell setprop debug.oculus.cpuLevel 4` and `adb shell setprop debug.oculus.gpuLevel 4`. Reset every setprop after profiling (they also clear on reboot); the reset procedure is in `quest-perf:quest-profiling-toolkit`.

### 1. First split: App GPU time vs the frame budget (Meta's rule, Q1-089 / Q2-031)

Read `App=` in the VrApi line or `app_gpu_time_microseconds` in the CSV. Do **not** use GPU utilisation for this split.

| Observation | Verdict | Next |
|---|---|---|
| App GPU time > budget, FPS below target | GPU-bound (CPU may also be over, hidden behind it) | Step 2b |
| App GPU time within budget, and FPS below target (or `Stale` > 0 while FPS is below target; `Stale` equal to refresh with steady FPS is extra-latency mode, not CPU-bound, Q1-024) | CPU-bound: main thread **or** render thread | Step 2a |
| FPS at target, `Stale` between 0 and refresh, or `Stale2/5/10` non-zero | Pacing hitch | Step 3 |
| Clock drop or `PLS`=1/2 aligned with a stale burst | Thermal | `quest-perf:quest-levels-thermal` |
| Rising memory trend, then `lowmemorykiller` in logcat | PSS over limit under pressure | `quest-perf:quest-budgets-tiers` |

### 2. Meta's two-step isolation test (Q1-091)

Run it to confirm step 1, and always when step 1 is ambiguous (App GPU time near the budget).

1. **Camera off.** Disable the rendering camera(s). Little change in frame time = CPU-bound. Big improvement = GPU-bound.
2. **GPU-bound only: render scale to minimum.** Meta's step sets `eyeTextureResolutionScale` to 0.01. No change = vertex/geometry-bound (culling and draw submission count as vertex-bound here). Improvement = fill-bound.
   - In URP, `UniversalRenderPipeline` pushes the asset's Render Scale into `XRDisplaySubsystem.scaleOfAllRenderTargets` at init and per camera (Q2-022 / Q3-006), so a direct `XRSettings.eyeTextureResolutionScale` write can be overridden. Drive the URP asset instead. Its range is 0.1-2.0, so the URP test runs at 0.1 per axis (1% of pixels, arithmetic), not Meta's 0.01.
   - Conflict Q3-C5: Meta says set `eyeTextureResolutionScale` (plus URP `renderScale`, Q3-011); Unity says `eyeTextureResolutionScale` is unsupported in URP (Q3-010). The URP source makes the asset value win, so set both to the same value and confirm with `SF=`.
   - Confirm the scale reached the compositor with `SF=` in logcat before reading the result (Q1-033). [verify on device]
   - `Unity ≥ 6000.3` `URP 17.3+`: disable any IUpscaler before the test; otherwise the XR scale is forced to 1.0 (Q3-007) [verify on device]. `SF=` staying at 1.00 is the tell.

Drop-in dev-build script. Adds `QTRIAGE phase=...` markers to logcat so the VrApi lines can be bucketed by phase. Unity 2021.3+ / URP 12+, untested on device.

```csharp
// QuestTriageIsolation.cs - development builds only. Unity 2021.3+ (URP 12) to 6.6 (URP 17).
// Runs: warmup -> BASELINE -> CAMERA_OFF -> RENDER_SCALE_MIN -> restore.
// Read with: adb logcat -s Unity,VrApi  (compare App=, CPU&GPU=, FPS=, SF= per phase)
using System.Collections;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public sealed class QuestTriageIsolation : MonoBehaviour
{
    [SerializeField] Camera[] renderCameras;          // every camera that renders the eye buffer
    [SerializeField] float warmupSeconds = 15f;       // let levels and shaders settle
    [SerializeField] float phaseSeconds = 20f;        // >= 20 s so the 1 Hz lines average out
    [SerializeField] float minRenderScale = 0.1f;     // URP asset lower clamp

    UniversalRenderPipelineAsset urp;
    float savedRenderScale = -1f;
    float savedEyeScale = -1f;

    IEnumerator Start()
    {
        if (renderCameras == null || renderCameras.Length == 0)
            renderCameras = new[] { Camera.main };
        urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
        if (urp == null) { Debug.LogError("QTRIAGE no active URP asset"); yield break; }
        savedRenderScale = urp.renderScale;
        savedEyeScale = UnityEngine.XR.XRSettings.eyeTextureResolutionScale;

        yield return new WaitForSecondsRealtime(warmupSeconds);
        Mark("BASELINE");
        yield return new WaitForSecondsRealtime(phaseSeconds);

        SetCameras(false);
        Mark("CAMERA_OFF");
        yield return new WaitForSecondsRealtime(phaseSeconds);
        SetCameras(true);

        urp.renderScale = minRenderScale;
        // Q3-C5: keep Meta tooling in step with the URP asset value.
        UnityEngine.XR.XRSettings.eyeTextureResolutionScale = minRenderScale;
        Mark("RENDER_SCALE_MIN");
        yield return new WaitForSecondsRealtime(phaseSeconds);

        Restore();
        Mark("DONE");
    }

    void SetCameras(bool on)
    {
        foreach (var c in renderCameras) if (c != null) c.enabled = on;
    }

    void Mark(string phase)
    {
        Debug.Log($"QTRIAGE phase={phase} t={Time.realtimeSinceStartup:F1}");
#if QTRIAGE_OVRMETRICS
        // Meta XR Core SDK: tags the OVR Metrics CSV segment (Q1-020). Check the exact
        // OVRMetricsToolSDK signature in your SDK version before defining QTRIAGE_OVRMETRICS.
        OVRMetricsToolSDK.Instance.AppendCsvDebugString("QTRIAGE_" + phase);
#endif
    }

    void Restore()
    {
        SetCameras(true);
        // Restoring matters in the Editor: runtime edits to the URP asset persist there.
        if (urp != null && savedRenderScale > 0f) urp.renderScale = savedRenderScale;
        if (savedEyeScale > 0f) UnityEngine.XR.XRSettings.eyeTextureResolutionScale = savedEyeScale;
    }

    void OnDisable() => Restore();
}
```

Notes: whether the XR frame loop keeps submitting with every camera disabled is not documented; if `FPS=` goes to 0 in CAMERA_OFF, use the Unity Profiler main-thread time for that phase instead [verify on device]. Changing render scale reallocates eye textures (Q2-022), so ignore the first seconds after the switch.

### 2a. CPU-bound: main thread or render thread?

- Logcat: render-thread CPU time about `CPU&GPU - App` (Unity and Unreal only). Close to the budget = render thread (Q1-032).
- Perfetto: `UnityMain` vs `UnityGfx` slices over budget with no fence waits = CPU-bound; which thread is long picks the branch (Q1-052).
- Unity Profiler: `XR.WaitForGPU` longer than a frame on the main thread means GPU-bound; do not read it as CPU time (U5-081).
- `CPU L` high with `GPU L` low while missing frames (Meta's example 4/2) = CPU-bound (Q1-025 / Q2-032). `CPU U` is the busiest core, not an average.
- Render thread long -> `unity-perf:unity-draw-calls-batching` (GLES builds with GL state calls dominating -> `gles3-perf:gles-driver-overhead`). Main thread long -> `unity-perf:unity-cpu-scripting`. Threads on wrong cores -> `arm-mobile-hw-perf:xr2-cpu-threads-neon`.

### 2b. GPU-bound: fill vs geometry/submission

- Render-scale test improves -> fill-bound -> `quest-perf:quest-resolution-foveation`. Cross-check with an FFR sweep 0->4 via `adb shell setprop debug.oculus.foveation.dynamic 0` then `adb shell setprop debug.oculus.foveation.level N` (N = 0..4): a large drop in App GPU time = fragment-bound (Q1-081 / Q3-028).
- Render-scale test changes nothing -> vertex/geometry/submission-bound -> `unity-perf:unity-draw-calls-batching` and `arm-mobile-hw-perf:xr2-adreno-architecture` (binning-pass vertex cost).
- GPU-bound only in MR -> the level ceiling dropped (Quest 3/3S passthrough caps CPU at L3, GPU at L2), not slower shaders; passthrough cost never appears in App GPU time (Q2-038, Q4-010) -> `quest-perf:quest-mr-costs`.
- Per-surface / per-pass attribution (which pass, LoadColor/StoreDepthStencil) -> captured with tools in `quest-perf:quest-profiling-toolkit`, interpreted in `unity-perf:unity-render-graph-tiling`.
- Automated classification (Quick Perf, Bottleneck Analysis) is the Quest Runtime Optimizer, owned by `quest-perf:quest-profiling-toolkit` (Q1-092).

### 3. Consistency sequence (Q1-094; researcher synthesis of Meta signals, not a Meta procedure)

1. Record a CSV with Basic preset, no HUD, no casting, 20-30 minutes along a scripted route; mark segments with `AppendCsvDebugString`.
2. Per segment: `stale_frame_count`, `stale_frames_consecutive`, `max_repeated_frames`, `shader_hitches`, p95/p99 of `app_gpu_time_microseconds`. Run the OVR Metrics CSV analyzer from `quest-perf:quest-profiling-toolkit` (`scripts/ovr_metrics_csv.py`, arguments documented there) to get these plus both hitch-rate definitions.
3. Correlate stale bursts with clock changes (`adb shell setprop debug.oculus.clockStateLogLevel 1`), `power_level_state`, and GC or loading markers in Perfetto.
4. Label each burst and route:

| Label | Signature | Owner |
|---|---|---|
| Content-bound | App GPU or CPU time over budget during the burst | back to step 1 |
| Pacing | irregular `Stale`, periodic, no single spike; PhaseSync idle near 0 ms | `quest-perf:quest-frame-pacing` |
| Shader/PSO | `shader_hitches` increments; first use only, gone on the warm run | `unity-perf:unity-shader-hitches` (GLES: `gles3-perf:gles-shader-binaries`) |
| Thermal | clock or POW L drop aligned with the burst, grows over the session | `quest-perf:quest-levels-thermal` |
| Load/stream | spike during a load or scene stream | `unity-perf:unity-memory-assets` |
| GC/physics | spike aligned with GC or physics markers | `unity-perf:unity-cpu-scripting` |

On FrameSync OS builds (default for Store apps from v203, Q2-072; FrameSync replaces PhaseSync, Q2-071) the PhaseSync-based label needs re-checking; whether the marker survives is unverified (Q1-051, QX-C4) [verify on device]. On v203+ use the `slice_headroom_*` / `icfl_*` CSV columns and stale counts instead (Q1-014).

## Key numbers

| Number | Value | Applies to | Source |
|---|---|---|---|
| Frame budget | 13.9 ms (13888 µs) @72 Hz, 11.1 ms @90, 8.3 ms @120 | all Quest | Q1-089 / Q2-031, Q2-009 [doc] |
| Unpublished budgets | 80 / 96 / 100 Hz = 12.5 / 10.4 / 10.0 ms | 80 Hz: Quest 2/3/3S; 96/100 Hz: listed on the refresh-rate page (Q2-010) but 'not available on all devices' per the VRC (Q1-084, QUEST-GF1-009) and absent from `debug.oculus.refreshRate` (QX-C5) [verify on device] | 1000/Hz arithmetic; no Meta row |
| Headroom rule | CPU about 70%, GPU about 80%, hitches < 3%, memory about 5 GB (Quest 3) / about 3.5 GB (Quest 2) | Quest 2 (recap only), Quest 3/3S (talk title, GF2-012) | QUEST-GF1-003 [doc, talk recap], QUEST-GF2-012 [doc, talk] |
| Why 70/80 | above ~70-80% OS scheduling jitter and sporadic tasks drop frames (not thermal) | Quest 3/3S | QUEST-GF2-012 [doc] |
| GPU level raise | GPU level rises at ≥ 87% GPU utilisation (falls at ≤ 81%); CPU rises at ≥ 83% (falls at ≤ 77%) | Quest 2/Pro/3/3S | Q2-046 / Q4-003 [doc] |
| Scheduling risk | `GPU%` > 0.9 | all Quest | Q1-025 / Q2-032, Q2-030 [doc] |
| Compositor GPU time | `TW=1.25ms` in Meta's example line (1.27 ms in the field table); grows with layer count/type | all Quest | Q2-030 [doc] [verify on device] |
| Net app headroom after compositor/OS | no published number; measure (see Verify) | all Quest | Q2-030 |
| Dip tolerance | one-off dip of a couple of seconds OK at 72 Hz if > 65 fps and recovers; no cyclic dips. No published number for 90/120 Hz | Quest 2/3/3S @72 Hz | Q1-090 [doc] |
| Consecutive misses | 4+ consecutive missed frames especially noticeable (recap); users notice "two or three" in a row (talk) | Quest 2/3/3S | QUEST-GF1-003, QUEST-GF2-012 [doc] |
| Half-rate trap | `FPS=36/72, GPU%=0.65, App=18.05ms` needs a 23% GPU cut, not 35%; full rate needs `GPU%` < ~50% | all Quest | Q2-031 [doc] |
| App logic | over 2 ms can probably be optimised | Quest 2/3/3S, Unity | Q1-091 [doc] |
| Memory kill | rising PSS then `lowmemorykiller` in logcat; limits are owned by `quest-perf:quest-budgets-tiers` | Quest 2/3/3S | Q2-042 [doc] |
| Passthrough caps | CPU max L3 (1.65 GHz vs 1.92), GPU max L2 (456 vs 545 MHz) | Quest 3/3S | Q2-038 [doc] [verify on device] |
| Agent heuristics (not VRC) | stale rate good < 5% / warn > 10% / critical > 25%; frame-time std dev < 1 / > 2 / > 4 ms; main thread share < 80% / > 80% / > 95%; GPU share < 85% / > 85% / > 95% | Quest 2/3/3S | Q1-053 [doc, Meta agent skill] |

The Meta level rule "design steady state to CPU L4 / GPU L4; L5 is opportunistic" is owned by `quest-perf:quest-levels-thermal` (Q2-028, Q2-029). Per-device budgets and draw-call ranges: `quest-perf:quest-budgets-tiers`.

**Open: what counts as a hitch in "< 3%".** The recap gives the figure, the talk audio never says it, and no denominator is published (QUEST-GF2-012). Report both candidates and the store-style metric (quest.md open unknowns):
- stale frames ÷ rendered frames;
- seconds with `stale_frames_consecutive` ≥ 4 ÷ total seconds;
- maximum stale frames in any 60 s window (matches Performance Analytics "Max Stale Frames", QUEST-GF2-013).

## Fixes, ranked by payoff ÷ effort

Triage fixes are routing and measurement fixes: they make the next change land on the real bottleneck. Content fixes live in the owning skills.

1. **Clean the capture before believing any number.** Basic preset, HUD off, casting off, dynamic resolution and dynamic foveation off, warm run, levels recorded (step 0).
   - Effect: removes tool and OS overhead from both the mean and the variance you are measuring; prevents fixing a phantom bottleneck.
   - Cost: none at runtime; you must re-validate with dynres/dynamic FFR back on.
   - `Quest 2` `Quest 3/3S` `any Unity` `GLES` `Vulkan`. Goal: Throughput and Consistency.
2. **Split with App GPU time vs budget, never with `GPU%` alone** (step 1).
   - Effect: correct CPU-vs-GPU call, especially at half rate where `GPU%` under-reports (Q2-031).
   - Effect is on the average: it picks the branch that lowers mean frame time. It has no direct effect on variance.
   - Cost: none. `Quest 2` `Quest 3/3S` `any Unity`. Goal: Throughput.
3. **Run the two-step isolation script** (step 2) and read `CPU&GPU - App` for the render thread.
   - Effect: separates main thread, render thread, fill and geometry in one ~75 s run.
   - Effect: on the average only. It picks the branch whose fix lowers mean frame time. It does not change variance, and the render-scale switch causes a one-off reallocation spike (Q2-022).
   - Cost: dev build only; render scale change reallocates eye textures (Q2-022).
   - `Quest 2` `Quest 3/3S` `Unity ≥ 2021.3` `URP 12+` `GLES` `Vulkan`. Goal: Throughput.
4. **Pin levels for every A/B** (`debug.oculus.cpuLevel` / `gpuLevel` 4, Q2-039), then unpin for the validation run.
   - Effect: removes level changes that otherwise swamp code-level differences (A1-085); shrinks run-to-run variance.
   - Cost: pinned numbers are not what users get; never ship conclusions from a pinned run alone.
   - `Quest 2` `Quest 3/3S` `any Unity`. Goal: Throughput and Consistency.
5. **Label every stale burst with the consistency sequence** (step 3) over 20-30 minutes.
   - Effect: targets p95/p99 and hitches rather than the mean; catches thermal decay a 1-minute run misses.
   - Cost: a 20-30 minute scripted route per build.
   - `Quest 2` `Quest 3/3S` `any Unity`. Goal: Consistency.
6. **Hold the headroom rule as the exit criterion**: CPU about 70%, GPU `gpu_utilization_percentage` ≤ 0.8 at the shipping refresh rate, both hitch ratios < 3%.
   - Effect: leaves margin below the 87% level-raise and 0.9 scheduling-risk lines, so OS contention does not drop frames (QUEST-GF2-012).
   - Cost: content budget spent on margin. "70% CPU" is ambiguous (busiest core vs aggregate): check both `cpu_utilization_percentage` and per-core columns [verify on device].
   - `Quest 2` `Quest 3/3S` `any Unity`. Goal: Consistency.
7. **Before switching graphics API to fix performance, route to `gles3-perf:gles-vs-vulkan`** (UUM-93226 and the A/B protocol live there).
   - Effect: prevents an API switch that can raise both average frame time and variance.
   - Cost: none from routing. The A/B itself costs a second build per device.
   - `Quest 2` `Quest 3/3S` `GLES` `Vulkan`. Goal: Throughput.

## Verify

- **Classification check:** the fix chosen from the owning skill must move the metric that triggered the route: App GPU time for GPU-bound; `CPU&GPU - App` or `UnityGfx` slice length for render thread; `UnityMain` / `PlayerLoop` p95 for main thread. If the triggering metric does not move, the classification was wrong: rerun step 2.
- **Throughput target:** App GPU time p95 at or below budget minus `TW`, with margin for the next thermal step, read at locked levels and at the shipping layer count (Q2-030). No published margin figure exists; measure `TW`, `GD` and `App` together.
- **Consistency target:** `Stale2/5/10` = 0 and `stale_frames_consecutive` = 0 in steady play; both hitch ratios < 3%; max stale frames per 60 s window reported (QUEST-GF2-013).
- **Session length:** triage phases run ≥ 20 s each (the 1 Hz lines need several samples; Q1-055 uses ≥ 20 s of steady play); the exit check is a 20-30 minute scripted soak with levels unpinned, comparing first vs last 5 minutes of `cpu_frequency_MHz`, `gpu_frequency_MHz`, `power_level_state` and p95 App GPU time (Q1-094, Q1-016 / Q2-061). Use the analyzer in `quest-perf:quest-profiling-toolkit`.
- **Frame-level check:** the CSV is 1 Hz interval averages and cannot show a single-frame hitch (Q1-010). For single-frame spikes, confirm in Perfetto: p95/p99 and max of `PlayerLoop` `dur` on `UnityMain` over ≥ 20 s steady play (Q1-055).

## Pitfalls and myths

- **"GPU% is 65%, so there is 35% headroom."** At half rate `GPU%` under-reports; use App ms (Q2-031).
- **"Stale = 72 every second means failure."** Stale equal to refresh with steady FPS is extra-latency mode, not a failure; irregular stale counts and consecutive runs are the failure signal (Q1-024 / Q2-066). Default latency mode for Unity is itself contested (Q1-C5): record `Lat=` with every capture.
- **Perfetto stale-frame SQL from Meta's agent skill.** It counts every `PlayerLoop` over 11.1 ms as stale, hard-coding 90 Hz and confusing CPU frame time with compositor staleness. Use VrApi `Stale` or CSV `stale_frame_count` (Q1-054, Q1-C7).
- **PhaseSync / `xrWaitFrame` wait is not wasted time.** The runtime controls it; near-0 ms idle means no headroom (Q1-051).
- **Runtime Optimizer Quick Perf targets 14.2 ms, not the 13.9 ms 72 Hz budget** (Q1-C6); a 14.0 ms frame reads 'green' yet misses vsync. Details: `quest-perf:quest-profiling-toolkit`.
- **Draw-call counts as a verdict.** Meta's figures disagree (under 300 in the Runtime Optimizer vs under 100 in the agent skill; neither is a VRC, Q1-C3). Capture render-thread time first; budgets live in `quest-perf:quest-budgets-tiers`.
- **"72 FPS is the store minimum."** The GDC 2026 recap and older pages say 72; VRC.Quest.Performance.1 sets a 60 fps floor (lowered 2024-08-07); 72 fps with no stale frames is the quality target (Q1-C1, QUEST-GF1-C3). Owned by `quest-perf:quest-budgets-tiers`.
- **"MR made my shaders slower."** Passthrough is composited by a system service; its cost is the level ceiling, not App GPU time (Q4-010).
- **Render scale 0.96-1.04 does nothing in URP.** Values within +/-0.05 of 1.0 snap to 1.0 (Q2-022). The isolation test at 0.1 is unaffected, but small A/Bs are.
- **Render-scale test "changes nothing" on Unity 6.3+ with an upscaler.** In URP 17.3+ an active IUpscaler forces the XR render scale passed to `XRSystem.SetRenderScale` to 1.0 (Q3-007), so the test does nothing and a fill-bound app is misclassified as vertex/geometry-bound. Disable the upscaler and check that `SF=` moves first. `Unity ≥ 6000.3` `URP 17.3+` [verify on device]
- **`Temp=` as a thermal indicator.** Legacy from phone VR; use `PLS` / `power_level_state` (Q1-016 / Q2-061).
- **Judging from the first run.** First run compiles shaders (Q1-011).
- **Profiling with dynamic resolution on.** It changes the workload you measure (Q3-051).
- **Trusting a 65 ms+ spike value in the CSV.** `app_gpu_time_microseconds` reportedly clamps at 65,535 µs ([community], Q1-018); use Perfetto GPU tracks for catastrophic frames.
- **`CPU4` in logcat is not a level.** The digit is the measured core; the levels are after `=` (Q1-025).

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ [doc] (Q1-089, Q1-090, Q1-006, Q1-011)
- https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ [doc] (Q2-031, Q2-009, Q2-066)
- https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ [doc] (Q1-091, A3-097)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc] (Q1-028 to Q1-036, Q2-030, Q2-032)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat/ [doc] (Q1-027, Q1-035)
- https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ [doc] (Q1-024, Q1-025, Q1-016)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc] (Q1-001 to Q1-006, Q1-020, A1-085)
- https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ [doc] (Q2-072)
- https://developers.meta.com/horizon/essentials/framesync/ [doc] (Q2-071, QX-C4)
- https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ [doc] (Q2-010, QX-C5)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc] (QX-C5)
- https://developers.meta.com/horizon/documentation/unity/os-render-scale/ [doc] (Q3-011, Q3-C5)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html [doc] (Q3-010, Q3-C5)
- https://github.com/meta-quest/agentic-tools [doc] (Meta-published agent skill; Q1-050 to Q1-055)
- https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ [doc] (QUEST-GF1-003)
- https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ [doc] (QUEST-GF2-012, QUEST-GF2-013)
- https://developers.meta.com/horizon/resources/publish-performance-analytics/ [doc] (QUEST-GF2-013)
- https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ [doc] (Q2-039)
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc] (A1-036, Q4-001, Q4-003)
- https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ [doc] (Q2-038, Q2-046, Q2-047)
- https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough/ [doc] (Q4-010)
- https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ [doc] (Q1-041)
- https://developers.meta.com/horizon/documentation/unity/unity-quest-runtime-optimizer/ [doc] (Q1-092, Q1-C6)
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc] (Q3-051)
- https://developers.meta.com/horizon/documentation/unity/os-fixed-foveated-rendering/ [doc] (Q1-081)
- https://developers.meta.com/horizon/essentials/memory-ram/ [doc] (Q2-041, cited in the routing table)
- https://developers.meta.com/horizon/documentation/unity/po-memory-ram/ [doc] (Q2-042)
- https://developers.meta.com/horizon/resources/vrc-quest-performance-1/ [doc] (Q1-C1, QUEST-GF1-C3, Q1-084, QUEST-GF1-009)
- https://docs.unity3d.com/6000.6/Documentation/Manual/VRFrameTiming.html [doc] (U5-081)
- https://raw.githubusercontent.com/Unity-Technologies/Graphics/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs [doc] (Q2-022, source code)
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs [doc] (Q3-007, source code)
- https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 [community] (G1-049 to G1-053; redirect target of the issuetracker.unity3d.com URL)
- https://github.com/DemoySegment/CubemapRendering/blob/HEAD/Demo/com.DefaultCompany.lakedemo%23UnityPlayerActivity-20260102_033328.csv [measured] (Q1-014 CSV columns, Quest 3)
- https://github.com/Grizfreak/network-data [community] (Q1-018)
