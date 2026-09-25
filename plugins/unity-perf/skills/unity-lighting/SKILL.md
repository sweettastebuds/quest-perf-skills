---
name: unity-lighting
description: "Lighting and shadow cost in URP on Quest 2/3/3S: baked vs mixed vs realtime lights, per-object light limits, shadow maps and cascades, lightmaps, light probes and Adaptive Probe Volumes, reflection probes, and HDR lightmap formats. Use when lights, shadows or GI cost GPU time, when choosing a lighting setup for a Quest scene, or when additional lights misbehave on device. Forward vs Forward+ choice: unity-perf:unity-urp-settings."
---

# Lighting and shadows (Unity URP on Quest)

Goal: **Throughput** (GPU time, memory, DRAM traffic); fixes 3, 8, 9, 10 and 12 also serve
**Consistency**. Evidence IDs: `research/unity.md` (U*), `research/quest.md` (Q*, QUEST-GF*),
`research/arm-mobile-hw.md` (A*), accessed 2026-09-24. Claims apply to Quest 2 and Quest 3/3S,
Vulkan and GLES, and the Unity/URP range in their tags unless stated.

Reference files:
- Read [references/lighting-setups.md](references/lighting-setups.md) when choosing a whole lighting
  setup for a content type (static interior, sun plus characters, many dynamic lights, MR, Unity 6
  with APV), or when you need the per-URP-version feature table, the shadow-atlas arithmetic or the
  lightmap format table.
- Read [references/lighting-code.md](references/lighting-code.md) when you need paste-ready code:
  the editor lighting audit (C#), the on-device A/B toggle and ASTC HDR probe (C#), a hardware-PCF
  main-light shader with the back-face early-out, and a Fast-Z-friendly ShadowCaster pass (URP
  HLSL).

## When to use / when not

Use when:
- GPU-bound and a capture attributes time to shadow-map surfaces, the lit opaque pass, or
  reflection/probe sampling.
- Choosing Subtractive vs Baked Indirect vs Shadowmask, realtime vs baked, light probes vs APV, or
  lightmap encoding for a Quest scene.
- Additional lights drop, pop, or render in blocky tiles on device.
- Lightmaps or probes take more memory on device than the Lighting window predicted.

When not:
- Bottleneck not yet known -> `quest-perf:quest-triage`.
- Forward vs Forward+ vs Deferred as a rendering-path decision, and other URP asset toggles ->
  `unity-perf:unity-urp-settings` (this skill supplies the light-count input to that decision).
- Shadow or lighting pass load/store, pass merging, Render Graph ->
  `unity-perf:unity-render-graph-tiling`.
- Custom lit-shader precision, keywords, SPI macros in general ->
  `unity-perf:unity-shader-authoring`; hitch the first time a light or shadow variant renders ->
  `unity-perf:unity-shader-hitches`.
- Texture compression, mip streaming, memory budgets in general -> `unity-perf:unity-memory-assets`,
  `quest-perf:quest-budgets-tiers`.
- LRZ / early-Z / overdraw hardware rules -> `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Dynamic resolution, render scale, FFR -> `quest-perf:quest-resolution-foveation`.
- Shadow casters from MRUK EffectMesh, passthrough cost -> `quest-perf:quest-mr-costs`.

## Diagnose first

1. **Confirm GPU-bound.** OVR Metrics Tool `app_gpu_time_microseconds` near the frame budget at
   locked levels, or Perfetto `FenceChecker::Wait` / `GPU completion` waits (Q1-052). Tool setup:
   `quest-perf:quest-profiling-toolkit`.
2. **Find the shadow surfaces (ovrgpuprofiler, Q1-067 to Q1-069).**
   ```
   adb shell ovrgpuprofiler -e com.company.app   # detailed mode; restart the app afterwards
   adb shell ovrgpuprofiler -t -l                # one line per surface, 100 ms capture
   adb shell ovrgpuprofiler -d                   # ALWAYS turn detailed mode off (~10% GPU overhead)
   ```
   Shadow maps are depth-only surfaces at shadow resolution (for example 2048x2048 with the default
   asset, U2-001); cascades live in one atlas. Meta's agent skill maps surface#0 to the eye buffer
   and surface#2+ to shadows and post, but that is a heuristic: identify surfaces by resolution,
   format and MSAA (Q1-052). Sum the shadow surfaces' ms; that is the ceiling of any shadow fix.
3. **Split lighting from shadows with an on-device A/B** (component in
   [references/lighting-code.md](references/lighting-code.md)): baseline, main-light shadows off,
   additional lights off (the component disables the listed `Light`s; lowering the per-object limit
   alone leaves their shadow maps and is ignored in Forward+, U2-012), Max Distance shortened. Each
   variant for 60 s at locked CPU/GPU levels for diagnosis (final verification uses 5 min, see
   Verify); compare mean and p95 GPU time. Discard the first seconds after a switch (a new variant
   may create a PSO, see `unity-perf:unity-shader-hitches`).
4. **Count what the scene asks for (Editor).** Run `Tools > Quest Perf > Audit Lighting` (C# in the
   reference): shadowed spot and point lights (a point light = 6 maps, U4-030/031), shadow-casting
   renderers, rendering path, per-object limit, probe blending, SH mode, lightmap count, formats and
   directionality. Frame Debugger works only with the mock HMD, not on Meta devices (U1-058); use it
   in the Editor to count `MainLightShadow` / `AdditionalLightsShadow` draws.
5. **Forward+ light density.** Assign the shader `Universal Render Pipeline > Debug > ForwardPlus`
   to see lights per tile (scale up to 32) (U2-027).
6. **Memory side.** Lighting window statistics give lightmap Memory Usage before build (U4-040); the
   audit prints each lightmap's runtime format. On device, read
   `SystemInfo.SupportsTextureFormat(TextureFormat.ASTC_HDR_6x6)` (probe in the reference) before
   using High Quality lightmaps or HDR cubemaps (U4-038). APV: URP Asset "Estimated GPU Memory Cost"
   plus the Memory Profiler package on device (U4-016).

## Key numbers

| Number | Source | Applies to |
|---|---|---|
| Forward: 1 main + 8 additional lights per object; visible additional lights per camera 32 on mobile, 16 on GLES 3.0 and earlier (extra lights are dropped, not cheaper) | U4-005 | `URP 12-17` `Forward` |
| Per Object Limit defaults to 4; ignored in Forward+ | U2-001, U2-012 | `URP 12-17` |
| Forward+: no per-object limit; per-camera limit one lower than Forward (main light counts) | U4-006 | `URP 14+` `Forward+` |
| Forward+ beats Forward from about 5 realtime lights (Meta, Viking Village; no ms published) [verify on device] | U2-027 [measured] | `URP 14-17` |
| Forward blends at most 2 reflection probes per object; more needs Forward+ | U4-021, U4-006 | `URP 14-17` |
| 6.6 GLES: MAX_VISIBLE_LIGHTS rises 16 -> 32 when "Use OpenGL ES 3.0 shaders" is off; Unity says this increases workload | U1-040 | `Unity ≥ 6000.6` `GLES` |
| New URP Asset defaults: shadow maps 2048, Max Distance 50, 1 cascade, soft shadows off, per-object limit 4 | U2-001 | `URP 12-17` |
| Max Distance 40 -> 10 lets a 1024 map replace 2048 with better near-field quality (1 cascade) | U4-029 | `URP 12-17` |
| Additional-light atlas 1024 holds 16 maps at 256; spot = 1 map, point = 6 maps | U4-030, U4-031 | `URP 12-17` |
| Soft shadows: Low = 4 PCF taps (6000.3 docs) vs PCF 3x3 (URP 14.0.3 changelog); Medium 5x5 tent; High 7x7 tent. Conflict U4-C3 | U4-025 | `URP 14+` |
| Depth-only pass with empty fragment shader and colour writes masked: Fast-Z at 2x rate | A3-026 | `Quest 2` `Quest 3/3S` |
| Quest shader opts (Meta GDC 2026, device/API unstated): shadow back-face early-out 4.96 -> 3.35 ms (contrived scene); lighting early-out ~0.2 ms; light-loop unroll 4.63 -> 4.25 ms, registers 10 -> 8, occupancy 50% -> 75% [verify on device] | QUEST-GF2-011 | `Unity ≥ 6000.5` `URP 17` |
| Lightmaps on Android/ASTC: dLDR, RGBM and HDR all 3.56 bpp (ASTC 6x6); ETC2 target: dLDR 4 bpp, RGBM 8 bpp | U4-035 | `Unity 2021.3-6000.6` |
| dLDR range [0, 2] (clamps above); RGBM 0 to 34.49 linear | U4-036 | all |
| Directional lightmaps: second texture, about 2x memory, two samples | U4-039 | all |
| Shadowmask: one extra lightmap-sized texture per atlas, up to 4 mixed lights per texel | U4-004, U4-043 | all |
| Max Lightmap Size default 1024; 2x Lightmap Resolution = 4x texels | U4-040 | all |
| Legacy probe: L2 SH, 27 floats, one interpolated probe per object; APV: 8 probes per pixel | U4-011 | APV `Unity ≥ 6000.0` |
| APV brick = 64 probes; default spacings 1, 3, 9, 27 m | U4-017 | `URP 17` |
| APV pool: Low 512, Medium 1024, High 2048 texels square, depth 4. Derived (not published): Low ~16 MiB at L1 / 32 MiB at L2; Medium ~64/128; High ~256/512 | U4-016 | `URP 17` |
| Realtime reflection probe, Every Frame: All Faces at Once 9 frames; Individual Faces 14 frames; No Time Slicing = one-frame update | U4-023 | all |
| Mixed-mode GPU cost, soft-shadow tier cost, APV cost, Forward vs Forward+ ms at equal light count | no published number; measure with the A/B in Diagnose step 3 | - |

## Fixes, ranked by payoff ÷ effort

Each fix: change, effect on average vs variance, cost, tags, goal.

### 1. Bake everything static; no realtime GI

Lighting window: static geometry Contribute GI, lights Baked or Mixed; Realtime Global Illumination
off; dynamic objects lit by probes. Meta: avoid realtime GI, limit per-pixel lights (U4-008,
Q4-071).
- Effect: removes per-pixel light loops and shadow passes for static content; lowers average GPU
  time. No variance effect.
- Cost: bake time, lightmap memory (see fix 8), no moving lights on statics.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3+` `URP 12+` `Vulkan` `GLES`. Goal: **Throughput**.

### 2. Pick the cheapest mixed mode that looks right

Lighting window > Mixed Lighting > Lighting Mode. Cost order, most to least: Distance Shadowmask >
Shadowmask > Baked Indirect > Subtractive (U4-001).
- **Subtractive**: only the brightest directional light casts realtime shadows; statics get no
  mixed-light specular (U4-002). Fits sun/key-light scenes. Use Realtime Shadow Color to match baked
  shadows.
- **Baked Indirect**: every shadow is realtime, so cost scales with Max Distance (U4-003).
- **Shadowmask**: extra texture per atlas (U4-043); Quality > Shadowmask Mode = Shadowmask, never
  Distance Shadowmask on Quest (renders static casters realtime inside Max Distance, U4-004).
- Subtractive and Shadowmask are Forward-optimised; do not combine with Deferred (U4-007).
- Effect: average GPU time; no ms per mode is published [verify on device].
- Cost: Subtractive gives statics no mixed-light specular and only one light casts realtime shadows;
  Shadowmask adds a lightmap-sized texture per atlas (U4-002, U4-043).
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3+` `URP 12+`. Goal: **Throughput**.

### 3. Shrink main-light shadows: distance first, then resolution and cascades

URP Asset > Shadows: Max Distance as short as the content allows, **1 cascade** as the starting
point to verify (U4-028), then lower Main Light Shadow Resolution (U4-029). Enable Conservative
Enclosing Sphere and re-tune splits (U4-033, `URP 15+`). Halving resolution quarters texels,
bandwidth and memory (U4-029 note).
- Effect: lowers the shadow surfaces' ms seen in Diagnose step 2, and DRAM traffic, which is the
  controllable part of power (ARM-GF2-003; physics in `arm-mobile-hw-perf:xr2-bandwidth-power`).
  Less heat means later throttling.
- Cost: shadow pop at the distance edge; fewer texels far away.
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `Vulkan` `GLES`. Goal: **Throughput**; lower DRAM power
  also delays thermal throttling (**Consistency**, ARM-GF2-003).

### 4. Kill shadow casters that do not need to cast

- Renderer > Lighting > Cast Shadows = Off on small props, floors, distant geometry; use a
  simplified proxy mesh set to Shadows Only for complex casters (U4-032).
- Characters: blob shadows (Meta 2018 tech note, U4-034, possibly stale) or a light cookie instead
  of realtime shadows (U4-032).
- Disable shadows entirely when near draw-call or geometry limits (Meta 2024, U4-034): the shadow
  pass re-submits every caster.
- Effect: fewer shadow-pass draws (CPU render thread) and vertex/binning work (GPU). Average only.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3+` `URP 12+` `Vulkan` `GLES`. Goal: **Throughput** (CPU
  and GPU).

### 5. Soft shadows off, or Low; set quality on the asset, not per light

URP Asset > Shadows > Soft Shadows off; if needed, Quality = Low (U2-009, U4-025). On Quest,
per-light Soft Shadow Quality is ignored from URP 17.0.0 / 6000.0.0b11; only the asset setting
applies (U4-026, U1-039, conflict U4-C5).
- Effect: fewer filter taps per shaded pixel in the lit pass. No Quest ms published; measure off /
  Low / Medium on a view where shadows fill the screen.
- Cost: aliased shadow edges.
- Tags: `Quest 2` `Quest 3/3S` `URP 14+` (tiers), `URP 12` on/off only. Goal: **Throughput**.

### 6. No shadowed point lights; cap additional-light shadows

A shadowed point light = 6 shadow maps, about the cost of 6 spot lights (U4-031). Prefer spot
lights, or disable Additional Lights > Cast Shadows on the asset (U2-014, U2-090). Size the atlas
from the count: at 256 per map a 1024 atlas holds 16 maps, a 512 atlas 4 (U4-030).
- Effect: removes whole shadow-atlas surfaces. Average only.
- Cost: point lights lose shadows; spot lights need re-aiming to cover the area.
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `Vulkan` `GLES`. Goal: **Throughput**.

### 7. Keep dynamic lights inside the right path's limits

- Forward: every object sees at most 1 main + Per Object Limit (max 8) additional lights (U4-005).
  Set Additional Lights to Per Vertex or Disabled if you can (U2-012).
- From about 5 realtime lights on screen, Forward+ wins in Meta's test (U2-027); the path choice
  itself is `unity-perf:unity-urp-settings`. On 2022.3, Forward+ in XR is unresolved (U1-C4): prefer
  Unity 6 for Forward+.
- `Unity ≥ 6000.5` with the Meta Quest build profile: Per Object Limit = 1 unrolls the light loop
  (`META_QUEST_LIGHTUNROLL`); Meta measured 4.63 -> 4.25 ms (QUEST-GF2-011). Cost: extra lights per
  object are dropped, more variants and build time (U3-068).
- `Unity ≥ 6000.6` `GLES`: keep "Use OpenGL ES 3.0 shaders" on unless you need 32 visible lights
  (U1-040). 2022.3 (URP 14) with many additional lights: check the URP 15.0.0 Quest additional-light
  regression fix is in your patch (U4-010) [verify on device].
- Effect: lowers average lit-pass time; no variance effect.
- Cost: lights past the limit are dropped per object and pop (U4-005).
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `Forward` `Forward+`, plus the per-bullet tags above. Goal:
  **Throughput**.

### 8. Lightmap memory: encoding, directionality, size

- Player > Other Settings > Lightmap Encoding: **Normal (RGBM) or Low (dLDR)**. Same 3.56 bpp on
  ASTC (U4-035); choose by range: dLDR clips above 2, RGBM can band (U4-036). Avoid High (HDR) until
  ASTC HDR is confirmed on the headset: without it Unity decompresses at load to RGB9E5 or RGBA
  Half, multiplying memory and load CPU (U4-038). HDR Cubemap Encoding follows the same scheme
  (U4-024).
- Directional Mode: Non-Directional halves lightmap memory and drops a sample (U4-039); Directional
  keeps baked normal-map response. Unresolved (U4-C2): decide by measured memory and GPU delta.
- Lighting > Max Lightmap Size and Lightmap Resolution: 2x resolution = 4x texels (U4-040). Repack
  Underused Lightmaps on; Fixed Lightmap Size only if GPU Resident Drawer needs it (it costs memory,
  U4-041, U4-044).
- Lightmap Streaming needs Mipmap Streaming (U4-045); a low resident mip looks blurry. Check
  `Texture2D.loadedMipmapLevel`.
- Effect: memory and texture bandwidth; average GPU time only slightly. The HDR fallback also adds
  load-time CPU (**Consistency** at load).
- Tags: `Unity 2021.3+` `Quest 2` (6 GB, tightest) `Quest 3/3S`. Goal: **Throughput**.

### 9. Probes: legacy probes by default, APV only on Unity 6 and measured

- Light Probe Groups: one interpolated L2 probe per object (U4-011); cheapest per pixel.
- SH Evaluation Mode (URP Asset, advanced): Auto resolves to Per Vertex on mobile XR for legacy SH
  (U4-013). **With APV, set Per Vertex (or Mixed) explicitly**: 6000.3 source enables APV vertex
  sampling only for explicit values, so Auto may leave APV per-pixel on Quest (U4-014, conflict
  U4-C6) [verify on device].
- APV (`Unity ≥ 6000.0` `URP 17`): Memory Budget Low, SH Bands L1 as the Quest 2 starting point
  (U4-016 note); raise minimum probe spacing to cut probe count and memory (U4-017). Do not update
  the ambient probe via `DynamicGI.UpdateEnvironment` at runtime: documented very large cost
  (U4-019).
- APV runtime cost on Quest is unmeasured, and APV on GLES is disputed (U4-020: a community write-up
  says it needs compute; URP source shows no GLES block). Test a GLES 3.2 build for magenta/unlit
  objects and logcat warnings.
- APV streaming: GPU streaming (CPU -> GPU) and disk streaming (needs GPU streaming) (U4-018). No
  Quest hitch data; watch render-thread spikes during fast traversal. Goal for streaming:
  **Consistency**. Disk streaming also requires compute (U1-041), so on GLES plan for GPU streaming
  only [verify on device].
- Effect: lowers per-pixel probe fetch cost (average); streaming affects spikes (variance).
- Cost: legacy probes can leak light on large objects; per-vertex APV loses detail (U4-011).
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` (legacy probes), `Unity ≥ 6000.0` `URP 17` (APV), `Vulkan`
  (GLES unverified). Goal: **Throughput** (probe choice), **Consistency** (streaming).

### 10. Reflection probes: baked, compressed, no blending

- Baked probes; compression under Lighting > Environment > Reflections > Compression. Realtime
  probes are uncompressed and cost more to sample (U4-022).
- URP Asset: Probe Blending off, Box Projection off; Forward+ Probe Atlas Blending off (Meta: the
  atlas is too costly on Quest) (U2-013, U4-021). The 6000.5 source defaults atlas blending on; GRD
  makes it the default (U4-021).
- If a probe must be realtime: Refresh Mode = Via Scripting, Time Slicing = Individual Faces (14
  frames, lowest per-frame cost), Culling Mask on large occluders only. No Time Slicing does a full
  update in one frame and hitches (U4-023).
- Legacy Meta advice (Skybox None, ambient Color, no realtime reflections) is Gear VR era; measure
  the skybox in RenderDoc before removing it (U4-009).
- Effect: baked, compressed, unblended probes lower average sampling cost; time slicing removes a
  one-frame hitch (variance).
- Cost: hard transitions between probes; no parallax correction without Box Projection.
- Tags: `URP 14+` (blending toggles), all. Goal: **Throughput**; time slicing is **Consistency**.

### 11. Custom lit shaders: hardware PCF, back-face early-out, empty ShadowCaster

- Sample shadows through URP's `MainLightRealtimeShadow` / `SAMPLE_TEXTURE2D_SHADOW` (comparison
  sampler), never manual multi-tap depth compares: Adreno has hardware PCF (A2-085).
- Skip shadow sampling and lighting where `NdotL <= 0`. Unity does this for you in URP library
  functions on `Unity ≥ 6000.5` with the Meta Quest build profile (U1-036, X-C7 resolved 6.5+);
  hand-rolled lighting and 2021.3-6.4 need it written (QUEST-GF2-011); it pays only when it skips
  texture samples.
- Opaque casters: ShadowCaster pass with `ColorMask 0` and an empty fragment (no `clip()`, Alpha
  Clipping off) to get Fast-Z at 2x rate (A3-026). LOD Cross Fade uses alpha test (U2-010); check
  whether it reaches the caster.
- `Unity ≥ 6000.6` Quest builds: `DistanceAttenuation` takes three arguments (U1-038). Code:
  [references/lighting-code.md](references/lighting-code.md); HLSL in general: `unity-perf:unity-shader-authoring`.
- Effect: average GPU time only (Meta GDC figures in Key numbers). Cost: a dynamic branch;
  alpha-tested casters cannot use the empty-fragment caster.
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `Vulkan` `GLES`. Goal: **Throughput**.

### 12. Dynamic resolution: fix misaligned additional lights

With Meta dynamic resolution (the OS lowers render scale during a thermal event, A3-086), URP
additional lights misalign: Forward+ shows blocky tiles, Deferred/Deferred+ drift. Fix: tick Dynamic
Resolution on the CenterEyeAnchor camera or set `camera.allowDynamicResolution = true` before
rendering; in custom HLSL derive screen UVs from `_ScaledScreenParams`, not `_ScreenParams`
(Q3-053).
- Effect: correctness under the thermal fallback; no frame-time change.
- Cost: none to image quality.
- Tags: `Quest 2` `Quest 3/3S` `URP 14+` `Forward+` `Deferred` `Deferred+ (Unity ≥ 6000.1)`. Goal:
  **Consistency** (keeps the dynamic-resolution safety valve usable). Scale policy:
  `quest-perf:quest-resolution-foveation`.

## Verify

- **Metric:** OVR Metrics `app_gpu_time_microseconds` (mean and p95 of the 1 Hz rows) at locked
  CPU/GPU levels, same scripted route, before and after; plus the shadow surfaces' ms in
  `ovrgpuprofiler -t -l` (then `-d`). Mark segments with `AppendCsvDebugString` (Q1-020). Analysis
  script: `quest-perf:quest-profiling-toolkit`.
- **Expected size:** a shadow fix can recover at most the shadow surfaces' ms plus the lit-pass
  filter cost; a lighting-mode or light-limit change moves only the lit opaque pass. No published
  Quest delta exists for any single fix here except Meta's GDC figures (QUEST-GF2-011); treat those
  as upper-bound examples, not predictions.
- **Session:** 5 min per variant for the final A/B (`secondsPerVariant = 300`; the 60 s default is
  for Diagnose step 3); then one 20-30 min run of the final setup to confirm GPU level and render
  scale hold (no thermal decay), per `quest-perf:quest-levels-thermal`.
- **Memory:** Lighting window Memory Usage vs Memory Profiler on device; any lightmap or cubemap in
  RGBAHalf or RGB9E5 means the HDR fallback happened (U4-038).
- **Correctness:** walk the scene with dynamic resolution forced low; lights must stay aligned (fix
  12). Check for popping lights (per-object limit).

## Pitfalls and myths

- "Shadows are banned on Quest." Guidance loosened over time: legacy page no shadow buffers, 2018
  hard-only, 2024 disable only near draw-call/geometry limits. Treat shadows as a measured budget
  item (U4-C7).
- "Per-light soft-shadow quality from PC carries over." Ignored on Quest from URP 17 / 6000.0.0b11;
  the manual still describes per-light overrides (U4-C5). Blocky shadows are usually
  cascade/distance misconfiguration, not quality (U4-027 [community]).
- "Low soft shadows = 4 taps." Docs say 4 PCF taps, URP 14.0.3 changelog says PCF 3x3 (U4-C3); read
  your version's `Shadows.hlsl`.
- "SH Auto means per-vertex everywhere." True for legacy SH on mobile XR, maybe not for APV (U4-C6).
  Set it explicitly.
- "Non-Directional lightmaps always." Legacy Meta advice (U4-039); current Meta pages do not restate
  it (U4-C2). It costs baked normal-map response.
- "Use High Quality lightmaps for HDR." Qualcomm lists HDR and LDR ASTC profiles as supported on
  Adreno in general (A2-086), but no source confirms ASTC HDR on Quest 2 (Adreno 650) or Quest 3/3S
  (Adreno 740); Unity falls back to RGB9E5 or RGBA Half without it (U4-038, U4-049). Probe on device
  first.
- "APV Lighting Scenario blending works on Quest." U4-019 documents blending (spread with
  `numberOfCellsBlendedPerFrame`, a second pool); U1-041 says URP on mobile does not support
  scenario blending. Do not plan on it for Quest 2 or Quest 3/3S [verify on device].
- "Deferred saves light cost on Quest." Unity's untethered-XR guide recommends Forward because
  G-buffer loads are slow on tile GPUs (U1-034); soft shadows in Deferred on Quest failed with
  "variant not found" until 6000.7.0a3 (U1-035).
- "Dropping lights past the limit is free performance." Excess lights are dropped per object and pop
  visually (U4-005 note).
- "Block Aligned Padding fixes lightmap seams on Quest." It aligns to 4x4; Android lightmaps use
  ASTC 6x6 (U4-042). Inspect seams on device.
- GPU Resident Drawer needs Forward+ (6000.3 docs) or Forward+/Deferred+ (6.1+ per other findings;
  X-C9) and pushes Fixed Lightmap Size, which costs memory (U4-044). Batching decision:
  `unity-perf:unity-draw-calls-batching`.
- Orthographic cameras on `Unity ≥ 6000.5` Quest builds light wrongly unless the ortho keyword
  override is added (U1-037); details in `unity-perf:unity-shader-authoring`.

## Sources

All accessed 2026-09-24.
- https://docs.unity3d.com/6000.3/Documentation/Manual/lighting-mode.html [doc] (U4-001, U4-002, U4-004, U4-043)
- https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-Subtractive.html [doc] (U4-002)
- https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-BakedIndirect.html [doc] (U4-003)
- https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-Shadowmask.html [doc] (U4-004, U4-043)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/lighting/light-limits-in-urp.html [doc] (U4-005)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/rendering-paths-comparison.html [doc] (U4-006, U4-007, U4-021)
- https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ [doc] (U4-007, U4-008, U4-034, Q4-071)
- https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ [doc] (legacy; U4-008, U4-009, U4-039)
- https://developers.meta.com/horizon/blog/tech-note-unity-settings-for-mobile-vr/ [doc] (2018; U4-034)
- https://developers.meta.com/horizon/documentation/unity/unity-forward-plus-rendering/ [measured] (U2-027, U2-013)
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/rendering/forward-plus-rendering-path.html [doc] (U1-032, U1-C4)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html [doc] (U1-032, U1-041)
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/changelog/CHANGELOG.html [doc] (U4-010, U4-026)
- https://unity.com/releases/editor/whats-new/6000.0.0b11 [doc] (U1-039)
- https://discussions.unity.com/t/meta-quest-shadows-unsmoothed-low-resolution-regardless-of-settings/1552250 [community] (U4-027)
- https://unity.com/releases/editor/whats-new/6000.6.0f1 [doc] (U1-040)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc] (U1-040)
- https://unity.com/releases/editor/whats-new/6000.6.0b1 [doc] (U1-038)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc] (U1-034)
- https://unity.com/releases/editor/whats-new/6000.7.0a3 [doc] (U1-035)
- https://docs.unity3d.com/6000.1/Documentation/Manual/urp/upgrade-guide-unity-6-1.html [doc] (U1-033)
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/universalrp-asset.html [doc] (U2-018)
- https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manage-scene-data/ [doc] (Q4-033)
- https://docs.unity3d.com/6000.3/Documentation/Manual/LightProbes-TechnicalInformation.html [doc] (U4-011)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-concept.html [doc] (U4-011, U4-017)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/probevolumes-concept.html [doc] (U1-041)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html [doc] (U4-012, U4-021, U4-025, U4-028, U4-033)
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html [doc] (U4-013)
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipelineCore.cs [doc] (U4-013)
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs [doc] (U4-014)
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/Data/UniversalRenderPipelineAsset.cs [doc] (U4-014)
- https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/Runtime/Data/UniversalRenderPipelineAsset.cs [doc] (U2-001)
- https://discussions.unity.com/t/urp-adaptive-probe-volumes-per-vertex-quality-setting-location/942672 [community] (U4-015)
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/Runtime/Lighting/ProbeVolume/ProbeBrickPool.cs [doc] (U4-016)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-streaming.html [doc] (U4-018)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-bakedifferentlightingsetups.html [doc] (U4-019)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-skyocclusion.html [doc] (U4-019)
- https://gamedevllm.com/en/unity-6-urp-adaptive-probe-volumes-deep-dive-en/ [community] (U4-020)
- https://docs.unity3d.com/6000.3/Documentation/Manual/RefProbePerformance.html [doc] (U4-022, U4-023)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html [doc] (U4-024, U4-045)
- https://docs.unity3d.com/6000.3/Documentation/Manual/shadows-optimization.html [doc] (U4-025, U4-031, U4-032)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/shadow-resolution-urp.html [doc] (U4-029, U4-030)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html [doc] (U2-009)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html [doc] (U2-010, U2-014, U2-090)
- https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-TechnicalInformation.html [doc] (U4-035, U4-036, U4-038)
- https://docs.unity3d.com/6000.3/Documentation/Manual/texture-formats-reference.html [doc] (U4-038, U4-049)
- https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-reference.html [doc] (U4-039 to U4-042)
- https://docs.unity3d.com/6000.3/Documentation/Manual/urp/gpu-resident-drawer.html [doc] (U4-044)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html [doc] (U1-036, U1-037, U2-012, U3-068)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html [doc] (U1-058)
- https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ [doc] (GDC 2026 talk, auto-captions; QUEST-GF2-011)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html [doc] (A2-085, A2-086)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md [doc] (A3-026)
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc] (A3-086, Q3-053)
- https://developers.meta.com/horizon/blog/optimizing-for-success-meta-quest-3-gdc/ [doc] (ARM-GF2-003)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc] (Q1-067 to Q1-069)
- https://github.com/meta-quest/agentic-tools [doc] (Q1-052)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc] (Q1-020)
