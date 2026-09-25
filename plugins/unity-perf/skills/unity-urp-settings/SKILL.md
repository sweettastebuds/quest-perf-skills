---
name: unity-urp-settings
description: "URP asset, renderer, Player and XR settings for Quest 2/3/3S: HDR, MSAA 2x vs 4x, upscaling filter, depth and opaque textures, depth priming, store actions, intermediate texture, Forward vs Forward+ vs Deferred, Tile-Only Mode and swapchain. Includes a C# editor audit script that reports a project's settings against these recommendations. Use when configuring or reviewing a Quest URP project, choosing an MSAA level, auditing settings, or asking \"which URP checkbox adds a pass\"."
---

# URP, Player and XR settings for Quest

Goal: **Throughput** first (fewer passes, GMEM loads/stores and bins), **Consistency** second
(no runtime reallocations). IDs such as U2-002 are finding IDs in `research/*.md`.

## When to use / when not

Use when:
- Setting up or reviewing a Quest URP project: URP Asset, Universal Renderer Data,
  Player settings (Android), OpenXR / Oculus XR settings.
- Choosing an MSAA level (2x vs 4x conflict) or Forward vs Forward+ vs Deferred.
- Someone asks "which checkbox adds a pass", "why is there a Final Blit", "HDR on Quest?",
  "Store Actions?", "Intermediate Texture Always vs Auto", "Tile-Only Mode".
- Running a settings audit before a perf pass or after an upgrade (`scripts/QuestPerfAudit.cs`).

Do not use (go to the owner instead):
- Cause of the slowdown unknown: `quest-perf:quest-triage`.
- Render Graph pass merging, PassBreakReasons, memoryless, framebuffer fetch, custom
  RG passes, bloom/tonemapping/post cost, Native RenderPass internals:
  `unity-perf:unity-render-graph-tiling`.
- Light counts, shadows, cascades, probes, lightmaps, APV: `unity-perf:unity-lighting`
  (this skill keeps only the rendering-path choice).
- Render scale, eye-buffer size, dynamic resolution, FFR / foveation:
  `quest-perf:quest-resolution-foveation`.
- Refresh-rate choice, OpenXR Latency Optimization, stale frames:
  `quest-perf:quest-frame-pacing` (the audit only reports the setting).
- GLES vs Vulkan decision and per-API MSAA cost table: `gles3-perf:gles-vs-vulkan`.
- Bin/GMEM hardware and the in-tile MSAA resolve: `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Graphics Jobs, Multithreaded Rendering, IL2CPP, GC: `unity-perf:unity-cpu-scripting`.
- Which features exist in which Unity version: `unity-perf:unity-version-matrix`.
- AppSW setup: `quest-perf:quest-appsw`.
- HDRP: out of scope for this plugin; every Quest source used here is URP guidance.

## Diagnose first

1. **Static audit (2 minutes).** Copy [scripts/QuestPerfAudit.cs](scripts/QuestPerfAudit.cs)
   into any `Editor` folder (e.g. `Assets/Editor/`), let it compile, then run
   **Tools > Quest Perf > Audit Project**. It prints a report to the Console and writes
   `Logs/QuestPerfAudit.txt`. CI: `Unity -batchmode -quit -projectPath <path>
   -executeMethod QuestPerfTools.QuestPerfAudit.RunBatch` (exit code 1 when any FAIL).
   If the project uses assembly definitions for editor code, put the script in an Editor
   asmdef that references `Unity.RenderPipelines.Universal.Runtime` and
   `Unity.RenderPipelines.Core.Runtime`. Read
   [references/audit-checks.md](references/audit-checks.md) when interpreting a check ID
   or deciding whether a WARN applies to your project.
2. **Confirm on device what the driver did** (settings express intent; the capture shows
   the result, U2-095):
   ```sh
   adb shell ovrgpuprofiler -e com.company.app   # detailed mode; restart the app afterwards
   adb shell ovrgpuprofiler -t -v                # per-surface: size, MSAA, Mode, bins, per-stage times
   adb shell ovrgpuprofiler -d                   # turn detailed mode off (~10% GPU overhead, A3-029)
   ```
   Read each surface line (A3-030, A2-025): more than one full-resolution eye surface per
   frame means an intermediate + final blit; non-trivial `LoadColor`, `StoreDepthStencil`
   or `LoadDepthStencil` on the eye surface means a pass broke the tile; `Mode: 0 (Direct)`
   on a full-screen surface means FFR does not apply to it (U2-034). Quest 2 prints one
   surface whose bins serve both views (A3-034).
3. **Name the pass** that caused it:
   - Unity 6.3+: Render Graph Viewer connected to a Development Build on the headset
     (Window > Analysis > Render Graph Viewer, Target Selection = device). Turn on
     View Options > Load Store Actions. Editor graphs differ from device graphs (U2-051).
   - URP 12/14, or anything pre-6.3: RenderDoc Meta Fork capture. The Unity Frame
     Debugger does not support Meta devices (U1-058).
4. **Route.** If the extra surfaces or load/store stages trace back to an asset, renderer or
   camera setting below, fix it here. If they trace to a custom pass or a post effect, go to
   `unity-perf:unity-render-graph-tiling`. If neither, and GPU time is still over budget,
   go back to `quest-perf:quest-triage`.

## Key numbers

| Number | Value | Applies to | Source |
|---|---|---|---|
| Frame budget | 13.9 / 11.1 / 8.3 ms at 72 / 90 / 120 Hz; runtime default is 72 Hz unless the app requests more | Quest 2, Quest 3/3S | Q2-009, Q2-010 [doc] |
| GMEM (tile memory) | about 1 MB (Adreno 650) / about 2 MB (Adreno 740) | Quest 2 / Quest 3/3S | U2-035 [doc] |
| Bytes per pixel per view (drives bin count) | no MSAA 8 B; 2x 16 B; 4x 32 B; 4x with RGBA16F colour 48 B (about 1.5x the bins of 4x RGBA8) | all Quest, any URP | A2-014 [doc, derived] |
| Quest 2 default eye buffer at 4x | 1440x1584 = 135 bins of 96x176 | Quest 2 | U2-095, ARM-GF1-006 [doc] |
| HDR R11G11B10 vs LDR RGBA8 | same 32-bit colour, no extra bins; RGBA16F (64-bit HDR) adds bins | all Quest | A2-014 [doc, derived] |
| 4x MSAA cost, Quest 3/3S | +3.3 ms GLES, +5.0 ms Vulkan on one user scene (Unity 6000.0-6000.7a); use deltas only, the report's absolutes are inconsistent (G2-C9) | Quest 3/3S | G2-039 [measured] |
| 4x MSAA cost, Quest 2 | about +7 ms (about 14 ms to 21 ms Vulkan; GLES within about 1 ms) | Quest 2, Unity 6000.x | G2-040 [measured] |
| 4x MSAA cost, original Quest | +0.5 to 1.5 ms, 10-15% for medium content; do not exceed 4x | Quest 1 hardware (stale) | U2-093, A2-056 [measured] |
| 2x MSAA cost | no published Quest 2/3 number; Qualcomm: "likely to be practically free" | Adreno generic | A2-017, A3-020 [doc] |
| Load/store share of a bad config | 3.9 ms of 10.62 ms was LoadColor/LoadDepth/StoreDepth/StoreColor | Quest 1-class example | U2-036 [measured] |
| Forward+ break-even | wins from about 5 real-time lights; Viking Village GPU frame time 7.5 ms both paths at 5 lights, 12 ms Forward vs 8.5 ms Forward+ at 30 lights; headset not stated | URP 14-17, Quest (headset unspecified) [verify on device] | U2-027 [measured] |
| Visible additional lights per camera | 32 on mobile (Vulkan, GLES with ES3.1 shaders); 16 on GLES with "Use OpenGL ES 3.0 shaders" | URP 12-17, 6.6 GLES setting | U4-005, U1-094, X-C6 [doc] |
| Render Scale snap | values within 0.05 of 1.0 snap to 1.0 | URP 12-17 | U2-007 [doc] |
| Swapchain buffers | default 3; setting ignored before 6000.0.83f1 / 6000.3.24f1 / 6000.6.0f1 | Vulkan | U1-068, U5-025 [doc] |
| Unity floor for Meta support | 6000.0.66f2 or later, 6.1+ recommended | Unity 6.0 | U1-008 [doc] |

No published Quest ms figures exist for HDR on/off, Depth/Opaque Texture, soft-shadow
tiers, LOD Cross Fade, SSAO, decals or Volume Update Mode (unity.md Known unknowns).
Measure each as a single-variable A/B (see Verify).

Read [references/urp-asset-settings.md](references/urp-asset-settings.md) when you need
the full per-setting table (Inspector path, serialized field, default, recommended value,
URP version, reason, finding ID), e.g. while editing an asset by hand or porting between
URP 12, 14 and 17.

## Fixes, ranked by payoff ÷ effort

Each fix: what to change, effect on average vs variance, cost, tags, goal.

### 1. HDR off (URP Asset > Quality > HDR)

- Change: untick HDR. If HDR is unavoidable, keep HDR Precision = 32 Bits (URP 14+) and
  never enable Alpha Processing (it needs 64-bit) (U2-002).
- Effect: removes the forced intermediate colour texture and final blit (URP 14 source,
  U2-030); lowers bandwidth. Average GPU time down; no variance effect.
- Cost: no HDR bloom/tonemapping range. 64-bit HDR also adds bins (A2-014).
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan`. Default asset has HDR **on**
  (U2-001), so new projects need this change. Goal: **Throughput**.

### 2. Depth Texture and Opaque Texture off (asset and every camera)

- Change: URP Asset > Rendering > Depth Texture off, Opaque Texture off; Camera >
  Rendering > Depth Texture / Opaque Texture = Use Pipeline Settings or Off.
  Any renderer feature that calls `ConfigureInput(Depth)` or `ConfigureInput(Color)`
  turns them back on (U2-003).
- If depth is required: Universal Renderer > Depth Texture Mode = **After Transparents**
  (URP 14+; the default from 2022.3). After Opaques inserts a Copy Depth between opaques
  and transparents that stores and reloads colour, MSAA samples included (U2-021, G2-019).
  URP 12 has no After Transparents option, so any depth texture there splits the pass.
- Effect: removes Copy Depth / Copy Color passes and their GMEM stores and reloads
  (U2-003, U2-004, G2-018). Average GPU time down.
- Cost: no soft particles, depth-fade water or refraction from scene colour. With After
  Transparents, transparents cannot read this frame's depth [verify on device].
- Side effect: on platforms without StoreAndResolve, Opaque Texture on makes Unity
  silently ignore MSAA (U2-004, G2-017); check `SystemInfo.supportsStoreAndResolveAction`
  on device (G2-015). Opaque Downsampling makes a half-size target that cannot merge under
  Render Graph (U2-004).
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` (After Transparents `URP 14+`) `GLES` `Vulkan`.
  Goal: **Throughput**.

### 3. Intermediate Texture = Auto; drop features that force one

- Change: Universal Renderer > Rendering > Intermediate Texture = **Auto**. The
  serialized default on the renderer is **Always** in every branch checked, 2021.3 to
  6000.5 (U2-023). Then check renderer features:
  - SSAO: remove on Quest (depth prepass, two blurs and a blit; U2-028).
  - Decal: requires an intermediate (U2-029); prefer baked decal meshes.
  - Full Screen Pass: `fetchColorBuffer` defaults true, which forces an intermediate
    and a colour copy (U2-026). Untick it when the effect does not read scene colour.
- Effect: removes a full-resolution intermediate and final blit per eye. Average GPU
  time down. On GLES, an intermediate also removes compositor FFR from the main pass
  (G2-024).
- Cost: none for Auto itself; features you remove lose their effect.
- Note: in URP 14 source, Always only allocates when the renderer has features; with zero
  features it is harmless, so re-audit whenever a feature is added (U2-023).
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan`. Goal: **Throughput**.

### 4. Upscaling Filter = Auto; change resolution with render scale instead

- Change: URP Asset > Quality > Upscaling Filter = Automatic. FSR 1.0 stays active even
  at Render Scale 1.0, and STP forces TAA (U2-008). Unity lists the upscaling filter as
  off-tile (U2-031). In XR, render scale alone never forces an intermediate: the eye
  texture itself is resized (U2-045).
- Effect: removes a final post blit (U2-070, via U2-008 notes). Average GPU time down.
- Cost: none at scale 1.0. Resolution control belongs to
  `quest-perf:quest-resolution-foveation`; do not change asset Render Scale per frame,
  since that reallocates the eye textures and is a hitch risk (U2-047).
- Tags: `Quest 2` `Quest 3/3S` `URP 12.1+` (FSR presence on 12.1 unconfirmed, U2-018) (STP
  `Unity ≥ 6000.0`). Goal: **Throughput**
  (and **Consistency** for the no-per-frame-realloc rule).

### 5. Choose the MSAA level (URP Asset > Quality > Anti Aliasing (MSAA))

The sources conflict (U2-C1 / U3-C7, unresolved):
- Unity's untethered-XR page: 2x is "a good balance"; the generic URP performance page says
  reduce or disable MSAA (U2-006, U2-090).
- Qualcomm: 2x MSAA is "likely to be practically free"; the resolve happens in tile memory
  (A2-017, A3-020).
- Meta: 4x is "extremely cheap" and recommended; do not exceed 4x (U2-092). Meta's only
  published numbers are original-Quest (U2-093, A2-056).
- Measured on Quest 2/3/3S (UUM-149765): 4x costs +3.3 ms GLES / +5.0 ms Vulkan on
  Quest 3/3S and about +7 ms on Quest 2 in one user scene (G2-039, G2-040). No 2x number
  exists for any current headset.

Decision rule:
- Start at **2x** on both headsets. It halves bytes per pixel vs 4x (A2-014).
- Try **4x on Quest 3/3S only** if aliasing is unacceptable and a single-variable A/B shows
  GPU headroom (G2-040: "treat 4x as a Quest 3-only option unless measured otherwise").
  Per-device MSAA needs one URP asset per quality level, selected at startup;
  headset detection is owned by `quest-perf:quest-budgets-tiers`.
- **Never 8x** (U2-093).
- MSAA off only for a GPU-bound Quest 2 build where the A/B shows 2x is not free.
- Keep one owner of MSAA: the URP asset. URP pushes the level into the XR display so the eye
  swapchain itself is multisampled (U2-050). Do not also enable OVRManager's
  "Use Recommended MSAA Level" (U2-050 notes).
- Keep camera MSAA/HDR consistent with the asset; mismatches broke GLES multipass render
  pass validation on 6000.0.23f1+ until fixed (G2-027).
- Unity 6.2+ uses `VK_QCOM_render_pass_shader_resolve` for Quest MSAA; no before/after
  number is published (U2-052).
- MSAA only works with Forward and Forward+ (U2-006). For the on-tile interaction, see
  fix 9.
- Effect: moves average GPU time (binning, render, resolve); A2C and framebuffer-fetch
  cost scale with sample count (U2-C1). No variance effect.
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan`. Per-API deltas:
  `gles3-perf:gles-vs-vulkan`. Resolve mechanism: `arm-mobile-hw-perf:xr2-adreno-architecture`.
  Goal: **Throughput**.

### 6. Depth Priming Mode = Disabled

- Change: Universal Renderer > Rendering > Depth Priming Mode = Disabled (the serialized
  default). Auto is unsupported on Android; priming is unsupported with MSAA and at
  runtime on TBDR mobile; two views double the prepass while LRZ gives similar rejection
  for free (U2-020 / U3-058, G2-020).
- Effect: avoids a full extra geometry pass per view. Average CPU (draw submission) and
  GPU time down.
- Cost: none on Quest, provided shaders keep LRZ enabled (see `unity-perf:unity-shader-authoring`).
- Unity 2021.3 before 9f1 forced a depth prepass on GLES3 (UUM-8381); an unrequested
  "DepthPrepass" there is that bug (G2-021).
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan`. Goal: **Throughput**.

### 7. Rendering path: Forward or Forward+, never Deferred

- Change: Universal Renderer > Rendering > Rendering Path.
  - **Forward** when few real-time lights are visible.
  - **Forward+** from about 5 real-time lights (Meta, U2-027), and whenever you use the GPU
    Resident Drawer (it requires Forward+ on Quest; X-C9). Forward+ ignores Per Object
    Limit (U2-012).
  - **Not Deferred / Deferred+**: G-buffer causes multiple GMEM loads, MSAA is unavailable,
    and Tile-Only Mode rejects it (U2-019, U1-034). UUM-147509 (soft shadows broken in
    Deferred on Quest) is only fixed in 6000.7.0a3 (U1-035).
- Forward+ in XR on 2022.3 is ambiguous (U1-C4): test stereo on 2022.3 before relying on
  it; prefer 6.x for Forward+.
- **GLES light-limit implication**: on Unity 6.6 GLES builds, the upgrade turns on
  "Use OpenGL ES 3.0 shaders", which keeps MAX_VISIBLE_LIGHTS at 16; turning it off gives
  32 and more shader work. UUM-148728 forced 32 on GLES by mistake until 6000.6.0f1
  (U1-094, U1-040, X-C6). Vulkan is in the 32 bucket.
- Effect: Forward+ vs Forward changes average GPU time depending on light count. Meta's only
  published data is the Viking Village curve in Key numbers (headset unspecified); measure at
  your light counts (U4-006).
- Tags: `Quest 2` `Quest 3/3S` Forward+ `URP 14+`, GLES light limit `Unity ≥ 6000.6` `GLES`.
  Light budgets: `unity-perf:unity-lighting`. Goal: **Throughput**.

### 8. Store Actions (URP 12/14 and 6.0-6.3 Compatibility Mode only)

- Change: URP Asset > Rendering > Store Actions (in URP 17 visible only with
  "Show All Advanced Properties", G2-016). Auto = Discard unless URP detects injected passes,
  then Store; Store "significantly increases the memory bandwidth" (U2-005). Set
  **Discard** only after confirming no injected pass reads a discarded target
  (`LoadStoreActionDebugModeSettings`, G2-025).
- Effect: Throughput: removes StoreColor/StoreDepthStencil stage time on URP 12/14; no
  variance effect.
- Cost: a wrongly discarded target shows garbage or black.
- Under Render Graph (6.0+ default) the setting is ignored: the native pass compiler
  decides load/store, and source marks the field obsolete from 6000.0 and a compile error
  from 6000.4. The 6.6 manual still documents it (U2-C4, resolved: ignore on 6.4+).
- GLES caveat: Unity does not always emit `glInvalidateFramebuffer` for Discard
  (UUM-45041, Adreno status unknown). Confirm with ovrgpuprofiler Load*/Store* stages
  (G2-014).
- Tags: `URP 12` `URP 14` `Unity 6000.0-6000.3 Compatibility Mode` `GLES` `Vulkan`.
  Goal: **Throughput**.

### 9. Tile-Only Mode (Unity 6.5+) as a guard, not a feature

- Change: Universal Renderer > Rendering > Tile-Only Mode (added in 6.5, default off).
  It warns on and blocks settings that need a non-memoryless intermediate, and adds Render
  Graph validation that throws on off-tile passes; validation is stripped from release
  builds (U2-025 / U1-063).
- Conflict (U2-C2, partly resolved): Unity's docs say MSAA "breaks on-tile rendering" and
  On-Tile Validation disables the MSAA option (U2-006, U2-017); Unity staff report a Quest
  Vulkan device build rendering straight into an MSAA backbuffer without intermediates
  (U2-051). Likely reconciliation: plain MSAA with no post stays merged; MSAA plus on-tile
  post or Tile-Only validation is not supported. Confirm in the on-device Render Graph
  Viewer [verify on device].
- Practical use: enable in a development branch to find every off-tile setting, then decide
  per feature. Deferred/Deferred+ are incompatible (U2-019). From 6000.6.0b6 Tile-Only
  falls back when the backbuffer is not sRGB (e.g. GLES in Linear) (U1-063).
- Effect: none at runtime by itself; it blocks settings that add off-tile passes.
- Cost: the Inspector disables HDR, MSAA, Depth/Opaque Texture, upscaling and renderer
  features while validation is on (U2-017).
- Tags: `Unity ≥ 6000.5` `URP 17` `Vulkan` (GLES Linear falls back). Goal: **Throughput**.

### 10. Cheap asset toggles

| Change | Why | Avg vs variance | Quality cost | Tags | Goal |
|---|---|---|---|---|---|
| Terrain Holes off (default on) unless used | Unity performance page and Meta OpenXR 2.6 page (U2-011) | avg down; no variance effect | none unless holes are used | `URP 12+` | Throughput |
| LOD Cross Fade off, or Dithering Type = 2x2 Stencil | Blue Noise default uses alpha test; stencil variant uses stencil bits 4 and 8 and cuts variants (U2-010) | avg down; no variance effect | popping instead of dither (off) | `URP 14+` | Throughput |
| Soft Shadows off, or quality Low | high impact on tile GPUs (U2-009); details in `unity-perf:unity-lighting` | GPU avg down; no variance effect | hard or coarser shadow edges | `URP 14+` tiers | Throughput |
| Volume Update Mode = Via Scripting | removes per-frame volume stack update on the main thread (U2-015) | main-thread avg down; no variance effect | none; must call UpdateVolumeStack on changes | `URP 12+` | Throughput |
| SRP Batcher on (default) | `unity-perf:unity-draw-calls-batching` (U2-016) | CPU avg down | none | `URP 12+` | Throughput |

With Via Scripting, call `Camera.UpdateVolumeStack()` whenever volumes change; paste-ready
component: "Volume stack refresher" in [references/urp-asset-settings.md](references/urp-asset-settings.md).

### 11. Player and XR settings not owned elsewhere

- **Graphics API**: Vulkan first in Player > Other Settings > Graphics APIs; Meta calls it
  "the required graphics API" and the 6.1+ Meta Quest build profile defaults to it (U2-094,
  U1-053). Effect: per-API average CPU/GPU time is scene-dependent; the decision itself:
  `gles3-perf:gles-vs-vulkan`. `Vulkan`. Goal: **Throughput**.
- **Stereo**: OpenXR Render Mode = Single Pass Instanced (Multiview on Quest); multi-pass
  doubles CPU draw submission (U2-040); GPU-time benefit is disputed: Unity says SPI
  "slightly decreases GPU usage", UUM-149765 measured no GPU difference on Quest 2/3/3S
  (G2-C10). CPU-side saving owner: `unity-perf:unity-draw-calls-batching`. Effect: CPU avg
  down; no quality cost. The Oculus XR plugin is unsupported from 6.5 (U1-091).
  `Quest 2` `Quest 3/3S`. Goal: **Throughput**.
- **Vulkan swapchain**: leave "Number of swapchain buffers" at 3 and "Get swapchain image
  late as possible" off; the runtime owns the eye swapchains, and late acquire adds a
  blit through a staging image (U5-025, U1-068, X-C5: resolved, leave the default).
  Effect: no avg change; avoids an extra blit through a staging image. `Vulkan`. Goal:
  **Consistency**.
- **Refresh rate**: the app runs at 72 Hz unless it requests another rate; set it
  explicitly. Effect: fixes the frame budget the app must hit. The choice is owned by
  `quest-perf:quest-frame-pacing` (Q2-010, UNITY-GF1-C2). Goal: **Consistency**.
- **Texture compression**: ASTC (Unity's Android default; Meta says ASTC on both
  headsets) (U4-046, U4-053). Effect: avoids runtime decompression (memory, load time).
  Owner: `unity-perf:unity-memory-assets`. Goal: **Throughput**.
- **Meta Quest build profile (6.1+)** silently switches graphics API, XR plugin and quality
  level on an upgraded project; re-run the audit after adopting it (U1-053, U1-055).

Paste-ready editor snippet that applies fixes 1, 2, 5 and 10 to every URP asset used by any
quality level: bottom of [references/urp-asset-settings.md](references/urp-asset-settings.md).

## Verify

- Re-run **Tools > Quest Perf > Audit Project**: no FAIL lines; every remaining WARN has a
  written reason.
- `ovrgpuprofiler -t -v` on device: one full-resolution eye surface per frame when
  post-processing is off; `LoadColor` / `LoadDepthStencil` / `StoreDepthStencil` near zero
  on that surface; bin count matches the bytes-per-pixel prediction for your MSAA/HDR
  choice (A2-014). No published ms target for each stage; compare before/after.
- Render Graph Viewer on device (6.3+): a single merged native pass from first opaque to
  the eye texture, no "Blit Final To Back Buffer" (U2-022).
- For each setting change, a single-variable A/B at pinned CPU/GPU levels, 5 minutes of a
  fixed camera path per build, OVR Metrics Tool App GPU time: the removed pass's stage
  time should disappear from ovrgpuprofiler; the frame-level delta is scene-dependent and
  has no published figure except MSAA 4x (G2-039/040). How to pin levels and log:
  `quest-perf:quest-profiling-toolkit`.
- Thermal: after the settings pass, one 20-30 minute session in OVR Metrics Tool; GPU
  level and stale frames should not climb relative to the baseline build
  (`quest-perf:quest-levels-thermal` owns the protocol).

## Pitfalls and myths

- **"The Inspector reset value is the default."** Templates and the Meta Quest build
  profile ship different asset values than script defaults. Audit the actual `.asset`
  files for every quality level (U2-001 notes).
- **"New URP assets are Quest-ready."** The script default has HDR on, Terrain Holes on and
  LOD Cross Fade on; the renderer defaults to Intermediate Texture Always (U2-001, U2-023).
- **"Store Actions / Native RenderPass still matter on Unity 6."** Under Render Graph the
  compiler decides; the 6.x manual text is stale (U2-C4). They matter on URP 12/14 and in
  6.0-6.3 Compatibility Mode only. Native RenderPass does nothing on GLES (G2-022).
- **"MSAA 4x is free."** Meta's "extremely cheap" (U2-092) cites unpublished internal
  benchmarks; Meta's only published numbers are original-Quest (U2-093, A2-056). The only
  current-headset measurement shows about +7 ms on Quest 2 and +3.3 / +5.0 ms (GLES /
  Vulkan) on Quest 3/3S (G2-039, G2-040).
- **"Use the Unity e-book's rendering-path advice."** Its Forward/Deferred guidance is
  generic mobile; Deferred is wrong for Quest (UNITY-GF1-011, U2-019). Its "XR devices
  enforce 90 Hz or higher" is wrong for Quest, which defaults to 72 Hz (UNITY-GF1-C2).
- **"Post-processing off" (Meta OpenXR 2.6 page) is universal.** It predates on-tile
  post-processing (6.3+); reconcile per Unity version with
  `unity-perf:unity-render-graph-tiling` (U2-091).
- **"The Frame Debugger shows what runs on Quest."** It does not support Meta devices;
  editor Render Graph shows MSAA intermediates that the device does not create (U1-058, U2-051).
- **"XRSettings.eyeTextureResolutionScale sets resolution in URP."** URP re-applies its
  asset Render Scale per camera, so the asset value probably wins (U2-C3, unresolved;
  owner `quest-perf:quest-resolution-foveation`).
- **"The URP 6.6 URP Settings Analyzer replaces this audit."** Its rule list was not
  inspected (unity.md Known unknowns); run both and compare (U2-096).
- **"Mirror view costs a blit on Quest."** URP skips it on Android (U2-042). But the XR
  Occlusion Mesh pass was missing on Unity 6 / Quest 2 until a newer OpenXR; confirm it
  runs (U2-043) [verify on device].
- **VRS**: the Unity 6.1+ VRS API needs Vulkan fragment shading rate; no source confirms
  Quest exposes it to Unity, or how it interacts with foveation. Treat as unsupported until
  a runtime capability query on device says otherwise (U1-061).
- **Unity's Quest capability flags**: which URP settings the build profile / capability
  flags actually change on Quest is not documented (open question; the audit reads the
  asset values, not the runtime-effective ones).

## Sources

All accessed 2026-09-24.

- Unity 6.6 manual [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (U2-002, U2-003, U2-006, U3-058, U1-034) ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html (U2-004, U2-029, U2-031) ; https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html (U2-005, U2-008, U2-009, U2-017) ; https://docs.unity3d.com/6000.6/Documentation/Manual/urp/urp-universal-renderer.html (U2-019, U2-020, U2-021, U2-023) ; https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html (U2-010, U2-015, U2-090) ; https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html (U2-025, U2-032) ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html (U2-007, U2-047) ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html (U2-012) ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html (U1-053) ; https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassStereoRendering.html (U2-040) ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html (U1-058) ; https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (U5-025) ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (U1-094) ; https://docs.unity3d.com/6000.6/Documentation/Manual/urp/variable-rate-shading-introduction.html (U1-061)
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-untethered-device-optimization.html [doc] (U2-028)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/lighting/light-limits-in-urp.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/urp/rendering-paths-comparison.html [doc] (U4-005, U4-006)
- https://docs.unity3d.com/6000.2/Documentation/Manual/WhatsNewUnity62.html [doc] (U2-052)
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/universalrp-asset.html [doc] (U2-018, G2-016, G2-017)
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/urp-universal-renderer.html [doc] (G2-019, G2-020, G2-022, G2-024)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/get-started/graphics-settings.html [doc] (U2-011, U2-091)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsStoreAndResolveAction.html [doc] (G2-015)
- https://docs.unity3d.com/6000.3/Documentation/Manual/android-requirements-and-compatibility.html [doc] (U4-046)
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/rendering/forward-plus-rendering-path.html [doc] (U1-032, U1-C4)
- https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/Runtime/Data/UniversalRenderPipelineAsset.cs [doc] (U2-001)
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderer.cs [doc] (U2-030, U2-045)
- URP source [doc]: https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRSystem.cs (U2-044, U2-050) ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/RendererFeatures/FullScreenPassRendererFeature.cs (U2-026) ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRMirrorView.cs (U2-042)
- Unity release notes [doc]: https://unity.com/releases/editor/whats-new/6000.6.0f1 (U1-040) ; https://unity.com/releases/editor/whats-new/6000.0.83f1 (U1-068) ; https://unity.com/releases/editor/whats-new/6000.5.0b4 (U1-091) ; https://unity.com/releases/editor/whats-new/6000.7.0a3 (U1-035) ; https://unity.com/releases/editor/whats-new/6000.6.0b6 (U1-063) ; https://unity.com/releases/editor/whats-new/6000.3.0a5 (U1-055)
- https://discussions.unity.com/t/performant-and-energy-efficient-rendering-with-render-graph-and-on-tile-post-processing-for-untethered-xr-in-unity-6-3/1703007 [community] (U2-022, U2-051, U2-070)
- https://discussions.unity.com/t/xr-occlusion-mesh-missing-in-meta-quest-headsets/1584869 [community] (U2-043)
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [measured] (G2-039, G2-040, G2-041, G2-C10)
- Unity issue tracker [community]: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-45041 (G2-014) ; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-8381 (G2-021) ; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-91896 (G2-027)
- Meta Horizon Unity docs [doc]: https://developers.meta.com/horizon/documentation/unity/gpu-improved-algorithms/ (U2-092) ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (A2-014, U2-034, U2-035, U2-036, U2-094) ; https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ (U2-095) ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (A2-025, A3-029, A3-030) ; https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ (Q2-009) ; https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ (Q2-010) ; https://developers.meta.com/horizon/documentation/unity/unity-project-setup/ (U1-008)
- https://developers.meta.com/horizon/documentation/native/android/mobile-msaa-analysis/ [measured] (U2-093, A2-056)
- https://developers.meta.com/horizon/documentation/unity/unity-forward-plus-rendering/ [measured] (U2-027)
- https://developers.meta.com/horizon/resources/device-optimization-comparison/ [doc] (U4-053)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md [doc] (A2-017, A3-020)
- Unity e-book "Optimize your game performance for mobile, XR, and the web in Unity (Unity 6 edition)": https://cdn.bfldr.com/S5BC9Y64/at/3mp8w3wk36k2k6mmj5pbbr/Optimize_your_game_performance_for_mobile__XR__and_the_web_in_Unity_Unity_6_edition_e-book.pdf [doc] (UNITY-GF1-011, UNITY-GF1-C2)
