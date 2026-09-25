# Profiler markers, counters and stats names on Quest

Marker -> meaning -> owning skill. Read when a marker in a Unity Profiler or
Perfetto capture from Quest 2/3/3S is not covered in SKILL.md, or when writing
Perfetto SQL against Unity names. Exact names differ between Unity and URP
versions; check them against your own capture before hard-coding (Q1-050).
Sources accessed 2026-09-24; IDs refer to `research/unity.md`,
`research/quest.md`, `research/gles3.md`, `research/arm-mobile-hw.md`.

## Unity Profiler: frame-level waits

| Marker (thread) | Meaning | Next skill | Source |
|---|---|---|---|
| `XR.WaitForGPU` (main) longer than one frame budget | GPU-bound. Wait, not CPU cost | `quest-perf:quest-triage` (GPU branch) | U5-081 [doc] |
| `XR.WaitForGPU` short, frame over budget | CPU-bound; find the long thread | this skill, then CPU owners below | U5-081 [doc] |
| `Gfx.WaitForPresentOnGfxThread` (render thread) inside `Gfx.PresentFrame` | GPU-bound | `quest-perf:quest-triage` | U5-082 [doc] |
| `Gfx.WaitForPresentOnGfxThread` inside `Camera.Render` | CPU / render-thread-bound | `unity-perf:unity-draw-calls-batching` | U5-082 [doc] |
| `Gfx.WaitForRenderThread` / `GfxDevice.WaitForRenderThread` (main) | Main thread blocked by the render thread | `unity-perf:unity-draw-calls-batching`, `unity-perf:unity-cpu-scripting` (Graphics Jobs, MT rendering) | U5-082, U5-090 [doc] |
| `Gfx.WaitForCommands` (render) | Render thread idle, waiting for the main thread | `unity-perf:unity-cpu-scripting` | U5-082 [doc] |
| `WaitForTargetFPS` | Frame-rate cap wait; part of `cpuMainThreadPresentWaitTime` | none (not work) | U5-082, U5-090 [doc] |
| `<GfxDevice>.WaitForLastPresent` | Waiting on previous present | `quest-perf:quest-frame-pacing` if periodic | U5-082 [doc] |
| `Semaphore.WaitForSignal`, `WaitForJobGroupID` (main) | Main thread waiting on jobs: completed too early or pool saturated | `unity-perf:unity-cpu-scripting`, `arm-mobile-hw-perf:xr2-cpu-threads-neon` | U5-082 [doc] |
| `PhaseSync` (start of `PlayerLoop`) | Runtime-controlled idle; 1-4 ms is normal, near 0 ms means no headroom. Not waste | `quest-perf:quest-frame-pacing` | Q1-051 [doc]; FrameSync (v203+) meaning unverified, QX-C4 |
| `xrWaitFrame` / `xrBeginFrame` / `xrEndFrame` | OpenXR frame calls. With Prioritize Input Polling the wait is at frame start, before simulation | `quest-perf:quest-frame-pacing` | Q1-050, U5-093 [doc] |
| `vrapi_WaitFrame` / `vrapi_BeginFrame` / `vrapi_SubmitFrame` | Legacy VrApi equivalents | `quest-perf:quest-sdk-choices` | Q1-050 [doc] |

## Unity Profiler: known-hitch markers (search these first for p99 spikes)

| Marker | Meaning | Owning skill | Source |
|---|---|---|---|
| `GC.Alloc` / `GC.Collect` | Managed allocation / collection; use CPU module Call Stacks | `unity-perf:unity-cpu-scripting` | U5-012 [doc] |
| `AssetBundle.asset`, `AssetBundle.allAssets` | Synchronous load stall | `unity-perf:unity-memory-assets` | U5-101 [doc] |
| `AsyncUploadManager.AsyncBufferResized` | Async upload ring buffer grew (too small) | `unity-perf:unity-memory-assets` | U5-101 [doc] |
| `Resources.UnloadUnusedAssets` | Hierarchy walk; implicit in Single-mode `LoadSceneAsync` | `unity-perf:unity-memory-assets` | U4-086, U4-087 [doc] |
| `Rigidbody.SetKinematic` | On a non-convex MeshCollider | `unity-perf:unity-cpu-scripting` | U5-101 [doc] |
| `Animation.AddClip` and related | Legacy animation setup hitch | `unity-perf:unity-cpu-scripting` | U5-101 [doc] |
| `Shader.ParseThreaded`, `Shader.ParseMainThread` | Deserialise/decompress variants | `unity-perf:unity-shader-hitches` | G3-002 [doc] |
| `Shader.CreateGPUProgram` | Driver compile/link on first use (the GLES hitch) | `unity-perf:unity-shader-hitches`, `gles3-perf:gles-shader-binaries` | G3-001, G3-002 [doc] |
| `CreateGraphicsGraphicsPipelineImpl` | PSO creation (Vulkan); whether it fires on GLES is undocumented | `unity-perf:unity-shader-hitches` | G3-002 [doc] [verify on device] |
| `Shader.MainThreadCleanup` | Variant unload | `unity-perf:unity-shader-hitches` | G3-002 [doc] |

## Perfetto (Unity on Quest)

Unity emits ATrace only: put the package in MQDH's ATrace Apps or the trace
has no Unity slices (Q1-044). `ProfilerMarker` scopes appear only from
Development builds (Q1-045).

| Name | Kind | Meaning | Source |
|---|---|---|---|
| `UnityMain` | thread | Main thread | Q1-050, A1-052 |
| `UnityGfxDeviceW` (Q1-050 lists `UnityGfx`) | thread | Unity render thread. Android `RenderThread` is HWUI, not Unity | A1-052 [community], Q1-050 [doc] |
| `UnityChoreWorker`, `Job.Worker` | thread | Unity workers; check core placement here | Q1-050, U5-097 |
| `GPU completion` | thread | Waiting there = GPU-bound | Q1-050, Q1-052 [doc] |
| `OVRPollEvent` | thread | Meta SDK event polling | Q1-050 |
| `PlayerLoop`, `PostLateUpdate.FinishRendering`, `RenderPipelineManager.DoRenderLoop`, `BatchRenderer.Flush`, `Gfx.WaitForPresent` | slices | Frame structure; `BatchRenderer.Flush` is submission | Q1-050 [doc] |
| `FenceChecker::Wait` | slice | CPU waiting on the GPU = GPU-bound | Q1-052 [doc] |
| `surface#N` on `GPU*` tracks | slice | GPU work per surface; reading rule owned by `quest-perf:quest-profiling-toolkit` | Q1-052 [doc] |

Stale-frame SQL must use the budget of the refresh rate in use (13.9, 11.1 or
8.3 ms), not a hard-coded 11.1 ms, and `PlayerLoop` duration is not
compositor staleness (Q1-054).

## FrameTimingManager formulas (U5-090)

- `cpuMainThreadFrameTime` = PlayerLoop - GfxDevice.WaitForRenderThread - Gfx.WaitForPresentOnGfxThread - WaitForTargetFPS
- `cpuMainThreadPresentWaitTime` = Gfx.WaitForPresentOnGfxThread + WaitForTargetFPS
- `cpuRenderThreadFrameTime` = RenderLoop - Gfx.PresentFrame (not measured on XR, Q1-106)
- `gpuFrameTime`: 0 on XR before 6.6 (Unity's example treats 0 as "Indeterminate"); 6000.6.0b1 adds OpenXR GPU times, unverified on Quest (X-C3).
- Non-development builds need Player > Other Settings > Rendering > Frame Timing Stats (U5-027). May lower GPU performance on GLES (U5-090).

## ProfilerRecorder counters usable in Release players (U5-080)

| Category | Name | Unit |
|---|---|---|
| `ProfilerCategory.Internal` | `Main Thread` | ns (Unity's sample multiplies by 1e-6 for ms) |
| `ProfilerCategory.Memory` | `GC Reserved Memory` | bytes |
| `ProfilerCategory.Memory` | `System Used Memory` | bytes |

List all with `ProfilerRecorderHandle.GetAvailable`. Dispose recorders.

## In-app XR stats APIs

| API | Provider / version | Status on Quest | Source |
|---|---|---|---|
| `XRDisplaySubsystem.TryGetAppGPUTimeLastFrame`, `TryGetCompositorGPUTimeLastFrame`, `TryGetDroppedFrameCount`, `TryGetFramePresentCount`, `TryGetMotionToPhoton`, `TryGetDisplayRefreshRate` | Unity XRModule, 2021.3-6.x | Returns what the plug-in fills; no published fill list [verify on device]. Seconds; OpenXR < 1.18.0-pre.2 wrote app/compositor GPU time in ms | Q1-097, U5-091, Q3-060 [doc] |
| `XRStats.TryGetGPUTimeLastFrame`, `TryGetDroppedFrameCount`, `TryGetFramePresentCount` | VRModule | Not obsolete 2021.3-6.2; deprecated from 6000.3 | Q1-098 [doc] |
| `Unity.XR.Oculus.Stats.PerfMetrics` (after `EnablePerfMetrics(true)`) | Oculus XR 4.5.x | All 0 under OpenXR | Q1-099 [doc] |
| `Unity.XR.Oculus.Stats.AdaptivePerformance` | Oculus XR 4.5.x | Undocumented under OpenXR; assume not working. CPU/GPU level range 0-3 is a legacy mapping | Q1-100 [doc] |
| `OVRPlugin.GetPerfMetricsFloat/Int`, `IsPerfMetricsSupported` | Meta XR Core SDK, OVRPlugin 1.30+ | Works under OpenXR via `XR_META_performance_metrics` | Q1-101, Q1-102 |
| `OVRPlugin.GetAppPerfStats`, `ResetAppPerfStats` | Meta XR Core SDK v85 | Unsupported on OpenXR; logs once, returns empty | Q1-104 [doc] |
| `xrQueryPerformanceMetricsCounterMETA` | `XR_META_performance_metrics` | Runtime picks the interval; must not drive app behaviour | Q1-103 [doc] |
| `XrPerformanceSettings` `OnXrPerformanceChangeNotification` | OpenXR plugin 1.11+ | Log next to frame times; Horizon OS support undocumented (owned by `quest-perf:quest-levels-thermal`) | U5-094 [doc] |

### `OVRPlugin.PerfMetrics` enum (SDK v85 source, Q1-101)

| Value | Name | Note |
|---|---|---|
| 0 | `App_CpuTime_Float` | not listed by a 2023 runtime (Q1-102 [community]) |
| 1 | `App_GpuTime_Float` | |
| 3 | `Compositor_CpuTime_Float` | |
| 4 | `Compositor_GpuTime_Float` | |
| 5 | `Compositor_DroppedFrameCount_Int` | |
| 7 | `System_GpuUtilPercentage_Float` | |
| 8 | `System_CpuUtilAveragePercentage_Float` | |
| 9 | `System_CpuUtilWorstPercentage_Float` | |
| 10-13 | `Device_CpuClockFrequencyInMHz_Float`, `Device_GpuClockFrequencyInMHz_Float`, `Device_CpuClockLevel_Int`, `Device_GpuClockLevel_Int` | added 1.32.0, "Deprecated 1.68.0"; use OVR Metrics or logcat for levels |
| 14 | `Compositor_SpaceWarp_Mode_Int` | |
| 32-39 | `Device_CpuCore0UtilPercentage_Float` to `Device_CpuCore7UtilPercentage_Float` | |

`XR_META_performance_metrics` counter paths under `/perfmetrics_meta`
(Q1-103): `app/cpu_frametime`, `app/gpu_frametime`,
`app/motion_to_photon_latency`, `compositor/cpu_frametime`,
`compositor/gpu_frametime`, `compositor/dropped_frame_count`,
`compositor/spacewarp_mode`, `device/cpu_utilization_average`,
`device/cpu_utilization_worst`, `device/gpu_utilization`,
`device/cpu0_utilization` onward. Get the live list with
`adb logcat -s OVRPlugin | grep "Supported Performance Metrics"` (Q1-102).

## Sources

All accessed 2026-09-24.

- https://docs.unity3d.com/6000.6/Documentation/Manual/VRFrameTiming.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/performance-track-garbage-collection.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Resources.UnloadUnusedAssets.html [doc]
- https://docs.unity3d.com/Packages/com.unity.addressables@1.21/manual/MemoryManagement.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/frame-timing-manager.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Profiling.ProfilerRecorder.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/ScriptReference/XR.XRStats.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/api/Unity.XR.Oculus.Stats.PerfMetrics.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/api/Unity.XR.Oculus.Stats.AdaptivePerformance.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ [doc]
- https://github.com/meta-quest/agentic-tools [doc]
- https://discussions.unity.com/t/android-thread-configuration-render/1731103 [community]
- https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/OVRPlugin.cs [doc] (SDK source mirror)
- https://github.com/Fb-dtalker/UnityMetaMRC/blob/HEAD/OVRMrclibUnloadLog.log [community]
- https://github.com/KhronosGroup/OpenXR-Docs/blob/main/specification/sources/chapters/extensions/meta/meta_performance_metrics.adoc [doc]
