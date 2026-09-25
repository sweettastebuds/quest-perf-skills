---
name: xr2-shader-cost-model
description: "Adreno hardware shader cost model on Quest 2/3/3S: fp16 vs fp32 rate, register (GPR) pressure and wave occupancy, wave64/128 divergence, branch costs, instruction and binding cliffs, varyings and constants, transcendental cost, and texture filtering and cache behaviour. Use when estimating what an instruction or sampler costs, reading shader stats (GPRs, instruction count), or explaining why half precision did or did not help. Writing URP HLSL: unity-shader-authoring."
---

# Adreno shader cost model (Quest 2 / Quest 3/3S)

Goal: **Throughput** (lower average GPU frame time per shaded pixel/vertex).
Nothing here targets frame-time variance directly; shader compile hitches are
Consistency and live in `unity-perf:unity-shader-hitches`.

Hardware scope: Quest 2 = Adreno 650 (A6xx), Quest 3 and Quest 3S = Adreno
740v3 (A7xx, same GPU on both, A2-001). The model is API- and
Unity-version-independent unless a line is tagged; tool steps are tagged
`Vulkan` / `GLES`. Qualcomm publishes no SP/ALU count, FLOPS or clock for
either GPU (A2-004): most per-op ratios below are **proxies** measured on the
Adreno 640 (A6xx) and Adreno X1 (A7xx) and are tagged as such.

## When to use / when not

Use when:
- A draw is confirmed shader-bound and you need to know *why*: "how expensive
  is this instruction", "GPR count", "occupancy", "wave divergence", "fp16
  rate", "why half did or did not help", "texture filtering cost".
- Reading RenderDoc Meta Fork shader stats (instruction counts, full/half
  register footprint, scratch) or per-draw ALU/EFU/texture counters.
- Estimating whether a shader crosses an Adreno cliff (instructions, UBOs,
  textures+SSBOs, samplers).

Do not use; go to the sibling instead:
- Not yet sure the frame is GPU-bound: `quest-perf:quest-triage`.
- Writing or fixing URP HLSL / Shader Graph (half, REAL_IS_HALF, discard, A2C,
  keywords vs branches in Unity terms, SPI macros):
  `unity-perf:unity-shader-authoring`. It cites this model; this skill does
  not repeat Unity authoring rules.
- LRZ, early-Z, GMEM, bins, overdraw, UBWC, binning-pass vertex cost:
  `arm-mobile-hw-perf:xr2-adreno-architecture`.
- What each Adreno counter means, Qualcomm healthy ranges, Offline Compiler
  and Snapdragon Profiler status: `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
- How to run ovrgpuprofiler / RenderDoc / Perfetto in general:
  `quest-perf:quest-profiling-toolkit`.
- GLES program binaries, mediump emission, GLES-side limits:
  `gles3-perf:gles-shader-binaries`.
- DRAM bytes and power of texture traffic: `arm-mobile-hw-perf:xr2-bandwidth-power`.
- Level/clock pinning and throttling: `quest-perf:quest-levels-thermal`.

## Diagnose first

Every millisecond number is meaningless without the GPU level/clock beside it:
Quest 3/3S spans 285-599 MHz from L0 to L5, about 2.1x (A2-008).

1. **Isolate app GPU cost** (Quest 2/3/3S, both APIs; A3-051):
   ```sh
   adb shell setprop debug.oculus.gpuLevel 4
   adb shell setprop debug.oculus.cpuLevel 4
   adb shell setprop debug.oculus.foveation.level 0
   adb shell setprop debug.oculus.foveation.dynamic 0
   adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SKIP_RENDERING --ei milliseconds 60000
   ```
   Pinned levels still throttle when hot; check PLS. Disable dynamic
   resolution while profiling (A3-052).
2. **ALU-bound or fetch-bound?** Realtime counters, IDs resolved on the device
   (IDs are list positions and differ per device/runtime, A2-087, Q1-065):
   ```sh
   adb shell ovrgpuprofiler -m -v          # list metrics with descriptions
   adb shell ovrgpuprofiler -r"1,4,5,6,7,8" # e.g. Clocks/Second, %Tex Fetch Stall, L1 miss/px, %Tex L1/L2 Miss, %Stalled on SysMem
   ```
   The IDs above follow Meta's example list; re-map them from `-m` on your
   device. No more than 30 metrics per run (Q1-066). Sustained
   `% Texture Fetch Stall` ≥ ~16% = fetch-bound (Qualcomm healthy range under
   ~2%, A3-054); low stall with the GPU still over budget points at ALU,
   confirmed per draw in step 3 (`% Shaders Busy`, ALU counts).
3. **Per-draw split** (Quest 2/3/3S, both APIs): RenderDoc Meta Fork draw-call
   trace gives Clocks, % Shaders Busy, % Texture Fetch Stall, Fragment ALU
   Instructions (Full) and (Half), EFU counts, % Shader ALU Capacity Utilized
   (U3-005), and texture-side `% Anisotropic/Linear/Nearest Filtered`,
   `% Non-Base Level Textures`, `% Texture L1 Miss` (A3-040). Scripted:
   ```sh
   renderdoccmd adb-list
   renderdoccmd adb-launch-drawcall-profiling --device <SERIAL> --package <pkg>
   renderdoccmd adb-capture --device <SERIAL> --ident <IDENT> --frames 1
   ```
   (A3-044). Per-draw ovrgpuprofiler (`-x`) adds stalls: compare draws within
   one trace only, and run `ovrgpuprofiler -d` afterwards (A2-088, Q1-067).
4. **Static shader stats** `Vulkan`: RenderDoc Meta Fork > Pipeline State >
   View reads VK_KHR_pipeline_executable_properties: instruction counts (all,
   32-bit ALU, 16-bit ALU, complex/EFU, texture read, flow control), full /
   half / overall register footprint, scratch (U3-006). On GLES there is no
   equivalent in Meta's tools; see `gles3-perf:gles-shader-binaries`.
5. **Occupancy**: `% Wave Context Occupancy` low = GPR or instruction-cache
   thrash (A2-067, A2-090). That counter is named by Qualcomm for Snapdragon
   Profiler, which is treated as unsupported on Quest (A3-067); on Quest read
   the register footprint in step 4 instead [verify on device].

## Key numbers

| Fact | Value | Applies to | Source |
|---|---|---|---|
| fp16 vs fp32 fragment rate | about 2x speed and 2x power efficiency | all Adreno [doc]; double rate measured on A640 and X1 [measured] | A2-063, A2-064 |
| Conflict ARM-C15 | first A640 test: fp16 = fp32 rate; correction: double rate (the first test was GPR-limited by vectorised code). Resolved to double rate | A6xx proxy for Quest 2 | ARM-C15 |
| Precision conversion | `int4 + 1.0` ≈ 8 instructions instead of 1; implicit vec4→vec3 truncation +1 | all | A2-066 |
| Meta counter units | Fragment ALU reported in full units, 2 mediump = 1 full; vertex ALU never counts mediump | all Quest | U3-054 |
| Register sizes (stats view) | full reg = 128-bit (4×FP32), half reg = 64-bit (4×FP16); 128-bit holds 8×FP16 | `Vulkan` | U3-055 |
| Register budget per SP | reg_size_vec4 64 on A650 vs 96 on A7xx base, about 1.5x | Quest 2 vs Quest 3/3S | A2-003 [community] |
| Wave size | wave64 and wave128 modes on both | Quest 2, Quest 3/3S | A2-068 [community] |
| Vulkan subgroup size | no published number; query `VkPhysicalDeviceSubgroupProperties` on device | Quest 2, Quest 3/3S | A2-068 |
| Special functions (rsqrt, exp, log, sin) | 1/8 rate, ≈ 8 FMA-equivalents each; `pow` = exp2+log2 = two | A640 proxy [measured]; X1 grouping unconfirmed | A2-072 |
| Integer add | 1/2 rate; 64-bit int halves again | A640 proxy | A2-072 |
| Instruction cliff | penalty at each multiple of 2000 instructions (2256 LPAC compute) | `Quest 3/3S` (A7x); A6x no published number | A2-070 |
| Binding cliffs | each multiple of 16 unique UBOs, 16 textures+SSBOs combined, 32 vertex buffers | `Quest 3/3S` (A7x) | A2-070 |
| Samplers | 16 on A6x-A8x; fragment+compute share one sampler cache, vertex has its own | Quest 2, Quest 3/3S | A2-070 |
| GLES limits | 16 texture units, 14 UBO blocks per stage, 31 varying vectors | `GLES` Quest 2 and 3 | G2-069 [measured] |
| Constant RAM | keep all UBOs one shader references under 0.9 × 8192 = 7372 B | all | A2-074 |
| ALU:TEX balance | 1 full-rate fetch per fragment ≈ 16 full-precision ALU ops | **A5x only**; A6x/A7x no published number | A2-082 |
| Anisotropic 16x | up to 16x isotropic cost worst case; average under 2x | all | A2-078 |
| Combined vs separate samplers | separate sampler objects: 2-5% lower fill rate | all Adreno `Vulkan` | A2-083 |
| Texture L1 | 1 KB/uSPTP (A640, 68.1% hit in Wild Life Extreme); 2 KB/uSPTP (X1); L2 128 KB at ~47 cycles (A640) | proxies; 650/740 not published | A2-081 |
| Coalesced fetch groups | keep each group under 15; any scratch memory = poor performance | `Vulkan` stats page | U3-006 |

Full per-operation ordering with device applicability:
[cost table](references/cost-table.md). Read it when ranking two shader
variants by expected cost, or before benchmarking relative ALU throughput.

## Fixes, ranked by payoff ÷ effort

Each fix states its effect on average frame time (Throughput) and on variance.
None of these change frame-time variance by themselves unless noted.

### 1. Make fp16 real, then prove it: GPR count, not source code
- What: keep whole fragment chains in `half` (colour, normals, lighting terms);
  keep positions, UVs on large atlases and heavy trig/pow/exp in float. Do not
  alternate precisions inside one chain: every hop is a conversion
  instruction (A2-066, U3-055). Authoring detail (Shader Precision Model,
  `real`, Shader Graph precision): `unity-perf:unity-shader-authoring`.
- Why: up to about 2x ALU rate and about 2x ALU energy (A2-063); half registers
  are half the size, so fewer GPRs → more resident waves (U3-055, A2-067).
- Proof: Fragment ALU (Half) share up, 16-bit ALU count up, full register
  footprint down (U3-005, U3-006). RelaxedPrecision/mediump is a hint and the
  driver decides (U3-052, A2-065). If Half share is near zero, the change did
  nothing.
- Effect: average GPU ms down on ALU-bound draws only; zero on fetch-bound or
  bandwidth-bound draws. No variance effect. Quality: banding/swimming in
  half UVs or very bright HDR values [verify on device].
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` `Unity ≥ 2021.3` · Throughput.

### 2. Cut GPRs to raise occupancy
- What: fewer live values across texture fetches; do not force-unroll loops
  that contain fetches (unrolling hoists fetches and raises GPRs); pack
  interpolants; split shaders that spill (any scratch = poor) (A2-067, U3-006).
- Why: occupancy is limited mainly by GPRs; a stalled wave is only hidden if
  another resident wave is ready (A2-009).
- Effect: average GPU ms down on fetch-latency-bound draws (high
  `% Texture Fetch Stall` with modest ALU). Quest 3/3S has about 1.5x the
  register budget of Quest 2 (A2-003), so a shader at the GPR limit on Quest 2
  may be fine on Quest 3: profile Quest 2 first. No variance effect.
- Side effects: splitting a spilling shader adds a pass or draw; it has no
  image-quality cost.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` · Throughput.

### 3. Remove divergence and uniform uber-branches
- Branch cost ladder, cheapest first (A2-069):
  1. Vulkan specialization constant: free.
  2. Compile-time constant (Unity `multi_compile` / `shader_feature`): possibly free.
  3. Uniform (Unity `dynamic_branch`, material float): per-wave load and
     test, both sides may run, raises GPRs.
  4. Per-pixel computed value: likely both sides run.
- Divergence is paid per 64- or 128-wide wave (A2-068), far wider than Mali's
  16-wide warps, so a per-pixel branch that is "rarely taken" still costs the
  whole wave whenever any lane takes it. Prefer branchless `lerp`/`step` for
  short sides; keep real branches only where whole screen regions agree.
- Trade-off: moving to (2) adds variants, which adds first-use hitches and
  blob-cache pressure (G3-039): that is a Consistency cost handled by
  `unity-perf:unity-shader-hitches`. GLES has no specialization constants
  (G3-039).
- Effect: average GPU ms down on ALU-bound draws; no direct variance effect,
  but more variants risk first-use hitches (Consistency cost, see the
  trade-off bullet).
- Quality: none; lerp/step select gives the same result.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` · Throughput.

### 4. Stay under the cliffs
- Instructions: under 2000 per graphics shader on `Quest 3/3S` (A2-070).
  Quest 2 has no published threshold (A2-070, G2-069); treat instruction-cache
  stalls as the risk and split long shaders, especially low-fetch ones where
  the scheduler has nothing to swap in (A2-071).
- Bindings: ≤ 16 textures+SSBOs, ≤ 16 unique UBOs, ≤ 16 samplers. Big Lit
  variants with many texture slots can cross 16 textures (A2-070); on GLES,
  16 texture units is also the hard cap, so adding an SSBO to a 16-texture
  shader crosses the cliff (G2-069).
- Sampler sharing in Unity HLSL (reuse one sampler for textures with the
  same filter/wrap):
  ```hlsl
  // URP 14+/17 (Core.hlsl macros). _DetailAlbedo has no sampler of its own.
  TEXTURE2D(_BaseMap);      SAMPLER(sampler_BaseMap);
  TEXTURE2D(_DetailAlbedo);
  half4 d = SAMPLE_TEXTURE2D(_DetailAlbedo, sampler_BaseMap, uvDetail);
  ```
  Whether sharing reduces hardware sampler count on Quest's driver:
  [verify on device] in RenderDoc.
- Effect: avoids a step increase in average GPU ms; no variance effect.
- Quality: none if you split or share samplers correctly. Sharing forces
  textures to use the same filter and wrap mode.
- Tags: `Quest 3/3S` (instruction and binding cliffs) `Quest 2` (samplers)
  `Vulkan` `GLES` · Throughput.

### 5. Pack varyings and constants; hoist uniform math
- Varyings: each interpolated value takes a full 4-component slot and a GPR
  (A2-073, A2-067, G3-041). Two float2 UVs → one float4; put a scalar (fog)
  in a spare `.w`. Values that are uniform per draw belong in constants, not
  varyings (A2-073).
  ```hlsl
  // URP 14+/17, Core.hlsl included; SPI/multiview safe via the stereo macro.
  struct Varyings
  {
      float4 positionCS   : SV_POSITION;
      float4 uv01         : TEXCOORD0; // xy base UV, zw detail UV: one slot
      half4  normalWS_fog : TEXCOORD1; // xyz normal, w fog factor
      UNITY_VERTEX_OUTPUT_STEREO
  };
  ```
- Constants: pack scalars into float4 (or at least float2); keep the sum of
  UnityPerDraw + UnityPerMaterial + globals + light CBUFFERs a shader
  references under 7372 B so they stay in constant RAM (A2-074) [verify on
  device]. Prefer UBOs to push constants (A2-074).
- Uniform-only math is cheaper than per-pixel math: A650 and A7xx have a
  scalar ALU, and A7xx an "early preamble" that can hoist it per draw
  (A2-075, Turnip behaviour; Qualcomm driver unpublished) [verify on device].
  Precomputing on the CPU (material property set from C#) is the guaranteed
  version.
- Scalar ISA: `float4` math buys nothing per ALU op (A2-009); vectorising
  source for "SIMD" is useless and was what hid the fp16 gain in the first
  A640 test (A2-064).
- Effect: average ms down (fewer GPRs and varying slots); no variance effect.
- Quality: `half4` normals/fog carry fp16 precision [verify on device].
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` · Throughput.

### 6. Budget transcendentals
- About 8 FMA-equivalents each (A640 proxy, A2-072); `pow(x, n)` is two of them.
  For small integer `n`, write the multiplies; `rsqrt` over `1/sqrt`. Prefer
  built-ins over hand-written equivalents (A2-076). Group EFU ops moderately
  (U3-006). Watch the EFU count in the draw trace (U3-005).
- Effect: average ms down on EFU-heavy draws; no variance effect.
- Quality: none for exact rewrites (`x*x` for `pow(x,2)`); approximations
  change the result.
- Tags: `Quest 2` `Quest 3/3S` (proxy numbers, [verify on device]) · Throughput.

### 7. Texture filtering and fetch pattern
- Cost order: nearest/bilinear < trilinear < anisotropic (A2-078). Cap
  anisotropy per texture (Texture Import Settings > Aniso Level) instead of
  forcing 16x globally; floors at grazing angles are the VR worst case.
- Always compress (ASTC first, then ETC2; A2-086, A3-015) and always mip
  minified textures: mips coalesce fetches (A2-080). No 3D textures where a 2D
  atlas works (A2-080).
- Explicit-gradient sampling (`SAMPLE_TEXTURE2D_GRAD`, triplanar, parallax,
  virtual texturing) costs more than a plain sample and gradients are not
  cached: every repeat pays again (A2-079).
- Dependent/random UVs thrash a 1-2 KB L1 (A2-081 proxies). Keep quad
  neighbours on neighbouring texels (A2-080).
- Shadow compares: use comparison samplers (`TEXTURE2D_SHADOW` +
  `SAMPLER_CMP`, `SAMPLE_TEXTURE2D_SHADOW`) to get hardware PCF instead of
  manual multi-tap depth compares (A2-085).
- Effect: average ms down on fetch-bound draws; no variance effect.
- Quality: a lower Aniso Level blurs floors at grazing angles, which is
  visible in VR; SampleGrad removal can change triplanar blending.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` · Throughput (texture bytes
  also cut DRAM power: `arm-mobile-hw-perf:xr2-bandwidth-power`).

### 8. Buffers and samplers at the API boundary
- Read-only storage buffers go through the texture pipe; HLSL
  `StructuredBuffer` may compile to SSBOs. Prefer vertex buffers, then UBOs,
  where the data fits (A2-084). Unity GPU instancing / BRG / Entities Graphics
  data reads take this path [verify on device].
- Combined image samplers are the fast path; separate samplers lose 2-5% fill
  rate (A2-083). Unity HLSL declares texture and sampler separately; whether
  Unity's Vulkan output on Quest emits combined samplers is unknown (Known
  unknown, A2-083). Not actionable until a RenderDoc capture shows it.
- Effect: small average fill-rate gain (2-5% for combined samplers, A2-083);
  no variance effect.
- Quality: none.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` · Throughput.

## Verify

- Same scene, same pinned GPU level, same resolution, foveation off
  (A3-051). A/B the one draw in a RenderDoc Meta Fork draw-call trace, then
  confirm frame-level `app_gpu_time` in OVR Metrics over a 60 s fixed-camera
  run at the pinned level (`quest-perf:quest-profiling-toolkit`).
- fp16 fix: Fragment ALU (Half) should dominate (Full) for that draw
  (G3-042); full register footprint should drop. The draw's Clocks should
  fall; up to about half on a purely ALU-bound draw (A2-063), close to zero
  on a fetch-bound one. No published Quest-specific speedup (U3-054): the
  number is what you measure.
- GPR fix: register footprint down, `% Texture Fetch Stall` down.
- Texture fix: `% Anisotropic Filtered` down, `% Texture L1 Miss` under 50%,
  `% Texture Fetch Stall` toward the ~2% healthy range (A3-040, A3-054).
- Cliff fix: instruction count under 2000 (Quest 3/3S), bindings under 16.
- Record GPU level or `Clocks / Second` with every number. A 60-120 s run is
  enough for a throughput A/B; this skill's changes need no 20-30 min
  thermal run unless they were made to recover thermal headroom
  (`quest-perf:quest-levels-thermal`).
- Relative ALU throughput Quest 2 vs Quest 3/3S, or half vs float on your
  build: benchmark in [cost table](references/cost-table.md#measuring-alu-throughput-a2-004).

## Pitfalls and myths

- **"half is always 2x."** Only if the compiler keeps values in half
  registers. The original A640 test showed no gain because vectorised code
  raised register pressure (A2-064, ARM-C15). Check stats, not source.
- **"half in the vertex shader saves ALU."** Meta's counters exclude mediump
  from vertex ALU counts; the inference is that vertex shaders gain nothing
  from half on Quest (U3-054) [verify on device].
- **"`2.0h` literals keep the chain in half."** Unity treats them as float
  (A2-065, U3-052); use `(half)2.0` or `half(2.0)`.
- **"half in a CBUFFER/StructuredBuffer saves bandwidth."** Stored at 32 bits
  (A2-065, U3-052).
- **"Clean compile = no precision problems."** Core RP suppresses warning
  3205 on mobile/GLES3 (U3-053).
- **"vec4 math is free SIMD."** Adreno is scalar (A2-009). Mali/PowerVR
  vec4-era advice does not transfer.
- **"A uniform branch is free."** Only specialization constants are; uniform
  branches may run both sides and raise GPRs (A2-069).
- **Mali numbers on Adreno.** Mali's 16-wide warps, malioc cycle counts and
  Mali counters do not apply (see `arm-mobile-hw-perf:xr2-adreno-architecture`).
- **Phone Adreno 740 numbers.** Quest's 740v3 has the same topology but a
  different chip id; phone clocks, GMEM and benchmarks do not copy over
  (A2-002).
- **Clocks from the profiler page.** ovrgpuprofiler's page says 690/492 MHz
  for Quest 3/3S; the levels table says 599 MHz at L5 (ARM-C3, A3-100).
  Budget with the levels table.
- **"16:1 ALU:TEX."** That is A5x only (A2-082). On Quest measure balance
  with `% Shaders Busy` vs `% Texture Fetch Stall`.
- **Offline Compiler numbers as ground truth.** Quest runs Meta-built
  drivers; phone-driver output may differ (A2-089) [verify on device].
- **Turnip debug flags** (`nolrz`, `sysmem` ...) do not exist on Quest's driver
  (A2-092).

## Sources

All accessed 2026-09-24.
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html [doc]
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md [doc]
- https://chipsandcheese.com/p/correction-on-qualcomm-igpus [measured]
- https://chipsandcheese.com/p/the-snapdragon-x-elites-adreno-igpu [measured]
- https://chipsandcheese.com/p/inside-the-snapdragon-855s-igpu [measured]
- https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py [community]
- https://docs.mesa3d.org/drivers/freedreno.html [community]
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-ai-tools/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/SL-Use16BitPrecisionInShaders.html [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl [doc]
- https://opengles.gpuinfo.org/displayreport.php?id=6387 [measured]
- https://opengles.gpuinfo.org/displayreport.php?id=8023 [measured]
