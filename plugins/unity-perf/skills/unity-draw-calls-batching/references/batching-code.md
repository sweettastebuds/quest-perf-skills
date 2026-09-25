# Batching code templates

Reference for `unity-perf:unity-draw-calls-batching`. Paste-ready, but untested
here (Unity cannot run in this repository). Sources accessed 2026-09-24; IDs
refer to `research/unity.md`.

## 1. SRP-Batcher-compatible, single-pass-safe unlit shader

`URP 12` to `URP 17`, `GLES` and `Vulkan`, `Quest 2` `Quest 3/3S`.
Rules it follows (U3-010, U3-044): every Properties entry, including the `_ST`
vector, inside one `UnityPerMaterial` CBUFFER and nothing else in it; built-ins
come from URP's `Core.hlsl` (`UnityPerDraw`); stereo macros so the right eye
renders under multiview/SPI. With more than one pass, keep the
`UnityPerMaterial` layout identical in every pass. For GRD/BRG the shader also
needs DOTS instancing support; follow Unity's "make object compatible with GPU
rendering" page for your URP version
(https://docs.unity3d.com/6000.6/Documentation/Manual/urp/make-object-compatible-gpu-rendering.html,
U3-033). The dossier has no paste-ready DOTS block.

```hlsl
Shader "Quest/UnlitBatched"
{
    Properties
    {
        _BaseMap ("Base Map", 2D) = "white" {}
        _BaseColor ("Base Color", Color) = (1,1,1,1)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Pass
        {
            Name "ForwardUnlit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

            // Every Properties entry, including the _ST vector, and nothing else.
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4  _BaseColor;
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
                float2 uv         : TEXCOORD0;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings vert(Attributes IN)
            {
                Varyings OUT = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(IN);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(OUT);
                OUT.positionCS = TransformObjectToHClip(IN.positionOS.xyz);
                OUT.uv = TRANSFORM_TEX(IN.uv, _BaseMap);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                return SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, IN.uv) * _BaseColor;
            }
            ENDHLSL
        }
    }
}
```

## 2. MaterialPropertyBlock replacement (bounded shared-material cache)

`Unity ≥ 2021.3`, any API. An MPB breaks SRP Batcher and GRD compatibility
(U3-015); Unity recommends Material Variants or separate materials. Runtime
copies of one material keep the same shader variant, so the SRP Batcher still
batches them (U3-009). Quantize tints to a small palette so the material count
stays bounded.

```csharp
using System.Collections.Generic;
using UnityEngine;

// Replaces renderer.SetPropertyBlock(tint) with shared materials that keep the
// same shader variant, so the SRP Batcher still batches them.
public static class TintedMaterialCache
{
    static readonly Dictionary<(int, int), Material> s_Cache = new Dictionary<(int, int), Material>();
    static readonly int s_BaseColor = Shader.PropertyToID("_BaseColor");

    public static Material Get(Material source, Color32 tint)
    {
        int rgba = tint.r | (tint.g << 8) | (tint.b << 16) | (tint.a << 24);
        var key = (source.GetInstanceID(), rgba);
        if (!s_Cache.TryGetValue(key, out var mat))
        {
            mat = new Material(source) { name = source.name + "_tint_" + rgba.ToString("X8") };
            mat.SetColor(s_BaseColor, tint);
            s_Cache.Add(key, mat);
        }
        return mat;
    }

    // Call on scene unload: runtime materials are not garbage-collected.
    public static void Clear()
    {
        foreach (var m in s_Cache.Values) Object.Destroy(m);
        s_Cache.Clear();
    }
}
// Usage: renderer.sharedMaterial = TintedMaterialCache.Get(baseMaterial, tint);
// Never renderer.material (creates a per-renderer copy, UNITY-GF1-010).
```

## 3. Editor audit: SRP Batcher breakers and GRD fallbacks

`Unity ≥ 2021.3` (GRD checks matter on `Unity ≥ 6000.0` `Vulkan`). Checks the
per-renderer conditions from U3-010, U3-017, U3-018 and U3-032. Put it in an
`Editor/` folder; run from Tools > Quest Perf > Batching Audit. Run it in Play
Mode too: MPBs are often set at runtime. It cannot detect shader-level SRP
Batcher incompatibility; check the shader Inspector for that.

```csharp
#if UNITY_EDITOR
// Editor/BatchingAudit.cs - lists renderers that break the SRP Batcher or fall back from GRD.
// Untested here (Unity cannot run in this repo). Run in Play Mode too: MPBs are often set at runtime.
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

static class BatchingAudit
{
    static readonly string[] k_Callbacks = { "OnWillRenderObject", "OnBecameVisible", "OnBecameInvisible" };
    const BindingFlags k_Flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

    [MenuItem("Tools/Quest Perf/Batching Audit (loaded scenes)")]
    static void Run()
    {
#if UNITY_2022_2_OR_NEWER
        var renderers = Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None);
#else
        var renderers = Object.FindObjectsOfType<MeshRenderer>(true);
#endif
        int issues = 0;
        foreach (var r in renderers)
        {
            var go = r.gameObject;
            var why = new System.Text.StringBuilder();
            if (r.HasPropertyBlock()) why.Append(" MPB(breaks SRP Batcher+GRD)");
            if (r.sortingLayerID != 0 || r.sortingOrder != 0) why.Append(" non-default sorting(GRD)");
            if (r.probeAnchor != null) why.Append(" AnchorOverride(GRD)");
            if (r.lightProbeUsage == LightProbeUsage.UseProxyVolume) why.Append(" ProxyVolume(GRD)");
            if (go.GetComponent<TextMesh>() != null) why.Append(" TextMesh(GRD)");
            if ((GameObjectUtility.GetStaticEditorFlags(go) & StaticEditorFlags.BatchingStatic) != 0)
                why.Append(" BatchingStatic(never reaches GRD)");
            foreach (var mb in go.GetComponents<MonoBehaviour>())
            {
                if (mb == null) continue;
                foreach (var cb in k_Callbacks)
                    if (mb.GetType().GetMethod(cb, k_Flags) != null) why.Append($" {mb.GetType().Name}.{cb}(GRD)");
            }
            foreach (var m in r.sharedMaterials)
                if (m != null && m.enableInstancing) why.Append($" {m.name}:instancing checkbox(adds variants)");
            if (why.Length > 0) { issues++; Debug.LogWarning($"[BatchingAudit] {go.name}:{why}", go); }
        }
        Debug.Log($"[BatchingAudit] {renderers.Length} MeshRenderers, {issues} with issues.");
    }
}
#endif
```

## 4. Startup log of the stereo and BRG path

Unity 2021.3+ (BRG lines 2022.3+). Drop on any GameObject in a Development
Build; read with `adb logcat -s Unity`.

```csharp
// Drop on any GameObject in a Development Build; read with: adb logcat -s Unity
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR;

public sealed class BatchingPathReport : MonoBehaviour
{
    void Start()
    {
        Debug.Log($"[Batching] api={SystemInfo.graphicsDeviceType} " +
                  $"supportsMultiview={SystemInfo.supportsMultiview} " +
                  $"stereoMode={XRSettings.stereoRenderingMode} " +
                  $"srpBatcher={GraphicsSettings.useScriptableRenderPipelineBatching}");
#if UNITY_2022_3_OR_NEWER
        // GLES reports ConstantBuffer (UBO window), Vulkan reports RawBuffer (SSBO).
        Debug.Log($"[Batching] brgTarget={BatchRendererGroup.BufferTarget} " +
                  $"cbMaxWindow={BatchRendererGroup.GetConstantBufferMaxWindowSize()} " +
                  $"cbAlign={BatchRendererGroup.GetConstantBufferOffsetAlignment()}");
#endif
    }
}
```
