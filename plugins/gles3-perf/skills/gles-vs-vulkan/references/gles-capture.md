# Capturing and timing a GLES build on Quest

Read before profiling or capturing a GLES build, and before trusting any GL
timing in an API A/B. Generic tool recipes (ovrgpuprofiler, Perfetto, OVR
Metrics, RenderDoc install) are owned by `quest-perf:quest-profiling-toolkit`;
what Adreno counters mean is owned by `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
This file covers only what differs on GLES. IDs refer to `research/gles3.md`.

## Tool status on GLES at a glance

| Tool | GLES status | Main caveat | IDs |
|---|---|---|---|
| ovrgpuprofiler | Works; no API restriction documented | Detailed mode (`-e`) must be on before the app starts | G3-080 |
| RenderDoc Meta Fork 68.18 | Works on OpenGL and Vulkan | Development build; shader stats and API validation are Vulkan-only; profiling mode pins max clock | G3-073 to G3-078, GLES3-GF1-004 |
| Perfetto (MQDH) | No API restriction documented | Unity emits only ATrace events; add the package under ATrace Apps | G3-082 [verify on device] |
| `GL_EXT_disjoint_timer_query` | Exposed on both headsets | Sums over bins; forces a flush that defeats later invalidates; not allowed inside multiview | G2-034 / G3-068, G2-006 |
| Snapdragon Profiler | Unreliable; treat as unsupported unless proven on your OS build | Meta's page is 404; captures reported failing on Quest 3/3S, snapshots crashing on Quest 2 | G3-084, G3-085, GLES3-GF2-008 |
| AGI | Not usable on Quest | No Quest in the supported-device list; GLES frame profiling runs through ANGLE-on-Vulkan | G3-086 |
| GPU Systrace | Deprecated 2024-12-02 | Replaced by Perfetto; older guides are stale | G3-083 |

## ovrgpuprofiler on a GL build

```sh
adb shell ovrgpuprofiler -e          # detailed mode; start BEFORE the app, else restart it
adb shell ovrgpuprofiler -t2         # render-stage trace, 2 s (-t<seconds>; default 0.1 s)
adb shell ovrgpuprofiler -t2 -v      # per-bin stages
adb shell ovrgpuprofiler -m          # list metrics (47)
adb shell ovrgpuprofiler -d          # detailed mode off
```

UUM-149765 wrote `-t 2` with a space (G2-010); Meta documents `-t<seconds>` (G3-080) [verify on device].

Each surface line gives resolution, bit depths, MSAA, Mode (0 Direct,
1 HwBinning, 2 SwBinning, 3 HwDirect), bin count and size, ms, and stage
totals (G3-080). A GL eye buffer in Direct or SwBinning where HwBinning is
expected is a red flag (G3-080 note). How to read the Load*/Store* lines for
GLES tuning: `gles3-perf:gles-tile-load-store`.

`-x` per-draw traces add stalls; use them only to compare draws with each other
(owned by `arm-mobile-hw-perf:xr2-gpu-counters-sdp`).

## RenderDoc Meta Fork on GLES

- **Version:** 68.18 (released 2026-07-28) fixes an "Adreno timing hang" and adds `--frame-number` and `--intent-args`; profiling features need Horizon OS 68+. Whether the hang fix is GL-specific is not stated; update before profiling GLES content (GLES3-GF1-004). Use `--frame-number` to capture the same frame on both API arms.
- **Build:** development build. Non-debuggable builds need JDWP, which Android 14 disables; Meta's workaround needs root, unavailable on retail headsets (G3-073, G3-074).
- **Settings** (Tools > Settings) (G3-076):
  - Timer query type: keep the per-renderpass default; per-draw duration queries are inaccurate on tiled GPUs.
  - Enable "Disable TimeWarp on replay".
  - Replay optimisation level: Fastest, otherwise RenderDoc's inserted GL commands show up as phantom operations in render-stage traces.
- **Per-draw GL timings:** per-draw `time_elapsed` queries stall the GPU between draws within each tile and inflate GL timings; per-renderpass timestamps add no overhead. For per-draw GL cost use the draw-call trace counters and Tile Timeline stage times (G3-077; source blog 2020, stale).
- **Tile Timeline** (Window > Tile Timeline): per-surface stages in µs per tile (Binning, Render, LoadColor, StoreColor, LoadDS, StoreDS, Blit, Preempt; GLAsyncCompute is GL-specific), plus bin count and size and a draw-call trace with up to 48 metrics (G3-078). This is where the UUM-93226 store-per-bin evidence came from (G1-054, G1-080).
- **Profiling mode** costs 5-10% GPU and pins the GPU at max clock; absolute times are best-case clocks, not shipping clocks (G3-075; 2020 blog, stale). Compare deltas between arms, not against the frame budget.
- **Shader stats:** not available on GL in RenderDoc (Vulkan only, via `KHR_pipeline_executable_properties`). Use the Adreno Offline Compiler for GL shaders (G3-073); owned by `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
- **API log for MSAA path checks:** look for `glFramebufferTexture2DMultisampleEXT` / `glFramebufferTextureMultisampleMultiviewOVR` to confirm the implicit-resolve path (KU-18); interpretation in `gles3-perf:gles-tile-load-store`.

## Timer queries on a binner (in-app GL timing)

- `EXT_disjoint_timer_query` provides `TIME_ELAPSED_EXT` and `TIMESTAMP_EXT`; always check `GPU_DISJOINT_EXT` (G2-034 / G3-068).
- In binning mode a query sums over all bins; each timed draw adds about 2-5 µs per tile (G2-034 / G3-068, Qualcomm).
- On GLES a timer query forces a flush, and later invalidates are then ignored, so depth gets written to RAM: the measurement changes the thing measured (G2-006, Meta).
- `OVR_multiview` does not allow timer queries inside multiview rendering (G2-034).
- A5x+ trims the tail of the visibility stream, but a final full-screen draw defeats that (G2-034).
- **Conflict (GX-C9):** Qualcomm says to issue timer queries inside a render pass; Meta says a query forces a flush. Dossier resolution: inside the pass there is no extra flush, but the query still sums over bins. Rule for Quest: use ovrgpuprofiler stages or RenderDoc per-renderpass timestamps for per-pass cost, not GL timer queries (G2-034).

## Perfetto

MQDH Perfetto offers GPU Metrics, GPU Render Stage Trace, high-precision
render-stage tracing and a trace buffer size. Enter the app package under
ATrace Apps (Unity emits only ATrace events). Best tool for tying a
`Shader.CreateGPUProgram` hitch to GPU render stages on one timeline; raise the
buffer size if data drops (G3-082) [verify on device]. Whether GLES and Vulkan
render stages look different in Perfetto is unknown (KU-36).

## Snapdragon Profiler: conflict kept open

- Meta's 2020 Quest page (now 404) said: start SDP before the app, only apps declaring the OpenGL requirement appear, enable "OpenGL ES > Rendering stages", snapshots work (G3-084, pre-2023).
- Qualcomm's current guide still lists GLES trace and snapshot, with about 5% CPU overhead even when tracing only frame rate (G3-084).
- Meta's current Unreal debugging page names SDP generically as usable on Quest (GLES3-GF2-008).
- Community: does not work with Vulkan on Quest; snapshots crash on Quest 2; a Qualcomm forum thread reports nothing captured on Quest 3/3S (G3-085, [community]).
- Working position (GX-C11, G3-C4): optional secondary tool only. Try it on a development build: launch SDP before the app, enable "OpenGL ES > Rendering Stages", and fall back to `ovrgpuprofiler -t -v` if nothing is captured (KU-35).

## AGI and GPU Systrace

- AGI needs Android 11+ and a debuggable app, lists no Quest headset, and profiles GLES by running the app through a custom ANGLE build that translates to Vulkan, so its GL timings do not reflect Adreno's native GL driver. Last release v3.3.3 (2025-01-20) (G3-086).
- GPU Systrace is unsupported since 2024-12-02; use the Perfetto integration (G3-083).

## Sources

All accessed 2026-09-24.
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-capture/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc]
- https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ [doc]
- https://developers.meta.com/horizon/blog/renderdoc-for-oculus/ [doc] (2020-09-03; stale)
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ [doc]
- https://developers.meta.com/horizon/documentation/unreal/ts-gpusystrace/ [doc]
- https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android/ [doc]
- http://web.archive.org/web/20200513224546/https://developer.oculus.com/documentation/native/android/mobile-snapdragon-profiler/ [doc] (stale)
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_disjoint_timer_query.txt [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html [doc]
- https://mysupport.qualcomm.com/supportforums/s/question/0D5dK000009EniESAS/snapdragon-profiler-not-able-to-capture-anything-on-meta-quest-33s [community]
- https://peterthor.se/tag/qualcomm-snapdragon-profiler/ [community] (site unreachable on 2026-09-24; content seen via search snippets only)
- https://developer.android.com/agi/supported-devices [doc]
- https://developer.android.com/agi/frame-trace/frame-profiler [doc]
