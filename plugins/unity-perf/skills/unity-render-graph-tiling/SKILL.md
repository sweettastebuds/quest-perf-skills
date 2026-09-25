---
name: unity-render-graph-tiling
description: "Keeping URP rendering on-tile on Adreno (Vulkan and URP-level GLES): Render Graph pass merging and pass-break reasons, memoryless attachments, load/store actions, native render passes (URP 12/14), on-tile post-processing and post-processing cost, framebuffer fetch, Render Graph Viewer on device, and custom ScriptableRendererFeature passes that break merging. Use when ovrgpuprofiler shows LoadColor or StoreDepthStencil, when a renderer feature or bloom costs milliseconds, or when writing RG passes for Quest."
---

# URP Render Graph on a tiler (Quest 2 / Quest 3/3S)

Goal: **Throughput** (remove GMEM↔DRAM loads, stores, resolves and final
blits from average GPU time); less DRAM traffic also helps sustained clocks
(→ `arm-mobile-hw-perf:xr2-bandwidth-power`). Target: **one native render pass
from the first opaque draw to the eye-texture write**, camera colour and depth
memoryless, only the resolved eye colour stored (U2-057, U2-077, A3-007).

## When to use / when not

Use when:
- `ovrgpuprofiler -t` shows `LoadColor`, `LoadDepthStencil`,
  `StoreDepthStencil` or extra eye-resolution surfaces.
- The Render Graph Viewer shows several merge bars, a "Final Blit" or a
  pass-break reason; a renderer feature or URP post costs ms on device.
- Writing a URP 17 custom pass, or choosing between Native RenderPass
  (URP 12/14), Meta's subpass fork and stock Render Graph.

Do not use for:
- Unknown bottleneck → `quest-perf:quest-triage`.
- Which URP asset/renderer checkbox to set (HDR, MSAA level, Depth/Opaque
  Texture, rendering path) → `unity-perf:unity-urp-settings`. This skill
  explains *why* they break the pass.
- GLES `glClear`/`glInvalidateFramebuffer`, MSRTT, GL load/store →
  `gles3-perf:gles-tile-load-store`.
- Bin math, GMEM size, LRZ, UBWC, why the hardware bins →
  `arm-mobile-hw-perf:xr2-adreno-architecture`.
- DRAM bytes per full-screen pass, bandwidth-bound diagnosis →
  `arm-mobile-hw-perf:xr2-bandwidth-power`.
- Feature by Unity version → `unity-perf:unity-version-matrix`; upgrade
  regressions → `unity-perf:unity-upgrade-risks`; capture tools in general →
  `quest-perf:quest-profiling-toolkit`.

## Diagnose first

**1. Render-stage trace on the headset (any Unity version, Vulkan or GLES).**

```sh
adb shell ovrgpuprofiler -e com.company.app   # detailed mode; then restart the app
adb shell ovrgpuprofiler -t -v                # 100 ms trace, per-bin/per-stage detail
adb shell ovrgpuprofiler -t1.2 -l             # low-overhead: one line per surface, better timings
adb shell ovrgpuprofiler -d                   # ALWAYS turn detailed mode off afterwards
```

Detailed mode costs about 10% of GPU render time. Leaving it on inflates every
later measurement (Q1-067). Each surface line shows its size, MSAA, mode
(0 Direct, 1 HwBinning, 2 SwBinning, 3 HwDirect), bin count and size, and
per-stage times (Q1-068, A2-025, A3-030). Full surface-line glossary →
`quest-perf:quest-profiling-toolkit`.

Read it this way:

| Seen on the eye-buffer surface | Meaning | Next step |
| --- | --- | --- |
| Only `Binning`, `Render`, `StoreColor` | Healthy (A3-007) | Look elsewhere |
| `LoadColor` / `LoadDepthStencil` | Something did not clear or invalidate, e.g. a split pass or a camera stack | Viewer: Load reason |
| `StoreDepthStencil` | Something downstream reads depth, or a pass split stored it | Viewer: `StoreUsedByLaterPass` on depth |
| Extra eye-resolution surfaces | Intermediate plus final blit, post-processing, copy passes | [Off-tile trigger list](references/off-tile-triggers.md) |
| Full-screen surface in Mode 0, one bin | Direct Mode: a full-screen pass with no depth and no MSAA; FFR is off on it (U2-034) | Remove the pass or merge it |

**2. Render Graph Viewer (Unity 6.0+; on device from 6.3).**
Open Window > Analysis > Render Graph Viewer. From 6.3, set Target Selection to
the Quest Development Build (Local/Remote/Direct Connection) (U2-071). Then:

- View Options > Load Store Actions: blue = clear, green = load, red = store,
  gray = don't care. A blue bar marks merged passes; want one ending at
  Backbuffer.
- Pass List: "Native Render Pass Info", "Pass break reasoning". Resource List:
  Memoryless column for `_CameraTargetAttachment`/`_CameraDepthAttachment`;
  "F" = on-chip framebuffer read (U2-071, U2-077).

**Capture on the headset, not in the Editor.** The Editor backbuffer is
single-sample, so the Editor graph shows MSAA intermediates that the Quest
device build does not have (U2-051, [community]). On URP 14 the Scene view
forces Native RenderPass off (U2-024).

**3. Pre-6.3 or Meta subpass fork.** Use RenderDoc Meta Fork and look for
`vkCmdNextSubpass`, or use the Render Graph Viewer with Meta XR Simulator on
Vulkan (U2-087).

**4. Rule out the 6.0 regression first.** UUM-90118 cost about +20% GPU with
Render Graph on Quest from 6000.0.16f1; it was fixed in 6000.0.46f1 (U1-031).
Details → `unity-perf:unity-upgrade-risks`.

**5. Confirm "no RG gains" is not Compatibility Mode.** A project upgraded to
6.0 from an earlier URP opens with Compatibility Mode on (Render Graph off)
(U1-023) (6.0-6.2: Project Settings > Graphics > Render Graph; 6.3: only if
the `URP_COMPATIBILITY_MODE` define is set; 6.4+: removed) (U1-025, U1-C5).

## Key numbers

| Number | Source / tag | Applies to |
| --- | --- | --- |
| Bad load/store example: 10.62 ms surface, of which LoadColor 0.71, LoadDepthStencil 0.828, StoreDepthStencil 0.871, StoreColor 1.525 ms, so about 3.9 ms of load/store | Meta po-advanced-gpu-pipelines (U2-036, A3-007) [measured] (Meta's capture; A2-054/A3-007 record it as [doc]) | 1216x1344 MSAA 2x, Quest 1-era surface; the stage names apply to all Quest. Re-measure [verify on device] |
| Avoidable share of that example (LoadColor + LoadDS + StoreDS): 2.41 ms, about 23%. All GMEM↔DRAM traffic: about 37% | A2-054, derived from Meta's numbers | Same example |
| Reading a previous pass's output from main memory is about 10x slower than from tile memory | Meta gpu-impaired-algorithms (U2-033, A2-059) [doc] | Quest 2/3/3S |
| Subpass merging gives ">10%" frame-time gains, in binning mode only | Qualcomm mobile best practices (A2-057) [doc] | Adreno, Vulkan |
| One extra full-screen RGBA8 store + read-back: about 47 MB/frame, about 3.4 GB/s at 72 Hz; FP16 doubles it | A3-012, derived [doc inputs] [verify on device] | Quest 3S default 1680x1760; owned by `arm-mobile-hw-perf:xr2-bandwidth-power` |
| Native render pass limits: 8 attachments, 8 subpasses | URP 6000.5 `PassesData.cs` (U2-058) [doc] | Unity 6.x |
| MSAA input-attachment reads: 2 samples in parallel are free, 4 are not | Meta (A2-058) [doc] | Quest 2 (Adreno 650); Adreno 740 not stated [verify on device] |
| Full-screen single-bin Direct Mode example: 1216x1344 in 2.01 ms | Meta (U2-034) [doc] | Quest 1-era resolution; re-measure |
| On-tile post vs classic post, bloom, tonemapping, colour grading: **no published ms number** | U2-070 (Quest 3 chart is an image only), unity.md Known unknowns | Measure: A/B at locked CPU/GPU levels, GPU ms in OVR Metrics plus `ovrgpuprofiler -t` stage times |
| ovrgpuprofiler detailed mode overhead: about 10% of GPU render time | Q1-067 [doc] | Quest 2/3/3S |

## Fixes, ranked by payoff ÷ effort

### 1. Remove the off-tile triggers you do not need — Throughput

Each of these moves URP to an intermediate plus a final blit (URP 14 source,
U2-030), or splits the native pass (U2-031, U2-032):

Depth/Opaque Texture (asset **and** each camera); HDR; integrated
post-processing, including the per-camera Post Processing checkbox (Q3-013);
upscaling filter, non-default viewport rect, camera stacking; Deferred;
IMGUI/OnGUI; FullScreenPass with Fetch Color Buffer on (U2-026); SSAO; Decals.

The full list, with the pass-break reason each one causes, is in
[references/off-tile-triggers.md](references/off-tile-triggers.md). Read it
whenever the viewer or trace shows an unexplained pass or store. The asset and
renderer paths for each checkbox are in `unity-perf:unity-urp-settings`.

- Effect: removes whole full-resolution store + load round trips from the
  average GPU time. Variance is unaffected.
- Quality cost: you lose features that need scene depth or colour (soft
  particles, refraction, SSAO). Replace depth reads with the depth input
  attachment (fix 5).
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `Vulkan` `GLES`.

Unity's 6.6 untethered-XR checklist is the baseline to check a project against
(U2-080, Q3-093): Vulkan + OpenXR with multiview, FFR and MVRR; Render Graph
and Forward; on-tile post from 6.3, post off before; MSAA 2x; depth priming,
Depth/Opaque Texture, SSAO and HDR off; depth input attachment when depth is
needed; resolution scaling, Quest shader optimizations, Adaptive Performance
(OpenXR). Setting paths → `unity-perf:unity-urp-settings`.

### 2. Post-processing: on-tile on 6.3+, off before 6.3 — Throughput

**Before 6.3:** Unity's XR advice was to disable post-processing (U2-038,
U2-C7). Turn off Post-processing on the renderer **and** Rendering > Post
Processing on every XR camera. Issue 22353 shows a camera still ticked forcing
`_CameraColorAttachmentA` and a redundant blit (Q3-013).

**6.3-6.4 (XR only):** Vulkan; renderer integrated post-processing off; add
the renderer feature "On Tile Post Processing (Untethered XR)" and the Volume
components. Supported: Color grading, Vignette, Tonemapping, Dithering, Film
Grain (U2-074). Tile-Only Mode does not exist yet (X-C10).

**6.5+ (all platforms):** renderer Post-processing off; tick the renderer's
**Tile-Only Mode**; add On Tile Post Processing and the Volume components.

Without Tile-Only Mode the feature **silently falls back** to texture sampling:
the image looks the same and there is no bandwidth saving (U2-075). A project
upgraded from 6.3 without ticking it pays full post bandwidth.

Rules for this path:
- **No bloom, and no effect that samples neighbouring pixels** (U2-076,
  [community]). The same goes for DoF, chromatic aberration, lens distortion,
  motion blur and Panini (U2-085). Bake a glow into emissive/unlit materials or
  sprites instead. Enabling one of these takes you back to the Uber blit plus
  "Blit Bloom Mipmaps" passes (U2-038).
- FXAA, FSR and TAA+RCAS each force a final post blit even when the other
  effects are off (U2-038).
- On-tile post supports foveated rendering (U2-076).
- MSAA vs on-tile is a documented conflict (U2-C2); see Pitfalls.
- GLES in Linear colour space: from 6000.6.0b6 Tile-Only falls back when the
  backbuffer is not sRGB, so GLES Quest builds lose on-tile post (U1-063).

**Meta subpass fork (2022.3 / 6000.0-6000.2):** 11 effects are tile-compatible
and integrated post stays on (U2-085; list in
[off-tile-triggers.md](references/off-tile-triggers.md) §5). Use Meta's list
only on the fork, Unity's 5-effect list on stock URP 6.3+ (U2-C5).

- Effect: removes the intermediate colour store and read-back, plus the Uber
  blit surface, from average GPU time. Variance is unaffected. Unity
  publishes no ms figure (U1-062). Measure it.
- Quality cost: no bloom, no neighbour-sampling effects.
- Tags: `Quest 2` `Quest 3/3S` `Unity ≥ 6000.3` (XR) / `Unity ≥ 6000.5`
  (Tile-Only) `URP 17.3+` `Vulkan`.

### 3. Keep Tile-Only validation on while developing — Throughput (guard)

On 6.5+, Tile-Only validation throws in development builds on an incompatible
pass; release builds strip it. It shares Project Settings > Graphics > Render
Graph > Enable Validity Checks (U2-025, U2-078). With it off, rendering can
fall off-tile silently. Validation is conservative (U2-076).
- Effect: none by itself; keeps fixes 1, 2 and 4 from silently regressing.
  Its dev-build CPU cost is not quantified (U2-078), so profile CPU with it off.
- Quality cost: none. Release builds strip it.
- Tags: `Unity ≥ 6000.5` `Vulkan`.

### 4. Write custom passes as merge-friendly raster passes — Throughput

For URP 17 (Unity 6.x):
- `AddRasterRenderPass<PassData>` in `RecordRenderGraph`; reads via
  `UseTexture`, colour targets via `SetRenderAttachment(tex, 0)`; a static
  render function (U2-063).
- Read the current pixel with `SetInputAttachment` (framebuffer fetch), not
  `UseTexture`. `UseTexture` of the previous output gives
  `NextPassReadsTexture` and a store (U2-058, U2-066).
- Never "blit back": set `resourceData.cameraColor = destination` (U2-065).
- `AddUnsafePass` and compute never merge; compute on camera colour cannot
  stay on-tile (U2-064). Move histogram/auto-exposure to a small downsample or
  last frame's data. Put "set globals" work in a raster pass with no
  attachments; it merges, an unsafe pass breaks the chain (U2-060).
- Use `Blitter` or `AddBlitPass`/`AddCopyPass`, never `CommandBuffer.Blit`,
  `Graphics.Blit` or `RenderingUtils.Blit` (U2-067, U2-068). With the default
  material, `AddBlitPass` can become an `AddCopyPass` that uses framebuffer
  fetch and merges. On 6.0 before 6000.0.49f1, `AddBlitPass`/`AddCopyPass`
  break multiview (left eye only; UUM-92499/93821, U1-078). Upgrade the patch
  or use `Blitter` in a raster pass. → `unity-perf:unity-upgrade-risks`.
- `AllowPassCulling(false)` only for debugging; reuse URP's Copy Color/Copy
  Depth through `ConfigureInput` instead of your own copies (U2-063).

A paste-ready URP 17 raster pass with framebuffer fetch (C# feature plus HLSL
shader) is in [references/rg-pass-template.md](references/rg-pass-template.md).
Read it before writing or reviewing any custom Quest pass.

- Effect: a merged per-pixel pass costs its ALU only, with no store or load of
  camera colour. Variance is unaffected.
- Quality cost: framebuffer fetch reads only the current pixel, so no blur,
  bloom or distortion (U2-066).
- Tags: `Unity ≥ 6000.0` `URP 17+` `Vulkan`. On GLES, framebuffer fetch falls
  back to copies through video memory (U2-066, U2-088).

### 5. Depth effects: depth input attachment instead of Depth Texture — Throughput

**6.6 stock URP:** a Render Objects feature with **Depth** and **Set As Input
Attachment** at After Rendering Opaques or later; in the shader
`#pragma multi_compile _ _DEPTH_AS_INPUT_ATTACHMENT _DEPTH_AS_INPUT_ATTACHMENT_MSAA`
and `FetchSceneDepth(positionCS.xy)` (MSAA: `FetchSceneDepth(xy, sampleIndex)`);
check `SystemInfo.supportsDepthAttachmentAsInputAttachment` at runtime. Shader
Graph has a Fetch Scene Depth node (U2-079). Snippet: the template reference.

**Meta fork (pre-6.3 / 6.3):** use the `DepthInputSubpass` layer, the
`_DEPTH_INPUT_ATTACHMENT` keyword, and
`LOAD_FRAMEBUFFER_INPUT_MS(depth_input, 0, float2(0,0))` (U2-086). Shaders
written for the fork must be ported to the 6.6 keywords.

- Effect: removes the depth copy and `StoreDepthStencil` from average GPU
  time. Variance is unaffected.
- Quality cost: one more `multi_compile` axis, so strip unused variants
  (→ `unity-perf:unity-shader-hitches`). Current pixel only.
- Tags: `Unity ≥ 6000.6` `Vulkan` (stock) / fork `Unity 2022.3.42f1+`,
  `6000.0.23f1+` `Vulkan`.

### 6. URP 12/14 and 6.0-6.3 Compatibility Mode: Native RenderPass, Store Actions — Throughput

Compatibility Mode is a Project Settings checkbox on 6.0-6.2 only; on 6.3 it
exists only behind the `URP_COMPATIBILITY_MODE` define (U1-025, U1-C5).

- Tick **Native RenderPass** on the Universal Renderer (off by default)
  (U2-024, U2-081). It has no effect on GLES.
- Set **Store Actions** on the URP asset to Discard only after confirming no
  injected pass reads a discarded target. Auto falls back to Store when it
  detects injected passes, and Store "significantly increases the memory
  bandwidth" (U2-005).
- Custom passes cannot declare input attachments on URP 12/14:
  `ConfigureInputAttachments` is internal (U2-082). Use
  `ConfigureColorStoreAction`/`ConfigureDepthStoreAction` and
  `ConfigureInput`, and never `cmd.SetRenderTarget`.
- For real subpasses on 2022.3.42f1+ or 6000.0.23f1-6000.2.x, use Meta's
  Oculus-VR/Unity-Graphics subpass branches. Branch names, version ranges and
  fork limits: [off-tile-triggers.md](references/off-tile-triggers.md) §5.
- On 6.4+ both settings are gone or obsolete (Native Pass Compiler decides,
  U2-C4); passes without `RecordRenderGraph` stop working (U1-026). Port them.
- Effect: removes URP-internal stores and loads from average GPU time;
  variance unaffected.
- Quality cost: none. Side effects: the fork loses **Dynamic Resolution and
  AppSW** before 6000.3 (U2-084); Discard can corrupt an injected pass that
  reads a discarded target.
- Tags: `Unity 2021.3` `Unity 2022.3` `Unity 6000.0-6000.3 (Compatibility Mode)`
  `URP 12/14` `Vulkan`. Dossier conflict: U2-024 says the URP 12 docs
  recommend it (default off in 2021.3). U1-027 found no Native RenderPass
  entry on the URP 12.1 renderer page. Treat 2021.3 as [verify on device].

### 7. MSAA resolve in the last subpass only — Throughput

Resolve only in the last subpass. An intermediate resolve, a separate
`vkCmdResolveImage`, or a `SHADER_READ` dependency instead of
`INPUT_ATTACHMENT_READ` breaks the benefit (A2-055, U2-037). Render Graph
enforces this with `MultisampledShaderResolveMustBeLastPass`. 6.2+ uses
`VK_QCOM_render_pass_shader_resolve` for Quest MSAA, and its input attachments
must be memoryless (U2-052, U2-061). Anything that makes URP store MSAA
samples also spills. The MSAA *level* (2x vs 4x) belongs to
`unity-perf:unity-urp-settings`.
- Effect: avoids an MSAA-sample store and a separate resolve in average GPU
  time; variance unaffected. No Quest ms figure is published (U2-052 gap).
- Quality cost: none.
- Tags: `Unity ≥ 6000.2` `Vulkan`; native-plugin authors on any version.

## Verify

1. **Trace:** re-run `ovrgpuprofiler -t -l`. On the eye surface, `Load*` and
   `StoreDepthStencil` should be gone, with only `StoreColor` left. Extra
   eye-resolution surfaces should disappear (A3-007). Then run
   `ovrgpuprofiler -d`.
2. **Viewer (6.3+ on device):** one blue merge bar ending at Backbuffer.
   Camera colour and depth are Memoryless. The on-tile post pass shows "F"
   and writes Backbuffer colour (U2-077). There is no Final Blit.
3. **GPU time:** OVR Metrics `app_gpu_time`, A/B on a fixed camera path at
   locked CPU/GPU levels, 2-5 minutes per variant, with detailed profiler
   mode **off**. Expect a drop about equal to the removed Load/Store stage
   times plus removed surfaces' time from step 1. No published Quest figure
   exists for on-tile post or depth input; this A/B is the number.
4. **Merging A/B (6.1+):** the Render Graph debug setting that disables pass
   merging gives a same-build baseline for the merge gain (U2-057).
5. **Sustained:** for a large bandwidth cut, run a 20-30 minute session and
   compare GPU level and throttle state between the first and last 5 minutes
   (→ `quest-perf:quest-levels-thermal`).

## Pitfalls and myths

- **"Enable Native RenderPass" on Unity 6.** The 6.6 renderer and performance
  pages still recommend it. Under Render Graph it is always on, and the toggle
  exists only in 6.0-6.3 Compatibility Mode (conflict U2-C4). The same
  applies to Store Actions.
- **Editor graph = device graph.** False for MSAA. The Editor shows
  intermediates that a Quest build does not have (U2-051). Capture on device.
- **MSAA and on-tile: conflict U2-C2, unresolved.** The 6.6 docs say MSAA
  "breaks on-tile rendering", and Tile-Only Mode disables it (U2-032, U2-025).
  Unity staff say a Quest/Vulkan build renders into an MSAA backbuffer without
  intermediates (U2-051, [community]). Likely: plain MSAA without post stays
  merged; MSAA plus on-tile post/Tile-Only does not [verify on device].
- **HDR renders straight to the eye texture.** Unity's XR resolution page says
  so. URP source says HDR forces an intermediate. Follow the source and keep
  HDR off (U2-C6).
- **"Tile-Only Mode is part of 6.3 on-tile post setup."** It does not exist
  before 6.5 (X-C10). On 6.5+ it is required, or the fallback is silent.
- **"Post-processing is fine now that on-tile post exists."** Only 5 effects
  run on-tile. Bloom never does (U2-076).
- **Pass count matters.** A pass with no fragment attachments merges freely
  (U2-060). The break reason matters, not the count.
- **The "except on Android XR" note** on upscaling and dynamic resolution in
  the 6.6 on-tile page: it is not documented whether this covers Quest (U2-032).
  [verify on device]
- **6.0 → 6.3 upgrade.** 6.3 uses a new shared RG compiler, and 6.2 made
  merging stricter. Re-check merges in the viewer after every minor upgrade
  (U2-057/U1-028).
- **`OnRenderObject` in any script** adds a callback pass that prevents merging
  (U2-087). Meta's fork comments that pass out [verify on device].
- **"`AddBlitPass`/`AddCopyPass` are safe on any 6.0 patch."** Before
  6000.0.49f1 (and 6000.1.0f1) they ignore XR multiview array textures, so only
  the left eye renders on Quest 2 (UUM-92499/93821, U1-078).
- **Capability flags** (memoryless, backbuffer MRT, depth input attachment)
  are unlogged on Quest 2 vs 3. Log them at startup with the template's
  `QuestTileCaps` (U2-059, U2-061) [verify on device].
- **GLES.** Native RenderPass does nothing, framebuffer fetch falls back to
  copies, and memoryless on-tile post needs Vulkan (U2-088). →
  `gles3-perf:gles-tile-load-store`, `gles3-perf:gles-vs-vulkan`.

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc] (the 3.9 ms breakdown is Meta's own measurement, [measured])
- https://developers.meta.com/horizon/documentation/unity/gpu-impaired-algorithms/ [doc]
- https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-post-processing.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-graphics-on-tile-post-processing.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-introduction.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-optimize.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-unsafe-pass.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-framebuffer-fetch.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-blit.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/customize/blit-overview.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-viewer-reference.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/read-depth-input-attachment.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc]
- https://docs.unity3d.com/6000.2/Documentation/Manual/WhatsNewUnity62.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity64.html [doc]
- https://docs.unity3d.com/6000.0/Documentation/Manual/urp/upgrade-guide-unity-6.html [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/urp-universal-renderer.html [doc]
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderer.cs [doc]
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/Passes/ScriptableRenderPass.cs [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/NativePassCompiler.cs [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRendererRenderGraph.cs [doc]
- https://issuetracker.unity.com/issues/22353 [doc]
- https://issuetracker.unity3d.com/issues/gpu-utilization-increases-by-20-percent-on-meta-quest-headsets-when-render-graph-is-enabled-on-6000-dot-0-16f1-and-higher [measured] (accessed 2026-09-24)
- https://unity.com/releases/editor/whats-new/6000.0.46f1 [doc] (accessed 2026-09-24)
- https://unity.com/releases/editor/whats-new/6000.0.49f1 [doc] (accessed 2026-09-24)
- https://unity.com/releases/editor/whats-new/6000.6.0b6 [doc] (accessed 2026-09-24)
- https://unity.com/releases/editor/whats-new/6000.3.23f1 [doc] (accessed 2026-09-24)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity62.html [doc] (accessed 2026-09-24)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity63.html [doc] (accessed 2026-09-24)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html [doc] (accessed 2026-09-24)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity61.html [doc] (accessed 2026-09-24)
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/RendererFeatures/FullScreenPassRendererFeature.cs [doc] (accessed 2026-09-24)
- https://discussions.unity.com/t/performant-and-energy-efficient-rendering-with-render-graph-and-on-tile-post-processing-for-untethered-xr-in-unity-6-3/1703007 [community]
