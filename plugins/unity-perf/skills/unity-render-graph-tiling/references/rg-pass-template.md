# Paste-ready URP 17 raster pass with framebuffer fetch (Quest, Vulkan)

Reference for `unity-perf:unity-render-graph-tiling`. Read it before you write,
port or review a custom ScriptableRendererFeature for Quest.

**Status:** untested, because Unity cannot run where this was written. The
APIs follow the Unity 6 manual pages cited below (accessed 2026-09-24) and
Unity's "URP RenderGraph Samples > FrameBufferFetch" sample (U2-072). Compile
it, then confirm the merge in the on-device Render Graph Viewer before trusting
it.

Applies to: `Unity ≥ 6000.0` `URP 17+` `Vulkan` `Quest 2` `Quest 3/3S`.
- MSAA: the camera colour descriptor carries the MSAA sample count, so with
  MSAA 2x/4x the input attachment is multisampled and must be read with the
  `_MS` macros. The template selects shader pass 0 (MSAA off), 1 (2x) or
  2 (4x) from `desc.msaaSamples`. The Unity framebuffer-fetch page does not
  cover the `_MS` variants, so [verify on device / compile]. On Adreno 650,
  2 input samples read in parallel are free and 4 are not (A2-058); Adreno 740
  is not stated.
- On 6.0 before 6000.0.49f1, do not swap `Blitter` for `AddBlitPass` /
  `AddCopyPass`: they render the left eye only in multiview (U1-078).
- On GLES, framebuffer fetch falls back to copies through video memory. It
  still renders but saves nothing (U2-066).
- On 6.0-6.3 with Compatibility Mode on, `RecordRenderGraph` does not run.
  Turn Compatibility Mode off.
- On 6.4+, `RecordRenderGraph` is the only path (U1-026).

## Design rules this template follows

| Rule | Why | Source |
| --- | --- | --- |
| `AddRasterRenderPass`, not `AddUnsafePass` / compute | Only raster passes merge | U2-063, U2-064 |
| Read colour with `SetInputAttachment`, not `UseTexture` | `UseTexture` of the previous output gives `NextPassReadsTexture` and a store | U2-058, U2-066 |
| Write a new texture and set `resourceData.cameraColor = destination` | No "blit back" pass | U2-065 |
| `AccessFlags.WriteAll` on the destination | Tells the compiler it is fully rewritten, so no load | U2-062 |
| Same size and sample count as camera colour (`GetTextureDesc(source)`) | Avoids `TargetSizeMismatch` | U2-058 |
| Static render function, `Blitter.BlitTexture` | No captures; `Blitter` is XR-aware; never `CommandBuffer.Blit` | U2-063, U2-068 |
| Skip non-Game cameras | Editor graphs differ from device graphs anyway | U2-051 |

Framebuffer fetch reads **only the current pixel**, so no blur, bloom or
distortion (U2-066).

Before writing a pass, check two cheaper options:
- If the effect is a pure colour transform, try to express it as colour
  grading, which the stock on-tile post path already handles (6.3+). That
  costs no extra pass.
- If the effect needs neighbouring pixels, it cannot stay on-tile. Budget it
  as a full-screen off-tile pass (→ `arm-mobile-hw-perf:xr2-bandwidth-power`).

## C# (TileTintFeature.cs)

```csharp
// URP 17 (Unity 6000.0+). Untested: verify compile and merge on device.
#if UNITY_6000_0_OR_NEWER
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.RenderGraphModule;
using UnityEngine.Rendering.Universal;

public sealed class TileTintFeature : ScriptableRendererFeature
{
    [SerializeField] Material material; // material using Hidden/QuestPerf/TileTint
    [SerializeField] RenderPassEvent passEvent = RenderPassEvent.AfterRenderingTransparents;

    TileTintPass m_Pass;

    public override void Create()
    {
        m_Pass = new TileTintPass();
    }

    public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
    {
        if (material == null)
            return;
        m_Pass.renderPassEvent = passEvent;
        m_Pass.material = material;
        renderer.EnqueuePass(m_Pass);
    }

    sealed class TileTintPass : ScriptableRenderPass
    {
        public Material material;

        sealed class PassData
        {
            public Material material;
            public int shaderPass;
        }

        public TileTintPass()
        {
            // The input attachment must be a graph texture, not the backbuffer.
            // A memoryless intermediate stays on-tile when the chain merges.
            requiresIntermediateTexture = true;
        }

        public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
        {
            UniversalCameraData cameraData = frameData.Get<UniversalCameraData>();
            if (cameraData.cameraType != CameraType.Game)
                return;

            UniversalResourceData resourceData = frameData.Get<UniversalResourceData>();
            if (resourceData.isActiveTargetBackBuffer)
                return; // Cannot read the backbuffer as an input attachment.

            TextureHandle source = resourceData.activeColorTexture;

            // Same size, format and MSAA as camera colour, so no TargetSizeMismatch.
            TextureDesc desc = renderGraph.GetTextureDesc(source);
            desc.name = "_TileTintColor";
            desc.clearBuffer = false;
            TextureHandle destination = renderGraph.CreateTexture(desc);

            // Shader pass 0 = single-sample, 1 = MSAA 2x, 2 = MSAA 4x (see HLSL).
            int samples = (int)desc.msaaSamples;
            int shaderPass = samples >= 4 ? 2 : (samples >= 2 ? 1 : 0);

            using (var builder = renderGraph.AddRasterRenderPass<PassData>("TileTint (FB fetch)", out PassData passData))
            {
                passData.material = material;
                passData.shaderPass = shaderPass;
                builder.SetInputAttachment(source, 0, AccessFlags.Read);
                builder.SetRenderAttachment(destination, 0, AccessFlags.WriteAll);
                builder.SetRenderFunc(static (PassData data, RasterGraphContext context) => ExecutePass(data, context));
            }

            // No blit back: later passes and the final write read the new texture.
            resourceData.cameraColor = destination;
        }

        static void ExecutePass(PassData data, RasterGraphContext context)
        {
            // Full-screen triangle; Blit.hlsl's Vert handles single-pass instanced / multiview.
            Blitter.BlitTexture(context.cmd, new Vector4(1f, 1f, 0f, 0f), data.material, data.shaderPass);
        }
    }
}
#endif
```

Notes:
- `requiresIntermediateTexture` is used by URP's own FullScreenPassRendererFeature.
  Confirm it exists in your exact 6.0 patch [verify on device / compile].
- With an intermediate, URP still writes the eye texture at the end of the
  graph. In the viewer, check that this final write sits under the **same**
  blue merge bar. If a separate "Final Blit" appears, the chain is not on-tile.
  Find its pass-break reason in
  [off-tile-triggers.md](off-tile-triggers.md).
- On 6.2+, the AfterRendering injection point runs after the final blit
  (U1-024). Inject at AfterRenderingTransparents or earlier.

## HLSL (TileTint.shader)

Follows the URP 17 ShaderLibrary conventions: `Core.hlsl` + `Blit.hlsl`
(`Vert`, `Varyings`), the `_X` framebuffer macros for XR texture arrays, and
a `UnityPerMaterial` CBUFFER.

```hlsl
Shader "Hidden/QuestPerf/TileTint"
{
    Properties
    {
        _Tint ("Tint", Color) = (1, 1, 1, 1)
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" }
        ZWrite Off ZTest Always Cull Off Blend Off

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.core/Runtime/Utilities/Blit.hlsl"

        CBUFFER_START(UnityPerMaterial)
            half4 _Tint;
        CBUFFER_END

        half4 ApplyTint(half4 color)
        {
            return half4(color.rgb * _Tint.rgb, color.a);
        }
        ENDHLSL

        // Pass 0: MSAA off. Input attachment 0 = camera colour, read on-chip (Vulkan).
        Pass
        {
            Name "TileTint"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag

            FRAMEBUFFER_INPUT_X_HALF(0);

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                return ApplyTint(LOAD_FRAMEBUFFER_X_INPUT(0, input.positionCS.xy));
            }
            ENDHLSL
        }

        // Pass 1: MSAA 2x. Multisampled input attachment, _MS macros.
        Pass
        {
            Name "TileTintMSAA2"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag

            FRAMEBUFFER_INPUT_X_HALF_MS(0);

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                half4 c = LOAD_FRAMEBUFFER_X_INPUT_MS(0, 0, input.positionCS.xy)
                        + LOAD_FRAMEBUFFER_X_INPUT_MS(0, 1, input.positionCS.xy);
                return ApplyTint(c * 0.5h);
            }
            ENDHLSL
        }

        // Pass 2: MSAA 4x. 4 input samples are not free on Adreno 650 (A2-058).
        Pass
        {
            Name "TileTintMSAA4"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag

            FRAMEBUFFER_INPUT_X_HALF_MS(0);

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                half4 c = 0;
                [unroll] for (int i = 0; i < 4; i++)
                    c += LOAD_FRAMEBUFFER_X_INPUT_MS(0, i, input.positionCS.xy);
                return ApplyTint(c * 0.25h);
            }
            ENDHLSL
        }
    }
}
```

MSAA notes [verify on device / compile]:
- The MSAA passes average the samples and write that value to every sample
  (the fragment runs per pixel). For a linear per-pixel transform such as a
  tint, the resolved result matches tinting each sample. For a non-linear
  transform, edge pixels differ slightly; per-sample shading (`SV_SampleIndex`)
  would avoid that but costs a fragment invocation per sample.
- The `_MS` macros take `(index, sampleIndex, positionCS.xy)`. They are not on
  the Unity framebuffer-fetch page, so confirm the names against your URP
  version's `ShaderLibrary` before shipping.

Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-framebuffer-fetch.html
(`FRAMEBUFFER_INPUT_X_HALF(0)`, `LOAD_FRAMEBUFFER_X_INPUT(0, input.positionCS.xy)`,
`builder.SetInputAttachment(..., 0, AccessFlags.Read)`,
`Blitter.BlitTexture(context.cmd, new Vector4(1, 1, 0, 0), material, pass)`) [doc].
Blitter shaders must be hand-written; Shader Graph is not Blitter-compatible
(U2-068).

## Depth input attachment (Unity 6.6, Vulkan) — replacing Depth Texture reads

Setup:
1. Add a Render Objects renderer feature.
2. Enable **Depth** and **Set As Input Attachment**.
3. Set Event to After Rendering Opaques or later.
4. Check `SystemInfo.supportsDepthAttachmentAsInputAttachment` at runtime
   (U2-079).

Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/read-depth-input-attachment.html [doc].

Put these lines in the `HLSLPROGRAM` block of the pass that the Render Objects
feature draws (for example a soft-particle or depth-fade material):

```hlsl
#pragma multi_compile _ _DEPTH_AS_INPUT_ATTACHMENT _DEPTH_AS_INPUT_ATTACHMENT_MSAA

#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

// positionCS = SV_Position from the fragment input; uv = screen UV for the fallback path.
float GetRawSceneDepth(float4 positionCS, float2 uv)
{
#if defined(_DEPTH_AS_INPUT_ATTACHMENT)
    return FetchSceneDepth(positionCS.xy);        // on-chip, no depth copy
#elif defined(_DEPTH_AS_INPUT_ATTACHMENT_MSAA)
    return FetchSceneDepth(positionCS.xy, 0);     // sample 0 of the MSAA depth
#else
    return SampleSceneDepth(uv);                  // fallback: needs Depth Texture on
#endif
}

// Example use (soft-particle / depth fade):
// float sceneEye = LinearEyeDepth(GetRawSceneDepth(input.positionCS, uv), _ZBufferParams);
// half  fade     = saturate((sceneEye - input.positionCS.w) * _FadeDistanceInv);
```

This adds a `multi_compile` axis, so strip the variants you do not ship
(→ `unity-perf:unity-shader-hitches`). The Meta-fork equivalent uses different
keywords (`_DEPTH_INPUT_ATTACHMENT`, `LOAD_FRAMEBUFFER_INPUT_MS`; see
[off-tile-triggers.md](off-tile-triggers.md) section 5). Shaders written for
the fork must be ported.

## Startup capability log (one-time, per headset)

These flags decide whether memoryless, backbuffer-MRT and depth input work.
None is published for Quest 2 vs Quest 3, so log them once
(unity.md Known unknowns) [verify on device].

```csharp
using UnityEngine;

public static class QuestTileCaps
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Log()
    {
        string s = $"[TileCaps] {SystemInfo.graphicsDeviceName} {SystemInfo.graphicsDeviceType}";
#if UNITY_6000_0_OR_NEWER
        s += $" memoryless={SystemInfo.supportsMemorylessTextures}";
#endif
#if UNITY_6000_5_OR_NEWER
        // Present in 6000.5 source (U2-059); may exist earlier.
        s += $" backbufferMRT={SystemInfo.supportsBackbufferInMultipleRenderTargets}";
#endif
#if UNITY_6000_6_OR_NEWER
        s += $" depthInputAttachment={SystemInfo.supportsDepthAttachmentAsInputAttachment}";
#endif
        Debug.Log(s);
    }
}
```

Read it with `adb logcat -s Unity | grep TileCaps`.

## URP 12/14 (2021.3 / 2022.3): what you can and cannot do

- There is no Render Graph and no public input attachments
  (`ConfigureInputAttachments` is internal, U2-082).
- Full-screen recipe (U2-083):
  1. Use `RTHandle`.
  2. Take `renderer.cameraColorTargetHandle` in `SetupRenderPasses`, then
     call `ConfigureTarget` in `OnCameraSetup`.
  3. Blit with `Blitter.BlitCameraTexture(cmd, src, dst, mat, 0)` and a
     `Blit.hlsl` shader.
  4. Declare `ConfigureInput(ScriptableRenderPassInput.Color)`.
- Set stores explicitly with `ConfigureColorStoreAction` /
  `ConfigureDepthStoreAction`. Never call `cmd.SetRenderTarget`.
- Such a pass is always off-tile: it is a full store and read-back of camera
  colour. For real subpasses, use Meta's fork branches (U2-084).
