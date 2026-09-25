---
name: quest-resolution-foveation
description: "GPU pixel-cost controls on Quest 2/3/3S in Unity URP: eye-buffer size, render scale, dynamic resolution, fixed and dynamic foveated rendering (FFR), subsampled layout, Symmetric Projection, multiview render regions and Meta Quest Super Resolution. Use when GPU-bound on fill rate, choosing an FFR level, when FFR seems to do nothing, for peripheral foveation artifacts, or when URP post-processing or an intermediate texture disables foveation."
---

# Quest resolution and foveation

Goal served: **Throughput** (fewer shaded and stored pixels), with a **Consistency** side through dynamic resolution (thermal degradation without dropped frames) and FFR/level changes kept off the gameplay path.

## When to use / when not

Use when:

- A capture shows the app is GPU-bound on **fragment/fill** work (render-scale test moves GPU time, see Diagnose).
- Choosing render scale, eye-buffer allocation or dynamic-resolution range per headset.
- Choosing an FFR level, or FFR "does nothing", or the periphery looks blocky / the top half goes low-res.
- Deciding on Subsampled Layout, Symmetric Projection, Multiview Render Regions (MVRR), Quad Views or MQSR.

Do not use; go to the sibling instead:

- Bottleneck not yet identified (CPU vs GPU vs pacing): `quest-perf:quest-triage`.
- Vertex/geometry/draw-submission bound (render scale 0.01 changes nothing): `unity-perf:unity-draw-calls-batching`.
- Still short after resolution and foveation cuts: `quest-perf:quest-appsw`.
- Blurry UI/text, overlay or video layers: `quest-perf:quest-compositor-layers`.
- GPU level 5, Battery Saver, throttling behaviour: `quest-perf:quest-levels-thermal` (this skill owns only the dynamic-resolution link to L5).
- URP asset settings in general (MSAA, HDR, post, rendering path): `unity-perf:unity-urp-settings`; on-tile post and Render Graph pass merging: `unity-perf:unity-render-graph-tiling`.
- Version regressions and patch floors in detail: `unity-perf:unity-upgrade-risks`.
- `QCOM_texture_foveated` mechanics and GLES foveation caveats: `gles3-perf:gles-extensions-multiview`.
- Bins, GMEM, direct mode hardware detail: `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Eye-tracked foveation (ETFR): Quest Pro only; it does nothing on Quest 2/3/3S (Q2-007 / Q3-040). No further coverage here.

## Diagnose first

Profile with dynamic resolution and dynamic foveation **off** and CPU/GPU levels fixed; both change the workload being measured (Q3-051, Q3-029).

1. **Is it fill-bound?** Meta's isolation step 2 (owned by `quest-perf:quest-triage`): with the app already GPU-bound, set render scale to 0.01. GPU time drops a lot = fill-bound, this skill applies. No-rebuild variant: lower `debug.oculus.textureWidth` / `textureHeight` (defaults 1440x1584 Quest 2, 1680x1760 Quest 3/3S; Q1-080).
2. **Which eye buffer is actually submitted?** VrApi logcat `SF=` is submitted size / recommended size; OVR Metrics EBW/EBH and the CSV columns `eye_buffer_width`, `eye_buffer_height`, `render_scale` (Q2-023 / Q3-052):
   ```sh
   adb logcat -s VrApi
   ```
   Read the `SF=`, `Fov=`, GPU% and `Stale` fields of the once-per-second line. `DSF=` above 1 means the display processor is upscaling.
3. **Is FFR really applied?** Sweep the level with no rebuild (Q1-081 / Q3-028):
   ```sh
   adb shell setprop debug.oculus.foveation.dynamic 0
   for l in 0 1 2 3 4; do adb shell setprop debug.oculus.foveation.level $l; sleep 20; done
   ```
   Log `app_gpu_time_microseconds` (OVR Metrics) per step. `Fov=0` while the app thinks it set a level = setting not reaching the runtime. GPU time flat across levels = the heavy pass is not foveated (intermediate target or direct mode; G2-061, A2-023).
4. **Which surfaces escape FFR?** `ovrgpuprofiler -e <pkg>` (restart app), then `ovrgpuprofiler -t -v`: each surface prints `Mode:` (0 Direct, 1 HwBinning, 2 SwBinning, 3 HwDirect) and each bin prints `Fov x/y` or `Fov L<x>/<y> R<x>/<y>` (Q1-067, Q1-068, Q1-069, G2-064). A full-eye-resolution surface that is not the swapchain, or a single bin covering the whole surface (direct mode), gets no FFR (A3-024). Run `ovrgpuprofiler -d` afterwards; detailed mode costs about 10% GPU (Q1-067).
5. **Does the main pass write the eye texture?** Frame Debugger: DrawOpaqueObjects target unnamed (back buffer) = direct; `_CameraColorAttachmentA` = intermediate (Q3-008, Q3-013). On 6.x also check the Render Graph Viewer.
6. **Dynamic-resolution controller behaviour:** log `SF`, GPU% and `Stale` at 1 Hz while ramping GPU load; Meta publishes no thresholds, step size or hysteresis (Q3-061).

## Key numbers

| Item | Value | Applies to | Source |
|---|---|---|---|
| Default eye buffer (scale 1.0) | Quest 2 1440x1584; Quest 3 and 3S 1680x1760 | per device | Q2-017 / Q3-001, ARM-GF2-004 [doc] |
| Quest 3/3S vs Quest 2 pixels | about +30% (2.96 vs 2.28 MP per eye) | Quest 3/3S | Q2-019 [doc] |
| Panel-match render scale | Quest 2 about 1.24, Quest 3S about 1.09; Quest 3 not published (table arithmetic about 1.23 x 1.25) | per device | Q2-018 / Q3-002 [doc] |
| Quest 3S at 1.09 | about +19% pixels (1.09²) for a panel-matched image | Quest 3S | Q2-088 [doc]; +19% is arithmetic, not published |
| URP render-scale snap | 0.96-1.04 snaps to 1.0 (`kRenderScaleThreshold = 0.05`); asset range 0.1-2.0 | URP 12/14/17 | Q2-022 / Q3-006 [doc, source code] [verify on device] |
| FFR saving, Meta example | Low 6.5%, Medium 11.5%, High 21% GPU utilisation (16% of the workload was TimeWarp); headline "up to 25%" | device not stated | Q3-022 [measured] [verify on device] |
| FFR per device | no published number for Quest 2 vs 3 vs 3S; 3S has 96° vs 110° H FOV and 20 vs 25 PPD, so savings differ | Quest 2/3/3S | Q3-022, Q2-091 [doc] |
| SRP Foveation vs Legacy | "often 20-30% faster" frame time for multi-pass/post pipelines (vendor claim) | Unity 6.x OpenXR | Q4-061, U1-085 [doc] [verify on device] |
| Symmetric Projection | typical 5-15% GPU when GPU-bound | Vulkan + Multiview | Q2-027 / Q3-087, G1-037 [doc]; Q3-087 tags the 5-15% as [measured] (a Meta-published range) [verify on device] |
| MVRR | typical 3-8% GPU when GPU-bound | Vulkan, Unity ≥ 6000.1 | Q2-027 / Q4-074, G1-039 [doc] [verify on device] |
| Quad Views | about 50% fewer pixels; extra geometry pass | Horizon OS v85+, OpenXR 1.18.0+ | Q3-090 [doc] [verify on device] |
| Subsampled layout | no published ms or bandwidth saving | Vulkan | Q3-047 [doc] |
| MQSR / sharpening / supersampling | no published ms cost on any Quest | all | Q3-020 [doc] |
| OVRManager dynamic-res defaults | Quest 2: 0.7-1.3; Quest 3/3S: 0.7-1.6 (eye textures allocated at max; 1.6 = 2688x2816 per eye) | Meta XR Core SDK 207 | Q2-024 / Q2-090 [doc, SDK source] [verify on device] |
| OpenXR Automatic Dynamic Resolution floor | effective minimum 0.5 | Unity ≥ 6000.3, OpenXR 1.16+ | Q3-059 [doc] |
| VRC.Quest.Performance.4 | render scale ≥ 85% for most of the experience; the VRC page marks it recommended, while Meta's render-scale doc says too-low render scale will not be approved (Q2-026) | Store apps | Q1-087 / Q2-026 / Q3-003 [doc] |
| Battery Saver | forces FFR level 3 | all Quest | Q2-062 [doc] |

GPU level 5 is available only with dynamic resolution enabled (Q2-029, Q2-050, Q3-049); the level rules themselves live in `quest-perf:quest-levels-thermal`.

Read [references/foveation-levels.md](references/foveation-levels.md) when you need the per-API/per-stack level mapping, setting paths, version gates, the regression list or the GLES conflict in full. Read [references/dynamic-resolution.md](references/dynamic-resolution.md) when choosing or debugging a render-scale or dynamic-resolution path, or checking a Unity patch against the known dynamic-resolution issues.

## Fixes, ranked by payoff ÷ effort

### 1. Make the heavy pass land in the eye texture, so FFR applies at all

FFR is a per-bin property of the swapchain surface. A main pass into a non-swapchain intermediate gets no FFR, and a depthless full-screen final blit runs in direct mode with no FFR (A2-023, A3-024, G2-061). On the Legacy/Meta API, intermediates (post, tonemapping, camera stacking) are never foveated (Q3-025).

- If the Universal Renderer has post-processing off, also untick **Post Processing** on the camera (CenterEyeAnchor); otherwise URP renders into `_CameraColorAttachmentA` and adds a full-resolution blit (Q3-013, issue 22353, reproduced on 2021.3.21f1 and 2022.2.12f1, no 2021.3/2022.3 fix listed).
- Keep HDR off on Quest: the SRP path with URP HDR has been reported to foveate the top half instead of the periphery on 6.0 (Q3-037 [community]); Unity 6.6's untethered checklist also says disable HDR (Q3-093). HDR and MSAA choices are owned by `unity-perf:unity-urp-settings`.
- If post must stay, use the SRP Foveation API on Unity 6 (fix 2) and on-tile post (`unity-perf:unity-render-graph-tiling`). On 6.0, foveated UberPost/FinalPostBlit needs 6000.0.22f1+ (U1-082).
- Effect: turns FFR's saving (fix 2) from zero into real; removes one full-screen store + reload. Average GPU time down; no variance effect.
- Cost: none visually; may drop effects you did not know were on.
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `Vulkan` `GLES` · **Throughput**.

### 2. Turn on FFR with the right API and a fixed level

- **Unity 6.x + OpenXR (preferred):** Project Settings > XR Plug-in Management > OpenXR > Foveated Rendering > gear > Foveated Rendering Method = *Foveated rendering (SRP API)* (default from OpenXR 1.17.0). Then set the level at runtime; the project feature must be on or the value is ignored (Q3-025, Q3-026):
  ```csharp
  // Unity 6000.0+, OpenXR 1.11+, URP. Untested on device.
  using System.Collections;
  using System.Collections.Generic;
  using UnityEngine;
  using UnityEngine.XR;

  public class QuestFoveation : MonoBehaviour
  {
      [Range(0f, 1f)] public float level = 0.5f; // Meta: 0.5 = Medium; Oculus XR map: <0.33 low, <0.66 medium, >=0.66 high
      static readonly List<XRDisplaySubsystem> s_Displays = new List<XRDisplaySubsystem>();

      IEnumerator Start()
      {
          for (int i = 0; i < 3; i++) yield return null; // Unity's sample waits ~3 frames for the display subsystem
          Apply(level);
      }

      // Call only at scene transitions or when entering/leaving menus (Q3-023).
      public static void Apply(float value)
      {
  #if UNITY_6000_0_OR_NEWER
          SubsystemManager.GetSubsystems(s_Displays);
          if (s_Displays.Count > 0)
              s_Displays[0].foveatedRenderingLevel = Mathf.Clamp01(value);
  #endif
      }
  }
  ```
- **Unity 2022.3, or Meta XR SDK stack:** only the Meta/Legacy path exists on 2022 (Q3-025, Q3-C4); it does not foveate intermediates, so fix 1 is mandatory there:
  ```csharp
  // Meta XR Core SDK (OVRManager present). Level enum: Off/Low/Medium/High/HighTop (HighTop = High on OpenXR backend).
  OVRManager.foveatedRenderingLevel = OVRManager.FoveatedRenderingLevel.Medium;
  OVRManager.useDynamicFoveatedRendering = false; // fixed level; see fix 8
  ```
- Level choice: start at Medium, sweep 0-3 with `debug.oculus.foveation.level` (Diagnose step 3) and keep the level where GPU time stops falling faster than the periphery degrades. **Low can be a net loss** on simple-shader content (Q3-023). Change the level only at transitions and turn FFR off in menus (Q3-023); a mid-gameplay change reads as a pop.
- Effect: average GPU time down by the fragment share only (Meta example 6.5 / 11.5 / 21%, Q3-022); vertex, binning and compositor costs unchanged (Q3-021). No variance effect with a fixed level.
- Cost: lower peripheral resolution; screen-space effects that sample neighbours can show tile-resolution steps at the edges. No HLSL remap needed on Quest (`SystemInfo.foveatedRenderingCaps = FoveationImage`, Q3-034). FFR does not touch compositor layers, in quality or cost (Q3-024).
- Tags: `Quest 2` `Quest 3/3S` `Unity ≥ 6000.0` (SRP API) or `Unity 2022.3` (Legacy) `Vulkan` · **Throughput**. GLES: see Pitfalls (conflict).

### 3. Symmetric Projection, then Multiview Render Regions

- **Symmetric Projection:** OpenXR > Meta Quest Support > *Symmetric Projection (Vulkan)* (Oculus XR: Symmetric Projection). Needs Vulkan + Multiview; Oculus XR 3.0.0+ or OpenXR 1.9.1+ (Q2-027 / Q3-087, Q4-058). Typical 5-15% GPU when GPU-bound.
- **MVRR:** OpenXR > Meta Quest Support > *Multiview Render Regions Optimizations* = All Passes (Unity 6.2+, OpenXR 1.15+) or Final Pass; Oculus: *Optimize Multiview Render Regions* (final pass only). Unity ≥ 6000.1; 6.3+ requires Render Graph (Q3-088, Q4-075). Plugins: OpenXR 1.14+ (All Passes 1.15+); Oculus XR 4.5.0 per changelog vs 4.6+ per Unity 6.6 manual (conflict Q4-C2; Q3-088, Q4-058). Typical 3-8%.
- Final Pass mode gives nothing when the frame goes through intermediates/post; switch All Passes to Final Pass only if bloom/DoF/blur edges clip (Q4-075). Custom Render Graph raster passes opt in with `SetExtendedFeatureFlags(ExtendedFeatureFlags.MultiviewRenderRegionsCompatible)` or drop out of All Passes (Q4-077).
- Conflict (Q4-C6): Meta's Unity page recommends Symmetric Projection for most apps; the native page warns it can hurt with heavy post-processing because intermediate passes are not foveated and shade the extra nasal pixels. A/B it on your pipeline. MVRR can regress with very simple shaders or minimal overdraw (Q4-074).
- Effect: average GPU time down; no variance effect. Cost: imperceptible per Meta; profile custom shaders that assume per-eye asymmetry.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `Unity ≥ 6000.1` (MVRR) · **Throughput**.

### 4. Dynamic resolution (with GPU level 5 as the bonus)

- **Meta XR SDK:** OVRCameraRig > OVR Manager > *Enable Dynamic Resolution*; set `quest2Min/MaxDynamicResolutionScale` and `quest3Min/MaxDynamicResolutionScale` in the Inspector (the max sets the startup allocation; the quest3 fields also govern 3S). Toggle at runtime with `OVRManager.instance.enableDynamicResolution` (Q3-050, Q2-024). Minimum versions: 2021.3.45f1 / 2022.3.49f1 / 6000.0.25f1 with Oculus XR 3.3.0+ or OpenXR 1.12.1+ (Q2-025).
- **Unity OpenXR (Unity ≥ 6000.3, OpenXR 1.16.0+):** Automatic Viewport Dynamic Resolution, Vulkan, URP 17.0.3+, camera *URP Dynamic Resolution* on; not in Compatibility Mode; use Final Pass MVRR with it (Q3-059).
- Always tick *Dynamic Resolution* on the CenterEyeAnchor camera (or set `camera.allowDynamicResolution = true` before rendering), or URP additional lights misalign (Q3-053).
- Range: keep the minimum at 0.85 for Store apps (VRC Perf.4, Q3-003). Lower the maximum from the 1.6 default if memory is tight: allocation happens at the max (Q2-024).
- Effect: **Consistency** first: during thermal events the OS lowers render scale instead of dropping frames (Q3-049, A3-086). **Throughput**: required for GPU L5 (Q2-029). Average GPU time follows the viewport; memory follows the max.
- Cost: variable sharpness; with both dynamic foveation and dynamic resolution on, foveation rises first and resolution drops after (Q3-031).
- Tags: `Quest 2` `Quest 3/3S` `URP 14.0.9+` `Vulkan` (GLES unconfirmed, KU-09); OpenXR path: `Unity ≥ 6000.3` `OpenXR 1.16+` `URP 17.0.3+` · **Consistency + Throughput**. Known issues and fix versions: [references/dynamic-resolution.md](references/dynamic-resolution.md).

### 5. Set render scale once, move only the viewport per frame

- In URP the asset (or camera) Render Scale is what lands in `XRDisplaySubsystem.scaleOfAllRenderTargets` every camera, with the ±0.05 snap (Q2-022 / Q3-006). Conflict Q3-C5: Meta says set `XRSettings.eyeTextureResolutionScale` (and "may additionally need" URP `renderScale`); Unity says `eyeTextureResolutionScale` is unsupported in URP. Working rule: set both to the same value, only at load/transition, and use ≤ 0.94 or ≥ 1.06 [verify on device with `SF=`].
- Per-frame changes: `XRSettings.renderViewportScale` (0-1, no reallocation, next frame) (Q3-004, Q3-008), the pattern of Meta's Unity-PerformanceSettings sample (Q3-012):
  ```csharp
  // Unity 2021.3+ (URP 14.0.9+ recommended when intermediates exist, Q3-014). Untested on device.
  using UnityEngine;
  using UnityEngine.XR;

  public static class QuestResolution
  {
      // Call at a load screen: reallocates eye textures (hitch).
      public static void SetAllocation(float scale, UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset urp)
      {
          XRSettings.eyeTextureResolutionScale = scale;
          if (urp != null) urp.renderScale = scale;
      }

      // Safe per frame: effective scale = renderViewportScale * eyeTextureResolutionScale.
      public static void SetEffective(float target)
      {
          float alloc = XRSettings.eyeTextureResolutionScale;
          XRSettings.renderViewportScale = Mathf.Clamp01(target / alloc);
      }
  }
  ```
- Per-device targets: Quest 3S at 1.0 is already below panel resolution (1.09 would match), so cutting scale on 3S costs visible clarity; above about 1.09 on 3S buys only sub-pixel gain (Q2-018, Q2-088). Tier by `SystemHeadset` (`quest-perf:quest-budgets-tiers`).
- Effect: average GPU time scales roughly with pixel count for fill-bound frames [verify on device]; allocation changes at load avoid mid-play hitches (**Consistency**).
- Cost: sharpness. With post-processing intermediates, `renderViewportScale` disables foveation on intermediate passes under Render Graph (Q3-035, Q3-C8), and the URP Dynamic Resolution camera path cannot be combined with FFR or TAA (Q3-009).
- Tags: `Quest 2` `Quest 3/3S` `URP 12+` `Vulkan` `GLES` · **Throughput**.

### 6. Custom Render Graph passes: match the foveation state

A custom raster pass on camera color that does not set the same foveation state as DrawObjects splits the native render pass (`FRStateMismatch`) and renders at full density (U2-054 / U1-085):

```csharp
// URP 17 (Unity 6000.0+), body of ScriptableRenderPass.RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData).
// Assumes: class PassData { } declared in the pass. Untested on device.
#if UNITY_6000_0_OR_NEWER
var cameraData   = frameData.Get<UniversalCameraData>();
var resourceData = frameData.Get<UniversalResourceData>();
using (var builder = renderGraph.AddRasterRenderPass<PassData>("MyColorPass", out var passData))
{
    builder.SetRenderAttachment(resourceData.activeColorTexture, 0);
    // Approximates URP's internal canFoveateIntermediatePasses (off only when renderViewportScale is active, Q3-035) [verify on device: Render Graph Viewer shows one merged native pass].
    bool fovIntermediates = UnityEngine.Mathf.Approximately(UnityEngine.XR.XRSettings.renderViewportScale, 1f);
    builder.EnableFoveatedRasterization(cameraData.xr.supportsFoveatedRendering && (fovIntermediates || resourceData.isActiveTargetBackBuffer));
    builder.SetRenderFunc((PassData d, RasterGraphContext ctx) => { /* draw */ });
}
#endif
```

In custom HLSL, derive screen UVs from `_ScaledScreenParams`, never `_ScreenParams`, or effects misalign under dynamic resolution (Q3-053). URP's helper already does this:

```hlsl
// URP 14/17
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareOpaqueTexture.hlsl"
float2 uv = GetNormalizedScreenSpaceUV(input.positionCS); // uses _ScaledScreenParams
half3 c = SampleSceneColor(uv);
```

`SampleSceneColor` already applies `UnityStereoTransformScreenSpaceTex` and `SAMPLE_TEXTURE2D_X`.

- Effect: restores foveation and pass merging for custom passes; average GPU time down. Cost: none visual beyond FFR's own. Tags: `Quest 2` `Quest 3/3S` `Unity ≥ 6000.0` `URP 17` `Vulkan` · **Throughput**.

### 7. Subsampled layout: A/B, default on only for direct-to-eye-texture pipelines

- Enable: OpenXR > Foveated Rendering gear > *Subsampled Layout (Vulkan)* or `FoveatedRenderingFeature.TrySetSubsampledLayoutEnabled(true)` (OpenXR 1.16.0+); Meta path: Meta XR feature group > *Meta XR Subsampled Layout* (OpenXR 1.9.0+) (Q3-044). Requires FDM2, Vulkan.
- Conflict Q3-C6: Meta "strongly recommends" it with Vulkan FFR (Q3-041); against it: it hurts with post-processing (Q3-042), adds TimeWarp cost so use only at FFR ≥ 2 (Q4-056), adds compositor cost with AppSW (Q3-044), and Quest 3-only right-eye corner artifacts in MR (issue 17355, Q3-046). No saving is published (Q3-047).
- A/B with no rebuild: `adb shell setprop debug.oculus.foveation.subsampled 1` vs `0` (Q3-045); compare app GPU time and compositor time (`TW=`), on Quest 2 and Quest 3 separately.
- Effect: lower store bandwidth and average GPU time, no variance effect. It can raise TimeWarp/compositor time (Q4-056, Q3-044).
- Cost: removes the blocky periphery via the compositor's bilinear upsample (Q3-041); right-eye corner artifacts in MR on Quest 3 (issue 17355).
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` · **Throughput** (bandwidth).

### 8. Dynamic foveation: only as a safety valve

- Level set becomes a maximum; runtime raises foveation with GPU utilisation (Q3-029). Unity OpenXR: gear > *Dynamic Foveation (Vulkan)* or `FoveatedRenderingFeature.DynamicFoveationEnabled`; SRP API only; OpenXR 1.18.0 vs 1.19 conflict (Q3-C2, plan for 1.19+); not with Quad Views or Legacy (Q3-030). Meta SDK: `OVRManager.useDynamicFoveatedRendering`.
- Effect: helps throughput under load, **hurts visual consistency** (periphery quality varies). Turn off when profiling. Tags: `Quest 2` `Quest 3/3S` `Vulkan` `Unity ≥ 6000.0` `OpenXR 1.19+ (1.18.0 per changelog, Q3-C2)` or `Meta XR Core SDK` · **Throughput**.

### 9. Higher-effort or niche options

- **Quad Views:** manifest `com.oculus.feature.QUAD_VIEWS` (required=true restricts to Horizon OS v85+), OpenXR 1.18.0+; must not be combined with FFR or dynamic foveation; inset fixed at centre without eye tracking; extra geometry pass, so measure in vertex-heavy scenes (Q3-090). Effect: average GPU time down only when fill-bound (about 50% fewer pixels, Q3-090); an extra geometry pass can cancel it. Cost: lower periphery resolution, inset fixed at centre. Tags: `Quest 2` `Quest 3/3S` API not stated (Q3-090) [verify on device] `OpenXR 1.18.0+` `Horizon OS v85+` · **Throughput**.
- **MQSR / sharpening:** `OVRManager.sharpenType` for the eye buffer; OVROverlay Super Sample / Sharpen / Auto Filtering per layer (Q3-019). Cost is in compositor GPU time and unpublished; Meta says weigh it against simply raising eye-buffer resolution; Auto filtering is a no-op when unneeded (Q3-016, Q3-017, Q3-020). Measure `TW=` A/B with levels fixed. Effect: adds compositor GPU time (unpublished, Q3-020). It pays off only if it lets you lower eye-buffer scale for the same clarity, so average app GPU time falls only with a matching render-scale cut; no variance effect. Tags: `Quest 2` `Quest 3/3S` `Meta XR Core SDK` compositor-side; API not stated (Q3-017) · **Throughput** (indirect).

## Verify

- **FFR:** with `debug.oculus.foveation.dynamic 0` and levels fixed, `app_gpu_time_microseconds` should fall stepwise from level 0 to 3; Meta's example is roughly 6.5 / 11.5 / 21% of GPU utilisation (Q3-022). Logcat `Fov=N` matches the set level; `ovrgpuprofiler -t -v` shows reduced `Fov` values on peripheral bins of the eye surface. No published dwell time; 20 s per level on a static view is a working choice, extend if `app_gpu_time_microseconds` has not settled.
- **Resolution:** `SF=` and CSV `eye_buffer_width/height` match the intended scale; GPU time falls roughly with pixel count if fill-bound [verify on device].
- **Symmetric Projection / MVRR:** A/B GPU time in a GPU-bound scene; expect within Meta's 5-15% / 3-8% ranges, or less with heavy post [verify on device].
- **Dynamic resolution:** over a 20-30 minute session (see `quest-perf:quest-levels-thermal` for the protocol), stale frames per minute should stay flat while CSV `render_scale` absorbs thermal events; check `render_scale` ≥ 85% for most of the session (VRC Perf.4). Run `ovr_metrics_csv.py` from `quest-perf:quest-profiling-toolkit` for the first-vs-last-5-minutes drift report.
- **No hitch from scale changes:** frame-time spikes should not coincide with render-scale changes during gameplay (only viewport moves there).

## Pitfalls and myths

- **"FFR on GLES."** Conflict, unresolved: Q3-039 says every current Meta/Unity FFR feature is Vulkan-only and treats GLES FFR as unsupported for new work; gles3.md documents `QCOM_texture_foveated` on the GLES swapchain, working only on direct swapchain rendering (G2-059 to G2-061), no statement either way for static FFR on GLES + OpenXR (KU-10, GLES3-GF2-006/007), and dynamic foveation documented Vulkan-only. On a GLES build: read `SystemInfo.foveatedRenderingCaps`, run the level sweep, trust only a GPU-time drop [verify on device]. Mechanics: `gles3-perf:gles-extensions-multiview`.
- **Setting URP Render Scale to 0.95 or 1.05 does nothing** (snap to 1.0, Q2-022).
- **Changing `eyeTextureResolutionScale` or the URP asset Render Scale per frame** reallocates the eye textures: a hitch every change (Q3-004, Q3-010).
- **"FFR Low is free."** It can cost more than it saves on simple shaders (Q3-023).
- **FFR level 0 is not the same as FFR off:** on 6.1/6.2 URP Vulkan a community report shows 90→40-60 fps and GPU 50%→90%+ even at level 0; test with the feature fully disabled and move to 6.3+ (Q3-036 [community]). Other regressions to recognise: black view with framebuffer fetch + FFR, UUM-132450, fixed 6000.3.14f1 / 6000.4.4f1 / 6000.5.0b5 (U1-083); FFR High + 24-bit depth submission glitches on the 6000.4 Meta fork (Q3-038 [community]); foveation off with MSAA on Vulkan, UUM-113364, fixed 6000.4.0b9, standalone Quest impact unclear (U1-084). Details: `unity-perf:unity-upgrade-risks`.
- **FFR will not fix a vertex- or draw-bound frame**; it saves fragment work only (Q3-021).
- **Dynamic resolution as optimisation:** Meta says it is not a substitute and must be off while profiling (Q3-051).
- **Custom controllers reading `GPUAppLastFrameTime`** are off by 1000x after OpenXR 1.18.0-pre.2 (seconds, not ms) (Q3-060).
- **`renderViewportScale` was broken in some Unity versions** per OVRManager's reference; confirm the applied value on device (Q3-004 notes).
- **OpenXR Automatic Dynamic Resolution lists Quest 2 and Quest 3 only**; 3S probably an omission (Q3-C7). Check `AutomaticDynamicResolutionFeature.IsAutomaticDynamicResolutionScalingSupported()` on a 3S.
- **Meta VR Glasses rules** on shared Meta pages (larger GMEM, smaller FFR savings) do not apply to Quest (Q2-008).
- **Blurry periphery blamed on resolution:** check `Fov=xD` first; dynamic foveation rises before resolution drops (Q3-031).

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/native/android/os-render-scale/ [doc]
- https://developers.meta.com/horizon/documentation/unity/os-render-scale/ [doc]
- https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ [doc]; Q3-022 figures [measured]
- https://developers.meta.com/horizon/documentation/unity/unity-fixed-foveated-rendering/ [doc]
- https://developers.meta.com/horizon/documentation/unity/os-fixed-foveated-rendering/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ [doc]
- https://developers.meta.com/horizon/resources/vrc-quest-performance-4/ [doc]
- https://developers.meta.com/horizon/documentation/native/android/os-symmetric-projection/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc]
- https://developers.meta.com/horizon/documentation/native/android/os-stereo-with-foveated-inset/ [doc]
- https://developers.meta.com/horizon/blog/vr-image-quality-meta-quest-super-resolution/ [doc]
- https://developers.meta.com/horizon/essentials/compare-devices/ [doc]
- https://developers.meta.com/horizon/essentials/battery-saver-mode/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-eye-tracked-foveated-rendering/ [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.6/changelog/CHANGELOG.html [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/changelog/CHANGELOG.html [doc]
- https://raw.githubusercontent.com/darktable-mirror/com.meta.xr.sdk.core/main/Scripts/OVRManager.cs [doc] (SDK source mirror)
- https://github.com/oculus-samples/Unity-PerformanceSettings [doc] (sample code)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRSettings-renderViewportScale.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem-scaleOfAllRenderTargets.html [doc]
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs [doc] (source code)
- https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs [doc] (source code)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/foveatedrendering.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/foveatedrendering.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/automaticdynamicresolution.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/subsampledlayout.html [doc]
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRDisplaySubsystem-foveatedRenderingLevel.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-support.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-multiview-render-regions.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc]
- https://unity.com/releases/editor/whats-new/6000.0.22f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.3.14f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.4.0b9 [doc]
- https://issuetracker.unity.com/issues/22353 [doc] (QA reproduced)
- https://issuetracker.unity.com/issues/17355 [doc] (QA reproduced)
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated.txt [doc]
- https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_FB_foveation.html [doc]
- https://discussions.unity.com/t/bug-severe-ffr-glitches-performance-loss-with-unity-6-1-6-2-with-urp-vulkan-openxr-on-quest/1677819 [community]
- https://discussions.unity.com/t/srp-foveated-rendering-on-quest-broken-with-openxr-urp-hdr/1672458 [community]
- https://developers.meta.com/horizon/feedback/vr/investigations/2302986490105678/ [community]
