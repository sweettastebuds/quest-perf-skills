# Player scripting settings for Quest, per Unity version

Read this when changing any CPU-side Player setting, when a menu path in SKILL.md
does not match your Unity version, or when you want the settings applied by a
build script. All sources accessed 2026-09-24. Settings owned elsewhere are named
with their owner.

## Settings table

| Setting | Path | Ship value on Quest | Versions | Goal | Source |
|---|---|---|---|---|---|
| Scripting Backend | Player > Other Settings > Configuration | IL2CPP (ARM64 requires it) | all | Throughput | U5-021 [doc] |
| Target Architectures | Player > Other Settings > Configuration | ARM64 only | all | Throughput | U5-021 [doc] |
| Enable Armv9 Security Features for Arm64 (PAC/BTI) | Player > Other Settings | off unless required; cost on Quest 3/3S unpublished [verify on device] | recent 6.x | Throughput | U5-021 [doc] |
| C++ Compiler Configuration | Player > Other Settings > Configuration | Master (longer builds); Release vs Master delta unpublished | 2021.3-6.6 | Throughput | U5-015 [doc] |
| IL2CPP Code Generation | 2021.3/2022.3: Build Settings; 6.x: Player settings | Faster runtime (2021.3/2022.3) / Optimize for runtime speed (6.x), the default | 2021.3-6.6 | Throughput | U5-016 [doc] |
| Managed Code Variant | Player settings (`PlayerSettings.SetManagedCodeVariant`) | Release for shipping; Instrumented or Checked for profiling builds (keeps ProfilerMarkers, RG Viewer, RG samplers) | 6.6+ | both (measurement) | U5-018 / U1-030 [doc] |
| Code Optimization "Maximum Size Reduction (with LTO)" | Build Settings | size levers; no runtime-speed data; prefer runtime-speed modes until measured | 6.6+ | none proven | U5-019 [doc] |
| Managed Stripping Level, Strip Engine Code | Player > Other Settings > Optimization | size levers; no per-frame CPU effect published | all | none proven | U5-019 [doc] |
| Use incremental GC | Player > Other Settings > Configuration | on (default); A/B off only when allocations ~0 B | 2019.1+ | Consistency | U5-005, U5-006 [doc] |
| Stack Trace (Log, Warning) | Player > Other Settings > Stack Trace | None (default ScriptOnly); keep ScriptOnly for Exception if needed | all | Throughput | U5-013 [doc] |
| Multithreaded Rendering | Player > Other Settings > Rendering | on; off only while debugging | all | Throughput | U5-039, A1-061 [doc] |
| Graphics Jobs | Player > Other Settings > Rendering | on only with MT rendering, main-thread-bound, Vulkan | 2022.3.35f1+ and 6.x (2021.3 unvalidated) | Throughput | A1-058, A1-062 [doc] |
| Graphics Jobs Mode | 6.x: Player settings (Native/Legacy/Split) or Vulkan Device Filtering Asset per device; 2022.3.35f1+: script only (Native/Legacy) | Legacy; Split/Native unmeasured on Quest | Vulkan only | Throughput | U5-035, U5-037, A1-059, A1-060, G1-025 [doc] |
| GPU Skinning | 2021.3 "Compute Skinning" checkbox; 2022.3 "GPU Compute Skinning"; 2023.2 dropdown CPU/GPU; 6.0+ CPU / GPU / GPU (Batched) | GPU (Batched) on 6.x when CPU-bound and GPU has slack | as listed | Throughput | U5-040 / U4-077 [doc] |
| Skin Weights | Quality settings | 4 bones (import default "Standard (4 Bones)") | all | Throughput | U5-068, U4-077 [doc] |
| Prebake Collision Meshes | Player > Other Settings > Optimization | on | 2021.3-6.x | Consistency (load) | U5-059 / U4-074 [doc] |
| Fixed Timestep | Project Settings > Time | open conflict (U5-C4 / UNITY-GF1-C3); measure 0.02, 1/refresh, 2/refresh | all | Consistency vs Throughput | U5-050, U5-051, UNITY-GF1-014 |
| Maximum Allowed Timestep | Project Settings > Time | one or two fixed steps (derived, no Meta number) | all | Consistency | U5-054 [doc] |
| Auto Sync Transforms | Project Settings > Physics | off (default) | all | Throughput | U5-056 [doc] |
| Reuse Collision Callbacks | Project Settings > Physics | on (default; check upgraded projects) | all | Consistency | U5-057 [doc] |
| Sleep Threshold / Default Contact Offset / Default Solver Iterations | Project Settings > Physics | ≥ 0.005 / ≥ 0.01 / ≤ 6 (Meta) | all | Throughput | U5-061 [doc] |
| Optimized Frame Pacing | Player > Resolution and Presentation | off pending stale-frame A/B (conflict U5-C5); owner of pacing: `quest-perf:quest-frame-pacing` | 2021.3-6.6 | Consistency | U5-023, U5-024 |
| Sustained Performance Mode | Player settings | do not rely on it; use CPU/GPU levels (`quest-perf:quest-levels-thermal`) | 2021.3-6.6 | none proven | U5-028 [doc] |
| Frame Timing Stats | Player > Other Settings > Rendering | on if you read FrameTimingManager in release (`unity-perf:unity-profiling-workflow`) | 2021.3-6.6 | measurement | U5-027 [doc] |
| Application Entry Point | Player settings | GameActivity on 6.0+ (OpenXR 1.16.0-pre.2 Quest validation rule); no CPU difference published | 6.0+ | none (correctness) | U5-026 [doc] |
| Script Call Optimization | iOS/tvOS only | not available on Android | - | - | U5-020 [doc] |

Burst package by Unity version (U5-030 [doc]): 6000.0+ newest 1.8.30; 2022.3 1.8.29;
2021.3 1.8.26. In 6.6 Burst is a built-in module; check that a pinned package does
not conflict. Burst targets and `FloatMode`: `arm-mobile-hw-perf:xr2-cpu-threads-neon`.

## Build-preprocess script (untested)

Drop into an `Editor/` folder. It applies the Throughput settings above for Android
and logs what it changed. It is marked **untested**: compile it in your exact
version before relying on it. API assumptions:
- `PlayerSettings.graphicsJobMode` / `GraphicsJobMode.Legacy` per Meta's page (U5-035).
  Meta says Legacy needs ≥ 2022.3.35f1; a patch version cannot be guarded with
  defines, so the script checks `Application.unityVersion` at build time.
- `NamedBuildTarget` overloads are used on 2022.3+ and `BuildTargetGroup` on 2021.3.
- `SetIl2CppCodeGeneration` exists from 2022.1; on 2021.3 the setting is
  `EditorUserBuildSettings.il2CppCodeGeneration`.

```csharp
#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;

public sealed class QuestCpuPlayerSettings : IPreprocessBuildWithReport
{
    public int callbackOrder => 0;

    // Set false to report only.
    const bool Apply = true;
    // Graphics Jobs are opt-in: enable only after an on-device A/B (SKILL.md fix 3).
    const bool EnableLegacyGraphicsJobs = false;

    public void OnPreprocessBuild(BuildReport report)
    {
        if (report.summary.platform != BuildTarget.Android) return;

#if UNITY_2022_3_OR_NEWER
        var t = NamedBuildTarget.Android;
        Check("Scripting backend IL2CPP",
            PlayerSettings.GetScriptingBackend(t) == ScriptingImplementation.IL2CPP,
            () => PlayerSettings.SetScriptingBackend(t, ScriptingImplementation.IL2CPP));
        Check("IL2CPP C++ config Master",
            PlayerSettings.GetIl2CppCompilerConfiguration(t) == Il2CppCompilerConfiguration.Master,
            () => PlayerSettings.SetIl2CppCompilerConfiguration(t, Il2CppCompilerConfiguration.Master));
        Check("IL2CPP code generation OptimizeSpeed",
            PlayerSettings.GetIl2CppCodeGeneration(t) == Il2CppCodeGeneration.OptimizeSpeed,
            () => PlayerSettings.SetIl2CppCodeGeneration(t, Il2CppCodeGeneration.OptimizeSpeed));
        Check("Multithreaded Rendering on",
            PlayerSettings.GetMobileMTRendering(t),
            () => PlayerSettings.SetMobileMTRendering(t, true));
#else
        var g = BuildTargetGroup.Android;
        Check("Scripting backend IL2CPP",
            PlayerSettings.GetScriptingBackend(g) == ScriptingImplementation.IL2CPP,
            () => PlayerSettings.SetScriptingBackend(g, ScriptingImplementation.IL2CPP));
        Check("IL2CPP C++ config Master",
            PlayerSettings.GetIl2CppCompilerConfiguration(g) == Il2CppCompilerConfiguration.Master,
            () => PlayerSettings.SetIl2CppCompilerConfiguration(g, Il2CppCompilerConfiguration.Master));
        Check("IL2CPP code generation OptimizeSpeed",
            EditorUserBuildSettings.il2CppCodeGeneration == Il2CppCodeGeneration.OptimizeSpeed,
            () => EditorUserBuildSettings.il2CppCodeGeneration = Il2CppCodeGeneration.OptimizeSpeed);
        Check("Multithreaded Rendering on",
            PlayerSettings.GetMobileMTRendering(g),
            () => PlayerSettings.SetMobileMTRendering(g, true));
#endif
        Check("Architecture ARM64 only",
            PlayerSettings.Android.targetArchitectures == AndroidArchitecture.ARM64,
            () => PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64);
        Check("Incremental GC on",
            PlayerSettings.gcIncremental,
            () => PlayerSettings.gcIncremental = true);
        Check("Stack trace None for Log",
            PlayerSettings.GetStackTraceLogType(LogType.Log) == StackTraceLogType.None,
            () => PlayerSettings.SetStackTraceLogType(LogType.Log, StackTraceLogType.None));
        Check("Stack trace None for Warning",
            PlayerSettings.GetStackTraceLogType(LogType.Warning) == StackTraceLogType.None,
            () => PlayerSettings.SetStackTraceLogType(LogType.Warning, StackTraceLogType.None));

        // Graphics Jobs: never without MT rendering (U5-038); Vulkan only (G1-025).
        var apis = PlayerSettings.GetGraphicsAPIs(BuildTarget.Android);
        bool vulkanFirst = apis.Length > 0 && apis[0] == GraphicsDeviceType.Vulkan;
        if (EnableLegacyGraphicsJobs && vulkanFirst && LegacyModeSupported())
        {
            Check("Graphics Jobs on (Legacy)",
                PlayerSettings.graphicsJobs && PlayerSettings.graphicsJobMode == GraphicsJobMode.Legacy,
                () => { PlayerSettings.graphicsJobs = true; PlayerSettings.graphicsJobMode = GraphicsJobMode.Legacy; });
        }
        else if (PlayerSettings.graphicsJobs)
        {
            Debug.LogWarning("[QuestCpu] Graphics Jobs is on without an A/B, on GLES, or below 2022.3.35f1. " +
                             "Measure main-thread AND GPU time (LRZ) before shipping it.");
        }
    }

    static bool LegacyModeSupported()
    {
#if UNITY_6000_0_OR_NEWER
        return true;
#elif UNITY_2022_3_OR_NEWER
        // "2022.3.35f1": parse the patch number.
        var v = Application.unityVersion;
        var parts = v.Split('.');
        if (parts.Length < 3) return false;
        var digits = new System.Text.StringBuilder();
        foreach (var c in parts[2]) { if (char.IsDigit(c)) digits.Append(c); else break; }
        return int.TryParse(digits.ToString(), out var patch) && patch >= 35;
#else
        return false; // 2021.3: no Meta guidance (A1-062)
#endif
    }

    static void Check(string name, bool ok, System.Action fix)
    {
        if (ok) return;
        if (Apply) { fix(); Debug.Log($"[QuestCpu] fixed: {name}"); }
        else Debug.LogWarning($"[QuestCpu] not set: {name}");
    }
}
#endif
```

Notes:
- Changing Player settings inside `OnPreprocessBuild` affects the current build on
  recent versions; if your version applies them only to the next build, run the
  checks from a menu item before building [verify on device/in Editor].
- The 6.6 Managed Code Variant is not set by this script; set it by hand per
  build type (U5-018).
- `unity-perf:unity-urp-settings` ships `QuestPerfAudit.cs`, which reports (not
  applies) Graphics Jobs mode and MT rendering alongside other skills' settings.

## Command-line thread arguments

`-job-worker-count`, `-platform-android-*-affinity` and priority arguments
(U5-033) are owned by `arm-mobile-hw-perf:xr2-cpu-threads-neon`. Keep defaults
unless a Perfetto trace shows a problem.
