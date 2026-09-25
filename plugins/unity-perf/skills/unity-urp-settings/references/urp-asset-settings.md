# URP asset, renderer, Player and XR settings for Quest: per-setting table

Read this from `SKILL.md` when editing an asset by hand, porting between URP 12, 14 and 17,
or checking what a serialized field is called. All findings are from the repo dossiers
(`research/unity.md`, `research/gles3.md`, `research/arm-mobile-hw.md`, `research/quest.md`),
accessed 2026-09-24. "Default" is the script default of a new asset (U2-001), not what a
template or the Meta Quest build profile ships; always audit the real `.asset` file.

Serialized field names are from URP source (U2-001 spot-check on 6000.5/staging, plus
2021.3/2022.3/6000.0 branches where the finding says so). Field names not listed in a
finding are marked "(not verified)".

## URP Asset (UniversalRenderPipelineAsset)

| Setting (Inspector) | Serialized field | Default | Quest recommendation | Versions | Reason | Finding |
|---|---|---|---|---|---|---|
| HDR | `m_SupportsHDR` | on | off | URP 12+ | forces intermediate + final blit; more bandwidth; Tile-Only unsupported | U2-001, U2-002, U2-030 |
| HDR Precision | `m_HDRColorBufferPrecision` | 32 Bits | 32 Bits if HDR is kept; never 64 | URP 14+ | 64-bit doubles colour bytes, adds bins | U2-002, A2-014, U2-035 |
| Alpha Processing | (not verified) | off | off | URP 14+ | requires 64-bit HDR | U2-002 |
| Depth Texture | `m_RequireDepthTexture` | off | off | URP 12+ | Copy Depth pass splits the native pass; GMEM loads | U2-003 |
| Opaque Texture | `m_RequireOpaqueTexture` | off | off | URP 12+ | Copy Color forces colour off-tile; can silently disable MSAA without StoreAndResolve | U2-004, G2-017, G2-018 |
| Opaque Downsampling | `m_OpaqueDownsampling` | 2x Bilinear | n/a if Opaque Texture off | URP 12+ | half-size target cannot merge under RG (TargetSizeMismatch) | U2-004 |
| Anti Aliasing (MSAA) | `m_MSAA` | Disabled | 2x start; 4x only on Quest 3/3S after A/B; never 8x | URP 12+ | see SKILL fix 5 and conflict U2-C1 | U2-006, U2-092, U2-093, G2-039, G2-040, A2-017 |
| Render Scale | `m_RenderScale` | 1.0 | set once at boot/level load; owner `quest-perf:quest-resolution-foveation` | URP 12+ | reallocates eye textures; snaps within 0.05 of 1.0 | U2-007, U2-047 |
| Upscaling Filter | `m_UpscalingFilter` | Auto | Auto | URP 12.1+ (STP 6.0+) | FSR active even at 1.0; STP forces TAA; off-tile | U2-008 |
| Store Actions | `m_StoreActionsOptimization` (not verified) | Auto | Discard after verification; ignored under Render Graph | URP 12, 14, 6.0-6.3 Compatibility Mode | Store "significantly increases the memory bandwidth" | U2-005, G2-016, U2-C4 |
| Soft Shadows | `m_SoftShadowsSupported` | off | off or Low | URP 12 on/off; tiers URP 14+ | high impact on tile GPUs | U2-009 |
| LOD Cross Fade | `m_EnableLODCrossFade` | on (Blue Noise) | off, or 2x2 Stencil dithering | URP 14+ | alpha test; stencil uses bits 4 and 8 | U2-010 |
| Terrain Holes | `m_SupportsTerrainHoles` | on | off unless used | URP 12+ | Unity perf page and Meta OpenXR 2.6 page | U2-011 |
| Additional Lights | `m_AdditionalLightsRenderingMode` (not verified) | not listed in U2-001 | owner `unity-perf:unity-lighting` | URP 12+ | Per Vertex/Disabled on low end | U2-012 |
| Per Object Limit | `m_AdditionalLightsPerObjectLimit` | 4 | owner `unity-perf:unity-lighting`; 1 unrolls the light loop with the Quest profile optimizations (6.5+) | URP 12+ | ignored in Forward+ | U2-012, X-C7 |
| Main/additional shadow resolution, cascades, distance | (see source) | 2048, 1 cascade, 50 | owner `unity-perf:unity-lighting` | URP 12+ | each shadow map is a separate RT | U2-014 |
| SRP Batcher | `m_UseSRPBatcher` | on | on | URP 12+ | owner `unity-perf:unity-draw-calls-batching` | U2-016 |
| Dynamic Batching | `m_SupportsDynamicBatching` | off | owner `unity-perf:unity-draw-calls-batching` | URP 12+ | | U2-001 |
| Volume Update Mode | `m_VolumeFrameworkUpdateMode` | Every Frame | Via Scripting + `camera.UpdateVolumeStack()` | URP 12+ | main-thread saving; no Quest ms figure | U2-015 |
| Reflection Probe Blending / Atlas | (see source) | Blending off; Atlas on (6000.5) | off (Meta) | URP 14+ | owner `unity-perf:unity-lighting` | U2-013 |
| GPU Resident Drawer / GPU occlusion culling | (not verified; audit searches `GPUResidentDrawer`) | off | Vulkan + Forward+ only; owner `unity-perf:unity-draw-calls-batching` | Unity 6.0+ | GLES unsupported; broken occlusion on 6.5.0-6.5.7 | U3-032, U1-020 |

## Universal Renderer Data

| Setting | Serialized field | Default | Quest recommendation | Versions | Reason | Finding |
|---|---|---|---|---|---|---|
| Rendering Path | `m_RenderingMode` (not verified) | not listed in U2-001 | Forward, or Forward+ from about 5 real-time lights / with GRD; never Deferred or Deferred+ | Forward+ URP 14+; Deferred+ 6.1+ | G-buffer GMEM loads; no MSAA in Deferred | U2-019, U2-027, U1-034, X-C9 |
| Depth Priming Mode | `m_DepthPrimingMode` (not verified) | Disabled | Disabled | URP 12+ | Auto unsupported on Android; unsupported with MSAA / TBDR runtime | U2-020, U3-058, G2-020 |
| Depth Texture Mode (copy depth) | `m_CopyDepthMode` | After Opaques (URP 12); After Transparents (URP 14+) | After Transparents when a depth texture is required | After Transparents URP 14+ | avoids colour store/reload between opaques and transparents | U2-021, U2-022, G2-019 |
| Intermediate Texture | `m_IntermediateTextureMode` (not verified) | Always | Auto | URP 12+ | Always forces an intermediate | U2-023, G2-024 |
| Native RenderPass | `m_UseNativeRenderPass` (not verified) | off | on with Vulkan on URP 12/14 and 6.0-6.3 Compatibility Mode; no effect on GLES; gone under RG | URP 12-17 Compat | owner `unity-perf:unity-render-graph-tiling` | U2-081, U2-024, G2-022 |
| Tile-Only Mode | (not verified; audit searches `TileOnly`) | off | on in a development branch as a guard | Unity 6.5+ | blocks off-tile settings; validation stripped from release | U2-025, U1-063 |
| SSAO feature | n/a | not added | remove | URP 12+ | several passes, high tile impact | U2-028 |
| Decal feature | n/a | not added | avoid; baked decal meshes | URP 12+ | requires intermediate | U2-029 |
| Full Screen Pass feature | `fetchColorBuffer` | true | false unless the effect reads colour | URP 14+ | forces intermediate + colour copy | U2-026 |

## Camera (per camera, UniversalAdditionalCameraData)

| Setting | Recommendation | Finding |
|---|---|---|
| Rendering > Depth Texture / Opaque Texture | Use Pipeline Settings or Off; an "On" override re-enables the copy | U2-003 notes |
| Post Processing checkbox | off unless using on-tile post (6.3+); owner `unity-perf:unity-render-graph-tiling` | U2-030, U2-091 |
| MSAA / HDR | consistent with the asset (GLES multipass validation bug) | G2-027 |
| Viewport rect | default; a non-default rect forces an intermediate | U2-030 |
| Camera stacking | avoid; breaks on-tile | U2-032 |

## Player settings (Android)

| Setting | Recommendation | Owner | Finding |
|---|---|---|---|
| Graphics APIs | Vulkan first, explicit list | gles3-perf:gles-vs-vulkan | U2-094, U2-091 |
| Color Space | GLES + OpenXR: validation requires Linear (G2-094); Linear makes blending costlier (U3-063) and loses Tile-Only / on-tile post from 6000.6.0b6 (U1-063) | this skill (report only) | U1-063, U3-063, G2-094 |
| Scripting Backend / Target Architectures | IL2CPP, ARM64 only | unity-perf:unity-cpu-scripting | U5-021 |
| IL2CPP Code Generation | runtime-speed option for release | unity-perf:unity-cpu-scripting | U5-016 |
| Multithreaded Rendering | on; never ship off | unity-perf:unity-cpu-scripting | A1-061 |
| Graphics Jobs | Legacy mode for main-thread-bound apps (2022.3.35f1+, 6.x); unvalidated on 2021.3 | unity-perf:unity-cpu-scripting | A1-058, A1-059, A1-062 |
| Use incremental GC | on (default) | unity-perf:unity-cpu-scripting | U5-005, UNITY-GF1-017 |
| Texture compression | ASTC | unity-perf:unity-memory-assets | U4-046, U4-053 |
| Vulkan: Number of swapchain buffers | 3 (default); takes effect only from 6000.0.83f1 / 6000.3.24f1 / 6000.6.0f1 | this skill | U5-025, U1-068, X-C5 |
| Vulkan: Get swapchain image late as possible | off | this skill | U5-025 |
| Use OpenGL ES 3.0 shaders (6.6 GLES) | on keeps 16 visible lights; off gives 32 + more shader work | this skill / `unity-perf:unity-lighting` | U1-094, U1-040, X-C6 |

## XR settings

| Setting | Recommendation | Owner | Finding |
|---|---|---|---|
| XR plugin | OpenXR on Unity 6.x; Oculus XR unsupported from 6.5 | unity-perf:unity-upgrade-risks | U1-091, U1-092 |
| OpenXR Render Mode | Single Pass Instanced (Multiview on Quest) | this skill | U2-040, U1-092 |
| OpenXR Depth Submission Mode | None unless AppSW or composition needs depth (Meta) | quest-perf:quest-appsw | U1-092 |
| OpenXR Latency Optimization | conflict: Meta recommends Prioritize Input Polling; Unity 1.18 default is Prioritize Rendering | quest-perf:quest-frame-pacing | Q2-076, U5-092, U5-C2 |
| Optimize Buffer Discards (Vulkan) | on whenever AppSW is on | quest-perf:quest-appsw | Q3-069, G1-031 |
| Space Warp motion-vector format | RG16f halves bandwidth vs RGBA16f | quest-perf:quest-appsw | Q3-070, G1-033 |
| Foveated rendering | SRP Foveation on Unity 6+ | quest-perf:quest-resolution-foveation | U1-092, U1-085 |
| Refresh rate | request it explicitly; default 72 Hz | quest-perf:quest-frame-pacing | Q2-010, Q2-011, Q2-012 |
| OVRManager "Use Recommended MSAA Level" | off; URP asset owns MSAA | this skill | U2-050 |

## URP version availability (U2-018, U2-073)

| URP | Unity | Relevant to this table |
|---|---|---|
| 12 | 2021.3 | Forward/Deferred only; copy depth After Opaques or Force Prepass; Native RenderPass toggle; Store Actions; no HDR Precision, no LOD Cross Fade, no soft-shadow tiers |
| 14 | 2022.3 | adds Forward+, After Transparents, HDR Precision, LOD Cross Fade, soft-shadow quality |
| 17.0 | 6.0 | Render Graph default with Compatibility Mode toggle; STP |
| 17.x | 6.1 | Deferred+, Meta Quest build profile, VRS API |
| 17.x | 6.2 | QCOM shader resolve for MSAA on Quest |
| 17.x | 6.3 | on-device Render Graph Viewer; XR on-tile post |
| 17.x | 6.4 | Compatibility Mode removed |
| 17.x | 6.5 | Tile-Only Mode; Quest shader optimizations |
| 17.x | 6.6 | URP Settings Analyzer in Project Auditor; GLES 3.1 minimum |

Full version matrix: `unity-perf:unity-version-matrix`.

## Baseline snippet (asset-level fixes 1, 2, 5 and 10)

Applies HDR off, Depth/Opaque Texture off, MSAA capped at 4x and Terrain Holes off to every
URP asset used by the Graphics default or any Quality level. Review the diff in version
control before committing; it does not touch renderer data, cameras or Player settings.

```csharp
// Assets/Editor/QuestUrpBaseline.cs  (Unity 2021.3+ / URP 12+)
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class QuestUrpBaseline
{
    [MenuItem("Tools/Quest Perf/Apply URP Asset Baseline")]
    static void Apply()
    {
        var seen = new System.Collections.Generic.HashSet<UniversalRenderPipelineAsset>();
        Visit(GraphicsSettings.defaultRenderPipeline, seen);
        for (int i = 0; i < QualitySettings.names.Length; i++)
            Visit(QualitySettings.GetRenderPipelineAssetAt(i), seen);
        AssetDatabase.SaveAssets();
    }

    static void Visit(RenderPipelineAsset rp, System.Collections.Generic.HashSet<UniversalRenderPipelineAsset> seen)
    {
        var a = rp as UniversalRenderPipelineAsset;
        if (a == null || !seen.Add(a)) return;
        Undo.RecordObject(a, "Quest URP baseline");
        a.supportsHDR = false;                 // fix 1
        a.supportsCameraDepthTexture = false;  // fix 2
        a.supportsCameraOpaqueTexture = false; // fix 2
        if (a.msaaSampleCount > 4) a.msaaSampleCount = 4; // fix 5: never above 4x
        var so = new SerializedObject(a);
        var holes = so.FindProperty("m_SupportsTerrainHoles"); // fix 10
        if (holes != null) holes.boolValue = false;
        so.ApplyModifiedProperties();
        EditorUtility.SetDirty(a);
        Debug.Log("Quest URP baseline applied to " + AssetDatabase.GetAssetPath(a));
    }
}
```

## Volume stack refresher (fix 10, Volume Update Mode = Via Scripting)

Call `Refresh()` after enabling/disabling a Volume or changing its weight/profile. URP 12+.

```csharp
using UnityEngine;
using UnityEngine.Rendering.Universal;

public sealed class VolumeStackRefresher : MonoBehaviour
{
    [SerializeField] Camera targetCamera;

    // Call after enabling/disabling a Volume or changing its weight/profile.
    public void Refresh()
    {
        if (targetCamera != null)
            targetCamera.UpdateVolumeStack(); // URP CameraExtensions
    }
}
```
