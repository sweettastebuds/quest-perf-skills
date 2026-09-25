# GraphicsStateCollection tracing and warmup: per-version API and C#

Deep reference for `unity-perf:unity-shader-hitches`. Read it when you are
writing or debugging the trace/warm code, upgrading across the 6.5 namespace
move, or shipping on 2021.3/2022.3 where GSC does not exist. All sources were
accessed 2026-09-24. All C# below is untested on device; it follows the
signatures on the Unity ScriptReference pages cited in each section.

## 1. API by version

| Unity | Namespace | What exists | Source |
|---|---|---|---|
| 2021.3, 2022.3 | none | No GSC. Only `ShaderVariantCollection.WarmUp`, `Shader.WarmupAllShaders`, `Experimental.Rendering.ShaderWarmup`, Preloaded Shaders. None know render-pass/RT state on Vulkan (U3-092). | https://docs.unity3d.com/6000.1/Documentation/Manual/shader-prewarm.html [doc] |
| 6000.0.0b11 | - | Vulkan honours `maxParallelPSOCreationJobs`; PSO-cache registration race and async PSO shutdown fixed; stereo-instancing variants are NOT prewarmed by legacy APIs (UUM-54697) (U1-049, U1-086, U3-091). | https://unity.com/releases/editor/whats-new/6000.0.0b11 [doc] |
| 6000.0.0b15 | `UnityEngine.Experimental.Rendering` | GSC added: `BeginTrace`, `EndTrace`, `SaveToFile`, `LoadFromFile`, `SendToEditor`, `WarmUp`, `WarmUpProgressively`, `ContainsVariant`, `isWarmedUp`, `completedWarmupCount`, `totalGraphicsStateCount`, `variantCount`, `qualityLevelName`, `graphicsDeviceType`, `runtimePlatform` (U3-083, U1-045). | https://unity.com/releases/editor/whats-new/6000.0.0 ; https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Experimental.Rendering.GraphicsStateCollection.html [doc] |
| 6000.0.55f1 | - | GSC falls back to legacy SVC warmup where `SystemInfo.supportsParallelPSOCreation` is false (UUM-112286). Conflict U3-C4: the 6.x manual says the fallback is 6.1+. Verify on 6.0 LTS before relying on it (U1-048). | https://unity.com/releases/editor/whats-new/6000.0.55f1 [doc] |
| 6000.0.74f1 / 6000.5.0b5 | - | Repeated fallback log in release builds removed (UUM-138841) (U1-048). | https://unity.com/releases/editor/whats-new/6000.0.74f1 [doc] |
| 6.3 | experimental | Utility methods, overrides, job-lifetime warnings (U1-046). | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html [doc] |
| 6000.3.21f1 | - | Warmup skips expensive per-variant work for variants already warmed: lower CPU cost of re-running warmup each launch (U1-050). | https://unity.com/releases/editor/whats-new/6000.3.21f1 [doc] |
| 6.4 (6000.4.0a2/a4) | experimental | Edit collections without re-tracing; generate states from Mesh/Material arrays; corrupted Vulkan pipeline cache handled; "Fixed GraphicsStateCollection warmup for Vulkan" (UUM-121231), see X-C1 (U1-046, U1-047, U3-095). | https://unity.com/releases/editor/whats-new/6000.4.0a4 [doc] |
| 6000.5.0a3 | - | `WarmUp(..., traceCacheMisses)`, `cacheMissCollection` (U1-046, U3-087). | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html [doc] |
| 6000.5.0a9 | `UnityEngine.Rendering` | Non-experimental; `LoadFromJson`, GlobalKeyword overloads, `Append`, `AddGraphicsStates`, `isTracingCacheMisses`; Graphics settings automation (section 5) (U1-046, U3-088). | https://unity.com/releases/editor/whats-new/6000.5.0a9 ; https://docs.unity3d.com/ScriptReference/Rendering.GraphicsStateCollection.html [doc] |

Signatures used below (6.6 ScriptReference, same shape on 6.0 minus
`traceCacheMisses`): `JobHandle WarmUp(JobHandle dependency)`,
`JobHandle WarmUpProgressively(int count, JobHandle dependency)`; both are
called without arguments in Unity's own examples, so `dependency` defaults.
Sources: https://docs.unity3d.com/ScriptReference/Rendering.GraphicsStateCollection.WarmUp.html ,
https://docs.unity3d.com/ScriptReference/Rendering.GraphicsStateCollection.WarmUpProgressively.html ,
https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Experimental.Rendering.GraphicsStateCollection.WarmUpProgressively.html [doc].

Semantics that matter on Quest (U3-086, [doc] [verify on device]):
- Real PSO warmup needs `SystemInfo.supportsParallelPSOCreation == true`.
  Otherwise GSC falls back to `ShaderVariantCollection.WarmUp` semantics and
  `count` limits variants, not PSOs. No published value for Quest Vulkan:
  log it on Quest 2 and Quest 3 (the tracer below does).
- Created PSOs are cached to disk by the driver/Unity pipeline cache
  (`vulkan_pso_cache.bin`, U3-094).

## 2. Tracing rules (U3-084, U3-085)

- Development builds only. `BeginTrace()` at startup, `EndTrace()` when done,
  then `SaveToFile()` (writes `.graphicsstate`) or `SendToEditor()` (needs
  Development Build + Autoconnect Profiler). On Quest pull with `adb pull`.
  https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-trace.html [doc]
- One collection per graphics API and platform. For Quest that means one
  Vulkan/Android collection per quality tier. Switch through quality levels
  while tracing. Trace on device, not in the Editor, because Editor traces
  carry desktop state. https://discussions.unity.com/t/graphicsstatecollection-tracing-and-warmup-in-unity-6/951031 [community]
- Every material and effect must actually render during the trace. Compute
  and ray-tracing shaders are not captured.
- Re-running tracing with the same collection appends new data on save
  (shader-pso-trace page, 6000.0).
- Re-trace after every Editor upgrade: variants and render-pass state change
  (U1-046 notes).
- Whether Quest 2 and Quest 3 need separate traces (different MSAA or
  formats per tier) is unverified [verify on device] (U3-085 notes).
- Whether GSC captures the stereo-instanced/multiview PSOs is undocumented
  (U1-049). Check: after tracing, confirm `variantCount` > 0 for your URP Lit
  shader and that the second pass of a scripted route shows no
  `CreateGraphicsGraphicsPipelineImpl` for it [verify on device].
- Reference tooling: URP 3D Sample (17.0.6+) ships
  `GraphicsStateCollectionManager.cs`, `GraphicsStateCollectionStripper.cs`,
  `GraphicsStateCollectionCombiner.cs` under
  `Assets/SharedAssets/GraphicsStateCollections` (U3-085). Unity's GSC
  example project builds only for Windows and macOS, no Android/Quest (U3-090,
  https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-example.html [doc]).

## 3. Tracer (dev build, Unity ≥ 6000.0, Vulkan)

Put it on a bootstrap object in the first scene of a Development Build. It
saves on pause (headset off, Meta menu) and quit, then resumes tracing.
File lands in `Application.persistentDataPath`, which on Quest is
`/sdcard/Android/data/<package>/files/`.

```csharp
// GscTracer.cs  -- runtime assembly. Unity 6000.0+. Development builds only.
#if UNITY_6000_0_OR_NEWER
using System.IO;
using UnityEngine;
#if UNITY_6000_5_OR_NEWER
using UnityEngine.Rendering;
#else
using UnityEngine.Experimental.Rendering;
#endif

public sealed class GscTracer : MonoBehaviour
{
    [SerializeField] string filePrefix = "Quest";
    GraphicsStateCollection _gsc;

    void Awake()
    {
        if (!Debug.isDebugBuild) { enabled = false; return; } // tracing needs a dev build
        DontDestroyOnLoad(gameObject);
        Debug.Log($"[GSC] supportsParallelPSOCreation={SystemInfo.supportsParallelPSOCreation} " +
                  $"api={SystemInfo.graphicsDeviceType} gpu={SystemInfo.graphicsDeviceName}");
        _gsc = new GraphicsStateCollection();
        _gsc.BeginTrace();
    }

    string PathForCurrentTier()
    {
        string tier = QualitySettings.names[QualitySettings.GetQualityLevel()];
        return Path.Combine(Application.persistentDataPath,
            $"{filePrefix}_{SystemInfo.graphicsDeviceType}_{tier}.graphicsstate");
    }

    public void Save()
    {
        if (_gsc == null || !_gsc.isTracing) return;
        _gsc.EndTrace();
        string p = PathForCurrentTier();
        _gsc.SaveToFile(p);
        Debug.Log($"[GSC] saved {_gsc.variantCount} variants / {_gsc.totalGraphicsStateCount} states to {p}");
    }

    // Call instead of QualitySettings.SetQualityLevel while tracing: one file per tier.
    public void SwitchTier(int level)
    {
        Save();
        QualitySettings.SetQualityLevel(level, true);
        _gsc = new GraphicsStateCollection();
        _gsc.BeginTrace();
    }

    void OnApplicationPause(bool paused)
    {
        if (_gsc == null) return;
        if (paused) Save();
        else if (!_gsc.isTracing) _gsc.BeginTrace();
    }

    void OnApplicationQuit() => Save();
}
#endif
```

Pull and import:

```sh
adb shell ls /sdcard/Android/data/<package>/files/
adb pull /sdcard/Android/data/<package>/files/Quest_Vulkan_<Tier>.graphicsstate Assets/GSC/
```

To trace several tiers in one session, call `SwitchTier(level)` instead of
`SetQualityLevel`. It saves the current tier's file, then starts a fresh
collection so the next file holds only that tier's states (`Save()` alone
ends the trace and keeps the old collection). The collection records
`qualityLevelName`.

## 4. Warmup behind a loading environment (Unity ≥ 6000.0)

Run it on every launch: the cache is invalidated by install, app update and
OS/driver update (U3-096), and on 6000.3.21f1+ re-warming already-warm
variants is cheaper (U1-050). Put it behind a loading environment and ask
for CPU Boost there (owned by `quest-perf:quest-levels-thermal`).

`perFrame` has no published per-PSO cost on Adreno. Start low, then size it
from measured `CreateGraphicsGraphicsPipelineImpl` durations so warm work
fits the frame's slack (13.9 ms at 72 Hz minus measured frame time) (U3-088
notes). The next batch is only scheduled when the previous job handle has
completed, so the main thread never blocks on PSO creation.

```csharp
// GscWarmup.cs  -- runtime assembly. Unity 6000.0+.
#if UNITY_6000_0_OR_NEWER
using System;
using System.Collections;
using Unity.Jobs;
using UnityEngine;
#if UNITY_6000_5_OR_NEWER
using UnityEngine.Rendering;
#else
using UnityEngine.Experimental.Rendering;
#endif

public sealed class GscWarmup : MonoBehaviour
{
    [Tooltip("One collection per quality tier, traced on device (Vulkan/Android).")]
    [SerializeField] GraphicsStateCollection[] collections = Array.Empty<GraphicsStateCollection>();
    [Tooltip("States scheduled per batch. No published Adreno per-PSO cost: size from Profiler.")]
    [SerializeField, Min(1)] int perFrame = 8;
    [SerializeField] int maxFrames = 3000; // safety stop if isWarmedUp never flips (fallback path)
#if UNITY_6000_5_OR_NEWER
    [Tooltip("QA builds: record PSOs requested after warmup that were not in the collection.")]
    [SerializeField] bool traceCacheMisses = false;
    GraphicsStateCollection _warmed;
#endif
    public bool Done { get; private set; }
    public event Action Completed;

    GraphicsStateCollection Pick()
    {
        string tier = QualitySettings.names[QualitySettings.GetQualityLevel()];
        GraphicsStateCollection fallback = null;
        foreach (var c in collections)
        {
            if (c == null || c.graphicsDeviceType != SystemInfo.graphicsDeviceType) continue;
            if (c.qualityLevelName == tier) return c;
            fallback ??= c;
        }
        return fallback;
    }

    IEnumerator Start()
    {
        var gsc = Pick();
        Debug.Log($"[GSC] parallelPSO={SystemInfo.supportsParallelPSOCreation} " +
                  $"collection={(gsc ? gsc.name : "none")} states={(gsc ? gsc.totalGraphicsStateCount : 0)}");
        if (gsc == null) { Finish(); yield break; }

#if UNITY_6000_5_OR_NEWER
        _warmed = gsc;
        if (traceCacheMisses && !gsc.isTracingCacheMisses)
        {
            // Cache-miss tracing must be off before this call (U3-087). Full warm, QA builds only.
            JobHandle all = gsc.WarmUp(default, traceCacheMisses: true);
            while (!all.IsCompleted) yield return null;
            all.Complete();
            Finish();
            yield break;
        }
#endif
        JobHandle h = default;
        int frames = 0;
        while (!gsc.isWarmedUp && frames++ < maxFrames)
        {
            if (h.IsCompleted)
            {
                h.Complete();
                h = gsc.WarmUpProgressively(perFrame);
            }
            yield return null;
        }
        h.Complete();
        Debug.Log($"[GSC] warmed {gsc.completedWarmupCount}/{gsc.totalGraphicsStateCount} " +
                  $"isWarmedUp={gsc.isWarmedUp} frames={frames}");
        Finish();
    }

    void Finish() { Done = true; Completed?.Invoke(); }

#if UNITY_6000_5_OR_NEWER
    // Saves cache misses on pause (headset off / Meta menu); OnApplicationQuit is unreliable on Quest.
    void OnApplicationPause(bool p)
    {
        if (p && traceCacheMisses && _warmed != null && _warmed.cacheMissCollection != null)
            _warmed.cacheMissCollection.SaveToFile(System.IO.Path.Combine(Application.persistentDataPath, $"Quest_{SystemInfo.graphicsDeviceType}_misses.graphicsstate"));
    }
#endif
}
#endif
```

Gate the scene reveal on `Done` (or the `Completed` event). If the log shows
`parallelPSO=False`, you are on the SVC fallback and Vulkan PSOs are not
being built with the right state (U3-082): use the render-once method in
section 6 as well [verify on device].

## 5. Cache-miss loop (Unity ≥ 6000.5) (U3-087)

1. QA dev build with `traceCacheMisses = true` in `GscWarmup` (above).
2. Play the full route. PSOs requested after warmup that were missing
   accumulate in the warmed collection's `cacheMissCollection`.
3. End the session by taking the headset off or opening the Meta menu:
   `GscWarmup.OnApplicationPause` (section 4) writes
   `Quest_Vulkan_misses.graphicsstate` to `Application.persistentDataPath`.
   Pull it and merge in the Editor:

```sh
adb pull /sdcard/Android/data/<package>/files/Quest_Vulkan_misses.graphicsstate Assets/GSC/
```

```csharp
#if UNITY_6000_5_OR_NEWER
// In the Editor, after importing both files:
// mainCollection.Append(missCollection);  then save the asset; check with ContainsVariant(shader, variantIndex).
#endif
```

Ship the merged collection. This is the closest thing to a p99 hitch
regression test (U3-087 notes).

6.5+ can do the same without code: Project Settings > Graphics > Shader
Settings (absent in 6.3/6.4) has Preload Graphics State Collection,
Collection Startup Behavior (None / Begin Trace / Warmup), Additional
Collections, Warmup Asynchronously, Warmup After Showing First Scene, a
progressive per-frame count (0 = all on the next frame), and Enable Cache
Miss Tracing with a save path (U3-088,
https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html [doc]).
Warming before the first scene lengthens black/splash time; warming after it
spreads PSO creation over frames the user sees. Put the warm window behind a
loading environment either way.

## 6. 2021.3 / 2022.3 (no GSC): render every material once

On Vulkan the legacy APIs do not know render-pass/RT state, so the reliable
method is to draw every material/state combination once behind a loading
screen (U3-092). Meta's archived Unity-ShaderPrewarmer does this: MeshRenderers
per material, 50-100 objects per frame at 1/60 s, 2021/2022 LTS, GLES and
Vulkan, built-in and URP, no Unity 6 support (U3-093,
https://github.com/oculus-samples/Unity-ShaderPrewarmer [doc]). It only
covers MeshRenderer states: skinned meshes, particles, UI and
shadow-caster/depth passes need their own warm content.

Minimal equivalent (2021.3+; also usable on 6.x as a top-up for PSOs a GSC
misses). Place the spawned objects inside the XR camera frustum (culled
objects issue no draw) and hide them behind an opaque loading environment;
a draw that fails the depth test still creates its PSO. Use the same camera,
URP asset, MSAA and render targets as gameplay, because PSOs bake RT format
and sample count (U3-082).

```csharp
// RenderOncePrewarmer.cs -- runtime assembly. Unity 2021.3+. Untested.
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public sealed class RenderOncePrewarmer : MonoBehaviour
{
    [SerializeField] Camera xrCamera;                 // the gameplay XR camera
    [SerializeField] Mesh[] meshes;                   // one per vertex layout you ship
    [SerializeField] Material[] materials;            // every material/keyword combination
    [SerializeField, Min(1)] int perFrame = 50;       // Meta sample used 50-100
    [SerializeField] float distance = 2f;             // metres in front of the camera
    public bool Done { get; private set; }

    IEnumerator Start()
    {
        var spawned = new List<GameObject>(perFrame);
        Transform cam = xrCamera.transform;
        foreach (var mesh in meshes)
        {
            for (int i = 0; i < materials.Length; i += perFrame)
            {
                for (int j = i; j < Mathf.Min(i + perFrame, materials.Length); j++)
                {
                    var go = new GameObject("prewarm");
                    go.transform.SetPositionAndRotation(cam.position + cam.forward * distance, cam.rotation);
                    go.transform.localScale = Vector3.one * 0.01f;
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var r = go.AddComponent<MeshRenderer>();
                    r.sharedMaterial = materials[j];
                    r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On; // warms ShadowCaster when a shadowed light is active
                    spawned.Add(go);
                }
                yield return null;          // let the frame render and create the PSOs
                yield return null;
                foreach (var go in spawned) Destroy(go);
                spawned.Clear();
            }
        }
        Done = true;
    }
}
```

Stereo-instancing/multiview variants are not prewarmed by the legacy warmup
APIs (U1-049); drawing through the real XR camera is what makes this method
hit the stereo variants [verify on device].

## 7. Placement checklist

- Warm on every launch, gated on a loading environment; do not reveal the
  scene until `Done`.
- Boost the CPU during the warm window and drop back afterwards (Boost owner:
  `quest-perf:quest-levels-thermal`).
- Warm per streamed area just before it is shown if a single collection is
  too large to warm at boot; there is no published size threshold, measure
  warm time per collection.
- Keep Loaded Shaders Alive (Player settings) prevents re-creating programs
  after scene unloads at a RAM cost (U3-080,
  https://docs.unity3d.com/6000.6/Documentation/Manual/shader-loading.html [doc]).
  Memory trade: `unity-perf:unity-memory-assets`.
