# Lighting code for Quest (C# and URP HLSL)

Paste-ready code for `unity-perf:unity-lighting`. None of it has been run on
every Unity/URP version listed; compile it in your project before relying on
it. Evidence IDs refer to `research/unity.md`, `research/quest.md` and
`research/arm-mobile-hw.md` (accessed 2026-09-24).

Contents:
1. `QuestLightingAudit.cs` - editor, read-only report of the lighting setup.
2. `LightingABToggle.cs` - runtime A/B of shadows and additional lights on device.
3. `AstcHdrProbe.cs` - runtime check for ASTC HDR before using HDR lightmaps.
4. `AllowDynamicResolution.cs` - fixes misaligned additional lights under dynamic resolution.
5. `QuestPerf/MainLightLit.shader` - hardware-PCF main light, back-face early-out, empty ShadowCaster.

## 1. QuestLightingAudit.cs (editor)

Put in any `Editor/` folder. Run `Tools > Quest Perf > Audit Lighting` with the
build target set to Android (so lightmap formats reflect the Android import).
Output goes to the Console. Targets `Unity 2021.3+` `URP 12+`. Serialized field
names come from URP source; a field missing in your URP version prints as
"not in this URP version" instead of failing.

```csharp
// Assets/Editor/QuestLightingAudit.cs
// Unity 2021.3+ / URP 12+. Read-only. Skill: unity-perf:unity-lighting.
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class QuestLightingAudit
{
    [MenuItem("Tools/Quest Perf/Audit Lighting")]
    public static void Run()
    {
        var sb = new StringBuilder("[QuestLightingAudit] unity-perf:unity-lighting\n");
        AuditUrpAsset(sb);
        AuditLights(sb);
        AuditRenderers(sb);
        AuditLightingSettings(sb);
        AuditLightmaps(sb);
        AuditReflectionProbes(sb);
        Debug.Log(sb.ToString());
    }

    static T[] FindAll<T>() where T : Object
    {
#if UNITY_2022_3_OR_NEWER
        return Object.FindObjectsByType<T>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
#else
        return Object.FindObjectsOfType<T>();
#endif
    }

    static string Field(SerializedObject so, string path, string label)
    {
        var p = so.FindProperty(path);
        if (p == null) return $"{label}: (field '{path}' not in this URP version)";
        switch (p.propertyType)
        {
            case SerializedPropertyType.Boolean: return $"{label}: {p.boolValue}";
            case SerializedPropertyType.Integer: return $"{label}: {p.intValue}";
            case SerializedPropertyType.Enum:
                var names = p.enumDisplayNames;
                int i = p.enumValueIndex;
                return $"{label}: {(i >= 0 && i < names.Length ? names[i] : p.intValue.ToString())}";
            default: return $"{label}: ({p.propertyType})";
        }
    }

    static void AuditUrpAsset(StringBuilder sb)
    {
        var urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
        if (urp == null) { sb.AppendLine("No URP asset active for the current quality level."); return; }

        sb.AppendLine($"URP asset: {urp.name}");
        sb.AppendLine($"  Main light shadows: {urp.supportsMainLightShadows}, resolution {urp.mainLightShadowmapResolution}, " +
                      $"Max Distance {urp.shadowDistance}, cascades {urp.shadowCascadeCount}");
        sb.AppendLine($"  Additional lights: {urp.additionalLightsRenderingMode}, per-object limit {urp.maxAdditionalLightsCount}, " +
                      $"shadows {urp.supportsAdditionalLightShadows}, atlas {urp.additionalLightsShadowmapResolution}");
        sb.AppendLine($"  Soft shadows: {urp.supportsSoftShadows}");
        if (urp.shadowCascadeCount > 1)
            sb.AppendLine("  WARN: more than 1 cascade; 1 cascade + short Max Distance is the Quest starting point (U4-028, U4-029).");
        if (urp.supportsSoftShadows)
            sb.AppendLine("  WARN: soft shadows on; Unity rates them high-impact on untethered XR; use Low or off (U2-009, U4-025).");

        var so = new SerializedObject(urp);
        sb.AppendLine("  " + Field(so, "m_SoftShadowQuality", "Soft Shadow Quality"));
        sb.AppendLine("  " + Field(so, "m_ReflectionProbeBlending", "Probe Blending"));
        sb.AppendLine("  " + Field(so, "m_ReflectionProbeBoxProjection", "Box Projection"));
        sb.AppendLine("  " + Field(so, "m_ReflectionProbeAtlas", "Probe Atlas Blending"));
        sb.AppendLine("  " + Field(so, "m_ShEvalMode", "SH Evaluation Mode (set Per Vertex explicitly with APV, U4-014)"));
        sb.AppendLine("  " + Field(so, "m_LightProbeSystem", "Light Probe System"));

        var list = so.FindProperty("m_RendererDataList");
        if (list != null && list.isArray)
        {
            for (int i = 0; i < list.arraySize; i++)
            {
                var rd = list.GetArrayElementAtIndex(i).objectReferenceValue as UniversalRendererData;
                if (rd != null) sb.AppendLine($"  Renderer {i}: {rd.name}, rendering path {rd.renderingMode}");
            }
        }
    }

    static void AuditLights(StringBuilder sb)
    {
        int realtime = 0, mixed = 0, baked = 0, shadowMaps = 0, shadowedPoints = 0;
        foreach (var l in FindAll<Light>())
        {
            if (!l.enabled) continue;
            switch (l.lightmapBakeType)
            {
                case LightmapBakeType.Realtime: realtime++; break;
                case LightmapBakeType.Mixed: mixed++; break;
                default: baked++; break;
            }
            if (l.lightmapBakeType == LightmapBakeType.Baked || l.shadows == LightShadows.None) continue;
            if (l.type == LightType.Point) { shadowMaps += 6; shadowedPoints++; }   // 6 maps per point light (U4-030)
            else if (l.type == LightType.Spot) shadowMaps += 1;
        }
        sb.AppendLine($"Lights (enabled): realtime {realtime}, mixed {mixed}, baked {baked}");
        sb.AppendLine($"  Additional-light shadow maps requested (upper bound): {shadowMaps} " +
                      "(1024 atlas holds 16 at 256, 512 holds 4; U4-030)");
        if (shadowedPoints > 0)
            sb.AppendLine($"  WARN: {shadowedPoints} shadowed point light(s); each costs about 6 spot lights (U4-031).");
        if (realtime + mixed >= 5)
            sb.AppendLine("  NOTE: 5+ realtime/mixed lights; Meta found Forward+ wins from about 5 (U2-027). Path choice: unity-perf:unity-urp-settings.");
    }

    static void AuditRenderers(StringBuilder sb)
    {
        int total = 0, casters = 0, shadowsOnly = 0;
        foreach (var r in FindAll<Renderer>())
        {
            if (!r.enabled) continue;
            total++;
            if (r.shadowCastingMode == ShadowCastingMode.ShadowsOnly) shadowsOnly++;
            else if (r.shadowCastingMode != ShadowCastingMode.Off) casters++;
        }
        sb.AppendLine($"Renderers: {total} enabled, {casters} cast shadows, {shadowsOnly} shadows-only proxies (U4-032)");
    }

    static void AuditLightingSettings(StringBuilder sb)
    {
        LightingSettings ls = null;
        try { ls = Lightmapping.lightingSettings; } catch (System.Exception) { /* no asset assigned */ }
        if (ls == null) { sb.AppendLine("Lighting Settings: none assigned to the active scene."); return; }

        sb.AppendLine($"Lighting Settings: baked GI {ls.bakedGI}, realtime GI {ls.realtimeGI}, mixed mode {ls.mixedBakeMode}, " +
                      $"directional mode {ls.directionalityMode}, max lightmap size {ls.lightmapMaxSize}");
        sb.AppendLine($"  Quality > Shadowmask Mode: {QualitySettings.shadowmaskMode}");
        if (ls.realtimeGI)
            sb.AppendLine("  WARN: realtime GI on; Meta says avoid it on Quest (U4-008).");
        if (ls.mixedBakeMode == MixedLightingMode.Shadowmask && QualitySettings.shadowmaskMode == ShadowmaskMode.DistanceShadowmask)
            sb.AppendLine("  WARN: Distance Shadowmask is the most expensive mixed mode (U4-001, U4-004).");
    }

    static void AuditLightmaps(StringBuilder sb)
    {
        long bytes = 0;
        var maps = LightmapSettings.lightmaps;
        sb.AppendLine($"Lightmaps: {maps.Length} atlas(es)");
        foreach (var m in maps)
        {
            Report(sb, "color", m.lightmapColor, ref bytes);
            Report(sb, "dir", m.lightmapDir, ref bytes);
            Report(sb, "shadowmask", m.shadowMask, ref bytes);
        }
        sb.AppendLine($"  Total (editor-side estimate): {bytes / (1024 * 1024)} MiB; confirm with the Memory Profiler on device.");
    }

    static void Report(StringBuilder sb, string kind, Texture2D t, ref long bytes)
    {
        if (t == null) return;
        long b = Profiler.GetRuntimeMemorySizeLong(t);
        bytes += b;
        sb.AppendLine($"  {kind} {t.name}: {t.width}x{t.height} {t.format} ~{b / 1024} KiB");
        if (t.format == TextureFormat.RGBAHalf || t.format == TextureFormat.RGB9e5Float || t.format.ToString().StartsWith("ASTC_HDR"))
            sb.AppendLine("    WARN: HDR format; without ASTC HDR on the headset Unity decompresses at load (U4-038).");
    }

    static void AuditReflectionProbes(StringBuilder sb)
    {
        foreach (var p in FindAll<ReflectionProbe>())
        {
            if (p.mode != ReflectionProbeMode.Realtime) continue;
            sb.AppendLine($"Realtime reflection probe {p.name}: refresh {p.refreshMode}, slicing {p.timeSlicingMode}, " +
                          $"resolution {p.resolution}, HDR {p.hdr}");
            if (p.refreshMode == ReflectionProbeRefreshMode.EveryFrame && p.timeSlicingMode == ReflectionProbeTimeSlicingMode.NoTimeSlicing)
                sb.AppendLine("  WARN: Every Frame + No Time Slicing updates in one frame and can hitch (U4-023).");
        }
    }
}
```

## 2. LightingABToggle.cs (runtime A/B on device)

Development build, one scene with a fixed camera path. Cycles Baseline ->
MainShadowsOff -> AdditionalLightsOff -> ShortShadowDistance, `secondsPerVariant`
each, and logs every switch (`adb logcat -s Unity | grep LightingAB`). Lock
CPU/GPU levels first (`quest-perf:quest-profiling-toolkit`). Ignore a few
seconds after each switch: a new keyword set can create a PSO
(`unity-perf:unity-shader-hitches`). AdditionalLightsOff disables the
`Light` components listed in `additionalLights`: lowering
`maxAdditionalLightsCount` alone only sets the per-object limit, is ignored in
Forward+ (U2-012), and (reading of URP source, not stated in the dossier) does
not stop additional-light shadow maps rendering [verify on your URP version].
`supportsAdditionalLightShadows` has no public setter, so disabling the lights
is the only script-side way to remove their shadow atlas. Assign every realtime
additional light in the test view. Use 60 s per variant for diagnosis and
`secondsPerVariant = 300` for the final 5 min A/B. In the Editor, changing the
URP asset at runtime writes to the asset; `OnDisable` restores it.
Targets `Unity 2021.3+` `URP 12+`.

```csharp
// LightingABToggle.cs - Unity 2021.3+ / URP 12+. Development builds only.
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public class LightingABToggle : MonoBehaviour
{
    public enum Variant { Baseline, MainShadowsOff, AdditionalLightsOff, ShortShadowDistance }

    [SerializeField] Light mainLight;
    [SerializeField] Light[] additionalLights = new Light[0];   // every realtime additional light in the test view
    [SerializeField] float shortShadowDistance = 10f;   // Unity's worked example: 40 -> 10 (U4-029)
    [SerializeField] float secondsPerVariant = 60f;         // 60 s diagnosis; 300 s for the final A/B

    UniversalRenderPipelineAsset urp;
    float baseDistance;
    int baseAdditionalLimit;
    LightShadows baseShadows;
    bool[] baseLightEnabled;
    int index;
    float nextSwitch;

    void OnEnable()
    {
        urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
        if (urp == null || mainLight == null) { enabled = false; return; }
        baseDistance = urp.shadowDistance;
        baseAdditionalLimit = urp.maxAdditionalLightsCount;
        baseShadows = mainLight.shadows;
        baseLightEnabled = new bool[additionalLights.Length];
        for (int i = 0; i < additionalLights.Length; i++)
            baseLightEnabled[i] = additionalLights[i] != null && additionalLights[i].enabled;
        index = 0;
        Apply(Variant.Baseline);
        nextSwitch = Time.realtimeSinceStartup + secondsPerVariant;
    }

    void Update()
    {
        if (Time.realtimeSinceStartup < nextSwitch) return;
        index = (index + 1) % 4;
        Apply((Variant)index);
        nextSwitch = Time.realtimeSinceStartup + secondsPerVariant;
    }

    void OnDisable()
    {
        if (urp != null && mainLight != null) Apply(Variant.Baseline);
    }

    void Apply(Variant v)
    {
        urp.shadowDistance = v == Variant.ShortShadowDistance ? shortShadowDistance : baseDistance;
        urp.maxAdditionalLightsCount = v == Variant.AdditionalLightsOff ? 0 : baseAdditionalLimit; // per-object limit only; ignored in Forward+
        for (int i = 0; i < additionalLights.Length; i++)
        {
            Light l = additionalLights[i];
            if (l != null) l.enabled = v != Variant.AdditionalLightsOff && baseLightEnabled[i];
        }
        mainLight.shadows = v == Variant.MainShadowsOff ? LightShadows.None : baseShadows;
        Debug.Log($"[LightingAB] variant={v} t={Time.realtimeSinceStartup:F0}");
        // To split the OVR Metrics CSV by variant, call AppendCsvDebugString here at most once per switch
        // (Q1-020; API in quest-perf:quest-profiling-toolkit).
    }
}
```

## 3. AstcHdrProbe.cs (runtime)

Answers the open question "does this headset expose ASTC HDR" (U4-038, Known
unknown for this skill). Run once on each headset; read with
`adb logcat -s Unity | grep AstcHdrProbe`. If `ASTC_HDR_6x6=False`, keep
Lightmap Encoding and HDR Cubemap Encoding at Normal or Low. Record the result
with the OS build; it is [verify on device] until someone logs it.

```csharp
// AstcHdrProbe.cs - Unity 2021.3+ (TextureFormat.ASTC_HDR_6x6 exists since 2019).
using UnityEngine;

public class AstcHdrProbe : MonoBehaviour
{
    void Start()
    {
        Debug.Log($"[AstcHdrProbe] device={SystemInfo.graphicsDeviceName} api={SystemInfo.graphicsDeviceType} " +
                  $"ASTC_HDR_6x6={SystemInfo.SupportsTextureFormat(TextureFormat.ASTC_HDR_6x6)} " +
                  $"ASTC_6x6={SystemInfo.SupportsTextureFormat(TextureFormat.ASTC_6x6)}");
    }
}
```

## 4. AllowDynamicResolution.cs (runtime)

Meta's documented fix for misaligned URP additional lights (blocky Forward+
tiles, drifting Deferred/Deferred+) when the viewport is scaled (Q3-053).
Add to the CenterEyeAnchor (or the XR rig's rendering camera), or tick
Dynamic Resolution on that camera. In custom HLSL use `_ScaledScreenParams`
for screen UVs.

```csharp
// AllowDynamicResolution.cs - Unity 2021.3+.
using UnityEngine;

[RequireComponent(typeof(Camera))]
public class AllowDynamicResolution : MonoBehaviour
{
    void Awake() => GetComponent<Camera>().allowDynamicResolution = true;
}
```

## 5. QuestPerf/MainLightLit.shader (URP HLSL)

Opaque, main light plus per-vertex SH ambient. Shows three rules:
- Shadow lookup through `MainLightRealtimeShadow`, which uses
  `SAMPLE_TEXTURE2D_SHADOW` with a comparison sampler: hardware PCF on Adreno
  (A2-085). No manual multi-tap compares.
- Shadow sampling and lighting only where `NdotL > 0` (the back-face early-out
  Unity applies automatically on `Unity ≥ 6000.5` with the Meta Quest build
  profile; write it yourself below that, QUEST-GF2-011). It is a dynamic
  branch; it pays only because it skips the shadow fetch.
- ShadowCaster with `ColorMask 0` and an empty fragment: no `clip()`, no fetch,
  so it qualifies for Fast-Z (A3-026).

Hard shadows only: the shader declares no `_SHADOWS_SOFT*` keywords, so it
ignores the asset's soft-shadow setting and adds no soft variants. Ambient uses
`SampleSH` (legacy probes / ambient probe); with APV use URP Lit or its probe
volume sampling instead. Add a `DepthOnly` pass if your renderer uses a depth
prepass or depth texture. SRP Batcher compatible (single `UnityPerMaterial`
CBUFFER). Stereo: `UNITY_VERTEX_OUTPUT_STEREO` for SPI/multiview. Targets
`URP 12-17`; compile-check on your version.

```hlsl
Shader "QuestPerf/MainLightLit"
{
    Properties
    {
        _BaseMap ("Base Map", 2D) = "white" {}
        _BaseColor ("Base Color", Color) = (1, 1, 1, 1)
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST;
            half4  _BaseColor;
        CBUFFER_END
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

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
                float3 positionWS : TEXCOORD1;
                half3  normalWS   : TEXCOORD2;
                half3  ambient    : TEXCOORD3;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings vert(Attributes v)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                VertexPositionInputs p = GetVertexPositionInputs(v.positionOS.xyz);
                VertexNormalInputs   n = GetVertexNormalInputs(v.normalOS);
                o.positionCS = p.positionCS;
                o.positionWS = p.positionWS;
                o.normalWS   = n.normalWS;
                o.uv         = TRANSFORM_TEX(v.uv, _BaseMap);
                o.ambient    = SampleSH(n.normalWS);   // per-vertex SH, as URP's Auto mode picks on mobile XR (U4-013)
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);

                half3 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).rgb * _BaseColor.rgb;
                half3 N = normalize(i.normalWS);

                Light mainLight = GetMainLight();          // no shadow fetch yet
                half  NdotL = dot(N, mainLight.direction);
                half3 direct = 0;

                UNITY_BRANCH
                if (NdotL > 0)
                {
                    float4 shadowCoord = TransformWorldToShadowCoord(i.positionWS);   // picks the cascade
                    half   shadow = MainLightRealtimeShadow(shadowCoord);             // hardware compare sampler
                    direct = mainLight.color * (NdotL * shadow * mainLight.distanceAttenuation);
                }

                return half4(albedo * (direct + i.ambient), 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull Back

            HLSLPROGRAM
            #pragma vertex ShadowVert
            #pragma fragment ShadowFrag
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"

            // Set by URP's shadow pass (declared in URP's ShadowCasterPass.hlsl, which this pass does not include).
            float3 _LightDirection;
            float3 _LightPosition;

            struct ShadowAttributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct ShadowVaryings
            {
                float4 positionCS : SV_POSITION;
            };

            ShadowVaryings ShadowVert(ShadowAttributes v)
            {
                ShadowVaryings o;
                UNITY_SETUP_INSTANCE_ID(v);

                float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
                float3 normalWS   = TransformObjectToWorldNormal(v.normalOS);
            #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                float3 lightDirectionWS = normalize(_LightPosition - positionWS);
            #else
                float3 lightDirectionWS = _LightDirection;
            #endif
                o.positionCS = TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, lightDirectionWS));
            #if UNITY_REVERSED_Z
                o.positionCS.z = min(o.positionCS.z, UNITY_NEAR_CLIP_VALUE);
            #else
                o.positionCS.z = max(o.positionCS.z, UNITY_NEAR_CLIP_VALUE);
            #endif
                return o;
            }

            // Empty fragment: no clip(), no texture fetch. With ColorMask 0 this is the
            // depth-only shape Qualcomm says gets Fast-Z at 2x rate (A3-026).
            half4 ShadowFrag(ShadowVaryings i) : SV_Target { return 0; }
            ENDHLSL
        }
    }
}
```

Alpha-tested casters (foliage, fences) cannot use the empty fragment; they need
`clip()` in the caster, which loses this path. Budget them separately, or cast
from an opaque proxy mesh set to Shadows Only (U4-032).
