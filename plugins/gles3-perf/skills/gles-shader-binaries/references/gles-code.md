# Paste-ready code for GLES warmup and precision

Read this when applying Fix 2 (multiview variants in an SVC) or Fix 5
(precision split) from the SKILL.md. Sources accessed 2026-09-24; finding IDs
refer to research/gles3.md and research/unity.md.

## SVC: add STEREO_MULTIVIEW_ON variants (Editor, Unity 2021.3+)

Why: an Editor-recorded ShaderVariantCollection holds non-stereo variants while
the headset renders multiview, so warmup misses them (GLES3-GF1-002,
[community]). Unity's 6000.0.0b11 note says legacy warmup APIs do not prewarm
stereo-instancing variants at all (U1-049, [doc]); this script covers the
community fix, and the post-warmup `Shader.CreateGPUProgram` check decides
which holds on your version [verify on device].

Put the file in an `Editor/` folder. Select the `.shadervariants` asset, run
Assets > Quest > Add STEREO_MULTIVIEW_ON Variants. Serialized field names
(`m_Shaders`, `first`, `second.variants`, `keywords`, `passType`) follow the
`.shadervariants` YAML. Variants that do not exist in the build are skipped
(the `ShaderVariant` constructor throws for them).

```csharp
#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class SvcAddMultiviewVariants
{
    const string Kw = "STEREO_MULTIVIEW_ON";

    [MenuItem("Assets/Quest/Add STEREO_MULTIVIEW_ON Variants")]
    static void Run()
    {
        var svc = Selection.activeObject as ShaderVariantCollection;
        if (svc == null) { Debug.LogError("Select a ShaderVariantCollection."); return; }
        var so = new SerializedObject(svc);
        var shaders = so.FindProperty("m_Shaders");
        var add = new List<ShaderVariantCollection.ShaderVariant>();
        for (int i = 0; i < shaders.arraySize; i++)
        {
            var e = shaders.GetArrayElementAtIndex(i);
            var shader = e.FindPropertyRelative("first").objectReferenceValue as Shader;
            var vars = e.FindPropertyRelative("second.variants");
            if (shader == null || vars == null) continue;
            for (int v = 0; v < vars.arraySize; v++)
            {
                var sv = vars.GetArrayElementAtIndex(v);
                string kws = sv.FindPropertyRelative("keywords").stringValue;
                if (kws.Contains(Kw)) continue;
                var list = new List<string>(kws.Split(new[] { ' ' },
                    System.StringSplitOptions.RemoveEmptyEntries)) { Kw };
                var pass = (PassType)sv.FindPropertyRelative("passType").intValue;
                try { add.Add(new ShaderVariantCollection.ShaderVariant(shader, pass, list.ToArray())); }
                catch (System.Exception) { /* variant stripped or no multiview path */ }
            }
        }
        Undo.RecordObject(svc, "Add multiview variants");
        int n = 0;
        foreach (var sv in add) if (svc.Add(sv)) n++;
        EditorUtility.SetDirty(svc);
        AssetDatabase.SaveAssets();
        Debug.Log($"{svc.name}: added {n} {Kw} variants");
    }
}
#endif
```

## URP depth-fade unlit: half/float split on GLES (URP 14+, Unity 2022.3+)

Demonstrates: `half` for color (emitted as `mediump` on GLES, G3-028, G3-029),
`float` for tiling, eye depth and scene depth (G3-030, G3-031), SPI/multiview
macros, `CBUFFER_START(UnityPerMaterial)` for the SRP Batcher. Works on GLES3
and Vulkan. GLES has no reversed Z (G3-035); `LinearEyeDepth` with
`_ZBufferParams` handles both conventions. Requires the URP Depth Texture,
which has its own cost (`unity-perf:unity-urp-settings`).

To force full-precision `real` in one shader, add `#define PREFER_HALF 0`
before the first include (G3-029).

```hlsl
// URP 14+ (Unity 2022.3+), GLES3 and Vulkan; SPI/multiview safe, SRP Batcher compatible.
// Needs the URP Depth Texture on (its cost: unity-perf:unity-urp-settings).
Shader "Quest/DepthFadeUnlit"
{
    Properties
    {
        _BaseMap ("Base Map", 2D) = "white" {}
        _BaseColor ("Base Color", Color) = (1,1,1,1)
        _FadeDistance ("Fade Distance (m)", Float) = 0.5
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;     // float: large tiling/offset
                half4  _BaseColor;      // color: mediump is enough
                float  _FadeDistance;   // metres, compared with depth
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings   { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float eyeDepth : TEXCOORD1; UNITY_VERTEX_OUTPUT_STEREO };

            Varyings vert (Attributes IN)
            {
                Varyings OUT;
                UNITY_SETUP_INSTANCE_ID(IN);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(OUT);
                VertexPositionInputs p = GetVertexPositionInputs(IN.positionOS.xyz);
                OUT.positionCS = p.positionCS;
                OUT.uv = TRANSFORM_TEX(IN.uv, _BaseMap);
                OUT.eyeDepth = -p.positionVS.z;       // float: depth never goes to half
                return OUT;
            }

            half4 frag (Varyings IN) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(IN);
                float2 suv = GetNormalizedScreenSpaceUV(IN.positionCS);
                float sceneEye = LinearEyeDepth(SampleSceneDepth(suv), _ZBufferParams); // float path
                half fade = (half)saturate((sceneEye - IN.eyeDepth) / _FadeDistance);
                half4 c = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, IN.uv) * _BaseColor;
                c.a *= fade;
                return c;
            }
            ENDHLSL
        }
    }
}
```

## Sources

All accessed 2026-09-24.

- https://discussions.unity.com/t/shadervariantcollection-warmup-not-work-on-oculus-quest-2/920217 [community]
- https://unity.com/releases/editor/whats-new/6000.0.0b11 [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/SL-Use16BitPrecisionInShaders.html [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/GLES3.hlsl [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl [doc]
- https://docs.unity3d.com/2019.4/Documentation/Manual/SL-DataTypesAndPrecision.html [doc]
