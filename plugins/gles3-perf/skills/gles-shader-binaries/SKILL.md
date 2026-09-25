---
name: gles-shader-binaries
description: "GLES-only shader compilation and program binaries on Quest 2/3/3S: first-use compile hitches in OpenGL ES builds (Shader.CreateGPUProgram), the Android EGL blob cache and its 64 KB / 2 MB limits, cache wipes after Horizon OS updates, glProgramBinary and UnityShaderCache, GLES warmup (GraphicsStateCollection falls back to SVC, STEREO_MULTIVIEW_ON variants missed), mediump emission, depth precision and Adreno shader limits. Use for shader hitches in a GLES build, stutter after an OS update, or GLES precision bugs. Vulkan PSO warmup: unity-perf:unity-shader-hitches."
---

# GLES shader binaries, warmup and precision on Quest

Goal: **Consistency** first (no first-use compile hitches or post-OS-update
cold regressions), **Throughput** second (mediump, Adreno per-shader cliffs).

Scope: OpenGL ES 3.x builds only. Quest 2 (Adreno 650, GL driver V@0690),
Quest 3/3S (Adreno 740, V@0837); Unity 2021.3, 2022.3, 6000.0-6000.6; URP 12,
14, 17.x. Every Horizon OS build in use in 2026 is Android 14 based
(GLES3-GF1-006, [community], UUM-149765 device list).

## When to use / when not

Use when:
- A GLES build hitches the first time a material, effect or keyword combination
  appears, or after a scene round-trip.
- Hitches came back after a Horizon OS update or a fresh install, while "it was
  fine on my headset".
- ShaderVariantCollection / GraphicsStateCollection warmup "does nothing" on
  Quest GLES, or shaders in AssetBundles/Addressables still hitch.
- GLES-only visual bugs from precision: banding, jittering UVs or world
  positions, depth reconstruction errors, or asking what `#version` / precision
  Unity emits.
- A long uber-shader on GLES hits Adreno instruction, texture or varying limits.

Do not use; go to the sibling instead:
- Vulkan PSO hitches, GSC tracing on Vulkan, `vulkan_pso_cache.bin`, variant
  counting and stripping: `unity-perf:unity-shader-hitches`.
- Writing cheap URP HLSL (half usage, LRZ-safe states, keywords vs branches):
  `unity-perf:unity-shader-authoring`.
- Why fp16, GPRs, waves and instruction counts cost what they do:
  `arm-mobile-hw-perf:xr2-shader-cost-model`.
- Which GLES version / `#pragma target` / "Use OpenGL ES 3.0 shaders" setting
  Unity targets: `gles3-perf:gles-versions-unity-output`.
- Whether to ship GLES at all, and GLES capture caveats:
  `gles3-perf:gles-vs-vulkan`.
- Meta's Shader Binary Cache (SBC) and its deprecation: `quest-perf:quest-sdk-choices`.
- Not sure the stutter is shader compilation at all: `quest-perf:quest-triage`.

## Diagnose first

1. **Is it a first-use hitch?** OVR Metrics Tool CSV: watch `shader_hitches`,
   `stale_frame_count` and `max_repeated_frames` (Q1-014). Meta publishes no
   definition of `shader_hitches`; confirm it on your build by putting a
   never-seen material on screen and watching the column move [verify on
   device]. Capture recipe: `quest-perf:quest-profiling-toolkit`. A hitch that
   appears on the first run only and not on the second is compilation (Q1-011).
2. **Attribute it** in a Development Build with the Unity Profiler attached
   (Quest 2/3/3S, Unity 6.x marker names, G3-002):
   - `Shader.CreateGPUProgram` (render thread) = driver compile/link, the hitch.
   - `Shader.ParseThreaded` / `Shader.ParseMainThread` = variant
     deserialize/decompress.
   - `CreateGraphicsGraphicsPipelineImpl` is the Vulkan PSO marker; Unity does
     not document whether it fires on GLES [verify on device].
   Every `Shader.CreateGPUProgram` during gameplay after warmup is a missed
   variant (G3-025). Note its keywords: `STEREO_MULTIVIEW_ON` means the
   multiview miss (Fix 2).
3. **Always measure cold and warm separately.** A warm blob cache hides hitches
   (G3-014). Cold launch on a debuggable build:
   ```sh
   adb shell am force-stop <pkg>
   adb shell run-as <pkg> ls -l cache/                      # blob cache file present?
   adb shell run-as <pkg> rm -f cache/com.android.opengl.shaders_cache
   # or wipe everything, including saves: adb shell pm clear <pkg>
   ```
   The file name and location are from AOSP HardwareRenderer (G3-010, [verify
   on device]); if the file never appears, see KU-04 in
   [blob-cache.md](references/blob-cache.md).
4. **Record the cache context** next to every capture, because an OS update
   wipes the cache (G3-014) and the multifile mode changes the limits (G3-013):
   ```sh
   adb shell getprop ro.build.id
   adb shell getprop ro.build.version.release
   adb shell getprop ro.egl.blobcache.multifile
   adb shell ls -l /sdcard/Android/data/<pkg>/cache/        # UnityShaderCache/ present? (KU-06)
   ```
5. **Precision questions**: Shader Inspector > Compile and show code for
   GLES3; read the `#version` line and the `precision` statements
   (GLES3-GF1-007). For static instruction/register counts use the Adreno
   Offline Compiler; on device, `adb shell ovrgpuprofiler -m -v` lists the
   metrics your OS build actually exposes (G3-042).

## Key numbers

| Number | Meaning | Source | Applies to |
| --- | --- | --- | --- |
| 0 shader binary formats, 1 program binary format | no precompiled GPU code can be shipped; every program compiles on device at least once per driver/OS build | gpuinfo reports 6387, 8023 (G1-008/G3-008) [measured] | Quest 2, Quest 3 |
| 12 KB key / 64 KB value / 2 MB total | AOSP monolithic blob cache limits; values over 64 KB are silently not stored | AOSP egl_cache.cpp (G3-011) [doc] | Quest if Horizon OS keeps AOSP defaults [verify on device] |
| evict to under 1 MB | random eviction when the 2 MB cache fills | AOSP BlobCache.cpp (G3-012) [doc] | same |
| 32 MB total / 8 MB value / 4096 entries | multifile cache, only if `ro.egl.blobcache.multifile` is true (default false) | AOSP egl_cache.cpp (G3-013) [doc] | unknown on Horizon OS (KU-04) |
| every `ro.build.id` change | whole cache discarded: first launch after each OS update is cold | AOSP BlobCache/MultifileBlobCache (G3-014) [doc] | all Quest |
| no published number | ms per `glCompileShader`/`glLinkProgram` for URP variants on Adreno 650/740 | G3-001, KU-05 | measure `Shader.CreateGPUProgram` cold vs warm |
| no published number | Adreno program-binary size of URP Lit variants vs the 64 KB limit | G3-011, KU-08 | measure cache-file growth per new variant |
| no published number | Vulkan PSO vs GLES link hitch size | G1-065, KU-03 | count frames over 1.5× budget, cold and warm, both APIs |
| up to 2x speed and power | mediump vs highp fragment arithmetic | Qualcomm (G3-026) [doc] | Adreno fragment shaders; no vertex claim |
| 0.5 step at 512-1024, 1.0 at 1024-2048 | fp16 spacing: unsafe for world position, big UV tiling, `_Time`, depth | IEEE fp16 via Unity 2019.4 page (G3-031) [doc] | any mediump math |
| each multiple of 2000 instructions | A7x instruction-cache cliff | Qualcomm spec sheet (G3-037, A2-070) [doc] | Quest 3/3S; no A6x number (KU-29) |
| 16 textures+SSBOs, 16 UBOs, 32 vertex buffers | A7x per-shader binding cliffs | Qualcomm (G3-038, G2-069) [doc] | Quest 3/3S |
| 16 samplers | A6x-A8x sampler-cache cliff (fragment+compute shared) | Qualcomm (G3-038) [doc] | Quest 2, Quest 3/3S |
| 16 texture units, 14 UBO blocks/stage, 31 varyings | GLES hard limits | gpuinfo 6387/8023 (G2-069, G3-041) [measured] | Quest 2, Quest 3 |

The frame slack you can spend on progressive warmup is the frame budget
(1000 / refresh rate, e.g. 13.9 ms at 72 Hz) minus measured frame time
(U3-088 note); no per-program link time is published, so size the per-frame
count by measurement.

## Fixes, ranked by payoff ÷ effort

Read [blob-cache.md](references/blob-cache.md) when you need the full AOSP
cache tables, the property list, the cold/warm test protocol, UnityShaderCache
details, or the glProgramBinary rules for a native plugin. Read
[gles-code.md](references/gles-code.md) when applying Fix 2 (Editor script that
adds multiview variants to an SVC) or Fix 5 (paste-ready URP shader with the
half/float split).

### 1. Warm every GLES variant behind a loading screen

- **Why it works on GLES:** Adreno "never recompile[s]" programs for state (G3-007, [doc]), so a variant compiled once stays valid for any blend/depth/vertex state. The Vulkan warning that SVC warmup builds wrong PSOs does not apply to GLES (G3-020, G3-021). Warmup does the real compile/link, so the cost moves into load time (G3-024, G3-C2): budget it there.
- **Which API:**
  - 2021.3 / 2022.3: `ShaderVariantCollection.WarmUp`, split into several
    collections to spread across frames (U3-092).
  - 6000.0+: `GraphicsStateCollection` traced on device; on GLES it falls back to SVC-style warmup and `count` limits variants, not PSOs (G3-019, U3-086). **Conflict U3-C4:** the manual says the GLES fallback exists in 6.1+ (G3-019); release notes add it in 6000.0.55f1 (U1-048). On 6.0 LTS below 6000.0.55f1, use SVC; on 6.0.55+ confirm with step 2 of Diagnose [verify on device].
  - Settings path (all 6.x): Project Settings > Graphics > Shader loading >
    Preloaded Shaders + "Preload Shaders After Showing First Scene" + "Preload
    Time Limit Per Frame (ms)"; 0 warms everything in one frame (G3-022). On
    6.5+, "Preload Graphics State Collection" + "Collection Startup Behavior =
    Warmup" (U3-088).
- **Code** (runtime MonoBehaviour; 2021.3+; GSC branch on 6000.0+, namespace
  moved in 6.5, U3-083; the GSC field assumes the `.graphicsstate` asset is
  assignable in the Inspector [verify on target Editor]):
  ```csharp
  using System.Collections;
  using UnityEngine;
  using UnityEngine.Rendering;
  #if UNITY_6000_0_OR_NEWER && !UNITY_6000_5_OR_NEWER
  using UnityEngine.Experimental.Rendering;   // GSC is experimental before 6.5
  #endif
  #if UNITY_6000_0_OR_NEWER
  using Unity.Jobs;
  #endif

  // Put in a loading scene; start the gameplay scene when Done is true.
  public sealed class GlesShaderWarmup : MonoBehaviour
  {
      [SerializeField] ShaderVariantCollection[] variantChunks; // one chunk per frame
  #if UNITY_6000_0_OR_NEWER
      [SerializeField] GraphicsStateCollection traced;           // traced on device, GLES
      [SerializeField, Min(1)] int variantsPerFrame = 8;        // placeholder, no published value: tune to measured slack
      [SerializeField, Min(1)] int maxGscFrames = 600;          // placeholder safety cap, no published value
  #endif
      public bool Done { get; private set; }

      IEnumerator Start()
      {
          if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.OpenGLES3)
          { Done = true; yield break; }                          // Vulkan: unity-shader-hitches
  #if UNITY_6000_0_OR_NEWER
          // On 6000.0 below 55f1 leave `traced` empty and use `variantChunks` (U3-C4).
          if (traced != null)
          {
              int frames = 0;
              while (!traced.isWarmedUp && frames++ < maxGscFrames)
              {
                  JobHandle h = traced.WarmUpProgressively(variantsPerFrame, default(JobHandle));
                  yield return null;
                  h.Complete();
              }
              if (!traced.isWarmedUp)
                  Debug.LogWarning("GSC warmup did not complete on GLES; relying on SVC chunks (U3-C4).");
          }
  #endif
          if (variantChunks != null)
              foreach (var svc in variantChunks)
              {
                  if (svc != null && !svc.isWarmedUp) svc.WarmUp();
                  yield return null;                             // one chunk per frame
              }
          Done = true;
      }
  }
  ```
- **Effect:** removes in-gameplay spikes (p99, `shader_hitches`, stale
  frames); avg unchanged; load time rises by the moved compile cost.
- **Cost:** longer loading; a blocking warm freezes app frames, so keep a
  compositor-layer loading screen up (G3-022 note). Boost during loads:
  `quest-perf:quest-levels-thermal`.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `Unity ≥ 2021.3` (SVC) `Unity ≥ 6000.0.55f1 or ≥ 6000.1` (GSC, U3-C4, [verify on device]) | Goal: Consistency.

### 2. Cover the `STEREO_MULTIVIEW_ON` variants

- **Problem:** an Editor-recorded SVC holds non-stereo variants while the
  headset renders multiview, so warmup "works" and gameplay still hitches
  (GLES3-GF1-002, [community], Quest 2, 2020.3-2022.3).
- **Conflict:** Unity's 6000.0.0b11 note says stereo-instancing variants are
  not prewarmed by the legacy warmup APIs because they need a layered render
  target (U1-049, [doc]); forum users report that adding the keyword to the SVC
  fixed it (GLES3-GF1-002). Do both, then check: any post-warmup
  `Shader.CreateGPUProgram` with `STEREO_MULTIVIEW_ON` means it is still missed.
- **Change:** on 6.x, trace the GSC on the headset (keyword captured
  automatically). On 2021.3/2022.3, duplicate SVC entries with the keyword via
  `SvcAddMultiviewVariants` in [gles-code.md](references/gles-code.md) ([verify
  on device] that the variants exist in your build).
- **Effect:** removes residual hitches from Fix 1; no avg change. **Cost:**
  longer warmup (twice the variants in the worst case).
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `Multiview` `Unity ≥ 2021.3` | Goal: Consistency.

### 3. Warm the shader copy that actually renders (AssetBundles / Addressables)

- **Problem:** a shader referenced by the player's SVC and also built into a
  bundle exists twice; the bundle's copy compiles again on first use
  (GLES3-GF1-003, [community], Unity 2022.3.16f1, GLES3).
- **Change:** load the bundles first, then warm an SVC/GSC that lives in the
  same bundle as the shaders (Unity staff advice in the same thread). Remove
  duplicate shader inclusion from the player build.
- **Effect:** avg: unchanged; variance: removes first-use spikes that survive
  "working" warmup. **Cost:** warmup moves after bundle load.
- **Tags:** `Quest (model unstated)` `Unity 2022.3` `GLES` [verify on device] | Goal: Consistency.

### 4. Keep the blob cache from thrashing

- **Problem:** with AOSP defaults the cache is 2 MB total with random eviction
  and a 64 KB per-program ceiling (G3-011, G3-012). Many variants, or programs
  over 64 KB, recompile on every cold launch even with a cache file present.
- **Change:** cut variant count (stripping, `shader_feature` over
  `multi_compile`: `unity-perf:unity-shader-hitches`); check the cache file size
  against 2 MB after a full playthrough; keep Fix 1 running on every launch so
  evicted programs are rebuilt at load, not in gameplay (U3-096 note).
- **Effect:** fewer hitches from the second launch on; no avg change. No
  published size or ms number (KU-05, KU-08).
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` [verify on device] | Goal: Consistency.

### 5. Keep `half`/`real` at mediump, keep depth and positions at float

- **What Unity emits:** `half` -> `min16float` -> `mediump` on GLES (G3-028).
  URP Common.hlsl sets REAL_IS_HALF on mobile, so `real` is `half` (G3-029).
  HLSLcc emits `precision highp float;` as the default, so everything typed
  `float` stays highp (GLES3-GF1-007). `2.0h` is treated as float (G3-032).
- **Change:**
  - Player Settings > Other Settings > Shader Precision Model: "Platform
    default" or "Unified" (in Unified, samplers default to full precision
    unless declared e.g. `Texture2D<half4>`) (G3-028). 2021.3 wording: "Use
    full sampler precision by default, lower precision explicitly declared"
    (G3-028). The 16-bit precision page calls "Unified" "Uniform"; same
    setting (U3-C5).
  - Type color, lighting and normalized vectors `half`; keep world position,
    tiled UVs, `_Time` math and depth `float` (G3-031).
  - Sample depth with `TEXTURE2D_X_FLOAT` / `SampleSceneDepth` (G3-030). GLES
    has no reversed Z (`UNITY_NEAR_CLIP_VALUE -1.0`, G3-035): push the camera
    near plane out as far as content allows.
  - If one shader needs full-precision `real`, `#define PREFER_HALF 0` before
    the includes (G3-029). Paste-ready URP 14+ example: [gles-code.md](references/gles-code.md).
- **Effect:** mediump fragment math up to 2x faster and more power-efficient
  (G3-026); lowers average GPU time and power; Qualcomm says relaxed precision
  only "often" yields 16-bit code (G3-027), so confirm with Fragment ALU
  (Half) vs (Full) or Offline Compiler counts (G3-042). Mixing float literals
  into half math adds conversion instructions (G3-032).
- **Cost:** banding/jitter if positions, UVs or depth drop to fp16.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `URP 12+` | Goal: Throughput (and
  thermal headroom, which serves Consistency over long sessions).

### 6. Stay under Adreno per-shader cliffs on GLES

- **Change:** keep fragment shaders at or below 16 textures, and do not add
  SSBOs to a shader that already samples 16 (crosses the A7x textures+SSBOs
  line, G2-069). Keep under 16 samplers per pipeline on both headsets (G3-038).
  Pack interpolators (two `float2` UVs into one `float4`): every varying takes a
  full 4-component slot, and the GLES limit is 31 (G3-041). Split uber-shaders
  that approach each 2000-instruction multiple on Quest 3/3S (G3-037). GLES has
  no specialization constants, so uniform-branch uber-shaders raise GPRs;
  keywords trade that for more variants, more hitches and more blob-cache
  pressure (G3-039). UBO cliff (16) cannot be reached on GLES: the limit is 14
  per stage (G2-069).
- **Effect:** lowers average GPU time; no variance effect expected; no
  published ms per cliff, measure with Offline Compiler counts or Snapdragon
  Profiler % Wave Context Occupancy (G3-037). **Cost:** more
  variants or passes. Cost model: `arm-mobile-hw-perf:xr2-shader-cost-model`.
- **Tags:** `Quest 3/3S` (instruction, binding) `Quest 2` `Quest 3/3S` (samplers, varyings) `GLES` | Goal: Throughput.

### 7. Engine-owned program binaries (native plugins only)

- `GL_OES_get_program_binary` is on both headsets; Qualcomm recommends saving
  `glGetProgramBinary` blobs and reloading with `glProgramBinary` (G2-081/
  G3-015). Unity does not expose this to C#, so it only applies to programs a
  native plugin creates. Always check `GL_LINK_STATUS` after `glProgramBinary`
  and recompile from source on failure: OS updates change the driver (G3-016).
  Unity's own `UnityShaderCache/` is documented only for Embedded Linux
  (G3-017, KU-06).
- **Effect:** removes cold-launch compile of plugin-owned programs (variance/load time); no avg change; no published ms (G3-015 says only "significantly"). **Cost:** binary store invalidated per driver/OS build; always keep the source fallback.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `native plugin` | Goal: Consistency.

### 8. Do not rely on Meta's Shader Binary Cache

- SBC is marked deprecated (page updated Aug 7, 2026) while the GDC 2026 recap
  still promotes it (QUEST-GF1-C2); Unity apps are "not guaranteed" to be
  processed (U3-097). Keep in-app warmup regardless. Owner:
  `quest-perf:quest-sdk-choices`.
- **Effect:** none to count on; keep Fix 1. **Tags:** `Quest 2` `Quest 3/3S` `GLES` `Vulkan` | Goal: Consistency.

## Verify

- **Metric:** `Shader.CreateGPUProgram` count during a scripted gameplay route
  (Profiler, dev build) -> target 0 after warmup; `shader_hitches` and
  `stale_frame_count` in the OVR Metrics CSV; frames above 1.5× budget
  (G1-065 method).
- **Protocol:** run the same route (2-5 minutes, every material and effect on
  screen) four ways: cold without warmup, cold with warmup, warm without,
  warm with. Cold = cache file deleted (Diagnose step 3). Expect the cold/with
  run to match the warm/without run in gameplay; the difference moves into
  load time. No published magnitude: report measured counts and load ms.
- **After a Horizon OS update:** re-run cold/with once; `ro.build.id` changes
  wipe the cache (G3-014).
- **Precision fixes:** App GPU time at a pinned GPU level, three 60 s segments
  per variant, plus Fragment ALU (Half) vs (Full) or Offline Compiler counts.
  Thermal drift over 20-30 min: `quest-perf:quest-levels-thermal`.

## Pitfalls and myths

- **"No hitch on my headset."** Usually a warm cache. Test cold, and after
  every OS update (G3-014, Q1-011).
- **"The blob cache is 64 KB per app, raise it to 1 MB."** That is Arm's Mali
  integration guide (G3-018). AOSP: 64 KB per entry, 2 MB total, 32 MB
  multifile option (G3-C1). Trust AOSP and check the file on the device.
- **"`EGL_ANDROID_blob_cache` is missing, so there is no cache."** The
  extension is private to the Android EGL loader by spec, so its absence proves
  nothing; whether META-EGL keeps the cache is unresolved (GX-C5, KU-04).
- **"State changes cause recompiles."** General GLES driver advice (Khronos);
  Adreno does not recompile for state (G3-C5, G3-007). Only first use costs.
- **"SVC warmup is wrong, use GSC."** True on Vulkan (U3-082); on GLES, GSC
  falls back to SVC semantics anyway (G3-019).
- **Strict shader variant matching off hides stripping errors:** a missing
  variant silently becomes a "similar" one (no hitch, wrong keywords). Turn
  strict matching on in QA builds (G3-005).
- **Evicted variants recompile.** Unity drops an unreferenced variant from
  GPU memory; reusing it after a scene switch creates the program again
  (G3-003). Whether that hits the blob cache is undocumented [verify on device].
- **Shader Variant Loading chunk count** (Player > Other Settings, G3-004)
  trades resident decompressed shader memory against re-parse cost; no
  published number, compare `Shader.ParseThreaded` times.
- **"Unity emits ES 3.2 shaders."** Public HLSLcc emits `300 es`/`310 es` only;
  UUM-60833 made compute emit `320 es` on 6000.2+/6000.3, 6000.0 port status is
  inconsistent (GLES3-GF2-005, GX-C10). Check "Show compiled code" on your
  version. Details: `gles3-perf:gles-versions-unity-output`.
- **"half in a cbuffer saves bandwidth."** Stored at 32 bits (G3-033).
- **Framebuffer fetch reads are mediump** by default (`gl_LastFragData`), so an
  RGBA16F readback is fp16 at best (G3-034).

## Sources

All accessed 2026-09-24.

- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm-other.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/ScriptReference/ShaderVariantCollection.WarmUp.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/class-GraphicsSettings.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-memory.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/SL-Use16BitPrecisionInShaders.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/class-PlayerSettingsAndroid.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/embedded-linux-optional-features.html [doc]
- https://docs.unity3d.com/2019.4/Documentation/Manual/SL-DataTypesAndPrecision.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.GraphicsStateCollection.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.GraphicsStateCollection.WarmUpProgressively.html [doc]
- https://docs.unity3d.com/6000.1/Documentation/Manual/shader-prewarm.html [doc]
- https://unity.com/releases/editor/whats-new/6000.0.0 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.0b11 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.55f1 [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/GLES3.hlsl [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/Vulkan.hlsl [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl [doc]
- https://github.com/Unity-Technologies/HLSLcc/blob/master/src/toGLSL.cpp [doc]
- https://issuetracker.unity.com/api/v1.0/issues/9889 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [community]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html [doc]
- https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_blob_cache.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/OES/OES_get_program_binary.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_shader_framebuffer_fetch.txt [doc]
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/egl_cache.cpp [doc]
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/BlobCache.cpp [doc]
- https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/graphics/java/android/graphics/HardwareRenderer.java [doc]
- https://developer.arm.com/documentation/101897/0303/System-integration/Android-blob-cache-size-in-OpenGL-ES [doc]
- https://opengles.gpuinfo.org/displayreport.php?id=6387 [measured]
- https://opengles.gpuinfo.org/displayreport.php?id=8023 [measured]
- https://discussions.unity.com/t/shadervariantcollection-warmup-not-work-on-oculus-quest-2/920217 [community]
- https://discussions.unity.com/t/shader-warmup-doesnt-seem-to-be-working-on-quest-android/936926 [community]
- https://discussions.unity.com/t/vulcan-and-shadervariantcollection-warmup/700973 [community]
- https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ [doc]
- https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ [doc]
- https://developers.meta.com/horizon/blog/vulkan-for-mobile-vr-rendering/ [doc]
