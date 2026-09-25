---
name: unity-cpu-scripting
description: "CPU-side Unity scripting cost on Quest 2/3/3S: GC allocations and GC spikes, incremental GC, IL2CPP settings, moving work into jobs and Burst, multithreaded rendering and Graphics Jobs, physics timestep and spikes, UI canvas rebuilds, animation and skinning, and Update-loop overhead. Use when the main thread is bound by scripts, GC, physics, animation or UI, for GC hitches, or when choosing Player scripting settings. Core counts, affinity and NEON: xr2-cpu-threads-neon."
---

# Unity CPU and scripting cost on Quest

Goal: **Throughput** (main-thread and render-thread ms) and **Consistency** (GC, physics catch-up
and UI-rebuild spikes; lower CPU level means less thermal decay). Scope: Unity 2021.3 to 6.6, URP 12
to 17.x, Quest 2 (XR2 Gen 1) and Quest 3/3S (XR2 Gen 2), OpenXR or Oculus XR plugin, Vulkan and GLES
unless tagged.

Runtime baseline for every claim here: on Quest, every Unity version 2021.3-6.6 runs C# through
**IL2CPP with the Boehm GC** (non-generational, non-compacting). CoreCLR is not a Quest option:
6.7's CoreCLR player is experimental and desktop-only, and no Android timeline exists (U5-001 /
U1-071, U5-002).

## When to use / when not

Use when:
- A capture shows the frame is CPU-bound on the **main thread**: long
  `PlayerLoop`/`Update.ScriptRunBehaviourUpdate`, `FixedUpdate.PhysicsFixedUpdate`,
  `DirectorUpdateAnimation*`, `Canvas.*` samples, or `GC.Collect` spikes.
- p99 frame time has one-off spikes that line up with `GC.Collect`, `Physics.Simulate` running 2+
  times, or UI rebuilds.
- You are choosing Player scripting settings: IL2CPP compiler configuration, code generation,
  incremental GC, stack traces, Managed Code Variant (6.6), Graphics Jobs mode, Multithreaded
  Rendering, GPU skinning.
- You are moving main-thread work into jobs/Burst, or setting `fixedDeltaTime`.

Do not use; go to the sibling instead:
- Not yet known whether CPU- or GPU-bound: `quest-perf:quest-triage`.
- Core counts, app-core set, thread affinity arguments, job-worker counts, NEON, Burst targets and
  `FloatMode`: `arm-mobile-hw-perf:xr2-cpu-threads-neon`.
- Render-thread cost from draw calls, SetPass, SRP Batcher, GRD, multiview:
  `unity-perf:unity-draw-calls-batching`. GLES driver/state overhead:
  `gles3-perf:gles-driver-overhead`.
- First-render hitches (PSO/shader compile): `unity-perf:unity-shader-hitches`.
- Loading, `Instantiate`, AUP and Addressables hitches: `unity-perf:unity-memory-assets`.
- Periodic judder with no single spike, stale frames, refresh rate, OpenXR Latency Optimization:
  `quest-perf:quest-frame-pacing`.
- CPU levels, dual-core mode, thermal soak: `quest-perf:quest-levels-thermal`.
- Reading Profiler markers, ProfilerRecorder HUDs, FrameTimingManager:
  `unity-perf:unity-profiling-workflow`. Simpleperf for IL2CPP hotspots:
  `quest-perf:quest-profiling-toolkit`.
- Choosing Vulkan vs GLES (Graphics Jobs is Vulkan-only): `gles3-perf:gles-vs-vulkan`.
- Whether GPU skinning runs as compute on GLES: `gles3-perf:gles-versions-unity-output`.

## Diagnose first

1. **Confirm CPU-bound, main thread.** Development build + Autoconnect Profiler, connect to
   `AndroidProfiler(ADB@127.0.0.1:34999)`; if needed
   `adb forward tcp:34999 localabstract:Unity-<bundle id>` (U5-084). CPU-bound when frame time
   exceeds budget while `XR.WaitForGPU` stays short (U5-081). Lock levels first
   (`adb shell setprop debug.oculus.cpuLevel <n>` / `debug.oculus.gpuLevel <n>`, see
   `quest-perf:quest-profiling-toolkit`), because dynamic clocks make A/Bs meaningless (U5-087).
2. **Main thread vs render thread.** With Multithreaded Rendering on, main-thread render cost shows
   as `Gfx.WaitForRenderThread` / `Gfx.WaitForCommands` stalls (U5-039, U5-082). `WaitForJobGroupID`
   on the main thread means jobs were completed too early or the worker pool is saturated (U5-082).
   To see submission cost on the main thread, turn MT rendering off *temporarily* while debugging,
   never in a shipped build (U5-039, A1-061).
3. **Core saturation.** In a Perfetto trace (MQDH), UnityMain saturating one core while the other
   app cores sit below 50% is the "move work into jobs" signature (A1-057). Perfetto setup:
   `quest-perf:quest-profiling-toolkit`.
4. **GC.** CPU Profiler module > **Call Stacks** on: `GC.Alloc` samples (magenta in Timeline) carry
   full stacks, on every thread (U5-012). Do not use Deep Profiling on Quest: slow, can run out of
   memory, and exaggerates small hot methods (U5-085). Spikes: `GC.Collect`, `GC.MarkDependencies`
   (U4-097).
5. **Physics.** `Physics.Simulate` appearing more than once per frame means catch-up steps;
   `Physics.ProcessReports` (Contacts, TriggerStays) large means callback count, not simulation
   (U5-064).
6. **Animation / UI.** `DirectorUpdateAnimationBegin` (all active Animators, culled or not) vs
   `DirectorUpdateAnimationEnd` (visible only) (U5-065, U5-066); `Canvas.SendWillRenderCanvases` /
   `Canvas.BuildBatch` for uGUI rebuilds (marker names not in the fetched reference, [verify on
   device]) (U5-071).
7. **Known hitch warnings.** Search captures for `Rigidbody.SetKinematic` (non-convex MeshCollider)
   and `Animation.AddClip` first (U5-101).
8. **Long hitch hunts without the Editor attached:** headless `-profiler-log-file` capture (player
   buffer defaults to 16 MB, U5-086); commands in `unity-perf:unity-profiling-workflow`.

## Key numbers

| Number | Applies to | Source |
|---|---|---|
| Target 0 B managed allocation per frame in steady state; 1 KB/frame at 60 fps = 3.6 MB garbage per minute | all versions, IL2CPP/Boehm | U5-004 [doc] |
| One `GC.Collect`: under 1 ms to hundreds of ms; no Quest pause figure published | all versions | U5-004 [doc]; measure `GC.Collect` vs "GC Reserved Memory" on device |
| Disabling incremental GC saves "as much as 1 ms per frame" (write barriers) in CPU-bound projects | all versions, not Quest-measured | U5-006 [doc] [verify on device] |
| `incrementalTimeSliceNanoseconds` default 3 ms (22% of 72 Hz, 27% of 90 Hz, 36% of 120 Hz); GC timer resolution can be a whole ms | all versions | U5-007 [doc] |
| Unity's manual-GC example: incremental collect at 8 MB allocated, full above 128 MB | all versions | U5-009 [doc]; no Quest heap ceiling published |
| Legacy Graphics Jobs + MT rendering: "up to 2 FPS" in major projects (no baseline fps given) | Unity ≥ 2022.3.35f1 and 6.x, Vulkan only (Graphics Jobs Mode requires Vulkan, G1-025) | A1-058, G1-025, G1-026 [doc] |
| 3 app cores at CPU L4 outperform dual-core mode at L6 | Quest 2/Pro (dual-core); principle all Quest | ARM-GF1-001 [doc] |
| App logic over ~2 ms "probably has room to optimize" (heuristic) | all Quest | U5-045 [doc] |
| Fixed Timestep default 0.02 s: 0.69 / 0.56 / 0.42 physics steps per frame at 72 / 90 / 120 Hz; 1/refresh raises physics cost 1.44x / 1.8x / 2.4x | all versions | U5-050 [doc] + arithmetic |
| Meta physics floors/ceilings: Sleep Threshold ≥ 0.005, Default Contact Offset ≥ 0.01, Solver Iterations ≤ 6 | all versions | U5-061 [doc] |
| Update manager with `T[]` about 5x faster than with `List<T>` on IL2CPP; plain-C# calls much cheaper than 10k `Update()` | Unity 5.2, iOS, 2015; principle only | U5-043 [measured] [verify on device] |
| uGUI rebuild of one large Canvas: "multiple milliseconds" (no device named) | uGUI, all versions | U5-071 [doc] [verify on device] |
| Job workers seen on Quest 3: 2 (unconfirmed forum report) | Quest 3, 2022.3.15 | A1-055 [community]; owned by `arm-mobile-hw-perf:xr2-cpu-threads-neon` |

No published Quest number exists for: IL2CPP Master vs Release, Faster runtime vs Faster builds, GPU
vs GPU (Batched) skinning, uGUI vs UI Toolkit world space, or Graphics Jobs Split vs Legacy. Measure
with the A/B in **Verify**.

Thermal headroom: Meta's level rule (steady state at CPU L4 / GPU L4), `quest-perf:quest-levels-thermal`.

## Fixes, ranked by payoff ÷ effort

Player-setting paths per Unity version, and a paste-ready editor script that applies fixes 1 and 4,
and fix 3 when you set `EnableLegacyGraphicsJobs = true` after an on-device A/B, are in
[references/player-scripting-settings.md](references/player-scripting-settings.md). Read it when
changing any Player setting or when paths differ from your version. Paste-ready C# (zero-allocation
replacements, pooling, update manager, GC control, Burst transform job, runtime `fixedDeltaTime`) is
in [references/gc-patterns.md](references/gc-patterns.md); read it when a Call Stacks capture shows
`GC.Alloc` samples or before writing any code for fixes 2 and 5-11.

### 1. Multithreaded Rendering on (never ship it off)
- **Change:** Player > Other Settings > Multithreaded Rendering = on. Check on device with
  `SystemInfo.renderingThreadingMode` and `adb logcat -s Unity`; the Editor always reports
  MultiThreaded (A1-058 notes).
- **Effect:** moves graphics-API calls off the main thread. With ~3 app cores, a serialized main and
  render thread loses a core of parallelism (A1-061, derived). Lower average CPU frame time; also
  more power-efficient: two cores at lower clock beat one at high clock (A1-040, ARM-GF1-001).
- **Cost:** none in quality. Off is a debugging-only state.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` `GLES` `Vulkan` - Throughput.

### 2. Get steady-state allocation to 0 B per frame
- **Change:** capture with Call Stacks (Diagnose step 4), then replace each source (U5-010, U5-013,
  U5-014, U5-057, U5-058, U5-070): string concat/format and `Debug.Log` in hot paths; closures and
  method-group delegates; boxing; `params`; array-returning APIs (`mesh.vertices`,
  `Animator.parameters`, `Renderer.sharedMaterials`); allocating physics queries;
  `.text = n.ToString()` on TMP. Allocate long-lived buffers at load, before gameplay allocations interleave,
  because the heap never compacts (U5-003). Large plain-data buffers go into `NativeArray<T>` (not
  scanned by the conservative GC; dispose explicitly) (U5-011). Stay on a current OpenXR plugin
  before chasing framework allocations (1.17.0-pre.2 fixed OpenXRProjectionLayer allocs, U5-095).
- **Effect:** removes GC-triggered spikes and heap growth; small average gain.
- **Cost:** code churn only. Patterns: [references/gc-patterns.md](references/gc-patterns.md).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` `GLES` `Vulkan` - Consistency (primary),
  Throughput.

### 3. Graphics Jobs = Legacy with MT rendering, for main-thread-bound apps
- **Change:** Unity 6: Player > Other Settings > Graphics Jobs on, Graphics Jobs Mode = Legacy.
  2022.3.35f1+: not settable in the UI, use an editor script (U5-035):
  ```csharp
  PlayerSettings.graphicsJobs = true;
  PlayerSettings.graphicsJobMode = GraphicsJobMode.Legacy;
  ```
  Unity 6.x can set the mode per device with a Vulkan Device Filtering Asset (A1-060), so Quest 2
  and Quest 3 can differ if measurements disagree.
- **Effect:** Meta measured up to 2 FPS in major projects; lower main-thread time.
- **Cost / conflict (U5-C1, surface both sides):** Meta XR Core SDK v68's Project Setup Tool said
  *disable* Graphics Jobs; v78/v83 and Meta's Nov 2024 page say enable Legacy on ≥ 2022.3.35f1
  (U5-036). A 2021.2-era Unity staff reply says Graphics Jobs implicitly disables Adreno LRZ/HSR,
  moving cost to the GPU (U5-038, [community]); whether that still holds for Legacy on 2022.3.35f1+
  is unknown. So: A/B GPU time and LRZ state (RenderDoc Meta Fork) as well as main-thread time.
  Graphics Jobs with MT rendering **off** roughly halved fps on Quest 2 (U5-038): never combine
  them. Split and Native modes are unmeasured on Quest (A1-059, U5-037).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 2022.3.35f1` `Unity ≥ 6000.0` `Vulkan` - Throughput. Not
  `GLES` (modes are Vulkan-only, G1-025). 2021.3: no mode selector, no Meta guidance, treat as
  unvalidated (A1-062).

### 4. IL2CPP for runtime speed, no log stack traces
- **Change (exact paths in the reference):** C++ Compiler Configuration = Master for shipping
  (U5-015); IL2CPP Code Generation = Faster runtime (2021.3/2022.3) / Optimize for runtime speed
  (6.x), the default: make sure CI's size option does not leak into release (U5-016); Stack Trace =
  None for Log and Warning in release, or `Application.SetStackTraceLogType` (U5-013); Target
  Architectures = ARM64 only, Armv9 security features off unless required (U5-021). 6.6: keep
  Managed Code Variant = Release for shipping; use Instrumented for profiling builds, because
  Release drops RG samplers and the RG Viewer connection from Development Builds (U1-030), and
  probably compiles out user `ProfilerMarker`s too (inference from `[Conditional]`, U5-018/U5-079)
  [verify on device].
- **Effect:** lower average CPU time; size of the gain has no published Quest number (Master vs
  Release: [verify on device]).
- **Cost:** longer builds (Master). Stack Trace None loses log call sites.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` (`Unity ≥ 6000.6` for Managed Code Variant) -
  Throughput.

### 5. Move main-thread work into Burst jobs; schedule early, complete late
- **Change:** move bulk per-object math (steering, culling, procedural animation, particle-like
  updates) into `IJobParallelFor` / `IJobParallelForTransform` with `[BurstCompile]`. Use
  `TransformHandle` on 6.3+ and `TransformAccessArray` on 2021.3-6.2 (U5-041). Schedule after input,
  complete in `LateUpdate` or next frame; completing immediately serializes onto the main thread
  (U5-042). Keep the worker count automatic (A1-053; counts owned by
  `arm-mobile-hw-perf:xr2-cpu-threads-neon`). Paste-ready `IJobParallelForTransform` + Burst
  manager: pattern 11 in [references/gc-patterns.md](references/gc-patterns.md). Check in Timeline
  that `BobJob` runs on worker threads, not inline on the main thread [verify on device].
- **Effect:** lower main-thread ms. Meta: 3 cores at L4 beat dual-core at L6, and spreading work at
  lower clocks is generally more power-efficient (ARM-GF1-001), so it also helps thermal. If only ~2
  workers exist, `IJobParallelFor` tops out near 3x if the main thread helps at Complete, about 2x
  with schedule-early/complete-late (A1-055, derived) [verify on device].
- **Cost:** job plumbing; Burst restrictions (no managed objects).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` (`Unity ≥ 6000.3` for TransformHandle) -
  Throughput, Consistency (thermal).

### 6. Physics: bound catch-up, then cut steps and queries
- **Change:**
  - Time > Maximum Allowed Timestep = one or two fixed steps, to stop the catch-up "spiral of doom"
    (U5-054; "one or two" is derived, no Meta number).
  - `fixedDeltaTime`: **open conflict, measure (U5-C4 / UNITY-GF1-C3).** Community and old Oculus
    samples use 1/refresh (one step per frame: constant cost, no judder, but 1.44x-2.4x the physics
    work; U5-050, U5-051 [community]); the Unity e-book says a step slightly *longer* than frame
    time on low-end devices (fewer steps, needs Rigidbody interpolation; UNITY-GF1-014). A 2024
    report says changing it had no visible effect on Quest (U5-053). Meta XR Core SDK uses
    `fixedDeltaTime` for physics pose prediction (U5-052). If you set it, read the refresh rate at
    runtime, since apps can switch rates: (runtime `XRDisplaySubsystem.TryGetDisplayRefreshRate`
    snippet: pattern 12 in [references/gc-patterns.md](references/gc-patterns.md)). Call it after a
    refresh-rate change, then log `Time.fixedDeltaTime` and FixedUpdate calls per frame on device
    (U5-053).
  - Meta limits: Sleep Threshold ≥ 0.005, Contact Offset ≥ 0.01, Solver Iterations ≤ 6; Rigidbodies
    on non-static colliders; pool objects (U5-061). Colliders moved every frame get a kinematic
    Rigidbody (U5-060).
  - Cheaper colliders (sphere < capsule < box < convex < mesh), Prebake Collision Meshes on, no
    runtime mesh cooking (U5-059); never `SetKinematic` on a body with a non-convex MeshCollider
    (U5-101).
  - Prune the Layer Collision Matrix; choose broadphase by measured time (U5-062). CCD only on small
    fast bodies such as thrown objects (U5-063).
  - Auto Sync Transforms off, one `Physics.SyncTransforms()` before queries (U5-056); Reuse
    Collision Callbacks on (U5-057); `*NonAlloc` queries or batched `RaycastCommand` completed late
    (U5-042, U5-058; code in gc-patterns.md).
  - No physics at all: `Physics.simulationMode = SimulationMode.Script` (2022.2+) or
    `Physics.autoSimulation = false` (2021.3) (U5-055).
- **Effect:** Maximum Allowed Timestep and the timestep choice mainly cut p99 (Consistency); the
  rest lowers average `Physics.Simulate` ms.
- **Cost:** a low Maximum Allowed Timestep slows simulation in game time during a spike; longer
  steps need interpolation.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` `GLES` `Vulkan` - Consistency, Throughput.

### 7. Take control of GC timing
- **Change:** keep Incremental GC on (default) unless allocations are already ~0 B, then A/B it off
  for up to ~1 ms (U5-005, U5-006). Tune `GarbageCollector.incrementalTimeSliceNanoseconds` in
  whole-ms steps (1 ms, 2 ms) when the main thread is the long pole (U5-007). For sections that must
  not hitch, use `GarbageCollector.GCMode = Disabled` and collect at a fade or load screen (U5-009;
  code in gc-patterns.md). GCMode is unsupported in the Editor: test on device.
- **Effect:** moves or removes collection spikes; average unchanged or slightly better.
- **Cost:** with GC disabled the heap only grows (U5-003); watch "GC Reserved Memory" against PSS
  limits (`quest-perf:quest-budgets-tiers`). Heavy reference churn can make incremental marking fall
  back to a stop-the-world collection (U4-097). Whether incremental GC uses the XR frame wait as
  idle time is undocumented (U5-008, conflict U5-C3): check where GC slices sit in Timeline.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` - Consistency.

### 8. Cut Update-loop overhead
- **Change:** delete empty `Update`/`LateUpdate`/`FixedUpdate`, especially empty virtuals in shared
  base classes (grep `virtual void Update`) (U5-044). Drive many objects from one manager calling a
  plain C# method over a `T[]` (U5-043; code in gc-patterns.md). On 6.0+, prefer `Awaitable` over
  `Task` for main-thread async (same-frame continuation, pooled), but not a `NextFrameAsync` loop
  per object, and never await one instance twice (U5-046 to U5-048). Cache `Animator.StringToHash`
  and `Shader.PropertyToID` in statics (U5-049).
- **Effect:** lower average main-thread ms; size scales with object count ([verify on device],
  U5-043's numbers are Unity 5.2/iOS).
- **Cost:** refactor to a manager; tickables lose per-object enable/disable semantics unless the
  manager handles them; `Awaitable` instances must not be awaited twice.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` (`Unity ≥ 6000.0` for Awaitable) - Throughput.

### 9. Animation and skinning
- **Change:** Animator Culling Mode = Cull Completely and SkinnedMeshRenderer Update When Offscreen
  off (U5-067); rig import Optimize Game Objects with only needed Extra Transforms, Skin Weights = 4
  bones (U5-068) (Meta's 2018 note said ≤ 2 bones, possibly stale; A/B 2 vs 4 on a crowd scene
  [verify on device]); flatten nested Animators (SortWriteJob) (U5-066); no OnStateMachineEnter/Exit
  behaviours on crowds (U5-065); legacy `Animation` or a script for simple loops, drop unused scale
  curves and root motion, zero-weight layers are skipped (U5-069); set up clips at load, never
  `AddClip` at runtime (U5-070). GPU skinning: Player > Other Settings > GPU Skinning = GPU
  (Batched) on 6.x (fewer compute dispatches), "GPU Compute Skinning" checkbox on 2022.3, "Compute
  Skinning" on 2021.3 (U5-040 / U4-077). Meta lists it as Optional "if CPU bound".
- **Effect:** lower main-thread and worker animation ms.
- **Cost:** GPU skinning trades CPU for GPU time and can lose on a GPU-bound title (U5-040); skinned
  meshes force Float32 position/normal/tangent (U4-072). Culled-by-shadow-caster behaviour in stereo
  is undocumented [verify on device]. On GLES, avoid compute dispatches between opaque draws
  (G2-067); GLES availability is `gles3-perf:gles-versions-unity-output`.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` `Vulkan` (`GLES` see link) - Throughput.

### 10. UI rebuilds and raycasts
- **Change:** split static and dynamic uGUI into separate Canvases or sub-Canvases (U5-071); remove
  Graphic Raycasters from non-interactive Canvases, Raycast Target off on static elements and
  labels, no Blocking Mask physics raycasts (U5-072); anchors instead of nested Layout Groups,
  virtualize long lists (U5-073); pool by disable-then-reparent, hide by disabling the Canvas
  component (U5-074); no Animators on UI except continuously changing elements (U5-075); TMP
  `SetText` with numeric args, StringBuilder, `char[]` or (6.6) `ReadOnlySpan<char>` (U5-014). UI
  Toolkit world space (6.2+): limit Max Interaction Distance (default infinity) and Interaction
  Layers (U5-077); 6.6 adds UI Toolkit Profiler modules (U5-078).
- **Effect:** removes multi-ms rebuild spikes (Consistency) and per-frame raycast cost (Throughput).
- **Cost:** more Canvases mean more batches/draws (Canvas splits break batching); disabling Raycast
  Target removes hit-testing on those elements.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` - Consistency, Throughput.

### 11. Spread bursty work across frames
- **Change:** anything that runs N items at once on an event (AI re-plans, spawns, pathfinding, save
  serialization) gets a per-frame budget: process k items per frame, or schedule a job and complete
  it next frame (U5-042 pattern). Time-sliced loop in gc-patterns.md. Heavy allocation bursts (JSON
  parse, instantiation) can trip the incremental-GC full-collection fallback (U4-097), so pre-size
  buffers.
- **Effect:** same average, lower p95/p99. Budget k from a ProfilerMarker on device; no published
  number.
- **Cost:** added latency. Results land k items per frame or one frame late, so AI or spawn response
  is delayed.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6` - Consistency.

## Verify

- **Allocation:** in a Development build, "GC Allocated In Frame" reads 0 in steady gameplay
  (Profiler Memory module; this counter is unavailable in Release players, per the counters
  reference). In release, record "GC Reserved Memory" with `ProfilerRecorder` (available in Release
  players, U5-080): it should stay flat across a **20-30 min** session, with no `GC.Collect` in
  gameplay captures.
- **Main-thread A/B:** Profile Analyzer compare, at least ~300 frames of identical content per
  variant (a working choice, U5-088), levels pinned. Expect the `PlayerLoop` median to fall for
  Throughput fixes (Graphics Jobs: roughly the "up to 2 FPS" scale; others: no published figure) and
  p95/p99 to fall for Consistency fixes.
- **GPU side-effects:** for Graphics Jobs and GPU skinning, GPU time and stale frames in OVR Metrics
  Tool must not rise (U5-038, U5-040).
- **Physics:** `Physics.Simulate` count per frame and ms at 72/90/120 Hz with each `fixedDeltaTime`
  candidate (0.02, 1/72, 1/36 at 72 Hz; UNITY-GF1-C3 method), plus visible judder, over at least 2
  min per variant.
- **Thermal:** a 20-30 min soak with OVR Metrics Tool logging CPU level, stale frames and
  temperature; CPU-side wins should show as holding a lower CPU level
  (`quest-perf:quest-levels-thermal`, `quest-perf:quest-profiling-toolkit`).

## Pitfalls and myths

- **"Set `Application.targetFrameRate` / `vSyncCount`."** Both are ignored in VR; the XR runtime
  paces frames (U5-022). Refresh rate: `quest-perf:quest-frame-pacing`.
- **"Script Call Optimization: Fast but no Exceptions."** iOS/tvOS only; not a Quest lever (U5-020).
- **CoreCLR / .NET GC advice.** Generational-GC tuning and the 85 KB LOH threshold apply only to
  CoreCLR, not IL2CPP/Boehm on Quest (U5-002).
- **Graphics Jobs "always off" (old Meta SDK v68) vs "always on".** Version-gated and measured, not
  a rule (U5-C1). And never Graphics Jobs with MT rendering off.
- **Profiling a 6.6 Release-variant build and seeing no custom markers.** Switch Managed Code
  Variant to Instrumented (U5-018 / U1-030) [verify on device].
- **`[Il2CppSetOption(Option.NullChecks/ArrayBoundsChecks, false)]` everywhere.** Only on profiled,
  known-safe hot loops: failures become native crashes (U5-017). Burst code avoids the question.
- **Managed Stripping / Strip Engine Code / 6.6 "Maximum Size Reduction" as speed levers.** They are
  size levers with no published per-frame effect (U5-019).
- **"Sustained Performance Mode" for thermals.** No Meta doc says Horizon OS honours it; use CPU/GPU
  levels (U5-028, `quest-perf:quest-levels-thermal`).
- **Optimized Frame Pacing (Swappy) on XR.** Undocumented under an XR compositor; community reports
  hitches and ignored refresh changes. Default off pending a stale-frame A/B (U5-023, U5-024,
  conflict U5-C5).
- **Dual-core mode before jobs.** Meta ranks 3 cores at L4 above dual-core at L6; dual-core exists
  only on Quest 2/Pro (ARM-GF1-001). Quest 3/3S has none (A1-057).
- **Thermal "use X% of frame time" from the Unity e-book.** Generic phone heuristic, not Quest
  guidance (UNITY-GF1-C1).
- **Community "Quest is a 3-core device, set workers = cores - 1".** Stale and unmeasured; owned by
  `arm-mobile-hw-perf:xr2-cpu-threads-neon` (U5-034, U5-C6).

## Sources

All accessed 2026-09-24.

- https://docs.unity3d.com/6000.7/Documentation/Manual/scripting-backends-coreclr.html [doc] (U5-001)
- https://unity.com/releases/editor/whats-new/6000.7.0a2 [doc] (U1-071)
- https://discussions.unity.com/t/path-to-coreclr-2026-upgrade-guide/1714279 [doc] (U5-002)
- https://docs.unity3d.com/6000.3/Documentation/Manual/performance-managed-memory-introduction.html [doc] (U5-003)
- https://docs.unity3d.com/6000.3/Documentation/Manual/performance-garbage-collector.html [doc] (U5-004)
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html [doc] (U5-004, U5-064 to 066, U5-082, U5-101)
- https://docs.unity3d.com/6000.6/Documentation/Manual/performance-incremental-garbage-collection.html [doc] (U5-005, U5-008)
- https://docs.unity3d.com/6000.3/Documentation/Manual/performance-disabling-garbage-collection.html [doc] (U5-006)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Scripting.GarbageCollector-incrementalTimeSliceNanoseconds.html [doc] (U5-007)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Scripting.GarbageCollector.GCMode.html [doc] (U5-009)
- https://docs.unity3d.com/6000.3/Documentation/Manual/performance-reference-types.html [doc] (U5-010)
- https://docs.unity3d.com/6000.3/Documentation/Manual/performance-optimizing-arrays.html [doc] (U5-010, U5-011)
- https://docs.unity3d.com/6000.3/Documentation/Manual/performance-track-garbage-collection.html [doc] (U5-012)
- https://docs.unity3d.com/6000.3/Documentation/Manual/stack-trace.html [doc] (U5-013)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc] (U5-014, U5-019, U5-078)
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html [doc] (U5-015, U5-018, U5-021, U5-037, U5-039, U5-040, A1-059)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc] (U1-030)
- https://docs.unity3d.com/6000.6/Documentation/Manual/il2cpp-runtime-checks.html [doc] (U5-017)
- https://docs.unity3d.com/6000.6/Documentation/ScriptReference/QualitySettings-vSyncCount.html [doc] (U5-022)
- https://docs.unity3d.com/2021.3/Documentation/Manual/class-PlayerSettingsAndroid.html [doc] (A1-062, U4-077)
- https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ [doc] (U5-035, A1-058, G1-026)
- https://github.com/icosa-mirror/com.meta.xr.sdk.core [doc] (U5-036, U5-052)
- https://discussions.unity.com/threads/vulkan-bug-quest-2-urp-graphics-jobs-no-multithreaded-rendering-slow.1208908/ [community] (U5-038)
- https://developers.meta.com/horizon/documentation/unity/unity-perf/ [doc] (U5-039, A1-061)
- https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ [doc] (A1-057, ARM-GF1-001)
- https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/ [doc] (A1-040)
- https://docs.unity3d.com/6000.3/Documentation/Manual/vulkanapi-graphics-jobs-configuration.html [doc] (G1-025)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-TransformHandle.html [doc] (U5-041)
- https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-raycasts-queries.html [doc] (U5-042, U5-058)
- https://unity.com/blog/engine-platform/10000-update-calls [measured] (U5-043, U5-044)
- https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ [doc] (U5-045)
- https://docs.unity3d.com/6000.3/Documentation/Manual/async-awaitable-introduction.html [doc] (U5-046, U5-048)
- https://docs.unity3d.com/6000.3/Documentation/Manual/async-awaitable-continuations.html [doc] (U5-047)
- https://docs.unity3d.com/6000.3/Documentation/Manual/MecanimPeformanceandOptimization.html [doc] (U5-049, U5-067, U5-069)
- https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-frequency.html [doc] (U5-050, U5-054)
- https://communityforums.atmeta.com/discussions/dev-unity/time---fixed-timestep--hz-values-for-oculus-devices-in-unity/751740 [community] (U5-051)
- https://discussions.unity.com/t/change-fixeddeltatime-for-meta-quest/1517687 [community] (U5-053)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-PhysicsManager.html [doc] (U5-055, U5-063)
- https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-transform-sync.html [doc] (U5-056)
- https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-collision-callbacks.html [doc] (U5-057)
- https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-collider-types.html [doc] (U5-059)
- https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-static-colliders.html [doc] (U5-060)
- https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ [doc] (U5-061)
- https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-broad-phase.html [doc] (U5-062)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-Animator.html [doc] (U5-067)
- https://docs.unity3d.com/6000.3/Documentation/Manual/FBXImporter-Rig.html [doc] (U5-068)
- https://unity.com/how-to/unity-ui-optimization-tips [doc] (U5-071 to 075)
- https://docs.unity3d.com/6000.6/Documentation/Manual/ui-systems/world-space-ui.html [doc] (U5-077)
- https://docs.unity3d.com/6000.6/Documentation/Manual/android-profile-on-an-android-device.html [doc] (U5-084)
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-command-line-arguments.html [doc] (U5-086)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Profiling.ProfilerRecorder.html [doc] (U5-080)
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-counters-reference.html [doc] (GC counter availability in Release players)
- https://docs.unity3d.com/6000.6/Documentation/Manual/VRFrameTiming.html [doc] (U5-081)
- https://developers.meta.com/horizon/documentation/unity/unity-profiler-tool/ [doc] (U5-087)
- https://packages.unity.com/com.unity.performance.profile-analyzer [doc] (U5-088)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc] (U5-095)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc] (G2-067)
- https://cdn.bfldr.com/S5BC9Y64/at/3mp8w3wk36k2k6mmj5pbbr/Optimize_your_game_performance_for_mobile__XR__and_the_web_in_Unity_Unity_6_edition_e-book.pdf [doc] (UNITY-GF1-008, UNITY-GF1-014, UNITY-GF1-017)
- https://web.archive.org/web/20260214200619/https://communityforums.atmeta.com/discussions/dev-quest/unity-quest-3-multithreaded-performance/1132006 [community] (A1-055)
