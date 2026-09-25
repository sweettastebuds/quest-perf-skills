# Paste-ready URP HLSL for Quest (URP 12 / 14 / 17)

Read when writing or reviewing a custom URP shader for Quest. All templates:

- include `Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl`
- keep every material property in `CBUFFER_START(UnityPerMaterial)` so the SRP
  Batcher accepts the shader (batching itself: `unity-perf:unity-draw-calls-batching`)
- carry the SPI/multiview macros (G2-054, U3-044)
- use `half` for colour/lighting and `float` for positions, UVs and depth
  (U3-057, G3-031)

Compile-checked against nothing here (Unity cannot run in this repo):
**untested**. Confirm on your URP version with "Compile and show code", then
read the Vulkan shader stats in RenderDoc Meta Fork (U3-006).

## Per-version differences that touch custom shaders

| Item | URP 12 (2021.3) | URP 14 (2022.3) | URP 17.x (6000.0-6000.6) | ID |
| --- | --- | --- | --- | --- |
| Shader Precision Model setting | yes | yes | yes | U3-051 |
| `real` = `half` on mobile (`PREFER_HALF` 1) | yes | yes | yes | U3-053 |
| Lit Alpha Clipping also sets `AlphaToMask` with MSAA | no | yes | yes | U3-061 |
| `dynamic_branch` keyword type | no (2022.1+) | yes | yes | U3-071 |
| Full-screen XR pass | fullscreen triangle + `TEXTURE2D_X` recipe | `Blitter` + `Blit.hlsl` | `Blitter` + `Blit.hlsl` | U2-041 |
| `_FORWARD_PLUS` | n/a | Forward+ keyword | deprecated in 6.1 (17.1) for `_CLUSTER_LIGHT_LOOP`; shim still works 6.1-6.5 | U1-033, UNITY-GF2-C1 |
| Shader Build Settings (keyword type override per profile) | no | no | 6.3+ | U3-074 |
| Shader Constant Defines | no | no | 6.6 | U3-075 |
| `UNITY_PLATFORM_META_QUEST` define, Quest lighting early-outs | no | no | 6.5+ (6000.5.0a3) | U3-066, U3-067 |
| `META_QUEST_ORTHO_PROJ`, `META_QUEST_LIGHTUNROLL` | no | no | 6.5+ | U3-068, U3-069, X-C8 |

## 1. Unlit opaque, half precision, SPI-safe

`Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan`

```hlsl
Shader "Quest/Unlit Opaque"
{
    Properties
    {
        [MainTexture] _BaseMap ("Base Map", 2D) = "white" {}
        [MainColor]   _BaseColor ("Base Color", Color) = (1, 1, 1, 1)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" "RenderPipeline" = "UniversalPipeline" }

        Pass
        {
            Name "Unlit"
            Tags { "LightMode" = "UniversalForward" }
            ZWrite On
            ZTest LEqual
            Cull Back

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            // Texture2D<half4>: sampling returns half (U3-052, G3-030).
            TEXTURE2D_HALF(_BaseMap);
            SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;   // float: tiling/offset feed UVs
                half4  _BaseColor;    // stored at 32-bit anyway (U3-052)
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv         : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv         : TEXCOORD0;   // keep UVs float (U3-057)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings vert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                half4 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv);
                return half4(albedo.rgb * _BaseColor.rgb, 1.0);
            }
            ENDHLSL
        }
    }
}
```

Notes:
- `1.0` in `half4(..., 1.0)` is a float literal; the constant is folded, but
  in arithmetic chains prefer `(half)1.0` casts at the chain start rather than
  mixing (A2-066). Never `1.0h` (treated as float, U3-052).
- `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX` is only required when the fragment
  reads a `TEXTURE2D_X` camera texture or `unity_StereoEyeIndex` (U3-046); it is
  harmless otherwise.
- If this material must cast shadows or appear in the depth texture, add
  `ShadowCaster` / `DepthOnly` passes copied from URP's `Unlit.shader` of the
  same URP version. `UsePass` into another shader breaks SRP Batcher
  compatibility because the `UnityPerMaterial` layouts differ.

## 2. Alpha-tested (cutout) variant

Differences from template 1 only. Queue AlphaTest so it draws after opaques and
tests against their LRZ (U3-060, A2-041). No `AlphaToMask` unless edges need
MSAA smoothing and alpha really varies (U3-061).

```hlsl
Tags { "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" "RenderPipeline" = "UniversalPipeline" }

// Properties
_Cutoff ("Alpha Cutoff", Range(0, 1)) = 0.5

// CBUFFER_START(UnityPerMaterial) ... add:
half _Cutoff;

// frag:
half4 frag(Varyings input) : SV_Target
{
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
    half4 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv) * _BaseColor;
    clip(albedo.a - _Cutoff);   // LRZ write + early-Z off for THIS draw only (A2-034, A2-038)
    return half4(albedo.rgb, 1.0);
}
```

For an artist toggle instead of a separate shader (adds a variant per used
combination, U3-071):

```hlsl
#pragma shader_feature_local_fragment _ALPHATEST_ON
...
#if defined(_ALPHATEST_ON)
    clip(albedo.a - _Cutoff);
#endif
```

Set the queue to 2450 from the material GUI or an editor script when the
keyword is on; a clipped material left in queue 2000 is drawn among opaques.

## 3. Per-material foliage depth prepass (Meta's experiment, U3-062)

`Quest 2` `Quest 3/3S` `URP 12+` `GLES` `Vulkan` [verify on device]

Two passes in one shader: pass A clips and writes depth only; pass B shades
with `ZTest Equal` and no `clip()`. Both use the Attributes/Varyings/vert of
template 1 and the `_Cutoff` property of template 2. Put the shared HLSL in an
`HLSLINCLUDE ... ENDHLSL` block at SubShader level.

```hlsl
Tags { "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" "RenderPipeline" = "UniversalPipeline" }

Pass
{
    Name "FoliageDepth"
    Tags { "LightMode" = "SRPDefaultUnlit" }
    ZWrite On
    ZTest LEqual
    ColorMask 0
    Cull Off

    HLSLPROGRAM
    #pragma vertex vert
    #pragma fragment fragDepth
    #pragma multi_compile_instancing
    half4 fragDepth(Varyings input) : SV_Target
    {
        UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
        half a = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).a * _BaseColor.a;
        clip(a - _Cutoff);
        return 0;
    }
    ENDHLSL
}

Pass
{
    Name "FoliageShade"
    Tags { "LightMode" = "UniversalForward" }
    ZWrite Off
    ZTest Equal
    Cull Off

    HLSLPROGRAM
    #pragma vertex vert
    #pragma fragment fragShade
    #pragma multi_compile_instancing
    half4 fragShade(Varyings input) : SV_Target
    {
        UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
        half4 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv) * _BaseColor;
        return half4(albedo.rgb, 1.0);   // no clip(): runs only where depth matched
    }
    ENDHLSL
}
```

Caveats:
- `ColorMask 0` + depth write is on Qualcomm's LRZ-write-off list (A2-033).
  Because the prepass sits in the AlphaTest queue, after the opaques, this
  should not hurt earlier draws; confirm the `LRZ State` of later draws.
- URP renders both LightMode passes per renderer inside the opaque/AlphaTest
  draw, so the prepass only saves overdraw within the same object; to reject
  across objects, move `FoliageDepth` into a Render Objects renderer feature
  (or a separate material/queue) that runs for all foliage before the shading
  pass. Confirm order in Frame Debugger [verify in Editor].
- `ZTest Equal` needs bit-identical vertex positions in both passes: same
  `vert`, same instancing path. Vertex work is paid twice.
- A clipped prepass can still be cheaper than a clipped full shade only if the
  shading pass is expensive. Measure GPU ms both ways; Meta says results vary.

## 4. Main-light lit fragment using SRP library functions

Calling URP's library functions keeps the 6.5+ Quest early-outs (U3-066,
U3-067). For full PBR use `UniversalFragmentPBR`, or better, URP Simple Lit /
Lit or Shader Graph. This fragment is main light + SH only.

`URP 12+` `GLES` `Vulkan`. Add the keyword pragma to template 1's pass and
include Lighting.hlsl after Core.hlsl.

```hlsl
#pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

struct Attributes
{
    float4 positionOS : POSITION;
    float3 normalOS   : NORMAL;
    float2 uv         : TEXCOORD0;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct Varyings
{
    float4 positionCS : SV_POSITION;
    float2 uv         : TEXCOORD0;
    float3 positionWS : TEXCOORD1;   // float: world position (U3-057)
    half3  normalWS   : TEXCOORD2;   // half: direction
    UNITY_VERTEX_OUTPUT_STEREO
};

Varyings vert(Attributes input)
{
    Varyings output = (Varyings)0;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
    VertexPositionInputs pos = GetVertexPositionInputs(input.positionOS.xyz);
    output.positionCS = pos.positionCS;
    output.positionWS = pos.positionWS;
    output.normalWS   = (half3)TransformObjectToWorldNormal(input.normalOS);
    output.uv         = TRANSFORM_TEX(input.uv, _BaseMap);
    return output;
}

half4 frag(Varyings input) : SV_Target
{
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
    half3 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).rgb * _BaseColor.rgb;
    half3 n = normalize(input.normalWS);

    float4 shadowCoord = TransformWorldToShadowCoord(input.positionWS);
    Light mainLight = GetMainLight(shadowCoord);
    half3 attenuated = mainLight.color * (mainLight.distanceAttenuation * mainLight.shadowAttenuation);
    half3 diffuse = LightingLambert(attenuated, mainLight.direction, n);

    half3 color = albedo * (diffuse + SampleSH(n));
    return half4(color, 1.0);
}
```

Notes:
- Soft shadows, additional lights and the Forward+/cluster loop need the
  keyword set of URP's `SimpleLit.shader` for your exact URP version; copy it
  from the installed package rather than from another version.
- On 6.1+, custom code that tests `_FORWARD_PLUS` / `USE_FORWARD_PLUS` should
  test `_CLUSTER_LIGHT_LOOP` / `USE_CLUSTER_LIGHT_LOOP` (U1-033). On 6.1-6.5
  the old names still work through `ForwardPlusKeyword.deprecated.hlsl` with a
  compile-time warning (UNITY-GF2-C1). If one shader file must serve both
  2022.3/6.0 and 6.1+, keep the old keyword until the project leaves 6.0,
  then rename; do not declare both, which doubles the variants.

## 5. Quest-only code paths (6.5+)

```hlsl
#if defined(UNITY_PLATFORM_META_QUEST)
    // Quest build profile only (6000.5.0a3+, U3-066): e.g. skip an effect
    // that is not worth its ALU at Quest resolution.
#endif
```

Keyword Declaration Overrides for orthographic cameras: add
`META_QUEST_ORTHO_PROJ` (master Lit.shader spelling; the manual writes
`_META_QUEST_ORTHO_PROJ`: X-C8; check `Lit.shader` in your installed URP
package and use its spelling).

## 6. Keyword and branch declarations

```hlsl
// Artist toggle, fragment-only, per-material: compiled only when a material uses it.
#pragma shader_feature_local_fragment _DETAIL_ON

// One variant, uniform branch (2022.1+). Both sides should cost about the same (U3-071);
// on Adreno a uniform branch is a per-wave test and both sides may run (A2-069).
// Unity recommends dynamic_branch only on fast GPUs with symmetric branches (U3-071):
// on Quest default to keywords; use this only where PSO count is the proven problem.
#pragma dynamic_branch_local _RIM_ON
// ... in frag:
if (_RIM_ON)
{
    color += rim;
}

// Keep full precision for one shader's `real` math (U3-053):
#define PREFER_HALF 0   // must come before the Core.hlsl include
```

## 7. Screen-space / camera textures under multiview

```hlsl
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
// _CameraDepthTexture is TEXTURE2D_X_FLOAT: keep depth float (G3-030).

half4 frag(Varyings input) : SV_Target
{
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);   // required before any _X read (U3-046)
    float2 screenUV = GetNormalizedScreenSpaceUV(input.positionCS);
    float rawDepth = SampleSceneDepth(screenUV);
    ...
}
```

`TEXTURE2D_X` is a Texture2DArray on Vulkan and GLES3; `SLICE_ARRAY_INDEX`
follows `unity_StereoEyeIndex` only on the stereo-instancing path (U3-047).
Validate per-eye output with `XR/StereoEyeIndexColor` or a RenderDoc capture.
Full-screen passes: `unity-perf:unity-render-graph-tiling`.

## Sources

- https://docs.unity3d.com/6000.6/Documentation/Manual/SL-Use16BitPrecisionInShaders.html (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/GLES3.hlsl (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/TextureXR.hlsl (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/UnityInput.hlsl (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassInstancing.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/renderer-features/how-to-fullscreen-blit-in-xr-spi.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Precision-Modes.html (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGUI/BaseShaderGUI.cs (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-conditionals-choose-a-type.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html (accessed 2026-09-24) [doc]
- https://raw.githubusercontent.com/Unity-Technologies/Graphics/master/Packages/com.unity.render-pipelines.universal/Shaders/Lit.shader (accessed 2026-09-24) [doc]
- https://docs.unity3d.com/6000.1/Documentation/Manual/urp/upgrade-guide-unity-6-1.html (accessed 2026-09-24) [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/ShaderLibrary/ForwardPlusKeyword.deprecated.hlsl (accessed 2026-09-24) [doc]
- https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-1/ (accessed 2026-09-24) [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) [doc]
