---
name: unity-upgrade-risks
description: "Known performance regressions and breaking changes when upgrading Unity/URP for Quest 2/3/3S: Render Graph GPU regressions, foveation breakages, GPU occlusion bugs, Oculus XR to OpenXR migration, removed Compatibility Mode, obsolete APIs, and safe patch floors per version. Use before or after an upgrade, when FPS dropped or GPU time rose after moving to Unity 6 or a new patch, when a migration broke stereo or FFR, or when choosing which patch release to ship."
---

# Unity upgrade risks for Quest (2021.3 to 6.6)

Goal: **Throughput** (don't ship a patch with a known GPU regression) and
**Consistency** (no new hitches, black frames, one-eye rendering or memory
growth after an upgrade). Scope is Quest 2 (XR2 Gen 1, Adreno 650) and Quest
3/3S (XR2 Gen 2, Adreno 740), URP 12 to URP 17.6, Vulkan primary, GLES legacy.

## When to use / when not

Use when:
- Planning a hop (2021.3 to 2022.3 to 6.0 to 6.3 to 6.6) and you need the list of what regresses or breaks.
- "Slower after upgrade", "GPU util jumped after moving to Unity 6", "FFR broke after upgrade", "only the left eye renders", "black screen after upgrade", "Compatibility Mode removed", "custom pass stopped working".
- Picking the patch to ship on a given stream (patch floors).
- Migrating Oculus XR to OpenXR as part of an engine upgrade.

When not:
- "Does version X have feature Y" or choosing an engine version, Meta's minimum version, LTS dates: `unity-perf:unity-version-matrix`.
- Vulkan slower than GLES (UUM-93226) and the API decision: `gles3-perf:gles-vs-vulkan`.
- FFR/dynamic foveation tuning when nothing regressed: `quest-perf:quest-resolution-foveation`.
- Choosing an XR plugin or Meta SDK toggle for a new project: `quest-perf:quest-sdk-choices`.
- `XRDisplaySubsystem` GPU-time units changing across OpenXR 1.18.0-pre.2: `unity-perf:unity-profiling-workflow`.
- Porting passes to Render Graph and pass merging mechanics: `unity-perf:unity-render-graph-tiling`.
- GSC/PSO warmup hitches: `unity-perf:unity-shader-hitches`.
- Unknown bottleneck, no upgrade involved: `quest-perf:quest-triage`.

## Diagnose first

An upgrade regression is confirmed only by a single-variable A/B: same
content, same device, same Horizon OS build, same scripted route, only the
Unity/URP/plugin version changes.

1. **Record versions.** Editor (`Application.unityVersion`), URP, OpenXR / Oculus XR plugin, Meta XR SDK, graphics API list. Run the editor check in Fix 1.
2. **Pin clocks for the timing A/B** (removes clock-scaling noise; props reset on reboot) (Q1-077, Q1-079):
   ```sh
   adb shell setprop debug.oculus.cpuLevel 4
   adb shell setprop debug.oculus.gpuLevel 4
   adb shell getprop | grep debug.oculus   # store next to every capture
   ```
3. **Capture OVR Metrics CSV** for each build over the same route (Q1-003, Q1-008):
   ```sh
   adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV
   # run the route, then
   adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.DISABLE_CSV
   adb pull /sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/ .
   ```
   Compare p50/p95/p99 of `app_gpu_time_microseconds` across rows, stale frames per minute and `shader_hitches`. Rows are 1 Hz averages, so they cannot show a single-frame hitch; use Perfetto for frame pacing (Q1-010). The analyzer lives in `quest-perf:quest-profiling-toolkit`.
4. **Count passes.** Render Graph Viewer (6.0+) or RenderDoc Meta Fork render-stage capture on both builds. A new surface, an unmerged depth copy, or a RenderObjects pass split into its own render pass is the fingerprint of the regressions below.
5. **Check foveation is actually on** after the hop: VrApi logcat `Fov=3` (`Fov=3D` when dynamic) (Q1-081 / Q3-028), foveation level in OVR Metrics, or the fragment density map attachment in RenderDoc (U1-084). For a controlled check, override it: `adb shell setprop debug.oculus.foveation.dynamic 0` then `adb shell setprop debug.oculus.foveation.level N` (Q1-081).
6. **Match the symptom to [references/regressions.md](references/regressions.md)** (read it whenever the source or target version is known; it has every issue ID, affected range, fixed-in version and workaround).

Unpin levels (reboot) before any 20-30 minute soak; the soak must see real runtime clock behaviour (Q1-077).

## Key numbers

| Number | Meaning | Applies to | Source |
| --- | --- | --- | --- |
| up to ~20% GPU utilization | UUM-90118 Render Graph regression; reporter saw ~50% vs ~90% util, worse on Quest 2 | `Quest 2` `Quest 3` `Unity 6000.0.16f1-6000.0.45f1` `Vulkan` RG on | U1-031 [measured] |
| 6000.0.46f1 / 6000.1.0b14 / 6000.2.0a9 | UUM-90118 fixed | `Unity 6.0-6.2` | U1-031 [doc] |
| ~6000.0.52f1 | Practical 6.0 floor from Quest fixes (right eye .14, RG+MSAA spam .38, logcat spam .49, blit/copy one-eye .49, Vulkan exit errors .52). UUM-84612 black screen with MSAA + post + AppSW depth submission: fix entry in 6000.0.50f1 but the issue link keeps appearing in notes through 6000.0.58f1 [verify on device] (U1-079) | `Unity 6.0` | U1-080, U1-079 [doc] |
| 6000.0.66f2 | Meta's required minimum (6.1+ recommended); owned by `unity-perf:unity-version-matrix` | `Unity 6.0` | U1-008 [doc] |
| 6.5.0-6.5.7 | UUM-146214: GPU occlusion culling costs GPU and culls nothing; fixed 6000.5.8f1 / 6000.6.0f1 | `Unity 6.5` `Vulkan` GRD | U1-020 [doc] |
| 90 to 40-60 fps, GPU util ~50% to over 90% | FFR regression IN-115870 even at FFR level 0; reported fixed in 6000.3.0f1 | `Quest 2` `Unity 6.1/6.2` `URP 17.0.3-17.2.0` `Vulkan` `OpenXR 1.15.1` | Q3-036 [community] [verify on device] |
| 20-30% frame time | SRP Foveation vs Legacy foveation with post, deferred or multi-pass (gain available only after moving to 6.0+ OpenXR) | `Unity ≥ 6000.0` `OpenXR` | U1-085 [doc] [verify on device] |
| 16 to 32 | URP MAX_VISIBLE_LIGHTS when a 6.6 GLES project moves to ES 3.1 shaders; UUM-148728 forced 32 regardless before 6000.6.0f1 (conflict X-C6) | `Unity 6.6` `GLES` | U1-094, U1-040 [doc] |
| 13.9 / 11.1 ms | Frame budget at 72 / 90 Hz, the threshold for counting over-budget frames in the A/B; owned by `quest-perf:quest-budgets-tiers` | `Quest 2` `Quest 3/3S` | 1000/72, 1000/90 (unity.md baseline, U5) [arithmetic] |
| no published number | Frame-time delta of a like-for-like Oculus XR to OpenXR migration | all | U1-093; measure with the A/B protocol |
| no published number | Memory saved by UUM-121520 (Vulkan command buffers with graphics jobs) | `Unity 6.0` vs `6.2.12+/6.3` | U1-087; measure with `adb shell dumpsys meminfo <pkg>` |

Practical patch floors (derived from the fixed-in versions; each floor is the
highest fix that applies to a typical Quest URP project; skip rows for
features you don't use):

| Stream | Floor | Why |
| --- | --- | --- |
| 2021.3 | 2021.3.36f1 if using dynamic resolution | Extra intermediate pass at scale ≠ 1 (Q3-056) |
| 2022.3 | 2022.3.53f1 | Dyn-res fixes .15/.22 (Q3-055/056), Vulkan transient flag .53 (U1-088) |
| 6.0 | 6000.0.66f2 (Meta); .73f1 if GLES; .81f1 if RenderObjects + dyn-res/FFR | U1-008, U1-081, Q3-054 |
| 6.1 / 6.2 | Avoid for FFR on Vulkan (IN-115870); if staying: 6.1 ≥ 6000.1.9f1, 6.2 ≥ 6000.2.12f1 | IN-115870 (Q3-036), UUM-109083 (U1-080), UUM-121520 (U1-087) |
| 6.3 | 6000.3.21f1 | UUM-132450 and UUM-93243 at .14 (U1-081/083), RenderObjects split at .21 (Q3-054) |
| 6.4 | 6000.4.4f1 | UUM-132450 (U1-083); FFR High + 24-bit depth on the Meta 6000.4 AppSW fork still open (Q3-038) |
| 6.5 | 6000.5.8f1 | UUM-146214 (U1-020), RenderObjects split at .6 (Q3-054) |
| 6.6 | 6000.6.0f1 | UUM-146214 (U1-020) |

## Fixes, ranked by payoff ÷ effort

### 1. Move to the patch floor before any other tuning

What: install the floor patch from the table above on your current stream
before profiling anything. A 6.0 project on 6000.0.16f1-.45f1 with Render
Graph on is paying up to ~20% GPU for a merge bug (U1-031).
Effect: removes a fixed average-GPU-time penalty (Throughput); removes
black-frame / one-eye / exit-error defects (Consistency).
Cost: patch upgrade only; re-run the A/B.
Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.6` `Vulkan` `GLES`. Goal: Throughput, Consistency.

Paste-ready editor check (untested: Unity cannot run here; API-conservative,
compiles on 2021.3+). Save as `Assets/Editor/QuestUpgradeRiskCheck.cs`, run
**Tools > Quest > Upgrade Risk Check**, read the Console.

```csharp
// Untested. Unity 2021.3+. Reports patch-floor, Compatibility Mode, plugin and shader-define risks.
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;
#if UNITY_6000_0_OR_NEWER && !UNITY_6000_3_OR_NEWER
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
#endif

public static class QuestUpgradeRiskCheck
{
    // stream, minimum f-patch, reason (see unity-upgrade-risks references/regressions.md)
    static readonly (string stream, int patch, string why)[] Floors =
    {
        ("2021.3", 36, "dyn-res extra intermediate pass (Q3-056)"),
        ("2022.3", 22, "dyn-res extra intermediate pass (Q3-056)"),
        ("2022.3", 53, "Vulkan transient usage flag UUM-71363"),
        ("6000.0", 46, "UUM-90118 +20% GPU with Render Graph"),
        ("6000.0", 49, "UUM-92499 AddBlitPass/AddCopyPass one eye"),
        ("6000.0", 50, "UUM-84612 black screen MSAA+post+SpaceWarp depth"),
        ("6000.0", 52, "practical Quest floor (U1-080)"),
        ("6000.0", 66, "Meta minimum 6000.0.66f2"),
        ("6000.0", 73, "UUM-93243 GLES crash (only if GLES)"),
        ("6000.0", 81, "RenderObjects split under dyn-res/FFR"),
        ("6000.1", 9,  "UUM-109083 Vulkan exit errors; FFR IN-115870 unfixed on 6.1"),
        ("6000.2", 12, "UUM-121520 Vulkan cmd-buffer memory; FFR IN-115870 unfixed on 6.2"),
        ("6000.3", 14, "UUM-132450 FB fetch + FFR black; UUM-93243"),
        ("6000.3", 21, "RenderObjects split under dyn-res/FFR"),
        ("6000.4", 4,  "UUM-132450 FB fetch + FFR black"),
        ("6000.5", 8,  "UUM-146214 GPU occlusion culling broken"),
    };

    [MenuItem("Tools/Quest/Upgrade Risk Check")]
    static void Run()
    {
        var sb = new StringBuilder("Quest upgrade risk check\n");
        var v = Application.unityVersion;                       // e.g. 6000.0.52f1
        var m = Regex.Match(v, @"^(\d+\.\d+)\.(\d+)([abfp])(\d+)");
        if (m.Success)
        {
            string stream = m.Groups[1].Value;
            int patch = int.Parse(m.Groups[2].Value);
            bool release = m.Groups[3].Value == "f" || m.Groups[3].Value == "p";
            if (!release) sb.AppendLine($"WARN {v}: alpha/beta editor, floors assume f releases");
            foreach (var f in Floors.Where(f => f.stream == stream && patch < f.patch))
                sb.AppendLine($"WARN {v} < {stream}.{f.patch}: {f.why}");
        }

#if UNITY_6000_0_OR_NEWER && !UNITY_6000_3_OR_NEWER
        if (GraphicsSettings.TryGetRenderPipelineSettings<RenderGraphSettings>(out var rg)
            && rg.enableRenderCompatibilityMode)
            sb.AppendLine("WARN Render Graph Compatibility Mode is ON: legacy path, no RG gains; removed in 6.4");
#endif
        string defines = PlayerSettings.GetScriptingDefineSymbols(NamedBuildTarget.Android);
        if (defines.Contains("URP_COMPATIBILITY_MODE"))
            sb.AppendLine("WARN URP_COMPATIBILITY_MODE define set: legacy passes; removed in 6000.4.0a4");

        var pkgs = UnityEditor.PackageManager.PackageInfo.GetAllRegisteredPackages();
        foreach (var p in pkgs.Where(p => p.name == "com.unity.xr.openxr" || p.name == "com.unity.xr.oculus"
                                       || p.name == "com.unity.render-pipelines.universal"))
            sb.AppendLine($"INFO {p.name} {p.version}");
#if UNITY_6000_5_OR_NEWER
        if (pkgs.Any(p => p.name == "com.unity.xr.oculus"))
            sb.AppendLine("WARN Oculus XR plugin installed: not supported on 6.5+; migrate to OpenXR");
#endif

        // URP 14 removed SHADER_QUALITY_* and SHADER_HINT_NICE_QUALITY (U1-099).
        var shaderHits = Directory.EnumerateFiles("Assets", "*.*", SearchOption.AllDirectories)
            .Where(f => f.EndsWith(".shader") || f.EndsWith(".hlsl") || f.EndsWith(".cginc"))
            .Where(f => Regex.IsMatch(File.ReadAllText(f), @"SHADER_QUALITY_(LOW|MEDIUM|HIGH)|SHADER_HINT_NICE_QUALITY"));
        foreach (var f in shaderHits)
            sb.AppendLine($"WARN {f}: SHADER_QUALITY_*/SHADER_HINT_NICE_QUALITY removed in URP 14, branch now dead");

        // Heuristic: ScriptableRenderPass without RecordRenderGraph stops running on 6.4+ (U1-026).
        foreach (var f in Directory.EnumerateFiles("Assets", "*.cs", SearchOption.AllDirectories))
        {
            string src = File.ReadAllText(f);
            if (src.Contains("ScriptableRenderPass") && !src.Contains("RecordRenderGraph"))
                sb.AppendLine($"WARN {f}: render pass without RecordRenderGraph (breaks on 6.4+)");
        }
        Debug.Log(sb.ToString());
    }
}
```

`GetAllRegisteredPackages` and `NamedBuildTarget` are 2021.2+ APIs; if either
fails to compile on your editor, delete that block. The 6.0 floors compare the
patch number only (6000.0.66f1 would pass the f2 floor).

### 2. Un-tick Compatibility Mode after a 2022.3 to 6.0 hop

What: Project Settings > Graphics > Render Graph > Compatibility Mode (Render
Graph Disabled): off. Upgraded projects are switched to Compatibility Mode
automatically (U1-023), so "Unity 6 gave no RG gain" usually means RG never
ran. Only do this on 6000.0.46f1+, or you trade the legacy path for UUM-90118.
Effect: Render Graph native pass merging lowers average GPU time where passes
now merge; see `unity-perf:unity-render-graph-tiling` for what merges.
Cost: every custom `ScriptableRenderPass` needs `RecordRenderGraph`; passes
without it stop running on 6.4+ (U1-026). 6.3 is the last version where legacy
passes run, and only behind `URP_COMPATIBILITY_MODE` (conflict U1-C5: the 6.3
guide says "removed", the define still works; both are true).
Tags: `Unity ≥ 6000.0` `URP 17` `Vulkan` `GLES`. Goal: Throughput.

### 3. Port custom passes, and set their foveation state

What: when porting to `RecordRenderGraph`, give every raster pass on camera
color the same foveation state as URP's DrawObjects pass. A mismatch
(`FRStateMismatch`) splits the native render pass: an extra GMEM store/load
per split (U2-054 / U1-085).

```csharp
// URP 17 (Unity 6000.0+), members of your ScriptableRenderPass subclass.
// usings: UnityEngine.Rendering, UnityEngine.Rendering.RenderGraphModule, UnityEngine.Rendering.Universal
class PassData { }
public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
{
    var resourceData = frameData.Get<UniversalResourceData>();
    var cameraData   = frameData.Get<UniversalCameraData>();
    using (var builder = renderGraph.AddRasterRenderPass<PassData>("QuestOverlayPass", out var passData))
    {
        builder.SetRenderAttachment(resourceData.activeColorTexture, 0, AccessFlags.ReadWrite);
        builder.AllowPassCulling(false); // remove once the render func draws
        // Match URP's DrawObjectsPass so the compiler can merge this pass.
        // Pass false when writing a non-foveated intermediate (see caveat below).
        builder.EnableFoveatedRasterization(cameraData.xr.supportsFoveatedRendering);
        builder.SetRenderFunc((PassData d, RasterGraphContext ctx) => { /* draw */ });
    }
}
```

URP's own pass additionally gates on the internal
`xrUniversal.canFoveateIntermediatePasses || isActiveTargetBackBuffer` check
(6000.3 `DrawObjectsPass.cs`), which this snippet does not replicate, so it
can mark a pass foveated on a target URP does not foveate. Untested here: confirm
`XRPass.supportsFoveatedRendering` is public in your URP/Core version, and
confirm the merge in the Render Graph Viewer [verify on device].
Also on the 6.0-6.2 hops: on 6.0 < .49 do not use `AddBlitPass`/`AddCopyPass`
for XR (one eye, U1-078); on 6.2+ `SetupRenderPasses` is deprecated and
AfterRendering runs after the final blit (U1-024); custom VolumeComponents
overriding `Override()` must set `overrideState = true` (U1-100).
Tags: `Unity ≥ 6000.0` `URP 17` `Vulkan`. Goal: Throughput, Consistency.

### 4. Treat foveation as broken until re-verified after every hop

What, by version:
- 6.0: foveated post (UberPost/FinalPostBlit) needs 6000.0.22f1+ (U1-082). SRP foveation + URP HDR foveated the top half of the image in one report; workaround Legacy API or HDR off (Q3-037, [community]).
- 6.1 / 6.2 on Vulkan: if GPU time doubles with Foveated Rendering on, disable the feature entirely (level 0 is not off) and move to 6.3+ (Q3-036, [community], IN-115870 reported fixed in 6000.3.0f1).
- Framebuffer fetch + FFR renders black below 6000.3.14f1 / 6000.4.4f1 / 6000.5.0b5; no 6.0 fix entry found (U1-083).
- UUM-113364 (foveation off with MSAA on Vulkan) was fixed in 6000.4.0b9 for "PC or linked XR". Conflict U1-C6: Unity's untethered guide recommends MSAA + foveation on standalone Quest, and whether standalone Quest on ≤ 6.3 lost foveation is unknown. Check the FDM attachment in RenderDoc with MSAA on vs off [verify on device].
- 6000.4 Meta AppSW URP fork: FFR High + 24-bit depth submission shows glitched squares, under investigation (Q3-038, [community]).
- OpenXR 1.18.0-pre.1 turns off FDM attachments at foveation level 0 on the SRP path (Q3-035): re-baseline any "level 0" capture across that plugin upgrade.
Effect: a silently disabled FFR raises average GPU time; glitches and black frames are Consistency defects. Tuning FFR itself: `quest-perf:quest-resolution-foveation`.
Tags: `Quest 2` `Quest 3/3S` `Unity 6.0-6.5` `Vulkan` `OpenXR`. Goal: Throughput, Consistency.

### 5. Plan the Oculus XR to OpenXR migration as its own A/B

What: on 6.5+ the Oculus XR package is not supported (U1-091); Meta also
caps Oculus XR at Meta XR SDK v73 (U1-009). A 2021.3/2022.3 to 6.x upgrade is
therefore also a plugin switch and a Meta XR SDK major bump; do them as
separate measured steps where possible. The switch changes which plugin owns
foveation, depth submission, eye-buffer format and frame timing, and
settings do not carry across (U1-093). Re-apply Meta's OpenXR settings
(Multi-View, SRP Foveation on 6+, Depth Submission None unless AppSW or layers
need it, and the rest in U1-092; the choices themselves are owned by
`quest-perf:quest-sdk-choices`). Remove `UnityEngine.VR` references before 6.5
(VR module removed, U1-101). If the project has in-app GPU telemetry, OpenXR
1.18.0-pre.2 changed `XRDisplaySubsystem` GPU-time units from ms to seconds;
normalize by plugin version (`unity-perf:unity-profiling-workflow`).
Effect: no published frame-time delta (U1-093); SRP foveation's 20-30% (U1-085)
is the main upside. Cost: re-baseline everything.
Tags: `Quest 2` `Quest 3/3S` `Unity ≥ 6000.0` `OpenXR ≥ 1.15.1`. Goal: Throughput, Consistency.

### 6. Turn off GPU occlusion culling on 6.5.0-6.5.7

What: Universal Renderer asset > GPU Occlusion off (it needs GRD), or upgrade
to 6000.5.8f1 / 6000.6.0f1. On the broken range it costs GPU time and culls
nothing (UUM-146214, U1-020). GRD and GPU occlusion culling are unavailable on
GLES regardless (U1-095).
Effect: removes a fixed average-GPU-time cost (Throughput); no variance change
is documented.
Cost: no quality loss on the broken range because it culls nothing. On
6000.5.8f1+ re-enable it and A/B, because Unity warns total time can rise when
a scene has little occlusion (U3-037). No published number; measure
`app_gpu_time_microseconds` p50 with it on vs off.
Tags: `Unity 6000.5.0-6000.5.7` `Vulkan`. Goal: Throughput.

### 7. Fix silent shader and batching fallbacks per hop

- URP 14 (2022.3) removed `SHADER_QUALITY_LOW/MEDIUM/HIGH` and `SHADER_HINT_NICE_QUALITY`; shaders that used them as a Quest switch now compile the default path (U1-099). Replace with `SHADER_API_MOBILE`:
  ```hlsl
  // Put in a shared include after Core.hlsl; replace every SHADER_QUALITY_LOW test with QUEST_LOW_QUALITY.
  #if defined(SHADER_API_MOBILE)
      #define QUEST_LOW_QUALITY 1
  #else
      #define QUEST_LOW_QUALITY 0
  #endif
  // usage:  #if QUEST_LOW_QUALITY  ...cheap path...  #else  ...full path...  #endif
  ```
  Effect: restoring the cheap branch lowers average GPU time; the quality cost is the old Quest look, i.e. the pre-upgrade behaviour. Tags: `URP 14+` `GLES` `Vulkan`. Goal: Throughput.
- 6.6 makes dynamic batching obsolete (U1-022); move small meshes to SRP Batcher / GRD / combining, see `unity-perf:unity-draw-calls-batching`. Effect: losing it raises average CPU render-thread time for small-mesh scenes; no quality change. Tags: `Unity ≥ 6000.6`. Goal: Throughput.
- 6.6 GLES: if you turn off "Use OpenGL ES 3.0 shaders", MAX_VISIBLE_LIGHTS goes 16 to 32 and shader work rises (U1-094); a project that already required ES 3.1 gets this immediately. UUM-148728 forced 32 on GLES regardless of the setting before 6000.6.0f1 (U1-040); 6.6 betas are affected. Effect: keeping the 16-light path holds average GPU time at the pre-upgrade level; the quality cost is fewer visible additional lights per camera. Tags: `Unity ≥ 6000.6` `GLES`. Goal: Throughput.
- 6.0 no longer applies the Quality mip limit to runtime-created textures by default (U1-089): memory can grow after the hop [verify on device]. Effect: raises memory; the variance risk is lmkd/GC hitches. To restore the old behaviour, set the texture's mipmap limit explicitly; the quality cost is the lower mips you shipped before. Tags: `Unity ≥ 6000.0`. Goal: Consistency.
- 6.0 obsoletes `FindObjectsOfType`; `FindObjectsByType(FindObjectsSortMode.None)` is faster (U1-100). Effect: lowers average main-thread time; side effect is unsorted results; no quality change. Tags: `Unity ≥ 6000.0`. Goal: Throughput.

### 8. Re-check the graphics API after the hop, don't assume

The graphics-API trade-off can change with the engine version (UUM-93226): re-run the API A/B on the new version, see `gles3-perf:gles-vs-vulkan`. `Quest 2` `Quest 3/3S` `Vulkan` `GLES`. Goal: Throughput, Consistency.

## Verify

- UUM-90118: after moving 6000.0.16-.45 to ≥ .46 with RG on, GPU utilization in OVR Metrics should drop by up to ~20% at the same levels (reporter: ~90% back toward ~50%), and the Render Graph Viewer should show the depth copy merged after uber post. Pinned-level A/B, 5 minutes of the same route per build.
- Compatibility Mode off: pass count in Render Graph Viewer / RenderDoc drops; p50 `app_gpu_time_microseconds` moves down. No published size; measure.
- Foveation: `Fov=` logcat / FDM attachment present at the configured level on the new version, and GPU time at FFR on vs off differs as it did before the hop.
- 6.5 GPU occlusion: GPU time with occlusion culling on ≤ off on 6000.5.8f1+; on the broken range, off wins.
- Consistency: stale frames per minute and p95/p99 GPU time no worse than the old build over a 20-30 minute unpinned soak (reboot first to clear props). A new `shader_hitches` spike in the first minute points at PSO warmup: `unity-perf:unity-shader-hitches`.
- Memory: `adb shell dumpsys meminfo <pkg>` peak PSS no higher than the old build (UUM-121520, U1-089).

## Pitfalls and myths

- **"Unity 6 is faster because of Render Graph."** Upgraded projects start in Compatibility Mode (U1-023), and 6000.0.16-.45 with RG on carries UUM-90118. Check both before comparing.
- **"FFR level 0 means foveation is off."** On 6.1/6.2 Vulkan the regression showed at level 0 (Q3-036); OpenXR 1.18.0-pre.1 changed level-0 behaviour (Q3-035). Disable the feature to get a real "off" baseline.
- **"The latest 6.0 LTS patch has every fix."** No 6.0 entry was found for UUM-132450 (U1-083) or UUM-121520 (U1-087). Vulkan GSC warmup (UUM-121231) is a recorded conflict: U1-047 finds it only in 6000.4.0a4 with no LTS backport; U3-091 reads it as a 6.4-alpha-only regression that never reached LTS (X-C1). Measure cold-start hitches on your LTS patch.
- **"Settings carry across the OpenXR migration."** They don't (U1-093). Re-baseline.
- **"Vulkan is always faster on Quest" / "GLES is always faster".** Neither is established; A/B on current OS (U1-C2, `gles3-perf:gles-vs-vulkan`).
- **"My SHADER_QUALITY_LOW Quest branch still works."** Removed in URP 14; the branch is dead code after the hop (U1-099).
- **"Dynamic resolution saves GPU."** On 2021.3 < .36 and 2022.3 < .22 it adds a full-screen intermediate pass (Q3-056); on 6.x before the Q3-054 fixes, RenderObjects features split into extra render passes under dyn-res + FFR.
- **Comparing in-app GPU times across OpenXR 1.18.0-pre.2** without normalizing units (U5-091).
- **Upgrading editor, URP, OpenXR and Meta XR SDK in one step.** Then no regression can be attributed. One variable per A/B.

## Sources

All accessed 2026-09-24.

- https://issuetracker.unity3d.com/issues/gpu-utilization-increases-by-20-percent-on-meta-quest-headsets-when-render-graph-is-enabled-on-6000-dot-0-16f1-and-higher [measured]
- https://unity.com/releases/editor/whats-new/6000.0.46f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.1.0b14 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.49f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.50f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.14f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.38f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.52f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.73f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.23f1 [doc]
- https://unity.com/releases/editor/whats-new/2022.3.53f1 [doc]
- https://issuetracker.unity3d.com/issues/the-view-renders-black-when-using-framebuffer-fetch-with-foveated-rendering-in-a-player-for-meta-quest [doc]
- https://unity.com/releases/editor/whats-new/6000.0.22f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.3.14f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.4.0b9 [doc]
- https://unity.com/releases/editor/whats-new/6000.4.0a4 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.0 [doc]
- https://unity.com/releases/editor/whats-new/6000.5.8f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.6.0f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.2.12f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.5.0b4 [doc]
- https://issuetracker.unity.com/api/v1.0/issues/1364 [doc]
- https://issuetracker.unity.com/issues/1364 [doc]
- https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 [community]
- https://discussions.unity.com/t/bug-severe-ffr-glitches-performance-loss-with-unity-6-1-6-2-with-urp-vulkan-openxr-on-quest/1677819 [community]
- https://discussions.unity.com/t/srp-foveated-rendering-on-quest-broken-with-openxr-urp-hdr/1672458 [community]
- https://developers.meta.com/horizon/feedback/vr/investigations/2302986490105678/ [community]
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-project-setup/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-and-openxr-compatibility [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ [doc]
- https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ [doc]
- https://docs.unity3d.com/6000.0/Documentation/Manual/urp/upgrade-guide-unity-6.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity62.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity63.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity64.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/upgrade-guide-2022-2.html [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.6/changelog/CHANGELOG.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem.html [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc]
