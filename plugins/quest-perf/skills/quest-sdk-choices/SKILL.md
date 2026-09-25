---
name: quest-sdk-choices
description: "Choose Meta and Unity XR plugins and SDK settings for performance on Quest 2/3/3S: OpenXR plugin vs deprecated Oculus XR plugin, Meta XR Core SDK version pinning, OpenXR Meta Quest Support toggles, Optimize Buffer Discards (OBD), Offscreen Rendering Only, the manifest performance-flag inventory, Project Setup Tool (PST) rules and CLI, and deprecated options such as Shader Binary Cache. Use when picking an XR stack or when a Meta SDK toggle may cost or save frame time or memory. Migration steps after a Unity upgrade: unity-perf:unity-upgrade-risks."
---

# quest-sdk-choices

Plugin stack, Meta XR SDK settings, OBD, the manifest-flag inventory, PST, and
deprecated features. Goals: **Throughput** (features only the OpenXR stack ships)
and **Consistency** (memory headroom from OBD / Offscreen Rendering Only; hitch
risk from deprecated shader-cache paths).

Read [references/manifest-flags.md](references/manifest-flags.md) when auditing
a merged AndroidManifest or when a `com.oculus.*` / `horizonos.*` key appears in
a build and you need its owner skill, device scope and source. This skill ships
no scripts.

## When to use / when not

Use when:
- Starting or re-platforming a Quest project and choosing Oculus XR vs Unity OpenXR, and which Meta XR Core SDK line.
- Auditing Project Settings > XR Plug-in Management > OpenXR > Meta Quest Support toggles for frame-time or memory cost.
- Checking which `com.oculus.*` manifest entries the build actually carries, or which deprecated SDK features a project still relies on.
- Encoding team perf rules as PST tasks and gating CI on the PST report.

When not:
- "Which Unity version has feature X", Meta minimum Unity versions: `unity-perf:unity-version-matrix`.
- Migrating an existing project Oculus XR to OpenXR after an Editor upgrade, regressions, patch floors: `unity-perf:unity-upgrade-risks`.
- GLES vs Vulkan decision, UUM-93226 detail, API A/B: `gles3-perf:gles-vs-vulkan`.
- Boost, dual-core mode, level trading semantics, XrPerformanceSettingsFeature: `quest-perf:quest-levels-thermal`.
- Latency Optimization, Late Latching, FrameSync / Phase Sync: `quest-perf:quest-frame-pacing`.
- Symmetric Projection, MVRR, FFR / SRP Foveation, dynamic resolution: `quest-perf:quest-resolution-foveation`.
- AppSW and its motion-vector format: `quest-perf:quest-appsw`.
- Passthrough / Depth API / PCA costs: `quest-perf:quest-mr-costs`.
- Low Overhead Mode (GLES): `gles3-perf:gles-driver-overhead`.
- Shader warm-up replacing SBC: `unity-perf:unity-shader-hitches`.
- Unknown bottleneck: start at `quest-perf:quest-triage`.

## Diagnose first

This skill's "bottleneck" is a wrong or stale configuration. Establish the
actual stack and flags before changing anything.

1. **Which stack and SDK line** (repo root, Git Bash):
   ```sh
   grep -E '"com\.(unity\.xr\.(oculus|openxr|meta-openxr)|meta\.xr\.sdk\.[a-z]+)"' Packages/manifest.json
   grep -E '^m_EditorVersion' ProjectSettings/ProjectVersion.txt
   ```
   `com.unity.xr.oculus` present on Unity ≥ 6000.5 = unsupported plugin (U1-091). `com.meta.xr.sdk.core` ≤ 73 with OpenXR = SDK too old for Meta's OpenXR path (Q4-052, U1-009).
2. **What the build really declares** (merged manifest, not your template):
   ```sh
   aapt2 dump xmltree --file AndroidManifest.xml Builds/app.apk \
     | grep -A1 -E 'com\.oculus|horizonos|glEsVersion|profileable|QUAD_VIEWS'
   ```
   `aapt2` prints `android:name` and `android:value` on separate `A:` lines; `-A1` keeps the `android:value` line that follows each `android:name` line (e.g. the `supportedDevices` string, `trade_cpu_for_gpu_amount`, `dualcorecpuset=true`). Compare against [references/manifest-flags.md](references/manifest-flags.md).
3. **Did the runtime accept the level flags** (per build, after launch):
   ```sh
   adb logcat -d | grep -E 'isCPUSingleThreadedBoost|tradeCpuForGpu'
   ```
   `CreateClient: Value of isCPUSingleThreadedBoost is 1` / `tradeCpuForGpu is <n>` confirm dual-core / trading reached the runtime (Q1-038, A1-031, A1-032). Value 0, or no line, while the manifest carries the flag: the runtime did not apply it. Check that OVRPlugin uses the OpenXR backend, which both features require (A1-031, A1-032). What logcat prints on the legacy backend is not documented [verify on device].
4. **PST status headless** (CI-safe; Core SDK v52+):
   ```sh
   Unity -batchmode -quit -projectPath <path> -logFile pst.log \
     -executeMethod OVRProjectSetupCLI.GenerateProjectSetupReport \
     -reportFile pst.json -buildTarget Android
   ```
   (Meta's page writes `-project`; `-projectPath` is Unity's documented flag.) Read `tasksStatus[]` (uid, group, message, level, isDone) (Q4-069). The default rule list is not published; diff the report of a blank project vs yours to see the effective rules for your SDK version (Q4-070).
5. **Memory attributable to eye buffers** (for OBD / Offscreen Rendering Only A/B): `adb shell dumpsys meminfo <package>` TOTAL PSS, same scene, same spot, toggle on vs off. PSS limits themselves: `quest-perf:quest-budgets-tiers`.

## Key numbers

| Fact | Value | Applies to | Source |
|---|---|---|---|
| OBD saving, 4x MSAA | ~90 MB per eye (180 MB both) at 1680x1760 | Quest 3/3S, Vulkan, both plugins | Q4-059, G1-038 [doc] |
| OBD saving, 4x MSAA | ~66 MB per eye at 1440x1584 | Quest 2, Vulkan | Q4-059, G1-038 [doc] |
| Offscreen Rendering Only saving | ~10-20 MB, quoted at 2064x2208 per eye | Quest 3, Vulkan, OpenXR, Unity 6.x | Q4-061, U1-090 [doc] |
| RG16f vs RGBA16f SpaceWarp MV | 4 vs 8 B/px; error under 0.5 px per Meta | OpenXR ≥ 1.14.0 with AppSW | Q4-062 [doc] |
| SRP Foveation vs Legacy | "often 20-30% faster" frame time for multi-pass pipelines (Meta claim) | Unity 6.x OpenXR | Q4-061 [doc] [verify on device] |
| OpenXR parity with Oculus XR | since OpenXR plugin 1.14 (Meta), OpenXR: Meta 2.1 (Unity) | Unity 6.x | U1-092, Q4-051 [doc] |
| Core SDK minimum Unity | v59-72: 2021.3.26f1; v74-201: 2022.3.15f1; v203+: 6000.0.66f2 | all | Q4-050 [doc] |
| Current Core SDK | 207.0.0 (npm 2026-09-24; downloads page says Sep 22) | all | Q4-049, Q4-C11 [doc] |
| Oculus XR last version | 4.5.5 (2026-07-19, adds deprecation warning) | Unity 2021.3-6.4 | Q4-051 [doc] |
| OpenXR minimum Editor | OpenXR 1.18.0-pre.1 needs 6000.0, so 2022.3 stops at ≤ 1.17.x | Unity 2022.3 | Q4-052 [doc] [verify on device] |
| Meta-recommended OpenXR floor | Unity 6000.0.66f2+, 6.1+ recommended, SDK v74+ | Unity 6.x | Q4-052 [doc] |
| SBC pre-warm cut-off | 10 min per backend headset; 2 app versions processed | Store apps; Unity "may be processed" | QUEST-GF1-004 [doc] |

Frame-time deltas for plugin choice itself: **no published number**. No
like-for-like Oculus XR vs OpenXR before/after data exists (U1-093). Measure
with the same scene and route, OVR Metrics CSV `app_gpu_time_microseconds`,
CPU time and stale frames per minute, 10+ min, both builds on the same OS
(see `quest-perf:quest-profiling-toolkit`).

Stack decision table (Q4-050, Q4-051, Q4-052, U1-009, U1-091, U1-C3):

| Editor | Recommended stack | Core SDK ceiling | Note |
|---|---|---|---|
| 2021.3 | Oculus XR (maintenance only) | v72 | Upgrade path is the real fix |
| 2022.3 | Oculus XR, or OpenXR ≤ 1.17.x | v73 with Oculus XR (Meta-validated); v201 by Editor minimum (Q4-050) | Meta's OpenXR path wants Unity 6 + SDK v74+; OpenXR ≤ 1.17.x on 2022.3 is outside Meta's recommendation [verify on device] |
| 6.0-6.4 | Unity OpenXR + OpenXR: Meta | none (v203+ needs 6000.0.66f2) | Oculus XR still works but caps SDK at v73 |
| 6.5-6.6 | Unity OpenXR only | none | Oculus XR "no longer supported" on this Editor |

## Fixes, ranked by payoff ÷ effort

### 1. Turn on Optimize Buffer Discards (Vulkan)
- **Change:** OpenXR: Project Settings > XR Plug-in Management > OpenXR (Android) > Meta Quest Support (cog) > Optimize Buffer Discards. Oculus XR: XR Plug-in Management > Oculus (Android) > Optimize Buffer Discards (Q4-055, Q4-056). First shipped Oculus XR 1.5.0 / OpenXR 1.10.0 (Q4-058).
- **Effect:** memory, not average frame time: MSAA attachments become lazily allocated (Q4-059). ~180 MB (Quest 3, 2 × 90 MB) / ~132 MB (Quest 2, 2 × 66 MB; 132 MB both eyes per Meta's page) of PSS headroom at 4x MSAA lowers lmkd-kill and streaming-hitch risk (Consistency). It is also Unity's recommended workaround for UUM-93226 Vulkan buffer-copy slowdown (G1-051, [community] tracker note), which is a Throughput effect; OS-side fix unconfirmed (GLES3-GF2-002), so the workaround may still be needed; details in `gles3-perf:gles-vs-vulkan`. The gles3 dossier also lists OBD as a prerequisite for AppSW (G1-038 note).
- **Cost / conflict (Q4-C7):** Meta's OpenXR page presents it as free; the Oculus XR manual warns it can break effects that sample depth, such as camera stacking. Test every depth-sampling pass (soft particles, depth-based fog, stacked overlay cameras) with it on.
- **Tags:** `Quest 2` `Quest 3/3S` `Vulkan` `MSAA on` `Oculus XR ≥ 1.5.0` `OpenXR ≥ 1.10.0`. **Goal:** Consistency (memory); Throughput (UUM-93226 workaround).

### 2. Pick the OpenXR stack on Unity 6.x
- **Change:** Packages: `com.unity.xr.openxr` + `com.unity.xr.meta-openxr` + Meta XR Core SDK v74+; remove `com.unity.xr.oculus`; enable the Meta Quest feature group under OpenXR (Android). Unity 6.1+: use the Meta Quest build profile, which installs OpenXR as required and lets Player/Graphics/Quality be overridden per Quest (Q4-054).
- **Effect:** no direct frame-time delta is published (U1-093). The payoff is access: Dynamic Foveation (OpenXR 1.18.0 only), `XR_META_tile_properties_hint` (1.17.0-pre.1+), `XrPerformanceSettings.SetPerformanceLevelHint` (1.11.0), URP AppSW (1.15.0), MVRR All Passes (1.15.0-pre.2, Unity 6.2+) (Q4-058); dual-core mode and level trading need the OpenXR backend (A1-031, A1-032); Core SDK v203+ tooling needs 6000.0.66f2 (Q4-050, Q4-066). Unity 6.5+ applies Quest URP ShaderLibrary optimizations only with the Meta Quest build profile (QUEST-GF2-011; authoring detail in `unity-perf:unity-shader-authoring`).
- **Cost:** plugin swap changes who owns foveation, depth submission, eye-buffer format and frame timing; settings do not carry over, re-baseline (U1-093). GLES: the Unity OpenXR plugin lists Vulkan only for Quest, so the OpenXR path implies Vulkan (G1-024 / G2-093); the Oculus XR GLES path is deprecated with the plugin from 6.5. Decide the API first in `gles3-perf:gles-vs-vulkan`. Migration steps: `unity-perf:unity-upgrade-risks`.
- **Conflicts:** Q4-C12 Unity says deprecated from 6.5 with no removal date; Meta says "scheduled for removal". Q4-C5 Meta's page still recommends OpenXR 1.15.1 / Oculus XR 4.5.1 while Unity ships OpenXR 1.18.0 and Oculus XR 4.5.5; use Unity's current package and re-verify on device. U1-C3: Meta's stated Oculus XR range is "Unity 2022 or later" with SDK ≤ v73, so it is not excluded on 6.0-6.4 by version, only by SDK ceiling.
- **Tags:** `Unity ≥ 6000.0` (floor 6000.0.66f2, 6.1+ recommended) `URP 17` `Vulkan` `Quest 2` `Quest 3/3S`. **Goal:** Throughput and Consistency (enables features owned elsewhere).

### 3. Set the OpenXR page to Meta's reference values
Fixes 3-4 presuppose the OpenXR stack (Fix 2); on Oculus XR only Fix 1 and Fix 5-7 apply.

Project Settings > XR Plug-in Management > OpenXR (Android) (Q4-055, Q4-061, U1-092):

| Setting | Value | Why | Owner for depth |
|---|---|---|---|
| Render Mode | Multi-view | halves draw-call dispatch vs multi-pass (Q4-065); required by Depth API and Symmetric Projection | `unity-perf:unity-draw-calls-batching` |
| Depth Submission Mode | None, unless AppSW or composition needs depth | depth submission costs a GPU resolve plus compositor work (Q4-061); no ms published | `quest-perf:quest-appsw` |
| Foveated Rendering API | SRP Foveation (Unity 6+) | see Key numbers | `quest-perf:quest-resolution-foveation` |
| Use OpenXR Predicted Time | On (SDK v83+; default from OpenXR 1.17.0) | Meta reference | `quest-perf:quest-frame-pacing` |
| Additional Graphics Queue | Off | Meta: adds CPU overhead from queue management with no measurable GPU gain on Quest; no ms published (unity-openxr-settings, refetched 2026-09-24) | measure |
| Latency Optimization | Meta: Prioritize Input Polling | conflicts with Unity default (U5-C2) | `quest-perf:quest-frame-pacing` |
| Offscreen Rendering Only | On (Vulkan) | ~10-20 MB | see fix 4 |
| Space Warp MV format (Meta Quest Support) | RG16f | half MV bandwidth vs RGBA16f (Q4-062) | `quest-perf:quest-appsw` |

- **Effect:** Depth Submission None lowers average GPU time by one resolve and compositor depth work (no number; measure `app_gpu_time_microseconds` A/B). The rest are latency, memory or feature gates.
- **Tags:** `Unity ≥ 6000.0` `OpenXR ≥ 1.14` `Vulkan` (Offscreen Rendering Only, OBD, Symmetric Projection, Late Latching) `Quest 2` `Quest 3/3S`. **Goal:** Throughput (depth submission, multiview), Throughput (CPU) (Additional Graphics Queue off) and Consistency (latency, memory).

### 4. Turn on Offscreen Rendering Only
- **Change:** OpenXR (Android) page > Offscreen Rendering Only = on (Q4-055, Q4-061).
- **Effect:** ~10-20 MB less memory (U1-090); no frame-time effect published.
- **Cost:** no quality cost documented; Vulkan-only.
- **Conflict (Q4-C3):** Meta quotes the saving at 2064x2208 per eye (panel resolution), while the default Quest 3 eye buffer is 1680x1760; the saving at your eye-buffer size is unpublished. Measure TOTAL PSS A/B.
- **Tags:** `Quest 3` (only device quoted; `Quest 2` `Quest 3S` [verify on device]) `Vulkan` `OpenXR` `Unity ≥ 6000.0`. **Goal:** Consistency (memory).

### 5. Encode perf rules as PST tasks and gate CI on the report
- **Change:** open PST via Window > Meta > Tools > Project Setup Tool (or Edit > Project Settings > Meta XR). Cog: enable "Required throw errors" so failing Required tasks block builds, and "Produce Report on Build" (Q4-067). Add team rules with `OVRProjectSetup.AddTask` (Q4-068); the task ID is a hash of `message`, so messages must be unique, and tasks cannot be removed once added. Put this in an `Editor` folder (asmdef users: reference the Meta XR Core SDK editor assembly). Untested here; AddTask: Core SDK v50+; PST UI: v59+ (Oculus Integration v49-57).
  ```csharp
  // Assets/Editor/QuestPerfSetupTasks.cs
  // Meta's page types these as OVRConfigurationTask.TaskLevel/TaskGroup;
  // recent SDK sources expose them as OVRProjectSetup.TaskLevel/TaskGroup.
  // Use whichever resolves on your Core SDK version [verify on device].
  using System.Linq;
  using UnityEditor;
  using UnityEngine.Rendering;

  [InitializeOnLoad]
  internal static class QuestPerfSetupTasks
  {
      static QuestPerfSetupTasks()
      {
          // Only after the GLES-vs-Vulkan A/B (gles3-perf:gles-vs-vulkan) chose Vulkan.
          OVRProjectSetup.AddTask(
              level: OVRProjectSetup.TaskLevel.Required,
              group: OVRProjectSetup.TaskGroup.Rendering,
              platform: BuildTargetGroup.Android,
              message: "[quest-perf] Android Graphics APIs must be exactly [Vulkan] (OBD, Offscreen Rendering Only, Symmetric Projection are Vulkan-only)",
              isDone: _ => !PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.Android)
                           && PlayerSettings.GetGraphicsAPIs(BuildTarget.Android)
                                            .SequenceEqual(new[] { GraphicsDeviceType.Vulkan }),
              fix: _ =>
              {
                  PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
                  PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.Vulkan });
              },
              fixMessage: "Set Android Graphics APIs to [Vulkan]");

  #if UNITY_6000_0_OR_NEWER
          OVRProjectSetup.AddTask(
              level: OVRProjectSetup.TaskLevel.Recommended,
              group: OVRProjectSetup.TaskGroup.XR,
              platform: BuildTargetGroup.Android,
              message: "[quest-perf] Remove com.unity.xr.oculus on Unity 6.x; use Unity OpenXR + OpenXR: Meta (Oculus XR caps Meta XR SDK at v73)",
              isDone: _ => UnityEditor.PackageManager.PackageInfo
                               .FindForAssetPath("Packages/com.unity.xr.oculus/package.json") == null);
  #endif
      }
  }
  ```
  CI gate: run the CLI in Diagnose step 4 and fail the job when any `tasksStatus[]` entry with `level` Required has `isDone` false. Other rules worth encoding (from Q4-068's note): URP MSAA 4x, HDR off in MR scenes, Symmetric Projection on, Depth Submission None, no second passthrough layer; each rule's value is owned by its topic skill.
- **Effect:** none on frame time directly; it prevents regressions that would cost frame time or memory (Consistency across builds).
- **Cost:** PST's default rule list is unpublished (Q4-070); "Fix All" may apply defaults you did not choose. Review each fix. Meta's best-practices page (Q4-071) routes its advice through PST, but which items PST checks automatically is undocumented.
- **Tags:** `Core SDK ≥ v50` (AddTask; report on build ≥ v52; PST UI ≥ v59) `Unity 2021.3-6.6` `GLES` `Vulkan`. **Goal:** Consistency.

### 6. Audit the manifest-flag inventory every build
- **Change:** run Diagnose step 2 on the release APK and check each key in [references/manifest-flags.md](references/manifest-flags.md). Put hand-added keys in `Assets/Plugins/Android/AndroidManifest.xml` (custom main manifest) or let the SDK setting that owns them generate them (e.g. OVRManager "Processor Favor" writes `com.oculus.trade_cpu_for_gpu_amount`, A1-032; OpenXR "Target Devices" drives `com.oculus.supportedDevices`, Q2-083).
- **Effect:** a missing `quest3s` in `com.oculus.supportedDevices` makes a 3S report an older model and limits refresh rates (Q2-081, Q2-015); a flag without the OpenXR backend is ignored (logcat value stays 0 / flag not applied [verify on device]). Semantics of each flag live in its owner skill.
- **Cost:** none; hand-edited keys can drift from the SDK-generated values, so let the owning setting generate them.
- **Tags:** all devices, `GLES` `Vulkan`. **Goal:** Throughput and Consistency (depends on flag).

### 7. Retire deprecated paths
- **Shader Binary Cache (SBC):** doc page (updated Aug 7, 2026) carries a deprecation banner: no longer actively maintained, replacement in development (QUEST-GF1-004). Conflict QUEST-GF1-C2: Meta's GDC 2026 recap (Mar 10, 2026) still promotes SBC; the newer doc page wins. If `com.oculus.sbcpath` is in the manifest, leave it (no source says it has a cost or a benefit for Unity apps) but do not count on it for first-use hitches: Unity support was never guaranteed. Keep in-app PSO/shader warm-up (`unity-perf:unity-shader-hitches`, `gles3-perf:gles-shader-binaries`). **Replacement: not confirmed by any source** (Known unknown).
- **Low Overhead Mode (GLES):** Oculus XR only, no OpenXR equivalent (Q4-058); it disappears with the plugin. See `gles3-perf:gles-driver-overhead`.
- **Oculus XR "Use Recommended MSAA Level" (OVRManager):** Built-in RP only; for URP set MSAA in the URP asset (Q4-064). Level choice: `unity-perf:unity-urp-settings`.
- **Effect:** none of these change average frame time directly, except that losing Low Overhead Mode on migration can raise GLES CPU time (no published number; measure render-thread time A/B with `quest-perf:quest-profiling-toolkit`).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3-6.6`. **Goal:** SBC = Consistency (first-use hitches); Low Overhead Mode = Throughput (GLES CPU, lost on migration); Use Recommended MSAA = Throughput and Consistency via the correct URP MSAA setting.

### 8. Unity 6.6: Adaptive Performance Basic provider for OpenXR
Unity 6.6's untethered-XR checklist says to enable it (Q4-053). Level behaviour and whether Horizon OS honours OpenXR level hints are owned by `quest-perf:quest-levels-thermal` (open question there).
- **Effect:** no published frame-time or variance effect.
- **Cost:** behaviour and level interaction undocumented [verify on device].
- **Tags:** `Unity ≥ 6000.6` `OpenXR`. **Goal:** Consistency [verify on device].

Core SDK v203+ also adds an "AI Runtime Optimizer Tool" and v205 an experimental "Hands Optimizer Tool"; no behaviour or cost documentation exists (Q4-066) [verify on device]. Whether this is the same product as the Runtime Optimizer is undocumented; tool usage: `quest-perf:quest-profiling-toolkit`.

## Verify

- **Stack:** `Packages/manifest.json` has no `com.unity.xr.oculus` (Unity 6.x); Core SDK version is within the Q4-050 row for your Editor.
- **OBD:** TOTAL PSS drops by roughly 132 MB (Quest 2, 2 × 66 MB) / 180 MB (Quest 3/3S) at 4x MSAA with the same scene (Q4-059); average GPU time should not rise. If the drop is near zero, MSAA is off or the API is GLES. If UUM-93226 was the motivation, GPU time and stale frames per minute should fall on Vulkan; magnitude unpublished, measure over 10+ min.
- **Offscreen Rendering Only:** PSS drop in the 10-20 MB range on Quest 3 (U1-090); other devices [verify on device].
- **Depth Submission None:** lower `app_gpu_time_microseconds` p50 vs the depth-submitting build; confirm AppSW / composition still behave.
- **Plugin switch:** p50/p95/p99 GPU and CPU frame time and stale frames per minute within noise of the old build or better, over a 20-30 min session on the same OS build (U1-093). Use `quest-perf:quest-profiling-toolkit` for the CSV analyzer.
- **Manifest flags:** every intended key present in `aapt2 dump`; `isCPUSingleThreadedBoost` / `tradeCpuForGpu` logcat lines match the manifest.
- **PST:** CLI report has zero Required tasks with `isDone: false`.

## Pitfalls and myths

- **"Oculus XR is faster / required for Quest features."** Meta and Unity both state parity since OpenXR plugin 1.14 (U1-092, Q4-051); new features ship only on OpenXR (G1-024). No measured delta either way exists (U1-093).
- **"Oculus XR can't run on Unity 6."** It runs on 6.0-6.4 but pins the Meta XR SDK at v73; Unity lists it as unsupported from 6.5 (U1-C3, U1-091).
- **Trusting Meta's pinned plugin versions.** Meta's page (May 2026) names OpenXR 1.15.1 / Oculus XR 4.5.1; Unity has shipped 1.18.0 / 4.5.5 (Q4-C5).
- **Upgrading Core SDK past your Editor's ceiling.** v203+ needs 6000.0.66f2; 2022.3 stops at v201, 2021.3 at v72 (Q4-050). Interaction SDK 207 still declares 2022.3.15f1 but cannot outrun Core.
- **OBD as universally free.** See Q4-C7; depth-sampling effects and camera stacking can break.
- **Expecting OBD / Offscreen Rendering Only on GLES.** Both are Vulkan-only (Q4-055, G1-038).
- **Setting dual-core or trading flags on the legacy OVRPlugin backend.** They need the OpenXR backend; confirm via logcat (A1-031, A1-032). Dual-core is Quest 2/Pro only; trading is Quest 3/3S only.
- **Relying on SBC for Unity first-use hitches.** Deprecated, Unity support not guaranteed (QUEST-GF1-004).
- **Keeping Phase Sync setup code.** Phase Sync API calls are no-ops on FrameSync OS builds (v203+) (Q2-071); owner `quest-perf:quest-frame-pacing`.
- **Relying on the FrameSync opt-out manifest value.** `com.oculus.enable_frame_sync=false` is [community]-only and may not exist (QUEST-GF1-C1). Owner: `quest-perf:quest-frame-pacing`.
- **"Target Devices = Quest 2 throttles Quest 3."** It does not; clocks are unchanged, but the headroom goes unused unless dynamic resolution or adaptive quality spends it (Q2-084).
- **Trusting "Fix All" in PST blindly.** Its rule list is unpublished per SDK version (Q4-070).

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc] (Q4-055, Q4-059, Q4-062, Q2-084, G1-038)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc] (Q4-061, U1-090, U1-092; Additional Graphics Queue rationale from the page, refetched)
- https://developers.meta.com/horizon/documentation/unity/unity-xr-plugin/ [doc] (Q4-051, Q4-052)
- https://developers.meta.com/horizon/documentation/unity/unity-project-setup/ [doc] (U1-009, U1-093)
- https://developers.meta.com/horizon/documentation/unity/unity-and-openxr-compatibility [doc] (U1-092)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc] (Q4-056, Q4-C7, G1-024)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html [doc] (Q4-051, Q4-058)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc] (Q4-052, Q4-058)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html [doc] (Q4-055, Q4-C8)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html [doc] (G2-055, Vulkan-only for Quest)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/whats-new.html [doc] (Q4-052)
- https://discussions.unity.com/t/oculusxr-package-deprecation/1717655 [doc] (Unity staff; Q4-051)
- https://unity.com/releases/editor/whats-new/6000.5.0b4 [doc] (U1-091)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html [doc] (Q4-054)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc] (Q4-053)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html [doc] (QUEST-GF2-011)
- https://npm.developer.oculus.com/com.meta.xr.sdk.core [doc] (Q4-049, Q4-050)
- https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/203.0/ [doc] (Q4-050, Q4-066)
- https://developers.meta.com/horizon/documentation/unity/unity-upst-overview/ [doc] (Q4-067 to Q4-070)
- https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ [doc] (Q4-071)
- https://developers.meta.com/horizon/documentation/unity/unity-ovrcamerarig/ [doc] (Q4-064)
- https://developers.meta.com/horizon/documentation/unity/enable-multiview/ [doc] (Q4-065)
- https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ [doc] (A1-031, A1-032, Q1-038)
- https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ [doc] (QUEST-GF1-004)
- https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ [doc] (QUEST-GF1-C2)
- https://developers.meta.com/horizon/essentials/framesync/ [doc] (Q2-071, QUEST-GF1-007)
- https://developers.meta.com/horizon/documentation/unity/os-compatibility-mode/ [doc] (Q2-081, Q2-083)
- http://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 [community] (G1-051)
- https://issuetracker.unity.com/api/v1.0/issues/1364 [community] (GLES3-GF2-002)
