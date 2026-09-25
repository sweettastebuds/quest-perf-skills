---
name: unity-draw-calls-batching
description: "Cutting CPU render cost in Unity URP on Quest 2/3/3S: too many draw calls, SetPass calls, SRP Batcher compatibility, static batching, GPU instancing, BatchRendererGroup, GPU Resident Drawer, GPU occlusion culling, and single-pass instanced/multiview. Use when the render thread is bound by draw submission, when draw calls exceed budget, or when choosing between batching methods. For the budget numbers, see quest-budgets-tiers."
---

# Draw calls and batching (Unity URP on Quest)

Goal: **Throughput (CPU)**, mainly render-thread time. One fix (static-batch
layout) also serves **Consistency**. Evidence IDs refer to `research/unity.md`
(U*, UNITY-GF*, X-C*) and `research/gles3.md` (G*); all accessed 2026-09-24.

Read [references/batching-methods.md](references/batching-methods.md) when you
need the full method × Unity version × API × constraints matrix, the GRD
eligibility checklist, BRG buffer modes, stereo-path rules, or the numbers
index with setups. Read [references/batching-code.md](references/batching-code.md)
when you need the paste-ready SRP Batcher shader template, the MPB-replacement
material cache, the editor batching/GRD audit (fixes 3 and 6), or the
startup stereo/BRG path logger (Diagnose step 5).

## When to use / when not

Use when:
- A capture shows the render thread (`UnityGfx`) or the main thread's rendering
  work over budget, and SetPass or draw counts are high.
- Choosing between SRP Batcher, static batching, GPU instancing, BRG, GPU
  Resident Drawer (GRD) and GPU occlusion culling for a Quest project.
- Checking that multiview is actually on, or that a custom shader keeps SRP
  Batcher compatibility.

When not:
- Bottleneck unknown ("low FPS", "stutter") -> `quest-perf:quest-triage`.
- "How many draw calls can I afford" -> `quest-perf:quest-budgets-tiers` (owns
  the budget figures; none is a hard limit).
- GPU-bound on fill rate or shading -> `quest-perf:quest-resolution-foveation`,
  `unity-perf:unity-shader-authoring`.
- GL state changes, glDraw overhead, buffer orphaning ->
  `gles3-perf:gles-driver-overhead`.
- OVR_multiview GLES mechanics -> `gles3-perf:gles-extensions-multiview`.
- Main thread bound by scripts, GC, physics, UI -> `unity-perf:unity-cpu-scripting`.
- Hitch the first time a material renders -> `unity-perf:unity-shader-hitches`.
- Which URP checkbox forces an intermediate texture -> `unity-perf:unity-urp-settings`
  and `unity-perf:unity-render-graph-tiling`.
- Slower after a Unity upgrade -> `unity-perf:unity-upgrade-risks`.

## Diagnose first

Batching pays off only in the CPU/render-thread-bound branch (U3-001).

1. **Split the frame (Meta's test, U3-001 / U5-083).** Lock CPU/GPU levels
   (commands: `quest-perf:quest-profiling-toolkit`). Disable the rendering
   camera: if frame time barely moves, you are CPU-bound. Note that disabling
   the camera also removes culling cost. Then set
   `XRSettings.eyeTextureResolutionScale` to about 0.01: if GPU time does not
   move you are vertex/geometry-bound, if it drops you are fragment-bound.
2. **Confirm it is the render thread.**
   - Perfetto (MQDH): `UnityGfx` or `UnityMain` slices run past the budget with
     no `FenceChecker::Wait` or `GPU completion` waits = CPU-bound (Q1-052).
   - Unity Profiler (Development Build, device): `Gfx.WaitForPresentOnGfxThread`
     inside `Camera.Render` = render-thread-bound; inside `Gfx.PresentFrame` =
     GPU-bound (U5-082). Disable Multithreaded Rendering while debugging so the
     full render cost is visible (U5-083) - never ship it off
     (`unity-perf:unity-cpu-scripting`).
   - Profiler/Perfetto capture setup: `unity-perf:unity-profiling-workflow`.
3. **Count the right thing (U3-002).** Rendering Statistics window and the
   Profiler Rendering module: **SetPass calls** is what the SRP Batcher moves;
   **draw calls / batches** is what instancing, static batching, BRG and GRD
   move. Record both. 6.4+ Rendering Statistics also shows SRP Batcher counts;
   6.6 adds GRD telemetry in the Profiler (U1-021).
4. **Read batch-break reasons in the Editor Frame Debugger.** The Frame Debugger
   is not supported on Meta devices, only the mock HMD (X-C2, U1-058). Break
   reasons are CPU-side and largely device-independent, so use it in the Editor.
   SRP-batched work shows as `RenderLoopNewBatcher.Draw`, each break shows its
   reason (U3-011); GRD work shows as "Hybrid Batch Group" (U3-035).
5. **Check the stereo path on device.** RenderDoc Meta Fork capture: the base
   pass must issue one draw per object and write straight into the XR eye
   texture array ("XR Texture [#]" / RTTextureArray), not `_CameraColorTexture`
   (U3-042, U3-049). Log the path at startup with the `BatchingPathReport`
   component in section 4 of [references/batching-code.md](references/batching-code.md)
   (Development Build; read with `adb logcat -s Unity`).

`XRSettings.stereoRenderingMode` under OpenXR may not reflect the plug-in's
Render Mode [verify on device]; the RenderDoc draw count is the ground truth.

## Key numbers

| Number | Applies to | Source |
|---|---|---|
| Multi-pass takes roughly 2× the CPU time to process draw calls vs Multi-View; multiview issues half the draw calls | all Quest; OpenXR (Vulkan) and Oculus XR (GLES/Vulkan; deprecated from 6.5) | U3-040, U3-041 [doc]; G2-055 |
| Multiview GPU saving: small or nil; budget vertex shading at ~2× [verify on device] | Quest 2, Quest 3/3S | G2-051 [measured, UUM-149765], conflict G2-C10 |
| Intermediate color target + final blit: fixed 1-1.5 ms GPU, and it forfeits FFR and MSAA benefits | all Quest, all Unity | U3-049 [doc] |
| Relative per-draw CPU: material switch +64%, shader switch +175%, same-object redraw ~25% | Quest 1, 2018.1, GLES - stale; keep only the ordering | U3-004 [measured] |
| SRP Batcher 1.2×-4× CPU rendering | Unity 2019, PC/PS4 - not Quest | U3-014 [measured] |
| Classic instanced array default: 250 (mobile Vulkan) / 500. Not the Quest cap: `UNITY_INSTANCING_SUPPORT_FLEXIBLE_ARRAY_SIZE` is defined for GLES3 and Vulkan and takes precedence (CB sized per batch; `maxcount:N` ignored, only `UNITY_FORCE_MAX_INSTANCE_COUNT` overrides). No published number for Quest; read instances per draw in the Frame Debugger [verify on device] | URP, classic instancing (not BRG); the 250/500 default does not apply on Quest's GLES3/Vulkan shader APIs | U3-025 [doc] + its spot-check |
| Static batch: ≤ 64,000 vertices per combined buffer | all versions | U3-019 [doc] |
| Dynamic batching: ≤ 300 vertices, ≤ 900 attributes; obsolete in 6.6 | 6.0-6.5; 6.6+ | UNITY-GF1-001, U1-022 [doc] |
| GRD: ≤ 128 materials; GLES unsupported | 6.0+, Vulkan only on Quest | U3-032, U1-095 [doc] |
| Each enabled camera: up to 1 ms CPU | generic low-end mobile, not Quest | UNITY-GF1-012 [doc] [verify on device] |
| Draw-call budgets | Quest 2 vs 3/3S | owned by `quest-perf:quest-budgets-tiers`; several Meta figures, none a limit |

No published Quest number exists for SRP Batcher on vs off, GRD CPU saving or
GPU cost, GPU occlusion cost, BRG UBO vs SSBO cost, or Multiview Render Regions.
Measure with the A/B in **Verify**.

## Fixes, ranked by payoff ÷ effort

### 1. Make sure multiview is on (never ship Multi-Pass)
- **Change:** OpenXR: Project Settings > XR Plug-in Management > OpenXR >
  Render Mode = Multi-view (Q4-061). Oculus XR (GLES path, deprecated from 6.5):
  XR Plug-in Management > Oculus > Android > Stereo Rendering Mode = Multiview
  (G2-053). If a custom shader shows only the left eye, fix the shader with the
  SPI macros (see the template in fix 3; details in
  `unity-perf:unity-shader-authoring`); check with the built-in
  `XR/StereoEyeIndexColor` shader (left green, right red) (U3-044).
- **Effect:** about half the render-thread draw submission (U3-040/041). Average
  CPU frame time down; GPU roughly unchanged (G2-C10).
- **Cost/side effects:** none in quality. Unity silently falls back to
  multi-pass when single-pass is unsupported (U3-042): verify in RenderDoc.
- **Tags:** `Quest 2` `Quest 3/3S` `all Unity in range` `GLES` `Vulkan` - Throughput.

### 2. Remove the intermediate texture and final blit
- **Change:** in RenderDoc, confirm the opaque pass targets the eye texture
  array. If it targets `_CameraColorTexture`, find what forces the intermediate
  (post-processing, Opaque Texture, Full Screen Pass with `fetchColorBuffer`,
  camera stacking; list and settings in `unity-perf:unity-render-graph-tiling`
  and `unity-perf:unity-urp-settings`) and remove it.
- **Effect:** GPU frame time down about 1-1.5 ms fixed (U3-049); also restores
  FFR and MSAA benefits (`quest-perf:quest-resolution-foveation`). Average
  GPU ms down; no variance change expected.
- **Cost:** losing whichever effect forced the intermediate.
- **Tags:** `Quest 2` `Quest 3/3S` `all Unity` `GLES` `Vulkan` - Throughput (GPU).

### 3. Keep the SRP Batcher on and every shader compatible
- **Change:** URP Asset > Rendering > SRP Batcher on (advanced property; the
  default) (U3-012, U2-016). Compatibility needs a MeshRenderer or
  SkinnedMeshRenderer, built-ins in one `UnityPerDraw` CBUFFER (URP's
  includes do this), every material property in one `UnityPerMaterial`
  CBUFFER, and no MaterialPropertyBlock (U3-010). The shader Inspector shows
  "SRP Batcher: compatible". Hand-written HLSL usually breaks it by leaving one
  property (often a `_ST` vector) outside `UnityPerMaterial`. Paste-ready
  SRP-Batcher-compatible, SPI-safe template (URP 12-17): section 1 of
  [references/batching-code.md](references/batching-code.md).
- **Replace MaterialPropertyBlocks.** An MPB breaks both SRP Batcher and GRD
  compatibility (U3-015). Unity recommends Material Variants or separate
  materials. For a runtime replacement with a bounded shared-material cache
  (always `renderer.sharedMaterial`, never `renderer.material`, UNITY-GF1-010),
  read section 2 of [references/batching-code.md](references/batching-code.md).
- **Effect:** fewer SetPass calls, lower render-thread time; draw count may not
  change (U3-009). Average render-thread ms down; no variance change expected.
- **Cost:** more material assets. Unity warns that a project whose shaders are
  not SRP-Batcher-optimized can run faster with it off on low-end devices
  (U3-012): A/B it (Verify). On GLES the SRP Batcher is single-threaded; it is
  multithreaded only on Vulkan with Graphics Jobs on (U3-013).
- **Tags:** `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan` - Throughput.

### 4. Cut shader variants and per-object batch breakers
- **Change:** the SRP Batcher batches by shader variant, so many materials on
  one variant are cheap and many variants are not (U3-009). Consolidate to a
  small set of uber shaders (Meta, U3-007), but weigh the extra keywords and
  PSOs (`unity-perf:unity-shader-hitches`). In the Frame Debugger, fix
  per-object breakers: give neighbouring objects the same reflection probe,
  lightmap index and light probes (Meta's 12 cubes went from 4 draws to 1 by
  sharing a probe, U3-008).
- **Effect:** fewer SetPass calls and batches; average render-thread ms down.
  **Cost:** art constraints on
  probe placement; uber shaders cost variants.
- **Tags:** `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan` - Throughput.

### 5. Choose static batching or GRD per API and version (U3-C1)
- **GLES, 2021.3/2022.3, or GRD lost its A/B:** keep Player > Other Settings >
  Static Batching on and mark props Batching Static. Limits: MeshRenderer
  only, ≤ 64,000 vertices per buffer, geometry duplicated in memory (U3-019).
  Keep each batch spatially compact: long, thin outliers inflate the bounds and
  keep the whole batch alive (U3-022). Culling splits a batch into several
  draws, so draw count and render-thread time vary with head direction (U3-020):
  check the draw-count spread over a head-turn capture, not only the mean.
  Runtime-built content: `StaticBatchingUtility.Combine(root)` needs Read/Write
  meshes; `Mesh.UploadMeshData(true)` drops the CPU copy after (U3-019).
- **Vulkan on Unity 6 with GRD:** turn Static Batching off, because
  static-batched renderers never reach GRD (U3-018, U3-035).
- **Tags:** `Quest 2` `Quest 3/3S` `all Unity` `GLES` `Vulkan` - Throughput, and
  Consistency for the compact-batch layout (tighter p95 render-thread time).

### 6. GPU Resident Drawer (A/B on device before committing)
- **Change (6.0+, Vulkan):** Project Settings > Graphics > Shader Stripping >
  BatchRendererGroup Variants = Keep All; SRP Batcher on; URP Asset > GPU
  Resident Drawer = Instanced Drawing; Universal Renderer > Rendering Path =
  Forward+ (X-C9: Deferred+ is also allowed from 6.1, but use Forward+ on
  Quest); Enlighten realtime GI off; Static Batching off; Lighting > Fixed
  Lightmap Size on, Use Mipmap Limits off (U3-032, U3-033, U3-035, U4-044).
  Renderers with MPBs, non-default sorting, Anchor Override, proxy volumes, a
  TextMesh or `OnWillRenderObject`/`OnBecameVisible`/`OnBecameInvisible`
  silently fall back (U3-032). Before the A/B, run the editor audit in section 3
  of [references/batching-code.md](references/batching-code.md) (lists MPBs, GRD
  disqualifiers, Batching Static flags and instancing checkboxes).
- **Version floor:** before 6000.0.65f1 / 6000.3.3f1, BRG/GRD objects may not
  render at all on 16 KiB constant-buffer Android devices (UUM-102083, U1-015)
  [verify on device].
- **Effect:** lower CPU draw submission. Unity says GRD "slightly increases GPU
  work" and lower-end mobile and VR feel it more; a GPU-bound app can get
  slower overall (U3-034). No Quest measurement exists (U3-C3); PC and Android
  XR data point both ways (U3-039 [community], U3-098 [measured]).
- **Cost:** longer builds (all BRG variants compiled) and a larger PSO warmup
  set (U3-033); no animated LOD cross-fade; `Light.shadowMatrixOverride`
  ignored for caster culling. Do not add depth priming for GRD overdraw: that
  advice is scoped to non-tiled GPUs; the XR page says keep depth priming off
  on tile GPUs (U3-C2). Keep All BRG variants add to the PSO warmup set: risk
  of first-use hitches (Consistency, see `unity-perf:unity-shader-hitches`).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 6000.0` `URP 17+` `Vulkan` - Throughput (CPU).

### 7. GPU occlusion culling (only after GRD wins, and only with real occlusion)
- **Change:** Universal Renderer > GPU Occlusion on. Requires GRD, Render Graph
  (Compatibility Mode off) and Vulkan; single-pass XR is supported from
  6000.0.0b12 (U3-037, U3-038).
- **Effect:** skips occluded instances; it tests bounding spheres against a depth
  pyramid from current and previous frames. It adds a depth-pyramid pass on a
  tile GPU, and Unity warns total time can rise when the scene has little
  occlusion; thin or elongated objects occlude poorly (U3-037).
- **Cost:** no image-quality change; adds a depth-pyramid GPU pass. Effect on
  variance: no published data; watch p95 GPU ms in both test scenes.
- **Version trap:** on 6000.5.0-6000.5.7 it culled nothing while still costing
  GPU time (UUM-146214, fixed 6000.5.8f1 / 6000.6.0f1, U1-020).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 6000.0` `Vulkan` - Throughput; A/B in
  an open scene and an interior scene [verify on device].

### 8. Classic GPU instancing for one hot mesh (when draw count, not SetPass, is the limit)
- **Change:** URP instances a custom shader only when the SRP Batcher is off or
  the shader is SRP-Batcher-incompatible; to force it for one shader, make it
  deliberately incompatible (a property outside `UnityPerMaterial`) (U3-016).
  Per-draw cap: U3-025 gives 250 (mobile Vulkan) / 500 as the array default,
  but the same file defines `UNITY_INSTANCING_SUPPORT_FLEXIBLE_ARRAY_SIZE` for
  GLES3 and Vulkan, which takes precedence: the instancing constant buffer is
  sized per batch, and `maxcount:N` has no effect there (only
  `UNITY_FORCE_MAX_INSTANCE_COUNT` overrides). No published number for Quest;
  read instances per draw in the Frame Debugger [verify on device]. On
  Unity 6 + Vulkan, GRD does this automatically.
- **Effect:** average render-thread ms down; GPU unchanged. CPU submission only;
  every instance is still vertex-transformed (U3-023). Use LODs and occlusion for dense foliage.
- **Cost:** the per-material instancing checkbox adds variants (U3-017).
- **Tags:** `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan` - Throughput (CPU).

### 9. Custom BatchRendererGroup (advanced)
- **Change (2022.3+ API; the 2021.3 API is experimental and gets rewritten):**
  SRP Batcher on, BRG Variants = Keep All, URP "Strip Unused Variants" off,
  "Allow 'unsafe' Code" on (U3-026, U1-013). Branch on
  `BatchRendererGroup.BufferTarget`: GLES = `ConstantBuffer` (offset aligned to
  `GetConstantBufferOffsetAlignment()`, window ≤ `GetConstantBufferMaxWindowSize()`),
  Vulkan = `RawBuffer` (offset and window 0) (U3-029). BRG does no culling:
  your `OnPerformCulling` job is render-thread cost, so Burst-compile it and
  time it separately (U3-027). Per-window instance count = window bytes ÷
  per-instance bytes (U3-030, measured on Mali, not Adreno).
- **Effect/cost:** large draw-count cuts for many instances; Keep All variants
  add PSOs to warm (consistency cost, `unity-perf:unity-shader-hitches`).
  Entities Graphics on GLES is deprecated; plan ECS on Vulkan (U3-031, U1-095).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 2022.3` `GLES` `Vulkan` - Throughput.

### 10. Turn dynamic batching off; trim cameras
- **Change:** URP Asset > Rendering > Dynamic Batching off (advanced). Unity
  says to disable it when the hardware supports GPU instancing, which every
  Quest GPU does; it is obsolete in 6.6 (UNITY-GF1-002, U1-022). Projects that
  relied on it for small meshes need the SRP Batcher, GRD or manual combining.
  Disable cameras that render nothing: each enabled camera has overhead (up to
  1 ms on low-end phones, UNITY-GF1-012 [verify on device]).
- **Effect:** average main/render-thread ms down (no Quest number; measure).
- **Cost:** small meshes need another batching path; no image-quality change.
- **Tags:** `Quest 2` `Quest 3/3S` `URP 12+` - Throughput (CPU).

Multiview Render Regions (GPU, Vulkan, 6.1+) is owned by
`quest-perf:quest-resolution-foveation`.

## Verify

- **A/B protocol:** same build, fixed camera path or recorded head pose, CPU/GPU
  levels locked, ≥ 60 s per variant (protocol choice, no published number;
  ≥ 60 s so one Store-style 60-s window is covered, QUEST-GF2-013), 10-15 min
  device cool-down between A/B captures (UNITY-GF1-008; not a replacement for
  the soak). Toggle one
  variable at a time; the SRP Batcher can be flipped at runtime with
  `GraphicsSettings.useScriptableRenderPipelineBatching` (U3-012).
- **Metrics that should move:** render-thread ms (Profiler / Perfetto
  `UnityGfx`), SetPass calls (SRP Batcher, variant cuts), draw calls/batches
  (static batching, instancing, BRG, GRD), and app GPU ms in OVR Metrics Tool
  (must not rise; GRD and GPU occlusion can raise it, U3-034, U3-037).
- **Expected size:** multiview vs multi-pass: draw-submission CPU roughly halves
  (U3-041). Removing the intermediate + blit: about 1-1.5 ms GPU (U3-049).
  Everything else has no published Quest number; the A/B delta is the answer.
- **Consistency check:** compare p95/p99 render-thread time and draw-count
  spread over a 360° head turn before and after static-batch changes (U3-020).
- **Session length:** ≥ 60 s per A/B variant (protocol choice above). If the change lowers CPU level demand, confirm in a 20-30 minute soak that
  levels stay lower (`quest-perf:quest-levels-thermal`).

## Pitfalls and myths

- **"Draw calls must be under N."** Meta publishes several figures and says none
  is a hard limit; measure render-thread time first (`quest-perf:quest-budgets-tiers`).
- **"The SRP Batcher reduces draw calls."** It reduces state changes; draw count
  can stay the same (U3-009). Track SetPass and draws separately.
- **"Enable dynamic batching for small meshes."** Its CPU cost can exceed the
  saving; obsolete in 6.6 (UNITY-GF1-001, U1-022).
- **"GPU instancing reduces vertex cost."** CPU only (U3-023).
- **"Just turn on GRD."** Vulkan only, silent per-renderer fallback (MPBs are
  common in 2021/2022-era Quest content, U1-017), static batching hides objects
  from it, and it adds GPU work on a platform that is usually GPU-bound (U3-034).
- **"Use depth priming to curb GRD overdraw."** Scoped to non-tiled GPUs; keep it
  off on Quest (U3-C2).
- **"Switch to Multi-Pass to fix a one-eye shader."** About 2× CPU; fix the SPI
  macros instead (U3-044, U3-041).
- **"Multiview halves GPU cost."** Sources disagree (G2-C10). Unity's manual:
  single-pass instanced "slightly decreases GPU usage". UUM-149765: no GPU-time
  difference on Quest 2/3/3S. OVR_multiview spec: GPU work may be duplicated
  per view. Treat the win as CPU-side and budget vertex shading at ~2×
  [verify on device].
- **Doubling instance counts under multiview.** `SetInstanceMultiplier` applies
  only on the SPI fallback path; on multiview, instanced and indirect draws keep
  their counts (U3-043, U3-045) [verify on device]. Check with
  StereoEyeIndexColor first.
- **Frame Debugger on the headset.** Not supported; use the Editor for batch
  breaks and RenderDoc Meta Fork for device captures (X-C2).
- **`renderer.material` in scripts.** Creates a per-renderer copy and breaks
  batching; use `sharedMaterial` (UNITY-GF1-010).
- **Quoting the 2018 "+175% shader switch" as Quest data.** Quest 1, GLES,
  pre-SRP Batcher; only the ordering holds (U3-004).
- **Profiling GLES multiview in a development build** with OculusXR 4.4.0 on
  6000.0.33f1: GL error spam causes FPS drops (G2-057 [community]); details in
  `gles3-perf:gles-extensions-multiview`.

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ [doc] (U3-001, U5-083)
- https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ [measured] (U3-004)
- https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-1/ [doc] (U3-008, U3-023, U3-049)
- https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-2/ [doc] (U3-007, U3-022)
- https://developers.meta.com/horizon/documentation/unity/enable-multiview/ [doc] (U3-040, G2-050)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc] (U3-041, Q4-061)
- https://developers.meta.com/horizon/resources/device-optimization-comparison/ [doc] (U3-021)
- https://github.com/meta-quest/agentic-tools [doc] (Q1-052, Meta-published agent skill)
- https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html [doc] (U3-002, U3-013, U3-015, U3-017, U3-018)
- https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher.html [doc] (U3-009)
- https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Materials.html [doc] (U3-010)
- https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Profile.html [doc] (U3-011)
- https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Enable.html [doc] (U3-012)
- https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Incompatible.html [doc] (U3-016)
- https://docs.unity3d.com/6000.6/Documentation/Manual/GPUInstancing.html [doc] (U3-016)
- https://unity.com/blog/engine-platform/srp-batcher-speed-up-your-rendering [measured] (U3-014)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html [doc] (U2-016)
- https://docs.unity3d.com/2022.3/Documentation/Manual/static-batching.html [doc] (U3-019)
- https://docs.unity3d.com/6000.6/Documentation/Manual/static-batching-enable.html [doc] (U3-020)
- https://docs.unity3d.com/6000.0/Documentation/Manual/DrawCallBatching.html [doc] (UNITY-GF1-001)
- https://docs.unity3d.com/6000.0/Documentation/Manual/urp/universalrp-asset.html [doc] (UNITY-GF1-002)
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/UnityInstancing.hlsl [doc] (U3-025, U3-028)
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/UnityInput.hlsl [doc] (U3-046)
- https://docs.unity3d.com/6000.0/Documentation/Manual/optimizing-draw-calls-choose-method.html [doc] (UNITY-GF1-002)
- https://docs.unity3d.com/6000.0/Documentation/Manual/urp/gpu-resident-drawer.html [doc] (U1-016)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html [doc] (G2-055)
- https://developers.meta.com/horizon/resources/publish-performance-analytics/ [doc] (QUEST-GF2-013)
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html [doc] (U3-024)
- https://docs.unity3d.com/6000.6/Documentation/Manual/batch-renderer-group-getting-started.html [doc] (U3-026)
- https://docs.unity3d.com/2022.3/Documentation/Manual/batch-renderer-group.html [doc] (U1-012, U1-013)
- https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Rendering.BatchRendererGroup.BufferTarget.html [doc] (U1-014)
- https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.BatchRendererGroup.AddBatch.html [doc] (U3-029)
- https://docs.unity3d.com/6000.6/Documentation/Manual/batch-renderer-group-how.html [doc] (U3-027)
- https://unity.com/blog/engine-platform/batchrenderergroup-sample-high-frame-rate-on-budget-devices [measured] (U3-030)
- https://docs.unity3d.com/Packages/com.unity.entities.graphics@6.5/manual/requirements-and-compatibility.html [doc] (U3-031)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html [doc] (U3-032, U1-016, U1-017)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/gpu-resident-drawer.html [doc] (U4-044, X-C9)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/make-object-compatible-gpu-rendering.html [doc] (U3-033)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html [doc] (U3-034, U3-035, U3-036)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc] (U3-C2, U1-095)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-culling.html [doc] (U3-037, U1-019)
- https://unity.com/releases/editor/whats-new/6000.0.0 [doc] (U3-038)
- https://developer.android.com/develop/xr/unity/performance/gpu-rendering [doc] (U3-038)
- https://discussions.unity.com/t/resident-drawer-performance/1554861 [community] (U3-039)
- https://android-developers.googleblog.com/2025/10/optimizing-performance-for-android-xr.html [measured] (U3-098)
- https://unity.com/releases/editor/whats-new/6000.0.65f1 [doc] (U1-015)
- https://unity.com/releases/editor/whats-new/6000.5.8f1 [doc] (U1-020)
- https://unity.com/releases/editor/whats-new/6000.6.0f1 [doc] (U1-020)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity64.html [doc] (U1-021)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc] (U1-021)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc] (U1-022)
- https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassStereoRendering.html [doc] (U3-042)
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/Runtime/XR/XRPass.cs [doc] (U3-043)
- https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassInstancing.html [doc] (U3-044, U3-045)
- https://docs.unity3d.com/6000.3/Documentation/Manual/SinglePassStereoRendering.html [doc] (G2-053)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html [doc] (G2-053)
- https://docs.unity3d.com/6000.6/Documentation/Manual/Android-SinglePassStereoRendering.html [doc] (GLES3-GF2-004)
- https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview.txt [doc] (G2-051)
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [measured] (G2-051, G2-C10)
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102876 [community] (G2-057)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html [doc] (U1-058, X-C2)
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html [doc] (U5-082)
- https://cdn.bfldr.com/S5BC9Y64/at/3mp8w3wk36k2k6mmj5pbbr/Optimize_your_game_performance_for_mobile__XR__and_the_web_in_Unity_Unity_6_edition_e-book.pdf [doc] (UNITY-GF1-010, UNITY-GF1-012, UNITY-GF1-008)
