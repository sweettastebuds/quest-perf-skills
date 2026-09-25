---
name: quest-frame-pacing
description: "Frame delivery on Quest 2/3/3S when average frame time already fits the budget: stale frames, repeated or dropped frames, periodic judder, bad p95/p99, FrameSync vs legacy Phase Sync, Late Latching, OpenXR Latency Optimization, choosing 72/90/120 Hz and Unity's Optimized Frame Pacing. Use when OVR Metrics shows stale frames or the image judders with no single CPU/GPU spike. Not for one-off spikes (unity-shader-hitches, unity-cpu-scripting) or drops that grow over a session (quest-levels-thermal)."
---

# Quest frame pacing

Goal: **Consistency**. The job here is to get every frame to the compositor on time: no stale runs, a tight p95/p99, and a refresh rate the content can hold. Average-FPS work belongs to other skills.

## When to use / when not

Use when:
- OVR Metrics or logcat shows `Stale` > 0, `Stale2/5/10/max` > 0 or non-zero `stale_frames_consecutive`, but average App T / CPU time is inside the budget.
- The image judders periodically with no single spike in the Unity Profiler.
- You are choosing or changing the refresh rate (72/80/90/96/100/120 Hz, Quest 3 extended rates), or handling a runtime refresh drop.
- You are deciding on FrameSync, the Phase Sync legacy setup, Late Latching, OpenXR Latency Optimization, or Unity's Optimized Frame Pacing.

When not:
- The cause is unknown. Start at `quest-perf:quest-triage`.
- Average CPU or GPU time is over budget. Route through `quest-perf:quest-triage` to the throughput skills.
- One-off spikes on first render of a material or effect: `unity-perf:unity-shader-hitches`. GC, physics or loading spikes: `unity-perf:unity-cpu-scripting`.
- Frame rate or stale count gets worse after 10 or more minutes, levels change, or clocks drop: `quest-perf:quest-levels-thermal`.
- How to run the capture tools (the OVR Metrics CSV analyzer, the ADB helper, Perfetto, RenderDoc): `quest-perf:quest-profiling-toolkit`.
- A GLES vs Vulkan decision (Late Latching is one Vulkan-only input): `gles3-perf:gles-vs-vulkan`.
- Missed-frame recovery: missed frames get rotation-only TimeWarp; Meta's recovery order is dynamic resolution, dynamic FFR, refresh throttle, then opt-in AppSW (Q2-078). Setup: `quest-perf:quest-appsw`; resolution and foveation: `quest-perf:quest-resolution-foveation`.
- Compositor layer cost (`Tear`, `TW`, `LCnt`): `quest-perf:quest-compositor-layers`.

## Diagnose first

1. **Per-second VrApi line.** `adb logcat -c; adb logcat -s VrApi,XrPerformanceManager` (Q1-027). Read these fields (Q1-028/029/030, Q2-068/069):
   - `FPS=rendered/refresh`, `Stale`, `Stale2/5/10/max` (runs of 2, 5 and 10 consecutive stale frames plus the longest run, over the past second), `Early`, `Tear`.
   - `VSnc`: should be 1. 2 means half rate. 0 means AppSW is active.
   - `Lat`: >0 extra-latency frames, 0 none, -1 Phase Sync, -2 fixed-latency Phase Sync, -3 Phase Sync tuned for AppSW. This page predates FrameSync, and what `Lat=` reports on v203+ is undocumented (QX-C9) [verify on device].
   - `Prd` (pose-to-photon prediction), `CFL=min/max`, `ICFLp95` (compositor latency).
   - `CPU4/GPU=a/b` plus clocks and `PLS`: a stale burst that lines up with a clock drop is thermal or DVFS, not pacing (Q1-035). Route it to `quest-perf:quest-levels-thermal`.
2. **Classify the staleness** (Q1-024 / Q2-066):
   - `Stale` between 0 and the refresh rate, or any non-zero `Stale5`/`Stale10`, means **judder**. That is the failure signal.
   - `Stale` equal to the refresh rate with steady FPS (for example 72/72 with 72 stale) is extra-latency mode. It is steady timing at a latency cost, not a failure.
   - `Early` close to FPS means you are in extra-latency mode or have more clock headroom than you need (Q1-026).
   - `Tear` > 0 means the compositor was too slow, usually from too many layers. That is not app pacing; see `quest-perf:quest-compositor-layers`.
3. **Session CSV.** Record an OVR Metrics CSV (Basic preset, no HUD, no casting) along a scripted route and mark segments with `AppendCsvDebugString` (Q1-094, Q1-020). Pacing columns (Q1-014): `stale_frame_count`, `stale_frames_consecutive`, `max_repeated_frames`, `skipped_frames`, `early_frame_count`, `screen_tear_count`, `phase_sync_mode`, `extra_latency_mode`, `icfl_mean/stdev_microseconds`, `slice_headroom_mean/stdev_microseconds`, `app_frame_throttle`. Meta publishes no definitions for most of these columns; treat them as relative signals. Run `ovr_metrics_csv.py` from `quest-perf:quest-profiling-toolkit` for stale frames per minute, the maximum stale frames in any 60 s window, and p50/p95/p99. Those percentiles are computed over 1 Hz rows, not per frame (Q1-010), so use Perfetto for per-frame pacing.
4. **Perfetto for per-frame shape.** Look at `PlayerLoop` duration on `UnityMain` and the `xrWaitFrame` / `PhaseSync` wait at its start. On pre-FrameSync builds, a `PhaseSync` idle of 1-4 ms is normal, and near 0 ms means the frame is one hitch away from stale (Q1-051). On v203+ that marker's meaning is unverified (QX-C4); use `slice_headroom_*` from the CSV instead. Do **not** reuse the stock hz-perfetto-debug stale SQL: it counts every `PlayerLoop` over 11.1 ms as stale, which hard-codes 90 Hz and confuses CPU frame time with compositor staleness (Q1-054, Q1-C7).
5. **Periodic vs one-off.** A spike every N frames (a timer, a streaming tick, a probe or occlusion update) belongs here; stagger it (Fix 4). A first-use spike belongs to `unity-perf:unity-shader-hitches`, and a GC or physics spike to `unity-perf:unity-cpu-scripting` (Q1-094 labelling).
6. **In-build counter (release builds).** `XRDisplaySubsystem.TryGetDroppedFrameCount` / `TryGetFramePresentCount` / `TryGetDisplayRefreshRate` per frame, logged as deltas (U5-091). Whether the Meta OpenXR provider fills every stat is [verify on device]. `unity-perf:unity-profiling-workflow` owns the in-app stats hooks.

## Key numbers

| Number | Value | Source | Applies to |
|---|---|---|---|
| Frame budget | 72 Hz 13.9 ms, 90 Hz 11.1 ms, 120 Hz 8.3 ms, 207 Hz 4.8 ms, 240 Hz 4.2 ms | Q2-009 [doc] | `Quest 2` `Quest 3/3S` (207/240 `Quest 3` only) |
| Runtime default refresh | 72 Hz unless the app requests another rate | Q2-010 [doc] | all Quest, all Unity |
| Supported rates | Quest 2: 60 (media apps only), 72, 80, 90, 96, 100, 120. Quest 3: 72, 80, 90, 96, 100, 120, plus any integer 72-207 Hz. Quest 3S: 72-120 only, including 96/100 | Q2-010, Q2-013, Q2-089 [doc] | HorizonOS v2.7+ for the Quest 3 extended rates |
| 240 Hz | developer mode plus `debug.oculus.forceDisplayScaling 1` and `debug.oculus.refreshRate 240`; the panel upscales above 207 Hz | Q2-013 [doc] | `Quest 3`, dev only, never ship |
| Thermal refresh drop | step 1: an app above 72 Hz drops to 72 Hz; step 2: refresh unchanged, app frame rate halved (like minVsyncs=2) | Q2-014 [doc] | all Quest |
| Stale-frame rate heuristic | good < 5%, warning > 10%, critical > 25% | Q1-053 [doc] (Meta agent skill, not a VRC) | `Quest 2` `Quest 3/3S` |
| Frame-time std dev heuristic | good < 1 ms, warning > 2 ms, critical > 4 ms | Q1-053 [doc] (Meta agent skill) | `Quest 2` `Quest 3/3S` |
| Late Latching latency saving | up to one frame of pose latency; overhead "negligible" (no number published) | Q2-075 [doc] | `Vulkan` + Multiview |
| Simulation vs render pose mismatch with Late Latching | about 10 ms (OVRManager "Late Controller Update" docs) | Q4-063 [doc] | Meta XR Core SDK |
| FrameSync cost | "slightly" higher CPU/GPU use, battery and heat; no number published | Q2-072, A1-039 [doc] | HzOS v201/v203+ |
| FrameSync stale-frame benefit | Meta claims fewer stale frames and fewer long runs; no number published | Q2-071 [doc] | HzOS v203+ |
| Store field telemetry | Max Stale Frames per ~60 s window | QUEST-GF2-013 [doc] | Store apps |

The CPU/GPU headroom rule (70% / 80% / hitches under 3%) belongs to `quest-perf:quest-triage`, and the VRC frame-rate floor to `quest-perf:quest-budgets-tiers`. Neither is repeated here.

## Fixes, ranked by payoff ÷ effort

### 1. Set the refresh rate explicitly, from the runtime's list, and survive a runtime drop
**Goal:** Consistency (and Throughput when you drop a rate the content cannot hold). `Quest 2` `Quest 3/3S` `Unity 2021.3+` (Meta XR Core SDK) / `Unity 2022.3+` (OpenXR: Meta)

- The runtime runs at 72 Hz unless you ask for more (Q2-010). Unity's e-book says "most XR devices enforce Vsync at 90 Hz or higher", which is wrong for Quest; the Vsync-is-runtime-enforced part is right (UNITY-GF1-009, UNITY-GF1-C2). `QualitySettings.vSyncCount` and `Application.targetFrameRate` are ignored in VR (U5-008).
- Choose the highest rate whose budget (Key numbers) the content holds with stale near 0 at the level you design to. Moving from 72 to 90 Hz takes 2.8 ms of budget away, so p99 has to fit 11.1 ms.
- Gate on the runtime-reported list, not on the device family. A rate is available only if the manifest's `com.oculus.supportedDevices` lists a device that supports it; compatibility mode limits it further (Q2-015). Check the merged AndroidManifest in every build: the refresh-rate page's "Unity auto-adds `quest|quest2`" is stale, and the canonical value is `quest2|questpro|quest3|quest3s` (Q2-C12).
- Effect: a correct rate removes the systematic judder you get from running content above what it holds. A higher rate lowers `Prd` (Q2-069). Cost: less budget per frame, more heat.

Meta XR Core SDK path (`Unity 2021.3+`) (Q2-011):
```csharp
using System;
using UnityEngine;

public sealed class QuestRefreshRate : MonoBehaviour
{
    [SerializeField] float[] preferredRates = { 90f, 72f }; // highest first

    void Start()
    {
        float[] available = OVRPlugin.systemDisplayFrequenciesAvailable;
        foreach (float rate in preferredRates)
        {
            if (available != null && Array.Exists(available, a => Mathf.Approximately(a, rate)))
            {
                OVRPlugin.systemDisplayFrequency = rate;
                break;
            }
        }
        OVRManager.DisplayRefreshRateChanged += OnRefreshRateChanged;
    }

    void OnDestroy() => OVRManager.DisplayRefreshRateChanged -= OnRefreshRateChanged;

    void OnRefreshRateChanged(float from, float to)
    {
        // A thermal event or Battery Saver can force 72 Hz (Q2-014, Q2-062).
        // Re-derive anything tied to the refresh rate here (animation steps, budgets, quality tier).
        Debug.Log($"[pacing] refresh {from} -> {to} Hz");
    }
}
```
Meta marks the list API deprecated but still documents it (Q2-011). Meta also accepts rates the list does not return (76 Hz works on Quest 2/Pro/3/3S) but recommends the charted rates (Q2-011).

Unity OpenXR: Meta path (`com.unity.xr.meta-openxr` 2.x, `Unity 2022.3+`; enable the "Meta Quest Display Utilities" feature) (Q2-012):
```csharp
using Unity.Collections;
using UnityEngine;
using UnityEngine.XR;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR.Features.Meta;

public static class QuestRefreshRateOpenXR
{
    // Returns the granted rate, or 0 if the request failed.
    public static float Request(params float[] preferredHighestFirst)
    {
        var general = XRGeneralSettings.Instance;
        var manager = general != null ? general.Manager : null;
        var loader = manager != null ? manager.activeLoader : null;
        var display = loader != null ? loader.GetLoadedSubsystem<XRDisplaySubsystem>() : null;
        if (display == null || !display.TryGetSupportedDisplayRefreshRates(Allocator.Temp, out NativeArray<float> rates))
            return 0f;
        try
        {
            foreach (float want in preferredHighestFirst)
                foreach (float have in rates)
                    if (Mathf.Approximately(want, have) && display.TryRequestDisplayRefreshRate(have))
                        return have;
            return 0f;
        }
        finally { rates.Dispose(); }
    }
}
```
Both calls return false when the feature is off or the rate is not in the supported list. That conflicts with Meta allowing unlisted rates (Q2-C10), and the Quest 3 extended rates may be rejected on this path [verify on device]. On this path, detect runtime drops by polling `XRDisplaySubsystem.TryGetDisplayRefreshRate` about once per second (U5-091).

Rehearse the thermal drop on every quality tier:
`adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SIMULATE_THERMAL --es subsystem refresh --ei seconds_throttled 10` (Q2-014). Anything that assumes a fixed `Time.deltaTime`, fixed-timestep physics or refresh-locked animation must survive a 90/120 to 72 Hz change. The right `fixedDeltaTime` on Quest is an open conflict (U5-C4, UNITY-GF1-C3): measure physics steps per frame and judder at each rate [verify on device]; `unity-perf:unity-cpu-scripting` owns physics.

### 2. Confirm FrameSync is active and remove Phase Sync assumptions
**Goal:** Consistency. `Quest 2` `Quest 3/3S` `HzOS v203+` all Unity versions, `GLES` `Vulkan`

- FrameSync is the default frame-timing algorithm for every app on every supported device from v203. It needs no integration, and Phase Sync API calls are no-ops (Q2-071, QUEST-GF1-007). It can be tested from v201 with `<meta-data android:name="com.oculus.enable_frame_sync" android:value="true"/>` (Q2-072, A1-039).
- It is a frame-start scheduler: it trades latency against GPU time so the frame finishes just before display. It works together with AppSW, which is not deprecated (QUEST-GF2-003).
- Action: nothing to enable on v203+. Remove Phase Sync setup at your convenience. Re-baseline CPU frame timings across v203, because frame start moved relative to vsync (A1-039).
- Cost: slightly higher CPU/GPU use, battery and heat (Q2-072); no number published. Measure with a same-route CSV before and after the OS update.
- **Opt-out: do not build a fix around it.** The blog promised an opt-out, but the essentials page documents none. `com.oculus.enable_frame_sync=false` comes only from UploadVR and a forum post that never reported it working (QUEST-GF1-007, QUEST-GF2-001, QUEST-GF1-C1) [verify on device]. If a title regresses under FrameSync, A/B with `false` and confirm the mode actually changed via CSV `phase_sync_mode` before trusting the result. `phase_sync_mode=4` in Aug 2026 Quest 3 captures probably marks FrameSync, but no Meta page defines the values (QUEST-GF2-002) [verify on device].

Read [references/framesync.md](references/framesync.md) when you need the OS-version timeline, the manifest keys, the legacy Phase Sync setup for pre-v203 OS builds, the `Lat=` and `phase_sync_mode` verification steps, or the OXPB-115 checkbox bug on older Oculus XR versions.

### 3. OpenXR Latency Optimization: Prioritize Input Polling
**Goal:** Consistency (pose freshness; fewer one-frame-stale poses). `Quest 2` `Quest 3/3S` `Unity 6.x` `OpenXR plugin 1.x` (Meta Quest validation rule from 1.15.0-pre.1)

- **Conflict (U5-C2):** Unity's OpenXR 1.18 manual defaults to **Prioritize Rendering**, which minimises simulate-to-submit time (U5-092). Meta recommends **Prioritize Input Polling** for Quest: `xrWaitFrame` runs on the main thread before simulation, so poses use the latest predicted display time. Prioritize Rendering moves the wait to the render thread and can give poses one frame stale (Q2-076, Q4-061, U1-092). OpenXR 1.15.0-pre.1 added a Meta Quest validation rule steering to Input Polling (U5-093). The dossier resolves this for Quest in Meta's favour. Keep Meta's setting unless a same-route A/B of stale frames per minute and `Prd` says otherwise.
- Path: Project Settings > XR Plug-in Management > OpenXR (Android tab) > Latency Optimization (Q4-055). It is build-time only; runtime changes are ignored (U5-092).
- Effect: no published change to average frame time; the benefit is pose freshness and fewer one-frame-stale poses (lower `Prd`, Q2-076). Measure stale frames per minute and `Prd` on the same route. Quality cost: none documented; the wait moves from the render thread to the main thread, so main-thread timings shift.
- Side effect: the frame wait moves between threads, so Perfetto and Profiler markers shift. Re-read wait placement in captures after changing it.
- Migrating from Oculus XR (deprecated from Unity 6.5) to OpenXR: check this setting, because Input Polling matches the Oculus XR default (Q2-076).

Build guard (Editor folder; `OpenXRSettings.latencyOptimization` is confirmed in the OpenXR 1.18 manual (U5-092); whether older 1.x versions have the property is unverified, so confirm it compiles on your plugin version):
```csharp
#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.XR.OpenXR;

sealed class QuestLatencyOptimizationGuard : IPreprocessBuildWithReport
{
    public int callbackOrder => 0;

    public void OnPreprocessBuild(BuildReport report)
    {
        if (report.summary.platform != BuildTarget.Android) return;
        var settings = OpenXRSettings.GetSettingsForBuildTargetGroup(BuildTargetGroup.Android);
        if (settings == null) return;
        if (settings.latencyOptimization != OpenXRSettings.LatencyOptimization.PrioritizeInputPolling)
        {
            // For an A/B build, comment this out instead of changing the default.
            settings.latencyOptimization = OpenXRSettings.LatencyOptimization.PrioritizeInputPolling;
            EditorUtility.SetDirty(settings);
            Debug.LogWarning("[pacing] OpenXR Latency Optimization set to Prioritize Input Polling (Meta Quest guidance).");
        }
    }
}
#endif
```
Untested here: Unity cannot run in this repo.

### 4. Stagger periodic work across frames
**Goal:** Consistency (p99, `Stale2/5`). `Quest 2` `Quest 3/3S` all Unity versions and APIs

- Meta: FrameSync absorbs variable frame cost, but still advises spreading expensive work across frames and keeping per-frame patterns predictable, for smoother output and lower sustained heat (Q2-063). Time-slice LOD streaming, GI probe updates and occlusion rebuilds instead of running each in a one-frame burst.
- Effect: average frame time is unchanged or slightly higher; the periodic spike goes away. No published number; measure p99 and `Stale2/5/10/max` per segment.
```csharp
using System;
using System.Collections.Generic;
using System.Diagnostics;
using UnityEngine;

// Runs queued work items within a per-frame time slice. Tune sliceMs from a capture, not a guess.
public sealed class FrameSlicer : MonoBehaviour
{
    [SerializeField] float sliceMs = 1.0f;
    readonly Queue<Action> _work = new Queue<Action>(256);
    readonly Stopwatch _sw = new Stopwatch();

    public void Enqueue(Action item) => _work.Enqueue(item);

    void Update()
    {
        _sw.Restart();
        while (_work.Count > 0 && _sw.Elapsed.TotalMilliseconds < sliceMs)
            _work.Dequeue().Invoke();
    }
}
```
Keep the enqueued delegates cached (no per-frame lambdas), or the slicer creates the GC spikes it is meant to remove. The `sliceMs` value is a placeholder: no source gives a figure. Set it from the measured headroom (`slice_headroom_mean_microseconds`, or `PhaseSync` idle on pre-v203 builds).

### 5. Late Latching (controllers and head) on Vulkan
**Goal:** Consistency (latency, not frame rate). `Vulkan` + Multiview only; `Quest 2` `Quest 3/3S`

- Updates poses just before GPU submit and removes up to one frame of pose latency. Meta calls the overhead negligible and recommends it for most apps (Q2-075, G1-036).
- Path: OpenXR > Meta Quest Support (cog) > Late Latching (Vulkan) (Q4-055). Oculus XR / Meta XR Core SDK: `OVRManager` Late Latching, which defaults to false (Q2-075). On the Unity OpenXR side, controller late latching is `TrySetControllerLateLatchAction` (OpenXR 1.9.1+). Unity's OpenXR 1.18 Meta Quest page does not list the setting that Meta documents (Q4-C8) [verify on device].
- Side effects: only children of tracked anchors and the view-projection matrix are patched. Scripts, simulation and physics still see the simulation-time pose, about 10 ms apart (Q4-063). Raycasts and hand-attached colliders can visibly disagree with rendered controllers, and local vs networked poses can drift slightly.
- **Never ship Late Latching Debug Mode** (Q2-075 / Q4-063).
- Verify by comparing `Prd` before and after (Q2-069). GLES projects cannot use it; if it matters, that becomes an input to `gles3-perf:gles-vs-vulkan`.

### 6. Unity Optimized Frame Pacing: off for XR until an A/B says otherwise
**Goal:** Consistency. `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` Android Player settings

- Path: Project Settings > Player > Android > Resolution and Presentation > Optimized Frame Pacing, or `PlayerSettings.Android.optimizedFramePacing = false;` in an editor script.
- **Conflict (U5-C5):** Unity describes it generically (Android Swappy spreads frames more evenly) and documents nothing about behaviour under the XR compositor, which already paces frames (U5-023). Community reports are mixed and old: some report no issues; one reports intermittent hitches on 2021.3.10f1 and that it ignores runtime refresh changes; a Cardboard SDK issue reports Swappy blocking the render thread and causing pose jumps (U5-024 [community]).
- Effect: Unity claims lower frame-time variance (U5-023), but nothing is published for XR; community reports include intermittent hitches (U5-024). Leaving it off costs no image quality. Turning it on risks render-thread blocking and pose jumps (the Cardboard Swappy report, U5-024).
- Default: off, then A/B stale frames per minute and `TryGetDroppedFrameCount` deltas with it on and off on the same route (U5-023) [verify on device].

## Verify

- **Stale frames:** on a fixed, scripted route, `Stale5`/`Stale10` should be 0 in every logcat line, and the CSV maximum stale count per 60 s window should fall toward 0. That window matches Store Performance Analytics (QUEST-GF2-013). Stale-frame rate should reach the "good" band (< 5%, Q1-053), aiming for 0 in steady play.
- **Frame-time spread:** frame-time std dev under 1 ms (Q1-053 heuristic), and p95/p99 of `PlayerLoop` `dur` from Perfetto under the budget, over at least 20 s of steady play (Q1-055).
- **Latency fixes (3, 5):** `Prd` falls. No published size; record before and after on the same OS build.
- **Mode:** record `Lat=`, `phase_sync_mode` and `extra_latency_mode` with every capture. Results are only comparable within one OS build (QX-C9).
- **Refresh:** after the thermal broadcast, the app keeps running correctly at 72 Hz and `OVRManager.DisplayRefreshRateChanged` fires (or `TryGetDisplayRefreshRate` changes). Read the granted rate from `FPS=x/refresh` in logcat.
- **Session length:** Prove a pacing fix on a scripted route of at least 20 s of steady play (Q1-055); no published minimum session length exists for pacing A/Bs, so repeat each route at least 3 times per build and compare stale frames per minute. [verify on device] Then run a 20-30 minute soak at the shipping rate, unplugged, battery above 50%, fixed ambient (Q2-060), to show that stale frames do not return late. If they do, and clocks or `PLS` moved, hand off to `quest-perf:quest-levels-thermal`.
- Record CPU/GPU level with every capture; casting or recording overrides levels, and those captures are not comparable (see `quest-perf:quest-triage`).

## Pitfalls and myths

- **"Good average FPS means smooth."** False. 72 FPS can coexist with irregular staleness. Track stale frames per minute and consecutive runs (Q1-024).
- **"72 stale per second at 72 FPS is a disaster."** Not necessarily: that pattern is extra-latency mode (Q1-024). Check `Lat=` / `extra_latency_mode` first. Meta pages disagree on whether extra-latency mode is Unity's default, and OpenXR Unity apps report `Lat=-1` (Q1-C5, Q2-C11). On Oculus XR 4.2.0+, Phase Sync is always on (Q4-057).
- **"XR devices run at 90 Hz or higher."** Wrong for Quest, where the default is 72 Hz (UNITY-GF1-C2).
- **`targetFrameRate` / `vSyncCount` control VR frame rate.** Ignored in VR (U5-008, UNITY-GF1-009). Use the refresh-rate APIs above.
- **The hz-perfetto-debug stale SQL.** It hard-codes 11.1 ms and counts CPU frame time as staleness (Q1-054). Use the runtime counters.
- **PhaseSync idle as a headroom gauge on v203+.** It is unverified under FrameSync (QX-C4). Use `slice_headroom_*`.
- **Toggling FrameSync off via `com.oculus.enable_frame_sync=false`.** Undocumented, community-only, and unconfirmed (QUEST-GF1-C1).
- **Phase Sync setprops.** `debug.Meta.phaseSync` (Unity page) vs `debug.oculus.phaseSync` (native page) (Q2-C1). Both are moot on FrameSync builds.
- **Oculus XR 3.3.0-4.0.0 Phase Sync checkbox.** Ignored; Phase Sync was always on (OXPB-115, Q2-074). Check `Lat=` instead of the checkbox.
- **Refresh lists.** The system-properties page's rate list is stale; trust the refresh-rate page and the runtime list (QX-C5). The VRC revision note saying 96/100 Hz are unavailable is superseded: they are "not available on all devices" (Q2-C4, QUEST-GF1-009). Quest 3S does not get the extended rates (Q2-089).
- **Extended rates above 207 Hz.** The display upscales and softens text and thin geometry; do not require extended rates (Q2-013).
- **60 Hz in a non-media app** fails store review (Q2-010).
- **Low Overhead Mode** is a GLES driver-validation switch, not a pacing lever, and does nothing on Vulkan. `gles3-perf:gles-driver-overhead` owns it (Q2-077).
- **Stale frames that appear only late in a session.** FrameSync adaptation is stage 3 of Meta's thermal model (Q2-058, A3-078); fix the thermal cause, not pacing (`quest-perf:quest-levels-thermal`).
- **Profiling while charging.** Can overstate sustained clocks. Meta states this for Meta VR Glasses; Quest behaviour is unverified (Q2-064) [verify on device].

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc] (Q1-028 to 033, Q2-065, Q2-068, Q2-069)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat/ [doc] (Q1-027, Q1-035)
- https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ [doc] (Q1-024, Q1-026, Q1-C5)
- https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ [doc] (Q2-066, Q2-078)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc] (Q1-094)
- https://developers.meta.com/horizon/essentials/framesync/ [doc] (Q2-071, QUEST-GF1-007)
- https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ [doc] (Q2-072, A1-039, QUEST-GF2-001)
- https://www.uploadvr.com/meta-horizon-os-framesync-smoother-vr-quest/ [community] (QUEST-GF1-007)
- https://web.archive.org/web/20260417023528/https://communityforums.atmeta.com/discussions/Questions_Discussions/app-frame-rate-drop/1368725 [community] (QUEST-GF2-001)
- https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_144005.csv [measured] (QUEST-GF2-002)
- https://github.com/DemoySegment/CubemapRendering/blob/HEAD/Demo/com.DefaultCompany.lakedemo%23UnityPlayerActivity-20260102_033328.csv [measured] (QUEST-GF2-002, Q1-014)
- https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ [doc] (QUEST-GF2-003, QUEST-GF2-013)
- https://developers.meta.com/horizon/documentation/unity/enable-phase-sync/ [doc] (Q2-073)
- https://developers.meta.com/horizon/documentation/native/android/mobile-phase-sync/ [doc] (Q2-C1)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html [doc] (Q4-057)
- https://issuetracker.unity.com/issues/11487/oculusxr-phasesync-toggle-is-not-respected-and-its-always-enabled [doc] (Q2-074)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc] (Q2-075, Q4-055, G1-036)
- https://developers.meta.com/horizon/documentation/unity/enable-late-latching/ [doc] (Q2-075)
- https://developers.meta.com/horizon/documentation/unity/unity-ovrcamerarig/ [doc] (Q4-063)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc] (Q2-076, Q4-061, U1-092, U5-093)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/project-configuration.html [doc] (U5-092)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc] (U5-093)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html [doc] (Q2-077)
- https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ [doc] (Q2-009 to 014, Q2-089)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.5/manual/features/display-utilities.html [doc] (Q2-012)
- https://developers.meta.com/horizon/documentation/unity/os-compatibility-mode/ [doc] (Q2-015)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc] (QX-C5)
- https://developers.meta.com/horizon/resources/vrc-quest-performance-1/ [doc] (QUEST-GF1-009)
- https://developers.meta.com/horizon/resources/publish-performance-analytics/ [doc] (QUEST-GF2-013)
- https://developers.meta.com/horizon/essentials/thermal/ [doc] (Q2-058, Q2-060, Q2-063, A3-078)
- https://developers.meta.com/horizon/essentials/battery-saver-mode/ [doc] (Q2-062)
- https://developers.meta.com/horizon/documentation/unity/optimize-performance/ [doc] (Q2-064)
- https://github.com/meta-quest/agentic-tools [doc] (Meta agent skill: Q1-051, Q1-053, Q1-054, Q1-055)
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html [doc] (U5-023)
- https://discussions.unity.com/t/optimized-frame-pacing-for-oculus-quest-2-and-other-android-headsets/860072 [community] (U5-024)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem.html [doc] (U5-091)
- https://docs.unity3d.com/6000.6/Documentation/Manual/performance-incremental-garbage-collection.html [doc] (U5-008)
- https://cdn.bfldr.com/S5BC9Y64/at/3mp8w3wk36k2k6mmj5pbbr/Optimize_your_game_performance_for_mobile__XR__and_the_web_in_Unity_Unity_6_edition_e-book.pdf p. 43 [doc] (UNITY-GF1-009)
- https://communityforums.atmeta.com/discussions/dev-unity/time---fixed-timestep--hz-values-for-oculus-devices-in-unity/751740 [community] (U5-C4)
