---
name: unity-version-matrix
description: "Lookup of which Unity/URP version has which Quest performance feature, 2021.3 LTS (URP 12) through Unity 6.0-6.6 (URP 17), plus 6.7 beta status: Render Graph, Forward+, GPU Resident Drawer, on-tile post-processing, Tile-Only Mode, Build Profiles and the Meta Quest profile, LTS dates, Meta's minimum Unity and OpenXR versions. Use for \"does Unity X have Y\" or choosing an engine version for a Quest 2/3/3S project; how to use each feature lives in its owning skill."
---

# Unity/URP version matrix for Quest

Feature availability gates every other fix in this marketplace: a setting that
does not exist in the project's Editor stream cannot be tuned. This skill
answers "what exists in which version" and "which version should this Quest
project be on". Goal: **Throughput and Consistency** (availability of the
features that deliver both, plus patch coverage for Quest regressions).

All facts: access date 2026-09-24. Stream naming: 6000.N = Unity 6.N.

## When to use / when not

Use when:
- someone asks "does Unity 2022.3 have X", "is X available in 6.3 LTS", "which
  Unity version for a new Quest project", "Meta minimum Unity version";
- a fix from another skill names a feature and you must check the project's
  version can run it (GRD, on-tile post, Tile-Only Mode, Multiview Render
  Regions, GSC, Quest shader optimizations, depth input attachment);
- deciding whether an engine upgrade is justified by a feature.

Do not use for:
- "FPS dropped after upgrading", regressions, patch floors, API breaks,
  Oculus XR to OpenXR migration steps: `unity-perf:unity-upgrade-risks`.
- Choosing OpenXR vs Oculus XR, Meta XR SDK settings, Optimize Buffer
  Discards, manifest flags: `quest-perf:quest-sdk-choices`.
- How to configure URP asset/renderer settings: `unity-perf:unity-urp-settings`.
- How to keep passes on-tile, Render Graph merging: `unity-perf:unity-render-graph-tiling`.
- Which GLES version Unity emits, GLES limits: `gles3-perf:gles-versions-unity-output`.
- Vulkan vs GLES decision (UUM-93226): `gles3-perf:gles-vs-vulkan`.
- Unknown bottleneck: `quest-perf:quest-triage`.

## Diagnose first

Establish the exact stack before answering any availability question. Five
facts decide almost every row of the matrix: Editor patch, URP version, XR
plugin and version, Android graphics API list, and (6.0-6.3) whether Render
Graph Compatibility Mode is on.

1. **Editor + packages + API + Compatibility Mode.** Paste into
   `Assets/Editor/QuestVersionReport.cs` and run *Tools > Quest Perf > Version
   Report*. [verify in Editor]; written to compile on 2021.3 LTS to 6.6 via
   `#if UNITY_6000_x_OR_NEWER` guards.

```csharp
// Assets/Editor/QuestVersionReport.cs  (Unity 2021.3 LTS .. 6.6; verify in Editor)
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using PackageInfo = UnityEditor.PackageManager.PackageInfo;

public static class QuestVersionReport
{
    [MenuItem("Tools/Quest Perf/Version Report")]
    static void Run()
    {
        var sb = new StringBuilder("Quest version report\n");
        sb.AppendLine("Editor: " + Application.unityVersion);
        foreach (var p in PackageInfo.GetAllRegisteredPackages()
                     .Where(p => p.name == "com.unity.render-pipelines.universal"
                              || p.name.StartsWith("com.unity.xr.")
                              || p.name.StartsWith("com.meta.xr."))
                     .OrderBy(p => p.name))
            sb.AppendLine($"  {p.name} {p.version}");
        // Graphics API list is global Player Settings; a build-profile
        // override takes precedence [verify in Editor].
        sb.AppendLine("Android graphics APIs (in order): " + string.Join(", ",
            PlayerSettings.GetGraphicsAPIs(BuildTarget.Android)));
#if UNITY_6000_0_OR_NEWER
        var bp = UnityEditor.Build.Profile.BuildProfile.GetActiveBuildProfile();
        sb.AppendLine("Active build profile: " + (bp != null ? bp.name : "none (platform default)"));
#endif
#if UNITY_6000_3_OR_NEWER && !UNITY_6000_4_OR_NEWER
        sb.AppendLine("Render Graph Compatibility Mode: hidden in 6.3; URP_COMPATIBILITY_MODE define set = " +
            PlayerSettings.GetScriptingDefineSymbols(UnityEditor.Build.NamedBuildTarget.Android).Contains("URP_COMPATIBILITY_MODE"));
#elif UNITY_6000_0_OR_NEWER && !UNITY_6000_3_OR_NEWER
        var rg = GraphicsSettings.GetRenderPipelineSettings<
            UnityEngine.Rendering.Universal.RenderGraphSettings>();
        sb.AppendLine("Render Graph Compatibility Mode: " +
            (rg != null && rg.enableRenderCompatibilityMode));
#elif UNITY_6000_4_OR_NEWER
        sb.AppendLine("Render Graph Compatibility Mode: removed in 6.4+");
#else
        sb.AppendLine("Render Graph: not available before 6.0 (URP 12/14)");
#endif
        Debug.Log(sb.ToString());
    }
}
```

2. **On device**, log `SystemInfo.graphicsDeviceName` once at startup
   (`Debug.Log(SystemInfo.graphicsDeviceName);`) and read it with
   `adb logcat -s Unity`. Meta names Adreno 650 (Quest 2) and Adreno 740
   (Quest 3/3S); Qualcomm's XR2 Gen 2 brief gives no model number, so the
   string on each device is a known unknown [verify on device].
3. **Meta Quest build profile active?** 6.1+: *File > Build Profiles*; check
   the active profile is "Meta Quest". The 6.5+ Quest shader optimizations
   only switch on under it (U1-036).
4. Look up each fact in [references/feature-matrix.md](references/feature-matrix.md).
   Read it whenever a question names a feature, a patch number or a plugin
   version; the body below keeps only the lead facts.

Result: a one-line stack string, e.g. `6000.3.25f1 / URP 17.3 / OpenXR 1.15.1 /
Vulkan / RG on`. Every answer from this skill should repeat that string.

## Key numbers

Version floors and dates (all `[doc]`, access 2026-09-24):

| Fact | Value | Applies to | Source |
| --- | --- | --- | --- |
| Meta's Unity floor | 6000.0.66f2 or later; 6.1+ recommended | all Quest, Meta XR SDK path | U1-008, Meta unity-project-setup |
| Meta's OpenXR path | Unity OpenXR Plugin 1.15.1 recommended; needs Unity 6+ and Meta XR SDK v74+ | Unity ≥ 6000.0 | U1-009 |
| Oculus XR plugin | deprecated by Meta (4.5.1 rec., "Unity 2022 or later", SDK ≤ v73); deprecated by Unity 6000.5.0b4, not supported on 6.5/6.6 | 2022.3-6.4 | U1-009, U1-091 |
| OpenXR parity with Oculus XR | since OpenXR Plugin 1.14 (Meta) | Unity ≥ 6000.0 | U1-092 |
| 6.0 LTS | ends Oct 2026; latest 6000.0.84f1 (2026-09-16) | 6.0 | U1-004, QUEST-GF1-001 |
| 6.3 LTS | standard support to Dec 2027 (+1 yr Enterprise/Industry); latest 6000.3.25f1 | 6.3 | U1-003, QUEST-GF1-001 |
| 6.6 | current release, 6000.6.3f1; supported only until 6.7 ships | 6.6 | U1-001 |
| 6.1 / 6.2 / 6.4 / 6.5 | no more patches (last: 6000.1.17f1, 6000.2.15f1, 6000.4.12f1, 6000.5.11f1) | those streams | U1-005 |
| 2021.3 / 2022.3 | out of public support (CVE-2025-59489 advisory); last public 2021.3.45f2, 2022.3.62f3; paid xLTS only | URP 12 / URP 14 | UNITY-GF2-005, U1-006, U1-007 |
| 6.7 | beta only (6000.7.0b2, 2026-09-23); LTS targeted end of 2026 | 6.7 | U1-002, UNITY-GF2-006, QUEST-GF1-002 |
| URP mapping | 2021.3=12.1, 2022.3=14.0, 6.0=17.0 ... 6.5=17.5, 6.6=17.6 (inferred) | all | U1-010 |
| Meta Quest build profile defaults | Vulkan, min API 29, target API 32, IL2CPP, ARM64, SPI, aniso Per Texture | Unity ≥ 6000.1 | U1-053 |
| Engine min Android API | 6.0: 23, 6.3: 25, 6.5: 26 (23-25 warn) | 6.x | U1-097 |
| GLES minimum | ES 3.1 from 6.6 | Unity ≥ 6000.6, `GLES` | U1-094 |

Lead availability facts (details and patch numbers in the reference):

- **Render Graph** is default in 6.0; upgraded projects land in Compatibility
  Mode. Compatibility Mode is hidden behind `URP_COMPATIBILITY_MODE` in 6.3 and
  removed in 6.4 (U1-023, U1-025/026, U1-C5 resolved: both true).
- **GRD and GPU occlusion culling**: 6.0+, `Vulkan` only (GLES n/a: needs a
  compute-capable non-GLES API), Forward+ (Deferred+ allowed 6.1+) (U3-032,
  U1-095, X-C9). GPU occlusion was broken on 6.5.0-6.5.7 (U1-020).
- **Dynamic batching** is obsolete in 6.6 (U1-022).
- **On-tile post-processing**: 6.3 XR-only on Vulkan; 6.5 all platforms and
  requires Tile-Only Mode. **Tile-Only Mode** exists only from 6.5 (U2-074,
  U2-025, X-C10).
- **Quest shader optimizations** (`UNITY_PLATFORM_META_QUEST`): 6.5+ only, not
  in 6.0 or 6.3 LTS (X-C7, QUEST-GF2-011).
- **STP**: not supported in XR in any version (U1-042).
- **Vulkan GSC warmup fix** (UUM-121231): conflict X-C1, see Pitfalls.

Frame budgets for context: 72 Hz = 13.9 ms, 90 Hz = 11.1 ms, 120 Hz = 8.3 ms
(arithmetic). No version choice has a published Quest ms delta of its own;
features it unlocks are measured in their owning skills.

## Fixes, ranked by payoff ÷ effort

Version choices change frame time only through the features and fixes they
unlock. Where the dossier has no number, measure with the verify protocol.

### 1. Put new or long-lived Quest projects on the latest 6.3 LTS patch

- **Change:** Unity Hub > install the newest 6000.3.x (6000.3.25f1 on
  2026-09-24). Use the Meta Quest build profile and the Unity OpenXR Plugin
  (1.15.1+).
- **Why:** meets Meta's floor and recommendation (U1-008), supported to Dec
  2027 (U1-003), and carries Render Graph-only features Quest uses: XR on-tile
  post-processing (U2-074), automatic viewport dynamic resolution with OpenXR
  1.16+ (U2-048), Multiview Render Regions (6.1+, Render Graph from 6.3;
  U3-050), Shader Build Settings keyword overrides (U3-074).
- **Effect:** average GPU time only through the features adopted (MVRR: Meta's
  typical 3-8% when GPU-bound, Q2-027 / Q4-074 [doc] [verify on device]);
  variance through continued patch coverage of Quest regressions (U1-004).
- **Cost/side effects:** Gradle 9.1.0 / AGP 9.0.0 can break old .aar plug-ins
  (U1-098); 6000.3.14f1 changed the Meta Quest profile's quality defaults
  (U1-055).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 6000.3` `URP 17.3` `Vulkan`.
  **Goal:** Throughput + Consistency.

### 2. On 6.0: be at ≥ 6000.0.66f2 now, plan the 6.3 move before Oct 2026

- **Change:** update to the latest 6000.0.x patch; schedule the 6.3 upgrade.
  The 6.0 practical floor from regressions (about 6000.0.52f1) is owned by
  `unity-perf:unity-upgrade-risks`.
- **Effect:** Consistency (patch coverage). Several Quest fixes exist only on
  6.3+ (U1-004 notes).
- **Cost:** none for the patch; the 6.3 move needs a re-measure.
- **Tags:** `Unity 6000.0` `URP 17.0` `Quest 2` `Quest 3/3S`. **Goal:** Consistency.

### 3. Pick 6.6 only when a 6.5+/6.6 feature pays for the short support window

- **Change:** install the latest 6000.6.x (6000.6.3f1) with the Meta Quest
  build profile active.

Justified when the project needs any of:
- Quest shader optimizations in URP Lit/SimpleLit/Shader Graph and SRP library
  functions (6.5+; U3-066). Unity publishes no ms figure (U1-036).
- Tile-Only Mode with its validation (6.5+; U2-025).
- Depth input attachment instead of a copied depth texture (6.6, DX12/Vulkan;
  U2-079) `Vulkan`.
- Shader Constant Defines per build profile, no extra variants (6.6; U3-075).
- AppSW UI/transparent/TMP motion vectors (6000.5.0b1, 6000.6.0b6; U1-070);
  AppSW needs Vulkan (Q3-064/065) `Vulkan`.

- **Effect:** Throughput (GPU) from the features; no published Quest number
  for any of them, measure per the owning skill. Variance: no change expected
  beyond patch coverage, which ends when 6.7 ships (U1-001).
- **Cost:** 6.6 is an Update release, supported only until 6.7 ships (U1-001);
  6.5 is already unpatched (U1-005). Dynamic batching obsolete (U1-022); GLES
  minimum 3.1 (U1-094); Oculus XR unsupported (U1-091); custom shaders calling
  two-argument `DistanceAttenuation` fail on 6.6 Quest builds (U1-038, detail
  in `unity-perf:unity-upgrade-risks`). If on 6.5, be at ≥ 6000.5.8f1 or GPU
  occlusion costs GPU time for no gain (U1-020).
- **Tags:** `Unity ≥ 6000.5` / `Unity ≥ 6000.6` `URP 17.5+` `Quest 2`
  `Quest 3/3S` (`Vulkan` only where marked above).
  **Goal:** Throughput.

### 4. Get off 2021.3 / 2022.3 when a needed fix or feature is 6.x-only

- **Change:** plan 2022.3 to 6.3 LTS together with the Oculus XR to OpenXR
  switch and a Meta XR SDK major bump (U1-009 notes). Migration steps:
  `unity-perf:unity-upgrade-risks`; plugin choice: `quest-perf:quest-sdk-choices`.
- **Why:** public 2021.3/2022.3 builds get no further engine or Quest fixes
  (UNITY-GF2-005). Missing entirely: Render Graph, GRD, GPU occlusion, GSC,
  Build Profiles, SRP Foveation, MVRR, on-tile post (reference tables B-D).
  Minimum: a title still on 2021.3.45f1 / 2022.3.62f1 or earlier should take
  the CVE patch build (UNITY-GF2-005).
- **Effect:** Consistency (GSC for PSO hitches; patch coverage) and Throughput
  (Meta: SRP Foveation often 20-30% faster than Legacy foveation with post,
  deferred or multi-pass rendering, U1-085 [doc] vendor claim, no method
  published [verify on device]).
- **Cost:** a full re-baseline; Compatibility Mode is on after the upgrade
  until turned off (U1-023).
- **Tags:** `Unity 2021.3` `Unity 2022.3` to `Unity ≥ 6000.3`. **Goal:** Both.

### 5. Adopt the Meta Quest build profile (6.1+)

- **Change:** *File > Build Profiles > Meta Quest*, then *Switch Profile*.
- **Why:** it is the gate for the 6.5+ Quest shader optimizations and sets
  Vulkan, ARM64, IL2CPP, SPI (U1-053, U1-036); 6.2+ adds thin LTO for Quest
  (U1-054, no published number).
- **Effect:** Throughput via shader optimizations and LTO. Avg GPU/CPU ms may
  drop (not quantified; U1-036, U1-054); no expected effect on variance.
- **Quality cost:** 6000.3.0a5+ Mobile quality default turns SSAO off (U1-055).
- **Side effects:** silently switches the graphics API and XR plugin on an
  upgraded project; check both before comparing performance (U1-053).
- **Tags:** `Unity ≥ 6000.1` `Quest 2` `Quest 3/3S`. **Goal:** Throughput.

### 6. Turn off Render Graph Compatibility Mode on 6.0-6.2

- **Change:** *Project Settings > Graphics > Render Graph > Compatibility Mode
  (Render Graph Disabled)* off (6.0-6.2); on 6.3 it is already read-only false unless the
  `URP_COMPATIBILITY_MODE` define is set (U1-025). Port custom passes to
  `RecordRenderGraph` first (how: `unity-perf:unity-render-graph-tiling`).
- **Why:** GPU occlusion culling, automatic viewport dynamic resolution, MVRR
  (6.3+) and Unity-native AppSW all require Render Graph (U3-038, Q3-059,
  U3-050, Q3-065).
- **Effect:** availability only; the frame-time effect belongs to the
  features. Avg/variance: none by itself (availability only).
- **Cost/side effects:** no visual change; any custom ScriptableRenderPass
  without `RecordRenderGraph` stops rendering (U1-026), so port first.
- **Tags:** `Unity 6000.0-6000.2` `URP 17.0-17.2` `Quest 2` `Quest 3/3S`
  `Vulkan`. **Goal:** Both.

### 7. Keep 6.7 off shipping branches

- 6.7 is beta (6000.7.0b2). Test on a branch only; re-read its What's New and
  Upgrade Guide at LTS for GSC, Quest shader optimizations, dynamic batching
  and MVRR (UNITY-GF2-006).
- **Effect:** Consistency only: avoids beta regressions; no Throughput claim
  is made for 6.7 (Decision 40).
- **Cost:** none; test on a branch only.
- **Tags:** `Unity 6000.7 (beta)` `Quest 2` `Quest 3/3S`. **Goal:** Consistency.

## Verify

- **After a version or profile change:** re-run the Version Report; the stack
  string must match the intended target. Confirm the Graphics API list starts
  with Vulkan if a Vulkan-only feature is expected (GRD, GPU occlusion, on-tile
  post, MVRR, depth input, AppSW, automatic viewport dynamic resolution
  (Q3-059)).
- **Feature actually active, not silently fallen back:** Render Graph Viewer on
  device (6.3+) shows the on-tile pass reading via framebuffer fetch ("F") with
  memoryless attachments (U2-077); GRD draws show as "Hybrid Batch Group" in
  the Editor Frame Debugger (U3-035; the Frame Debugger does not support Quest
  devices, X-C2).
- **Performance:** same scripted route, fixed CPU/GPU levels, 10 minutes before
  and after, OVR Metrics GPU/CPU ms and stale frames per minute (protocol:
  `unity-perf:unity-upgrade-risks`, tools: `quest-perf:quest-profiling-toolkit`).
  No published number predicts the delta of an engine move itself; expect the
  delta only from features switched on. For 20-30 minute thermal behaviour use
  `quest-perf:quest-levels-thermal`.

## Pitfalls and myths

- **"Update the URP package" on Unity 6.** URP, SRP Core and Shader Graph are
  locked to the Editor from 6.0; every URP fix comes with an Editor patch
  (U1-011).
- **"We upgraded to Unity 6 but got no Render Graph gains."** Upgraded projects
  start in Compatibility Mode (U1-023).
- **"6.3 LTS has the Quest shader optimizations."** No: 6.5+ only. U2-056 dates
  them to 6.1+; U1-036/U3-066 and the manual page (absent in 6.4 and earlier)
  say 6.5 (X-C7, resolved: profile 6.1+, optimizations 6.5+).
- **Orthographic cameras** need a keyword override under the 6.5+ Quest
  optimizations; spelling conflict X-C8 (manual `_META_QUEST_ORTHO_PROJ` vs
  master Lit.shader `META_QUEST_ORTHO_PROJ`): see
  `unity-perf:unity-shader-authoring`.
- **"Enable Tile-Only Mode" on 6.3/6.4.** It does not exist there (X-C10). On
  6.5+ on-tile post without Tile-Only Mode falls back to texture sampling with
  no bandwidth saving (U2-075).
- **STP for Quest.** Unity's e-book path (URP Asset > Quality > Upscaling
  Filter > STP, UNITY-GF1-013) has no XR caveat; the XR compatibility table
  marks STP "No", and it needs compute and TAA (U1-042).
- **GRD on a GLES build** is silently unavailable (U3-032). Even on Vulkan it
  adds GPU work and can slow a GPU-bound app (U3-034); see
  `unity-perf:unity-draw-calls-batching`.
- **"Oculus XR cannot run on Unity 6."** Meta's page says "Unity 2022 or later"
  with SDK ≤ v73; it runs on 6.0-6.4 but caps the SDK and is deprecated; Unity
  drops it from 6.5 (U1-C3, resolved: use OpenXR on 6.x).
- **Vulkan GSC warmup on 6.0/6.3 LTS (conflict X-C1, unresolved).** U1-047:
  UUM-121231 "Fixed GraphicsStateCollection warmup for Vulkan" appears only in
  6000.4.0a4, no LTS backport found, so LTS warmup may not remove hitches.
  U3-091: that line was a 6.4-alpha-only regression and the LTS lines are
  safe. Do not pick a side; measure cold-vs-warm first-use stale frames per
  `unity-perf:unity-shader-hitches` [verify on device].
- **Forward+ in XR on 2022.3 (U1-C4, unresolved).** 6.0 lists XR support for
  Forward+ as new; 2022.3.16f1 already had Forward+ foveation. Test in stereo
  before relying on it; prefer 6.x.
- **"Use 6.1/6.2/6.4/6.5, they're newer than 6.3."** Unpatched (U1-005).
- **"2022.3 LTS is still supported."** Only the paid xLTS stream is; the
  public builds are out of support (UNITY-GF2-005).
- **Swapchain buffer count.** `vulkanNumSwapchainBuffers` was ignored before
  6000.0.83f1 / 6000.3.24f1 / 6000.6.0f1; leave the default (X-C5);
  see `unity-perf:unity-urp-settings`.
- **FrameTimingManager GPU time on XR** arrives with 6.6 (U1-057) while the
  manual still says Partial (X-C3); see `unity-perf:unity-profiling-workflow`.
- **HDRP** is not used on Quest; one-line note in `unity-perf:unity-urp-settings`.

## Sources

All accessed 2026-09-24.

- https://services.api.unity.com/unity/editor/release/v1/releases [doc] (U1-001, U1-005..007, UNITY-GF2-006)
- https://unity.com/releases/unity-6/support [doc] (U1-003, U1-004, QUEST-GF1-001)
- https://unity.com/topics/render-pipelines-strategy-for-2026 [doc] (U1-002)
- https://unity.com/security/sept-2025-01 [doc] (UNITY-GF2-005)
- https://github.com/endoflife-date/endoflife.date/blob/master/products/unity.md [community] (UNITY-GF2-005 notes)
- https://developers.meta.com/horizon/documentation/unity/unity-project-setup/ [doc] (U1-008, U1-009)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc] (U1-085, U1-092)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc] (Q2-027 / Q4-074)
- https://developers.meta.com/horizon/documentation/unity/unity-asw/ [doc] (Q3-064)
- https://raw.githubusercontent.com/Unity-Technologies/Graphics/6000.5/staging/Packages/com.unity.render-pipelines.universal/package.json [doc] (U1-010)
- https://docs.unity3d.com/6000.0/Documentation/Manual/urp/upgrade-guide-unity-6.html [doc] (U1-011, U1-023)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity63.html [doc] (U1-025)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity64.html [doc] (U1-026)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html [doc] (U1-026, U1-097)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc] (U1-022, U1-094)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity62.html [doc] (U1-054)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc] (U1-021, U1-051, U1-057, U1-073)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html [doc] (U1-053)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html [doc] (U1-036, U3-066, QUEST-GF2-011, X-C7, X-C8)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html [doc] (U1-042, U1-058)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html [doc] (U3-032)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html [doc] (U3-034, U3-035)
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-graphics-on-tile-post-processing.html [doc] (U2-074)
- https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-post-processing.html [doc] (U2-075)
- https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html [doc] (U2-025)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html [doc] (U2-077)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-multiview-render-regions.html [doc] (U3-050)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-prerequisites.html [doc] (Q3-065)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/automaticdynamicresolution.html [doc] (Q3-059)
- https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html [doc] (U3-074, U3-075)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html [doc] (U1-098)
- https://unity.com/releases/editor/whats-new/6000.4.0a4 [doc] (U1-047, X-C1)
- https://unity.com/releases/editor/whats-new/6000.0.0 [doc] (U3-091, X-C1)
- https://unity.com/releases/editor/whats-new/6000.5.0b4 [doc] (U1-091)
- https://unity.com/releases/editor/whats-new/6000.5.8f1 [doc] (U1-020)
- https://unity.com/releases/editor/whats-new/6000.6.0b1 [doc] (U1-038)
- https://unity.com/releases/editor/whats-new/6000.3.14f1 [doc] (U1-055)
- https://unity.com/releases/editor/whats-new/6000.0.83f1 [doc] (U1-068, X-C5)
- https://unity.com/releases/editor/whats-new/6000.7.0b2 [doc] (UNITY-GF2-006)
- https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf [doc] (no Adreno model number)
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc] (Adreno 650 / 740 naming)
- https://cdn.bfldr.com/S5BC9Y64/at/3mp8w3wk36k2k6mmj5pbbr/Optimize_your_game_performance_for_mobile__XR__and_the_web_in_Unity_Unity_6_edition_e-book.pdf [doc] (UNITY-GF1-007, UNITY-GF1-013; STP path pp. 60-61, no XR caveat)
