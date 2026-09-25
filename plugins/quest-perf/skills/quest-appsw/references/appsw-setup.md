# AppSW setup by path and version

Reference for `quest-perf:quest-appsw`. Every item applies to Vulkan only; no other graphics API supports AppSW (G1-031). All sources accessed 2026-09-24.

## Which path for which Unity version

| Unity | URP | Recommended path | Notes |
|---|---|---|---|
| 2021.3 | 12 | none | Below Meta's minimum (2022.3.15f1) |
| 2022.3.11-17 | 14.0.8 | Meta fork `2022.3/14.0.8-oculus-app-spacewarp` (branch covers 11-17; use 15f1+ per Meta's minimum) | Meta's minimum is 2022.3.15f1 (Q3-064) |
| 2022.3.18-23 | 14.0.9 | Meta fork `2022.3/14.0.9-oculus-app-spacewarp` | |
| 2022.3.24+ | 14.0.10+ | Meta fork `2022.3/14.0.10-oculus-app-spacewarp` | |
| 6000.0.9f1-6000.3.x | 17.0.x-17.3 | Meta fork `6000.0/oculus-app-spacewarp`. Stock URP with Render Graph also works per Meta. | Conflict Q3-C3: Unity's own docs start stock support at 6.1 / URP 17.0.3 |
| 6000.1+ | 17.1+ | Unity-native OpenXR "Application SpaceWarp" on stock URP | 6000.1.13f1+ with OpenXR 1.15.1+ for the right-handed NDC option (Q3-065) |
| 6000.4 | 17.4 | Unity-native, or Meta fork `6000.4/oculus-app-spacewarp` | Meta lists 6000.4.0f1 as a minimum (Q3-064) |
| 6000.5 / 6000.6 | 17.5 / 17.6 | Unity-native | UI and transparent SpaceWarp in 6000.5.0b1; TMP SpaceWarp shaders in 6000.6.0b6 (U1-070) |

The fork lives at `Oculus-VR/Unity-Graphics` on GitHub. Pin the URP and core packages to the branch that matches your editor patch.

Fixes in the SpaceWarp history (U1-070, U1-079, Q3-068):

| Change | Version |
|---|---|
| Shader Graph MV support | 6000.1.0a8 |
| Background motion-vector fix | 6000.0.54f1 |
| Matrices fix | 6000.3.0b3 |
| UUM-84612 fix entry (black screen with MSAA + post + SpaceWarp depth) | 6000.0.50f1 / 6000.2.0a1. The issue link still appears in 6.0 notes through 6000.0.58f1. [verify on device] |
| Spacewarp depth-texture corruption from depth submission fixed | OpenXR 1.14.2 (2025-03-20) |

Meta's Vulkan subpass fork branches are incompatible with AppSW before 6000.3 (U2-084 notes, https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ [doc]).

## Meta path steps (Q3-064, Q3-067 to 069)

1. Player > Android > Graphics APIs: Vulkan only.
2. Install Meta XR Core SDK (OVRPlugin v34+) with the Unity OpenXR Plugin. Meta recommends that stack from SDK v74. The deprecated Oculus XR Plugin also works.
3. Swap URP for the matching fork branch (table above).
4. Enable the feature:
   - OpenXR: XR Plug-in Management > OpenXR > "Meta XR Space Warp".
   - Oculus XR: Android > Experimental > "Application SpaceWarp (Vulkan)".
5. Turn on Optimize Buffer Discards (Vulkan). Meta calls it "very important" for AppSW.
6. Depth submission: needed for Camera Motion Only statics. On OpenXR use 16- or 24-bit. On Oculus XR use "Depth Submission (Vulkan)".
7. Custom shaders need a `LightMode = MotionVectors` pass. `OculusMotionVectorPass` filters on that tag. Use the fork branch's own URP Lit shader as the template for your version, and keep matrices and late-latching state identical to the eye pass. Gate any extra renderer-feature work on `cameraData.xr.motionVectorRenderTargetValid`.
8. Transparents and UI on the fork:
   - Alpha-clipped MV for UI and text.
   - To give transparents motion vectors, change `RenderQueueRange.opaque` to `RenderQueueRange.all` in the fork's MV pass filter. Cost: more MV draws.
9. Runtime: `OVRManager.SetSpaceWarp(true)`. Call it again after every main-camera change (Q3-075).

## Unity-native path steps (Q3-065, Q3-066, Q3-069, Q3-070)

1. Unity 6000.1+ (6000.1.13f1+ for NDC choice), OpenXR 1.11.0+ (1.15.1+ for NDC choice), URP 17.0.3+.
   - OpenXR minimum conflict: Q4-058's changelog summary lists URP AppSW from OpenXR 1.15.0; the prerequisites page says 1.11.0 (Q3-065). Target 1.15.1+, which also gives the NDC option.
   - Render Graph must be on. Compatibility Mode is not supported.
2. Vulkan only, plus a provider package for Quest.
3. Enable the feature: Edit > Project Settings > XR Plug-in Management > OpenXR > All Features > "Application SpaceWarp".
   - Its gear holds "Use Right Handed NDC". Set it as the runtime requires. A mismatch is a likely cause of wrong warps [verify on device].
4. OpenXR > Meta Quest Support gear:
   - Optimize Buffer Discards (Vulkan): OpenXR 1.10.0+.
   - Space Warp motion vector texture format: RG16f, which halves MV bandwidth; RGBA16f for precision. The option is from OpenXR 1.14.0.
5. Materials:
   - Built-in Lit, Unlit, Complex Lit, Simple Lit, Baked Lit and Shader Graph Lit/Unlit: enable Advanced Options > "XR Motion Vectors Pass (Space Warp)".
   - Custom HLSL: add the pass below.
6. Renderers:
   - Motion Vectors = Per Object Motion for moving objects.
   - Camera Motion Only for statics. This needs depth submission (Q3-068).
7. Runtime API: `UnityEngine.XR.OpenXR.Features.SpaceWarpFeature`:
   - `static void SetSpaceWarp(bool enabled)`: call at start, and again after camera changes.
   - `static void SetAppSpacePosition(Vector3)` and `static void SetAppSpaceRotation(Quaternion)`: call every frame.
   - SKILL.md Fix 5 has the driver component.

## Custom shader XRMotionVectors pass (URP 17.0.3+)

`URP 17.0.3+` `Unity ≥ 6000.1` `Vulkan`. From Unity's SpaceWarp shader page (Q3-066). Add the property to the shader's `Properties` block:

```hlsl
[HideInInspector] _XRMotionVectorsPass("_XRMotionVectorsPass", Float) = 1.0
```

Add this pass inside the `SubShader`, next to the forward pass:

```hlsl
Pass
{
    Name "XRMotionVectors"
    Tags { "LightMode" = "XRMotionVectors" }
    ColorMask RGBA

    // Stencil write marks object-motion pixels for the runtime
    Stencil
    {
        WriteMask 1
        Ref 1
        Comp Always
        Pass Replace
    }

    HLSLPROGRAM
    #pragma shader_feature_local _ALPHATEST_ON
    #pragma multi_compile _ LOD_FADE_CROSSFADE
    #pragma shader_feature_local_vertex _ADD_PRECOMPUTED_VELOCITY
    #define APPLICATION_SPACE_WARP_MOTION 1

    // Replace with YOUR shader's input include: it must declare the same
    // CBUFFER_START(UnityPerMaterial) ... CBUFFER_END as every other pass,
    // or the SRP Batcher drops the material.
    #include "Packages/com.unity.render-pipelines.universal/Shaders/BakedLitInput.hlsl"
    #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ObjectMotionVectors.hlsl"
    ENDHLSL
}
```

Notes:
- `ObjectMotionVectors.hlsl` supplies the vertex and fragment programs. If you use `_ALPHATEST_ON`, your input include must provide the base-map and cutoff properties that file's alpha-test path samples. Check the file in your URP version for the exact names. [verify on device]
- Vertex displacement (wind, VFX offsets) is not in the stock MV vertex program. Either write your own MV vertex program that applies the same displacement to the current and the previous position, or accept head-motion-only warping for that object. Meta's workaround for complex vertex animation is to use the current position as the previous position (Q3-071).
- UI shaders need a hand-written MV pass: unjittered view-projection, previous position from the "Previous Position" canvas channel, `ZWrite On`, clip on alpha × `_XRMotionVectorsPass`. On 6.5+, use Unity's shipped SpaceWarp UI shaders instead of writing your own (Q3-072).
- Check the result with `debug.oculus.MVOverlay 4`. A moving object that shows gray is missing its pass (Q3-074).

## Sources

- https://developers.meta.com/horizon/documentation/unity/unity-asw/ [doc], accessed 2026-09-24 (page updated May 13, 2026)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-prerequisites.html [doc], accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-workflow.html [doc], accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-shaders.html [doc], accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-ui.html [doc], accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html [doc], accessed 2026-09-24
- https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html [doc], accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc], accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html [doc], accessed 2026-09-24 (Q4-058)
- https://unity.com/releases/editor/whats-new/6000.1.0a8, https://unity.com/releases/editor/whats-new/6000.5.0b1, https://unity.com/releases/editor/whats-new/6000.6.0b6, https://unity.com/releases/editor/whats-new/6000.0.50f1 [doc], accessed 2026-09-24
- https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ [doc], accessed 2026-09-24
- https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ [doc], accessed 2026-09-24
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc], accessed 2026-09-24
