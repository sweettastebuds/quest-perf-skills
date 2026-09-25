---
name: unity-shader-hitches
description: "Removing shader and pipeline-compilation hitches in Unity on Quest (Vulkan and API-agnostic): hitch on first use, spike when an object first renders, shader variant explosion, variant stripping, PSO tracing and GraphicsStateCollection warmup, ShaderVariantCollection limits on Vulkan, the Vulkan pipeline cache, and shader build size. Use for one-off spikes when content first renders, or when shader_hitches shows in OVR Metrics. GLES blob cache and program binaries: gles3-perf:gles-shader-binaries."
---

# Shader and PSO hitches in Unity on Quest (consistency)

Goal: **Consistency** (no stale frames at first use of a material, effect or
area; tight p99). Warmup work moved into loads also shortens nothing on the
average frame, so nothing here is a Throughput fix unless stated.

Scope: Unity 2021.3 / 2022.3 / 6000.0-6000.6, URP 12 / 14 / 17.x, Vulkan
(Meta's default for Quest) unless tagged; Quest 2 (Adreno 650) and
Quest 3/3S (Adreno 740). All sources accessed 2026-09-24.

Lead facts:
- On Vulkan a PSO bakes shader variant + render state + vertex layout + RT
  formats. `ShaderVariantCollection.WarmUp` / `Shader.WarmupAllShaders` can
  build the wrong PSOs "due to missing graphics states"; Unity does not
  recommend SVC warmup there (U3-082). Unity 6: trace a
  GraphicsStateCollection (GSC) in a development build ON DEVICE and warm it
  with `WarmUpProgressively` (U3-084, U3-086).
- Conflict X-C1: "Fixed GraphicsStateCollection warmup for Vulkan"
  (UUM-121231) appears only in 6000.4.0a4 with no 6.0/6.3 backport found
  (U1-047), vs. a reading that it was a 6.4-alpha-only regression and LTS is
  safe (U3-091). Unresolved: measure on your LTS (Verify). [verify on device]
- Stereo-instancing (multiview/SPI) variants are not prewarmed by the legacy
  warmup APIs (U1-049). Whether GSC traces them on Quest is undocumented.
- Unity persists PSOs in `vulkan_pso_cache.bin` (U3-094). Install, app
  update and Horizon OS/driver update each start cold (U3-096).
- OVR Metrics CSV column `shader_hitches` is the field signal; it has no
  published definition (Q1-014).

## When to use / when not

Use when:
- A one-off spike or stale-frame burst lines up with something rendering for
  the first time (new material, effect, area, UI panel, quality switch).
- The first run after install is worse than the second (Q1-011).
- `shader_hitches` increments in the OVR Metrics CSV.
- Profiler shows `Shader.CreateGPUProgram` or
  `CreateGraphicsGraphicsPipelineImpl` in a spike frame.
- Variant counts, build time or shader build size are out of hand; writing
  a stripper; choosing between SVC and GSC.

Do not use; go to the sibling instead:
- Not yet sure it is a first-use hitch: `quest-perf:quest-triage`.
- Periodic judder with no single spike, stale frames with a good average:
  `quest-perf:quest-frame-pacing`.
- Spike during a load or scene stream (not at first render):
  `unity-perf:unity-memory-assets`. GC or physics spikes:
  `unity-perf:unity-cpu-scripting`.
- GLES build: Android blob cache, `glProgramBinary`, stutter after an OS
  update on GLES, GLES SVC warmup: `gles3-perf:gles-shader-binaries`.
- Shader too expensive per pixel, keyword vs `dynamic_branch` GPU cost:
  `unity-perf:unity-shader-authoring`.
- Which Unity version has which GSC feature, and flagging X-C1:
  `unity-perf:unity-version-matrix`.
- CPU Boost during the warm window: `quest-perf:quest-levels-thermal`.
- Profiler/Perfetto setup and capture hygiene:
  `unity-perf:unity-profiling-workflow`.

## Diagnose first

1. **Cold vs warm split (field signal).** Record an OVR Metrics CSV for the
   same scripted route twice: first run after a fresh install (cold), then a
   second launch (warm). Keep them as separate datasets (Q1-011). Pull:
   ```sh
   adb pull /sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/ .
   ```
   Compare `shader_hitches`, `stale_frame_count`, `stale_frames_consecutive`
   and `max_repeated_frames` per segment (Q1-008, Q1-014, Q1-094). Rows are
   1 Hz averages, so they locate the second, not the frame (Q1-010). The
   CSV analysis script lives in `quest-perf:quest-profiling-toolkit`.
   Diagnosis: cold run hitches, warm run clean = compile/PSO (this skill).
   Both hitch at the same spot = something else (triage).
2. **Confirm `shader_hitches` means what you think.** It is undocumented.
   Put a never-seen material on screen and watch the column move
   (Q1-014 notes). [verify on device]
3. **Frame-level attribution (Profiler, dev build on device).** Deep Profile
   off, Autoconnect Profiler on. In the spike frame look for (U3-081):
   - `Shader.CreateGPUProgram`: GPU program creation (variant first use).
   - `CreateGraphicsGraphicsPipelineImpl`: Vulkan PSO creation.
   - `Shader.ParseThreaded` / `Shader.ParseMainThread`: load;
     `Shader.MainThreadCleanup`: unload (re-creation after unload is a
     Keep Loaded Shaders Alive question, U3-080).
   Unity 6: also enable Project Settings > Graphics > Log Shader Compilation
   in the dev build and read it with `adb logcat -s Unity`.
4. **Check the pipeline cache survives.** Debuggable build only:
   ```sh
   adb shell run-as <package> ls -l cache/     # after a warm session, and again after force-stop
   ```
   Missing or zero-size `vulkan_pso_cache.bin` after a warm session means
   every launch is cold (U3-094). When Unity flushes it (pause or quit) is
   undocumented; a kill before the flush can lose it.
5. **Log whether real PSO warmup is possible.** Log
   `SystemInfo.supportsParallelPSOCreation` at startup on Quest 2 and
   Quest 3. False = GSC silently uses SVC semantics (U3-086). No published
   value for Quest Vulkan. [verify on device]
6. **Count variants** with URP Shader Variant Log Level (URP 14+) or Export
   Shader Variants (6.x): per-shader `Total=kept/all` lines (U3-077).

- Read [references/gsc-warmup.md](references/gsc-warmup.md) when writing or
  debugging GSC trace/warm code, upgrading across the 6.5 namespace move, or
  shipping 2021.3/2022.3 without GSC.
- Read [references/variant-stripping.md](references/variant-stripping.md)
  when variant count or shader build size is high, when writing or auditing
  an IPreprocessShaders stripper, or when changing URP Assets or quality
  tiers.

## Key numbers

| Number | Value | Source | Applies to |
|---|---|---|---|
| Frame budget | 13.9 ms at 72 Hz, 11.1 ms at 90 Hz, 8.3 ms at 120 Hz | Q1-089 [doc] | `Quest 2` `Quest 3/3S` |
| Dip tolerance | one-off dip lasting a couple of seconds OK at 72 Hz if it stays above 65 fps and recovers; must not repeat in a cycle. No published figure for 90/120 Hz | Q1-090 [doc] | `Quest 2` `Quest 3/3S` at 72 Hz |
| Cold-start cache build | heavy apps can pause "several seconds, sometimes minutes" at startup; triggers: first run after install, app update, OS/driver update | U3-096 [doc] | `Quest 2` `Quest 3/3S` |
| Per-PSO creation time on Adreno | no published number; measure `CreateGraphicsGraphicsPipelineImpl` durations | U3-088 notes | - |
| GSC warm per-frame count | no published number; size from measured PSO time so warm work fits frame slack (budget minus measured frame time) | U3-088 notes | `Unity ≥ 6000.0` |
| Meta prewarm sample rate | 50-100 objects per frame at 1/60 s | U3-093 [doc] | `Unity 2021.3/2022.3` |
| `multi_compile` growth | 8 keyword sets of 3 can exceed 6,000 variants | U3-071 [doc] | all |
| Keyword count | over 128 keywords per shader: small runtime penalty; 4 reserved | U3-072 [doc] | 2021.2+ |
| Shader Graph variant limit | 128 (2021.3 per-user pref), 2048 (2022.3, 6.x) | UNITY-GF2-001 [doc] | per branch |
| Shader chunk size | 16 MB default; chunk count 0 = no limit | U3-080 [doc] | 2021.3+ |
| SBC prewarm cut-off (deprecated) | 10 minutes per backend headset | U3-097, QUEST-GF1-004 [doc] | `Quest 2` `Quest 3/3S` |
| SBC case study | Asgard's Wrath 2 startup 7 min to 20 s (Meta case study, not reproducible) | QUEST-GF1-004 [doc] | Meta Store app |

## Fixes, ranked by payoff ÷ effort

### 1. Stop relying on SVC warmup on Vulkan; trace and warm a GSC on device

- **Change (Unity 6000.0+):** add a tracer to a Development Build, play
  every material, effect and quality tier on the headset, `SaveToFile`,
  `adb pull` the `.graphicsstate`, import it, and warm it at launch with
  `WarmUpProgressively` behind a loading environment (U3-084, U3-085,
  U3-086). One collection per graphics API and quality tier; re-trace after
  every Editor upgrade (U1-046 notes). Paste-ready `GscTracer` and
  `GscWarmup` (with the `#if UNITY_6000_5_OR_NEWER` namespace switch) are
  in [references/gsc-warmup.md](references/gsc-warmup.md).
- **Effect:** removes first-use PSO creation from gameplay frames: cuts
  p99/stale bursts; average frame time unchanged. Moves cost into the load.
- **Cost / side effects:** longer loading window; per-tier trace upkeep;
  compute shaders are not captured (U3-084). On 6.0/6.3 LTS the Vulkan fix
  is disputed (X-C1): confirm with the Verify protocol.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 6000.0` `URP 17` `Vulkan`;
  Consistency.

### 2. Put the warm window where the user cannot see it, and repeat every launch

- **Change:** warm on every launch (the cache goes cold after install,
  update and OS update, U3-096) behind a loading environment, and reveal
  the scene only when warmup reports done. Request CPU Boost for the window
  and drop back afterwards (one line here; owner
  `quest-perf:quest-levels-thermal`). 6000.3.21f1+ skips per-variant work
  for already-warm variants, so repeat launches are cheaper (U1-050).
  Unity 6.5+: Project Settings > Graphics > Shader Settings can do this
  without code (Preload Graphics State Collection, Collection Startup
  Behavior = Warmup, Warmup Asynchronously, Warmup After Showing First
  Scene, per-frame count; U3-088).
- **Effect:** consistency during play; slightly longer load.
- **Cost / side effects:** warming before the first scene lengthens black/splash
  time; after it, PSO creation lands in visible frames.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 6000.0` (settings UI
  `Unity ≥ 6000.5`) `Vulkan`; Consistency.

### 3. Close the gaps with the cache-miss loop

- **Change (6.5+):** QA dev builds warm with `traceCacheMisses: true`; PSOs
  requested after warmup collect in `cacheMissCollection`; save, pull,
  `Append` into the shipping collection, check with `ContainsVariant`.
  `isTracingCacheMisses` must be false before the warmup call (U3-087).
  Before 6.5: re-run the tracer around the scenes that still hitch; saving
  with the same collection appends (shader-pso-trace, 6000.0). Code in
  [references/gsc-warmup.md](references/gsc-warmup.md).
- **Effect:** drives the residual p99 hitches toward zero; the closest thing
  to a hitch regression test (U3-087 notes).
- **Cost:** a QA playthrough per content change; full (non-progressive) QA warm.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 6000.5` `Vulkan`; Consistency.

### 4. 2021.3 / 2022.3 (no GSC): render every material once behind a load

- **Change:** draw each material/state combination once through the real
  XR camera, in-frustum, behind an opaque loading environment, 50-100
  objects per frame as in Meta's archived Unity-ShaderPrewarmer (U3-092,
  U3-093). It covers MeshRenderer states only: add skinned meshes,
  particles, UI and shadow-caster/depth passes yourself. Drawing through
  the XR camera is how stereo variants get hit, since legacy APIs skip them
  (U1-049) [verify on device]. Code: `RenderOncePrewarmer` in
  [references/gsc-warmup.md](references/gsc-warmup.md). Also usable on
  6.x as a top-up for PSOs a GSC misses or when
  `supportsParallelPSOCreation` is false.
- **Effect:** removes first-draw PSO creation; average unchanged.
- **Cost:** load time; content upkeep (every new material must be listed).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3` `Unity 2022.3` `URP 12`
  `URP 14` `URP 17` `Unity ≥ 6000.0 (top-up)` `Vulkan` `GLES`; Consistency.
- GLES warmup specifics (SVC fallback, multiview): `gles3-perf:gles-shader-binaries`.

### 5. Cut variants before you warm them

- **Change:** fewer variants = fewer PSOs to trace and warm, shorter
  builds, smaller shader data. In order of effort:
  - One URP Asset feature set across quality tiers: tiers differ only in
    values (render scale, shadow resolution), not feature toggles; URP keeps
    the union of features across all assets (U3-078).
  - URP stripping: Strip Unused Variants, Strip Unused Post Processing
    Variants, Strip Screen Coord Override Variants (URP 14+) (U3-077). With
    GPU Resident Drawer keep BRG variants via Graphics > BatchRendererGroup
    Variants.
  - Remove shaders from Always Included Shaders; it forces every variant
    (U3-089).
  - 6.3+: Graphics > Shader Build Settings retypes URP `multi_compile` sets
    to `shader_feature` or `dynamic_branch` per build profile, no URP fork
    (U3-074). The GPU cost of `dynamic_branch` is judged in
    `unity-perf:unity-shader-authoring`.
  - 6.6: Shader Constant Defines replace keyword switches with per-profile
    constants, no variant (U3-075) [verify on device].
  - Shader Graph: Shader Feature not Multi Compile for artist toggles, stage
    scope Vertex/Fragment (UNITY-GF1-003); leave Allow Material Override off
    on high-count environment graphs (UNITY-GF2-002).
  - `IPreprocessShaders` stripper for XR default keywords a Quest build never
    uses (U3-048, U3-076). Never strip the active stereo keyword.
  Tables and the paste-ready stripper:
  [references/variant-stripping.md](references/variant-stripping.md).
- **Effect:** smaller warm set and shorter load; no direct frame-time change.
- **Side effect:** a wrongly stripped variant renders the error shader (or
  silently the nearest match without strict matching).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 2021.3` `URP 12+` `Vulkan` `GLES`; Consistency.

### 6. Turn on Strict shader variant matching in test builds

- **Change:** Player > Strict shader variant matching (2022.3+). A missing
  variant renders the error shader and logs shader, subshader, pass and
  keywords instead of silently using the closest match, which can load a
  different PSO later (U3-073).
- **Effect:** catches stripping mistakes and variant drift before they ship.
- **Cost:** a missing variant shows the error shader in test builds; do not
  ship with it on unless intended.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 2022.3` `Vulkan` `GLES`; Consistency.

### 7. Keep programs alive across scene unloads (memory trade)

- **Change:** Player settings > Keep Loaded Shaders Alive, if Profiler shows
  `Shader.MainThreadCleanup` followed later by `Shader.CreateGPUProgram` for
  the same shader after a scene round-trip (U3-080). A chunk-count cap can
  force decompression again later (inference, [verify on device]).
- **Effect:** no re-creation hitches after a scene round-trip; average same.
- **Cost:** RAM, a real trade on Quest 2's 6 GB (U3-080 notes). Budget
  owner: `unity-perf:unity-memory-assets`.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 2021.3`; Consistency.

### 8. Protect the pipeline cache

- **Change:** make sure the app lives long enough to flush
  `vulkan_pso_cache.bin` (check step 4 of Diagnose). On 6.4+ a corrupted
  cache file no longer makes `vkCreatePipelineCache` fail; before 6.4 a bad
  file can cost the whole persisted cache (U3-095). No 6.0/6.3 backport was
  found.
- **Effect:** keeps later launches warm; average unchanged.
- **Cost:** none on 6.4+; on 6.0/6.3 a corrupted file means a cold session.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 6000.4` (fix) `Vulkan`; Consistency.

### Not a fix: Meta Shader Binary Cache (SBC)

Meta's automated SBC is marked deprecated and unmaintained, Unity apps are
"not guaranteed" to be processed, and it only helps Store installs (U3-097,
QUEST-GF1-004). Resolved for planning: treat it as absent and ship your own
warmup (U3-C6). If already integrated (`com.oculus.sbcpath` manifest entry)
it does no harm.

### Out of Unity's reach

Qualcomm: create all pipelines at init (fixes 1-4 do this); also link-time
optimization bit and specialization constants (A2-077), for which no dossier
finding shows a Unity control.

## Verify

Protocol for every fix above, and the method for X-C1 on 6.0/6.3 LTS:

1. Build the release configuration you ship (plus a dev build for Profiler
   markers). Keep quality tier, refresh rate and route identical across runs.
2. Make it cold: reinstall the APK (or on a debuggable build delete the
   cache file with `adb shell run-as <package> rm cache/vulkan_pso_cache.bin`).
3. Run a scripted route that shows every material and effect once, with the
   OVR Metrics CSV recording. Mark segments with `AppendCsvDebugString`
   (Q1-094). Then run it a second time in the same launch or a new launch.
4. Compare per segment, cold-with-warmup vs cold-without-warmup, and pass 1
   vs pass 2:
   - `shader_hitches` should drop to 0 (or its baseline) on the warmed cold
     run, not only on pass 2.
   - `stale_frame_count` / `stale_frames_consecutive` at first appearance of
     each material should match the warm pass.
   - Profiler (dev build): no `CreateGraphicsGraphicsPipelineImpl` or
     `Shader.CreateGPUProgram` in gameplay frames after the warm window.
   - Warm logs: `isWarmedUp=True`, `completedWarmupCount` close to
     `totalGraphicsStateCount`, `supportsParallelPSOCreation` logged.
5. X-C1 verdict: if on 6.0 or 6.3 LTS the warmed cold run still shows PSO
   creation markers for states that are in the collection, the Vulkan
   warmup issue applies to your version: add the render-once top-up (fix 4)
   or move to 6.4+ (`unity-perf:unity-upgrade-risks`).
6. Stereo check (U1-049): the XR camera's Lit materials must not show PSO
   creation on the warmed run. [verify on device]

Magnitude: no published hitch counts exist for Quest (U1-086 notes). The
target is Meta's dip tolerance, no dip below 65 fps at 72 Hz that repeats
(Q1-090). Session length: one full route covering all content, cold, then
the same route warm. Repeat on Quest 2 and Quest 3/3S, and again after every
Editor upgrade and after a Horizon OS update (the cache resets, U3-096).

## Pitfalls and myths

- **"We call `ShaderVariantCollection.WarmUp`, so shaders are warm."** Not on
  Vulkan: variants without graphics state can produce the wrong PSOs
  (U3-082). This is why 2021.3/2022.3 Vulkan apps that "warm shaders" still
  hitch on first draw.
- **Tracing in the Editor.** Editor traces carry desktop state; trace on the
  headset in a dev build (U3-085). Tracing does not work in release builds
  (U3-084).
- **One collection for all tiers.** Quality levels change PSOs; switch tiers
  while tracing and keep one collection per tier (U3-085). Whether Quest 2
  and Quest 3 need separate traces is unverified. [verify on device]
- **6.5 upgrade breaks the build.** GSC moved from
  `UnityEngine.Experimental.Rendering` to `UnityEngine.Rendering` in
  6000.5.0a9; guard with `#if UNITY_6000_5_OR_NEWER` (U3-083).
- **Assuming GSC falls back cleanly.** Fallback to SVC semantics happens
  when `supportsParallelPSOCreation` is false (U3-086). Conflict U3-C4: the
  6.x manual says the fallback is 6.1+, release notes add it in
  6000.0.55f1. Verify on 6.0 LTS before relying on it.
- **Assuming 6.0/6.3 LTS Vulkan warmup works (or that it does not).** X-C1
  is unresolved both ways; measure (Verify step 5).
- **Unity's GSC sample works on Quest.** It builds only for Windows and
  macOS; Quest integration is yours (U3-090).
- **Compute shaders are in the collection.** They are not captured (U3-084);
  warm compute kernels by dispatching them once in the load.
- **"Warm once at install."** Every OS update invalidates the driver cache
  (U3-096); warm on every launch.
- **SBC will handle it.** Deprecated, Unity not guaranteed (U3-097, U3-C6).
  Meta's GDC 2026 recap still promoted it (QUEST-GF1-004); the doc page is
  the later word.
- **Stripping `STEREO_MULTIVIEW_ON`.** It is the active keyword on Quest
  (U3-042, U3-043); stripping it gives left-eye-only rendering or the error
  shader (U3-048 notes).
- **Strip Unused Variants with GPU Resident Drawer.** It strips DOTS
  instancing variants BRG needs (U3-077 notes).
- **Arm's 512 KB-1 MB blob cache advice.** Wrong for Quest; GLES owner
  `gles3-perf:gles-shader-binaries` (G3-018).

## Sources

- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-prewarm-other.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-introduction.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-trace.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.0/Documentation/Manual/shader-pso-trace.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/shader-prewarm.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.1/Documentation/Manual/shader-prewarm.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-prewarm.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-example.html (2026-09-24) [doc]
- https://docs.unity3d.com/ScriptReference/Rendering.GraphicsStateCollection.html (2026-09-24) [doc]
- https://docs.unity3d.com/ScriptReference/Rendering.GraphicsStateCollection.WarmUp.html (2026-09-24) [doc]
- https://docs.unity3d.com/ScriptReference/Rendering.GraphicsStateCollection.WarmUpProgressively.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Experimental.Rendering.GraphicsStateCollection.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Experimental.Rendering.GraphicsStateCollection.WarmUpProgressively.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity61.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (2026-09-24) [doc]
- https://unity.com/releases/editor/whats-new/6000.0.0 (2026-09-24) [doc]
- https://unity.com/releases/editor/whats-new/6000.0.0b11 (2026-09-24) [doc]
- https://unity.com/releases/editor/whats-new/6000.0.55f1 (2026-09-24) [doc]
- https://unity.com/releases/editor/whats-new/6000.0.74f1 (2026-09-24) [doc]
- https://unity.com/releases/editor/whats-new/6000.3.21f1 (2026-09-24) [doc]
- https://unity.com/releases/editor/whats-new/6000.4.0a4 (2026-09-24) [doc]
- https://unity.com/releases/editor/whats-new/6000.4.0f1 (2026-09-24) [doc]
- https://unity.com/releases/editor/whats-new/6000.5.0a9 (2026-09-24) [doc]
- https://discussions.unity.com/t/graphicsstatecollection-tracing-and-warmup-in-unity-6/951031 (2026-09-24) [community]
- https://github.com/oculus-samples/Unity-ShaderPrewarmer (2026-09-24) [doc]
- https://docs.unity3d.com/6000.0/Documentation/Manual/embedded-linux-optional-features.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-loading.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-conditionals-choose-a-type.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/SL-MultipleProgramVariants-declare.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-keywords-default.html (2026-09-24) [doc]
- https://docs.unity3d.com/2022.3/Documentation/Manual/shader-keywords.html (2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/Runtime/XR/XRPass.cs (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-features.html (2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-check.html (2026-09-24) [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-global-settings.html (2026-09-24) [doc]
- https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Keywords-reference.html (2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/2021.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphPreferences.cs (2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs (2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs (2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Targets/UniversalTarget.cs (2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ (2026-09-24) [doc]
- https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ (2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ (2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ (2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (2026-09-24) [doc]
- https://github.com/batunii/Arjuna/blob/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_142600.csv (2026-09-24) [measured]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (2026-09-24) [doc]
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/egl_cache.cpp (2026-09-24) [doc]
- https://developer.arm.com/documentation/101897/0303/System-integration/Android-blob-cache-size-in-OpenGL-ES (2026-09-24) [doc]
