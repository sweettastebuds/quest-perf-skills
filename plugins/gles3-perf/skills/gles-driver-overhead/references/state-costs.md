# GLES state costs, limits and streaming options on Quest

Companion to `gles3-perf:gles-driver-overhead`. All sources accessed 2026-09-24. Finding IDs refer to `research/gles3.md`, `research/quest.md`, `research/unity.md` and `research/arm-mobile-hw.md`.

## 1. Meta's draw-call state-cost study (G2-065, G2-066)

Setup: Quest 1, Unity 2018.1.6f1, single-pass stereo, multithreaded rendering off, ATW off. Source: https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ [measured]. Stale (2018); the only Quest GLES state-change cost data found (KU-23). Direction assumed to hold on Quest 2 and Quest 3/3S GLES [verify on device].

CPU side (G2-065):

| Change between draws | Per-draw CPU time |
|---|---|
| Redraw the same object | about 25% of drawing a different object |
| Mesh change | less than a material change |
| Material switch, same shader | +64% |
| More textures on the changed material | more cost (no figure) |
| Shader (program) switch | +175% |
| Texture size, filtering, compression | negligible CPU cost |

Sort order implied: shader, then material, then mesh.

GPU side (G2-066): mesh complexity outweighs material changes; a dependent texture read costs only slightly more than an independent one; polygons spanning several tiles add cost; blending costs more in linear colour space.

Unity dossier note (U3 section, draw calls): keep only the ordering (shader/variant switch > material switch > same-state redraw), which matches the SRP Batcher design. Re-measure with N quads using identical vs distinct materials vs distinct shaders on Quest 2, comparing render-thread time in the Profiler.

## 2. GL limits and per-shader thresholds (G2-069, G2-070)

Sources: https://opengles.gpuinfo.org/displayreport.php?id=6387 , https://opengles.gpuinfo.org/displayreport.php?id=8023 [community]; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]. Only 7 gpuinfo reports exist for these devices, so per-device availability is thin evidence (GLES3-GF1-005).

| Limit | Quest 2 | Quest 3 |
|---|---|---|
| GL_MAX_VERTEX_UNIFORM_BLOCKS | 14 | 14 |
| GL_MAX_FRAGMENT_UNIFORM_BLOCKS | 14 | 14 |
| GL_MAX_COMBINED_UNIFORM_BLOCKS | 84 | 84 |
| GL_MAX_UNIFORM_BLOCK_SIZE | 65536 | 65536 |
| GL_MAX_TEXTURE_IMAGE_UNITS | 16 | 16 |
| GL_MAX_VERTEX_UNIFORM_VECTORS | 256 | 256 |

Adreno 7x (Quest 3/3S) per-shader thresholds where performance cliffs are possible (G2-069 / G3-037 / G3-038): each multiple of 2000 instructions, 32 vertex buffers, 16 unique UBOs, 16 textures+SSBOs; samplers at N = 16 on A6x to A8x.

UBO performance budget (G2-070, A2-074): sum of all UBOs referenced by one shader under 0.9 × 8192 = 7372 bytes so they fit constant RAM. 65536 is a correctness limit only. Past the budget the compiler maps only provably accessed portions; dynamic indexing (including `unity_InstanceID`-indexed instancing arrays) defeats this. In Unity the combined size of `UnityPerDraw`, `UnityPerMaterial`, the global and light cbuffers is what counts [verify on device]. No Quest-specific number is published; check with the Adreno Offline Compiler.

## 3. Buffer streaming options (G2-071 to G2-073, G3-070, G2-C6)

| Option | GL mechanism | Fences | Available to | Notes |
|---|---|---|---|---|
| Orphan | `glBufferData(NULL, same size, same usage)` or `glMapBufferRange` + `GL_MAP_INVALIDATE_BUFFER_BIT` | none | native plugins; Unity's own path undocumented (KU-19) | driver hands out fresh storage and usually recycles blocks |
| Ring buffer | `glMapBufferRange` + `GL_MAP_UNSYNCHRONIZED_BIT`, non-overlapping writes, orphan on wrap | none if sized for frames in flight | native plugins | dossier's preferred Quest resolution of G2-C6 |
| Persistent mapping | `GL_EXT_buffer_storage` with `MAP_PERSISTENT_BIT_EXT` / `MAP_COHERENT_BIT_EXT`, fence per region | yes | native plugins; exposed on Quest 2 and Quest 3 (G3-070) | conflicts with Qualcomm's fence advice (G2-030, G2-C6); if unavoidable, poll without flushing mid-pass |

Batch rule (G2-072): if VBO contents must change mid-frame, batch all updates before any draw that uses the modified buffers; update, draw, update, draw may make the driver keep several copies of the whole VBO.

Sources: https://web.archive.org/web/20250118034434/https://www.khronos.org/opengl/wiki/Buffer_Object_Streaming [doc] (desktop-GL oriented; live URL returned 403); https://registry.khronos.org/OpenGL/extensions/EXT/EXT_buffer_storage.txt [doc]; Qualcomm mobile best practices [doc].

## 4. Unity API to GL call mapping (inferred, not documented)

| Unity API | Likely GL on GLES 3.x | Status |
|---|---|---|
| GPU instancing on materials, `Graphics.RenderMeshInstanced` | `glDrawElementsInstanced` (ES 3.0) | inferred (G2-075) |
| `Graphics.RenderMeshIndirect`, `CommandBuffer.DrawMeshInstancedIndirect` | `glDrawElementsIndirect` (ES 3.1) | inferred (G2-075); availability varies by Unity version |
| `CommandBuffer.DispatchCompute` with args buffer | `glDispatchComputeIndirect` | inferred; workgroup ≥ 64 rule applies (G2-080) |
| `Mesh.MarkDynamic` | "dynamic" GPU buffers, faster to update, possibly slightly slower to read | documented behaviour, GL calls undocumented (G2-073) |
| `GraphicsBuffer` + `UsageFlags.LockBufferForWrite` | NativeArray on GPU memory "if possible", otherwise CPU staging | documented behaviour, GL calls undocumented (G2-073, KU-19) |
| `GraphicsFence`, `AsyncGPUReadback`, `Texture2D.ReadPixels` | fence / flush / readback: pass split | G2-029; owned by `gles3-perf:gles-tile-load-store` |
| Oculus XR Low Overhead Mode | `GL_KHR_no_error` / `EGL_KHR_create_context_no_error` context | G1-043 / G2-079 |

Sources: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Mesh.MarkDynamic.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GraphicsBuffer.LockBufferForWrite.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GraphicsBuffer.UsageFlags.LockBufferForWrite.html [doc].

Confirm any row with a RenderDoc Meta Fork GL call trace of a development build (G3-073).

## 5. Low Overhead Mode history (Q4-057, Q4-058, G1-024)

- Added in Oculus XR 1.4.0; Oculus XR only (no OpenXR equivalent found, KU-43).
- Oculus XR settings path: Project Settings > XR Plug-in Management > Oculus (Android tab), Oculus XR 4.x on Unity 2021.3-6.4 (Q4-056).
- Oculus XR plugin deprecated from Unity 6.5; OpenXR Meta 2.1 on OpenXR 1.14 is at feature parity, and new Quest features go only to OpenXR (G1-024 / G2-093).
- Known issue: UUM-102878, OES external textures render black in release builds with Low Overhead Mode; Closed Won't Fix [community].

Sources: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc]; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102878 [community].

## 6. Open questions and how to measure them

| ID | Question | Method |
|---|---|---|
| KU-07 | Adreno driver CPU overhead, GLES vs Vulkan, on XR2 and XR2 Gen 2 | draw-call sweep (200, 500, 1000) comparing render-thread ms in Perfetto on both APIs, Low Overhead Mode on and off |
| KU-12 | Whether graphics jobs of any mode run on GLES Quest builds | log `SystemInfo.renderingThreadingMode` on a GLES build with Graphics Jobs ticked |
| KU-19 | Unity's GLES buffer-update strategy for constant buffers and dynamic VB/IB | GL call trace in RenderDoc |
| KU-23 | Post-2018 CPU cost per state change, program switch and texture bind on Quest GLES | native microbenchmark, or Unity draw sweep with material-switch patterns, timed in Perfetto |
| KU-43 | OpenXR equivalent of Low Overhead Mode | check OpenXR feature settings in your plugin version; A/B render-thread ms |
