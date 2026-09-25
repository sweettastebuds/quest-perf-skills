# Render scale and dynamic resolution in Unity URP on Quest

All sources accessed 2026-09-24. Finding IDs refer to `research/quest.md` unless noted. URLs and evidence tags: see SKILL.md Sources.

## The knobs

| Knob | Reallocates? | When it applies | Notes | Source |
|---|---|---|---|---|
| URP asset / camera Render Scale | Yes | Written into `XRDisplaySubsystem.scaleOfAllRenderTargets` at pipeline init and per camera | ±0.05 around 1.0 snaps to 1.0; range 0.1-2.0; URP 12/14/17 | Q2-022 / Q3-006 [doc, source] |
| `XRSettings.eyeTextureResolutionScale` | Always | Next allocation | Unity calls it unsupported in URP; Meta still uses it | Q3-004, Q3-010, Q3-011 |
| `XRDisplaySubsystem.scaleOfAllRenderTargets` | Always | - | QX-C1 resolved: not a per-frame knob | Q3-005 [doc] |
| `XRSettings.renderViewportScale` (0-1) | No | Next frame; not while cameras render | Not with deferred; runtime treats it as a hint | Q3-004 [doc] |
| `XRDisplaySubsystem.scaleOfAllViewports` (0-1) | No | Next scene render (after LateUpdate) | Read `appliedViewportScale`; providers may clamp | Q3-005 [doc] |

Conflict Q3-C5 (which knob in URP): Meta says `eyeTextureResolutionScale` plus possibly URP `renderScale`; Unity says `renderViewportScale`, with asset Render Scale as the expensive alternative; URP source shows the asset value is what lands. Working rule: set allocation via URP `renderScale` and `eyeTextureResolutionScale` to the same value only at loads; use `renderViewportScale` per frame. [verify on device] by logging the eye texture size and `SF=`.

URP 17.3 (Unity 6.3+): with an IUpscaler active, the XR render scale passed to `XRSystem.SetRenderScale` is forced to 1.0; the upscaler owns the pre-upscale resolution (Q3-007) [verify on device].

Direct vs intermediate: with no post-processing URP renders into the eye texture and `renderViewportScale` applies directly (compatible with FFR). With post intermediates, enable camera *URP Dynamic Resolution*; URP scales intermediates via ScalableBufferManager, and this path cannot be combined with FFR or TAA (Q3-008, Q3-009, Q3-C8). `renderViewportScale` on intermediates: "Improved" in URP 14.0.9, "Enabled" in URP 17 (Q3-014).

## Per-device allocation arithmetic

| Device | Scale 1.0 | Panel | Panel-match scale | OVRManager default range | Allocation at default max |
|---|---|---|---|---|---|
| Quest 2 | 1440x1584 | 1832x1920 | about 1.24 | 0.7-1.3 | 1872x2059 (arithmetic) |
| Quest 3 | 1680x1760 | 2064x2208 | not published (about 1.23 x 1.25 arithmetic) | 0.7-1.6 | 2688x2816 |
| Quest 3S | 1680x1760 | 1832x1920 | about 1.09 | 0.7-1.6 (quest3 fields) | 2688x2816 |

Sources: Q2-017 / Q3-001, Q2-018, Q2-024 / Q2-090 (SDK 207 source mirror; confirm against your installed package). Quest 2 allocation at 1.3 is arithmetic from the table, not a published figure.

## Horizon OS dynamic resolution (Meta XR SDK)

- Scales the viewport from GPU utilisation: lowers resolution when frames start going stale, raises it with headroom; textures allocated once at max (Q3-048).
- Setup: OVRCameraRig > OVR Manager > Enable Dynamic Resolution; `quest2Min/MaxDynamicResolutionScale`, `quest3Min/MaxDynamicResolutionScale`; runtime `OVRManager.instance.enableDynamicResolution` (Q3-050). Off by default (Q4-006).
- When enabled, OVRManager sets `eyeTextureResolutionScale` and URP `renderScale` to the max (Q2-024).
- Minimum versions, from the version checks in the Meta XR SDK's `OVRManager.cs` (the dynamic-resolution page itself lists only 6000.0.25f1, as a distortion-bug fix): OpenXR loader, Unity 2021.3.45f1, 2022.3.49f1 or 6000.0.25f1; Oculus loader on Vulkan, Oculus XR 3.3.0+ (or OpenXR 1.12.1+). Meta recommends URP 14.0.9+ (Q2-025, G1-045).
- Prerequisite for GPU level 5; during thermal events the OS lowers render scale instead of dropping frames (Q3-049, Q2-050). Level rules: `quest-perf:quest-levels-thermal`.
- With dynamic foveation also on, foveation rises first, resolution drops after (Q3-031).
- No published thresholds, step size or hysteresis (Q3-061). Measure: log `SF`, GPU% and `Stale` at 1 Hz while ramping GPU load; record the GPU% at which SF falls and recovery speed.
- GLES support: not stated either way (KU-09, G1-045). Test: enable on a GLES build, log `renderViewportScale` and eye-texture size, check available GPU levels.
- Store: a min below 0.85 makes you responsible for VRC Perf.4's 85% expectation (Q3-003).

## Unity OpenXR Automatic Viewport Dynamic Resolution

- Unity 6.3+, OpenXR 1.16.0+, URP 17.0.3+, Vulkan, a provider (Unity OpenXR Meta or Android XR); uses `XR_META_recommended_layer_resolution` (Q3-059).
- Min Resolution Scalar (effective floor currently 0.5), Max Resolution Scalar; camera *URP Dynamic Resolution* on; not in URP Compatibility Mode.
- API: `AutomaticDynamicResolutionFeature.IsAutomaticDynamicResolutionScalingSupported()`, `SetUsingSuggestedResolutionScale(bool)`.
- With MVRR, use Final Pass mode (Q3-088).
- Device list names Quest 2 and Quest 3 only; 3S probably an omission (Q3-C7) [verify on device].

## Known URP issues under dynamic resolution

| Issue | Affected | Fixed in | Workaround | Source |
|---|---|---|---|---|
| Additional lights misaligned (Forward+ blocky tiles; Deferred/Deferred+ drift) | URP with Meta DR | - | Tick Dynamic Resolution on CenterEyeAnchor camera or set `camera.allowDynamicResolution`; use `_ScaledScreenParams` in HLSL | Q3-053 |
| RenderObjects wrong viewport; with foveation, each RenderObjects pass split into its own Vulkan render pass | 6.x URP | 6000.0.81f1, 6000.3.21f1, 6000.5.6f1, 6000.6.0b5, 6000.7.0a3 (alpha) | Count render passes in RenderDoc / Render Graph Viewer | Q3-054 |
| Temporary RTs reallocated on every scale change (OOM risk) | 2022.3 < 15f1, early 6000.0 | 6000.0.1f1, 2022.3.15f1 (URP 14.0.9) | `ScalableBufferManager.ResizeBuffers(scale, scale)` | Q3-055 |
| Extra intermediate pass whenever scale ≠ 1.0 | 2021.3 < 36f1, 2022.3 < 22f1 | 6000.0.1f1, 2022.3.22f1, 2021.3.36f1 | Upgrade; otherwise DR can cost more than it saves | Q3-056 |
| Screen distortion | 6000.0.22f1-24f1 | 6000.0.25f1 | - | Q3-057 |
| Wrong copy-depth scaling | URP 14 < 14.0.11 | URP 14.0.11 | Latest 2022.3 patch | Q3-058 |
| Hardware DR settings enforcement | URP 14 < 14.0.10 | URP 14.0.10 | - | Q3-058 |
| Redundant blit when camera post ticked but renderer post off (issue 22353) | 2020.3-2023.2 | Fix note for 2023.2; none listed for 2021.3/2022.3 | Untick camera post | Q3-013 |

## Custom controllers

- Meta's Unity-PerformanceSettings sample (Unity 6000.3.15f1+): effective scale = `renderViewportScale × eyeTextureResolutionScale`; raise allocation only when needed, then `renderViewportScale = target / eyeTextureResolutionScale`; turning DR off resets viewport scale to 1.0 (Q3-012).
- OpenXR 1.18.0-pre.2 changed `GPUAppLastFrameTime` / `GPUCompositorLastFrameTime` from milliseconds to seconds; a home-made controller is off by 1000x after the upgrade (Q3-060). Timing-read details: `unity-perf:unity-profiling-workflow`.
- Quantise manual sizes to tile-friendly multiples of 16 (Meta's symmetric-projection sample); no published cost for non-aligned sizes (Q3-089).
