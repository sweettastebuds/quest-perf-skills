# GLES limits and driver strings on Quest 2 / Quest 3 / Quest 3S

All values are device-reported capability dumps from opengles.gpuinfo.org (third-party submissions of real device queries, tagged [measured]) unless stated otherwise. Accessed 2026-09-24. The driver on any given headset depends on its OS build: query at runtime before relying on a value (G1-007 / G1-010 / G2-035).

Coverage gap: the gpuinfo database holds exactly 7 Quest reports. None is later than Jan 2023 for Adreno 650, and none is a Quest 3S or Quest Pro (GLES3-GF1-005). Quest 3S shares the Adreno 740v3 and UUM-149765 lists the same V@0837.0.7 GLES driver on a Quest 3S, so its limits should match Quest 3 on the same OS build [verify on device] (KU-11).

## 1. Driver strings

| Headset | Report | Report date | OS | GL_VERSION / driver build | Driver date |
|---|---|---|---|---|---|
| Quest 2 (Adreno 650) | #5092 | 2020-12-20 | - | V@0514.0 | 11/06/20 |
| Quest 2 | #5278 | 2021-04-03 | - | - | - |
| Quest 2 | #5808 | 2022-02-24 | - | V@0582.0 | 09/03/21 |
| Quest 2 | #6387 | 2023-01-13 | Android 12 | `OpenGL ES 3.2 V@0690.0` | 12/13/22 |
| Quest 3 (Adreno 740) | #7267 | 2024-03-29 | Android 12 | V@0757 (per G3 notes) | - |
| Quest 3 | #7475 | 2024-07-07 | Android 12 | V@0767.0 | 02/29/24 |
| Quest 3 | #8023 | 2026-02-20 | Android 14 | `OpenGL ES 3.2 V@0837.0.7 (GIT@3dbacedba8...)` | 01/12/26 |
| Quest 3S | none (UUM-149765 device list) [verify on device] | 2026 | Android 14, firmware v2.6 | GLES V@0837.0.7; Vulkan driver 512.837.7 (Vulkan 1.3.295) | - |

Sources: G1-001, G1-002, G1-004, G2-082, GLES3-GF1-006.

Common strings on both headsets (#6387, #8023):

- GL_SHADING_LANGUAGE_VERSION: `OpenGL ES GLSL ES 3.20`
- GL_VENDOR: `Qualcomm`; GL_RENDERER: `Adreno (TM) 650` / `Adreno (TM) 740`
- EGL_VERSION: `1.5 Android META-EGL` (Meta's own EGL layer over the Qualcomm driver; G1-003)
- Current OS base: Quest 2 on Android 14 (firmware 2.1.1034), Quest 3 on Android 14 (firmware 2.4.1031), per UUM-149765 (GLES3-GF1-006). The gpuinfo Quest 2 report predates this.

How to read the string on your headset (G2-082):

```sh
adb shell dumpsys SurfaceFlinger | grep GLES
# Windows PowerShell / cmd:
adb shell "dumpsys SurfaceFlinger | grep GLES"
```

Record the line with every capture. Qualcomm warns newer drivers may optimise anti-patterns away, so results move with OS updates (G2-082). "Legacy" does not mean frozen: the Quest 3 GLES driver moved from 02/29/24 to 01/12/26 and gained `GL_EXT_clear_texture` (G1-004, G3-071).

## 2. Version level and binaries

| Item | Quest 2 | Quest 3 | Finding |
|---|---|---|---|
| Highest ES level | 3.2 | 3.2 | G1-001, G1-002 |
| ES 3.1+AEP (`GL_ANDROID_extension_pack_es31a`) | yes | yes | G1-013 / G3-043 |
| Geometry / tessellation extensions | yes | yes | G1-013 / G3-043 |
| GL_NUM_PROGRAM_BINARY_FORMATS | 1 | 1 | G1-008 / G3-008 |
| GL_NUM_SHADER_BINARY_FORMATS | 0 | 0 | G1-008 / G3-008 |
| `GL_OES_get_program_binary` | yes | yes | baseline |
| `EGL_ANDROID_blob_cache` visible to apps | no (by design) | no (by design) | G3-009 |
| GL extensions (badge count) | 110 (V@0690) | 123 (V@0837); 122 in the 2024 reports | GX-C3 |
| EGL extensions (badge count) | 34 | 35 | GX-C3 |

Quest 3 (V@0837) is a strict superset of Quest 2 (V@0690): 13 more GL extensions plus `EGL_NV_context_priority_realtime` (G1-015 / G3-044). G1-015's "157 vs 143" totals do not match the badges; use the badge counts. The per-extension matrix is owned by `gles3-perf:gles-extensions-multiview`.

## 3. Resource limits

| Limit | Quest 2 | Quest 3 | Finding |
|---|---|---|---|
| GL_MAX_SAMPLES | 4 | 4 | G1-007 / G1-010 / G2-035 |
| GL_MAX_VERTEX_SHADER_STORAGE_BLOCKS | 4 | 12 | G1-005 |
| GL_MAX_FRAGMENT_SHADER_STORAGE_BLOCKS | 4 | 12 | G1-005 |
| GL_MAX_COMPUTE_SHADER_STORAGE_BLOCKS | 24 | 36 | GLES3-GF2-001 |
| GL_MAX_SHADER_STORAGE_BUFFER_BINDINGS | 24 | 36 | G1-005 |
| GL_MAX_COMPUTE_WORK_GROUP_INVOCATIONS | 1024 | 1024 | G1-006 |
| GL_MAX_COMPUTE_SHARED_MEMORY_SIZE | 32768 B | 32768 B | G1-006 |
| GL_MAX_VERTEX_UNIFORM_BLOCKS | 14 | 14 | G2-069 |
| GL_MAX_FRAGMENT_UNIFORM_BLOCKS | 14 | 14 | G2-069 |
| GL_MAX_COMBINED_UNIFORM_BLOCKS | 84 | 84 | G2-069 |
| GL_MAX_UNIFORM_BLOCK_SIZE | 65536 B | 65536 B | G2-069, G2-070 |
| GL_MAX_TEXTURE_IMAGE_UNITS | 16 | 16 | G2-069 |
| GL_MAX_VERTEX_UNIFORM_VECTORS | 256 | 256 | G2-069 |
| GL_MAX_FRAGMENT_UNIFORM_VECTORS | 256 | 256 | G2-069 |
| GL_MAX_COLOR_ATTACHMENTS / GL_MAX_DRAW_BUFFERS | 8 | 8 | G2-069 |
| GL_MAX_VARYING_VECTORS | 31 | 31 | G3-041 |
| GL_MAX_VIEWS_OVR | not in reports (KU-21) | not in reports | query at runtime |
| GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT | not captured (KU-30) | not captured | query at runtime |

Performance thresholds are not the same as these correctness limits:

- UBO size: 65536 B is a correctness limit only. Qualcomm's performance target is the sum of all UBOs referenced by one shader under 7372 B (90% of 8 KB) (G2-070, [doc] [verify on device]). Owner: `gles3-perf:gles-driver-overhead`.
- Adreno 7x (Quest 3/3S) per-shader cliffs at each multiple of 2000 instructions, 16 unique UBOs, 16 textures+SSBOs, 32 vertex buffers; samplers at N = 16 on A6x-A8x (G3-037, G3-038, G2-069). The GLES cap of 14 UBO blocks per stage sits below the UBO cliff; 16 texture units sit exactly at the textures+SSBOs cliff. Owner: `gles3-perf:gles-shader-binaries` and `arm-mobile-hw-perf:xr2-shader-cost-model`.

## 4. Unity-side mapping per version

| Unity | GLES setting surface | Manifest | ES 3.0 shaders | Finding |
|---|---|---|---|---|
| 2021.3 (URP 12) | no dossier source; check Player settings [verify on device] | - | - | - |
| 2022.3 (URP 14) | Auto Graphics API; Require ES3.1 / ES3.1+AEP / ES3.2 | added only with Auto on or OpenGLES3 listed | yes, unless Require ES3.1 ticked; GLES2 still present in 2022.3 | G1-016, G1-023 |
| 2023.1+ | same | same | GLES2 removed from engine and URP | G1-023 |
| 6000.0-6000.5 (URP 17) | same | same | unless Require ES3.1 ticked | G1-016 |
| 6000.5 | adds `UNITY_PLATFORM_META_QUEST`; Oculus XR plugin deprecated | - | - | G1-022, G1-024 |
| 6000.6 | "Use OpenGL ES 3.0 shaders" replaces Require ES3.1; `openGLRequireES31` getter always true, setter no-op | `glEsVersion 0x00030001`; no ES 3.0 context; irreversible | only if "Use OpenGL ES 3.0 shaders" on (auto-on for upgraded projects that never required ES 3.1) | G1-017, G1-018, U1-094 |
| 6000.7 | beta only at research time; docs match 6.6 | - | - | GX-C7 |

Features unavailable or shrinking on GLES (U1-095, U3-032): GPU Resident Drawer, GPU occlusion culling and STP never on GLES; Entities Graphics GLES support deprecated (6000.3.12f1, 6000.4.1f1); Tile-Only falls back on non-sRGB GLES backbuffers (6000.6.0b6).

## 5. Runtime query snippet (native side)

If you need a value Unity's `SystemInfo` does not expose (GL_MAX_VIEWS_OVR, anisotropy), query it from a native plugin on the render thread with `glGetIntegerv` / `glGetFloatv`, or dump `glGetStringi(GL_EXTENSIONS)` (KU-11, KU-21, KU-30). No published Quest value exists for these; measure on device.
