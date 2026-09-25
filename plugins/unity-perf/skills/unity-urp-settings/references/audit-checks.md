# QuestPerfAudit.cs: check reference

Read this from `SKILL.md` when interpreting a line of the audit report
(`Logs/QuestPerfAudit.txt`) or deciding whether a WARN applies to your project. Each row
names the skill that owns the recommendation (the report prints it after `->`) and the
dossier finding it rests on (all accessed 2026-09-24).

Severity meaning:
- **FAIL**: contradicts a documented requirement or a clear Quest recommendation. `RunBatch`
  exits with code 1.
- **WARN**: costs frame time or risks a hitch in the common case; keep only with a written
  reason and a device measurement.
- **INFO**: reported for context, or the sources conflict and the audit cannot decide.
- **PASS**: matches the recommendation.

Limits (the script is UNTESTED, written without a Unity editor):
- Reads serialized asset values, not runtime-effective values. Build Profile overrides
  (6.1+), per-platform quality overrides and Quest capability flags are not applied.
- Fields it cannot find are skipped silently; missing lines are not a PASS.
- Cameras are checked only in scenes open in the editor.
- The refresh-rate check is a text search, not code analysis.

## Editor and Player

| ID | Check | FAIL / WARN rule | Owner | Finding |
|---|---|---|---|---|
| V00 | Editor version | report only | unity-perf:unity-version-matrix | - |
| V01 | 6.0 below 6000.0.66f2 | WARN | unity-perf:unity-version-matrix | U1-008 |
| V02 | 2022.3 below 35f1 with Graphics Jobs on | INFO (Legacy mode unavailable) | unity-perf:unity-cpu-scripting | A1-058 |
| P01 | Android Graphics APIs | WARN if Auto or Vulkan not first | gles3-perf:gles-vs-vulkan | U2-094, U2-091, G1-031, Q3-039 |
| P03 | Scripting backend | FAIL if not IL2CPP | unity-perf:unity-cpu-scripting | U5-021 |
| P04 | Target architectures | FAIL if no ARM64; WARN if ARMv7 included | unity-perf:unity-cpu-scripting | U5-021 |
| P05 | IL2CPP Code Generation | WARN if the size/build-time option | unity-perf:unity-cpu-scripting | U5-016 |
| P06 | IL2CPP compiler configuration | report only (no Quest guidance found) | unity-perf:unity-cpu-scripting | - |
| P07 | Android texture compression override | WARN if not ASTC and not "Don't override" | unity-perf:unity-memory-assets | U4-046, U4-053 |
| P08 | Color space | report only; GLES + Linear note | unity-perf:unity-urp-settings | U3-063, U1-063 |
| P09 | Multithreaded Rendering | FAIL if off | unity-perf:unity-cpu-scripting | A1-061 |
| P10 | Graphics Jobs and mode | report only | unity-perf:unity-cpu-scripting | A1-058, A1-059, A1-062 |
| P11 | Incremental GC | INFO if off | unity-perf:unity-cpu-scripting | U5-005, U5-006 |
| P12 | Vulkan swapchain buffers | WARN if not 3 | unity-perf:unity-urp-settings | U5-025, U1-068, X-C5 |
| P13 | Vulkan late acquire | WARN if on | unity-perf:unity-urp-settings | U5-025 |

## URP asset (one block per distinct asset in Graphics and every Quality level)

| ID | Check | FAIL / WARN rule | Owner | Finding |
|---|---|---|---|---|
| U00 | Any URP asset assigned | FAIL if none | unity-perf:unity-urp-settings | - |
| U01 | HDR | WARN if on; FAIL if on with 64-bit precision | unity-perf:unity-urp-settings | U2-002, U2-030, A2-014 |
| U02 | Depth Texture | WARN if on | unity-perf:unity-urp-settings | U2-003, U2-021 |
| U03 | Opaque Texture | WARN if on (adds MSAA note) | unity-perf:unity-urp-settings | U2-004, G2-017 |
| U04 | MSAA | INFO off; PASS 2x; WARN 4x; FAIL above 4x | unity-perf:unity-urp-settings | U2-006, A2-017, G2-039, G2-040, U2-093 |
| U05 | Upscaling Filter | WARN if FSR or STP | unity-perf:unity-urp-settings | U2-008 |
| U06 | Render Scale | report only | quest-perf:quest-resolution-foveation | U2-007, U2-047 |
| U07 | Store Actions | FAIL if Store (WARN on Unity 6, where Render Graph ignores it); PASS Discard | unity-perf:unity-urp-settings | U2-005, U2-C4 |
| U08 | Terrain Holes | WARN if on | unity-perf:unity-urp-settings | U2-011 |
| U09 | LOD Cross Fade | WARN if on without 2x2 Stencil | unity-perf:unity-urp-settings | U2-010 |
| U10 | Soft Shadows | WARN if on | unity-perf:unity-lighting | U2-009 |
| U11 | Volume Update Mode | INFO if Every Frame | unity-perf:unity-urp-settings | U2-015 |
| U12 | SRP Batcher | WARN if off | unity-perf:unity-draw-calls-batching | U2-016 |
| U13 | Additional lights mode / per-object limit | report only | unity-perf:unity-lighting | U2-012 |
| U14 | GPU Resident Drawer | WARN if on with GLES in the API list | unity-perf:unity-draw-calls-batching | U3-032, X-C9 |
| U15 | GPU occlusion culling on 6.5.0-6.5.7 | WARN | unity-perf:unity-upgrade-risks | U1-020 |

## Renderer data and renderer features

| ID | Check | FAIL / WARN rule | Owner | Finding |
|---|---|---|---|---|
| R00 | Renderer list readable / Universal Renderer | report only | unity-perf:unity-urp-settings | - |
| R01 | Rendering Path | FAIL if Deferred or Deferred+; GLES light-limit note on Forward+ | unity-perf:unity-urp-settings | U2-019, U1-034, U2-027, X-C6 |
| R02 | Depth Priming Mode | WARN if not Disabled | unity-perf:unity-urp-settings | U2-020, U3-058 |
| R03 | Depth Texture Mode with Depth Texture on | WARN if not After Transparents | unity-perf:unity-urp-settings | U2-021, G2-019 |
| R04 | Intermediate Texture | WARN if Always | unity-perf:unity-urp-settings | U2-023 |
| R05 | Native RenderPass | report only | unity-perf:unity-render-graph-tiling | U2-081, G2-022, U2-C4 |
| R06 | Active renderer features | WARN for SSAO, Decal, Full Screen Pass with fetchColorBuffer | unity-perf:unity-urp-settings | U2-028, U2-029, U2-026 |
| R07 | Tile-Only Mode (6.5+) | report only | unity-perf:unity-urp-settings | U2-025 |
| R08 | Tile-Only Mode with MSAA | WARN (conflict U2-C2) | unity-perf:unity-urp-settings | U2-006, U2-051, U2-C2 |
| G01 | Render Graph Compatibility Mode (6.0-6.3) | WARN if on | unity-perf:unity-render-graph-tiling | U1-025, U1-026 |

## Cameras (open scenes)

| ID | Check | FAIL / WARN rule | Owner | Finding |
|---|---|---|---|---|
| C00 | Camera count | report only | unity-perf:unity-urp-settings | - |
| C01 | Depth Texture override On | WARN | unity-perf:unity-urp-settings | U2-003 |
| C02 | Opaque Texture override On | WARN | unity-perf:unity-urp-settings | U2-004 |
| C03 | Post Processing on | INFO | unity-perf:unity-render-graph-tiling | U2-030, U2-091 |
| C04 | Non-default viewport rect | WARN | unity-perf:unity-urp-settings | U2-030 |

## XR

| ID | Check | FAIL / WARN rule | Owner | Finding |
|---|---|---|---|---|
| X01 | Android XR loaders | FAIL Oculus XR on 6.5+; WARN Oculus XR earlier; WARN none | unity-perf:unity-upgrade-risks | U1-091, U1-092 |
| X02 | OpenXR Render Mode | FAIL if multi-pass (doubles CPU draw submission; GPU delta disputed) | unity-perf:unity-urp-settings | U2-040, G2-C10 |
| X03 | OpenXR Depth Submission Mode | report only | quest-perf:quest-appsw | U1-092 |
| X04 | OpenXR Latency Optimization | report only (conflict) | quest-perf:quest-frame-pacing | Q2-076, U5-092 |
| X05 | Optimize Buffer Discards | report only | quest-perf:quest-appsw | Q3-069, U1-076 |
| X06 | Space Warp settings / motion-vector format | report only | quest-perf:quest-appsw | Q3-070, G1-033 |
| X07 | Foveation feature | report only | quest-perf:quest-resolution-foveation | U1-092 |
| X08 | Oculus XR Android stereo mode | FAIL if not Multiview | unity-perf:unity-urp-settings | U2-040 |
| X09 | Oculus XR Low Overhead Mode | report only | gles3-perf:gles-driver-overhead | - |
| X10 | AppSW on with OBD off | FAIL | quest-perf:quest-appsw | Q3-069, G1-031 |
| X11 | AppSW on without Vulkan first | FAIL | quest-perf:quest-appsw | G1-031 |
| X12 | Refresh-rate request present in Assets/*.cs | WARN if none found | quest-perf:quest-frame-pacing | Q2-010, Q2-011, Q2-012 |

`ERR` lines mean a section threw (usually an API that differs in your Unity version); the
rest of the audit still runs. Fix the reflection lookup for that section or check it by hand.
