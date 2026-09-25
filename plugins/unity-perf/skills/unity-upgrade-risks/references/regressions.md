# Quest upgrade regressions and breaks: issue table

Read from `SKILL.md` when you need the full per-issue list for a specific
source/target Unity version pair. All rows accessed 2026-09-24. "Goal" is
Throughput (T) or Consistency (C). Fixed-in versions are the ones the release
notes or Meta page list; a missing stream means no entry was found, not that
the stream is safe.

## 1. Performance and rendering regressions (with fixes)

| Issue | Symptom on Quest | Affected | Fixed in | Workaround / check | Goal | Evidence | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UUM-90118 | Up to ~20% higher GPU utilization with Render Graph on (reporter: ~50% vs ~90% util, worse on Quest 2, firmware v71). ReadOnlyDepth flag stops depth-copy merging into uber post on XR Android Vulkan | 6000.0.16f1-6000.0.45f1, 6.1 before b14 (not on 6000.0.15f1) | 6000.0.46f1, 6000.1.0b14, 6000.2.0a9 | Upgrade the patch before any other tuning | T | [measured] | https://issuetracker.unity3d.com/issues/gpu-utilization-increases-by-20-percent-on-meta-quest-headsets-when-render-graph-is-enabled-on-6000-dot-0-16f1-and-higher ; https://unity.com/releases/editor/whats-new/6000.0.46f1 ; https://unity.com/releases/editor/whats-new/6000.1.0b14 |
| UUM-92499 / UUM-93821 | RG `AddBlitPass` / `AddCopyPass` ignore multiview array slices: only left eye renders (Quest 2) | 6.0 before .49 | 6000.0.49f1, 6000.1.0f1 | Do not build custom RG passes on these helpers on older 6.0 patches | C | [doc] | https://unity.com/releases/editor/whats-new/6000.0.49f1 |
| UUM-84612 | Black player with MSAA + post-processing + SpaceWarp depth submission | 6000.0.40f1-6000.0.49f1 (at least) | Fix entry in 6000.0.50f1, 6000.2.0a1; issue link keeps appearing in 6.0 notes through 6000.0.58f1 | [verify on device] with AppSW on | C | [doc] | https://unity.com/releases/editor/whats-new/6000.0.50f1 |
| UUM-76868 | Unused extensions broke right-eye rendering on Quest 2 with OpenXR | 6.0 before .14 | 6000.0.14f1 | Upgrade | C | [doc] | https://unity.com/releases/editor/whats-new/6000.0.14f1 |
| UUM-95617 | RenderGraph + MSAA log spam (CPU cost on device) | 6.0 before .38 | 6000.0.38f1 | Upgrade | T | [doc] | https://unity.com/releases/editor/whats-new/6000.0.38f1 |
| UUM-104169 | GameManager logcat spam on Quest 2 | 6.0 before .49 | 6000.0.49f1 | Upgrade | T | [doc] | https://unity.com/releases/editor/whats-new/6000.0.49f1 |
| UUM-109083 | Vulkan errors on app exit | 6.0 before .52, 6.1 before .9, 6.2 before b8 | 6000.0.52f1, 6000.1.9f1, 6000.2.0b8 | Upgrade | C | [doc] | https://unity.com/releases/editor/whats-new/6000.0.52f1 |
| UUM-91896 | GLES multi-pass render-pass validation errors | 6.0 before .46 | 6000.0.46f1, 6000.1.0b14 | Upgrade | C | [doc] | https://unity.com/releases/editor/whats-new/6000.0.46f1 |
| UUM-93243 | GLES crash in ClearBufferSubData on second launch (Quest 2) | 6.0 before .73, 6.3 before .14 | 6000.0.73f1, 6000.3.14f1, 6000.5.0b8 | Upgrade if shipping GLES | C | [doc] | https://unity.com/releases/editor/whats-new/6000.0.73f1 |
| UUM-146214 | GPU occlusion culling with GRD stops culling occluded instances: GPU cost for no gain | 6000.5.0-6000.5.7, 6.6 betas | 6000.5.8f1, 6000.6.0f1 (one snippet says 6000.6.0b5), 6000.7.0a3 | Turn GPU occlusion culling off on 6.5.0-6.5.7; Vulkan only anyway | T | [doc] | https://unity.com/releases/editor/whats-new/6000.5.8f1 ; https://unity.com/releases/editor/whats-new/6000.6.0f1 ; https://unity.com/releases/editor/whats-new/6000.5.6f1 |
| UUM-148728 | URP GLES additional-light limit forced from 16 to 32 regardless of the "Use OpenGL ES 3.0 shaders" setting (conflict X-C6) | 6.6 pre-release | 6000.6.0f1 | Upgrade to 6000.6.0f1+ | T | [doc] | https://unity.com/releases/editor/whats-new/6000.6.0f1 |
| UUM-121520 | Higher Vulkan command-buffer memory with graphics jobs on Android. No MB figure published | 6.0 (no backport found), 6.2 before .12 | 6000.2.12f1, 6000.3.0b8 (6.3.0f1+), 6000.4.0a2 | Measure `adb shell dumpsys meminfo <pkg>` (Graphics / GL mtrack) 6.0 vs 6.3 with graphics jobs on | C | [doc] [verify on device] | https://unity.com/releases/editor/whats-new/6000.2.12f1 ; https://unity.com/releases/editor/whats-new/6000.3.0f1 |
| UUM-71363 | Vulkan images missing transient usage flag when lazily allocated memory unavailable | 2022.3 before .53, 6.0 before .23 | 2022.3.53f1, 6000.0.23f1 | Upgrade | T | [doc] | https://unity.com/releases/editor/whats-new/6000.0.23f1 ; https://unity.com/releases/editor/whats-new/2022.3.53f1 |
| Vulkan PSO cache | Race in Vulkan PSO cache registration / async PSO shutdown; corrupted pipeline cache handling | 6.0 betas; cache handling before 6.4 | 6000.0.0b11; 6000.4.0a2/a4 | See unity-perf:unity-shader-hitches | C | [doc] | https://unity.com/releases/editor/whats-new/6000.0.0b11 ; https://unity.com/releases/editor/whats-new/6000.4.0a4 |
| UUM-121231 | "Fixed GraphicsStateCollection warmup for Vulkan". CONFLICT X-C1: U1-047 finds no 6.0/6.3 backport, so LTS warmup may not remove hitches; U3-091 reads it as a 6.4-alpha-only regression that never hit LTS | 6.0, 6.3 (disputed) | 6000.4.0a4 | Cold-run A/B with and without GSC warmup; owner unity-perf:unity-shader-hitches | C | [doc] [verify on device] | https://unity.com/releases/editor/whats-new/6000.4.0a4 ; https://unity.com/releases/editor/whats-new/6000.0.0 |

## 2. Dynamic-resolution regressions (Meta's known-issues list)

| Symptom | Affected | Fixed in | Goal | Evidence | Source |
| --- | --- | --- | --- | --- | --- |
| Extra intermediate render pass whenever render scale is not 1.0 (can make dynamic resolution cost more than it saves) | 2021.3 before .36, 2022.3 before .22 | 2021.3.36f1, 2022.3.22f1, 6000.0.1f1 | T | [doc] | https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ |
| Temporary RTs reallocated on every scale change, possible OOM. Workaround `ScalableBufferManager.ResizeBuffers(scale, scale)` | 2022.3 before .15 (URP before 14.0.9), early 6.0 | 2022.3.15f1, 6000.0.1f1 | C | [doc] | https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ |
| Screen distortion | 6000.0.22f1-6000.0.24f1 | 6000.0.25f1 | C | [doc] | https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ |
| RenderObjects feature gets wrong viewport under dynamic resolution; with foveation each RenderObjects pass becomes its own Vulkan render pass (extra load/store) | Unity 6.x URP before the fixes | 6000.0.81f1, 6000.3.21f1, 6000.5.6f1, 6000.6.0b5, 6000.7.0a3 | T | [doc] | https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ |
| Wrong copy-depth scaling with dynamic resolution; consistent HW dynamic-res settings enforced | URP 14 before 14.0.11 / 14.0.10 | URP 14.0.11, 14.0.10 | C | [doc] | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/changelog/CHANGELOG.html |

## 3. Foveation regressions

| Issue | Symptom | Affected | Fixed in | Check | Goal | Evidence | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Foveated post support | UberPost / FinalPostBlit not foveated | 6.0 before .22 | 6000.0.22f1 (Render Graph support 6000.0.0b15; Forward+ 2022.3.16f1 / 6000.0.0b11) | Foveated post on 6.0 needs 6000.0.22f1+ | T | [doc] | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html ; https://unity.com/releases/editor/whats-new/6000.0.22f1 |
| UUM-132450 | Black view with framebuffer fetch + foveated rendering (wrong MSAA resolve attachment) | 6.3 before .14, 6.4 before .4; no 6.0 entry found | 6000.3.14f1, 6000.4.4f1, 6000.5.0b5 | Do not ship FB fetch + FFR below these | C | [doc] | https://unity.com/releases/editor/whats-new/6000.3.14f1 ; https://issuetracker.unity3d.com/issues/the-view-renders-black-when-using-framebuffer-fetch-with-foveated-rendering-in-a-player-for-meta-quest |
| UUM-113364 | Foveation switched off when MSAA on, Vulkan. Fix note says "PC or linked XR"; standalone Quest status unknown (conflict U1-C6) | 6.3 and earlier (if affected) | 6000.4.0b9, 6000.5.0a7 | Check FDM attachment in RenderDoc Meta Fork / foveation level in OVR Metrics with MSAA on vs off | T | [doc] [verify on device] | https://unity.com/releases/editor/whats-new/6000.4.0b9 |
| IN-115870 | FFR glitches, 90 to 40-60 fps, GPU util ~50% to over 90%, even at FFR level 0 (URP 17.0.3-17.2.0, OpenXR 1.15.1, Meta SDK v77, Vulkan, confirmed Quest 2) | 6000.1.15f1, 6.2 | Reported fixed in 6000.3.0f1 | Disable the feature fully (not level 0), move to 6.3+ | T, C | [community] [verify on device] | https://discussions.unity.com/t/bug-severe-ffr-glitches-performance-loss-with-unity-6-1-6-2-with-urp-vulkan-openxr-on-quest/1677819 |
| SRP foveation + URP HDR | Top half of image goes low-res instead of periphery | 6.0 URP, OpenXR | None recorded | Legacy API or HDR off | C | [community] [verify on device] | https://discussions.unity.com/t/srp-foveated-rendering-on-quest-broken-with-openxr-urp-hdr/1672458 |
| Meta feedback 2302986490105678 | FFR High + 24-bit depth submission shows glitched squares, Meta 6000.4 oculus-app-spacewarp URP fork | 6000.4.8f1 | Investigating | Avoid the combination or verify | C | [community] [verify on device] | https://developers.meta.com/horizon/feedback/vr/investigations/2302986490105678/ |
| OpenXR 1.18.0-pre.1 | FDM attachments turned off at foveation level 0 (SRP path): behaviour change at level 0 across the plugin upgrade | OpenXR before vs from 1.18.0-pre.1 | n/a | Re-baseline FFR level 0 captures | T | [doc] | https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html |
| FRStateMismatch | Custom raster pass on camera color without matching `EnableFoveatedRasterization` state splits the native render pass | 6.0+ Render Graph | By design | Set foveation state on custom passes | T | [doc] | https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs |

## 4. API and pipeline breaks per hop

| Hop | Break | Perf consequence | Goal | Source |
| --- | --- | --- | --- | --- |
| 2021.3 to 2022.3 (URP 12 to 14) | RTHandle system (`cameraColorTargetHandle`, `RenderingUtils.ReAllocateIfNeeded`); camera targets accessed in `SetupRenderPasses` | Custom passes must be ported | C | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/upgrade-guide-2022-1.html |
| 2021.3 to 2022.3 | `SHADER_QUALITY_LOW/MEDIUM/HIGH` and `SHADER_HINT_NICE_QUALITY` removed; use `SHADER_API_MOBILE` / `SHADER_API_GLES` | Shaders using them as a Quest switch silently take the default (expensive) path | T | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/upgrade-guide-2022-2.html |
| 2022.3 to 6.0 (URP 17) | Render Graph default; upgraded projects auto-set to Compatibility Mode; non-RG APIs obsolete from 6000.0.0b11 | Upgraded project runs the legacy path, no RG gains until unticked | T | https://docs.unity3d.com/6000.0/Documentation/Manual/urp/upgrade-guide-unity-6.html |
| 2022.3 to 6.0 | Custom VolumeComponents overriding `Override()` must set `overrideState = true` when changing a value | Parameters not reset: wrong post settings | C | https://docs.unity3d.com/6000.0/Documentation/Manual/urp/upgrade-guide-unity-6.html |
| 2022.3 to 6.0 | `FindObjectsOfType` obsolete; `FindObjectsByType` is unsorted and faster | CPU | T | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html |
| 2022.3 to 6.0 | Quality mip limit no longer applies to runtime-created textures by default | Memory growth for procedural/runtime textures | C | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html |
| to 6.2 | `SetupRenderPasses` deprecated; AfterRendering injection runs after the final blit | Custom passes move relative to the backbuffer write | C | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity62.html |
| to 6.3 | Compatibility Mode hidden behind `URP_COMPATIBILITY_MODE` define (6000.3.0a2); `enableRenderCompatibilityMode` read-only false; `AddRenderPass()` legacy path deprecated (6000.3.0a5) | Last version where legacy passes run | C | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity63.html ; https://unity.com/releases/editor/whats-new/6000.3.0a2 |
| to 6.4 | Compatibility Mode and the define removed (6000.4.0a4); `StoreActionsOptimization` obsolete; passes without `RecordRenderGraph` stop working | Unported passes silently absent | C | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity64.html |
| to 6.5 | Oculus XR package deprecated (6000.5.0b4), not supported on 6.5/6.6; VR module removed (`UnityEngine.VR` fails to compile); legacy RG compiler obsolete; Built-in RP deprecated; Rendering Debugger on UI Toolkit | Forced OpenXR migration | C | https://unity.com/releases/editor/whats-new/6000.5.0b4 ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html |
| to 6.6 | Dynamic batching obsolete | Small-mesh batching path lost; see unity-perf:unity-draw-calls-batching | T | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html |
| to 6.6 | GLES minimum 3.1; "Use OpenGL ES 3.0 shaders" auto-on only if project never required ES 3.1; ES 3.1 shaders raise MAX_VISIBLE_LIGHTS 16 to 32 | More shader work on GLES builds; ES 3.0 context no longer possible | T | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html |
| OpenXR plugin across 1.18.0-pre.2 | `XRDisplaySubsystem` GPU times change from ms to seconds | In-app telemetry off by 1000x across the upgrade; owner unity-perf:unity-profiling-workflow | C | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem.html |

Toolchain changes (not performance, but they block the A/B build): 6.0 Gradle
8.4 / AGP 8.3.0 / JDK 17; 6.1 Gradle 8.11 / AGP 8.7.2 / NDK r27c; 6.3 Gradle
9.1.0 / AGP 9.0.0, no `proguard-android.txt`, plug-ins need a unique namespace.
Old Meta or third-party .aar plug-ins can break the build. Sources:
https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html ;
https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity61.html ;
https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html [doc].
Minimum Android API (6.0: 23, 6.3: 25, 6.5: 26) does not affect projects on the
Meta Quest build profile (min 29, target 32).

## 5. Where to find the official lists

- What's New: `https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html`, `WhatsNewUnity61.html` ... `WhatsNewUnity66.html`.
- Upgrade guides: `UpgradeGuideUnity6.html`, `UpgradeGuideUnity61.html` ... `UpgradeGuideUnity66.html` (same folder). From 6.2 on, URP breaks live here, not in separate URP pages.
- URP-only guides: URP 13/14 in the 14.0 package docs; `urp/upgrade-guide-unity-6.html` (URP 17) and `urp/upgrade-guide-unity-6-1.html` (URP 17.1).
- XR feature support per version: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html
- Per-patch notes: `https://unity.com/releases/editor/whats-new/<version>`.
