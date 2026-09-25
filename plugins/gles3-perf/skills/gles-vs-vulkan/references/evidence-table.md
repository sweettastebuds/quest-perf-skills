# GLES vs Vulkan on Quest: evidence table

Every published comparison and claim found by the gles3 and unity dossiers
(accessed 2026-09-24). Finding IDs refer to `research/gles3.md` (G*, GX-*,
GLES3-GF*) and `research/unity.md` (U*). Grades: [doc] vendor or engine
documentation, [measured] a source reporting its own timing with a stated
setup, [community] forum or tracker discussion. "Favours" is the API that was
faster in that source, not a general verdict.

## 1. Measured GPU / FPS comparisons

| # | Source | Device | Unity / pipeline | Setup | Numbers | Favours | Grade | IDs |
|---|---|---|---|---|---|---|---|---|
| 1 | UUM-149765 (Open, updated 2026-09-24) | Quest 3/3S (Adreno 740, GLES V@0837.0.7) | 6000.0.81f1, 6000.3.21f1, 6000.5.7f1, 6000.6.0b7, 6000.7.0a4 | ovrgpuprofiler; gpu/cpuLevel 3; OBD on; 63 bins of 192x256 at 4x | GLES off/4x 9.7/13.0 ms; Vulkan off/4x 9.1/14.1 ms. 4x delta +3.3 GLES vs +5.0 Vulkan. StoreColor GLES 0.04 to 0.15, Vulkan 0.18 to 0.45 ms | GLES at 4x, Vulkan with MSAA off | [measured] | G2-039, G2-041 |
| 2 | UUM-149765 notes | Quest 2 (Adreno 650) | 6000.x | as above | Vulkan ~14 ms off, ~21 ms 4x; GLES within ~1 ms | neither | [measured] (approximate) | G2-040 |
| 3 | Thread 1561926, first post 2024-11-29 | Quest 2, Quest 3 | 2022.x and 6000.0; URP, 4x MSAA, Entities Graphics, Forward+ | RenderDoc tile timeline | Vulkan 6+ ms extra per frame; 8 alternating StoreColor/StoreDepthStencil per bin at ~15 µs each vs 1 colour store at ~2-3 µs on GLES; MSAA raised bins from ~16-18 to ~63-66; without MSAA gap 1-2 ms with 4 stores per bin; Vulkan often below 60 fps at a 72 fps target | GLES | [community] | G1-054 |
| 4 | Thread 1561926, 2025-04-24 | Quest 3 | 2022.3.61f1, Built-in RP | GPU utilisation | 25% GLES vs 44% Vulkan | GLES | [community] | G1-056 |
| 5 | Thread 1561926, 2025-12-19 to 2026-01-12 | Quest 3 | custom SRP | RenderDoc Tile Timeline | Extra ~1.5 ms render-to-system-memory blit on Vulkan only, no matching API command; gone on GLES3 with identical code and MSAA off | GLES | [community] | G1-056 |
| 6 | UUM-30269 (Closed Won't Fix; ports closed 2026-05-06) | Quest 2 (Android 10) | 2022.2.9f1, ECS 1.0.0-pre.44; also 2020.3.46f1, 2021.3.20f1, 2023.1.0b5 | Unity QA repro | 72 fps GLES3 vs 50 fps Vulkan | GLES | [community] | G1-057 |
| 7 | Thread 938162, 2024-01-20 | Quest 3 | 2022.3.17f1, baked lighting, no post, ASTC | GPU-bound; **confounded**: Vulkan had OBD + Symmetric Projection + FFR, GLES had Low Overhead Mode | 72 Hz: ~46 Vulkan vs ~63 GLES fps; 90 Hz: ~44 vs ~60 | GLES (confounded) | [community] | G1-059 |
| 8 | Thread 1203082 | Quest 2 | 2021.2, Oculus XR 3.0-preview, graphics jobs on | | 72 fps GLES vs 24-36 fps Vulkan; `EarlyUpdate.XRUpdate` ~85% of the frame. Traced to URP PR #4488 (MSAA depth copy / depth prepass) reverted for GLES3 only by PR #4705. Fixes reported: depth texture + depth priming off, Deferred to Forward (2021.3.10f1, URP 12.1.7), or back to 2020.3.26f1 / URP 10.8.0 where a poster found Vulkan faster | GLES (pre-2023; stale) | [community] | G1-061 |
| 9 | Thread 1322298 | Quest 2 | 2021.3.8, 4x MSAA, no depth/opaque textures, no post | App GPU time | 4-6 ms GLES vs 15 ms Vulkan | GLES (pre-2023; stale) | [community] | G1-062 |
| 10 | UUM-93226 QA notes | Quest 2, Quest 3 (device OS field 12) | 2022.3.56f1, 6000.0.33f1 (+ found-in 6000.1.0b2, 6000.2.0a1, 6000.3.0a1) | OpenXR and Oculus XR; Multi-pass, Multiview, SPI made no difference | Vulkan lower FPS and "much more stutter"; also occurs on GLES; MSAA off on the camera rig: ~30 fps (API unstated) and the stutter stopped. No FPS numbers in the tracker text | GLES (qualitative) | [community] | G1-049, G1-052, G1-066, U1-074 |
| 11 | Thread 1561926, 2024-12-11 | Quest 2, Quest 3 | | | Vulkan sometimes better for no clear reason; results differed between a clean install and later runs (warm-up / cache effect) | mixed | [community] | G1-067 |
| 12 | Discussion #6223, Unity staff 2023-07-20 | Quest | 2022.2 / 2023 trunk | | Vulkan slower than GLES3 "in many scenarios", being addressed; inconsistent across projects. No closing follow-up found | GLES | [community] | G1-060 |
| 13 | Thread 1561926, Unity staff 2024-12-09 | | URP 17 / Unity 6 | internal tests, no numbers | Vulkan on par with GLES when the renderer minimises colour/depth stores (Render Graph) | parity | [community] | G1-055 |

Coverage gap: every comparison is on Quest 2 or Quest 3 (UUM-149765 adds a
Quest 3S). Versions covered: 2021.2, 2021.3.8, 2022.2.9, 2022.3.17, 2022.3.56,
2022.3.61, 6000.0.33 and the UUM-149765 eye-buffer-only set. Nothing tests
Unity 6.1-6.6 with OBD + Symmetric Projection + MRR + on-tile post, the
configuration Unity and Meta recommend (G1-077, KU-16).

## 2. Vendor claims (no independent measurement)

| Claim | Applies to | Grade | IDs |
|---|---|---|---|
| Vulkan recommended, "lower overhead" (no number); GLES "legacy", no new features, still supported | all Quest | [doc] | G1-028 |
| Vulkan "the required graphics API" (Advanced GPU Pipelines page); Unity's Meta Quest build profile defaults to Vulkan | current Quest development | [doc] | U2-094, G2-C1 |
| No store/VRC rule requiring Vulkan found | store submission | [doc] | G1-030, KU-14 |
| Unity: "Use the Vulkan API" is step 1; Vulkan more stable and faster than GLES in URP XR | Unity ≥ 6000.0, URP | [doc] | G1-040 |
| Qualcomm: "Prefer Vulkan to OpenGL ES" | Adreno | [doc] | G3-C3 |
| AppSW: up to 70% more compute budget ("initial testing") | Vulkan only | [doc] [verify on device] | G1-032 |
| Symmetric Projection: 5-15% in GPU-bound scenes | Vulkan + Multiview | [doc] [verify on device] | G1-037 |
| MRR: 3-8%; no gain with intermediates / post | Unity ≥ 6000.1, Vulkan | [doc] [verify on device] | G1-039 |
| Legacy Graphics Jobs: up to ~2 FPS in major projects | Unity 2022.3.35f1+, Vulkan | [doc] | G1-026 |
| 2020 blog: ~10% CPU render cost improvement, no GPU gain in nearly all cases; depth resolve 1-3 ms; MSAA +150-250 MB; graphics jobs unstable | Unity 2019.3-era, Quest 1 | [doc] (pre-2023; stale) | G1-047 |
| 2019 blog: wrong MSAA store/load/resolve setup ~3 ms GPU; precompiled SPIR-V speeds loading | Quest 1 era | [doc] (pre-2023; stale) | G1-046 |

## 3. Vulkan-only and GLES-only features

| Feature | API | Requirement / value | Owner skill | IDs |
|---|---|---|---|---|
| AppSW | Vulkan | Unity 2022.3.15f1+ / 6000.0.9f1+ / 6000.4.0f1+ (Meta path), OVRPlugin v34+, OBD required | `quest-perf:quest-appsw` | G1-031 |
| Late Latching | Vulkan | latency; negligible overhead per Meta | `quest-perf:quest-frame-pacing` | G1-036 |
| Symmetric Projection | Vulkan + Multiview | 5-15% claim | `quest-perf:quest-sdk-choices` | G1-037 |
| Optimize Buffer Discards | Vulkan | ~90 MB/eye Quest 3, ~66 MB/eye Quest 2 at 4x; UUM-93226 workaround | `quest-perf:quest-sdk-choices` | G1-038 |
| Multiview Render Regions | Vulkan | Unity 6.1+, Oculus XR 4.6 or OpenXR 1.14, Multiview + Symmetric Projection | `quest-perf:quest-sdk-choices` | G1-039 |
| Memoryless render textures / on-tile XR post intermediates | Vulkan (or Metal) | without them, an extra final blit | `unity-perf:unity-render-graph-tiling` | G1-041, GLES3-GF1-001 |
| Depth input attachments | Vulkan (or DX12) | URP 17 | `unity-perf:unity-render-graph-tiling` | G1-042 |
| Dynamic foveation, Subsampled Layout | Vulkan | OpenXR 1.19+ (dynamic); OpenXR 1.9.0+ (subsampled) | `quest-perf:quest-resolution-foveation` | GLES3-GF2-006, G1-035 |
| ETFR | Vulkan + Multiview + ARM64 | Quest Pro only; out of scope | - | G1-034 |
| Graphics Jobs Mode (Native / Legacy / Split) | Vulkan | Graphics Jobs on | `unity-perf:unity-cpu-scripting` | G1-025 |
| Unity OpenXR plugin on Quest | Vulkan | lists Quest as Vulkan-only | `quest-perf:quest-sdk-choices` | G1-024 / G2-093, G2-C8 |
| GRD, GPU occlusion culling, STP | not on GLES | never available on GLES | `unity-perf:unity-draw-calls-batching` | U1-095 |
| Entities Graphics on GLES | deprecated | 6000.3.12f1, 6000.4.1f1 | - | U1-095 |
| Tile-Only mode | falls back on non-sRGB GLES backbuffers | 6000.6.0b6 | `unity-perf:unity-render-graph-tiling` | U1-095 |
| Low Overhead Mode | GLES only | Oculus XR 4.x (deprecated from 6.5); UUM-102878 black OES external textures in release builds | `gles3-perf:gles-driver-overhead` | G1-043 / G2-079 |

## 4. Hitching, CPU overhead, tooling, stability, support

| Criterion | What exists | Grade | IDs |
|---|---|---|---|
| Hitching / pacing | Unity QA: more stutter on Vulkan in the MSAA repro; no PSO-vs-program-link numbers; GLES always compiles GLSL on device (no shader binary formats) | qualitative | G1-065, G1-066, G1-073 |
| CPU / driver overhead | "Lower overhead" with no number; ~10% (2020); no Qualcomm number for XR2 / XR2 Gen 2 | vendor claim | G1-068, G1-071 |
| Tooling | Both APIs capturable (RenderDoc Meta Fork, ovrgpuprofiler, Perfetto); RenderDoc shader stats and validation Vulkan-only; GL timer queries distort tiled timings; SDP unreliable; AGI unsupported | [doc] / [community] | G1-074, GX-C9 |
| Stability | Unity docs: Vulkan more stable. Tracker: UUM-93226 and UUM-30269 closed Won't Fix without fixes. GLES XR bugs on 6000.x closed Won't Fix: UUM-70930, UUM-109377, UUM-102876, OXPB-144, UUM-102878; UUM-91896 fixed | conflicting | G1-075, G1-C5 |
| Future support | GLES legacy with no new features; Oculus XR deprecated from 6.5; Unity 6.6 raises GLES floor to 3.1 rather than removing GLES; Quest 3 GLES driver still updated (V@0767 2024-02-29 to V@0837.0.7 2026-01-12); no end date | [doc] / [measured] | G1-076, G1-017, G1-004 |

## 5. UUM-93226 status record

| When | Status | Source |
|---|---|---|
| Created 2025-01-17 | not a regression; found in 2022.3.56f1, 6000.0.33f1, 6000.1.0b2, 6000.2.0a1, 6000.3.0a1; "Reproducible on" line reads 2022.3.56f1, 6000.0.33f1, 6000.0.0b2 (both lists genuine, different fields) | G1-049, GX-C1 |
| Feb 2025 | Active / Under Consideration | G1-050 (Wayback) |
| By Dec 2025 | Third Party Issue; note: Qualcomm visibility-stream bug with many meshes, fix expected in a future Meta OS; remaining copies are "Qualcomm's cost of using Vulkan"; workaround OBD | G1-051, U1-075 |
| 2025-12-09 to 2026-09-24 | Closed Won't Fix on 2022.3.X, 6000.0.X-6000.3.X; JSON state 102 / status 4; no fixed-in version; resolution note null in the new API; 21 votes | G1-050, GLES3-GF2-002 |
| 2026-05-22, 2026-07-22 | Users ask for news; no staff reply; no Horizon OS note mentions a visibility-stream or Vulkan binning fix | G1-058, GLES3-GF2-002, U1-077 |

## 6. Conflicts (both sides, not resolved here)

- **G1-C1 relative performance.** Better/equal: Unity untethered-XR guide, Meta overhead claim, Unity staff internal parity. Worse: UUM-93226, UUM-30269, Unity staff 2023 admission, threads 1561926 / 938162 / 1203082 / 1322298. Dossier assessment: measured evidence favours GLES in MSAA scenes; doc claims carry no numbers; parity unproven for the 6.1+ recommended configuration.
- **G1-C2 root cause.** Qualcomm visibility-stream bug + Vulkan copy cost (tracker, Dec 2025) vs too many stores in the renderer setup (Unity staff, Dec 2024) vs URP PR #4488 depth-copy strategy reverted only for GLES3 (community). Assessment: probably layered; no fix confirmed shipped.
- **G1-C4 does Vulkan improve GPU time?** Meta 2020: no GPU gain. Meta now: Symmetric Projection 5-15%, MRR 3-8%. Community: Vulkan costs more GPU. Assessment: base API is not GPU-faster; gains must come from Vulkan-only features.
- **G1-C5 stability.** Docs: Vulkan more stable. Tracker: more stutter on Vulkan. Assessment: the doc claim is about correctness, not frame pacing.
- **G1-C6 Meta's recommended API.** 2022 "GLES for production" (stale) vs current Vulkan recommendation. Current doc wins.
- **G2-C1 "required" vs "recommended".** Advanced GPU Pipelines page says required; OpenGL ES and Vulkan page says recommended and GLES still supported. Treat "required" as policy direction.
- **G2-C7 / G3-C3.** Meta and Qualcomm prefer Vulkan; UUM-149765 and UUM-93226 show GLES cheaper with MSAA. Choose per project with an A/B.
- **G2-C9 UUM-149765 internal inconsistency.** Table GLES 9.7 / 13.0 ms vs notes GLES ~12 / ~15 and Vulkan ~11 / ~16. Quote deltas only.
- **GX-C2 what the "buffer copies" are.** Vertex/constant buffer updates (G2-074, no cited source) vs render-target stores/resolves (tracker note, RenderDoc store counts). Evidence supports stores/resolves.
- **G1-C3 GPU skinning on GLES.** Forum post (2026): unavailable. Unity docs: no API restriction; compute chain available on ES 3.1+. Unresolved [verify on device].

## Sources

All accessed 2026-09-24.
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [measured]
- https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 [community]
- https://issuetracker.unity.com/api/v1.0/issues/1364 [community]
- http://web.archive.org/web/20250215025510/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 [community]
- http://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 [community]
- https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (and ?page=2) [community]
- https://discussions.unity.com/t/1725076 [community]
- https://issuetracker.unity.com/issues/6553/significant-performance-difference-between-vulkan-and-opengles3-when-built-with-ecs [community]
- https://discussions.unity.com/t/performance-discrepancy-between-vulkan-and-opengl-with-unity-2022-3-17f1-on-meta-quest-3/938162 [community]
- https://discussions.unity.com/t/xr-perf-quest-2022-2-and-trunk-vulkan-vs-gles-perf-disparity-increased-significantly-6223/1726043 [community]
- https://discussions.unity.com/threads/horrible-performance-on-vulkan-with-simple-scene-quest-2.1203082/ [community]
- https://discussions.unity.com/threads/serious-performance-regression-of-using-vulkan-vs-opengl-in-unity-2021-3-8-lts.1322298/ [community]
- https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-asw/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ [doc]
- https://developers.meta.com/horizon/blog/vulkan-support-for-oculus-quest-in-unity-experimental/ [doc]
- https://developers.meta.com/horizon/blog/vulkan-for-mobile-vr-rendering/ [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture-memorylessMode.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-foveated-rendering-support.html [doc]
- https://docs.unity3d.com/6000.1/Documentation/Manual/xr-multiview-render-regions.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/vulkanapi-graphics-jobs-configuration.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc]
- https://unity.com/releases/editor/whats-new/6000.3.12f1 [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc]
- https://opengles.gpuinfo.org/displayreport.php?id=7475 [measured]
- https://opengles.gpuinfo.org/displayreport.php?id=8023 [measured]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
