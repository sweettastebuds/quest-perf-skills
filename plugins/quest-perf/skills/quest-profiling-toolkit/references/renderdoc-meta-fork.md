# RenderDoc Meta Fork on Quest

Applies to: Quest 2, Quest 3/3S on Horizon OS 68+. Accessed 2026-09-24.
GLES capture caveats (timer queries, v68.18 limits, AGI unsupported) are owned
by `gles3-perf:gles-vs-vulkan`; counter meanings by
`arm-mobile-hw-perf:xr2-gpu-counters-sdp`.

## Version and features

| Item | Value | ID |
|---|---|---|
| Version | 68.18 (download page updated Jul 28, 2026); needs Horizon OS 68+ | Q1-057 |
| New in 68.18 | CLI `--frame-number`, `--intent-args`; ships `renderdoc_mcp` | Q1-057 |
| Tile Timeline | Window > Tile Timeline: per surface render mode, bins, stage timings incl. LoadDS/StoreDS, VKLoadInput | Q1-058, A3-035 |
| Per-draw counters | Window > Performance Counter Viewer | Q1-058 |
| Shader stats | Vulkan only, via `KHR_pipeline_executable_properties` | Q1-058, Q1-063 |
| Validation | Vulkan only | Q1-058 |
| GL | supported except shader stats and validation | Q1-058 |
| Builds | Development builds required | Q1-058 |
| Agent skills | installed at `C:\Program Files\RenderDocForMetaQuest\.claude\skills` (optimization-agent, shader-optimization, vertex-optimization, isa-analysis, renderdoccmd-adb-capture) | Q1-064 |

Draw-call metric count conflict (Q1-C2, ARM-C16): overview page (Sep 9, 2026)
says "up to 48", 68.18 download page says "up to 59". Read the real number in
the Performance Counter Viewer.

Sources: https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ ,
https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ ,
https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-ai-tools/ [doc].

## Settings for profiling (Q1-059, A3-042)

https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ (updated Dec 15, 2024) [doc]

- Timer queries per render pass, not per draw: Adreno renders in tiles.
- Enable "Disable TimeWarp on replay".
- Replay optimisation level: Fastest.

## Capturing (Q1-060, A3-044)

https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-capture/ [doc]

- Store (non-debuggable) builds on API 34+ need JDWP, which needs root:
  `adb root; adb shell setprop persist.debug.dalvik.vm.jdwp.enabled 1; adb reboot`.
  On retail headsets, profile Development Builds [verify on device].
- A crash during capture usually means out of memory.
- Scripted CLI flow (A3-044):
  ```
  renderdoccmd adb-list
  renderdoccmd adb-launch-drawcall-profiling --device <SERIAL> --package <pkg>
  renderdoccmd adb-capture --device <SERIAL> --ident <IDENT> --frames 1
  ```
  Use `--frame-number` (68.18) to grab a chosen frame, for example just after a
  scene load.

## Render Stage view (Q1-061, A3-043)

https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc]

- Needs a replay context in profiling mode; briefly disables the proximity
  sensor.
- Quest 3 + Vulkan multiview: one surface, `multiple rendertargets` = 2, a
  foveation scale per view. GL multiview on Quest 3/3S: the page still has a
  TODO (unverified).
- Tile Browser: per-bin heatmap; use it to find expensive bins (heavy shader
  or dense overdraw in the centre) before choosing foveation or LOD.

## Draw-call metrics (Q1-062, A3-036 to A3-041)

https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ and
https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-drawcall/ [doc]

- Clocks (sort by this first).
- Stalls: % Vertex Fetch Stall, % Texture Fetch Stall, % Stalled on System Memory.
- Cache: L1 Texture Cache Miss Per Pixel, % Texture L1 Miss, % Texture L2 Miss, % Instruction Cache Miss.
- Primitives: Pre-clipped Polygon, % Prims Trivially Rejected, % Prims Clipped, Average Vertices/Polygon, Reused Vertices/Second, Average Polygon Area.
- Shader load: % Shaders Busy, Vertices/Fragments Shaded, Vertex/Fragment Instructions, Fragment ALU Instructions (Full/Half), Fragment EFU Instructions.
- Ratios: Textures/Vertex, Textures/Fragment, ALU/Vertex, ALU/Fragment, EFU/Fragment, EFU/Vertex.
- Time split: % Time Shading Fragments/Vertices, % Time Compute, % Shader ALU Capacity Utilized, % Time ALUs/EFUs Working.
- Filtering: % Nearest/Linear/Anisotropic Filtered, % Non-Base Level Textures, % Texture Pipes Busy.
- Memory (bytes): Read Total, Write Total, Texture Memory Read BW, Vertex Memory Read, SP Memory Read; Avg Bytes/Fragment (Meta calls it imprecise), Avg Bytes/Vertex. These are the only documented per-draw byte counters on Quest (A3-036).
- Preemption, Avg Preemption Delay.

`lowp` maps to 16-bit (Half). The Full/Half ALU split is the direct check
that HLSL `half` compiled to 16-bit (Q1-062 note).

Known error: "Failed to retrieve drawcall trace results. Received 0 metrics."
The page has a Quest 3 TODO next to it; status on current firmware unknown
[verify on device].

Bandwidth method (A3-037, a method built from documented metrics, not a Meta
recipe): sum Write Total across an eye-buffer pass's draws and compare with the
resolved-colour size; several times larger points to stored MSAA samples or
depth. Store traffic may be charged to the last draw in a bin or to none
[verify on device]. Capture byte counters in a separate pass from timing,
because Qualcomm marks them slow to trace (A3-055).

## Vulkan shader stats (Q1-063)

https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ (updated Dec 1, 2024) [doc]

Fields: Instruction Count All, ALU 32-bit / 16-bit, Complex, Texture Read,
Flow Control, Barrier/Fence, Short/Long Latency Sync, register footprints,
Scratch Memory, I/O components, Shader Processor Utilization %, Memory
Read/Write. Meta's guidance: texture read groups below 15; any scratch memory
means poor performance (register spill). Interpretation of these for HLSL:
`unity-perf:unity-shader-authoring`, `arm-mobile-hw-perf:xr2-shader-cost-model`.
