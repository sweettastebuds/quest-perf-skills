# Unity/URP feature-by-version matrix for Quest

Read this when you need the exact version, patch or plugin version at which a
Quest-relevant feature exists. Every cell is sourced; the IDs point to
`research/unity.md` (U1-, U2-, U3-, X-C) or `research/quest.md` (Q-, QUEST-).
All sources accessed 2026-09-24.

Legend: `-` = not available in that version. `n/a` = does not apply to Quest.
"same" = unchanged from the column to its left. A version cell names the first
alpha/beta/patch that carried the change where the dossier records it.
Headsets: all rows apply to Quest 2 and Quest 3/3S unless the row says otherwise.

Streams use 6000.N = 6.N. URP 17.6 for 6.6 is inferred from Graphics `master`
(no 6000.6/staging branch existed; U1-010).

## A. Support, platform and toolchain

| Feature | 2021.3 | 2022.3 | 6.0 | 6.1 | 6.2 | 6.3 | 6.4 | 6.5 | 6.6 | IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| URP version | 12.1 | 14.0 | 17.0 | 17.1 | 17.2 | 17.3 | 17.4 | 17.5 | 17.6 (inferred) | U1-010 |
| URP updatable apart from Editor | yes (package) | yes (package) | no: locked to Editor | no | no | no | no | no | no | U1-011 |
| Support on 2026-09-24 | out of public support; paid xLTS only | out of public support; paid xLTS only | LTS, ends Oct 2026 (latest 6000.0.84f1) | no patches (last 6000.1.17f1) | no patches (last 6000.2.15f1) | LTS to Dec 2027 (latest 6000.3.25f1) | no patches (last 6000.4.12f1) | no patches (last 6000.5.11f1) | supported until 6.7 ships (latest 6000.6.3f1) | U1-001..007, UNITY-GF2-005 |
| On Meta's supported path | no | no (Oculus XR path only, SDK ≤ v73) | only ≥ 6000.0.66f2 | yes (recommended) | yes | yes | yes | yes | yes | U1-008, U1-009 |
| Oculus XR plugin | yes | yes | yes (4.5.2 bundled as late as 6000.0.57f1) | yes | yes | yes | yes | deprecated 6000.5.0b4; not supported | not supported | U1-091, U1-C3 |
| Unity OpenXR plugin as Meta's path | - (Meta: Unity 6+ only) | - (Meta: Unity 6+ only) | yes: OpenXR 1.15.1 rec., Meta XR SDK v74+ | same | same (6000.2.0a10 bundles 1.14.3) | same | same | same | same | U1-009, U1-092 |
| Build Profiles | - | - | yes (replace Build Settings) | per-profile Graphics/Quality overrides | same | "Add Settings" UI, per-profile keyword shader exclusion | same | `CreateBuildProfile` API | same | U1-052 |
| Meta Quest build profile | - | - | - | yes (6000.1.0a2; optimal defaults 6000.1.0b14) | OpenXR default in profile (6000.2.0a9) | Mobile quality default (6000.3.0a5); quality defaults changed again 6000.3.14f1 | yes | yes | yes | U1-053, U1-055 |
| Profile defaults | - | - | - | Vulkan, min API 29, target API 32, IL2CPP, ARM64, SPI, aniso Per Texture | same | same | same | same | same | U1-053 / U3-070 |
| Engine minimum Android API | not verified | not verified | 23 | 23 | 23 | 25 | 25 | 26 (23-25 warn) | 26 | U1-097 |
| Android toolchain | not recorded | not recorded | Gradle 8.4, AGP 8.3.0, JDK 17 | Gradle 8.11, AGP 8.7.2, NDK r27c | not recorded | Gradle 9.1.0, AGP 9.0.0 | not recorded | not recorded | not recorded | U1-098 |
| GLES minimum | not recorded | not recorded | not recorded | not recorded | not recorded | not recorded | not recorded | not recorded | ES 3.1 (manifest 0x00030001; "Use OpenGL ES 3.0 shaders" transition toggle) | U1-094 |
| ARMv7 still in engine | yes | yes | yes | yes | yes | yes | yes | yes | yes (profile sets ARM64) | U1-096 |
| Vulkan Device Filter asset | - | - | - | yes | yes | yes | yes | yes | yes | U1-069 |
| `vulkanNumSwapchainBuffers` honoured | not recorded | not recorded | from 6000.0.83f1 | no | no | from 6000.3.24f1 | no | no | from 6000.6.0f1 | U1-068, X-C5 |
| Thin LTO for Quest profile | - | - | - | - | yes (6000.2.0a8) | yes | yes | yes | yes | U1-054 |
| CoreCLR player | - | - | - | - | - | - | - | - | - (6.7: experimental, desktop only) | U5-001 / U1-071 |

## B. Render pipeline and tile features

| Feature | 2021.3 | 2022.3 | 6.0 | 6.1 | 6.2 | 6.3 | 6.4 | 6.5 | 6.6 | IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Render Graph | - | - | default on; upgraded projects land in Compatibility Mode | same | same; AfterRendering now after final blit | Compatibility Mode hidden behind `URP_COMPATIBILITY_MODE` | only path (Compatibility Mode and define removed) | legacy RG compiler obsolete | only path | U1-023..026, U1-C5 |
| Native RenderPass toggle | yes (Vulkan; U2-081) | yes (Vulkan) | Compatibility Mode only | same | same | same (define only) | - | - | - | U2-081 / U1-027, U2-089 |
| Forward+ | - | yes; XR completeness unresolved (U1-C4); foveation in F+ from 2022.3.16f1 | yes, incl. XR | `_FORWARD_PLUS` deprecated for `_CLUSTER_LIGHT_LOOP` (shim) | same | same | same | same | same | U1-032, U1-033, UNITY-GF2-C1 |
| Deferred+ (not recommended on Quest) | - | - | - | yes | yes | yes | yes | yes | yes | U1-034 |
| On-tile post-processing | - | - | - | - | - | XR only, Vulkan (6000.3.0b3), renderer feature | same | all platforms; needs Tile-Only Mode or silently falls back | same; falls back on non-sRGB GLES backbuffer (6000.6.0b6) | U2-074 / U1-062, U2-075, X-C10 |
| Tile-Only Mode | - | - | - | - | - | - (on-tile only on Universal Renderer from 6000.3.23f1) | - | yes (On-Tile Validation 6000.5.0a5) | yes | U2-025 / U1-063 |
| Depth as input attachment | - | - | - | - | - | - | - | - | yes (DX12/Vulkan) | U2-079 / U1-065 |
| MSAA in-shader resolve (`VK_QCOM_render_pass_shader_resolve`) | - | - | - | - | yes | yes | yes | yes | yes | U2-052 / U1-043 |
| Visible Triangle Mesh (post only on visible pixels) | - | - | - | - | yes | yes | yes | yes | yes | U2-052 |
| UberPost final-pass colour-load fix (UUM-140408) | - | - | - | - | - | not found | - | from 6000.5.11f1 | yes (6000.6.0f1) | U1-064 |
| STP upscaler | n/a | n/a | n/a (not in XR) | n/a | n/a | n/a | n/a | n/a | n/a (XR table: No) | U1-042 |
| Adaptive Probe Volumes | - | - | yes (per-vertex quality option) | yes | yes | yes | yes | yes | yes | U1-041 |
| Meta Quest shader optimizations (`UNITY_PLATFORM_META_QUEST`) | - | - | - | - | - | - | - | yes (6000.5.0a3) | yes + 3 micro-opts; `DistanceAttenuation` 3-arg on Quest | U3-066 / U1-036, X-C7, U1-038 (U2-056 dated these to 6.1+; X-C7 resolved: build profile 6.1+, optimizations 6.5+) |
| Shader Build Settings (Keyword Declaration Overrides, `dynamic_branch` override) | - | - | - | - | - | yes | yes | yes | yes | U3-074 |
| Shader Constant Defines per build profile | - | - | - | - | - | - | - | - | yes | U3-075 / U1-051 |
| Multiview Render Regions (Vulkan, Symmetric Projection) | - | - | - | Final Pass (Oculus 4.6+ / OpenXR 1.14+) | All Passes with OpenXR 1.15+ | requires Render Graph; per-pass opt-in | same | same | same | U3-050 / U2-053 |
| Automatic viewport dynamic resolution | - | - | - | - | - | yes, OpenXR 1.16+, not in Compatibility Mode | yes | yes | yes | U2-048 / U1-044, Q3-059 |
| SRP Foveation (OpenXR) | - | - | yes | yes | yes | yes | yes | yes | yes | U1-085, U1-092 |
| Foveated post (UberPost, FinalPostBlit) | - | - | from 6000.0.22f1 | yes | yes | yes | yes | yes | yes | U1-082 |
| VRS API (Quest support unconfirmed) | - | - | - | yes | yes | + Frame Debugger inspection | yes | yes | yes | U1-061 |
| Mesh LOD | - | - | - | - | yes | yes | inspector preview | Entities Graphics support | yes | U1-059, U1-060 |

## C. Batching and GPU-driven rendering

| Feature | 2021.3 | 2022.3 | 6.0 | 6.1 | 6.2 | 6.3 | 6.4 | 6.5 | 6.6 | IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SRP Batcher | yes | yes | yes | yes | yes | yes | yes | yes | yes | U3-009 / U1-012 |
| BatchRendererGroup | experimental, old API | yes (Vulkan SSBO, GLES UBO window) | yes | yes | yes | yes | yes | yes | yes | U3-026 / U1-013, U1-014 |
| GPU Resident Drawer | - | - | Vulkan only (GLES n/a), Forward+ | + Deferred+ allowed | same | same; 16 KiB cbuffer fix 6000.3.3f1 (6.0: 6000.0.65f1) | Rendering Statistics rebuilt | same | GRD Profiler telemetry | U3-032 / U1-016, U1-015, U1-021, X-C9 |
| GPU occlusion culling | - | - | Vulkan only, needs GRD and Render Graph (single-pass XR from 6000.0.0b12) | same | same | same | same | broken 6.5.0-6.5.7 (UUM-146214), fixed 6000.5.8f1 | fixed from 6000.6.0f1 | U3-037 / U1-019, U1-020 |
| Dynamic batching | yes | yes | yes | yes | yes | yes | yes | yes | obsolete | U1-022 |
| Entities Graphics on GLES | not recorded | not recorded | not recorded | not recorded | not recorded | deprecated 6000.3.12f1 | deprecated 6000.4.1f1 | deprecated | deprecated | U1-095 |

## D. PSO warmup and shaders

| Feature | 2021.3 | 2022.3 | 6.0 | 6.1 | 6.2 | 6.3 | 6.4 | 6.5 | 6.6 | IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GraphicsStateCollection | - | - | experimental (6000.0.0b15, `UnityEngine.Experimental.Rendering`); SVC fallback 6000.0.55f1 | same | same | utility methods, overrides | edit without re-trace; states from Mesh/Material | `UnityEngine.Rendering` namespace, cache-miss tracing, auto trace/prewarm settings (6000.5.0a9) | same | U3-083 / U1-045, U1-046, U1-048 |
| Vulkan GSC warmup fix (UUM-121231) | - | - | conflict X-C1 | conflict X-C1 (stream unpatched) | conflict X-C1 (stream unpatched) | conflict X-C1 | yes (6000.4.0a4) | yes | yes | U1-047, U3-091, X-C1 |
| Legacy warmup covers stereo-instanced variants | not recorded | not recorded | no (UUM-54697) | no | no | no | no | no | no | U1-049 |
| `VariantsUploadedToGpuLastFrame` | - | - | - | - | - | - | - | yes | yes | U3-084 |

## E. XR plugins, frame timing, tooling

| Feature | 2021.3 | 2022.3 | 6.0 | 6.1 | 6.2 | 6.3 | 6.4 | 6.5 | 6.6 | IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AppSW, Meta path (Meta URP fork, OVRPlugin v34+, Vulkan) | - | 2022.3.15f1+ | 6000.0.9f1+ | fork branch `6000.0/oculus-app-spacewarp` covers 6.0-6.3 | same | same | 6000.4.0f1+ (`6000.4/...` branch) | Meta page lists no newer branch | same | Q3-064 |
| AppSW, Unity-native path (OpenXR 1.11+, URP 17.0.3+, Render Graph, Vulkan) | - | - | - | yes (6000.1.13f1+ for right-handed NDC with OpenXR 1.15.1+) | yes | yes | yes | yes | yes | Q3-065 |
| AppSW motion-vector coverage in URP | - | - | background MV fix 6000.0.54f1 | Shader Graph (6000.1.0a8) | same | matrices fix 6000.3.0b3 | same | UI and transparents (6000.5.0b1) | TextMeshPro (6000.6.0b6) | U1-070 |
| OpenXR predicted frame time fix / tile size to runtime | - | - | - | - | predicted time fix (6000.2.0a4) | tile size passed (6000.3.0a5/0b1) | yes | yes | yes | U1-067 |
| Adaptive Performance | not recorded | not recorded | Android provider | same | same | core module | same | same | OpenXR support (Basic provider) | U1-073 |
| FrameTimingManager GPU time from OpenXR | - | - | - | - | - | - | - | - | yes (6000.6.0b1); manual still says Partial (X-C3) | U1-057, X-C3 |
| Frame Debugger on device | no (mock HMD only) | no | no | no | no | no | no | no | no | U1-058, X-C2 |
| Project Auditor | package 1.1.0 | package 2.0.0 | package 3.1.1 | 3.1.1 | 3.1.1 | 3.1.1 | in Editor | flags obsolete APIs between versions | URP Settings Analyzer | U1-056 / U5-099 |

## F. 6.7 (beta only; do not ship)

6000.7.0b2 (2026-09-23) is the newest build; 6.7 LTS is targeted for the end of
2026 (U1-002, UNITY-GF2-006, QUEST-GF1-002). Entries to recheck when it ships;
make no performance claim from them:

- on-tile support for the URP deferred renderer (first seen 6000.7.0a2, U1-034);
- URP keywords switchable to dynamic branch;
- XR shader resolve fix in on-tile post (UUM-143511);
- Deferred soft-shadow "variant not found" fix on Quest (UUM-147509, U1-035), with no 6.3/6.6 backport found;
- GRD batching stats and "GRD Batches" Profiler chart (6000.7.0a3, U1-021);
- CoreCLR as an experimental desktop-only player; Android unsupported (U5-001 / U1-071).
