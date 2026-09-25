# Foveation levels, paths and version gates

Per level, device, API and Unity stack. All sources accessed 2026-09-24. Finding IDs refer to `research/quest.md`, `research/unity.md`, `research/gles3.md`, `research/arm-mobile-hw.md`. URLs and evidence tags: see SKILL.md Sources.

## Level mapping per control

| Control | Off | Low | Medium | High | High Top | Source |
|---|---|---|---|---|---|---|
| `adb shell setprop debug.oculus.foveation.level N` | 0 | 1 | 2 | 3 | 4 | Q1-081 / Q3-028 [doc] |
| `XRDisplaySubsystem.foveatedRenderingLevel` (SRP API, Unity 6.x OpenXR) | 0 (default) | - | 0.5 = Medium on Meta | 1 = platform max | - | Q3-026 [doc] |
| Same property, Oculus XR plugin mapping | 0 | < 0.33 | < 0.66 | ≥ 0.66 | - | Q4-056 [doc] |
| `OVRManager.foveatedRenderingLevel` (Meta XR SDK) | Off | Low | Medium | High | HighTop (= High on OpenXR backend) | Q3-027 [doc] |
| Native `XrFoveationLevelProfileCreateInfoFB` | NONE | LOW | MEDIUM | HIGH | High + `verticalOffset` | Q3-032, Q3-027 [doc] |
| Logcat readback | `Fov=0` | `Fov=1` | `Fov=2` | `Fov=3` | `Fov=4` | `D` suffix = dynamic (Q1-081) |

- Set `debug.oculus.foveation.dynamic 0` before overriding the level, or dynamic foveation overrides it (Q1-081).
- Under old VrApi, levels 3 and 4 behave the same when dynamic (Q3-029).
- Older Meta SDK members `fixedFoveatedRenderingLevel` / `useDynamicFixedFoveatedRendering` are documented as Qualcomm-only (Q3-027).
- Battery Saver forces level 3 (Q2-062).

## Savings per level

| Level | Meta example GPU-utilisation gain | Notes |
|---|---|---|
| Low | 6.5% | Can be a net loss on simple shaders (Q3-023) |
| Medium | 11.5% | |
| High | 21% | Headline "up to 25%" in pixel-intensive apps |

Source: Q3-022, https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ [measured]. One unnamed workload with 16% of GPU utilisation in TimeWarp; device not stated. **No per-device (Quest 2 / 3 / 3S) or per-URP figures exist.** Quest 3S has 96° vs 110° horizontal FOV and 20 vs 25 PPD, so peripheral savings differ from Quest 3 (Q2-091). Measure: dynamic foveation and dynamic resolution off, GPU level fixed, sweep `debug.oculus.foveation.level` 0-3, log `app_gpu_time_microseconds`, on each target headset.

## Paths per Unity version and stack

| Stack | Setting path | Unity | Foveates intermediates? | Source |
|---|---|---|---|---|
| Unity OpenXR, SRP Foveation API | OpenXR > All Features > Foveated Rendering > gear > Method = Foveated rendering (SRP API); runtime `foveatedRenderingLevel` | 6.0+ with OpenXR 1.11.0+ and URP; default method from OpenXR 1.17.0 | Yes, per pass that calls `EnableFoveatedRasterization` | Q3-025, Q3-026, Q4-058 [doc] |
| Unity OpenXR, Meta/Legacy API | Method = Legacy, Foveated Rendering off, "Meta XR Foveation" on; Meta Core SDK 68.0+ | 2022.3 (only path on 2022), 6.x, BiRP | No (post, tonemapping, camera stacking escape) | Q3-025, GLES3-GF2-006 [doc] |
| Oculus XR plugin (deprecated from 6.5) | Project Settings > XR Plug-in Management > Oculus > Foveated Rendering Method | 2021.3-6.4 | Legacy FFR breaks with URP's default final blit | Q4-056, G2-062 [doc] |
| Meta XR SDK | `OVRManager.foveatedRenderingLevel`, `useDynamicFoveatedRendering` | 2021.3-6.x | Same as underlying provider | Q3-027 [doc] |

Conflict Q3-C4: Unity's 6.3 support reference lists 2022.3+ and URP for foveated rendering, while the OpenXR docs say the SRP API is Unity 6+ only. Resolution in the dossier: 2022.3 gets FFR only through Meta/Legacy or Oculus XR, neither of which foveates intermediates.

## URP foveation integration history

| Version | Change | Source |
|---|---|---|
| URP 14 (2022.3.16f1) / 6000.0.0b11 | Foveation in Forward+ | U1-082 [doc] |
| URP 14/15 | Foveated rendering integrated | Q3-035 [doc] |
| 6000.0.0b15 | Render Graph support | U1-082 [doc] |
| 6000.0.22f1 | UberPost and FinalPostBlit foveated (when last pass) | U1-082, Q3-035 [doc] |
| URP 17 | Foveation disabled on intermediate passes when `renderViewportScale` is active under Render Graph | Q3-035 [doc] |
| OpenXR 1.17.0-pre.2 | Checks `VK_EXT_fragment_density_map` before using FDM | Q3-033 [doc] |
| OpenXR 1.17.0-pre.1 | `XR_META_tile_properties_hint` enabled automatically (tile-aligned sizes/FDMs) | Q3-089 [doc] |
| OpenXR 1.18.0-pre.1 | FDM attachments off at level 0 (SRP path); Quad Views option documented | Q3-035, QUEST-GF1-C4 [doc] |
| OpenXR 1.18.0 / 1.19 | Dynamic foveation (Vulkan) toggle; conflict Q3-C2 on which version | Q3-030, Q3-C2 [doc] |

Technique order in Unity OpenXR: gaze FDM, fixed FDM, FSR from provider texture, FSR from compute (Q3-033). Quest reports `SystemInfo.foveatedRenderingCaps = FoveationImage` (linear raster; no HLSL remap needed) (Q3-034).

Render Graph rule: URP's DrawObjects, Skybox and Occlusion Mesh passes call `builder.EnableFoveatedRasterization(...)`; passes with differing foveation state cannot merge (`FRStateMismatch`) (U2-054). URP pattern (6000.3 `DrawObjectsPass.cs`): `passSupportsFoveation = cameraData.xrUniversal.canFoveateIntermediatePasses || resourceData.isActiveTargetBackBuffer`.

## Feature availability per graphics API

| Feature | Vulkan | GLES | Source |
|---|---|---|---|
| Static FFR, Meta SDK / OVRManager | Yes | Doc states no API restriction; applies only to direct swapchain rendering | G1-044, G2-061 [doc] |
| Static FFR, Unity OpenXR (SRP or Legacy) | Yes | Undocumented; OpenXR plugin lists Quest as Vulkan-only | GLES3-GF2-006, GX-C8, KU-10 |
| Dynamic foveation, Unity OpenXR | Yes (needs `XR_FB_foveation_vulkan`) | No (documented Vulkan-only) | Q3-030, GLES3-GF2-006 [doc] |
| Subsampled layout | Yes (FDM2) | GL extension exposed, but Unity cannot enable it without native code | Q3-041, G1-035 [doc] |
| Symmetric Projection | Yes (+ Multiview) | No | G1-037 [doc] |
| MVRR | Yes (Unity 6.1+) | No GL equivalent exposed | G1-039 [doc] |
| Dynamic resolution | Yes | Not stated (KU-09) | G1-045 [doc] |

**Conflict (OUTLINE decision 38):** quest.md Q3-039 says every current Meta/Unity FFR feature is Vulkan-only and no current page documents a GLES FFR path for URP, so GLES FFR is unsupported for new work. gles3.md documents `QCOM_texture_foveated` per-texture foveation on Quest GLES, applied by the runtime to the swapchain texture (G2-059, G2-060, G2-061), and at spec level `XR_FB_foveation` is API-agnostic (GLES3-GF2-007). Neither side is settled: test on device with the level sweep and `ovrgpuprofiler -t -v` `Fov` fields (G2-064). GLES mechanics are owned by `gles3-perf:gles-extensions-multiview`.

## Subsampled layout constraints

- Mip count 1; samplers immutable, `VK_SAMPLER_CREATE_SUBSAMPLED_BIT_EXT`, `VK_FILTER_LINEAR`, `MIPMAP_MODE_NEAREST`, LOD clamp [0,0]; flag silently ignored if unsupported (Q3-043).
- Oculus XR: raises Timewarp cost; use only at FFR ≥ 2 (Q4-056).
- MQSR supports subsampled textures from runtime v56 (Q3-018).
- Unity issue 17355: right-eye corner artifacts in MR on Quest 3 only (2022.3.33f1, Oculus XR 4.2.0), no fix listed (Q3-046).

## Regressions to recognise

| Symptom | Versions | Status | Source |
|---|---|---|---|
| FFR glitches, 90→40-60 fps, GPU 50%→90%+ even at level 0 | 6000.1.15f1, 6000.2, URP 17.0.3-17.2.0, OpenXR 1.15.1, Vulkan, confirmed Quest 2 | Fix reported in 6000.3.0f1 (community) | Q3-036 [community] |
| SRP foveation + URP HDR: top half low-res | 6.0 URP OpenXR | Workaround: Legacy API or HDR off | Q3-037 [community] |
| FFR High + 24-bit depth submission: glitched squares | 6000.4.8f1, Meta 6000.4 AppSW URP fork | Investigating | Q3-038 [community] |
| Black view: framebuffer fetch + foveation (UUM-132450) | 6.3 < .14f1, 6.4 < .4f1 | Fixed 6000.3.14f1, 6000.4.4f1, 6000.5.0b5; no 6.0 entry | U1-083 / U2-055 [doc] |
| Foveation off with MSAA on Vulkan (UUM-113364) | 6.3 and earlier if affected | Fixed 6000.4.0b9, 6000.5.0a7; note says "PC or linked XR" [verify on device] | U1-084 [doc] |
| RenderObjects split into separate Vulkan render passes with foveation | 6.x URP | Fixed 6000.0.81f1, 6000.3.21f1, 6000.5.6f1, 6000.6.0b5 | Q3-054 [doc] |

Patch-floor decisions belong to `unity-perf:unity-upgrade-risks`.

## Eye-tracked foveation (one line)

ETFR is Quest Pro only (Vulkan, Multiview, ARM64); it does nothing on Quest 2/3/3S (Q2-007 / Q3-040).
