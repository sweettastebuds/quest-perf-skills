# unity-perf research dossier

**Scope.** This dossier covers frame-rate and frame-time consistency for Unity URP apps on Meta Quest 2 (XR2 Gen 1, Adreno 650), Quest 3 and Quest 3S (XR2 Gen 2, Adreno 740). It spans Unity 2021.3 LTS (URP 12) through Unity 6.6 (URP 17.6, the current release on the access date); 6.7 is in beta and appears only where it changes a baseline, such as CoreCLR. Vulkan is the primary graphics API and GLES 3.x the legacy path. Topics: the version and feature matrix, upgrade-path risks (including UUM-93226), URP asset and renderer settings, Render Graph on tile GPUs, draw calls and batching, shaders and PSO hitches, lighting, CPU and scripting, memory and assets, the profiling workflow, and the status of Unity's Unity 6 mobile/XR optimization e-book. Out of scope: PC VR and Link, Unreal, Godot, and generic phone advice. HDRP gets one line: it is a desktop/console pipeline and is not used on Quest.

**Access date.** 2026-09-24 for every source unless a finding says otherwise.

**Method.** Five topic researchers (U1 version matrix and upgrades, U2 URP settings and Render Graph, U3 draw calls, shaders and PSO, U4 lighting, memory and assets, U5 CPU, scripting and profiling) each wrote sourced notes. This dossier is the synthesis:
- findings are regrouped by coverage area, not by researcher;
- duplicates are merged into one entry that keeps every original ID and source;
- conflicts between topics that only appear when the notes are read together get new X-C IDs;
- gap-fill is limited to cross-topic answers (for example U1-083 supplies the fixed-in version that U2-055 lacked) and one quick source check that settled a contradiction (X-C8).

Gap-fill round 1 (coverage critic, 2026-09-24) added findings UNITY-GF1-001 to -017 and conflicts UNITY-GF1-C1 to -C3. It also re-fetched 18 findings' sources; corrections are marked inline with "Spot-check (gap-fill round 1)". No finding in the notes was dropped, and no unsourced claim was added.

Gap-fill round 2 (coverage critic, 2026-09-24) added findings UNITY-GF2-001 to -006 and conflict UNITY-GF2-C1. It re-fetched the sources of 20 findings; corrections are marked inline with "Spot-check (gap-fill round 2)". Finding text is carried over unchanged, so each finding keeps its own format: claim with goal tags, then `Source` (URL, access date), `Applies to` and `Evidence`, then optional `Notes`.

**Evidence tags** (exactly one per finding, plus an optional `[verify on device]`):
- `[doc]`: official documentation, release notes, vendor source code read directly (Unity-Technologies/Graphics, Meta XR Core SDK C#), and vendor staff posts on vendor forums where noted.
- `[measured]`: a source reporting its own measurements, with its setup.
- `[community]`: forums, issue-tracker comments, blogs, third-party and reverse-engineered driver docs. Treat as leads.

**Goal tags:**
- `[T]` throughput: lower average CPU or GPU frame time, bandwidth, memory.
- `[C]` consistency: no stale or dropped frames, tight p95/p99, no hitches (GC, shader/PSO compilation, loading, physics), no thermal decay over a 20-30 minute session, predictable behaviour across upgrades.

**Applicability tag conventions** (used in each finding's `Applies to` field and in skills built from this dossier):
- Headset: `Quest 2`, `Quest 3/3S` (Quest 3S is a Quest 3 variant with a Quest 2-class display).
- Engine: `Unity >= 6000.0`, `Unity 6.3+`, or an exact patch range such as `6.0 < .83`. Unity 6.x streams are written 6000.N (6.N).
- Pipeline: `URP 14+`, `URP 17.x`. Mapping: 2021.3 = URP 12, 2022.3 = URP 14, 6.0 = 17.0, 6.1 = 17.1, 6.2 = 17.2, 6.3 = 17.3, 6.4 = 17.4, 6.5 = 17.5, 6.6 = 17.6 (inferred).
- API: `GLES`, `Vulkan`.

**Frame budgets:** 72 Hz = 13.9 ms, 90 Hz = 11.1 ms, 120 Hz = 8.3 ms. The app never gets the whole budget; see the quest-perf dossier for Meta's headroom guidance.

### Merged duplicates

Findings that several researchers recorded independently are merged into one entry. The primary ID leads, and every merged ID stays in the entry header and in a "Merged" sub-bullet with its own sources.

| Merged entry | Placed in |
| --- | --- |
| U1-031 / U2-069 | 2. Upgrade-path risks > Render Graph and XR regressions (6.0 line) |
| U2-057 / U1-028 | 4. Render Graph on tile GPUs > Native pass merging rules and Render Graph APIs |
| U2-071 / U1-029 | 4. Render Graph on tile GPUs > Native pass merging rules and Render Graph APIs |
| U2-081 / U1-027 / U2-024 | 4. Render Graph on tile GPUs > Pre-Render-Graph equivalents (URP 12/14 and 6.0-6.3 Compatibility Mode) |
| U1-025 / U1-026 / U2-089 | 1. Version matrix > Render Graph, Compatibility Mode, Native RenderPass, Render Graph Viewer by version |
| U3-032 / U1-016 / U1-017 / U3-033 / U4-044 | 5. Draw calls and batching > GPU Resident Drawer and GPU occlusion culling |
| U3-034 / U1-018 | 5. Draw calls and batching > GPU Resident Drawer and GPU occlusion culling |
| U3-037 / U1-019 / U3-038 | 5. Draw calls and batching > GPU Resident Drawer and GPU occlusion culling |
| U3-026 / U1-013 / U1-014 / U3-028 / U3-029 | 5. Draw calls and batching > BatchRendererGroup, DOTS instancing, Entities Graphics |
| U3-009 / U1-012 / U2-016 | 5. Draw calls and batching > SRP Batcher |
| U3-066 / U1-036 / U2-056 | 6. Shaders: precision, discard, variants, stripping, PSO hitches > URP's Quest-only shader paths (6.5+) |
| U3-069 / U1-037 | 6. Shaders: precision, discard, variants, stripping, PSO hitches > URP's Quest-only shader paths (6.5+) |
| U1-053 / U3-070 | 1. Version matrix > Build Profiles, the Meta Quest build profile and Project Auditor |
| U2-052 / U1-043 / U1-054 | 3. URP asset and renderer settings > XR specifics: stereo path, mirror view, occlusion mesh, resolution, MSAA, foveation |
| U3-075 / U1-051 | 6. Shaders: precision, discard, variants, stripping, PSO hitches > Keywords, variants, stripping |
| U2-054 / U1-085 | 3. URP asset and renderer settings > XR specifics: stereo path, mirror view, occlusion mesh, resolution, MSAA, foveation |
| U1-083 / U2-055 | 2. Upgrade-path risks > Foveation regressions |
| U2-074 / U1-062 | 4. Render Graph on tile GPUs > On-tile rendering, on-tile post-processing and depth input (6.3-6.6) |
| U2-025 / U1-063 | 3. URP asset and renderer settings > Universal Renderer settings |
| U2-079 / U1-065 | 4. Render Graph on tile GPUs > On-tile rendering, on-tile post-processing and depth input (6.3-6.6) |
| U2-080 / U1-066 | 4. Render Graph on tile GPUs > On-tile rendering, on-tile post-processing and depth input (6.3-6.6) |
| U2-020 / U3-058 | 3. URP asset and renderer settings > Universal Renderer settings |
| U2-048 / U1-044 | 3. URP asset and renderer settings > XR specifics: stereo path, mirror view, occlusion mesh, resolution, MSAA, foveation |
| U3-050 / U2-053 | 5. Draw calls and batching > Stereo submission: multiview, single-pass instanced, Multiview Render Regions |
| U3-044 / U2-041 | 5. Draw calls and batching > Stereo submission: multiview, single-pass instanced, Multiview Render Regions |
| U3-083 / U1-045 / U1-046 / U1-048 / U4-096 | 6. Shaders: precision, discard, variants, stripping, PSO hitches > PSO hitches: GraphicsStateCollection (Unity 6) |
| U3-095 / U1-050 | 6. Shaders: precision, discard, variants, stripping, PSO hitches > PSO hitches before Unity 6, GLES, and on-disk caches |
| U3-080 / U4-093 | 6. Shaders: precision, discard, variants, stripping, PSO hitches > Keywords, variants, stripping |
| U5-005 / U4-097 | 8. CPU and scripting > Managed runtime, CoreCLR and garbage collection |
| U5-040 / U4-077 | 8. CPU and scripting > Burst, Jobs, Graphics Jobs and multithreaded rendering |
| U5-059 / U4-074 | 8. CPU and scripting > Physics (PhysX) |
| U3-003 / U4-076 | 5. Draw calls and batching > Triage: submission, shading or first-use compilation |
| U1-032 / U2-027 / U4-006 | 1. Version matrix > Rendering paths, lighting features and Quest shader optimizations by version |
| U4-026 / U4-027 / U1-039 | 7. Lighting > Shadows |
| U4-021 / U2-013 | 7. Lighting > Reflection probes |
| U5-018 / U1-030 | 8. CPU and scripting > IL2CPP and Player settings |
| U5-098 / U1-057 | 10. Profiling workflow > Profiling workflow and instrumentation on Quest |
| U1-056 / U5-099 / U2-096 | 1. Version matrix > Build Profiles, the Meta Quest build profile and Project Auditor |
| U5-001 / U1-071 | 8. CPU and scripting > Managed runtime, CoreCLR and garbage collection |
| U3-001 / U5-083 | 5. Draw calls and batching > Triage: submission, shading or first-use compilation |

## Baseline fact re-verification

Merged from the U1 and U5 baseline tables. Where both topics checked the same fact, the row names both.

| Fact | Status | Detail | Source |
| --- | --- | --- | --- |
| Unity release list and dates, 2021.3 through 6.7 (U1) | confirmed | 2021.3.0f1 2022-04-11 to 2021.3.45f2 2025-10-03. 2022.3.0f1 2023-05-30 to 2022.3.62f3 2025-10-28. 6000.0.0f1 2024-04-29 (LTS from 6000.0.23f1, 2024-10-16) to 6000.0.84f1 2026-09-16. 6000.1.0f1 2025-04-23. 6000.2.0f1 2025-08-12. 6000.3.0f1 2025-12-03 (LTS) to 6000.3.25f1 2026-09-24. 6000.4.0f1 2026-03-18. 6000.5.0f1 2026-06-15. 6000.6.0f1 2026-08-31 to 6000.6.3f1 2026-09-24. | https://services.api.unity.com/unity/editor/release/v1/releases |
| Unity 6.6 is the current release (U1, U5) | confirmed | 6000.6.3f1 shipped 2026-09-24; stream SUPPORTED (non-LTS), supported until 6.7 ships. The 6000.6 manual is live; "New in Unity 6.6" lists Managed Code Variant, Profileable Shell, built-in Burst module and the GLES 3.1 minimum. | https://services.api.unity.com/unity/editor/release/v1/releases ; https://unity.com/releases/unity-6/support ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html |
| 6.7 LTS has shipped (U1, U5) | confirmed NOT shipped | Only 6000.7.0a6 (2026-09-03), 0b1 (2026-09-17) and 0b2 (2026-09-23) exist, all beta; the 6000.7 manual is labeled beta. Unity targets 6.7 LTS for the end of 2026. Out of range except for the CoreCLR baseline. | https://services.api.unity.com/unity/editor/release/v1/releases?version=6000.7 ; https://unity.com/topics/render-pipelines-strategy-for-2026 ; https://docs.unity3d.com/6000.7/Documentation/Manual/scripting-backends-coreclr.html |
| Unity 6.0 LTS support ends October 2026 (U1) | confirmed | Stated on the Unity 6 support page; a few weeks away on the access date. | https://unity.com/releases/unity-6/support |
| Unity 6.3 LTS support runs to December 2027 (U1) | confirmed | Two years of standard support, plus one extra year for Enterprise/Industry. | https://unity.com/releases/unity-6/support |
| 2021.3 and 2022.3 end-of-support dates (U1; updated gap-fill round 2) | changed: both out of public support | Unity's CVE-2025-59489 advisory lists "2021.3 LTS" and "2022.3 LTS" under Out of Support Versions (patched builds 2021.3.45f2 and 2022.3.62f2). Only the paid "xLTS" streams (2021.3.56f2, 2022.3.67f2) are listed as in support. Unity's LTS page promises biweekly fixes for two years. No exact end date appears on a Unity page; endoflife.date (community) gives 2021.3 EOL 2025-02-18 and 2022.3 EOL 2025-05-07. See UNITY-GF2-005. | https://unity.com/security/sept-2025-01 ; https://unity.com/releases/lts ; https://github.com/endoflife-date/endoflife.date/blob/master/products/unity.md |
| URP version mapping (U1) | confirmed (6.6 inferred) | From package.json on the Graphics repo branches: 2021.3 12.1.16, 2022.3 14.0.12, 2023.1 15.0.7, 2023.2 16.0.6, 6000.0 17.0.4, 6000.1 17.1.0, 6000.2 17.2.0, 6000.3 17.3.0, 6000.4 17.4.0, 6000.5 17.5.0. Master shows 17.6.0 and there is no 6000.6/staging branch, so 6.6 = 17.6 is inferred. | https://raw.githubusercontent.com/Unity-Technologies/Graphics/6000.5/staging/Packages/com.unity.render-pipelines.universal/package.json |
| Vulkan buffer-copy issue on Quest (UUM-93226) is open or awaiting a fix (U1) | changed | Closed 2025-12-09 with no fix version on any stream. Old tracker label "Third Party Issue"; new tracker API shows every port Won't Fix / Closed. Unity blames a Qualcomm visibility-stream bug and expects a Meta OS fix. Workaround: Optimize Buffer Discard. See section 2 and U1-C1, U1-C2. | https://issuetracker.unity.com/issues/1364 ; https://issuetracker.unity.com/api/v1.0/issues/1364 |
| Vulkan recommended, GLES legacy (U5, CPU-side evidence; U1) | confirmed | 6.6 raises the Android GLES minimum to 3.1. Graphics Jobs modes are Vulkan-only. FrameTimingManager warns it may reduce GPU performance on GLES. The Meta Quest build profile defaults to Vulkan. Performance parity is not settled: see U1-C2. | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html |
| Minimum Android API level by version (U1) | confirmed | 6.0 raised the minimum to API 23, 6.3 to API 25, 6.5 to API 26 (warning only for 23-25). The Meta Quest build profile sets a minimum of 29. 2021.3/2022.3 minimums not verified. | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html |
| Oculus XR Plugin is usable on Unity 6.x (U1) | changed | Unity deprecated it in 6000.5.0b4. Meta marks it deprecated and scheduled for removal: "Unity 2022 or later" with Meta XR SDK v73 or earlier (re-checked in gap-fill round 1; the previous "before Unity 6" wording was wrong). See U1-C3. | https://unity.com/releases/editor/whats-new/6000.5.0b4 ; https://developers.meta.com/horizon/documentation/unity/unity-project-setup/ |
| URP Compatibility Mode (non-Render-Graph path) removal (U1) | confirmed | Hidden behind a define in 6.3, fully removed in 6.4 (see U1-C5). | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity64.html |
| OpenGL ES minimum raised to 3.1 (U1) | confirmed | In 6.6. | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html |
| CoreCLR transition status within 2021.3-6.6 (U5, shared with U1) | changed | No release in 2021.3-6.6 ships a CoreCLR player. CoreCLR is an experimental desktop-only player back end in 6.7 alpha/beta; Android unsupported; not production-ready. Unity's June 2026 update: 6.7 LTS is the final Mono-based release; Unity 7.0 removes Mono and targets .NET 10 / C# 14; CoreCLR performance tuning is deferred to the LTS after 7.0 (2027). Quest (Android, IL2CPP) stays on IL2CPP with the Boehm GC, which staff say is not changing. | https://docs.unity3d.com/6000.7/Documentation/Manual/scripting-backends-coreclr.html ; https://discussions.unity.com/t/coreclr-scripting-and-serialization-update-june-2026/1723299 ; https://discussions.unity.com/t/path-to-coreclr-2026-upgrade-guide/1714279 |
| Quest builds are IL2CPP + ARM64 (U5) | confirmed | The Android Player settings state the ARM64 target is available only with IL2CPP. | https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html |
| Incremental GC is on by default (U5) | confirmed | Player > Other Settings > Use incremental GC; default on in 2021.3 through 6.6. | https://docs.unity3d.com/6000.6/Documentation/Manual/performance-incremental-garbage-collection.html |
| Frame budgets 13.9 / 11.1 / 8.3 ms (U5) | confirmed | 1000/72 = 13.89, 1000/90 = 11.11, 1000/120 = 8.33 ms. | arithmetic |
| Quest CPU clock ranges by CPU level (U5) | confirmed (re-fetched in gap-fill rounds 1 and 2; page updated 2026-09-02) | Quest 2 CPU L0-L8 runs 0.71-2.42 GHz (L4 1.48 GHz); Quest 3/3S runs 0.69-2.36 GHz (L4 1.92 GHz). GPU L0-L5: Quest 2 305-587 MHz (L4 525), Quest 3/3S 285-599 MHz (L4 545). Levels auto-raise at 83% or more CPU / 87% or more GPU utilization and lower at 77% or less / 81% or less. | https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ |
| XR2 Gen 2 (Quest 3/3S) core configuration (U5) | changed (gap-fill round 1) | Qualcomm's XR2 Gen 2 product brief gives "4 + 2 performance cores, up to 2.4/2.0 GHz" (Kryo), LPDDR5 4x16 up to 3.2 GHz and an 8 MB system cache. The brief has no little cores and no Adreno model number (round 2 also checked the XR2+ Gen 2 brief and the XR2 Gen 2 reference-design brief: both say only "Adreno GPU"; see UNITY-GF2-003). The arm-mobile-hw dossier (A1-014, ARM-C1) identifies all six cores as Cortex-A78C from the Geekbench MIDR. The earlier third-party "2x A715 + 4x A510" row was wrong and is withdrawn. [verify on device] with `adb shell cat /proc/cpuinfo`. | https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf ; research/arm-mobile-hw.md |
| Quest 2 = Snapdragon XR2 (Gen 1), Adreno 650, 6 GB (gap-fill round 1) | confirmed | Meta's device comparison page (updated 2026-05-11) lists "Snapdragon XR2 Gen 1" and 6 GB. Meta's po-advanced-gpu-pipelines page names "XR2 (Adreno 650)" with 1 MB GMEM (re-fetched this round). Meta's current compare-devices page (updated 2026-09-18) no longer lists Quest 2. | https://developers.meta.com/horizon/resources/device-optimization-comparison/ ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ |
| Quest 3 = XR2 Gen 2, Adreno 740, 8 GB (gap-fill round 1; device-comparison figures re-fetched in round 2) | confirmed; the Adreno model number comes from Meta only | The device comparison page lists XR2 Gen 2, 8 GB and GPU "~2.5x Quest 2", and gives budgets of < 200 draw calls and < 1.5M triangles (Quest 2: < 100 and < 750K). po-advanced-gpu-pipelines names "XR2 Gen 2 (Adreno 740)" with about 2 MB GMEM (Quest 2: 1 MB). Compare-devices: LCD 2064x2208, 25 PPD, 120 Hz. | https://developers.meta.com/horizon/resources/device-optimization-comparison/ ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ ; https://developers.meta.com/horizon/essentials/compare-devices/ |
| Quest 3S = XR2 Gen 2 with a Quest 2-class display (gap-fill round 1) | confirmed | Compare-devices lists Quest 3S with Snapdragon XR2 Gen 2, 8 GB, LCD 1832x1920 (the Quest 2 panel resolution), 20 PPD and 120 Hz max. Its default eye buffer is 1680x1760, the Quest 3 value (os-render-scale). It shares the Quest 3 CPU/GPU level table. | https://developers.meta.com/horizon/essentials/compare-devices/ ; https://developers.meta.com/horizon/documentation/unity/os-render-scale/ ; https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ |
| No eye tracking on Quest 2/3/3S (gap-fill round 1) | confirmed; new device noted | Compare-devices lists "Head and hand tracking" for Quest 3 and 3S. The same page (2026-09-18) now also lists "Meta VR Glasses" (XR2 Gen 3, 12 GB, micro-OLED 2412x2288, head/hand/eye tracking), which is outside this project's headset scope. It gets a one-line note only, like eye-tracked foveation. | https://developers.meta.com/horizon/essentials/compare-devices/ |
| Display refresh rates (gap-fill round 1) | confirmed | Default app refresh rate is 72 Hz. Quest 2/3/3S support 72/80/90/96/100/120 Hz; Quest 3 alone goes above 120 Hz. | https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ |

## 1. Version matrix

When each Quest-relevant feature arrived and how mature it is. Merged entries from the other topics sit here when the version history is their main content. Forward+ (U1-032 group), APV history (U1-041; detail in section 7), STP (U1-042) and Project Auditor (U1-056 group) are in this section.

### Releases and support windows

- **U1-001** Unity 6.6 (6000.6) is the newest production release. 6000.6.0f1 shipped 2026-08-31 and 6000.6.3f1 shipped on the access date. It is an Update ("Supported") release, not LTS, so it gets fixes only until 6.7 ships. [C]
  - Source: https://services.api.unity.com/unity/editor/release/v1/releases?version=6000.6 (accessed 2026-09-24) · Applies to: 6.6 · Evidence: [doc]
  - Notes: The stream field returns SUPPORTED. The support page says Update releases are supported until the next release.

- **U1-002** 6.7 LTS has not shipped. Only 6000.7.0a6 (2026-09-03), 6000.7.0b1 (2026-09-17) and 6000.7.0b2 (2026-09-23) exist. Unity's render-pipeline strategy page targets 6.7 LTS for the end of 2026. [C]
  - Source: https://unity.com/topics/render-pipelines-strategy-for-2026 (accessed 2026-09-24) · Applies to: 6.7 · Evidence: [doc]
  - Notes: A secondary source reports the same quarterly-to-6.7-LTS cadence from Unite 2025: https://www.digitalproduction.com/2025/11/26/unitys-2026-roadmap-coreclr-verified-packages-fewer-surprises/ (2025-11-26). Do not recommend 6.7 betas for shipping Quest titles.

- **U1-003** 6.3 LTS (6000.3) went to release as LTS on 2025-12-03 with 6000.3.0f1. The latest patch is 6000.3.25f1 (2026-09-24). Standard support runs to December 2027, and Enterprise/Industry get one more year. It is the safest long-lived target for a Quest project today. [C]
  - Source: https://unity.com/releases/unity-6/support (accessed 2026-09-24) · Applies to: 6.3 · Evidence: [doc]

- **U1-004** 6.0 shipped as a Tech release on 2024-04-29 (6000.0.0f1) and became LTS at 6000.0.23f1 (2024-10-16). The latest patch is 6000.0.84f1 (2026-09-16). Unity lists October 2026 as the end of 6.0 LTS support, so 6.0 projects are about to lose patch coverage. [C]
  - Source: https://unity.com/releases/unity-6/support (accessed 2026-09-24) · Applies to: 6.0 · Evidence: [doc]
  - Notes: Several Quest fixes listed below exist only on 6.3 or later (UUM-121520, UUM-121231, on-tile post). Staying on 6.0 after October 2026 means no further Quest regression fixes.

- **U1-005** The 6.1, 6.2, 6.4 and 6.5 Update releases no longer receive patches. Their last patches were 6000.1.17f1 (2025-10-03), 6000.2.15f1 (2025-12-03), 6000.4.12f1 (2026-06-17) and 6000.5.11f1 (2026-09-02). A project pinned to one of them should move to 6.3 LTS or 6.6. [C]
  - Source: https://services.api.unity.com/unity/editor/release/v1/releases (accessed 2026-09-24) · Applies to: 6.1, 6.2, 6.4, 6.5 · Evidence: [doc]
  - Notes: 6000.5.11f1 shipped two days after 6.6.0f1. Expect a short overlap, then nothing.

- **U1-006** 2022.3 LTS (URP 14) ran from 2022.3.0f1 (2023-05-30) to 2022.3.62f3 (2025-10-28). No 2022.3 release has appeared in the eleven months since, and no end-of-support date was found on Unity's pages. Treat it as frozen. [C]
  - Source: https://services.api.unity.com/unity/editor/release/v1/releases?version=2022.3 (accessed 2026-09-24) · Applies to: 2022.3 · Evidence: [doc]

- **U1-007** 2021.3 LTS (URP 12) ran from 2021.3.0f1 (2022-04-11) to 2021.3.45f1 (2024-10-16). One more re-release, 2021.3.45f2, shipped 2025-10-03. [C]
  - Source: https://services.api.unity.com/unity/editor/release/v1/releases?version=2021.3 (accessed 2026-09-24) · Applies to: 2021.3 · Evidence: [doc]
  - Notes: On 2025-10-03, 2021.3.45f2, 2022.3.62f2, 2023.1.22f1, 2023.2.22f1 and 6000.1.17f1 all shipped the same day. This looks like a cross-version security patch but was not verified; see Leads.
  - Spot-check (gap-fill round 2): confirmed. These are the CVE-2025-59489 patch builds; Unity's advisory lists exactly these versions as patches for out-of-support streams. See UNITY-GF2-005.

- **U1-008** Meta's Unity setup page (updated 2026-09-09) requires Unity 6000.0.66f2 or later and recommends 6.1 or newer. That is stricter than Unity's own LTS floor, so a 6.0 project below .66f2 is off Meta's supported path. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-project-setup/ (accessed 2026-09-24) · Applies to: 6.0.x < 66f2 · Evidence: [doc]
  - Notes: 6000.0.66f2 is present in the Unity Release API list.
  - Spot-check (gap-fill round 2): confirmed on re-fetch. The page (updated 2026-09-09) reads "Unity Editor 6000.0.66f2 or later (6.1 or later recommended)".

- **UNITY-GF2-005** 2021.3 LTS and 2022.3 LTS are out of public support. Unity's security advisory for CVE-2025-59489 (patches available 2025-10-02) splits its version table in two. [C]
  - **Current in Support Versions:** 6000.3 (6000.3.0b4), 6000.2 (6000.2.6f2), 6000.0 LTS (6000.0.58f2), "2022.3 xLTS" (2022.3.67f2) and "2021.3 xLTS" (2021.3.56f2).
  - **Out of Support Versions:** "2022.3 LTS" (patched as 2022.3.62f2) and "2021.3 LTS" (patched as 2021.3.45f2), along with 6000.1, 2023.x and older streams.

  Unity's LTS page says an LTS release gets biweekly fixes for two years. The xLTS builds (2021.3.56f2, 2022.3.67f2) do not appear in the public Release API, which ends at 2021.3.45f2 and 2022.3.62f3. A Quest team on the public 2021.3/2022.3 builds therefore gets no further engine or Quest fixes, including for UUM-93226-class Vulkan issues.
  - Source: https://unity.com/security/sept-2025-01 ; https://unity.com/releases/lts ; https://services.api.unity.com/unity/editor/release/v1/releases?version=2022.3 (accessed 2026-09-24) · Applies to: 2021.3, 2022.3 (all devices, both APIs) · Evidence: [doc]
  - Notes: No Unity page gives an exact end-of-support date. endoflife.date (community, derived from the release policy) lists 2021.3 EOL 2025-02-18 and 2022.3 EOL 2025-05-07 (https://github.com/endoflife-date/endoflife.date/blob/master/products/unity.md). A 2025-06 Unity Discussions thread (non-staff) reports the same from download availability: 2022.3.63f1 and later are Enterprise/Industry only (https://discussions.unity.com/t/2022-3-lts-is-now-enterprise-and-industry-only/1652230). Consequence for skills: treat 2021.3/2022.3 advice as maintenance-only and put the upgrade to 6.3 LTS first when a fix exists only on 6.x. The advisory lists Android as affected (code execution / elevation of privilege, High), so a Quest title still on 2021.3.45f1 or 2022.3.62f1 or earlier should at least take the patch build.

- **UNITY-GF2-006** Unity 6.7 has not shipped as of 2026-09-24. The Release API lists 6000.7.0a1 (2026-06-25) through 6000.7.0b2 (2026-09-23), all ALPHA or BETA. The cumulative 6.7 pre-release notes contain these Quest-relevant entries to recheck at LTS: [T][C]
  - "URP: Added on-tile support to the URP deferred renderer."
  - "URP: Added support for changing URP keywords to dynamic branch." This is a variant-count lever (fewer variants and PSOs, at the cost of runtime branching).
  - "URP: Fixed shader resolve for XR is not enabled properly in on-tile postprocessing" (UUM-143511).
  - Fixed soft shadows breaking for spot and point lights in Deferred on Meta Quest ("variant not found"; UUM-147509, see U1-035).
  - "Profiler: Fixed labelling of Unrooted Allocations associated with GraphicsStateCollection Allocations" (UUM-139555).
  - Several fixes for intermittent crashes on Adreno GPUs using OpenGL ES (UI Toolkit mesh and text updates, uniform-block binding reads).

  No 6.7 note found changes the dynamic-batching deprecation (U1-022) or the Quest shader paths (section 6).
  - Source: https://services.api.unity.com/unity/editor/release/v1/releases?version=6000.7 ; https://unity.com/releases/editor/whats-new/6000.7.0b2 ; https://unity.com/releases/editor/whats-new/6000.7.0a6 (accessed 2026-09-24) · Applies to: 6000.7 alpha/beta only · Evidence: [doc]
  - Notes: The whats-new pages for 6.7 pre-releases appear cumulative, so the first version of each entry is not pinned here (U1-034 and U1-035 name 6000.7.0a2/a3 from earlier reads). Do not ship Quest titles on 6.7 betas. When 6.7 LTS ships, re-read its What's New and Upgrade Guide pages for GSC, Quest shader optimizations, dynamic batching and Multiview Render Regions.

- **U1-009** Meta: the Unity OpenXR Plugin path (recommended version 1.15.1) needs Unity 6+ and Meta XR SDK v74+. The Oculus XR Plugin (recommended 4.5.1) is marked deprecated and scheduled for removal. Meta lists it as requiring Unity 2022 or later with Meta XR SDK v73 or earlier. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-project-setup/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: In practice, a 2021.3/2022.3 → 6.x upgrade is also a switch from Oculus XR to OpenXR and a Meta XR SDK major bump. Plan both together.
  - Spot-check (gap-fill round 1): corrected. The earlier text said Meta restricts Oculus XR to "Unity versions before 6". The page (updated 2026-09-09) actually states "Unity 2022 or later" and gates on SDK v73 or earlier. So Oculus XR on Unity 6 is not excluded by Unity version, but it pins the project to SDK v73 or older and loses every v74+ feature. U1-C3 and the baseline row are updated to match.

### URP version mapping

- **U1-010** URP version by Editor stream: 2021.3 → URP 12.1.x (12.1.16 on staging). 2022.3 → 14.0.x (14.0.12). 2023.1 → 15.0.x. 2023.2 → 16.0.x. 6000.0 → 17.0.x (17.0.4). 6000.1 → 17.1. 6000.2 → 17.2. 6000.3 → 17.3. 6000.4 → 17.4. 6000.5 → 17.5. 6000.6 → 17.6 (inferred from master). [C]
  - Source: https://raw.githubusercontent.com/Unity-Technologies/Graphics/2022.3/staging/Packages/com.unity.render-pipelines.universal/package.json (and the matching branch for each stream) (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: Docs for package versions 12.1 and 14.0 still live under `docs.unity3d.com/Packages/com.unity.render-pipelines.universal@<ver>/`. From Unity 6, URP docs moved into the Editor manual under `/Manual/urp/`.

- **U1-011** From Unity 6, URP, SRP Core and Shader Graph are core packages locked to the Editor version. You cannot move URP forward or back on its own, so every URP fix and regression comes with an Editor patch. [C]
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/urp/upgrade-guide-unity-6.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: Implication for skills: never suggest "update the URP package" on 6.x. Suggest an Editor patch instead, and check the release note for the UUM ID.

### Batching and GPU-driven rendering by version

- **U1-015** A fix for BRG, the GPU Resident Drawer and Entities Graphics on devices limited to 16 KiB constant buffers, where objects did not render on Android (UUM-102083), shipped in 6000.0.65f1, 6000.3.3f1 and 6000.4.0b3. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.65f1 (accessed 2026-09-24) · Applies to: 6.0 < .65, 6.3 < .3 · Evidence: [doc]
  - Spot-check (gap-fill round 2): confirmed in 6000.0.65f1 ("Fixed BRG,GRD and EG 16KiB cbuffer limited low end mobiles", UUM-102083). The 6.3 and 6.4 versions were not re-fetched.

- **U1-020** Regression UUM-146214 caused GPU occlusion culling to stop culling occluded instances with GRD on. It was reported against 6000.5.0b2 and 6000.6.0a2 and fixed in 6000.5.8f1 and 6000.6.0f1 (and 6000.7.0a3). On 6.5.0–6.5.7, occlusion culling cost GPU time for no gain. [T]
  - Source: https://unity.com/releases/editor/whats-new/6000.5.8f1 ; https://unity.com/releases/editor/whats-new/6000.6.0f1 (accessed 2026-09-24) · Applies to: 6.5.0–6.5.7 · Evidence: [doc]
  - Spot-check (gap-fill round 2): confirmed with a nuance. The fix notes don't describe the symptom. 6000.5.8f1 says "Make CullingParameters.viewID 64 bits"; 6000.6.0f1 lists a BatchPackedCullingViewID EntityID change under UUM-146214. The symptom (occluded instances not culled with GRD, seen in 6000.5.0b2 / 6000.6.0a2) is in the Known Issues of earlier 6.5.x/6.6 beta notes (e.g. https://unity.com/releases/editor/whats-new/6000.5.6f1). One search snippet says the 6.6 fix landed in 6000.6.0b5, so 6000.6.0f1 is a safe floor.

- **U1-021** New GRD tooling: 6.4 rebuilt the Rendering Statistics window and added SRP Batcher counts. 6.6 adds GRD telemetry in the Profiler. 6000.7.0a3 adds GRD batching stats (unique materials and meshes, single-instance batches) and a "GRD Batches" Profiler chart. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity64.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.4+ · Evidence: [doc]

- **U1-022** Dynamic batching is marked obsolete in 6.6. Projects that relied on it for small Quest meshes lose that path and need the SRP Batcher, GRD or manual combining instead. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]
  - Spot-check (gap-fill round 2): confirmed. The Graphics section says "Dynamic batching is now obsolete" and links to the page on choosing a draw-call optimization method.

### Render Graph, Compatibility Mode, Native RenderPass, Render Graph Viewer by version

- **U1-023** Render Graph is on by default in 6.0 (URP 17). Projects opened from an earlier URP are switched to Compatibility Mode (Render Graph disabled) automatically. The non-Render-Graph APIs were marked obsolete from 6000.0.0b11. Unity says it no longer develops the non-Render-Graph path. [C]
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/urp/upgrade-guide-unity-6.html (accessed 2026-09-24) · Applies to: 6.0 · Evidence: [doc]
  - Notes: A 2022.3 → 6.0 upgrade therefore runs the legacy path until someone unticks Compatibility Mode. Skills should check this setting first when someone reports "no RG gains".

- **U1-024** 6.2 changes when custom passes run. `SetupRenderPasses` is deprecated, and the AfterRendering injection point now runs after the final blit. Custom passes at AfterRendering move relative to the backbuffer write. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity62.html (accessed 2026-09-24) · Applies to: 6.2+ · Evidence: [doc]

- **U1-025 / U1-026 / U2-089** In 6.3, Compatibility Mode is hidden behind the `URP_COMPATIBILITY_MODE` scripting define (6000.3.0a2). The 6.3 upgrade guide calls it removed: `RenderGraphSettings.enableRenderCompatibilityMode` is read-only false, and the define exists only to help convert. The legacy `AddRenderPass()` path is deprecated in 6000.3.0a5. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity63.html ; https://unity.com/releases/editor/whats-new/6000.3.0a2 (accessed 2026-09-24) · Applies to: 6.3 · Evidence: [doc]
  - **Merged U1-026:** 6.4 removes Compatibility Mode completely, together with the `URP_COMPATIBILITY_MODE` define (6000.4.0a4). `StoreActionsOptimization` becomes obsolete. In 6.5 the legacy Render Graph compiler is obsolete too. Any custom ScriptableRenderPass without a RecordRenderGraph implementation stops working. [C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity64.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html (accessed 2026-09-24) · Applies to: 6.4+ · Evidence: [doc]
  - **Merged U2-089:** Compatibility Mode in 6.0-6.3 keeps the URP 14-style path (Native RenderPass toggle, `Execute`-based passes). 6.4 removes it for custom passes, along with the `URP_COMPATIBILITY_MODE` scripting define. Custom Quest passes must be ported to `RecordRenderGraph` before moving to 6.4+. [T]
    - Source: https://docs.unity3d.com/6000.4/Documentation/Manual/UpgradeGuideUnity64.html (accessed 2026-09-24) · Applies to: 6.0-6.4 · Evidence: [doc]
    - Notes: The ScriptableRendererData field `m_UseNativeRenderPass` is still serialized in 6000.3 but absent in 6000.5 source.

### Rendering paths, lighting features and Quest shader optimizations by version

- **U1-032 / U2-027 / U4-006** Forward+ first shipped in URP 14 (2022.3). It removes the per-object light limit, though a per-camera limit still applies. 2022.3.16f1 and 6000.0.0b11 added foveated rendering in Forward+. 6.0 then added XR and orthographic-camera support for Forward+ and clustered reflection probes (more than two probes per object). [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/rendering/forward-plus-rendering-path.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html (accessed 2026-09-24) · Applies to: 2022.3+ · Evidence: [doc] [verify on device]
  - Notes: Whether Forward+ was fully supported in XR on 2022.3 is ambiguous; see U1-C4. GRD needs Forward+ or Deferred+, so choosing GRD forces the rendering path.
  - **Merged U2-027:** **Forward+** on Quest:
    - Meta's testing (Viking Village) found Forward+ wins from about 5 real-time lights.
    - Meta maintained URP branches for Quest Forward+ (`2022.3/forward-plus`, `6000.0/forward-plus`). From 6000.3, built-in URP includes the Quest optimizations.
    - Meta says disable Probe Blending and Probe Atlas Blending.

    [T]
    - Source: https://developers.meta.com/horizon/documentation/unity/unity-forward-plus-rendering/ (accessed 2026-09-24) · Applies to: URP 14-17.x · Evidence: [measured]
    - Notes: For debugging, Meta points to the shader Universal Render Pipeline > Debug > ForwardPlus, which visualizes lights per tile (scaling up to 32). Only the break-even light count is published, no ms figures. Re-measure per scene [verify on device].
  - **Merged U4-006:** Forward+ removes the per-object light limit. Its per-camera limits are one lower than Forward's, because the main light counts as a regular light. Forward+ is also required to blend more than 2 reflection probes per object. [T]
    - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/rendering-paths-comparison.html (accessed 2026-09-24) · Applies to: URP 14+ (2022.2+) to 17.x · Evidence: [doc] [verify on device]
    - Notes: No published Quest number compares Forward and Forward+ GPU cost at equal light counts. Measure with GPU frame time and RenderDoc (Meta fork) on a scene with 4, 8, and 16 visible lights.

- **U1-033** In 6.1 the `_FORWARD_PLUS` shader keyword is deprecated in favour of `_CLUSTER_LIGHT_LOOP` (URP 17.1). Old shaders keep working through a compatibility shim. URP still sets both global keywords when Forward+ is active. `ForwardPlusKeyword.deprecated.hlsl`, included from `Core.hlsl`, maps `USE_FORWARD_PLUS` to `USE_CLUSTER_LIGHT_LOOP` and `FORWARD_PLUS_SUBTRACTIVE_LIGHT_CHECK` to `CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK`, and defines `_CLUSTER_LIGHT_LOOP` when `_FORWARD_PLUS` is defined. It also emits a `#warning` that compile times "may be negatively affected". Rename the keywords in custom HLSL to drop the warning and the extra keyword, and before the shim is removed ("in a future release"). [C]
  - Source: https://docs.unity3d.com/6000.1/Documentation/Manual/urp/upgrade-guide-unity-6-1.html ; https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/ShaderLibrary/ForwardPlusKeyword.deprecated.hlsl ; https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/Runtime/ForwardLights.cs (accessed 2026-09-24) · Applies to: 6.1-6.5 (source checked on 6000.1 and 6000.5 staging) · Evidence: [doc]
  - Spot-check (gap-fill round 2): corrected. The earlier text said custom HLSL branching on `_FORWARD_PLUS` "stops taking the clustered path after the upgrade". The source contradicts this: `ForwardLights.cs` calls `cmd.SetKeyword(ShaderGlobalKeywords.ForwardPlus, m_UseForwardPlus)` next to the `ClusterLightLoop` call, with the comment "Backward compatibility. Deprecated in 6.1". The upgrade guide says only "deprecated". See UNITY-GF2-C1. Whether 6.6 or 6.7 removes the shim was not checked.

- **U1-034** Deferred on Quest: Unity's untethered-XR guide recommends Forward, because G-buffer loads are slow on tile-based GPUs. Deferred+ was added in 6.1 (it uses Forward+ for transparents and forward-only opaques). On-tile deferred first appears in 6000.7.0a2, which is alpha only. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity61.html ; https://unity.com/releases/editor/whats-new/6000.7.0a2 (accessed 2026-09-24) · Applies to: 6.1+ (Deferred+), 6.7 alpha (on-tile deferred) · Evidence: [doc]

- **U1-035** UUM-147509: soft shadows broke in Deferred on Quest with shader "variant not found" errors. The only fix found is in 6000.7.0a3, with no 6.3 or 6.6 backport in the notes. This is another reason to stay on Forward on shipping versions. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.7.0a3 (accessed 2026-09-24) · Applies to: ≤6.6 · Evidence: [doc]

- **U1-038** In 6000.6.0b1, `DistanceAttenuation` takes three arguments when building for Meta Quest, as part of a further round of micro-optimizations. Custom shaders that call the two-argument form fail to compile on 6.6 Quest builds. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.6.0b1 (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]

- **U1-040** UUM-148728 was a URP GLES performance regression where the maximum additional-light count was forced from 16 to 32. It was fixed in 6000.6.0f1. It is tied to the 6.6 change that raised MAX_VISIBLE_LIGHTS from 16 to 32 when ES3.1 shaders are used. [T]
  - Source: https://unity.com/releases/editor/whats-new/6000.6.0f1 ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (accessed 2026-09-24) · Applies to: 6.6 pre-release; GLES builds · Evidence: [doc]
  - Spot-check (gap-fill round 2): confirmed. The 6000.6.0f1 note reads "Fixed a URP performance regression on OpenGL ES devices where the maximum number of additional lights was forced from 16 to 32" (first seen in 6000.6.0b9). The upgrade guide gives the precondition: the 16-to-32 `MAX_VISIBLE_LIGHTS` rise happens when the project turns off "Use OpenGL ES 3.0 shaders" and adopts ES 3.1 shaders. Unity says this "increases the application's workload".

- **U1-041** Adaptive Probe Volumes (APV) arrived in URP 17 (6.0). They sample 8 probes per pixel. 6.0 added per-vertex quality for cheaper indirect lighting. URP on mobile does not support Lighting Scenario blending, and disk streaming requires compute. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/probevolumes-concept.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc] [verify on device]
  - Notes: No published Quest cost for per-pixel vs per-vertex APV sampling. Measure the GPU ms delta on a lit test scene with APV per-pixel, APV per-vertex and classic light probes.

### Upscaling (STP), anti-aliasing and resolution by version

- **U1-042** STP is not supported in XR. Unity's XR render-pipeline compatibility table marks it No in both 6.0 and 6.6. It also needs compute (SM5.0), does not run on OpenGL ES, and requires TAA, which cannot be combined with MSAA. It does not apply to Quest. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/urp/stp/stp-upscaler.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Spot-check (gap-fill round 2): confirmed. The 6000.6 XR compatibility table marks Spatial-Temporal Post-processing "No".

### PSO tracing and GraphicsStateCollection by version

- **U1-047** UUM-121231, "Fixed GraphicsStateCollection warmup for Vulkan", appears only in 6000.4.0a4. No 6.0 or 6.3 backport was found in any release note. On 6.0 and 6.3 LTS, Vulkan GSC warmup may not remove hitches as expected. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.4.0a4 (accessed 2026-09-24) · Applies to: 6.0, 6.3 · Evidence: [doc] [verify on device]
  - Spot-check (gap-fill round 2): confirmed. 6000.4.0a4 reads "Graphics: Fixed GraphicsStateCollection warmup for Vulkan. (UUM-121231)". The absence of a backport was not re-searched.
  - Notes: To check, capture a first-run session on Quest with and without warmup. Count frames over budget (for example OVR Metrics stale frames) during the first appearance of each material or effect.

- **U1-049** Stereo-instancing shader variants are not prewarmed, because they need a layered render-target setup (6000.0.0b11, UUM-54697). The same release made `WarmupAllShaders` warm every variant, and made Vulkan honour `maxParallelPSOCreationJobs` for async PSO creation. Quest multiview/SPI variants therefore cannot be prewarmed through the legacy warmup APIs. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.0b11 (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc] [verify on device]
  - Notes: Whether GSC traces the stereo-instanced PSOs on Quest is not documented. Check by tracing on device and inspecting the collection.

### Build Profiles, the Meta Quest build profile and Project Auditor

- **U1-052** How Build Profiles have changed: they were introduced in 6.0 and replaced the Build Settings window. 6.1 added per-profile Graphics and Quality overrides. 6.3 added an "Add Settings" UI and per-profile exclusion of shader code for keywords. 6.5 added the `CreateBuildProfile` API. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity61.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]

- **U1-053 / U3-070** The Meta Quest build profile (6000.1.0a2; optimal defaults from 6000.1.0b14) overrides these settings by default: Vulkan, minimum API 29, target API 32, IL2CPP, ARM64, single-pass instanced stereo, anisotropic filtering per texture, and a "Meta Quest (Build Profile)" quality level. The OpenXR plugin is a required package, and it has been the default since 6000.2.0a9. [C][T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html (accessed 2026-09-24) · Applies to: 6.1+ · Evidence: [doc]
  - Notes: Adopting the profile on an upgraded project silently switches the graphics API and XR plugin. Check both before comparing performance.
  - Spot-check (gap-fill round 2): confirmed on the 6000.6 page. It lists Vulkan, "Android 10 (API level 29)", "Android 12L (API level 32)", IL2CPP, ARM64, Stereo Rendering Path Instancing, Anisotropic Filtering Per Texture and the "Meta Quest (Build Profile)" quality level. The required-package list is on a separate page and was not re-fetched.
  - **Merged U3-070:** Unity's 6.1+ Meta Quest build profile defaults:
    - Vulkan
    - minimum API level 29, target API level 32
    - IL2CPP, ARM64
    - Stereo Rendering Path Instancing
    - Anisotropic Per Texture

    [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html (accessed 2026-09-24) · Applies to: 6.1+ · Evidence: [doc]
    - Notes: The build profile is also where per-profile Shader Build Settings and constants live (U3-074/075). The Quest shader define is tied to this build target.

- **U1-055** From 6000.3.0a5 the Meta Quest profile uses Mobile quality by default, which keeps SSAO off. 6000.3.14f1 updated the profile's custom Quality defaults again, so a 6.3 patch upgrade can change the effective quality settings. [T][C]
  - Source: https://unity.com/releases/editor/whats-new/6000.3.0a5 ; https://unity.com/releases/editor/whats-new/6000.3.14f1 (accessed 2026-09-24) · Applies to: 6.3+ · Evidence: [doc]

- **U1-056 / U5-099 / U2-096** Project Auditor was a package on 6.3 and earlier and became part of the Editor in 6.4 (some APIs became internal). 6.5 can flag APIs made obsolete between Editor versions, which helps with upgrades. 6.6 adds a URP Settings Analyzer and a Roslyn statics analyzer. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity64.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.4+ (in Editor) · Evidence: [doc]
  - Notes: 6000.7.0a6 adds URP and CoreCLR migration pages to it.
  - **Merged U5-099:** Project Auditor versions:

    | Unity | Project Auditor |
    |---|---|
    | 6000.0+ | 3.1.1 (2026-09-22) |
    | 2022.3 | 2.0.0 |
    | 2021.3 | 1.1.0 |

    Unity 6.6 adds a URP Settings Analyzer and a Domain Reload page. Use it as a static pre-pass for costly code patterns and settings before profiling. [T]
    - Source: https://packages.unity.com/com.unity.project-auditor (accessed 2026-09-24); https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
    - Notes: The CoreCLR upgrade guide asks for Project Auditor 2.0.0+ for its readiness checks.
  - **Merged U2-096:** Unity 6.6 adds a **URP Settings Analyzer** to Project Auditor that flags URP settings with performance implications. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.6 · Evidence: [doc]
    - Notes: Its rule set was not inspected. Check whether it knows Quest-specific rules (HDR, MSAA, Tile-Only) before relying on it in a skill (gap).

### Mesh LOD and VRS

- **U1-059** Mesh LOD arrived in 6.2. It generates LODs on import and stores them in the index buffer of the original mesh, with no extra GameObjects. Unity says it uses less memory and has lower overhead than LOD Group. 6.4 added an inspector preview, and 6.5 added Entities Graphics support. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/lod/mesh-lod-introduction.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity62.html (accessed 2026-09-24) · Applies to: 6.2+ · Evidence: [doc] [verify on device]
  - Notes: Inference to verify: because only the index buffer changes, the full LOD0 vertex buffer stays resident and is bound for every LOD. Triangle and raster cost drops, but vertex memory does not. No Quest number published. Measure the GPU vertex-shading share and memory against LOD Group.

- **U1-060** Mesh LOD limits: Particle System, VFX Graph and static batching always use LOD0. Cross-fade needs GRD and has no custom transition zones. Skinned meshes still deform LOD0 whatever LOD is drawn, and the simplifier ignores skin weights and blend shapes. Only triangle topology is supported, and mixing it with LOD Group is discouraged. `RenderMeshInstanced` and `RenderMeshPrimitives` need an explicit `forceMeshLod`. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/lod/mesh-lod-introduction.html (accessed 2026-09-24) · Applies to: 6.2+ · Evidence: [doc]
  - Notes: On Quest, Mesh LOD saves nothing on skinning cost, and static-batched environments get no LOD selection.

- **U1-061** The Variable Rate Shading API (6.1) lets Scriptable Renderer Features set shading rate. It is supported on DX12, on Android Vulkan with fragment-shading-rate support, and on PS5 and Xbox Series. 6.3 added VRS inspection to the Frame Debugger. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/variable-rate-shading-introduction.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity61.html (accessed 2026-09-24) · Applies to: 6.1+ · Evidence: [doc] [verify on device]
  - Notes: No Unity or Meta page found that confirms Quest 2 or Quest 3 exposes Vulkan fragment shading rate to Unity's VRS API, or how VRS interacts with the fixed/eye-tracked foveation that Quest drives. Treat it as unsupported until tested: query the shading-rate capability at runtime on device.

### 6.3-6.6 Android and XR performance features

- **U1-064** UUM-140408 removed unnecessary colour loads when UberPost is the final pass on tile-based GPUs. It shipped in 6000.5.11f1 and 6000.6.0f1, with no 6.3 entry found. [T]
  - Source: https://unity.com/releases/editor/whats-new/6000.6.0f1 (accessed 2026-09-24) · Applies to: 6.5.11+, 6.6+ · Evidence: [doc]
  - Spot-check (gap-fill round 2): confirmed in both 6000.6.0f1 and 6000.5.11f1 (UUM-140408, "avoiding unnecessary color loads when UberPost (post-processing) is the final pass").

- **U1-067** From 6000.3.0a5/0b1, Unity passes the framebuffer tile size to the OpenXR runtime. 6000.2.0a4 fixed wrong predicted frame times on OpenXR. Both affect how well the runtime paces frames and schedules foveation. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.3.0b1 ; https://unity.com/releases/editor/whats-new/6000.2.0a4 (accessed 2026-09-24) · Applies to: 6.2+, 6.3+ · Evidence: [doc]

- **U1-068** UUM-148724: `PlayerSettings.vulkanNumSwapchainBuffers` was ignored, and players always used 3 swapchain buffers. It was fixed in 6000.0.83f1, 6000.3.24f1 and 6000.6.0f1, so the setting only takes effect from those patches. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.83f1 ; https://unity.com/releases/editor/whats-new/6000.3.24f1 (accessed 2026-09-24) · Applies to: 6.0 < .83, 6.3 < .24, 6.4, 6.5 · Evidence: [doc]
  - Notes: For OpenXR, the runtime usually owns the eye swapchains, so this affects the Unity-managed surface. Whether it changes Quest latency is unverified. [verify on device]
  - Spot-check (gap-fill round 2): confirmed in 6000.0.83f1 ("Vulkan Player would not respect the value of 'PlayerSettings.vulkanNumSwapchainBuffers' and instead use a fixed count of 3"). The UUM ID also appears in 6000.3.24f1 and 6000.6.0f1.

- **U1-069** 6.1 added a Vulkan Device Filter asset that picks the graphics-jobs mode, or Vulkan use, per Android device at runtime. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity61.html (accessed 2026-09-24) · Applies to: 6.1+ · Evidence: [doc]

- **U1-070** How SpaceWarp (application spacewarp motion vectors) support has changed: Shader Graph support in 6000.1.0a8; a background motion-vector fix in 6000.0.54f1; a matrices fix in 6000.3.0b3; UI and transparent SpaceWarp in 6000.5.0b1 (and 6.6); TextMeshPro SpaceWarp shaders in 6000.6.0b6. [T][C]
  - Source: https://unity.com/releases/editor/whats-new/6000.1.0a8 ; https://unity.com/releases/editor/whats-new/6000.5.0b1 ; https://unity.com/releases/editor/whats-new/6000.6.0b6 (accessed 2026-09-24) · Applies to: 6.0–6.6 · Evidence: [doc]
  - Notes: Projects that depend on SpaceWarp with UI or text over the world should target 6.5+/6.6.

### Adaptive Performance on Quest

- **U1-073** Adaptive Performance history: 6.0 lists an Android provider for Adaptive Performance. 6.3 moved Adaptive Performance into a core module. 6.6 added OpenXR support, which adjusts quality from device frame timing; Unity's untethered guide places it under a Basic provider. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity63.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ for Quest via OpenXR · Evidence: [doc] [verify on device]
  - Notes: No Unity page found that documents Adaptive Performance reading Quest thermal or CPU/GPU level data before 6.6. Meta's own performance APIs (CPU/GPU levels, dynamic resolution) are the alternative. How AP-OpenXR and Meta's dynamic resolution interact is undocumented.

## 2. Upgrade-path risks

Risks of moving a Quest URP project along 2021.3 -> 2022.3 -> 6.0 -> 6.3 -> 6.6. The UUM-93226 status is in the first subsection; the GLES-vs-Vulkan decision it drives is recorded in Conflict U1-C2.

### Vulkan buffer-copy issue (UUM-93226): current status

- **U1-074** UUM-93226, "[Performance] Vulkan performing much worse than OpenGLES due to excessive buffer copies on Quest 2/3". Filed 2025-01-17 in the Graphics XR category, with 21 votes and not marked as a regression. Found in 2022.3.56f1, 6000.0.33f1, 6000.1.0b2, 6000.2.0a1 and 6000.3.0a1. Tested on Quest 3 (Adreno 740) and Quest 2 (Adreno 650). [T]
  - Source: https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 (redirects to https://issuetracker.unity.com/issues/1364) (accessed 2026-09-24) · Applies to: 2022.3, 6.0–6.3 (reported); later versions not stated · Evidence: [measured]
  - Notes: In the repro, Vulkan had lower FPS and more stutter than GLES. It reproduced on both OpenXR and Oculus XR, with no difference between multi-pass, multiview and SPI. With MSAA off on the camera rig, FPS sat around 30 but the stutter stopped. The public entry has no GPU ms breakdown.

- **U1-075** Status: closed on 2025-12-09 with no fix version on any stream (6000.0, 2022.3, 6000.1, 6000.2 and 6000.3 ports). Unity's note puts the worst Vulkan-vs-GL gap down to a Qualcomm visibility-stream bug that shows up with many meshes and is expected to be fixed in a future Meta OS. Unity says the remaining extra buffer copies, with or without MSAA, are the Qualcomm cost of using Vulkan. [T][C]
  - Source: https://issuetracker.unity.com/api/v1.0/issues/1364 ; https://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 (accessed 2026-09-24) · Applies to: all versions in range · Evidence: [doc]
  - Notes: The label differs between the old and new tracker; see U1-C1. The resolution note is null in the new API and only readable in the Wayback snapshot of the old page.

- **U1-076** Unity's documented workaround for UUM-93226 is to turn on "Optimize Buffer Discard", available in both the OpenXR (Meta) and Oculus XR plugins. [T]
  - Source: https://issuetracker.unity.com/issues/1364 ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@1.12/manual/index.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc] [verify on device]
  - Notes: No number published for how much of the gap Optimize Buffer Discard recovers. Measure GLES vs Vulkan vs Vulkan with Optimize Buffer Discard on a high-mesh-count scene, recording GPU ms and stale frames with OVR Metrics Tool on the current Quest OS.

- **U1-077** No public confirmation found that a Meta OS release fixed the Qualcomm visibility-stream bug. A user asked for news on the Unity Discussions thread on 2026-05-22 and got no Unity reply as of the access date. [T]
  - Source: https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (accessed 2026-09-24) · Applies to: all · Evidence: [community] [verify on device]
  - Notes: Skills should not claim Vulkan is always faster on Quest. They should recommend A/B testing the specific content on the current OS.

### Render Graph and XR regressions (6.0 line)

- **U1-031 / U2-069** UUM-90118: with Render Graph on, Quest GPU utilization rose by about 20% from 6000.0.16f1. It was not reproducible on 6000.0.15f1, and it was reproduced on 6000.0.29f1 and 6000.1.0a6. The cause was a ReadOnlyDepth flag, set in XR on Android Vulkan, that stopped the depth-copy subpass merging into the pass before it (for example the uber post). It was listed as a known issue in 6000.0.40f1–45f1 and fixed in 6000.0.46f1, 6000.1.0b14 and 6000.2.0a9. [T]
  - Source: https://issuetracker.unity3d.com/issues/gpu-utilization-increases-by-20-percent-on-meta-quest-headsets-when-render-graph-is-enabled-on-6000-dot-0-16f1-and-higher ; https://unity.com/releases/editor/whats-new/6000.0.46f1 (accessed 2026-09-24) · Applies to: 6.0.16–6.0.45, 6.1 < b14 · Evidence: [measured]
  - Notes: The 20% figure comes from the tracker reproduction, not a Unity benchmark. The reporter also saw about 50% vs 90% GPU utilization, worse on Quest 2, firmware v71. Any Quest project on 6.0 older than .46 with Render Graph on should upgrade the patch before any other tuning.
  - **Merged U2-069:** Unity **UUM-90118**: from 6000.0.16f1, Quest 2 and Quest 3 showed up to about +20% GPU utilization with Render Graph enabled (worse on Quest 2). The cause was the ReadOnlyDepth flag stopping the Depth Copy pass from merging after the Uber Post pass on XR Android Vulkan. Fixed in 6000.0.46f1 (release note wording: up to 20% regression on Meta Quest), 6000.1.0b14 and 6.2. [T][C]
    - Source: https://issuetracker.unity.com/issues/21971/gpu-utilization-increases-by-20-on-meta-quest-headsets-when-render-graph-is-enabled-on-6000016f1-and-higher (accessed 2026-09-24) · Applies to: 6000.0.16f1 to 6000.0.45f1, early 6.1 betas · Evidence: [measured]
    - Notes: Release note: https://unity.com/releases/editor/whats-new/6000.0.46f1. The user-reported utilization readings were 50% and 90%. Not reproducible in 6000.0.15f1. If a project is pinned to 6000.0.16-45, upgrade before profiling. Related thread: https://discussions.unity.com/t/introduction-of-render-graph-in-the-universal-render-pipeline-urp/930355/707.
    - Spot-check (gap-fill round 1): corrected 6000.1.0b12 to 6000.1.0b14. The 6000.1.0b12 release notes list UUM-90118 under Known Issues, marked as fixed in 6000.1.0b14, and 6000.1.0b14 lists it under Fixes. U1-031 already had b14. Sources: https://unity.com/releases/editor/whats-new/6000.1.0b12 ; https://unity.com/releases/editor/whats-new/6000.1.0b14 (accessed 2026-09-24).

- **U1-078** UUM-92499 / UUM-93821: Render Graph `AddBlitPass` and `AddCopyPass` did not handle XR multiview array textures, so only the left eye rendered on Quest 2. Fixed in 6000.0.49f1 and 6000.1.0f1. Custom RG passes built from these helpers on earlier 6.0 patches break stereo. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.49f1 (accessed 2026-09-24) · Applies to: 6.0 < .49 · Evidence: [doc]

- **U1-079** UUM-84612: the player rendered black on Quest when MSAA, post-processing and SpaceWarp depth submission were all on. It was a known issue from 6000.0.40f1. A fix entry ("black screen with XR and the copy depth pass") appears in 6000.0.50f1 and 6000.2.0a1, though the issue link keeps appearing in 6.0 notes through 6000.0.58f1. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.50f1 (accessed 2026-09-24) · Applies to: 6.0.40–6.0.49 (at least) · Evidence: [doc] [verify on device]

- **U1-080** Other Quest-specific fixes in the 6.0 line: UUM-76868 turned off unused extensions that broke right-eye rendering on Quest 2 with OpenXR (6000.0.14f1). UUM-95617 stopped log spam from RenderGraph with MSAA (6000.0.38f1). UUM-104169 stopped GameManager logcat spam on Quest 2 (6000.0.49f1). UUM-109083 fixed Vulkan errors on app exit (6000.0.52f1, 6000.1.9f1, 6000.2.0b8). [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.14f1 ; https://unity.com/releases/editor/whats-new/6000.0.38f1 ; https://unity.com/releases/editor/whats-new/6000.0.49f1 ; https://unity.com/releases/editor/whats-new/6000.0.52f1 (accessed 2026-09-24) · Applies to: 6.0 early patches · Evidence: [doc]
  - Notes: Log spam costs CPU on device and hides real warnings. Together these make roughly 6000.0.52f1 the practical floor for Quest on 6.0, and Meta's floor of 6000.0.66f2 (U1-008) is higher still.

- **U1-081** GLES Quest fixes: UUM-91896 (render-pass validation errors in GLES multi-pass) was fixed in 6000.0.46f1 and 6000.1.0b14. UUM-93243 (crash in GLES ClearBufferSubData on second launch, Quest 2) was fixed in 6000.0.73f1, 6000.3.14f1 and 6000.5.0b8. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.46f1 ; https://unity.com/releases/editor/whats-new/6000.0.73f1 (accessed 2026-09-24) · Applies to: 6.0, 6.3 < .14 · Evidence: [doc]

### Foveation regressions

- **U1-082** Timeline for foveation support in URP: foveated rendering on Vulkan/D3D12 listed in 6.0 What's New; foveation in Forward+ (2022.3.16f1 and 6000.0.0b11); Render Graph support (6000.0.0b15); UberPost and FinalPostBlit support (6000.0.22f1). On 6.0, foveated post-processing needs 6000.0.22f1 or later. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html ; https://unity.com/releases/editor/whats-new/6000.0.22f1 (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]

- **U1-083 / U2-055** UUM-132450: black view on Quest when framebuffer fetch and foveated rendering were combined. The MSAA resolve attachment was chosen wrongly. Fixed in 6000.3.14f1, 6000.4.4f1 and 6000.5.0b5; no 6.0 entry found. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.3.14f1 (accessed 2026-09-24) · Applies to: 6.3 < .14, 6.4 < .4 · Evidence: [doc]
  - **Merged U2-055:** A known Quest bug renders the view black when framebuffer fetch is combined with foveated rendering in a player. It was linked by a user in the Unity on-tile thread. [C]
    - Source: https://issuetracker.unity3d.com/issues/the-view-renders-black-when-using-framebuffer-fetch-with-foveated-rendering-in-a-player-for-meta-quest (accessed 2026-09-24) · Applies to: 6.x, fixed version not captured · Evidence: [community]
    - Notes: Unity staff said on-tile post-processing does support foveated rendering. Check the issue's fixed-in version before shipping FB fetch plus FFR [verify on device]. The same thread reports passthrough failing when the camera's post-process flag is on.
  - Merge note: U1-083 supplies the fixed-in versions (6000.3.14f1, 6000.4.4f1, 6000.5.0b5) that U2-055 did not capture; the U2 gap is closed by this merge.

- **U1-084** UUM-113364: foveation was switched off when MSAA was on under Vulkan. Fixed in 6000.4.0b9 and 6000.5.0a7. The fix note says it applied to "PC or linked XR", so it is unclear whether standalone Quest was affected. [T]
  - Source: https://unity.com/releases/editor/whats-new/6000.4.0b9 (accessed 2026-09-24) · Applies to: 6.3 and earlier (if affected) · Evidence: [doc] [verify on device]
  - Notes: To check on 6.3, look at the foveation level in OVR Metrics or RenderDoc (fragment density map attachment present) with MSAA 2x/4x on and off.

### Vulkan PSO and pipeline-cache fixes

- **U1-086** Vulkan PSO and pipeline-cache fixes across the range: race conditions in Vulkan PSO cache registration and async PSO shutdown were fixed (6000.0.0b11). A corrupted pipeline cache is handled from 6000.4.0a2/a4. Vulkan GSC warmup was fixed only in 6000.4.0a4 (U1-047). 6.0 LTS and 6.3 LTS therefore carry older Vulkan warmup behaviour. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.0b11 ; https://unity.com/releases/editor/whats-new/6000.4.0a4 (accessed 2026-09-24) · Applies to: 6.0, 6.3 · Evidence: [doc] [verify on device]
  - Notes: No published hitch counts for Quest. Measure first-run hitches with a scripted camera path: record frames over 13.9 ms (72 Hz) or 11.1 ms (90 Hz) with and without a GSC collection.

### Memory-related changes

- **U1-087** UUM-121520 reduced the memory overhead of Vulkan command buffers when graphics jobs are used on Android. It shipped in 6000.2.12f1, 6000.3.0b8 (so 6.3.0f1 onwards) and 6000.4.0a2. No 6000.0 entry was found, so 6.0 LTS keeps the higher overhead. [T]
  - Source: https://unity.com/releases/editor/whats-new/6000.2.12f1 ; https://unity.com/releases/editor/whats-new/6000.3.0f1 (accessed 2026-09-24) · Applies to: 6.0, 6.2 < .12 · Evidence: [doc] [verify on device]
  - Notes: No published MB figure. Measure with `adb shell dumpsys meminfo <pkg>` (Graphics / GL mtrack) with graphics jobs on, comparing 6.0 and 6.3 builds.

- **U1-088** UUM-71363: Vulkan images now get the transient usage flag even when lazily allocated memory is unavailable. Shipped in 6000.0.23f1 and 2022.3.53f1. [T]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.23f1 ; https://unity.com/releases/editor/whats-new/2022.3.53f1 (accessed 2026-09-24) · Applies to: 2022.3 < .53, 6.0 < .23 · Evidence: [doc]

- **U1-089** 6.0 upgrade guide: mipmap limits (the Quality setting for texture mip limit) no longer apply to textures created at runtime by default. Projects that relied on the global mip limit to shrink runtime or procedural textures on Quest can see memory grow after upgrading. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html (accessed 2026-09-24) · Applies to: 2022.3 → 6.0 · Evidence: [doc] [verify on device]

- **U1-090** Meta: turning on "Offscreen Rendering Only" in the OpenXR settings saves about 10–20 MB at 2064x2208 per eye on Quest 3. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (accessed 2026-09-24) · Applies to: 6.x with OpenXR · Evidence: [doc]

### Oculus XR to OpenXR migration

- **U1-091** Unity deprecated the Oculus XR package (com.unity.xr.oculus) in 6000.5.0b4. From 6.5 and 6.6 the release notes list it as no longer supported on that Editor. Earlier versions bundled Oculus XR 4.5.2 as recently as 6000.0.57f1 and 6000.3.0b1. Separately, 6000.0.49f1 says the Unity XR SDK (the vendor provider SDK) is no longer available, as Unity focuses on OpenXR. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.5.0b4 ; https://unity.com/releases/editor/whats-new/6000.0.49f1 ; https://unity.com/releases/editor/whats-new/6000.0.57f1 (accessed 2026-09-24) · Applies to: 6.0–6.6 · Evidence: [doc]

- **U1-092** Meta says Unity's OpenXR plugin, via `com.unity.xr.meta-openxr`, has had feature and performance parity with the Oculus XR plugin since OpenXR Plugin 1.14. Meta's recommended OpenXR settings are Multi-View, Color Submission Auto, Latency Optimization set to Prioritize Input Polling, Depth Submission Mode None (unless SpaceWarp or composition needs depth), SRP Foveation on Unity 6+, Additional Graphics Queue off, and OpenXR Predicted Time (SDK v83+). [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-and-openxr-compatibility ; https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: 6000.2.0a10 bundles OpenXR 1.14.3. Gap-fill round 1 confirmed the number twice (rendered page and raw HTML): Meta's setup page (updated 2026-09-09) recommends Unity OpenXR Plugin 1.15.1, and Oculus XR Plugin 4.5.1 for the deprecated path. See U1-009.

- **U1-093** Migration risk: switching from Oculus XR to OpenXR changes the plugin that owns foveation, depth submission, the eye-buffer format and frame timing. Settings do not carry across automatically, so the performance baseline must be re-measured after the switch. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-project-setup/ (accessed 2026-09-24) · Applies to: 2021.3/2022.3 → 6.x · Evidence: [doc] [verify on device]
  - Notes: No published before/after frame-time data for a like-for-like migration was found.

### GLES deprecation path

- **U1-094** 6.6 raises the OpenGL ES minimum to 3.1. The manifest declares `glEsVersion 0x00030001`, and `PlayerSettings.openGLRequireES31` is deprecated. A transition setting, "Use OpenGL ES 3.0 shaders", is turned on automatically when a project that never used Require ES3.1 is upgraded. Turning it off gives ES3.1 shaders, which raise MAX_VISIBLE_LIGHTS from 16 to 32 and so add shader workload. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]
  - Notes: Quest hardware supports ES 3.2, so the new minimum does not lock Quest out. What changes is the light-count ceiling and the shader cost on GLES Quest builds. See U1-040.
  - Spot-check (gap-fill round 1): clarified. The upgrade guide enables "Use OpenGL ES 3.0 shaders" automatically only if the project never used Require ES3.1 or a similar setting. A project that already required ES 3.1 gets ES 3.1 shaders, and so the 32-light ceiling, straight away. Higher requirements use `openGLRequireES31AEP` / `openGLRequireES32`. Reverting to an ES 3.0 context is not possible.

- **U1-095** GLES loses features over the range. GRD, GPU occlusion culling and STP are unavailable on GLES from the start. Entities Graphics GLES support is deprecated (6000.3.12f1, 6000.4.1f1). Tile-Only falls back on non-sRGB GLES backbuffers (6000.6.0b6). Unity's untethered-XR guide calls Vulkan more stable and faster than GLES for XR URP. [T][C]
  - Source: https://unity.com/releases/editor/whats-new/6000.3.12f1 ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: GLES is not removed for Android in 6.6, but new Quest performance features target Vulkan. This sits in tension with UUM-93226 (U1-C2).

### Architecture, Android API and toolchain

- **U1-096** ARMv7 is not removed in this range. 6000.6.0a5 adds Burst notes for ARM32, and ARMv7 bug fixes continue through 6000.7.0b2. The Meta Quest build profile sets ARM64 by default. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html ; https://unity.com/releases/editor/whats-new/6000.6.0a5 (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: 6.5 removed x86-64 Android, which does not affect Quest.

- **U1-097** Minimum Android API by version: 6.0 raised it to 23 (Android 6.0). 6.3 raised it to 25 (Android 7.1). 6.5 raised it to 26 (Android 8.0), and API 23–25 only warn for now. The Meta Quest build profile already uses a minimum of 29 and a target of 32, so Quest-only projects that use the profile are not affected. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: The 2021.3 and 2022.3 minimum API levels were not verified this pass.

- **U1-098** Android build tools by version: 6.0 uses Gradle 8.4, AGP 8.3.0 and JDK 17. 6.1 uses Gradle 8.11, AGP 8.7.2 and NDK r27c. 6.3 moves to Gradle 9.1.0 and AGP 9.0.0; `proguard-android.txt` is no longer supported, custom plug-ins must declare a unique namespace, and an App Category setting covers Android 16 large-screen behaviour. Old Meta or third-party .aar plug-ins can break the build. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity61.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html (accessed 2026-09-24) · Applies to: 6.0, 6.1, 6.3 · Evidence: [doc]
  - Notes: The current 6.0 upgrade-guide page also shows a Gradle 9.1/AGP 9.0 table, which looks like shared content. Rely on the per-version release notes.

### API and pipeline breaks

- **U1-099** URP 13/14 (2021.3 → 2022.3) upgrade: 2022.1 moved to the RTHandle system (`cameraColorTargetHandle`, `RenderingUtils.ReAllocateIfNeeded`), and camera target access moved to `SetupRenderPasses`. URP 14 removed `SHADER_QUALITY_LOW/MEDIUM/HIGH` and `SHADER_HINT_NICE_QUALITY`; Unity suggests `SHADER_API_MOBILE` or `SHADER_API_GLES` instead. [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/upgrade-guide-2022-1.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/upgrade-guide-2022-2.html (accessed 2026-09-24) · Applies to: 2021.3 → 2022.3 · Evidence: [doc]
  - Notes: Custom shaders that used SHADER_QUALITY_LOW as a Quest switch silently take the default path after the upgrade.

- **U1-100** URP 17 (6.0) upgrade: custom passes should be rewritten for Render Graph. Custom VolumeComponents that override `Override()` must set `overrideState` to true whenever they change a value, or the Volume framework will not reset parameters correctly. 6.0 also makes `FindObjectsOfType` obsolete; `FindObjectsByType` is unsorted and faster. [C][T]
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/urp/upgrade-guide-unity-6.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html (accessed 2026-09-24) · Applies to: 2022.3 → 6.0 · Evidence: [doc]

- **U1-101** 6.5 breaks: the Built-in RP is deprecated (supported through the 6.7 LTS lifecycle; Unity's strategy page says end of 2028), the VR module is removed, Magic Leap is removed, the legacy Render Graph compiler is obsolete, the Rendering Debugger moved to UI Toolkit, and the Reflection Probe Shader Graph node is deprecated. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html ; https://unity.com/topics/render-pipelines-strategy-for-2026 (accessed 2026-09-24) · Applies to: 6.5+ · Evidence: [doc]
  - Notes: Code that still references `UnityEngine.VR` or the legacy `XRSettings` paths through the VR module fails to compile on 6.5.

### What's New pages, upgrade guides and the XR compatibility table

- **U1-102** The Unity 6.x What's New pages all sit under the 6.6 manual: `WhatsNewUnity6.html` (6.0), `WhatsNewUnity61.html` … `WhatsNewUnity66.html`. The matching upgrade guides are `UpgradeGuideUnity6.html` and `UpgradeGuideUnity61.html` … `UpgradeGuideUnity66.html`. Each What's New page lists changes since the previous release, and 6.0's lists changes since 2022 LTS. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (accessed 2026-09-24) · Applies to: 6.0–6.6 · Evidence: [doc]

- **U1-103** The URP-specific upgrade guides are URP 13 (`upgrade-guide-2022-1.html`) and URP 14 (`upgrade-guide-2022-2.html`) in the 14.0 package docs, then `urp/upgrade-guide-unity-6.html` (URP 17) and `urp/upgrade-guide-unity-6-1.html` (URP 17.1) in the Editor manual. From 6.2 on, URP breaking changes appear in the Editor upgrade guides rather than separate URP pages. [C]
  - Source: https://docs.unity3d.com/6000.1/Documentation/Manual/urp/upgrade-guide-unity-6-1.html (accessed 2026-09-24) · Applies to: 2021.3 → 6.x · Evidence: [doc]
  - Notes: A dedicated URP 17.2+ page was not searched for exhaustively.

- **U1-105** Unity's XR render-pipeline compatibility table is the single page for "does feature X work in XR" in each version. As of 6.6, besides STP it marks Lens Distortion and Physical Camera unsupported in XR. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]

## 3. URP asset and renderer settings

### URP Asset settings on tile GPUs

- **U2-001** The serialized defaults of a new URP Asset (read from source) are:
  - Depth Texture off, Opaque Texture off, Opaque Downsampling 2x Bilinear
  - **HDR on** (32-bit precision), MSAA Disabled, Render Scale 1.0, Upscaling Filter Auto
  - LOD Cross Fade on (Blue Noise), **Terrain Holes on**
  - Main and additional shadow maps 2048, shadow distance 50, 1 cascade, soft shadows off (quality Medium)
  - per-object light limit 4
  - SRP Batcher on, Dynamic Batching off
  - Store Actions Auto, color grading LDR with LUT 32, Volume Update Mode Every Frame

  For Quest, HDR, Terrain Holes and LOD Cross Fade are the defaults to change. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/Runtime/Data/UniversalRenderPipelineAsset.cs (accessed 2026-09-24); the same field defaults are in the 2021.3, 2022.3 and 6000.0 branches · Applies to: URP 12-17.x (fields added later default as listed) · Evidence: [doc]
  - Notes: templates and the Meta Quest build profile can ship different asset values than these script defaults. Audit the actual `.asset` files, not the Inspector's reset values.
  - Spot-check (gap-fill round 2): confirmed against the 6000.5/staging source. The `[SerializeField]` initializers are `m_RequireDepthTexture = false`, `m_RequireOpaqueTexture = false`, `m_OpaqueDownsampling = _2xBilinear`, `m_SupportsTerrainHoles = true`, `m_SupportsHDR = true`, `m_HDRColorBufferPrecision = _32Bits`, `m_MSAA = Disabled`, `m_RenderScale = 1.0f`, `m_UpscalingFilter = Auto`, `m_EnableLODCrossFade = true` (BlueNoise), shadow maps `_2048`, `m_ShadowDistance = 50`, `m_ShadowCascadeCount = 1`, `m_SoftShadowsSupported = false` (Medium), `m_AdditionalLightsPerObjectLimit = 4`, `m_UseSRPBatcher = true`, `m_SupportsDynamicBatching = false`, LDR color grading, LUT 32, `VolumeFrameworkUpdateMode.EveryFrame`. Store Actions was not re-checked.

- **U2-002** Turn **HDR** off for Quest. Unity says most untethered XR devices don't support HDR rendering, and disabling it reduces bandwidth. HDR also forces an intermediate color texture, which adds a final blit. The Tile-Only Mode list marks HDR unsupported. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: In URP 14 source, `RequiresIntermediateColorTexture` returns true when `isHdrEnabled` is true (see U2-030). HDR Precision (URP 14+) defaults to 32-bit (R11G11B10). The 64-bit option is documented as more bandwidth. Alpha Processing requires 64-bit HDR, so avoid it on Quest (https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html).

- **U2-003** Keep **Depth Texture** off. Unity's XR guidance says it adds copies and GMEM loads. With it on, URP inserts a Copy Depth pass, which splits the merged native pass. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: URP 12-17.x · Evidence: [doc]
  - Notes: if one pixel's own depth is enough, use the depth input attachment instead (U2-079, 6.6+; U2-087 for the Meta fork before 6.3). Any camera or renderer feature that calls `ConfigureInput(Depth)` re-enables the copy even with the asset toggle off. Check per camera: Camera > Rendering > Depth Texture can override the asset.

- **U2-004** Keep **Opaque Texture** off. It adds a Copy Color pass that forces the camera color off-tile. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html (accessed 2026-09-24) · Applies to: URP 12-17.x · Evidence: [doc]
  - Notes: The 6.6 asset reference adds a side effect. On mobile platforms without the StoreAndResolve store action, enabling Opaque Texture makes Unity silently ignore MSAA (https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html). The Opaque Downsampling default (2x Bilinear) also produces a half-size target. Under Render Graph, a different target size cannot merge with full-size passes (TargetSizeMismatch, U2-058).

- **U2-005** **Store Actions**: Auto (the default) uses Discard unless URP detects injected passes, then falls back to Store. Discard lowers bandwidth. Store stores every target of every pass. Unity says Store "significantly increases the memory bandwidth" on tile GPUs. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 12, URP 14, and the URP 17 Compatibility Mode path · Evidence: [doc]
  - Notes: In 6000.5 source the field and property carry `[Obsolete("#from(6000.0) #breakingFrom(6000.4)", true)]`, so under Render Graph the compiler's load/store audit decides instead (U2-062). The 6.6 manual still documents the setting (Conflict U2-C4). On URP 12/14, use Discard only after confirming no injected pass reads a discarded target.

- **U2-006** **MSAA** defaults to Disabled. Unity's untethered XR page recommends 2x as the balance, and notes MSAA only works with Forward and Forward+. The same page says MSAA breaks on-tile rendering: disable it if Tile-Only Mode or on-tile post-processing is enabled. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: all versions; the on-tile caveat applies to 6.3+ · Evidence: [doc]
  - Notes: Meta recommends 4x (U2-095). Unity staff say MSAA runs without intermediates on device (U2-051). See Conflicts U2-C1 and U2-C2. MSAA shrinks tiles and so raises bin count (U2-035).

- **U2-007** **Render Scale** on the asset is the XR eye-texture scale:
  - URP forwards it to `XRDisplaySubsystem.scaleOfAllRenderTargets` (U2-044).
  - Changing it reallocates the eye textures. Unity says don't change it every frame.
  - Values within 0.05 of 1.0 snap to 1.0 (source constant `kRenderScaleThreshold = 0.05`).

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html (accessed 2026-09-24) · Applies to: URP 12-17.x · Evidence: [doc]
  - Notes: The threshold is in `UniversalRenderPipeline.cs` (2022.3 branch, https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs). The 6.6 asset page says Render Scale is disabled on some platforms under On-Tile Validation.

- **U2-008** **Upscaling Filter**: Auto picks Nearest-Neighbor or Bilinear only when Render Scale is below 1.0. **FSR 1.0 stays active even at scale 1.0**, and STP forces TAA. Unity's tile XR page lists Upscaling filter as off-tile, and Tile-Only Mode disables it. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 12.1+ (the 12.1 docs page lists FSR), STP 6.0+ · Evidence: [doc]
  - Notes: A Unity staff forum post says FSR (any non-linear upscaler), FXAA, and TAA with RCAS force a final post blit (U2-070). In XR, render scale does not create an intermediate on its own (U2-045), but a non-Auto upscaler combined with post-processing does.

- **U2-009** **Soft Shadows** default off. Unity rates them as having high performance impact on tile-based platforms, naming untethered XR. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 14+ for quality tiers; URP 12 is on/off only · Evidence: [doc]
  - Notes: Quality tiers: Low = 4 PCF taps, Medium = 5x5 tent (default), High = 7x7 tent. If soft shadows are unavoidable, use Low. No Quest ms numbers were found (gap).

- **U2-010** **LOD Cross Fade** defaults to on (Blue Noise) in URP 14+. Unity's performance page says disable it on low-end mobile because it uses alpha test. The 2x2 Stencil dithering type uses stencil bits instead of alpha test and cuts shader variants. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html (accessed 2026-09-24) · Applies to: URP 14+ (not in URP 12) · Evidence: [doc]
  - Notes: The stencil variant uses stencil bit values 4 and 8 (6.6 asset page). The renderer reserves bits 0-3 for users, so check for conflicts with stencil-based effects. Measure the cost of alpha test on Adreno depth rejection on device [verify on device].

- **U2-011** Disable **Terrain Holes** (default on) unless holes are used. Both Unity's performance page and Unity's Meta OpenXR 2.6 graphics settings page say so. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/get-started/graphics-settings.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The same Meta OpenXR page lists the URP baseline: HDR off, Post-processing off, Intermediate Texture Auto.

- **U2-012** **Additional lights**:
  - Per Object Limit defaults to 4 and is ignored in Forward+.
  - For low-end devices, Unity's performance page suggests Per Vertex or Disabled.
  - With the Meta Quest build profile's shader optimizations and Per Object Limit = 1, Unity unrolls the light loop.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html (accessed 2026-09-24) · Applies to: 6.1+ for the build profile; the limit exists in all versions · Evidence: [doc]
  - Notes: Forward (non-plus) in URP 12/14 caps lights per object (the URP 14 renderer page says 9). For Forward+ on Quest, see U2-027.

- **U2-014** Each shadow map is a separate render target, and shadow cascades add draw passes. Unity's performance page says to lower shadow resolution, reduce cascade count (fewer passes), lower Max Distance, and disable additional-light shadows where possible. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Shadow passes are off-tile by nature, because the shadow map is sampled later, so the store is unavoidable. Budget them by resolution, not merge state. The Render Graph compiler can merge raster passes with no fragments that only set shadow globals (U2-060).

- **U2-015** Setting **Volume Update Mode** to Via Scripting removes the per-frame volume stack update. Unity's performance page lists it as a CPU saving. You must then call the volume update yourself when volumes change. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc]
  - Notes: This is a main-thread cost, so it matters most when the app is CPU-bound at 90/120 Hz. No Quest ms figure was found.

- **U2-017** When **On-Tile Validation** is active, the 6.6 asset Inspector disables these asset options:
  - Depth Texture, Opaque Texture, HDR, MSAA, Upscaling Filter
  - GPU Occlusion Culling, Renderer Features
  - Render Scale, on some platforms

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html (accessed 2026-09-24) · Applies to: 6.5+ · Evidence: [doc]
  - Notes: The same page lists GPU Resident Drawer's occlusion culling among the disabled options, which matters if a project relies on it for CPU savings (lead). MSAA is disabled in the Inspector under validation, which fits Unity's "MSAA breaks on-tile" statement but not the staff forum post (Conflict U2-C2).

- **U2-018** Settings available by URP version:
  - **URP 12 (2021.3)**: Forward/Deferred only. Depth Texture Mode is After Opaques or Force Prepass only. Native RenderPass toggle. Store Actions. No HDR Precision, no LOD Cross Fade, no soft-shadow quality tiers.
  - **URP 14 (2022.3)**: adds Forward+, After Transparents copy-depth, HDR Precision, LOD Cross Fade with dithering type, and soft-shadow quality.
  - **URP 17.0 (6.0)**: Render Graph is the default for new projects, with a Compatibility Mode toggle.

  [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/universalrp-asset.html and https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 12/14/17 · Evidence: [doc]
  - Notes: Per-6.x feature additions are in U2-073. The URP 12.1 docs page already lists FSR 1.0; whether that came via a 12.1.x patch was not confirmed (gap).

### Universal Renderer settings

- **U2-019** **Rendering Path**: keep Forward or Forward+.
  - Unity's untethered page rejects Deferred because the G-buffer causes multiple GMEM loads.
  - MSAA is unavailable in Deferred.
  - Under On-Tile Validation, Deferred and Deferred+ fall back to Forward and Forward+.

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: all versions; Deferred+ 6.1+ · Evidence: [doc]
  - Notes: The 6000.5 renderer editor warns that Deferred and Deferred+ are incompatible with Tile-Only Mode (https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/Editor/UniversalRendererDataEditor.cs). Under Render Graph, deferred uses framebuffer fetch (`UseFramebufferFetch = nativeRenderPassesEnabled` in 6000.3 source), but Unity's XR guidance still says Forward.

- **U2-020 / U3-058** **Depth Priming Mode**: keep it Disabled (the serialized default).
  - Auto is unsupported on Android, iOS and Apple TV.
  - Priming is unsupported with Deferred, with MSAA, and at runtime on TBDR mobile.
  - Unity's XR page adds that two views double the prepass cost, while the LRZ/HSR hardware already gives similar rejection.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc]
  - Notes: 6000.3 source hard-codes `depthPrimingRecommended = false` under `UNITY_ANDROID || UNITY_IOS ...`. It also turns priming off where a depth copy is unsupported, for example GLES with MSAA (https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRendererRenderGraph.cs). A source comment attributes the Disabled default to TextMesh issues.
  - **Merged U3-058:** Unity's untethered-XR guidance: disable depth priming. Two views multiply the prepass cost, and hardware Low-Resolution-Z (LRZ) or hidden surface removal gets a similar result for free. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: 6.0+ page (the setting exists in URP 14+) · Evidence: [doc]
    - Notes: U2 covers the setting itself. What matters here is that LRZ only helps if your shaders don't disable it (U3-059/060).

- **U2-021** **Depth Texture Mode** (copy depth) defaults and trade-offs:
  - Default is After Opaques in 2021.3 (URP 12) and After Transparents from 2022.3 (URP 14) onward.
  - After Transparents avoids the render-target switch between the opaque and transparent passes. That switch would store color to main memory and reload it, and the store/load of MSAA data on top makes it worse.
  - URP 12 has no After Transparents option, so any depth texture there splits the opaque/transparent pass.

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: URP 14+ for After Transparents · Evidence: [doc]
  - Notes: Serialized defaults are from `UniversalRendererData.cs` on the 2021.3 and 2022.3 branches (`m_CopyDepthMode`). The trade-off: transparents cannot read scene depth in the same frame (soft particles, depth-fade water) [verify on device].

- **U2-022** In a Unity staff forum walkthrough (Jan 2026), setting Depth Texture Mode to After Transparents re-merged the opaque, skybox and transparent passes into one native pass. With After Opaques, the Copy Depth split them. [T]
  - Source: https://discussions.unity.com/t/performant-and-energy-efficient-rendering-with-render-graph-and-on-tile-post-processing-for-untethered-xr-in-unity-6-3/1703007 (accessed 2026-09-24) · Applies to: 6.3 Render Graph · Evidence: [community]
  - Notes: The same post shows that enabling Depth Texture moves rendering onto the `_CameraTargetAttachment`/`_CameraDepthAttachment` intermediates and adds a "Blit Final To Back Buffer" pass. The copy still costs a depth store even when merging is restored.

- **U2-023** Set **Intermediate Texture** to Auto. Auto uses each pass's `ConfigureInput` declarations to decide whether an intermediate is needed. Always forces rendering through an intermediate, which Unity says might have "a significant performance impact". Always is also the serialized default on the renderer in every branch checked (2021.3 to 6000.5). [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc]
  - Notes: In URP 14 source, Always only creates the color texture when the renderer has renderer features. With zero features it is harmless, so audit once features are added. The Meta subpass guide and Unity's Meta OpenXR guide both specify Auto.

- **U2-025 / U1-063** **Tile-Only Mode** is a renderer checkbox (Rendering section) added in 6.5, serialized default false:
  - It warns on every property that would need a non-memoryless intermediate and blocks those features at runtime.
  - It adds Render Graph validation that throws on off-tile passes.

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html (accessed 2026-09-24) · Applies to: 6.5+ · Evidence: [doc]
  - Notes: Validation shares Project Settings > Graphics > Render Graph > Enable Validity Checks and is stripped from release builds. Disabling it can let rendering fall off-tile silently. The 6000.5 editor warns that post-processing is incompatible and suggests the On-Tile Post Processing feature instead.
  - **Merged U1-063:** Tile-Only Mode (6.5) checks camera, renderer and URP-asset settings, then warns about or automatically disables options that force extra passes. 6000.5.0a5 added an On-Tile Validation option. From 6000.6.0b6, Tile-Only falls back when the backbuffer is not sRGB (for example GLES in Linear). From 6000.3.23f1, on-tile is allowed only on the Universal Renderer. [T][C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html ; https://unity.com/releases/editor/whats-new/6000.6.0b6 ; https://unity.com/releases/editor/whats-new/6000.3.23f1 (accessed 2026-09-24) · Applies to: 6.3.23+, 6.5+ · Evidence: [doc]
    - Notes: GLES Quest builds in Linear colour space quietly lose on-tile post in 6.6. This is another reason to use Vulkan.

- **U2-026** The **Full Screen Pass Renderer Feature** defaults `fetchColorBuffer = true`, which sets `requiresIntermediateTexture = true`. That makes the camera render to an intermediate and adds a copy of the color. Unity's tile XR page lists "FullScreenPass if FetchColorBuffer is true" as off-tile. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/RendererFeatures/FullScreenPassRendererFeature.cs (accessed 2026-09-24) · Applies to: URP 14+ (feature), 6.3 source · Evidence: [doc]
  - Notes: For effects that only need the current pixel, write a raster pass with `SetInputAttachment` (U2-066) instead of the stock feature. In 6.3+ the feature uses `AddBlitPass`/`AddCopyPass` internally.

- **U2-028** **SSAO** (renderer feature): Unity says to disable it on untethered XR because it needs several passes with high impact on tile GPUs. The 6.3 version of the page lists a depth prepass, two blur passes and a blit. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The 6.6 page keeps the recommendation with shorter wording. No Quest ms figure was found.

- **U2-029** The **Decal** renderer feature requires an intermediate texture (tile XR page). Unity's performance page adds that decals cost an extra pass. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc]
  - Notes: The DBuffer and Screen Space techniques were not separately characterized for Quest (gap). Baked decal meshes or projected decal shaders avoid the feature entirely.

### XR specifics: stereo path, mirror view, occlusion mesh, resolution, MSAA, foveation

- **U2-040** Single Pass Instanced renders both eyes in one pass with instanced draws. On devices that support it, Unity replaces SPI with Multiview, and Meta Quest is named as a supported Android target. The Meta Quest build profile (6.1+) defaults Stereo Rendering Path to Instancing. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassStereoRendering.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Hand-written shaders that aren't SPI-ready render only the first array slice (left eye). If SPI is set where unsupported, Unity falls back to multi-pass, doubling draw passes. Build profile defaults: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html.

- **U2-042** On Android, the XR mirror view (companion-window blit) returns early in URP's core `XRMirrorView.RenderMirrorView`, with an XRTODO comment about the Quest plugin. Quest builds pay no mirror-view blit. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRMirrorView.cs (accessed 2026-09-24) · Applies to: 2022.3 and 6000.3 branches (same code) · Evidence: [doc]
  - Notes: On Link/PC VR the mirror blit does run, which is out of scope here. Don't count the mirror blit when reading Quest captures.

- **U2-043** **Occlusion mesh**: URP has an XR Occlusion Mesh pass that masks the invisible (nasal/edge) eye-buffer region with depth. A Jan 2025 report found that Unity 6 URP on Quest 2 drew no such pass because the display subsystem returned no mesh. The reporter said a newer OpenXR version fixed it (Apr 2025). The OpenXR plugin changelog notes that in 2022.3 the visibility mask does not create an occlusion mesh. [T]
  - Source: https://discussions.unity.com/t/xr-occlusion-mesh-missing-in-meta-quest-headsets/1584869 (accessed 2026-09-24) · Applies to: OpenXR plugin versions of that period, Unity 6.0 · Evidence: [community]
  - Notes: Confirm in the Frame Debugger or Render Graph Viewer that "XR Occlusion Mesh" runs on device [verify on device]. 6.2 adds Visible Triangle Mesh (U2-052). Multiview Render Regions is a separate, complementary nasal-region cull (U2-053).

- **U2-044** URP's asset Render Scale goes to the XR display: `XRSystem.SetRenderScale(renderScale)` sets `display.scaleOfAllRenderTargets` for every XR display. It runs at pipeline init and again per camera render. [T][C]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRSystem.cs (accessed 2026-09-24) · Applies to: URP 14; the same pattern in 17.x · Evidence: [doc]
  - Notes: Implication (not verified on device): because URP re-applies renderScale per camera, a value set through `XRSettings.eyeTextureResolutionScale` may be overwritten. That is consistent with Unity's statement that eyeTextureResolutionScale "isn't supported in URP" (Conflict U2-C3) [verify on device].

- **U2-045** In XR, URP's `isScaledRender` is false, so render scale alone never forces an intermediate texture. The eye texture itself is resized. Outside XR, scaled rendering does force one. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderer.cs (accessed 2026-09-24) · Applies to: URP 14 source · Evidence: [doc]
  - Notes: That is why render scale is the tile-safe resolution lever in XR, while the Upscaling Filter setting is not (U2-008).

- **U2-046** **XRSettings.renderViewportScale** is Unity's recommended URP resolution control:
  - It is per-frame, with no eye-texture reallocation, and is compatible with FFR.
  - It is only a hint to the runtime; read `XRSettings.appliedRenderViewportScale` to see what applied.
  - With post-processing on, enable Camera > Output > URP Dynamic Resolution (uses ScalableBufferManager). Unity says this path is not compatible with FFR or TAA.

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html (accessed 2026-09-24) · Applies to: URP (page versions 6.3-6.6) · Evidence: [doc]
  - Notes: The page says URP renders directly to the eye texture when post-processing is off "or when you enable HDR". This looks inverted, since HDR forces an intermediate (U2-030), so flag it as a likely doc error. The 6.6 on-tile page lists dynamic resolution as off-tile except on Android XR (U2-032).

- **U2-047** Changing URP asset Render Scale reallocates the eye texture, which Unity calls expensive. Do not change it every frame. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html (accessed 2026-09-24) · Applies to: URP 12-17.x · Evidence: [doc]
  - Notes: Set it once at boot or at level load. A runtime change is a hitch risk.

- **U2-048 / U1-044** Automatic viewport dynamic resolution requires Unity 6.3+ and OpenXR 1.16+. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/WhatsNewUnity63.html (accessed 2026-09-24) · Applies to: 6.3+ · Evidence: [doc]
  - Notes: Lead for the dynamic-resolution/Adaptive Performance topic. Adaptive Performance for OpenXR (Basic provider) arrived in 6.6.
  - **Merged U1-044:** 6.3 added automatic viewport dynamic resolution for OpenXR headsets, which scales resolution based on device performance. UUM-83765 (Quest Vulkan distortion when changing the viewport resolution scale) was fixed in 6000.0.25f1. UUM-143709 (blocky or shifted XR lighting with dynamic resolution in Deferred/Forward+) was fixed in 6000.0.84f1. [T][C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html ; https://unity.com/releases/editor/whats-new/6000.0.25f1 ; https://unity.com/releases/editor/whats-new/6000.0.84f1 (accessed 2026-09-24) · Applies to: 6.0+, 6.3+ · Evidence: [doc] [verify on device]

- **U2-049** Meta eye-buffer defaults:
  - Default eye-buffer resolution: Quest 2 1440x1584, Quest 3 1680x1760, Quest 3S 1680x1760.
  - Physical panel resolution: Quest 2 1832x1920, Quest 3 2064x2208, Quest 3S 1832x1920.
  - Scale that matches physical pixels: about 1.24 (Quest 2), 1.09 (Quest 3S), 1.23 (Quest Pro).

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-render-scale/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Meta's Quest 3 examples: 0.8 gives 1344x1408 and 1.5 gives 2520x2640. VRC.Quest.Performance.4 sets minimum render-scale thresholds (lead for the store-requirements topic). Meta says Dynamic Resolution overrides both render-scale knobs.

- **U2-050** URP sends the MSAA level to the XR display: `XRSystem.SetDisplayMSAASamples` (from the asset's MSAA count / QualitySettings.antiAliasing) calls `display.SetMSAALevel`, so the eye swapchain itself is multisampled. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRSystem.cs (accessed 2026-09-24) · Applies to: URP 14; the pattern persists in 17.x · Evidence: [doc]
  - Notes: The Meta subpass page warns that OVRManager's "Use Recommended MSAA Level" causes a first-frame glitch with the subpass branches. Keep one owner of MSAA: the URP asset.

- **U2-051** Unity staff (AljoshaD, Jan 2026): in the Editor or on desktop, the backbuffer is single-sample, so the Render Graph shows MSAA intermediates. On device (Quest, Android Vulkan), a development build connected to the viewer shows rendering without intermediates, straight to an MSAA backbuffer. [T]
  - Source: https://discussions.unity.com/t/performant-and-energy-efficient-rendering-with-render-graph-and-on-tile-post-processing-for-untethered-xr-in-unity-6-3/1703007 (accessed 2026-09-24) · Applies to: 6.3+ on Quest · Evidence: [community]
  - Notes: This contradicts the 6.6 docs' "MSAA breaks on-tile rendering" for the plain (no on-tile PP) case (Conflict U2-C2). The practical rule: only trust device captures. A community port (Torgo13, 6000.3.12f1, desktop) counted 6 passes base, 7 with MSAA and 8 with Depth Texture.

- **U2-052 / U1-043 / U1-054** Unity 6.2 XR improvements:
  - VK_QCOM_render_pass_shader_resolve is enabled for MSAA on untethered XR such as Quest, so the MSAA resolve happens in-shader in the last subpass.
  - Visible Triangle Mesh limits post-processing to visible (non-occlusion-mesh) pixels.
  - Thin LTO arrived for Quest builds.

  [T]
  - Source: https://docs.unity3d.com/6000.2/Documentation/Manual/WhatsNewUnity62.html (accessed 2026-09-24) · Applies to: 6.2+ · Evidence: [doc]
  - Notes: In the compiler, a pass using `MultisampledShaderResolve` must be the last pass of its native pass (`MultisampledShaderResolveMustBeLastPass`), and its input attachments must be memoryless (6000.5 source). No Quest ms delta was published (gap).
  - **Merged U1-043:** 6.2 turned on Qualcomm's `VK_QCOM_render_pass_shader_resolve` so MSAA can be used on untethered XR such as Quest. Unity's untethered guide calls MSAA 2x a good balance and notes that MSAA works only with Forward/Forward+ and breaks Tile-Only/on-tile paths. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity62.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: 6.2+ · Evidence: [doc] [verify on device]
    - Notes: No number was published for the MSAA resolve cost before and after 6.2 on Quest.
  - **Merged U1-054:** 6.2 enabled thin Link Time Optimization of engine code for the Meta Quest profile (6000.2.0a8). [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity62.html (accessed 2026-09-24) · Applies to: 6.2+ · Evidence: [doc] [verify on device]
    - Notes: No published number found. Measure CPU main- and render-thread ms with the profile on, compared with a manual build without LTO.

- **U2-054 / U1-085** For **foveated rendering state**, URP's DrawObjects, Skybox and Occlusion Mesh passes call `builder.EnableFoveatedRasterization(...)` when XR supports foveation. The compiler refuses to merge passes whose foveation state differs (`FRStateMismatch`). A custom raster pass on camera color that doesn't set the same state will split the native pass. [T][C]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs (accessed 2026-09-24) · Applies to: 6.0+ Render Graph · Evidence: [doc]
  - Notes: The URP pattern (6000.3 `DrawObjectsPass.cs`): `passSupportsFoveation = cameraData.xrUniversal.canFoveateIntermediatePasses || resourceData.isActiveTargetBackBuffer`, then `EnableFoveatedRasterization(cameraData.xr.supportsFoveatedRendering && passSupportsFoveation)`. FinalBlit and post-processing disable foveation when the device reports NonUniformRaster.
  - **Merged U1-085:** Meta says SRP Foveation (Unity 6+) is often 20–30% faster in frame time than Legacy foveation when post-processing, deferred or multi-pass rendering is used. It is controlled with `builder.EnableFoveatedRasterization(bool)` on Render Graph passes. [T]
    - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (accessed 2026-09-24) · Applies to: 6.0+ with OpenXR · Evidence: [doc] [verify on device]
    - Notes: This is a vendor claim with no published method or scene. Custom RG passes that do not call EnableFoveatedRasterization render at full density, a silent throughput loss after a 2022 → 6.x port.

### Unity and Meta configuration pages (cross-checked)

- **U2-090** Unity's "Configure for better performance" (URP 6.6), relevant items:
  - Memory: Depth/Opaque textures off; HDR off, or 32-bit if needed; lower shadow resolution; Store Actions Auto/Discard on low-end mobile; Intermediate Texture Auto (verify in the Frame Debugger); minimize Decals; strip variants.
  - CPU: Volume Update Mode Via Scripting; no probe blending or box projection; fewer cascades; no additional-light shadows; fewer cameras.
  - GPU: reduce or disable MSAA; Terrain Holes off; SRP Batcher on; LOD Cross Fade off on low end; additional lights Per Vertex/Disabled; soft shadows off or low quality; Native RenderPass on Vulkan/Metal/DX12; Depth Priming Disabled on mobile; Depth Texture Mode After Transparents; Baked Lit/Simple Lit over Complex Lit.

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html (accessed 2026-09-24) · Applies to: URP generic (not XR-specific) · Evidence: [doc]
  - Notes: The MSAA advice conflicts with the XR and Meta pages (Conflict U2-C1). The Native RenderPass item is stale under Render Graph (Conflict U2-C4).

- **U2-091** Unity's Meta OpenXR 2.6 "graphics settings" page:
  - Vulkan first in the API list.
  - URP: Terrain Holes off, HDR off, Post-processing off, Intermediate Texture Auto.
  - The Built-In Render Pipeline is deprecated from 6.5.

  [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/get-started/graphics-settings.html (accessed 2026-09-24) · Applies to: Unity OpenXR Meta 2.6 · Evidence: [doc]
  - Notes: The "Post-processing off" recommendation predates or ignores on-tile PP. Reconcile per Unity version (off before 6.3; on-tile PP from 6.3).

- **U2-092** Meta says 4x MSAA is "extremely cheap" on its tile GPUs per internal benchmarks, and recommends it. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/gpu-improved-algorithms/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The underlying measurements are not published on that page. See U2-093 for the only numbers found.

- **U2-093** Meta's native MSAA analysis:
  - Overall: MSAA adds about 0.5-1.5 ms per frame, and about 10-15% for medium content. Don't exceed 4x.
  - Test 1 (GPU level 2, one eye): render 2.65 → 3.15 ms, resolve 0.17 → 0.44 ms.
  - Test 2 (GPU level 4, both eyes): render 10.449 → 11.497 ms, resolve 0.313 → 0.626 ms.
  - Test 4 (trivial load): render 0.044 → 0.388 ms, resolve 0 → 0.44 ms. Direct rendering occurs only with MSAA off.

  [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-msaa-analysis/ (accessed 2026-09-24) · Applies to: Quest 1 hardware (1216x1344 eye buffer); stale for Quest 2/3 · Evidence: [measured]
  - Notes: No Quest 2/3 MSAA cost numbers were found (gap). Re-measure with ovrgpuprofiler render-stage timing on the target device [verify on device].

- **U2-094** Meta's advanced GPU pipeline page states that Vulkan is "the required graphics API" for Meta Quest development. Unity's Meta Quest build profile defaults to Vulkan. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: current Quest development · Evidence: [doc]
  - Notes: Lead for the platform/store-requirements topic, to confirm whether this is a store requirement or guidance.

- **U2-095** Meta's tiled-GPU page recommends the Tile Timeline in the RenderDoc Meta Fork to inspect bins, with an example of 135 bins of 96x176. Every bin of every non-merged pass pays its own GMEM load/store, so bin count times pass count is the cost multiplier to watch. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ (accessed 2026-09-24; page dated Dec 4 2024) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Use it alongside the Render Graph Viewer. The viewer shows intent; RenderDoc and ovrgpuprofiler show what the driver actually did.

## 4. Render Graph on tile GPUs

Render Graph merging rules, load/store audit, on-tile post-processing and the pre-Render-Graph path. Render Graph version history (Compatibility Mode removal, viewer availability) is in section 1; the UUM-90118 regression is in section 2.

### What adds a pass or forces a GMEM load, store, resolve, copy or final blit

- **U2-030** In URP 14 source, `RequiresIntermediateColorTexture` returns true for any of:
  - a base camera in a stack that doesn't resolve the final target;
  - the Deferred path;
  - post-processing on;
  - Opaque Texture required;
  - an explicit MSAA resolve;
  - a non-default viewport rect;
  - the Scene view;
  - a scaled render (non-XR only);
  - HDR on;
  - camera capture actions;
  - an sRGB conversion requirement.

  Any of these moves rendering to an intermediate plus a final blit. [T][C]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderer.cs (accessed 2026-09-24) · Applies to: URP 14 (the logic carries into 17.x in modified form) · Evidence: [doc]
  - Notes: Use this as the checklist when the Frame Debugger or Render Graph Viewer shows a "Final Blit"/"Blit Final To Back Buffer" pass. Camera-level overrides (post-processing checkbox, viewport rect, per-camera Depth/Opaque texture) count too.

- **U2-031** Unity's tile XR page lists what to avoid on untethered XR:
  - intermediate textures;
  - Depth and Opaque textures;
  - Upscaling filter;
  - URP's built-in post-processing;
  - renderer features that need intermediates (Decal, FullScreenPass with FetchColorBuffer, SSAO).

  Each adds a final blit and breaks tile rendering. Only memoryless intermediates stay on-tile, and they require Vulkan or Metal. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html (accessed 2026-09-24) · Applies to: 6.3+ pages; the physics applies to all versions · Evidence: [doc]
  - Notes: The goal the page states is a single merged native render pass straight into the eye texture.

- **U2-032** The 6.6 on-tile rendering page lists these as breaking on-tile:
  - Depth/Opaque textures, TAA, MSAA, built-in post-processing, HDR
  - upscaling and dynamic resolution (both "except on Android XR")
  - IMGUI, subrectangle viewports, camera stacking, the Deferred path

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html (accessed 2026-09-24) · Applies to: 6.5+ · Evidence: [doc]
  - Notes: It is unclear whether "Android XR" means Google's Android XR platform only or any Android XR target including Quest (gap). IMGUI (OnGUI debug overlays) is an easy thing to leave in dev builds by accident.

- **U2-033** Meta on tile GPUs: reading the output of a previous pass needs a resolve to main memory, and main-memory reads are roughly 10x slower than on-chip. Copying or blitting into the swapchain afterwards may prevent FFR and MSAA from applying. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/gpu-impaired-algorithms/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The same page notes vertex shaders run once for binning and again per tile they touch (up to 2 × tiles + 1). Heavy vertex work in a multi-pass setup multiplies.

- **U2-034** A full-screen pass with no depth attachment and no MSAA can drop into Adreno Direct Mode: one bin, bypassing tiling, and FFR is disabled. In ovrgpuprofiler it shows as a single full-surface bin. Meta also says a two-pass Unity pipeline on GLES gets no FFR. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Meta's example line shows a 1216x1344 surface as one bin taking 2.01 ms. The resolution is Quest 1-era, so re-measure. A URP final blit with no depth or MSAA fits this pattern [verify on device].

- **U2-035** Tile memory (GMEM) is about 1 MB on Adreno 650 (Quest 2) and about 2 MB on Adreno 740 (Quest 3/3S). In Meta's example (XR2, multiview, 4x MSAA, 32-bit color, D24S8), a pixel costs 32 bytes, giving 96x176 tiles. Raising per-pixel bytes (MSAA, HDR, more attachments) shrinks tiles and raises bin count. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Meta's tiled-GPU page gives a generic 1-5 MB range and eye-texture sizes of 6.52 MB (1440x1584 RGB8) and 8.46 MB (1680x1760), so the eye buffer never fits in GMEM at once (https://developers.meta.com/horizon/documentation/unity/gpu-tiled/). HDR's 64-bit precision doubles color bytes per pixel.

- **U2-036** Meta's ovrgpuprofiler "bad config" example: a 1216x1344 surface, MSAA 2, 28 bins of 320x192, 10.62 ms total. Of that, LoadColor was 0.71 ms, LoadDepthStencil 0.828 ms, StoreDepthStencil 0.871 ms and StoreColor 1.525 ms, so about 3.9 ms was load/store traffic. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 1-class data; the method applies to Quest 2/3 · Evidence: [measured]
  - Notes: Meta's fixes: clear or invalidate at pass start, and use DONT_CARE for depth and MSAA stores. Under Render Graph, look for StoreReason/LoadReason in the viewer (U2-062). Use `ovrgpuprofiler -t -p` style render-stage traces on device to confirm.

- **U2-037** Meta's Vulkan guidance:
  - Resolve MSAA only in the last subpass, through `pResolveAttachment`. An intermediate MSAA resolve forces a store.
  - Intermediate STORE ops break the tile flow.
  - Using `VK_ACCESS_SHADER_READ_BIT` as the dstAccessMask breaks subpasses (use `VK_ACCESS_INPUT_ATTACHMENT_READ_BIT`).
  - On Adreno 540/650, reading 2 input-attachment MSAA subsamples in parallel is free but 4 is not.

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2 (Adreno 650); Adreno 740 not stated · Evidence: [doc]
  - Notes: These are driver-level rules Unity's Render Graph compiler follows for you. They matter when reading RenderDoc captures or writing native plugins. Adreno 740 behavior is unknown (gap).

- **U2-038** Integrated post-processing adds intermediates and an Uber "Blit Post Processing" pass. Bloom adds mip passes ("Blit Bloom Mipmaps"). FXAA, a non-linear upscaler such as FSR, and TAA with standalone RCAS each force a final post blit even when other effects are off. [T][C]
  - Source: https://discussions.unity.com/t/performant-and-energy-efficient-rendering-with-render-graph-and-on-tile-post-processing-for-untethered-xr-in-unity-6-3/1703007 (accessed 2026-09-24) · Applies to: URP 17.3 (6.3) Render Graph · Evidence: [community]
  - Notes: Unity staff post with Render Graph Viewer screenshots. Before 6.3, Unity's XR advice was to disable post-processing entirely. The camera's Post Processing checkbox is part of the trigger.

- **U2-039** Camera stacking:
  - A base camera whose stack doesn't resolve the final target forces an intermediate (URP 14 source).
  - Tile-Only Mode lists camera stacking as unsupported.
  - Unity's performance page says to minimize camera count.

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Put UI and hands into the base camera, or use compositor layers (lead for the compositor topic), instead of overlay cameras.

### Native pass merging rules and Render Graph APIs

- **U2-057 / U1-028** The Render Graph (default for new projects since 6.0) culls unused passes, reuses memory, and on TBDR GPUs merges compatible raster passes into native render passes (Vulkan subpasses). The goal on Quest is one native pass from first opaque to eye-texture write. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-introduction.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: 6.3 shares one compiler between URP and HDRP. 6.2 made subpass merging stricter with early exits. 6.1 added a debug setting to disable pass merging, which is useful for A/B bandwidth tests (What's New 6.1/6.2/6.3).
  - **Merged U1-028:** Under Render Graph (6.0+), native render pass and subpass merging is done by the Render Graph compiler. 6.1 added a debug setting that turns off pass merging so you can isolate problems. 6.2 optimized the subpass-merge logic and ExecuteBeginRenderPass lookups, which are CPU-side. 6.3 moved URP and HDRP onto one shared Render Graph compiler. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity61.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity62.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html (accessed 2026-09-24) · Applies to: 6.1+ · Evidence: [doc]
    - Notes: The shared compiler in 6.3 means pass-merge behaviour can differ between 6.0 and 6.3 for the same renderer features. After upgrading, re-check merged passes in the Render Graph Viewer.

- **U2-058** The Native Pass Compiler's `PassBreakReason` values and what to do about each:
  - `NonRasterPass`: compute or unsafe passes. Only raster passes merge.
  - `TargetSizeMismatch`: different size or MSAA sample count.
  - `NextPassReadsTexture`: the next pass samples this output as a texture. Use an input attachment instead.
  - `NextPassTargetsTexture`
  - `DifferentDepthTextures`: one depth per native pass.
  - `AttachmentLimitReached`: 8 attachments.
  - `SubPassLimitReached`: 8 subpasses.
  - `FRStateMismatch`
  - `DifferentShadingRateImages` / `DifferentShadingRateStates`
  - `MultisampledShaderResolveMustBeLastPass`
  - `ExtendedFeatureFlagsIncompatible`
  - `PassMergingDisabled`
  - `BackbufferInMultipleRenderTargetsNotSupported`
  - `EndOfGraph`, `Merged`

  [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs (accessed 2026-09-24) · Applies to: 6000.5 (Unity 6.0 has only the values up to `FRStateMismatch` plus `Merged`) · Evidence: [doc]
  - Notes: The viewer's "Pass break reasoning" shows these names, so map them to the fixes above. The pixel-storage limit check applies only to iOS GPU families, not Adreno.

- **U2-059** `BackbufferInMultipleRenderTargetsNotSupported` breaks a merge when one pass targets the backbuffer and another targets user render targets. It triggers only where `SystemInfo.supportsBackbufferInMultipleRenderTargets` is false. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs (accessed 2026-09-24) · Applies to: 6.5-era source · Evidence: [doc]
  - Notes: Log `SystemInfo.supportsBackbufferInMultipleRenderTargets` on Quest 2 and Quest 3 once [verify on device]. It decides whether MRT custom passes (e.g. writing a mask alongside eye color) can stay merged.

- **U2-060** Two merge exemptions in the compiler:
  - Raster passes with no fragment attachments (for example, passes that only set shadow globals) can merge without the attachment checks.
  - Reading a texture whose producing pass was culled does not break the merge.

  [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs (accessed 2026-09-24) · Applies to: 6000.5 source (with NativePassCompiler.cs in the same folder) · Evidence: [doc]
  - Notes: Put "set globals" work in a raster pass with no attachments rather than an unsafe pass, which would break the chain.

- **U2-061** Memoryless attachments:
  - The compiler marks a transient attachment memoryless only when `SystemInfo.supportsMemorylessTextures` is true.
  - Loading or resolving a memoryless resource throws.
  - Input attachments used with multisampled shader resolve must be memoryless.

  [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/NativePassCompiler.cs (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: In the viewer's Resource List, the Memoryless column confirms it. `_CameraDepthAttachment` drawn with an empty square in the viewer means memoryless (Unity staff post, thread 1703007).

- **U2-062** Load and store audit reasons appear per attachment in the viewer:
  - Loads: `LoadImported`, `LoadPreviouslyWritten`, `ClearImported`, `ClearCreated`, `FullyRewritten`.
  - Stores: `StoreImported`, `StoreUsedByLaterPass`, `DiscardImported`, `DiscardUnused`, `DiscardBindMs`, `NoMSAABuffer`.

  On Quest the target state is Clear/FullyRewritten at the start, and only the eye color stored at the end. `StoreUsedByLaterPass` on depth means something downstream reads depth. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: This replaces the URP 12/14 Store Actions setting (U2-005).

- **U2-063** Author custom passes as raster passes, with these API rules:
  - Use `AddRasterRenderPass<PassData>` in `RecordRenderGraph`.
  - Declare reads with `UseTexture` and color targets with `SetRenderAttachment(tex, 0)`.
  - Use a static lambda in `SetRenderFunc`.
  - Only set `AllowPassCulling(false)` for debugging.

  Unity's optimization page adds: reuse URP's Copy Color/Copy Depth via `ConfigureInput` instead of your own copies, and prefer raster passes. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-optimize.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: Write-pass reference: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-write-render-pass.html.

- **U2-064** `AddUnsafePass` (with `UnsafeGraphContext` and manual `SetRenderTarget`) prevents Render Graph optimization of that pass: it never merges. Compute passes don't merge either. Unity staff confirmed that compute on camera color cannot stay on-tile. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-unsafe-pass.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: The builder from `AddComputePass`/`AddUnsafePass` has no `SetInputAttachment` (thread 1703007). Auto-exposure or histogram work on Quest therefore costs a store of camera color. Move it to a small downsample or to last-frame data.

- **U2-065** Avoid "blit back". After writing to a new texture, set `resourceData.cameraColor = destination` rather than copying back into the camera color. Unity's AddBlitPass example does this. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-optimize.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: Each blit back is a full-screen pass, and at eye-buffer size on Quest that is a full-resolution store plus load when not merged.

- **U2-066** Framebuffer fetch (input attachments) in Render Graph:
  - Bind with `builder.SetInputAttachment(sourceHandle, 0, AccessFlags.Read)`.
  - Declare with `FRAMEBUFFER_INPUT_X_HALF/FLOAT/INT/UINT(0)` and read with `LOAD_FRAMEBUFFER_X_INPUT(0, input.positionCS.xy)`; include `Blit.hlsl`.
  - It stays on-chip on Vulkan and Metal. On other APIs Unity falls back to copies through video memory.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-framebuffer-fetch.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: The `_X` macros are the XR (texture-array) variants. Only the current pixel is readable, so no blur, bloom or distortion. The "FrameBufferFetch" sample is under URP RenderGraph Samples (U2-072).

- **U2-067** `RenderGraph.AddBlitPass` / `AddCopyPass`:
  - With the default material, the blit can become an `AddCopyPass`, which uses framebuffer fetch and so can merge.
  - In 6.3, `AddBlitPass` returns a builder (`returnBuilder: true`), can target the backbuffer, and supports depth blit with automatic MSAA resolve.
  - URP's FullscreenPassRendererFeature and CopyColorPass use these internally from 6.3.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-blit.html (accessed 2026-09-24) · Applies to: 6.0+ (the builder return is 6.3+) · Evidence: [doc]
  - Notes: 6.3 changes from https://docs.unity3d.com/6000.3/Documentation/Manual/WhatsNewUnity63.html. Parameters go through `RenderGraphUtils.BlitMaterialParameters`.

- **U2-068** Unity's blit guidance:
  - Do not use `CommandBuffer.Blit`, `Graphics.Blit` or `RenderingUtils.Blit` in URP: they can break XR and native render passes.
  - Use `Blitter` (`Blitter.BlitCameraTexture` / `Blitter.BlitTexture`).
  - Blitter-compatible shaders must be hand-written; the page says Shader Graph is not compatible.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/customize/blit-overview.html (accessed 2026-09-24) · Applies to: URP 14+ · Evidence: [doc]
  - Notes: The Blitter uses the XR-aware `Blit.hlsl` (`Vert`, `Attributes`, `Varyings`, `TEXTURE2D_X`), which handles SPI/multiview correctly.

- **U2-070** Unity staff Render Graph walkthrough on Quest-class settings (thread started 2026-01-07):
  - A minimal pipeline renders straight to the backbuffer in one native render pass.
  - Enabling Depth Texture splits the pass and moves to intermediates plus a final blit.
  - Post-processing adds intermediates and Uber blit passes.
  - The optimal 6.3 setup (on-tile PP) has no final blit and no intermediate color/depth stores.

  [T][C]
  - Source: https://discussions.unity.com/t/performant-and-energy-efficient-rendering-with-render-graph-and-on-tile-post-processing-for-untethered-xr-in-unity-6-3/1703007 (accessed 2026-09-24) · Applies to: 6.3+ · Evidence: [community]
  - Notes: A Quest 3 bandwidth/GPU-time comparison chart exists in the post but only as an image, so no numbers were captured (gap). The Unite Barcelona 2025 talk "Glow up your graphics with Unity 6.3 LTS and beyond" covers it at about 26:35 (https://www.youtube.com/watch?v=K3-wPnhmDi4).

- **U2-071 / U1-029** Render Graph Viewer:
  - Open it from Window > Analysis > Render Graph Viewer. From 6.3 it connects to a Development Build on device (Target Selection: Editor, Local, Remote, Direct Connection). Unity's What's New calls out Quest 3.
  - Legend: green = read, red = write, gray = none, globe icon = global texture, "F" = on-chip framebuffer read.
  - View Options > Load Store Actions draws triangles: blue = clear, green = load, red = store, gray = don't care.
  - A blue bar marks merged passes. The Pass List shows Native Render Pass Info and "Pass break reasoning"; the Resource List shows Memoryless, BindMS and Samples.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-viewer-reference.html (accessed 2026-09-24) · Applies to: 6.0+ (on-device connection 6.3+) · Evidence: [doc]
  - Notes: How-to: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-view.html. Editor graphs differ from device graphs (U2-051), so capture on the headset.
  - **Merged U1-029:** The Render Graph Viewer arrived in 6.0. From 6000.0.23f1 it can open while in Compatibility Mode. From 6.3 it can connect to player builds on device, including Quest 3. Unity presents that as the way to find unmerged passes and unnecessary load/store actions on untethered XR. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html (accessed 2026-09-24) · Applies to: 6.3+ (on-device) · Evidence: [doc]

- **U2-072** Unity ships example passes under Samples > Universal Render Pipeline > 17.3.0 > URP RenderGraph Samples: Blit, BlitWithFrameData, BlitWithMaterial, FrameBufferFetch, UnsafePass. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-framebuffer-fetch.html (accessed 2026-09-24) · Applies to: 6.3+ package versions · Evidence: [doc]
  - Notes: FrameBufferFetch is the template for tile-friendly per-pixel effects. BlitWithMaterial shows the texture-sampling path that breaks merging.

- **U2-073** Tile-relevant changes by Unity 6.x release:
  - 6.1: Deferred+, VRS API (DX12/Vulkan), a debug switch to disable pass merging, the Meta Quest build profile.
  - 6.2: stricter merging, Visible Triangle Mesh, QCOM shader resolve, Quest thin LTO.
  - 6.3: shared RG compiler, on-device RG Viewer, AddBlitPass builder, XR on-tile post-processing, Kawase/Dual bloom filters, automatic viewport dynamic resolution.
  - 6.4: URP Compatibility Mode removed for custom passes (the `URP_COMPATIBILITY_MODE` define is gone).
  - 6.5: on-tile PP for all platforms, Tile-Only Mode, Quest shader optimizations, `UNITY_PLATFORM_META_QUEST`.
  - 6.6: depth input attachment (DX12/Vulkan), URP Settings Analyzer in Project Auditor, OpenXR Adaptive Performance, more Quest optimizations.

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.1-6.6 · Evidence: [doc]
  - Notes: The other pages are WhatsNewUnity61/62/63/64/65 under the matching version path, plus https://docs.unity3d.com/6000.4/Documentation/Manual/UpgradeGuideUnity64.html. 6.7 is Beta and excluded.

### On-tile rendering, on-tile post-processing and depth input (6.3-6.6)

- **U2-074 / U1-062** On-tile post-processing, 6.3 (XR only):
  - Requirements: Unity 6.3+, URP, integrated post-processing disabled, Vulkan. Add the renderer feature "On Tile Post Processing (Untethered XR)".
  - Supported effects: Color grading, Vignette, Tonemapping, Dithering, Film Grain.
  - Unity recommends it for Quest 2 and Quest 3.
  - Rendering off-tile with it enabled causes compilation errors. Unsupported platforms fall back.

  [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/xr-graphics-on-tile-post-processing.html (accessed 2026-09-24) · Applies to: 6.3-6.4 · Evidence: [doc]
  - Notes: The effects apply per tile before the store, so the eye buffer is written once, already graded. Developed with Meta (thread 1703007).
  - **Merged U1-062:** On-tile post-processing arrived for untethered XR in 6.3 (6000.3.0b3) and for all platforms in 6.5. Supported effects are color grading, vignette, tonemapping, dithering and film grain. Setup: turn off integrated post-processing, enable Tile-Only Mode, and add the On Tile Post Processing renderer feature. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-post-processing.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html (accessed 2026-09-24) · Applies to: 6.3+ (XR), 6.5+ (all) · Evidence: [doc] [verify on device]
    - Notes: Unity says it avoids costly round trips through system memory but gives no number. Check with the Render Graph Viewer that no texture-sampling fallback pass appears. Measure GPU ms and bandwidth (for example Snapdragon Profiler or OVR GPU metrics) against the fullscreen-blit post path.
  - Merge note: U1-062's setup step "enable Tile-Only Mode" applies to 6.5+, where Tile-Only Mode exists; see Conflict X-C10.

- **U2-075** On-tile post-processing, 6.5+:
  - Setup: disable renderer Post-processing, enable Tile-Only Mode, then add On Tile Post Processing.
  - Without Tile-Only Mode it falls back to texture sampling: visually identical, with no bandwidth saving.
  - It enables no effect by itself; add the volume components.
  - Verify the path with the Render Graph Viewer on device (look for the "F" framebuffer-input marker).

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-post-processing.html (accessed 2026-09-24) · Applies to: 6.5+ (all platforms); XR from 6.3 · Evidence: [doc]
  - Notes: The silent fallback is the trap. A project upgraded from 6.3 without Tile-Only Mode may be paying full post-processing bandwidth.

- **U2-076** Unity staff on-tile limits (thread 1703007):
  - Bloom, or any effect that samples neighboring pixels, is impossible on-tile; fake bloom by other means.
  - On-tile post-processing supports foveated rendering.
  - On-tile PP for all platforms landed in 6000.5.0a9.
  - Tile-Only validation is conservative.

  [T]
  - Source: https://discussions.unity.com/t/performant-and-energy-efficient-rendering-with-render-graph-and-on-tile-post-processing-for-untethered-xr-in-unity-6-3/1703007 (accessed 2026-09-24) · Applies to: 6.3+ · Evidence: [community]
  - Notes: DoF and other neighbor-sampling depth effects also force `_CameraDepthAttachment` out of memoryless (same post).

- **U2-077** Unity's XR page shows a correct on-tile frame in the Render Graph Viewer:
  - one blue merge bar;
  - `cameraTargetAttachment` and `cameraDepthAttachment` memoryless;
  - the on-tile PP pass reading camera color via framebuffer fetch ("F") and writing the Backbuffer color.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html (accessed 2026-09-24) · Applies to: 6.3+ · Evidence: [doc]
  - Notes: Use it as the pass/fail picture for a skill's "is my frame on-tile?" check.

- **U2-078** Tile-Only validation throws exceptions in development builds when a pass is incompatible and is stripped from release builds. Unity advises disabling it only for performance profiling in dev builds. With it off, rendering can fall off-tile silently. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html (accessed 2026-09-24) · Applies to: 6.5+ · Evidence: [doc]
  - Notes: The validation's own CPU cost in dev builds is not quantified (gap). Profile CPU with it off, and check graph correctness with it on.

- **U2-079 / U1-065** Depth input attachment (6.6):
  - Add a Render Objects feature with a Depth override and "Set As Input Attachment", at After Rendering Opaques or later.
  - In shaders use `#pragma multi_compile _ _DEPTH_AS_INPUT_ATTACHMENT _DEPTH_AS_INPUT_ATTACHMENT_MSAA` and call `FetchSceneDepth(fragCoord)` (or `FetchSceneDepth(fragCoord, sampleIndex)` for MSAA). Shader Graph has a Fetch Scene Depth node.
  - Runtime check: `SystemInfo.supportsDepthAttachmentAsInputAttachment`.
  - DX12 and Vulkan only.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/read-depth-input-attachment.html (accessed 2026-09-24) · Applies to: 6.6 · Evidence: [doc]
  - Notes: Unity's untethered XR page recommends this over Depth Texture for per-pixel depth effects (soft particles, depth fade, intersection highlights). It adds a multi_compile axis, so strip unused variants.
  - **Merged U1-065:** 6.6 lets URP read the current depth buffer as an input attachment from GPU memory on DX12 and Vulkan, avoiding a depth copy. Unity's untethered-XR guide recommends it in place of a copied depth texture. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: 6.6+ (Vulkan) · Evidence: [doc] [verify on device]

- **U2-080 / U1-066** Unity's 6.6 untethered XR checklist:
  - Vulkan with OpenXR (multiview, foveated rendering, multiview render regions)
  - Render Graph
  - Forward (not Deferred)
  - on-tile post-processing from 6.3; before 6.3, disable post-processing
  - avoid geometry shaders
  - MSAA 2x
  - depth priming off; Depth/Opaque textures off; depth input attachment when depth is needed
  - SSAO off, HDR off
  - resolution scaling
  - Meta Quest build-profile shader optimizations
  - Adaptive Performance (OpenXR, 6.6)

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: 6.6 (the 6.3 page lacks the MSAA note, depth input and 6.6 items) · Evidence: [doc]
  - Notes: The geometry shader rationale: extra primitives break the tiled flow, and some devices lack support.
  - **Merged U1-066:** Unity's untethered-XR checklist (6.6 manual) recommends Vulkan with OpenXR, Multiview, foveated rendering, multiview render regions, Render Graph and Forward. It also recommends on-tile post (turning post off on versions before 6.3), MSAA 2x, turning off depth priming (rely on LRZ), turning off the Opaque and Depth textures, no SSAO, no HDR, resolution scaling, the Quest shader optimizations and Adaptive Performance for OpenXR. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: 6.6 (items gated by version as noted) · Evidence: [doc]
    - Notes: This is the best current Unity source to reconcile against Meta's OpenXR settings page (U1-092).

### Pre-Render-Graph equivalents (URP 12/14 and 6.0-6.3 Compatibility Mode)

- **U2-081 / U1-027 / U2-024** In URP 12/14 the tile-merging mechanism is the renderer's **Native RenderPass** toggle, used with Vulkan. The URP 14 docs say to enable it on Vulkan or Metal. It merges URP's own passes into subpasses. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: URP 12/14; 6.0-6.3 in Compatibility Mode · Evidence: [doc]
  - Notes: Off by default (U2-024). On GLES it does nothing. Compatibility Mode and its custom-pass path are removed in 6.4.
  - **Merged U1-027:** Native RenderPass in URP 14 (pre-Render-Graph) is a Universal Renderer toggle. Unity advises turning it on for Vulkan, Metal and DX12 to cut render-texture copies to and from memory. It has no effect on OpenGL ES. [T]
    - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: 2022.3 (URP 14) · Evidence: [doc]
    - Notes: The URP 12 (2021.3) renderer page fetched this pass has no Native RenderPass entry, so 2021.3 behaviour is unverified. 6000.0.0b11 fixed a bug where Native RenderPass was not disabled on GLES when Render Graph was on.
  - **Merged U2-024:** **Native RenderPass** (the pre-Render-Graph toggle on the renderer):
    - It defaults to false in 2021.3, 2022.3 and 6000.0-6000.3.
    - The URP 12 docs recommend it for Vulkan, Metal and DX12. It has no effect on GLES.
    - In 6000.0-6000.3 the Inspector shows it only in Compatibility Mode, and it is gone from 6000.5 source.

    [T]
    - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: URP 12/14; URP 17.0-17.3 Compatibility Mode · Evidence: [doc]
    - Notes: Under Render Graph, native render passes are always on (`RenderGraph.nativeRenderPassesEnabled` defaults to true in 6000.3 source), so the toggle doesn't matter there. The 6.6 renderer page still describes it (Conflict U2-C4). On URP 14, `useRenderPassEnabled` is forced false for non-Game cameras, so the Scene view differs from the headset (https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderer.cs).

- **U2-082** In URP 12/14, `ScriptableRenderPass.ConfigureInputAttachments`, `useNativeRenderPass` and `overrideCameraTarget` are `internal`. Custom passes cannot declare input attachments without a modified URP package, which is why Meta shipped fork branches (U2-084). [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/Passes/ScriptableRenderPass.cs (accessed 2026-09-24) · Applies to: URP 12/14 · Evidence: [doc]
  - Notes: The public URP 14 API offers:
    - `ConfigureColorStoreAction(RenderBufferStoreAction, uint attachmentIndex = 0)`
    - `ConfigureColorStoreActions(RenderBufferStoreAction[])`
    - `ConfigureDepthStoreAction`
    - `ConfigureInput`, `ConfigureTarget(RTHandle...)`, `ConfigureClear`

    Unity says never call `cmd.SetRenderTarget` (https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/api/UnityEngine.Rendering.Universal.ScriptableRenderPass.html).

- **U2-083** The URP 14 full-screen blit recipe:
  - Use `RTHandle`.
  - Take `renderer.cameraColorTargetHandle` in `SetupRenderPasses`, then call `ConfigureTarget` in `OnCameraSetup`.
  - Blit with `Blitter.BlitCameraTexture(cmd, src, dst, mat, 0)` and a shader built on `Blit.hlsl` (`Vert`, `input.texcoord`).
  - Test SPI with MockHMD.

  [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/renderer-features/how-to-fullscreen-blit.html (accessed 2026-09-24) · Applies to: URP 14 · Evidence: [doc]
  - Notes: Declare `ConfigureInput(ScriptableRenderPassInput.Color)` so Intermediate Texture = Auto can still work.

- **U2-084** Meta's Vulkan subpass support by Unity version:
  - Requires 2022.3.42f1+ or 6000.0.23f1+.
  - From 6000.3, URP supports Vulkan subpasses by default through Render Graph (Compatibility Mode off).
  - Before that, use Meta's Oculus-VR/Unity-Graphics branches:
    - `6000.0/17.0.4-subpass` for 6000.0.40 to 6000.2.x;
    - `17.0.3-subpass` for 6000.0.23-39;
    - `2022.3/staging-subpass` for 2022 LTS, with Native RenderPass checked.

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ (accessed 2026-09-24; page updated Jun 16 2026) · Applies to: 2022.3, 6000.0-6000.2 via fork; 6000.3+ built in · Evidence: [doc]
  - Notes: Before 6000.3, the fork branches are incompatible with Dynamic Resolution and Application SpaceWarp. That is a real trade-off for 72 Hz titles relying on AppSW.

- **U2-085** Meta's subpass limits:
  - All subpasses need the same framebuffer dimensions and can read only the current pixel.
  - Tile-compatible post effects (11): Channel Mixer, Color Adjustments, Color Curves, Color Lookup, Film Grain, Lift Gamma Gain, Shadows Midtones Highlights, Split Toning, Tonemapping, Vignette, White Balance.
  - Incompatible: Bloom, Chromatic Aberration, Depth of Field, Lens Distortion, Motion Blur, Panini Projection.

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ (accessed 2026-09-24) · Applies to: Meta subpass branches and 6000.3+ · Evidence: [doc]
  - Notes: Unity's on-tile PP list is shorter (5 effects; Conflict U2-C5). Many of Meta's 11 are folded into Unity's LUT-based color grading.

- **U2-086** Meta's depth-input setup for the fork:
  1. Add a "DepthInputSubpass" layer.
  2. Uncheck Depth and Opaque textures, whose copies break merging.
  3. Set Intermediate Texture to Auto.
  4. Add a Render Objects feature at AfterRenderingOpaques/Transparents with Depth and Depth Input overrides and Write Depth off.
  5. In Shader Graph, add keyword `_DEPTH_INPUT_ATTACHMENT` (MultiCompile). In HLSL, use `FRAMEBUFFER_INPUT_FLOAT_MS(depth_input)` and `LOAD_FRAMEBUFFER_INPUT_MS(depth_input, 0, float2(0,0))`.

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ (accessed 2026-09-24) · Applies to: Meta subpass branches, 6000.3 · Evidence: [doc]
  - Notes: The 6.6 Unity-native equivalent uses different keywords (`_DEPTH_AS_INPUT_ATTACHMENT`, U2-079). Shaders written for the Meta fork need porting when moving to 6.6.

- **U2-087** Meta notes that URP's `OnRenderObjectCallbackPass` prevents subpass merging; it is commented out in the fork. Known issues:
  - OVRManager "Use Recommended MSAA Level" causes a first-frame glitch.
  - The Unity 6 editor with Vulkan, OpenXR and MSAA renders black.

  Debug with the RenderDoc Meta Fork (look for `vkCmdNextSubpass`) or the Render Graph Viewer with Meta XR Simulator on Vulkan. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ (accessed 2026-09-24) · Applies to: fork branches · Evidence: [doc]
  - Notes: Any script using `OnRenderObject` can add that callback pass. Grep projects for it [verify on device].

- **U2-088** GLES specifics:
  - Native RenderPass has no effect on GLES.
  - URP does not bind MSAA depth as a texture on GLES; Unity judged the fix costlier than a depth prepass (fogbugz 1339401 comment).
  - Depth priming is turned off where GLES with MSAA can't copy depth.
  - Framebuffer-fetch input attachments fall back to copies outside Vulkan/Metal.

  [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRendererRenderGraph.cs (accessed 2026-09-24) · Applies to: GLES builds, all versions · Evidence: [doc]
  - Notes: A second reason (with U2-034) to treat Vulkan as mandatory on Quest. Meta's advanced-GPU page calls Vulkan the required API for Quest development.

## 5. Draw calls and batching

### Triage: submission, shading or first-use compilation

- **U3-001 / U5-083** Split the frame before touching batching. Meta's workflow:
  1. Disable the rendering camera. If frame time barely moves, the app is CPU-bound.
  2. Set eyeTextureResolutionScale to about 0.01. If GPU time doesn't move, the app is vertex/geometry-bound; if it drops, it is fragment-bound.

  Batching work pays off only in the CPU/render-thread-bound branch. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ (accessed 2026-09-24) · Applies to: all Quest, all Unity versions · Evidence: [doc]
  - Notes: The page was updated Dec 9, 2024. It notes that turning the camera off also removes culling, so culling cost shows up on the "vertex-bound" side of this test.
  - **Merged U5-083:** Meta's quick bound tests:
    - Disable all cameras. If frame time barely changes, the app is CPU-bound.
    - Lower `eyeTextureResolutionScale`. If frame time drops, the app is GPU fill-bound.
    - Lock CPU/GPU levels while profiling.
    - Disable Multithreaded Rendering while debugging, so the full render cost is visible.

    [T]
    - Source: https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ (accessed 2026-09-24); https://developers.meta.com/horizon/documentation/unity/unity-perf/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
    - Notes: Meta's page states 72 FPS as the minimum.

- **U3-002** Unity frames draw-call optimization as a fix for a CPU-bound frame. It gives three checks: SetPass calls in the Rendering Statistics window, the Profiler's Rendering module, and the draw list in the Frame Debugger. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html (accessed 2026-09-24) · Applies to: 6.x (the same tools exist in 2021.3/2022.3) · Evidence: [doc]
  - Notes: SetPass calls (state changes) is the metric the SRP Batcher moves. Raw draw count is the metric instancing, BRG and GRD move. Track both before and after a change.

- **U3-003 / U4-076** Meta's per-device guidance:

  | Metric | Quest 3 | Quest 2 |
  | --- | --- | --- |
  | Draw calls per frame | <200 | <100 |
  | Triangles per frame | <1.5M | <750K |

  Meta calls Quest 2 "more draw-call sensitive" and rates the Quest 3 GPU at about 2.5x Quest 2. [T]
  - Source: https://developers.meta.com/horizon/resources/device-optimization-comparison/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 · Evidence: [doc] [verify on device]
  - Notes: Updated May 11, 2026. The page does not say whether a multiview draw counts once or twice (one API draw covers both eyes; see U3-040). No Quest 3S number was found; it has the same SoC as Quest 3, so assume the Quest 3 CPU budget. Treat these as starting budgets and measure render-thread ms.
  - **Merged U4-076:** Meta's comparison page gives these per-frame budgets: [T]
    - Quest 3: under 200 draw calls and under 1.5M triangles.
    - Quest 2: under 100 draw calls and under 750K triangles.

    The legacy Android page gave a conservative 50,000 static triangles per eye per view and favored texture detail over geometry.
    - Source: https://developers.meta.com/horizon/resources/device-optimization-comparison/ (2026-05-11); https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ (legacy) (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
    - Notes: The legacy triangle figure is possibly stale and is superseded by the 2026 page. Geometry budgets belong mainly to the draw-call and geometry topic (see Leads).
  - Merge note: the Meta unity-perf page cited in U5's leads gives different triangle ranges; see Conflict X-C4.

- **U3-004** Meta measured relative draw-call CPU cost:
  - changing the material (same shader): +64% per-draw time
  - changing the shader: +175%
  - redrawing the same object: about 25% of the cost of drawing a different one
  - texture size, compression and filtering: negligible CPU cost

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (accessed 2026-09-24) · Applies to: measured on Quest 1, Unity 2018.1.6f1, single-pass stereo, multithreaded rendering off, 500 quads, ATW off · Evidence: [measured]
  - Notes: Possibly stale: 2018, pre-SRP Batcher, Quest 1 on GLES. Keep only the ordering (shader/variant switch > material switch > same-state redraw), which matches the SRP Batcher design (U3-009). To re-measure: N quads with identical vs distinct materials vs distinct shaders on Quest 2, comparing render-thread time in the Profiler.

- **U3-005** For per-draw GPU cost, use a RenderDoc Meta Fork draw-call trace. Per draw, it reports:
  - Clocks
  - % Vertex Fetch Stall and % Texture Fetch Stall
  - L1/L2 misses
  - % Shaders Busy
  - Fragment ALU Instructions (Full) and (Half)
  - EFU (transcendental) counts, ALU/Fragment, and % Shader ALU Capacity Utilized

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) · Applies to: all Quest, GLES and Vulkan · Evidence: [doc]
  - Notes: This answers "is this material ALU-bound or fetch-bound?". Pair it with GPU ms from OVR Metrics Tool.

- **U3-006** On Vulkan, RenderDoc Meta Fork reads per-pipeline static shader stats through VK_KHR_pipeline_executable_properties (Pipeline State, then View). It shows:
  - instruction counts: all, 32-bit ALU, 16-bit ALU, complex/EFU, texture read, flow control, barrier, short/long sync
  - full, half and overall register footprints
  - scratch memory
  - shader processor utilization

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ (accessed 2026-09-24) · Applies to: Vulkan builds only · Evidence: [doc]
  - Notes: Updated Dec 1, 2024. The page's own thresholds:
    - keep each group of coalesced texture fetches under 15
    - any scratch memory use means poor performance
    - group EFU ops moderately
    - high register use lowers wave count and latency hiding

    This is the fastest way to diff two variants (for example half vs float) without a device A/B.

- **U3-007** Meta's rule of thumb is 25–50 shader instructions as a "sweet spot". It also recommends a small set of uber shaders, to maximize batching and minimize SetPass/pipeline changes. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-2/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Spot-check (gap-fill round 2): confirmed. The page says 25-50 instructions is "generally a sweet spot" and recommends "a limited set of uber shaders". It still shows no date.
  - Notes: A vendor heuristic with no measurement behind it; no update date was extractable. Weight it by pixel coverage. Uber shaders trade fewer shaders/PSOs for more keywords and variants; see section 9.

- **U3-008** Read the Frame Debugger's batch-break reason instead of guessing. In Meta's example, 12 cubes landed in 4 instanced draws because they sat in different reflection probes; sharing one probe collapsed them into one draw. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-1/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Per-object inputs split batches in every submission path: reflection probe, lightmap index, light probes, and in GRD also sorting order and MPBs.

### SRP Batcher

- **U3-009 / U1-012 / U2-016** The SRP Batcher cuts render-state changes, not draw count:
  - it batches by shader variant
  - material constant buffers stay resident in GPU memory
  - only per-object data is written into a large per-draw buffer

  So many materials that share one variant are cheap, and many variants are not. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher.html (accessed 2026-09-24) · Applies to: URP 12+ (every version in scope) · Evidence: [doc]
  - Notes: Keyword and variant count is the lever that decides batch size (section 9).
  - **Merged U1-012:** The SRP Batcher is available across the whole range (2021.3+). It is a prerequisite for BRG and the GPU Resident Drawer in every version checked. It stays the baseline CPU draw-submission path on both GLES and Vulkan. [T]
    - Source: https://docs.unity3d.com/2022.3/Documentation/Manual/batch-renderer-group.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
    - Notes: The per-platform SRP Batcher support list was not re-verified this pass.
  - **Merged U2-016:** Leave **SRP Batcher** on (the default). Unity's performance page lists it under GPU/CPU settings to keep enabled. Dynamic batching defaults off. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
    - Notes: In 6.x the SRP Batcher toggle is an advanced property on the asset.

- **U3-010** SRP Batcher compatibility requires all of the following:
  - a MeshRenderer or SkinnedMeshRenderer (particles don't qualify)
  - built-in engine properties declared in a single `UnityPerDraw` CBUFFER
  - every material property in a single `UnityPerMaterial` CBUFFER
  - no MaterialPropertyBlock on the renderer

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Materials.html (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc]
  - Notes: The shader Inspector shows compatible/not compatible. Hand-written HLSL commonly breaks compatibility by leaving one Properties entry (for example a `_ST` vector) outside `UnityPerMaterial`.

- **U3-011** To diagnose in the Frame Debugger:
  - SRP-batched work appears as `RenderLoopNewBatcher.Draw` under the camera's opaque/transparent passes.
  - Each break shows its reason (for example "Nodes have different shaders").

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Profile.html (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc]

- **U3-012** Unity warns that if a project's assets and shaders aren't optimized for the SRP Batcher, low-performance devices may run faster with it off. The toggle is URP Asset > Rendering > SRP Batcher (an advanced property). [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Enable.html (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc] [verify on device]
  - Notes: No published Quest on/off number was found. To measure: toggle `GraphicsSettings.useScriptableRenderPipelineBatching` at runtime in a fixed camera path on Quest 2, and compare render-thread ms (Profiler) and GPU ms (OVR Metrics Tool).

- **U3-013** The SRP Batcher runs multithreaded only on DX12, Vulkan and consoles, and only with Graphics Jobs on. On GLES it is single-threaded. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html (accessed 2026-09-24) · Applies to: 6.x · Evidence: [doc]
  - Notes: Graphics Jobs modes are Native, Legacy and Split; Split is Vulkan-only (https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html). This is one more reason to leave GLES; thread tuning belongs to the CPU topic.

- **U3-014** Unity's launch numbers for the SRP Batcher:
  - 1.2x–4x faster CPU rendering, depending on the scene
  - x1.47 on an HDRP scene on PS4
  - x1.23 on the FPS Sample on PC DX11

  Target: the SRPBatcherProfiler "standard code path" timing should be near zero. [T]
  - Source: https://unity.com/blog/engine-platform/srp-batcher-speed-up-your-rendering (accessed 2026-09-24; published Feb 28, 2019) · Applies to: 2019.x SRPs on PC/PS4, not Quest · Evidence: [measured]
  - Notes: Possibly stale and not from Quest. No published Quest number was found (see U3-012 for how to measure).

- **U3-015** In URP, MaterialPropertyBlocks break both SRP Batcher and GPU Resident Drawer compatibility. For per-object color and similar properties, Unity recommends Material Variants or separate materials instead of MPBs. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html (accessed 2026-09-24) · Applies to: URP, all versions in scope · Evidence: [doc]

- **U3-016** URP GPU-instances a custom shader only when the SRP Batcher is off or the shader is SRP-Batcher-incompatible. To force instancing for one shader, make it deliberately incompatible, either with a property outside `UnityPerMaterial` or with an MPB. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/GPUInstancing.html and https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Incompatible.html (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc]
  - Notes: Only worth it when many copies of one mesh and material make the draw count, not SetPass, the bottleneck. On Unity 6 with Vulkan, GRD does this automatically (section 4).

### Static batching, GPU instancing, dynamic batching: precedence

- **U3-017** Unity 6.6's URP recommendations:

  | Feature | URP recommendation |
  | --- | --- |
  | SRP Batcher | Enable |
  | GPU Resident Drawer | Enable |
  | BRG API | Only for advanced cases |
  | Per-material GPU Instancing checkbox | Disable (it adds shader variants) |
  | Static batching | Disable (not compatible with BRG or GRD) |

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html (accessed 2026-09-24) · Applies to: 6.x · Evidence: [doc]
  - Notes: These are general recommendations, not XR-specific. On GLES (no GRD) and on 2021.3/2022.3, static batching is still the main tool for static props. See U3-C1.

- **U3-018** When every method is enabled, Unity applies them in this order:
  1. Static meshes: static batching.
  2. Dynamic meshes with a compatible shader: SRP Batcher plus GRD/BRG.
  3. Remaining compatible meshes: GPU instancing.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html (accessed 2026-09-24) · Applies to: 6.x · Evidence: [doc]
  - Notes: Static-batched renderers therefore never reach GRD. When adopting GRD, turn off Player > Static Batching (U3-031).

- **U3-019** Static batching combines meshes into world-space vertex and index buffers:
  - Up to 64,000 vertices per buffer; Unity starts another batch past that.
  - MeshRenderer only.
  - Combined meshes need the same vertex attributes.
  - Every instance's geometry is duplicated, which costs memory (repeated trees, for example).

  Build-time static batching has no runtime CPU cost. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/DrawCallBatching.html and https://docs.unity3d.com/2022.3/Documentation/Manual/static-batching.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Runtime `StaticBatchingUtility.Combine` needs Read/Write meshes. `Mesh.UploadMeshData(true)` drops the CPU copy afterwards.

- **U3-020** Culling splits static batches: when some sub-meshes are culled, the batch is submitted as several draws. The draw count, and with it render-thread time, therefore varies with head direction. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/static-batching-enable.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: To check for p95 spikes, look at the draw-count spread across a head-turn capture, not just the average.

- **U3-021** Meta's Quest guidance: Quest 2 is more draw-call sensitive, so batch geometry and use instanced rendering where possible. [T]
  - Source: https://developers.meta.com/horizon/resources/device-optimization-comparison/ (accessed 2026-09-24) · Applies to: Quest 2 · Evidence: [doc]
  - Notes: This contradicts U3-017's "disable static batching" only when GRD/BRG is in use; see U3-C1.

- **U3-022** Keep merged batches spatially compact. A few long, thin outliers inflate the bounds, so frustum and occlusion culling keep the whole batch alive and the GPU transforms geometry that contributes no pixels. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-2/ (accessed 2026-09-24) · Applies to: all versions (static batching, manual merging, HLODs) · Evidence: [doc]

- **U3-023** GPU instancing reduces CPU submission only. Every instance's vertices are still transformed, so it does not lower GPU vertex cost. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-1/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: For dense instanced foliage, use LODs and GPU occlusion, not just instancing.

- **U3-024** Unity 6.x Graphics Settings has two stripping controls that affect submission paths:
  - **Instancing Variants:** Strip Unused (default), Strip All, Keep All.
  - **BatchRendererGroup Variants:** "Strip if Entities Graphics Package is not installed" (default), Strip All, Keep All. GRD requires Keep All.

  More kept variants means more programs to load and more PSOs to warm. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html (accessed 2026-09-24) · Applies to: 6.x (Instancing Variants also exists in 2021.3/2022.3) · Evidence: [doc]

- **U3-025** URP's legacy instanced-array size is 250 on mobile Vulkan and 500 elsewhere, unless `UNITY_MAX_INSTANCE_COUNT` (`#pragma instancing_options maxcount:N`) overrides it. This bounds the instances per classic instanced draw. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/UnityInstancing.hlsl (accessed 2026-09-24) · Applies to: classic GPU instancing (not BRG/DOTS instancing) · Evidence: [doc] [verify on device]
  - Notes: The actual count per draw also depends on per-instance data size versus the constant buffer limit. Check the instance count per draw in the Frame Debugger.
  - Spot-check (gap-fill round 1): re-read master `UnityInstancing.hlsl`. The 250 value applies when `SHADER_API_VULKAN && SHADER_API_MOBILE` (also Switch, Switch 2 and WebGPU). `UNITY_FORCE_MAX_INSTANCE_COUNT` and `UNITY_INSTANCING_SUPPORT_FLEXIBLE_ARRAY_SIZE` (array size 2) take priority over `UNITY_MAX_INSTANCE_COUNT`. Confirmed.

- **UNITY-GF1-001** Dynamic batching on 6.0-6.5 (before the 6.6 obsoletion in U1-022) is documented as "no longer recommended" for most uses, because its CPU overhead can exceed the draw call it saves. It is recommended only on lower-end devices. The limits are unchanged from older versions: [T]
  - At most 300 vertices and 900 vertex attributes per mesh.
  - Only the first pass of a multi-pass shader is batched.
  - Lightmapped objects must share the lightmap texture and UVs.
  - Negative and positive scale do not batch together.

  Dynamic batching transforms vertices on the CPU (main/render thread), so enabling it shifts cost from draw submission to vertex transformation.
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/DrawCallBatching.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/DrawCallBatching.html (accessed 2026-09-24) · Applies to: 6.0-6.5 (and older URP, same limits) · Evidence: [doc] [verify on device]
  - Notes: Serves throughput (CPU). No Quest measurement exists. The 6.6 DrawCallBatching page covers static batching only, which is consistent with U1-022. Closes the "Dynamic batching in URP 6.x precedence" gap in Known unknowns.

- **UNITY-GF1-002** Dynamic batching has the lowest precedence on 6.0. When every method is enabled, Unity applies them in this order: static batching, SRP Batcher with GRD/BRG, GPU instancing, and only then dynamic batching for the remaining meshes. The URP Asset's Advanced Properties add two rules: [T]
  - The SRP Batcher takes precedence over dynamic batching whenever the shader is SRP Batcher compatible.
  - Disable Dynamic Batching if the target hardware supports GPU instancing. It can be changed at run time.
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/optimizing-draw-calls-choose-method.html ; https://docs.unity3d.com/6000.0/Documentation/Manual/urp/universalrp-asset.html (accessed 2026-09-24) · Applies to: 6.0-6.5, URP 17.0-17.5 · Evidence: [doc]
  - Notes: Every Quest GPU supports instancing, so the documented guidance for Quest is Dynamic Batching off (matching U3-017 and the 6.6 obsoletion). Unity's 6.0 URP asset page also says projects whose shaders are not SRP Batcher optimized can run faster on low-end devices with the SRP Batcher off. This duplicates U3-012; see U3-012 for its measurement method.

### BatchRendererGroup, DOTS instancing, Entities Graphics

- **U3-026 / U1-013 / U1-014 / U3-028 / U3-029** BRG setup requirements:
  - SRP Batcher on
  - Graphics > BatchRendererGroup Variants = Keep All
  - in URP, disable "Strip Unused Variants", or DOTS instancing variants get stripped
  - "Allow 'unsafe' Code" on

  BRG supports Android Vulkan and GLES 3.x. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/batch-renderer-group-getting-started.html (accessed 2026-09-24) · Applies to: 2022.1+ (BRG API), 6.x docs · Evidence: [doc]
  - **Merged U1-013:** BatchRendererGroup (BRG) is experimental in 2021.3 with an older API that Unity said would be replaced in 2022.1. In 2022.3 the supported platforms include Android on Vulkan and on OpenGL ES 3.x. It requires the SRP Batcher, BRG variants set to Keep All, and unsafe code. [T]
    - Source: https://docs.unity3d.com/2022.3/Documentation/Manual/batch-renderer-group.html (accessed 2026-09-24) · Applies to: 2021.3 (experimental), 2022.3+ · Evidence: [doc]
    - Notes: Custom BRG code written against 2021.3 should be treated as a rewrite on upgrade.
  - **Merged U1-014:** BRG has two buffer modes. On GLES it uses a constant-buffer (UBO) window: `BatchBufferTarget.ConstantBuffer`, with `GetConstantBufferMaxWindowSize` and `GetConstantBufferOffsetAlignment` limits. On Vulkan it uses raw SSBO (`RawBuffer`). These APIs are documented from 2022.3; the 2021.3 page is a 404. [T][C]
    - Source: https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Rendering.BatchRendererGroup.BufferTarget.html (accessed 2026-09-24) · Applies to: 2022.3+ · Evidence: [doc]
    - Notes: Quest GLES builds run BRG through the UBO window path. Instance data per draw is bounded by the window size. No published Quest number exists for the UBO-mode vs SSBO-mode cost. To measure, A/B the same BRG scene with GLES vs Vulkan and read GPU/CPU frame time from OVR Metrics or RenderDoc. [verify on device]
  - **Merged U3-028:** DOTS instancing data comes from a UBO on GLES/GL (`UNITY_DOTS_INSTANCING_UNIFORM_BUFFER`) and from an SSBO elsewhere, including Vulkan. On GL/GLES, `DOTS_INSTANCING_ON` requires `#pragma target 3.5` or higher. [T]
    - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/UnityInstancing.hlsl (accessed 2026-09-24) · Applies to: 2022.3, 6.x · Evidence: [doc]
    - Notes: On Quest with Vulkan, windowing constraints (U3-029/030) don't apply.
  - **Merged U3-029:** `BatchRendererGroup.BufferTarget` reports the buffer model at runtime: RawBuffer (SSBO) or ConstantBuffer (UBO). In ConstantBuffer mode:
    - `AddBatch` needs an offset aligned to `GetConstantBufferOffsetAlignment()`
    - the window size must be ≤ `GetConstantBufferMaxWindowSize()`

    In RawBuffer mode, both offset and window size must be 0. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.BatchRendererGroup.AddBatch.html (accessed 2026-09-24) · Applies to: 2022.3, 6.x · Evidence: [doc] [verify on device]
    - Notes: No published Adreno GLES window size was found. Log the two getters on Quest 2 and Quest 3 under GLES if you still ship GLES.
  - Merge note: U1-013/U1-014 give the version history and buffer modes; U3-026/028/029 give setup and runtime detection. Same subject, combined here.

- **U3-027** BRG does no culling. Your `OnPerformCulling` callback supplies the visible instances. Unity splits one draw command into several when the graphics API's limit is lower than `visibleCount`. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/batch-renderer-group-how.html (accessed 2026-09-24) · Applies to: 2022.3, 6.x · Evidence: [doc]
  - Notes: The culling job is your render-thread cost. Burst-compile it and time it separately in the Profiler.

- **U3-030** Unity's BRG sample, measured on a budget phone:
  - most GLES 3.0 devices report 0 vertex-shader storage blocks, which forces the UBO path
  - the window is typically 16 KiB, with 4–256 B alignment
  - at 112 B per instance, a window holds 146 instances
  - 3,200 instances took 22 draws (22 BatchIDs) from a 350 KiB raw buffer
  - 16,384 debris items needed 113 windows
  - result: a steady 60 fps

  [T]
  - Source: https://unity.com/blog/engine-platform/batchrenderergroup-sample-high-frame-rate-on-budget-devices (accessed 2026-09-24; published Oct 3, 2023) · Applies to: Samsung Galaxy A51 (Mali-G72 MP3), GLES 3.0, Unity 2022.3 · Evidence: [measured]
  - Notes: Mali, not Adreno. Use only the arithmetic: per-instance bytes set the draws per window. Not a Quest number.

- **U3-031** Entities Graphics requirements: URP Forward+ only; Android on Vulkan or GLES 3.1+; XR supported. In package 6.5.0, GLES support is deprecated and slated for removal. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.entities.graphics@6.5/manual/requirements-and-compatibility.html (accessed 2026-09-24) · Applies to: Entities Graphics 1.x / 6.5 · Evidence: [doc]
  - Notes: For new Quest ECS work, plan on Vulkan only.

### GPU Resident Drawer and GPU occlusion culling

- **U3-032 / U1-016 / U1-017 / U3-033 / U4-044** GRD works only when all of these hold:
  - the renderer is Forward+ or Deferred+ (6.1+)
  - the graphics API supports compute and is not OpenGL ES (so on Quest, Vulkan only)
  - Enlighten realtime GI is off

  Each MeshRenderer must also:
  - use no Proxy Volume or Anchor Override
  - have no MPB
  - keep the default sorting layer and order
  - use BRG-compatible materials, 128 materials at most
  - have no TextMesh and no MonoBehaviour implementing `OnWillRenderObject`, `OnBecameVisible` or `OnBecameInvisible`

  Anything else silently falls back to the normal path. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: Unity's XR page recommends avoiding Deferred on tile GPUs. Forward+ adds a clustered light loop (`_CLUSTER_LIGHT_LOOP`). That GPU cost is part of GRD's price on Quest.
  - **Merged U1-016:** The GPU Resident Drawer (GRD) arrived in 6.0 (URP 17). It draws GameObjects through BRG with GPU instancing. On 6.0 and 6.3 it requires Forward+, a compute-capable API other than OpenGL ES, and Mesh Renderers. On 6.6 it requires Forward+ or Deferred+. On Quest, that means Vulkan only. [T]
    - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/urp/gpu-resident-drawer.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
    - Notes: Setup: set BatchRendererGroup Variants to Keep All, keep the SRP Batcher on, and set GPU Resident Drawer to Instanced Drawing.
  - **Merged U1-017:** GRD restrictions listed for 6.6: no MaterialPropertyBlocks, and objects must keep the default sorting layer and order. It supports up to 128 materials. OnWillRenderObject, OnBecameVisible and OnBecameInvisible are not called. It requires Enlighten realtime GI to be off, and it does not support animated LOD cross-fade. Objects that break a rule silently fall back to the normal path. [C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html (accessed 2026-09-24) · Applies to: 6.6 (most apply to 6.0+) · Evidence: [doc]
    - Notes: Content built around MaterialPropertyBlocks, which is common in 2021/2022 Quest projects, gains nothing from GRD until it is refactored.
  - **Merged U3-033:** To enable GRD:
    1. Graphics > Shader Stripping > BatchRendererGroup Variants = Keep All.
    2. SRP Batcher on.
    3. URP Asset > GPU Resident Drawer = Instanced Drawing.
    4. Renderer path = Forward+.

    Consequences:
    - Builds get longer, because all BRG variants are compiled.
    - Animated LOD cross-fade is unsupported; it falls back to static distance cross-fade.
    - `Light.shadowMatrixOverride` is ignored for caster culling.
    - The Disallow GPU Driven Rendering component opts an object out.

    [T][C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html and https://docs.unity3d.com/6000.6/Documentation/Manual/urp/make-object-compatible-gpu-rendering.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
    - Notes: The extra BRG variants add to the PSO warmup set (section 10).
  - **Merged U4-044:** GPU Resident Drawer requires Forward+ and compute support, which excludes GLES. Its docs recommend enabling Fixed Lightmap Size and disabling Use Mipmap Limits in Lightmapping Settings, so that lightmapped objects can batch. [T]
    - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/gpu-resident-drawer.html (accessed 2026-09-24) · Applies to: 6000.0+ · Evidence: [doc] [verify on device]
    - Notes: Whether GPU Resident Drawer pays off on Quest belongs to the batching topic (see Leads). Here the point is that it forces lightmap settings that cost memory.
  - Merge note: U4-044 (6000.3 page) lists Forward+ only; U1-016 and U3-032 add Deferred+ for 6.1+/6.6; see Conflict X-C9.

- **U3-034 / U1-018** Unity: GRD improves CPU time but slightly increases GPU work, and lower-end mobile and VR feel it more. A GPU-bound app can get slower overall. Unity says to watch both vertex and fragment stages. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc] [verify on device]
  - Notes: Most Quest apps are GPU-bound, so A/B on Quest 2 before committing. No published Quest GPU-cost number was found. To measure: GPU ms (OVR Metrics Tool) with GRD off vs Instanced Drawing, same camera path, fixed CPU/GPU levels.
  - **Merged U1-018:** Unity's GRD performance page warns that GRD adds a small GPU cost, and more on lower-end mobile and VR. GPU-bound apps can get slower, and static batching should be disabled when GRD is on. Most Quest titles are GPU-bound, so treat GRD as a CPU-side fix only. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc] [verify on device]
    - Notes: No published number found for Quest. To measure, A/B GRD off vs Instanced Drawing on the same scene. Record CPU main/render-thread ms and GPU ms with OVR Metrics Tool or Unity Profiler plus FrameTimingManager (OpenXR GPU times from 6.6).

- **U3-035** Unity's GRD performance checklist:
  - disable Player > Static Batching
  - enable Lighting > Fixed Lightmap Size
  - disable Use Mipmap Limits

  To verify, look for draws named "Hybrid Batch Group" in the Frame Debugger and for lower SetPass calls and CPU time in Rendering Statistics. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]

- **U3-036** The same GRD page suggests Depth Priming Mode Auto/Forced to curb overdraw from merged instanced draws, and scopes that advice to non-tiled desktop/console GPUs. The XR page says to disable depth priming on XR tile GPUs (see U3-C2). [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html and https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]

- **U3-037 / U1-019 / U3-038** How GPU occlusion culling works:
  - It requires GRD and is enabled with "GPU Occlusion" on the Universal Renderer.
  - It tests bounding spheres against a downsampled depth pyramid, using depth from the current and previous frames.
  - Thin or elongated objects occlude poorly, because their spheres are much bigger than the mesh.
  - Unity warns that total time can rise when a scene has little occlusion.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-culling.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc] [verify on device]
  - Notes: It builds and reads depth mips, which costs GPU time and bandwidth on a tile GPU. No published Quest cost was found. To measure: GPU ms with occlusion on vs off in an open scene and in an interior scene.
  - **Merged U1-019:** GPU occlusion culling arrived in 6.0 (6000.0.0b11) and requires GRD. 6000.0.0b12 added support for single-pass XR in URP. It uses a depth pyramid built from current- and previous-frame depth. Unity warns it can cost more than it saves when a scene has little occlusion. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-culling.html ; https://unity.com/releases/editor/whats-new/6000.0.0b12 (accessed 2026-09-24) · Applies to: 6.0+ (Vulkan) · Evidence: [doc] [verify on device]
    - Notes: No Quest number published. Building the depth pyramid is extra GPU work on a tiler. Measure it as a separate pass in RenderDoc or the Render Graph Viewer.
  - **Merged U3-038:** Unity 6000.0.0b12 added GPU occlusion culling for single-pass XR in URP and HDRP. Google's Android XR guidance adds that GPU occlusion needs Render Graph, meaning Compatibility Mode off. [T]
    - Source: https://unity.com/releases/editor/whats-new/6000.0.0 (6000.0.0b12 notes, accessed 2026-09-24); https://developer.android.com/develop/xr/unity/performance/gpu-rendering (updated 2026-05-19, accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
    - Notes: Google's page targets Android XR headsets, not Quest. The Render Graph requirement is engine-side, so it applies on Quest too.

- **U3-039** A forum measurement on PC:

  | Unity 6, PC, Nov 2024 | Draws | CPU | GPU |
  | --- | --- | --- | --- |
  | GRD on | 1,502 | 6.1 ms | 5–6 ms |
  | GRD off | 1,788 | 5.8 ms | 4–5 ms |

  Another user reported 150 → 120 fps with GRD on. Unity staff pointed to the extra visibility buffer GRD maintains. [T]
  - Source: https://discussions.unity.com/t/resident-drawer-performance/1554861 (accessed 2026-09-24) · Applies to: 6.0, PC · Evidence: [community]
  - Notes: Not Quest. It does show that GRD can be a net loss when a scene doesn't have many instanceable repeats.

- **U3-098** Google's Android XR blog reports that GRD cut 200 trees to 5–10 draw calls. [T]
  - Source: https://android-developers.googleblog.com/2025/10/optimizing-performance-for-android-xr.html (accessed 2026-09-24; Oct 23, 2025) · Applies to: Unity 6 on Android XR hardware, not Quest · Evidence: [measured]
  - Notes: Best case: identical meshes and materials. Not transferable as a ms number.

### Stereo submission: multiview, single-pass instanced, Multiview Render Regions

- **U3-040** Meta on multiview:
  - The render thread issues half the draw calls, because each draw hits both eye buffers.
  - The GPU keeps cache coherence, because an object's data is loaded once for both eyes.
  - Every Quest supports multiview on both GLES and Vulkan.
  - Multiview is the default with the OpenXR Meta Quest feature group.

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/enable-multiview/ (accessed 2026-09-24) · Applies to: all Quest; Oculus XR and OpenXR plug-ins · Evidence: [doc]
  - Notes: Updated Nov 12, 2025.

- **U3-041** Meta's OpenXR settings reference recommends Multi-View and says Multi-Pass takes roughly double the CPU time to process draw calls. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (accessed 2026-09-24) · Applies to: OpenXR plug-in · Evidence: [doc]
  - Notes: Updated May 11, 2026. The page keeps Multi-Pass only for legacy shaders that lack stereo support.

- **U3-042** Unity treats Multiview as a variant of single-pass instanced that replaces it where the device supports it; Android devices with the Multiview extension, including Quest, are supported. If single-pass isn't supported, rendering silently falls back to multi-pass. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassStereoRendering.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: A silent fallback doubles draws and render-thread time. Verify in RenderDoc that the base pass issues one draw per object, not one per eye.

- **U3-043** URP's XR pass chooses the stereo path at runtime:
  - If `SystemInfo.supportsMultiview` is true, it enables `STEREO_MULTIVIEW_ON` and does not touch instance counts.
  - Otherwise it enables `STEREO_INSTANCING_ON` and calls `SetInstanceMultiplier(viewCount)`.

  [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/Runtime/XR/XRPass.cs (accessed 2026-09-24) · Applies to: URP with XR (checked on master; same pattern expected in 2022.3/6.x) · Evidence: [doc] [verify on device]
  - Notes: So on Quest the SPI instance-doubling rules (U3-045) apply only if multiview is unavailable. Your instanced and indirect draws keep their own instance counts, and the driver replicates each view.

- **U3-044 / U2-041** Unmodified custom shaders render only to the first slice (the left eye) under single-pass. Required macros:
  - `UNITY_VERTEX_INPUT_INSTANCE_ID`, `UNITY_VERTEX_OUTPUT_STEREO`
  - `UNITY_SETUP_INSTANCE_ID`, `UNITY_INITIALIZE_OUTPUT`, `UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO`
  - `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX`, needed when the fragment stage needs the eye
  - screen-space texture declare/sample macros

  The built-in debug shader XR/StereoEyeIndexColor paints the left eye green and the right eye red. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassInstancing.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: A broken shader tempts teams into Multi-Pass, which costs about 2x CPU (U3-041). Fix the shader instead.
  - **Merged U2-041:** For SPI/multiview-safe full-screen shaders (URP 12 recipe):
    - Draw a fullscreen mesh or triangle rather than `cmd.Blit`, because `cmd.Blit` toggles XR keywords and breaks SPI.
    - Use `UNITY_VERTEX_INPUT_INSTANCE_ID`, `UNITY_VERTEX_OUTPUT_STEREO`, `UNITY_SETUP_INSTANCE_ID`, `UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO`, and `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX`.
    - Declare textures with `TEXTURE2D_X` and sample with `SAMPLE_TEXTURE2D_X`.

    [T]
    - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/renderer-features/how-to-fullscreen-blit-in-xr-spi.html (accessed 2026-09-24) · Applies to: URP 12 · Evidence: [doc]
    - Notes: URP 14+ replaces this with `Blitter` plus `Blit.hlsl` (U2-083).

- **U3-045** In the SPI path, URP doubles instance counts for normal draws through `CommandBuffer.SetInstanceMultiplier`, but not for indirect draws such as `DrawProceduralIndirect`. For those, double the count in your args buffer yourself. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassInstancing.html (accessed 2026-09-24) · Applies to: 6.x docs; applies wherever SPI rather than multiview is active · Evidence: [doc]
  - Notes: On Quest's multiview path the multiplier is not applied (U3-043). Check with StereoEyeIndexColor before you double anything.

- **U3-046** URP's multiview shader plumbing:
  - `STEREO_MULTIVIEW_ON` on GLES3, GLCORE or Vulkan defines `UNITY_STEREO_MULTIVIEW_ENABLED`.
  - In the vertex stage, the eye index is `gl_ViewID`, declared through an `OVR_multiview` cbuffer macro.
  - The fragment stage gets the eye only through a `BLENDWEIGHT0` varying written by `UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO` and read by `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX`.

  [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/UnityInput.hlsl and https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/UnityInstancing.hlsl (accessed 2026-09-24) · Applies to: URP 12+ (checked on master) · Evidence: [doc]
  - Notes: The macro name reflects GL_OVR_multiview on GLES; Vulkan uses core multiview (VK_KHR_multiview). The extension names are my inference from the macro and API, not stated in Unity docs. A fragment shader that reads `unity_StereoEyeIndex` without the post-vertex setup reads the wrong eye.

- **U3-047** In TextureXR.hlsl, `TEXTURE2D_X` becomes a Texture2DArray on Vulkan and GLES3, but `SLICE_ARRAY_INDEX` equals `unity_StereoEyeIndex` only in the stereo-instancing path; otherwise it is 0. Custom full-screen or screen-space sampling code therefore needs checking under multiview. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/TextureXR.hlsl (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc] [verify on device]
  - Notes: Always use the `_X` macros for camera textures, and validate per-eye output with StereoEyeIndexColor or a RenderDoc capture. Where Unity's own full-screen passes get the per-eye slice under multiview was not resolved here.

- **U3-048** Unity adds `STEREO_INSTANCING_ON`, `STEREO_MULTIVIEW_ON`, `STEREO_CUBEMAP_RENDER_ON` and `UNITY_SINGLE_PASS_STEREO` to every graphics shader by default. A script can strip them, and URP strips XR variants when the XR modules are disabled. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-keywords-default.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc] [verify on device]
  - Notes: A Quest-only build can use an `IPreprocessShaders` stripper to drop the stereo keywords Quest never uses, which cuts variant and PSO count. Stripping the active one (`STEREO_MULTIVIEW_ON`) yields left-eye-only rendering or the error shader. Confirm with strict variant matching (U3-073).

- **U3-049** In RenderDoc, the base pass should write straight into the XR eye texture array, labeled "XR Texture [#]" or RTTextureArray, not `_CameraColorTexture`. An intermediate target plus a final blit costs a fixed 1–1.5 ms GPU resolve and forfeits FFR and MSAA benefits. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-1/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Render-target configuration is covered in U2; it is listed here because multiview output checks happen in the same capture.

- **U3-050 / U2-053** Multiview Render Regions skips the nasal region each eye can't see, by setting per-view viewports, scissors and render areas on Vulkan. Requirements:
  - Unity 6.1+
  - Stereo Rendering Mode = Multiview and Symmetric Projection (Vulkan)
  - plug-in: Oculus 4.6+ or OpenXR 1.14+
  - "All Passes" mode needs 6.2+ with OpenXR 1.15+
  - 6.3+ requires Render Graph

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-multiview-render-regions.html (accessed 2026-09-24) · Applies to: 6.1+ Vulkan · Evidence: [doc] [verify on device]
  - Notes: "Final Pass" mode touches only passes that write eye textures, so intermediate textures or post-processing erase the gain. On 6.3+, only passes flagged `MultiviewRenderRegionsCompatible` (set via `SetExtendedFeatureFlags`) take part. The doc cites two Vulkan extensions, per-view viewports and per-view render areas; I believe these are the VK_QCOM_multiview_per_view_* pair (my inference). No published Quest ms saving was found. To measure: GPU ms with the feature on vs off, no post, same pose.
  - **Merged U2-053:** **Multiview Render Regions** (Vulkan-only, 6.1+) skip the nasal region per eye.
    - "All Passes" mode needs 6.2+ and OpenXR 1.15+.
    - From 6.3 both modes require Render Graph, and only passes flagged `MultiviewRenderRegionsCompatible` get it. Custom raster passes opt in via `SetExtendedFeatureFlags`.
    - "Final Pass" mode gives no gain if you render through intermediates or post-processing.

    [T]
    - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/xr-multiview-render-regions.html (accessed 2026-09-24) · Applies to: 6.1+ (Render Graph requirement from 6.3) · Evidence: [doc]
    - Notes: Unity's compatible-pass list includes DrawObjectsPass, DrawSkyboxPass, CopyDepthPass, FinalBlitPass, PostProcessPassRenderGraph, RenderObjectsPass, XROcclusionMeshPass and others. In 6000.5 source, `AreExtendedFeatureFlagsCompatible` always returns true, so mismatched flags do not currently break merging.

### Measured numbers index (draw calls, batching, stereo)

Carried over from the U3 notes. Each row points to the finding that holds the setup.

| ID | Number | Setup | Evidence |
| --- | --- | --- | --- |
| U3-004 | +64% material switch, +175% shader switch, ~25% same-object redraw | Quest 1, Unity 2018.1, GLES, 500 quads | [measured], stale |
| U3-014 | SRP Batcher 1.2x–4x CPU; x1.47 PS4; x1.23 PC DX11 | Unity 2019 blog, HDRP/FPS Sample | [measured], not Quest |
| U3-030 | 146 instances per 16 KiB window; 3,200 instances → 22 draws; 60 fps | Galaxy A51 (Mali-G72), GLES 3.0, 2022.3 | [measured], not Adreno |
| U3-039 | GRD: 1,788 → 1,502 draws but CPU 5.8 → 6.1 ms, GPU +1 ms | PC, Unity 6, Nov 2024 | [community] |
| U3-098 | 200 trees → 5–10 draws with GRD | Android XR device, Unity 6 | [measured], not Quest |
| U3-049 | 1–1.5 ms fixed resolve for intermediate target + blit | Quest (Meta RenderDoc guide) | [doc] |
| U3-003 | <100 draws / <750K tris (Q2); <200 / <1.5M (Q3) | Meta guidance | [doc] |

No published Quest 2/3/3S number was found for SRP Batcher on/off, GRD or GPU occlusion GPU cost, per-PSO creation time, half vs float speedup, discard or A2C cost, or Multiview Render Regions savings. Measurement methods are in the findings and in Gaps.

## 6. Shaders: precision, discard, variants, stripping, PSO hitches

Quest shader-optimization history also appears in section 1 (U1-038 DistanceAttenuation, U1-040 light-count regression).

### Shader precision on Adreno

- **UNITY-GF2-003** Qualcomm's public product briefs don't name the Adreno model in either XR2 generation. The XR2 Gen 2 platform brief (87-73689-1 Rev A), the XR2+ Gen 2 brief (87-73622-1 Rev A, ©2024) and the XR2 Gen 2 reference-design brief (87-61723-1 Rev B) all say only "Qualcomm Adreno GPU". They add relative figures: 2.5x the GPU performance of XR2 Gen 1, and 15% higher maximum GPU frequency for XR2+ Gen 2 over XR2 Gen 2. The Adreno 650 (Quest 2) and Adreno 740 (Quest 3/3S) identification therefore rests on Meta's documentation. [T]
  - Source: https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf ; https://docs.qualcomm.com/doc/87-73622-1/87-73622-1_REV_A_Snapdragon_XR2__Gen_2_Platform_Product_Brief.pdf ; https://docs.qualcomm.com/bundle/publicresource/87-61723-1_REV_B_Snapdragon_XR2_Gen_2_Reference_Design_Product_Brief.pdf ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2 (XR2 Gen 1), Quest 3/3S (XR2 Gen 2) · Evidence: [doc]
  - Notes: Qualcomm's XR2 product web pages are JS-rendered and returned no spec text; the 2019 XR2 press release could not be read either (Wayback returned no GPU text). Third-party reports put the Quest 3 GPU "in the Adreno 740 family" (a TechInsights teardown names the SoC SXR2230P), but they are not primary. For skills this matters in one way: use Adreno 6xx guidance for Quest 2 and Adreno 7xx guidance for Quest 3/3S, citing Meta. To confirm on a device: `adb shell dumpsys SurfaceFlinger | grep -i GLES`, or read `SystemInfo.graphicsDeviceName` in a build; both report the driver's renderer string. [verify on device]

- **U3-051** Player Settings > Shader Precision Model:
  - **Platform default:** lower precision on mobile, full elsewhere.
  - **Unified:** lower precision wherever the platform supports it.

  The setting already exists in 2021.3 and 2022.3. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3+ · Evidence: [doc]

- **U3-052** Under the Unified model, `half` compiles to `min16float`: mediump on OpenGL/GLES and a RelaxedPrecision float on Vulkan. Other rules:
  - `half` values in buffers are stored at 32-bit size and alignment, so they save ALU and registers, not buffer bandwidth.
  - The `h` literal suffix (`2.0h`) isn't supported and is treated as float.
  - `Texture2D<half4>` makes texture sampling return half.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SL-Use16BitPrecisionInShaders.html (accessed 2026-09-24) · Applies to: 6.x docs; the precision model exists 2021.3+ · Evidence: [doc]
  - Notes: RelaxedPrecision is a hint, so the Adreno driver decides. Confirm in the 16-bit ALU count (U3-006).

- **U3-053** Core RP's `real` type:
  - `HAS_HALF` is defined on `SHADER_API_MOBILE` or under the unified model.
  - `PREFER_HALF` defaults to 1, so on mobile `real` becomes `half` (`min16float`).
  - Defining `PREFER_HALF 0` before including Common.hlsl forces float.
  - Warning 3205 (precision-loss conversion) is suppressed on mobile/GLES3.

  [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl (accessed 2026-09-24) · Applies to: URP 12+ (checked on master) · Evidence: [doc]
  - Notes: Suppressing 3205 hides narrowing conversions in custom code. Review the compiled stats rather than trusting a clean compile.

- **U3-054** Meta's counters define precision behavior on Quest:
  - Fragment ALU instructions are reported in full-precision units, where 2 mediump equal 1 full.
  - `lowp` maps to 16-bit and counts as Half.
  - Vertex-shader ALU counts exclude medium precision because vertex shaders don't use it.

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc] [verify on device]
  - Notes: Inference: half pays off in fragment shaders, and `half` in vertex code buys no ALU saving on Quest. No published Adreno 650 vs 740 half-rate speedup was found. To measure: compare the Fragment ALU (Full) vs (Half) split and GPU ms for float vs half variants of one material.

- **U3-055** In the stats view, full-precision registers are 128-bit (4×FP32) and half-precision registers are 64-bit (4×FP16); overall footprint counts 4×FP32 or 8×FP16 per 128-bit register. Fewer registers mean more active waves, which hide texture latency better. Meta advises half variables but warns against excessive mixed-precision operations. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ (accessed 2026-09-24) · Applies to: Vulkan · Evidence: [doc]
  - Notes: Half-to-float conversions are ALU work. Keep precision consistent along a chain.

- **U3-056** Shader Graph precision modes are Single, Half, Switchable (Sub Graphs only) and Inherit, set in Graph Settings or per node:
  - New nodes inherit the graph's precision.
  - A node fed both Half and Single inputs resolves to Single.
  - Color Mode = Precision tints nodes: blue for Single, red for Half, green for Switchable.

  [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Precision-Modes.html (accessed 2026-09-24) · Applies to: Shader Graph 12+ (checked 17.0) · Evidence: [doc]
  - Notes: A single Single-precision input (for example a Position node) promotes everything downstream. Check with Color Mode = Precision, then confirm in the Vulkan stats.

- **U3-057** Shader Graph's guidance: keep world-space positions, texture coordinates and heavy scalar math (trig, pow, exp) in Single. Half suits directions, short vectors, object-space positions and most HDR colors, but not very bright sources such as the sun. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Precision-Modes.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Half UVs on large atlases or tiling detail maps visibly swim at 2064×2208 per eye on Quest 3. [verify on device]

### Fragment cost, discard, LRZ, alpha-to-coverage, blending

- **U3-059** On Adreno, LRZ is an early depth test built during the binning pass. Two limits:
  - It can't be used when late-Z is required, such as a shader writing depth.
  - It works in one depth-compare direction; flipping the comparison mid-pass invalidates it. Before A650 this disabled LRZ for the rest of the render pass. A650+ tracks direction on the GPU, and A7xx adds bidirectional LRZ buffers.

  [T]
  - Source: https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html (accessed 2026-09-24) · Applies to: Adreno 6xx/7xx as reverse-engineered for the open Turnip/freedreno driver · Evidence: [community] [verify on device]
  - Notes: Quest ships Qualcomm's proprietary driver, so treat this as architecture and not exact driver policy. Qualcomm's Adreno best-practice pages were not retrievable (JS-rendered). Avoid ZTest direction flips (for example reversed-Z tricks) and `SV_Depth` writes in the main opaque pass.

- **U3-060** Per the same Mesa doc, draws whose fragment shader uses `discard` (clip/alpha test) can't contribute to LRZ during binning. Some GPUs can feed their depth back during the rendering pass (LRZ feedback), which matters most when such draws come early in the pass. [T]
  - Source: https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html (accessed 2026-09-24) · Applies to: Adreno 6xx/7xx (Mesa reverse-engineering) · Evidence: [community] [verify on device]
  - Notes: Practical rule: draw opaque (queue 2000) before alpha-tested (URP's AlphaTest queue, 2450), so cutout pixels test against LRZ built by solid geometry. URP's BaseShaderGUI already assigns alpha-clipped materials to the AlphaTest queue (U3-061 source). No published Quest ms cost for discard was found. To measure: GPU ms and % Shaders Busy on a foliage-heavy view with Alpha Clipping on vs an opaque stand-in.

- **U3-061** In URP 14+ Lit, turning on Alpha Clipping for an Opaque material also sets `AlphaToMask` on:
  - URP marks A2C as available (`_AlphaToMaskAvailable`) only when the camera target has MSAA > 1 and the pass is opaque.
  - The shader then exports an `fwidth`-sharpened alpha to the coverage mask and still clips near-zero alpha.

  URP's own tooltip says to avoid Alpha Clipping on materials whose alpha is constant, because with MSAA it adds cost for nothing. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGUI/BaseShaderGUI.cs; https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/ShaderLibrary/ShaderVariablesFunctions.hlsl; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/Runtime/Passes/DrawObjectsPass.cs (accessed 2026-09-24) · Applies to: URP 14 (2022.3) and later; URP 12 (2021.3) Lit has no AlphaToMask · Evidence: [doc]
  - Notes: A2C adds derivative ALU plus per-sample coverage work, and it keeps the discard (U3-060). No published Adreno A2C cost was found. To measure: GPU ms with MSAA 2x/4x and A2C on vs off (force `_AlphaToMask` to 0 in a material copy).

- **U3-062** For expensive alpha-tested foliage, Meta suggests trying a depth-only prepass that writes depth where alpha ≠ 0, followed by a color pass with depth test Equal. Experiment, because results vary. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-1/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc] [verify on device]
  - Notes: This is a targeted, per-material prepass, not URP's global depth priming (U3-058). With it, the costly shading pass runs without discard.

- **U3-063** Meta's DCA page: alpha blending is not cheap. Linear color space makes blending costlier, because every blend applies gamma conversion on read and write. Framebuffer-fetch cost scales with MSAA sample count. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (accessed 2026-09-24) · Applies to: measured on Quest 1 / Unity 2018 · Evidence: [doc]
  - Notes: Possibly stale hardware. The direction still holds on tile GPUs; re-measure large transparent quads on Quest 2.

- **U3-064** Disable renderers that have faded to alpha 0. The engine still submits and shades them, and in Meta's example a full-screen faded vignette kept paying full cost. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-2/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]

- **U3-065** Avoid geometry shaders on tile GPUs: generating primitives breaks the tiled flow, and some devices lack them entirely. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Stereo expansion via geometry shaders is legacy. Multiview replaces it.

### URP's Quest-only shader paths (6.5+)

- **U3-066 / U1-036 / U2-056** Unity 6.5 added the `UNITY_PLATFORM_META_QUEST` shader define for Meta Quest builds. It is first listed in the 6000.5.0a3 notes. URP's Lit, SimpleLit, ComplexLit, Terrain, Particles, WavingGrass and SRP library functions branch on it, and custom shaders that call SRP library lighting and shadow functions inherit the optimizations. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html; https://unity.com/releases/editor/whats-new/6000.5.0 (accessed 2026-09-24) · Applies to: 6.5, 6.6 only (not in 6.0 LTS or 6.3 LTS) · Evidence: [doc]
  - Notes: The page exists only in 6.5+ manuals. Hand-rolled lighting that doesn't call the SRP functions gets none of this.
  - **Merged U1-036:** 6.5 added automatic Meta Quest shader optimizations. They switch on when the Meta Quest build profile is active and apply to URP Lit, Simple Lit, Shader Graph nodes and the SRP library functions. The additions are the `UNITY_PLATFORM_META_QUEST` define (6000.5.0a3), skipping shadow-map sampling on back faces, skipping a light when distanceAttenuation ≤ 0 (6000.5.0a9), a camera-projection query shortcut (6000.5.0a5), and a light-loop unroll keyword when Per Object Limit = 1. [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html (accessed 2026-09-24) · Applies to: 6.5+ · Evidence: [doc] [verify on device]
    - Notes: Unity says these lower GPU frame time, instruction count and bandwidth, but publishes no number. To measure, build the same scene with the profile's optimizations on and off, then compare GPU ms and the Lit shader instruction count in the compiled shader (RenderDoc or Snapdragon Profiler). Custom HLSL that calls SRP library functions picks these up automatically. The light-loop unroll adds variants.
  - **Merged U2-056:** Meta Quest build-profile shader optimizations (6.1+; expanded in 6.5/6.6):
    - Camera projection queries are compiled as perspective-only. Orthographic cameras need the `_META_QUEST_ORTHO_PROJ` keyword.
    - The light loop is unrolled when Per Object Limit = 1.
    - 6.5 adds a `UNITY_PLATFORM_META_QUEST` shader macro.

    [T]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html (accessed 2026-09-24) · Applies to: 6.1+ · Evidence: [doc]
    - Notes: Lead for the shader-variant topic. Build profile defaults: Vulkan, min API 29, target API 32, IL2CPP, ARM64, SPI, anisotropic filtering Per Texture.
  - Merge note: U2-056 dates the shader optimizations to 6.1+, U1-036 and U3-066 to 6.5; see Conflict X-C7.

- **U3-067** The automatic Quest optimizations, read from URP source:
  - Shadow sampling is skipped for geometry facing away from the main light (the release notes say so).
  - The shadow lookup early-outs outside the shadow map.
  - Lighting evaluates behind a `[branch] if (NdotL > 0)`.
  - Lights with zero distance attenuation are skipped.
  - 6.6 adds "three shader micro-optimizations" for Quest.

  [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl, .../ShaderLibrary/Shadows.hlsl (accessed 2026-09-24); release notes https://unity.com/releases/editor/whats-new/6000.6.0 (6000.6.0b1 line, accessed 2026-09-24) · Applies to: 6.5+ (micro-optimizations 6.6+) · Evidence: [doc] [verify on device]
  - Notes: Unity describes the goals (lower GPU time, fewer instructions, less bandwidth, better occupancy) but publishes no per-optimization ms. To quantify, diff the Vulkan shader stats (U3-006) for Lit built on 6.3 vs 6.6.

- **U3-068** Configurable: "Light loop unroll". Setting the URP Asset's per-object light limit to 1 makes `ForwardLights` enable `META_QUEST_LIGHTUNROLL`. Unity says this improves runtime performance but increases variant count and build time. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/Shaders/Lit.shader (accessed 2026-09-24) · Applies to: 6.5+ · Evidence: [doc]
  - Notes: It is a `multi_compile`, so it doubles the affected passes before stripping. Check the URP stripping log (U3-077) and extend the GSC trace (section 10).

- **U3-069 / U1-037** Configurable: "Camera projection query". On Quest, URP always resolves the camera as perspective. Orthographic cameras need the `META_QUEST_ORTHO_PROJ` keyword enabled through Keyword Declaration Overrides. Master Lit.shader also carries a `META_QUEST_NO_SPOTLIGHTS_LIGHT_LOOP` multi_compile. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/Shaders/Lit.shader (accessed 2026-09-24) · Applies to: 6.5+ (NO_SPOTLIGHTS seen on master; undocumented) · Evidence: [doc] [verify on device]
  - Notes: Ortho UI or minimap cameras in a Quest build will render wrongly unless you opt in. `META_QUEST_NO_SPOTLIGHTS_LIGHT_LOOP` has no manual entry; confirm what enables it before relying on it.
  - **Merged U1-037:** The Quest camera-projection optimization assumes every camera is perspective. Projects that use orthographic cameras on Quest must add the `_META_QUEST_ORTHO_PROJ` keyword via Project Settings > Graphics > Shader Build Settings > Keyword Declaration Overrides. Otherwise lighting and projection are wrong. [C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html (accessed 2026-09-24) · Applies to: 6.5+ · Evidence: [doc]
  - Merge note: the keyword spelling differs between findings (`_META_QUEST_ORTHO_PROJ` vs `META_QUEST_ORTHO_PROJ`); see Conflict X-C8.

### Keywords, variants, stripping

- **U3-071** How the three keyword types compile:
  - **`shader_feature`:** compiles only the combinations used by materials in the build.
  - **`multi_compile`:** compiles every combination. Unity's example: 8 keyword sets of 3 can exceed 6,000 variants.
  - **`dynamic_branch`:** compiles one variant; each keyword becomes a uniform int sent per draw, tested with `if`, never `#if`.

  Unity recommends `dynamic_branch` only on fast GPUs and only when both branches cost about the same. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-conditionals-choose-a-type.html (accessed 2026-09-24) · Applies to: `dynamic_branch` 2022.1+; the others all versions · Evidence: [doc]
  - Notes: On Quest, `dynamic_branch` trades PSO count (consistency) against per-pixel branch cost and register pressure (throughput). Because the worst branch sets the register count, always check the Vulkan stats (U3-006).

- **U3-072** A shader that uses more than 128 keywords in total carries a small runtime performance penalty, and Unity reserves 4 per shader. In 2022.3, the ceilings are about 4.29 billion global keywords and 65,534 local keywords per shader. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/SL-MultipleProgramVariants-declare.html; https://docs.unity3d.com/2022.3/Documentation/Manual/shader-keywords.html (accessed 2026-09-24) · Applies to: 2021.2+ keyword system · Evidence: [doc]
  - Notes: Use `_local` and stage-scoped (`_fragment`/`_vertex`) declarations to cut both counts and variants.

- **U3-073** Enable Player > Strict shader variant matching in test builds. A missing variant then renders with the error shader and logs the shader, subshader, pass and keywords, instead of silently using the closest match. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html and https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html (accessed 2026-09-24) · Applies to: 2022.3+ (the setting is not on the 2021.3 Android Player settings page) · Evidence: [doc]
  - Notes: A silent fallback can hide a stripped variant that later loads a different PSO. Strict mode is also how you validate XR keyword stripping (U3-048).

- **U3-074** Graphics > Shader Build Settings (6.3+; absent in 6.2) lets you add keywords and set a Type Override to `shader_feature` or `dynamic_branch`, overriding the shader source. Each build profile can override it, for example a Quest profile that turns `multi_compile` sets into `dynamic_branch`. [C][T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html (accessed 2026-09-24) · Applies to: 6.3+ · Evidence: [doc]
  - Notes: This is the cheapest way to shrink URP's `multi_compile` sets on Quest without forking URP shaders.

- **U3-075 / U1-051** Shader Constant Defines (seen only in the 6.6 manual) set a compile-time constant per build profile, for example `NUMBER_OF_MSAA_SAMPLES 2`. The shader guards its default with `#ifndef`, so the value is baked in without creating variants. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html (accessed 2026-09-24) · Applies to: 6.6 (not found in the 6.0–6.5 manual pages) · Evidence: [doc] [verify on device]
  - **Merged U1-051:** 6.6 lets you set shader constant values per build profile without creating variants. Quest-specific quality switches can then be compile-time constants rather than keywords, which avoids variant growth and the PSO count that comes with it. [T][C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]

- **U3-076** For project-specific stripping, `IPreprocessShaders.OnProcessShader` and `IPreprocessComputeShaders.OnProcessComputeShader` run before each pass or compute kernel compiles into a build. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]

- **U3-077** URP stripping controls:
  - In 6.x they sit under Graphics > Additional Shader Stripping Settings: Strip Unused Variants, Strip Unused Post Processing Variants, Strip Screen Coord Override Variants, Shader Variant Log Level, Export Shader Variants.
  - In URP 12/14 they sat in URP Global Settings, with Strip Debug Variants too; Screen Coord Override and the log level arrived in URP 14.
  - Export writes `Temp/graphics-settings-stripping.json` and `Temp/shader-stripping.json`.
  - The log reports lines such as `Universal Render Pipeline/Lit - Total=8/39(20.51%)`.

  [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-features.html; https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-check.html; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-global-settings.html (accessed 2026-09-24) · Applies to: URP 12–17 · Evidence: [doc]
  - Notes: "Strip Unused Variants" is the switch that also strips DOTS instancing variants, which conflicts with BRG (U3-026). GRD projects keep BRG variants via Graphics > BatchRendererGroup Variants.

- **U3-078** URP strips by the features enabled across every URP Asset in the build, so shipping assets with different rendering paths or features in one build multiplies variants. Unity advises against mixing rendering paths. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-features.html (accessed 2026-09-24) · Applies to: URP 12+ · Evidence: [doc]
  - Notes: Quality-level URP assets for Quest 2 vs Quest 3 should differ only in values such as render scale and shadow resolution, not in feature toggles, unless you accept the extra variants and warmup set.

- **U3-079** URP's prebuilt shaders use dynamic branching only for fog (`_ FOG_LINEAR FOG_EXP FOG_EXP2`), `_REFLECTION_PROBE_BLENDING` and `_REFLECTION_PROBE_BOX_PROJECTION`. Unity warns this can slow older mobile devices. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-fog.html (accessed 2026-09-24) · Applies to: 6.x URP · Evidence: [doc] [verify on device]
  - Notes: If fog is off project-wide, confirm the uniform branch really skips the work on Adreno 650 (Vulkan stats flow-control count).

- **U3-080 / U4-093** How shaders load at runtime:
  1. Variants load into CPU memory with the scene, in compressed chunks that are decompressed on demand.
  2. On first use, the driver builds the GPU program. This is the stall.
  3. The program is cached until the shader is unloaded.

  Player settings: chunk size (16 MB default), chunk count (0 = no limit), and Keep Loaded Shaders Alive to prevent unloading. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-loading.html; https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3+ (chunk settings and Keep Loaded Shaders Alive appear on the 2021.3 Android Player page) · Evidence: [doc]
  - Notes: Keep Loaded Shaders Alive avoids re-creating programs after scene unloads, at the cost of RAM, a real trade on Quest 2's 6 GB. A chunk-count cap can force decompression again later; this is inference [verify on device].
  - **Merged U4-093:** When Unity loads a scene or resource, it loads that content's compiled shader variants into CPU memory and, by default, decompresses them. The first time a variant is used, the driver builds the GPU-specific version, which can cause a visible stall. Unity caches the result, and frees a variant once no object references it. [C]
    - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/shader-loading.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
    - Notes: The Profiler markers for these stalls are `Shader.CreateGPUProgram` (shader variant) and `CreateGraphicsGraphicsPipelineImpl` (PSO).

- **U3-081** Profiler markers for shader and PSO hitches:
  - `Shader.ParseThreaded` / `Shader.ParseMainThread`: load
  - `Shader.CreateGPUProgram`: GPU program creation
  - `CreateGraphicsGraphicsPipelineImpl`: PSO creation
  - `Shader.MainThreadCleanup`: unload

  Development builds can also log compiles with Graphics > Log Shader Compilation. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-introduction.html; https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html (accessed 2026-09-24) · Applies to: 6.x (the CreateGPUProgram marker also exists in older versions) · Evidence: [doc]
  - Notes: Correlate these markers with OVR Metrics Tool stale-frame spikes to attribute hitches.

### Shader Graph overhead: keywords, variant limits, generated code (gap-fill round 1)

- **UNITY-GF1-003** Shader Graph keyword **Definition** controls variant count: [C]
  - **Shader Feature:** only compiles variants for keyword combinations that materials in the build use, and strips the rest.
  - **Multi Compile:** compiles every combination, used or not.
  - **Predefined:** reuses a keyword the target or built-in macros already define, for build-time static branching.

  Keywords can also be limited to a **Stage** (All, Vertex or Fragment). Unity warns that the number of branch combinations grows extremely fast as keywords are added, which mainly hurts build time.
  - Source: https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Keywords-reference.html ; https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Keywords-concepts.html (accessed 2026-09-24) · Applies to: Shader Graph 12+ (checked 17.0.4) · Evidence: [doc]
  - Notes: Serves consistency. Every variant is a potential PSO the GSC warmup must cover (section on GraphicsStateCollection), so prefer Shader Feature for artist toggles and a Stage of Vertex or Fragment where possible. The docs give no runtime cost figure; each variant is a separate program, so runtime cost is per variant, not per keyword.

- **UNITY-GF1-004** Shader Graph Project Settings defaults, from the 6000.0 source: [T]
  - Shader Variant Limit: 2048 (`defaultVariantLimit`), applied unless Override Variant Limit is set.
  - Custom Interpolator Warning Threshold: 16 channels.
  - Custom Interpolator Error Threshold: 32 channels.
  - Allowed thresholds range from 8 to 32 channels.
  - Source: https://raw.githubusercontent.com/Unity-Technologies/Graphics/6000.0/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs ; https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Project-Settings.html (the docs page names the settings but gives no defaults) (accessed 2026-09-24) · Applies to: 6000.0 (round 2 confirmed the same values on 6000.3, 6000.5 and master; 2021.3 and 2022.3 differ, see UNITY-GF2-001) · Evidence: [doc]
  - Notes: A graph that hits 2048 variants per graph is far past what a Quest title should ship. Use the limit as a tripwire, not a budget. Custom interpolators move vertex-stage work out of the fragment stage (throughput), but each channel adds varyings, which cost attribute bandwidth. There is no published per-channel cost on Adreno. [verify on device]

- **UNITY-GF1-005** With the URP target's **Allow Material Override** enabled, these properties become per-material in the Material Inspector: [T]
  - Workflow Mode and Receive Shadows (Lit only)
  - Cast Shadows
  - Surface Type
  - Render Face
  - Alpha Clipping
  - Depth Write and Depth Test
  - Support VFX Graph

  The page does not say whether the option adds keywords or variants. Its only performance statement concerns Support VFX Graph: enabling it without using the graph in a VFX affects import time only.
  - Source: https://docs.unity3d.com/Packages/com.unity.shadergraph@17.3/manual/surface-options.html ; https://docs.unity3d.com/Packages/com.unity.shadergraph@14.0/manual/surface-options.html (accessed 2026-09-24) · Applies to: Shader Graph 12+ (URP and Built-in targets) · Evidence: [doc]
  - Notes: A material-level Alpha Clipping toggle lets artists turn on `clip()` per material, which disables LRZ/early-Z benefits for that material (section 6, fragment cost). Variant impact is resolved from source in UNITY-GF2-002.

- **UNITY-GF2-001** How the Shader Graph variant limit works on each branch (read from source): [C]
  - **2021.3 (Shader Graph 12):** there is no project setting. The limit is a per-user Editor preference, Preferences > Shader Graph > Shader Variant Limit. It is stored in EditorPrefs key `UnityEditor.ShaderGraph.VariantLimit`, and `EditorPrefs.GetInt(Keys.variantLimit, 128)` makes the effective default **128**, even though the field initializer is 2048. The limit can differ between team members' machines.
  - **2022.3 (Shader Graph 14):** Project Settings > Shader Graph > Shader Variant Limit (`shaderVariantLimit`) defaults to **2048** and has no override toggle. A separate per-user **Preview Variant Limit** preference defaults to 128 (same EditorPrefs key). If the preview limit is higher than the project limit, it is ignored.
  - **6000.0, 6000.3, 6000.5 and master (Shader Graph 17.x):** `defaultVariantLimit = 2048` applies unless **Override Variant Limit** is ticked, in which case `shaderVariantLimit` is used. The Preview Variant Limit preference still defaults to 2048 by field initializer.
  - **Custom interpolators, all branches:** warning at 16 channels, error at 32, allowed range 8-32.
  - Source: https://github.com/Unity-Technologies/Graphics/blob/2021.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphPreferences.cs ; https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs ; https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphPreferences.cs ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs ; https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs ; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs (accessed 2026-09-24) · Applies to: Shader Graph 12 (2021.3), 14 (2022.3), 17.x (6000.0-6000.6); both APIs · Evidence: [doc]
  - Notes: Serves consistency. The limit is a build-time guard, not a runtime cost. Its value for Quest is as a tripwire: a graph that needs more than a few hundred variants will also carry many PSOs to trace and warm (GSC section). On 2021.3, put the preference value in the team's setup doc, because a machine at 128 and one at 2048 can produce different results from the same graph. The 6000.6 value is inferred from master (no 6000.6/staging branch; see the URP mapping row).

- **UNITY-GF2-002** Turning on the URP target's **Allow Material Override** replaces compile-time defines with `shader_feature` keywords, and fixed render states with material-property render states. Read from `UniversalTarget.cs` and `UniversalLitSubTarget.cs`: [C][T]
  - **Keywords added** (all `KeywordDefinition.ShaderFeature`, fragment stage):
    - `_SURFACE_TYPE_TRANSPARENT` (global scope, "needs to match HDRP"), `_ALPHAPREMULTIPLY_ON`, `_ALPHAMODULATE_ON` (local), from `AddTargetSurfaceControlsToPass`
    - `_ALPHATEST_ON` (local), from `AddAlphaClipControlToPass`
    - Lit only: `_SPECULAR_SETUP` and `_RECEIVE_SHADOWS_OFF` (local)

    With the option off, each of these is a `#define` fixed by the graph setting, or is absent.
  - **Render states** become material-driven. `UberSwitchedRenderState` emits ZTest, ZWrite, Cull and Blend (color and alpha) bound to material properties (`Uniforms.zTest = "[" + Property.ZTest + "]"`, and so on), and `AddAlphaToMaskControlToPass` emits `AlphaToMask [_AlphaToMask]`, instead of fixed values.
  - **Passes:** `mayWriteDepth` returns true, so a DepthOnly pass is always generated. The Lit ShadowCaster pass is always generated, even if the graph's Cast Shadows is off.

  All keywords are `shader_feature`, so the build compiles only the combinations that materials actually use. A single graph used by N materials with different surface, clip or workflow settings compiles up to N distinct variants per pass. Each render-state combination is also a distinct PSO on Vulkan. [C]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Targets/UniversalTarget.cs ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Targets/UniversalLitSubTarget.cs ; https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Targets/UniversalTarget.cs ; https://github.com/Unity-Technologies/Graphics/blob/2021.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Targets/UniversalTarget.cs ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGUI/BaseShaderGUI.cs (accessed 2026-09-24) · Applies to: URP 12 (2021.3; no `_ALPHAMODULATE_ON`), URP 14 (2022.3), URP 17.x (checked 6000.3); both APIs · Evidence: [doc]
  - Notes: Consistency: every distinct material configuration adds a variant and PSO that GSC tracing must capture (UNITY-GF1-005, GSC section). Throughput: URP's material GUI (`BaseShaderGUI.cs`) sets `_AlphaToMask` = 1 whenever an opaque material has Alpha Clipping on. Its tooltip warns this adds "an unnecessary performance cost when used with MSAA" if alpha is constant. It also makes `clip()` reachable, which costs LRZ/early-Z on Adreno (section 6). Recommendation for Quest: leave Allow Material Override off for high-count environment graphs and make separate opaque and alpha-clipped graph assets. Turn it on only where artists need per-material surface switching, and audit the material set. Round 1's Known unknown on this point is resolved; the runtime cost per variant is still unmeasured.

- **UNITY-GF1-006** A May 2023 forum thread describes where Shader Graph code generation costs more than hand-written HLSL. The generated temporaries are usually removed by the compiler, so generated code size is not a cost indicator. The real overhead is structural. For example, each Sample Texture node set to Normal unpacks and reconstructs Z per sample. Hand-written code can blend packed normals and reconstruct once. The respondent's view is that large systematic shaders (terrain, layered materials) gain most from hand-writing. [T]
  - Source: https://discussions.unity.com/t/urp-hdrp-shader-graph-code-gen-optimization/918879 ; https://discussions.unity.com/t/urp-shadergraph-versus-writing-urp-shaders-with-lighting-by-hand/918888 (accessed 2026-09-24) · Applies to: URP 12-15 era Shader Graph; the principle applies to 17.x · Evidence: [community] [verify on device]
  - Notes: The respondent is not Unity staff. In the second thread, Unity staff (2023-05-25) recommended Shader Graph where feasible because hand-written URP HLSL has no stable API contract across upgrades, and pointed to the then-upcoming Block Shaders. No source gives a measured Shader Graph vs HLSL GPU-ms delta on Quest. Method: compile the Shader Graph and an equivalent hand-written shader for Vulkan/Android, compare the Adreno instruction counts (Snapdragon Profiler or Adreno offline compiler), then compare GPU ms at locked GPU level in OVR Metrics Tool.

### PSO hitches: GraphicsStateCollection (Unity 6)

- **U3-082** On Vulkan (and DX12/Metal), a PSO bakes the shader variant together with render state, vertex layout and render-target formats. Warming variants alone (`ShaderVariantCollection.WarmUp`, `Shader.WarmupAllShaders`) can build the wrong PSOs "due to missing graphics states". Unity does not recommend SVC-based warmup on these APIs. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-prewarm-other.html; https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-introduction.html (accessed 2026-09-24) · Applies to: Vulkan on all versions (the explanation is in the 6.x manual) · Evidence: [doc]
  - Notes: This is why a Quest Vulkan app that "warms up shaders" in 2021.3/2022.3 can still hitch on first draw.

- **U3-083 / U1-045 / U1-046 / U1-048 / U4-096** GraphicsStateCollection (GSC) timeline:

  | Version | Change |
  | --- | --- |
  | 6000.0.0b15 | Added, in `UnityEngine.Experimental.Rendering` |
  | 6000.0.55f1 | Automatic fallback to legacy SVC warmup on platforms without parallel PSO compilation |
  | 6.5 | Moved to `UnityEngine.Rendering` (non-experimental); cache-miss tracing added; Graphics Settings automation added (6000.5.0a9) |

  [C]
  - Source: release notes https://unity.com/releases/editor/whats-new/6000.0.0 (b15), https://unity.com/releases/editor/whats-new/6000.0.55f1, https://unity.com/releases/editor/whats-new/6000.5.0 (accessed 2026-09-24); https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.GraphicsStateCollection.html · Applies to: 6.0+ · Evidence: [doc]
  - Notes: Code shared between 6.0/6.3 and 6.5+ needs a `#if UNITY_6000_5_OR_NEWER` namespace switch. The 6.3/6.4 prewarm pages still call it experimental. See U3-C4 on the fallback version.
  - **Merged U1-045:** GraphicsStateCollection (GSC) was added in 6000.0.0b15 as an experimental API (UnityEngine.Experimental.Rendering). It traces the PSOs a run actually uses so they can be compiled ahead of time. 6.1 What's New presents it as the fix for shader-compilation stutter. [C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity61.html ; https://unity.com/releases/editor/whats-new/6000.0.0b15 (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - **Merged U1-046:** How GSC has changed: 6.3 added utility methods, overrides and job-lifetime warnings. 6.4 added editing collections without re-tracing and generating states from Mesh and Material arrays. 6.5 added `Warmup(traceCacheMisses: true)` and `cacheMissCollection` (6000.5.0a3). In 6000.5.0a9 it moved to the `UnityEngine.Rendering` namespace and gained `LoadFromJson`, GlobalKeyword overloads, and Project Settings > Graphics options to trace and prewarm PSOs automatically. [C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity64.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html ; https://unity.com/releases/editor/whats-new/6000.5.0a9 (accessed 2026-09-24) · Applies to: 6.3–6.6 · Evidence: [doc]
    - Notes: The namespace move breaks `using UnityEngine.Experimental.Rendering` code when upgrading to 6.5. Collections traced on one version should be re-traced after an Editor upgrade, because shader variants and render-pass state change.
  - **Merged U1-048:** On platforms without parallel PSO compilation, GSC falls back to the legacy ShaderVariantCollection warmup (6000.0.55f1, UUM-112286). A repeated fallback log in release builds was removed in 6000.0.74f1 and 6000.5.0b5 (UUM-138841). [C]
    - Source: https://unity.com/releases/editor/whats-new/6000.0.55f1 ; https://unity.com/releases/editor/whats-new/6000.0.74f1 (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - **Merged U4-096:** Unity 6 adds PSO warm-up. `GraphicsStateCollection.WarmUp` or `WarmUpProgressively` (an experimental API) builds PSOs during loading, and the driver caches them to disk. The progressive variant spreads the work to avoid blocking. Unity recommends warming up during app or scene loading. [C]
    - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/shader-prewarm.html (accessed 2026-09-24) · Applies to: 6000.0+ · Evidence: [doc]
    - Notes: PSO tracing belongs to the shader/PSO topic (see Leads). It is listed here because it is a scene-load step.
  - Merge note: U1-047 (Vulkan GSC warmup fix only in 6.4) is kept separate because it conflicts with U3-091; see Conflict X-C1.

- **U3-084** Tracing rules:
  - Tracing works only in development builds.
  - Call `BeginTrace()` at startup and `EndTrace()` when done, then either `SaveToFile()` (writes `.graphicsstate`; on Quest, retrieve with `adb pull`) or `SendToEditor()` (needs Development Build plus Autoconnect Profiler).
  - Trace one collection per graphics API and platform.
  - Compute and ray-tracing shaders aren't captured.

  [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-trace.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: Release builds can list uploaded variants per frame with the `VariantsUploadedToGpuLastFrame` API (6.5+). It is useful for spotting misses in the field, but it does not capture PSO state.

- **U3-085** Unity staff guidance on GSC tracing:
  - Collections are per graphics API, not per GPU vendor.
  - Every material and effect must actually render during the trace.
  - Switch through quality levels while tracing, because each quality level can change PSOs.

  The URP 3D Sample (17.0.6+) ships reference tooling: `GraphicsStateCollectionManager.cs`, `GraphicsStateCollectionStripper.cs` and `GraphicsStateCollectionCombiner.cs` under `Assets/SharedAssets/GraphicsStateCollections`. [C]
  - Source: https://discussions.unity.com/t/graphicsstatecollection-tracing-and-warmup-in-unity-6/951031 (accessed 2026-09-24; staff post Jul 5, 2024) · Applies to: 6.0+ · Evidence: [community]
  - Notes: For Quest, one Vulkan/Android collection per quality tier. Trace on device, because Editor traces carry desktop state. Whether Quest 2 and Quest 3 PSOs differ enough to need separate traces (different MSAA or formats per tier) is unverified [verify on device].

- **U3-086** Warmup API:
  - `WarmUp(JobHandle)` schedules every PSO in the collection.
  - `WarmUpProgressively(int count, JobHandle)` schedules N per call.
  - Both return a JobHandle; created PSOs are then cached to disk.
  - Real parallel PSO warmup needs `SystemInfo.supportsParallelPSOCreation == true` (WebGPU excepted). Otherwise Unity falls back to `ShaderVariantCollection.WarmUp` semantics, and `count` then limits variants, not PSOs.

  [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.GraphicsStateCollection.WarmUpProgressively.html; https://docs.unity3d.com/6000.6/Documentation/Manual/shader-prewarm.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc] [verify on device]
  - Notes: No published value of `supportsParallelPSOCreation` on Quest Vulkan was found. Log it at startup on Quest 2 and Quest 3; if it is false, you get the variant-only fallback of U3-082. Useful state: `completedWarmupCount`, `isWarmedUp`, `totalGraphicsStateCount`.

- **U3-087** Cache-miss loop (6.5+): warm with `traceCacheMisses = true`, and PSOs requested after warmup that weren't in the collection accumulate in `cacheMissCollection`. Merge them back with `Append` or `AddGraphicsStates`, and check coverage with `ContainsVariant`. Cache-miss tracing requires `isTracingCacheMisses` to be false before the warmup call. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.GraphicsStateCollection.html; https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-trace.html (accessed 2026-09-24) · Applies to: 6.5+ · Evidence: [doc]
  - Notes: Run QA playthroughs on dev builds with this on and ship the merged collection. It is the closest thing to a p99-hitch regression test.

- **U3-088** Graphics Settings > Shader Settings, 6.5+ (absent in 6.3/6.4):
  - Preload Graphics State Collection.
  - Collection Startup Behavior: None (default), Begin Trace, or Warmup.
  - Additional Collections.
  - Warmup Asynchronously.
  - Warmup After Showing First Scene.
  - A progressive per-frame count (0 = all on the next frame).
  - Enable Cache Miss Tracing, with a save path.

  [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html (accessed 2026-09-24) · Applies to: 6.5, 6.6 · Evidence: [doc]
  - Notes: On Quest, warming before the first scene lengthens the black or splash time. Warming progressively after it spreads PSO creation over frames the user sees. Put the warm window behind a loading environment, and size the per-frame count so PSO creation fits the frame's slack (13.9 ms at 72 Hz minus measured frame time). No published per-PSO creation time on Adreno was found; measure `CreateGraphicsGraphicsPipelineImpl` durations.

- **U3-089** The same page still offers SVC-era controls: Preload Shaders, Preload Shaders After Showing First Scene, and Preload Time Limit Per Frame (ms). It warns against Always Included Shaders (which force every variant) in favor of GSCs. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html (accessed 2026-09-24) · Applies to: 6.x (Preloaded Shaders exists in all versions) · Evidence: [doc]

- **U3-090** Unity's own GSC example project builds only for Windows (DX12/Vulkan) or macOS (Metal). There is no Android or Quest sample, so Quest integration is on you. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-example.html (accessed 2026-09-24) · Applies to: 6.x · Evidence: [doc]

- **U3-091** Unity 6.0 beta fixes show the Vulkan async PSO system at work: the `maxParallelPSOCreationJobs` limit is now obeyed on Vulkan, async PSO jobs are no longer cancelled by PipelineKey conflicts, and a race in Vulkan PSO cache registration was fixed. The unfixed issues would have shown up as warmup that silently didn't complete. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.0.0 (6000.0.0b11 notes, accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: Stay on current 6.0/6.3 LTS patches for GSC work. A later 6.4-alpha-only regression ("Fixed GraphicsStateCollection warmup for Vulkan", first seen 6000.4.0a1) did not affect LTS lines.

### PSO hitches before Unity 6, GLES, and on-disk caches

- **U3-092** 2021.3 and 2022.3 have no GSC. Available tools:
  - `ShaderVariantCollection.WarmUp`
  - `Shader.WarmupAllShaders`
  - `Experimental.Rendering.ShaderWarmup` (warms with an explicit vertex layout)
  - the Preloaded Shaders list

  On Vulkan none of these know render-pass/RT state, so hitches remain (U3-082). The reliable technique is to actually render every material and state combination once, off-view or behind a loading screen. [C]
  - Source: https://docs.unity3d.com/6000.1/Documentation/Manual/shader-prewarm.html (the 6.1 page lists the non-GSC methods, accessed 2026-09-24) · Applies to: 2021.3, 2022.3 (and non-GSC APIs later) · Evidence: [doc]

- **U3-093** Meta's archived Unity-ShaderPrewarmer sample does exactly that:
  - It renders MeshRenderers with each material, spawning 50–100 objects per frame at 1/60 s intervals.
  - It targets 2021/2022 LTS, GLES and Vulkan, and built-in RP and URP.
  - It has no Unity 6 PSO-tracing support.

  [C]
  - Source: https://github.com/oculus-samples/Unity-ShaderPrewarmer (accessed 2026-09-24; created 2025-03-18, last push 2025-03-20, archived) · Applies to: 2021.3/2022.3 · Evidence: [doc]
  - Notes: Only MeshRenderer states are covered. Skinned meshes, particles, UI and shadow-caster/depth passes need their own warm scenes. Archived means no fixes; on Unity 6, prefer GSC.

- **U3-094** Unity persists a Vulkan pipeline cache (`vulkan_pso_cache.bin`) and, on GLES3, a program binary cache (`UnityShaderCache/`) under the app's temp/cache directory. Both are device- and driver-specific and must be refreshed when the player updates. Unity documents this for Embedded Linux. [C]
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/embedded-linux-optional-features.html (accessed 2026-09-24) · Applies to: 6.0+ (doc is Embedded Linux) · Evidence: [doc] [verify on device]
  - Notes: That the same files exist on Android/Quest is inference, supported by Meta's SBC page using `/data/user/0/<pkg>/cache/vulkan_pso_cache.bin` as its example path (U3-096). To check: `adb shell run-as <pkg> ls -l cache/` after a warm session and after a force-stop. When Unity flushes the file (on pause or quit) is undocumented, so a crash or kill before the flush could lose the warm cache.

- **U3-095 / U1-050** Unity 6.4 fixed a case where a corrupted Vulkan pipeline cache file made `vkCreatePipelineCache` fail. Before that fix, a bad cache file could cost the whole persisted cache, meaning a cold, hitchy session. [C]
  - Source: https://unity.com/releases/editor/whats-new/6000.4.0f1 (accessed 2026-09-24; also listed in 6000.4.0a2/a4) · Applies to: 6.4+ (no backport to 6.0/6.3 found in the release notes checked) · Evidence: [doc] [verify on device]
  - **Merged U1-050:** Vulkan pipeline cache robustness: 6000.4.0a2/a4 handle a corrupted pipeline cache file that made `vkCreatePipelineCache` fail. 6000.3.21f1 and 6000.5.9f1 skip expensive per-variant work for variants that are already warmed, which lowers CPU cost during warmup. [C][T]
    - Source: https://unity.com/releases/editor/whats-new/6000.4.0a4 ; https://unity.com/releases/editor/whats-new/6000.3.21f1 (accessed 2026-09-24) · Applies to: 6.3.21+, 6.4+ · Evidence: [doc]

- **U3-096** Meta's Shader Compilation page (updated Aug 7, 2026) says heavy Unity and Unreal apps can pause at startup for several seconds, sometimes minutes, to build shader caches. It lists when this happens:
  - first run after install
  - first run after an app update
  - first run after a graphics-driver (OS) update

  First encounters with new content can also drop frames. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ (accessed 2026-09-24) · Applies to: Quest 2, Pro, 3, 3S · Evidence: [doc]
  - Notes: A Horizon OS update invalidates driver caches, so every user re-pays warmup after OS updates. Runtime warmup (GSC or prewarm scene) should run on every launch and be cheap when the cache is already hot.

- **U3-097** The Meta SBC mechanism the same page describes is deprecated:
  - Horizon OS Shader Binary Cache (SBC) automation is marked deprecated and unmaintained, with a replacement in development.
  - Opt-in was a manifest `<meta-data android:name="com.oculus.sbcpath">` pointing at the cache path, for example `cache/vulkan_pso_cache.bin`, plus a dashboard toggle.
  - Automation launches carried the boolean extra `horizonos.extra.SHADER_PREWARMING_AUTOMATION`.
  - The app had to prewarm on launch, with a 10-minute cut-off.
  - Unity apps were "not guaranteed" to be processed.

  [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ (accessed 2026-09-24) · Applies to: Quest 2, Pro, 3, 3S · Evidence: [doc]
  - Notes: Don't build a hitch strategy on SBC. If it's already integrated it does no harm, but ship your own warmup. See U3-C6.

## 7. Lighting

### Mixed lighting modes, URP light limits, forward paths

- **U4-001** Unity ranks the mixed lighting modes by runtime cost. From most to least expensive: Distance Shadowmask, Shadowmask, Baked Indirect, Subtractive. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/lighting-mode.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x, Built-in and URP · Evidence: [doc] [verify on device]
  - Notes: Unity publishes no GPU-ms figure per mode for Quest. To measure, build the same scene once per mode and compare GPU frame time in OVR Metrics Tool or the Unity Profiler GPU module. Keep the camera fixed and CPU/GPU levels locked.

- **U4-002** Subtractive is the cheapest mode. Only the brightest directional light casts realtime shadows, and only dynamic objects get specular from mixed lights. Unity positions it for low-end hardware. The Realtime Shadow Color setting tints the realtime shadow so it blends with baked shadows. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/lighting-mode.html ; https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-Subtractive.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: The visual trade-offs are that static objects get no mixed-light specular and dynamic shadows come from one light only. This mode suits Quest scenes lit mainly by one sun or key light.

- **U4-003** In Baked Indirect, every shadow is realtime, so shadow-caster cost scales with Shadow Distance. Unity's lever is to shorten Shadow Distance. [T]
  - Source: https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-BakedIndirect.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: In URP, Max Distance on the URP Asset (Shadows section) is the effective lever. See U4-029.

- **U4-004** Shadowmask bakes static shadows for up to 4 overlapping mixed lights per texel. Where more than 4 overlap, the extra lights fall back to fully baked; the Light Overlap scene view mode shows where. Unity lists Shadowmask as the most expensive mixed mode in performance and memory. Quality Settings > Shadowmask Mode picks Shadowmask or Distance Shadowmask. [T][C]
  - Source: https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-Shadowmask.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/lighting-mode.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: Distance Shadowmask renders static casters as realtime shadows inside Shadow Distance, which is why it costs more. For the extra texture, see U4-043.

- **U4-005** In the URP Forward path, each object gets 1 main light plus 8 additional lights (9 total). Per camera, the visible additional-light limit is 32 on mobile platforms, 16 on OpenGL ES 3.0 and earlier, and 256 on desktop and console. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/lighting/light-limits-in-urp.html ; the same numbers appear in https://docs.unity3d.com/6000.6/Documentation/Manual/urp/lighting/light-limits-in-urp.html (accessed 2026-09-24) · Applies to: URP 12 to 17.x (numbers taken from the 6000.x pages; check older URP docs for your exact version) · Evidence: [doc]
  - Spot-check (gap-fill round 2): confirmed on the 6000.3 page: 1 main + 8 additional per object; per camera 256 on desktop/console, 32 on mobile, 16 on OpenGL ES 3.0 and earlier. On 6.6 GLES builds, the 16 vs 32 bucket depends on the "Use OpenGL ES 3.0 shaders" setting (U1-040).
  - Notes: Quest runs Vulkan or GLES 3.2, so the 32-light mobile bucket applies. The URP 17 changelog also restates the 32 visible-light mobile limit. Additional lights beyond the per-object limit are silently dropped, which produces visual popping, not a performance gain.

- **U4-007** Unity says the Subtractive and Shadowmask modes are optimized for Forward and should not be used with Deferred. Meta's Quest best-practices page recommends the Forward or Forward+ path. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/rendering-paths-comparison.html ; https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ (updated 2024-09-15; accessed 2026-09-24) · Applies to: URP 14 to 17.x · Evidence: [doc]
  - Notes: The G-buffer cost of Deferred on tile GPUs belongs to topic U2 (see Leads).

- **U4-008** Meta tells Quest developers to avoid realtime GI and to limit per-pixel lights, using Forward+ when many lights are needed. The older Meta Android page says to use baked lightmaps rather than precomputed realtime GI and to light dynamic objects with light probes. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ ; https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ (legacy, undated; accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The legacy page is possibly stale, but this advice matches the 2024 page.

- **U4-009** The legacy Meta Android page recommends setting the Skybox to None and the ambient source to Color instead of the default procedural skybox. It also advises against realtime reflections and shadow buffers. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ (legacy, undated; accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Possibly stale (Gear VR era). The skybox cost is one full-screen-ish draw per eye. Measure it with RenderDoc before removing a skybox your art direction needs. See U4-C7 for the shadow-buffer advice.

- **U4-010** The URP 15.0.0 changelog lists a fix for a performance regression with additional lights on Quest. It is not clear whether the fix was backported to URP 14 (2022.3 LTS). [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: URP 14 (2022.3) versus URP 15+ · Evidence: [doc] [verify on device]
  - Notes: On 2022.3 projects with many additional lights, compare GPU time against a 6000.x build of the same scene, or check the 2022.3 patch release notes.

### Light probes, SH evaluation, Adaptive Probe Volumes

- **U4-011** Legacy light probes store L2 spherical harmonics: 27 floats, 9 per color channel. The URP docs describe Light Probe Groups as lighting each object from one interpolated probe. APV instead samples per pixel, interpolating 8 surrounding probes. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/LightProbes-TechnicalInformation.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-concept.html (accessed 2026-09-24) · Applies to: legacy probes in all versions; APV in URP 17 (Unity 6) · Evidence: [doc]
  - Notes: Per-object probes are cheap per pixel but can leak light on large objects. APV gives better quality but adds a per-pixel (or per-vertex, see U4-013) fetch cost.

- **U4-012** The Unity 6 URP Asset exposes a Light Probe System choice: Light Probe Groups (Legacy) or Adaptive Probe Volumes. APV settings include: [T][C]
  - Memory Budget (Low, Medium, High)
  - SH Bands (L1 or L2)
  - Enable Streaming
  - an "Estimated GPU Memory Cost" readout
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 17 (6000.0+); APV Lighting Scenario baking in URP arrived in 17.0.2 (6000.0.0b15) per the changelog · Evidence: [doc]
  - Notes: For 2021.3 and 2022.3 URP projects, APV is not a practical option. Plan APV only for Unity 6 projects.

- **U4-013** SH Evaluation Mode (URP 14+) offers Auto, Per Vertex, Mixed, and Per Pixel. It is an advanced property of the URP Asset. In URP source, Auto resolves to Per Vertex when the target is mobile XR or the shader API is mobile, and to Per Pixel otherwise. The URP 17.0.2 changelog says the same for mobile. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipelineCore.cs (`ShAutoDetect`, around line 2094) (accessed 2026-09-24) · Applies to: URP 14 to 17.x (absent from URP 12.1 docs) · Evidence: [doc]
  - Notes: On 2021.3 (URP 12), probe SH is evaluated with the pipeline's fixed default, with no user toggle.

- **U4-014** In URP 6000.3 source, APV vertex sampling is enabled only when the asset's SH mode is explicitly Per Vertex or Mixed. The asset getter returns the raw value, so Auto is not resolved at that call. With Auto on Quest, APV may therefore stay on per-pixel sampling even though legacy SH resolves to per-vertex. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs (`SetVertexSamplingEnabled`, line 802); https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/Data/UniversalRenderPipelineAsset.cs (`shEvalMode` getter, line 1203) (accessed 2026-09-24) · Applies to: URP 17.0 to 17.3 (checked in the 6000.0 and 6000.3 branches) · Evidence: [doc] [verify on device]
  - Notes: This is an inference from reading the source. Unity does not document it. With APV on Quest, set SH Evaluation Mode explicitly to Per Vertex (or Mixed). Confirm by checking the shader keywords in a RenderDoc or Frame Debugger capture, or by comparing GPU time between Auto and Per Vertex. See U4-C6.

- **U4-015** A Unity Discussions thread says APV per-vertex quality arrived in 2023.2 and that Mixed means per-pixel L1 plus per-vertex L2. [T]
  - Source: https://discussions.unity.com/t/urp-adaptive-probe-volumes-per-vertex-quality-setting-location/942672 (2024-03; accessed 2026-09-24) · Applies to: 2023.2 to 6000.x · Evidence: [community]

- **U4-016** In core source, the APV Memory Budget enum sets the brick-pool texture size. Low is 512, Medium is 1024, and High is 2048 texels wide and high, all with a depth of 4. The pool is allocated at that size when it is created. Per-probe storage: [C]
  - L0+L1 red: RGBA16F (8 bytes)
  - L1 green and L1 blue: RGBA8 (4 bytes each)
  - L2: four more RGBA8 textures
  - validity: R8, or RGBA8 where R8 sample/load-store is unsupported (GLES 3.x)
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/Runtime/Lighting/ProbeVolume/ProbeBrickPool.cs ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/Runtime/Lighting/ProbeVolume/ProbeReferenceVolume.cs (enum `ProbeVolumeTextureMemoryBudget`) (accessed 2026-09-24) · Applies to: URP 17.x · Evidence: [doc] [verify on device]
  - Notes: The following is derived arithmetic, not a published number:
    - Low holds about 1.05M probes: about 16 MiB at L1, 32 MiB at L2.
    - Medium: about 64 MiB at L1, 128 MiB at L2.
    - High: about 256 MiB at L1, 512 MiB at L2.

    These exclude validity, sky occlusion, and the scenario-blending pool. Trust the URP Asset's Estimated GPU Memory Cost readout, and on device use the Memory Profiler package. On Quest 2 (6 GB shared), treat Low with L1 as the starting point.

- **U4-017** APV bricks hold 4x4x4 = 64 probes. The default probe spacings across subdivision levels are 1, 3, 9, and 27 m. Probes are organized into Baking Sets and can carry multiple Lighting Scenarios. Raising the minimum probe spacing directly cuts probe count and memory. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-concept.html (accessed 2026-09-24) · Applies to: URP 17.x · Evidence: [doc]

- **U4-018** APV streaming has two layers: [C]
  - GPU streaming moves cells from CPU memory to the GPU.
  - Disk streaming moves cells from disk to CPU memory, uses StreamingAssets, and requires GPU streaming.

  The cell is the streaming unit. Projects that ship APV data through AssetBundles or Addressables can use "Probe Volume Disable Streaming Assets". Unity warns this may raise memory use.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-streaming.html (accessed 2026-09-24) · Applies to: URP 17.x · Evidence: [doc] [verify on device]
  - Notes: No published Quest data exists on streaming hitches. Watch Profiler frames during fast traversal, and check whether cell uploads appear as render-thread spikes.

- **U4-019** Lighting Scenario blending can be spread over frames: the documented sample sets `numberOfCellsBlendedPerFrame` (10 in the sample). Sky occlusion lengthens bakes and raises runtime memory. Updating the ambient probe from a skybox through DynamicGI.UpdateEnvironment is documented as having a very large performance impact. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-bakedifferentlightingsetups.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-skyocclusion.html (accessed 2026-09-24) · Applies to: URP 17.x · Evidence: [doc]
  - Notes: Blending allocates a second pool; core source has `EstimateMemoryCostForBlending`. Avoid scenario blending on Quest 2 unless you have measured it.

- **U4-020** A third-party write-up claims APV needs compute shaders and does not run on GLES. The URP source read for this report shows no GLES block. [T]
  - Source: https://gamedevllm.com/en/unity-6-urp-adaptive-probe-volumes-deep-dive-en/ (accessed 2026-09-24) · Applies to: URP 17.x · Evidence: [community] [verify on device]
  - Notes: The claim is unverified. The only GLES-specific handling found in the pool code is the validity format fallback in U4-016. Test an APV scene on a GLES 3.2 Quest build and look for magenta or unlit objects, plus warnings in logcat.

### Reflection probes

- **U4-021 / U2-013** The URP Asset exposes Probe Blending, Probe Atlas Blending, and Box Projection toggles: [T]
  - Probe Atlas Blending works only in Forward+, and becomes the default when GPU Resident Drawer is on.
  - Forward blends at most 2 probes per object; Forward+ is needed for more.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/urp/rendering-paths-comparison.html (accessed 2026-09-24) · Applies to: URP 14 to 17.x (atlas blending in 17.x) · Evidence: [doc] [verify on device]
  - Notes: No published Quest cost exists for blending or box projection. A/B each toggle and compare GPU time on a reflective material that covers the screen.
  - **Merged U2-013:** **Reflection probes**: Probe Blending and Box Projection default off. Probe Atlas Blending (Forward+ only) defaults on in 6000.5 source. Meta says to disable probe blending and the probe atlas on Quest because the atlas is too costly there. [T]
    - Source: https://developers.meta.com/horizon/documentation/unity/unity-forward-plus-rendering/ (accessed 2026-09-24) · Applies to: Forward+ on URP 14+ (in 6000.3+ built into URP; Meta branches before that) · Evidence: [doc]
    - Notes: Unity's performance page also says disable probe blending and box projection on low-end mobile (https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html). The setting was called "Probe Atlas" before 6000.3, and only in the Meta fork.

- **U4-022** Realtime reflection probes are stored uncompressed, and their memory depends on resolution and HDR. Sampling them usually costs more than sampling baked probes. Baked probe compression is set under Lighting window > Environment > Reflections > Compression. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/RefProbePerformance.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]

- **U4-023** Realtime probe Refresh Mode choices: [C]
  - Every Frame: the most expensive.
  - On Awake: renders once.
  - Via Scripting: renders on demand.

  Time Slicing choices for Every Frame:
  - All Faces at Once: finishes in 9 frames.
  - Individual Faces: finishes in 14 frames, with the lowest per-frame impact.
  - No Time Slicing: does the whole update in one frame, which can cause a hitch.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/RefProbePerformance.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: On Quest, prefer baked probes. If a probe must be realtime, use Via Scripting with Individual Faces, and use the probe's Culling Mask to render only large occluders.

- **U4-024** The HDR Cubemap Encoding Player setting (Low, Normal, or High Quality) sets the encoding and compression of HDR cubemaps, such as baked reflection probes and HDR skyboxes. It follows the same scheme as lightmap encoding. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc] [verify on device]
  - Notes: If High Quality leads to ASTC HDR and Quest lacks the extension, cubemaps may decompress to a much larger format. See U4-038 and U4-049.

### Shadows

- **U4-025** URP soft shadows have three quality levels: [T]
  - Low: 4 PCF taps, aimed at mobile.
  - Medium (default): a 5x5 tent filter.
  - High: a 7x7 tent filter.

  Unity flags soft shadows as having a high impact on untethered XR.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/shadows-optimization.html (accessed 2026-09-24) · Applies to: URP 15 to 17.x for the asset-level quality; URP 14.0.3 added per-light quality · Evidence: [doc] [verify on device]
  - Notes: No published Quest ms figure exists per quality level. Measure GPU time with soft shadows off, Low, and Medium on a scene where the shadowed area fills much of the view. See U4-C3 for the tap-count discrepancy.

- **U4-026 / U4-027 / U1-039** URP 17.0.0 disabled per-light soft shadow quality levels on Quest and HoloLens to improve XR performance. On those platforms, the URP Asset's global setting governs soft shadow quality. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/changelog/CHANGELOG.html (17.0.0 entry, 2023-09-26) (accessed 2026-09-24) · Applies to: URP 17.x (Unity 6). Behavior on URP 14/15 depends on backports. · Evidence: [doc]
  - Notes: See U4-C5, where the manual still describes per-light overrides.
  - **Merged U4-027:** A Unity graphics staff member gave the history of Quest soft-shadow handling: [T]
    - 2020 forced low shadow quality on Quest.
    - 2021 moved to per-light control, which regressed performance.
    - A later fix makes Quest ignore the per-light setting.

    The original poster's blocky shadows turned out to be cascade and distance misconfiguration, not quality level.
    - Source: https://discussions.unity.com/t/meta-quest-shadows-unsmoothed-low-resolution-regardless-of-settings/1552250 (2024-11-12; accessed 2026-09-24) · Applies to: 2020.3 to 6000.x · Evidence: [community]
  - **Merged U1-039:** Per-light Soft Shadow Quality is disabled on Quest (6000.0.0b11, UUM-33025). Soft-shadow settings authored per light on PC do not carry over to Quest. [C]
    - Source: https://unity.com/releases/editor/whats-new/6000.0.0b11 (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]

- **U4-028** Each extra shadow cascade costs performance. Max Distance, cascade splits, and Last Border control how shadow-map texels are spread. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 12 to 17.x · Evidence: [doc]
  - Notes: The Meta and Unity XR pages do not publish a cascade count for Quest. A starting point to verify is 1 cascade with a short Max Distance (see U4-029).

- **U4-029** Unity's shadow-resolution page gives a worked example with a single cascade. Cutting Max Distance from 40 to 10 lets a 1024 shadow map replace a 2048 one and still improves near-field quality. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/shadow-resolution-urp.html (accessed 2026-09-24) · Applies to: URP 12 to 17.x · Evidence: [doc]
  - Notes: Halving resolution quarters the texel count, and so the shadow-map bandwidth and memory.

- **U4-030** A 1024 x 1024 additional-light shadow atlas holds up to 16 maps at 256 x 256; a 512 atlas holds only 4. Each spot light needs 1 map and each point light needs 6. Unity's example: 4 shadowed spot lights plus 1 point light need 10 maps at 256, which fit in a 1024 atlas but not a 512. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/shadow-resolution-urp.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 12 to 17.x · Evidence: [doc]
  - Spot-check (gap-fill round 2): reworded. The earlier text ("packs up to 16 maps") read like a global cap. The page gives 16 only as the capacity of a 1024 atlas at 256 per map. "4 maps at 512 in a 1024 atlas" is arithmetic, not a quote. The 6-maps-per-point-light figure is from the page.

- **U4-031** A shadowed point light renders 6 shadow maps, which costs about as much as 6 spot lights. Unity advises reducing or avoiding shadowed point lights on mobile. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/shadows-optimization.html (accessed 2026-09-24) · Applies to: all URP versions · Evidence: [doc]

- **U4-032** Unity's other shadow levers: [T]
  - Toggle lights with Light.enabled and fade intensity for transitions.
  - Use light cookies instead of realtime shadows.
  - Set Cast Shadows to Off on renderers that don't need them.
  - Cast shadows from a simplified mesh set to "Shadows Only".
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/shadows-optimization.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]

- **U4-033** The URP Asset's Conservative Enclosing Sphere option tightens cascade culling spheres. Unity says it likely improves performance. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 15+ (option present in 17.x docs) · Evidence: [doc] [verify on device]
  - Notes: Enabling it can change cascade coverage, so re-tune the cascade splits.

- **U4-034** Meta's 2024 best practices say to disable shadows when a scene nears its draw-call or geometry limits. Meta's 2018 tech note recommended Hard Shadows Only or no shadows, with blob shadows for characters. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ ; https://developers.meta.com/horizon/blog/tech-note-unity-settings-for-mobile-vr/ (2018-04-12; accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The 2018 note is possibly stale because it predates URP. Shadow casting adds a depth-only pass with its own draw calls, so it compounds any draw-call budget problem.

### Lightmaps: encoding, compression, directional mode, shadowmask memory

- **U4-035** Player > Other Settings > Lightmap Encoding offers three levels: [T][C]
  - Low: dLDR on mobile.
  - Normal: RGBM.
  - High: HDR.

  On Android with ASTC as the compression target, dLDR and RGBM lightmaps use ASTC at 3.56 bpp (6x6 blocks), and HDR uses ASTC HDR at 3.56 bpp. With an ETC2 target, dLDR uses ETC2 RGB at 4 bpp and RGBM uses ETC2 RGBA at 8 bpp. HDR stays ASTC HDR under ETC2 and ETC targets too.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-TechnicalInformation.html ; the same table appears in the 2021.3, 2022.3, 6000.0, and 6000.6 versions of this page (accessed 2026-09-24) · Applies to: 2021.3 to 6000.6 · Evidence: [doc]
  - Notes: The format also depends on the Build Profile compression override (U4-045).

- **U4-036** dLDR maps the range [0, 2] and clamps anything brighter. Its linear-space decode factor is 4.59482. RGBM covers 0 to 34.49 in linear space. Unity notes that some platforms use dLDR because their hardware compression gives RGBM visible artifacts. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-TechnicalInformation.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: The bitrate is the same on ASTC. Pick dLDR or RGBM for quality: bright baked lights clip in dLDR, and RGBM can band. Decode cost differs by a few ALU ops per pixel, and no published number measures it.

- **U4-037** Precomputed realtime GI (Enlighten) writes its irradiance output as RGB9E5 where the hardware supports it, falling back to RGBM. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-TechnicalInformation.html (accessed 2026-09-24) · Applies to: versions that ship Enlighten realtime GI · Evidence: [doc]
  - Notes: Meta advises against realtime GI on Quest (U4-008). This finding documents the memory format if a project uses it anyway.

- **U4-038** High Quality (HDR) lightmaps on Android rely on ASTC HDR. When a GPU lacks the ASTC HDR extension, Unity decompresses ASTC HDR at load, to RGB9E5 (alpha dropped) or to RGBA Half. That multiplies memory and adds load-time CPU work. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/texture-formats-reference.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-TechnicalInformation.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc] [verify on device]
  - Notes: No source found confirms whether Quest 2 (Adreno 650) or Quest 3 (Adreno 740) exposes ASTC HDR. Check on device with `SystemInfo.SupportsTextureFormat(TextureFormat.ASTC_HDR_6x6)`, or run `vulkaninfo` over adb and look for `textureCompressionASTC_HDR`. Until that is confirmed, use Normal (RGBM) or Low (dLDR) on Quest.

- **U4-039** Directional Mode defaults to Directional. It stores a second texture, costing about twice the video memory, and the shader samples both. Non-Directional uses one texture, less memory, and a cheaper decode. The legacy Meta Android page recommends Non-Directional. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-reference.html ; https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ (legacy) (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: See U4-C2. On normal-mapped surfaces, Directional keeps baked normal-map response. Decide per project, and measure both the memory delta and the GPU delta.

- **U4-040** Max Lightmap Size defaults to 1024. Doubling Lightmap Resolution quadruples texel count. The Lighting window's statistics report lightmap Memory Usage and Occupied Texels, which gives a baked-memory estimate before building. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-reference.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]

- **U4-041** Lightmap Compression has four settings: None, Low, Normal, and High Quality. With Fixed Lightmap Size, every atlas is the Max Lightmap Size. Repack Underused Lightmaps shrinks sparse atlases. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-reference.html (accessed 2026-09-24) · Applies to: 6000.x (setting names vary on 2021.3 and 2022.3) · Evidence: [doc]
  - Notes: Fixed Lightmap Size costs memory. It is recommended with GPU Resident Drawer (U4-044).

- **U4-042** Block Aligned Padding (XAtlas packing) aligns UV charts to a 4x4 texel grid to reduce block-compression artifacts. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-reference.html (accessed 2026-09-24) · Applies to: 6000.x · Evidence: [doc] [verify on device]
  - Notes: Android lightmaps use ASTC 6x6 blocks (U4-035), which do not line up with a 4x4 grid. The benefit on Quest is unverified. Inspect chart seams on device with and without the option.

- **U4-043** In Shadowmask mode, Unity bakes an extra shadowmask texture per lightmap. It uses the same UV layout and resolution as the lightmap and stores up to 4 lights in its RGBA channels. A Shadowmask scene therefore adds another lightmap-sized texture per atlas, on top of color, plus direction if Directional. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/lighting-mode.html ; https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-Shadowmask.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc] [verify on device]
  - Notes: The doc sources read here don't give the shadowmask texture's compression format on Android. Check it in the Memory Profiler or by inspecting the baked asset's import settings.

- **U4-045** Android Player settings include Lightmap Streaming, which requires Mipmap Streaming, and a lightmap Streaming Priority from -128 to 127. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc] [verify on device]
  - Notes: A streamed lightmap that is still at a low mip shows as blurry baked lighting. Check whether lightmaps are resident at full resolution with `Texture2D.loadedMipmapLevel` on the lightmap textures.

## 8. CPU and scripting

### Managed runtime, CoreCLR and garbage collection

- **U1-072** Other 6.6 scripting changes: domain reload is off by default, and the IL2CPP converter was rebuilt on NativeAOT. Code that relies on static state being reset on entering Play Mode behaves differently in Editor profiling sessions. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]
  - Notes: The NativeAOT rebuild affects the build-time converter. No runtime codegen difference on Quest has been published. [verify on device]

- **U5-001 / U1-071** On Quest, every Unity version in range (2021.3–6.6) runs C# through IL2CPP with the Boehm-based GC. CoreCLR is not a Quest option in 2026. The 6.7 CoreCLR back end is experimental, desktop-only (Windows/macOS/Linux player), and explicitly not production-ready. Plan GC work around IL2CPP/Boehm, not a generational GC. [T][C]
  - Source: https://docs.unity3d.com/6000.7/Documentation/Manual/scripting-backends-coreclr.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6.6 (and 6.7 beta) · Evidence: [doc]
  - Notes: The CoreCLR back end uses JIT with tiered compilation and a generational GC; the Editor still embeds Mono. None of that reaches Android.
  - **Merged U1-071:** CoreCLR is not on the Quest path in this version range. 6000.7.0a2 adds experimental CoreCLR players for Windows, macOS and Linux only, and 6000.7.0a4 bundles .NET 10. The roadmap from Unite 2025 puts an experimental desktop CoreCLR player in 6.7, then a CoreCLR Editor. No Android timeline was found, so Quest players stay on IL2CPP through 6.7. [C]
    - Source: https://unity.com/releases/editor/whats-new/6000.7.0a2 ; https://www.digitalproduction.com/2025/11/26/unitys-2026-roadmap-coreclr-verified-packages-fewer-surprises/ (Unite 2025 report, 2025-11-26) (accessed 2026-09-24) · Applies to: 6.7 beta · Evidence: [doc]
    - Notes: 6.6 adds CoreCLR deep profiling and GC.Alloc support in the Editor and warns that Mono and domain reload will be removed.

- **U5-002** Unity's roadmap has three steps:
  - 6.7 LTS: last Mono-based release.
  - Unity 7.0 (developed as the 6.8 alpha): removes Mono, moves to .NET 10 / C# 14.
  - CoreCLR performance optimization: deferred to the LTS after 7.0 (2027).

  The March 2026 upgrade guide says IL2CPP stays on .NET Standard 2.1 / C# 9 for now. A Unity engineer (joncham, 2026-03-27) says the Boehm GC used by IL2CPP does not change. [T][C]
  - Source: https://discussions.unity.com/t/coreclr-scripting-and-serialization-update-june-2026/1723299 (accessed 2026-09-24); https://discussions.unity.com/t/path-to-coreclr-2026-upgrade-guide/1714279 (accessed 2026-09-24) · Applies to: roadmap; Quest players unaffected through 6.6 · Evidence: [doc] (official Unity staff posts on Unity Discussions)
  - Notes: The 85 KB large-object-heap threshold in the guide applies only to CoreCLR; do not apply it to IL2CPP. The prep items ([AutoStaticsCleanup], [BeforeCodeUnloading], Project Auditor 2.0.0+) matter for domain-reload correctness, not device performance.

- **U5-003** The managed heap grows on demand and is not compacted:
  - A large allocation that doesn't fit in contiguous free space first triggers a GC.
  - If it still doesn't fit, the heap expands; on most platforms each expansion doubles the previous one.
  - Unity keeps expanded heap memory and returns empty pages to the OS only at an unreliable interval.

  Fragmentation from mixed-lifetime allocations therefore causes permanent heap growth and more frequent GCs. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/performance-managed-memory-introduction.html (accessed 2026-09-24) · Applies to: all versions (IL2CPP) · Evidence: [doc]
  - Notes: Allocate long-lived buffers at load time, before gameplay allocations interleave.

- **U5-004** Unity's target is 0 bytes of managed allocation per frame in steady state. The GC overview gives an example: 1 KB/frame at 60 fps is 3.6 MB of garbage per minute. The profiler-markers reference says a GC.Collect can take from under 1 ms to hundreds of ms. At a 90 Hz budget of 11.1 ms, one full collection can drop several frames. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/performance-garbage-collector.html (accessed 2026-09-24); https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: No published Quest-specific GC pause numbers were found. Measure the `GC.Collect` marker duration against heap size on device (Profiler Timeline, or `ProfilerRecorder` on "GC Reserved Memory").

- **U5-005 / U4-097** Incremental GC (the default) splits marking across frames and adds write barriers, so every reference write costs a little more. If marking cannot converge because references change too fast, it falls back to a full stop-the-world collection. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/performance-incremental-garbage-collection.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: The toggle is Player > Other Settings > Configuration > Use incremental GC.
  - **Merged U4-097:** Incremental GC is on by default. It spreads collection over frames, and with VSync or `targetFrameRate` set it uses the idle time left at the end of each frame. Heavy reference churn can prevent incremental marking from finishing, and Unity then falls back to a full stop-the-world collection. `GarbageCollector.GCMode` can disable GC during critical sections. Unity's pattern for levels is to disable GC during the level and run `System.GC.Collect` between levels. [C]
    - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/performance-incremental-garbage-collection.html (accessed 2026-09-24) · Applies to: 2019.1+ through 6000.x (the web platform excluded) · Evidence: [doc]
    - Notes: During loading, per-frame allocation spikes, such as JSON parsing or instantiation, can trip the full-collection fallback. On Quest, where the XR runtime paces frames, check whether the idle-time heuristic sees usable slack. Look for `GC.Collect` / `GC.MarkDependencies` markers and compare them with frame time. General GC tuning belongs to the scripting/GC topic.

- **U5-006** Unity's GC configuration page says disabling incremental GC can save "as much as 1 ms per frame" in CPU-bound projects, because it removes write-barrier overhead. It recommends A/B testing with Profile Analyzer. That 1 ms is 7–12% of a 72–120 Hz budget. Only trade it away if allocations are already near zero. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/performance-disabling-garbage-collection.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: No Quest-specific measurement found. [verify on device]: compare PlayerLoop median and p99 over 2+ minutes of identical gameplay with each setting.

- **U5-007** `GarbageCollector.incrementalTimeSliceNanoseconds` defaults to 3,000,000 ns (3 ms). That is 22% of a 72 Hz budget, 27% at 90 Hz and 36% at 120 Hz. The slice is a guideline, not a hard cap, and memory pressure can still force a full collection. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Scripting.GarbageCollector-incrementalTimeSliceNanoseconds.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: There is no published recommended value for Quest. Treat it as a tuning knob: lower it when the main thread is the long pole, and confirm that GC work doesn't then accumulate into full collections.
  - Spot-check (gap-fill round 2): confirmed ("3 ms (3000000 nanoseconds)"), with a caveat added from the page. The GC uses the platform timer, which "can have a resolution as low as a whole millisecond", so sub-millisecond tuning may do nothing. Tune in whole-millisecond steps (for example 1 ms or 2 ms).

- **U5-008** Unity uses leftover end-of-frame time for incremental GC only when `QualitySettings.vSyncCount` is not "Don't Sync" or `Application.targetFrameRate` is set. In VR, Unity documents that both are ignored and the XR SDK controls the frame rate. Unity does not document whether incremental GC uses the time the main thread spends blocked in the XR frame wait. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/performance-incremental-garbage-collection.html (accessed 2026-09-24); https://docs.unity3d.com/6000.6/Documentation/ScriptReference/QualitySettings-vSyncCount.html (accessed 2026-09-24) · Applies to: all versions, XR · Evidence: [doc]
  - Notes: [verify on device]. Look for incremental GC samples in Timeline; if they sit inside the frame rather than in the wait, assume no idle-time scheduling. See Conflict U5-C3.

- **U5-009** Manual GC control uses `GarbageCollector.GCMode` (Enabled / Disabled / Manual) plus `GarbageCollector.CollectIncremental(ulong nanoseconds)`, which returns true while work remains; the default of 0 does nothing.
  - Unity's example runs an incremental collection once 8 MB has been allocated and a full collection above 128 MB.
  - GCMode is not supported in the Editor; test on device.
  - Pattern: disable the GC during a combat or level section, then collect at a loading screen or fade.

  [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Scripting.GarbageCollector.GCMode.html (accessed 2026-09-24); https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Scripting.GarbageCollector.CollectIncremental.html (accessed 2026-09-24) · Applies to: 2019.x+ (all versions in range) · Evidence: [doc]
  - Notes: While disabled, the heap only grows (U5-003). On 6 GB (Quest 2) and 8 GB (Quest 3/3S) devices, OS memory limits are a separate topic. No published safe heap ceiling for Quest was found. Watch "GC Reserved Memory" with ProfilerRecorder.

- **U5-010** Common hidden allocation sources in Unity C#:
  - string concatenation and formatting
  - lambdas and closures capturing locals, and method-group-to-delegate conversions
  - boxing (shows in allocation call stacks as `Box`/`_Box` frames)
  - `params` arrays
  - Unity APIs that return new arrays each call (`mesh.vertices`, `Input.touches`, `Animator.parameters`, `Renderer.sharedMaterials`)

  [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/performance-reference-types.html (accessed 2026-09-24); https://docs.unity3d.com/6000.3/Documentation/Manual/performance-optimizing-arrays.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Non-allocating substitutes:
    - `Mesh.GetVertices(List<Vector3>)`
    - `Animator.parameterCount` + `GetParameter(i)`
    - `Renderer.GetSharedMaterials(List<Material>)`
    - `Physics.RaycastNonAlloc`
    - a cached static zero-length array instead of `new T[0]`

- **U5-011** Unity's GC is conservative and scans pointer-sized fields, so large managed arrays of plain data add scan work and false retention. Unity recommends `NativeArray<T>` (unmanaged memory) for large data buffers. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/performance-optimizing-arrays.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: NativeArray memory shows under the `UnsafeUtility.Malloc` marker and counters, not GC.Alloc. Dispose it explicitly.

- **U5-012** To find allocation sites without Deep Profiling, turn on Call Stacks mode in the CPU Profiler module. GC.Alloc samples (magenta in Timeline) then carry full call stacks. Check non-main threads with the thread selector too. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/performance-track-garbage-collection.html (accessed 2026-09-24) · Applies to: 2019.3+ (all versions in range) · Evidence: [doc]
  - Notes: Deep Profiling on device is slow and can run out of memory (U5-085).

- **U5-013** Resolving stack traces for log messages is expensive, and Full (managed + native) is the most expensive. Unity advises against shipping with stack traces enabled and suggests limiting them to exceptions/warnings. Set Player > Other Settings > Stack Trace to None (or ScriptOnly only for Exception) for Log/Warning in release builds, or call `Application.SetStackTraceLogType`. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/stack-trace.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The default is ScriptOnly for all log types. Per-frame `Debug.Log` in a shipping build pays string formatting (GC.Alloc) plus stack-trace resolution. No Quest number published.

- **U5-014** TextMesh Pro `SetText()` is the allocation-conscious update path: it accepts StringBuilder, formatted numeric arguments and char[]. Unity 6.6 adds `ReadOnlySpan<char>` input, so text can be updated from stack or pooled buffers without creating strings. Use it for per-frame counters such as timers and ammo. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: SetText overloads in all versions; the span overload in 6.6+ · Evidence: [doc]
  - Notes: Assigning `.text = someInt.ToString()` allocates every time it is called.

### Animation and skinning

- **U5-065** `DirectorUpdateAnimationBegin` processes every active Animator regardless of culling. It covers:
  - `Animators.PrepareFirstPass`
  - `Animators.ProcessGraphJob` / `Animator.ProcessGraph`
  - `Animators.FireAnimationEventsAndBehaviours`
  - `Animators.ApplyOnAnimatorMove`

  StateMachineBehaviours that implement OnStateMachineEnter/Exit force that work onto the main thread. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Avoid OnStateMachineEnter/Exit in StateMachineBehaviours on crowds.

- **U5-066** `DirectorUpdateAnimationEnd` handles only visible or Always Animate Animators. It covers:
  - `Animators.PrepareSecondPass`
  - `Animators.SortWriteJob`
  - `Animators.ProcessAnimationsJob`
  - `OnAnimatorIK`
  - `Animators.WriteJob` / `WriteTransforms`
  - `Animator.WriteProperties`

  Multiple Animators in one hierarchy make SortWriteJob expensive. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Flatten nested Animators, for example a prop Animator under a character Animator.

- **U5-067** Culling Mode:
  - Always Animate: never culls.
  - Cull Update Transforms: skips retargeting, IK and transform writes when renderers are invisible.
  - Cull Completely: stops animation while invisible.

  Unity recommends Cull Completely and turning off SkinnedMeshRenderer "Update When Offscreen". [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-Animator.html (accessed 2026-09-24); https://docs.unity3d.com/6000.3/Documentation/Manual/MecanimPeformanceandOptimization.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: It is not documented whether shadow-caster visibility counts as visible in stereo/single-pass XR. [verify on device]: turn away from a culled character and watch whether DirectorUpdateAnimationEnd time drops.

- **U5-068** Rig import **Optimize Game Objects** makes Unity skip Transforms not mapped in the Avatar and use its internal skeleton, which Unity says improves CPU performance. Expose only needed bones via "Extra Transforms to Expose". Skin Weights "Standard (4 Bones)" is the default and the recommended setting for performance. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/FBXImporter-Rig.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The option is available only when the Avatar Definition is Create From This Model.

- **U5-069** Mecanim authoring costs from Unity's performance page:
  - Scale curves cost more than translation/rotation curves; constant curves are optimized.
  - A layer with zero weight is skipped.
  - Use Avatar Masks to drop IK goals and fingers on Humanoid clips.
  - Generic root motion costs more; don't set a root bone if unused.
  - One clip with no blending can be slower in Animator than in the legacy Animation component.
  - An Animator with no Controller costs nothing.

  [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/MecanimPeformanceandOptimization.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: For simple looping props (fans, doors), the legacy `Animation` component or a script is cheaper than Mecanim.

- **U5-070** The Profiler warns on `Animation.AddClip`, `RemoveClip` and similar calls. These trigger `RebuildInternalState` and can hitch. `Animator.parameters` allocates on every call. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html (accessed 2026-09-24); https://docs.unity3d.com/6000.3/Documentation/Manual/performance-optimizing-arrays.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Set up clips at load time.

### IL2CPP and Player settings

- **U5-015** C++ Compiler Configuration has three levels:
  - Debug: no optimization; quick to build, slow to run.
  - Release: optimizations on, smaller binary, longer compile.
  - Master: every optimization. Unity's example is link-time code generation on MSVC platforms.

  Unity recommends Master for shipping builds when the extra build time is acceptable. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: The page does not say which configuration is the default, or what Master adds on the Android clang toolchain. No published Quest numbers for the Master vs Release delta. [verify on device]: build both from the same commit and compare CPU Main Thread median/p99 with ProfilerRecorder in non-development builds.

- **U5-016** IL2CPP Code Generation has two options, named differently by version. The runtime-speed option is the default; keep it for shipping. In the 2021.3/2022.3 manual, the default produces more machine code to reduce IL2CPP's runtime overhead. The build-size option emits less machine code, which can reduce runtime performance but significantly cuts build time. [T]

  | Unity | Runtime-speed option (default) | Size/build-time option |
  |---|---|---|
  | 2021.3, 2022.3 (Build Settings) | Faster runtime | Faster (smaller) builds |
  | 6.x (Player settings) | Optimize for runtime speed | Optimize for code size and build time |
  - Source: https://docs.unity3d.com/2021.3/Documentation/Manual/IL2CPP.html (accessed 2026-09-24); https://docs.unity3d.com/2022.3/Documentation/Manual/IL2CPP.html (accessed 2026-09-24); https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: No published runtime cost numbers for Quest. If CI uses the size option for iteration speed, make sure release builds switch back.

- **U5-017** `[Il2CppSetOption(Option.NullChecks, false)]` and `Option.ArrayBoundsChecks, false` remove IL2CPP's emitted null and bounds checks. Both default to enabled; DivideByZeroChecks defaults to disabled.
  - The attribute applies at assembly, type, method or property scope.
  - Copy `Il2CppSetOptionAttribute.cs` from the Editor's `Data/il2cpp` folder into the project.
  - Use it only on profiled hot loops that are known to be safe.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/il2cpp-runtime-checks.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Without the checks, a null or out-of-range access becomes a native crash instead of a managed exception. Burst-compiled code avoids this question entirely.

- **U5-018 / U1-030** Unity 6.6 adds **Managed Code Variant** (Player setting; `PlayerSettings.SetManagedCodeVariant`) and deprecates the `UNITY_64` / `DEVELOPMENT_BUILD` defines. Each variant includes the defines of the variants below it:

  | Variant | Optimized | Defines |
  |---|---|---|
  | Debug | no | `DEBUG` + all Checked defines |
  | Checked | yes | `UNITY_ENABLE_CHECKS`, `UNITY_ASSERTIONS` + all Instrumented defines |
  | Instrumented | yes | `UNITY_INCLUDE_INSTRUMENTATION`, `ENABLE_PROFILER` |
  | Release (default) | yes | none |

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24); https://discussions.unity.com/t/unity-64-and-development-build-deprecation-and-managed-code-variants/1721546 (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc] (manual; staff post by Tautvydas-Zilys, 2026-05-30)
  - Notes: The setting is separate from the Development Build checkbox. Inference to [verify on device]: `ProfilerMarker.Begin/End` are `[Conditional]` (U5-079). User markers may therefore compile out when the variant is Release, even in a Development Build. Select Instrumented when profiling custom markers on 6.6.
  - **Merged U1-030:** In 6.6, the default Managed Code Variant is Release. With Release, Development Builds no longer include the Render Graph Viewer connection, render-graph validation, RG profiling samplers or `ScriptableRenderPass.profilingSampler`. To keep them, choose the Checked or Instrumented variant (`UNITY_ENABLE_CHECKS` / `UNITY_INCLUDE_INSTRUMENTATION`). [C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]
    - Notes: Upgrade trap: on-device RG inspection that worked in 6.3–6.5 disappears after moving to 6.6 until the variant is changed. Profile markers also disappear from Development Builds. Also, the `UNITY_64` and `DEVELOPMENT_BUILD` defines are deprecated and will be removed in 6.8.

- **U5-019** Unity 6.6 adds Build Settings > Code Optimization modes "Maximum Size Reduction" and "Maximum Size Reduction with LTO". These are size-oriented. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]
  - Notes: No published runtime-speed impact. Assume the runtime-speed modes are preferable for CPU-bound Quest titles until measured. Managed Stripping Level and Strip Engine Code (IL2CPP only) also mainly reduce size. No published per-frame CPU effect was found for them, so treat them as build-size levers.

- **U5-020** Script Call Optimization ("Fast but no Exceptions") is documented only in the iOS/tvOS Player settings, not Android. It is not a Quest lever. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsiOS.html (accessed 2026-09-24); https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: Checked by searching both pages: the phrase appears in the iOS page and is absent from the 2021.3 and 6.6 Android pages.

- **U5-021** Target Architectures: ship ARM64 only (it requires IL2CPP). "Enable Armv9 Security Features for Arm64" adds pointer authentication (PAC) and branch target identification (BTI); Burst honors the setting. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: ARM64 security option in recent 6.x; ARM64 target in all versions · Evidence: [doc]
  - Notes: No published CPU cost of PAC/BTI on Quest; it would apply only to Armv9 cores (Quest 3/3S). [verify on device]. Leave it off unless you need it for security.

- **U5-022** In VR, `QualitySettings.vSyncCount` and `Application.targetFrameRate` are ignored; the XR SDK and display refresh rate control frame rate. Frame-rate caps written for flat Android builds do nothing on Quest. Select the refresh rate through the XR/Meta display APIs instead. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/ScriptReference/QualitySettings-vSyncCount.html (accessed 2026-09-24) · Applies to: all versions, XR · Evidence: [doc]
  - Notes: This interacts with incremental GC idle-time scheduling (U5-008).

- **U5-023** Optimized Frame Pacing (Android Swappy) is described only generically: it spreads frames more evenly to reduce frame-time variance. Unity documents nothing about its behavior under an OpenXR/Meta compositor that already paces frames. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: See U5-024 and Conflict U5-C5. Default recommendation until measured: leave it off for XR builds and let the XR runtime pace frames. [verify on device]: compare stale-frame counts in OVR Metrics Tool with it on and off.

- **U5-024** Community reports on Optimized Frame Pacing with Quest are mixed:
  - One developer reported no issues (Jan 2022).
  - Another raised latency concerns.
  - ckohlmeyer (Unity 2021.3.10f1, Nov 2022) reported intermittent hitches, and that it does not track runtime refresh-rate changes.
  - A Google Cardboard SDK issue (#245) describes Swappy blocking the render thread and causing pose jumps with a Cardboard XR plugin.

  No Unity staff answer. [C]
  - Source: https://discussions.unity.com/t/optimized-frame-pacing-for-oculus-quest-2-and-other-android-headsets/860072 (accessed 2026-09-24) · Applies to: 2020.3–2021.3 era reports · Evidence: [community]
  - Notes: The reports are stale; current behavior is unverified.

- **U5-025** Vulkan Player settings:
  - "Number of swapchain buffers" defaults to 3, and the doc says not to use this setting on Android.
  - "Get swapchain image late as possible" adds an extra blit through a staging image.

  In OpenXR/Meta XR, the runtime owns the eye-buffer swapchains. These settings probably affect only the non-XR backbuffer (for example the mirror). [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: all versions (Vulkan) · Evidence: [doc]
  - Notes: The XR interaction is inferred, not documented. [verify on device]. Leave the defaults.

- **U5-026** Application Entry Point: GameActivity is the default for new Unity 6 projects. With GameActivity:
  - The player loop runs on a native thread, so plugins that rely on Java thread-local state (for example `Looper.myLooper()`) fail.
  - Frame callbacks use the NDK Choreographer.
  - Unity 6.0 ships GameActivity library 4.4.2, 6.2 ships 3.0.5, and 6.3+ ships 4.4.0.

  OpenXR plugin 1.16.0-pre.2 (2025-09-26) added a Meta Quest validation rule requiring GameActivity on Unity 6.0+. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/android-application-entries-game-activity-requirements.html (accessed 2026-09-24); https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: Unity 6.0+ (GameActivity); 2021.3/2022.3 use Activity · Evidence: [doc]
  - Notes: No published Quest CPU or frame-pacing difference between Activity and GameActivity. The practical risk is plugin thread assumptions, not throughput. OpenXR 1.8.1 fixed a Unity 2023 crash caused by using Activity instead of GameActivity.

- **U5-027** The "Frame Timing Stats" Player setting (Rendering) must be on for FrameTimingManager data in non-development builds. Dynamic Resolution cannot use frame-timing data when it is off. "OpenGL: Profiler GPU Recorders" is optional only on GLES; other APIs always have it on. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: FrameTimingManager's XR limits are covered in U5-090.

- **U5-028** "Sustained Performance Mode" (Android Player setting) wraps the Android Sustained Performance API. It trades peak performance for consistency. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: No Meta documentation says whether Horizon OS honors it. On Quest, clock control is documented through CPU/GPU levels and the performance-level hints. Do not rely on this toggle; see Leads.

### Burst, Jobs, Graphics Jobs and multithreaded rendering

- **U5-029** Burst compile targets for 64-bit Arm Android:
  - `ARMV8A`
  - `ARMV8A_HALFFP` (adds fullfp16, dotprod, crypto, crc, rdm, lse; Cortex-A75/A55 and later)
  - `ARMV9A` (SVE2; experimental)

  Burst dispatches the best compiled variant at runtime on 64-bit Arm Android and builds with the NDK from Unity Hub. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-projects.html (accessed 2026-09-24) · Applies to: Burst 1.8.x · Evidence: [doc]
  - Notes: XR2 Gen 1 and Gen 2 should both qualify for the HALFFP tier. [verify on device] with `/proc/cpuinfo` feature flags (asimdhp, asimddp, sve2).

- **U5-030** Burst versions by Unity version:

  | Unity | Newest Burst |
  |---|---|
  | 6000.0+ | 1.8.30 (published 2026-07-21) |
  | 2022.3 | 1.8.29 |
  | 2021.3 | 1.8.26 |

  In 6.6, Burst becomes a built-in module. [T]
  - Source: https://packages.unity.com/com.unity.burst (registry metadata, accessed 2026-09-24); https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: On 6.6, check that the built-in module and any explicit package pin don't conflict.

- **U5-031** Burst float settings:
  - `FloatMode.Default` is Strict.
  - `FloatMode.Fast` allows reordering and FMUL+FADD → FMLA fusion.
  - `FloatPrecision`: Standard/Medium = 3.5 ulp, High = 1.0 ulp, Low = 350 ulp (applies to sin/cos/exp/log/pow/fmod).
  - `FloatMode.Deterministic` is 64-bit-only and flushes denormals.

  For visual-only math such as particles, procedural animation and culling, `[BurstCompile(FloatPrecision.Medium, FloatMode.Fast)]` or Low precision reduces instruction count. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstcompile.html (accessed 2026-09-24) · Applies to: Burst 1.8.x · Evidence: [doc]
  - Notes: No Quest speedup numbers are published. Check the output in the Burst Inspector (look for `fmla`) and time the job on device.

- **U5-032** `JobsUtility.JobWorkerCount` defaults to `JobWorkerMaximumCount`. The job system never creates more worker threads than logical cores. On Android, Unity adjusts the worker count at runtime when available cores change. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerCount.html (accessed 2026-09-24) · Applies to: 2019.3+ (all versions in range) · Evidence: [doc]
  - Notes: No published default worker count for Quest 2/3/3S. [verify on device]: log `JobsUtility.JobWorkerMaximumCount`, `JobWorkerCount` and `SystemInfo.processorCount` at startup on each headset.

- **U5-033** Android thread configuration:
  - Unity classes a core as "big" when its capacity is at least 2x the slowest core's.
  - Command-line arguments set the priority (-20..19) and affinity (any/little/big/hex mask) of the main thread, job workers and graphics-device worker, plus the worker count:
    - `-platform-android-unitymain-priority` / `-affinity`
    - `-platform-android-jobworker-priority` / `-affinity`
    - `-platform-android-gfxdeviceworker-priority` / `-affinity`
    - `-job-worker-count`
    - `-platform-android-cpucapacity-threshold [0-1024]`
  - Unity advises keeping the defaults unless profiling shows a problem.

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/android-thread-configuration.html (accessed 2026-09-24) · Applies to: 6.x (page present in 6.6; availability in 2021.3/2022.3 unverified) · Evidence: [doc]
  - Notes: To pass arguments for testing: `adb shell am start -n "<pkg>/com.unity3d.player.UnityPlayerActivity" -e unity "-job-worker-count 2"`. For shipping, override `updateUnityCommandLineArguments(String)` in a custom activity (https://docs.unity3d.com/6000.6/Documentation/Manual/android-custom-activity-command-line.html). With GameActivity the activity class name differs.

- **U5-034** Community reports on Quest thread counts:
  - TheGamedev.Guru (2019, Quest 1): Unity spawned 4 job workers while the OS reserves cores; suggested workers = available cores − 1.
  - A 2021 Unity forum thread calls Quest 2 a "3-core device" for apps; one summary claims Unity creates main + render + 2 job threads there.

  None of these include measurements on current OS versions. [T][C]
  - Source: https://thegamedev.guru/unity-performance/job-system-excessive-multithreading/ (accessed 2026-09-24); https://discussions.unity.com/threads/vulkan-bug-quest-2-urp-graphics-jobs-no-multithreaded-rendering-slow.1208908/ (accessed 2026-09-24) · Applies to: Quest 1/2, old OS versions · Evidence: [community]
  - Notes: Stale. See Conflict U5-C6. [verify on device]: capture a Perfetto trace, count Unity worker threads, and check which cores they run on.

- **U5-035** Meta's "Graphics Jobs in Unity" page (updated 2024-11-11):
  - Legacy Graphics Jobs with Multithreaded Rendering gave up to 2 FPS in major projects (Meta's test, no methodology).
  - The mode is available from 2022.3.35f1 and in Unity 6; try it when main-thread-bound.
  - On 2022.3.35f1+, the mode cannot be set in the UI. Use an editor script:

    ```
    PlayerSettings.graphicsJobs = true;
    PlayerSettings.graphicsJobMode = GraphicsJobMode.Legacy;
    ```

  [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ (accessed 2026-09-24) · Applies to: 2022.3.35f1+, Unity 6.x · Evidence: [doc]
  - Notes: The "2 FPS" figure has no baseline frame rate, so treat it as directional.

- **U5-036** The Meta XR Core SDK Project Setup Tool rule for Graphics Jobs reversed between versions:
  - v68.0.2: "Disable Graphics Jobs" (Recommended).
  - v78.0.0 and v83.0.0: behind `#if UNITY_GRAPHICS_JOB_FIX` (asmdef versionDefine for Unity ≥ 2022.3.35f1), the rule says to enable Legacy Graphics Jobs, which can help main-thread-bound apps.

  [T]
  - Source: Meta XR Core SDK `Editor/ProjectSetupTool/OVRProjectSetupRenderingTasks.cs` read from GitHub mirrors of the UPM package (https://github.com/icosa-mirror/com.meta.xr.sdk.core) (accessed 2026-09-24) · Applies to: SDK v68 vs v78+ · Evidence: [doc] (Meta source)
  - Notes: The current Meta XR Core SDK on Meta's registry is 207.0.0 (published 2026-09-24), which was not read. Check its Project Setup Tool output. See Conflict U5-C1.

- **U5-037** Unity 6.6 has three Graphics Jobs modes, Vulkan only:
  - **Native:** workers write to a task executor that the render thread consumes.
  - **Legacy:** workers write directly to the render thread.
  - **Split:** the render thread converts commands and fans out native command writing to workers.

  A Vulkan Device Filtering Asset can assign the mode per device. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: Unity 6.x · Evidence: [doc]
  - Notes: Meta's guidance names only Legacy. No published Quest comparison of Native or Split exists. [verify on device].

- **U5-038** A Quest 2 report (Unity 2021.2.1f1, URP, Vulkan): Graphics Jobs on with Multithreaded Rendering off roughly halved the frame rate. A Unity graphics engineer (florianpenzkofer) replied that Graphics Jobs implicitly disables Adreno LRZ/HSR, which moves the cost to the GPU. [T]
  - Source: https://discussions.unity.com/threads/vulkan-bug-quest-2-urp-graphics-jobs-no-multithreaded-rendering-slow.1208908/ (accessed 2026-09-24) · Applies to: 2021.2-era Vulkan backend; current status unknown · Evidence: [community] (includes a Unity staff reply)
  - Notes: Never enable Graphics Jobs without Multithreaded Rendering. Whether the LRZ side effect remains in 2022.3.35f1+ Legacy mode is unverified. Check GPU time and LRZ counters (RenderDoc Meta Fork, or the GPU profiling topic) before and after.

- **U5-039** Multithreaded Rendering moves graphics-API calls off the main thread; Meta's Project Setup Tool marks enabling it as Recommended. Meta's unity-perf page says to disable it temporarily while debugging, so render-submission cost shows on the main thread in captures. Re-enable it for shipping. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24); https://developers.meta.com/horizon/documentation/unity/unity-perf/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: With it on, main-thread render cost appears as Gfx.WaitForRenderThread / Gfx.WaitForCommands stalls (U5-083).

- **U5-040 / U4-077** GPU Skinning moves skinning and blend shapes to the GPU. The options are:
  - CPU
  - GPU
  - GPU (Batched), 6.x only, which batches and reorders dispatches to reduce dispatch count

  Meta's Project Setup Tool lists "consider GPU Skinning if CPU bound" as Optional. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24); Meta XR Core SDK OVRProjectSetupRenderingTasks.cs v78/v83 (accessed 2026-09-24) · Applies to: GPU (Batched) on 6.x; a checkbox on older versions · Evidence: [doc]
  - Notes: This trades CPU time for GPU time. On a GPU-bound Quest title it can lose.
  - **Merged U4-077:** The GPU skinning Player setting has changed across versions: [T]
    - 2021.3: a "Compute Skinning" checkbox.
    - 2022.3: "GPU Compute Skinning".
    - 2023.2: a "GPU Skinning" dropdown (CPU or GPU).
    - 6000.0 and 6000.3: CPU, GPU, or GPU (Batched). Unity says GPU (Batched) reduces the number of compute dispatches by batching skinned meshes together.

    The Quality setting Skin Weights caps bones per vertex.
    - Source: https://docs.unity3d.com/2021.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://docs.unity3d.com/2022.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://docs.unity3d.com/2023.2/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/class-QualitySettings.html (accessed 2026-09-24) · Applies to: as listed · Evidence: [doc] [verify on device]
    - Notes: No published Quest figure measures GPU against GPU (Batched) skinning. Compare with a crowd scene, reading render-thread and GPU time in the Profiler and OVR Metrics Tool. Meta's 2018 tech note suggested at most 2 bones per vertex (possibly stale). Skinned meshes also carry the attribute costs in U4-072.

- **U5-041** `TransformHandle` (Unity 6.3+) is an unmanaged, Burst-compatible handle to a Transform. Get it from `gameObject.transformHandle` or `transform.GetTransformHandle()`. It lets jobs read and write transforms without managed Transform access. It is runtime-only and lacks sibling index, `Find` and `hasChanged`. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-TransformHandle.html (accessed 2026-09-24) · Applies to: 6.3+ · Evidence: [doc]
  - Notes: On 2021.3–6.2, use `TransformAccessArray` / `IJobParallelForTransform`.

- **U5-042** Physics queries can run on job workers in batches: fill a `NativeArray<RaycastCommand>`, call `RaycastCommand.ScheduleBatch`, and complete the handle later, for example next frame. Unity describes this as a major gain for many independent queries. `SpherecastCommand` and `BoxcastCommand` work the same way. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-raycasts-queries.html (accessed 2026-09-24) · Applies to: all versions (API since 2018) · Evidence: [doc]
  - Notes: Completing the handle in the same frame serializes the work onto the main thread. On Quest's small worker pool, schedule early and complete late.

### Update overhead, update managers and Awaitable

- **U5-043** Unity keeps a per-type list of scripts that define each magic method. Every call is a native → managed transition, preceded by safe-iteration and validity checks. A 10,000-object test (Unity 5.2, iOS, Release) found a single manager calling a plain C# `UpdateMe()` on each object much cheaper than 10,000 `Update()` messages. Switching the manager's `List<T>` to `T[]` gave a further ~5x on IL2CPP. [T]
  - Source: https://unity.com/blog/engine-platform/10000-update-calls (accessed 2026-09-24) · Applies to: principle holds; the numbers are Unity 5.2 / iOS 2015 · Evidence: [measured]
  - Notes: The blog's timing tables are images and were not transcribed. The only readable figure is 0.23 ms for the array manager on Mono. The engine has changed a lot since. [verify on device]: re-run the 10k test with IL2CPP Master on Quest 2 and Quest 3.

- **U5-044** A shared base class that declares empty virtual `Update`/`LateUpdate`/`FixedUpdate` puts every derived script into every update list. The engine then pays the per-call overhead for empty bodies. Declare magic methods only where needed. [T]
  - Source: https://unity.com/blog/engine-platform/10000-update-calls (accessed 2026-09-24) · Applies to: all versions · Evidence: [measured]
  - Notes: Easy to audit: search for `virtual void Update`.

- **U5-045** Meta's basic optimization workflow gives a rule of thumb: app logic taking longer than about 2 ms probably has room to optimize. At 90 Hz that is 18% of the frame; at 120 Hz, 24%. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: This is a heuristic, not a hard budget.

- **U5-046** `Awaitable` (Unity 2023.1+, so 6.0+ within this range) is pooled to avoid per-await allocations. Because instances are pooled, awaiting the same instance twice is undefined behavior (exception or deadlock). Wrap it in a Task if multiple consumers need it. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/async-awaitable-introduction.html (accessed 2026-09-24) · Applies to: 6.0–6.6 (not in 2021.3/2022.3) · Evidence: [doc]
  - Notes: The `Awaitable` ScriptReference page returns 404 for 2021.3 and 2022.3 and exists from 2023.1.

- **U5-047** Continuations differ between Task and Awaitable:
  - A .NET Task continuation started on the main thread is posted to `UnitySynchronizationContext` and runs at the next frame's Update. That adds up to a frame of latency plus context-capture overhead.
  - An Awaitable continuation runs synchronously when completion fires, in the same frame.

  Use Awaitable over Task for main-thread gameplay async. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/async-awaitable-continuations.html (accessed 2026-09-24) · Applies to: 6.0–6.6 · Evidence: [doc]
  - Notes: `Awaitable.BackgroundThreadAsync()` / `MainThreadAsync()` switch threads. Returning to the main thread from a background thread waits for the next frame. Release builds do not check for main-thread-only API misuse.

- **U5-048** Awaitable coroutines are usually cheaper than iterator coroutines, especially when the iterator yields non-null objects such as `WaitForFixedUpdate`. Unity warns that the advantage shrinks with many concurrent instances. A `while(true) { await Awaitable.NextFrameAsync(); }` loop on every GameObject is called out as a likely performance problem. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/async-awaitable-introduction.html (accessed 2026-09-24) · Applies to: 6.0–6.6 · Evidence: [doc]
  - Notes: For per-frame work across many objects, the manager pattern (U5-043) still applies. No published Quest cost per await.

- **U5-049** Use Animator parameter hashes (`Animator.StringToHash`, cached in statics) instead of string names in per-frame calls. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/MecanimPeformanceandOptimization.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The same applies to `Shader.PropertyToID` for material property calls; see the rendering topics.

### Physics (PhysX)

- **U5-050** The Fixed Timestep defaults to 0.02 s (50 Hz). Quest displays run at 72/90/120 Hz, which gives about 0.69, 0.56 or 0.42 physics steps per rendered frame. Some frames run a step and some don't, so main-thread cost alternates frame to frame. Physics-driven motion also judders unless Rigidbody interpolation is on. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-frequency.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The per-frame step ratios are arithmetic from the documented default. Matching the step to the refresh rate gives exactly one step per frame (constant cost) but raises total physics cost by 1.44x (72 Hz), 1.8x (90 Hz) or 2.4x (120 Hz) versus 50 Hz.

- **U5-051** Community practice sets `Time.fixedDeltaTime = 1 / refreshRate`, for example 0.0138 at 72 Hz. An older Oculus SampleFramework script (DistanceGrabberSample) sets it from `OVRManager.display.displayFrequency` at runtime. [C]
  - Source: https://communityforums.atmeta.com/discussions/dev-unity/time---fixed-timestep--hz-values-for-oculus-devices-in-unity/751740 (search snippet only; the page returned 403) (accessed 2026-09-24); https://github.com/sebastianstarke/AI4Animation (copy of Oculus SampleFramework `DistanceGrabberSample.cs`) (accessed 2026-09-24) · Applies to: all versions · Evidence: [community]
  - Notes: Read the rate at runtime (`XRDisplaySubsystem.TryGetDisplayRefreshRate` or the Meta display API), because apps can switch rates. See Conflict U5-C4.

- **U5-052** Current Meta XR Core SDK code uses `Time.fixedDeltaTime` to predict node poses for physics steps. `OVRInput` computes the prediction time as fixedUpdateCount × fixedDeltaTime / timeScale and passes it to `OVRPlugin.UpdateNodePhysicsPoses`. No evidence was found that OVRManager overrides `fixedDeltaTime` itself. [C]
  - Source: https://github.com/icosa-mirror/com.meta.xr.sdk.core/blob/main/Scripts/OVRInput.cs (accessed 2026-09-24) · Applies to: Meta XR Core SDK (mirrored version) · Evidence: [doc] (Meta source)
  - Notes: A GitHub code search of the mirror found `fixedDeltaTime` only in OVRInput and sample scripts.

- **U5-053** A September 2024 Unity forum thread reports that changing `fixedDeltaTime` had no visible effect on a Quest build. It is unresolved, with no staff answer. [C]
  - Source: https://discussions.unity.com/t/change-fixeddeltatime-for-meta-quest/1517687 (accessed 2026-09-24) · Applies to: Unity 2022.3/6.0 era · Evidence: [community]
  - Notes: [verify on device]: log `Time.fixedDeltaTime` and count FixedUpdate calls per frame after setting it.

- **U5-054** When physics falls behind, Unity runs several fixed steps in one frame to catch up. The extra steps lengthen the frame, which requires more steps next frame: the "spiral of doom". **Maximum Allowed Timestep** (Time settings) caps catch-up per frame, at the cost of simulation slowing down in game time. On Quest, where missed frames already cause reprojection, set it to one or two fixed steps. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-frequency.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: "One or two steps" is a derived recommendation; no Meta number was found.

- **U5-055** Physics can be stepped manually: `Physics.simulationMode = SimulationMode.Script` plus `Physics.Simulate(step)`. It can also be stepped once per frame (`SimulationMode.Update`). Query-only apps can skip simulation entirely and call `Physics.SyncTransforms` before queries. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PhysicsManager.html (accessed 2026-09-24) · Applies to: `simulationMode` 2022.2+; 2021.3 uses `Physics.autoSimulation` · Evidence: [doc]
  - Notes: `Physics-simulationMode` does not exist in the 2021.3 ScriptReference (404), and `Physics-autoSimulation` does (200).

- **U5-056** Keep **Auto Sync Transforms** off (the default). When on, it inserts a sync before every physics query. If code moves colliders and must query in the same frame, call `Physics.SyncTransforms()` once before the queries. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-transform-sync.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: `Physics.autoSyncTransforms` is deprecated in recent 6.x.

- **U5-057** Keep **Reuse Collision Callbacks** on (the default). Otherwise every OnCollision*/OnTrigger* callback allocates a new Collision object. With reuse, the Collision data is valid only inside that callback. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-collision-callbacks.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Check projects upgraded from old versions, where it may be off.

- **U5-058** Standard queries (`Physics.Raycast` with all-hits variants, `OverlapSphere`, `SphereCastAll`) allocate result arrays. Use the `*NonAlloc` versions with a preallocated buffer sized to typical hit counts; excess hits are silently dropped. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-raycasts-queries.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Batch with RaycastCommand (U5-042).

- **U5-059 / U4-074** Collider cost order: sphere < capsule < box < convex mesh < non-convex mesh. Prebake Collision Meshes is on by default. Runtime mesh cooking causes spikes. Tune the cooking options:
  - Cook For Faster Simulation
  - Enable Mesh Cleaning
  - Weld Colocated Vertices
  - Use Fast Midphase

  [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-collider-types.html (accessed 2026-09-24); https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-mesh-cooking-options.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The Profiler flags a known hitch: calling `Rigidbody.SetKinematic` on a body with a non-convex MeshCollider recreates the collider (profiler-markers reference).
  - **Merged U4-074:** The Prebake Collision Meshes Player setting adds physics collision data to meshes at build time. Meta's 2018 tech note recommended it so collision data isn't generated at load time. [C]
    - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://developers.meta.com/horizon/blog/tech-note-unity-settings-for-mobile-vr/ (2018-04-12; accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc] [verify on device]
    - Notes: The 2018 note is possibly stale. The 2018 AUP blog lists mesh collision generation as a load-time step (U4-081). Measure scene-load time with and without this setting in the Profiler, and look for physics cooking markers during load.

- **U5-060** Moving a static collider (no Rigidbody) forces the physics system to update its spatial structures at the next step. Give colliders that move every frame a kinematic Rigidbody. Don't add a Rigidbody to something that moves only occasionally just to move it. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-static-colliders.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Meta's best-practices page also says non-static colliders need Rigidbodies (U5-061).

- **U5-061** Meta's Unity best practices say to avoid:
  - Sleep Threshold below 0.005
  - Default Contact Offset below 0.01
  - Solver Iteration Count above 6

  They also say to put Rigidbodies on non-static colliders and to pool objects. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Unity's own default contact offset is 0.01. Per-body overrides: `Rigidbody.solverIterations` and `Rigidbody.sleepThreshold`.

- **U5-062** Broadphase: Sweep and Prune (the default) produces false-positive pairs in large flat worlds with many colliders. Multibox or Automatic Box Pruning grids fit those worlds better. Automatic Box Pruning loses in highly dynamic scenes and can spike when world bounds change. Choose by profiling the broadphase time. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-broad-phase.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Also prune the Layer Collision Matrix: disabled layer pairs skip broadphase work (https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-collision-layers.html).

- **U5-063** Other physics settings with a CPU cost:
  - Solver type: PGS (default) or TGS.
  - CCD modes, cheapest first: Discrete (default) → Continuous Speculative → Continuous → Continuous Dynamic, the last as a last resort.
  - Default Max Angular Speed is 50.
  - Scratch Buffer Chunk Count defaults to 4 (16 KB chunks, 64 KB total).
  - Queries Hit Triggers is on by default.

  Use CCD only on small fast bodies, such as thrown objects in VR. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PhysicsManager.html (accessed 2026-09-24); https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-rigidbody-collision-modes.html (accessed 2026-09-24) · Applies to: all versions (6.x UI) · Evidence: [doc]
  - Notes: No Quest numbers. Turning Queries Hit Triggers off removes trigger colliders from queries.

- **U5-064** Physics profiler markers:
  - `Physics.Simulate`
  - `Physics.FetchResults`
  - `Physics.Processing` (may include work stolen by job workers)
  - `Physics.ProcessReports` (Contacts, JointBreaks, TriggerEnterExits, TriggerStays)
  - `Physics.UpdateBodies`
  - `Physics.Interpolation`

  A large TriggerStays or Contacts cost points to callback count, not simulation. Window > Analysis > Physics Debugger shows collider and contact layout. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The Physics Profiler module also counts broadphase pairs and active contacts.

### UI (uGUI, world-space UI, UI Toolkit, TextMesh Pro)

- **U5-071** In uGUI, changing one element dirties its whole Canvas, which triggers a mesh and batch rebuild. On a single large Canvas with thousands of elements, Unity reports CPU spikes of multiple milliseconds. Split static and dynamic content into separate Canvases or nested sub-Canvases (each rebuilds independently). Keep the elements of one Canvas on the same Z, material and texture. [C][T]
  - Source: https://unity.com/how-to/unity-ui-optimization-tips (accessed 2026-09-24) · Applies to: uGUI, all versions · Evidence: [doc]
  - Notes: "Multiple milliseconds" is Unity's wording, with no device given. The rebuild cost is expected under the `Canvas.SendWillRenderCanvases` / `Canvas.BuildBatch` samples. Those names are from general Unity knowledge, not the fetched markers reference; [verify on device] in a capture.

- **U5-072** Every Graphic Raycaster loops over the pointer inputs and checks them against every raycast-target element on its Canvas. To cut the cost:
  - Remove Graphic Raycasters from non-interactive Canvases.
  - Turn off Raycast Target on static elements, including button labels.
  - Avoid Blocking Mask physics raycasts (world-space/camera canvases), which Unity calls expensive.

  [T]
  - Source: https://unity.com/how-to/unity-ui-optimization-tips (accessed 2026-09-24); https://docs.unity3d.com/Packages/com.unity.ugui@2.0/manual/script-GraphicRaycaster.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: In VR, XR Interaction Toolkit's tracked-device raycasters add per-controller work on top. No published cost found.

- **U5-073** Every layout-dirtying element calls GetComponent up the hierarchy to find layout groups, so nested Layout Groups multiply the cost. Prefer anchors. For dynamic lists, compute the layout in code on demand. For big lists or grids, pool and virtualize items. [T][C]
  - Source: https://unity.com/how-to/unity-ui-optimization-tips (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Unity 6.6 adds LayoutElement max width/height and a ContentSizeFitter "Clamped" mode. These are layout features, not performance fixes.

- **U5-074** Pooling UI elements:
  - Into the pool: disable first, then reparent. The old hierarchy is dirtied once and the new one not at all.
  - Out of the pool: reparent, update, then enable.
  - To hide a Canvas: disable the Canvas component. It keeps its vertex buffer, so re-enabling doesn't rebuild, and it skips OnEnable/OnDisable callbacks down the hierarchy.

  [C]
  - Source: https://unity.com/how-to/unity-ui-optimization-tips (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Per-frame scripts on children of a disabled Canvas keep running; disable those separately.

- **U5-075** Animators on UI elements dirty the elements every frame even when values don't change. Use tweens or code for occasional UI animation, and keep Animators only on continuously changing elements. [T]
  - Source: https://unity.com/how-to/unity-ui-optimization-tips (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Common in VR wrist menus and tooltips.

- **U5-076** A world-space Canvas behaves like any scene object. Its RectTransform size sets its pixel resolution, and uniform scale converts that to meters; for example, 800 px wide × 0.0025 = 2 m. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.ugui@2.0/manual/HOWTO-UIWorldSpace.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Canvas resolution drives text mesh density (TMP SDF quads) and overdraw area. GPU side effects belong to the rendering topics.

- **U5-077** UI Toolkit world-space panels exist from Unity 6.2: set Panel Settings Render Mode to World Space. The 6.2 manual page exists; 2022.3, 6.0 and 6.1 return 404.
  - Pixels Per Unit defaults to 100.
  - Panel Input Configuration > Max Interaction Distance defaults to infinity. Unity suggests limiting it for XR or performance.
  - Interaction Layers restricts which physics layers the world-space rays hit.

  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/ui-systems/world-space-ui.html (accessed 2026-09-24); https://docs.unity3d.com/6000.6/Documentation/Manual/ui-systems/world-space-panel-input-configuration.html (accessed 2026-09-24) · Applies to: 6.2+ · Evidence: [doc]
  - Notes: The same page links to XR Interaction Toolkit support for UI Toolkit world space. No published Quest cost comparison between uGUI and UI Toolkit world space. [verify on device].

- **U5-078** Unity 6.6 adds UI Toolkit and UI Toolkit Details Profiler modules. They show layout and binding update time, events dispatched per panel, and the reasons for render batch breaks. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]
  - Notes: On earlier versions, UI Toolkit cost shows only as generic markers.

## 9. Memory and assets

### Texture compression: ASTC, defaults, overrides, normal maps, ASTC HDR

- **U4-046** ASTC is Unity's default Android texture compression target, per the 2021.3, 2022.3, 2023.2, 6000.0, and 6000.3 manuals. A texture in a format the device can't sample is decompressed at runtime, which costs memory and load time. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/android-requirements-and-compatibility.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]

- **U4-047** Compression settings apply in this order, highest priority first: [C]
  1. A per-texture platform override.
  2. The Build Settings / Build Profile "Texture Compression" setting (default "Use Player Settings").
  3. The Player setting "Texture compression formats". Since 2023.1 this is a list used for texture compression targeting (AAB only). For an APK, only the first entry is used.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/android-requirements-and-compatibility.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x (list form from 2023.1) · Evidence: [doc]
  - Notes: Quest store uploads are APKs, so the first list entry is the one that matters. A stray ETC2 Build Profile override silently changes every texture without a per-texture override.

- **U4-048** On Android, the Default texture importer maps each compression quality to an ASTC block size: [T]
  - Normal: ASTC 6x6.
  - High: ASTC 4x4.
  - Low: ASTC 8x8.

  The ETC2/ETC fallbacks apply when ASTC isn't the target.
  - Source: https://docs.unity3d.com/2022.3/Documentation/Manual/class-TextureImporter.html ("Default formats" section) (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x (per-platform defaults) · Evidence: [doc]

- **U4-049** ASTC bitrates are fixed by block size: [T][C]
  - 4x4: 8 bpp
  - 5x5: 5.12 bpp
  - 6x6: 3.56 bpp
  - 8x8: 2 bpp
  - 10x10: 1.28 bpp
  - 12x12: 0.89 bpp

  ASTC HDR on Android needs GL_KHR_texture_compression_astc_hdr or the Vulkan equivalent. Without it, Unity decompresses to RGB9E5 (alpha dropped) or RGBA Half, and RGBA Half uses twice the memory of RGB9E5. Adreno 4xx and later support LDR ASTC.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/texture-formats-reference.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/texture-choose-format-by-platform.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc] [verify on device]
  - Notes: Whether Quest supports ASTC HDR is unconfirmed (see U4-038 and Gaps).

- **U4-050** Arm's 2020 guidance on the Meta blog says to start at ASTC 5x5 or 6x6 and move to larger blocks for assets that take up less of the view. The same post advises avoiding micro-triangles, using LODs, and using alpha-to-coverage for foliage. [T]
  - Source: https://developers.meta.com/horizon/blog/top-tips-from-arm-for-vr-asset-optimization/ (2020-10-02; accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Possibly stale (2020), but block-size physics hasn't changed. No published per-block-size texture bandwidth or GPU-ms figure exists for Quest. Measure texture-read bandwidth with Snapdragon Profiler or OVR Metrics Tool GPU counters, A/B-ing 4x4 against 6x6 on a full-screen material.

- **U4-051** The Normal Map Encoding Player setting offers XYZ or DXT5nm-style. Unity says DXT5nm-style gives higher quality but costs more to decode in shaders. In the SRP core shader library, the DXT5nm-style path defines `UNITY_ASTC_NORMALMAP_ENCODING` and decodes with `UnpackNormalAG`, which reconstructs Z from X and Y. The XYZ path (`UNITY_NO_DXT5nm`) uses `UnpackNormalRGBNoScale`. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/ShaderLibrary/Packing.hlsl (accessed 2026-09-24) · Applies to: 2022.x to 6000.x (check your version's Player settings for this option) · Evidence: [doc] [verify on device]
  - Notes: The decode difference is a few ALU ops (a sqrt), traded against better ASTC quality. No Quest GPU-ms figure is published. Measure on a scene dominated by normal-mapped surfaces.

- **U4-052** Arm's astc-encoder guidance for normal maps is to store X and Y as luminance plus alpha (the `rrrg` swizzle), sample `.ga`, and rebuild Z in the shader. This matches the DXT5nm-style path. Arm also notes that the ASTC decode-mode extensions (for example, decoding LDR to RGBA8) improve texture-cache efficiency. [T]
  - Source: https://github.com/ARM-software/astc-encoder/blob/main/Docs/Encoding.md (accessed 2026-09-24) · Applies to: all versions (hardware-level) · Evidence: [doc]
  - Notes: No source was found on whether Unity enables the decode-mode extensions on Quest.

- **U4-053** Meta's Quest guidance: [T][C]
  - Compress large textures.
  - Watch for textures above 2k x 2k after LOD bias.
  - Keep large textures and many prefabs out of startup scenes.

  Meta's 2026 Quest 2 vs Quest 3 page says to use ASTC on both, and to use lower-resolution textures or fewer mip levels on Quest 2. Quest 3 has 8 GB of RAM and Quest 2 has 6 GB.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ ; https://developers.meta.com/horizon/resources/device-optimization-comparison/ (2026-05-11; accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Quest 3S is not covered on the comparison page. Its SoC and RAM match Quest 3 per public spec sheets (verify), with lower display resolution.

- **U4-054** A Read/Write-enabled texture keeps a CPU copy, which doubles its memory. `Texture2D.Apply(updateMipmaps, makeNoLongerReadable: true)` frees the CPU copy after upload. After that, the texture's uploaded resolution is fixed: it stops following later mipmap-limit changes unless it was uploaded at full resolution or uses `ignoreMipmapLimit`. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/texture-type-default.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Texture2D.Apply.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x (the mipmap-limit interaction applies to 2022.2+) · Evidence: [doc]
  - Notes: Read/Write also disqualifies a texture from the Async Upload Pipeline (U4-078).

### Mipmaps, mipmap limits, filtering, mipmap streaming

- **U4-055** Meta's filtering and mipmap guidance has changed over time: [T]
  - The 2024 best-practices page says to use trilinear or anisotropic filtering.
  - The legacy Android page says always use mipmaps, calls trilinear worth its cost, and limits anisotropic filtering to one lookup per fragment.
  - The 2018 tech note said to disable anisotropic filtering.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ ; https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ ; https://developers.meta.com/horizon/blog/tech-note-unity-settings-for-mobile-vr/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: See U4-C4. The 2018 reason (Mali/Exynos lacked anisotropic support) doesn't apply to Adreno-based Quest devices.

- **U4-056** The Quality setting Anisotropic Textures has three values: Disabled, Per Texture, or Forced On. Unity says anisotropic filtering increases rendering time. The texture importer's Aniso Level is described as resource-intensive and best suited to floors and ground. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-QualitySettings.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/texture-type-default.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc] [verify on device]
  - Notes: No published Adreno 650/740 cost exists per aniso level. Use Per Texture, raise Aniso Level only on surfaces seen at grazing angles, and A/B GPU time on a floor-dominated view.

- **U4-057** Global Mipmap Limit (0 Full, 1 Half, 2 Quarter, 3 Eighth) drops top mips for every texture that respects mipmap limits. Mipmap Limit Groups let a group offset that value by -3 to +3 or override it. Per texture, the Mipmap Limit checkbox can opt out. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-QualitySettings.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/texture-type-default.html (accessed 2026-09-24) · Applies to: 2022.2+ for groups. 2021.3 has the older Texture Quality setting (`QualitySettings.masterTextureLimit`); check your version's docs. · Evidence: [doc]
  - Notes: This is the cheapest lever for a Quest 2 quality tier that uses fewer mips (U4-053).

- **U4-058** Texture Mipmap Stripping (Player setting) removes, at build time, the mip levels that every quality level for the platform excludes. That reduces build size and load I/O. If the global mipmap limit is later set to a stripped level, Unity snaps to the nearest level that remains. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]

- **U4-059** Mipmap Streaming Quality settings: [C]
  - Add All Cameras.
  - Memory Budget: default 512 MB.
  - Renderers Per Frame: default 512.
  - Max Level Reduction: default 2. This is also the mip level streaming textures load at first.
  - Max IO Requests: default 1024.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-QualitySettings.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x (names changed from "Texture Streaming" to "Mipmap Streaming" in newer docs) · Evidence: [doc] [verify on device]
  - Notes: The default budget is not sized for Quest. Size it from measured `Texture.desiredTextureMemory` (U4-060).

- **U4-060** The mipmap streaming budget also counts non-streamed textures. Unity says to estimate the budget from `Texture.desiredTextureMemory`. Known limits: [C]
  - Not supported: terrain, texture arrays, cubemap arrays, and 3D textures.
  - Draws such as `Graphics.DrawMeshNow` get the lowest allowed mip.
  - The shader needs the texture's `_ST` property.
  - The renderer needs a Mesh Filter or Skinned Mesh Renderer.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/TextureStreaming.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/TextureStreaming-configure.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]

- **U4-061** Per texture, "Stream Mipmap Levels" opts a texture into streaming. Priority (-128 to 127) sets both allocation priority and a mip bias. For example, priority 2 aims two mip levels sharper than priority 0. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/texture-type-default.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]

- **U4-062** Procedural or runtime meshes need `Mesh.RecalculateUVDistributionMetrics` for streaming to pick correct mips. Without it, streaming can't compute the UV density. [C]
  - Source: https://docs.unity3d.com/2021.3/Documentation/Manual/TextureStreaming.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]

- **U4-063** No Unity or Meta document found in this research says how mipmap streaming picks mips for stereo XR cameras (two eyes, or single-pass multiview). [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/TextureStreaming.html (accessed 2026-09-24; searched, no XR statement found) · Applies to: 2021.3 to 6000.x · Evidence: [doc] [verify on device]
  - Notes: To verify on device, log `Texture2D.desiredMipmapLevel` against `loadedMipmapLevel` for a close-up texture in a Quest build. Also watch for visible blur while turning the head quickly.

### Measuring texture and mesh memory

- **U4-064** The Profiler's Memory module shows Texture Memory, Mesh Memory, Material Count, Object Count, GC Used Memory, and GC Allocated In Frame. Its "Objects stats" (per-type counts and sizes) are not available in release players. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/ProfilerMemory.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x (module layout varies by version) · Evidence: [doc]

- **U4-065** These profiler counters are unavailable in release (non-development) players: [C]
  - Texture Memory, Texture Count, Mesh Memory, Mesh Count, Material Memory
  - Gfx Used Memory and Gfx Reserved Memory
  - the asset-loading byte counters (Texture Reads, Mesh Reads)

  System Used Memory (app resident memory) and System Total Used Memory are available in release players through `ProfilerRecorder`. `Profiler.GetRuntimeMemorySizeLong` does not report graphics memory in release builds.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-counters-reference.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-memory-counters-players.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: Take texture and mesh memory numbers from a Development build, with the Memory Profiler package for per-object breakdowns. Use System Used Memory, or `adb shell dumpsys meminfo <package>`, for release-build totals.

- **U4-066** Debug APIs for mipmap streaming: [C]
  - Global: `Texture.currentTextureMemory`, `desiredTextureMemory`, `totalTextureMemory`, `targetTextureMemory`, `nonStreamingTextureMemory`, `streamingMipmapUploadCount`, `streamingTextureCount`.
  - Per texture: `Texture2D.desiredMipmapLevel`, `loadingMipmapLevel`, `loadedMipmapLevel`.

  In URP, the Rendering Debugger visualizes streaming.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/TextureStreaming-analyze.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]

- **U4-067** For a release-build view on Quest, the Memory Profiler module's "Other" bucket and the Memory Profiler package are the documented routes to see what is in native memory. Unity points to the package for a deeper breakdown than the module's categories. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/ProfilerMemory.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: No Meta page read here maps Unity's Gfx memory numbers onto Android's GL/graphics mtrack rows in `dumpsys meminfo`. Cross-check the two on device.

### Mesh data: compression, attribute formats, index format, Read/Write

- **U4-068** Vertex Compression (a Player setting) stores selected channels as FP16 instead of FP32. By default it compresses Normal, Tangent, TexCoord0, TexCoord2, and TexCoord3. Position and TexCoord1 (lightmap UVs) stay FP32. It applies only when all of these hold: [T][C]
  - Read/Write is off.
  - The mesh is not skinned.
  - The platform supports FP16.
  - Mesh Compression is Off.
  - The mesh is not dynamic-batched.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/configure-vertex-compression.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/types-of-mesh-data-compression.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: Unity's example gives about a 1.45x reduction for a mesh with normals, tangents, color, and 3 UV sets. It cuts memory and vertex-fetch bandwidth.

- **U4-069** Mesh Compression (a model importer setting: Off, Low, Medium, High) quantizes data on disk only. Unity publishes a ratio table; for example, High compresses vertices about 3.2x and normals about 7.4x. It costs CPU time and temporary memory at load. A mesh with Mesh Compression on also skips vertex compression and the Async Upload Pipeline. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/configure-mesh-compression.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/LoadingTextureandMeshData-make-compatible.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: For Quest, leave Mesh Compression Off on runtime meshes, rely on LZ4 build compression for disk size, and keep AUP eligibility.

- **U4-070** Optimize Mesh Data (`PlayerSettings.stripUnusedMeshComponents`) strips vertex attributes that no material in the build uses. That reduces build size, load time, and runtime memory. Unity warns against changing materials or shaders at runtime when it is on. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings-stripUnusedMeshComponents.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: A material swapped at runtime to a shader that needs a stripped channel, such as tangents, renders incorrectly.

- **U4-071** The model importer's Index Format has three values: [T]
  - Auto (default).
  - 16-bit: meshes over 64k vertices are split into chunks.
  - 32-bit.

  Unity's best practice is 16-bit where possible. Weld Vertices defaults to on, and Optimize Mesh defaults to Everything (vertex and polygon order).
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/FBXImporter-Model.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]

- **U4-072** For custom vertex layouts (`VertexAttributeDescriptor`), each attribute's byte size must be a multiple of 4. Float16 x3 is invalid; use x4. A mesh can use up to 4 vertex streams. Skinned meshes force position, normal, and tangent to Float32. Check format support with `SystemInfo.SupportsVertexAttributeFormat`. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.VertexAttributeDescriptor.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: Skinned meshes therefore get neither vertex compression (U4-068) nor FP16 positions, so their per-vertex footprint is larger.

- **U4-073** The model importer's Read/Write defaults to off. Turning it on keeps a CPU copy of the mesh. `Mesh.isReadable` lists the runtime cases that need a readable mesh: [C]
  - runtime `StaticBatchingUtility.Combine`
  - `CanvasRenderer.SetMesh`
  - runtime NavMesh baking
  - some MeshCollider cases (negative scale with convex, skewed transforms, non-default cooking options)
  - particle mesh emission without GPU instancing

  `Mesh.UploadMeshData(markNoLongerReadable: true)` frees the CPU copy.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/FBXImporter-Model.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Mesh-isReadable.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: A readable mesh also can't use vertex compression or AUP (U4-078).

- **U4-075** Meta's 2021 Quest 2 profiling of scene activation found the following: [C]
  - Activation cost grows linearly with GameObject count.
  - TextMeshPro objects cost more than ParticleSystems, which cost more than MeshFilter/MeshRenderer.
  - CPU-readable meshes (Read/Write on, or skinned meshes with bones or blendshapes) have a steep activation cost.

  Meta advises splitting modular characters into separate meshes.
  - Source: https://developers.meta.com/horizon/blog/avoiding-hitches-when-loading-scenes-in-unity/ (2021-12-15, Quest 2, Unity 2020.3.8f1; accessed 2026-09-24) · Applies to: 2020.3 onward (possibly stale) · Evidence: [measured] [verify on device]
  - Notes: The post gives relative rankings from profiling, not published ms figures. Measure activation on your own content with the Profiler's `Application.Integrate Assets in Background` and activation markers.

### Async Upload Pipeline (AUP) and upload hitches

- **U4-078** Unity has two paths for uploading texture and mesh data: [C]
  - The synchronous path stores header and binary data together in `.res`, and loads it on the main thread in a single frame.
  - The async path (AUP) stores the binary in `.resS` and streams it through a ring buffer over several frames.

  To be AUP-eligible, a texture must be non-readable, outside Resources, and built with LZ4 build compression on Android; `LoadImage` always forces the sync path. A mesh must be non-readable, outside Resources, without BlendShapes or bone weights, not quads, not dynamic-batched, not needed by Particle Systems, Terrain, or MeshColliders, with Mesh Compression Off, and built with LZ4.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/LoadingTextureandMeshData.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/LoadingTextureandMeshData-make-compatible.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: Skinned characters (bone weights) always take the sync path. Budget their loads behind a loading screen or fade.

- **U4-079** Async Asset Upload is controlled by three settings: [C]
  - Time Slice: 1 to 33 ms.
  - Buffer Size: 2 to 2047 MB.
  - Persistent Buffer: default true.

  With Persistent Buffer off, the ring buffer is freed when idle, which saves memory but can fragment the heap. The ring buffer grows automatically, and resizing is slow, so size it to the largest texture you load.
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/QualitySettings-asyncUploadTimeSlice.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/QualitySettings-asyncUploadBufferSize.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/QualitySettings-asyncUploadPersistentBuffer.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/LoadingTextureandMeshData.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: The largest ASTC 6x6 texture with mips sets the minimum useful buffer size. Compute it from the Memory Profiler's texture list.

- **U4-080** Unity's 2018 AUP blog gives these details: [C]
  - The upload time slice (default 2 ms) runs on the render thread, twice per frame, while uploads are pending.
  - The default buffer has been 16 MB since 2018.3 (it was 4 MB in 2018.2).
  - A full ring buffer only slows loading; it doesn't block the main thread.
  - Some projects loaded more than 2x faster with AUP.
  - Source: https://unity.com/blog/engine-platform/understanding-the-async-upload-pipeline (2018-10-08; accessed 2026-09-24) · Applies to: 2018.3 onward (possibly stale) · Evidence: [doc] [verify on device]
  - Notes: On Quest, a larger time slice speeds loading but eats render-thread headroom at 72/90/120 Hz. Tune it only during loading screens: raise it there and lower it again in gameplay. Check the defaults in your project's Quality settings, since the 2018 values may differ from current.

- **U4-081** The 2018 AUP blog describes the pipeline steps: [C]
  1. Read into the ring buffer (on the AsyncRead thread).
  2. Post-process the data, which includes texture decompression when a format is unsupported, and mesh collision generation.
  3. Upload, time-sliced.
  - Source: https://unity.com/blog/engine-platform/understanding-the-async-upload-pipeline (2018-10-08; accessed 2026-09-24) · Applies to: 2018.3 onward (possibly stale) · Evidence: [doc]
  - Notes: This is why unsupported formats (U4-046, U4-049) and non-prebaked collision (U4-074) add load cost.

- **U4-082** Profiler markers that show AUP is in use: `AsyncUploadManager.ScheduleAsyncRead`, `AsyncReadManager.ReadFile`, `Async.DirectTextureLoadBegin`, and activity on the AsyncRead thread. The 2022.3 manual says these markers do not by themselves prove AUP use: `Initialization.AsyncUploadTimeSlicedUpdate`, `AsyncUploadManager.AsyncResourceUpload`, and `AsyncUploadManager.ScheduleAsyncCommands`. [C]
  - Source: https://docs.unity3d.com/2022.3/Documentation/Manual/LoadingTextureandMeshData.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]

### Scene loading, activation, unloading, Addressables and AssetBundles

- **U4-083** `Application.backgroundLoadingPriority` caps how long the main thread spends each frame integrating loaded assets: [C]
  - Low: 2 ms.
  - BelowNormal (default): 4 ms.
  - Normal: 10 ms.
  - High: 50 ms.

  It affects `Resources.LoadAsync`, `AssetBundle.LoadAssetAsync`, and `SceneManager.LoadSceneAsync`. The Profiler marker is `Application.Integrate Assets in Background`. It has no effect in the Editor.
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Application-backgroundLoadingPriority.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: At 72 Hz a frame is about 13.9 ms, so High (50 ms) guarantees dropped frames. Use it only behind a black or compositor loading screen. Use Low during gameplay streaming.

- **U4-084** With `AsyncOperation.allowSceneActivation = false`, progress stops at 0.9. Every later AsyncOperation, such as `UnloadSceneAsync`, queues behind it until activation. `AsyncOperation.priority` (default 0; higher runs first) orders the queue. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/AsyncOperation-allowSceneActivation.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/AsyncOperation-priority.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: Holding a pre-loaded scene at 0.9 blocks other async loads and unloads, a common cause of "loading froze" bugs.

- **U4-085** Scene activation is a main-thread hitch. Meta's 2021 guidance for keeping it short: [C]
  - Nest objects under a few roots.
  - Load objects disabled and enable them over several frames.
  - Pool objects instead of instantiating them.
  - Warm up shaders with a reference scene instead of `Shader.WarmupAll`.
  - Source: https://developers.meta.com/horizon/blog/avoiding-hitches-when-loading-scenes-in-unity/ (2021-12-15; accessed 2026-09-24) · Applies to: 2020.3 to 6000.x (possibly stale) · Evidence: [doc] [verify on device]
  - Notes: The post uses `LoadSceneAsync` with `allowSceneActivation`, which conflicts with the legacy Meta advice in U4-C1.

- **U4-086** `SceneManager.LoadSceneAsync` in Single mode automatically calls `Resources.UnloadUnusedAssets`. `UnloadUnusedAssets` walks the whole object hierarchy and static variables to find unreferenced assets. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SceneManagement.SceneManager.LoadSceneAsync.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Resources.UnloadUnusedAssets.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: A Single-mode load therefore includes an unload sweep whose cost scales with the live object count.

- **U4-087** The Addressables 1.21 docs call `Resources.UnloadUnusedAssets` slow and a cause of frame-rate hitches. They advise calling it only where hitches aren't visible, such as a loading screen. [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.addressables@1.21/manual/MemoryManagement.html (accessed 2026-09-24) · Applies to: Addressables 1.21 (2021.3/2022.3); the sentence is gone from the 2.3 page, but the engine behavior is unchanged · Evidence: [doc] [verify on device]
  - Notes: No published Quest figure measures its cost. Time it with a `ProfilerMarker` around the call, or read the `Resources.UnloadUnusedAssets` / GC markers in a Development build, at the object counts your app actually has.

- **U4-088** Community reports say `UnloadUnusedAssets` gets slower as a session goes on, and that it can hang the player in some cases. [C]
  - Source: https://discussions.unity.com/t/resources-unloadunusedassets-execution-time-slowly-increases-over-time/920692 ; https://issuetracker.unity3d.com/issues/the-player-hangs-when-unloading-a-scene-using-the-unloadunusedassets-method ; https://www.gamedeveloper.com/programming/when-is-unity-really-unloading-your-assets-from-memory- (accessed 2026-09-24; titles only, from search-result listings) · Applies to: unspecified versions · Evidence: [community] [verify on device]
  - Notes: The ms figures quoted in search snippets were not read in context, so none are reproduced here. Treat this as a lead to measure, not as evidence of a size.

- **U4-089** In Addressables, releasing an asset does not free its memory until the whole AssetBundle unloads, because bundles can't be partially unloaded. Releasing the last asset in a bundle and then reloading from it causes "asset churn": unload followed by immediate reload. Use the Addressables Profiler module to spot both. [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.addressables@2.3/manual/MemoryManagement.html ; https://docs.unity3d.com/Packages/com.unity.addressables@1.21/manual/MemoryManagement.html (accessed 2026-09-24) · Applies to: Addressables 1.21 to 2.x · Evidence: [doc]
  - Notes: On Quest 2 (6 GB), a large bundle kept alive by one small asset can be the memory problem. Group bundles by lifetime.

- **U4-090** The two AssetBundle compression formats behave differently: [C]
  - LZMA compresses the whole content section. The entire file must be decompressed into RAM before any asset is read.
  - LZ4 compresses 128 KB chunks separately, so only the needed chunks load. Unity says LZ4 loads in comparable time to uncompressed bundles.

  BuildPipeline defaults to LZMA, and Unity's cache recompresses downloads to LZ4.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/assetbundles-compression-format.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc]
  - Notes: For bundles shipped in the APK or OBB on Quest, use LZ4. LZ4 is also required for AUP (U4-078).

- **U4-091** Meta's startup guidance says to avoid large textures and many prefabs in startup scenes. The legacy page suggests a small first scene, then loading the main scene in the background. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ ; https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ (legacy) (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]

- **U4-092** The legacy Meta Android page also says to avoid `LoadLevelAsync` and `LoadLevelAdditiveAsync`: fade to black and load synchronously instead. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ (legacy, undated; accessed 2026-09-24) · Applies to: pre-2018 Unity era · Evidence: [doc]
  - Notes: Possibly stale. The old APIs are obsolete, and the advice predates AUP. See U4-C1.

### Shader loading at scene load, and GC during loading

- **U4-094** Shader Variant Loading settings (Player > Other Settings) control shader memory: [C]
  - Default chunk size: 16 MB of compressed data per chunk.
  - Default chunk count: 0, meaning no limit on decompressed chunks kept in memory.
  - Per-platform overrides are available.
  - `Shader.maximumChunksOverride` changes the chunk count at runtime.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/shader-memory.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings.SetDefaultShaderChunkSizeInMB.html (accessed 2026-09-24) · Applies to: 2021.3 to 6000.x · Evidence: [doc] [verify on device]
  - Notes: Capping the chunk count saves memory but can make Unity decompress chunks again at runtime, which risks hitches. Measure both memory and frame time before capping.

- **U4-095** "Keep Loaded Shaders Alive" stops loaded shaders from unloading, so they aren't recreated later, at the cost of memory. Meta's 2018 tech note recommended it, along with preloading shaders through the preloaded shaders list, to avoid compiling on demand. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://developers.meta.com/horizon/blog/tech-note-unity-settings-for-mobile-vr/ (2018-04-12; accessed 2026-09-24) · Applies to: 2021.3 to 6000.x (the 2018 note is possibly stale) · Evidence: [doc] [verify on device]

## 10. Profiling workflow

U5-083 (Meta's quick bound tests) is merged into U3-001 in section 5.

### Profiling workflow and instrumentation on Quest

- **U1-058** The XR compatibility table says the Frame Debugger is not supported for Meta/Oculus devices, only the mock HMD. Use RenderDoc, the Meta tools or the on-device Render Graph Viewer instead. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]

- **U5-079** `ProfilerMarker.Begin/End/Auto` are `[Conditional]`-compiled, with zero overhead in non-development (Release) builds. They pass an integer marker ID to the profiler stream, while `Profiler.BeginSample` passes the full string. They work in jobs. Use them to instrument hot systems instead of Deep Profiling. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Profiling.ProfilerMarker.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: On 6.6, see U5-018 (the Managed Code Variant determines `ENABLE_PROFILER`).

- **U5-080** `ProfilerRecorder` reads profiler counters and marker timings in Editor and Player builds, including Release players. Useful counters include "Main Thread" (Internal), "GC Reserved Memory" and "System Used Memory". List everything available with `ProfilerRecorderHandle.GetAvailable`. Recorders are unmanaged: dispose them. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Profiling.ProfilerRecorder.html (accessed 2026-09-24) · Applies to: 2020.2+ (page present in 2022.3) · Evidence: [doc]
  - Notes: Build a small in-headset HUD or CSV logger that records per-frame main-thread time and GC reserved memory in release builds for p95/p99 tracking. No release-build overhead number is published.

- **U5-081** First classify each frame as CPU-bound or GPU-bound. Unity's VR frame timing page:
  - GPU-bound: `XR.WaitForGPU` takes longer than one frame time.
  - CPU-bound: frame time exceeds the budget while `XR.WaitForGPU` stays short.
  - Missed frames are reprojected by the runtime. Persistent misses lock the app into rendering every other frame.

  [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/VRFrameTiming.html (accessed 2026-09-24) · Applies to: all versions (XR) · Evidence: [doc]
  - Notes: The markers and blocking points move with OpenXR Latency Optimization (U5-092 and Conflict U5-C2).

- **U5-082** Non-XR wait markers:
  - `WaitForTargetFPS`
  - `Gfx.PresentFrame`
  - `Gfx.WaitForPresentOnGfxThread`: the render thread inside Gfx.PresentFrame means GPU-bound; inside Camera.Render means CPU/render-thread-bound.
  - `Gfx.WaitForCommands`, `Gfx.WaitForRenderThread`
  - `<GfxDevice>.WaitForLastPresent`
  - `Semaphore.WaitForSignal`, `WaitForJobGroupID` (the main thread waiting on jobs)

  [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: WaitForJobGroupID on the main thread means jobs were completed too early or the worker pool is saturated.

- **U5-084** Profiling a Quest over ADB:
  1. Enable Development Build + Autoconnect Profiler.
  2. Connect to the "AndroidProfiler(ADB@127.0.0.1:34999)" target.
  3. If needed, forward the port manually: `adb forward tcp:34999 localabstract:Unity-<bundle id>`.

  Unity uses ports 54998–55511 (firewall). [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/android-profile-on-an-android-device.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Meta's Unity Profiler pages give the same steps and add the GPU Usage module (https://developers.meta.com/horizon/documentation/unity/unity-profiler-tool/).

- **U5-085** Deep Profiling instruments every managed method. It is much slower and can run out of memory on large apps, so avoid it on Quest. Use Call Stacks mode for GC.Alloc (U5-012) and ProfilerMarkers for timing. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-deep-profiling.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Deep-profile timings exaggerate small, frequently called methods.

- **U5-086** Headless capture for hitch hunting: start the player with `-profiler-enable -profiler-log-file <path>.raw -profiler-capture-frame-count <n>`, passed via the `-e unity` intent extra (U5-033). The player's profiler buffer (`-profiler-maxusedmemory`) defaults to 16 MB; raise it for long captures. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-command-line-arguments.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: The Editor default is 256 MB.

- **U5-087** Profiler overhead inflates draw and submission timings. GPU clocks vary under dynamic CPU/GPU levels, so compare captures only at locked levels. Runtime GPU preemptions (boundary, ATW/compositor) add noise to GPU timings. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-profiler-tool/ (accessed 2026-09-24); https://developers.meta.com/horizon/documentation/unity/tools-unityprofiler/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: CPU clock ranges per level are in the baseline table. Level control is a sibling topic.

- **U5-088** Profile Analyzer (latest 1.4.0, 2026-06-05; supports Unity 2021.3+) compares two captures by marker median and distribution. It is the documented way to A/B incremental GC (U5-006) and other settings on p95/p99, not single frames. [C]
  - Source: https://packages.unity.com/com.unity.performance.profile-analyzer (accessed 2026-09-24); https://docs.unity3d.com/6000.3/Documentation/Manual/performance-disabling-garbage-collection.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: Capture at least 300 frames of identical content per variant. That count is a working choice, not a published threshold.

- **U5-089** Memory Profiler package versions:

  | Unity | Memory Profiler |
  |---|---|
  | 2022.3+ | 1.1.12 (2026-03-10); 1.2.0-pre.1 (2026-09-02) is the registry "latest" tag |
  | 2021.3 | up to 0.7.1-preview.1 (min Unity 2019.4) |

  Use it to find managed-heap growth and fragmentation behind GC frequency. [C]
  - Source: https://packages.unity.com/com.unity.memoryprofiler (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: The 1.x line requires 2022.2+ (1.0.0) or 2022.3+ (1.1.x).

- **U5-090** FrameTimingManager has these limits:
  - Results lag by 4 frames.
  - On XR, both Vulkan and GLES support is "Partial": CPU Render Thread Frame Time and GPU Frame Time are not measured.
  - In release builds it needs Frame Timing Stats enabled; it is always on in development builds.
  - It may reduce GPU performance on GLES.

  Counter formulas:
  - cpuMainThreadFrameTime = PlayerLoop − GfxDevice.WaitForRenderThread − Gfx.WaitForPresentOnGfxThread − WaitForTargetFPS
  - cpuMainThreadPresentWaitTime = Gfx.WaitForPresentOnGfxThread + WaitForTargetFPS
  - cpuRenderThreadFrameTime = RenderLoop − Gfx.PresentFrame

  [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/frame-timing-manager.html (accessed 2026-09-24) · Applies to: 2021.3–6.6 · Evidence: [doc]
  - Notes: Unity's CPU/GPU-bound example treats gpuFrameTime == 0 as "Indeterminate", which is what XR returns. Use XR stats for GPU time (U5-091).

- **U5-091** Per-frame XR stats come from `XRDisplaySubsystem`:
  - `TryGetAppGPUTimeLastFrame`
  - `TryGetCompositorGPUTimeLastFrame`
  - `TryGetDroppedFrameCount`
  - `TryGetFramePresentCount`
  - `TryGetDisplayRefreshRate`
  - `TryGetMotionToPhoton`

  Log dropped-frame deltas and app GPU time alongside ProfilerRecorder main-thread time to get CPU/GPU p99 in release builds. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem.html (accessed 2026-09-24) · Applies to: all versions (XR plug-in dependent) · Evidence: [doc]
  - Notes: Unit bug: OpenXR plugin 1.18.0-pre.2 (2026-06-16) fixed GPUAppLastFrameTime and GPUCompositorLastFrameTime being written in milliseconds instead of seconds. Values from OpenXR < 1.18 are in different units than ≥ 1.18. Normalize by plugin version. Whether the Meta/OpenXR provider fills every stat on Quest is [verify on device].

- **U5-092** OpenXR Latency Optimization sets where the frame wait happens. The Unity OpenXR 1.18 manual lists the default as Prioritize Rendering (minimizes simulate→submit time). Prioritize Input Polling minimizes input→submit time. It is build-time only; runtime changes are ignored. Set it via `OpenXRSettings.latencyOptimization` in an `IPreprocessBuildWithReport`. [C][T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/project-configuration.html (accessed 2026-09-24) · Applies to: OpenXR plugin 1.x · Evidence: [doc]
  - Notes: Meta's page (next finding) recommends Prioritize Input Polling for Quest. See Conflict U5-C2.

- **U5-093** Meta's Unity OpenXR settings page (updated 2026-05-11) recommends Prioritize Input Polling; there, `xrWaitFrame` runs on the main thread before simulation. Other recommendations on the page:
  - Use OpenXR Predicted Time: enable it if judder appears.
  - Additional Graphics Queue: off.

  OpenXR plugin 1.15.0-pre.1 added a validation rule steering Meta Quest builds to Prioritize Input Polling. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (accessed 2026-09-24); https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: OpenXR plugin 1.15+ with Meta Quest Support · Evidence: [doc]
  - Notes: With Input Polling, main-thread wait time appears at frame start (the XR wait) rather than in present. Read captures accordingly.

- **U5-094** The OpenXR plugin exposes thermal and performance state:
  - `XrPerformanceSettings.SetPerformanceLevelHint` (1.11+): PowerSavings, SustainedLow, SustainedHigh (default), Boost.
  - `OnXrPerformanceChangeNotification`: Normal / Warning / Impaired, per domain (Compositing / Rendering / Thermal).

  Log these alongside frame times so thermal throttling isn't mistaken for a code regression. [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: OpenXR plugin 1.11+ · Evidence: [doc]
  - Notes: Level policy belongs to the thermal/levels topic.

- **U5-095** Allocation fixes in the OpenXR plugin: 1.17.0-pre.2 fixed unnecessary allocations in OpenXRProjectionLayer (UUM-135657). Stay on a current plugin before chasing framework-owned GC.Alloc samples. [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: OpenXR < 1.17 · Evidence: [doc]
  - Notes: Latest stable on the access date is 1.18.0 (changelog date 2026-08-04; registry publish 2026-08-11). 1.19.0-pre.1 is the preview. The registry's current "latest" release declares Unity 6000.0 as its minimum, so 2021.3/2022.3 projects are held to older plugin lines.

- **U5-096** The Profiler Highlights module (6.0+; absent from the 2022.3 manual) labels frames CPU- or GPU-bound using FrameTiming data. Because FrameTimingManager has no GPU time in XR (U5-090), Highlights probably can't classify XR frames. [T]
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/ProfilerHighlights.html (accessed 2026-09-24) · Applies to: 6.0–6.6 · Evidence: [doc]
  - Notes: The XR limitation is inferred. [verify on device].

- **U5-097** Perfetto on Quest through Meta Quest Developer Hub:
  - Add the app's package name to Perfetto's "ATrace Apps". Unity emits ATrace instrumentation, and ProfilerMarkers appear in the trace from Development builds.
  - Callstack sampling needs a Development build, or symbol files supplied for stripped builds.
  - Perfetto puts app markers, CPU scheduling, clocks and GPU render stages on one timeline. Use it to see thread placement and preemption that the Unity Profiler can't show.

  [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Check job-worker core placement here (U5-034).

- **U5-098 / U1-057** Unity 6.6 adds an Android **Profileable Shell** build setting. It lets Android system services and shell tools profile release builds: Perfetto and simpleperf against near-shipping code without Development Build overhead. [T][C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]
  - Notes: On earlier versions, add `<profileable android:shell="true"/>` to a custom manifest. That route is not Unity-documented; [verify on device].
  - **Merged U1-057:** Profiling hooks added in 6.6: a Profileable Shell Android build setting, which lets Android system tools profile release builds; FrameTimingManager reporting GPU times from OpenXR devices (6000.6.0b1); and the Performance Testing package becoming a core package. [T][C]
    - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html ; https://unity.com/releases/editor/whats-new/6000.6.0b1 (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]

- **U5-100** Unity 6.6 Profiler adds screenshots per frame, which tie a hitch to what was on screen, and module pinning. The Frame Debugger shows constant-buffer values. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: 6.6+ · Evidence: [doc]
  - Notes: On-device screenshot capture overhead is not documented.

- **U5-101** Profiler warning markers that flag known hitches:
  - `AssetBundle.asset` / `allAssets` sync-load stalls
  - `AsyncUploadManager.AsyncBufferResized`: the async upload ring buffer grew
  - `Rigidbody.SetKinematic` on a non-convex MeshCollider
  - `Animation.AddClip` and related calls

  Search captures for these names first when chasing p99 spikes. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: AsyncBufferResized means the async upload buffer is too small (QualitySettings.asyncUploadBufferSize). The streaming topic owns sizing.

- **U5-102** An OpenXR/Meta Quest settings baseline for CPU-side consistency:
  - Multi-View render mode.
  - Offscreen Rendering Only enabled.
  - Depth Submission None unless the runtime needs depth (Space Warp or composition).

  These cut CPU work: one render pass for both eyes, no mirror blit. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (accessed 2026-09-24) · Applies to: OpenXR plugin 1.x · Evidence: [doc]
  - Notes: GPU details for these settings are in the rendering topics. Here they matter because Multi-View halves CPU draw submission compared with multi-pass.

## 11. Unity 6 mobile/XR optimization e-book guidance

### E-book status

- **U1-104** Unity's e-book "Optimize your game performance for mobile, XR, and the web in Unity (Unity 6 edition)" sits behind a form. Only the landing page could be read, so none of its recommendations or numbers are captured here. [T]
  - Source: https://unity.com/resources/mobile-xr-web-game-performance-optimization-unity-6 (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: Superseded by UNITY-GF1-007: the landing page's HTML links the PDF directly on Unity's asset CDN, and round 1 read it in full.

- ~~Known unknown: the e-book's recommendations and numbers are not captured.~~ Resolved in gap-fill round 1 (UNITY-GF1-007 to -017). The e-book is generic mobile/XR/web guidance. It contains no Quest-specific numbers, and every Quest-relevant claim is either already covered in sections 3-10 or recorded below with its conflicts.

### E-book content (gap-fill round 1)

- **UNITY-GF1-007** About the e-book: [T]
  - Title: "Optimize your game performance for mobile, XR, and the web in Unity (Unity 6 edition)".
  - Length: 100 pages. © 2024. The landing page's schema.org data gives a publication date of 2024-10-17. Unity's announcement blog (Thomas Krogh-Jacobsen) is dated 2024-11-11.
  - Scope: the XR chapter is 4 pages (pp. 97-100). Nothing in the book targets Quest hardware specifically.
  - Source: https://cdn.bfldr.com/S5BC9Y64/at/3mp8w3wk36k2k6mmj5pbbr/Optimize_your_game_performance_for_mobile__XR__and_the_web_in_Unity_Unity_6_edition_e-book.pdf ; https://unity.com/resources/mobile-xr-web-game-performance-optimization-unity-6 ; https://unity.com/blog/unity-6-game-optimization-guides (accessed 2026-09-24) · Applies to: Unity 6.0 (written against 6.0; predates 6.1-6.6 features) · Evidence: [doc]
  - Notes: The book predates the Meta Quest build profile (6.1), GSC, on-tile post-processing and Tile-Only Mode, so it cannot be cited for them. Treat it as a secondary source behind Meta's docs and the versioned Unity manual.

- **UNITY-GF1-008** The e-book's thermal rule of thumb for mobile is to use only about 65% of the available frame time, leaving time to cool down between frames. It gives about 22 ms at 30 fps and 11 ms at 60 fps as typical budgets. Devices can exceed this briefly (cutscenes, loading) but not for long. It also recommends profiling in short bursts and letting the device cool for 10-15 minutes between sessions. [C]
  - Source: e-book p. 19, "Account for device temperature" (PDF URL in UNITY-GF1-007) (accessed 2026-09-24) · Applies to: generic mobile; not XR-specific · Evidence: [doc]
  - Notes: Serves consistency (thermal decay). The book gives no XR number. Applied to Quest this would mean about 9.0 ms at 72 Hz, 7.2 ms at 90 Hz and 5.4 ms at 120 Hz (arithmetic, not a Unity or Meta figure). Meta's own headroom guidance is in the quest-perf dossier and takes precedence; see UNITY-GF1-C1. The 10-15 minute cool-down conflicts with the 20-30 minute thermal soak this project needs to measure thermal decay. Use cool-downs between A/B captures, not instead of soak tests.

- **UNITY-GF1-009** The e-book tells XR developers to assume Vsync is on regardless of the Quality setting. If a frame misses, the previous frame is held, which lowers effective fps. It states that most XR devices enforce Vsync at 90 Hz or higher. [C]
  - Source: e-book p. 43, "Vsync in XR, web, and mobile development" (accessed 2026-09-24) · Applies to: generic XR · Evidence: [doc]
  - Notes: The "90 Hz or higher" wording does not hold for Quest, where 72 Hz is a supported and common rate (see UNITY-GF1-C2). The rest (Vsync is runtime-enforced; `QualitySettings.vSyncCount` and `targetFrameRate` are ignored in VR) matches U5-008.

- **UNITY-GF1-010** The e-book's draw-call guidance for Unity 6: [T]
  - Enable the SRP Batcher.
  - Use static batching for non-moving meshes; it costs memory.
  - Use dynamic batching only with enough low-poly meshes (at most 300 vertices each and 900 vertex attributes), or it wastes CPU time searching for batches.
  - GRD works only with Forward+, APIs with compute support except OpenGL ES, and MeshRenderer GameObjects. It needs Graphics Settings > BatchRendererGroup Variants set to Keep All.
  - Use `Renderer.sharedMaterial`, not `Renderer.material`, to avoid breaking batches with instanced material copies.
  - Source: e-book pp. 49-52 (accessed 2026-09-24) · Applies to: 6.0 · Evidence: [doc]
  - Notes: Consistent with U1-016, U3-017, U3-018 and UNITY-GF1-001/-002. The book says GRD works "out of the box" on Vulkan mobile, but it does not mention GRD's XR constraints or the static-batching incompatibility (U3-031). Rely on section 5 for those.

- **UNITY-GF1-011** The e-book's URP rendering-path guidance: Forward is "generally recommended as default" for mobile. Forward+ (from 2022 LTS) culls lights spatially rather than per object, and removes the per-object light limit (the per-camera limit still applies). Deferred suits scenes with many dynamic lights. It also advises limiting dynamic lights in XR and using baked lighting and light probes. [T]
  - Source: e-book pp. 45-46, 53 (accessed 2026-09-24) · Applies to: 6.0, URP 17 · Evidence: [doc]
  - Notes: This is generic mobile advice. For Quest projects using GRD, Forward+ is required (X-C9). Meta's best-practices page accepts Forward or Forward+ (U4-007). Choose the path from the GRD decision and the light count, not from this line.

- **UNITY-GF1-012** The e-book says each enabled camera has overhead even when it renders nothing, up to 1 ms of CPU time per camera on lower-end mobile platforms. [T]
  - Source: e-book p. 60, "Limit use of cameras" (accessed 2026-09-24) · Applies to: generic mobile, Unity 6.0 · Evidence: [doc] [verify on device]
  - Notes: Serves throughput. The 1 ms is an upper bound for unnamed low-end phones, not a Quest measurement. On Quest, measure per-camera main- and render-thread cost with the Profiler (the per-camera render sample in the CPU hierarchy, camera enabled vs disabled) on Quest 2.

- **UNITY-GF1-013** The e-book's STP setup path is URP Asset > Quality > Upscaling Filter > Spatial-Temporal Post-Processing. [T]
  - Source: e-book pp. 60-61 (accessed 2026-09-24) · Applies to: 6.0+ · Evidence: [doc]
  - Notes: The book presents STP as suitable from mobile upward, with no XR caveat. The dossier's STP finding (U1-042) and GLES exclusion (U1-095) govern Quest use. Do not cite the e-book as evidence that STP is viable on Quest.

- **UNITY-GF1-014** The e-book's physics advice: [C]
  - The default Fixed Timestep is 0.02 s (50 Hz).
  - A long frame (40 ms or more) makes Unity run two physics steps next frame to catch up. This can spiral on low-end platforms until Maximum Allowed Timestep is hit and physics updates are dropped.
  - On lower-end platforms, raise Fixed Timestep to slightly more than the frame time (for example 0.035 s at 30 fps).
  - If physics is unused, turn off Auto Simulation and Auto Sync Transforms.
  - Use `RaycastCommand` to batch queries on the job system.
  - Source: e-book pp. 42, 80-81, 89 (accessed 2026-09-24) · Applies to: 6.0 (the default applies to all versions) · Evidence: [doc]
  - Notes: The 0.02 s default matches U5-050. The "larger than frame time" advice conflicts with the community "1/refresh" practice in U5-C4; see UNITY-GF1-C3. The spiral mechanism is the hitch path to watch for. Inference, not in the book: lowering Maximum Allowed Timestep bounds how many catch-up steps one slow frame can trigger, at the cost of physics running slower than real time during the spike.

- **UNITY-GF1-015** The e-book's XR chapter: [T]
  - Set Render Mode to Single Pass Instanced in the OpenXR plugin settings.
  - Unity 6 integrates foveated rendering for Oculus XR and OpenXR (and PS VR2).
  - Use the XR Interaction Toolkit's event-driven input to avoid polling.
  - It lists the "Oculus Performance HUD" and SteamVR's tool as XR-specific profilers.
  - Source: e-book pp. 97-100 (accessed 2026-09-24) · Applies to: 6.0 · Evidence: [doc]
  - Notes: Nothing here is new against the dossier. The profiler list is dated: Meta's current tools are OVR Metrics Tool, MQDH + Perfetto and the RenderDoc Meta Fork (section 10). Do not cite the book for Quest tooling. For Oculus XR vs OpenXR plugin choice on Unity 6, see U1-009 (corrected in this round).

- **UNITY-GF1-016** The e-book's audio Load Type table: [T][C]
  - Small clips (< 200 KB): Decompress On Load, or Compressed In Memory with ADPCM (a fixed 3.5:1 ratio that is cheap to decode).
  - Medium clips (≥ 200 KB): Compressed In Memory if memory is the priority, or Decompress On Load if CPU is.
  - Large clips (> 350-400 KB): Streaming, which carries about 200 KB of overhead per clip.
  - Also: Force To Mono for positional sounds, Vorbis for most sounds (MP3 for non-looping), and unload muted AudioSources.
  - Source: e-book pp. 74-75 (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Serves consistency (decode spikes) and memory. The dossier had no audio findings. On Quest, the choice matters most for many simultaneous Compressed In Memory voices decoding on the audio thread. No Quest cost number exists: measure `Audio` CPU in the Profiler with the worst-case voice count.

- **UNITY-GF1-017** The e-book's asset and GC guidance: [T][C]
  - Use ASTC for mobile, XR and web. Its example shows an uncompressed texture using almost 26 times the memory of a compressed one.
  - Disable Read/Write on textures and meshes, and disable mipmaps on UI textures.
  - Use `AssetPostprocessor` to enforce import settings.
  - Enable the Incremental GC to spread collections over several frames, and verify the benefit with the Profile Analyzer.
  - Source: e-book pp. 24, 28-31 (accessed 2026-09-24) · Applies to: all versions · Evidence: [doc]
  - Notes: Consistent with section 9 and U5-007. The 26x figure is one illustrative texture, not a rule.

### Companion XR e-book (gap-fill round 2)

- **UNITY-GF2-004** Unity's companion e-book "Create virtual and mixed reality experiences in Unity" (the one the optimization e-book refers to): [T]
  - Edition: "UNITY 2022 LTS EDITION", 121 PDF pages (numbered "of 120"), ©2024. The landing page's schema.org data gives a publication date of 2024-06-27.
  - It is a workflow book: XR Interaction Toolkit, the VR and MR templates, AR Foundation, visionOS. It has **no XR-specific frame-time, draw-call, triangle or memory numbers**.
  - Its example VR project targets Meta Quest 2 on Unity 2022 LTS + URP + OpenXR.

  Its few performance statements:
  - Choose the **Performant** quality level (and its "Performant" URP Asset) as the project default in the VR template. The book says this asset reduces draw calls, optimizes shader execution and gives more control over lighting and shadows, but lists no settings.
  - Lightmap worked example: one 512x512 lightmap for the crypt scene, reached by lowering lightmap texel density from 40 to 20 after a 512 bake had split into three lightmaps. Each extra lightmap adds draw calls.
  - A generic Profiler checklist: GPU render time, draw calls, batches and SetPass calls, GC spikes, frame-rate stability, audio DSP, Canvas rebuilds.
  - Single-pass instanced rendering issues one draw call for both eyes, which lowers CPU cost (stated in the visionOS chapter).
  - Source: https://unity.com/resources/create-virtual-mixed-reality-experiences-unity ; https://cdn.bfldr.com/S5BC9Y64/at/88s95mhhwcsshcgrwbm7c5g/Create_virtual_and_mixed_reality_experiences_in_Unity_e-book.pdf (pp. 29-31, 66-72, 84-87, 104) (accessed 2026-09-24) · Applies to: Unity 2022.3 LTS (URP 14), Quest 2 in the worked example · Evidence: [doc]
  - Notes: For numbers, cite Meta's docs and the versioned Unity manual, not this book. What the reader can use: the VR template's "Performant" quality/URP asset is a starting point to audit against section 3 (HDR, MSAA, depth/opaque texture, shadows). It is not a verified Quest configuration. The lightmap-count point (fewer lightmap atlases means fewer material/lightmap splits, so fewer batches) serves throughput and matches section 7. No conflicts with the dossier were found.

## Conflicts

Every conflict recorded in the topic notes is kept under its original ID. Conflicts found only when the five topics were read together carry X-C IDs. Each side lists the findings it rests on, with their source URLs and evidence tags.

### U1-C1: UUM-93226 status label

- **Old tracker page (Wayback, 2025-12-09): "Third Party Issue".** U1-075 [doc]: https://issuetracker.unity.com/api/v1.0/issues/1364 ; https://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3
- **New tracker API: every port status 4 (Won't Fix) and state Closed.** https://issuetracker.unity.com/api/v1.0/issues/1364 [doc]
- **Assessment:** Both agree there is no Unity fix version. The difference is labeling only.
- **Status:** Resolved: treat as closed, blamed on Qualcomm/Meta, no engine fix.

### U1-C2: Vulkan vs GLES on Quest

- **Unity's untethered-XR guide (6.6) calls Vulkan more stable and faster than GLES; the Meta Quest build profile defaults to Vulkan; Meta calls Vulkan required.** U1-066 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html | U1-053 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html | U2-094 [doc]: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/
- **UUM-93226, closed without a fix, reproduces Vulkan slower and stuttering more than GLES on Quest 2 and 3 with many meshes.** U1-074 [measured]: https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 ; https://issuetracker.unity.com/issues/1364 | U1-075 [doc]: https://issuetracker.unity.com/api/v1.0/issues/1364 ; https://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 | U1-077 [community] [verify on device]: https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926
- **Assessment:** Unity expects a Meta OS fix for the Qualcomm visibility-stream bug, but none has been confirmed. GLES also keeps losing features (U1-094, U1-095).
- **Status:** Unresolved. A/B GLES and Vulkan on the actual content and current Horizon OS, with Optimize Buffer Discard on (U1-076). [verify on device]

### U1-C3: Oculus XR Plugin on Unity 6.x

- **Meta marks the Oculus XR Plugin deprecated: Unity 2022 or later, Meta XR SDK v73 or earlier only; OpenXR needs Unity 6+ and SDK v74+.** (Corrected in gap-fill round 1; this previously read "Unity versions before 6".) U1-009 [doc]: https://developers.meta.com/horizon/documentation/unity/unity-project-setup/
- **Unity kept bundling and patching Oculus XR 4.5.x on 6.0 and 6.3 and deprecated it only in 6.5.** U1-091 [doc]: https://unity.com/releases/editor/whats-new/6000.5.0b4 ; https://unity.com/releases/editor/whats-new/6000.0.49f1 ; https://unity.com/releases/editor/whats-new/6000.0.57f1
- **Assessment:** On 6.0-6.4 the plugin still works, and Meta's stated range does not exclude Unity 6. But it caps the Meta XR SDK at v73, and Meta has deprecated the plugin. Unity deprecated it in 6.5.
- **Status:** Resolved: on Unity 6.x use OpenXR (U1-092, U1-093).

### U1-C4: Forward+ XR support on 2022.3

- **6.0 What's New lists "XR rendering support for Forward+" as new since 2022 LTS.** U1-032 [doc] [verify on device]: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/rendering/forward-plus-rendering-path.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html
- **2022.3.16f1 already added foveated rendering in Forward+, and the URP 14 Forward+ page claims no limitations versus Forward.** U1-082 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html ; https://unity.com/releases/editor/whats-new/6000.0.22f1
- **Assessment:** How complete Forward+ was in XR on 2022.3 is unclear.
- **Status:** Unresolved. Test Forward+ in stereo on 2022.3 before relying on it; prefer 6.x for Forward+ on Quest.

### U1-C5: Compatibility Mode removal: 6.3 vs 6.4

- **6.3 upgrade guide says Compatibility Mode was removed in 6.3.** U1-025 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity63.html ; https://unity.com/releases/editor/whats-new/6000.3.0a2
- **It is still reachable in 6.3 through `URP_COMPATIBILITY_MODE`; the 6.4 guide says it was fully removed in 6.4.** U1-026 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity64.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html
- **Assessment:** Both are true: hidden in 6.3, gone in 6.4.
- **Status:** Resolved: 6.3 is the last version where legacy passes run, only behind the define.

### U1-C6: UUM-113364 (foveation off with MSAA on Vulkan): standalone Quest affected?

- **The fix note limits the bug to "PC or linked XR".** U1-084 [doc] [verify on device]: https://unity.com/releases/editor/whats-new/6000.4.0b9
- **Unity's untethered guide recommends MSAA and foveation together for standalone Quest.** U1-066 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html
- **Assessment:** Unknown whether standalone Quest on 6.3 or earlier lost foveation with MSAA on.
- **Status:** Unresolved. Check the foveation level (OVR Metrics, or the fragment density map attachment in RenderDoc) with MSAA on and off on 6.3. [verify on device]

### U2-C1 / U3-C7: MSAA level: 2x vs 4x (and its effect on A2C and framebuffer-fetch cost)

- **Unity: 2x is a good balance (untethered XR page); the generic URP performance page says reduce or disable MSAA.** U2-006 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html | U2-090 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html
- **Meta: 4x is "extremely cheap", recommended, and the cap; the best-practices page points to 4x when not using OVRManager's recommendation.** U2-092 [doc]: https://developers.meta.com/horizon/documentation/unity/gpu-improved-algorithms/ | U2-093 [measured]: https://developers.meta.com/horizon/documentation/native/android/mobile-msaa-analysis/
- **Assessment:** The only published MSAA numbers are Quest 1 era. A2C (U3-061) and framebuffer-fetch cost (U3-063) scale with sample count, so the choice also moves shader cost. U3-C7 and U2-C1 record the same disagreement and are merged here.
- **Status:** Unresolved. Measure 2x vs 4x GPU ms on Quest 2 and Quest 3 with the shipping shaders. [verify on device]

### U2-C2: MSAA and on-tile rendering

- **6.6 docs: MSAA "breaks on-tile rendering"; Tile-Only Mode lists MSAA as unsupported; On-Tile Validation disables the MSAA option.** U2-032 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html | U2-017 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html | U2-025 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html
- **Unity staff (Jan 2026): on Quest/Vulkan a device build runs without intermediates into an MSAA backbuffer; 6.2 enabled VK_QCOM shader resolve for Quest MSAA.** U2-051 [community]: https://discussions.unity.com/t/performant-and-energy-efficient-rendering-with-render-graph-and-on-tile-post-processing-for-untethered-xr-in-unity-6-3/1703007 | U2-052 [doc]: https://docs.unity3d.com/6000.2/Documentation/Manual/WhatsNewUnity62.html
- **Assessment:** Likely reconciliation: plain MSAA with no post-processing stays merged; MSAA plus on-tile post-processing or Tile-Only validation is not supported.
- **Status:** Partly resolved; confirm in the on-device Render Graph Viewer. [verify on device]

### U2-C3: Resolution control: eyeTextureResolutionScale vs URP Render Scale

- **Unity: XRSettings.eyeTextureResolutionScale isn't supported in URP; use URP Render Scale (reallocating) or renderViewportScale (per frame). URP re-applies renderScale per camera.** U2-044 [doc]: https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRSystem.cs | U2-046 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html
- **Meta's render-scale page: set eyeTextureResolutionScale and, in URP, possibly also the asset renderScale.** U2-049 [doc]: https://developers.meta.com/horizon/documentation/unity/os-render-scale/
- **Assessment:** URP source re-applies renderScale to scaleOfAllRenderTargets per camera, so the asset value probably wins.
- **Status:** Unresolved. Log the applied eye-texture size on device after setting each knob. [verify on device]

### U2-C4: Stale Store Actions and Native RenderPass documentation in 6.x

- **The 6.6 URP Asset page still documents Store Actions; the 6.6 Renderer and performance pages still describe or recommend Native RenderPass.** U2-005 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html | U2-090 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html
- **Source marks Store Actions obsolete from 6000.0 and a compile error from 6000.4; Native RenderPass shows only in Compatibility Mode (6.0-6.3) and is gone from 6000.5 source.** U2-024 [doc]: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/urp-universal-renderer.html | U1-026 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity64.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html
- **Assessment:** Documentation lag. Under Render Graph both are superseded by the native pass compiler.
- **Status:** Resolved: follow source; ignore both settings on 6.4+.

### U2-C5: Tile-compatible post effects: 11 (Meta) vs 5 (Unity)

- **Meta's subpass guide lists 11 compatible effects; Meta's fork keeps integrated post-processing on.** U2-085 [doc]: https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ | U2-084 [doc]: https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/
- **Unity's on-tile PP lists 5 (color grading, vignette, tonemapping, dithering, film grain) and requires integrated post-processing off plus the renderer feature.** U2-074 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/xr-graphics-on-tile-post-processing.html | U2-075 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-post-processing.html
- **Assessment:** Different implementations: many of Meta's 11 fold into Unity's LUT-based color grading. The setup rules differ by path.
- **Status:** Resolved by path: use Meta's list only on the Meta fork, Unity's list on stock URP 6.3+.

### U2-C6: HDR and direct rendering to the eye texture

- **Unity's XR resolution page says URP renders directly to the eye texture "when you enable HDR".** U2-046 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html
- **URP 14 source and the tile pages say HDR forces an intermediate texture.** U2-030 [doc]: https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderer.cs | U2-002 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html
- **Assessment:** Likely a documentation error.
- **Status:** Resolved in favour of source: keep HDR off on Quest.

### U2-C7: Post-processing guidance by Unity version

- **Unity's Meta OpenXR 2.6 page and the pre-6.3 untethered page say disable post-processing.** U2-091 [doc]: https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/get-started/graphics-settings.html
- **The 6.3+ untethered page recommends on-tile post-processing.** U2-080 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html | U2-074 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/xr-graphics-on-tile-post-processing.html
- **Assessment:** Both are right for their versions.
- **Status:** Resolved: skills must branch on version (off before 6.3; on-tile post from 6.3).

### U3-C1: Static batching on Quest

- **Unity 6.6: disable static batching in URP; it isn't compatible with BRG or GRD.** U3-017 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html
- **Meta: Quest 2 is draw-call sensitive; batch geometry.** U3-021 [doc]: https://developers.meta.com/horizon/resources/device-optimization-comparison/
- **Assessment:** Both true in context. With Vulkan and GRD on Unity 6, disable static batching and let GRD instance. On GLES, on 2021.3/2022.3, or when GRD's GPU overhead loses on device (U3-034), static batching remains right.
- **Status:** Resolved by context; decide by device A/B.

### U3-C2: Depth priming with GRD

- **Unity's GRD performance page suggests Depth Priming Auto/Forced to curb overdraw.** U3-036 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html
- **Unity's untethered-XR page: disable depth priming on XR; LRZ covers it.** U2-020 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/urp-universal-renderer.html | U3-058 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html
- **Assessment:** The GRD advice is explicitly scoped to non-tiled GPUs.
- **Status:** Resolved: follow the XR page on Quest; verify overdraw in RenderDoc if GRD merges many overlapping objects.

### U3-C3: Whether GRD helps mobile XR

- **Unity 6.6 warns GRD raises GPU load, hitting lower-end mobile and VR hardest; a PC forum user saw CPU and GPU regress.** U3-034 [doc] [verify on device]: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html | U3-039 [community]: https://discussions.unity.com/t/resident-drawer-performance/1554861
- **Google's Android XR guidance recommends GRD plus GPU occlusion; 200 trees went to 5-10 draws.** U3-038 [doc]: https://unity.com/releases/editor/whats-new/6000.0.0 ; https://developer.android.com/develop/xr/unity/performance/gpu-rendering | U3-098 [measured]: https://android-developers.googleblog.com/2025/10/optimizing-performance-for-android-xr.html
- **Assessment:** No Quest measurement exists.
- **Status:** Unresolved. A/B per project on Quest 2 and Quest 3. [verify on device]

### U3-C4: GSC automatic fallback version

- **The 6.x "other prewarm methods" page says the GLES/DX11 fallback is available in 6.1 and later.** U3-082 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/shader-prewarm-other.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-introduction.html
- **6000.0.55f1 release notes add a GSC fallback to legacy SVC warmup on platforms without parallel PSO compilation.** U3-083 [doc]: https://unity.com/releases/editor/whats-new/6000.0.0 ; https://unity.com/releases/editor/whats-new/6000.0.55f1 ; https://unity.com/releases/editor/whats-new/6000.5.0 ; https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.GraphicsStateCollection.html | U1-048 [doc]: https://unity.com/releases/editor/whats-new/6000.0.55f1 ; https://unity.com/releases/editor/whats-new/6000.0.74f1
- **Assessment:** Likely a 6.1 feature later backported to 6.0.55+.
- **Status:** Partly resolved; verify on 6.0 LTS with GLES before relying on it.

### U3-C5: Precision model naming: Uniform vs Unified

- **The 16-bit precision page calls the mode "Uniform".** U3-051 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html
- **Player Settings labels it "Unified".** U3-052 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/SL-Use16BitPrecisionInShaders.html
- **Assessment:** Same setting.
- **Status:** Resolved: naming only.

### U3-C6: Meta Shader Binary Cache (SBC) status

- **Meta marks automated SBC deprecated and unmaintained, replacement in development; the same page still documents opt-in and says Unity apps may or may not be processed.** U3-097 [doc]: https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ | U3-096 [doc]: https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/
- **Assessment:** Self-contradictory single source.
- **Status:** Resolved for planning: treat SBC as non-existent; ship your own warmup.

### U4-C1: Loading strategy: synchronous vs async

- **Legacy Meta Android page: avoid async level loading, fade to black and load synchronously.** U4-092 [doc]: https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/
- **The same page's startup advice (load the main scene in the background), Meta's 2021 hitch blog (LoadSceneAsync with allowSceneActivation), and Unity's AUP/backgroundLoadingPriority guidance.** U4-091 [doc]: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ ; https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ | U4-085 [doc] [verify on device]: https://developers.meta.com/horizon/blog/avoiding-hitches-when-loading-scenes-in-unity/ | U4-078 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/LoadingTextureandMeshData.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/LoadingTextureandMeshData-make-compatible.html | U4-083 [doc]: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Application-backgroundLoadingPriority.html
- **Assessment:** The legacy advice is stale.
- **Status:** Resolved: async loading behind a fade or compositor loading screen.

### U4-C2: Lightmap directionality

- **Legacy Meta Android page: Non-Directional lightmaps.** https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ [doc, possibly stale]
- **Unity default Directional; about 2x memory plus an extra sample.** U4-039 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-reference.html ; https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/
- **Assessment:** Meta's current pages don't restate the recommendation.
- **Status:** Unresolved: decide by measured memory and GPU cost, and whether baked normal-map detail matters.

### U4-C3: Soft shadow Low quality tap count

- **6000.3 URP Asset docs: Low is 4 PCF taps.** U4-025 [doc] [verify on device]: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/shadows-optimization.html
- **URP 14.0.3 changelog: Low is PCF 3x3 with fixed offsets.** URP 14.0.3 changelog (cited in U4-025 notes) [doc]
- **Assessment:** Both describe a cheap mobile filter; tap counts differ, possibly by version.
- **Status:** Unresolved: read the version's `Shadows.hlsl`.

### U4-C4: Anisotropic filtering on Quest

- **Meta 2018: disable; Meta legacy page: one lookup per fragment; Meta 2024: trilinear or anisotropic.** U4-055 [doc]: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ ; https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ ; https://developers.meta.com/horizon/blog/tech-note-unity-settings-for-mobile-vr/
- **Unity: anisotropic filtering increases rendering time.** U4-056 [doc] [verify on device]: https://docs.unity3d.com/6000.3/Documentation/Manual/class-QualitySettings.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/texture-type-default.html
- **Assessment:** The 2018 reason (Mali/Exynos lacked support) does not apply to Adreno.
- **Status:** Resolved as method: use Per Texture mode and measure.

### U4-C5: Per-light soft shadow quality

- **The URP manual still describes per-light soft shadow quality overrides.** U4-025 [doc] [verify on device]: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/shadows-optimization.html
- **URP 17.0.0 changelog and a Unity staff post: per-light levels are disabled or ignored on Quest.** U4-026 [doc]: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/changelog/CHANGELOG.html | U4-027 [community]: https://discussions.unity.com/t/meta-quest-shadows-unsmoothed-low-resolution-regardless-of-settings/1552250 | U1-039 [doc]: https://unity.com/releases/editor/whats-new/6000.0.0b11
- **Assessment:** Manual lag.
- **Status:** Resolved: on Quest only the URP Asset's global quality takes effect.

### U4-C6: SH Evaluation Mode Auto on mobile

- **URP 17.0.2 changelog: Auto picks Per Vertex on mobile.** U4-013 [doc]: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipelineCore.cs
- **6000.3 source enables APV vertex sampling only for explicit Per Vertex or Mixed.** U4-014 [doc] [verify on device]: https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs ; https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/Data/UniversalRenderPipelineAsset.cs
- **Assessment:** Documentation-versus-source mismatch; Auto may leave APV sampling per pixel on Quest.
- **Status:** Unresolved. Set Per Vertex or Mixed explicitly, or inspect the compiled keywords on device. [verify on device]

### U4-C7: Shadows on Quest

- **Legacy Meta page: no shadow buffers; Meta 2018: Hard Shadows Only or disable; Meta 2024: disable only near draw-call or geometry limits.** U4-009 [doc]: https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ | U4-034 [doc]: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ ; https://developers.meta.com/horizon/blog/tech-note-unity-settings-for-mobile-vr/
- **Unity documents tuned realtime shadows with cascades, distance and quality levels.** U4-028 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html | U4-029 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/shadow-resolution-urp.html | U4-032 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/shadows-optimization.html
- **Assessment:** Guidance has loosened over time.
- **Status:** Resolved: treat shadows as a measured budget item, not a blanket ban.

### U4-C8: Texture memory

- **Legacy Meta page: texture memory nearly free relative to other costs.** https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ [doc, possibly stale]
- **2026 Meta device comparison: cut texture resolution or mip levels on Quest 2 (6 GB).** U4-053 [doc]: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ ; https://developers.meta.com/horizon/resources/device-optimization-comparison/
- **Assessment:** Current guidance supersedes the legacy page.
- **Status:** Resolved: texture memory is a real budget on Quest 2.

### U5-C1: Graphics Jobs on Quest: disable vs enable Legacy

- **Meta XR Core SDK v68 Project Setup Tool recommended disabling Graphics Jobs; a 2021 Unity staff reply says Graphics Jobs disables Adreno LRZ/HSR.** U5-036 [doc]: https://github.com/icosa-mirror/com.meta.xr.sdk.core | U5-038 [community]: https://discussions.unity.com/threads/vulkan-bug-quest-2-urp-graphics-jobs-no-multithreaded-rendering-slow.1208908/
- **Meta's 2024-11-11 doc and SDK v78/v83 recommend Legacy Graphics Jobs with MT rendering on Unity >= 2022.3.35f1.** U5-035 [doc]: https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/
- **Assessment:** Version-gated. The LRZ claim may still hold.
- **Status:** Partly resolved: on 2022.3.35f1+ and 6.x try Legacy with MT rendering, measure main-thread and GPU time; never enable Graphics Jobs without MT rendering. [verify on device]

### U5-C2: OpenXR Latency Optimization default and recommendation

- **Unity OpenXR manual (1.18): default Prioritize Rendering.** U5-092 [doc]: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/project-configuration.html
- **Meta recommends Prioritize Input Polling; OpenXR 1.15.0-pre.1 added a Meta Quest validation rule for it.** U5-093 [doc]: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html
- **Assessment:** Different defaults for different goals; Meta's rule is Quest-specific.
- **Status:** Resolved for Quest: follow Meta and the validation rule; read wait placement in captures accordingly.

### U5-C3: Incremental GC idle-time scheduling vs XR frame control

- **Unity: incremental GC uses end-of-frame idle time only when vSyncCount or targetFrameRate is set.** U5-008 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/performance-incremental-garbage-collection.html ; https://docs.unity3d.com/6000.6/Documentation/ScriptReference/QualitySettings-vSyncCount.html | U4-097 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/performance-incremental-garbage-collection.html
- **Unity: XR ignores both settings.** U5-022 [doc]: https://docs.unity3d.com/6000.6/Documentation/ScriptReference/QualitySettings-vSyncCount.html
- **Assessment:** The docs don't say whether the XR frame wait counts as idle time.
- **Status:** Unresolved. Check Timeline placement of incremental GC slices on device. [verify on device]

### U5-C4: fixedDeltaTime alignment on Quest

- **Unity default: 0.02 s.** U5-050 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-frequency.html
- **Community and old Oculus sample code: 1/refresh; Meta XR Core SDK uses fixedDeltaTime for pose prediction.** U5-051 [community]: https://communityforums.atmeta.com/discussions/dev-unity/time---fixed-timestep--hz-values-for-oculus-devices-in-unity/751740 ; https://github.com/sebastianstarke/AI4Animation | U5-052 [doc]: https://github.com/icosa-mirror/com.meta.xr.sdk.core/blob/main/Scripts/OVRInput.cs
- **A 2024 Unity forum report: changing fixedDeltaTime had no visible effect on Quest.** U5-053 [community]: https://discussions.unity.com/t/change-fixeddeltatime-for-meta-quest/1517687
- **Assessment:** No Meta or Unity doc resolves it.
- **Status:** Unresolved. Measure physics steps per frame and judder at 72/90/120 Hz with each setting. [verify on device]

### U5-C5: Optimized Frame Pacing with XR

- **Unity: generic benefit claim.** U5-023 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html
- **Community: mixed reports (no issues vs intermittent hitches and ignored refresh-rate changes); Cardboard: a Swappy pose-jump bug.** U5-024 [community]: https://discussions.unity.com/t/optimized-frame-pacing-for-oculus-quest-2-and-other-android-headsets/860072
- **Assessment:** No XR-specific documentation.
- **Status:** Unresolved; default off for XR pending measurement of stale frames on vs off. [verify on device]

### U5-C6: Job worker count on Quest

- **Unity: workers default to JobWorkerMaximumCount and adapt on Android.** U5-032 [doc]: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerCount.html | U5-033 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/android-thread-configuration.html
- **Community: Quest 1/2 expose only about 3 cores to apps and Unity over-subscribes.** U5-034 [community]: https://thegamedev.guru/unity-performance/job-system-excessive-multithreading/ ; https://discussions.unity.com/threads/vulkan-bug-quest-2-urp-graphics-jobs-no-multithreaded-rendering-slow.1208908/
- **Assessment:** No current measurement.
- **Status:** Unresolved. Log JobWorkerCount at startup and check thread placement in Perfetto. [verify on device]

### X-C1: Vulkan GSC warmup fix on the LTS lines (new, cross-topic U1/U3)

- **U1: UUM-121231 "Fixed GraphicsStateCollection warmup for Vulkan" appears only in 6000.4.0a4; no 6.0/6.3 backport found, so Vulkan GSC warmup on 6.0 and 6.3 LTS may not remove hitches.** U1-047 [doc] [verify on device]: https://unity.com/releases/editor/whats-new/6000.4.0a4
- **U3: the same line was a 6.4-alpha-only regression (first seen 6000.4.0a1) that did not affect LTS lines; 6.0 beta fixes already made the async PSO system work.** U3-091 [doc]: https://unity.com/releases/editor/whats-new/6000.0.0
- **Assessment:** Both read release notes. U3's reading (regression introduced and fixed inside 6.4 alphas) would make the LTS lines safe; U1 found no evidence either way.
- **Status:** Unresolved. On 6.0 and 6.3 LTS, run a cold first session with and without GSC warmup and count stale frames at first appearance of each material. [verify on device]

### X-C2: Frame Debugger on Quest (new, cross-topic U1/U3/U2)

- **U1: the XR compatibility table says the Frame Debugger is not supported on Meta/Oculus devices, only the mock HMD.** U1-058 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html
- **U3/U2: diagnose SRP Batcher and batch breaks with the Frame Debugger.** U3-002 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html | U3-008 [doc]: https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-1/ | U3-011 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Profile.html | U2-090 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html
- **Assessment:** Batch-break reasons are CPU-side and largely device-independent, so the Editor (or mock HMD) Frame Debugger is still useful. It cannot show device-only behavior (multiview output, tile passes, foveation).
- **Status:** Resolved by scope: use the Frame Debugger in the Editor for batching; use RenderDoc Meta Fork, the Meta tools or the on-device Render Graph Viewer for device captures.

### X-C3: FrameTimingManager GPU time on XR (new, cross-topic U1/U5)

- **U5: FrameTimingManager's XR support is "Partial"; CPU render-thread and GPU frame time are not measured on XR (Vulkan and GLES).** U5-090 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/frame-timing-manager.html
- **U1: 6.6 adds FrameTimingManager GPU times from OpenXR devices (6000.6.0b1).** U1-057 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html ; https://unity.com/releases/editor/whats-new/6000.6.0b1
- **Assessment:** Likely a version difference: the manual page may predate the 6.6 change. Before 6.6, use XRDisplaySubsystem stats (U5-091).
- **Status:** Unresolved for 6.6. Log gpuFrameTime on a 6.6 Quest build; if nonzero, compare with OVR Metrics GPU time. [verify on device]

### X-C4: Meta triangle budgets per headset (new, cross-topic U3/U4/U5)

- **U3/U4: Meta's device comparison page (2026-05-11): Quest 3 under 200 draw calls and 1.5M triangles; Quest 2 under 100 and 750K.** U3-003 [doc] [verify on device]: https://developers.meta.com/horizon/resources/device-optimization-comparison/ | U4-076 [doc]: https://developers.meta.com/horizon/resources/device-optimization-comparison/ ; https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/
- **U5 lead (not a finding): Meta's unity-perf page gives Quest 3/3S 1.3-1.8M triangles and Quest 2 750k-1M.** https://developers.meta.com/horizon/documentation/unity/unity-perf/ [doc]
- **Assessment:** Two Meta pages give different ranges; the ranges overlap. Neither says whether a multiview draw counts once or twice.
- **Status:** Unresolved. Use the lower bound of each as a starting budget and measure render-thread and GPU ms. Re-read the unity-perf page to capture its exact wording.

### X-C5: Vulkan swapchain buffer count (new, cross-topic U1/U5)

- **U5: the doc says not to use "Number of swapchain buffers" on Android; in OpenXR the runtime owns the eye swapchains.** U5-025 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html
- **U1: UUM-148724 made the setting take effect only from 6000.0.83f1, 6000.3.24f1 and 6000.6.0f1 (it was ignored before).** U1-068 [doc]: https://unity.com/releases/editor/whats-new/6000.0.83f1 ; https://unity.com/releases/editor/whats-new/6000.3.24f1
- **Assessment:** Not contradictory in practice: both say it probably affects only the Unity-managed surface on Quest, and both leave the default.
- **Status:** Resolved: leave the default; after the fix patches, do not change it without a latency measurement. [verify on device]

### X-C6: Visible additional-light limit on GLES Quest builds (new, cross-topic U1/U4)

- **U4: per-camera visible additional lights are 32 on mobile and 16 on GLES 3.0 and earlier; Quest (Vulkan or GLES 3.2) is in the 32 bucket.** U4-005 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/lighting/light-limits-in-urp.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/urp/lighting/light-limits-in-urp.html
- **U1: on 6.6, upgraded projects get "Use OpenGL ES 3.0 shaders" on automatically, which keeps MAX_VISIBLE_LIGHTS at 16; turning it off gives 32 and more shader work. UUM-148728 forced 32 on GLES by mistake before 6000.6.0f1.** U1-094 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html | U1-040 [doc]: https://unity.com/releases/editor/whats-new/6000.6.0f1 ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html
- **Assessment:** On GLES the limit depends on the shader level, not the device. U4's "32 on Quest" holds for Vulkan and for GLES with ES3.1 shaders.
- **Status:** Resolved by version and setting.

### X-C7: First version of the Meta Quest shader optimizations (new, cross-topic U1/U2/U3)

- **U2: build-profile shader optimizations are 6.1+ (expanded in 6.5/6.6).** U2-056 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html | U2-012 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html
- **U1/U3: the optimizations and `UNITY_PLATFORM_META_QUEST` arrived in 6.5; the manual page exists only in 6.5+ manuals.** U1-036 [doc] [verify on device]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html | U3-066 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html ; https://unity.com/releases/editor/whats-new/6000.5.0
- **Assessment:** The Meta Quest build profile is 6.1+ (U1-053); the shader optimizations are 6.5+.
- **Status:** Resolved: build profile 6.1+, shader optimizations 6.5+.

### X-C8: Orthographic-camera keyword spelling (new, cross-topic U1/U2/U3)

- **U1/U2: `_META_QUEST_ORTHO_PROJ`.** U1-037 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html | U2-056 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html
- **U3: `META_QUEST_ORTHO_PROJ`.** U3-069 [doc] [verify on device]: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html ; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/Shaders/Lit.shader
- **Assessment:** Quick source check during synthesis (accessed 2026-09-24): master Lit.shader declares `#pragma multi_compile _ META_QUEST_ORTHO_PROJ`, with no leading underscore, next to `META_QUEST_LIGHTUNROLL` and `META_QUEST_NO_SPOTLIGHTS_LIGHT_LOOP`. The underscore form may come from the manual page or a transcription.
- **Status:** Resolved for master source: use `META_QUEST_ORTHO_PROJ` in Keyword Declaration Overrides. Re-check the 6000.5/6000.6 staging branches before shipping. Source: https://raw.githubusercontent.com/Unity-Technologies/Graphics/master/Packages/com.unity.render-pipelines.universal/Shaders/Lit.shader [doc]

### X-C9: GRD rendering-path requirement (new, cross-topic U1/U3/U4)

- **U4 (6000.3 page): GRD requires Forward+ and compute.** U4-044 [doc] [verify on device]: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/gpu-resident-drawer.html
- **U1/U3: on 6.6 (and 6.1+ per U3) GRD requires Forward+ or Deferred+.** U1-016 [doc]: https://docs.unity3d.com/6000.0/Documentation/Manual/urp/gpu-resident-drawer.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html | U3-032 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html
- **Assessment:** Version difference; Deferred+ arrived in 6.1. On Quest, Deferred is not recommended anyway (U1-034).
- **Status:** Resolved: Forward+ on Quest in every version.

### X-C10: On-tile post-processing setup steps (new, cross-topic U1/U2)

- **U1: setup includes enabling Tile-Only Mode.** U1-062 [doc] [verify on device]: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-post-processing.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html
- **U2: 6.3 requirements are integrated post-processing off, Vulkan and the renderer feature; Tile-Only Mode is a 6.5 renderer checkbox.** U2-074 [doc]: https://docs.unity3d.com/6000.3/Documentation/Manual/xr-graphics-on-tile-post-processing.html | U2-025 [doc]: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html
- **Assessment:** Tile-Only Mode does not exist in 6.3/6.4.
- **Status:** Resolved by version: 6.3-6.4 without Tile-Only Mode; 6.5+ with it (and its validation in development builds).

### UNITY-GF1-C1: Thermal headroom rule (new, gap-fill round 1)

- **Unity e-book: use about 65% of the frame time on mobile, to leave thermal cool-down.** UNITY-GF1-008 [doc]: e-book p. 19 (PDF URL in UNITY-GF1-007)
- **Meta (quest-perf dossier baseline): no headroom percentage is published; design to nominal CPU L4 / GPU L4 and treat GPU L4 as the maximum budget.** quest.md baseline row "The app never gets the full budget" [doc]: https://developers.meta.com/horizon/documentation/unity/optimize-performance/
- **Assessment:** The sources measure different things. Unity's is a generic phone heuristic in frame-time percent. Meta's is a clock-level ceiling for Quest, where the OS manages levels. Neither gives a Quest-validated percentage.
- **Status:** Open. Prefer Meta's level-based rule for Quest. Do not quote "65%" as Quest guidance. Method to settle it: 30-minute soak at fixed content, with OVR Metrics Tool logging GPU/CPU level, GPU%, stale frames and temperature. Compare a build at about 65% GPU utilization with one at about 85%.

### UNITY-GF1-C2: "XR devices enforce Vsync at 90 Hz or higher" (new, gap-fill round 1)

- **Unity e-book: most XR devices enforce Vsync at 90 Hz or higher.** UNITY-GF1-009 [doc]: e-book p. 43
- **Meta: the default display refresh rate for apps is 72 Hz. Quest 2, 3 and 3S all support 72, 80, 90, 96, 100 and 120 Hz, and Quest 3 alone goes above 120 Hz.** Baseline "Frame budgets" row [arithmetic]; https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ [doc]
- **Assessment:** The e-book's generalization is wrong for Quest, whose default is below 90 Hz. The Vsync-enforcement part is right.
- **Status:** Resolved in Meta's favor: Quest defaults to 72 Hz, and the app selects a higher rate.

### UNITY-GF1-C3: Fixed Timestep direction (new, gap-fill round 1; extends U5-C4)

- **Unity e-book: on lower-end platforms set Fixed Timestep slightly longer than the frame time (for example 0.035 s at 30 fps) to avoid the catch-up spiral.** UNITY-GF1-014 [doc]: e-book p. 81
- **Community and old Oculus sample code: set fixedDeltaTime = 1/refresh (0.0138 s at 72 Hz), which is shorter than the 0.02 s default.** U5-051 [community]: https://communityforums.atmeta.com/discussions/dev-unity/time---fixed-timestep--hz-values-for-oculus-devices-in-unity/751740
- **Assessment:** These pull in opposite directions. 1/refresh makes physics run exactly once per frame, which fixes judder and keeps main-thread cost steady (consistency) but raises the physics step count from 50 to 72-120 per second (throughput). The e-book's longer step lowers cost but gives fewer steps than frames, which needs Rigidbody interpolation in VR.
- **Status:** Open; depends on physics cost. Method: on Quest 2 at 72 Hz, compare 0.02 s, 1/72 s and 1/36 s, with interpolation on. Record main-thread p95/p99 (Profiler / OVR Metrics Tool), `Physics.Simulate` ms and visible judder.

### UNITY-GF2-C1: `_FORWARD_PLUS` after 6.1 (correction, gap-fill round 2)

- **Dossier text before round 2 (U1-033): custom HLSL branching on `_FORWARD_PLUS` stops taking the clustered path after the 6.1 upgrade.** Derived from https://docs.unity3d.com/6000.1/Documentation/Manual/urp/upgrade-guide-unity-6-1.html [doc]
- **URP source (6000.1 and 6000.5 staging): URP still sets `_FORWARD_PLUS` alongside `_CLUSTER_LIGHT_LOOP`, and a shim maps the old macros to the new ones with a compile warning.** https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/Runtime/ForwardLights.cs ; https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/ShaderLibrary/ForwardPlusKeyword.deprecated.hlsl [doc]
- **Assessment:** The upgrade guide says only "deprecated". The "stops taking the clustered path" wording was an over-reading and has been removed from U1-033. Custom shaders keep working on 6.1-6.5, with a warning and a possible compile-time cost.
- **Status:** Resolved in favor of the source. Open: whether 6.6 or 6.7 removes the shim. Method: grep `ForwardPlusKeyword.deprecated.hlsl` in the installed URP package of each Editor.

## Known unknowns

Open gaps collected from all five topics, deduplicated. Each gives the measurement or retrieval method.

### Version and upgrade

- ~~**2021.3 and 2022.3 end-of-support dates.**~~ Largely resolved in gap-fill round 2 (UNITY-GF2-005): Unity's CVE-2025-59489 advisory classes the public 2021.3 LTS and 2022.3 LTS as "Out of Support" and only the paid xLTS streams as supported. Still unpublished: the exact end dates (community endoflife.date gives 2025-02-18 and 2025-05-07) and the xLTS end dates. Method: ask Unity sales or account management for the xLTS schedule.
- **UUM-93226 OS fix.** No confirmation that a Horizon OS release fixed the Qualcomm visibility-stream bug, and no data on how much Optimize Buffer Discard recovers. Method: GLES vs Vulkan A/B on the current OS with a many-mesh scene, Optimize Buffer Discard on and off, GPU ms and stale frames in OVR Metrics Tool.
- **Vulkan GSC warmup on 6.0/6.3 LTS (X-C1).** Method: cold first-run capture with and without warmup; count stale frames at first material use.
- **UUM-84612 status.** The fix note in 6000.0.50f1 conflicts with later notes still linking the issue. Method: reproduce MSAA + post + SpaceWarp depth submission on the current 6.0 patch.
- **UUM-113364 on standalone Quest (U1-C6).** Method: foveation level with MSAA on/off on 6.3.
- **6.6 = URP 17.6** is inferred (no 6000.6/staging branch). Method: read the URP package.json in a 6.6 project.
- **Minimum Android API for 2021.3/2022.3** and **Native RenderPass in URP 12** not verified. Method: 2021.3/2022.3 manuals and release notes.
- ~~**October 2025 cross-version patch wave**~~ Resolved in gap-fill round 2: these are the CVE-2025-59489 patch builds (https://unity.com/security/sept-2025-01; UNITY-GF2-005).
- **Meta's recommended Unity OpenXR plugin version** not confirmed with a second fetch; **the OpenXR version that fixed the missing occlusion mesh** not identified.
- **Adaptive Performance on Quest before 6.6** undocumented.
- **Current Meta XR Core SDK (207.0.0) Project Setup Tool rules** for Graphics Jobs, MT rendering and GPU skinning not read.

### Rendering, Render Graph and tile behavior

- **No Quest numbers** for GRD, GPU occlusion culling, Mesh LOD, the 6.5+ Quest shader optimizations, on-tile post vs classic post, thin LTO, depth input attachment, APV per-pixel vs per-vertex, BRG UBO vs SSBO, SRP Batcher on/off, Multiview Render Regions savings, SSAO, decals, soft shadow tiers, cascades, LOD Cross Fade, camera stacking, FXAA or Stop NaN. Method: A/B each on a fixed camera path at locked CPU/GPU levels on Quest 2 and Quest 3; GPU ms from OVR Metrics Tool, render-thread ms from the Profiler, pass timing from RenderDoc Meta Fork.
- **MSAA 2x vs 4x cost on Quest 2/3** (U2-C1 / U3-C7). Only Quest 1 data exists.
- **VRS on Quest.** No source confirms Quest exposes Vulkan fragment shading rate to Unity's VRS API, or how it interacts with fragment-density-map foveation. Method: `SystemInfo`/`ShadingRateInfo` support query in a Quest build.
- **Device capability flags** (`supportsBackbufferInMultipleRenderTargets`, `supportsMemorylessTextures`, `supportsDepthAttachmentAsInputAttachment`, `supportsParallelPSOCreation`) on Quest 2 vs Quest 3. Method: log at startup.
- **Adreno 740 MSAA input-attachment sample parallelism.** Meta states only the A540/A650 rule (2 free, 4 not).
- **"Except on Android XR"** in the 6.6 on-tile page: does it cover Quest? Method: check dynamic-resolution behavior in the on-device Render Graph Viewer.
- **URP Settings Analyzer (6.6) rule list** not inspected. Method: run it on a Quest project and list the rules.
- **FSR 1.0 in URP 12.1 docs**: patch feature or docs backport.
- **Tile-Only validation CPU cost** in development builds, and **Render Graph record/compile CPU cost** on the Quest render thread. Method: Profiler markers in a development build.
- **Discard/LRZ in Qualcomm's proprietary driver** (only Mesa sources) and **A2C cost**. Method: RenderDoc Meta Fork LRZ counters and GPU ms with and without alpha clip.
- **Half vs float fragment speedup on Adreno 650 vs 740.** Method: twin variants, Fragment ALU Full/Half counters and GPU ms.
- **Per-PSO creation time on Adreno 650/740** and **`vulkan_pso_cache.bin` write timing** (pause vs quit; GLES `UnityShaderCache/`). Method: `CreateGraphicsGraphicsPipelineImpl` durations on a cold run; `adb shell run-as <pkg> ls -l cache/ files/` across session, force-stop and reinstall.
- **BRG constant-buffer window on Adreno GLES.** Method: log `GetConstantBufferMaxWindowSize()` and `GetConstantBufferOffsetAlignment()`.
- ~~**Dynamic batching in URP 6.x**: precedence on 6.0-6.5 unverified.~~ Resolved in gap-fill round 1 by UNITY-GF1-001/-002: it is last in precedence, and the docs say not recommended except on low-end devices. Still unmeasured: its CPU cost vs saved draw calls on Quest 2 for sub-300-vertex props. Method: A/B the URP asset's Dynamic Batching toggle on a scene of many small props with the SRP Batcher on; compare main- and render-thread ms and batch counts (Profiler, Frame Debugger).
- **Shader Graph variant cost of Allow Material Override (UNITY-GF1-005).** Keyword side resolved from source in gap-fill round 2 (UNITY-GF2-002): six `shader_feature` keywords plus material-driven render states and always-generated DepthOnly/ShadowCaster passes. Still unmeasured: the actual variant and PSO count for a real material set. Method: build the same graph with the option on and off. Compare the compiled variant count in the Shader inspector ("Compile and show code" or the variant count after build) and the Editor.log shader-compilation summary. Also compare PSO count in a GSC trace.
- **Shader Graph vs hand-written HLSL GPU cost on Adreno (UNITY-GF1-006).** No published measurement. Method: equivalent Lit material both ways. Compare Adreno offline-compiler instruction/register counts, then GPU ms at a locked GPU level in OVR Metrics Tool on Quest 2 and Quest 3.
- **Per-camera CPU overhead on Quest (UNITY-GF1-012).** The e-book's "up to 1 ms" is a generic low-end-phone figure. Method: toggle an extra overlay camera and compare main-thread and render-thread ms on Quest 2.
- **Draw-call counting under multiview** and **stereo slice selection in URP full-screen passes** not traced.
- **Quest 3S budgets.** No separate draw-call, triangle or memory guidance; assume Quest 3 SoC and RAM with a Quest 2-class display.
- **Unity 6.7** has not shipped (6000.7.0b2 is the latest on 2026-09-24; UNITY-GF2-006 lists the beta items to watch). Recheck GSC, Quest shader paths, dynamic batching, the "URP keywords to dynamic branch" option and Render Regions when 6.7 LTS ships. This is time-gated, not researchable today.
- **Adreno model number from a Qualcomm primary source.** Not available: all three public XR2 Gen 2 / XR2+ Gen 2 briefs say only "Adreno GPU", and the product pages are JS-rendered (UNITY-GF2-003). Method: read the renderer string on device (`SystemInfo.graphicsDeviceName`, or `adb shell dumpsys SurfaceFlinger | grep GLES`).
- **Third-party draw-call ceilings** exist but no primary source was retrieved.

### Lighting, textures, meshes, loading

- **ASTC HDR on Quest 2/3/3S.** Decides whether High Quality lightmaps and HDR cubemaps stay compressed. Method: `SystemInfo.SupportsTextureFormat(TextureFormat.ASTC_HDR_6x6)` in a Quest build, or `vulkaninfo` over adb for `textureCompressionASTC_HDR`.
- **APV runtime cost and memory on Quest**, streaming hitches, and whether APV runs on GLES 3.2. Method: OVR Metrics GPU ms, RenderDoc, Memory Profiler, Profiler during fast traversal.
- **Mixed lighting mode GPU cost** (Subtractive, Baked Indirect, Shadowmask). Method: A/B variants of one scene at fixed levels.
- **Anisotropic filtering cost on Adreno.** Method: Aniso 1/2/4/8 on a floor-dominated view; GPU ms and texture-fetch counters in Snapdragon Profiler.
- **Mipmap streaming with stereo XR cameras.** Method: log desired vs loaded mips; watch for blur in fast head turns.
- **Normal-map encoding decode cost** (DXT5nm-style vs XYZ). Method: A/B on a normal-map-heavy scene.
- **`UnloadUnusedAssets` and scene activation cost vs object count.** Method: ProfilerMarkers in a development build.
- **GPU (Batched) skinning gain over GPU skinning.** Method: crowd scene A/B.
- **Shadowmask texture format and memory on Android.** Method: Memory Profiler.
- **AUP defaults** (Time Slice, Buffer Size) come from a 2018 blog. Method: read Quality settings in a new project on your version.
- **Unity Gfx memory counters vs Android `dumpsys meminfo` rows**, and **ASTC decode-mode extensions** on Quest: no mapping found.

### CPU, scripting, profiling

- **IL2CPP Master vs Release, Code Generation options, stripping level, PAC/BTI** on Quest. Method: ProfilerRecorder main-thread p50/p95/p99 over identical 2-minute non-development runs.
- **Incremental GC and the XR frame wait (U5-C3).** Method: Timeline placement of GC slices.
- **Optimized Frame Pacing under OpenXR (U5-C5).** Method: stale frames and XRDisplaySubsystem dropped-frame deltas, on vs off.
- **Job worker count and usable cores (U5-C6)**, **XR2 Gen 2 core types and SVE2 for Burst ARMV9A.** Method: log at startup; `/proc/cpuinfo`; Perfetto thread placement; Burst Inspector plus timing.
- **Graphics Jobs vs Adreno LRZ on 2022.3.35f1+/6.x**, and **Native vs Split vs Legacy** on Quest. Method: RenderDoc Meta Fork LRZ counters and GPU ms, GJ on vs off.
- **fixedDeltaTime on Quest (U5-C4).**
- **Animator culling** in multiview stereo and with shadow casters.
- **uGUI vs UI Toolkit world-space cost, Canvas rebuild, TMP mesh generation, Update-message overhead, Awaitable vs coroutine** on IL2CPP ARM64: no Quest data.
- **6.6 Managed Code Variant = Release**: whether custom ProfilerMarkers vanish from development builds.
- **Background/focus-loss CPU behavior**, **Sustained Performance Mode on Horizon OS**, **Profiler Highlights with XR frames**, **which XRDisplaySubsystem stats the Meta/OpenXR provider fills** (and units per plugin version), **Activity vs GameActivity** on Quest: undocumented. Method for XR stats: log every stat per frame on each plugin version and compare with OVR Metrics.
- **FrameTimingManager GPU time on 6.6 XR (X-C3).**

### E-book

- ~~**Unity 6 mobile/XR/web optimization e-book content** not captured (form-gated PDF).~~ Resolved in gap-fill round 1 (UNITY-GF1-007 to -017). The companion XR e-book was read in round 2 (UNITY-GF2-004): it has no XR-specific numbers.

### Findings tagged [verify on device]

Each of these findings carries a claim that needs hardware confirmation. The finding's own Notes line gives the measurement method where the researcher recorded one; the last column quotes that method or states the default A/B method.

| ID | Claim (first sentence) | How to measure |
| --- | --- | --- |
| U1-014 (in U3-026) | BRG has two buffer modes. | To measure, A/B the same BRG scene with GLES vs Vulkan and read GPU/CPU frame time from OVR Metrics or RenderDoc. |
| U1-018 (in U3-034) | Unity's GRD performance page warns that GRD adds a small GPU cost, and more on lower-end mobile and VR. | To measure, A/B GRD off vs Instanced Drawing on the same scene. |
| U1-019 (in U3-037) | GPU occlusion culling arrived in 6.0 (6000.0.0b11) and requires GRD. | Measure it as a separate pass in RenderDoc or the Render Graph Viewer. |
| U1-032 | Forward+ first shipped in URP 14 (2022.3). | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-036 (in U3-066) | 6.5 added automatic Meta Quest shader optimizations. | To measure, build the same scene with the profile's optimizations on and off, then compare GPU ms and the Lit shader instruction count in the compiled shader (RenderDoc or Snapdragon Profiler). |
| U1-041 | Adaptive Probe Volumes (APV) arrived in URP 17 (6.0). | Measure the GPU ms delta on a lit test scene with APV per-pixel, APV per-vertex and classic light probes. |
| U1-043 (in U2-052) | 6.2 turned on Qualcomm's `VK_QCOM_render_pass_shader_resolve` so MSAA can be used on untethered XR such as Quest. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-044 (in U2-048) | 6.3 added automatic viewport dynamic resolution for OpenXR headsets, which scales resolution based on device performance. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-047 | UUM-121231, "Fixed GraphicsStateCollection warmup for Vulkan", appears only in 6000.4.0a4. | To check, capture a first-run session on Quest with and without warmup. |
| U1-049 | Stereo-instancing shader variants are not prewarmed, because they need a layered render-target setup (6000.0.0b11, UUM-54697). | Check by tracing on device and inspecting the collection. |
| U1-054 (in U2-052) | 6.2 enabled thin Link Time Optimization of engine code for the Meta Quest profile (6000.2.0a8). | Measure CPU main- and render-thread ms with the profile on, compared with a manual build without LTO. |
| U1-059 | Mesh LOD arrived in 6.2. | Inference to verify: because only the index buffer changes, the full LOD0 vertex buffer stays resident and is bound for every LOD. |
| U1-061 | The Variable Rate Shading API (6.1) lets Scriptable Renderer Features set shading rate. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-062 (in U2-074) | On-tile post-processing arrived for untethered XR in 6.3 (6000.3.0b3) and for all platforms in 6.5. | Check with the Render Graph Viewer that no texture-sampling fallback pass appears. |
| U1-065 (in U2-079) | 6.6 lets URP read the current depth buffer as an input attachment from GPU memory on DX12 and Vulkan, avoiding a depth copy. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-068 | UUM-148724: `PlayerSettings.vulkanNumSwapchainBuffers` was ignored, and players always used 3 swapchain buffers. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-072 | Other 6.6 scripting changes: domain reload is off by default, and the IL2CPP converter was rebuilt on NativeAOT. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-073 | Adaptive Performance history: 6.0 lists an Android provider for Adaptive Performance. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-076 | Unity's documented workaround for UUM-93226 is to turn on "Optimize Buffer Discard", available in both the OpenXR (Meta) and Oculus XR plugins. | Measure GLES vs Vulkan vs Vulkan with Optimize Buffer Discard on a high-mesh-count scene, recording GPU ms and stale frames with OVR Metrics Tool on the current Quest OS. |
| U1-077 | No public confirmation found that a Meta OS release fixed the Qualcomm visibility-stream bug. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-079 | UUM-84612: the player rendered black on Quest when MSAA, post-processing and SpaceWarp depth submission were all on. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-084 | UUM-113364: foveation was switched off when MSAA was on under Vulkan. | To check on 6.3, look at the foveation level in OVR Metrics or RenderDoc (fragment density map attachment present) with MSAA 2x/4x on and off. |
| U1-085 (in U2-054) | Meta says SRP Foveation (Unity 6+) is often 20–30% faster in frame time than Legacy foveation when post-processing, deferred or multi-pass rendering is used. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-086 | Vulkan PSO and pipeline-cache fixes across the range: race conditions in Vulkan PSO cache registration and async PSO shutdown were fixed (6000.0.0b11). | Measure first-run hitches with a scripted camera path: record frames over 13.9 ms (72 Hz) or 11.1 ms (90 Hz) with and without a GSC collection. |
| U1-087 | UUM-121520 reduced the memory overhead of Vulkan command buffers when graphics jobs are used on Android. | Measure with `adb shell dumpsys meminfo <pkg>` (Graphics / GL mtrack) with graphics jobs on, comparing 6.0 and 6.3 builds. |
| U1-089 | 6.0 upgrade guide: mipmap limits (the Quality setting for texture mip limit) no longer apply to textures created at runtime by default. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U1-093 | Migration risk: switching from Oculus XR to OpenXR changes the plugin that owns foveation, depth submission, the eye-buffer format and frame timing. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U2-010 | **LOD Cross Fade** defaults to on (Blue Noise) in URP 14+. | The renderer reserves bits 0-3 for users, so check for conflicts with stencil-based effects. |
| U2-021 | **Depth Texture Mode** (copy depth) defaults and trade-offs: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U2-027 (in U1-032) | **Forward+** on Quest: | Re-measure per scene. |
| U2-034 | A full-screen pass with no depth attachment and no MSAA can drop into Adreno Direct Mode: one bin, bypassing tiling, and FFR is disabled. | The resolution is Quest 1-era, so re-measure. |
| U2-043 | **Occlusion mesh**: URP has an XR Occlusion Mesh pass that masks the invisible (nasal/edge) eye-buffer region with depth. | Confirm in the Frame Debugger or Render Graph Viewer that "XR Occlusion Mesh" runs on device. |
| U2-044 | URP's asset Render Scale goes to the XR display: `XRSystem.SetRenderScale(renderScale)` sets `display.scaleOfAllRenderTargets` for every XR display. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U2-055 (in U1-083) | A known Quest bug renders the view black when framebuffer fetch is combined with foveated rendering in a player. | Check the issue's fixed-in version before shipping FB fetch plus FFR. |
| U2-059 | `BackbufferInMultipleRenderTargetsNotSupported` breaks a merge when one pass targets the backbuffer and another targets user render targets. | Log `SystemInfo.supportsBackbufferInMultipleRenderTargets` on Quest 2 and Quest 3 once. |
| U2-087 | Meta notes that URP's `OnRenderObjectCallbackPass` prevents subpass merging; it is commented out in the fork. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U2-093 | Meta's native MSAA analysis: | Re-measure with ovrgpuprofiler render-stage timing on the target device. |
| U3-003 | Meta's per-device guidance: | Treat these as starting budgets and measure render-thread ms. |
| U3-012 | Unity warns that if a project's assets and shaders aren't optimized for the SRP Batcher, low-performance devices may run faster with it off. | To measure: toggle `GraphicsSettings.useScriptableRenderPipelineBatching` at runtime in a fixed camera path on Quest 2, and compare render-thread ms (Profiler) and GPU ms (OVR Metrics Tool). |
| U3-025 | URP's legacy instanced-array size is 250 on mobile Vulkan and 500 elsewhere, unless `UNITY_MAX_INSTANCE_COUNT` (`#pragma instancing_options maxcount:N`) overrides it. | Check the instance count per draw in the Frame Debugger. |
| U3-029 (in U3-026) | `BatchRendererGroup.BufferTarget` reports the buffer model at runtime: RawBuffer (SSBO) or ConstantBuffer (UBO). | Log the two getters on Quest 2 and Quest 3 under GLES if you still ship GLES. |
| U3-034 | Unity: GRD improves CPU time but slightly increases GPU work, and lower-end mobile and VR feel it more. | Most Quest apps are GPU-bound, so A/B on Quest 2 before committing. |
| U3-037 | How GPU occlusion culling works: | To measure: GPU ms with occlusion on vs off in an open scene and in an interior scene. |
| U3-043 | URP's XR pass chooses the stereo path at runtime: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U3-047 | In TextureXR.hlsl, `TEXTURE2D_X` becomes a Texture2DArray on Vulkan and GLES3, but `SLICE_ARRAY_INDEX` equals `unity_StereoEyeIndex` only in the stereo-instancing path; otherwise it is 0. | Always use the `_X` macros for camera textures, and validate per-eye output with StereoEyeIndexColor or a RenderDoc capture. |
| U3-048 | Unity adds `STEREO_INSTANCING_ON`, `STEREO_MULTIVIEW_ON`, `STEREO_CUBEMAP_RENDER_ON` and `UNITY_SINGLE_PASS_STEREO` to every graphics shader by default. | Confirm with strict variant matching (U3-073). |
| U3-050 | Multiview Render Regions skips the nasal region each eye can't see, by setting per-view viewports, scissors and render areas on Vulkan. | To measure: GPU ms with the feature on vs off, no post, same pose. |
| U3-054 | Meta's counters define precision behavior on Quest: | To measure: compare the Fragment ALU (Full) vs (Half) split and GPU ms for float vs half variants of one material. |
| U3-057 | Shader Graph's guidance: keep world-space positions, texture coordinates and heavy scalar math (trig, pow, exp) in Single. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U3-059 | On Adreno, LRZ is an early depth test built during the binning pass. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U3-060 | Per the same Mesa doc, draws whose fragment shader uses `discard` (clip/alpha test) can't contribute to LRZ during binning. | Practical rule: draw opaque (queue 2000) before alpha-tested (URP's AlphaTest queue, 2450), so cutout pixels test against LRZ built by solid geometry. |
| U3-062 | For expensive alpha-tested foliage, Meta suggests trying a depth-only prepass that writes depth where alpha ≠ 0, followed by a color pass with depth test Equal. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U3-067 | The automatic Quest optimizations, read from URP source: | To quantify, diff the Vulkan shader stats (U3-006) for Lit built on 6.3 vs 6.6. |
| U3-069 | Configurable: "Camera projection query". | `META_QUEST_NO_SPOTLIGHTS_LIGHT_LOOP` has no manual entry; confirm what enables it before relying on it. |
| U3-075 | Shader Constant Defines (seen only in the 6.6 manual) set a compile-time constant per build profile, for example `NUMBER_OF_MSAA_SAMPLES 2`. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U3-079 | URP's prebuilt shaders use dynamic branching only for fog (`_ FOG_LINEAR FOG_EXP FOG_EXP2`), `_REFLECTION_PROBE_BLENDING` and `_REFLECTION_PROBE_BOX_PROJECTION`. | If fog is off project-wide, confirm the uniform branch really skips the work on Adreno 650 (Vulkan stats flow-control count). |
| U3-080 | How shaders load at runtime: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U3-085 | Unity staff guidance on GSC tracing: | Trace on device, because Editor traces carry desktop state. |
| U3-086 | Warmup API: | Log it at startup on Quest 2 and Quest 3; if it is false, you get the variant-only fallback of U3-082. |
| U3-094 | Unity persists a Vulkan pipeline cache (`vulkan_pso_cache.bin`) and, on GLES3, a program binary cache (`UnityShaderCache/`) under the app's temp/cache directory. | To check: `adb shell run-as <pkg> ls -l cache/` after a warm session and after a force-stop. |
| U3-095 | Unity 6.4 fixed a case where a corrupted Vulkan pipeline cache file made `vkCreatePipelineCache` fail. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U4-001 | Unity ranks the mixed lighting modes by runtime cost. | To measure, build the same scene once per mode and compare GPU frame time in OVR Metrics Tool or the Unity Profiler GPU module. |
| U4-006 (in U1-032) | Forward+ removes the per-object light limit. | Measure with GPU frame time and RenderDoc (Meta fork) on a scene with 4, 8, and 16 visible lights. |
| U4-010 | The URP 15.0.0 changelog lists a fix for a performance regression with additional lights on Quest. | On 2022.3 projects with many additional lights, compare GPU time against a 6000.x build of the same scene, or check the 2022.3 patch release notes. |
| U4-014 | In URP 6000.3 source, APV vertex sampling is enabled only when the asset's SH mode is explicitly Per Vertex or Mixed. | Confirm by checking the shader keywords in a RenderDoc or Frame Debugger capture, or by comparing GPU time between Auto and Per Vertex. |
| U4-016 | In core source, the APV Memory Budget enum sets the brick-pool texture size. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U4-018 | APV streaming has two layers: | Watch Profiler frames during fast traversal, and check whether cell uploads appear as render-thread spikes. |
| U4-020 | A third-party write-up claims APV needs compute shaders and does not run on GLES. | Test an APV scene on a GLES 3.2 Quest build and look for magenta or unlit objects, plus warnings in logcat. |
| U4-021 | The URP Asset exposes Probe Blending, Probe Atlas Blending, and Box Projection toggles: | A/B each toggle and compare GPU time on a reflective material that covers the screen. |
| U4-024 | The HDR Cubemap Encoding Player setting (Low, Normal, or High Quality) sets the encoding and compression of HDR cubemaps, such as baked reflection probes and HDR skyboxes. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U4-025 | URP soft shadows have three quality levels: | Measure GPU time with soft shadows off, Low, and Medium on a scene where the shadowed area fills much of the view. |
| U4-033 | The URP Asset's Conservative Enclosing Sphere option tightens cascade culling spheres. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U4-038 | High Quality (HDR) lightmaps on Android rely on ASTC HDR. | Check on device with `SystemInfo.SupportsTextureFormat(TextureFormat.ASTC_HDR_6x6)`, or run `vulkaninfo` over adb and look for `textureCompressionASTC_HDR`. |
| U4-042 | Block Aligned Padding (XAtlas packing) aligns UV charts to a 4x4 texel grid to reduce block-compression artifacts. | Inspect chart seams on device with and without the option. |
| U4-043 | In Shadowmask mode, Unity bakes an extra shadowmask texture per lightmap. | Check it in the Memory Profiler or by inspecting the baked asset's import settings. |
| U4-044 (in U3-032) | GPU Resident Drawer requires Forward+ and compute support, which excludes GLES. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U4-045 | Android Player settings include Lightmap Streaming, which requires Mipmap Streaming, and a lightmap Streaming Priority from -128 to 127. | Check whether lightmaps are resident at full resolution with `Texture2D.loadedMipmapLevel` on the lightmap textures. |
| U4-049 | ASTC bitrates are fixed by block size: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U4-051 | The Normal Map Encoding Player setting offers XYZ or DXT5nm-style. | Measure on a scene dominated by normal-mapped surfaces. |
| U4-056 | The Quality setting Anisotropic Textures has three values: Disabled, Per Texture, or Forced On. | Use Per Texture, raise Aniso Level only on surfaces seen at grazing angles, and A/B GPU time on a floor-dominated view. |
| U4-059 | Mipmap Streaming Quality settings: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U4-063 | No Unity or Meta document found in this research says how mipmap streaming picks mips for stereo XR cameras (two eyes, or single-pass multiview). | To verify on device, log `Texture2D.desiredMipmapLevel` against `loadedMipmapLevel` for a close-up texture in a Quest build. |
| U4-074 (in U5-059) | The Prebake Collision Meshes Player setting adds physics collision data to meshes at build time. | Measure scene-load time with and without this setting in the Profiler, and look for physics cooking markers during load. |
| U4-075 | Meta's 2021 Quest 2 profiling of scene activation found the following: | Measure activation on your own content with the Profiler's `Application.Integrate Assets in Background` and activation markers. |
| U4-077 (in U5-040) | The GPU skinning Player setting has changed across versions: | Compare with a crowd scene, reading render-thread and GPU time in the Profiler and OVR Metrics Tool. |
| U4-080 | Unity's 2018 AUP blog gives these details: | Check the defaults in your project's Quality settings, since the 2018 values may differ from current. |
| U4-085 | Scene activation is a main-thread hitch. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U4-087 | The Addressables 1.21 docs call `Resources.UnloadUnusedAssets` slow and a cause of frame-rate hitches. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U4-088 | Community reports say `UnloadUnusedAssets` gets slower as a session goes on, and that it can hang the player in some cases. | Treat this as a lead to measure, not as evidence of a size. |
| U4-094 | Shader Variant Loading settings (Player > Other Settings) control shader memory: | Measure both memory and frame time before capping. |
| U4-095 | "Keep Loaded Shaders Alive" stops loaded shaders from unloading, so they aren't recreated later, at the cost of memory. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-006 | Unity's GC configuration page says disabling incremental GC can save "as much as 1 ms per frame" in CPU-bound projects, because it removes write-barrier overhead. | : compare PlayerLoop median and p99 over 2+ minutes of identical gameplay with each setting. |
| U5-008 | Unity uses leftover end-of-frame time for incremental GC only when `QualitySettings.vSyncCount` is not "Don't Sync" or `Application.targetFrameRate` is set. | Look for incremental GC samples in Timeline; if they sit inside the frame rather than in the wait, assume no idle-time scheduling. |
| U5-015 | C++ Compiler Configuration has three levels: | : build both from the same commit and compare CPU Main Thread median/p99 with ProfilerRecorder in non-development builds. |
| U5-018 | Unity 6.6 adds **Managed Code Variant** (Player setting; `PlayerSettings.SetManagedCodeVariant`) and deprecates the `UNITY_64` / `DEVELOPMENT_BUILD` defines. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-021 | Target Architectures: ship ARM64 only (it requires IL2CPP). | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-023 | Optimized Frame Pacing (Android Swappy) is described only generically: it spreads frames more evenly to reduce frame-time variance. | : compare stale-frame counts in OVR Metrics Tool with it on and off. |
| U5-025 | Vulkan Player settings: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-029 | Burst compile targets for 64-bit Arm Android: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-032 | `JobsUtility.JobWorkerCount` defaults to `JobWorkerMaximumCount`. | : log `JobsUtility.JobWorkerMaximumCount`, `JobWorkerCount` and `SystemInfo.processorCount` at startup on each headset. |
| U5-034 | Community reports on Quest thread counts: | : capture a Perfetto trace, count Unity worker threads, and check which cores they run on. |
| U5-037 | Unity 6.6 has three Graphics Jobs modes, Vulkan only: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-043 | Unity keeps a per-type list of scripts that define each magic method. | : re-run the 10k test with IL2CPP Master on Quest 2 and Quest 3. |
| U5-053 | A September 2024 Unity forum thread reports that changing `fixedDeltaTime` had no visible effect on a Quest build. | : log `Time.fixedDeltaTime` and count FixedUpdate calls per frame after setting it. |
| U5-067 | Culling Mode: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-071 | In uGUI, changing one element dirties its whole Canvas, which triggers a mesh and batch rebuild. | Those names are from general Unity knowledge, not the fetched markers reference;  in a capture. |
| U5-077 | UI Toolkit world-space panels exist from Unity 6.2: set Panel Settings Render Mode to World Space. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-091 | Per-frame XR stats come from `XRDisplaySubsystem`: | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-096 | The Profiler Highlights module (6.0+; absent from the 2022.3 manual) labels frames CPU- or GPU-bound using FrameTiming data. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| U5-098 | Unity 6.6 adds an Android **Profileable Shell** build setting. | A/B on Quest 2 and Quest 3 at locked CPU/GPU levels; compare GPU ms (OVR Metrics Tool), render-thread ms (Profiler) and stale frames. |
| UNITY-GF1-001 | Dynamic batching on 6.0-6.5 is documented as "no longer recommended" for most uses. | Toggle URP asset Dynamic Batching on a small-prop scene on Quest 2; compare main/render-thread ms and batch count. |
| UNITY-GF1-004 | Shader Graph Project Settings defaults (variant limit 2048; interpolator thresholds 16/32). | Custom-interpolator channel count vs GPU ms on Adreno 650/740 at locked GPU level. |
| UNITY-GF1-006 | Shader Graph generated code costs more than hand-written HLSL mainly for structural reasons. | Offline-compiler instruction counts plus GPU ms, Shader Graph vs HLSL twin. |
| UNITY-GF1-012 | E-book: up to 1 ms CPU per enabled camera on lower-end mobile. | Extra overlay camera on/off on Quest 2; main- and render-thread ms. |

## Leads for other bundles

Leads recorded by the topic researchers that belong to other bundles, or to topics this dossier does not own. Unverified leads are marked.

### quest-perf (Meta platform, runtime, SDK, tools)

- **CPU/GPU levels and Quest Boost:** Quest 2 CPU 0.71-2.42 GHz; Quest 3/3S 0.69-2.36 GHz; `OVRManager.suggestedCpuPerfLevel`; Boost lasts at most 45 s and 20% of runtime, gains +23% on Quest 3/3S vs +64% on Quest 2/Pro; dual-core mode only on Quest 2/Pro. https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ ; https://developers.meta.com/horizon/documentation/unity/po-quest-boost/
- **Meta OpenXR settings page:** Symmetric Projection, Optimize Buffer Discards, Multiview Render Regions (6.1+), Late Latching (`XRDisplaySubsystem.MarkTransformLateLatched`), Space Warp (RG16f motion vectors), Depth Submission Mode None, Offscreen Rendering Only (10-20 MB saved on Quest 3). https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/
- **Foveation:** Meta claims SRP Foveation is 20-30% faster than Legacy in Unity 6 (vendor claim); Google cites about 0.5 ms extra for Vulkan subsampling on Android XR; check `EnableFoveatedRasterization` and `MultiviewRenderRegionsCompatible` on custom passes. Eye-tracked foveation: none of the target headsets has eye tracking (one line only).
- **Application SpaceWarp** is incompatible with the Meta subpass fork before 6000.3; SpaceWarp shader support history is in U1-070.
- **Compositor layers** as an alternative to overlay cameras for UI.
- **Dynamic resolution and thermal:** Adaptive Performance for OpenXR (6.6, Basic provider); automatic viewport dynamic resolution (6.3+, OpenXR 1.16+); OpenXR `XrPerformanceSettings` hints (U5-094); Frame Timing Stats required for Unity Dynamic Resolution (U5-027).
- **Store requirements:** VRC.Quest.Performance.4 minimum render-scale thresholds.
- **Frame pacing:** Meta's "Missed frames and frame recovery" page (not read). https://developers.meta.com/horizon/documentation/unity/os-missed-frames/
- **Tools:** OVR Metrics Tool, RenderDoc Meta Fork (Tile Timeline, draw-call trace), ovrgpuprofiler "bad config" example (1216x1344, MSAA 2, 28 bins, 10.62 ms, avoidable LoadColor 0.71 ms / LoadDepthStencil 0.828 ms / StoreDepthStencil 0.871 ms), simpleperf, MQDH Performance Analyzer and Perfetto. https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/
- **Meta's draw-call and triangle guidance** on the unity-perf page differs from the device comparison page (X-C4). https://developers.meta.com/horizon/documentation/unity/unity-perf/
- **Oculus XR to OpenXR migration checklist:** map setting names between plugins (U1-091 to U1-093).
- **Not for Quest:** Meta's "optimize-performance" page (updated 2026-09-19) targets Meta VR Glasses CPU4/GPU4 levels; do not import its numbers.
- **Unverified:** a third-party article claims a 207 Hz mode on Quest 3 (skarredghost, 2026-09-01; title seen in search only). https://skarredghost.com/2026/09/01/meta-quest-207-hz-how-to/
- **Unverified security lead:** check whether the 2025-10-03 patch wave corresponds to CVE-2025-59489; if so, Quest builds from older editors need a rebuild on patched versions or the Unity patcher.

### gles3-perf (GLES and the GLES-vs-Vulkan decision)

- **UUM-93226 A/B protocol** and Optimize Buffer Discard (section 2, U1-C2).
- **6.6 GLES 3.1 minimum** and the "Use OpenGL ES 3.0 shaders" transition setting: MAX_VISIBLE_LIGHTS 16 vs 32 (X-C6), UUM-148728.
- **Features absent on GLES:** GRD, GPU occlusion culling, STP; Entities Graphics GLES support deprecated; Graphics Jobs modes Vulkan-only; SRP Batcher single-threaded on GLES (U3-013).
- **GLES-specific behavior:** BRG UBO window (U1-014, U3-029); GLES program binary cache `UnityShaderCache/` (U3-094); FrameTimingManager may reduce GPU performance on GLES (U5-090); Tile-Only falls back when the backbuffer is not sRGB, as with GLES in Linear (U1-063); GLES Quest fixes UUM-91896 and UUM-93243 (U1-081); GLES specifics in the pre-Render-Graph path (U2-088).
- **Vulkan side of the decision:** `vulkanNumSwapchainBuffers` fix (U1-068, X-C5); Vulkan command-buffer memory fix missing from 6.0 (U1-087); Vulkan pipeline-cache corruption fix (U3-095); Meta calls Vulkan "required" for Quest (U2-094).

### arm-mobile-hw-perf (XR2 CPU, Adreno GPU, memory, thermals)

- **XR2 Gen 2 core configuration** unverifiable from first-party sources; SVE2 availability for Burst ARMV9A targets. Method: `/proc/cpuinfo`.
- **Cores available to apps and job-worker over-subscription** (U5-C6).
- **GMEM:** about 1 MB on Adreno 650 and 2 MB on Adreno 740 (U2-035); Adreno Direct Mode for full-screen passes without depth or MSAA (U2-034).
- **LRZ:** built during binning; discard disables LRZ contribution (Mesa docs, U3-059/060); Graphics Jobs vs LRZ (U5-038).
- **MSAA input attachments:** A540/A650 read 2 samples in parallel but not 4; Adreno 740 unknown.
- **Precision:** half vs float register footprint (U3-054/055); speedup unmeasured.
- **Texture formats:** ASTC HDR support and ASTC decode-mode extensions on Quest unconfirmed.
- **Memory:** Quest 2 has 6 GB and needs texture reductions (U4-053); Quest 3 has 8 GB.
- **Thermal:** sustained-performance behavior and CPU/GPU levels belong with thermals; Sustained Performance Mode on Horizon OS is undocumented.

## Source index

Deduplicated from every URL in the five topic notes (407 URLs). All were accessed 2026-09-24. The date column gives a publication or update date only where the notes recorded one; otherwise it shows the access date. Titles come from the notes' source-list labels where present, and otherwise from the page path. URL templates with `<version>` or `<branch>` placeholders are kept as the notes wrote them.

### Unity

| Title | URL | Date |
| --- | --- | --- |
| Unity Manual 2021.3: IL2CPP | https://docs.unity3d.com/2021.3/Documentation/Manual/IL2CPP.html | accessed 2026-09-24 |
| Unity Manual 2021.3: TextureStreaming | https://docs.unity3d.com/2021.3/Documentation/Manual/TextureStreaming.html | accessed 2026-09-24 |
| Unity Manual 2021.3: class PlayerSettingsAndroid | https://docs.unity3d.com/2021.3/Documentation/Manual/class-PlayerSettingsAndroid.html | accessed 2026-09-24 |
| Unity Manual 2022.3: IL2CPP | https://docs.unity3d.com/2022.3/Documentation/Manual/IL2CPP.html | accessed 2026-09-24 |
| Unity Manual 2022.3: LightMode Mixed BakedIndirect | https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-BakedIndirect.html | accessed 2026-09-24 |
| Unity Manual 2022.3: LightMode Mixed Shadowmask | https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-Shadowmask.html | accessed 2026-09-24 |
| Unity Manual 2022.3: LightMode Mixed Subtractive | https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed-Subtractive.html | accessed 2026-09-24 |
| Unity Manual 2022.3: LoadingTextureandMeshData | https://docs.unity3d.com/2022.3/Documentation/Manual/LoadingTextureandMeshData.html | accessed 2026-09-24 |
| Unity Manual 2022.3: batch renderer group | https://docs.unity3d.com/2022.3/Documentation/Manual/batch-renderer-group.html | accessed 2026-09-24 |
| Unity Manual 2022.3: class PlayerSettingsAndroid | https://docs.unity3d.com/2022.3/Documentation/Manual/class-PlayerSettingsAndroid.html | accessed 2026-09-24 |
| Unity Manual 2022.3: class TextureImporter | https://docs.unity3d.com/2022.3/Documentation/Manual/class-TextureImporter.html | accessed 2026-09-24 |
| Unity Manual 2022.3: shader keywords | https://docs.unity3d.com/2022.3/Documentation/Manual/shader-keywords.html | accessed 2026-09-24 |
| Unity Manual 2022.3: static batching | https://docs.unity3d.com/2022.3/Documentation/Manual/static-batching.html | accessed 2026-09-24 |
| Unity Scripting API 2022.3: BatchRendererGroup.BufferTarget | https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Rendering.BatchRendererGroup.BufferTarget.html | accessed 2026-09-24 |
| Unity Manual 2023.2: class PlayerSettingsAndroid | https://docs.unity3d.com/2023.2/Documentation/Manual/class-PlayerSettingsAndroid.html | accessed 2026-09-24 |
| Unity Manual 6000.0: ProfilerHighlights | https://docs.unity3d.com/6000.0/Documentation/Manual/ProfilerHighlights.html | accessed 2026-09-24 |
| Unity Manual 6000.0: embedded linux optional features | https://docs.unity3d.com/6000.0/Documentation/Manual/embedded-linux-optional-features.html | accessed 2026-09-24 |
| Unity Manual 6000.0: gpu resident drawer | https://docs.unity3d.com/6000.0/Documentation/Manual/urp/gpu-resident-drawer.html | accessed 2026-09-24 |
| Unity Manual 6000.0: upgrade guide unity 6 | https://docs.unity3d.com/6000.0/Documentation/Manual/urp/upgrade-guide-unity-6.html | accessed 2026-09-24 |
| What's New | https://docs.unity3d.com/6000.1/Documentation/Manual/WhatsNewUnity61.html | accessed 2026-09-24 |
| Unity Manual 6000.1: shader prewarm | https://docs.unity3d.com/6000.1/Documentation/Manual/shader-prewarm.html | accessed 2026-09-24 |
| Unity Manual 6000.1: upgrade guide unity 6 1 | https://docs.unity3d.com/6000.1/Documentation/Manual/urp/upgrade-guide-unity-6-1.html | accessed 2026-09-24 |
| Unity Manual 6000.2: WhatsNewUnity62 | https://docs.unity3d.com/6000.2/Documentation/Manual/WhatsNewUnity62.html | accessed 2026-09-24 |
| Unity Manual 6000.3: FBXImporter Model | https://docs.unity3d.com/6000.3/Documentation/Manual/FBXImporter-Model.html | accessed 2026-09-24 |
| Unity Manual 6000.3: FBXImporter Rig | https://docs.unity3d.com/6000.3/Documentation/Manual/FBXImporter-Rig.html | accessed 2026-09-24 |
| Unity Manual 6000.3: LightProbes TechnicalInformation | https://docs.unity3d.com/6000.3/Documentation/Manual/LightProbes-TechnicalInformation.html | accessed 2026-09-24 |
| Unity Manual 6000.3: Lightmaps TechnicalInformation | https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-TechnicalInformation.html | accessed 2026-09-24 |
| Unity Manual 6000.3: Lightmaps reference | https://docs.unity3d.com/6000.3/Documentation/Manual/Lightmaps-reference.html | accessed 2026-09-24 |
| Unity Manual 6000.3: LoadingTextureandMeshData make compatible | https://docs.unity3d.com/6000.3/Documentation/Manual/LoadingTextureandMeshData-make-compatible.html | accessed 2026-09-24 |
| Unity Manual 6000.3: LoadingTextureandMeshData | https://docs.unity3d.com/6000.3/Documentation/Manual/LoadingTextureandMeshData.html | accessed 2026-09-24 |
| Unity Manual 6000.3: MecanimPeformanceandOptimization | https://docs.unity3d.com/6000.3/Documentation/Manual/MecanimPeformanceandOptimization.html | accessed 2026-09-24 |
| Unity Manual 6000.3: ProfilerMemory | https://docs.unity3d.com/6000.3/Documentation/Manual/ProfilerMemory.html | accessed 2026-09-24 |
| Unity Manual 6000.3: RefProbePerformance | https://docs.unity3d.com/6000.3/Documentation/Manual/RefProbePerformance.html | accessed 2026-09-24 |
| Unity Manual 6000.3: TextureStreaming analyze | https://docs.unity3d.com/6000.3/Documentation/Manual/TextureStreaming-analyze.html | accessed 2026-09-24 |
| Unity Manual 6000.3: TextureStreaming configure | https://docs.unity3d.com/6000.3/Documentation/Manual/TextureStreaming-configure.html | accessed 2026-09-24 |
| Unity Manual 6000.3: TextureStreaming | https://docs.unity3d.com/6000.3/Documentation/Manual/TextureStreaming.html | accessed 2026-09-24 |
| Unity Manual 6000.3: WhatsNewUnity63 | https://docs.unity3d.com/6000.3/Documentation/Manual/WhatsNewUnity63.html | accessed 2026-09-24 |
| Unity Manual 6000.3: android requirements and compatibility | https://docs.unity3d.com/6000.3/Documentation/Manual/android-requirements-and-compatibility.html | accessed 2026-09-24 |
| Unity Manual 6000.3: assetbundles compression format | https://docs.unity3d.com/6000.3/Documentation/Manual/assetbundles-compression-format.html | accessed 2026-09-24 |
| Unity Manual 6000.3: async awaitable continuations | https://docs.unity3d.com/6000.3/Documentation/Manual/async-awaitable-continuations.html | accessed 2026-09-24 |
| Unity Manual 6000.3: async awaitable introduction | https://docs.unity3d.com/6000.3/Documentation/Manual/async-awaitable-introduction.html | accessed 2026-09-24 |
| Unity Manual 6000.3: class Animator | https://docs.unity3d.com/6000.3/Documentation/Manual/class-Animator.html | accessed 2026-09-24 |
| Unity Manual 6000.3: class PhysicsManager | https://docs.unity3d.com/6000.3/Documentation/Manual/class-PhysicsManager.html | accessed 2026-09-24 |
| Unity Manual 6000.3: class PlayerSettingsAndroid | https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html | accessed 2026-09-24 |
| Unity Manual 6000.3: class QualitySettings | https://docs.unity3d.com/6000.3/Documentation/Manual/class-QualitySettings.html | accessed 2026-09-24 |
| Unity Manual 6000.3: class TransformHandle | https://docs.unity3d.com/6000.3/Documentation/Manual/class-TransformHandle.html | accessed 2026-09-24 |
| Unity Manual 6000.3: configure mesh compression | https://docs.unity3d.com/6000.3/Documentation/Manual/configure-mesh-compression.html | accessed 2026-09-24 |
| Unity Manual 6000.3: configure vertex compression | https://docs.unity3d.com/6000.3/Documentation/Manual/configure-vertex-compression.html | accessed 2026-09-24 |
| Unity Manual 6000.3: lighting mode | https://docs.unity3d.com/6000.3/Documentation/Manual/lighting-mode.html | accessed 2026-09-24 |
| Unity Manual 6000.3: performance disabling garbage collection | https://docs.unity3d.com/6000.3/Documentation/Manual/performance-disabling-garbage-collection.html | accessed 2026-09-24 |
| Unity Manual 6000.3: performance garbage collector | https://docs.unity3d.com/6000.3/Documentation/Manual/performance-garbage-collector.html | accessed 2026-09-24 |
| Unity Manual 6000.3: performance incremental garbage collection | https://docs.unity3d.com/6000.3/Documentation/Manual/performance-incremental-garbage-collection.html | accessed 2026-09-24 |
| Unity Manual 6000.3: performance managed memory introduction | https://docs.unity3d.com/6000.3/Documentation/Manual/performance-managed-memory-introduction.html | accessed 2026-09-24 |
| Unity Manual 6000.3: performance optimizing arrays | https://docs.unity3d.com/6000.3/Documentation/Manual/performance-optimizing-arrays.html | accessed 2026-09-24 |
| Unity Manual 6000.3: performance reference types | https://docs.unity3d.com/6000.3/Documentation/Manual/performance-reference-types.html | accessed 2026-09-24 |
| Unity Manual 6000.3: performance track garbage collection | https://docs.unity3d.com/6000.3/Documentation/Manual/performance-track-garbage-collection.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization collision callbacks | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-collision-callbacks.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization cpu broad phase | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-broad-phase.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization cpu collider types | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-collider-types.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization cpu collision layers | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-collision-layers.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization cpu frequency | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-frequency.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization cpu mesh cooking options | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-mesh-cooking-options.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization cpu rigidbody collision modes | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-rigidbody-collision-modes.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization cpu static colliders | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-static-colliders.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization cpu transform sync | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-cpu-transform-sync.html | accessed 2026-09-24 |
| Unity Manual 6000.3: physics optimization raycasts queries | https://docs.unity3d.com/6000.3/Documentation/Manual/physics-optimization-raycasts-queries.html | accessed 2026-09-24 |
| Unity Manual 6000.3: profiler command line arguments | https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-command-line-arguments.html | accessed 2026-09-24 |
| Unity Manual 6000.3: profiler counters reference | https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-counters-reference.html | accessed 2026-09-24 |
| Unity Manual 6000.3: profiler deep profiling | https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-deep-profiling.html | accessed 2026-09-24 |
| Unity Manual 6000.3: profiler markers | https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html | accessed 2026-09-24 |
| Unity Manual 6000.3: profiler memory counters players | https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-memory-counters-players.html | accessed 2026-09-24 |
| Unity Manual 6000.3: shader loading | https://docs.unity3d.com/6000.3/Documentation/Manual/shader-loading.html | accessed 2026-09-24 |
| Unity Manual 6000.3: shader memory | https://docs.unity3d.com/6000.3/Documentation/Manual/shader-memory.html | accessed 2026-09-24 |
| Unity Manual 6000.3: shader prewarm | https://docs.unity3d.com/6000.3/Documentation/Manual/shader-prewarm.html | accessed 2026-09-24 |
| Unity Manual 6000.3: shadows optimization | https://docs.unity3d.com/6000.3/Documentation/Manual/shadows-optimization.html | accessed 2026-09-24 |
| Unity Manual 6000.3: stack trace | https://docs.unity3d.com/6000.3/Documentation/Manual/stack-trace.html | accessed 2026-09-24 |
| Unity Manual 6000.3: texture choose format by platform | https://docs.unity3d.com/6000.3/Documentation/Manual/texture-choose-format-by-platform.html | accessed 2026-09-24 |
| Unity Manual 6000.3: texture formats reference | https://docs.unity3d.com/6000.3/Documentation/Manual/texture-formats-reference.html | accessed 2026-09-24 |
| Unity Manual 6000.3: texture type default | https://docs.unity3d.com/6000.3/Documentation/Manual/texture-type-default.html | accessed 2026-09-24 |
| Unity Manual 6000.3: types of mesh data compression | https://docs.unity3d.com/6000.3/Documentation/Manual/types-of-mesh-data-compression.html | accessed 2026-09-24 |
| Unity Manual 6000.3: gpu resident drawer | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/gpu-resident-drawer.html | accessed 2026-09-24 |
| Unity Manual 6000.3: light limits in urp | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/lighting/light-limits-in-urp.html | accessed 2026-09-24 |
| Unity Manual 6000.3: probevolumes bakedifferentlightingsetups | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-bakedifferentlightingsetups.html | accessed 2026-09-24 |
| Unity Manual 6000.3: probevolumes concept | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-concept.html | accessed 2026-09-24 |
| Unity Manual 6000.3: probevolumes skyocclusion | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-skyocclusion.html | accessed 2026-09-24 |
| Unity Manual 6000.3: probevolumes streaming | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-streaming.html | accessed 2026-09-24 |
| Unity Manual 6000.3: probevolumes use | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/probevolumes-use.html | accessed 2026-09-24 |
| Unity Manual 6000.3: rendering paths comparison | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/rendering-paths-comparison.html | accessed 2026-09-24 |
| Unity Manual 6000.3: shadow resolution urp | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/shadow-resolution-urp.html | accessed 2026-09-24 |
| Unity Manual 6000.3: universalrp asset | https://docs.unity3d.com/6000.3/Documentation/Manual/urp/universalrp-asset.html | accessed 2026-09-24 |
| 6.3 on-tile PP (XR) | https://docs.unity3d.com/6000.3/Documentation/Manual/xr-graphics-on-tile-post-processing.html | accessed 2026-09-24 |
| 6.3 Multiview Render Regions | https://docs.unity3d.com/6000.3/Documentation/Manual/xr-multiview-render-regions.html | accessed 2026-09-24 |
| 6.3 untethered XR | https://docs.unity3d.com/6000.3/Documentation/Manual/xr-untethered-device-optimization.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Application backgroundLoadingPriority | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Application-backgroundLoadingPriority.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: AsyncOperation allowSceneActivation | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/AsyncOperation-allowSceneActivation.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: AsyncOperation priority | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/AsyncOperation-priority.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Awaitable | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Awaitable.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Mesh isReadable | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Mesh-isReadable.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: PlayerSettings stripUnusedMeshComponents | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings-stripUnusedMeshComponents.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: PlayerSettings.SetDefaultShaderChunkSizeInMB | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings.SetDefaultShaderChunkSizeInMB.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: QualitySettings asyncUploadBufferSize | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/QualitySettings-asyncUploadBufferSize.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: QualitySettings asyncUploadPersistentBuffer | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/QualitySettings-asyncUploadPersistentBuffer.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: QualitySettings asyncUploadTimeSlice | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/QualitySettings-asyncUploadTimeSlice.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Rendering.VertexAttributeDescriptor | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.VertexAttributeDescriptor.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Resources.UnloadUnusedAssets | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Resources.UnloadUnusedAssets.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: SceneManagement.SceneManager.LoadSceneAsync | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SceneManagement.SceneManager.LoadSceneAsync.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Scripting.GarbageCollector incrementalTimeSliceNanoseconds | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Scripting.GarbageCollector-incrementalTimeSliceNanoseconds.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Scripting.GarbageCollector.CollectIncremental | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Scripting.GarbageCollector.CollectIncremental.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Scripting.GarbageCollector.GCMode | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Scripting.GarbageCollector.GCMode.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Texture2D.Apply | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Texture2D.Apply.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerCount | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerCount.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Unity.Profiling.ProfilerMarker | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Profiling.ProfilerMarker.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: Unity.Profiling.ProfilerRecorder | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Unity.Profiling.ProfilerRecorder.html | accessed 2026-09-24 |
| Unity Scripting API 6000.3: XR.XRDisplaySubsystem | https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem.html | accessed 2026-09-24 |
| 6.4 upgrade guide | https://docs.unity3d.com/6000.4/Documentation/Manual/UpgradeGuideUnity64.html | accessed 2026-09-24 |
| Unity Manual 6000.6: Manual | https://docs.unity3d.com/6000.6/Documentation/Manual/ | accessed 2026-09-24 |
| Unity Manual 6000.6: DrawCallBatching | https://docs.unity3d.com/6000.6/Documentation/Manual/DrawCallBatching.html | accessed 2026-09-24 |
| Unity Manual 6000.6: GPUInstancing | https://docs.unity3d.com/6000.6/Documentation/Manual/GPUInstancing.html | accessed 2026-09-24 |
| Unity Manual 6000.6: SL MultipleProgramVariants declare | https://docs.unity3d.com/6000.6/Documentation/Manual/SL-MultipleProgramVariants-declare.html | accessed 2026-09-24 |
| Unity Manual 6000.6: SL Use16BitPrecisionInShaders | https://docs.unity3d.com/6000.6/Documentation/Manual/SL-Use16BitPrecisionInShaders.html | accessed 2026-09-24 |
| Unity Manual 6000.6: SRPBatcher Enable | https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Enable.html | accessed 2026-09-24 |
| Unity Manual 6000.6: SRPBatcher Incompatible | https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Incompatible.html | accessed 2026-09-24 |
| Unity Manual 6000.6: SRPBatcher Materials | https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Materials.html | accessed 2026-09-24 |
| Unity Manual 6000.6: SRPBatcher Profile | https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher-Profile.html | accessed 2026-09-24 |
| Unity Manual 6000.6: SRPBatcher | https://docs.unity3d.com/6000.6/Documentation/Manual/SRPBatcher.html | accessed 2026-09-24 |
| Unity Manual 6000.6: SinglePassInstancing | https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassInstancing.html | accessed 2026-09-24 |
| Stereo rendering | https://docs.unity3d.com/6000.6/Documentation/Manual/SinglePassStereoRendering.html | accessed 2026-09-24 |
| Upgrade guides | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity6.html | accessed 2026-09-24 |
| Unity Manual 6000.6: UpgradeGuideUnity61 | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity61.html | accessed 2026-09-24 |
| Unity Manual 6000.6: UpgradeGuideUnity62 | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity62.html | accessed 2026-09-24 |
| Unity Manual 6000.6: UpgradeGuideUnity63 | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity63.html | accessed 2026-09-24 |
| Unity Manual 6000.6: UpgradeGuideUnity64 | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity64.html | accessed 2026-09-24 |
| Unity Manual 6000.6: UpgradeGuideUnity65 | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity65.html | accessed 2026-09-24 |
| Unity Manual 6000.6: UpgradeGuideUnity66 | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html | accessed 2026-09-24 |
| Unity Manual 6000.6: VRFrameTiming | https://docs.unity3d.com/6000.6/Documentation/Manual/VRFrameTiming.html | accessed 2026-09-24 |
| What's New | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity6.html | accessed 2026-09-24 |
| Unity Manual 6000.6: WhatsNewUnity61 | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity61.html | accessed 2026-09-24 |
| Unity Manual 6000.6: WhatsNewUnity62 | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity62.html | accessed 2026-09-24 |
| Unity Manual 6000.6: WhatsNewUnity63 | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html | accessed 2026-09-24 |
| Unity Manual 6000.6: WhatsNewUnity64 | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity64.html | accessed 2026-09-24 |
| Unity Manual 6000.6: WhatsNewUnity65 | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity65.html | accessed 2026-09-24 |
| Unity Manual 6000.6: WhatsNewUnity66 | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html | accessed 2026-09-24 |
| Unity Manual 6000.6: android application entries game activity requirements | https://docs.unity3d.com/6000.6/Documentation/Manual/android-application-entries-game-activity-requirements.html | accessed 2026-09-24 |
| Unity Manual 6000.6: android custom activity command line | https://docs.unity3d.com/6000.6/Documentation/Manual/android-custom-activity-command-line.html | accessed 2026-09-24 |
| Unity Manual 6000.6: android profile on an android device | https://docs.unity3d.com/6000.6/Documentation/Manual/android-profile-on-an-android-device.html | accessed 2026-09-24 |
| Unity Manual 6000.6: android thread configuration | https://docs.unity3d.com/6000.6/Documentation/Manual/android-thread-configuration.html | accessed 2026-09-24 |
| Unity Manual 6000.6: batch renderer group getting started | https://docs.unity3d.com/6000.6/Documentation/Manual/batch-renderer-group-getting-started.html | accessed 2026-09-24 |
| Unity Manual 6000.6: batch renderer group how | https://docs.unity3d.com/6000.6/Documentation/Manual/batch-renderer-group-how.html | accessed 2026-09-24 |
| Unity Manual 6000.6: class GraphicsSettings | https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html | accessed 2026-09-24 |
| Unity Manual 6000.6: class PlayerSettingsAndroid | https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html | accessed 2026-09-24 |
| Unity Manual 6000.6: class PlayerSettingsiOS | https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsiOS.html | accessed 2026-09-24 |
| Unity Manual 6000.6: frame timing manager | https://docs.unity3d.com/6000.6/Documentation/Manual/frame-timing-manager.html | accessed 2026-09-24 |
| Unity Manual 6000.6: il2cpp runtime checks | https://docs.unity3d.com/6000.6/Documentation/Manual/il2cpp-runtime-checks.html | accessed 2026-09-24 |
| Mesh LOD | https://docs.unity3d.com/6000.6/Documentation/Manual/lod/mesh-lod-introduction.html | accessed 2026-09-24 |
| On-tile post-processing | https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-post-processing.html | accessed 2026-09-24 |
| On-tile rendering | https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html | accessed 2026-09-24 |
| Unity Manual 6000.6: optimizing draw calls choose method | https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html | accessed 2026-09-24 |
| Unity Manual 6000.6: performance incremental garbage collection | https://docs.unity3d.com/6000.6/Documentation/Manual/performance-incremental-garbage-collection.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader conditionals choose a type | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-conditionals-choose-a-type.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader keywords default | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-keywords-default.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader loading | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-loading.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader prewarm other | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-prewarm-other.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader prewarm | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-prewarm.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader pso example | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-example.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader pso introduction | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-introduction.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader pso trace | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-pso-trace.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader variant stripping | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html | accessed 2026-09-24 |
| Unity Manual 6000.6: static batching enable | https://docs.unity3d.com/6000.6/Documentation/Manual/static-batching-enable.html | accessed 2026-09-24 |
| Unity Manual 6000.6: create world space ui | https://docs.unity3d.com/6000.6/Documentation/Manual/ui-systems/create-world-space-ui.html | accessed 2026-09-24 |
| Unity Manual 6000.6: world space panel input configuration | https://docs.unity3d.com/6000.6/Documentation/Manual/ui-systems/world-space-panel-input-configuration.html | accessed 2026-09-24 |
| Unity Manual 6000.6: world space ui | https://docs.unity3d.com/6000.6/Documentation/Manual/ui-systems/world-space-ui.html | accessed 2026-09-24 |
| Configure for better performance | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/configure-for-better-performance.html | accessed 2026-09-24 |
| Unity Manual 6000.6: blit overview | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/customize/blit-overview.html | accessed 2026-09-24 |
| GPU occlusion culling | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-culling.html | accessed 2026-09-24 |
| Unity Manual 6000.6: gpu resident drawer performance | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html | accessed 2026-09-24 |
| Unity Manual 6000.6: gpu resident drawer | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html | accessed 2026-09-24 |
| Unity Manual 6000.6: light limits in urp | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/lighting/light-limits-in-urp.html | accessed 2026-09-24 |
| Unity Manual 6000.6: make object compatible gpu rendering | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/make-object-compatible-gpu-rendering.html | accessed 2026-09-24 |
| APV | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/probevolumes-concept.html | accessed 2026-09-24 |
| Unity Manual 6000.6: read depth input attachment | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/read-depth-input-attachment.html | accessed 2026-09-24 |
| Unity Manual 6000.6: render graph blit | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-blit.html | accessed 2026-09-24 |
| Unity Manual 6000.6: render graph framebuffer fetch | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-framebuffer-fetch.html | accessed 2026-09-24 |
| Unity Manual 6000.6: render graph introduction | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-introduction.html | accessed 2026-09-24 |
| Unity Manual 6000.6: render graph optimize | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-optimize.html | accessed 2026-09-24 |
| Unity Manual 6000.6: render graph unsafe pass | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-unsafe-pass.html | accessed 2026-09-24 |
| Unity Manual 6000.6: render graph view | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-view.html | accessed 2026-09-24 |
| Unity Manual 6000.6: render graph viewer reference | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-viewer-reference.html | accessed 2026-09-24 |
| Unity Manual 6000.6: render graph write render pass | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/render-graph-write-render-pass.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader stripping check | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-check.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader stripping features | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-features.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader stripping fog | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-fog.html | accessed 2026-09-24 |
| STP | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/stp/stp-upscaler.html | accessed 2026-09-24 |
| URP asset reference | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/universalrp-asset.html | accessed 2026-09-24 |
| Universal Renderer reference | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/urp-universal-renderer.html | accessed 2026-09-24 |
| Unity Manual 6000.6: gpu culling | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-culling.html | accessed 2026-09-24 |
| Unity Manual 6000.6: gpu resident drawer performance | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html | accessed 2026-09-24 |
| Unity Manual 6000.6: make object compatible gpu rendering | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/make-object-compatible-gpu-rendering.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader stripping check | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-check.html | accessed 2026-09-24 |
| Unity Manual 6000.6: shader stripping fog | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-fog.html | accessed 2026-09-24 |
| VRS | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/variable-rate-shading-introduction.html | accessed 2026-09-24 |
| Tile-based rendering in XR | https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html | accessed 2026-09-24 |
| XR resolution control | https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html | accessed 2026-09-24 |
| Meta Quest build profile | https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html | accessed 2026-09-24 |
| Meta Quest shader optimizations | https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html | accessed 2026-09-24 |
| Unity Manual 6000.6: xr multiview render regions | https://docs.unity3d.com/6000.6/Documentation/Manual/xr-multiview-render-regions.html | accessed 2026-09-24 |
| XR render pipeline compatibility | https://docs.unity3d.com/6000.6/Documentation/Manual/xr-render-pipeline-compatibility.html | accessed 2026-09-24 |
| Untethered XR optimization | https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html | accessed 2026-09-24 |
| Unity Scripting API 6000.6: QualitySettings vSyncCount | https://docs.unity3d.com/6000.6/Documentation/ScriptReference/QualitySettings-vSyncCount.html | accessed 2026-09-24 |
| Unity Scripting API 6000.6: Rendering.BatchRendererGroup.AddBatch | https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.BatchRendererGroup.AddBatch.html | accessed 2026-09-24 |
| Unity Scripting API 6000.6: Rendering.GraphicsStateCollection.WarmUpProgressively | https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.GraphicsStateCollection.WarmUpProgressively.html | accessed 2026-09-24 |
| Unity Scripting API 6000.6: Rendering.GraphicsStateCollection | https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Rendering.GraphicsStateCollection.html | accessed 2026-09-24 |
| Unity Manual 6000.7: scripting backends coreclr | https://docs.unity3d.com/6000.7/Documentation/Manual/scripting-backends-coreclr.html | accessed 2026-09-24 |
| com.unity.addressables@1.21: MemoryManagement | https://docs.unity3d.com/Packages/com.unity.addressables@1.21/manual/MemoryManagement.html | accessed 2026-09-24 |
| com.unity.addressables@2.3: MemoryManagement | https://docs.unity3d.com/Packages/com.unity.addressables@2.3/manual/MemoryManagement.html | accessed 2026-09-24 |
| com.unity.burst@1.8: building projects | https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-projects.html | accessed 2026-09-24 |
| com.unity.burst@1.8: compilation burstcompile | https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstcompile.html | accessed 2026-09-24 |
| com.unity.entities.graphics@6.5: requirements and compatibility | https://docs.unity3d.com/Packages/com.unity.entities.graphics@6.5/manual/requirements-and-compatibility.html | accessed 2026-09-24 |
| URP 12.1 XR SPI blit | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/renderer-features/how-to-fullscreen-blit-in-xr-spi.html | accessed 2026-09-24 |
| URP 12.1 asset | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/universalrp-asset.html | accessed 2026-09-24 |
| URP 12.1 renderer | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/urp-universal-renderer.html | accessed 2026-09-24 |
| URP 14 ScriptableRenderPass API | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/api/UnityEngine.Rendering.Universal.ScriptableRenderPass.html | accessed 2026-09-24 |
| URP 14 full-screen blit | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/renderer-features/how-to-fullscreen-blit.html | accessed 2026-09-24 |
| URP 14 Forward+ | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/rendering/forward-plus-rendering-path.html | accessed 2026-09-24 |
| URP 14 asset | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html | accessed 2026-09-24 |
| com.unity.render-pipelines.universal@14.0: upgrade guide 2022 1 | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/upgrade-guide-2022-1.html | accessed 2026-09-24 |
| com.unity.render-pipelines.universal@14.0: upgrade guide 2022 2 | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/upgrade-guide-2022-2.html | accessed 2026-09-24 |
| com.unity.render-pipelines.universal@14.0: urp global settings | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-global-settings.html | accessed 2026-09-24 |
| URP 14 Universal Renderer (Native RenderPass) | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html | accessed 2026-09-24 |
| com.unity.render-pipelines.universal@17.0: CHANGELOG | https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/changelog/CHANGELOG.html | accessed 2026-09-24 |
| com.unity.shadergraph@17.0: Precision Modes | https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Precision-Modes.html | accessed 2026-09-24 |
| com.unity.ugui@2.0: HOWTO UIWorldSpace | https://docs.unity3d.com/Packages/com.unity.ugui@2.0/manual/HOWTO-UIWorldSpace.html | accessed 2026-09-24 |
| com.unity.ugui@2.0: script GraphicRaycaster | https://docs.unity3d.com/Packages/com.unity.ugui@2.0/manual/script-GraphicRaycaster.html | accessed 2026-09-24 |
| Unity OpenXR Meta 2.6 graphics settings | https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/get-started/graphics-settings.html | accessed 2026-09-24 |
| Oculus XR plugin (Optimize Buffer Discard) | https://docs.unity3d.com/Packages/com.unity.xr.oculus@1.12/manual/index.html | accessed 2026-09-24 |
| com.unity.xr.openxr@1.18: project configuration | https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/project-configuration.html | accessed 2026-09-24 |
| com.unity.xr.openxr@1.19: CHANGELOG | https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html | accessed 2026-09-24 |
| Unity Release API | https://services.api.unity.com/unity/editor/release/v1/releases | accessed 2026-09-24 |
| releases | https://services.api.unity.com/unity/editor/release/v1/releases?version=2021.3 | accessed 2026-09-24 |
| releases | https://services.api.unity.com/unity/editor/release/v1/releases?version=2022.3 | accessed 2026-09-24 |
| releases | https://services.api.unity.com/unity/editor/release/v1/releases?version=6000.6 | accessed 2026-09-24 |
| releases | https://services.api.unity.com/unity/editor/release/v1/releases?version=6000.7 | accessed 2026-09-24 |
| 10000 update calls | https://unity.com/blog/engine-platform/10000-update-calls | accessed 2026-09-24 |
| batchrenderergroup sample high frame rate on budget devices | https://unity.com/blog/engine-platform/batchrenderergroup-sample-high-frame-rate-on-budget-devices | accessed 2026-09-24 |
| srp batcher speed up your rendering | https://unity.com/blog/engine-platform/srp-batcher-speed-up-your-rendering | accessed 2026-09-24 |
| understanding the async upload pipeline | https://unity.com/blog/engine-platform/understanding-the-async-upload-pipeline | published/updated 2018-10-08; accessed 2026-09-24 |
| unity ui optimization tips | https://unity.com/how-to/unity-ui-optimization-tips | accessed 2026-09-24 |
| archive | https://unity.com/releases/editor/archive | accessed 2026-09-24 |
| Release notes 2022.3.53f1 | https://unity.com/releases/editor/whats-new/2022.3.53f1 | accessed 2026-09-24 |
| Release notes 6000.0.0 | https://unity.com/releases/editor/whats-new/6000.0.0 | accessed 2026-09-24 |
| Release notes 6000.0.0b11 | https://unity.com/releases/editor/whats-new/6000.0.0b11 | accessed 2026-09-24 |
| Release notes 6000.0.0b12 | https://unity.com/releases/editor/whats-new/6000.0.0b12 | accessed 2026-09-24 |
| Release notes 6000.0.0b15 | https://unity.com/releases/editor/whats-new/6000.0.0b15 | accessed 2026-09-24 |
| Release notes 6000.0.14f1 | https://unity.com/releases/editor/whats-new/6000.0.14f1 | accessed 2026-09-24 |
| Release notes 6000.0.22f1 | https://unity.com/releases/editor/whats-new/6000.0.22f1 | accessed 2026-09-24 |
| Release notes 6000.0.23f1 | https://unity.com/releases/editor/whats-new/6000.0.23f1 | accessed 2026-09-24 |
| Release notes 6000.0.25f1 | https://unity.com/releases/editor/whats-new/6000.0.25f1 | accessed 2026-09-24 |
| Release notes 6000.0.38f1 | https://unity.com/releases/editor/whats-new/6000.0.38f1 | accessed 2026-09-24 |
| Release notes 6000.0.46f1 | https://unity.com/releases/editor/whats-new/6000.0.46f1 | accessed 2026-09-24 |
| Release notes 6000.0.49f1 | https://unity.com/releases/editor/whats-new/6000.0.49f1 | accessed 2026-09-24 |
| Release notes 6000.0.50f1 | https://unity.com/releases/editor/whats-new/6000.0.50f1 | accessed 2026-09-24 |
| Release notes 6000.0.52f1 | https://unity.com/releases/editor/whats-new/6000.0.52f1 | accessed 2026-09-24 |
| Release notes 6000.0.55f1 | https://unity.com/releases/editor/whats-new/6000.0.55f1 | accessed 2026-09-24 |
| Release notes 6000.0.57f1 | https://unity.com/releases/editor/whats-new/6000.0.57f1 | accessed 2026-09-24 |
| Release notes 6000.0.65f1 | https://unity.com/releases/editor/whats-new/6000.0.65f1 | accessed 2026-09-24 |
| Release notes 6000.0.73f1 | https://unity.com/releases/editor/whats-new/6000.0.73f1 | accessed 2026-09-24 |
| Release notes 6000.0.74f1 | https://unity.com/releases/editor/whats-new/6000.0.74f1 | accessed 2026-09-24 |
| Release notes 6000.0.83f1 | https://unity.com/releases/editor/whats-new/6000.0.83f1 | accessed 2026-09-24 |
| Release notes 6000.0.84f1 | https://unity.com/releases/editor/whats-new/6000.0.84f1 | accessed 2026-09-24 |
| Release notes 6000.1.0a8 | https://unity.com/releases/editor/whats-new/6000.1.0a8 | accessed 2026-09-24 |
| Release notes 6000.2.0a4 | https://unity.com/releases/editor/whats-new/6000.2.0a4 | accessed 2026-09-24 |
| Release notes 6000.2.12f1 | https://unity.com/releases/editor/whats-new/6000.2.12f1 | accessed 2026-09-24 |
| Release notes 6000.3.0a2 | https://unity.com/releases/editor/whats-new/6000.3.0a2 | accessed 2026-09-24 |
| Release notes 6000.3.0a5 | https://unity.com/releases/editor/whats-new/6000.3.0a5 | accessed 2026-09-24 |
| Release notes 6000.3.0b1 | https://unity.com/releases/editor/whats-new/6000.3.0b1 | accessed 2026-09-24 |
| Release notes 6000.3.0f1 | https://unity.com/releases/editor/whats-new/6000.3.0f1 | accessed 2026-09-24 |
| Release notes 6000.3.12f1 | https://unity.com/releases/editor/whats-new/6000.3.12f1 | accessed 2026-09-24 |
| Release notes 6000.3.14f1 | https://unity.com/releases/editor/whats-new/6000.3.14f1 | accessed 2026-09-24 |
| Release notes 6000.3.21f1 | https://unity.com/releases/editor/whats-new/6000.3.21f1 | accessed 2026-09-24 |
| Release notes 6000.3.23f1 | https://unity.com/releases/editor/whats-new/6000.3.23f1 | accessed 2026-09-24 |
| Release notes 6000.3.24f1 | https://unity.com/releases/editor/whats-new/6000.3.24f1 | accessed 2026-09-24 |
| Release notes 6000.4.0a4 | https://unity.com/releases/editor/whats-new/6000.4.0a4 | accessed 2026-09-24 |
| Release notes 6000.4.0b9 | https://unity.com/releases/editor/whats-new/6000.4.0b9 | accessed 2026-09-24 |
| Release notes 6000.4.0f1 | https://unity.com/releases/editor/whats-new/6000.4.0f1 | accessed 2026-09-24 |
| Release notes 6000.5.0 | https://unity.com/releases/editor/whats-new/6000.5.0 | accessed 2026-09-24 |
| Release notes 6000.5.0a9 | https://unity.com/releases/editor/whats-new/6000.5.0a9 | accessed 2026-09-24 |
| Release notes 6000.5.0b1 | https://unity.com/releases/editor/whats-new/6000.5.0b1 | accessed 2026-09-24 |
| Release notes 6000.5.0b4 | https://unity.com/releases/editor/whats-new/6000.5.0b4 | accessed 2026-09-24 |
| Release notes 6000.5.8f1 | https://unity.com/releases/editor/whats-new/6000.5.8f1 | accessed 2026-09-24 |
| Release notes 6000.6.0 | https://unity.com/releases/editor/whats-new/6000.6.0 | accessed 2026-09-24 |
| Release notes 6000.6.0a5 | https://unity.com/releases/editor/whats-new/6000.6.0a5 | accessed 2026-09-24 |
| Release notes 6000.6.0b1 | https://unity.com/releases/editor/whats-new/6000.6.0b1 | accessed 2026-09-24 |
| Release notes 6000.6.0b6 | https://unity.com/releases/editor/whats-new/6000.6.0b6 | accessed 2026-09-24 |
| Release notes 6000.6.0f1 | https://unity.com/releases/editor/whats-new/6000.6.0f1 | accessed 2026-09-24 |
| Release notes 6000.7.0a2 | https://unity.com/releases/editor/whats-new/6000.7.0a2 | accessed 2026-09-24 |
| Release notes 6000.7.0a3 | https://unity.com/releases/editor/whats-new/6000.7.0a3 | accessed 2026-09-24 |
| Release notes (per version) | https://unity.com/releases/editor/whats-new/<version | accessed 2026-09-24 |
| Unity 6 support windows | https://unity.com/releases/unity-6/support | accessed 2026-09-24 |
| Unity 6 mobile/XR/web e-book landing page | https://unity.com/resources/mobile-xr-web-game-performance-optimization-unity-6 | accessed 2026-09-24 |
| Render pipelines strategy 2026 | https://unity.com/topics/render-pipelines-strategy-for-2026 | accessed 2026-09-24 |
| Unity Manual 6000.0: DrawCallBatching (gap-fill round 1) | https://docs.unity3d.com/6000.0/Documentation/Manual/DrawCallBatching.html | accessed 2026-09-24 |
| Unity Manual 6000.3: DrawCallBatching (gap-fill round 1) | https://docs.unity3d.com/6000.3/Documentation/Manual/DrawCallBatching.html | accessed 2026-09-24 |
| Unity Manual 6000.0: Choose a draw call optimization method (gap-fill round 1) | https://docs.unity3d.com/6000.0/Documentation/Manual/optimizing-draw-calls-choose-method.html | accessed 2026-09-24 |
| Unity Manual 6000.0: URP Asset (gap-fill round 1) | https://docs.unity3d.com/6000.0/Documentation/Manual/urp/universalrp-asset.html | accessed 2026-09-24 |
| com.unity.shadergraph@17.0: Keywords reference (gap-fill round 1) | https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Keywords-reference.html | accessed 2026-09-24 |
| com.unity.shadergraph@17.0: Keywords concepts (gap-fill round 1) | https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Keywords-concepts.html | accessed 2026-09-24 |
| com.unity.shadergraph@17.0: Shader Graph Project Settings (gap-fill round 1) | https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Project-Settings.html | accessed 2026-09-24 |
| com.unity.shadergraph@17.3: Surface options / Allow Material Override (gap-fill round 1) | https://docs.unity3d.com/Packages/com.unity.shadergraph@17.3/manual/surface-options.html | accessed 2026-09-24 |
| com.unity.shadergraph@14.0: Surface options / Allow Material Override (gap-fill round 1) | https://docs.unity3d.com/Packages/com.unity.shadergraph@14.0/manual/surface-options.html | accessed 2026-09-24 |
| E-book PDF: Optimize your game performance for mobile, XR, and the web in Unity (Unity 6 edition) (gap-fill round 1) | https://cdn.bfldr.com/S5BC9Y64/at/3mp8w3wk36k2k6mmj5pbbr/Optimize_your_game_performance_for_mobile__XR__and_the_web_in_Unity_Unity_6_edition_e-book.pdf | published/updated 2024-10-17; accessed 2026-09-24 |
| Unity blog: Unity 6 optimization guides (gap-fill round 1) | https://unity.com/blog/unity-6-game-optimization-guides | published/updated 2024-11-11; accessed 2026-09-24 |
| XR e-book landing page: Create virtual and mixed reality experiences in Unity (gap-fill round 2) | https://unity.com/resources/create-virtual-mixed-reality-experiences-unity | published/updated 2024-06-27; accessed 2026-09-24 |
| XR e-book PDF, Unity 2022 LTS edition (gap-fill round 2) | https://cdn.bfldr.com/S5BC9Y64/at/88s95mhhwcsshcgrwbm7c5g/Create_virtual_and_mixed_reality_experiences_in_Unity_e-book.pdf | ©2024; accessed 2026-09-24 |
| Unity Security Update Advisory CVE-2025-59489 (gap-fill round 2) | https://unity.com/security/sept-2025-01 | patches 2025-10-02; accessed 2026-09-24 |
| Unity LTS releases page (gap-fill round 2) | https://unity.com/releases/lts | accessed 2026-09-24 |
| Unity Release API, 6000.7 stream (gap-fill round 2) | https://services.api.unity.com/unity/editor/release/v1/releases?version=6000.7 | accessed 2026-09-24 |
| Unity 6000.7.0b2 release notes (gap-fill round 2) | https://unity.com/releases/editor/whats-new/6000.7.0b2 | 2026-09-23; accessed 2026-09-24 |
| Unity 6000.7.0a6 release notes (gap-fill round 2) | https://unity.com/releases/editor/whats-new/6000.7.0a6 | 2026-09-03; accessed 2026-09-24 |
| Unity 6000.5.6f1 release notes, Known Issues (gap-fill round 2) | https://unity.com/releases/editor/whats-new/6000.5.6f1 | accessed 2026-09-24 |
| Unity 6000.1.0b12 release notes (gap-fill round 1) | https://unity.com/releases/editor/whats-new/6000.1.0b12 | accessed 2026-09-24 |
| Unity 6000.1.0b14 release notes (gap-fill round 1) | https://unity.com/releases/editor/whats-new/6000.1.0b14 | accessed 2026-09-24 |

### Meta

| Title | URL | Date |
| --- | --- | --- |
| avoiding hitches when loading scenes in unity | https://developers.meta.com/horizon/blog/avoiding-hitches-when-loading-scenes-in-unity/ | published/updated 2021-12-15; accessed 2026-09-24 |
| tech note unity settings for mobile vr | https://developers.meta.com/horizon/blog/tech-note-unity-settings-for-mobile-vr/ | published/updated 2018-04-12; accessed 2026-09-24 |
| top tips from arm for vr asset optimization | https://developers.meta.com/horizon/blog/top-tips-from-arm-for-vr-asset-optimization/ | published/updated 2020-10-02; accessed 2026-09-24 |
| mobile msaa analysis | https://developers.meta.com/horizon/documentation/native/android/mobile-msaa-analysis/ | accessed 2026-09-24 |
| enable multiview | https://developers.meta.com/horizon/documentation/unity/enable-multiview/ | accessed 2026-09-24 |
| gpu impaired algorithms | https://developers.meta.com/horizon/documentation/unity/gpu-impaired-algorithms/ | accessed 2026-09-24 |
| gpu improved algorithms | https://developers.meta.com/horizon/documentation/unity/gpu-improved-algorithms/ | accessed 2026-09-24 |
| gpu tiled | https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ | accessed 2026-09-24 |
| os cpu gpu levels | https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ | accessed 2026-09-24 |
| os missed frames | https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ | accessed 2026-09-24 |
| os render scale | https://developers.meta.com/horizon/documentation/unity/os-render-scale/ | accessed 2026-09-24 |
| po advanced gpu pipelines | https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ | accessed 2026-09-24 |
| po draw call analysis | https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ | accessed 2026-09-24 |
| po graphics jobs | https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ | accessed 2026-09-24 |
| po perf opt mobile | https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ | accessed 2026-09-24 |
| po quest boost | https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ | accessed 2026-09-24 |
| po renderdoc optimizations 1 | https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-1/ | accessed 2026-09-24 |
| po renderdoc optimizations 2 | https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-2/ | accessed 2026-09-24 |
| ps shader compilation | https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ | accessed 2026-09-24 |
| tools unityprofiler | https://developers.meta.com/horizon/documentation/unity/tools-unityprofiler/ | accessed 2026-09-24 |
| ts draw call metrics | https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ | accessed 2026-09-24 |
| ts perfettoguide | https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ | accessed 2026-09-24 |
| ts renderdoc shaderstats | https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ | accessed 2026-09-24 |
| unity and openxr compatibility | https://developers.meta.com/horizon/documentation/unity/unity-and-openxr-compatibility | accessed 2026-09-24 |
| unity best practices intro | https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ | published/updated 2024-09-15; accessed 2026-09-24 |
| unity forward plus rendering | https://developers.meta.com/horizon/documentation/unity/unity-forward-plus-rendering/ | accessed 2026-09-24 |
| unity mobile performance intro | https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ | accessed 2026-09-24 |
| unity openxr settings | https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ | accessed 2026-09-24 |
| unity perf | https://developers.meta.com/horizon/documentation/unity/unity-perf/ | accessed 2026-09-24 |
| unity profiler tool | https://developers.meta.com/horizon/documentation/unity/unity-profiler-tool/ | accessed 2026-09-24 |
| unity project setup | https://developers.meta.com/horizon/documentation/unity/unity-project-setup/ | accessed 2026-09-24 |
| vulkan subpasses | https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ | accessed 2026-09-24 |
| device optimization comparison | https://developers.meta.com/horizon/resources/device-optimization-comparison/ | published/updated 2026-05-11; accessed 2026-09-24 |
| compare devices (gap-fill round 1) | https://developers.meta.com/horizon/essentials/compare-devices/ | published/updated 2026-09-18; accessed 2026-09-24 |
| unity set disp freq (gap-fill round 1) | https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ | accessed 2026-09-24 |
| optimize performance (cited via quest dossier, gap-fill round 1) | https://developers.meta.com/horizon/documentation/unity/optimize-performance/ | accessed 2026-09-24 |

### Android / Google

| Title | URL | Date |
| --- | --- | --- |
| optimizing performance for android xr | https://android-developers.googleblog.com/2025/10/optimizing-performance-for-android-xr.html | accessed 2026-09-24 |
| gpu rendering | https://developer.android.com/develop/xr/unity/performance/gpu-rendering | published/updated 2026-05-19; accessed 2026-09-24 |

### GitHub (ARM-software)

| Title | URL | Date |
| --- | --- | --- |
| Encoding | https://github.com/ARM-software/astc-encoder/blob/main/Docs/Encoding.md | accessed 2026-09-24 |

### GitHub (icosa-mirror)

| Title | URL | Date |
| --- | --- | --- |
| com.meta.xr.sdk.core | https://github.com/icosa-mirror/com.meta.xr.sdk.core | accessed 2026-09-24 |
| OVRInput | https://github.com/icosa-mirror/com.meta.xr.sdk.core/blob/main/Scripts/OVRInput.cs | accessed 2026-09-24 |

### GitHub (oculus-samples)

| Title | URL | Date |
| --- | --- | --- |
| Unity ShaderPrewarmer | https://github.com/oculus-samples/Unity-ShaderPrewarmer | accessed 2026-09-24 |

### GitHub (sebastianstarke)

| Title | URL | Date |
| --- | --- | --- |
| AI4Animation | https://github.com/sebastianstarke/AI4Animation | accessed 2026-09-24 |

### Internet Archive (snapshot)

| Title | URL | Date |
| --- | --- | --- |
| performance vulkan performing much worse than opengles due to excessive buffer copies on quest 2 slash 3 | https://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 | accessed 2026-09-24 |

### Mesa (community)

| Title | URL | Date |
| --- | --- | --- |
| lrz | https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html | accessed 2026-09-24 |

### Qualcomm (gap-fill round 1)

| Title | URL | Date |
| --- | --- | --- |
| Snapdragon XR2 Gen 2 Platform Product Brief | https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf | accessed 2026-09-24 |
| Snapdragon XR2+ Gen 2 Platform Product Brief, 87-73622-1 Rev A (gap-fill round 2) | https://docs.qualcomm.com/doc/87-73622-1/87-73622-1_REV_A_Snapdragon_XR2__Gen_2_Platform_Product_Brief.pdf | ©2024; accessed 2026-09-24 |
| Snapdragon XR2 Gen 2 Reference Design Product Brief, 87-61723-1 Rev B (gap-fill round 2) | https://docs.qualcomm.com/bundle/publicresource/87-61723-1_REV_B_Snapdragon_XR2_Gen_2_Reference_Design_Product_Brief.pdf | ©2024; accessed 2026-09-24 |

### Unity (GitHub source)

| Title | URL | Date |
| --- | --- | --- |
| Graphics | https://github.com/Unity-Technologies/Graphics | accessed 2026-09-24 |
| XRSystem | https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRSystem.cs | accessed 2026-09-24 |
| BaseShaderGUI | https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGUI/BaseShaderGUI.cs | accessed 2026-09-24 |
| ScriptableRenderPass | https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/Passes/ScriptableRenderPass.cs | accessed 2026-09-24 |
| UniversalRenderPipeline | https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs | accessed 2026-09-24 |
| UniversalRenderer | https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderer.cs | accessed 2026-09-24 |
| ShaderVariablesFunctions | https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/ShaderLibrary/ShaderVariablesFunctions.hlsl | accessed 2026-09-24 |
| ProbeBrickPool | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/Runtime/Lighting/ProbeVolume/ProbeBrickPool.cs | accessed 2026-09-24 |
| ProbeReferenceVolume | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/Runtime/Lighting/ProbeVolume/ProbeReferenceVolume.cs | accessed 2026-09-24 |
| XRMirrorView | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRMirrorView.cs | accessed 2026-09-24 |
| Packing | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.core/ShaderLibrary/Packing.hlsl | accessed 2026-09-24 |
| UniversalRenderPipelineAsset | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/Data/UniversalRenderPipelineAsset.cs | accessed 2026-09-24 |
| FullScreenPassRendererFeature | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/RendererFeatures/FullScreenPassRendererFeature.cs | accessed 2026-09-24 |
| UniversalRenderPipeline | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs | accessed 2026-09-24 |
| UniversalRenderPipelineCore | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipelineCore.cs | accessed 2026-09-24 |
| UniversalRendererRenderGraph | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRendererRenderGraph.cs | accessed 2026-09-24 |
| NativePassCompiler | https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/NativePassCompiler.cs | accessed 2026-09-24 |
| PassesData | https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs | accessed 2026-09-24 |
| UniversalRendererDataEditor | https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/Editor/UniversalRendererDataEditor.cs | accessed 2026-09-24 |
| UniversalRenderPipelineAsset | https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/Runtime/Data/UniversalRenderPipelineAsset.cs | accessed 2026-09-24 |
| XRPass | https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/Runtime/XR/XRPass.cs | accessed 2026-09-24 |
| Common | https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl | accessed 2026-09-24 |
| TextureXR | https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/TextureXR.hlsl | accessed 2026-09-24 |
| UnityInstancing | https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/UnityInstancing.hlsl | accessed 2026-09-24 |
| DrawObjectsPass | https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/Runtime/Passes/DrawObjectsPass.cs | accessed 2026-09-24 |
| Lighting | https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl | accessed 2026-09-24 |
| UnityInput | https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/UnityInput.hlsl | accessed 2026-09-24 |
| Lit | https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/Shaders/Lit.shader | accessed 2026-09-24 |
| package | https://raw.githubusercontent.com/Unity-Technologies/Graphics/2022.3/staging/Packages/com.unity.render-pipelines.universal/package.json | accessed 2026-09-24 |
| package | https://raw.githubusercontent.com/Unity-Technologies/Graphics/6000.5/staging/Packages/com.unity.render-pipelines.universal/package.json | accessed 2026-09-24 |
| URP package.json per branch | `raw.githubusercontent.com/Unity-Technologies/Graphics/<branch>/Packages/com.unity.render-pipelines.universal/package.json` | accessed 2026-09-24 |
| ShaderGraphProjectSettings.cs, 6000.0/staging (gap-fill round 1) | https://raw.githubusercontent.com/Unity-Technologies/Graphics/6000.0/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs | accessed 2026-09-24 |
| ShaderGraphProjectSettings.cs, 2022.3 / 6000.3 / 6000.5 / master (gap-fill round 2) | https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs (same path on 6000.3/staging, 6000.5/staging, master) | accessed 2026-09-24 |
| ShaderGraphPreferences.cs, 2021.3 / 2022.3 (gap-fill round 2) | https://github.com/Unity-Technologies/Graphics/blob/2021.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphPreferences.cs (same path on 2022.3/staging) | accessed 2026-09-24 |
| UniversalTarget.cs, 2021.3 / 2022.3 / 6000.3 (gap-fill round 2) | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Targets/UniversalTarget.cs (same path on 2021.3/staging, 2022.3/staging) | accessed 2026-09-24 |
| UniversalLitSubTarget.cs, 6000.3 (gap-fill round 2) | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Targets/UniversalLitSubTarget.cs | accessed 2026-09-24 |
| BaseShaderGUI.cs, 6000.3 (gap-fill round 2) | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGUI/BaseShaderGUI.cs | accessed 2026-09-24 |
| ForwardPlusKeyword.deprecated.hlsl, 6000.1 / 6000.5 (gap-fill round 2) | https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/ShaderLibrary/ForwardPlusKeyword.deprecated.hlsl | accessed 2026-09-24 |
| ForwardLights.cs, 6000.5 (gap-fill round 2) | https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.universal/Runtime/ForwardLights.cs | accessed 2026-09-24 |

### Unity Discussions (community)

| Title | URL | Date |
| --- | --- | --- |
| 1517687 | https://discussions.unity.com/t/change-fixeddeltatime-for-meta-quest/1517687 | accessed 2026-09-24 |
| 1723299 | https://discussions.unity.com/t/coreclr-scripting-and-serialization-update-june-2026/1723299 | accessed 2026-09-24 |
| 951031 | https://discussions.unity.com/t/graphicsstatecollection-tracing-and-warmup-in-unity-6/951031 | accessed 2026-09-24 |
| 1681683 | https://discussions.unity.com/t/how-to-import-color-backbuffer-to-read-on-meta-quest-3-vulkan/1681683 | accessed 2026-09-24 |
| 707 | https://discussions.unity.com/t/introduction-of-render-graph-in-the-universal-render-pipeline-urp/930355/707 | accessed 2026-09-24 |
| 1552250 | https://discussions.unity.com/t/meta-quest-shadows-unsmoothed-low-resolution-regardless-of-settings/1552250 | published/updated 2024-11-12; accessed 2026-09-24 |
| 860072 | https://discussions.unity.com/t/optimized-frame-pacing-for-oculus-quest-2-and-other-android-headsets/860072 | accessed 2026-09-24 |
| 1714279 | https://discussions.unity.com/t/path-to-coreclr-2026-upgrade-guide/1714279 | accessed 2026-09-24 |
| 1703007 | https://discussions.unity.com/t/performant-and-energy-efficient-rendering-with-render-graph-and-on-tile-post-processing-for-untethered-xr-in-unity-6-3/1703007 | accessed 2026-09-24 |
| 1554861 | https://discussions.unity.com/t/resident-drawer-performance/1554861 | accessed 2026-09-24 |
| 920692 | https://discussions.unity.com/t/resources-unloadunusedassets-execution-time-slowly-increases-over-time/920692 | accessed 2026-09-24 |
| 1721546 | https://discussions.unity.com/t/unity-64-and-development-build-deprecation-and-managed-code-variants/1721546 | accessed 2026-09-24 |
| 942672 | https://discussions.unity.com/t/urp-adaptive-probe-volumes-per-vertex-quality-setting-location/942672 | accessed 2026-09-24 |
| Unity Discussions | https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 | accessed 2026-09-24 |
| 1584869 | https://discussions.unity.com/t/xr-occlusion-mesh-missing-in-meta-quest-headsets/1584869 | accessed 2026-09-24 |
| vulkan bug quest 2 urp graphics jobs no multithreaded rendering slow.1208908 | https://discussions.unity.com/threads/vulkan-bug-quest-2-urp-graphics-jobs-no-multithreaded-rendering-slow.1208908/ | accessed 2026-09-24 |
| 918879: URP/HDRP Shader Graph code gen optimization (gap-fill round 1) | https://discussions.unity.com/t/urp-hdrp-shader-graph-code-gen-optimization/918879 | published/updated 2023-05-25; accessed 2026-09-24 |
| 918888: URP ShaderGraph versus writing URP shaders by hand (gap-fill round 1) | https://discussions.unity.com/t/urp-shadergraph-versus-writing-urp-shaders-with-lighting-by-hand/918888 | published/updated 2023-05-25; accessed 2026-09-24 |
| 1652230: 2022.3 LTS is now Enterprise and Industry only? (gap-fill round 2) | https://discussions.unity.com/t/2022-3-lts-is-now-enterprise-and-industry-only/1652230 | published/updated 2025-06-06; accessed 2026-09-24 |

### endoflife.date (community, gap-fill round 2)

| Title | URL | Date |
| --- | --- | --- |
| Unity product page source | https://github.com/endoflife-date/endoflife.date/blob/master/products/unity.md | accessed 2026-09-24 |

### Unity Issue Tracker

| Title | URL | Date |
| --- | --- | --- |
| 1364 | https://issuetracker.unity.com/api/v1.0/issues/1364 | accessed 2026-09-24 |
| 1364 | https://issuetracker.unity.com/issues/1364 | accessed 2026-09-24 |
| gpu utilization increases by 20 on meta quest headsets when render graph is enabled on 6000016f1 and higher | https://issuetracker.unity.com/issues/21971/gpu-utilization-increases-by-20-on-meta-quest-headsets-when-render-graph-is-enabled-on-6000016f1-and-higher | accessed 2026-09-24 |
| gpu utilization increases by 20 percent on meta quest headsets when render graph is enabled on 6000 dot 0 16f1 and higher | https://issuetracker.unity3d.com/issues/gpu-utilization-increases-by-20-percent-on-meta-quest-headsets-when-render-graph-is-enabled-on-6000-dot-0-16f1-and-higher | accessed 2026-09-24 |
| performance vulkan performing much worse than opengles due to excessive buffer copies on quest 2 slash 3 | https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 | accessed 2026-09-24 |
| the player hangs when unloading a scene using the unloadunusedassets method | https://issuetracker.unity3d.com/issues/the-player-hangs-when-unloading-a-scene-using-the-unloadunusedassets-method | accessed 2026-09-24 |
| the view renders black when using framebuffer fetch with foveated rendering in a player for meta quest | https://issuetracker.unity3d.com/issues/the-view-renders-black-when-using-framebuffer-fetch-with-foveated-rendering-in-a-player-for-meta-quest | accessed 2026-09-24 |

### communityforums.atmeta.com

| Title | URL | Date |
| --- | --- | --- |
| 751740 | https://communityforums.atmeta.com/discussions/dev-unity/time---fixed-timestep--hz-values-for-oculus-devices-in-unity/751740 | accessed 2026-09-24 |

### en.wikipedia.org

| Title | URL | Date |
| --- | --- | --- |
| Meta Quest 3 | https://en.wikipedia.org/wiki/Meta_Quest_3 | accessed 2026-09-24 |

### gamedevllm.com

| Title | URL | Date |
| --- | --- | --- |
| unity 6 urp adaptive probe volumes deep dive en | https://gamedevllm.com/en/unity-6-urp-adaptive-probe-volumes-deep-dive-en/ | accessed 2026-09-24 |

### packages.unity.com

| Title | URL | Date |
| --- | --- | --- |
| com.unity.burst | https://packages.unity.com/com.unity.burst | accessed 2026-09-24 |
| com.unity.memoryprofiler | https://packages.unity.com/com.unity.memoryprofiler | accessed 2026-09-24 |
| com.unity.performance.profile analyzer | https://packages.unity.com/com.unity.performance.profile-analyzer | accessed 2026-09-24 |
| com.unity.project auditor | https://packages.unity.com/com.unity.project-auditor | accessed 2026-09-24 |

### skarredghost.com

| Title | URL | Date |
| --- | --- | --- |
| meta quest 207 hz how to | https://skarredghost.com/2026/09/01/meta-quest-207-hz-how-to/ | accessed 2026-09-24 |

### thegamedev.guru

| Title | URL | Date |
| --- | --- | --- |
| job system excessive multithreading | https://thegamedev.guru/unity-performance/job-system-excessive-multithreading/ | accessed 2026-09-24 |

### www.digitalproduction.com

| Title | URL | Date |
| --- | --- | --- |
| Unite 2025 roadmap report (CoreCLR, cadence) | https://www.digitalproduction.com/2025/11/26/unitys-2026-roadmap-coreclr-verified-packages-fewer-surprises/ | published/updated 2025-11-26; accessed 2026-09-24 |

### www.gamedeveloper.com

| Title | URL | Date |
| --- | --- | --- |
| when is unity really unloading your assets from memory | https://www.gamedeveloper.com/programming/when-is-unity-really-unloading-your-assets-from-memory- | accessed 2026-09-24 |

### www.youtube.com

| Title | URL | Date |
| --- | --- | --- |
| watch | https://www.youtube.com/watch?v=K3-wPnhmDi4 | accessed 2026-09-24 |

Added during synthesis (X-C8 source check): Lit.shader, master branch, Unity (GitHub source), https://raw.githubusercontent.com/Unity-Technologies/Graphics/master/Packages/com.unity.render-pipelines.universal/Shaders/Lit.shader, accessed 2026-09-24.

Unity source files read from `github.com/Unity-Technologies/Graphics` `<version>/staging` branches (U2): UniversalRenderPipelineAsset.cs, UniversalRendererData.cs, ScriptableRendererData.cs, UniversalRenderer.cs, UniversalRendererRenderGraph.cs, UniversalRenderPipeline.cs, Passes/ScriptableRenderPass.cs, Passes/DrawObjectsPass.cs, Passes/FinalBlitPass.cs, RendererFeatures/FullScreenPassRendererFeature.cs, XR/XRPassUniversal.cs, Editor/UniversalRendererDataEditor.cs, XR/XRSystem.cs, XR/XRMirrorView.cs, RenderGraph/RenderGraph.cs, RenderGraph/Compiler/NativePassCompiler.cs, RenderGraph/Compiler/PassesData.cs.
