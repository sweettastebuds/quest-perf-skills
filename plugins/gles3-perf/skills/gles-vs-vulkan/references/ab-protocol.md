# GLES vs Vulkan A/B protocol (Quest 2/3/3S, Unity 2022.3 to 6.6)

Read when running or reviewing an API A/B. The rule it serves is G1-078:
default to Vulkan; keep GLES only if a single-variable A/B shows a win after
OBD and store minimisation on Vulkan. Finding IDs refer to `research/gles3.md`
and `research/quest.md`.

## 0. The XR plugin trap

The Unity OpenXR plugin lists Quest as Vulkan-only, and GLES + OpenXR on Quest
is off-document; Unity's own 6000.x GLES XR repros use the Oculus XR plugin,
deprecated from 6.5 (G1-024 / G2-093, G2-C8). So:

- If the project ships on **Oculus XR**, both arms use Oculus XR. One variable.
- If the project ships on **OpenXR**, a GLES arm forces a plugin swap too. Run
  it as two comparisons: (a) Vulkan + Oculus XR vs GLES + Oculus XR for the API
  effect, (b) Vulkan + Oculus XR vs Vulkan + OpenXR for the plugin effect. No
  published number exists for (b) (U1-093); plugin choice is owned by
  `quest-perf:quest-sdk-choices`.
- On Unity 6.5+ the Oculus XR plugin is deprecated; a GLES result there has a
  short shelf life (G1-076).

## 1. Hold these identical in both builds (G1-079)

| Setting | Why |
|---|---|
| Auto Graphics API **off**, exactly one API listed | Auto tries Vulkan, then GLES 3.2/3.1/3.0 (G1-016) |
| MSAA level (URP asset > Quality > Anti Aliasing) | MSAA is the mechanism of the known gap (G1-064) |
| Renderer (Forward), depth priming, Opaque Texture, Depth Texture, HDR, post stack | depth copies and depth priming are recurring Vulkan suspects (G1-061, G1-064) |
| ES shader level: on ≤ 6.5 "Require ES3.1"; on 6.6 "Use OpenGL ES 3.0 shaders" | MAX_VISIBLE_LIGHTS is 16 for GLES 3.0 shaders vs 32 for Vulkan / GLES 3.1+ (G1-019, G1-020). To match Vulkan's 32, the GLES arm needs ES 3.1 shaders |
| Stereo mode (Multiview) | multiview has a native GLES path (G1-010); Multi-pass / Multiview / SPI did not change UUM-93226 (G1-049) |
| Refresh rate, FFR level, render scale | foveation on GLES + OpenXR is undocumented (GX-C8) |
| Development build flag | GLES development builds with Oculus XR 4.4.0 + Multiview can spam GL_INVALID_OPERATION and drop FPS (UUM-102876, G2-057); time non-development builds, capture development builds |
| Unity version, URP version, OS build, headset unit | the claimed Qualcomm fix ships through the OS (G1-051) |

Vulkan-only features (OBD, Symmetric Projection, MRR, FFR subsampling, AppSW)
are **off** in step A and added one at a time in step B (G1-079).

## 2. Build both arms from one project (C# editor helper)

`Assets/Editor/QuestApiAbBuild.cs`. Compiles on Unity 2022.3 and 6000.x
(URP 14 / 17). Untested on device. It builds a non-development APK per API,
restores the original API list, and logs the settings that must match.

```csharp
// Assets/Editor/QuestApiAbBuild.cs
#if UNITY_2022_3_OR_NEWER
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class QuestApiAbBuild
{
    const BuildTarget Target = BuildTarget.Android;

    [MenuItem("Tools/Quest API AB/Build Vulkan only")]
    static void BuildVulkan() => Build(GraphicsDeviceType.Vulkan, "vk", false);

    [MenuItem("Tools/Quest API AB/Build OpenGLES3 only")]
    static void BuildGles() => Build(GraphicsDeviceType.OpenGLES3, "gles", false);

    [MenuItem("Tools/Quest API AB/Build Vulkan only (Development, for RenderDoc)")]
    static void BuildVulkanDev() => Build(GraphicsDeviceType.Vulkan, "vk_dev", true);

    [MenuItem("Tools/Quest API AB/Build OpenGLES3 only (Development, for RenderDoc)")]
    static void BuildGlesDev() => Build(GraphicsDeviceType.OpenGLES3, "gles_dev", true);

    [MenuItem("Tools/Quest API AB/Log settings that must match")]
    static void LogSettings() => Debug.Log(Snapshot());

    static void Build(GraphicsDeviceType api, string tag, bool development)
    {
        bool prevAuto = PlayerSettings.GetUseDefaultGraphicsAPIs(Target);
        GraphicsDeviceType[] prevApis = PlayerSettings.GetGraphicsAPIs(Target);
        try
        {
            PlayerSettings.SetUseDefaultGraphicsAPIs(Target, false);
            PlayerSettings.SetGraphicsAPIs(Target, new[] { api });

            string[] scenes = EditorBuildSettings.scenes
                .Where(s => s.enabled).Select(s => s.path).ToArray();
            Directory.CreateDirectory("Builds/ApiAB");
            var options = new BuildPlayerOptions
            {
                scenes = scenes,
                target = Target,
                locationPathName = $"Builds/ApiAB/{PlayerSettings.productName}_{tag}.apk",
                options = development ? BuildOptions.Development : BuildOptions.None
            };
            BuildReport report = BuildPipeline.BuildPlayer(options);
            Debug.Log($"[API A/B] {api} dev={development}: {report.summary.result} " +
                      $"-> {report.summary.outputPath}\n{Snapshot()}");
        }
        finally
        {
            PlayerSettings.SetUseDefaultGraphicsAPIs(Target, prevAuto);
            PlayerSettings.SetGraphicsAPIs(Target, prevApis);
        }
    }

    static string Snapshot()
    {
        string urp = "no URP asset active";
        if (GraphicsSettings.currentRenderPipeline is UniversalRenderPipelineAsset a)
        {
            urp = $"URP asset={a.name} msaa={a.msaaSampleCount} " +
                  $"depthTex={a.supportsCameraDepthTexture} opaqueTex={a.supportsCameraOpaqueTexture} " +
                  $"hdr={a.supportsHDR} renderScale={a.renderScale}";
        }
        // Graphics Jobs Mode is only meaningful on Vulkan (G1-025).
        return $"unity={Application.unityVersion} graphicsJobs={PlayerSettings.graphicsJobs} " +
               $"graphicsJobMode={PlayerSettings.graphicsJobMode} {urp}. " +
               "Check by hand: renderer path, depth priming (renderer asset), ES shader level, " +
               "XR plugin, stereo mode, OBD / Symmetric Projection / MRR state.";
    }
}
#endif
```

Both APKs share the package name, so installing one replaces the other. Run
one arm at a time.

## 3. Stamp every run from inside the player (runtime C#)

`Assets/Scripts/ApiAbStamp.cs`. No component needed; it runs after the first
scene loads. Read it with `adb logcat -s Unity | grep "API A/B"` (use
`findstr` on Windows).

```csharp
// Assets/Scripts/ApiAbStamp.cs  (Unity 2022.3 / 6000.x)
using UnityEngine;
using UnityEngine.XR;

static class ApiAbStamp
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Stamp()
    {
        Debug.Log(
            "[API A/B] api=" + SystemInfo.graphicsDeviceType +
            " version=\"" + SystemInfo.graphicsDeviceVersion + "\"" +
            " gpu=\"" + SystemInfo.graphicsDeviceName + "\"" +
            " threading=" + SystemInfo.renderingThreadingMode +
            " msaaAutoResolve=" + SystemInfo.supportsMultisampleAutoResolve +
            " eye=" + XRSettings.eyeTextureWidth + "x" + XRSettings.eyeTextureHeight +
            " unity=" + Application.unityVersion);
    }
}
```

`supportsMultisampleAutoResolve` true on GLES is consistent with the implicit
on-tile MSAA resolve path (G2-044) [verify on device]. `renderingThreadingMode`
on a GLES build with Graphics Jobs ticked answers whether any jobs mode runs on
GLES (KU-12).

## 4. Record the environment for every capture

```sh
adb shell getprop ro.build.id                      # OS build; blob cache is keyed on it (G3-014)
adb shell dumpsys SurfaceFlinger | grep GLES       # GLES driver string (G2-082)
adb shell getprop | grep debug.oculus              # props in force (Q1-077)
```

The Vulkan driver version is in the `[API A/B]` stamp (`graphicsDeviceVersion`).

## 5. Step A: GPU timing, pinned levels, no Vulkan-only features

1. Pin levels (Meta-documented props; reset on reboot) (Q1-079):
   ```sh
   adb shell setprop debug.oculus.cpuLevel 3
   adb shell setprop debug.oculus.gpuLevel 3
   ```
   UUM-149765 also set `debug.oculus.sysPropDebug 1` and `debug.oculus.headlock 1`, the latter to fix the head pose (G2-010). These come from a Unity QA report, not a Meta page: [verify on device]. Without headlock, use a fixed headset pose or a scripted camera.
2. `adb shell ovrgpuprofiler -e` **before** launching the app (else restart it), launch, reach the test view, then `adb shell ovrgpuprofiler -t2` (a 2 s trace). Add `-v` (`-t2 -v`) for per-bin stages (G3-080). UUM-149765 wrote `-t 2` (G2-010); Meta documents `-t<seconds>` (G3-080) [verify on device].
3. Read for the eye-buffer surface: total ms, Binning, Render, StoreColor, StoreDepthStencil, bin count and size, Mode (0 Direct, 1 HwBinning, 2 SwBinning, 3 HwDirect) (G3-080).
4. Repeat with MSAA off on both arms. Reference deltas: Quest 3/3S 4x +3.3 ms GLES vs +5.0 ms Vulkan, MSAA-off gap within about 1 ms; Quest 2 4x about +7 ms, APIs within about 1 ms (G2-039, G2-040). Quote deltas, not absolute ms (G2-C9).
5. Development builds only: RenderDoc Meta Fork 68.18 capture with `--frame-number` for the same frame on both arms; count Store* per bin in the Tile Timeline (GLES3-GF1-004, G3-078). Caveats: [gles-capture.md](gles-capture.md).
6. `adb shell ovrgpuprofiler -d` when done.

## 6. Step B: add Vulkan-only features one at a time

Vulkan arm only, re-measure after each: OBD (the UUM-93226 workaround; G1-051),
then Symmetric Projection (5-15% claim; G1-037), then MRR on 6.1+ (3-8% claim;
G1-039). Paths and caveats: `quest-perf:quest-sdk-choices`. Also apply the
store-minimising settings (depth priming off, no Opaque/Depth texture, Forward)
to both arms if the project allows (G1-048, G1-064). The Vulkan arm to compare
against GLES is the best Vulkan configuration the project can actually ship.

## 7. Step C: hitches, cold and warm

- Scripted camera route through first-seen materials, development builds, both arms (G1-065).
- Count frames above 1.5x the frame budget (13.9 / 11.1 / 8.3 ms at 72 / 90 / 120 Hz) in OVR Metrics / Perfetto; attribute spikes with `Shader.CreateGPUProgram` (GLES compile/link) vs `CreateGraphicsGraphicsPipelineImpl` (Vulkan PSO) (G3-002). Whether the PSO marker fires on GLES is undocumented [verify on device].
- Run the route on the first launch after an OS update (cold: the EGL blob cache is dropped when `ro.build.id` changes; G3-014) and on the next launch (warm). Report them separately (G1-067).
- No published PSO-vs-link numbers exist (KU-03). Warmup fixes: `unity-perf:unity-shader-hitches` (Vulkan), `gles3-perf:gles-shader-binaries` (GLES).

## 8. Step D: consistency soak, unpinned

Reboot (clears the level props), then per arm a 20-30 minute session on the
same route with OVR Metrics CSV (Q1-003, Q1-008):

```sh
adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV
# play the session
adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.DISABLE_CSV
adb pull /sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/ .
py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/ovr_metrics_csv.py <file.csv>
```

Compare p50/p95/p99 of `app_gpu_time_microseconds` across rows, stale frames
per minute, `shader_hitches`, and first-vs-last-5-minute drift. Rows are 1 Hz
averages, so use Perfetto for per-frame pacing (Q1-010). No GLES-vs-Vulkan
p95/p99 data is published (KU-42).

## 9. Step E (only if CPU-bound): render-thread sweep

Same scene at about 200, 500 and 1000 draws, Multithreaded Rendering on; compare
render-thread ms (Profiler `Gfx.*` markers or Perfetto `UnityGfxDeviceW`
slices) and OVR Metrics CPU app time per arm (G1-068, KU-07). On GLES also
toggle Low Overhead Mode (Oculus XR only; `gles3-perf:gles-driver-overhead`).
No published CPU delta exists. No OpenXR equivalent of Low Overhead Mode was
found in the OpenXR Meta Quest Support feature list, so a GLES arm on OpenXR
may lose this CPU saving [verify on device]: check the OpenXR feature list for
your plugin version and A/B render-thread ms (KU-43, G1-043).

## 10. Record template

```
date / tester:
headset + unit:            OS build (ro.build.id):
GLES driver (dumpsys):     Vulkan driver (stamp):
Unity / URP / XR plugin:   stereo mode:  refresh:  MSAA:  ES shader level:
arm | features on | pinned lvl | eye-buffer total / Binning / Render / StoreColor / StoreDS / bins | p50/p95/p99 app GPU | stale/min | >1.5x-budget frames cold / warm
```

## 11. Decide

- Any Vulkan-only feature needed: Vulkan. Keep the numbers as the baseline for fixes (G1-078).
- GLES wins only step A: not enough. It must also beat the step-B Vulkan configuration.
- GLES wins step B and C/D: GLES is defensible for this OS build. Re-run steps A-B after each Horizon OS update (G1-051) and before moving to Unity 6.5+ (G1-024).

## Sources

All accessed 2026-09-24.
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/Input.hlsl [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsMultisampleAutoResolve.html [doc]
- https://docs.unity3d.com/2022.3/Documentation/ScriptReference/SystemInfo-renderingThreadingMode.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc]
- https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [measured] (recipe: [community])
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102876 [community]
- https://discussions.unity.com/t/performance-discrepancy-between-vulkan-and-opengl-with-unity-2022-3-17f1-on-meta-quest-3/938162 [community]
- https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 [community]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/BlobCache.cpp [doc]
