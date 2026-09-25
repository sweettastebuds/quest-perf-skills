# Layer types, limits and Unity paths

Reference for `quest-perf:quest-compositor-layers`. All sources accessed
2026-09-24. Quest 2/3/3S unless stated.

## Shapes (OVROverlay.OverlayShape, Meta XR Core SDK v85)

| Shape | Use for | Limit per scene (OVROverlay) | Relative compositor cost | If layer cannot be created | Notes |
|---|---|---|---|---|---|
| Quad | UI panels, text, HUD, flat video | counts toward 15 | lowest (with projection) | falls back to scene geometry | Head-locked FIXED_TO_VIEW quads merge at no extra cost (native, Quest 2 L4) |
| Cylinder | wide curved panels, curved video | 1 | higher than quad | disappears | |
| Cubemap | skybox | 1 | not published | disappears | MQSR not supported, bilinear fallback |
| OffcenterCubemap | skybox with offset centre | not stated | not published | not stated | |
| Equirect | 360 video / panoramas | not stated | higher than quad | not stated | |
| Fisheye | fisheye video | not stated | not published | not stated | |
| ReconstructionPassthrough, SurfaceProjectedPassthrough, KeyboardHandsPassthrough, KeyboardMaskedHandsPassthrough | passthrough | not stated | see `quest-perf:quest-mr-costs` | n/a | Passthrough is rendered by a system service into a compositor layer (Q4-010) |

Sources: shape list and field names from
https://developers.meta.com/horizon/reference/unity/v85/class_o_v_r_overlay/ [doc];
limits and fallback from https://developers.meta.com/horizon/documentation/unity/unity-ovroverlay/ [doc] (Q3-080);
relative cost from https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ and
https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc] (Q1-026 / Q2-067 / Q2-070);
merge rule from https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/ [measured] (Q3-079);
MQSR support from https://developers.meta.com/horizon/blog/vr-image-quality-meta-quest-super-resolution/ [doc] (Q3-018).

## Types (OVROverlay.OverlayType)

| Type | Ordering vs eye buffer | Cost note |
|---|---|---|
| Overlay | drawn on top of the eye buffer | default choice |
| Underlay | drawn behind; eye buffer must punch an alpha hole (Underlay Transparent Occluder / Underlay Impostor shaders) | more bandwidth-heavy (Q3-081) |
| None | layer not submitted | |

Ordering between layers of the same type: `compositionDepth` (int field). No
published cost for ordering. `noDepthBufferTesting` controls depth testing
against the eye buffer ("Enable Depth Buffer Testing" in the Inspector);
no published cost figure, measure `TW=` [verify on device].

## OVROverlayCanvas DrawMode

Opaque, OpaqueWithClip, Transparent (default), AlphaToMask (Q3-081,
unity-ovroverlay [doc]). Prefer Opaque or OpaqueWithClip where the panel
design allows.

## Filtering fields (OVROverlay)

| Field | Meaning | Cost |
|---|---|---|
| `useAutomaticFiltering` | compositor picks per layer from layer PPD vs display PPD, GPU utilization, visibility | no overhead when no filter needed (Q3-016) |
| `useEfficientSupersample` / `useExpensiveSuperSample` | NORMAL (2 taps alternating per frame, approximates 4) / QUALITY (4 taps) supersampling | no published ms (Q3-020) |
| `useEfficientSharpen` / `useExpensiveSharpen` | NORMAL (3 taps approximating 5) / QUALITY (MQSR) sharpening | no published ms; MQSR cost is content-dependent and lands in TimeWarp time (Q3-017) |
| `useBicubicFiltering` | hardware bicubic, bilinear fallback | costs more, especially with trilinear (Q3-082) |

If both bits of a pair are set, the normal variant wins; all are suggestions
the compositor may ignore (Q3-015, https://developers.meta.com/horizon/documentation/native/android/mobile-openxr-composition-layer-filtering/ [doc]).
Projection-layer (eye-buffer) filtering is `OVRManager.sharpenType`, owned by
`quest-perf:quest-resolution-foveation`.

## Content fields (OVROverlay)

- `textures` (Texture[]; the Inspector exposes a Texture and a Left Texture for stereo).
- `isDynamic`: texture content updated each frame (per-frame copy).
- `isExternalSurface`, `externalSurfaceWidth`, `externalSurfaceHeight`,
  `externalSurfaceObject`: video decoder output straight to a layer surface.
- `isProtectedContent`: protected (DRM) content flag.
- `srcRectLeft/Right`, `destRectLeft/Right`, `overrideTextureRectMatrix`:
  sub-rect sampling, useful when several panels share one atlas texture.
- `hidden`: hide without destroying.

## Unity OpenXR path: XR Composition Layers

| Item | Version | Source |
|---|---|---|
| Install XR Composition Layers package; enable OpenXR feature "Composition Layer Support" | OpenXR plugin 1.18 docs | https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/compositionlayers.html [doc] |
| Custom layer types via `OpenXRCustomLayerHandler<T>` | 1.18 | same |
| Per-eye composition layers | OpenXR 1.18.0-pre.1 | https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc] |
| Dynamic Texture (needs XR Composition Layers 2.6.0); texture transfer moved to CopyTexture | OpenXR 1.19.0-pre.1 | same |
| Layer-count limit specific to the package | not documented; assume runtime 15/16 | Q3-085 notes |
| System Splash Screen shown as a compositor layer | OpenXR Meta Quest Support settings | https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html [doc] |

Filter hints on this path go through `XR_FB_composition_layer_settings`
(Q3-015). Whether the Unity package exposes every bit is not documented in
the dossier [verify on device].

## Layer limit conflict (Q3-C1)

- Native: 16 layers per frame, extras not rendered
  (os-compositor-layers [doc]).
- OVROverlay: 15 per scene, max one cylinder and one cubemap
  (unity-ovroverlay [doc]).
- Assessment: probably consistent if the projection layer takes one slot.
  Budget 15 app layers and confirm with `LCnt`, which also counts system
  layers.

## Open unknowns

- Per-layer compositor ms on Quest 3/3S (no Meta figure; the compositor-layers
  page is still dated Mar 11, 2025; MQDH layer-tools blog Jan 13, 2025 has
  none). Method: fixed levels, add 1..N quads and cylinders of known texel
  size, log `TW=` per step.
- Device PPD for Quest 3/3S: read `DevicePPD` from the CLP log
  (`adb logcat -s CompositorVR`).
- ms cost of each filter mode on any device (Q3-020).
