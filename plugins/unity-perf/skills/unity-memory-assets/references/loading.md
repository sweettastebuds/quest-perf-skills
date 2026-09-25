# Loading, streaming and upload hitches on Quest (detail)

Read from `SKILL.md` when a hitch lines up with a load, scene stream, unload
or Addressables release, or before writing a loading-screen controller.
Finding IDs refer to `research/unity.md` (accessed 2026-09-24). Frame budgets
used below: 72 Hz = 13.9 ms, 90 Hz = 11.1 ms, 120 Hz = 8.3 ms (unity.md
header, arithmetic).

## 1. Async Upload Pipeline (AUP)

Two paths (U4-078), Unity 2021.3 to 6000.x:
- Sync: header and binary in `.res`, loaded on the main thread in one frame.
- Async (AUP): binary in `.resS`, streamed through a ring buffer over several
  frames.

Eligibility checklist (U4-078):

| Asset | Must be true for AUP |
|---|---|
| Texture | non-readable; outside `Resources`; Android build uses LZ4 compression. `Texture2D.LoadImage` always takes the sync path. |
| Mesh | non-readable; outside `Resources`; no BlendShapes, no bone weights; not quads; not dynamic-batched; not needed by Particle Systems, Terrain or MeshColliders; Mesh Compression Off; LZ4 build |

Skinned characters (bone weights) always take the sync path: load them behind
a loading screen or fade (U4-078 notes).

Settings (U4-079), Project Settings > Quality, or `QualitySettings.*` at
runtime:

| Setting | Range | Default | Note |
|---|---|---|---|
| Async Upload Time Slice (`asyncUploadTimeSlice`) | 1-33 ms | 2 ms (2018 blog, U4-080) | Runs on the render thread, twice per frame, while uploads are pending (U4-080) |
| Async Upload Buffer Size (`asyncUploadBufferSize`) | 2-2047 MB | 16 MB since 2018.3 (U4-080) | Grows automatically; resizing is slow. Size to the largest texture you load (U4-079). |
| Async Upload Persistent Buffer (`asyncUploadPersistentBuffer`) | bool | true | Off frees the buffer when idle: saves memory, can fragment the heap |

- The 2018 defaults may differ from current versions; read your project's
  Quality settings (U4-080 notes). [verify on device]
- A full ring buffer slows loading but does not block the main thread
  (U4-080).
- Pipeline steps: read into the ring buffer (AsyncRead thread) ->
  post-process (texture decompression for unsupported formats, mesh
  collision generation) -> time-sliced upload (U4-081). Unsupported formats
  and non-prebaked collision therefore lengthen loads.
- The time slice spends render-thread time: raise it only behind a loading
  screen and lower it again for gameplay (U4-080 notes). No published Quest
  value for either; measure load duration vs render-thread frame time.

Profiler markers (U4-082):
- Confirm AUP is used: `AsyncUploadManager.ScheduleAsyncRead`,
  `AsyncReadManager.ReadFile`, `Async.DirectTextureLoadBegin`, activity on
  the AsyncRead thread.
- Do not prove AUP by themselves: `Initialization.AsyncUploadTimeSlicedUpdate`,
  `AsyncUploadManager.AsyncResourceUpload`,
  `AsyncUploadManager.ScheduleAsyncCommands`.

## 2. Main-thread integration budget

`Application.backgroundLoadingPriority` caps main-thread integration time per
frame for `Resources.LoadAsync`, `AssetBundle.LoadAssetAsync` and
`SceneManager.LoadSceneAsync` (U4-083). Marker:
`Application.Integrate Assets in Background`. No effect in the Editor.

| Value | Cap per frame | Use on Quest |
|---|---|---|
| Low | 2 ms | gameplay streaming |
| BelowNormal (default) | 4 ms | - |
| Normal | 10 ms | - |
| High | 50 ms | only behind a black or compositor loading screen: 50 ms exceeds every Quest frame budget |

## 3. Scene activation and unloading

- `allowSceneActivation = false` stops progress at 0.9, and every later
  AsyncOperation (including `UnloadSceneAsync`) queues behind it until
  activation. `AsyncOperation.priority` (default 0, higher first) orders the
  queue (U4-084). Holding a preloaded scene at 0.9 is a common cause of
  "loading froze" bugs.
- Activation is a main-thread hitch. Meta (2021, possibly stale, U4-085):
  nest objects under a few roots; load objects disabled and enable them over
  several frames; pool instead of instantiate; warm shaders with a reference
  scene, not `Shader.WarmupAll` (PSO warmup: `unity-perf:unity-shader-hitches`).
- Activation cost ranking from Meta's Quest 2 profiling (U4-075, relative
  only): cost grows linearly with GameObject count; TextMeshPro >
  ParticleSystem > MeshRenderer; readable or skinned meshes are steep.
- `LoadSceneAsync` in Single mode calls `Resources.UnloadUnusedAssets`
  automatically, which walks all objects and statics (U4-086). A Single-mode
  load therefore includes an unload sweep that scales with live object count.
- Addressables 1.21 docs: `UnloadUnusedAssets` is slow and a cause of
  hitches; call it only where hitches are not visible (U4-087). No Quest
  figure is published: read the `Resources.UnloadUnusedAssets` / GC markers in
  a Development build at your real object counts.
- Community reports: it slows down as a session goes on and can hang in some
  cases (U4-088, [community], sizes not verified). Measure it at minute 1 and
  minute 25 of the same session.

Conflict U4-C1 (resolved): the legacy Meta page says avoid async level loads,
fade to black and load synchronously (U4-092); current Meta and Unity guidance
is async loading behind a fade or compositor loading screen (U4-091, U4-085,
U4-078, U4-083). The legacy advice predates AUP.

## 4. Addressables and AssetBundles

- Releasing an Addressables asset frees nothing until its whole AssetBundle
  unloads; bundles cannot partially unload. Releasing the last asset and
  reloading immediately causes "asset churn". Spot both in the Addressables
  Profiler module (U4-089, Addressables 1.21 to 2.x).
- Group bundles by lifetime: a large bundle kept alive by one small asset is a
  memory problem on Quest 2 (U4-089 notes).
- Compression (U4-090): LZMA decompresses the whole content section into RAM
  before any read; LZ4 compresses 128 KB chunks separately and loads in about
  the time of uncompressed. BuildPipeline defaults to LZMA; Unity's cache
  recompresses downloads to LZ4. Use LZ4 for bundles shipped in the APK/OBB;
  LZ4 is also required for AUP.
- Startup: keep large textures and many prefabs out of the first scene; load
  a small first scene, then the main scene in the background (U4-053, U4-091).

## 5. Shader memory at load

- Player > Other Settings > Shader Variant Loading: default chunk size 16 MB
  of compressed data; default chunk count 0 (no limit on decompressed chunks
  kept); per-platform overrides; `Shader.maximumChunksOverride` at runtime
  (U4-094). Capping the count saves memory but can force re-decompression at
  runtime (hitches). Measure memory and frame time before capping.
- "Keep Loaded Shaders Alive" stops shaders unloading so they are not
  recreated later, at a memory cost (U4-095; Meta's 2018 recommendation,
  possibly stale).
- Variant count, stripping and PSO warmup: `unity-perf:unity-shader-hitches`.

## 6. Audio load types (UNITY-GF1-016)

Unity 6 optimisation e-book, all versions:

| Clip size | Load Type |
|---|---|
| < 200 KB | Decompress On Load, or Compressed In Memory with ADPCM (fixed 3.5:1, cheap decode) |
| ≥ 200 KB | Compressed In Memory if memory is the priority, Decompress On Load if CPU is |
| > 350-400 KB | Streaming (about 200 KB overhead per clip) |

Also: Force To Mono for positional sounds; Vorbis for most sounds (MP3 for
non-looping); unload muted AudioSources. No Quest cost number exists: measure
`Audio` CPU in the Profiler at the worst-case voice count.

## 7. Loading-screen controller (C#)

Unity 2021.3 to 6000.x, any render pipeline and graphics API. Raises the
integration and upload budgets only while the loading screen covers the view,
then restores gameplay values. Show your loading screen as a compositor layer
or black fade before calling it (compositor layers:
`quest-perf:quest-compositor-layers`; CPU Boost during loads:
`quest-perf:quest-levels-thermal`).

```csharp
// QuestSceneLoader.cs  - Unity 2021.3 - 6000.x
using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;

public sealed class QuestSceneLoader : MonoBehaviour
{
    [Tooltip("AUP time slice while hidden behind the loading screen (1-33 ms, U4-079). " +
             "2 = no change from the 2018 default (U4-080); raise and measure. " +
             "No published Quest value: measure total load time.")]
    [Range(1, 33)] public int loadingUploadSliceMs = 2;

    // Set Async Upload Buffer Size once in Project Settings > Quality, sized to
    // the largest texture you load (U4-079); resizing at runtime is slow.

    // Wrap the real transition: call after the view is covered.
    public IEnumerator LoadCovered(string sceneToLoad, string sceneToUnload)
    {
        UnityEngine.ThreadPriority prevPriority = Application.backgroundLoadingPriority;
        int prevSlice = QualitySettings.asyncUploadTimeSlice;

        Application.backgroundLoadingPriority = UnityEngine.ThreadPriority.High; // 50 ms cap: covered view only (U4-083)
        QualitySettings.asyncUploadTimeSlice = loadingUploadSliceMs;

        AsyncOperation load = SceneManager.LoadSceneAsync(sceneToLoad, LoadSceneMode.Additive);
        load.allowSceneActivation = true; // never park at 0.9: it blocks later ops (U4-084)
        while (!load.isDone) yield return null;

        if (!string.IsNullOrEmpty(sceneToUnload))
        {
            AsyncOperation unload = SceneManager.UnloadSceneAsync(sceneToUnload);
            while (unload != null && !unload.isDone) yield return null;
        }

        // Explicit sweep while hidden (U4-086, U4-087). Time it via the
        // Resources.UnloadUnusedAssets marker in a Development build.
        AsyncOperation sweep = Resources.UnloadUnusedAssets();
        while (!sweep.isDone) yield return null;

        SceneManager.SetActiveScene(SceneManager.GetSceneByName(sceneToLoad));

        // Back to gameplay budgets.
        QualitySettings.asyncUploadTimeSlice = prevSlice;
        Application.backgroundLoadingPriority = prevPriority;
    }

    // Streaming during gameplay: keep integration at 2 ms per frame (U4-083).
    public IEnumerator StreamAdditive(string sceneToLoad)
    {
        UnityEngine.ThreadPriority prevPriority = Application.backgroundLoadingPriority;
        Application.backgroundLoadingPriority = UnityEngine.ThreadPriority.Low;
        AsyncOperation load = SceneManager.LoadSceneAsync(sceneToLoad, LoadSceneMode.Additive);
        while (!load.isDone) yield return null;
        Application.backgroundLoadingPriority = prevPriority;
        // Activation of the new roots still runs on the main thread: author the
        // streamed scene with its heavy roots disabled and enable them over
        // several frames (U4-085).
    }
}
```

Notes:
- `StreamAdditive` does not call `UnloadUnusedAssets`: during gameplay that
  sweep is a visible hitch (U4-087).
- Garbage collection during loads, and the incremental GC time slice, belong
  to `unity-perf:unity-cpu-scripting`.

## 8. Long-session memory probe (C#)

Unity 2021.3 to 6000.x, any API. Logs every 10 s so the log lines up with an
OVR Metrics CSV. Texture/Mesh/Gfx counters read 0 in release players; System
Used Memory works in both (U4-065). Mip-streaming totals come from the
`Texture` debug APIs (U4-066).

```csharp
// QuestMemoryProbe.cs - logs every 10 s; dev-only counters read 0 in release players (U4-065).
using Unity.Profiling;
using UnityEngine;

public sealed class QuestMemoryProbe : MonoBehaviour
{
    ProfilerRecorder _system, _tex, _mesh, _gfx;
    float _next;

    void OnEnable()
    {
        _system = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "System Used Memory");
        _tex    = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "Texture Memory");
        _mesh   = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "Mesh Memory");
        _gfx    = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "Gfx Used Memory");
    }

    void OnDisable() { _system.Dispose(); _tex.Dispose(); _mesh.Dispose(); _gfx.Dispose(); }

    void Update()
    {
        if (Time.unscaledTime < _next) return;
        _next = Time.unscaledTime + 10f;
        const float MB = 1f / (1024f * 1024f);
        Debug.Log($"[mem] sys={_system.LastValue * MB:F0} tex={_tex.LastValue * MB:F0} " +
                  $"mesh={_mesh.LastValue * MB:F0} gfx={_gfx.LastValue * MB:F0} " +
                  $"streamDesired={Texture.desiredTextureMemory * MB:F0} " +
                  $"streamCurrent={Texture.currentTextureMemory * MB:F0} " +
                  $"nonStreamed={Texture.nonStreamingTextureMemory * MB:F0} " +
                  $"uploads={Texture.streamingMipmapUploadCount}");
    }
}
```

The string formatting allocates every 10 s; strip the component from
shipping builds.
