---
name: unity-memory-assets
description: "Asset memory and loading cost for Unity on Quest 2/3/3S: texture compression (ASTC block sizes), mipmaps and mip streaming, mesh compression and vertex formats, Async Upload Pipeline, asset-loading and scene-streaming hitches, Addressables, and render-texture memory. Use to shrink texture/mesh memory, for loading stutter, or for texture bandwidth. Memory limits and lmkd kills: quest-perf:quest-budgets-tiers."
---

# Unity asset memory and loading on Quest 2 / Quest 3/3S

Goals: **Consistency** (no loading and streaming hitches, no Low Memory Kill
in long sessions) and **Throughput** (less texture and vertex fetch
bandwidth). Scope: Unity 2021.3 to 6000.x, URP 12 to 17, GLES and Vulkan,
Quest 2 (Adreno 650, 6 GB) and Quest 3 (Adreno 740, 8 GB; Quest 3S same
SoC/RAM per spec sheets [verify on device]) (U4-053).
Everything here is importer, Player, Quality or C# loading code.

Lead facts: ASTC first, then ETC2 (A2-086); Read/Write doubles texture memory
and blocks AUP (U4-054, U4-078); `backgroundLoadingPriority` High (50 ms/frame)
only behind a cover, Low (2 ms) for gameplay streaming (U4-083); Meta publishes
no texture-memory budget beyond the app PSS limit (Q2-037).

## When to use / when not

Use when:
- A hitch lines up with a scene load, additive stream, Addressables load or
  release, or `Resources.UnloadUnusedAssets`.
- PSS or `app_gpu_*_MB` is high or climbs across scene transitions, or you
  need a Quest 2 texture tier.
- Counters show texture or vertex fetch stalls and you want to change
  formats, block sizes, mips or vertex layouts.
- Auditing texture/model importer, Vertex Compression, AUP, mip streaming or
  AssetBundle settings.

Do not use for:
- PSS limit per headset, lmkd, RAM table, memory budgets, device tiers ->
  `quest-perf:quest-budgets-tiers`. Unknown bottleneck -> `quest-perf:quest-triage`.
- First-render spike (PSO / shader compile), variant stripping, warmup ->
  `unity-perf:unity-shader-hitches`.
- DRAM bytes and power -> `arm-mobile-hw-perf:xr2-bandwidth-power`; binning and
  vertex re-shading -> `arm-mobile-hw-perf:xr2-adreno-architecture`; filtering
  cost model -> `arm-mobile-hw-perf:xr2-shader-cost-model`.
- Lightmap/probe formats -> `unity-perf:unity-lighting`; GC and pooling ->
  `unity-perf:unity-cpu-scripting`; memoryless / transient RTs ->
  `unity-perf:unity-render-graph-tiling`; HDR, Opaque/Depth Texture, MSAA ->
  `unity-perf:unity-urp-settings`.
- Optimize Buffer Discards, Offscreen Rendering Only ->
  `quest-perf:quest-sdk-choices`; AppSW memory -> `quest-perf:quest-appsw`; CPU
  Boost during loads -> `quest-perf:quest-levels-thermal`; running OVR Metrics,
  gpumeminfo, ovrgpuprofiler -> `quest-perf:quest-profiling-toolkit`.

## Diagnose first

Pick the row that matches the symptom; do not change assets before one
capture confirms it.

| Symptom | Capture that confirms it | Owner if it does not confirm |
|---|---|---|
| Hitch during load or stream | Development build + Profiler on device: `Application.Integrate Assets in Background`, `Resources.UnloadUnusedAssets`, AUP markers `AsyncUploadManager.ScheduleAsyncRead` / `AsyncReadManager.ReadFile` (U4-082, U4-083) | Spike on first render with PSO markers -> `unity-perf:unity-shader-hitches` |
| Memory grows per transition | PSS sampled after each transition, same scene (Q2-043) | Managed heap growth -> `unity-perf:unity-cpu-scripting` |
| LMK crash reports | logcat `lowmemorykiller` (Q2-042) | Limits -> `quest-perf:quest-budgets-tiers` |
| Texture bandwidth | `% Texture Fetch Stall`, `% Texture L1 Miss`, `Texture Memory Read BW` (Q1-062 draw-call metrics; realtime: `% Texture Fetch Stall`/`% Texture L1 Miss` via Q1-065/066) | Shader ALU -> `unity-perf:unity-shader-authoring` |
| Vertex fetch / binning | `% Vertex Fetch Stall`, `Vertex Memory Read`, `Avg Bytes/Vertex` (Q1-062) | Triangle budget -> `quest-perf:quest-budgets-tiers` |

Commands (PowerShell or bash; replace the package name):

```sh
# Totals, release or development build (Q2-043, U4-065)
adb shell dumpsys meminfo com.company.app
# Per-process GPU memory (Q1-095); single quotes so pidof runs on the device
adb shell 'gpumeminfo -p $(pidof com.company.app)'
# OVR Metrics CSV columns to log: app_pss_MB, app_gpu_physical_MB,
#   app_gpu_allocated_percentage, stale_frame_count, percent_texture_fetch_stall,
#   percent_texture_l1_miss, percent_vertex_fetch_stall (quest.md Q1-012)
# Realtime GPU counters: list IDs on THIS device first; they are positions (Q1-065)
adb shell ovrgpuprofiler -m
adb shell ovrgpuprofiler -r"4,6,8"   # IDs from Meta's example list (Texture Fetch Stall,
                                     # L1 Miss, Stalled on System Memory); re-check with -m
adb logcat -s lowmemorykiller
```

Per-object texture and mesh sizes: Profiler Memory module and the Memory Profiler package,
Development build only. Texture Memory, Mesh Memory and Gfx counters are absent in release players;
System Used Memory is available through `ProfilerRecorder` (U4-064, U4-065, U4-067). No Meta page
maps Unity's Gfx numbers onto `dumpsys meminfo` graphics rows; cross-check both (U4-067).

For a long-session in-app log (System Used Memory via `ProfilerRecorder`, plus mip-streaming
totals), use the probe in [references/loading.md section 8](references/loading.md).

## Key numbers

| Number | Value | Source | Applies to |
|---|---|---|---|
| App PSS limit | Quest 2 4.4 GiB; Quest 3/3S 5.75 GiB (owned by `quest-perf:quest-budgets-tiers`) | Q2-041 [doc] | `Quest 2` `Quest 3/3S` |
| Texture-memory budget | none published beyond PSS; eye buffers and RTs count against PSS | Q2-037 [doc] | all |
| ASTC bitrate | 4x4 8 bpp; 5x5 5.12; 6x6 3.56; 8x8 2; 10x10 1.28; 12x12 0.89 | U4-049 [doc] | `Unity 2021.3-6000.x` |
| Importer quality -> block (Android) | High 4x4; Normal 6x6; Low 8x8 | U4-048 [doc] | `Unity 2021.3-6000.x` |
| Uncompressed vs ASTC | "almost 26x" in one e-book example; illustrative, not a rule | UNITY-GF1-017 [doc] | all |
| Mip streaming defaults | budget 512 MB; renderers/frame 512; max level reduction 2; max IO 1024 | U4-059 [doc] | `Unity 2021.3-6000.x` |
| AUP ranges | time slice 1-33 ms; buffer 2-2047 MB; persistent buffer on | U4-079 [doc] | `Unity 2021.3-6000.x` |
| AUP 2018 defaults | 2 ms slice, run twice per frame on the render thread; 16 MB buffer (possibly stale) | U4-080 [doc] [verify on device] | `Unity ≥ 2018.3` |
| Integration cap | Low 2 / BelowNormal 4 (default) / Normal 10 / High 50 ms per frame | U4-083 [doc] | `Unity 2021.3-6000.x` |
| Frame budget | 72 Hz 13.9 ms; 90 Hz 11.1 ms; 120 Hz 8.3 ms | unity.md header (arithmetic) | all |
| LZ4 bundle chunk | 128 KB; LZMA decompresses the whole content section | U4-090 [doc] | `Unity 2021.3-6000.x` |
| Shader variant chunks | 16 MB compressed per chunk; count 0 = unlimited | U4-094 [doc] | `Unity 2021.3-6000.x` |
| Vertex Compression | about 1.45x smaller in Unity's example mesh | U4-068 [doc] | `Unity 2021.3-6000.x` |
| Mesh Compression High | vertices about 3.2x, normals about 7.4x, disk only | U4-069 [doc] | `Unity 2021.3-6000.x` |
| 16-bit index | meshes over 64k vertices split into chunks | U4-071 [doc] | `Unity 2021.3-6000.x` |
| A7x vertex cache | 32 four-component vertices | A2-049 [doc] | `Quest 3/3S` |
| 8x aniso on all textures | 8.9 ms of a 13.8 ms frame, non-Unity engine | Q1-075 [community][measured] | `Quest 3` |
| Optimize Buffer Discards | about 90 MB/eye at 1680x1760, 66 MB/eye at 1440x1584 (owned by `quest-perf:quest-sdk-choices`) | Q4-059 [doc] | `Vulkan` 4x MSAA |
| Offscreen Rendering Only | about 10-20 MB on Quest 3 at 2064x2208 per eye (owned by `quest-perf:quest-sdk-choices`) | U1-090 [doc] | `Quest 3` `OpenXR` `Unity 6.x` |
| AppSW memory | about 18 MB Quest 3, 14 MB Quest 2 (owned by `quest-perf:quest-appsw`) | Q3-063 [doc] | `Quest 2` `Quest 3` `Vulkan` (Q3-064) |
| Audio thresholds | < 200 KB Decompress On Load or ADPCM (3.5:1); > 350-400 KB Streaming, about 200 KB overhead/clip | UNITY-GF1-016 [doc] | all |
| Per-block GPU ms, unload sweep ms, AUP slice for Quest | no published number; measure with the Verify methods below | U4-050, U4-087, U4-080 | - |

## Fixes, ranked by payoff ÷ effort

Detail and paste-ready code live in three reference files:
- Read [references/texture-import.md](references/texture-import.md) when choosing ASTC blocks,
  setting mip limits or mip streaming, handling normal maps or ASTC HDR, or installing the texture
  `AssetPostprocessor`.
- Read [references/mesh-import.md](references/mesh-import.md) when auditing mesh importer settings,
  index formats, custom vertex layouts, Mesh LOD, or running the position-stream splitter.
- Read [references/loading.md](references/loading.md) when a hitch lines up with a load or unload,
  for AUP eligibility, Addressables churn, audio load types, the loading-screen controller C#, or
  the long-session memory probe.

### 1. Make ASTC the only path - Throughput + Consistency

- Set Player > Android > Other Settings > Texture compression formats with ASTC as the **first**
  entry (the only one used for an APK), and set File > Build Profiles (6.0+) or Build Settings >
  Android > Texture Compression to "Use Player Settings" (U4-047).
- Search for per-texture Android overrides to ETC2/RGBA32: `t:Texture2D` in the Project window, then
  sort by format in the Memory Profiler.
- Effect: removes load-time decompression (lower load hitches) and cuts texture bytes read per frame
  (average GPU time) (U4-046, A3-015).
- Cost: none for LDR. HDR sources: see the ASTC HDR conflict in Pitfalls.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` `URP 12+` `GLES` `Vulkan`.

### 2. Read/Write off on every texture and mesh - Consistency

- Texture Inspector > Advanced > Read/Write off; Model importer > Model > Read/Write off. Keep it
  only for the runtime cases in [mesh-import.md section 5](references/mesh-import.md). Runtime-built
  textures: `tex.Apply(true, makeNoLongerReadable: true)`; meshes: `mesh.UploadMeshData(true)`
  (U4-054, U4-073).
- Effect: halves those textures' memory, frees mesh CPU copies, makes them AUP-eligible (multi-frame
  upload instead of one main-thread frame), and cuts activation cost for readable meshes (U4-075,
  U4-078). Variance improves more than the average.
- Cost: code that reads pixels or vertices at runtime breaks; find it by searching for `GetPixels`,
  `.vertices`, `MeshCollider` with convex + negative scale.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` `GLES` `Vulkan`.

### 3. Load behind a cover, stream at 2 ms - Consistency

- Behind a black fade or compositor loading screen: `Application.backgroundLoadingPriority =
  ThreadPriority.High` and a larger `QualitySettings.asyncUploadTimeSlice`; during gameplay
  streaming: `ThreadPriority.Low` and restore the slice (U4-083, U4-080 notes). The controller in
  [loading.md section 7](references/loading.md) does both.
- Never hold `allowSceneActivation = false`: later loads and unloads queue behind it (U4-084).
- Author streamed scenes with heavy roots disabled; enable over several frames; pool instead of
  instantiate (U4-085).
- Effect: bounds per-frame main-thread integration to 2 ms during gameplay; stale frames during
  transitions move to covered time. Average frame time unchanged.
- Cost: slower gameplay streaming; plan prefetch distance.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` `GLES` `Vulkan`.

### 4. Keep `UnloadUnusedAssets` out of visible frames - Consistency

- Additive loads plus an explicit `Resources.UnloadUnusedAssets()` while the view is covered. A
  Single-mode `LoadSceneAsync` runs the sweep for you, at a cost that scales with live objects
  (U4-086, U4-087).
- Measure the sweep at minute 1 and minute 25: community reports say it slows over a session
  (U4-088, [community]).
- Effect: removes a one-frame main-thread sweep from visible frames, so p99 and stale frames drop
  and the average does not change.
- Cost: memory stays resident until the next covered transition; scenes loaded in Single mode during
  gameplay still sweep (U4-086).
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` `Addressables 1.21+`.

### 5. Make assets AUP-eligible - Consistency

- Textures and meshes outside `Resources`, non-readable, Android build compression LZ4, Mesh
  Compression Off; meshes without blend shapes or bone weights (U4-078). Checklist: [loading.md
  section 1](references/loading.md).
- Size Async Upload Buffer Size to the largest texture you load (`asyncUploadBufferSize`); resizing
  at runtime is slow (U4-079).
- Confirm with `AsyncUploadManager.ScheduleAsyncRead` / `AsyncReadManager.ReadFile` markers
  (U4-082).
- Effect: one-frame main-thread uploads become time-sliced render-thread work.
- Cost: skinned characters stay on the sync path; load them covered.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` `GLES` `Vulkan`.

### 6. Quest 2 texture tier via mip limits - Consistency (memory)

- Quality level for Quest 2: Global Mipmap Limit 1 (Half), or Mipmap Limit Groups per content class
  (2022.2+); pick the level with `SystemHeadset` detection (`quest-perf:quest-budgets-tiers`). Turn
  on Player > Texture Mipmap Stripping to drop levels no quality level uses (U4-057, U4-058).
- Meta: ASTC on both headsets; lower resolution or fewer mips on Quest 2 (U4-053).
- Unity 6.0: limits no longer apply to runtime-created textures by default (U1-089); set
  `ignoreMipmapLimit` deliberately.
- Effect: a one-level drop quarters the top-mip footprint of affected textures (arithmetic). Also
  fewer bytes per frame.
- Cost: blur on close-up surfaces; exempt hero textures and UI.
- Tags: `Quest 2` `Unity ≥ 2022.2` (groups) `Unity 2021.3` (`masterTextureLimit`).

### 7. ASTC block size by screen coverage - Throughput + memory

- Start 5x5 or 6x6; go to 8x8 or larger for assets small on screen; 4x4 only for text, faces and
  hero props (U4-050). Enforce with the `AssetPostprocessor` in [texture-import.md section
  8](references/texture-import.md) (UNITY-GF1-017).
- Effect: 6x6 is 44.5% of 4x4 bytes (3.56 ÷ 8, U4-049); lower texture read bandwidth. No published
  GPU-ms per block size (U4-050 notes).
- Cost: block artefacts on gradients and normal maps; review in headset.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` `GLES` `Vulkan`.

### 8. Mesh import settings - Throughput + memory

- Player > Vertex Compression: keep defaults (Normal, Tangent, UV0/2/3 as FP16). Player > Optimize
  Mesh Data on. Model importer: Mesh Compression Off, Index Format 16-bit where vertex count allows,
  Optimize Mesh Everything, Weld Vertices on (U4-068 to U4-071).
- Effect: smaller vertex buffers and fewer bytes per vertex fetched in both the binning and render
  passes (A2-046, A3-018).
- Cost: Optimize Mesh Data breaks runtime material swaps to shaders needing stripped channels
  (U4-070). Skinned meshes get none of the FP16 savings (U4-072).
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` `GLES` `Vulkan`.

### 9. Mipmap streaming for large texture sets - Consistency (memory)

- Quality > Mipmap Streaming on; set Memory Budget from measured `Texture.desiredTextureMemory` at
  the heaviest view (the budget also counts non-streamed textures); per texture Stream Mipmap Levels
  on (U4-059 to U4-061). Runtime meshes: `mesh.RecalculateUVDistributionMetrics()` (U4-062).
- Effect: lower peak texture memory; upload work spread over frames.
- Cost: how it picks mips for stereo cameras is undocumented (U4-063); a budget that is too small
  shows blur while turning. Not supported for terrain, texture arrays, cubemap arrays, 3D textures
  (U4-060).
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` [verify on device].

### 10. Addressables grouped by lifetime, LZ4 bundles - Consistency (memory)

- One bundle per lifetime (level, session, always), so a release actually frees memory; watch churn
  in the Addressables Profiler module (U4-089).
- Bundle compression LZ4, not the LZMA default (U4-090).
- Effect: memory actually drops when a bundle unloads, and the load/unload churn stops (U4-089).
- Cost: more bundles and more build-layout work; LZ4 bundles are larger on disk than LZMA (U4-090).
- Tags: `Quest 2` `Quest 3/3S` `Addressables 1.21-2.x` `GLES` `Vulkan`.

### 11. Anisotropic filtering Per Texture - Throughput

- Quality > Anisotropic Textures = Per Texture; Aniso Level above 1 only on floors and grazing-angle
  surfaces (U4-056, U4-C4).
- Effect: average GPU time; one non-Unity measurement put 8x-everywhere at 8.9 ms of 13.8 ms on
  Quest 3 (Q1-075, [community]).
- Cost: blurrier floors and other grazing-angle surfaces wherever Aniso Level is left at 1.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` [verify on device].

### 12. Position-only vertex stream - Throughput

- Split static meshes into stream 0 = FP32 position, stream 1 = packed attributes, with the Editor
  tool in [mesh-import.md section 4](references/mesh-import.md) (A2-048, A3-018).
- Effect: fewer bytes in the position-only binning shader. No published Quest ms; vertex-heavy
  scenes only.
- Cost: a copy asset per mesh; static batching behaviour unverified.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` `GLES` `Vulkan` [verify on device].

### 13. Render-texture memory you own - Consistency (memory)

- Custom RTs: allocate once, reuse; in URP 14-16 use `RTHandle` with
  `RenderingUtils.ReAllocateIfNeeded` (U1-099) `URP 14-16` (on URP 17 non-Render-Graph compatibility
  paths the API was renamed `ReAllocateHandleIfNeeded` [verify in Editor]). In Unity 6 Render Graph,
  use transient textures so the compiler can make them memoryless
  (`unity-perf:unity-render-graph-tiling`, U2-061).
- Eye buffers and RTs count against PSS (Q2-037). The 4x MSAA eye attachments alone are about 90 MB
  per eye on Quest 3 when not lazily allocated: Optimize Buffer Discards (Q4-059,
  `quest-perf:quest-sdk-choices`).
- Unity 6.0 LTS: Vulkan command-buffer memory with Graphics Jobs is higher than 6000.2.12f1+ / 6.3
  (UUM-121520, no MB figure) (U1-087).
- Tags: `Quest 2` `Quest 3/3S` `URP 14-16` (RTHandle) `Vulkan` (Render Graph: `Unity ≥ 6000.0` `URP
  17`).

### 14. Audio load types - Consistency (memory)

- Apply the table in [loading.md section 6](references/loading.md): Streaming for long clips, ADPCM
  or Decompress On Load for short ones, Force To Mono for positional sounds (UNITY-GF1-016).
- Effect: lower resident audio memory and no decode spikes when clips load; no published Quest
  number (UNITY-GF1-016).
- Cost: Streaming costs about 200 KB overhead per clip, and ADPCM gives up some quality.
- Tags: `Quest 2` `Quest 3/3S` all Unity versions.

### 15. Shader memory at load - Consistency

- Leave Shader Variant Loading chunk count at 0 unless memory forces it; capping it can
  re-decompress chunks at runtime (U4-094). "Keep Loaded Shaders Alive" trades memory for no
  re-creation (U4-095). Warmup: `unity-perf:unity-shader-hitches`.
- Effect: chunk count 0 avoids runtime re-decompression hitches, which is a Consistency gain.
- Cost: more resident shader memory.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.x` `GLES` `Vulkan`.

## Verify

Run each A/B on the same build config, same scripted route, CPU/GPU levels pinned
(`quest-perf:quest-profiling-toolkit`), for 20-30 minutes including at least the scene transitions a
real session has.

- Memory: `app_pss_MB` (OVR Metrics) or `dumpsys meminfo` after each transition should return to the
  same plateau; a staircase is a leak or bundle kept alive. Peak PSS with background apps running
  (Q2-042) must sit under the device limit; Meta publishes no safety margin. Fixes 2, 6, 7, 9, 10
  should lower the plateau by the texture/mesh bytes the Memory Profiler attributes to the changed
  assets.
- Loading hitches: `stale_frame_count` during uncovered streaming should fall toward zero;
  `Application.Integrate Assets in Background` should stay at or under the priority cap (2 ms at
  Low) per frame; no single frame with `Resources.UnloadUnusedAssets` outside covered time.
- Bandwidth: `percent_texture_fetch_stall`, `Texture Memory Read BW` and `app_gpu_time_microseconds`
  should drop after fixes 1, 7, 11; vertex fixes 8 and 12 should lower `Vertex Memory Read` / `%
  Vertex Fetch Stall`. No published expected size: report the measured delta.
- Consistency over time: compare the first and last 5 minutes of the run; PSS and unload-sweep time
  should not trend upward (U4-088).

## Pitfalls and myths

- "Texture memory is nearly free" is from a legacy Meta page; current Meta guidance says cut texture
  resolution or mips on Quest 2 (U4-C8, Q2-035).
- "Load synchronously behind a fade" is pre-AUP legacy advice (U4-092); resolved in favour of
  covered async loads (U4-C1).
- "Disable anisotropic filtering" (Meta 2018) was a Mali/Exynos reason; on Adreno, use Per Texture
  and measure (U4-C4).
- Mesh Compression is disk-only: no runtime saving, and it disables vertex compression and AUP
  (U4-069). Unity has no 8-bit indices (A3-018).
- ASTC HDR on Quest is conflicting evidence: unity.md finds no source confirming it (U4-049,
  U4-038), while the gles3.md gpuinfo matrix lists `KHR_texture_compression_astc_ldr / _hdr` as
  present on Quest 2 and Quest 3 in one merged row ([measured]) and Qualcomm's Adreno overview says
  "HDR and LDR ASTC profiles are supported" (A2-086 [doc]). Check
  `SystemInfo.SupportsTextureFormat(TextureFormat.ASTC_HDR_6x6)` on device, and on Vulkan `adb shell
  vulkaninfo` for `textureCompressionASTC_HDR` (U4-038), before shipping HDR ASTC; without it Unity
  decompresses to RGB9E5 or RGBA Half. [verify on device]
- "ASTC stays compressed in L2" is stated only for Adreno 5xx (A3-015).
- Unity 6.0 global mip limits skip runtime-created textures by default (U1-089);
  `Apply(makeNoLongerReadable: true)` freezes the uploaded resolution (U4-054).
- Texture Memory / Mesh Memory counters read nothing in release players (U4-065); do not conclude "0
  MB".
- Mesh LOD (6.2+) likely keeps the LOD0 vertex buffer resident (inference, [verify on device]);
  skinned meshes still deform LOD0; static batching always uses LOD0 (U1-059, U1-060).
- Defaults that are wrong for Quest: mip streaming 512 MB budget (U4-059); BuildPipeline LZMA
  bundles (U4-090); 2018-blog AUP values (U4-080).

## Sources

Accessed 2026-09-24. Finding IDs index `research/*.md`.

- https://docs.unity3d.com/6000.3/Documentation/Manual/android-requirements-and-compatibility.html [doc] (U4-046, U4-047)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html [doc] (U4-047, U4-051, U4-058, U4-070, U4-094, U4-095)
- https://docs.unity3d.com/2022.3/Documentation/Manual/class-TextureImporter.html [doc] (U4-048)
- https://docs.unity3d.com/6000.3/Documentation/Manual/texture-formats-reference.html ; .../texture-choose-format-by-platform.html [doc] (U4-049, U4-038)
- https://developers.meta.com/horizon/blog/top-tips-from-arm-for-vr-asset-optimization/ [doc] (U4-050)
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/ShaderLibrary/Packing.hlsl [doc] (U4-051)
- https://github.com/ARM-software/astc-encoder/blob/main/Docs/Encoding.md [doc] (U4-052)
- https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ [doc] (U4-053, U4-055, U4-091)
- https://developers.meta.com/horizon/resources/device-optimization-comparison/ [doc] (U4-053)
- https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ [doc] (legacy; U4-092, U4-C8, Q2-035)
- https://developers.meta.com/horizon/blog/tech-note-unity-settings-for-mobile-vr/ [doc] (U4-055, U4-095)
- https://docs.unity3d.com/6000.3/Documentation/Manual/texture-type-default.html [doc] (U4-054, U4-056, U4-057, U4-061)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Texture2D.Apply.html [doc] (U4-054)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-QualitySettings.html [doc] (U4-056, U4-057, U4-059)
- https://docs.unity3d.com/6000.3/Documentation/Manual/TextureStreaming.html ; .../TextureStreaming-configure.html ; .../TextureStreaming-analyze.html ; https://docs.unity3d.com/2021.3/Documentation/Manual/TextureStreaming.html [doc] (U4-060, U4-062, U4-063, U4-066)
- https://docs.unity3d.com/6000.3/Documentation/Manual/ProfilerMemory.html [doc] (U4-064, U4-067)
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-counters-reference.html ; .../profiler-memory-counters-players.html [doc] (U4-065)
- https://docs.unity3d.com/6000.3/Documentation/Manual/configure-vertex-compression.html ; .../types-of-mesh-data-compression.html ; .../configure-mesh-compression.html [doc] (U4-068, U4-069)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings-stripUnusedMeshComponents.html [doc] (U4-070)
- https://docs.unity3d.com/6000.3/Documentation/Manual/FBXImporter-Model.html [doc] (U4-071, U4-073)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.VertexAttributeDescriptor.html [doc] (U4-072)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Mesh-isReadable.html [doc] (U4-073)
- https://developers.meta.com/horizon/blog/avoiding-hitches-when-loading-scenes-in-unity/ [measured] (U4-075, U4-085; Quest 2, Unity 2020.3.8f1)
- https://docs.unity3d.com/6000.3/Documentation/Manual/LoadingTextureandMeshData.html ; .../LoadingTextureandMeshData-make-compatible.html [doc] (U4-069, U4-078, U4-079)
- https://docs.unity3d.com/2022.3/Documentation/Manual/LoadingTextureandMeshData.html [doc] (U4-082)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/QualitySettings-asyncUploadTimeSlice.html ; .../QualitySettings-asyncUploadBufferSize.html ; .../QualitySettings-asyncUploadPersistentBuffer.html [doc] (U4-079)
- https://unity.com/blog/engine-platform/understanding-the-async-upload-pipeline [doc] (U4-080, U4-081; 2018)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Application-backgroundLoadingPriority.html [doc] (U4-083)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/AsyncOperation-allowSceneActivation.html ; .../AsyncOperation-priority.html [doc] (U4-084)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SceneManagement.SceneManager.LoadSceneAsync.html ; .../Resources.UnloadUnusedAssets.html [doc] (U4-086)
- https://docs.unity3d.com/Packages/com.unity.addressables@1.21/manual/MemoryManagement.html ; https://docs.unity3d.com/Packages/com.unity.addressables@2.3/manual/MemoryManagement.html [doc] (U4-087, U4-089)
- https://discussions.unity.com/t/resources-unloadunusedassets-execution-time-slowly-increases-over-time/920692 [community] (U4-088)
- https://docs.unity3d.com/6000.3/Documentation/Manual/assetbundles-compression-format.html [doc] (U4-090)
- https://docs.unity3d.com/6000.3/Documentation/Manual/shader-memory.html [doc] (U4-094)
- https://docs.unity3d.com/6000.6/Documentation/Manual/lod/mesh-lod-introduction.html [doc] (U1-059, U1-060)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html [doc] (U1-089)
- https://unity.com/releases/editor/whats-new/6000.2.12f1 [doc] (U1-087)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc] (U1-090)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc] (Q4-059)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc] (A2-048, A2-049, A3-018, A3-015)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html [doc] (A2-049, A3-019)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html [doc] (A2-046, A2-086)
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_texture_compression_astc_decode_mode.txt [doc] (G3-063)
- https://opengles.gpuinfo.org/displayreport.php?id=8023 [measured] (gles3.md section 7.1 extension matrix)
- https://developers.meta.com/horizon/essentials/memory-ram/ [doc] (Q2-037, Q2-041)
- https://developers.meta.com/horizon/documentation/unity/po-memory-ram/ [doc] (Q2-042)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc] (Q2-043)
- https://developers.meta.com/horizon/documentation/unity/ts-gpumeminfo/ [doc] (Q1-095)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc] (Q1-065, Q1-066)
- https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ [doc] (Q1-062)
- https://github.com/tommy-xr/functor/blob/HEAD/.claude/skills/oculus-profiling/SKILL.md [community] (Q1-075)
- https://unity.com/resources/mobile-xr-web-game-performance-optimization-unity-6 [doc] (Unity 6 e-book pp. 24, 28-31, 74-75; UNITY-GF1-016, UNITY-GF1-017)
- https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ [doc] (Q3-063)
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/upgrade-guide-2022-1.html [doc] (U1-099)
- https://developers.meta.com/horizon/documentation/unity/unity-perf/ [doc] (Q2-034)
- https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/NativePassCompiler.cs [doc] (U2-061)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity62.html [doc] (U1-059)
