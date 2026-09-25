# Android EGL blob cache, program binaries and cold-start testing on Quest GLES

Read this when you need the full cache limits, the device properties to log,
the cold/warm test protocol, or the rules for a native `glProgramBinary` cache.
All sources accessed 2026-09-24. Applies to OpenGL ES builds on Quest 2
(Adreno 650) and Quest 3/3S (Adreno 740); every current Horizon OS build is
Android 14 based (GLES3-GF1-006, UUM-149765 device list, [community]).

## 1. What caches exist

| Layer | Who writes it | Where | Survives | Source |
| --- | --- | --- | --- | --- |
| Android EGL blob cache (`EGL_ANDROID_blob_cache`) | Android EGL loader, automatically; app writes no code | `cache/com.android.opengl.shaders_cache` in the app's cache dir | app restarts; wiped on `ro.build.id` change, app cache/data clear | G3-009, G3-010, G3-014 [doc] [verify on device] |
| Unity GLES3 `UnityShaderCache/` | Unity player | `[TEMP]/[COMPANY]/[PROJECT]/UnityShaderCache/`, pre-seedable in `Data/UnityShaderCache/` | per Player build, identical HW/SW only | G3-017, U3-094 [doc]; documented only for Embedded Linux; Android use unknown (KU-06) |
| App-owned program binaries | a native plugin via `glGetProgramBinary` / `glProgramBinary` | anywhere the plugin chooses | until the driver rejects them | G2-081/G3-015, G3-016 [doc] |
| Meta Shader Binary Cache (SBC) | Meta backend, pre-warmed per headset type | manifest `com.oculus.sbcpath` | deprecated; Unity apps not guaranteed | QUEST-GF1-004, U3-097 [doc] |

Neither headset accepts precompiled shader binaries: `GL_NUM_SHADER_BINARY_FORMATS
= 0`, `GL_NUM_PROGRAM_BINARY_FORMATS = 1` (driver-opaque) on both (G1-008/G3-008,
gpuinfo 6387 and 8023, [measured]). Every program compiles on the device at
least once per driver or OS build.

## 2. AOSP limits

Values from AOSP `egl_cache.cpp` / `BlobCache.cpp` (main; same in 12, 14, 15).
Whether Horizon OS's META-EGL keeps these defaults is unverified (GX-C5, KU-04).

| Property | Monolithic (default) | Multifile |
| --- | --- | --- |
| Enabled when | always, unless multifile is on | `ro.egl.blobcache.multifile` = true (default false); `debug.egl.blobcache.multifile` and `*_limit` override on test devices |
| Max key | 12 KB | 1 MB |
| Max value (one program) | 64 KB; larger values silently not stored (verbose log only) | 8 MB |
| Max total | 2 MB | 32 MB |
| Max entries | not stated | 4096 |
| When full | random eviction until under half the maximum (1 MB) | not documented in the dossier |
| Invalidation | whole cache dropped when `ro.build.id` changes | same |

Sources: G3-011, G3-012, G3-013, G3-014.

Consequences:
- A program whose binary exceeds 64 KB recompiles on every cold launch
  (G3-011). No published binary size for URP Lit variants exists (KU-08).
- Hundreds of variants can thrash a 2 MB cache: some programs recompile every
  launch even though the file exists (G3-012).
- The first launch after every Horizon OS update is cold for every user
  (G3-014; Meta lists first run after install, after app update and after a
  driver/OS update as the shader-cache-building cases, U3-096).

### Conflict G3-C1: blob cache size

- Arm's Mali integration guide: about 64 KB per application by default,
  raise to 512 KB-1 MB (G3-018).
- AOSP source: 64 KB is the per-entry limit, 2 MB the monolithic total, 32 MB
  the multifile option (G3-011, G3-013).
- For Quest, use the AOSP figures and check the file on the device. Arm's page
  targets Mali integrators, not Quest.

### Conflict GX-C5 / KU-04: does META-EGL keep the loader cache?

- G3-009 assumes the AOSP loader cache is active.
- The EGL string on both headsets is `1.5 Android META-EGL` and
  `EGL_ANDROID_blob_cache` is not listed (G1-008). The spec makes the
  extension private to the loader, so its absence proves nothing.
- Unresolved. It is also unknown whether META-EGL keeps the cache across app
  updates. Method: the protocol in section 4.

## 3. Device properties and paths to log

Record these with every hitch capture:

```sh
adb shell getprop ro.build.id                  # cache invalidation key (G3-014)
adb shell getprop ro.build.version.release     # Android base, 14 expected (GLES3-GF1-006)
adb shell getprop ro.egl.blobcache.multifile   # empty/false = 2 MB monolithic (G3-013)
adb shell run-as <pkg> ls -l cache/            # debuggable builds only (G3-010)
adb shell ls -l /sdcard/Android/data/<pkg>/cache/   # Application.temporaryCachePath; UnityShaderCache? (G3-017)
```

Do not ship with `debug.egl.*` props set; they are a test-device setting
(G3-013 note).

## 4. Cold vs warm test protocol

Answers KU-04, KU-05, KU-06 and KU-08 for your build. Development build, Unity
Profiler attached (or OVR Metrics CSV for release builds).

1. Install the build. `adb shell am force-stop <pkg>`.
2. **Cold:** `adb shell run-as <pkg> rm -f cache/com.android.opengl.shaders_cache`
   (or `adb shell pm clear <pkg>`, which also clears saves and `UnityShaderCache/`).
3. Launch, run the scripted route (every material, effect, quality level on
   screen). Record: load time, `Shader.CreateGPUProgram` count and total ms
   during load and during gameplay, `shader_hitches`, `stale_frame_count`,
   frames above 1.5× budget (G1-065 method).
4. `ls -l cache/` again: file size after one run. Near 2 MB means you are at
   the monolithic ceiling (G3-011, G3-012).
5. Force-stop, relaunch without clearing (**warm**). Repeat step 3.
6. Warm `Shader.CreateGPUProgram` ms vs cold = what the blob cache saves
   (KU-05). A warm run that still shows the same programs compiling means the
   cache is absent, evicted, or the program is over 64 KB (KU-04, KU-08).
7. Install an updated APK of the same app over it and run warm again: tells
   you whether the cache survives app updates on META-EGL (KU-04).
8. After the next Horizon OS update, run once without clearing: expect cold
   behaviour (G3-014).

Measure program binary size precisely only from a native plugin
(`GL_PROGRAM_BINARY_LENGTH`), otherwise from cache-file growth per newly seen
variant (G3-011 note).

## 5. glProgramBinary rules (native plugins)

- `GL_OES_get_program_binary` is exposed on Quest 2 and Quest 3 (G2-081,
  gpuinfo 6387/8023).
- Qualcomm: save binaries with `glGetProgramBinary`, reload with
  `glProgramBinary`; "can significantly" shorten launch; no number given
  (G3-015).
- After `glProgramBinary`, check `GL_LINK_STATUS`; on failure compile from
  source and re-save. Binaries are rejected after driver updates, and Horizon
  OS updates change the driver (G3-016, G3-044).
- Key the store by `GL_RENDERER`/`GL_VERSION` strings plus your build, and
  drop it on mismatch; the driver strings differ per headset (V@0690 vs
  V@0837, G3-044).
- Unity does not expose its program objects to C#, so this does not help Unity
  shaders (G2-081).

## 6. Warmup API availability (GLES view)

| Unity | GLES warmup options | Notes |
| --- | --- | --- |
| 2021.3, 2022.3 | `ShaderVariantCollection.WarmUp`, `Shader.WarmupAllShaders`, `Experimental.Rendering.ShaderWarmup`, Preloaded Shaders | U3-092, G3-020; Meta's archived Unity-ShaderPrewarmer renders MeshRenderers 50-100 per frame at 1/60 s (U3-093) |
| 6000.0.0b15+ | adds `GraphicsStateCollection` (experimental namespace) | U3-083 |
| 6000.0.55f1+ or 6.1+ | GSC falls back to SVC warmup on GLES | conflict U3-C4: release notes 6000.0.55f1 (U1-048) vs manual "6.1 and later" (G3-019) |
| 6000.0.74f1, 6000.5.0b5 | repeated fallback log removed from release builds | U1-048 |
| 6.5+ | GSC in `UnityEngine.Rendering`; Graphics Settings "Collection Startup Behavior", cache-miss tracing | U3-083, U3-087, U3-088 |

On GLES the GSC `count` in `WarmUpProgressively` limits variants, not PSOs
(U3-086). Stereo-instanced variants are not prewarmed by the legacy APIs
(U1-049, 6000.0.0b11) while community reports fix SVC misses by adding
`STEREO_MULTIVIEW_ON` (GLES3-GF1-002): verify with post-warmup
`Shader.CreateGPUProgram` markers.

## Sources

All accessed 2026-09-24.

- https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_blob_cache.txt [doc]
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/egl_cache.cpp [doc]
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/BlobCache.cpp [doc]
- https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/graphics/java/android/graphics/HardwareRenderer.java [doc]
- https://developer.arm.com/documentation/101897/0303/System-integration/Android-blob-cache-size-in-OpenGL-ES [doc]
- https://registry.khronos.org/OpenGL/extensions/OES/OES_get_program_binary.txt [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://opengles.gpuinfo.org/displayreport.php?id=6387 [measured]
- https://opengles.gpuinfo.org/displayreport.php?id=8023 [measured]
- https://docs.unity3d.com/6000.5/Documentation/Manual/embedded-linux-optional-features.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm-other.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.GraphicsStateCollection.WarmUpProgressively.html [doc]
- https://unity.com/releases/editor/whats-new/6000.0.0b11 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.55f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.0.74f1 [doc]
- https://unity.com/releases/editor/whats-new/6000.5.0 [doc]
- https://github.com/oculus-samples/Unity-ShaderPrewarmer [doc]
- https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ [doc]
- https://discussions.unity.com/t/shadervariantcollection-warmup-not-work-on-oculus-quest-2/920217 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [community]
