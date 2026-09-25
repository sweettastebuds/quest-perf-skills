---
name: unity-shader-authoring
description: "Writing and fixing cheap URP HLSL and Shader Graph for Quest 2/3/3S: half precision and RelaxedPrecision, clip/discard and alpha-to-coverage vs LRZ, depth-write and blend states that disable early-Z, keywords vs uniform branches, single-pass instanced macros, Quest shader keywords, and texture sampling choices. Use when a shader or material is GPU-expensive, alpha-tested foliage is slow, when writing or reviewing custom URP shaders, or asking \"should I use half\". Hardware cost reasoning: arm-mobile-hw-perf:xr2-shader-cost-model."
---

# URP shader authoring for Quest (throughput)

Goal: **Throughput** (lower average GPU frame time per shaded pixel). First-use
hitches, variant counts and PSO warmup are Consistency and live in
`unity-perf:unity-shader-hitches`.

Scope: URP 12 (Unity 2021.3), URP 14 (2022.3), URP 17.x (6000.0-6000.6);
Quest 2 (Adreno 650), Quest 3/3S (Adreno 740); Vulkan and GLES unless tagged.

## When to use / when not

Use when:
- A capture points at one material or shader as the expensive draw (high
  Clocks, fragment ALU, or LRZ `Disabled` on a big draw).
- You are writing or reviewing custom URP HLSL or Shader Graph for Quest.
- "Should I use half", "clip() cost", "alpha-tested material is expensive",
  "keyword or branch", "Shader Graph precision", "right eye missing".

Do not use; go to the sibling instead:
- Not yet sure the app is GPU-bound: `quest-perf:quest-triage`.
- Why an instruction, GPR count, wave divergence or fp16 rate costs what it
  does: `arm-mobile-hw-perf:xr2-shader-cost-model` (this skill cites it, does
  not repeat it).
- LRZ/early-Z/overdraw hardware mechanics, transparency and particle overdraw:
  `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Hitch on first use, variant explosion, stripping, GSC/PSO warmup:
  `unity-perf:unity-shader-hitches`. GLES program binaries and GLES precision
  emission: `gles3-perf:gles-shader-binaries`.
- Full-screen passes, load/store, Render Graph merging:
  `unity-perf:unity-render-graph-tiling`.
- Light counts, shadows, Forward vs Forward+: `unity-perf:unity-lighting` and
  `unity-perf:unity-urp-settings` (Depth Priming Mode also lives there).
- Counter glossary and capture recipes: `quest-perf:quest-profiling-toolkit`.

## Diagnose first

1. **Confirm GPU-bound at a fixed GPU level** (`quest-perf:quest-triage`). A
   shader fix does nothing for a CPU-bound frame.
2. **Find the draw and its LRZ state** with ovrgpuprofiler per-draw counters
   (Quest 2/3/3S, both APIs):
   ```sh
   adb shell ovrgpuprofiler -e <package>      # detailed mode; restart the app
   adb shell ovrgpuprofiler -x -m             # list per-draw counter IDs on THIS device
   # replace IDs with the ones -x -m printed on this device (Q1-065)
   adb shell ovrgpuprofiler -t3 -x="1,2,3,4,12,15,16,17,18,22,27,28,29,38,49,50"
   adb shell ovrgpuprofiler -d                # ALWAYS turn detailed mode off
   ```
   Each draw prints `LRZ State: TestEnabled, WriteEnabled <0x03>`,
   `TestEnabled` (write off: blend/ColorMask/stencil + ZWrite, A2-033, or a
   per-draw discard/A2C), `Disabled`, or `Unknown(old driver?)`. Detailed mode costs about 10% GPU time, and
   per-draw timings compare draws only within one trace (Q1-067, Q1-073).
   The first big draw after which every later draw reads LRZ `Disabled` is
   the state killer (see [LRZ state table](references/lrz-state-table.md)).
3. **Per-draw ALU vs fetch split** in a RenderDoc Meta Fork draw-call trace:
   Clocks, % Shaders Busy, % Texture Fetch Stall, Fragment ALU Instructions
   (Full) and (Half), EFU counts (U3-005). Fragment ALU is reported in
   full-precision units, 2 mediump = 1 full (U3-054). Half share near zero on a
   shader you wrote in `half` means the compiler did not keep fp16.
4. **Static stats (Vulkan only):** RenderDoc Meta Fork, Pipeline State > View
   shader stats: 32-bit vs 16-bit ALU count, texture reads, full/half register
   footprint, scratch memory (U3-006). On GLES use the Adreno Offline Compiler
   or Snapdragon Profiler (G3-042).
5. **Unity side:** Frame Debugger in the Editor for which pass/keywords a draw
   uses; enable Strict shader variant matching in a test build (2022.3+) so a
   missing variant shows the error shader instead of a silent fallback (U3-073).
6. **SPI correctness:** if the right eye is missing or draws double, check the
   stereo macros before anything else (G2-054, U3-042). Debug shader
   `XR/StereoEyeIndexColor` paints left green, right red (U3-044).

## Key numbers

| Number | Meaning | Source | Applies to |
| --- | --- | --- | --- |
| up to 2x speed and 2x power efficiency | mediump (fp16) vs highp fragment arithmetic | Qualcomm (G3-026, A2-063) [doc]; double-rate fp16 measured on Adreno 640 proxy (A2-064) [measured] | Adreno fragment shaders, Quest 2/3/3S; no vertex claim |
| no published number | measured half vs float speedup on Adreno 650 vs 740 | unity.md Known unknowns | measure: twin variants, Fragment ALU Full/Half + GPU ms |
| 1 -> ~8 instructions | `int4 + 1.0` implicit conversion example | Qualcomm (A2-066) [doc] | all Adreno |
| 25-50 instructions | Meta's "sweet spot" per shader; vendor heuristic, weight by pixel coverage | Meta (U3-007) [doc] | all Quest |
| under 15 per group; any scratch = poor | coalesced texture fetches per group; scratch memory | Meta shader stats page (U3-006) [doc] | Vulkan |
| 32-bit | storage of a `half` in a constant buffer: saves ALU/registers, not bandwidth | Unity (U3-052, G3-033) [doc] | Unity 6.x docs, precision model 2021.3+ |
| step 0.5 at 512-1024, 1.0 at 1024-2048 | fp16 value spacing; unsafe for world position, big UV tiling, `_Time`, depth | IEEE fp16 via Unity 2019.4 page (G3-031) [doc] | any mediump math |
| up to 4x fill rate | early-Z rejection; lost with depth write from shader, discard, A2C | Qualcomm (A2-038) [doc] | all Adreno |
| 128 keywords | above this per shader, small runtime penalty; 4 reserved | Unity (U3-072) [doc] | 2021.2+ keyword system |
| 16 warn / 32 error channels | Shader Graph custom interpolator thresholds (each varying costs a GPR, A2-067) | Unity source (UNITY-GF1-004, UNITY-GF2-001) [doc] | Shader Graph 12-17 |
| 2x CPU draw cost | Multi-Pass vs Multiview, the fallback a broken SPI shader tempts you into | Meta (U3-041) [doc] | OpenXR plug-in |
| 0.14 ms, 0.23 ms, 4.96 -> 3.35 ms, ~0.2 ms, regs 10 -> 8 / occupancy 50% -> 75% / 4.63 -> 4.25 ms | Unity 6.5 Quest shader optimizations: alpha-output keyword, ortho check, shadow back-face early-out (contrived scene), lighting early-out, partial loop unroll | Meta GDC 2026 talk, auto-captions (QUEST-GF2-011) [doc] | Unity ≥ 6000.5, device and API not stated [verify on device] |
| no published number | discard cost, A2C cost, Shader Graph vs hand HLSL delta | unity.md Known unknowns | measure per Verify |

## Fixes, ranked by payoff ÷ effort

Paste-ready shaders and snippets for each fix are in
[urp-hlsl-templates.md](references/urp-hlsl-templates.md): read it when you
need to write or rewrite a shader, or need the per-URP-version differences.
Read [lrz-state-table.md](references/lrz-state-table.md) when a trace shows LRZ
`Disabled` or you are auditing material states; it also holds a C# material
audit.

### 1. Remove render states that kill LRZ for the rest of the pass

- **Change:** find draws that write depth together with a state Qualcomm lists
  as LRZ-hostile, and fix them:
  - `ZTest Always` + `ZWrite On` mid-frame (custom sky, "always on top" gizmo)
    disables LRZ test **and** write until the next depth clear (A2-032). Set
    `ZWrite Off`, or draw it last.
  - Blending, `ColorMask`, any `Stencil {}` block, or framebuffer fetch **plus**
    `ZWrite On` disables LRZ write until the next clear (A2-033). Transparent
    materials: `ZWrite Off` (URP default for Surface = Transparent). Stencil
    portal/mask draws that write depth: move after all opaques.
  - Depth-compare direction flips (`ZTest GEqual`/`Greater` in a `LEqual`
    pass, reversed-Z tricks) followed by a depth write: LRZ test and write off
    until the next clear (A2-032). Sources conflict: Qualcomm [doc] says until
    the next clear on all Adreno; Mesa [community] says A650+ tracks direction
    on the GPU (only pre-A650 lost LRZ for the rest of the pass), so the flip
    may survive on Quest 2/3/3S; the shipping driver's policy is unpublished
    (A2-031, U3-059) [verify on device]. Keep one direction in the main pass.
  - Per-draw note (not frame-wide): `SV_Depth` / RW UAV output turns LRZ test
    and write off for that draw only, plus early-Z off (A2-034, A2-038); see
    fix 2 and the per-draw table.
- **Effect:** average GPU time; payoff scales with the opaque overdraw that
  follows the offending draw. No published ms figure; measure per Verify.
  Variance: no change expected (steady per-pixel cost).
- **Cost:** none visually if the draw order is still correct.
- **Tags:** `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan` | Goal: Throughput.
  Unity mapping of Qualcomm's rules is inference [verify on device].

### 2. Alpha test: fewer clipped materials, drawn after opaques

- **Change:**
  - Turn Alpha Clipping off on any material whose alpha is constant. In URP 14+
    Lit, Alpha Clipping on an opaque material also sets `AlphaToMask` on when
    MSAA > 1; URP's own tooltip calls this an unnecessary cost (U3-061).
  - Keep clipped materials in the AlphaTest queue (2450) so they test against
    LRZ built by solid geometry. URP's material GUI does this; custom shaders
    need `"Queue"="AlphaTest"` (U3-060).
  - Split one Shader Graph into opaque and cutout assets instead of an
    artist-facing clip toggle (see fix 7).
  - Disable renderers faded to alpha 0: they still submit and shade (U3-064).
- **Effect:** `clip()`, A2C and sample-mask output disable LRZ **write** for
  that draw only, and early-Z for that draw (A2-034, A2-038). Partial-wave
  discard still runs the whole wave, so "early exit" rarely saves ALU (A2-041).
  Average GPU time; no published ms. Variance: no change expected (steady
  per-pixel cost).
- **Cost:** A2C off loses edge anti-aliasing on cutouts under MSAA.
- **Tags:** `Quest 2` `Quest 3/3S` `URP 14+` for A2C (URP 12 Lit has none)
  `GLES` `Vulkan` | Goal: Throughput.

### 3. Half precision in fragment chains, float where range matters

- **Change:**
  - Player Settings > Other Settings > Shader Precision Model: Platform
    default (lower precision on mobile) or Unified (the 16-bit precision
    manual page calls it "Uniform", U3-C5; same setting) (U3-051). Under
    Unified, samplers stay full precision unless declared `Texture2D<half4>` /
    `TEXTURE2D_HALF` (G3-028). 2021.3 wording differs (G3-028 note).
  - Fragment colour, normal, direction and lighting math in `half`; keep
    world position, UVs, `_Time`, depth and heavy trig/pow/exp in `float`
    (U3-057, G3-031). Declare colour maps `TEXTURE2D_HALF` (`Texture2D<half4>`)
    and depth `TEXTURE2D_X_FLOAT` / `SampleSceneDepth` (U3-052, G3-030).
  - Keep each expression chain in one precision; do not write `2.0h`, it is a
    float literal in Unity (U3-052, A2-066).
  - Per shader that needs `real` at full precision: `#define PREFER_HALF 0`
    before including Core.hlsl (U3-053, G3-029).
- **Effect:** fewer fragment ALU cycles and registers -> more waves, better
  latency hiding (U3-055). Average GPU time on ALU-bound draws; nothing on
  fetch-bound ones. `half` in vertex code buys no ALU saving on Quest (U3-054,
  inference). Variance: no change expected (steady per-pixel cost).
- **Cost:** banding or UV swimming if range-sensitive values go half.
  `half` is a hint (RelaxedPrecision on Vulkan, mediump on GLES); confirm in
  the Half ALU counter (A2-065, G3-027).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 2021.3` `URP 12+` `GLES` `Vulkan`
  Goal: Throughput.

### 4. Unity 6.5+: let URP's Quest paths do the work

- **Change:**
  - Use the Meta Quest build profile (6.1+) and, for lit surfaces, call SRP
    library lighting and shadow functions (`GetMainLight`, `LightingLambert`,
    `UniversalFragmentPBR`) instead of hand-rolled lighting: 6.5+ inherits the
    Quest optimizations under `UNITY_PLATFORM_META_QUEST` (U3-066, U3-067).
  - URP Asset > Lighting > Additional Lights > Per Object Limit = 1 enables
    `META_QUEST_LIGHTUNROLL` (U3-068).
  - Orthographic cameras (UI, minimap): add `META_QUEST_ORTHO_PROJ` in
    Project Settings > Graphics > Shader Build Settings > Keyword Declaration
    Overrides, or they render wrong (U3-069).
- **Conflicts:** spelling: the manual page and QUEST-GF2-011 write
  `_META_QUEST_ORTHO_PROJ`; master Lit.shader declares `META_QUEST_ORTHO_PROJ`
  (X-C8, resolved for master; re-check your 6000.5/6000.6 URP package).
  Version: U2-056 dates the build-profile optimizations to 6.1+, U1-036/U3-066
  to 6.5; the resolution is profile 6.1+, shader optimizations 6.5+ (X-C7).
- **Effect:** talk figures in Key numbers; average GPU time.
- **Cost:** Per Object Limit = 1 drops extra lights beyond one per object
  (quality decision, QUEST-GF2-011); `META_QUEST_LIGHTUNROLL` is a
  `multi_compile` that raises variant count and build time (U3-068);
  ortho cameras break without `META_QUEST_ORTHO_PROJ`. Variance: none
  expected at runtime; new variants are a hitch risk, see
  `unity-perf:unity-shader-hitches`.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 6000.5` `URP 17` `Vulkan` (profile
  default). Goal: Throughput. Not in 6.0 LTS or 6.3 LTS.

### 5. Keywords vs uniform branches

- **Change:**
  - Artist toggles: `#pragma shader_feature_local_fragment _FEATURE_ON`
    (compiled only when used; `_local`/`_fragment` cut counts, U3-071, U3-072).
  - `dynamic_branch` (2022.1+) only when both sides cost about the same; it
    becomes a per-draw uniform and an `if` (U3-071). On Adreno a uniform branch
    is a per-wave test and both sides may run; the worst side sets the
    register count; keywords behave like compile-time constants (A2-069).
    Unity recommends `dynamic_branch` only "if your shaders run on a fast
    GPU" with symmetric branches (U3-071); Quest is not that case, so default
    to keywords and use `dynamic_branch` only where PSO count is the proven
    problem.
  - 6.3+: Graphics > Shader Build Settings can retype URP `multi_compile` sets
    to `shader_feature` or `dynamic_branch` per build profile (U3-074). 6.6:
    Shader Constant Defines bake a per-profile constant without a variant
    (U3-075).
- **Effect:** keywords = best average GPU time, more variants/PSOs;
  `dynamic_branch` = fewer PSOs (Consistency), possible ALU/GPR cost
  (Throughput). Check registers in the Vulkan stats for both. Variance:
  keywords add variants/PSOs, a first-use hitch risk (see
  `unity-perf:unity-shader-hitches`).
- **Cost:** keywords add variants/PSOs (hitch risk, Consistency);
  `dynamic_branch` can raise GPRs on every pixel.
- **Tags:** `Unity ≥ 2022.3` for `dynamic_branch` `Unity ≥ 6000.3` for Shader
  Build Settings `Unity ≥ 6000.6` for constant defines `GLES` `Vulkan` | Goal:
  Throughput (with a Consistency trade).

### 6. Per-material foliage depth prepass

- **Change:** for expensive alpha-tested foliage, a depth-only pass that clips
  and writes depth, then the shading pass with `ZTest Equal`, `ZWrite Off` and
  no `clip()` (U3-062). Template in the reference.
- **Effect:** the costly shading runs without discard and once per visible
  pixel; the prepass pays vertex work twice. Meta: "experiment, results vary".
  Not URP's global Depth Priming, which Unity says to keep disabled on Quest
  (U3-058). Variance: no change expected (steady per-pixel cost).
- **Cost:** second pass doubles vertex/binning work; `ColorMask 0` + `ZWrite`
  turns off LRZ write for later draws (A2-033).
- **Tags:** `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan` | Goal: Throughput
  [verify on device].

### 7. Shader Graph settings

- **Change:**
  - Graph Settings > Precision = Half; check with Color Mode = Precision (blue
    Single, red Half). A node fed Half and Single resolves to Single; one
    Position node can promote everything downstream (U3-056).
  - Leave the URP target's **Allow Material Override** off for high-count
    environment graphs. On, it turns `_ALPHATEST_ON`, `_SURFACE_TYPE_TRANSPARENT`
    and others into `shader_feature` keywords, makes ZTest/ZWrite/Cull/Blend/
    AlphaToMask material-driven, and always generates DepthOnly and
    ShadowCaster passes (UNITY-GF2-002).
  - Terrain and layered materials: hand-written HLSL can unpack and blend
    normals once instead of per Sample Texture node (UNITY-GF1-006,
    [community]); generated temporaries are compiled away, so code length is not
    a cost signal. Unity staff counter that hand HLSL has no stable API across
    upgrades (same thread).
- **Effect:** average GPU time via fp16 ALU and no per-material clip/A2C;
  fewer variants. Variance: no change expected (steady per-pixel cost).
- **Cost:** half banding on position-fed chains; artists lose per-material
  surface toggles.
- **Tags:** `Shader Graph 12+` `URP 12+` `GLES` `Vulkan` | Goal: Throughput.

### 8. SPI/multiview macros in every custom shader

- **Change:** `UNITY_VERTEX_INPUT_INSTANCE_ID`, `UNITY_VERTEX_OUTPUT_STEREO`,
  `UNITY_SETUP_INSTANCE_ID`, `UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO`, and
  `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX` before reading any `_X` texture;
  camera textures via `TEXTURE2D_X` / `SAMPLE_TEXTURE2D_X` (G2-054, U3-044,
  U3-047). Do not strip `STEREO_MULTIVIEW_ON` (U3-048).
- **Effect:** correctness first; the payoff is never shipping Multi-Pass (about
  2x CPU draw cost, U3-041) because a shader was broken. Variance: no change
  expected.
- **Cost:** none.
- **Tags:** `Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan` | Goal: Throughput.

### 9. Housekeeping

- 6.1+: rename `_FORWARD_PLUS` / `USE_FORWARD_PLUS` to `_CLUSTER_LIGHT_LOOP` /
  `USE_CLUSTER_LIGHT_LOOP` in custom HLSL. The shim in Core.hlsl still works on
  6.1-6.5 and URP still sets both keywords, but it warns about compile time and
  will be removed "in a future release" (U1-033, UNITY-GF2-C1; 6.6/6.7 removal
  unchecked: grep `ForwardPlusKeyword.deprecated.hlsl` in your URP package).
  `Unity ≥ 6000.1` `URP 17.1+` | Goal: Throughput (keeps custom shaders on the
  clustered path when the shim goes). Effect: no runtime change on 6.1-6.5;
  avoids breakage when the shim is removed. Variance: no change expected.
  Cost: none; one extra variant avoided.
- No geometry shaders: they break the tiled flow (U3-065). Effect: average GPU
  time; no published ms. Variance: no change expected. Cost: rewrite the
  effect in vertex/compute. `all` | Goal: Throughput.

## Verify

- **Metric:** `app_gpu_time` (OVR Metrics Tool) at a pinned GPU level, plus the
  fixed draw's Clocks in a per-draw trace, same camera pose.
- **Expect:**
  - Fix 1: later opaque draws go from `Disabled` or `TestEnabled` to
    `TestEnabled, WriteEnabled`; Fragments Shaded drops.
  - Fix 3: Fragment ALU (Half) rises vs (Full) (G3-042); 16-bit ALU count
    and full-register footprint in the Vulkan stats move the same way.
  - Fix 4: compare Meta Quest vs Android build profile on the same 6.5+
    Editor; the only published deltas are the talk figures above.
  - No other published magnitude exists; report the measured delta, do not
    predict one.
- **Session:** three 60 s steady segments per variant with ovrgpuprofiler
  detailed mode **off** (it adds about 10%, Q1-067), then one 10-minute run to
  confirm the GPU level does not climb. Thermal drift is owned by
  `quest-perf:quest-levels-thermal`.

## Pitfalls and myths

- **"`2.0h` makes it half."** No: Unity treats it as float (U3-052, G3-032).
- **"half in a cbuffer saves bandwidth."** Stored at 32-bit (U3-052).
- **"A clean compile means no precision problems."** Core RP suppresses
  warning 3205 on mobile/GLES3 (U3-053); read the stats.
- **"clip() early-out saves work."** Rarely, per Qualcomm (A2-041).
- **"clip() poisons LRZ for the whole frame."** Only that draw's LRZ write
  (A2-034); ZTest Always/ZWrite and blend+ZWrite are the frame-wide killers.
- **Mali habits.** Adreno has no Forward Pixel Kill; keep opaques front-to-back
  (A2-039). Mali counters and tile sizes do not transfer.
- **Enable Depth Priming.** Keep it Disabled on Quest (U3-058).
- **LRZ internals come partly from Mesa's reverse-engineered driver**
  (U3-059/060, A2-035) [community]; Quest ships Qualcomm's driver. Qualcomm's
  own rules (A2-032 to 034) are [doc]; LRZ feedback is not confirmed there.
- **Blending cost numbers** on Meta's draw-call-analysis page are Quest 1 /
  Unity 2018 (U3-063): keep the direction, not the numbers.
- **GLES depth.** Unity's GLES path has no reversed Z (G3-035): depth
  reconstruction in custom shaders is less precise on GLES than Vulkan.
- **Shader Graph variant limit on 2021.3** is a per-user EditorPrefs value
  defaulting to 128 (UNITY-GF2-001): teammates can get different builds.
- **6.5 optimizations on LTS.** Not in 6.0 LTS or 6.3 LTS (U3-066).

## Sources

- https://docs.unity3d.com/6000.6/Documentation/Manual/SL-Use16BitPrecisionInShaders.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/GLES3.hlsl (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/Vulkan.hlsl (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/2019.4/Documentation/Manual/SL-DataTypesAndPrecision.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Precision-Modes.html (accessed 2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ (accessed 2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-1/ (accessed 2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-2/ (accessed 2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (accessed 2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (accessed 2026-09-24) [doc]
- https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ (accessed 2026-09-24) [doc] (auto-captions)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html (accessed 2026-09-24) [doc]
- https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html (accessed 2026-09-24) [community]
- https://chipsandcheese.com/p/correction-on-qualcomm-igpus (accessed 2026-09-24) [measured]
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGUI/BaseShaderGUI.cs (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/urp-universal-renderer.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html (accessed 2026-09-24) [doc]
- https://raw.githubusercontent.com/Unity-Technologies/Graphics/master/Packages/com.unity.render-pipelines.universal/Shaders/Lit.shader (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl (accessed 2026-09-24) [doc]
- https://unity.com/releases/editor/whats-new/6000.5.0 (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-conditionals-choose-a-type.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/SL-MultipleProgramVariants-declare.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-keywords-default.html (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Targets/UniversalTarget.cs (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/2021.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphPreferences.cs (accessed 2026-09-24) [doc]
- https://discussions.unity.com/t/urp-hdrp-shader-graph-code-gen-optimization/918879 (accessed 2026-09-24) [community]
- https://discussions.unity.com/t/urp-shadergraph-versus-writing-urp-shaders-with-lighting-by-hand/918888 (accessed 2026-09-24) [community]
- https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassInstancing.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassStereoRendering.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/renderer-features/how-to-fullscreen-blit-in-xr-spi.html (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/TextureXR.hlsl (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.1/Documentation/Manual/urp/upgrade-guide-unity-6-1.html (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/ShaderLibrary/ForwardPlusKeyword.deprecated.hlsl (accessed 2026-09-24) [doc]
