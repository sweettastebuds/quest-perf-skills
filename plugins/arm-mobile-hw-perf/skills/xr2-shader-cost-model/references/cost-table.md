# Adreno operation cost table (Quest 2 / Quest 3/3S)

Relative costs only. Qualcomm publishes no SP/ALU count, FLOPS, texture-cache
size or clock for the Adreno 650 or 740 (A2-004); where a number comes from a
sibling GPU it is labelled **proxy**. All sources accessed 2026-09-24.

Device tags: **Q2** = Quest 2, Adreno 650 (A6xx). **Q3** = Quest 3 and Quest 3S,
Adreno 740v3 (A7xx, identical GPU on both, A2-001).

## ALU and precision

| Operation | Relative cost | Applies to | Source | Evidence |
|---|---|---|---|---|
| fp32 FMA/ADD/MUL (scalar) | 1 (baseline) | Q2, Q3 | A2-005, A2-006, A2-009 | [measured] proxy, [doc] |
| fp16 FMA/ADD/MUL | about 0.5 (double rate) if kept in half registers | Q2 (A640 proxy), Q3 (X1 proxy) | A2-063, A2-064, ARM-C15 | [doc], [measured] |
| vec4 op vs scalar op | 4 scalar ops: no vector speedup | Q2, Q3 | A2-009 | [doc] |
| fp32 ↔ fp16 conversion | +1 instruction per hop | Q2, Q3 | A2-066, U3-055 | [doc] |
| int ↔ float mix (`int4 + 1.0`) | about 8 instructions vs 1 | Q2, Q3 | A2-066 | [doc] |
| Implicit vec4 → vec3 truncation of a sample | +1 instruction | Q2, Q3 | A2-066 | [doc] |
| 32-bit integer add | about 2 (half rate) | A640 proxy | A2-072 | [measured] |
| 64-bit integer add | about 4 | A640 proxy | A2-072 | [measured] |
| rsqrt, exp, log, sin, cos | about 8 (1/8 rate) | A640 proxy; X1 grouping unconfirmed | A2-072 | [measured] [verify on device] |
| `pow` | about 16 (exp2 + log2) | A640 proxy | A2-072 | [measured] [verify on device] |
| Math on uniforms only | cheaper than per-pixel: scalar ALU (Q2, Q3), early preamble (Q3) | Turnip behaviour | A2-075 | [community] [verify on device] |
| Built-in vs hand-written equivalent | built-in preferred | Q2, Q3 | A2-076 | [doc] |

## Control flow and occupancy

| Item | Cost | Applies to | Source | Evidence |
|---|---|---|---|---|
| Branch on specialization constant | free (stripped) | `Vulkan` | A2-069 | [doc] |
| Branch on compile-time constant (Unity keyword variant) | possibly free | Q2, Q3 | A2-069, G3-039 | [doc] |
| Branch on uniform (Unity `dynamic_branch`) | per-wave load + test; both sides may run; raises GPRs | Q2, Q3 | A2-069 | [doc] |
| Branch on per-pixel value | likely both sides run | Q2, Q3 | A2-069 | [doc] |
| Divergence granularity | whole wave64 or wave128 | Q2, Q3 | A2-068 | [community] |
| Register budget per SP | reg_size_vec4 64 (Q2) vs 96 (Q3), about 1.5x | Q2, Q3 | A2-003 | [community] |
| Register file per partition | 64 KB (A730) vs 96 KB (X1) | A7xx proxies | A2-006 | [measured] |
| GPR → occupancy table | no published number; measure register footprint (RenderDoc stats, `Vulkan`) | Q2, Q3 | A2-067, U3-006 | [doc] |
| Unrolled loop with fetches | raises GPRs (fetches hoisted to the top) | Q2, Q3 | A2-067 | [doc] |
| Scratch (spill) memory | any use = poor performance | `Vulkan` stats page | U3-006 | [doc] |
| Vulkan subgroup size | no published number; query `VkPhysicalDeviceSubgroupProperties` / subgroup size control on device | Q2, Q3 | A2-068 | [doc] |

## Cliffs and limits

| Limit | Threshold | Applies to | Source | Evidence |
|---|---|---|---|---|
| Graphics shader instructions | penalty at each multiple of 2000 | Q3 (A7x) | A2-070 | [doc] |
| LPAC compute instructions | each multiple of 2256 | Q3 (A7x) | A2-070 | [doc] |
| A6x instruction threshold | no published number; watch instruction-cache stalls (A2-071) | Q2 | A2-070, G2-069 | [doc] |
| Unique UBOs | each multiple of 16 | Q3 | A2-070 | [doc] |
| Textures + SSBOs combined | each multiple of 16 | Q3 | A2-070 | [doc] |
| Vertex buffers | each multiple of 32 | Q3 | A2-070 | [doc] |
| Samplers | 16; fragment and compute share one sampler cache, vertex has its own | Q2, Q3 (A6x-A8x) | A2-070 | [doc] |
| UBO total per shader in constant RAM | under 7372 B (0.9 × 8192) | Q2, Q3 | A2-074 | [doc] |
| GL_MAX_TEXTURE_IMAGE_UNITS | 16 | `GLES` Q2, Q3 | G2-069 | [measured] |
| GL_MAX_FRAGMENT_UNIFORM_BLOCKS / VERTEX | 14 / 14 (below the 16-UBO cliff) | `GLES` Q2, Q3 | G2-069 | [measured] |
| GL_MAX_VARYING_VECTORS | 31 | `GLES` Q2, Q3 | G2-069, G3-041 | [measured] |
| Varying | one 4-component slot + one GPR each | Q2, Q3 | A2-073, A2-067 | [doc] |
| Coalesced texture fetch group | under 15 | `Vulkan` stats page | U3-006 | [doc] |

## Texture fetch and filtering

| Operation | Relative cost | Applies to | Source | Evidence |
|---|---|---|---|---|
| Nearest / bilinear | 1 (baseline) | Q2, Q3 | A2-078, A3-017 | [doc] |
| Trilinear | above bilinear; mip clamping lowers the average | Q2, Q3 | A2-078 | [doc] |
| Anisotropic 16x | up to 16x worst case, average under 2x | Q2, Q3 | A2-078 | [doc] |
| Per-filter cost on Adreno 740 | no published number; measure with `% Anisotropic/Linear/Nearest Filtered` | Q3 | A3-017, A3-040 | [doc] |
| 3D texture | expensive filtering; avoid | Q2, Q3 | A2-080 | [doc] |
| Wide formats, per-quad gradient/LOD variation | slower sampling | Q2, Q3 | A2-080, A3-017 | [doc] |
| Explicit gradients (SampleGrad / textureGrad) | above a plain sample; gradients never cached | Q2, Q3 | A2-079 | [doc] |
| Hardware PCF (comparison sampler) | one bilinear compare vs manual multi-tap | Q2, Q3 | A2-085 | [doc] |
| Separate vs combined sampler | separate: 2-5% lower fill rate | Q2, Q3 `Vulkan` | A2-083 | [doc] |
| Read-only storage buffer | routed through the texture pipe; loads it | Q2, Q3 | A2-084 | [doc] |
| Preferred buffer source | vertex buffer > UBO > SSBO | Q2, Q3 | A2-084 | [doc] |
| ALU:TEX balance | 16 full ALU ops per full-rate fetch | A5x only; A6x/A7x no published number | A2-082 | [doc] |
| Format priority | ASTC, then ETC2 (HDR and LDR ASTC supported) | Q2, Q3 | A2-086, A3-015 | [doc] |
| ASTC in cache | compressed in L2, decompressed into L1; ETC compressed in L1 | A5x only; 650/740 unpublished | A2-082, A3-015 | [doc] |

## Texture cache proxies

| GPU | Texture L1 | L2 (UCHE) | Other | Source | Evidence |
|---|---|---|---|---|---|
| Adreno 640 (A6xx, proxy for Q2) | 1 KB per uSPTP, 68.1% hit rate (3DMark Wild Life Extreme) | 128 KB, about 47 cycles | about 30 GB/s DRAM (phone) | A2-081 | [measured] |
| Adreno X1 (A7xx, proxy for Q3) | 2 KB per uSPTP | not stated here | 192 KB register file per uSPTP | A2-006, A2-081 | [measured] |
| Adreno 650 / 740v3 | no published number | no published number | measure `% Texture L1 Miss` ASTC vs uncompressed on one draw | A3-015 | [doc] |

Qualcomm healthy ranges for the related counters: `% Texture L1 Miss` under
50%, `% Texture L2 Miss` under 40%, `% Texture Fetch Stall` under ~2%
(sustained ~16% is too high) (A3-054, Adreno in general, not Quest-specific).

## Measuring ALU throughput (A2-004)

Use to compare Quest 2 vs Quest 3/3S per clock, or half vs float on your
exact build and driver. Method (A2-004, A2-008, A3-051):

1. Pin levels and isolate the app:
   ```sh
   adb shell setprop debug.oculus.gpuLevel 4
   adb shell setprop debug.oculus.cpuLevel 4
   adb shell setprop debug.oculus.foveation.level 0
   adb shell setprop debug.oculus.foveation.dynamic 0
   ```
2. Put an opaque quad filling the view in an otherwise empty scene, with the
   shader below. Fix `_Iterations` (e.g. 64, 128, 256) so GPU time is
   dominated by the loop.
3. Stream `Clocks / Second` (resolve its ID with `adb shell ovrgpuprofiler -m`)
   with `adb shell ovrgpuprofiler -r"<id>"`, and read GPU time from OVR
   Metrics. Also stream `% Shaders Busy` (resolve its ID from `-m`); it
   should be near 100% or the run is not ALU-bound (A2-004). Take the slope
   of GPU ms vs `_Iterations`; divide by the clock to get time per 32 scalar
   FMAs per clock.
4. Toggle the `BENCH_HALF` keyword for fp16 vs fp32. Compare devices at
   matched MHz (Quest 2 L4 = 525 MHz, Quest 3/3S L4 = 545 MHz per the levels
   table; not identical, so normalise by clock).
5. In a RenderDoc Meta Fork capture (`Vulkan`), confirm the half variant shows
   16-bit ALU instructions and a smaller full register footprint; if not, the
   driver kept fp32 and the result measures nothing about fp16.

Shader (URP 14 / Unity 2022.3 and URP 17 / Unity 6000.0+; single-pass
instanced / multiview safe; `Vulkan` and `GLES`):

```hlsl
Shader "Bench/AluLoop"
{
    Properties
    {
        _Iterations ("Iterations", Integer) = 128
        _Seed ("Seed", Float) = 0.37
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Pass
        {
            Name "Bench"
            Tags { "LightMode"="UniversalForward" }
            ZWrite On
            ZTest LEqual
            Cull Back

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_local _ BENCH_HALF
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                int _Iterations;
                float _Seed;
            CBUFFER_END

            #if defined(BENCH_HALF)
                #define BT  half
                #define BT4 half4
            #else
                #define BT  float
                #define BT4 float4
            #endif

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv         : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv         : TEXCOORD0;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                o.uv = input.uv;
                return o;
            }

            half4 frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                // Four independent scalar FMA chains (Adreno is scalar); the unrolled
                // inner block gives 32 scalar FMAs per outer iteration, so loop
                // overhead (int add is half rate, A2-072) does not hide the fp16 gain.
                BT4 a = BT4(input.uv, input.uv.yx);
                BT  b = (BT)_Seed;          // |b| < 1 keeps values bounded in half
                BT  c = (BT)0.5;
                [loop]
                for (int k = 0; k < _Iterations; ++k)
                {
                    [unroll] for (int j = 0; j < 8; ++j) { a = a * b + c; }
                }
                return half4(a);
            }
            ENDHLSL
        }
    }
}
```

Notes:
- The `Integer` property type needs Unity 2021.1+; on older versions use
  `Int`. `_Iterations` must stay a uniform so the compiler cannot fold the
  loop.
- The result is a relative number for your build and driver only. There is no
  published Quest FLOPS figure to compare against (A2-004). Vendor GPU-gain
  claims conflict: Meta "twice", Qualcomm "2.5x" (ARM-C20); measure at
  matched levels.
- Keep the shader out of shipping builds.
