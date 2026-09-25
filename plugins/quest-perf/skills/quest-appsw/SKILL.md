---
name: quest-appsw
description: "Application SpaceWarp (AppSW) on Quest 2/3/3S with Unity URP: render at half rate and let the runtime synthesize frames from motion vectors and depth, for up to about 70% GPU headroom. Covers both setup paths (Meta URP fork from 2022.3.15f1 / 6000.0.9f1, Unity-native from 6.1 / URP 17.0.3+), Vulkan and Optimize Buffer Discards requirements, motion-vector passes and format, shader and UI support, artifacts, and runtime toggling. Use for \"SpaceWarp\", \"half frame rate\", warping artifacts, or when resolution and foveation cuts are not enough to hold 72/90 Hz."
---

# Application SpaceWarp (AppSW) on Quest

Goal: **Throughput** (primary: half-rate rendering frees GPU and CPU time) and **Consistency** (headroom that absorbs spikes and thermal decay). AppSW is Vulkan-only. There is no GLES path.

## When to use / when not

Use when:
- The app is GPU-bound at 72/90 Hz after the cheap resolution and foveation cuts, and the content is slow-moving: exploration, sims, social, or a GPU-heavy hero scene.
- You are setting up AppSW on either path (Meta URP fork or Unity-native OpenXR SpaceWarp), or auditing custom shaders and UI for motion vectors.
- You see warping artifacts: smearing on moving objects, UI swimming, halos on transparents, or a silent drop back to full rate after a scene load.

Do not use; go to the sibling instead:
- Render scale, FFR, dynamic resolution or the subsampled layout alone: `quest-perf:quest-resolution-foveation`.
- Stale frames, FrameSync, Late Latching or refresh-rate choice: `quest-perf:quest-frame-pacing`.
- You have not yet shown that the app is GPU-bound: `quest-perf:quest-triage`.
- Still on GLES and deciding whether to move to Vulkan: `gles3-perf:gles-vs-vulkan`. AppSW is one of the Vulkan-only features that go into that decision.
- Which Unity/URP patch to target: `unity-perf:unity-version-matrix`. The fixes on the MSAA + post + SpaceWarp depth path are covered in `unity-perf:unity-upgrade-risks`.
- Main-pass shader ALU/bandwidth cost: `unity-perf:unity-shader-authoring`.
- HUD on compositor layers instead of the eye buffer: `quest-perf:quest-compositor-layers`.

## Diagnose first

1. **Confirm the app is GPU-bound before reaching for AppSW.** In OVR Metrics Tool, App GPU time should sit near the frame budget while CPU time has slack. Use `adb logcat -s VrApi,XrPerformanceManager` and read the per-second line (Q1-027). The full split is in `quest-perf:quest-triage`.
2. **Lock the levels for every A/B.** Use `adb shell setprop debug.oculus.cpuLevel <n>` and `debug.oculus.gpuLevel <n>` (Q1-079). Otherwise the governor hides the saving. `quest-perf:quest-profiling-toolkit` has a wrapper: `quest_adb.py pin-levels`.
3. **Confirm that AppSW is actually active** (Q2-079, Q1-034, Q3-074):
   - `adb logcat -s VrApi`: the line reads `FPS=36/72` and includes `ASW=72, Type=App`, with `VSnc=0`. At 90 Hz expect `FPS=45/90`, `ASW=90`.
   - OVR Metrics Tool: enable the FPS, ASW FPS and ASW TYPE stats.
   - Per-layer flags: run `adb shell setprop debug.oculus.logLayers 1`, then `adb logcat -s CompositorClient`. The projection layer should carry `APP_SPACE_WARP` (Q3-083).
   - After every scene or rig change, check `ASW=` again. A silent return to full rate means SpaceWarp was not re-armed (Q3-075).
4. **Look at the motion vectors themselves** (Q3-074):
   ```sh
   adb shell setprop debug.oculus.spaceWarpDebug 1
   adb shell setprop debug.oculus.MVOverlay 4        # 1=MV 2=depth 3=MV amplified 4=amplified, gray at zero
   adb shell setprop debug.oculus.MVOverlay.Alpha 0.8
   # then press the power button twice (sleep/wake) to apply
   ```
   An object that moves but shows gray (zero motion) in mode 4 has no MV pass. Fix its shader (see Fix 4). `quest_adb.py appsw-debug` in `quest-perf:quest-profiling-toolkit` wraps these props.
5. **Force half rate without integrating AppSW**, to size the win: run `adb shell setprop debug.oculus.sysPropDebug 1` and then `adb shell setprop debug.oculus.swapInterval 2` (Q3-074). This shows the budget at half rate. It shows no warp quality.
6. **Measure the MV pass cost.** The published figures conflict (see Key numbers). Take a RenderDoc Meta Fork capture and time the motion-vector pass. Or compare App GPU time with AppSW on vs off at locked levels (QUEST-GF2-007 notes). For a trace, `metavr perf analyze-trace --asw` adds the ASW view (quest.md §9.4).

## Key numbers

| Number | Value | Source / tag |
|---|---|---|
| Extra GPU compute | "up to 70%". Meta calls it "our initial testing". Unity calls it the best case. | Q3-062, G1-032 [doc] [verify on device]. `Quest 2` `Quest 3/3S` `Vulkan` |
| Budget per rendered frame at half rate | 27.8 ms (72 Hz), 22.2 ms (90 Hz), 16.7 ms (120 Hz). Arithmetic from the budgets. The compositor still runs at the full rate. | Q3-062 notes, quest.md §2.2. `all Quest` |
| Lower limit | Unity says it does not work at about 18 fps or below | Q3-062 [doc]. `Unity 6.x` |
| MV pass cost, **conflict QUEST-GF2-C3** | Meta GDC 2024: "expect 30%" of the new (doubled) frame goes to motion vectors (QUEST-GF2-007). The Meta native page calls the low-res MV pass "almost free" (Q3-063). Neither is a measurement. Plan with 30% and measure per title. | [doc] both. `Quest 3` (blog) / `Quest 2` (native example) |
| MV target size | 368x400 for a 1440x1584 eye buffer (Quest 2 example) | Q3-063 [doc]. `Quest 2` |
| AppSW memory | about 18 MB on Quest 3 (about 5.5 MB system plus 13.5 MB swapchains); about 14 MB on Quest 2 | Q3-063 [doc]. `Quest 2` `Quest 3` |
| MV format | RGBA16f (precision) or RG16f (memory). RG16f halves MV bandwidth. The option exists from OpenXR 1.14.0. | G1-033, Q3-070 [doc]. `OpenXR 1.14.0+` `Vulkan` |
| Gains at 90 / 120 Hz, and 3S vs 3 | **No published number.** Measure it (Verify, step 3). | Q3-077 [doc] [verify on device] |
| Store floor | Half-rate rendering with AppSW is VRC-compliant | Q2-079 [doc] |

Lead only: UploadVR reports that XR2 Gen 2 offloads "SpaceWarp motion extrapolation" to on-chip accelerators (A1-024, [community]). No Meta source ties this to the app-visible AppSW cost. Do not plan around it. [verify on device] by comparing the compositor `TW=` time with AppSW on, Quest 2 vs Quest 3.

## Fixes, ranked by payoff ÷ effort

### 1. Pick one setup path and meet every prerequisite (Throughput)

| | Meta path (Q3-064) | Unity-native path (Q3-065) |
|---|---|---|
| Unity | 2022.3.15f1+, 6000.0.9f1+, 6000.4.0f1+ (minimums; Meta recommends the latest stable) | 6.1+. 6000.1.13f1+ for right-handed NDC. |
| URP | Meta fork `Oculus-VR/Unity-Graphics`, branch per patch. Stock URP from 6000.0.9f1 with Render Graph also works. | URP 17.0.3+ with Render Graph. Not Compatibility Mode. |
| XR | OVRPlugin v34+, with OpenXR "Meta XR Space Warp" or the deprecated Oculus XR "Application SpaceWarp (Vulkan)" | OpenXR 1.11.0+ (1.15.1+ for right-handed NDC), "Application SpaceWarp". (Q4-058's changelog summary lists URP AppSW from OpenXR 1.15.0; the prerequisites page says 1.11.0. Target 1.15.1+, which also gives the NDC option.) |
| API | Vulkan only | Vulkan only |
| MV LightMode | `MotionVectors` | `XRMotionVectors` |
| Toggle | `OVRManager.SetSpaceWarp(bool)` | `SpaceWarpFeature.SetSpaceWarp(bool)` plus per-frame app-space pose |

**Conflict Q3-C3 (surface it, don't pick silently):** Meta says stock URP supports SpaceWarp from 6000.0.9f1 and still recommends its fork, for extra optimizations and for transparents. Unity lists 6.1+ / URP 17.0.3+, and its 6.2 manual says the fork is no longer needed from URP 17.0.3. Working rule from the dossier:
- On 2022.3 and 6.0, use the Meta fork.
- On 6.1+, stock URP works. Keep the fork only for transparent motion vectors or Meta's extra optimizations.
- On 6.5+/6.6, stock URP also gains UI and transparent SpaceWarp (U1-070). That removes the main reason for the fork.

Shaders written for one path's LightMode are skipped on the other (Q3-067). Choose once per project. Per-version branches and step lists are in [references/appsw-setup.md](references/appsw-setup.md). Read it when you do the setup, pick a fork branch, or upgrade Unity.

Tags: `Quest 2` `Quest 3/3S` `Vulkan` `Unity ≥ 2022.3.15f1` (Meta) / `Unity ≥ 6000.1` `URP 17.0.3+` (native). Effect: average GPU time per rendered frame gets up to about 2x budget (for example 27.8 ms at 72 Hz) minus the MV pass; variance: absorbs spikes as long as the rendered frame stays under the half-rate budget (Q3-062). Quality cost: warp artifacts (Fix 6). Latency: Positional TimeWarp and Phase Sync are automatic with AppSW, but controller latency can still be higher (Q3-073).

Side effect to check: before 6000.3, Meta's Vulkan subpass fork branches are incompatible with AppSW (U2-084 notes). You cannot have both on 2022.3 to 6000.2. Link: `unity-perf:unity-render-graph-tiling`.

### 2. Turn on Optimize Buffer Discards (Throughput)

Meta calls "Optimize Buffer Discards (Vulkan)" very important for AppSW performance (Q3-069). It makes 4x MSAA textures memoryless. gles3.md lists it as required (G1-031).
- Path: Project Settings > XR Plug-in Management > OpenXR > Android > Meta Quest Support (gear) > Optimize Buffer Discards (Vulkan).
- Tags: `Quest 2` `Quest 3/3S` `OpenXR 1.10.0+` / Oculus XR 1.5.0+ (Q4-058) `Vulkan`.
- Effect: lowers the average GPU time and bandwidth. No published ms figure.
- Quality cost: none documented. OBD itself, as a general feature, belongs to `quest-perf:quest-sdk-choices`.

### 3. Set the MV format to RG16f (Throughput)

- Path: OpenXR > Meta Quest Support > Space Warp motion vector texture format = RG16f.
- Effect: RG16f is 4 B/px vs 8 B/px for RGBA16f, which halves MV write and read bandwidth (Q4-062, G1-033, Q3-070). Lowers average GPU time; no published ms figure.
- Quality cost: less MV precision than RGBA16f; Meta states the error is under 0.5 px and lists RG16f as the recommended setting (Q4-062, G1-033).
- Tags: `Quest 2` `Quest 3/3S` `OpenXR 1.14.0+` `Vulkan`.
- Keep RGBA16f only if the MV overlay shows banding or wrong warps after the switch. [verify on device]

### 4. Give every moving opaque a motion-vector pass; statics use camera motion (Throughput: prerequisite that makes AppSW usable; Camera Motion Only on statics is the throughput saving)

- **Renderer > Additional Settings > Motion Vectors** (Q3-068):
  - Per Object Motion: moving opaques and skinned meshes.
  - Camera Motion Only (2022.3+): static meshes. It reuses depth and needs depth submission. On OpenXR use Depth Submission Mode 16- or 24-bit. On Oculus XR use "Depth Submission (Vulkan)".
  - Camera Motion Only on statics removes MV-pass draw calls. That directly shrinks the ~30%-or-"almost free" MV cost.
- **Built-in URP shaders, native path:** Lit, Unlit, Complex Lit, Simple Lit, Baked Lit and Shader Graph Lit/Unlit. Enable Material > Advanced Options > "XR Motion Vectors Pass (Space Warp)" (Q3-066). Shader Graph support landed in 6000.1.0a8 (U1-070).
- **Custom HLSL, native path:** needs a `_XRMotionVectorsPass` property, a `LightMode = XRMotionVectors` pass that writes stencil Ref 1, `APPLICATION_SPACE_WARP_MOTION`, and `ObjectMotionVectors.hlsl` (Q3-066). A paste-ready pass is in [references/appsw-setup.md](references/appsw-setup.md#custom-shader-xrmotionvectors-pass-urp-1703).
- **Custom HLSL, Meta fork:** `OculusMotionVectorPass` filters on `LightMode = MotionVectors`. The MV pass must use the same matrices and the same late-latching state as the eye pass. Gate extra work on `cameraData.xr.motionVectorRenderTargetValid` (Q3-067).
- **Vertex animation** (wind, vertex-offset VFX, GPU skinning outside the SkinnedMeshRenderer): apply the same displacement to the current and the previous position, i.e. previous = current. The object then warps by head motion only instead of producing wrong vectors (Q3-071).
- Tags: `Quest 2` `Quest 3/3S` `URP 14+` (fork) / `URP 17.0.3+` (native) `Vulkan`.
- Effect: average GPU time rises by one geometry pass per MV-writing object (Q3-063 notes); Camera Motion Only on statics removes those draws. No frame-time variance effect. Quality: removes smear on moving objects.

### 5. Re-arm on camera change and set the app-space pose every frame (Consistency)

`SetSpaceWarp(true)` must be called again whenever the main camera changes, for example after a scene or rig swap (Q3-075). The Unity-native path also needs `SetAppSpacePosition` and `SetAppSpaceRotation` every frame (Q3-065; which transform is disputed, see below). This component covers both paths. It is untested; compile-check it in your project.

```csharp
// AppSpaceWarpDriver.cs - attach once (DontDestroyOnLoad). Untested: compile-check in your project.
// Unity-native path: Unity 6000.1+, com.unity.xr.openxr 1.11.0+, "Application SpaceWarp" enabled.
// (On 6000.1+ without com.unity.xr.openxr 1.11+, define META_APPSW or remove this component.)
// Meta path: define META_APPSW (Player > Scripting Define Symbols) and have Meta XR Core SDK (OVRManager).
using UnityEngine;
#if UNITY_6000_1_OR_NEWER && !META_APPSW
using UnityEngine.XR.OpenXR.Features;
#endif

public sealed class AppSpaceWarpDriver : MonoBehaviour
{
    [Tooltip("Unity example: main camera transform; dossier Q3-065: tracking origin. A/B with MVOverlay 4.")]
    [SerializeField] Transform appSpaceSource; // null = Camera.main.transform
    [SerializeField] bool spaceWarpWanted = true;
    Camera _lastMain;
    bool _applied;

    // Per-frame policy toggle (Fix 6): off for fast combat / close hand work, on for slow GPU-heavy stretches.
    public void SetWanted(bool on) { spaceWarpWanted = on; Apply(on); _applied = true; }

    void Update()
    {
        var main = Camera.main;
        if (main != _lastMain) { _lastMain = main; _applied = false; } // Q3-075: re-arm after camera change
        if (!_applied) { Apply(spaceWarpWanted); _applied = true; }

#if UNITY_6000_1_OR_NEWER && !META_APPSW
        var src = appSpaceSource != null ? appSpaceSource : (main != null ? main.transform : null);
        if (spaceWarpWanted && src != null)
        {
            SpaceWarpFeature.SetAppSpacePosition(src.position);
            SpaceWarpFeature.SetAppSpaceRotation(src.rotation);
        }
#endif
    }

    static void Apply(bool on)
    {
#if META_APPSW
        OVRManager.SetSpaceWarp(on);
#elif UNITY_6000_1_OR_NEWER
        SpaceWarpFeature.SetSpaceWarp(on);
#endif
    }
}
```

Which transform to feed, both sides: Unity's OpenXR 1.18 spacewarp-workflow example passes the main camera's `transform.position` / `transform.rotation`, and says some headsets may not need the camera pose at all. Dossier Q3-065 says "from the tracking origin". The component defaults to `Camera.main.transform`; assign the XR Origin to test the other side. [verify on device] with MVOverlay 4: during smooth locomotion over a static scene, the MV overlay should show camera motion only, with no object-motion errors.

Tags: `Quest 2` `Quest 3/3S` `Vulkan` `Unity ≥ 6000.1` (native) or Meta XR SDK (Meta path). Effect: no cost when working. Prevents a silent drop to full rate, which on a scene tuned for half rate means stale frames.

### 6. Content and UI policy: toggle per frame and keep transparents out (Consistency)

AppSW can be toggled per frame (Q3-062). Content that warps badly (Q3-071; QUEST-GF2-007):
- transparents, particles and unsupported shaders: only one MV per pixel
- clean or high-contrast backgrounds
- very fast rotation
- near-field controllers and fast-moving held objects
- complex vertex animation

Policy:
- Turn AppSW off (`SetWanted(false)`) for fast combat or close hand interactions, and on for slow, GPU-heavy segments. The off state needs a full-rate budget. Keep a lower render-scale tier ready for it (`quest-perf:quest-resolution-foveation`).
- UI (Q3-072, U1-070):
  - Unity 6.5+: uGUI and TMP are supported. Enable Canvas > Additional Shader Channels > "Previous Position". Use the UI-Default, UI-DefaultETC1 or UI Unlit Detail shaders, or TMP "Mobile/Distance Field With SpaceWarp Compatibility". The TMP SpaceWarp shaders landed in 6000.6.0b6.
  - Before 6.5: UI takes the motion vectors behind it. Workaround: a URP/Unlit quad with the MV pass behind the World Space canvas.
  - Screen Space canvases are incompatible.
  - Meta fork: alpha-clipped MV for UI and text. For transparents, change `RenderQueueRange.opaque` to `.all` in the fork's MV pass.
  - HUD on compositor layers is Meta's alternative. See the conflict in Pitfalls.
- Tags: `Quest 2` `Quest 3/3S` `Unity ≥ 6000.5` (native UI) `Vulkan`.
- Effect: average cost rises during the off stretches (full-rate budget); variance: avoids artifact-driven perceptual judder; no frame-time gain.
- Cost: toggling off loses the headroom for that stretch. Plan the full-rate tier.

### 7. Late Latching with AppSW (Consistency, latency)

Meta advises enabling Late Latching with AppSW (Q3-073). On the Meta fork, the MV pass must share the eye pass's late-latching state (Q3-067). The setup and caveats are owned by `quest-perf:quest-frame-pacing`. Effect: latency only, no average-GPU change published; quality cost: none documented. Never ship Debug Mode (see `quest-perf:quest-frame-pacing`). Tags: `Quest 2` `Quest 3/3S` `Vulkan` `Unity ≥ 2022.3.15f1` (Meta fork) / `Unity ≥ 6000.1` (native).

## Verify

Keep the scene and path identical, lock CPU/GPU levels, and run 10 minutes per arm, then a 20-30 minute soak for the winner with levels unpinned (`adb reboot` clears the debug props; Q1-079), so the runtime governor and thermal behaviour are real:
1. **Active:** `ASW=<Hz>, Type=App`, `FPS=<Hz/2>/<Hz>` and `VSnc=0` in every per-second VrApi line. Check it again after every scene load (Q3-074, Q3-075).
2. **Throughput:** App GPU time per rendered frame may rise toward the half-rate budget (27.8 ms at 72 Hz) while stale frames stay at 0. The saving to expect is at most "up to 70%" more compute (Q3-062). Budget about 30% of the doubled frame for motion vectors until your RenderDoc capture says otherwise (QUEST-GF2-C3).
3. **90/120 Hz and 3S:** no published number (Q3-077). Compare AppSW off at full rate vs on at half rate at the same levels. Record App GPU time, stale frames per minute, and compositor time (`TW=`), which grows with AppSW. Use the CSV analyzer in `quest-perf:quest-profiling-toolkit`.
4. **Thermal:** with AppSW on, GPU level demand should drop. Over the 20-30 minute soak, the first-5 vs last-5 minute frame time and level drift should be flatter than the full-rate arm. Meta lists "not using ... App Spacewarp" as a thermal-pressure pattern (A3-079). No published magnitude. [verify on device]
5. **Quality:** MVOverlay 4 shows no gray on moving objects. Do a visual pass on transparents, UI, held objects and fast turns.

## Pitfalls and myths

- **"AppSW works on GLES."** It does not. It is Vulkan only (G1-031). `GL_QCOM_frame_extrapolation` exists in the Quest 3 GLES driver, but no Meta or Unity doc ties it to AppSW (G1-015, G3-062).
- **"70% is guaranteed."** It is Meta's "initial testing" best case, minus the MV pass. Measure it (G1-032).
- **"The MV pass is free."** One Meta page says so, and another says to expect 30% (QUEST-GF2-C3). It costs a geometry pass per MV-writing object, so skinned-heavy scenes pay more.
- **Mixing paths.** An `XRMotionVectors` shader on the Meta fork, or a `MotionVectors` shader on the native path, is silently skipped. The object smears (Q3-067).
- **NDC handedness mismatch** (Unity 6000.1.13f1+ / OpenXR 1.15.1+): the "Use Right Handed NDC" gear option must match what the runtime expects. A mismatch is a likely cause of wrong warps (Q3-065 notes). [verify on device]
- **Depth submission bugs:**
  - OpenXR before 1.14.2 corrupted the spacewarp depth texture (Q3-068).
  - UUM-84612: black screen with MSAA + post + SpaceWarp depth submission on 6000.0.40f1 and later. A fix is listed in 6000.0.50f1, but the issue link persists in notes through 6000.0.58f1 (U1-079). [verify on device]
  - Keep Depth Submission Mode None unless SpaceWarp or composition needs it (U1-092).
- **Composition layers under AppSW, conflict Q3-C9 / Q3-086:**
  - Unity lists composition layers as not warped.
  - Meta says Compositor Layer SpaceWarp smooths layer motion, and recommends layers for HUD UI.
  - AppSW itself applies to the projection layer only (Q3-076).
  - Probably different mechanisms. [verify on device]
- **Subsampled layout plus AppSW** adds compositor cost (Q3-C6). A/B it; `quest-perf:quest-resolution-foveation` owns it.
- **Forgetting the off state.** If gameplay toggles AppSW off, that segment needs a full-rate budget, or it drops frames.
- **Screen Space UI** cannot be warped (Q3-072).

## Sources

All accessed 2026-09-24.
- https://developers.meta.com/horizon/documentation/unity/unity-asw/ [doc]: Meta path, fork branches, OBD, MV passes, UI on the fork, SetSpaceWarp re-arm (Q3-063 to 069, Q3-072, Q3-074, Q3-075, G1-031, G1-032)
- https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ [doc]: mechanism, "almost free" MV pass, memory, artifacts, diagnostics, projection-layer scope (Q3-062, Q3-063, Q3-071, Q3-073, Q3-074, Q3-076, Q3-077)
- https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ [doc]: half rate, VRC compliance, `VSnc=0` / `ASW=` (Q2-079)
- https://developers.meta.com/horizon/blog/optimizing-for-success-meta-quest-3-gdc/ [doc] (blog): "expect 30%" for MVs (QUEST-GF2-007)
- https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html [doc]: best case, the 18 fps floor, built-in shader support, the fork not needed from URP 17.0.3 (Q3-062, Q3-066, Q3-C3)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-prerequisites.html [doc]: native-path prerequisites (Q3-065)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp.html and .../spacewarp/spacewarp-workflow.html [doc]: `SpaceWarpFeature` API (Q3-065)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-shaders.html [doc]: XRMotionVectors pass (Q3-066)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-ui.html [doc]: UI support (Q3-072)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html [doc]: OBD, MV format (Q3-069, Q3-070)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/metaquest.html [doc]: RG16f halves MV bandwidth (G1-033)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc]: Meta's recommended OpenXR settings incl. Space Warp RG16f, Depth Submission None (unity.md settings summary, U1-092)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc]: 1.14.2 depth fix (Q3-068)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/subsampledlayout.html [doc]: compositor cost with AppSW (Q3-C6)
- https://unity.com/releases/editor/whats-new/6000.1.0a8, https://unity.com/releases/editor/whats-new/6000.5.0b1 and https://unity.com/releases/editor/whats-new/6000.6.0b6 [doc]: SpaceWarp support history (U1-070)
- https://unity.com/releases/editor/whats-new/6000.0.50f1 [doc]: UUM-84612 (U1-079)
- https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ [doc]: the subpass fork is incompatible with AppSW before 6000.3
- https://developers.meta.com/horizon/essentials/thermal/ [doc]: AppSW in thermal guidance (A3-079)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc]: VrApi per-second line (Q1-027, Q1-034)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]: CPU/GPU level pinning, unpin before soaks (Q1-079)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc]: RG16f 4 vs 8 B/px, under 0.5 px error (G1-033, Q4-062)
- https://developers.meta.com/horizon/documentation/native/android/os-compositor/ [doc]: Late Latching and latency with AppSW (Q3-073)
- https://developers.meta.com/horizon/documentation/unity/unity-ovroverlay/ [doc]: `debug.oculus.logLayers` / CompositorClient flags (Q3-083)
- https://www.uploadvr.com/snapdragon-xr2-gen-2/ [community]: XR2 Gen 2 offload claim, lead only (A1-024)
