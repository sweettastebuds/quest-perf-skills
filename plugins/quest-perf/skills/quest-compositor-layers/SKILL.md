---
name: quest-compositor-layers
description: "Compositor layers on Quest 2/3/3S in Unity (OVROverlay, OVROverlayCanvas, OpenXR XR Composition Layers): moving UI, text, video and skyboxes out of the eye buffer for sharper text and lower app GPU cost, per-layer compositor cost, the 15/16 layer limit, overlay vs underlay, layer filtering, and when a layer costs more than it saves. Use for blurry UI text or menus, expensive world-space canvases, video playback cost, screen tears, rising TW time, or too many overlays."
---

# Quest compositor layers

Compositor layers (OVROverlay on the Meta XR Core SDK path, XR Composition
Layers on the Unity OpenXR path) are textures the compositor samples once,
instead of the app drawing them into the eye buffer and the compositor
resampling that again. They buy text clarity and take UI work off the app GPU,
but every layer adds compositor (TimeWarp) GPU time, invisible in `App=`, that
can cause tears. Goals: **Throughput** (less app GPU work, lower eye-buffer
scale for the same legibility) and **Consistency** (no tears or compositor
preemption; layer UI stays smooth when the app misses frames).

## When to use / when not

Use when:

- UI text, menus or HUD look blurry or shimmer, and raising render scale to
  fix it is too expensive.
- World-space canvases, video surfaces or skyboxes cost measurable app GPU time.
- `Tear` > 0 in logcat, `TW=` rising, or `LCnt` high; overlays "disappear"
  (layer limit hit).
- Deciding quad vs cylinder vs cubemap vs equirect, overlay vs underlay,
  static vs dynamic layer textures, or which layer filter flags to set.

Do not use for:

- Eye-buffer render scale, FFR, dynamic resolution or MQSR on the projection
  layer: `quest-perf:quest-resolution-foveation`.
- How to run OVR Metrics, logcat, Perfetto or ovrgpuprofiler in general:
  `quest-perf:quest-profiling-toolkit`.
- UI rebuild cost on the CPU (Canvas.SendWillRenderCanvases, layout):
  `unity-perf:unity-cpu-scripting`.
- HUD behaviour under Application SpaceWarp: `quest-perf:quest-appsw`
  (conflict summarised in Pitfalls below).
- The passthrough layer's cost and level caps: `quest-perf:quest-mr-costs`.
- Overlay cameras and camera stacking cost in URP:
  `unity-perf:unity-render-graph-tiling`.
- Unknown bottleneck, "low FPS" with no cause yet: `quest-perf:quest-triage`.

## Diagnose first

Layer cost shows up in compositor time and layer counts, not in app GPU time
(Q1-026 / Q2-067 / Q2-070). Confirm it there.

1. **Per-second VrApi line** (all Quest, both APIs):

   ```sh
   adb logcat -s VrApi
   ```

   Read `TW=` (compositor GPU time), `Tear=`, `LCnt=n(DRx,LMy)` (layer count
   including system layers; LM = merged layers), `App=`, `GPU%=`. Compositor-
   bound signature: `Tear` > 0, `TW` rising with layer count, high `LCnt`.
   `Tear` means the compositor took too long, usually from too many layers.

2. **OVR Metrics Tool CSV** columns for A/B runs: `timewarp_gpu_time_microseconds`,
   `total_layer_count`, `merged_layer_count`, `screen_tear_count`,
   `app_gpu_time_microseconds`, `gpu_utilization_percentage`. Record with the
   Performance HUD off; the HUD is itself a compositor layer (Q1-002).

3. **List the layers and their flags:**

   ```sh
   adb shell setprop debug.oculus.logLayers 1
   adb logcat -s CompositorClient
   ```

   Tint layers: `adb shell setprop debug.oculus.visualizeLayers 1`. MQDH
   Performance Analyzer toggles individual layer visibility for a live A/B.

4. **Size each layer objectively (CLP logs):**

   ```sh
   adb shell setprop debug.oculus.sysPropDebug 1
   # double-press the power button
   adb shell setprop debug.oculus.layerProperties 1
   adb logcat -s CompositorVR
   ```

   Per layer: DevicePPD, LayerRenderedPPD, texture resolution, recommended
   texture resolution, recommended filter (Sharpening, SuperSampling, None).

5. **Stable measurement** before any A/B: lock levels and remove foveation
   noise (Q2-039):

   ```sh
   adb shell setprop debug.oculus.cpuLevel 4
   adb shell setprop debug.oculus.gpuLevel 4
   adb shell setprop debug.oculus.foveation.level 0
   adb shell setprop debug.oculus.foveation.dynamic 0
   ```

   Reset all setprops after profiling.

6. **In-app inventory** (Meta XR Core SDK path): run the audit component in
   Fixes #1 to print every live OVROverlay with shape, type, texture size and
   filter flags.

Reading rule: if `App=` is inside budget but `TW=` + `App=` approaches the
frame budget, or `Tear` > 0, the fix is fewer, smaller or cheaper layers. If
`App=` is over budget and a world-space canvas or video surface is a large
share of it (RenderDoc Meta Fork or Frame Debugger), the fix is moving that
content onto a layer.

## Key numbers

| Number | Value | Applies to | Source / tag |
|---|---|---|---|
| Frame budget | 13.9 ms @ 72 Hz, 11.1 ms @ 90 Hz, 8.3 ms @ 120 Hz | all Quest | Q2-009, os-missed-frames [doc] |
| Cost per additional layer | ~0.1 ms | Quest 2, CPU/GPU L4 | os-compositor-layers (Q3-079) [measured] [verify on device] |
| Head-locked FIXED_TO_VIEW quad layers | merged, no extra cost | Quest 2, L4 | os-compositor-layers (Q3-079) [measured] |
| Fullscreen layer | ~0.6 ms, even fully occluded or 0 alpha | Quest 2, L4 | os-compositor-layers (Q3-079) [measured] [verify on device] |
| Per-layer cost on Quest 3/3S | **not published**; measure (method in Verify) | Quest 3/3S | Q3-079, QUEST-GF2-008 [doc] |
| Spatial SDK panel cost (order-of-magnitude prior only) | ~1% GPU per 480,000 panel pixels; ~48 M panel pixels budget at 90 FPS; headset not stated | Spatial SDK apps | spatial-sdk-runtime-guidelines (QUEST-GF2-008) [doc] [verify on device] |
| Native compositor layer limit | 16 per frame; extras dropped | all Quest | os-compositor-layers (Q3-080) [doc] |
| OVROverlay limit | 15 per scene, max 1 cylinder and 1 cubemap | Meta XR SDK | unity-ovroverlay (Q3-080) [doc] |
| XR Composition Layers package limit | not documented; assume runtime limit | Unity OpenXR | Q3-085 notes [doc] |
| Compositor time example | `TW=1.25ms` (page table says 1.27 ms) | all Quest (doc example; device not stated) | ts-logcat-stats (Q2-030) [doc] |
| Quest 2 display PPD | DevicePPD 20.67 | Quest 2 | os-compositor-layers (Q3-084) [doc]; Quest 3/3S: read from CLP log |
| FFR effect on layer cost | none | all Quest | os-fixed-foveated-rendering (Q3-024) [doc] |
| MQSR / sharpen / supersample / bicubic cost | no published ms figure | all Quest | Q3-020 [doc]; measure via `TW=` |

Limit conflict (Q3-C1): 16 (native page) vs 15 (OVROverlay page). Most
likely consistent if the eye-buffer projection layer takes one of the 16.
Budget 15 app layers, then confirm with `LCnt`; system layers (Guardian, the
OVR Metrics HUD, passthrough) also count in `LCnt`.

Relative cost (Q1-026 / Q2-067 / Q2-070 / Q2-030, [doc]): equirect and cylinder
layers cost more compositor time than quad and projection layers. Cost scales
with screen coverage, not visible content (Q3-079).

Per-shape limits, fallback behaviour and OpenXR package versions:
read [references/layer-types.md](references/layer-types.md) when choosing a
layer shape or type, or when porting layers between OVROverlay and XR
Composition Layers.

## Fixes, ranked by payoff ÷ effort

### 1. Audit, merge and cut layers to the minimum

- **Change:** combine planar UI panels into one RenderTexture on one quad
  instead of several layers (Q3-080). Remove layers that are hidden
  (`OVROverlay.hidden` or disable the component) rather than leaving them
  alive at 0 alpha. Keep `LCnt` under the 15 app-layer budget; beyond the limit
  quads fall back to scene geometry but cylinders and cubemaps simply vanish.
- **Audit component** (Meta XR Core SDK v85 API; runtime or dev build;
  untested in Unity here):

  ```csharp
  // Requires Meta XR Core SDK (OVROverlay). Attach to any GameObject in a dev build.
  using System.Text;
  using UnityEngine;

  public sealed class OverlayLayerAudit : MonoBehaviour
  {
      [SerializeField] float intervalSeconds = 5f;
      const int AppLayerBudget = 15; // OVROverlay page; native limit is 16 incl. projection layer
      float _next;

      void Update()
      {
          if (Time.unscaledTime < _next) return;
          _next = Time.unscaledTime + intervalSeconds;

          var sb = new StringBuilder();
          int active = 0, cylinders = 0, cubemaps = 0;
          foreach (var o in OVROverlay.instances)
          {
              if (o == null || !o.isActiveAndEnabled || o.hidden) continue;
              active++;
              if (o.currentOverlayShape == OVROverlay.OverlayShape.Cylinder) cylinders++;
              if (o.currentOverlayShape == OVROverlay.OverlayShape.Cubemap) cubemaps++;
              Texture t = (o.textures != null && o.textures.Length > 0) ? o.textures[0] : null;
              sb.AppendFormat("  {0}: {1}/{2} tex={3} dyn={4} bicubic={5} ssE={6} ssX={7} shE={8} shX={9} auto={10}\n",
                  o.name, o.currentOverlayType, o.currentOverlayShape,
                  t != null ? t.width + "x" + t.height : (o.isExternalSurface ? "external" : "none"),
                  o.isDynamic, o.useBicubicFiltering,
                  o.useEfficientSupersample, o.useExpensiveSuperSample,
                  o.useEfficientSharpen, o.useExpensiveSharpen, o.useAutomaticFiltering);
          }
          string warn = (active > AppLayerBudget ? " OVER BUDGET" : "")
                      + (cylinders > 1 ? " >1 CYLINDER" : "")
                      + (cubemaps > 1 ? " >1 CUBEMAP" : "");
          Debug.Log($"[OverlayLayerAudit] active={active}/{AppLayerBudget}{warn}\n{sb}");
      }
  }
  ```

- **Effect:** removes ~0.1 ms compositor time per layer removed on Quest 2 at
  L4 (Q3-079); on Quest 3/3S no published number. Mostly a variance fix: fewer
  tears and less compositor preemption of app GPU work (Q2-040).
- **Cost:** one merged texture means one filter setting and one update rate
  for everything in it.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `Vulkan` ; Meta XR Core SDK ;
  **Consistency**, Throughput (compositor share of GPU).

### 2. Crop every layer to its content; never ship a fullscreen transparent layer

- **Change:** size the quad (transform scale) and texture to the content
  bounds. A fullscreen layer costs ~0.6 ms on Quest 2 at L4 even when fully
  occluded or at 0 alpha (Q3-079), so a mostly transparent fullscreen HUD is a
  bad trade: split it into small quads, or put it back in the eye buffer.
  Fade-to-black and loading screens are fine as fullscreen layers only while
  they are shown; destroy or disable them afterwards.
- **Effect:** up to ~0.5 ms compositor time back per fullscreen layer
  replaced (0.6 vs 0.1 ms, Quest 2, L4); Quest 3/3S unmeasured
  [verify on device].
- **Cost:** none visually; more transforms to manage.
- **Tags:** `Quest 2` `Quest 3/3S` ; **Consistency**, Throughput.

### 3. Move text and UI out of the eye buffer onto a quad overlay

- **Change (Meta XR SDK):** add `OVROverlayCanvas` to the world-space canvas.
  Set DrawMode to **Opaque** or **OpaqueWithClip** where the design allows;
  the default is Transparent (Q3-081). Shape Quad, type Overlay.
- **Change (Unity OpenXR, Unity 6.x):** install the XR Composition Layers
  package, enable Project Settings > XR Plug-in Management > OpenXR >
  **Composition Layer Support**, then use a quad composition layer for the
  panel (Q3-085).
- **Effect:** layer texels are sampled once by the compositor, so text stays
  sharp at a lower eye-buffer render scale (Q3-078). App GPU loses the canvas
  draw and blending; compositor gains ~0.1 ms per layer (Quest 2, L4). The net
  app saving is not published; measure `App=` and `TW=` before and after.
  Layer UI is displayed at compositor rate, so it stays smooth when the app
  drops frames (Consistency). FFR does not degrade layer text (Q3-024).
- **Cost:** no custom pixel shaders or lighting on layer content (Q3-078);
  depth interaction with the scene is limited (see references). Whether it
  lets you lower render scale is a quality call owned by
  `quest-perf:quest-resolution-foveation`.
- **When it costs more than it saves:** small, simple, opaque UI that is cheap
  in the eye buffer, or UI that would need its own fullscreen layer. A/B it.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `Vulkan` ; OVROverlayCanvas
  (Meta XR SDK) or `Unity ≥ 6000.0` + OpenXR with XR Composition Layers ;
  **Throughput**, Consistency.

### 4. Prefer overlays to underlays; prefer opaque canvases

- **Change:** `currentOverlayType = OVROverlay.OverlayType.Overlay`. Use
  Underlay only when scene geometry must occlude the layer.
- **Effect:** underlays make the eye buffer punch an alpha hole
  (Underlay Transparent Occluder / Underlay Impostor shaders), which is more
  bandwidth-heavy (Q3-081). No published ms number.
- **Cost:** without Enable Depth Buffer Testing (`noDepthBufferTesting = false`)
  an overlay renders on top of everything, so hands or controllers in front
  of a panel are hidden; depth testing has no published cost, A/B `TW=`
  [verify on device].
- **Tags:** `Quest 2` `Quest 3/3S` ; Meta XR SDK ; **Throughput**.

### 5. Size layer textures from the CLP log and let the compositor pick filters

- **Change:** set texture resolution to the CLP "recommended texture
  resolution" (Diagnose step 4) instead of guessing. Leave per-layer filtering
  on **Auto Filtering** (`useAutomaticFiltering = true`); it is a no-op with no
  overhead when no filter is needed (Q3-016). Force `useExpensiveSuperSample`,
  `useExpensiveSharpen` or `useBicubicFiltering` only after a `TW=` A/B.
  Bicubic costs more, especially combined with trilinear (Q3-082).
  Supersample layers whose texture PPD is above display PPD (minification
  shimmer); sharpen layers at or below display PPD (Q3-015).
- **Effect:** smaller textures cut memory and bandwidth for the layer; filter
  choice moves `TW=`. No published ms per filter (Q3-020).
- **Cost:** undersized textures blur; expensive filters raise compositor
  time. MQSR does not support YUV or cubemap layers, which fall back to
  bilinear (Q3-018).
- **Tags:** `Quest 2` `Quest 3/3S` ; Meta XR Core SDK v85 (OVROverlay filter
  dropdowns, Q3-019); OpenXR `XR_FB_composition_layer_settings` ;
  **Throughput**, Consistency.

### 6. Update layer textures only when content changes

- **Change (OVROverlay):** keep `isDynamic = false` for static panels; enable
  it only for content that changes every frame. For panels that change
  occasionally, enable `isDynamic` for the frames that change, then disable it
  [verify on device]: the SDK's handling of a one-frame toggle is not
  documented in the dossier.
- **Change (OpenXR):** OpenXR 1.19.0-pre.1 Dynamic Texture (needs XR
  Composition Layers 2.6.0) transfers layer textures with CopyTexture each
  update, a per-frame GPU copy; keep dynamic layers small (Q3-085).
- **Effect:** removes a per-frame copy of the layer texture from app GPU time.
  No published number; measure `App=`.
- **Tags:** `Quest 2` `Quest 3/3S` ; OVROverlay; `Unity ≥ 6000.0`
  `OpenXR ≥ 1.19.0-pre.1` ; **Throughput**.

### 7. Choose the cheapest shape that works

- **Change:** quad first. Cylinder only for wide curved panels (max one per
  scene on OVROverlay); cubemap for skyboxes (max one). Equirect and cylinder
  layers cost more compositor time than quads (Q1-026 / Q2-067 / Q2-070).
  Head-locked quad layers are merged at no extra cost (Q3-079, native
  FIXED_TO_VIEW); whether a Unity OVROverlay parented to the camera rig maps
  to that flag is not documented [verify on device] with `LCnt(LM)` rising.
- **Effect:** lower `TW=`; no published per-shape ms.
- **Tags:** `Quest 2` `Quest 3/3S` ; **Consistency**, Throughput.

### 8. Video on a layer

- **Change:** play video into an OVROverlay with `isExternalSurface = true`
  and `externalSurfaceWidth` / `externalSurfaceHeight` set to the video size
  (OVROverlay v85 API; the SDK hands back `externalSurfaceObject` for the
  decoder to render into). Use a quad (or one cylinder).
- **Effect:** removes the video surface draw from the eye buffer and samples
  video once (Q3-078). Whether the external-surface path also avoids an
  app-side copy is not documented in the dossier; no published number for
  either path. A/B `App=` and `TW=`.
- **Cost:** YUV layers get no MQSR, bilinear fallback (Q3-018). Same depth
  and ordering limits as other layers.
- **Tags:** `Quest 2` `Quest 3/3S` ; Meta XR SDK ; **Throughput**
  [verify on device].

### 9. System splash as a compositor layer

- **Change:** Project Settings > XR Plug-in Management > OpenXR > Meta Quest
  Support (feature settings) > System Splash Screen. It is shown as a
  compositor layer (Q3-091). Use it rather than an in-app loading scene.
- **Effect:** no change to average frame time; removes startup judder
  (variance): the splash stays smooth while the first scene loads.
- **Cost:** static splash image only; one compositor layer while shown.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `Vulkan` ; Unity OpenXR ;
  **Consistency**.

## Verify

Protocol: locked levels (Diagnose step 5), static camera, Guardian off, HUD
off, same scene, 60 s per variant, each twice; then a 20-30 min soak at
normal (unlocked) levels for tears and thermal behaviour.

| Change | Metric that should move | Expected size |
|---|---|---|
| Layers removed or merged | `TW=` / `timewarp_gpu_time_microseconds` down; `LCnt` down or `LM` up | ~0.1 ms per layer on Quest 2 L4; unknown on Quest 3/3S |
| Fullscreen layer replaced | `TW=` down | up to ~0.5 ms on Quest 2 L4 |
| UI moved to a layer | `App=` / `app_gpu_time_microseconds` down, `TW=` up | net not published; keep only if `App` + `TW` falls or render scale can drop |
| Filter or texture size changes | `TW=` | no published number |
| Any of the above | `Tear` / `screen_tear_count` to 0; `Stale2/5/10` unchanged or down | 0 tears across the 20-30 min soak |

Quest 3/3S per-layer cost (open unknown): at fixed levels, add 1..N quad and
cylinder layers of known texel size and log `TW=` per step; read compositor
GPU time from `ovrgpuprofiler` or the Perfetto compositor track, and the
headroom change from `GPU%` / `gpu_utilization_percentage`
(`quest-perf:quest-profiling-toolkit`). Record per device; compositor cost scales with panel resolution (Q3-020 notes).

Headroom rule: keep `App` at or below the frame budget minus `TW` at the
shipping layer count, with margin for the next thermal step (Q2-030).

## Pitfalls and myths

- **"Layers are free."** Each costs compositor GPU time, invisible in `App=`
  and in the Unity Profiler; a fullscreen layer costs ~0.6 ms on Quest 2 even
  when invisible (Q3-079).
- **"A transparent or hidden fullscreen layer costs nothing."** Cost scales
  with coverage, not visible content (Q3-079). Disable it.
- **"FFR will cut layer cost."** FFR does not affect compositor layers
  (Q3-024).
- **"The 0.1 ms / 0.6 ms numbers hold on Quest 3."** They are Quest 2 at L4.
  No Quest 3/3S figure exists; the Spatial SDK 1%-per-480k-pixels figure is
  from a different SDK with an unstated headset and unclear whether it means
  app or compositor GPU (QUEST-GF2-008).
- **Exceeding the limit silently.** Beyond 16 layers the compositor drops
  extras; OVROverlay quads fall back to scene geometry, cylinders and cubemaps
  disappear (Q3-080). `LCnt` includes system layers.
- **Forcing "quality" filters everywhere.** Auto filtering is the safer
  default (Q3-016); forced bicubic plus trilinear is the costly combination
  (Q3-082).
- **Layers under AppSW (conflict Q3-C9).** Unity's SpaceWarp page lists
  composition layers as not warped; Meta's native AppSW page says Compositor
  Layer SpaceWarp smooths layer motion and recommends layers for HUD UI.
  Probably both true: no app motion vectors for layer content, but the
  compositor reprojects layer poses [verify on device] with the MV overlay and
  a moving world-locked quad. AppSW itself runs on the projection layer only
  (Q3-076). Details: `quest-perf:quest-appsw`.
- **Overlay cameras for UI.** In URP a base camera whose stack does not
  resolve the final target forces an intermediate (U2-039); put UI in the base
  camera or on a compositor layer instead. `URP 14+`. Owner:
  `unity-perf:unity-render-graph-tiling`.
- **Measuring with the OVR Metrics HUD on.** The HUD is its own compositor
  layer (Q1-002); capture CSV with it off.

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/ [doc]; Quest 2 L4 layer costs in it are [measured] (Q3-078 to Q3-084)
- https://developers.meta.com/horizon/documentation/unity/unity-ovroverlay/ [doc] (Q3-080, Q3-081, Q3-082, Q3-019)
- https://developers.meta.com/horizon/reference/unity/v85/class_o_v_r_overlay/ [doc] (OVROverlay field names used in code; targeted check)
- https://developers.meta.com/horizon/reference/unity/v85/class_o_v_r_manager/ [doc] (Q3-019)
- https://developers.meta.com/horizon/documentation/native/android/mobile-openxr-composition-layer-filtering/ [doc] (Q3-015, Q3-016)
- https://developers.meta.com/horizon/blog/vr-image-quality-meta-quest-super-resolution/ [doc] (Q3-017, Q3-018, Q3-020)
- https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ [doc] (Q3-024)
- https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ [doc] (Q1-026, CSV columns)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc] (Q2-030, Q2-067, Q2-070)
- https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ [doc] (Q2-009)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc] (Q1-002)
- https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ [doc] (Q2-039)
- https://developers.meta.com/horizon/blog/how-to-obtain-stable-gpu-measurements-on-quest/ [doc] (Q2-040)
- https://developers.meta.com/horizon/documentation/spatial-sdk/spatial-sdk-runtime-guidelines/ [doc] (QUEST-GF2-008)
- https://developers.meta.com/horizon/blog/mqdh-compositor-layers-visibility-properties-functions-enhance-visual-quality-performance/ [doc] (MQDH layer tools)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/compositionlayers.html [doc] (Q3-085)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc] (Q3-085)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html [doc] (Q3-091)
- https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html [doc] (Q3-086, Q3-C9)
- https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ [doc] (Q3-076, Q3-086, Q3-C9)
- https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html [doc] (U2-039)
