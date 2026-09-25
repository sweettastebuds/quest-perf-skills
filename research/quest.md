# quest-perf research dossier

**Scope.** This dossier covers the performance of Unity URP apps on standalone Meta Quest 2 (Snapdragon XR2 Gen 1, Adreno 650, 6 GB) and Quest 3 / Quest 3S (XR2 Gen 2, Adreno 740, 8 GB). Vulkan comes first; OpenGL ES is legacy. It covers:
- **Triage:** CPU-bound vs GPU-bound vs pacing/compositor-bound.
- **Budgets:** per-device budgets and quality tiers.
- **Frame pacing:** stale and early frames, FrameSync / Phase Sync, late latching, CPU/GPU levels, refresh rate, thermal behaviour over long sessions.
- **Resolution:** eye-buffer size, render scale, fixed foveated rendering (FFR), dynamic resolution, Vulkan subsampled layout, symmetric projection, Multiview Render Regions.
- **AppSW:** Application SpaceWarp.
- **Compositor layers:** UI and text.
- **Quest 3 mixed-reality costs:** passthrough, Passthrough Camera API, Depth API, Scene/MRUK, hand and body tracking.
- **SDK and plugin choices:** Meta XR Core SDK vs Unity OpenXR + OpenXR: Meta vs the legacy Oculus XR Plugin.
- **Profiling toolkit:** OVR Metrics Tool, logcat, MQDH, Perfetto, `metavr`, RenderDoc Meta Fork, ovrgpuprofiler, ADB properties, in-app hooks.
- **Also:** real headroom after compositor and OS overhead, store VRCs, and the OVR Metrics CSV column format.

Unity range: 2021.3 LTS (URP 12) through Unity 6.6 (6000.6, URP 17.x). Unity 6.7 had not shipped by the access date (beta or alpha only; QX-C3), so it is excluded.

Out of scope: PC VR and Link, HDRP (one line: Q3-092), Unreal (cited only where an Unreal page contradicts a Unity one), and Godot. Quest Pro and eye-tracked foveation get one finding (Q2-007 / Q3-040 / Q4-008). Meta VR Glasses appear only as context (Q2-008).

**Access date.** 2026-09-24 for every source.

**Method.**
- **Topic research.** Four topic researchers wrote research notes from web sources:
  - Q1: profiling toolkit, triage, logcat/ADB, VRCs.
  - Q2: devices, budgets, pacing, CPU/GPU levels, thermals.
  - Q3: resolution, foveation, dynamic resolution, AppSW, compositor layers.
  - Q4: mixed-reality costs and SDK/plugin choices.
- **Synthesis.** This dossier merges those notes by coverage area, not by researcher:
  - Every finding keeps its original ID.
  - Duplicates are merged into one finding that lists every original ID, separated by " / ".
  - "(part)" marks an ID that contributed only part of its content to a merged finding.
  - Every topic-level conflict is kept. New cross-topic conflicts found while merging are numbered QX-C1 onward.
- **Gap-fill.** One web check was made during synthesis, to settle the Q2-021 vs Q3-005 contradiction: the Unity `XRDisplaySubsystem.scaleOfAllRenderTargets` and `scaleOfAllViewports` pages (QX-C1). No other new research was done during synthesis.
- **Gap-fill round 1 (coverage audit).** The synthesis stopped after section 4.5, so sections 5–12 and the Conflicts, Gaps and Source list sections were missing.
  - Sections 4.6–12 were filled by porting every remaining sourced finding from the four topic notes. Each finding keeps its original ID and text; section 1–4 findings are not repeated.
  - The topic conflicts, gaps and source lists were merged. The QX-C1 to QX-C9 conflicts that sections 1–4 cite were rebuilt from those references.
  - New web research added the findings numbered QUEST-GF1-001 onward and the conflicts QUEST-GF1-C1 onward.
  - At least 12 numeric or version-specific findings were re-fetched and spot-checked. The log is at the top of "Gaps and known unknowns".
- **Gap-fill round 2 (coverage audit).** This round targeted the items left open after round 1:
  - the FrameSync opt-out and what `Lat=` / `phase_sync_mode` report under FrameSync
  - the "hitches below 3%" definition
  - hand-tracking cost and compositor-layer cost on Quest 3/3S
  - the Shader Binary Cache replacement
  - a docs-page headroom figure

  Sources included the captions of Meta's GDC 2026 talk video, new Meta and Unity pages, and public third-party OVR Metrics CSVs. The new findings are numbered QUEST-GF2-001 onward and the new conflicts QUEST-GF2-C1 onward. Another 12+ findings were spot-checked (log in "Gaps and known unknowns"), and one note (Q2-072) was corrected in place.

**Evidence tags.**
- [doc]: official documentation. This covers Meta Horizon developer docs, essentials, resources, blog and release notes; the Unity manual, package docs, changelogs, issue tracker and Graphics source; Khronos; Meta-published SDK source and repos; Qualcomm; Arm; Android.
- [measured]: a source reporting its own measurements, with the test setup given.
- [community]: forums, third-party repos, papers, Wikipedia and press. These are leads, confirmed where possible.
- [verify on device]: the claim needs confirmation on hardware.

**Goal tags.**
- [T] Throughput: lower average CPU/GPU frame time.
- [C] Consistency: no stale or dropped frames, tight p95/p99, no hitches, no thermal decay over a 20–30 minute session.

**Applicability conventions.**
- **Devices:**
  - "Quest 2".
  - "Quest 3/3S": shared SoC, clock table and memory limit. Quest 3S differences are called out.
  - "Quest 3S" alone.
  - "Quest Pro": one line only.
- **Unity:** "2021.3", "2022.3", "Unity >= 6000.0" or "6.x". Exact patch floors are written as, for example, `6000.0.25f1+`.
- **URP:** "URP 12" (2021.3), "URP 14" (2022.3), "URP 17" (6.x). "URP 14+" means URP 14 and later.
- **Graphics API:** "Vulkan", "GLES".
- **Packages:**
  - "Core SDK vNN": `com.meta.xr.sdk.core`.
  - "OpenXR 1.xx": `com.unity.xr.openxr`.
  - "OpenXR: Meta 2.x": `com.unity.xr.meta-openxr`.
  - "Oculus XR 4.x": `com.unity.xr.oculus`, the legacy provider.
  - "MRUK": `com.meta.xr.mrutilitykit`.
- **Horizon OS versions:** "HzOS vNN". The OS moved to 2xx numbering in 2026 (v201, v203, v205, v207), and one page names a release "HorizonOS v2.7". The mapping between the two schemes is unverified.
- **Frame budgets:** 72 Hz = 13.9 ms, 80 Hz = 12.5 ms, 90 Hz = 11.1 ms, 96 Hz = 10.4 ms, 100 Hz = 10.0 ms, 120 Hz = 8.3 ms. The 80, 96 and 100 Hz values are arithmetic, not published (Q2-009). The app never gets the full budget (section 10).

**Finding ID prefixes.**
- Q1: tooling and triage.
- Q2: budgets, pacing, thermal.
- Q3: resolution, foveation, AppSW, layers.
- Q4: mixed reality and SDK.

Conflicts are numbered Q1-C*, Q2-C*, Q3-C* and Q4-C*, plus QX-C* for new cross-topic conflicts. Cross-references use these IDs.

---

## Baseline fact re-verification

| Fact | Status | Detail | Source |
|---|---|---|---|
| Quest 2 = Snapdragon XR2 (Gen 1), Adreno 650, 6 GB | confirmed | XR2 is SD865-derived, with Adreno 650 at 587 MHz and 6 GB LPDDR4X (Wikipedia). Meta's GPU level-5 clock for Quest 2 is 587 MHz, which matches. Meta's compare-devices page (Sep 18, 2026) no longer lists Quest 2, but Meta still documents its clock table, memory limit and `supportedDevices` ID. Quest 2 was discontinued Sep 25, 2024 (Q2-003). | https://en.wikipedia.org/wiki/Quest_2 ; https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ |
| Quest 3 = XR2 Gen 2, Adreno 740, 8 GB | confirmed | Meta lists XR2 Gen 2 and 8 GB. Wikipedia lists Adreno 740 and LPDDR5 at 4200 MT/s (68 GB/s). Peak GPU clock is disputed: Meta's level table maxes at 599 MHz (L5), Wikipedia says 640 MHz, and the ovrgpuprofiler page says 690 MHz (Q2-C5, QX-C6). | https://developers.meta.com/horizon/essentials/compare-devices/ ; https://en.wikipedia.org/w/index.php?title=Meta_Quest_3&action=raw ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ |
| Quest 3S = XR2 Gen 2 with a Quest 2-class display | confirmed, with one open item | Meta lists XR2 Gen 2, 8 GB, LCD 1832x1920 per eye, 20 PPD, 96°H FOV and no depth sensor. The CPU/GPU clock table and PSS limit are shared with Quest 3. Memory type and bandwidth are unverifiable: Wikipedia's LPDDR4X 2600 MT/s claim has no citation (Q2-005). The default eye buffer is the Quest 3 value, 1680x1760, not a Quest 2 value (Q2-088). | https://developers.meta.com/horizon/essentials/compare-devices/ ; https://developers.meta.com/horizon/documentation/native/android/os-render-scale/ |
| No eye tracking on Quest 2/3/3S; eye-tracked foveation is Quest Pro only | confirmed | The Oculus XR docs say ETFR is Quest Pro only (Vulkan, Multiview, ARM64). Meta VR Glasses also have eye tracking but are out of scope. | https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html ; https://developers.meta.com/horizon/documentation/unity/unity-eye-tracked-foveated-rendering/ |
| Frame budgets: 72 Hz = 13.9 ms, 90 Hz = 11.1 ms, 120 Hz = 8.3 ms | confirmed | Meta gives these exact figures and adds 207 Hz = 4.8 ms and 240 Hz = 4.2 ms (Quest 3 only). No published rows exist for 80, 96 or 100 Hz. | https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ ; https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ |
| The app never gets the full budget | confirmed qualitatively; no percentage published | Meta publishes no headroom percentage. Its guidance is to design to nominal CPU L4 / GPU L4 and to treat GPU L4 as the maximum budget. The compositor (TW = 1.25 ms in the logcat example), Guardian and system layers take GPU time, and compositor work can preempt the app (Q2-028, Q2-030, Q2-040). | https://developers.meta.com/horizon/documentation/unity/optimize-performance/ ; https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ ; https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ |
| Refresh rates per device | changed | 96 and 100 Hz were added for Quest 2/3/3S. Quest 3 alone accepts any integer rate from 72 to 207 Hz, and up to 240 Hz in developer mode (HorizonOS v2.7+). Quest Pro supports 72/80/90. The VRC page still says 96/100 are "not yet available" (Q2-C4), and the system-properties page lists the old set (QX-C5). | https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ |
| Default eye buffer: Quest 2 1440x1584, Quest 3/3S 1680x1760 | confirmed | Meta's render-scale table, the system-properties defaults and a Jan 2026 Quest 3 CSV agree. Meta's agentic-tools skill wrongly gives 1440x1584 for Quest 3 (Q1-C4). | https://developers.meta.com/horizon/documentation/native/android/os-render-scale/ ; https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ |
| App memory (PSS) limits | confirmed | Quest 2 = 4.4 GiB, Quest Pro = 4.4 GiB, Quest 3/3S = 5.75 GiB (page updated Aug 31, 2026). | https://developers.meta.com/horizon/essentials/memory-ram/ |
| Phase Sync is the frame-timing mechanism | changed | FrameSync replaced Phase Sync and is the default (the default for Store apps from v203; testable from v201). Phase Sync API calls are now no-ops (Q2-071, Q2-072; QX-C4, QX-C9). | https://developers.meta.com/horizon/essentials/framesync/ ; https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ |
| CPU/GPU levels are set via `OVRManager.cpuLevel` / `gpuLevel` | changed | Those properties are `[Obsolete]`. Use `suggestedCpuPerfLevel` / `suggestedGpuPerfLevel` with `ProcessorPerformanceLevel` (Q1-105 / Q2-044). | https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ |
| Graphics API: Vulkan is recommended; GLES is legacy | confirmed | These are Vulkan-only: Late Latching, Optimize Buffer Discards, Subsampled Layout, Symmetric Projection, AppSW, SRP foveation / dynamic foveation, Multiview Render Regions and the Depth API. Low Overhead Mode is GLES-only. No current doc covers GLES FFR for URP (Q3-039). | https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html ; https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ |
| GPU is Qualcomm Adreno (not Mali) | confirmed | Adreno 650 (Quest 2) and Adreno 740 ("Adreno 740v3" on the ovrgpuprofiler page) on Quest 3/3S. FFR uses Adreno fragment density maps and `VK_QCOM_*` extensions. | https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ ; https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ |
| Unity path: legacy Oculus XR Plugin vs OpenXR | changed | Oculus XR (`com.unity.xr.oculus`) is deprecated from Unity 6.5: supported through 6.4, with LTS support via 6.3 LTS, and latest version 4.5.5 (2026-07-19). The recommended path is Unity OpenXR + OpenXR: Meta, which reached parity at OpenXR 1.14 (Q4-051). | https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html ; https://discussions.unity.com/t/oculusxr-package-deprecation/1717655 |
| Current package versions (Sep 2026) | new fact | Meta XR Core SDK 207.0.0; the numbering jumped from 85.0.0 to 201.0.0 in Apr 2026. Unity OpenXR 1.18.0 (2026-08-04) and 1.19.0-pre.1 (2026-08-12); OpenXR: Meta 2.6.1; MRUK 207.0.0. Core SDK 203+ and MRUK 207 need Unity 6000.0.66f2+. 2021.3 projects stop at Core SDK v72 and 2022.3 projects at v201 (Q4-049, Q4-050, Q4-052, Q4-037). | https://npm.developer.oculus.com/com.meta.xr.sdk.core ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html |
| Unity 6.7 LTS has shipped | not shipped | The Unity issue tracker banner advertises the "Unity 6.7 beta". Meta's fix lists cite only 6000.7.0a3, and 6000.7 Scripting API docs exist. Excluded (QX-C3). Gap-fill round 1: Unity's support page still names 6.3 as the latest LTS, and the 6.7 alpha was reported on Jun 25, 2026 (QUEST-GF1-002). | https://issuetracker.unity.com/issues/11487/oculusxr-phasesync-toggle-is-not-respected-and-its-always-enabled ; https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ |
| Unity 6.0 LTS ends Oct 2026; 6.3 LTS supported to Dec 2027 | confirmed (gap-fill round 1) | Unity's support page: 6.0 LTS through October 2026, and 6.3 LTS (the latest LTS) until December 2027, each with one extra year for Enterprise/Industry (QUEST-GF1-001). | https://unity.com/releases/unity-6/support |
| Store minimum frame rate (VRC.Quest.Performance.1) | changed | The floor is 60 fps (lowered from 72 on 2024-08-07), or half refresh with AppSW. Other Meta pages still say 72 (Q1-C1 / Q2-C3). | https://developers.meta.com/horizon/resources/vrc-quest-performance-1/ |
| Store thermal test (VRC.Quest.Performance.2) | changed | Retired 2024-10-16 (Q1-085; see QX-C7). | https://developers.meta.com/horizon/resources/vrc-quest-performance-2/ |
| OVR Metrics Tool version | new fact (gap-fill round 1) | The SDK package is 2.0.1 (Dec 12, 2025). The on-device app version is not published; read it with `dumpsys` (QUEST-GF1-006, Q1-001). | https://developers.meta.com/horizon/downloads/package/ovr-metrics-tool-sdk/ |
| Old developer.oculus.com URLs | n/a | Every URL cited here is the current developers.meta.com/horizon form. | — |

---

## 1. Triage entry: CPU-bound vs GPU-bound vs pacing/compositor-bound

Order of tools:
1. OVR Metrics Tool CSV or HUD and the VrApi logcat line: cheap, 1 Hz, engine-agnostic (section 9).
2. Perfetto for frame-level pacing and thread attribution.
3. ovrgpuprofiler and RenderDoc Meta Fork for GPU internals.

Profile with dynamic resolution, dynamic foveation and casting off, and levels either locked or recorded (Q2-039, Q3-051 / Q2-025 (part) / Q4-060 (part), Q1-041).

**Triage map.** This is a synthesis index: every row points to sourced findings.

| Signal | Points to | Findings |
|---|---|---|
| App GPU time (`App=` / `app_gpu_time_microseconds`) above the frame budget | GPU-bound | Q1-089 / Q2-031 |
| App GPU time within budget, but FPS below target or `Stale` > 0 | CPU-bound (main or render thread) | Q1-089 / Q2-031 |
| `CPU&GPU − App` close to the budget | Unity render thread | Q1-032 |
| CPU L high and GPU L low (for example 4/2) while missing frames | CPU-bound | Q1-025 / Q2-032 |
| `GPU%` ≥ 0.9 | GPU saturated; scheduling risk | Q1-025 / Q2-032, Q2-030 |
| `GPU%` at half rate | under-reports load; use App ms | Q1-089 / Q2-031 |
| `Stale` between 0 and refresh; `Stale2/5/10` non-zero; `stale_frames_consecutive` > 0 | pacing hitch (visible judder) | Q1-024 / Q2-066, Q1-029, Q1-014 |
| `Stale` = refresh with steady FPS | extra-latency mode, not a failure | Q1-024 / Q2-066 |
| `Early` ≈ FPS | extra-latency mode, or levels higher than needed | Q1-026 / Q2-067 / Q2-070, Q2-054 |
| `Tear` > 0, `TW` rising, high `LCnt` | compositor-bound (layers) | Q1-026 / Q2-067 / Q2-070, Q3-079, Q3-083 |
| Perfetto `FenceChecker::Wait` or waits on the `GPU completion` thread | GPU-bound | Q1-052 |
| `UnityMain`/`UnityGfx` slices over budget with no fence waits | CPU-bound | Q1-052 |
| `PhaseSync` idle near 0 ms at the start of `PlayerLoop` | no headroom (pre-FrameSync semantics) | Q1-051, QX-C4 |
| Clock drop, or `PLS`/`power_level_state` at 1–2, lining up with a stale burst | thermal | Q1-035 / Q1-036 / Q2-056, Q1-016 / Q2-061 |
| `shader_hitches` increments; hitches on first run only | shader/PSO compilation | Q1-011, Q1-014 |
| Render scale at 0.01 changes nothing | vertex/geometry/submission-bound | Q1-091 |
| FFR sweep 0→4 gives a large drop in app GPU time | fragment-bound | Q1-081 / Q3-028 |
| GPU-bound only in MR | lower clock ceiling, not slower shaders | Q4-010, Q2-038 / Q4-001 |
| Memory trend rising, then Low Memory Kill | PSS over limit under pressure | Q2-041, Q2-042, Q1-095 |

### 1.1 First split from OVR Metrics and logcat

- **Q1-089 / Q2-031** The first CPU-or-GPU split compares app GPU time with the frame budget: 13888 µs at 72 Hz, 11111 µs at 90 Hz, 8333 µs at 120 Hz. It does not use GPU utilisation. [T]
  - App GPU time over budget with FPS below target: GPU-bound (the CPU may also be over budget, hidden behind the GPU).
  - App GPU time within budget, but FPS below target or `Stale` > 0: CPU-bound.
  - At half rate, `GPU%` under-reports load. Meta's example is `FPS=36/72, Stale=36, GPU%=0.65, App=18.05ms`: 18 ms of GPU work in a 27.8 ms interval. It needs a 23% GPU cut, not the 35% headroom that `GPU%` suggests, and getting back to full rate needs `GPU%` below about 50%.
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ (Q1-089, undated; the budget rule and dip tolerance, while the half-rate example below is on os-missed-frames); https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ (Q2-031, updated Mar 9, 2026) (accessed 2026-09-24) · Applies to: Quest 2/3/3S; any engine · Evidence: [doc]
  - Notes: A CPU-bound verdict can mean the Unity render thread rather than game logic. Split the two with logcat `CPU&GPU − App` (Q1-032) or Perfetto `UnityGfx` vs `UnityMain` (Q1-052).

- **Q1-025 / Q2-032** How to read utilisation and levels. [T]
  - OVR Metrics App T is app GPU time in µs. Above budget (13.88 ms at 72 fps) means GPU-bound; below it means probably CPU-bound.
  - GPU U at 100% means GPU-bound; above 90% risks scheduling problems.
  - CPU U reports the busiest core.
  - The Stats guide's example of CPU L 4 with GPU L 2 indicates a CPU-bound app.
  - In logcat, `CPU4/GPU=2/2` gives the CPU and GPU levels. The digit after "CPU" is the core being measured, not a level. `1171/441MHz` gives the clocks.
  - At 4/4, judge with stale counts, `App` time and utilisation instead.
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (Q1-025, undated, partly pre-2023); https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (Q2-032, updated Jul 31, 2025) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Levels show what the runtime's dynamic clocking requested. Read them next to the `*_frequency_MHz` columns, because the same level means different clocks on different devices (Q2-046 / Q2-047 / Q4-003).

- **Q1-090** At 72 Hz, a one-off dip lasting a couple of seconds is acceptable if it stays above 65 fps and recovers quickly. Dips must not repeat in a cycle. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S at 72 Hz · Evidence: [doc]
  - Notes: This is the only published dip tolerance found. For 90 and 120 Hz no published number was found; scaling by the same ratio is a guess and must be labelled as one.

- **Q1-091** Meta's basic optimisation workflow (Dec 2024). [T]
  1. Turn off the render camera. Little change means CPU-bound; a big improvement means GPU-bound.
  2. If GPU-bound, set render scale (`eyeTextureResolutionScale`) to 0.01. No change means vertex or geometry bound; an improvement means fill-bound. Culling and draw submission count as vertex-bound in this test.
  3. Any app logic over 2 ms can probably be optimised.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S, Unity · Evidence: [doc]
  - Notes: The same page says all Quest apps need at least 72 FPS, which conflicts with the current VRC (Q1-C1 / Q2-C3). In URP, `eyeTextureResolutionScale` may be overridden by the URP asset's render scale (Q2-022 / Q3-006, Q3-C5). Confirm the test took effect with `SF=` in logcat.

- **Q1-094** A consistency [C] triage sequence built from documented signals. [C]
  1. Record a CSV with the Basic preset, no HUD and no casting, for 20–30 minutes along a scripted route. Mark segments with `AppendCsvDebugString`.
  2. For each segment, compute the stale count, `stale_frames_consecutive`, `max_repeated_frames`, `shader_hitches`, and p95/p99 of `app_gpu_time_microseconds`.
  3. Correlate stale bursts with clock changes (`debug.oculus.clockStateLogLevel 1`), `power_level_state`, and GC or loading markers in Perfetto.
  4. Label each burst as content-bound (GPU or CPU over budget), pacing (PhaseSync at about 0 ms, CFL/ICFL spikes), shader/PSO (first use) or thermal (a clock or POW L drop).
  - Source: synthesis of https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ , https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ and https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] for the individual signals; the sequence is the researcher's synthesis
  - Notes: This ordering is not a Meta-published procedure; present it as a recommended method. On FrameSync OS builds (v203+), PhaseSync-based labels need re-checking (QX-C4).

### 1.2 Reading a Perfetto trace

- **Q1-050** Names to look for in a Unity trace on Quest. [T][C]
  - Markers: `PlayerLoop`, `PhaseSync`, `Gfx.WaitForPresent`, `PostLateUpdate.FinishRendering`, `RenderPipelineManager.DoRenderLoop`, `BatchRenderer.Flush`.
  - Threads: `UnityMain`, `UnityGfx`, `UnityChoreWorker`, `Job.Worker`, `GPU completion`, `OVRPollEvent`.
  - OpenXR frame calls: `xrWaitFrame`, `xrBeginFrame`, `xrEndFrame`. Legacy VrApi: `vrapi_WaitFrame`, `vrapi_BeginFrame`, `vrapi_SubmitFrame`.
  - Source: https://github.com/meta-quest/agentic-tools (skills/hz-perfetto-debug/SKILL.md, references/frame-timing.md) (accessed 2026-09-24) · Applies to: Unity on Quest 2/3/3S · Evidence: [doc] (Meta-published agent skill)
  - Notes: Exact marker names differ between Unity and URP versions. Check them against your own trace before hard-coding SQL.

- **Q1-051** Reading pacing: `PhaseSync` appears as 1–4 ms of idle time at the start of `PlayerLoop`, which is normal. When it shrinks to near zero, the app is using almost its whole budget. Do not report PhaseSync or `xrWaitFrame` waits as wasted time; the runtime controls them. [C]
  - Source: https://github.com/meta-quest/agentic-tools (skills/hz-perfetto-debug/references/frame-timing.md) (accessed 2026-09-24) · Applies to: Unity OpenXR on Quest 2/3/3S · Evidence: [doc] (Meta-published agent skill)
  - Notes: Track PhaseSync duration as a headroom gauge; a steady run with PhaseSync near 0 ms is one hitch away from a stale frame. FrameSync replaced PhaseSync from v203 (Q2-071). Whether the `PhaseSync` marker and its meaning survive on FrameSync builds is unverified (QX-C4). [verify on device]

- **Q1-052** Reading GPU-bound vs CPU-bound. [T]
  - GPU-bound: the CPU waits on the GPU in `FenceChecker::Wait`, or the `GPU completion` thread is waiting. GPU work appears as `surface#N` slices on tracks whose names start with `GPU`.
  - CPU-bound: `UnityMain` or `UnityGfx` slices run past the budget with no fence waits.
  - Source: https://github.com/meta-quest/agentic-tools (skills/hz-perfetto-debug/references/gpu-analysis.md) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] (Meta-published agent skill)
  - Notes: The skill maps surface#0 to the eye buffer and surface#2+ to shadows and post-processing. That mapping is a heuristic. Identify surfaces by resolution and MSAA (compare with ovrgpuprofiler `-t` output, Q1-069) before attributing cost.

- **Q1-053** Thresholds in Meta's hz-perfetto-debug skill (good / warning / critical). [T][C]

  | Metric | Good | Warning | Critical |
  |---|---|---|---|
  | Stale frame rate | < 5% | > 10% | > 25% |
  | Frame time std dev | < 1 ms | > 2 ms | > 4 ms |
  | Main thread, share of budget | < 80% | > 80% | > 95% |
  | GPU, share of budget | < 85% | > 85% | > 95% |
  | Draw calls per frame | < 100 | > 200 | > 500 |

  - Source: https://github.com/meta-quest/agentic-tools (skills/hz-perfetto-debug/SKILL.md) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] (Meta-published agent skill; not in the official performance docs)
  - Notes: These are heuristics for an agent, not VRC limits. The draw-call row conflicts with the Runtime Optimizer and with Meta's per-device draw-call ranges (Q1-C3). The same skill states Quest 3 eye resolution wrongly (Q1-C4).

- **Q1-054** The skill's stale-frame SQL counts every `PlayerLoop` slice longer than 11.1 ms as stale. That hard-codes 90 Hz and confuses CPU frame duration with compositor staleness. Under Phase Sync, FrameSync or extra latency, measure staleness with VrApi `Stale`, the CSV `stale_frame_count`, or the XR runtime tracks. [C]
  - Source: https://github.com/meta-quest/agentic-tools (skills/hz-perfetto-debug/references/frame-timing.md) vs https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] (both; see Q1-C7)
  - Notes: When reusing that SQL, replace the constant with the budget for the refresh rate in use (13.9, 11.1 or 8.3 ms).

- **Q1-055** Perfetto trace-processor tables for SQL: `slice`, `thread_track`, `thread`, `process`, `counter`, `counter_track`, `args`, `sched_slice`. For example, per-frame main-thread cost is the `slice` rows named `PlayerLoop` joined to `thread_track` for `UnityMain`; take the percentiles of their `dur`. [T][C]
  - Source: https://github.com/meta-quest/agentic-tools (skills/hz-perfetto-debug/SKILL.md, references/sql-queries.md) (accessed 2026-09-24) · Applies to: any Perfetto trace · Evidence: [doc] (Meta-published agent skill)
  - Notes: For [C], compute p95/p99 and the maximum of `dur` over at least 20 s of steady play. For [T], compute the mean.

### 1.3 Quest Runtime Optimizer (automated classification)

- **Q1-092** Quest Runtime Optimizer (experimental; updated Jul 31, 2026). [T]
  - Needs Horizon OS v78+ and Unity 2022.3+, and is distributed on the Asset Store. Open it from Window > Meta > Tools > Quest Runtime Optimizer.
  - It adds the `ENABLE_RUNTIME_OPTIMIZER` define and forces a Development Build, so turn it off for release-candidate builds.
  - Quick Perf targets 14.2 ms (about 70 FPS). It colour-codes green below 80%, yellow 80–95% and red above 95%, and classifies the app as CPU-bound, GPU-bound or both.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-quest-runtime-optimizer/ (accessed 2026-09-24) · Applies to: Unity 2022.3+ (not 2021.3), HzOS v78+, Quest 2/3/3S · Evidence: [doc]
  - Notes: The 14.2 ms target is looser than the 13.9 ms budget at 72 Hz (Q1-C6). Known issues: rare kernel panics on OS v78, and dynamic objects are not supported. Core SDK v203 separately lists an "AI Runtime Optimizer Tool" (Q4-066); whether the two are the same product is undocumented.

- **Q1-093** More Runtime Optimizer modes. [T]
  - **Bottleneck Analysis** (about 25 s) sorts GPU cost into Texture, Fragment, Setup (draw calls under 300), Vertex and Vertex Fetch.
  - **What If? Analysis** costs about 200 ms per GameObject, up to 200 objects. It can report a negative GPU time for an object that was hiding more expensive geometry.
  - Captures export as `.roz`, a ZIP of the Perfetto trace, screenshots and JSON. The Adreno Offline Compiler is optional.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-quest-runtime-optimizer/ (accessed 2026-09-24) · Applies to: Unity 2022.3+, HzOS v78+ · Evidence: [doc]
  - Notes: The `.roz` Perfetto trace can go through the same SQL pipeline as MQDH traces (Q1-055).

---

## 2. Per-device budgets and quality tiers

### 2.1 Hardware baselines

- **Q2-001** Quest 3 and Quest 3S use the same chipset (Snapdragon XR2 Gen 2) and the same 8 GB of memory, and both run Android 14 builds of Horizon OS. [T]
  - Source: https://developers.meta.com/horizon/essentials/compare-devices/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [doc]
  - Notes: The page was updated Sep 18, 2026, and Quest 2 is no longer listed on it. Every compute budget in this dossier is therefore shared by Quest 3 and 3S; the differences are optical, display and sensor.

- **Q2-002** Display differences. [T][C]
  - Quest 3: 2064x2208 per eye, 25 PPD, 110°H x 96°V FOV, pancake lenses, continuous IPD.
  - Quest 3S: 1832x1920 per eye, 20 PPD, 96°H x 90°V, Fresnel lenses, three IPD presets.
  - Both list a 120 Hz maximum on the compare page.
  - Source: https://developers.meta.com/horizon/essentials/compare-devices/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [doc]
  - Notes: The Fresnel lens detail is from Wikipedia ([community]). Passthrough is 4 MP (18 PPD) on both, but only Quest 3 has the depth sensor.

- **Q2-003** Quest 2 hardware: XR2 (Gen 1, SD865-derived), Adreno 650, 6 GB LPDDR4X, one fast-switch LCD at 1832x1920 per eye, IPD presets 58/63/68 mm. It was discontinued Sep 25, 2024, but Meta still documents its clock tables, memory limits and a `supportedDevices` ID. [T]
  - Source: https://en.wikipedia.org/wiki/Quest_2 (accessed 2026-09-24) · Applies to: Quest 2 · Evidence: [community]
  - Notes: The 587 MHz GPU maximum matches Meta's GPU level-5 clock (https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/, [doc]). The panel resolution matches Meta's render-scale table.

- **Q2-004** Quest 3 memory is listed as LPDDR5 at 4200 MT/s (68 GB/s). The CPU is 2x Cortex-A715 plus 4x Cortex-A510 (Kryo). [T]
  - Source: https://en.wikipedia.org/w/index.php?title=Meta_Quest_3&action=raw (accessed 2026-09-24) · Applies to: Quest 3 · Evidence: [community] [verify on device]
  - Notes: The runtime memory clock appears in the `Mem=` field of the VrApi logcat line (Q1-031); use it to confirm the memory clock on your unit.

- **Q2-005** Wikipedia lists Quest 3S memory as LPDDR4X at 2600 MT/s (42 GB/s), which would be about 38% less bandwidth than Quest 3. The spec field has no specific citation, and Meta publishes no memory type for either device. [T]
  - Source: https://en.wikipedia.org/w/index.php?title=Meta_Quest_3S&action=raw (accessed 2026-09-24) · Applies to: Quest 3S · Evidence: [community] [verify on device]
  - Notes: If true, bandwidth-heavy work (wide formats, MSAA resolves, full-screen post-processing, passthrough composition) would scale worse on 3S than CPU/GPU clocks suggest. To check, compare `Mem=` in `adb logcat -s VrApi` on both headsets, and A/B a bandwidth-bound test scene at fixed CPU/GPU levels.

- **Q2-006 / Q4-002** Meta's Quest 3 launch guidance. [T]
  - Quest 3 has about 2x Quest 2's GPU performance, about 33% more CPU performance and more than 30% more memory.
  - Passthrough (MR) apps get about 17% less GPU and 14% less CPU than VR-only apps. Depth API use adds more GPU cost on top, with no number given.
  - An MR app's remaining budget on Quest 3 still exceeds Quest 2's entire budget.
  - App SpaceWarp gives up to 70% extra compute.
  - Source: https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ (blog dated Oct 11, 2023) (accessed 2026-09-24) · Applies to: Quest 3 vs Quest 2 (3S shares the SoC; the blog does not mention it) · Evidence: [doc] [verify on device]
  - Notes: The blog predates later OS clock changes, and its percentages are Meta's figures for Meta's test content. The 17%/14% match the current clock table: GPU L4→L2 is 545→456 MHz (−16.3%) and CPU L4→L3 is 1.92→1.65 GHz (−14.1%). That is arithmetic on documented clocks, not measured frame time (Q2-038 / Q4-001).

- **Q2-007 / Q3-040 / Q4-008** Quest Pro and eye-tracked foveation, one line. [T]
  - Quest Pro has the same CPU/GPU clock tables and 4.4 GiB PSS limit as Quest 2.
  - It is the only Quest with eye-tracked foveated rendering. Enable ETFR with `OVRManager.eyeTrackedFoveatedRenderingEnabled`, or on the SRP path with `FoveatedRenderingFlags.GazeAllowed` plus the `oculus.software.eye_tracking` feature and the `com.oculus.permission.EYE_TRACKING` permission. It needs Vulkan, Multiview and ARM64.
  - Enabling passthrough, eye/face/body tracking or gaze foveation removes CPU L4 and GPU L4.
  - ETFR does nothing on Quest 2, 3 or 3S.
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ (Q2-007); https://developers.meta.com/horizon/documentation/unity/unity-eye-tracked-foveated-rendering/ and https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/foveatedrendering.html (Q3-040); https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (Q4-008); https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html (Q2-007 note) (accessed 2026-09-24) · Applies to: Quest Pro only (out of device scope; shown for contrast) · Evidence: [doc]

- **Q2-008** Context only: Meta VR Glasses (XR2 Gen 3, 12 GB, micro-OLED 2412x2288) now appear on Meta's device pages. They run Quest 3 apps in compatibility mode and have their own clock table (CPU L4 2.09 GHz, GPU L4 633 MHz). [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/optimize-performance/ (accessed 2026-09-24) · Applies to: Meta VR Glasses (out of scope) · Evidence: [doc]
  - Notes: This matters for Quest work only because shared Meta pages now carry glasses-specific rules (a boost token bucket, no trading, no dual-core, larger GMEM so smaller FFR savings). Do not apply those rules to Quest.

### 2.2 Frame budgets

- **Q2-009** Frame budgets: 72 Hz = 13.9 ms, 90 Hz = 11.1 ms, 120 Hz = 8.3 ms, 207 Hz = 4.8 ms, 240 Hz = 4.2 ms. The combined CPU and GPU pipeline must deliver a frame within this interval, or the compositor re-shows the previous one (a stale frame). [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: The 207 and 240 Hz rows are from https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/. Meta publishes no budget rows for 80, 96 or 100 Hz; the arithmetic (1000/Hz) gives 12.5, 10.4 and 10.0 ms. At half rate with AppSW the per-rendered-frame budget is 27.8 ms (72 Hz), 22.2 ms (90 Hz) or 16.7 ms (120 Hz) (Q2-079 / Q3-062). Net app headroom is covered in section 10.

- **Q2-019** The Quest 3 eye buffer (1680x1760, 2.96 MP per eye) is about 30% larger than Quest 2's (1440x1584, 2.28 MP per eye). Meta describes the Quest 3 default as nearly 30% over Quest 2. [T]
  - Source: https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ (accessed 2026-09-24) · Applies to: Quest 3/3S vs Quest 2 · Evidence: [doc]
  - Notes: The pixel counts are arithmetic from Q2-017 / Q3-001. Part of the 2x GPU uplift (Q2-006 / Q4-002) is used up by the larger default buffer before any content change.

### 2.3 Draw calls, triangles, fill rate, texture memory

- **Q2-033** Meta's example draw-call ranges per frame (guidance, not a hard limit). [T]

  | Device | Busy simulation | Medium simulation | Light simulation |
  |---|---|---|---|
  | Quest 2 / Pro | 80–200 | 200–300 | 400–600 |
  | Quest 3 / 3S | 200–300 | 400–600 | 700–1000 |

  - Source: https://developers.meta.com/horizon/documentation/unity/unity-perf/ (page dated Oct 30, 2024) (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: Meta's definitions:
    - Busy: multiplayer or social apps with VoIP and many skinned characters.
    - Medium: most apps.
    - Light: puzzle or escape-room games with minimal state changes.

    The main drivers are pipeline state changes, main- and render-thread load (animation, skinning and networking delay the render thread) and API choice (Vulkan vs GLES, bindless, indirect draws). This table conflicts with the < 100 and < 300 agent and optimizer heuristics (Q1-C3).

- **Q2-034** Internally recommended triangle ranges per frame: Quest 2/Pro 750k to 1M; Quest 3/3S 1.3M to 1.8M. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-perf/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: On tiled GPUs, cost depends on tile coverage: the vertex shader runs per vertex for each tile a triangle covers, so large triangles cost more. Meta recommends:
    - Putting position and skinning data in their own vertex stream.
    - Removing unused vertex channels.
    - Using half precision for non-position attributes.

- **Q2-035** Several older Meta Unity pages are stale and should not be cited as budgets. [C]
  - unity-mobile-performance-intro: a 50,000 static triangles per eye figure, `OVRManager.cpuLevel`, and a claim that texture memory is nearly free.
  - po-draw-call-analysis: Quest 1 / Unity 2018 cost multipliers.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ ; https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (accessed 2026-09-24) · Applies to: n/a (stale; pre-2023) · Evidence: [doc]
  - Notes: The analysis page measured a material switch at about +64%, a shader switch at about +175% and a redraw at about 25%. Those are Quest 1 numbers; use them only for relative ordering.

- **Q2-036** No published fill-rate or pixel-throughput number exists for any Quest: no pixels-per-second and no bytes-per-frame budget. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/optimize-performance/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc] [verify on device]
  - Notes: To measure, capture a render-stage trace in RenderDoc Meta Fork. The Tile Timeline gives per-surface duration, render mode and bin count; compare tiled-forward surfaces against full-screen passes. At 100% scale the shaded pixel rate is 1680x1760x2 x Hz on Quest 3/3S (about 532 Mpx/s at 90 Hz, arithmetic) and 1440x1584x2 x Hz on Quest 2, before MSAA and overdraw. `avg_fill_percentage` (Q1-007) estimates overdraw.

- **Q2-037** No per-device texture memory budget is published beyond the app PSS limit (Q2-041). [T]
  - Source: https://developers.meta.com/horizon/essentials/memory-ram/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: No published number found. Measure PSS in MQDH or OVR Metrics (VSS/RSS/Dalvik PSS stats, `app_gpu_*_MB`) at peak scene load. Eye buffers (Q2-024 / Q2-090, Q2-027 (part) / Q4-059) and render textures count against the same PSS.

- **QUEST-GF2-005** Meta's GDC 2026 performance talk gave quick rules:
  - Keep draw calls under about 500 per frame, which the speaker called "not at all a hard and fast rule". Apps can go well above 1,000 with good cache locality and shader choices.
  - Keep a baseline render scale of about 85% or more, and let dynamic resolution scale up from that floor when there is headroom. [T][C]
  - Source: https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ (Meta talk video (GDC 2026, Mar 10, 2026, David Borel and Neel Bedekar), read from its auto-generated captions; about 3:50–5:20) (accessed 2026-09-24) · Applies to: Quest 3/3S (talk title); the draw-call rule is stated generally · Evidence: [doc] (Meta talk)
  - Notes: The 500 figure is a fourth draw-call number, alongside Meta's per-device ranges (Q2-033), the Runtime Optimizer's under-300 and the agent skill's under-100 (Q1-C3). See QUEST-GF2-C5. "85% render scale" is read here as a dynamic-resolution minimum (0.85). The OVRManager default minimum is 0.7 (Q2-024 / Q2-090), so a Quest 3/3S title following the talk would raise `minDynamicResolutionScale` to about 0.85. [verify on device]

### 2.4 Memory limits

- **Q2-041** App memory limits are checked against PSS (Proportional Set Size): Quest 2 = 4.4 GiB, Quest Pro = 4.4 GiB, Quest 3 and Quest 3S = 5.75 GiB (Meta VR Glasses also 5.75). [T][C]
  - Source: https://developers.meta.com/horizon/essentials/memory-ram/ (updated Aug 31, 2026) (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: The Unity page (https://developers.meta.com/horizon/documentation/unity/po-memory-ram/, Aug 12, 2025) has the same table. Quest 3/3S get about 1.35 GiB more than Quest 2 (arithmetic). A shared Quest 2/3 build must fit in 4.4 GiB unless assets are tiered.

- **Q2-042** Going over the limit may not crash immediately, because lmkd kills only under memory pressure. Store crash analytics then show "Low Memory Kill" crashes from users with background activity. Search logcat for `lowmemorykiller`. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-memory-ram/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Test peak PSS with background apps and updates running, not on a clean boot.

- **Q2-043** `Free=` in the VrApi logcat line is Android's available memory and only a general guide. It is useful for spotting leaks or unreleased memory, not for judging headroom, because foregrounded apps and the OS can reclaim or consume memory abruptly. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Use PSS for limit checks: MQDH, `dumpsys meminfo`, OVR Metrics `app_pss_MB`, and `gpumeminfo` for GPU memory (Q1-095).

### 2.5 Runtime device detection and tiering

- **Q2-080** `OVRPlugin.GetSystemHeadsetType()` returns the `SystemHeadset` enum: Oculus_Quest = 8, Oculus_Quest_2 = 9, Meta_Quest_Pro = 10, Meta_Quest_3 = 11, Meta_Quest_3S = 12, Meta_VR_Glasses = 13, then placeholders 14–20. Link variants start at 0x1000. [C]
  - Source: https://raw.githubusercontent.com/darktable-mirror/com.meta.xr.sdk.core/main/Scripts/OVRPlugin.cs (accessed 2026-09-24) · Applies to: Core SDK 207 (GitHub mirror of the Meta package) · Evidence: [doc] (SDK source)
  - Notes: Map unknown future values to your highest tier with a capability check, rather than falling back to the lowest.

- **Q2-081** Compatibility mode. [C]
  - If the manifest's `com.oculus.supportedDevices` does not list the physical headset, selected APIs (including `GetSystemHeadsetType()`) report the most recent older listed model.
  - If the entry is missing entirely, they report the original Quest.
  - CPU/GPU speed and passthrough quality are unchanged.
  - Source: https://developers.meta.com/horizon/documentation/unity/os-compatibility-mode/ (updated Sep 4, 2026) (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: A missing `quest3s` entry makes a 3S report as an older model, and limits refresh rates to those both models support (Q2-015). Tiering keyed only on the model then misfires.

- **Q2-082** No public API reports whether compatibility mode is active. Meta says not to use `android.os.Build.MODEL`, or any single device value, to decide feature availability; check the capability itself and provide fallbacks. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-compatibility-mode/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: For performance tiering, combine the headset enum (with a correct `supportedDevices` list), the supported refresh-rate list and the frame time measured in the first seconds. Re-tier on `DisplayRefreshRateChanged`.

- **Q2-083** The canonical `supportedDevices` string for all current Quests is `quest2|questpro|quest3|quest3s`. Unity and Unreal generate the entry from project settings, and older engine or SDK versions may omit newer headsets, so inspect the generated manifest. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-compatibility-mode/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: The OpenXR Quest "Target Devices" setting drives this list (https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/). Meta VR Glasses cannot be listed; use Store "Future devices" targeting. The refresh-rate page still says Unity auto-adds `quest|quest2` (Q2-C12).

- **Q2-084 / Q4-020** Compatibility mode and the OpenXR "Target Devices" setting do not throttle performance or change performance settings. Newer devices run at full clocks even when reporting an older model, and Target Devices does not gate colour passthrough. Target Devices lists Quest 2, 3, 3S (the 3S target was added in Unity OpenXR 1.13.0) and Pro. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (accessed 2026-09-24) · Applies to: Quest 3/3S running a Quest 2-targeted build; Unity OpenXR Meta Quest Support · Evidence: [doc]
  - Notes: A Quest 2-tier build on Quest 3 leaves GPU headroom unused unless dynamic resolution or adaptive quality spends it.

- **Q2-085** A suggested tier structure built from Meta's own groupings. [T][C]
  - **Tier A:** Quest 3 (pure VR).
  - **Tier A-display:** Quest 3S. Same compute and same default eye buffer; differs in panel, FOV, lenses and possibly bandwidth.
  - **Tier B:** Quest 2 and Quest Pro (Pro loses levels with passthrough or tracking).
  - **MR modifier:** Quest 3/3S with passthrough on, capped at CPU L3 / GPU L2.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-perf/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc] (for the groupings)
  - Notes: The groupings come from Meta's draw-call and triangle tables (3/3S grouped, 2/Pro grouped) and the CPU/GPU level availability rules. The tier structure itself is the researcher's synthesis, not a Meta recommendation.

- **Q2-086** Meta's adaptive-quality recommendation: scale LOD bias, view distance, MSAA sample count, shadows and post-processing quality from the measured CPU/GPU level, and use dynamic resolution to turn spare GPU time into pixels. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/optimize-performance/ (accessed 2026-09-24) · Applies to: written for Meta VR Glasses; the pattern applies to Quest · Evidence: [doc]
  - Notes: There is no documented in-app API on Quest for reading the level at runtime (Q1-035 / Q1-036 / Q2-056 gap). Frame-time-based scaling is the practical proxy, using app and compositor timings from `OVRPlugin.GetPerfMetricsFloat` (Q1-101). Per the `XR_META_performance_metrics` spec, counters should not drive app behaviour (Q1-103). [verify on device]

### 2.6 Quest 3S specifics

- **Q2-087** Quest 3S has the same CPU/GPU clock table, level availability rules, trading support, Boost behaviour and 5.75 GiB PSS limit as Quest 3. CPU/GPU budgets and the draw-call and triangle ranges are shared. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 3S · Evidence: [doc]
  - Notes: The one compute-relevant unknown is memory bandwidth (Q2-005). The ovrgpuprofiler page gives a different GPU clock for 3S (492 MHz) than for Quest 3 (690 MHz) (QX-C6).

- **Q2-088** Quest 3S renders the Quest 3 default eye buffer (1680x1760) even though its panel is 1832x1920. At render scale 1.0 its GPU pixel cost matches Quest 3, and it gets no automatic GPU relief from the lower-resolution panel. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-render-scale/ (accessed 2026-09-24) · Applies to: Quest 3S · Evidence: [doc]
  - Notes: Because 1.0 is already below 3S panel resolution (1.09 would match), lowering the scale on 3S costs visible clarity. Raising it to about 1.09 gives a panel-matched image for about 19% more pixels (arithmetic, 1.09²).

- **Q2-089** Quest 3S supports 72–120 Hz (including 96 and 100) but not the Quest 3 extended rates; its panel does not accept rates above 120 Hz. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ (accessed 2026-09-24) · Applies to: Quest 3S · Evidence: [doc]
  - Notes: Gate any mode above 120 Hz on the device's reported rate list, not on the Quest 3 family.

- **Q2-091** Quest 3S has a smaller FOV (96°H vs 110°H) and lower angular resolution (20 vs 25 PPD) behind Fresnel lenses. The same eye buffer covers a narrower field, so peripheral foveation savings and edge-clarity trade-offs differ from Quest 3. [C]
  - Source: https://developers.meta.com/horizon/essentials/compare-devices/ (accessed 2026-09-24) · Applies to: Quest 3S · Evidence: [doc] [verify on device]
  - Notes: Meta publishes no number for FFR savings on 3S vs Quest 3. Measure `App` at each FFR level on both devices.

- **Q2-092** Quest 3S passthrough is 4 MP / 18 PPD like Quest 3, but 3S has no depth sensor. The CPU/GPU restrictions with passthrough on are the same as on Quest 3 (Q2-038 / Q4-001). [T]
  - Source: https://developers.meta.com/horizon/essentials/compare-devices/ (accessed 2026-09-24) · Applies to: Quest 3S · Evidence: [doc]
  - Notes: The Oculus XR docs and Meta's Depth API page say Environment Depth works on Quest 3 and 3S (Q4-026). How 3S produces depth without a sensor, and what that costs, is not documented.

- **Q2-093** Quest 3S reports `SystemHeadset.Meta_Quest_3S = 12` and uses the `supportedDevices` ID `quest3s`. If `quest3s` is missing but `quest3` is listed, the compatibility rule should make it report Quest 3, the most recent older listed model. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-compatibility-mode/ (accessed 2026-09-24) · Applies to: Quest 3S · Evidence: [doc] [verify on device]
  - Notes: Meta gives only the Quest 3 example of the ordering; the 3S-to-Quest 3 case is inferred from release order.

- Cross-references for 3S: dynamic-resolution defaults (Q2-024 / Q2-090); Automatic Viewport Dynamic Resolution device list (Q3-C7); PCA, Depth API and MR level caps (section 7).

## 3. Frame pacing: stale and early frames, frame timing, levels, refresh, thermals

The logcat fields that pacing relies on (`Lat=`, `VSnc=`, `Prd`, `CFL`, `ICFLp95`, `LCnt`, `SF`) are defined in section 9.2 (Q1-028 / Q2-065, Q1-029, Q1-030 / Q2-068, Q1-033 / Q2-069). Reading levels from logs is covered in Q1-035 / Q1-036 / Q2-056.

### 3.1 Stale, early and torn frames

- **Q1-024 / Q2-066** How to read stale frames. [C]
  - A stale frame was not ready in time, so the compositor re-showed the previous one.
  - `Stale2/5/10/max` count runs of 2, 5 and 10 consecutive stale frames, plus the longest run, over the past second.
  - `Stale` between 0 and the refresh rate means judder.
  - `Stale` equal to the refresh rate with steady FPS (for example 72 FPS with 72 stale frames per second) means extra-latency mode: steady timing at the cost of latency, not a failure.
  - The Stats guide says extra-latency mode is on by default in Unity.
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (Q1-024, undated, partly pre-2023); https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ (Q2-066) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The failure signal is irregular staleness: a count between 0 and the refresh rate, non-zero `stale_frames_consecutive`, or non-zero Stale2/5/10. OVR Metrics shows STALE and "Max Consecutive Stale Frames". The consecutive-run counts are the best single comfort metric for [C]. The default-latency-mode claim conflicts with Lat=-1 reports (Q1-C5 / Q2-C11).

- **Q1-026 / Q2-067 / Q2-070** Early frames, tears, compositor time and swap interval. [T][C]
  - `Early` counts frames delivered before they were needed, which happens in extra-latency mode. Persistently high `Early` suggests levels are higher than needed. If `Early` roughly equals FPS, turn extra-latency mode off or spend the headroom.
  - `Tear` (screen tears) means the compositor took too long, usually because of too many layers.
  - `TW` / TW T is compositor (ATW) GPU time. It grows with layer count and layer type: equirect and cylinder layers cost more than quad and projection layers.
  - `LCnt` counts compositor layers including system layers. Layers with identical settings are merged.
  - SWAP (`VSnc`) should be 1.
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (Q1-026); https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (Q2-067, Q2-070) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Fix tears by removing overlay layers or disabling AppSW. Compositor-layer UI keeps text sharp, but its cost appears in TW T and layer counts, not in App T (section 6). The logcat page says extra-latency mode is on by default in Unity, but Phase Sync or FrameSync overrides it (Q1-C5 / Q2-C11).

- **Q2-078** What a missed frame looks like. [C]
  - The compositor re-shows the last frame with rotation-only TimeWarp. There is no positional correction unless AppSW is active.
  - Sustained misses show as judder, black flicker at the view edges during fast head turns, and added latency.
  - The display refresh rate never changes because of app misses.
  - Source: https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: See also https://developers.meta.com/horizon/documentation/native/android/os-compositor/ (Aug 2024). Recovery mechanisms, in order: dynamic resolution, dynamic FFR, refresh-rate throttle, then opt-in AppSW. A refresh drop does happen on thermal events (Q2-014); that is separate from app misses.

### 3.2 Frame-timing mode: FrameSync, Phase Sync, extra latency

- **Q2-071** FrameSync is now the default frame-timing algorithm on every app and device, replacing Phase Sync. [C]
  - It uses equally weighted sliding-window statistics, where Phase Sync used exponential decay.
  - It handles early and late frames symmetrically.
  - It trims the highest and lowest samples before averaging.
  - Phase Sync's three modes (adaptive, fixed latency, AppSW) are gone, and Phase Sync API calls are no-ops.
  - Source: https://developers.meta.com/horizon/essentials/framesync/ (updated May 13, 2026) (accessed 2026-09-24) · Applies to: all Quest on FrameSync OS builds (v203+) · Evidence: [doc]
  - Notes: Meta claims fewer stale frames (especially long runs) and lower motion-to-photon latency, but the doc page gives no numbers. Remove Phase Sync setup at your convenience. Whether Perfetto still shows a `PhaseSync` marker and `Lat=` still reports -1 on v203+ is unverified (QX-C4, QX-C9).

- **Q2-072** FrameSync rollout. [C]
  - Testable on v201 with the manifest meta-data `com.oculus.enable_frame_sync` set to true.
  - Default for Store apps from v203, with an opt-out.
  - Meta notes small, expected trade-offs: possibly slightly higher CPU/GPU use, battery drain and heat.
  - Source: https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ (Mar 2026) (accessed 2026-09-24) · Applies to: Quest on v201/v203+ · Evidence: [doc]
  - Notes: A forum developer who saw frame-rate drops said they had *added* `com.oculus.enable_frame_sync` = false "just in case" to a pending update. They did not report that it worked. The one reply came from a Start-program partner, not Meta staff (https://communityforums.atmeta.com/discussions/Questions_Discussions/app-frame-rate-drop/1368725, [community]). No official opt-out doc was found. [verify on device] (Corrected in gap-fill round 2. This note used to say the developer "reported opting out", which overstated the post; see QUEST-GF2-001.)

- **QUEST-GF1-007** FrameSync opt-out status. The FrameSync essentials page (updated May 13, 2026) documents no opt-out: it says FrameSync is on by default for every app on every supported device, needs no integration, and cannot run side by side with PhaseSync. The Mar 3, 2026 announcement blog says only that an opt-out "will be available" for Store apps from v203, without naming it. UploadVR reports the opt-out as `com.oculus.enable_frame_sync` = `false`, the same key used to opt in on v201. [C]
  - Source: https://developers.meta.com/horizon/essentials/framesync/ ; https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ ; https://www.uploadvr.com/meta-horizon-os-framesync-smoother-vr-quest/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S on v201/v203+ · Evidence: [doc] for the essentials page and blog; [community] for the `false` value [verify on device]
  - Notes: Treat the opt-out as undocumented. If a title regresses under FrameSync (the blog names higher CPU/GPU use, battery and thermal throttling as possible trade-offs), A/B with the manifest value `false` and confirm the mode switched from the CSV `phase_sync_mode` column or logcat `Lat=` before trusting the result. See QUEST-GF1-C1.

- **Q2-073** Phase Sync (legacy, for OS builds before FrameSync). [C]
  - No added overhead. More stale frames under spiky load. Pairs well with Late Latching. Overrides extra-latency mode.
  - Unity setup: the OpenXR provider on Unity 6+ with Meta XR SDK v74+, or the Oculus provider on Unity versions before 6 with SDK versions before v74.
  - Verify with `Lat=-1`.
  - Source: https://developers.meta.com/horizon/documentation/unity/enable-phase-sync/ (accessed 2026-09-24) · Applies to: Unity 2021.3 to 6.x on pre-FrameSync OS · Evidence: [doc]
  - Notes: The setprop toggle is `debug.Meta.phaseSync` on the Unity page and `debug.oculus.phaseSync` on the native page (https://developers.meta.com/horizon/documentation/native/android/mobile-phase-sync/, 2022, possibly stale) (Q2-C1).

- **Q4-057** Phase Sync has been always on since Oculus XR 4.2.0, which removed the setting. The same release added the Environment Depth APIs. Earlier releases added Phase Sync (1.7.0), Optimize Buffer Discards (1.5.0) and Low Overhead Mode (1.4.0). [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: Oculus XR Plugin versions · Evidence: [doc]
  - Notes: On Oculus XR 4.2.0+, extra-latency mode cannot be the Unity default through this plugin, which supports the Lat=-1 reports (Q1-C5 / Q2-C11). Under FrameSync the question is moot (Q2-071).

- **Q2-074** Unity bug OXPB-115: in Oculus XR 3.3.0 to 4.0.0 the PhaseSync toggle was ignored and Phase Sync was always on. It reproduced on 2021.3.28f1, 2022.3.4f1, 2023.1.2f1 and 2023.2.0a21, and was fixed in the Oculus XR 3.3.0 and 4.0.0 releases. [C]
  - Source: https://issuetracker.unity.com/issues/11487/oculusxr-phasesync-toggle-is-not-respected-and-its-always-enabled (accessed 2026-09-24) · Applies to: Unity 2021.3 to 2023.2 with Oculus XR 3.3 to 4.0 · Evidence: [doc]
  - Notes: For older projects on these versions, check `Lat=` rather than trusting the checkbox.

- **QUEST-GF2-001** FrameSync opt-out, round-2 re-check. Nothing newer than the Mar 2026 blog documents an opt-out. [C]
  - The blog's raw page text (re-read 2026-09-24) shows only the opt-in example, `<meta-data android:name="com.oculus.enable_frame_sync" android:value="true"/>`, and says an opt-out "will be available"; it never shows `false`.
  - The FrameSync essentials page (updated May 13, 2026) still names no opt-out, manifest key or OS version.
  - The Core SDK 203.0 and 205.0 download pages, the Horizon release-notes index and the Unity release archive contain no FrameSync text.
  - The forum thread usually cited for `false` (thread 1368725, posted Mar 7, 2026) does not report a working opt-out. The poster added `false` "just in case" for a future update. The only reply (Apr 2026) is from a Start-program partner, not Meta staff, and claims without data that disabling "has helped others".
  - Source: https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ ; https://developers.meta.com/horizon/essentials/framesync/ ; https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/203.0/ ; https://web.archive.org/web/20260417023528/https://communityforums.atmeta.com/discussions/Questions_Discussions/app-frame-rate-drop/1368725 (accessed 2026-09-24) · Applies to: Quest 2/3/3S on HzOS v201/v203+ · Evidence: [doc] for the absence on Meta pages; [community] for the forum thread [verify on device]
  - Notes: Whether `false` switches a v203+ Store build back to Phase Sync remains unverified. The cheapest check is the CSV `phase_sync_mode` column (QUEST-GF2-002): build once with `false` and once without, then compare the value on the same OS build.

- **QUEST-GF2-002** In public OVR Metrics CSVs, `phase_sync_mode` reads `4` in Aug 2026 Quest 3 captures and `1` in a Jan 2026 Quest 3 capture. That suggests `4` marks the FrameSync timing path on v203+ OS builds, but no Meta page defines the values. [C]
  - Aug 2026 setup: Quest 3, Unity app built from Meta's Passthrough Camera API samples, 72 Hz, OVR Metrics Basic CSV; three files, all 979 rows `phase_sync_mode=4`, `extra_latency_mode=0`.
  - Jan 2026 setup: Quest 3, Unity app, 72 Hz, 71 rows, all `phase_sync_mode=1`, `extra_latency_mode=0`.
  - An Oct 2023 Quest capture (Gym Class) has no `phase_sync_mode` column and shows `extra_latency_mode=1`.
  - Source: https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_144005.csv ; https://github.com/batunii/Arjuna/blob/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/session-log.md ; https://github.com/DemoySegment/CubemapRendering/blob/HEAD/Demo/com.DefaultCompany.lakedemo%23UnityPlayerActivity-20260102_033328.csv ; https://github.com/Raiduy/GAS-publication-figures/blob/main/Raw%20Data/Gym%20Class/com.IRLStudios.GymClass-20231015_201503.csv (accessed 2026-09-24) · Applies to: Quest 3; OVR Metrics CSV; HzOS versions not recorded in either capture · Evidence: [measured] (third-party captures; the value mapping is an inference) [verify on device]
  - Notes: Neither capture records its OS build, so the 1 to 4 change could also come from an OVR Metrics or runtime update. Before an analyzer script labels `4` as FrameSync, confirm it on a v203+ headset (and with the opt-out, QUEST-GF2-001). Until then, report the raw value and flag any change in it within a capture. The legacy `Lat=` values (-1 default Phase Sync, -2 fixed-latency, -3 AppSW-tuned, >0 extra-latency frames, 0 neither) were re-confirmed on the logcat page (Jul 31, 2025), which still does not mention FrameSync (QX-C9).

- **QUEST-GF2-003** In the GDC 2026 Q&A, Meta's speakers described FrameSync as a frame-start scheduler. It trades rendering latency against the GPU time the app gets, aiming to start each frame so it finishes just before display. They said Application SpaceWarp is not being deprecated and that the two work together. [C]
  - Source: https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ (Meta talk video (GDC 2026, Mar 10, 2026, David Borel and Neel Bedekar), read from its auto-generated captions; Q&A at about 55:30) (accessed 2026-09-24) · Applies to: Quest 3/3S (talk scope), HzOS v203+ · Evidence: [doc] (Meta talk)
  - Notes: This is the only Meta statement found on FrameSync plus AppSW. The talk gives no FrameSync overhead number and does not mention the `PhaseSync` Perfetto marker or `Lat=` (QX-C4, QX-C9 stay open).

### 3.3 Pose latency: Late Latching, input polling, GLES overhead

- **Q2-075 / Q4-063** Late Latching. [C]
  - It updates head and controller poses as late as possible, just before GPU submit, removing up to one frame of pose latency.
  - It needs Vulkan and Multiview.
  - Only children of tracked anchors and the view-projection matrix are patched. Other scripts, simulation and physics still see the simulation-time pose. The OVRManager "Late Controller Update" docs describe about a 10 ms mismatch between simulation and rendering.
  - Meta says its overhead is negligible and recommends it for most apps. Late Latching Debug Mode is for development only and must never ship.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (Q2-075, Q4-063); https://developers.meta.com/horizon/documentation/unity/enable-late-latching/ (Dec 6, 2024; Q2-075); https://developers.meta.com/horizon/documentation/unity/unity-ovrcamerarig/ (Q4-063) (accessed 2026-09-24) · Applies to: Unity with the OpenXR Meta Quest feature or Oculus XR, Vulkan. On Unity OpenXR, controller late latching is `TrySetControllerLateLatchAction` (1.9.1+). · Evidence: [doc]
  - Notes: `OVRManager.LateLatching` defaults to false. Local and networked poses can drift apart slightly. Unity's OpenXR 1.18 Meta Quest page does not list Late Latching as a setting (Q4-C8). Compare `Prd` before and after enabling it (Q1-033 / Q2-069).

- **Q2-076** OpenXR Latency Optimization setting. [C]
  - "Prioritize Input Polling" (recommended; matches the Oculus XR plugin's default behaviour) calls `xrWaitFrame` on the main thread before simulation, so poses use the latest predicted display time.
  - "Prioritize Rendering" moves the call to the render thread and can give poses one frame stale.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (updated May 11, 2026) (accessed 2026-09-24) · Applies to: Unity + OpenXR on Quest · Evidence: [doc]
  - Notes: Check this when migrating from Oculus XR to OpenXR (Oculus XR is deprecated from Unity 6.5). Q4-061 lists it with the other OpenXR settings.

- **Q2-077** Low Overhead Mode (an Oculus XR plugin setting) only makes the GLES driver skip validation. It is GLES-only and does nothing on Vulkan. Disable it if graphics become unstable. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html (accessed 2026-09-24) · Applies to: Unity + Oculus XR, GLES only · Evidence: [doc]
  - Notes: Not a lever for Vulkan projects.

### 3.4 CPU/GPU levels, Boost, dual-core, trading

- **Q1-105 / Q2-044** API surface for CPU/GPU levels. [T][C]
  - Unity (Meta XR Core SDK): `OVRManager.suggestedCpuPerfLevel` / `suggestedGpuPerfLevel`, backed by `OVRPlugin.suggestedCpuPerfLevel` / `suggestedGpuPerfLevel`.
  - Native: `ovrp_SetSuggestedCpuPerformanceLevel` / `ovrp_SetSuggestedGpuPerformanceLevel`.
  - Enum: `OVRPlugin.ProcessorPerformanceLevel { PowerSavings=0, SustainedLow=1, SustainedHigh=2, Boost=3 }`.
  - `OVRManager.cpuLevel` / `gpuLevel` are `[Obsolete]`.
  - Related members: `OVRManager.gpuUtilSupported` and `OVRManager.gpuUtilLevel` (OVRPlugin 1.21+), and the event `OVRManager.DisplayRefreshRateChanged(float from, float to)`.
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (Q2-044); SDK source https://raw.githubusercontent.com/darktable-mirror/com.meta.xr.sdk.core/main/Scripts/OVRPlugin.cs (Q2-044, SDK 207) and https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/OVRManager.cs (Q1-105, SDK v85) (accessed 2026-09-24) · Applies to: Unity 2021.3 to 6.x + Meta XR Core SDK (Oculus XR or OpenXR backend) · Evidence: [doc] (doc + SDK source)
  - Notes: Levels are hints; the OS picks the actual level within a range. Confirm the applied level with `debug.oculus.clockStateLogLevel` (Q1-035 / Q1-036 / Q2-056). The OpenXR-standard path is Q2-055.

- **Q2-045** Level ranges per `ProcessorPerformanceLevel`. [T][C]

  | ProcessorPerformanceLevel | CPU range | GPU range |
  |---|---|---|
  | PowerSavings | 0-4 | 0-4 |
  | SustainedLow | 2-4 | 1-4 |
  | SustainedHigh | 4-4 (5-5 with Quest 3/3S trading; 6-6 with Quest 2/Pro dual-core) | 3-5 |
  | Boost | 4 to device max | 3-5 |

  - Source: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ (updated Sep 2, 2026) (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: SustainedHigh is the default when nothing is set; this conflicts with the Unreal page (Q2-C2). Under SustainedHigh the CPU is fixed at level 4. The OS keeps levels as low as it can within the range while holding frame rate. For how the MR level caps interact with these ranges, see Q4-005.

- **Q2-046 / Q2-047 / Q4-003** Clock tables and automatic level changes. [T][C]

  | Level | Quest 2 / Pro CPU | Quest 3 / 3S CPU | Quest 2 / Pro GPU | Quest 3 / 3S GPU |
  |---|---|---|---|---|
  | 0 | 0.71 GHz | 0.69 GHz | 305 MHz | 285 MHz |
  | 1 | 0.94 GHz | 1.09 GHz | 400 MHz | 350 MHz |
  | 2 | 1.17 GHz | 1.38 GHz | 442 MHz | 456 MHz |
  | 3 | 1.38 GHz | 1.65 GHz | 490 MHz | 492 MHz |
  | 4 | 1.48 GHz | 1.92 GHz | 525 MHz | 545 MHz |
  | 5 | 1.86 GHz | 2.05 GHz | 587 MHz | 599 MHz |
  | 6 | 2.15 GHz | 2.21 GHz | n/a | n/a |
  | 8 | 2.42 GHz | 2.36 GHz | n/a | n/a |

  - Utilisation hysteresis on all of Quest 2/Pro/3/3S: the CPU level rises at 83% or more utilisation and falls at 77% or less; the GPU level rises at 87% or more and falls at 81% or less. Quest 1 used 91% / 85% for the GPU.
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ (Q2-046, Q2-047); https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (Q4-003) (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes:
    - GPU clocks per level are nearly the same across generations. The Quest 3 GPU uplift is architectural (Adreno 740 vs 650), not clock speed. Meta warns that equal level numbers across models do not mean equal throughput, so profile each device.
    - A workload hovering near 87% GPU utilisation at level N can oscillate between levels. That shows up as frame-time variance under FrameSync, and as heat.
    - Q4-003's rule of thumb for a sustained MR budget on Quest 3/3S is GPU L2 (456 MHz) and CPU L3 (1.65 GHz).
    - The ovrgpuprofiler page and Wikipedia give different peak GPU clocks (Q2-C5, QX-C6).

- **Q2-048 / Q4-009** Quest 2 level availability. [T][C]
  - CPU 0-4: always. CPU 5: only without dual-core mode. CPU 6: only with dual-core mode. CPU 8: only with CPU Boost.
  - GPU 0-4: always. GPU 5: only with dynamic resolution.
  - The current table lists no passthrough restriction for Quest 2.
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ (Q2-048); https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (Q4-009) (accessed 2026-09-24) · Applies to: Quest 2 (Quest Pro is the same, but loses level 4 with passthrough or tracking features), all Unity versions · Evidence: [doc] [verify on device]
  - Notes: Background OS features such as casting can override levels. No published number exists for what black-and-white passthrough costs a Quest 2 app. To measure it, build the same scene with the passthrough feature on and off, then compare OVR Metrics CPU L/GPU L, GPU% and app GPU time at locked levels.

- **Q2-049** Quest 3 / 3S level availability. [T]
  - CPU 0-3: always. CPU 4: only without passthrough. CPU 5: needs CPU 4 available plus trading set to -1. CPU 6: listed as needing CPU Boost (probably a doc error; see Q2-C8).
  - GPU 0-2: always. GPU 3-4: only without passthrough. GPU 5: needs GPU 4 available plus trading +1, or dynamic resolution.
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [doc] [verify on device]
  - Notes: The boost page says CPU Boost goes from level 4 to 8, so the "level 6 needs Boost" row disagrees with it. Check with `debug.oculus.clockStateLogLevel` (Q1-035 / Q1-036 / Q2-056). The passthrough restriction is Q2-038 / Q4-001, and whether GPU L5 can be reached with passthrough on is ambiguous (Q4-C1).

- **Q2-051** Dual-core mode. [T]
  - Quest 2 and Quest Pro only, on the OpenXR backend only (not legacy OVRPlugin).
  - Enable it with `<meta-data android:name="com.oculus.dualcorecpuset" android:value="true"/>`.
  - SustainedHigh CPU becomes 6-6 (2.15 GHz) on two cores.
  - At startup logcat shows `CreateClient: Value of isCPUSingleThreadedBoost is 1`.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2, Quest Pro; Unity with OpenXR · Evidence: [doc] [verify on device]
  - Notes: Meta calls Unity a typical candidate because UnityMain is single-threaded. Check in Perfetto for one saturated core (UnityMain) with the other cores under 50%. An app that uses three cores well at level 4 beats dual-core at level 6.

- **Q2-052** CPU/GPU level trading. [T]
  - Quest 3/3S only, on the OpenXR backend only, fixed at build time.
  - Manifest `com.oculus.trade_cpu_for_gpu_amount`: 1 = +1 GPU / -1 CPU; 0 = no change; -1 = -1 GPU / +1 CPU.
  - In Unity this is the "Processor Favor" setting on OVRManager/OVRCameraRig.
  - Logcat: `CreateClient: Value of tradeCpuForGpu is 1`.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S; Unity with OpenXR · Evidence: [doc] [verify on device]
  - Notes: The page frames trading as choosing which processor keeps its speed when thermal throttling downclocks. Changing it needs a new build, so choose it from long-session profiles, not startup profiles. With passthrough on, CPU L5 via trading is unreachable (Q4-004).

- **Q1-038** Boost and CPU/GPU trade settings leave logcat evidence: `CreateClient: Value of isCPUSingleThreadedBoost is 0` (or `1`) and `CreateClient: Value of tradeCpuForGpu is 1`. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S (the trade is Quest 3/3S only) · Evidence: [doc]
  - Notes: Check these lines once per build to confirm the manifest entries (Q2-051, Q2-052) reached the runtime.

- **Q2-053 / Q4-007** CPU Boost hint. [T][C]
  - It raises the CPU from level 4 to 8: +64% on Quest 2/Pro, about +23% on Quest 3/3S.
  - Limits: 45 consecutive seconds, and a share of total runtime that the same page gives as both 20% and 80% (Q2-C7 / Q4-C9).
  - It is inactive under Battery Saver or thermal throttling. When inactive it behaves exactly like SustainedHigh.
  - Code: `OVRManager.suggestedCpuPerfLevel = ProcessorPerformanceLevel.Boost;` then set it back to `SustainedHigh`.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc] [verify on device]
  - Notes: Use it for loading screens, scene transitions and MR bursts such as scene or room load. The token-bucket budget on the same page applies only to Meta VR Glasses. The page does not say how Boost behaves when passthrough has already removed CPU L4 on Quest 3/3S. To verify, look for `CreateClient: Value of isCPUSingleThreadedBoost is 1` and a jump in OVR Metrics "CPU L". Unity's OpenXR docs advise keeping Boost under 30 s (Q2-055; QX-C8).

- **Q2-054** Over-requesting levels costs battery and heat without adding frames. [C]
  - Meta says to pick the lowest levels that hold the target frame rate.
  - Persistently high `Early` frames suggest levels are higher than needed.
  - Sustained Boost defeats its purpose and costs battery and thermal headroom.
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ ; https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (Early guidance) ; https://developers.meta.com/horizon/essentials/thermal/ (Boost guidance) (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: For light scenes (menus, loading), step down to SustainedLow or PowerSavings to bank thermal headroom for later.

- **Q2-055** The Unity OpenXR path (`XR_EXT_performance_settings`). [T][C]
  - `XrPerformanceSettingsFeature.SetPerformanceLevelHint(PerformanceDomain.Cpu or Gpu, PerformanceLevelHint.PowerSavings / SustainedLow / SustainedHigh / Boost)`. SustainedHigh is the default. Keep Boost under 30 s.
  - `OnXrPerformanceChangeNotification` reports Normal/Warning/Impaired per domain (CPU/GPU) and per subdomain (Compositing/Rendering/Thermal).
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/performance-settings.html (accessed 2026-09-24) · Applies to: Unity + com.unity.xr.openxr (API since 1.11.0 per Q4-058; 1.19 docs) · Evidence: [doc] [verify on device]
  - Notes: No Meta page was found confirming that Horizon OS supports `XR_EXT_performance_settings` or sends the thermal notifications (gap). Check `xrEnumerateInstanceExtensionProperties` or the feature's validation on device before relying on it. The Meta SDK path (Q1-105 / Q2-044) is the documented one.

- **QUEST-GF1-010** Community evidence that Horizon OS exposes `XR_EXT_performance_settings`: the open-source PPSSPP OpenXR port calls `xrPerfSettingsSetPerformanceLevelEXT` on Quest 2 and, to reach CPU/GPU level 5, switched from `XR_PERF_SETTINGS_LEVEL_BOOST_EXT` (75) to a value 100 named `XR_PERF_SETTINGS_LEVEL_PERFORMANCE_MAX_EXT`, which is not in the Khronos spec. [T]
  - Source: https://github.com/hrydgard/ppsspp/commit/5491a05796863c89051bf9569e1d6597ed13f4a2 ; spec https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_EXT_performance_settings.html (accessed 2026-09-24) · Applies to: Quest 2 (stated in the commit), native OpenXR · Evidence: [community] [verify on device]
  - Notes: This narrows the Q2-055 gap: the extension is enumerated on Quest, but no Meta page documents it, the value 100 is not in the spec, and thermal notifications through Unity's `XrPerformanceSettingsFeature` remain unconfirmed. Stay on the documented Meta SDK API (Q1-105 / Q2-044) for shipping code. To check on device, log `xrEnumerateInstanceExtensionProperties` and watch `CPU L`/`GPU L` in OVR Metrics after each hint.

- **Q2-057** An OS update gave a 7% GPU boost at GPU level 4 in OS v49, with no app rebuild. Clock tables depend on the OS, so re-check them after major OS updates. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 2 era and later · Evidence: [doc]
  - Notes: Tie device baselines to an OS version in profiling notes.

- **QUEST-GF2-004** Meta's newer "CPU and GPU levels" essentials page gives its own range table for `ProcessorPerformanceLevel` on Quest:
  - PowerSavings: CPU 0–4, GPU 0–4.
  - SustainedLow: CPU 2–4, GPU 1–4.
  - SustainedHigh: CPU 4–4 on Quest 3/3S, 4–6 on Quest 2/Pro with dual-core; GPU 3–5.
  - Boost: CPU 4–6 on Quest 3/3S, 4–8 on Quest 2/Pro; GPU 3–5.
  - It adds that GPU level 5 needs dynamic resolution, and that higher CPU levels may be unavailable with passthrough or tracking features.
  - It gives a "CPU/GPU level 4 as the steady-state performance target" line, but only in its Meta VR Glasses section. [T][C]
  - Source: https://developers.meta.com/horizon/essentials/cpu-gpu-levels/ (no last-updated date in the page data) (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: The Quest 3/3S Boost ceiling of "6" conflicts with the boost page's Quest 3/3S row (level 4 to 8, +23%, which matches 1.92 to 2.36 GHz) (QUEST-GF2-C1). The "L6 needs Boost" availability row on the native levels page (Q2-049, Q2-C8) agrees with the essentials page, so the dispute is over the number of the Boost level, not the clock. Read `cpu_frequency_MHz` during Boost instead of trusting a level number: a third-party Aug 2026 Quest 3 CSV shows 2361 MHz samples (QUEST-GF2-011).

### 3.5 Refresh rate

- **Q2-010** The default refresh rate is 72 Hz. Supported rates: [C]

  | Device | Supported rates |
  |---|---|
  | Quest 2 | 60 (media apps only), 72, 80, 90, 96, 100, 120 |
  | Quest 3 | 72, 80, 90, 96, 100, 120 (plus extended rates, Q2-013) |
  | Quest 3S | 72, 80, 90, 96, 100, 120 |
  | Quest Pro | 72, 80, 90 |

  - Source: https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ (updated Aug 27, 2026) (accessed 2026-09-24) · Applies to: Quest 2/3/3S/Pro · Evidence: [doc]
  - Notes: 60 Hz in a non-media app fails store review. UploadVR (Sep 2026) reports that 96 and 100 Hz arrived earlier in 2026: https://www.uploadvr.com/qhorizon-os-2-7-adds-gamepad-emulation-and-207-hz-display-mode-240-hz-in-dev-mode/ ([community]). The system-properties page lists an older set (QX-C5), and the VRC page says 96/100 are not yet available (Q2-C4).

- **Q2-011** Meta XR Core SDK refresh-rate APIs. [C]
  - Query: `OVRPlugin.systemDisplayFrequenciesAvailable` / `OVRManager.display.displayFrequenciesAvailable`.
  - Set: `OVRPlugin.systemDisplayFrequency = 90.0f`.
  - React: subscribe to `OVRManager.DisplayRefreshRateChanged(float from, float to)`.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ (accessed 2026-09-24) · Applies to: Unity + Meta XR Core SDK, all Quest · Evidence: [doc]
  - Notes: The list API is marked deprecated. Requesting a rate it does not return is allowed; for example, 76 Hz works on Quest 2/Pro/3/3S. Meta still recommends staying on the charted rates for forward compatibility.

- **Q2-012** The Unity OpenXR: Meta path (`com.unity.xr.meta-openxr`). [C]
  - Enable the "Meta Quest Display Utilities" feature.
  - Query: `XRDisplaySubsystem.TryGetSupportedDisplayRefreshRates(Allocator, out NativeArray<float>)`.
  - Set: `TryRequestDisplayRefreshRate(float)`.
  - Both return false if the feature is disabled or the requested rate is not in the supported list.
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.5/manual/features/display-utilities.html (accessed 2026-09-24) · Applies to: Unity 2022.3+/6.x with OpenXR: Meta 2.x · Evidence: [doc] [verify on device]
  - Notes: The list-only check conflicts with Meta allowing unlisted rates (Q2-C10). The Quest 3 extended rates (73 to 207 Hz) may be rejected on this path.

- **Q2-013** Quest 3 extended refresh rates. [T][C]
  - Quest 3 accepts any integer rate from 72 to 207 Hz through the standard APIs, with no extra setup.
  - 207 Hz is the highest rate that delivers a full-resolution frame to the display.
  - Up to 240 Hz needs developer mode plus `adb shell setprop debug.oculus.forceDisplayScaling 1` and `adb shell setprop debug.oculus.refreshRate 240`. Reset both with `''`.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ (accessed 2026-09-24) · Applies to: Quest 3 only (not 3S, not Quest 2), HorizonOS v2.7+ · Evidence: [doc]
  - Notes: Above 207 Hz the display hardware upscales the image, which visibly softens small text and thin geometry. Meta says not to require extended rates, and to fall back to a reported rate when a request fails. Dynamic throttling still applies at these rates. Budgets: 207 Hz = 4.8 ms, 240 Hz = 4.2 ms (Q2-009).

- **Q2-014** How thermal handling changes the refresh rate. [C]
  - If an app running above 72 Hz hits a thermal event, the first step drops the display to 72 Hz.
  - The next step keeps the refresh rate but halves the app frame rate (equivalent to minVsyncs=2).
  - Simulate it with `adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SIMULATE_THERMAL --es subsystem refresh --ei seconds_throttled 10`.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Test every quality tier with this broadcast. Anything that assumes `Time.deltaTime`, fixed-timestep physics or refresh-locked animation must survive a 90/120 to 72 Hz change. Confirm the change by reading `OVRPlugin.systemDisplayFrequency`.

- **Q2-015** A refresh rate is available only if the manifest's `com.oculus.supportedDevices` lists a device that supports it. In compatibility mode, the available rates are limited to those supported by both the physical model and the compatibility model. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-compatibility-mode/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: The refresh-rate doc still says the Unity integration auto-adds `quest|quest2`, which is stale (Q2-C12). Inspect the merged AndroidManifest in every build.

- Cross-reference: Q4-016. At 72 Hz in flicker-free lighting, Quest 3/3S passthrough syncs its cameras to the display (section 7.1).

### 3.6 Thermals over 20–30 minutes

- **Q2-058** Horizon OS manages heat in four stages. [C]
  1. Sustained budgeting through CPU/GPU levels.
  2. Throttling: clock cuts, so per-frame cost rises and timing varies.
  3. FrameSync adapting to the variable cost.
  4. A forced cool-down state with a user notification, if a hard limit is passed.
  - Source: https://developers.meta.com/horizon/essentials/thermal/ (updated Sep 15, 2026) (accessed 2026-09-24) · Applies to: all Meta VR devices · Evidence: [doc]
  - Notes: Sensors cover the SoC, battery and surface.

- **Q2-059** Meta: "Build for the long session." The page warns of a "thermal cliff at minute ten": an app that looks fine for three minutes and then degrades is running near the thermal ceiling. [C]
  - Source: https://developers.meta.com/horizon/essentials/thermal/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Meta's listed heat drivers:
    - Heavy shaders plus high-resolution post-processing.
    - Full-resolution passthrough with a heavy 3D scene.
    - Always-on physics, particles or dynamic lights.
    - Not using foveation or AppSW.

- **Q2-060** No published Meta number exists for the thermal decay curve (FPS, level or clock over 20–30 minutes). Community figures (such as FPS drops at about 18 minutes, or 3S throttling less than Quest 3) could not be traced to a primary measurement and are excluded. [C]
  - Source: https://developers.meta.com/horizon/essentials/thermal/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] [verify on device]
  - Notes: How to measure it:
    - Run a 30-minute soak at the shipping refresh rate with an OVR Metrics CSV recording FPS, STALE, APP T, CPU L, GPU L, POW L and DRR.
    - Keep ambient temperature fixed, the battery above 50% and the headset unplugged.
    - Repeat per device and per MR/VR mode.
    - Fire `COMPOSITOR_SIMULATE_THERMAL` (Q2-014) to rehearse the response.

- **Q1-016 / Q2-061** Power and thermal signals. [C]
  - `PLS=` in logcat, and `power_level_state` / POW L in OVR Metrics: 0 NORMAL, 1 SAVE, 2 DANGER. DANGER shows the user an overheat dialog.
  - `Temp=` (battery/sensor temperature) is legacy from phone VR; use `PLS` as the thermal indicator on Quest.
  - CSV soak signals: `battery_temperature_celcius`, `power_wattage`, `power_current`, `power_voltage`, plus CPU/GPU level and frequency over time.
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (Q1-016); https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (Q1-016, Q2-061) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Meta advises cutting rendering cost when the device enters power save. Detect decay yourself: flag any move of `power_level_state` to 1 or 2, and any fall in `gpu_frequency_MHz` or `cpu_frequency_MHz` while the scene is steady. No published number exists for when each device's thermal states begin; measure with a 30-minute scripted soak at room temperature. Q1-016 notes that since Performance.2 was retired the store no longer gates thermal decay; the 45-minute Performance.1 test still catches decay below 60 fps (QX-C7).

- **Q2-062** Battery Saver (a user setting: Settings > General > Power). [T][C]
  - Lowers brightness to 40%.
  - Forces FFR to level 3.
  - Drops the display to 72 Hz, capping FPS at 72.
  - Disables GPU level 5 (the dynamic-resolution boost) and the CPU Boost hint.
  - Logcat shows `LP=1`.
  - Source: https://developers.meta.com/horizon/essentials/battery-saver-mode/ (updated Apr 8, 2026); Unity page https://developers.meta.com/horizon/documentation/unity/os-battery-saver-mode/ (Jul 29, 2025) (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc] [verify on device]
  - Notes: Meta says apps should detect it and adapt, but no Unity detection API was found. The practical signal is `OVRManager.DisplayRefreshRateChanged` to 72 Hz.

- **Q2-063** FrameSync is designed to absorb the variable frame cost that throttling causes. Meta still advises spreading expensive work across frames and keeping per-frame patterns predictable, for smooth output and lower sustained heat. [C]
  - Source: https://developers.meta.com/horizon/essentials/thermal/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Time-slice LOD streaming, GI probe updates and occlusion rebuilds instead of running each in a one-frame burst.

- **Q2-064** Charging raises sustained clocks above nominal. Meta says this for Meta VR Glasses, and it is why tethered profiling sessions can overstate sustained performance. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/optimize-performance/ (accessed 2026-09-24) · Applies to: Meta VR Glasses (stated); Quest behaviour unverified · Evidence: [doc] [verify on device]
  - Notes: Profile Quest thermal runs on battery, or record the charging state in the capture metadata. To test on Quest, run the same 10-minute soak plugged in and unplugged and compare the `gpu_frequency_MHz` / `cpu_frequency_MHz` series.

## 4. Resolution and foveation: eye buffer, render scale, FFR, subsampled layout, dynamic resolution, symmetric projection, MVRR

### 4.1 Eye-buffer size and render scale

- **Q2-017 / Q3-001** Physical panel and default eye buffer at render scale 1.0, per device. Every default is below panel resolution. Quest 1 rendered 1216x1344 on a 1440x1600 panel. [T][C]

  | Device | Physical per eye | 100% render scale |
  |---|---|---|
  | Quest 2 | 1832x1920 | 1440x1584 |
  | Quest Pro | 1800x1920 | 1440x1584 |
  | Quest 3 | 2064x2208 | 1680x1760 |
  | Quest 3S | 1832x1920 | 1680x1760 |

  - Source: https://developers.meta.com/horizon/documentation/native/android/os-render-scale/ (updated Jan 9, 2025) (accessed 2026-09-24) · Applies to: all Quest, all engines · Evidence: [doc]
  - Notes: Quest 3 and 3S share the default eye buffer, so at equal content and scale their eye-buffer fill cost is the same. The panels differ, so decide supersampling per device (Q2-088). The same defaults appear as `debug.oculus.textureWidth` / `textureHeight` (Q1-080) and in a Jan 2026 Quest 3 CSV (Q1-015). Meta's agentic skill gives a wrong Quest 3 value (Q1-C4).

- **Q2-018 / Q3-002** The render scale needed to match the panel is about 1.09 on Quest 3S, 1.24 on Quest 2 and 1.23 on Quest Pro. On Quest 3, scale 0.8 gives 1344x1408 per eye and 1.5 gives 2520x2640. Rendering above panel resolution still adds sub-pixel clarity and reduces the blur from the lens-distortion resample, mostly toward the edges. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-render-scale/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: The page text gives no Quest 3 panel-match value. Dividing the table values gives about 1.23 horizontally and 1.25 vertically (arithmetic, not published). Render scale does not change system popups or the passthrough feed, which are composited separately. For native apps, render scale is the declared target size divided by the recommended size. On 3S, anything above about 1.09 spends GPU time for sub-pixel gain only.

- **Q2-020 / Q2-021 (part) / Q3-004** Unity's two XRSettings knobs. [T][C]
  - `XRSettings.eyeTextureResolutionScale` multiplies the device's recommended eye-texture size and always reallocates the eye textures.
  - `XRSettings.renderViewportScale` (0 to 1) renders into a sub-rectangle of the already-allocated eye texture, with no reallocation. It cannot be changed while cameras are rendering, it takes effect on the next frame, and it is not supported with deferred rendering.
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRSettings-eyeTextureResolutionScale.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRSettings-renderViewportScale.html (accessed 2026-09-24) · Applies to: Unity 2021.3 to 6.x · Evidence: [doc]
  - Notes: 1.0 is the Meta default in Q2-017 / Q3-001, so 1.0 on Quest 3 means 1680x1760 per eye. Change `eyeTextureResolutionScale` only at loads or transitions, because reallocation causes a hitch. For per-frame changes use `renderViewportScale` and read back `XRSettings.appliedRenderViewportScale`, because the runtime treats the value as a hint. OVRManager's reference says `renderViewportScale` was broken in some Unity versions it does not list, so check the applied value on device. Q2-021 also called `XRDisplaySubsystem.scaleOfAllRenderTargets` the display-subsystem equivalent of `renderViewportScale`. That part is superseded by Q3-005 (QX-C1).

- **Q3-005** `XRDisplaySubsystem.scaleOfAllRenderTargets` also always reallocates. `scaleOfAllViewports` is the per-frame alternative. [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem-scaleOfAllRenderTargets.html ; gap-fill check during synthesis: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem-scaleOfAllViewports.html (page built 2026-09-23) (accessed 2026-09-24) · Applies to: Unity 2021.3 to 6.x · Evidence: [doc]
  - Notes: The gap-fill check read both Unity pages.
    - `scaleOfAllRenderTargets`: changing it always reallocates the textures, and Unity points to `scaleOfAllViewports` for changes on the fly.
    - `scaleOfAllViewports`: range 0.0 to 1.0, changed without reallocation, applied the next time scene rendering begins (after LateUpdate). Providers may ignore or clamp it; read `appliedViewportScale` for the value actually applied. Not supported with legacy deferred.

    This resolves QX-C1 in favour of Q3-005.

- **Q2-022 / Q3-006** URP writes its render scale into XR itself. [T][C]
  - At pipeline init, and again per camera, `UniversalRenderPipeline` passes the camera render scale to `XRSystem.SetRenderScale(...)`, which sets `XRDisplaySubsystem.scaleOfAllRenderTargets`.
  - Values within ±0.05 of 1.0 (`kRenderScaleThreshold = 0.05f`) snap to exactly 1.0, so 0.96 to 1.04 does nothing.
  - The asset range is 0.1 to 2.0.
  - Source: https://raw.githubusercontent.com/Unity-Technologies/Graphics/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs ; https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRSystem.cs ; https://raw.githubusercontent.com/Unity-Technologies/Graphics/master/Packages/com.unity.render-pipelines.core/Runtime/XR/XRSystem.cs (accessed 2026-09-24) · Applies to: URP 12 (2021.3, as `XRSystem.UpdateRenderScale` in the URP package), URP 14, URP 17 (6000.0/6000.3 branches checked) · Evidence: [doc] (source code) [verify on device]
  - Notes: In XR, the URP asset Render Scale is therefore the eye-texture scale. Changing it reallocates the eye textures, the same cost as changing `eyeTextureResolutionScale` (Q3-005). For a real change use 0.94 or lower, or 1.06 or higher. Verify with `SF=` in logcat or EBW/EBH in OVR Metrics (Q2-023 / Q3-052).

- **Q3-007** In URP for Unity 6.3, when an IUpscaler is active, the XR render scale passed to `XRSystem.SetRenderScale` is forced to 1.0 so scaling is not applied twice. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs (accessed 2026-09-24) · Applies to: URP 17.3 (Unity 6.3) and later · Evidence: [doc] (source code) [verify on device]
  - Notes: With a custom IUpscaler the eye texture stays at full allocation, and the upscaler owns the pre-upscale resolution.

- **Q3-008** For URP, Unity recommends `XRSettings.renderViewportScale`. When URP renders straight into the eye texture (no post-processing), the viewport scale applies directly: 0.5 renders into a quarter of the texture. Unity says this is compatible with FFR. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/xr-graphics-resolution-scaling.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html (accessed 2026-09-24) · Applies to: Unity 6.3 to 6.6 URP · Evidence: [doc]
  - Notes: The same page says URP also renders directly "when you enable HDR", which looks wrong (Q3-C10). To confirm a camera renders straight to the eye texture, check in Frame Debugger that the DrawOpaqueObjects target is unnamed (the back buffer), or use the Render Graph Viewer. FFR compatibility holds only for direct rendering (Q3-C8).

- **Q3-009** When post-processing forces intermediate textures, dynamic resolution needs "URP Dynamic Resolution" enabled on the camera (Output section). URP then scales the intermediates through ScalableBufferManager, and `renderViewportScale` controls the final blit viewport. Unity says this path cannot be combined with FFR or with TAA. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html (accessed 2026-09-24) · Applies to: Unity 6.x URP with post-processing · Evidence: [doc]
  - Notes: Projects that keep post-processing on get either dynamic resolution on the intermediates or FFR, not both. This points toward on-tile post-processing (6.3+) or turning post-processing off (lead for the URP bundle).

- **Q3-010** Unity's manual says changing the URP asset Render Scale reallocates the eye texture, is expensive, and should not be done per frame. It presents this as the URP alternative to `eyeTextureResolutionScale`, which it calls unsupported in URP. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html (accessed 2026-09-24) · Applies to: Unity 6.x URP · Evidence: [doc]
  - Notes: Meta's guidance disagrees (Q3-011, Q3-C5).

- **Q3-011** Meta's Unity render-scale guidance: set `XRSettings.eyeTextureResolutionScale`; with URP you "may additionally need" to set the URP asset's `renderScale`. Enabling Dynamic Resolution overrides both. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-render-scale/ (accessed 2026-09-24) · Applies to: Meta XR SDK, BiRP and URP · Evidence: [doc]
  - Notes: Given Q2-022 / Q3-006, in URP it is the asset `renderScale` that actually lands in `scaleOfAllRenderTargets`. Set both to the same value and change them only at loads.

- **Q3-012** Meta's Unity-PerformanceSettings sample treats the effective scale as `renderViewportScale × eyeTextureResolutionScale`. [T][C]
  - It raises `eyeTextureResolutionScale` and the URP asset `renderScale` only when it needs more than is allocated.
  - It then sets `renderViewportScale = target / eyeTextureResolutionScale`.
  - Turning dynamic resolution off resets `renderViewportScale` to 1.0.
  - Source: https://github.com/oculus-samples/Unity-PerformanceSettings (accessed 2026-09-24) · Applies to: Unity 6000.3.15f1+ (sample requirement), Meta XR SDK · Evidence: [doc] (sample code)
  - Notes: This is the reference pattern: allocate high once, then move only the viewport, which avoids reallocation hitches. The sample also drives `OVRManager.instance.minDynamicResolutionScale` / `maxDynamicResolutionScale` and `OVRManager.SetSpaceWarp`.

- **Q3-013** Unity issue 22353 (Graphics XR): in an OVRCameraRig project with post-processing disabled on the Universal Renderer asset but still ticked on the CenterEyeAnchor camera, URP renders into `_CameraColorAttachmentA` (an intermediate) instead of straight to the eye texture. The fix note for 2023.2 calls it a redundant blit caused by post-processing. [T]
  - Source: https://issuetracker.unity.com/issues/22353 (accessed 2026-09-24) · Applies to: reproduced on 2020.3.46f1, 2021.3.21f1, 2022.2.12f1, 2023.1.0b9, 2023.2.0a8 · Evidence: [doc] (Unity issue tracker, QA reproduced) [verify on device]
  - Notes: The tracker lists no fixed-in version for 2021.3 or 2022.3. The cost is an extra full-resolution resolve and blit. With the Meta (Legacy) FFR API, the intermediate also escapes foveation (Q3-025). Untick camera post-processing when the renderer has it off, then check the DrawOpaqueObjects target in Frame Debugger. An extra eye-resolution surface in `ovrgpuprofiler -t` is the same symptom (Q1-069).

- **Q3-014** The URP 14 changelog lists "Improved renderViewportScale for XR intermediate textures" in 14.0.9 (2023-12-21). The URP 17 line lists "Enabled renderViewportScale for XR intermediate textures". [T][C]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/changelog/CHANGELOG.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.6/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: URP 14.0.9+ (2022.3), URP 17.x · Evidence: [doc]
  - Notes: On 2021.3 (URP 12) and early 2022.3, do not assume `renderViewportScale` behaves correctly when intermediate textures exist. Stay on the latest 2022.3 patch.

- **Q2-023 / Q3-052** Confirming the eye-buffer size actually submitted. [T][C]
  - `SF=` in the VrApi logcat line is the submitted framebuffer divided by the device-recommended size (Meta's dynamic-resolution example shows `SF=1.03`). The same line carries GPU%, `Stale`, `LCnt` and `CFL`.
  - OVR Metrics shows EBW/EBH (eye buffer width and height) and a "Render Scale Percent" graph. The CSV columns are `eye_buffer_width`, `eye_buffer_height` and `render_scale`.
  - `DSF=` (DPU scaling factor) above 1 means the display processor is upscaling to native resolution.
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (Q2-023); https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ (Q2-023, EBW/EBH); https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ and https://developers.meta.com/horizon/resources/vrc-quest-performance-4/ (Q3-052) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Graph SF against GPU% over a play session to see where resolution drops come from. SF is also the quickest check that a render-scale change reached the compositor (Q1-033 / Q2-069).

- **Q3-092** Unity says `XRSettings.renderViewportScale` is not supported on HDRP. HDRP is out of scope for Quest. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html (accessed 2026-09-24) · Applies to: HDRP · Evidence: [doc]

- Cross-references: the Quest 3 vs Quest 2 pixel-count ratio is Q2-019. The Quest 3S panel-match trade-off is Q2-088. The VRC 85% render-scale floor is Q1-087 / Q2-026 / Q3-003.

- **QUEST-GF2-006** On XR2 Gen 2 (Quest 3/3S), Meta now recommends 2x MSAA rather than 4x. For more sharpness, use TAA or supersampling rather than 4x. The recommended-MSAA API still returns 4 only so existing apps don't break. Unity's 6.6 untethered-XR optimization page also recommends MSAA 2X, alongside Vulkan, HDR off, Forward, Depth Priming off, Opaque and Depth Texture off, SSAO off, and on-tile post-processing (Unity 6.3+). [T]
  - Source: https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ (Meta talk video (GDC 2026, Mar 10, 2026, David Borel and Neel Bedekar), read from its auto-generated captions; about 8:10–8:40); https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: Quest 3/3S (the talk names XR2 Gen 2); Unity 6.6 page is URP, Vulkan · Evidence: [doc] (Meta talk; Unity manual) [verify on device]
  - Notes: This conflicts with older 4x MSAA advice in this dossier (Q4-059 / Q3-069 memory figures assume 4x; the Meta settings pages in section 8 say to set 4x in the URP asset) (QUEST-GF2-C2). The talk gives no ms figure for 2x vs 4x on Adreno 740. On Quest 2 (Adreno 650) the talk makes no claim, so keep 4x as the Quest 2 default until measured. Measure `App` GPU time at 2x vs 4x with FFR and levels locked.

### 4.2 Fixed foveated rendering (FFR)

- **Q3-021** Quest FFR works on the Adreno tiled renderer by setting the resolution of individual bins (tiles). In Meta's debug maps, white tiles are full resolution, green tiles are 1/4 resolution and black tiles are not rendered. On Vulkan it is driven by `VK_EXT_fragment_density_map`; `VK_EXT_fragment_density_map2` reduces latency on Qualcomm. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (updated Apr 7, 2026) (accessed 2026-09-24) · Applies to: Quest 2/3/3S (Adreno 650/740) · Evidence: [doc]
  - Notes: The maps shown are for Quest 3; tile layout varies by headset and settings. FFR saves fragment work only. Vertex, binning and compositor costs are unchanged.

- **Q3-022** In Meta's example graph, with 16% of GPU utilisation spent in TimeWarp (which FFR does not affect), FFR Low gave a 6.5% improvement, Medium 11.5% and High 21%. The page's headline is up to 25% in pixel-intensive apps. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: device for the graph not stated · Evidence: [measured] [verify on device]
  - Notes: These are relative GPU-utilisation gains for one unnamed workload. No per-device (Quest 2/3/3S) or per-Unity-pipeline numbers were found. To measure, turn off dynamic foveation and dynamic resolution, fix the GPU level, and sweep `debug.oculus.foveation.level` 0 to 3 while logging GPU time.

- **Q3-023** On apps with simple shaders, FFR Low can be a net loss, because its fixed overhead exceeds the fragment savings. Meta advises changing the level only at scene transitions and turning FFR off in menus. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Unlit or baked-lighting mobile content should A/B FFR rather than assume a win. A visible level change mid-gameplay reads as a pop.

- **Q3-024** FFR does not affect compositor layers. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: HUD and text on layers keep full quality at any FFR level, but FFR does not reduce their compositor cost either.

- **Q3-025** Unity OpenXR has two FFR paths. On Unity 2022 only the legacy path exists. [T][C]
  - **SRP Foveation API:** needs Unity 6+, OpenXR 1.11.0+ and URP. Unity recommends it.
  - **Meta/Legacy API:** Quest only. Works on Unity 2022.3 and with BiRP (Meta Core SDK 68.0+), but does not foveate intermediate render targets (post-processing, tonemapping, camera stacking).
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/foveatedrendering.html (accessed 2026-09-24) · Applies to: Unity 2022.3 (legacy only), 6.0 to 6.6 · Evidence: [doc]
  - Notes:
    - Select the SRP path under OpenXR > All Features > Foveated Rendering > gear > Foveated Rendering Method = "Foveated rendering (SRP API)".
    - The legacy path uses Method = Legacy, with Foveated Rendering disabled and "Meta XR Foveation" enabled.
    - OpenXR 1.17.0 (2026-04-09) made the SRP API the default method.
    - On 2022.3 with any intermediate target, FFR is effectively off for the passes that write it.
    - Meta says the SRP API is often 20–30% faster in frame time than Legacy for multi-pass pipelines (Q4-061).
    - See Q3-C4 for the 2022.3 support claim.

- **Q3-026** With the SRP API, the control is `XRDisplaySubsystem.foveatedRenderingLevel`, a value from 0 to 1. [T]
  - 1 is the platform maximum, the default is 0 (off), and on Meta 0.5 maps to Medium.
  - A change applies the next time scene rendering begins.
  - The project-level Foveated Rendering setting must be enabled, or the runtime value is ignored.
  - Unity's sample waits about 3 frames for the display subsystem to initialise.
  - Source: https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRDisplaySubsystem-foveatedRenderingLevel.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-enable.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/foveatedrendering.html (accessed 2026-09-24) · Applies to: Unity 6.x with OpenXR · Evidence: [doc]
  - Notes: Code: `SubsystemManager.GetSubsystems(displays); displays[0].foveatedRenderingLevel = 0.5f;`. For gaze (Quest Pro only), also set `foveatedRenderingFlags = FoveatedRenderingFlags.GazeAllowed`. The Oculus XR manual maps the same property as 0 = off, < 0.33 low, < 0.66 medium, ≥ 0.66 high (Q4-056).

- **Q3-027** With the Meta XR SDK, the controls are `OVRManager.foveatedRenderingLevel` (Off/Low/Medium/High/HighTop) and `OVRManager.useDynamicFoveatedRendering`. On the OpenXR backend HighTop is treated as High. The older members (`fixedFoveatedRenderingLevel`, `useDynamicFixedFoveatedRendering`) are documented as Qualcomm-only. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-fixed-foveated-rendering/ (updated Aug 28, 2026); https://developers.meta.com/horizon/reference/unity/v85/class_o_v_r_manager/ (accessed 2026-09-24) · Applies to: Meta XR Core SDK (reference v85) · Evidence: [doc]
  - Notes: The reference publishes no default values. Natively, HighTop is achieved on OpenXR with High plus `verticalOffset`.

- **Q1-081 / Q3-028** Overriding and reading foveation on device. [T][C]
  - Set the level with `adb shell setprop debug.oculus.foveation.level N`: 0 Off, 1 Low, 2 Medium, 3 High, 4 High Top.
  - Set `debug.oculus.foveation.dynamic 0` first (it accepts 0 or 1), or dynamic foveation overrides the level.
  - The VrApi logcat line reports `Fov=3`, with a `D` suffix (`Fov=3D`) when dynamic foveation is active.
  - Source: https://developers.meta.com/horizon/documentation/unity/os-fixed-foveated-rendering/ (updated Dec 4, 2024; Q1-081); https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (Q1-081); https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (Q3-028) (accessed 2026-09-24) · Applies to: Quest 2/3/3S (fixed foveation; no eye tracking) · Evidence: [doc]
  - Notes: Use this to A/B FFR without a rebuild. Sweep 0 to 4 and plot `app_gpu_time_microseconds`: a large drop means the app is fragment-bound. `Fov=0` while the app believes it set a level means the setting is not taking effect.

- **Q3-029** With dynamic foveation, the set level becomes a maximum, and the runtime raises foveation up to it based on GPU utilisation. It has no effect at level 0. Under the old VrApi, levels 3 and 4 behave the same when dynamic. [T][C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/foveatedrendering.html ; https://developers.meta.com/horizon/documentation/native/android/mobile-ffr/ (VrApi, deprecated; updated Oct 18, 2024) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Dynamic foveation helps throughput and hurts visual consistency, because periphery quality changes with load. Turn it off when profiling so FFR savings are not mistaken for scene changes.

- **Q3-030** Unity OpenXR dynamic foveation requirements. [T][C]
  - Vulkan; the Foveated Rendering feature with Method = SRP API; runtime support for XR_FB_foveation, XR_FB_foveation_configuration, XR_FB_foveation_vulkan and XR_FB_swapchain_update_state.
  - Enable it with gear > "Dynamic Foveation (Vulkan)", or at runtime with `FoveatedRenderingFeature.DynamicFoveationEnabled`.
  - It is not compatible with Quad Views or the Legacy API.
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/foveatedrendering.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-support.html (accessed 2026-09-24) · Applies to: OpenXR 1.18.0 or 1.19 (Q3-C2), Unity 6.x · Evidence: [doc]
  - Notes: The doc sample sets `foveatedRenderingLevel = 0.7f` before enabling dynamic mode. Meta recommends combining dynamic foveation with eye tracking where available, but it works without eye tracking. Q4-058 says dynamic foveation ships in OpenXR 1.18.0 only (see Q3-C2).

- **Q3-032** Natively, foveation is configured with `XrFoveationLevelProfileCreateInfoFB`: level NONE/LOW/MEDIUM/HIGH, `verticalOffset`, and dynamic mode through `XR_FOVEATION_DYNAMIC_LEVEL_ENABLED_FB`. The profile can be updated per frame with `xrUpdateSwapchainFB`. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: native OpenXR, and what Unity's providers call underneath · Evidence: [doc]
  - Notes: The required extensions are XR_FB_swapchain_update_state, XR_FB_foveation, XR_FB_foveation_configuration, XR_FB_foveation_vulkan and XR_META_vulkan_swapchain_create_info.

- **Q3-033** Unity OpenXR picks a foveation technique in this order: gaze-based FDM, fixed FDM, fragment shading rate from a provider texture, then fragment shading rate from a compute shader. On Vulkan, FDM foveation turns itself off if `VK_EXT_fragment_density_map` is missing. OpenXR 1.17.0-pre.2 added a check for that extension before using the FDM bit. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/foveatedrendering.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: Quest (FDM path) · Evidence: [doc]

- **Q3-034** Quest reports `SystemInfo.foveatedRenderingCaps = FoveationImage`: variable-rate shading with linear rasterization, so custom HLSL needs no coordinate remapping. `NonUniformRaster` (variable-rate rasterization, visionOS Metal) is the case that needs Unity's remap shader functions. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-support.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-introduction.html (accessed 2026-09-24) · Applies to: Unity 6.x · Evidence: [doc]
  - Notes: Screen-space effects that sample neighbours can still show tile-resolution steps in the periphery, because content there really is lower resolution. No shader rewrite is needed on Quest.

- **Q3-035** URP's FFR integration history. [T]
  - Foveated rendering was integrated into URP in the 14 and 15 lines (URP 15.0.1 changelog, and a URP 14 entry).
  - URP 17 enabled foveation for the UberPost pass when it is the last pass, and for FinalPostBlit.
  - URP 17 fixed per-XRPass control, so foveation is turned off on intermediate passes when `renderViewportScale` is active under RenderGraph.
  - OpenXR 1.18.0-pre.1 turns off FDM attachments at foveation level 0 (SRP path).
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.6/changelog/CHANGELOG.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/changelog/CHANGELOG.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: URP 14 (2022.3) to 17.x (6.x) · Evidence: [doc]
  - Notes: On URP 17, a final post pass that writes the eye texture can be foveated. Earlier post chains could not.

- **Q3-036** A community report on Unity 6000.1.15f1 and 6000.2 (URP 17.0.3 to 17.2.0, OpenXR 1.15.1, Meta SDK v77) on Vulkan describes FFR glitches, frame rate falling from 90 to 40–60 fps, and GPU utilisation rising from about 50% to over 90%, even at FFR level 0. It was confirmed on Quest 2. Unity bug IN-115870 was filed Sep 16, 2025, and a fix is reported in 6000.3.0f1. [T][C]
  - Source: https://discussions.unity.com/t/bug-severe-ffr-glitches-performance-loss-with-unity-6-1-6-2-with-urp-vulkan-openxr-on-quest/1677819 (accessed 2026-09-24) · Applies to: Unity 6.1/6.2 URP, Quest 2 (others likely) · Evidence: [community] [verify on device]
  - Notes: If a 6.1 or 6.2 project shows doubled GPU time with the Foveated Rendering feature on, test with the feature fully disabled (not just at level 0), and move to 6.3+.

- **Q3-037** A community report says that on Unity 6.0 with the SRP foveation path and URP HDR enabled, the top half of the image goes low-resolution instead of the periphery. Workarounds: the Legacy API, or HDR off. [C]
  - Source: https://discussions.unity.com/t/srp-foveated-rendering-on-quest-broken-with-openxr-urp-hdr/1672458 (Jul 30, 2025) (accessed 2026-09-24) · Applies to: Unity 6.0 URP, OpenXR, Quest · Evidence: [community] [verify on device]
  - Notes: Unity's 6.6 untethered guidance also says to disable HDR for bandwidth (Q3-093 / Q4-053; Q3-C10).

- **Q3-038** A Meta feedback report says that on Unity 6000.4.8f1, FFR High combined with 24-bit Depth Submission produces glitched squares with Meta's 6000.4 oculus-app-spacewarp URP fork. Status: Investigating, with 2 similar reports. [C]
  - Source: https://developers.meta.com/horizon/feedback/vr/investigations/2302986490105678/ (accessed 2026-09-24) · Applies to: Unity 6000.4, Meta URP fork, AppSW with depth submission · Evidence: [community] [verify on device]

- **Q3-039** Every current FFR feature in Meta's and Unity's docs (SRP Foveation API on Quest, dynamic foveation, subsampled layout, FDM2) is Vulkan-only. No current (2023 or later) Meta or Unity page read documents a GLES FFR path for URP. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/foveatedrendering.html (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The deprecated VrApi FFR page references GL subsampled-layout specs, which is legacy (VrApi was deprecated Aug 31, 2022). Treat GLES FFR as unsupported for new Unity work. If a GLES build must ship, verify it with `Fov=` in logcat.

- Cross-references:
  - Dynamic foveation plus dynamic resolution: Q3-031 / Q2-025 (part) / Q4-060 (part).
  - Eye-tracked foveation (Quest Pro only): Q2-007 / Q3-040 / Q4-008.
  - Battery Saver forces FFR level 3: Q2-062.
  - Quest 3S FOV effect on FFR savings: Q2-091.
  - The RenderObjects render-pass split with foveation: Q3-054 / Q2-025 (part) / Q4-060 (part).
  - FFR in the Unity 6.6 checklist: Q3-093 / Q4-053.

### 4.3 Vulkan subsampled layout

- **Q3-041** Subsampled layout (`VK_IMAGE_CREATE_SUBSAMPLED_BIT_EXT`) stores low-density tiles at their reduced resolution in a subregion, instead of expanding them to full resolution on store. This saves bandwidth, and the compositor's bilinear upsample removes the blocky periphery. Meta says it is available on all Quest devices and strongly recommended with Vulkan FFR. It requires FDM2. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S, Vulkan · Evidence: [doc]
  - Notes: The Oculus XR manual says it makes Timewarp more expensive and should be used only with FFR level 2 or higher (Q4-056). See Q3-C6.

- **Q3-042** Meta warns that with post-processing, subsampled layout can hurt performance, because intermediate passes are not foveated. Test with and without it. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: Vulkan, any pipeline with post-processing · Evidence: [doc] [verify on device]

- **Q3-043** Constraints on sampling a subsampled image. [T][C]
  - Mip count must be 1.
  - Samplers must be immutable and created with `VK_SAMPLER_CREATE_SUBSAMPLED_BIT_EXT`, `VK_FILTER_LINEAR`, `MIPMAP_MODE_NEAREST` and an LOD clamp of [0,0].
  - If the device does not support it, the flag is silently ignored.
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: Vulkan · Evidence: [doc]
  - Notes: Any Unity pass that reads the eye texture as a sampled texture falls under these rules, which is one reason pipelines with intermediates handle subsampled layout poorly.

- **Q3-044** Enabling it in Unity. [T][C]
  - Meta path: Vulkan plus Unity OpenXR 1.9.0+, via Project Settings > XR Plug-in Management > OpenXR > Android > Meta XR feature group > "Meta XR Subsampled Layout".
  - Unity OpenXR path: Foveated Rendering gear > "Subsampled Layout (Vulkan)", or at runtime `FoveatedRenderingFeature.TrySetSubsampledLayoutEnabled(true)` / `isSubsampledLayoutEnabled` (OpenXR 1.16.0+).
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-fixed-foveated-rendering/ ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/subsampledlayout.html (accessed 2026-09-24) · Applies to: Unity 6.0+ (OpenXR docs), 2022.3 via the Meta feature · Evidence: [doc]
  - Notes: The OpenXR doc notes that with AppSW, subsampled layout can add compositor GPU cost but may still improve overall performance. The Oculus XR setting is in Q4-056; version history is in Q4-058.

- **Q3-045** Toggle it on device with `adb shell setprop debug.oculus.foveation.subsampled 1|0`. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Use it for a no-rebuild A/B of GPU time and peripheral quality.

- **Q3-046** Unity issue 17355 (OXPB-153): with Subsampled Layout on Vulkan, Quest 3 shows corner artifacts in the right eye in MR. It reproduced on Quest 3 (Adreno 740) but not Quest 2 (Adreno 650), with Oculus XR 4.2.0, Unity 2022.3.33f1, Meta SDK 65 and URP. Last updated 2026-01-14; no fixed-in version listed. [C]
  - Source: https://issuetracker.unity.com/issues/17355 (accessed 2026-09-24) · Applies to: Quest 3, Oculus XR plugin, 2022.3 · Evidence: [doc] (Unity issue tracker, QA reproduced) [verify on device]
  - Notes: It is device-specific, so test subsampled layout on Quest 3 as well as Quest 2. Reproducing it sometimes needed an app relaunch.

- **Q3-047** No published ms or bandwidth saving exists for subsampled layout on any Quest. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] [verify on device]
  - Notes: To measure, keep FFR fixed with dynamic foveation off, toggle `debug.oculus.foveation.subsampled`, and compare app GPU time and compositor time (the compositor now does the upsample). Where available, compare the GPU memory read/write counters.

### 4.4 Dynamic resolution

- **Q3-048** Horizon OS Dynamic Resolution scales the rendered viewport from GPU utilisation. It lowers resolution when frames start going stale and raises it when the GPU has headroom. The eye textures are allocated once at the maximum scale, and only the viewport moves. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (updated Aug 6, 2026) (accessed 2026-09-24) · Applies to: Quest 2 and later · Evidence: [doc]
  - Notes: It is the OS-driven version of the pattern in Q3-012. It is also the gate for GPU level 5: see Q2-029 / Q2-050 / Q3-049 / Q4-006 in section 10.

- **Q3-050 / Q4-060 (part)** Setup in Unity. [T][C]
  - Tick OVRCameraRig > OVR Manager > "Enable Dynamic Resolution" and set the min/max scale. Per-device fields: `quest2Min/MaxDynamicResolutionScale` and `quest3Min/MaxDynamicResolutionScale`.
  - At runtime, set `OVRManager.instance.enableDynamicResolution`.
  - The maximum sets the eye-buffer allocation at startup: eye textures are allocated at the maximum scale factor, so a maximum above 1.0 costs memory.
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (Q3-050, Q4-060); https://developers.meta.com/horizon/reference/unity/v85/class_o_v_r_manager/ (Q3-050) (accessed 2026-09-24) · Applies to: Meta XR Core SDK, Unity 2021.3–6.6, URP, both stacks · Evidence: [doc]
  - Notes: Q3-050 found no published default min/max on the reference page. The SDK source gives them (Q2-024 / Q2-090; QX-C2). For Store compliance, a minimum below 0.85 makes you responsible for the VRC 85% expectation (Q1-087 / Q2-026 / Q3-003).

- **Q2-024 / Q2-090** Default dynamic-resolution ranges in OVRManager (SDK 1.207). [T]
  - Quest 2 and Quest Pro: min 0.7, max 1.3.
  - All other headsets, including Quest 3 and 3S (the default branch): min 0.7, max 1.6.
  - When dynamic resolution is enabled, OVRManager sets `XRSettings.eyeTextureResolutionScale` and the URP asset's `renderScale` to the maximum, so the eye textures are allocated at maximum scale.
  - Source: https://raw.githubusercontent.com/darktable-mirror/com.meta.xr.sdk.core/main/Scripts/OVRManager.cs (accessed 2026-09-24) · Applies to: Meta XR Core SDK 207 (GitHub mirror of the Meta package), Unity + Oculus XR or OpenXR; Quest 2/Pro/3/3S · Evidence: [doc] [verify on device]
  - Notes:
    - At 1.6 on Quest 3/3S the allocation is 2688x2816 per eye (arithmetic). Budget that memory, and lower `quest3MaxDynamicResolutionScale` if memory is tight; that field also governs 3S.
    - If 3S bandwidth really is lower (Q2-005), a 1.6 maximum may be optimistic on 3S.
    - The source is a mirror, so confirm against your installed package.
    - The same ranges appear on Meta's OVRCameraRig page (Q4-064) and in Q4-006's notes.

- **Q2-025 (part)** Dynamic-resolution minimum versions: Unity 2021.3.45f1, 2022.3.49f1 or 6000.0.25f1, with Oculus XR 3.3.0+ or OpenXR 1.12.1+. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (updated Aug 6, 2026) (accessed 2026-09-24) · Applies to: Unity 2021.3 to 6.x, all Quest · Evidence: [doc]
  - Notes: `SF` in logcat shows the current multiplier. The known URP issues and their fix versions are the next six findings.

- **Q3-051 / Q2-025 (part) / Q4-060 (part)** Meta says to disable dynamic resolution while profiling, because it changes the workload being measured. It is not a substitute for optimisation. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: The same applies to dynamic foveation (Q3-029). Profile with both off, then validate with both on.

- **Q3-031 / Q2-025 (part) / Q4-060 (part)** When dynamic foveation (FFR or ETFR) and dynamic resolution are both on, the runtime raises the foveation level first and lowers resolution only after that. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: Quest 2 and later · Evidence: [doc]
  - Notes: When diagnosing a blurry periphery, check `Fov=xD` (Q1-081 / Q3-028) before blaming resolution.

- **Q3-053 / Q2-025 (part) / Q4-060 (part)** Known issue: when the viewport is scaled, URP additional lights are misaligned. Forward+ shows blocky tiles; Deferred and Deferred+ drift. The fix is to tick Dynamic Resolution on the CenterEyeAnchor camera, or set `camera.allowDynamicResolution` before rendering. `_ScaledScreenParams` and `_ScreenSize` track the scaled viewport only when the camera has it enabled. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: URP with Meta Dynamic Resolution · Evidence: [doc]
  - Notes: In custom HLSL, derive screen UVs from `_ScaledScreenParams`, not `_ScreenParams`, or effects misalign when resolution changes.

- **Q3-054 / Q2-025 (part) / Q4-060 (part)** Known issue: the RenderObjects renderer feature gets the wrong viewport under dynamic resolution. With foveation, each RenderObjects pass is also split into its own Vulkan render pass even though it writes the same attachments, which costs performance. Fixed in 6000.0.81f1+, 6000.3.21f1+, 6000.5.6f1+, 6000.6.0b5+ and 6000.7.0a3+. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: Unity 6.x URP · Evidence: [doc]
  - Notes: On unfixed versions, every RenderObjects feature is an extra load/store round trip on Adreno. Check the render-pass count in RenderDoc or the Render Graph Viewer. The 6000.7.0a3 entry is the alpha reference behind QX-C3.

- **Q3-055 / Q2-025 (part)** Known issue: temporary render targets were reallocated on every scale change, which could run out of memory. Fixed in 6000.0.1f1+ and 2022.3.15f1+ (URP 14.0.9 or later). Workaround: `ScalableBufferManager.ResizeBuffers(scale, scale)`. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: 2022.3 before 15f1, early 6000.0 · Evidence: [doc]

- **Q3-056 / Q2-025 (part)** Known issue: URP added an extra intermediate render pass whenever the scale was not 1.0 (the `RequiresIntermediateColorTexture` / `isDefaultViewport` logic). Fixed in 6000.0.1f1+, 2022.3.22f1+ and 2021.3.36f1+. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: 2021.3 before 36f1, 2022.3 before 22f1 · Evidence: [doc]
  - Notes: On older patches, dynamic resolution can cost more than it saves because of the extra full-screen pass.

- **Q3-057 / Q2-025 (part) / Q4-060 (part)** Known issue: screen distortion on 6000.0.22f1 to 24f1, fixed in 6000.0.25f1. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: 6000.0.22f1–24f1 · Evidence: [doc]

- **Q3-058** The URP 14 line also fixed wrong copy-depth scaling with dynamic resolution (14.0.11, 2025-02-13), and added enforcement of consistent hardware dynamic-resolution settings during rendering (14.0.10, 2024-04-03). [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: Unity 2022.3 / URP 14 · Evidence: [doc]
  - Notes: 2022.3 projects using dynamic resolution with a depth texture should be on the latest patch.

- **Q3-059** OpenXR Automatic Viewport Dynamic Resolution. [T][C]
  - Requires Unity 6.3+, OpenXR 1.16.0+, URP 17.0.3+, Vulkan and a provider (Unity OpenXR Meta or Android XR).
  - Uses `XR_META_recommended_layer_resolution`.
  - Settings: Min Resolution Scalar (the effective floor is currently 0.5) and Max Resolution Scalar. The camera's "URP Dynamic Resolution" must be enabled.
  - Not supported in URP Compatibility Mode.
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/automaticdynamicresolution.html (accessed 2026-09-24) · Applies to: Unity 6.3+; listed devices Quest 2, Quest 3 and Android XR · Evidence: [doc]
  - Notes: API: `AutomaticDynamicResolutionFeature.IsAutomaticDynamicResolutionScalingSupported()` and `SetUsingSuggestedResolutionScale(bool)`. With Multiview Render Regions on, use the Final Pass mode rather than All Passes (Q3-088 / Q4-076). Quest 3S is not listed (Q3-C7).

- **Q3-060** OpenXR 1.18.0-pre.2 (2026-06-16) changed `GPUAppLastFrameTime` and `GPUCompositorLastFrameTime` to report seconds instead of milliseconds. Custom controllers that read these timings must account for it. [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: OpenXR 1.18+ · Evidence: [doc]
  - Notes: A home-made dynamic-resolution or foveation controller built on these values will be off by 1000x after the upgrade. The same applies to custom perf HUDs (section 9.8).

- **Q3-061** No published thresholds, step size or hysteresis exist for the Horizon OS dynamic-resolution controller. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] [verify on device]
  - Notes: To measure, log `SF`, GPU% and `Stale` from VrApi logcat at 1 Hz while ramping GPU load (for example with a shader-cost slider). Record the GPU% at which SF starts to fall and how fast it recovers.

### 4.5 Symmetric projection, Multiview Render Regions, tile hint, quad views

- **Q2-027 (part) / Q3-087 / Q4-072 / Q4-073** Symmetric Projection. [T]
  - It replaces the two asymmetric per-eye frusta with one wider shared frustum, widening the render target, so multiview geometry lands in matching tiles in both eyes.
  - FFR tile turn-off then discards the extra nasal-side tiles outside the original FOV. It uses `VK_QCOM_multiview_per_view_render_areas`.
  - Meta reports a typical 5–15% GPU gain when GPU-bound, largest in geometry-heavy or draw-call-heavy scenes. It says the visual difference is imperceptible and recommends it for most apps.
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-symmetric-projection/ (updated Apr 6, 2026; Q3-087, Q4-072, Q4-073); https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (Q2-027, Q4-072) (accessed 2026-09-24) · Applies to: Quest 2/3/3S; Vulkan + Multiview; Oculus XR 3.0.0+ or OpenXR 1.9.1+ (Multiview enforced from OpenXR 1.13.0) · Evidence: [doc]; Q3-087 tags the 5–15% as [measured] (a Meta-published range) [verify on device]
  - Notes:
    - Quantise the widened size to multiples of 16, and pair it with `XR_META_recommended_layer_resolution`.
    - It can hurt with heavy post-processing: intermediate passes are not foveated, so the extra pixels are shaded and resolved there (Q4-C6). Test with and without.
    - Profile both ways if custom shaders depend on per-eye asymmetry.
    - In Unity it is Meta Quest Support > "Symmetric Projection (Vulkan)". The black right-edge pixels in Meta's FFR maps come from it.
    - For MR apps with post-processing off (Q4-015), the post-processing risk mostly goes away.

- **Q2-027 (part) / Q4-074** Multiview Render Regions (MVRR) builds on Symmetric Projection. The symmetric eye buffers contain edge regions outside the visible frustum, and MVRR uses render-region hints to tell the driver to skip shading, storing and bandwidth for them. The typical gain is 3–8% when GPU-bound, highest with forward rendering and expensive fragment shaders. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S; Vulkan; Unity 6.1+ · Evidence: [doc] [verify on device]
  - Notes: It can regress with very simple shaders, minimal overdraw, or drivers that handle regions poorly. The percentages are Meta's typical ranges, not guarantees. No Unity-URP-specific saving is published (Q3-088 / Q4-076 notes).

- **Q3-088 / Q4-076** MVRR prerequisites. [T]
  - Unity 6.1+ and Vulkan, with multiview plus Symmetric Projection.
  - "All Passes" only on Unity 6.2+ with OpenXR 1.15+. Unity 6.3+ requires render graph for both modes.
  - Plugins: Oculus XR 4.6+ (but see Q4-C2) or OpenXR 1.14+.
  - Setting path: OpenXR > Meta Quest Support > Multiview Render Regions Optimizations, or Oculus > Optimize Multiview Render Regions.
  - The Oculus toggle and the OpenXR 1.14 toggle apply MVRR to the final (eye-texture) pass only. So on the deprecated Oculus stack, MVRR does nothing once post-processing or an intermediate texture is in use.
  - Custom passes must be flagged `MultiviewRenderRegionsCompatible`. With Automatic Dynamic Resolution, use Final Pass mode.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/xr-multiview-render-regions.html (Q3-088); https://docs.unity3d.com/6000.6/Documentation/Manual/xr-multiview-render-regions.html (Q4-076, built 2026-09-24); https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/automaticdynamicresolution.html (Q3-088) (accessed 2026-09-24) · Applies to: Unity 6.1–6.6 · Evidence: [doc]
  - Notes: No published ms saving for MVRR in Unity URP was found; measure with an A/B of GPU time. Unity 6.6 guidance lists MVRR among the settings to enable for untethered XR (Q3-093 / Q4-053).

- **Q4-075** MVRR modes. [T][C]
  - All Passes (recommended) applies the regions to every pass.
  - Final Pass applies them only to passes that write the eye textures.
  - Switch to Final Pass if bloom, depth of field, motion blur or large-kernel blurs show clipped edges.
  - Final Pass gives no gain when the pipeline renders through intermediate textures or post-processing.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-multiview-render-regions.html (accessed 2026-09-24) · Applies to: Unity 6.1+ (All Passes needs 6.2+); Vulkan · Evidence: [doc]

- **Q4-077** In Unity 6.3+, only render-graph passes marked compatible get All Passes treatment. [T]
  - URP passes marked compatible: CopyDepthPass, DecalScreenSpaceRenderPass, DepthNormalOnlyPass, DepthOnlyPass, DrawObjectsPass, DrawSkyboxPass, FinalBlitPass, MotionVectorRenderPass, PostProcessPassRenderGraph, RenderObjectsPass, TemporalAA, XRDepthMotionPass, XROcclusionMeshPass.
  - Custom raster passes opt in by calling the render-graph `SetExtendedFeatureFlags(ExtendedFeatureFlags)` method with `MultiviewRenderRegionsCompatible`.
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-multiview-render-regions.html (accessed 2026-09-24) · Applies to: Unity 6.3–6.6, URP render graph · Evidence: [doc]
  - Notes: A custom pass without the flag (for example a custom occlusion or passthrough-alpha pass in a ScriptableRenderPass) drops out of All Passes. Audit custom renderer features.

- **Q3-089** `XR_META_tile_properties_hint` with `VK_QCOM_tile_properties` makes the runtime return tile-aligned recommended resolutions (through `XR_META_recommended_layer_resolution`) and tile-aligned FDMs. Unity OpenXR enables it automatically from 1.17.0-pre.1. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-tile-properties-hint/ (updated Apr 7, 2026); https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: OpenXR 1.17+, Vulkan · Evidence: [doc]
  - Notes: With a manual render scale, sizes that are not tile-aligned leave partly filled bins. No published cost figure exists; the symmetric-projection sample rounds to multiples of 16. Q4-058 lists the extension under OpenXR 1.17.0-pre.1 only.

- **Q3-090** Quad Views (`XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO_WITH_FOVEATED_INSET`) renders four views, two low-resolution wide and two inset, for about 50% fewer pixels. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-stereo-with-foveated-inset/ (updated Sep 14, 2026) (accessed 2026-09-24) · Applies to: Horizon OS v85+ when required=true; Quest 2/3/3S · Evidence: [doc] [verify on device]
  - Notes:
    - It needs the manifest feature `com.oculus.feature.QUAD_VIEWS`; required=true restricts the app to Horizon OS v85+.
    - It is meant to be rendered as two multiview-2 passes and must not be combined with FFR.
    - Without eye tracking the inset is fixed at the centre.
    - The Unity OpenXR option was added in 1.17.0-pre.2, and it is incompatible with dynamic foveation.
    - The extra geometry pass means a pixel saving is not a GPU-time saving in vertex-heavy scenes, so measure.
    - Gap-fill round 1: the OpenXR changelog shows that 1.17.0-pre.2 changed how Single Pass Instanced renders when Quad Views is enabled, and 1.18.0-pre.1 (2026-06-02) added and documented the user-facing Quad Views option. Treat OpenXR 1.18.0 as the first release with the documented option (QUEST-GF1-C4).

- Cross-references: Optimize Buffer Discards (memoryless MSAA): Q2-027 (part) / Q4-059 (section 8). Symmetric Projection and MVRR with passthrough and Depth API: Q4-078 (section 7).


---

### 4.6 Compositor-side sharpening, supersampling and super resolution

- **Q3-015** By default the compositor resamples layers bilinearly. `XR_FB_composition_layer_settings` adds four suggestion bits:
  - NORMAL_SUPER_SAMPLING: 2 taps, with the pattern alternating per frame to approximate 4 taps.
  - QUALITY_SUPER_SAMPLING: 4 taps, no temporal component.
  - NORMAL_SHARPENING: 3 taps approximating 5.
  - QUALITY_SHARPENING: Meta Quest Super Resolution (MQSR).

  If both bits of a pair are set, the normal variant wins. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-openxr-composition-layer-filtering/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S, OpenXR · Evidence: [doc]
  - Notes: These are suggestions, and the compositor may ignore them. Supersampling helps layers whose texture PPD is above display PPD (minification shimmer). Sharpening helps layers whose texture PPD is at or below display PPD.

- **Q3-016** Auto filtering lets the compositor choose per layer from layer PPD against display PPD, GPU utilization and visibility. When no filter is needed it is a no-op with no overhead. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-openxr-composition-layer-filtering/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: This is the safer default than forcing the "quality" variants on every layer.

- **Q3-017** MQSR is a single-pass, edge-aware spatial upscaler and sharpener built on Snapdragon Game Super Resolution. Its cost depends on content (more fine detail costs more) and it adds to compositor (TimeWarp) GPU time. Meta says to weigh it against simply raising eye-buffer resolution. It can add temporal aliasing when the content is already near display resolution. [T][C]
  - Source: https://developers.meta.com/horizon/blog/vr-image-quality-meta-quest-super-resolution/ (accessed 2026-09-24) · Applies to: Quest 2/Pro at publication; Quest 3/3S not covered · Evidence: [doc] [verify on device]
  - Notes: The blog is dated Jul 10, 2023, so it predates Quest 3 tuning. MQSR replaced the old "quality" sharpening in v55, and "normal" sharpening (RCAS) was optimized in v53. Meta claims up to 2x faster than the Link Sharpening+ quality path on Quest 2/Pro, which is a relative figure only.

- **Q3-018** MQSR does not support YUV or cubemap layers, which fall back to bilinear. It supports subsampled textures from runtime v56. [C]
  - Source: https://developers.meta.com/horizon/blog/vr-image-quality-meta-quest-super-resolution/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]

- **Q3-019** In Unity, the projection (eye-buffer) layer filter is set through `OVRManager.sharpenType` (`OVRPlugin.LayerSharpenType`). Per-layer filtering is set on OVROverlay with the Super Sample and Sharpen dropdowns (a normal and a more expensive variant each) plus an Auto Filtering option. [T]
  - Source: https://developers.meta.com/horizon/reference/unity/v85/class_o_v_r_manager/ and https://developers.meta.com/horizon/documentation/unity/unity-ovroverlay/ (accessed 2026-09-24) · Applies to: Meta XR Core SDK v85 · Evidence: [doc]

- **Q3-020** No published ms cost exists for MQSR, sharpening, supersampling or bicubic filtering on Quest 2, 3 or 3S. [T]
  - Source: https://developers.meta.com/horizon/blog/vr-image-quality-meta-quest-super-resolution/ and https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc] [verify on device]
  - Notes: To measure, fix CPU/GPU levels and keep the scene static. A/B the flag and compare the compositor time (VrApi `TW=` field, or compositor GPU time in OVR Metrics and the MQDH Performance Analyzer). Record per device, because compositor cost scales with panel resolution.

- **Q3-091** On the Meta Quest Support settings page, the System Splash Screen is shown as a compositor layer. [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html (accessed 2026-09-24) · Applies to: OpenXR · Evidence: [doc]
  - Notes: It stays smooth while the first scene loads, which avoids a judder at startup.

## 5. Application SpaceWarp (AppSW)

- **Q2-079** App SpaceWarp (AppSW) lets the app render at half the refresh rate while the compositor synthesizes frames from motion vectors and depth. Meta cites up to 70% more GPU headroom, and it is VRC-compliant at half rate. `VSnc=0` and an `ASW=` logcat line indicate it is active. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Implementation details (URP motion vectors, formats) belong to another topic. It is not automatic; it must be integrated.

- **Q3-062** AppSW renders the app at half the display rate (for example 36 fps for a 72 Hz display). The compositor synthesizes the other frames from the app's motion vectors and depth. Meta cites up to 70% more compute available to the app, and Unity calls that the best case. AppSW can be turned on or off per frame. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ and https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html (accessed 2026-09-24) · Applies to: Quest 2/3/3S, Vulkan · Evidence: [doc]
  - Notes: The native page was updated Aug 16, 2024. Budget per rendered frame at half rate: 72 Hz gives 27.8 ms, 90 Hz gives 22.2 ms and 120 Hz gives 16.7 ms (arithmetic from the budgets). The compositor's own cost still runs at full rate. Unity says it does not work at about 18 fps or below.

- **Q3-063** The motion-vector pass renders into a small target: on Quest 2 a 1440x1584 eye buffer pairs with a 368x400 MV target, which Meta calls almost free. AppSW memory is about 18 MB total on Quest 3 (about 5.5 MB system plus 13.5 MB swapchains) and about 14 MB on Quest 2. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ and https://developers.meta.com/horizon/documentation/unity/unity-asw/ (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]
  - Notes: No published ms cost exists for the MV pass. It is still a second geometry pass over every MV-writing object, so it costs vertex and binning time. To measure, compare GPU time with AppSW forced on at full rate against off, or use a RenderDoc capture of the MV pass. The MV depth is also sent to the compositor for Positional TimeWarp.

- **Q3-064** Meta-path requirements:
  - Vulkan only, and OpenXR OVRPlugin v34+.
  - Unity OpenXR Plugin (recommended from Meta SDK v74) or the deprecated Oculus XR Plugin.
  - Unity 2022.3.15f1+, 6000.0.9f1+ or 6000.4.0f1+ (these are minimums; Meta recommends the latest stable Unity release; corrected in gap-fill round 1).
  - Meta's URP fork (Oculus-VR/Unity-Graphics). Branches: `2022.3/14.0.8-oculus-app-spacewarp` (2022.3.11–17), `…14.0.9…` (18–23), `…14.0.10…` (24+), `6000.0/oculus-app-spacewarp` (6000.0.9–6000.3.x) and `6000.4/oculus-app-spacewarp`.
  
  [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-asw/ (accessed 2026-09-24) · Applies to: Unity 2022.3, 6.0–6.4+ · Evidence: [doc]
  - Notes: The page was updated May 13, 2026. Meta says stock URP supports SpaceWarp from 6000.0.9f1 with RenderGraph, but its fork is still recommended for extra optimizations and transparent-object support (see Q3-C3). Enable it with OpenXR "Meta XR Space Warp", or on Oculus XR with "Application SpaceWarp (Vulkan)" under Android Experimental.

- **Q3-065** Unity-native path requirements:
  - Unity 6.1+ (6000.1.13f1+ for right-handed NDC), OpenXR 1.11.0+ (1.15.1+ for right-handed NDC), URP 17.0.3+ with RenderGraph (not Compatibility Mode), Vulkan and a provider package.
  - Enable OpenXR > "Application SpaceWarp", which has a gear option "Use Right Handed NDC".
  - Runtime: `SpaceWarpFeature.SetSpaceWarp(bool)`, plus per-frame `SetAppSpacePosition(...)` and `SetAppSpaceRotation(...)` from the tracking origin.
  
  [T][C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-prerequisites.html and https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp.html (accessed 2026-09-24) · Applies to: Unity 6.1–6.6 · Evidence: [doc]
  - Notes: Unity says the Meta fork is no longer required from URP 17.0.3 (6.2 manual). OpenXR 1.15.1 (2025-07-23) made developers choose right-handed or left-handed NDC explicitly. A mismatch is a likely cause of wrong warps [verify on device].

- **Q3-066** For stock URP (Unity-native path), custom shaders need:
  - a `_XRMotionVectorsPass` property;
  - a Pass with LightMode "XRMotionVectors" that writes stencil Ref 1;
  - the `APPLICATION_SPACE_WARP_MOTION` keyword;
  - an include of ObjectMotionVectors.hlsl.
  
  Supported built-ins are Lit, Unlit, Complex Lit, Simple Lit, Baked Lit and Shader Graph Lit/Unlit, each with the material toggle "XR Motion Vectors Pass (Space Warp)" under Advanced Options. [C]
  - Source: https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html and https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-shaders.html (accessed 2026-09-24) · Applies to: Unity 6.1+ URP 17 · Evidence: [doc]
  - Notes: Objects without the pass get no motion vectors, so they are warped only by head motion and smear when they move.

- **Q3-067** On the Meta fork path, `OculusMotionVectorPass` filters on `LightMode=MotionVectors`, not XRMotionVectors. The MV pass and the eye pass must use matching matrices and the same late-latching state. Gate any extra work on `cameraData.xr.motionVectorRenderTargetValid`. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-asw/ (accessed 2026-09-24) · Applies to: Meta URP fork branches · Evidence: [doc]
  - Notes: Shaders written for one path's LightMode will be skipped on the other. Pick one path per project and audit every custom shader, including Shader Graph targets.

- **Q3-068** Motion Vector Generation Mode:
  - Use Per Object Motion for moving opaques.
  - Use Camera Motion Only (2022.3+) for static meshes. It reuses depth and needs depth submission (16- or 24-bit on OpenXR; "Depth Submission (Vulkan)" on Oculus XR).
  
  OpenXR 1.14.2 (2025-03-20) fixed depth submission corrupting the spacewarp depth texture. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-asw/ and https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: Unity 2022.3+, OpenXR · Evidence: [doc]
  - Notes: Camera Motion Only on statics cuts MV-pass draw calls. On OpenXR versions before 1.14.2, expect depth-related warp errors.

- **Q3-069** Meta calls "Optimize Buffer Discards (Vulkan)" very important for AppSW performance. It makes 4x MSAA textures memoryless and was added in OpenXR 1.10.0. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-asw/ and https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html (accessed 2026-09-24) · Applies to: OpenXR 1.10.0+, Vulkan · Evidence: [doc]

- **Q3-070** The Space Warp motion-vector texture format is set in Meta Quest Support settings: RGBA16f for precision or RG16f for memory. The option was added in OpenXR 1.14.0. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html (accessed 2026-09-24) · Applies to: OpenXR 1.14.0+ · Evidence: [doc]

- **Q3-071** Content AppSW handles badly:
  - Transparency (only one motion vector per pixel), so transparents, particles and unsupported shaders are not warped correctly.
  - Clean or high-contrast backgrounds, which show distortion.
  - Very fast rotation.
  - Near-field controllers.
  - Complex vertex animation. The workaround is to use the current position as the previous position.
  
  [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ and https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: AppSW trades throughput for visual consistency. Use it for GPU-heavy, slow-motion content, and turn it off per frame for fast combat or hand-close interactions if artifacts show.

- **Q3-072** UI with AppSW:
  - Unity 6.5+ supports uGUI and TMP. Enable Canvas Additional Shader Channels "Previous Position" and use SpaceWarp-compatible UI shaders: UI-Default, UI-DefaultETC1, UI Unlit Detail, and TMP "Mobile/Distance Field With SpaceWarp Compatibility".
  - Before 6.5, UI takes the motion vectors of whatever is behind it. The workaround is a URP/Unlit quad with the MV pass behind a World Space canvas.
  - Screen-space UI is incompatible.
  - On the Meta fork, use alpha-clipped MV for UI and text. Transparents need `RenderQueueRange.opaque` changed to `.all`.
  
  [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-ui.html and https://developers.meta.com/horizon/documentation/unity/unity-asw/ (accessed 2026-09-24) · Applies to: Unity 6.1+ (Unity-native), Meta fork · Evidence: [doc]
  - Notes: Meta's alternative is to put HUD UI on compositor layers (Q3-078, Q3-086).

- **Q3-073** With AppSW, Phase Sync and Positional TimeWarp are automatic; without AppSW the compositor's TimeWarp corrects rotation only. Meta advises enabling Late Latching and warns that controller latency can still be higher. [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ and https://developers.meta.com/horizon/documentation/native/android/os-compositor/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]

- **Q3-074** AppSW diagnostics:
  - VrApi logcat shows `FPS=36/72` with `ASW=72, Type=App`. OVR Metrics shows FPS, ASW FPS and ASW TYPE.
  - Motion-vector overlay: `adb shell setprop debug.oculus.spaceWarpDebug 1`, then `debug.oculus.MVOverlay 4` and `debug.oculus.MVOverlay.Alpha 0.8`, then two power-button presses. MVOverlay modes: 1 = MV, 2 = depth, 3 = MV amplified, 4 = amplified with gray at zero.
  - To force half rate for testing: `debug.oculus.sysPropDebug 1` plus `debug.oculus.swapInterval 2`.
  
  [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ and https://developers.meta.com/horizon/documentation/unity/unity-asw/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Objects that show gray (zero motion) in mode 4 while moving are missing an MV pass.

- **Q3-075** `OVRManager.SetSpaceWarp(true)` has to be called again whenever the main camera changes, for example after a scene or rig swap. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-asw/ (accessed 2026-09-24) · Applies to: Meta XR SDK · Evidence: [doc]
  - Notes: A silent drop back to full-rate rendering after a scene load is the typical symptom. Check `ASW=` in logcat after each transition.

- **Q3-076** AppSW runs on one compositor layer only (the projection layer). [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]

- **Q3-077** No published number exists for AppSW gains at 90 Hz (45 fps rendering) or 120 Hz (60 fps) on Quest 3/3S, or for Quest 3S versus Quest 3 behaviour. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes: To measure, fix CPU/GPU levels and compare app GPU time and stale-frame counts with AppSW off at the full refresh rate against AppSW on at half rate. Also compare compositor time (TW), because it grows with AppSW.

- **QUEST-GF2-007** Meta's GDC 2024 Quest 3 guidance: with AppSW, "expect 30%" of the new (doubled) frame time to go to generating motion vectors. It also names transparency and fast-moving held objects as the main artifact sources. [T]
  - Source: https://developers.meta.com/horizon/blog/optimizing-for-success-meta-quest-3-gdc/ (Meta blog recap of a GDC 2024 talk, Mar 21, 2024) (accessed 2026-09-24) · Applies to: Quest 3 (blog scope); AppSW on any engine · Evidence: [doc] (blog) [verify on device]
  - Notes: This is the only Meta number found for the motion-vector cost. It is a planning figure, not a measurement with a stated setup. It lines up with "up to 70% extra compute" (Q3-062 / Q2-079: 100% − 30%), but conflicts with the native page calling the low-res MV pass "almost free" (Q3-063) (QUEST-GF2-C3). The real cost depends on how many objects write motion vectors and on skinning. Measure the MV pass directly in RenderDoc Meta Fork, or as the App GPU delta with AppSW on and off at locked levels.

## 6. Compositor layers for UI and text

- **Q3-078** Compositor layers are sampled once, directly by the compositor, instead of being rendered into the eye buffer and then resampled again in distortion. They are displayed at the compositor frame rate, but support no custom pixel shaders or lighting. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: The page was updated Mar 11, 2025. Layers are the tool for text and UI clarity at a lower eye-buffer scale, and they stay smooth when the app misses frames.

- **Q3-079** Layer costs measured on Quest 2 at CPU/GPU level 4:
  - About 0.1 ms per additional layer. Head-locked FIXED_TO_VIEW quad layers are merged at no extra cost.
  - About 0.6 ms for a fullscreen layer, even when it is fully occluded or shows 0 alpha.
  
  [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/ (accessed 2026-09-24) · Applies to: Quest 2 (measured); Quest 3/3S not published · Evidence: [measured] [verify on device]
  - Notes: Layer cost scales with screen coverage, not visible content. A mostly transparent fullscreen UI layer is a bad trade. Crop layers to their content bounds.

- **Q3-080** The native compositor draws up to 16 layers per frame and drops any beyond that. The Unity OVROverlay page says 15 per scene, with at most one cylinder and one cubemap. [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/ and https://developers.meta.com/horizon/documentation/unity/unity-ovroverlay/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: The likely reason for the 15/16 difference is that the eye-buffer projection layer takes one slot (Q3-C1). When a layer cannot be created, only quads fall back to scene geometry; cylinders and cubemaps simply disappear. Combine planar UI into one RenderTexture.

- **Q3-081** Underlays are more bandwidth-heavy than overlays, because the eye buffer has to punch an alpha hole for them (Underlay Transparent Occluder / Underlay Impostor shaders). OVROverlayCanvas has a DrawMode setting: Opaque, OpaqueWithClip, Transparent (the default) or AlphaToMask. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-ovroverlay/ (accessed 2026-09-24) · Applies to: Meta XR SDK · Evidence: [doc]
  - Notes: The page was updated Aug 28, 2026. Prefer overlays, and prefer Opaque or OpaqueWithClip canvases where the design allows.

- **Q3-082** Bicubic layer filtering is done in hardware, falls back to bilinear where unavailable, and costs more, especially when combined with trilinear. The cost shows up in composition timing. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-ovroverlay/ (accessed 2026-09-24) · Applies to: Meta XR SDK · Evidence: [doc]

- **Q3-083** Layer diagnostics:
  - VrApi `TW=` includes layer composition cost. `LCnt=5(DR14,LM2)` gives the layer count, where LM is the number of merged layers.
  - `adb shell setprop debug.oculus.logLayers 1` plus `adb logcat -s CompositorClient` lists layers and flags (for example APP_SPACE_WARP).
  - `debug.oculus.visualizeLayers 1` tints layers on screen.
  - MQDH Performance Analyzer can toggle layer visibility.
  
  [T][C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]

- **Q3-084** The CLP logs report, per layer, DevicePPD (20.67 on Quest 2), LayerRenderedPPD, texture resolution, recommended texture resolution, and a recommended filter (Sharpening, SuperSampling or None). Enable them with `debug.oculus.sysPropDebug 1`, a double power press, then `debug.oculus.layerProperties 1`, and read `adb logcat -s CompositorVR`. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: This is the objective way to size layer textures (to cut memory and bandwidth) and pick filter flags per layer instead of guessing. The device PPD for Quest 3/3S was not published on the page; read it from the log.

- **Q3-085** On the Unity OpenXR path, install the XR Composition Layers package and enable "Composition Layer Support" in OpenXR. Custom layer types go through `OpenXRCustomLayerHandler<T>`. OpenXR 1.18.0-pre.1 added per-eye composition layers. 1.19.0-pre.1 added Dynamic Texture (which needs XR Composition Layers 2.6.0) and moved layer texture transfer to CopyTexture. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/compositionlayers.html and https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: Unity 6.x with OpenXR · Evidence: [doc]
  - Notes: The CopyTexture per update is a per-frame GPU copy for dynamic layers, so keep dynamic layers small. No layer-count limit specific to the package on Quest was found; assume the runtime limit from Q3-080.

- **Q3-086** Unity's SpaceWarp docs list composition layers among the things that are not warped. Meta's native AppSW page says Compositor Layer SpaceWarp smooths layer motion and recommends layers for HUD UI under AppSW. [C]
  - Source: https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html and https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ (accessed 2026-09-24) · Applies to: AppSW with layers · Evidence: [doc] [verify on device]
  - Notes: See Q3-C9. Most likely, layer content gets no app motion vectors, while the compositor reprojects the layer pose. Verify with the MV overlay plus a moving world-locked quad.

- **QUEST-GF2-008** The only Meta figure for compositor-layer pixel cost beyond the Quest 2 L4 numbers comes from the Spatial SDK runtime guidelines (updated Oct 6, 2025): panel GPU cost scales at about 1% GPU per 480,000 panel pixels, with a budget of about 48 million panel pixels at 90 FPS. The headset model is not stated. [T]
  - Source: https://developers.meta.com/horizon/documentation/spatial-sdk/spatial-sdk-runtime-guidelines/ (accessed 2026-09-24) · Applies to: Meta Spatial SDK apps (out of engine scope); device unspecified · Evidence: [doc] [verify on device]
  - Notes: Use it only as an order-of-magnitude prior for Unity OVROverlay or XR Composition Layers texel counts. Spatial SDK panels are not guaranteed to go through the same compositor path, and the page does not say whether "GPU %" is app or compositor GPU. No Quest 3/3S per-layer ms figure exists in the compositor-layers page (re-checked, still dated Mar 11, 2025) or in the MQDH layer-tools blog (Jan 13, 2025). The Quest 3/3S layer cost stays unresolved.

## 7. Quest 3/3S mixed-reality costs

### 7.1 Passthrough: clock ceilings, compositing and cost

- **Q2-038** Passthrough (mixed reality) cuts the available levels on Quest 3/3S: CPU level 4 is lost (max 3, 1.65 GHz instead of 1.92) and GPU levels 3 and 4 are lost (max 2, 456 MHz instead of 545). Budget mixed-reality modes as a separate, lower tier. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [doc] [verify on device]
  - Notes: The clock drop from GPU L4 to L2 is about 16% (arithmetic). This is on top of the passthrough composition cost in Q2-006. GPU level 5 requires GPU level 4 to be available, so it is also lost. Confirm with the `CPU4/GPU=` levels in logcat during MR.

- **Q4-001** On Quest 3 and 3S, an app that enables passthrough loses CPU level 4 and GPU levels 3–4. CPU levels 0–3 and GPU levels 0–2 remain always available. This is the main, documented way passthrough costs an app throughput: a lower clock ceiling, not a line item in the app's GPU time. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24; page updated Sep 2, 2026)
  - Applies to: Quest 3 and Quest 3S. This is an OS policy, so it applies to every Unity version and to both the Oculus XR and OpenXR stacks.
  - Evidence: [doc] [verify on device]
  - Notes: The condition is worded "does not enable passthrough features". The page does not say whether turning passthrough off at runtime (`OVRManager.isInsightPassthroughEnabled = false`) brings levels 3–4 back. To check on device: in the OVR Metrics Tool overlay, watch the CPU L and GPU L values while toggling passthrough in a GPU-bound scene.

- **Q4-004** Passthrough apps on Quest 3/3S cannot reach CPU L5 through level trading. CPU L5 needs CPU L4 to be available and trading set to −1, and passthrough removes L4. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ ; https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S. Level trading exists only on these two headsets and needs OVRPlugin's OpenXR backend, not the legacy OVRPlugin backend.
  - Evidence: [doc]
  - Notes:
    - Trading is set at build time through the manifest entry `com.oculus.trade_cpu_for_gpu_amount` (1, 0 or −1). In Unity it is the "Processor Favor" setting on OVRManager.
    - To confirm, logcat shows `CreateClient: Value of tradeCpuForGpu is 1`.

- **Q4-005** Default `ProcessorPerformanceLevel.SustainedHigh` requests CPU level 4 (range 4–4) and GPU levels 3–5 on Quest 3/3S. On a passthrough app, CPU L4 and GPU L3–4 are unavailable, and GPU L5 availability is unclear (Q4-C1). The doc does not say which level the OS actually grants. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S, both stacks. The APIs are `OVRPlugin.suggestedCpuPerfLevel` / `suggestedGpuPerfLevel` and, on OpenXR, `XrPerformanceSettings.SetPerformanceLevelHint` (Unity OpenXR 1.11.0+).
  - Evidence: [doc] [verify on device]
  - Notes: The other ranges are PowerSavings 0–4/0–4, SustainedLow 2–4/1–4, and Boost 4–max/3–5. Log the level the app actually gets at runtime (OVR Metrics "CPU L/GPU L", or logcat VrApi/XrPerformanceManager lines). Don't assume the requested range.

- **Q4-010** Passthrough is rendered by a separate system service into a compositor layer, and the app never sees the camera pixels. The passthrough render cost therefore never appears in the app's GPU timings, whether from the Unity profiler or from a GPU render-stage trace. What the app does see is the level ceilings (Q4-001) and the compositor work. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S, both stacks.
  - Evidence: [doc]
  - Notes: For diagnosis, "GPU-bound only in MR" usually means the ceiling dropped, not that shaders got slower. Compare GPU% at the same GPU L before optimizing content.

- **Q4-011** An app can have at most 3 passthrough layers. Every layer adds a non-trivial overhead, so use as few as possible, ideally one. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-bp/ ; https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S, both stacks (`XR_FB_passthrough`).
  - Evidence: [doc]
  - Notes: No per-layer cost is published.

- **Q4-012** In Unity, keep one `OVRPassthroughLayer` alive across scenes (a DontDestroyOnLoad owner) instead of creating one per scene. Enabling passthrough is asynchronous and the cameras take a few hundred milliseconds to start. Gate reveals on the `passthroughLayerResumed` event so there is no black frame or flicker. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-passthrough-gs/ (accessed 2026-09-24; updated Apr 9, 2026)
  - Applies to: Meta XR Core SDK (OVRPassthroughLayer) on either plugin.
  - Evidence: [doc]
  - Notes: Known issue from the v203 release notes: `passthroughLayerResumed` does not fire over Link; it is scheduled to be fixed in v204 (https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/203.0/).

- **Q4-013** When passthrough isn't needed for an extended period, disable it to save resources. In Unity use `OVRPassthroughLayer.enabled = false` or `OVRManager.isInsightPassthroughEnabled = false`. Re-enabling carries a creation delay, so toggle at scene transitions. In native code, pause the layer with `xrPassthroughLayerPauseFB` rather than just skipping its submission. Pausing is cheaper than destroying the layer but can keep resources allocated. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-passthrough-bp/ ; https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-bp/ ; https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S, both stacks.
  - Evidence: [doc]
  - Notes: `XR_PASSTHROUGH_IS_RUNNING_AT_CREATION_BIT_FB` starts environment reconstruction as soon as the layer is created. Schedule that during a loading beat.

- **Q4-014** Underlay compositing contract:
  - Environment blend mode must be OPAQUE.
  - The passthrough layer is submitted before the projection layer.
  - The projection layer blends by source alpha (`XR_COMPOSITION_LAYER_BLEND_TEXTURE_SOURCE_ALPHA_BIT`).
  - Unity with the Core SDK: set the Lighting Skybox Material to None and the camera background to (0,0,0,0).
  - Unity OpenXR: Meta: use the "Meta Quest: Camera (Passthrough)" feature plus an AR Camera Manager (enabling or disabling the component toggles passthrough). Its passthrough composition layer uses order −1 with alpha blend. [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough/ ; https://developers.meta.com/horizon/documentation/unity/unity-passthrough-gs/ ; https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/camera/passthrough.html (accessed 2026-09-24)
  - Applies to: all devices. The OpenXR: Meta path needs Unity 6+.
  - Evidence: [doc]
  - Notes: Premultiplied alpha is assumed unless `XR_COMPOSITION_LAYER_UNPREMULTIPLIED_ALPHA_BIT` is set. Wrong alpha shows up as haloing, not as a performance cost.

- **Q4-015** Unity OpenXR: Meta says the default URP settings do not give optimal passthrough performance. Its recommended settings:
  - Graphics API: Vulkan.
  - URP Asset: Terrain Holes off, HDR off.
  - Universal Renderer: Post-processing off, Intermediate Texture = Auto. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/get-started/graphics-settings.html (accessed 2026-09-24)
  - Applies to: Unity 6+ with com.unity.xr.meta-openxr 2.x, URP. The same URP choices apply on the Core SDK path.
  - Evidence: [doc]
  - Notes (inference, not stated on the page): HDR off and no post-processing also let URP skip the intermediate color target, so it renders straight to the eye texture. That saves a full-screen resolve.

- **Q4-016** On Quest 3/3S in flicker-free lighting, running at 72 Hz makes passthrough sync its cameras to the display, which gives stable latency and no judder. The trade-off is a 13.9 ms frame budget instead of 11.1 ms at 90 Hz. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-passthrough-bp/ (accessed 2026-09-24; updated Dec 9, 2025)
  - Applies to: Quest 3 and 3S.
  - Evidence: [doc]
  - Notes: On OpenXR: Meta, set the rate with `TryGetSupportedDisplayRefreshRates` / `TryRequestDisplayRefreshRate` (Display Utilities, https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/display-utilities.html). On the Core SDK path, use its display-frequency API (e.g. `OVRPlugin.systemDisplayFrequency`; not re-checked in this pass).

- **Q4-017** Passthrough color LUT costs:
  - Maximum LUT resolution is 64. Resolution drives both memory and GPU cost; start at 16 and stay at 32 or below.
  - Creating a LUT at resolution 64 takes a few ms, so create it ahead of time.
  - Updating a high-resolution LUT every frame has a notable cost. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-customization/ (accessed 2026-09-24)
  - Applies to: all devices; `XR_META_passthrough_color_lut`. Unity's color LUT styling wraps the same extension [verify on device].
  - Evidence: [doc]

- **Q4-018** A separate alpha-mask passthrough layer adds significant overhead. The cheapest way to do selective passthrough is to punch holes in the app's own eye-buffer alpha. In Unity, that means the Core SDK "Selective Passthrough" shader/material, for example on an MRUK EffectMesh. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-customization/ ; https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manipulate-scene-visuals/ (accessed 2026-09-24)
  - Applies to: all devices, both stacks.
  - Evidence: [doc]

- **Q4-019** `OVRManager.IsPassthroughRecommended()` (native `XR_META_passthrough_preferences`) reports whether the user's system prefers MR. An app that starts in VR mode when MR isn't preferred never enables passthrough, so it keeps the full CPU L4 / GPU L3–4 range on Quest 3/3S. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-passthrough-gs/ ; https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S (the MR-first devices), Core SDK.
  - Evidence: [doc] [verify on device]
  - Notes: Whether the full range really comes back depends on the Q4-001 open question: the passthrough feature may still be declared in the manifest.

- **Q4-021** No published number found for passthrough's per-frame GPU time, memory or bandwidth on Quest 3/3S, apart from the 2023 budget statement in Q4-002. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-passthrough-bp/ ; https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-bp/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S.
  - Evidence: [doc] [verify on device]
  - Notes: How to measure:
    1. Make an A/B build of the same scene with the passthrough feature fully off, then on.
    2. Lock levels, or record the granted levels.
    3. Record OVR Metrics CPU L, GPU L, GPU%, App GPU ms, stale frames and free memory.
    4. Add a Perfetto trace to see compositor and system-service CPU.
    5. Repeat with passthrough toggled off at runtime to answer Q4-001.

- **QUEST-GF2-009** A third-party Aug 2026 Quest 3 capture of a Unity app built from Meta's Passthrough Camera API samples, with its passthrough scene running, shows these granted levels over 565 one-second samples at 72 Hz:
  - CPU L2 (1382 MHz) in 549 samples and L3 in 16.
  - GPU L2 (456 MHz) in 531 samples and L3 (492 MHz) in 34.
  - 10 samples at 2361 MHz CPU (the Quest 3/3S top clock).
  - `average_frame_rate` 72–73, stale frames 0 in 547 samples, `app_gpu_time_microseconds` mostly around 3.1–3.3 ms.

  In a second scene of the same app (a video test scene), GPU L4 appears in 238 of 405 samples. [T][C]
  - Source: https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_144005.csv ; https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block3-video/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_150156.csv ; session log https://github.com/batunii/Arjuna/blob/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/session-log.md (accessed 2026-09-24) · Applies to: Quest 3, OS build not recorded, Unity (version not recorded), OVR Metrics Basic CSV · Evidence: [measured] [verify on device]
  - Notes: The light passthrough workload mostly sits at CPU L2 / GPU L2, as the MR level caps predict (Q2-038 / Q4-001). The 34 GPU L3 samples conflict with the documented "no GPU L3/L4 with passthrough" rule (QUEST-GF2-C4). Possible reasons: samples taken before passthrough was active, or the scene toggling passthrough; the log does not say. The session log also does not say whether passthrough is active in the video scene, so its GPU L4 samples prove nothing about the MR cap. Use this capture only as a sanity range for a light MR scene (about 3 ms app GPU at L2).

### 7.2 Passthrough Camera API (PCA)

- **Q4-022** Meta's published PCA costs:
  - About 1–2% GPU overhead per streamed camera.
  - About 45 MB memory overhead.
  - 20–40 ms capture latency.
  - 60 Hz data rate, maximum 1280x1280, internal format YUV420. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-pca-overview/ (accessed 2026-09-24; updated Apr 21, 2026)
  - Applies to: Quest 3 and 3S only; Horizon OS v74+; permission `horizonos.permission.HEADSET_CAMERA`. The API is built on Android Camera2.
  - Evidence: [doc]
  - Notes: Because the cost is quoted per camera, streaming both cameras for stereo roughly doubles the GPU overhead (about 2–4%, derived) [verify on device]. The page doesn't say whether the 45 MB is per stream.

- **Q4-023** Don't let PCA pick the largest resolution automatically. The 1280x1280 mode arrived in Horizon OS v83, and apps that grab the maximum can break when a new mode appears. Request a concrete tested resolution or a specific aspect ratio (4:3 for 1280x960, 1:1 for 1280x1280). `PassthroughCameraAccess` exposes `RequestedResolution` (the list runs from 320x240 to 1280x1280) and `MaxFramerate` (default 60). [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-pca-overview/ ; https://developers.meta.com/horizon/documentation/unity/unity-pca-documentation/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S, Core SDK/MRUK PCA path.
  - Evidence: [doc] [verify on device]
  - Notes: No published data on whether a lower resolution or `MaxFramerate` reduces the 1–2% GPU or 45 MB cost. Measure each configuration with OVR Metrics GPU% at fixed GPU L.

- **Q4-024** `PassthroughCameraAccess` (MRUK v81+) replaces the `WebCamTextureManager` / `WebCamTexture` path. Meta claims better performance but publishes no numbers. It provides `GetTexture()` (a GPU texture of the latest frame), per-frame `Timestamp`, and `GetCameraPose()` at that timestamp. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-pca-migration-from-webcamtexture/ (accessed 2026-09-24; updated Apr 21, 2026)
  - Applies to: Quest 3 and 3S; MRUK ≥ v81 (MRUK 207.0.0 is current, and it requires Unity 6000.0.66f2+).
  - Evidence: [doc]
  - Notes: With 20–40 ms latency, register CV results using the frame's timestamp and camera pose, not the current head pose. Otherwise content will swim.

- **Q4-025** Unity OpenXR: Meta image capture has two paths:
  - GPU path: zero-copy, Vulkan only. The image must be acquired and released inside `RenderPipelineManager.beginCameraRendering` / `endCameraRendering`.
  - CPU path: more expensive, and needs Android API level 32.
  - In 2.6 both paths are opt-in (Camera Image Support). 2.6 adds stereo pair capture; `SetMaxStereoSyncAttempts` defaults to 3 and is clamped to 1–10. [T] [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/camera/image-capture.html ; https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/whats-new.html (accessed 2026-09-24)
  - Applies to: Unity 6+, com.unity.xr.meta-openxr 2.6.x (2.6.1 latest), Quest 3 and 3S.
  - Evidence: [doc]
  - Notes: Prefer the GPU path for anything drawn on screen. Use the CPU path only for CPU-side CV, and run it off the main thread.

### 7.3 Depth API and occlusion

- **Q4-026** Depth API support by stack:
  - Quest 3 and 3S only.
  - Requires Vulkan, Multiview, passthrough enabled in every scene that uses it, OVRManager Scene Support = Required, and the USE_SCENE permission.
  - Compatible stacks: Unity 2022.3.15f1+ or 2023.2+ with Oculus XR Plugin 4.2.0+ and Core SDK ≥ v67 and < v74; or Unity 6+ with Unity OpenXR: Meta 2.1.0+ and Core SDK v74+. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-get-started/ (accessed 2026-09-24; updated May 18, 2026)
  - Applies to: Quest 3 and 3S.
  - Evidence: [doc]
  - Notes: Meta recommends the latest SDK for the best Depth API quality and performance. Because Depth API requires passthrough, it always runs under the Q4-001 ceiling. See Q4-C10 for a conflicting support statement.

- **Q4-027** Hard occlusion is cheaper, but edges are jagged and less stable over time. Soft occlusion looks better and needs "slightly more GPU". `EnvironmentDepthManager.OcclusionShadersMode` defaults to SoftOcclusion; the other values are HardOcclusion and None. No published ms or percentage figure exists for either mode. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions/ ; https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-get-started/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S; Core SDK EnvironmentDepthManager on both stacks.
  - Evidence: [doc] [verify on device]
  - Notes: How to measure: use a full-screen occluding material in a GPU-bound scene, switch OcclusionShadersMode between None, Hard and Soft at locked GPU L, and compare GPU% and App GPU ms. A RenderDoc Meta Fork render-stage trace shows the per-surface delta.

- **Q4-028** Depth API costs something even when no shader samples the depth textures. Turn it off when no occluders are visible: `EnvironmentDepthManager.enabled = false` stops requesting depth textures, and on XR.Oculus you can call `SetEnvironmentDepthRendering(false)`. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-depthapi-xr-oculus/ ; https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-get-started/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S, both stacks.
  - Evidence: [doc]

- **Q4-029** Occlusion is evaluated in each occluding material's shader:
  - Include `EnvironmentOcclusionURP.hlsl` and add `#pragma multi_compile _ HARD_OCCLUSION SOFT_OCCLUSION`.
  - Use `META_DEPTH_VERTEX_OUTPUT` / `META_DEPTH_INITIALIZE_VERTEX_OUTPUT` in the vertex stage and `META_DEPTH_OCCLUDE_OUTPUT_PREMULTIPLY(_WORLDPOS)` in the fragment stage, with a `_EnvironmentDepthBias` material float. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-advanced-usage/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S, URP (a Built-in RP include also exists).
  - Evidence: [doc]
  - Notes (inference): Because the macro runs per fragment, the cost scales with the pixels covered by occluding materials. The three-way multi_compile triples those shaders' variants. If you ship one mode, strip the other keyword with an IPreprocessShaders stripper [verify on device].

- **Q4-030** If the Depth API is too expensive in CPU or GPU, the documented fallback is occlusion from tracked or scene geometry. This also works on Quest 2. Draw a depth-only mesh (for example the hand mesh or scene mesh) before opaque geometry, at render queue < 2000. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-customize-passthrough-passthrough-occlusions/ ; https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-customization/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S.
  - Evidence: [doc]
  - Notes: A depth-only pre-pass writes depth and no color, so it is cheap on a tiler. It also early-z-rejects the virtual pixels behind it.

- **Q4-031** Environment raycasting in MRUK v81+ (`EnvironmentRaycastManager`: `Raycast`, `PlaceBox`, `CheckBox`) no longer needs the Depth API or an `EnvironmentDepthManager` in the scene. Don't keep depth running just for placement. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-environment-raycast/ (accessed 2026-09-24; updated Apr 6, 2026)
  - Applies to: Quest 3 and 3S; MRUK ≥ v81. On OpenXR the pre-v81 path needs Unity 6 and com.unity.xr.meta-openxr 2.1.0.
  - Evidence: [doc]
  - Notes: Rays only hit inside the depth camera frustum; outside it they return `HitPointOutsideOfCameraFrustum` or `NoHit`.

### 7.4 Scene API, global mesh and MRUK

- **Q4-032** Scene data needs on-device Space Setup; it can't be done over Link. Loading is asynchronous: `MRUK.Instance.LoadSceneFromDevice()`, "Load Scene on Startup", or `OVRScene.RequestSpaceSetup()`. Dependent work should hang off `SceneLoadedEvent`, sequenced with MRUK's Script Execution list. No published load-time or hitch number exists for scene loading. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manage-scene-data/ (accessed 2026-09-24; updated Jul 6, 2026)
  - Applies to: Quest 2, 3 and 3S; MRUK. On OpenXR: Meta, AR Foundation meshing also requires Space Setup and a permission (https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/meshing.html).
  - Evidence: [doc] [verify on device]
  - Notes: To measure, bracket `LoadSceneFromDevice` → `SceneLoadedEvent` with a ProfilerMarker, capture a Perfetto trace, and look for main-thread spikes when EffectMesh and colliders are generated.

- **Q4-033** EffectMesh generates render geometry from anchors: triangulated planes, cuboid volumes, and the raw global mesh. Options that add cost include Add Colliders (physics), Cast Shadows (shadow casters) and one GameObject per primitive. Hide Mesh keeps colliders and shader interactions without visible geometry. No per-option costs are published. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manage-scene-data/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S; MRUK.
  - Evidence: [doc] [verify on device]
  - Notes:
    - Turn Cast Shadows off unless the room mesh must cast shadows.
    - For occlusion or physics only, use Hide Mesh, or a depth-only material (Q4-030).
    - Use one EffectMesh per material; the doc suggests multiple instances for layered materials, and each instance adds draw calls.

- **Q4-034** No published triangle count, memory size or update rate exists for the GLOBAL_MESH anchor. Its cost as a render mesh or MeshCollider depends on the room scan. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manage-scene-data/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S (the global mesh comes from Space Setup scans; Quest 2 scene data is mostly planes and volumes).
  - Evidence: [doc] [verify on device]
  - Notes: To measure, log `mesh.triangles.Length / 3` after `SceneLoadedEvent` in several real rooms. Use a simplified or convex collider if physics is the only use.

- **Q4-035** DestructibleGlobalMeshSpawner (beta) splits the global mesh into fragments. Each fragment is its own GameObject with a MeshFilter and MeshRenderer, and "Segments Density" trades fragment count against performance. Draw calls and culling cost therefore scale with density. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manipulate-scene-visuals/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S; MRUK.
  - Evidence: [doc]

- **Q4-036** MRUK guidance: cache room and anchor references you access often, because the queries have overhead. Never delete or modify MRUK-owned rooms, anchors or trackables; to show a subset, use EffectMesh and AnchorPrefabSpawner. Unsubscribe from events in `OnDestroy`. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manage-scene-data/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S; MRUK.
  - Evidence: [doc]

- **Q4-037** MRUK package versions track the Core SDK. MRUK 207.0.0, published 2026-09-24, requires Core SDK 207.0.0 and Unity 6000.0.66f2+. Minimum Unity by MRUK version: 2021.3.26f1 from v60, 2022.3.15f1 from v74, 6000.0.66f2 from v203. [C]
  - Source: https://npm.developer.oculus.com/com.meta.xr.mrutilitykit (registry metadata, accessed 2026-09-24)
  - Applies to: MRUK on any stack.
  - Evidence: [doc]
  - Notes: PassthroughCameraAccess needs MRUK v81+ (Q4-024), which needs Unity 2022.3.15f1+.

### 7.5 Hand tracking, Fast Motion Mode, multimodal input and body tracking

- **Q4-038** OVRManager > Quest Features > Hand Tracking Frequency: higher frequency improves gesture detection and latency but "reserves some performance headroom" from the app's budget. The current docs give no number, and the current CPU/GPU level tables list no hand-tracking restriction. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-ovrcamerarig/ (accessed 2026-09-24; updated Aug 26, 2026)
  - Applies to: Quest 2, 3 and 3S; Core SDK.
  - Evidence: [doc] [verify on device]

- **Q4-039** Historical (2021, Quest 2) numbers: apps with low-frequency hand tracking were downclocked to CPU L3 / GPU L3, and high-frequency apps to CPU L3 / GPU L2. High frequency cut latency by about 10%. [T]
  - Source: https://developers.meta.com/horizon/blog/oculus-developer-release-notes-v28/ (accessed 2026-09-24; dated Apr 30, 2021)
  - Applies to: Quest 2 on the 2021 OS. Stale, see Q4-C4.
  - Evidence: [doc]
  - Notes: Use this only as a hypothesis to test. On device, enable hand tracking at Low and High and watch the granted CPU L/GPU L in OVR Metrics.

- **Q4-040** Fast Motion Mode (FMM) is the new name for High Frequency Hand Tracking. Meta says to test without it first and enable it only when fast motion causes heavy tracking loss. [T] [C]
  - FMM can add jitter, which hurts direct touch and typing.
  - Tracking gets worse in low light because of the short exposure.
  - Hand Tracking Frequency High and Max behave the same.
  - Toggle at runtime with `OVRPlugin.RequestFastMotionMode(bool)` or `OVRManager.instance.fastMotionModeHandPosesEnabled`. The build-time and runtime settings are independent.
  - Source: https://developers.meta.com/horizon/documentation/unity/fast-motion-mode/ (accessed 2026-09-24; updated Aug 11, 2026)
  - Applies to: Quest 2, Pro, 3 and 3S; Unity 6000.0.66f2+ per the current page; Core SDK v59+.
  - Evidence: [doc]
  - Notes: The current page publishes no performance number.

- **Q4-041** FMM incompatibilities that silently change behavior: [C]
  - Multimodal wins over FMM.
  - FMM disables the Dynamic Object Tracker, so MRUK keyboard tracking calls succeed but produce no anchors.
  - IOBT/WMM won't run when passthrough, FBS and FMM run together.
  - On Quest Pro, FMM excludes face tracking, eye tracking, lip sync and foveated rendering.
  - With passthrough, virtual hands can look more responsive than the passthrough hands.
  - Source: https://developers.meta.com/horizon/documentation/unity/fast-motion-mode/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S (the Pro item is out of scope).
  - Evidence: [doc]

- **Q4-042** Verifying FMM on device:
  - `adb logcat -e FMM` should show `HandTrackingService: FMM: enabled: true; active: true`.
  - `adb logcat -e "Camera FPS"` should read about 60 Hz, or 50 Hz on 50 Hz mains grids.
  - There is a developer override under Settings > System > Advanced > Developer > Hand Tracking Frequency Override. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/fast-motion-mode/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S.
  - Evidence: [doc]

- **Q4-043** Native `XR_META_hand_tracking_frequency_hint`: `xrSetHandTrackingFrequencyHintMETA(session, DEFAULT=1 | HIGH=2)`. The hint is advisory and session-wide. The default is the power-efficient frequency, and HIGH reduces temporal smoothing, which can add jitter. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/native-openxr-hand-tracking-frequency-hint/ (accessed 2026-09-24; updated Apr 24, 2026)
  - Applies to: Quest 2, 3 and 3S; OpenXR runtime. This is the mechanism under the Unity setting.
  - Evidence: [doc]

- **Q4-044** Multimodal input (simultaneous hands and controllers) is set under OVRManager > Quest Features > Simultaneous Hands And Controllers (Supported or Required). [T] [C]
  - Needs Unity 6000.0.66f2+ and SDK v62+.
  - Incompatible with IOBT/FBS and FMM; on Quest 2, also with LipSync.
  - With passthrough, multimodal and WMM all on, the system disables WMM.
  - No performance numbers are published.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-multimodal/ (accessed 2026-09-24; updated Aug 11, 2026)
  - Applies to: Quest 2, Pro, 3 and 3S.
  - Evidence: [doc] [verify on device]

- **Q4-045** Wide Motion Mode runs Inside-Out Body Tracking under the hood to infer hands outside the camera frustum. Enabling WMM therefore carries body-tracking cost. [T]
  - It requires OVRManager Body Tracking Support = Required.
  - `OVRHand` / `OVRPlugin` report whether a pose is inferred.
  - Debug setup uses `adb shell setprop debug.oculus.forceEnablePerformanceFeatures BODY_TRACKING`.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-wide-motion-mode/ (accessed 2026-09-24; updated Aug 11, 2026)
  - Applies to: Quest 3 and 3S.
  - Evidence: [doc] [verify on device]

- **Q4-046** IOBT (Body Tracking Fidelity = High) is only a suggestion. If you request it after the system is already heavily loaded (passthrough plus FMM or controllers, or high CPU load), body tracking starts in low fidelity with no error. Elbow and lean fidelity are lost. Check with `adb shell dumpsys activity service com.oculus.bodyapiservice.BodyAPIService`. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/move-body-tracking/ (accessed 2026-09-24; updated Dec 19, 2025)
  - Applies to: Quest 3 and 3S (IOBT); Movement SDK.
  - Evidence: [doc]
  - Notes: Request IOBT before enabling other heavy services, and test the exact feature mix you ship.

- **Q4-047** Turning on "Update When Offscreen" for body-tracked skinned meshes recalculates bounds every frame, which costs CPU. Prefer enlarging the SkinnedMeshRenderer bounds. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/move-body-tracking/ (accessed 2026-09-24)
  - Applies to: all devices; Movement SDK characters.
  - Evidence: [doc]

- **Q4-048** No published number found for the current CPU/GPU cost of hand tracking (default or FMM), multimodal, WMM or IOBT. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/fast-motion-mode/ ; https://developers.meta.com/horizon/documentation/unity/unity-multimodal/ ; https://developers.meta.com/horizon/documentation/unity/move-body-tracking/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S.
  - Evidence: [doc] [verify on device]
  - Notes: How to measure:
    1. Use a fixed scene and fixed CPU/GPU levels.
    2. Toggle each feature on its own and then combined with passthrough.
    3. Record granted CPU L/GPU L, App CPU ms, main-thread timings from Unity ProfilerRecorder, and stale frames.
    4. Use Perfetto to see tracking-service CPU on the other cores.

### 7.6 Symmetric Projection and MVRR with passthrough and Depth API

- **Q4-078** No published measurement shows how Symmetric Projection and MVRR interact with a passthrough underlay or the Depth API. The only documented numbers are the generic 5–15% and 3–8% GPU-bound ranges. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (accessed 2026-09-24)
  - Applies to: Quest 3 and 3S MR apps.
  - Evidence: [doc] [verify on device]
  - Notes: To measure, turn on Symmetric Projection, then MVRR All Passes, then Final Pass, in a GPU-bound MR scene with occlusion on. Record GPU% at the same GPU L (which is capped at L2 under passthrough), and check edge alpha for passthrough artifacts.

## 8. SDK and plugin choices

### 8.1 SDK landscape (September 2026): versions, stacks, feature availability, settings paths

- **Q4-049** Meta XR Core SDK: the current version is 207.0.0 (npm `latest`, published 2026-09-24T16:34Z; the downloads page says "Updated: Sep 22, 2026"). Versioning jumped from 85.0.0 (2026-02-10) to 201.0.0 (2026-04-15), following the OS's new standardized numbering. Later releases: 203.0.0 (2026-06-05), 205.0.0 (2026-07-22), 207.0.0. [C]
  - Source: https://npm.developer.oculus.com/com.meta.xr.sdk.core ; https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/ ; https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/201.0/ (accessed 2026-09-24)
  - Applies to: all devices.
  - Evidence: [doc]

- **Q4-050** Core SDK minimum Unity by version:
  - 59.0.0–72.0.0: 2021.3.26f1.
  - 74.0.0–201.0.0: 2022.3.15f1.
  - 203.0.0 and later: 6000.0.66f2.
  - So Unity 2021.3 projects stop at Core SDK v72 and 2022.3 projects stop at v201. [C]
  - Source: https://npm.developer.oculus.com/com.meta.xr.sdk.core (per-version `unity` / `unityRelease` fields, accessed 2026-09-24) ; https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/203.0/
  - Applies to: Unity 2021.3–6.6.
  - Evidence: [doc]
  - Notes: Interaction SDK 207.0.0 still declares 2022.3.15f1 as its minimum (https://npm.developer.oculus.com/com.meta.xr.sdk.interaction), but it can't go past the Core SDK version the editor supports.

- **Q4-051** The Oculus XR Plugin (com.unity.xr.oculus) is deprecated from Unity 6.5. [C]
  - Unity: supported through Unity 6.4, with LTS support via 6.3 LTS and no removal date announced.
  - The latest version is 4.5.5 (2026-07-19), which adds a deprecation warning.
  - Unity says OpenXR: Meta 2.1 reached parity as of OpenXR 1.14.
  - Meta: the plugin is deprecated and "scheduled for removal"; it is validated for Unity 2022+ with Meta SDK ≤ v73.
  - Source: https://discussions.unity.com/t/oculusxr-package-deprecation/1717655 (Unity staff post, Apr 23, 2026) ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html ; https://developers.meta.com/horizon/documentation/unity/unity-xr-plugin/ (accessed 2026-09-24)
  - Applies to: Unity 2021.3–6.6.
  - Evidence: [doc]
  - Notes: New Quest work on Unity 6.x should use the Unity OpenXR Plugin. Stay on Oculus XR only for 2021.3/2022.3 maintenance.

- **Q4-052** Meta recommends the Unity OpenXR Plugin: Unity 6+, Meta SDK v74+, editor 6000.0.66f2+, with 6.1+ recommended. [C]
  - Meta's page still names 1.15.1 and 4.5.1 as recommended versions; see Q4-C5.
  - Unity's current releases: OpenXR 1.18.0 (2026-08-04), 1.19.0-pre.1 (2026-08-12), and OpenXR: Meta 2.6.1.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-xr-plugin/ ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html ; https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/whats-new.html (accessed 2026-09-24)
  - Applies to: Unity 6.0–6.6.
  - Evidence: [doc]
  - Notes: OpenXR 1.18.0-pre.1 raised the minimum editor to 6000.0, so 2022.3 projects are limited to OpenXR ≤ 1.17.x [verify on device].

- **Q4-053** Unity 6.6's untethered-XR URP workflow tells you to: [T] [C]
  - Use Vulkan, the OpenXR plugin, render graph and Forward rendering.
  - Enable Multiview, foveated rendering and Multiview Render Regions.
  - Consider URP Application SpaceWarp.
  - From Unity 6.6, enable the Adaptive Performance Basic provider for OpenXR.
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24; built 2026-09-24)
  - Applies to: Unity 6.6 (Adaptive Performance for OpenXR is new in 6.6); URP.
  - Evidence: [doc]

- **Q4-054** Unity 6.1+ has a Meta Quest build profile. It auto-installs the OpenXR plugin as a required package, preconfigures some Player and Quality settings, and lets you override Player, Graphics and Quality settings for Quest separately from Android. The profile also enables automatic shader optimizations. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24)
  - Applies to: Unity 6.1–6.6.
  - Evidence: [doc]

- **Q4-055** OpenXR settings path: Project Settings > XR Plug-in Management > OpenXR (Android tab) > Meta Quest Support (cog). [T]
  - Meta lists these settings there: Symmetric Projection (Vulkan), Optimize Buffer Discards (Vulkan), Multiview Render Regions Optimizations (None / All Passes / Final Pass), Space Warp motion vector texture format, Late Latching (Vulkan), Force Remove Internet Permission, System Splash Screen, and Target Devices.
  - Other settings live on the OpenXR page itself: Render Mode, Latency Optimization, Depth Submission Mode, Foveated Rendering API, Use OpenXR Predicted Time, Additional Graphics Queue, and Offscreen Rendering Only.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ ; https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html (accessed 2026-09-24)
  - Applies to: Unity OpenXR 1.14+ on Unity 6.x (MVRR needs 6.1+).
  - Evidence: [doc]
  - Notes: Unity's own 1.18 Meta Quest page does not list Late Latching; see Q4-C8.

- **Q4-056** Oculus XR settings path: Project Settings > XR Plug-in Management > Oculus (Android tab). [T]
  - Settings: Stereo Rendering Mode (Multi Pass / Multiview), Low Overhead Mode (GLES only), Optimize Buffer Discards (Vulkan), Symmetric Projection (Vulkan + Multiview), Subsampled Layout (Vulkan), Foveated Rendering Method, Depth Submission, System Splash Screen, Late Latching (Vulkan), Late Latching Debug Mode, Application SpaceWarp, Optimize Multiview Render Regions (Vulkan).
  - Subsampled Layout makes Timewarp more expensive; use it only with FFR level ≥ 2.
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html (accessed 2026-09-24)
  - Applies to: Oculus XR 4.x on Unity 2021.3–6.4.
  - Evidence: [doc]
  - Notes: FFR level is set via `XRDisplaySubsystem.foveatedRenderingLevel`, mapped as 0 = off, < 0.33 low, < 0.66 medium, ≥ 0.66 high. `foveatedRenderingFlags` includes GazeAllowed, which only matters on Quest Pro.

- **Q4-058** Performance feature availability by stack (first version that ships each feature), from the changelogs. [T] [C]
  - Symmetric Projection: Oculus 3.0.0 / OpenXR 1.9.1. OpenXR has required Multiview for it since 1.13.0.
  - Optimize Buffer Discards: Oculus 1.5.0 / OpenXR 1.10.0.
  - Multiview Render Regions: Oculus 4.5.0 / OpenXR 1.14.0. "All Passes" arrived in OpenXR 1.15.0-pre.2 and needs Unity 6.2+.
  - Application SpaceWarp: both stacks; OpenXR from 1.9.1, URP AppSW from 1.15.0, RG16f motion vectors from 1.14.0.
  - Subsampled Layout: both. OpenXR had an option from 1.9.1 and moved it onto the Foveated Rendering feature in 1.16.0-pre.1.
  - SRP Foveation: OpenXR 1.11.0, default method from 1.17.0 / Oculus 4.3.0 common foveation API.
  - Dynamic Foveation: OpenXR 1.18.0 only. `XR_META_tile_properties_hint`: OpenXR 1.17.0-pre.1 only.
  - Low Overhead Mode (GLES): Oculus only.
  - Performance-level hint API: `XrPerformanceSettings.SetPerformanceLevelHint` in OpenXR 1.11.0; the Core SDK OVRPlugin API works on both.
  - `XR_META_performance_metrics`: OpenXR 1.7.0.
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html (accessed 2026-09-24)
  - Applies to: Unity 2021.3–6.6.
  - Evidence: [doc]
  - Notes: Dual-core mode and CPU/GPU level trading need OVRPlugin's OpenXR backend, not the legacy backend (Q4-004). Depth API support by stack is in Q4-026.

- **Q4-059** Optimize Buffer Discards (Vulkan) lazily allocates the transient MSAA attachments. With 4x MSAA it saves about 90 MB per eye at 1680x1760 (Quest 3 default), 180 MB for both eyes. At 1440x1584 (Quest 2 default) it saves about 66 MB per eye. Meta calls it free; the Oculus XR docs say it can break effects that sample depth, such as camera stacking (Q4-C7). [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S; Vulkan; both stacks.
  - Evidence: [doc]

- **Q4-061** OpenXR settings choices that affect throughput and latency (Meta's reference): [T] [C]
  - Render Mode: Multi-view.
  - Latency Optimization: Prioritize Input Polling.
  - Depth Submission Mode: None. Depth submission costs a GPU resolve plus compositor work.
  - Foveated Rendering API: SRP Foveation. Meta says it is often 20–30% faster in frame time than Legacy for multi-pass pipelines. Custom render-graph passes opt in with `builder.EnableFoveatedRasterization(bool)`.
  - Use OpenXR Predicted Time: on. It needs v83+ and is the default from OpenXR 1.17.0.
  - Additional Graphics Queue: off.
  - Offscreen Rendering Only (Vulkan): on; saves 10–20 MB.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (accessed 2026-09-24; updated May 11, 2026)
  - Applies to: Unity 6.x with the OpenXR plugin.
  - Evidence: [doc]
  - Notes: Foveation and SpaceWarp details are owned by other topics; see Leads.

- **Q4-062** Space Warp motion vector format: use RG16f (4 B/px) rather than RGBA16f (8 B/px). That halves the bandwidth for writing and reading motion vectors, and Meta states the error is under 0.5 px. Switch to RGBA16f only if profiling shows artifacts. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (accessed 2026-09-24)
  - Applies to: Unity OpenXR 1.14.0+ with AppSW.
  - Evidence: [doc]

- **Q4-064** OVRManager settings that matter for MR performance: [T] [C]
  - "Use Recommended MSAA Level" only works on the Built-in RP. For URP, set 4x MSAA in the URP asset yourself.
  - Enable Dynamic Resolution: off by default, and a prerequisite for the top GPU levels. Ranges are Quest 2/Pro 0.7–1.3 and Quest 3/3S 0.7–1.6.
  - Skip Unneeded Shaders enables shader stripping to cut build time.
  - Quest Features holds Passthrough Support, Scene Support, Hand Tracking Frequency, Simultaneous Hands And Controllers, and Body Tracking Support.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-ovrcamerarig/ ; https://developers.meta.com/horizon/documentation/unity/unity-passthrough-gs/ (accessed 2026-09-24)
  - Applies to: Core SDK on both stacks.
  - Evidence: [doc]

- **Q4-065** Multiview halves draw-call dispatch compared with multi-pass, and it is on by default in OpenXR. MR features depend on it: Depth API requires it (Q4-026), and so does Symmetric Projection (Q4-072). [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/enable-multiview/ (accessed 2026-09-24; updated Nov 12, 2025)
  - Applies to: all devices, both stacks.
  - Evidence: [doc]

- **Q4-066** Recent Core SDK releases added performance tooling but no published numbers: [T]
  - v203: the `XR_META_temporal_pixel_synthesis` OpenXR extension, and the "AI Runtime Optimizer Tool" for real-time bottleneck analysis (Tools menu, Windows Unity).
  - v205: an experimental "Hands Optimizer Tool" that scans the project for hand-tracking optimization opportunities.
  - Source: https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/203.0/ ; https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/205.0/ (accessed 2026-09-24)
  - Applies to: Core SDK v203+ (Unity 6000.0.66f2+).
  - Evidence: [doc] [verify on device]

- **Q3-093** Unity 6.6's untethered-XR checklist says:
  - Use Vulkan.
  - Enable multiview, foveated rendering and Multiview Render Regions.
  - Consider AppSW, while noting it can cause visible artifacts.
  - Implement resolution scaling.
  - Disable HDR to cut bandwidth; Unity notes most untethered devices do not support HDR rendering.
  
  [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: Unity 6.6 URP · Evidence: [doc]
  - Notes: This is Unity's current baseline to check a project against.

### 8.2 Project Setup Tool (PST)

- **Q4-067** PST location and behavior: [C]
  - Open it from Window > Meta > Tools > Project Setup Tool, from Edit > Project Settings > Meta XR, or from the Meta XR SDK window (Window > Meta > Meta XR SDK; pinnable to the toolbar in 6000.3+).
  - Needs Core SDK v59+ (or Oculus Integration v49–57).
  - Tasks can be filtered by target group and category.
  - Actions: Fix All, per-task Fix/Apply, and Ignore/Unignore.
  - Cog options: Background Checks, "Required throw errors" (unchecking lets builds proceed despite failing Required tasks), Log outstanding issues, Show Status Icon, Produce Report on Build.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-upst-overview/ (accessed 2026-09-24; updated Aug 25, 2026) ; https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-get-started/
  - Applies to: Core SDK on both stacks.
  - Evidence: [doc]

- **Q4-068** Custom performance rules go through `OVRProjectSetup.AddTask`:
  - Parameters: group, isDone, platform, fix, level, conditionalLevel, message, conditionalMessage, fixMessage, conditionalFixMessage, url, conditionalUrl, validity, conditionalValidity.
  - The task ID is a hash of the message, so the message must be unique. Tasks can't be removed once added.
  - Levels include Required and Recommended; groups include Quality, XR and more. Group "All" is invalid. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-upst-overview/ (accessed 2026-09-24)
  - Applies to: Core SDK v50+.
  - Evidence: [doc]
  - Notes: Encode team MR performance rules as Required tasks, for example: Vulkan only; URP MSAA = 4x; URP HDR off in MR scenes; Symmetric Projection on; Depth Submission None; no second passthrough layer.

- **Q4-069** PST writes a JSON report with createdAt, platform, projectName, unityVersion, projectUrl and tasksStatus (uid, group, message, level, isDone). You can produce it on build (Core SDK v52+) or headlessly: `Unity -project <path> -executeMethod OVRProjectSetupCLI.GenerateProjectSetupReport -reportFile <file> -buildTarget <platform>`. Use this for CI gating. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-upst-overview/ (accessed 2026-09-24)
  - Applies to: Core SDK v52+.
  - Evidence: [doc]

- **Q4-070** The docs do not publish the concrete list of default PST rules; it lives in the SDK source. The MR requirements PST checks and fixes, per the Depth API page, are: Vulkan, Multiview, passthrough enabled, and Scene Support Required. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-upst-overview/ ; https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-get-started/ (accessed 2026-09-24)
  - Applies to: Core SDK on both stacks.
  - Evidence: [doc] [verify on device]
  - Notes: To get the effective rule list for a given SDK version, run the CLI report (Q4-069) on a blank project and on the real project, then diff the `tasksStatus` arrays.

- **Q4-071** Meta's Unity best-practices page points to PST for applying its recommendations: [T]
  - Forward or Forward+ rendering; 4x MSAA.
  - Avoid SSAO, motion blur, global fog and parallax mapping; avoid real-time GI.
  - Avoid more than 2 render passes; disable shadows near the geometry or draw-call limits.
  - Dynamic Resolution for GPU L5.
  - Link Time Optimization only in release builds.
  - Avoid slow physics settings: Sleep Threshold < 0.005, Default Contact Offset < 0.01, or Solver Iterations > 6.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ (accessed 2026-09-24; updated Sep 15, 2024)
  - Applies to: all devices, Unity 2021.3–6.6.
  - Evidence: [doc]
  - Notes: The page predates the OpenXR switch. Which of these PST checks automatically isn't documented (Q4-070).

### 8.3 Engine release status and platform shader cache

- **QUEST-GF1-001** Unity LTS support windows: Unity 6.0 LTS has two-year LTS support through October 2026, and Unity 6.3 LTS (the latest LTS) is supported until December 2027. Enterprise and Industry subscribers get one extra year on each. [C]
  - Source: https://unity.com/releases/unity-6/support (accessed 2026-09-24) · Applies to: Unity 6000.0 and 6000.3 · Evidence: [doc]
  - Notes: Confirms the user baseline. For Quest projects, 6.3 LTS is the long-lived target: it carries the FFR/RenderObjects fix (Q3-054), IUpscaler handling (Q3-007), Automatic Viewport Dynamic Resolution (Q3-059) and MVRR render-graph gating (Q4-077). A 6.0 project gets engine fixes only until Oct 2026.

- **QUEST-GF1-002** Unity 6.7 had not shipped as a final release by 2026-09-24. Unity's support page still lists 6.3 as the latest LTS. A Japanese trade outlet reports the 6.7 alpha released on June 25, 2026, and Meta's fix lists cite only 6000.7.0a3. [C]
  - Source: https://unity.com/releases/unity-6/support ([doc]); https://gamemakers.jp/article/2026_06_26_140306/ ([community]) (accessed 2026-09-24) · Applies to: Unity 6000.7 · Evidence: [doc] (for "latest LTS is 6.3"); the alpha date is [community]
  - Notes: Keeps 6.7 out of scope, consistent with QX-C3. Re-check at skill-writing time.

- **QUEST-GF1-004** Horizon OS Shader Binary Cache (SBC) pre-warming. [C]
  - Mechanism: Meta's backend launches the app on each headset type (Quest 2, Pro, 3, 3S) with the intent extra `horizonos.extra.SHADER_PREWARMING_AUTOMATION=true`, uploads the resulting driver shader cache, and ships it with installs and updates to headsets with the same device and app configuration.
  - Setup: manifest `<meta-data android:name="com.oculus.sbcpath" android:value="<cache path relative to app storage>"/>` (the page's examples include a `vulkan_pso_cache.bin` path), plus Developer Dashboard > Development > Shader Compilation > "Enable Shader Cache Automation".
  - Limits: a 10-minute pre-warm cut-off per backend headset; only two app versions are processed (latest live and most recently uploaded); caches rebuild after installs, app updates and graphics driver or OS updates. Unity and Unreal apps "may be processed", but support is not guaranteed.
  - Status: the doc page (updated Aug 7, 2026) now carries a deprecation banner. It says the feature is no longer actively maintained and a replacement is in development.
  - Source: https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S Store apps; Unity support not guaranteed · Evidence: [doc] [verify on device]
  - Notes: Meta's GDC 2026 recap (Mar 10, 2026) still promoted SBC, citing *Asgard's Wrath 2* startup falling from 7 minutes to 20 seconds (a Meta case study, not a reproducible measurement). See QUEST-GF1-C2. For Unity, do not rely on SBC for first-use hitches. Keep your own PSO/shader warm-up (unity-perf bundle) and measure the cold-vs-warm split with the CSV `shader_hitches` column (Q1-014) and Q1-011.

- **QUEST-GF2-011** Unity 6.5+ applies Meta Quest-specific optimizations to the URP Shader Library when the Meta Quest build profile is used. [T]
  - The manual page "Configure shader optimizations for Meta Quest" (6000.5 and 6000.6; 404 on 6000.4) says the automatic optimizations target GPU frame time, instruction count and bandwidth in the prebuilt URP shaders (Lit, Simple Lit, Shader Graph nodes) and in custom shaders that use SRP library functions.
  - Two are configurable:
    - **Light-loop unroll:** set the URP asset's Per Object Limit (additional lights) to 1. This raises the variant count and build time.
    - **Camera projection query:** the projection check always resolves as perspective. Projects that render orthographic cameras must enable the `_META_QUEST_ORTHO_PROJ` keyword under Project Settings > Graphics > Shader Build Settings > Keyword Declaration Overrides.
  - In the GDC 2026 talk, Meta described four more changes made with Unity:
    - transparent-alpha output resolved by keyword instead of a dynamic branch
    - the orthographic check above
    - an early-out for pixels back-facing the main light, which skips shadow sampling
    - the same early-out for main-light lighting
  - Talk figures:
    - The first two saved about 0.14 ms and 0.23 ms on a "representative" benchmark scene. The captions read ". 14" and ". 23" milliseconds.
    - The shadow early-out took a contrived back-facing test scene from 4.96 to 3.35 ms.
    - The lighting early-out saved about 0.2 ms.
    - Partial loop unroll cut registers from 10 to 8 and raised occupancy from 50% to 75%, taking frame time from 4.63 to 4.25 ms.
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html ; https://docs.unity3d.com/6000.5/Documentation/Manual/xr-meta-quest-graphics-optimization.html ; https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ (Meta talk video (GDC 2026, Mar 10, 2026, David Borel and Neel Bedekar), read from its auto-generated captions; about 18:40–30:10) (accessed 2026-09-24) · Applies to: Unity >= 6000.5, URP 17.x, Meta Quest build profile; the device for the talk figures is not stated (the talk is scoped to Quest 3/3S) · Evidence: [doc] for the Unity page; the ms figures are [doc] (Meta talk) from auto-captions, with no stated device or API [verify on device]
  - Notes: For custom HLSL on 6.5+, calling the SRP ShaderLibrary lighting functions inherits the optimizations; hand-rolled lighting does not. Use the back-facing early-out pattern in custom shaders on 2021.3–6.4 as well. It is a dynamic branch that pays off only when it skips texture samples. Per Object Limit = 1 is a quality decision: extra lights beyond one per object are dropped.

## 9. Profiling toolkit: commands, captures, counters

### 9.1 OVR Metrics Tool (install, modes, intents, Unity SDK)

- **Q1-001** Install OVR Metrics Tool from the Horizon Store, or from MQDH Device Manager > Device Actions > "Install OVR Metrics Tool". Install it before you launch the app under test: installing while the app runs force-closes that app when the install finishes. Open the tool's UI from ADB with `adb shell am start omms://app`. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S, any engine, OpenXR and legacy VrApi apps · Evidence: [doc]
  - Notes: Page updated Jun 21, 2026. The page gives no current tool version number. The only version named anywhere is "1.5", in the Stats Definition Guide (Q1-023). No published number found. To read the installed version: `adb shell dumpsys package com.oculus.ovrmonitormetricsservice | grep versionName` (a standard Android command, not from Meta docs).

- **Q1-002** The tool has two independent modes:
  - **Report Mode** writes CSV. Turn it on with the "Record all captured metrics to csv files" toggle or the `ENABLE_CSV` intent. Meta says report data exports as CSV with PNG images.
  - **Performance HUD** is the overlay. Turn it on with "Enable Persistent Overlay (may require reboot)" or the `ENABLE_OVERLAY` intent. The HUD shows no stats until you pick them (the FPS graph is always there). "Render Overlay on GPU" and "Lock Overlay to Head" are both on by default. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: For soak tests, record CSV with the HUD off. That way the HUD's own compositor layer and GPU draw are not part of what you measure. No published number found for HUD overhead. To measure it: run the same scene with the HUD on and off, compare `app_gpu_time_microseconds` and `timewarp_gpu_time_microseconds`, and check `total_layer_count`. [verify on device]

- **Q1-003** All tool settings can be scripted with broadcast intents of this form: `adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.<ACTION>`. The actions are:
  - `ENABLE_OVERLAY`, `DISABLE_OVERLAY`
  - `ENABLE_GRAPH`, `ENABLE_STATS`, `DISABLE_GRAPH`, `DISABLE_STATS` (all stats at once)
  - `ENABLE_GRAPH`, `ENABLE_STAT`, `DISABLE_GRAPH`, `DISABLE_STATS` with `--es stat <stat>` (one stat)
  - `ENABLE_CSV`, `DISABLE_CSV`
  - `ENABLE_DROPPED_FRAME_SCREENSHOT --ei count <count> --ei time <time>`, `DISABLE_DROPPED_FRAME_SCREENSHOT`
  - `LOG_STATE`, which prints the current configuration to logcat as JSON. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The dropped-frame screenshot fires when `<count>` frames are missed within a window of `<time>`. The page does not give the unit of `time`. No published number found; send `LOG_STATE` after setting it to see how the tool stored the value. Use `LOG_STATE` as a precondition check in automated capture scripts.

- **Q1-004** Overlay placement extras for `ENABLE_OVERLAY`:
  - `--eb headlocked (true|false)`
  - `--ef pitch` (-90 to 90; negative is down)
  - `--ef yaw` (-180 to 180; negative is left)
  - `--ei scale (1, 2, or 3)`
  - `--ef distance (0.1+)` (headlocked only)
  
  Meta does not recommend world-locking the overlay (it calls this unpredictable). [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Pitch the HUD down or yaw it aside so it does not cover the part of the screen being profiled, for example foveation edges.

- **Q1-006** The tool has two presets:
  - **Basic**: battery level, CPU level, GPU level, average FPS, stale frame count, CPU utilization, GPU utilization, App GPU time.
  - **Advanced** adds: foveation level, early frames, eye buffer width and height, Timewarp GPU time, VrShell+Boundary GPU time, Spacewarp FPS, and Max Consecutive Stale Frames.
  
  Meta's guidance is to use Basic for measurement. Advanced adds overhead that can distort results and is meant for isolated GPU-bottleneck hunts. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ and https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: No published number found for the size of the Advanced overhead. To measure it: A/B the same scripted scene and compare the `app_gpu_time_microseconds` distribution. The best-practices page is undated.

- **Q1-007** Some stats only work when ovrgpuprofiler support is enabled inside OVR Metrics Tool. These are `avg_fill_percentage`, the `percent_*` stall, miss and filter stats, instructions per fragment or vertex, and textures per fragment. `avg_fill_percentage` estimates overdraw: 100 means each eye pixel was touched once on average, and system overlays add to it. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The Stats Definition Guide is undated and partly pre-2023. For clean FPS or VRC runs, leave counter stats off. For GPU diagnosis, turn them on in a separate run.

- **Q1-011** The overlay trails reality by about 1 second. A fresh install compiles shaders on first run, so play a level once before you judge its performance. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S, Unity · Evidence: [doc]
  - Notes: The first-run hitches are exactly what a shader/PSO warm-up workstream must remove. Measure both cold (first run) and warm runs, and keep them as separate datasets.

- **Q1-019** The Unity toolkit is `OVRMetricsToolSDK`. Import it from the downloaded `Unity/OVRMetricsToolSDK.unitypackage`; it also ships inside `com.meta.xr.sdk.core` at `Scripts/Util/OVRMetricsToolSDK.cs`, checked in v85.0.0. `OVRMetricsToolSDK.Instance.GetLatestMetricsSnapshot()` returns a nullable `MetricsSnapshot`: a `long time` plus fields named after the stat list (the v85 struct includes `phase_sync_mode`, `max_repeated_frames`, `render_scale` and `dynres_recommendation_*`). The SDK talks to the tool's service through the Java class `com.oculus.metrics.OVRMetricsToolClient`, with native `ovrMetricsTool_*` calls behind it. Other public methods: `GetError`, `DeleteAppMetric`. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ ; SDK source mirror https://github.com/elliot170802/Practicas_AR_TSIC/tree/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/Util (accessed 2026-09-24) · Applies to: Unity projects on Meta XR Core SDK (v85 checked); Quest 2/3/3S · Evidence: [doc]
  - Notes: The OVR Metrics service must be installed and running on the headset. That makes this a QA or dev-build hook, not something to ship for players. Null-check the snapshot.

- **Q1-021** Custom metrics:
  - `DefineAppMetric(name, displayName, group, rangeMin, rangeMax, graphMin, graphMax, redPercent, greenPercent, showGraph, showStat)` defines a metric; `redPercent` and `greenPercent` run from 0 to 1.
  - `UpdateAppMetric(name, int)` updates it.
  - Meta advises updating only when a value changes, to limit overhead.
  - The "OVR Metrics Manager" component on the camera rig (Core Metrics Reporting) publishes Unity memory and render stats through this API. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Unity + Meta XR Core SDK · Evidence: [doc]
  - Notes: A good use is to publish your own counters, such as active particle systems, visible skinned meshes or PSO misses, so they sit on the same timeline as the GPU numbers.

- **Q1-022** In `OVRMetricsCore.cs` (SDK v85), Core Metrics come from Unity `ProfilerRecorder`. The code only compiles under `UNITY_PROFILING && UNITY_ANDROID`. Four frame-time metrics are marked `developmentOnly`: `CPU Main Thread Frame Time` ("CPU MAIN T"), CPU render-thread time, `CPU Total Frame Time` ("CPU T") and `GPU Frame Time` ("GPU T"). A release build therefore gets only memory and count metrics. The default frame-time graph maximum is 2 × (1e6/72) µs, with green at 50% and red at 60%. [T]
  - Source: https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/Util/OVRMetricsCore.cs (SDK source mirror) (accessed 2026-09-24) · Applies to: Meta XR Core SDK v85; Unity 2020.2+ (ProfilerRecorder) · Evidence: [doc] (SDK source)
  - Notes: The 72 Hz graph default is hard-coded. At 90 or 120 Hz the red and green colours do not match the real budget.

- **Q1-023** The Stats Definition Guide lists these as new in OVR Metrics Tool 1.5: Boundary GPU time, CPU utilization for cores 0–7 (earlier Quest apps were limited to cores 5–7), and VSS, RSS and Dalvik PSS. [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The page is undated and describes pre-2023 behaviour. The core-5/6/7 limit is historical; 2026 CSVs have all of core0–7.

- **QUEST-GF1-006** The OVR Metrics Tool SDK download page lists version 2.0.1, updated Dec 12, 2025, as the latest. It highlights app-defined metrics and Core Metrics Reporting for Unity. [T][C]
  - Source: https://developers.meta.com/horizon/downloads/package/ovr-metrics-tool-sdk/ (accessed 2026-09-24) · Applies to: OVR Metrics Tool SDK (Unity package); Quest 2/3/3S · Evidence: [doc]
  - Notes: This is the SDK package version. The on-device tool version may differ; read it with `adb shell dumpsys package com.oculus.ovrmonitormetricsservice | grep versionName` (Q1-001). Record both versions in capture metadata, because the CSV header changes between tool versions (Q1-012).

### 9.2 Logcat: the per-second VrApi line and XrPerformanceManager

- **Q1-027** Filter the stats with `adb logcat -s VrApi,XrPerformanceManager` (tags can also be used one at a time). To start from a clean buffer, run `adb logcat -c; adb logcat -s XrPerformanceManager`. Meta describes logcat as low-overhead, engine-agnostic, basic triage. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat/ ; https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The ts-logcat page is undated. The logcat stats page was updated Jul 31, 2025 (unity/ and native/ copies are identical).

- **Q1-028** The VrApi stats line is printed once per second. Documented example (verbatim): `FPS=72/72,Prd=38ms,Tear=0,Early=0,Stale=0,Stale2/5/10/max=0/0/0/0,VSnc=1,Lat=-1,Fov=0,CPU4/GPU=2/2,1171/441MHz,OC=FF,TA=0/0/0,SP=N/N/N,Mem=2092MHz,Free=2975MB,PLS=0,Temp=32.2C/0.0C,TW=1.25ms,App=4.49ms,GD=0.00ms,CPU&GPU=12.96ms,LCnt=2(DR72,LM2),GPU%=0.43,CPU%=0.37(W0.50),DSF=1.00,CFL=19.79/21.54,ICFLp95=20.94,LD=0,SF=1.00,LP=0,DVFS=0,ShrpLCnt=5,ShrpR=1.000,SSLCnt=3/3`. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ ; https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Parse it as comma-separated `key=value` pairs, with special cases for `CPU4/GPU=a/b`, the bare `1171/441MHz` token, `LCnt=n(DRx,LMy)` and `CPU%=a(Wb)`. The token set changes with features (the Shrp* tokens appear only with auto-filtering), so parse by key.

- **Q1-029** Pacing fields in the line:
  - `FPS=rendered/refresh`; with AppSW it shows 50% of refresh.
  - `Prd` is the prediction time.
  - `Tear` counts tears (compositor too slow).
  - `Early` and `Stale` count per-second events.
  - `Stale2/5/10/max` count runs of consecutive stale frames in the last second.
  - `VSnc` is the swap interval; it is 0 with AppSW. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The Stale2/5/10/max counts are the best cheap hitch detector. Any non-zero Stale5 or Stale10 means a visible hitch even when average FPS looks fine.

- **Q1-030** `Lat` values: >0 means extra-latency frames; 0 means none; -1 is Phase Sync (the default); -2 is fixed-latency phase sync; -3 is phase sync tuned for AppSW. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The CSV counterparts are `phase_sync_mode` and `extra_latency_mode`. Record Lat with every capture, because it changes how you read Stale/Early (see Q1-C5).

- **Q1-031** Clock and thread fields:
  - `CPU4/GPU=2/2` gives the CPU and GPU levels; "4" identifies the CPU core being measured. The next token is CPU/GPU MHz.
  - `OC` is obsolete.
  - `TA` gives thread affinities for the ATW, main and render threads.
  - `SP` gives scheduling priority: F = SCHED_FIFO, N = SCHED_NORMAL. It is set through `XR_KHR_android_thread_settings`; the older `vrapi_SetPerfThread` is deprecated.
  - `Mem` is memory clock, `Free` is free memory, `PLS` is power level (0/1/2), `Temp` is temperatures, `LP` is battery saver.
  - `DVFS` is documented as never enabled at present. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: No published statement found on which SP values a Unity OpenXR app should show for its main and render threads. Record SP in a known-good build and treat any change as a regression signal. [verify on device]

- **Q1-032** GPU timing fields:
  - `TW` is the ATW (TimeWarp) GPU time.
  - `App` is app GPU time.
  - `GD` is boundary (Guardian) GPU time.
  - `CPU&GPU` is reported for Unity and Unreal only. It runs from the start of the render thread's frame to GPU completion. Render-thread CPU time is roughly `CPU&GPU − App`. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S, Unity · Evidence: [doc]
  - Notes: Use `CPU&GPU` minus `App` to catch a render-thread-bound frame. That case looks CPU bound in App T triage, but it is the render thread, not game logic (see Q1-089).

- **Q1-033** Layer, utilisation and latency fields:
  - `LCnt=n(DRx,LMy)`: layer count including system layers; DR is direct-render FPS; LM is merged layers.
  - `GPU%` runs 0–1; above 0.9 means scheduling problems.
  - `CPU%` is the average, with W the worst core.
  - `DSF` is the DPU scaling factor.
  - `CFL=min/max` is compositor frame latency in ms; `ICFLp95` is the p95 of integrated compositor frame latency.
  - `LD` is local dimming (Quest Pro).
  - `SF` is submitted resolution ÷ recommended resolution. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: SF is the quickest way to confirm that `eyeTextureResolutionScale` or dynamic resolution actually reached the compositor.

- **Q1-034** The AppSW (Application SpaceWarp) line looks like `ASW=90, Type=App E=0.022/0.271,D=0.000/0.000`. With AppSW active, FPS shows half of refresh and VSnc is 0. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S with AppSW · Evidence: [doc]
  - Notes: The CSV counterparts are `spacewarp_motion_vector_type`, `spacewarped_frames_per_second` and `extrapolation_factor_*` / `data_extrapolation_factor_*` (2026 CSV).

- **Q1-035** Clock changes appear in XrPerformanceManager lines such as `01-19 16:05:56.196  2817  3566 I XrPerformanceManager: perfmgr: SetClockLevels: Apply pending clock request change: 4,3 -> 3,3`. The fields are timestamp, PID, TID, severity, tag and body. The buffered history can be older than the moment you started reading. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat/ ; https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: A clock drop in the middle of a session that lines up with a stale burst points to DVFS or thermal behaviour, not content.

- **Q1-036** `adb shell setprop debug.oculus.clockStateLogLevel 1` logs, for every CPU and GPU clock change, the Min/Max/Current/Final level and the reason. Level `2` also logs REJECTED and ignored requests; `0` or a reboot turns it off. Example reasons: "Enabling the dynamic resolution boost" (FORCED) and "Clamp to max allowed hardware level." (REJECTED). [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: This is the direct way to see why a requested level (for example `suggestedGpuPerfLevel`) did not take effect.

- **Q1-037** The VrApi-tagged stats line still prints for OpenXR Unity apps. The docs point this way: they describe Lat=-1 Phase Sync as the default and name the OpenXR extension `XR_KHR_android_thread_settings` for SP. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) plus community reports of Lat=-1 in OpenXR Unity logs · Applies to: Quest 2/3/3S, OpenXR apps · Evidence: [community] [verify on device]
  - Notes: No Meta page says outright "this line appears for OpenXR apps". Check once per project with `adb logcat -s VrApi` on the current Horizon OS.

- **Q1-039** Crash triage for VRC Functional.1:
  1. Right after a crash, run `adb logcat > crash.log` and search for `backtrace:`.
  2. If the buffer has rolled over, run `adb bugreport outputfile.zip` (includes tombstones).
  3. Symbolicate with `ndk-stack -sym <project-path>/symbols/arm64-v8a -dump crash.log > stack.log`. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S, IL2CPP arm64 · Evidence: [doc]
  - Notes: The symbols come from Unity's IL2CPP symbol output. Keep the symbols for every build you submit.

- **Q2-065** Capture frame pacing with `adb logcat -s VrApi`, which prints one line per second. Example:
  `FPS=72/72,Prd=38ms,Tear=0,Early=0,Stale=0,Stale2/5/10/max=0/0/0/0,VSnc=1,Lat=-1,...,TW=1.25ms,App=4.49ms,GD=0.00ms,CPU&GPU=12.96ms,LCnt=2(DR72,LM2),GPU%=0.43,CPU%=0.37(W0.50),DSF=1.00,CFL=19.79/21.54,ICFLp95=20.94,SF=1.00,LP=0,DVFS=0` [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Updated Jul 31, 2025. `CPU&GPU` is the time from render-thread start to GPU completion. Subtracting `App` approximates render-thread time.

- **Q2-068** `Lat=` shows the frame-timing mode: above 0 is extra latency mode (value = extra frames), 0 is neither, -1 is default phase sync, -2 is fixed-latency phase sync, -3 is phase sync tuned for AppSW. `VSnc=` is the swap interval: it should be 1, 2 causes half rate, and 0 means AppSW is active. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc] [verify on device]
  - Notes: The page predates FrameSync. How `Lat=` reports under FrameSync is not documented (gap); record it on a v203+ device.

- **Q2-069** Latency fields:
  - `Prd=` is prediction time, from the pose query to photons.
  - `CFL=` is compositor frame latency, min/max over the past second: the part of `Prd` spent in the compositor.
  - `ICFLp95=` is the 95th-percentile integrated compositor latency. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Compare `Prd` before and after frame-timing, Late Latching or refresh changes. Higher frame rate plus Late Latching lowers `Prd`.

- **Q2-056** Reading the current level:
  - OVR Metrics overlay: CPU L / GPU L (also POW L, CPU U, GPU U).
  - VrApi logcat: `CPU4/GPU=a/b` plus clocks.
  - XrPerformanceManager logs: `adb logcat -s VrApi,XrPerformanceManager`, for example "SetClockLevels: Apply pending clock request change: 4,3 -> 3,3".
  - Detailed min/max/current reasons (including REJECTED and FORCED clamps): `adb shell setprop debug.oculus.clockStateLogLevel 1` (or 2); reset with 0. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: In-app, the OVRPlugin `PerfMetrics` fields `Device_CpuClockLevel_Int` and `Device_GpuClockLevel_Int` (and the clock-frequency fields) have been deprecated since OVRPlugin 1.68.0, per the SDK 207 source. No documented runtime replacement was found (gap). App/compositor CPU/GPU times and utilization are still in `PerfMetrics`.

### 9.3 MQDH Performance Analyzer and its Perfetto integration

- **Q1-040** MQDH Device Manager > Device Actions has "Install OVR Metrics Tool", a "Metrics HUD" toggle and a "Metrics Recording" toggle; the "..." menu shows recorded files. Uninstall the tool with `adb uninstall com.oculus.ovrmonitormetricsservice`. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Page updated Apr 8, 2026. No current MQDH version number found on the pages read.

- **Q1-041** The Performance Analyzer starts with the play button. Turn off the Casting toggle to reduce overhead. It has 12 modules: VRCs, CPU, GPU, GPU Memory Access, GPU Render Pipeline Stats, Vertex Shading Stats, Fragment Shading Stats, GPU Misc. Shader Unit Stats, Frame Rate, Rendering Config, Timings, and Memory. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Casting costs frame time; VRC.Quest.Performance.1 explicitly allows slight dips while streaming or recording. Never judge VRC compliance with casting on.

- **Q1-042** Performance flags use thresholds you set under the gear icon. The Live button returns the view to real time. The Logs pane is expensive, so filter it. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Set the flag thresholds to the refresh-rate budget you ship at. The docs give no default; the Runtime Optimizer uses 14.2 ms (see Q1-C6).

- **Q1-043** MQDH Perfetto settings:
  - Perfetto Settings Preference: General, or a Custom JSON TraceConfig.
  - Auto open trace, Trace duration, Trace buffer size, GPU Trace buffer size.
  - CPU Scheduling, ATrace Categories, ATrace Apps, TrackEvent.
  - XR Runtime Metrics, GPU Metrics, GPU Render Stage Trace, and "Enable high precision GPU render stage tracing".
  - TrackEvent Config: Process Name Filter (and Regex), Disabled/Enabled Categories, Disabled/Enabled Tags.
  - Callstack Sampling Config.
  
  Traces are saved under File Manager > MQDH Files > Perfetto. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ ; https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: A buffer that is too small silently drops data. Meta's advice is to size the buffer for the workload and keep traces short.

- **QUEST-GF1-005** Since GDC 2026 (Mar 10, 2026), MQDH ships a Perfetto MCP server that connects AI assistants directly to captured Perfetto traces. MQDH also consolidates OVR Metrics, Perfetto traces, logcat and ADB. Meta also highlighted an Immersive Debugger with AI integration and Horizon OS-specific Unity MCP extensions (`meta_add_camerarig`, `meta_add_interactionrig`, `meta_add_grabbable`, `meta_update_android_manifest`). [T][C]
  - Source: https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ (accessed 2026-09-24) · Applies to: MQDH (Windows/Mac), Quest 2/3/3S · Evidence: [doc]
  - Notes: Relevant to the reader's agent workflow: an agent can query MQDH traces through MCP instead of parsing exported files. The blog gives no MQDH version and no MCP tool list, so check the installed MQDH release notes. The SQL approach in Q1-055 still works on exported traces.

### 9.4 Perfetto capture on Quest

- **Q1-044** Unity (and Unreal) emit only ATrace events, not Perfetto TrackEvent. The Unity package name must be in MQDH's ATrace Apps field, or the trace will have no Unity markers. Meta recommends filling this field for every app. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (accessed 2026-09-24) · Applies to: Unity 2021.3–6.x; Quest 2/3/3S · Evidence: [doc]
  - Notes: Page updated Sep 3, 2026. This is the most common reason an "empty" Unity Perfetto trace has no PlayerLoop slices.

- **Q1-045** Custom `ProfilerMarker` scopes show up in Perfetto, but only in a Development Build, which is what makes the instrumentation emit at runtime. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (accessed 2026-09-24) · Applies to: Unity; Quest 2/3/3S · Evidence: [doc]
  - Notes: A Development Build changes timing (it includes profiler hooks). Use it to find where time goes, and a non-dev build plus OVR Metrics CSV to measure the final numbers.

- **Q1-046** To capture GPU render stages:
  1. In Perfetto Settings, turn on GPU Render Stage Trace and "Enable high precision GPU render stage tracing".
  2. Choose GPU traces > Enable from the MQDH menu.
  3. Run the app, then click Record. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: High-precision render-stage tracing adds per-surface detail. Keep the capture short; see Q1-043 on buffer sizes.

- **Q1-047** From Horizon OS v51 on, Perfetto supports callstack sampling through `traced_perf`. Settings: Enabled App(s), symbol folder(s) for stripped builds, a trigger (`PerfEvents.Counter` or `PerfEvents.Tracepoint`), and Frequency or Period. For Unity, use a Development Build so symbols are not stripped, or point the symbol folders at the build's symbol output. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S, IL2CPP · Evidence: [doc]
  - Notes: This lets you sample release builds by supplying symbols from your PC, which is the closest you can get to shipping timing.

- **Q1-048** Capturing from the command line. This comes from a 2021 blog post, so treat it as pre-2023 advice.
  - Perfetto is enabled by default in developer mode since OS v27, and VrApi and GPU metrics are emitted as TrackEvents.
  - Config snippet: `data_sources: { config { name: "track_event" } }`, buffers 63488 KB and 2048 KB (DISCARD), `linux.process_stats`, `duration_ms: 10000`.
  - Commands:
    - `adb shell rm -f /data/misc/perfetto-traces/trace`
    - `adb shell perfetto -c - --txt -o /data/misc/perfetto-traces/trace < config.txt`
    - `adb pull /data/misc/perfetto-traces/trace trace.pftrace`
  - GPU metrics need `adb shell ovrgpuprofiler -r` running in the background. [T][C]
  - Source: https://developers.meta.com/horizon/blog/how-to-run-a-perfetto-trace-on-oculus-quest-or-quest-2/ (accessed 2026-09-24) · Applies to: Quest 2 era; still valid Perfetto CLI on Quest 3/3S [verify on device] · Evidence: [doc]
  - Notes: The post is dated Apr 21, 2021. The Perfetto CLI itself is stable, but the Meta data-source names may have changed. Prefer MQDH or `metavr perf capture` (Q1-049) for current configs.

- **Q1-049** Meta's `metavr` CLI (formerly hzdb) captures and analyses traces from the command line.
  - Install: `iwr -useb https://developers.meta.com/horizon/install-cli/windows/ | iex` or `npx -y metavr`. `-d` or the `HZDB_DEVICE` environment variable picks the device.
  - Capture: `metavr perf capture --mode standard|gpu|cpu|memory|lightweight|full|vr/xr|custom --duration <ms, default 5000> --app <pkg> -o <file>`. Optional flags: `--gpu-render-stage`, `--gpu-metrics`, `--cpu-scheduling`, `--xr-runtime`, `--vulkan-layer`, `--extended-scheduling`; `--launch` captures a cold start.
  - Analysis: `metavr perf analyze-trace --focus overview|gpu|cpu|frames|threads --json-out --report-out --asw`.
  - Other commands: `perf query` (SQL), `perf compare`, `perf gpu-counters` (needs at least 20 frames), `perf thread-state`, `perf memory-snapshot --app`, `perf simpleperf classify|record|kernel-overhead`. [T][C]
  - Source: https://github.com/meta-quest/agentic-tools (docs/metavr-cli.md) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] (Meta-published repo; not on developers.meta.com)
  - Notes: This is the best scripting entry point for CI and agents. `--launch` is the tool of choice for measuring cold-start hitches.

- **Q1-056** The names of the XR runtime tracks produced by the "XR Runtime Metrics" option are not documented on any Meta page read. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ ; https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] (absence)
  - Notes: No published list found. To find them: capture with XR Runtime Metrics on, then run `SELECT DISTINCT name FROM counter_track` and `SELECT DISTINCT name FROM track` in trace processor. Record the names per Horizon OS version.

- **QUEST-GF2-010** Meta's GDC 2026 talk walked through a CPU pacing case study in Perfetto. [T][C]
  - Thread layout: Quest reserves roughly half the cores for the system and half for the app. On the Quest 3 trace shown, the app ran on cores 3–5, and the speakers called the top three cores system-earmarked.
  - The bug: FPS averaged 67 instead of 72. Only about 5 of 72 frames per second were bad. In those frames `UnityMain` slept about 3.3 ms in a blocking wait on a system thread that took that long to be scheduled.
  - The method: scan the zoomed-out timeline for frames with large gaps, go to the end of the main-thread sleep, follow the wake-up dependency back to the thread that signalled it, and check that thread's scheduling state.
  - An in-engine profiler would only show the main thread stalled.
  - Source: https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ (Meta talk video (GDC 2026, Mar 10, 2026, David Borel and Neel Bedekar), read from its auto-generated captions; about 33:30–38:10) (accessed 2026-09-24) · Applies to: Quest 3 trace shown; the method applies to Quest 2/3/3S · Evidence: [doc] (Meta talk)
  - Notes: This is the documented way to label a pacing burst as "system contention" rather than content (Q1-094). The core split quoted is from auto-captions ("bottom half... for the app", "top three cores... for the system") and the exact core IDs differ per device. Confirm them in the Perfetto CPU-scheduling track, and do not pin threads by hand (the logcat page recommends against manual affinity). The fix Meta described was in its own OS component. For app code, remove blocking waits on the main thread (`JobHandle.Complete` on long jobs, synchronous I/O).

### 9.5 RenderDoc Meta Fork

- **Q1-057** RenderDoc Meta Fork is at version 68.18 (download page updated Jul 28, 2026) and requires Horizon OS 68 or later. This release adds the command-line options `--frame-number` and `--intent-args` and ships `renderdoc_mcp`. [T]
  - Source: https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S on HzOS 68+ · Evidence: [doc]
  - Notes: `--frame-number` lets you capture a chosen frame from a script, for example the frame just after a scene load.

- **Q1-058** Features:
  - Tile Timeline (Window > Tile Timeline).
  - Per-draw-call trace of hardware counters in Window > Performance Counter Viewer.
  - Vulkan shader stats through `KHR_pipeline_executable_properties`.
  - Vulkan validation.
  
  GL is supported except for shader stats and validation, which are Vulkan-only. Development builds are required. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Page updated Sep 9, 2026. The metric-count limit differs between this page and the download page (Q1-C2).

- **Q1-059** Recommended settings:
  - Timer queries measure per render pass, not per draw, because Adreno renders in tiles.
  - Turn on "Disable TimeWarp on replay".
  - Set Replay optimisation level to Fastest. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Page updated Dec 15, 2024. Do not read per-draw timer queries as absolute cost on a tiler.

- **Q1-060** Capturing:
  - Store builds need JDWP, which requires root on API 34 and later (`persist.debug.dalvik.vm.jdwp.enabled 1`).
  - An app crash during capture usually means it ran out of memory.
  - Profiling replay runs at the Fastest optimisation level. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-capture/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: For practical purposes, profile Development Builds. On a retail headset you cannot capture a store build.

- **Q1-061** The Render Stage view needs a replay context in profiling mode, and it briefly disables the proximity sensor. On Quest 3 with Vulkan multiview, it shows one surface with `multiple rendertargets` = 2 and a foveation scale per view. The Tile Browser gives a per-bin heatmap. The page still has a TODO saying Quest 3/3S behaviour with GL multiview is unverified. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ (accessed 2026-09-24) · Applies to: Quest 3/3S (Vulkan confirmed), GL unverified · Evidence: [doc]
  - Notes: Use the heatmap to find expensive bins, such as a heavy shader or dense overdraw in the view centre, and set foveation or LOD accordingly.

- **Q1-062** Draw-call metrics available include:
  - Clocks.
  - Stalls: % Vertex Fetch Stall, % Texture Fetch Stall, % Stalled on System Memory.
  - Cache: L1 Texture Cache Miss Per Pixel, % Texture L1 Miss, % Texture L2 Miss, % Instruction Cache Miss.
  - Primitives: Pre-clipped Polygon, % Prims Trivially Rejected, % Prims Clipped, Average Vertices/Polygon, Reused Vertices/Second, Average Polygon Area.
  - Shader load: % Shaders Busy, Vertices Shaded, Fragments Shaded, Vertex/Fragment Instructions, Fragment ALU Instructions (Full/Half), Fragment EFU Instructions.
  - Per-element ratios: Textures/Vertex, Textures/Fragment, ALU/Vertex, ALU/Fragment, EFU/Fragment, EFU/Vertex.
  - Time split: % Time Shading Fragments, % Time Shading Vertices, % Time Compute, % Shader ALU Capacity Utilized, % Time ALUs Working, % Time EFUs Working.
  - Texture filtering: % Nearest/Linear/Anisotropic Filtered, % Non-Base Level Textures, % Texture Pipes Busy.
  - Memory: Read Total, Write Total, Texture Memory Read BW, Vertex Memory Read, SP Memory Read (all in bytes), Avg Bytes/Fragment, Avg Bytes/Vertex.
  - Preemption, Avg Preemption Delay.
  
  `lowp` maps to 16-bit (Half). Sort by Clocks first. A known error string is "Failed to retrieve drawcall trace results. Received 0 metrics." [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ ; https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-drawcall/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Both pages are undated. The draw-call page has a TODO about Quest 3 around the 0-metrics error. Whether it is fixed on current firmware is unknown [verify on device]. The Full/Half ALU split is the direct check that HLSL `half` / `min16float` actually compiled to 16-bit.

- **Q1-063** Vulkan shader stats fields:
  - Instruction Count All, ALU 32-bit / 16-bit, Complex, Texture Read, Flow Control, Barrier/Fence, Short/Long Latency Sync.
  - Register footprints, Scratch Memory, I/O components, Shader Processor Utilization %, Memory Read/Write.
  
  Meta's guidance: keep texture read groups below 15, and any scratch memory use means poor performance. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S, Vulkan only · Evidence: [doc]
  - Notes: Page updated Dec 1, 2024. These are the HLSL-level checks: register spills show as scratch, and `half` usage shows in the ALU 16-bit count.

- **Q1-064** RenderDoc for Meta Quest installs agent skills at `C:\Program Files\RenderDocForMetaQuest\.claude\skills`, including optimization-agent, shader-optimization, vertex-optimization, isa-analysis and renderdoccmd-adb-capture. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-ai-tools/ (accessed 2026-09-24) · Applies to: Windows host + Quest 2/3/3S · Evidence: [doc]
  - Notes: Page updated Sep 9, 2026. These pair with `renderdoc_mcp` (Q1-057) for scripted capture and analysis.

### 9.6 ovrgpuprofiler

- **Q1-065** `ovrgpuprofiler` ships with the OS (a community skill puts the binary at `/system_ext/bin/ovrgpuprofiler`). `ovrgpuprofiler -m` lists the real-time metrics, and `-m -v` adds descriptions. Metric IDs are just list positions, so they vary by device and runtime; always resolve names from `-m` on the target device. The doc's example list shows 47 metrics, starting: 1 Clocks / Second, 2 GPU % Bus Busy, 3 % Vertex Fetch Stall, 4 % Texture Fetch Stall, 5 L1 Texture Cache Miss Per Pixel, 6 % Texture L1 Miss, 7 % Texture L2 Miss, 8 % Stalled on System Memory, 9 Pre-clipped Polygons/Second, 10 % Prims Trivially Rejected, 11 % Prims Clipped. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24); https://github.com/tommy-xr/functor/blob/HEAD/.claude/skills/oculus-profiling/SKILL.md (community, Jul 2026) · Applies to: Quest 2/3/3S · Evidence: [doc] (+ [community] for the binary path)
  - Notes: Page updated Sep 9, 2026. Metric counts differ across sources (Q1-C8). Tools must map metric names to IDs at run time.

- **Q1-066** Real-time mode: `ovrgpuprofiler -r4`, `-r"4,5,6"` or `--realtime="4,6"` prints the chosen metrics once per second. Do not request more than 30 metrics at once. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24); https://github.com/o3de/o3de-extras/wiki/Advanced-GPU-profiling-tools-for-Meta-Quest-2 (long form, undated) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Wrap it in `timeout <s>` when scripting so it cannot hang. The counters should be stable on a steady scene; if they are not, the scene has not settled.

- **Q1-067** Detailed profiling mode:
  - `ovrgpuprofiler -e [package]` turns it on for apps started afterwards, so restart the app.
  - It costs about 10% of GPU render time.
  - `-i` shows the current state; `-d` turns it off. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Always run `-d` when finished. A headset left in detailed mode inflates every later measurement by about 10%.

- **Q1-068** Render-stage traces (need detailed mode):
  - `-t` captures 100 ms by default; `-t1.2` sets the length in seconds.
  - `-c` keeps capturing until Ctrl-C and reports in batches.
  - `-l` is low-overhead mode: one line per surface and more accurate timings.
  - `-v` adds per-bin and per-stage detail. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Use `-l` for the per-surface time budget, and `-v` only when working out bin or stage costs.

- **Q1-069** The surface line looks like this (verbatim): `Surface 1 | 1216x1344 | color 32bit, depth 24bit, stencil 0 bit, MSAA 4, Mode: 1 (HwBinning) | 60 128x224 bins ( 60 rendered) | 5.08 ms | 130 stages : Binning : 0.623ms Render : 1.877ms StoreColor : 0.309ms Blit : 0.002ms Preempt : 1.286ms`. Mode values are 0 Direct, 1 HwBinning, 2 SwBinning, 3 HwDirect. Compute work prints `Compute N | ... | x ms`. Bin lines print as `Bin 0 | topLeft 0 x0 | 1x1 logical bins | Fov 8/8`, or `Fov L<x>/<y> R<x>/<y>` for multiview. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Check format, MSAA and mode against what URP is supposed to allocate. An unexpected extra surface at eye resolution is the classic sign of an intermediate texture (see the URP topic).

- **Q1-070** Stage names: Binning, Render, LoadColor, StoreColor, LoadDepthStencil, StoreDepthStencil, Blit, Preempt, Load/Store, Dispatch/GLAsyncCompute, VKQueue, VKRenderClear, VKLoadInput, Workload, RayTracingBuild/Update/Copy, Unknown. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Time in LoadColor or LoadDepthStencil on an eye-buffer surface usually means a render pass loads its attachments when it should clear them or not care. Time in StoreDepthStencil means depth is being written back to memory. Both are bandwidth costs you can remove with load/store actions. That interpretation is not on the Meta page. [verify on device]. The doc's example spends 1.286 ms of a 5.08 ms surface in Preempt. No published guidance found on whether to subtract Preempt when budgeting app cost.

- **Q1-071** Multiview output differs by device:
  - The page's general statement is one surface line per slice, with both eye surfaces added together.
  - Quest 2 (Adreno 650 hardware multiview) prints one surface for both views, with shared bins shown as `135 96x176x2 bins`.
  - Quest 3 and 3S (both Adreno 740v3; the page says 690 MHz on Quest 3 and 492 MHz on Quest 3S) also print one surface for both views. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: For the three target devices, do not double-count: one line is both eyes. The 690/492 MHz figures have no second source [verify on device] (compare the CSV `gpu_frequency_MHz` under load). See Q1-C11.

- **Q1-072** Per-render-stage counters:
  - `-m -t` lists them; `-t3 -s "1,2,3"` captures them, and `-s` requires `-t`.
  - A fixed counter budget applies per pass. Output reports, for example, "Captured 2 metrics, 1 rejected by SoC counter budget". Split a long list across several runs.
  - `-s` is ignored when `-x` is present. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Automation should parse the "rejected" line and re-queue the dropped metrics.

- **Q1-073** Per-draw counters:
  - `-x -m` lists them; capture with `-t3 -x="1,2,3,4,12,15,16,17,18,22,27,28,29,38,49,50"`.
  - Output includes `LRZ State: TestEnabled, WriteEnabled <0x03>`, `Disabled`, or `Unknown(old driver?)`.
  - Per-draw timings are only good for comparing draws within one trace, because per-draw measurement adds pipeline stalls. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: A draw showing LRZ `Disabled` loses Adreno's low-resolution early-Z rejection. The conditions that disable LRZ are Qualcomm-documented, not on this page; this is a lead for the shader and depth topic.

- **Q1-074** Counters to read first:
  - **Which stage owns the frame:** % Time Shading Fragments vs % Time Shading Vertices.
  - **Stalled or computing:** % Shaders Busy high with % Shader ALU Capacity Utilized low means the shaders are stalled.
  - **Where the stalls come from:** % Texture Fetch Stall, % Texture L1 Miss vs % Texture L2 Miss (high L1 miss with low L2 miss means access-pattern thrash, not bandwidth), % Vertex Fetch Stall, % Stalled on System Memory, GPU % Bus Busy.
  - **Work volume:** Vertices Shaded/Second and Fragments Shaded/Second divided by FPS give per-frame counts. Overdraw ≈ fragments per frame ÷ (2 × eye width × eye height). Stage ms ≈ App ms × % time shading ÷ 100. [T]
  - Source: https://github.com/tommy-xr/functor/blob/HEAD/.claude/skills/oculus-profiling/SKILL.md (Jul 2026); counter names at https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [community] (the derivations); [doc] (counter names)
  - Notes: The same community skill claims texture fetches in a vertex shader run twice on Adreno: once in the binning pass's position-only shader and once in the vertex pass. [community] [verify on device]

- **Q1-075** One measured case: setting 8x anisotropic filtering on every mipmapped texture cost 8.9 ms of a 13.8 ms frame on Quest 3 and dropped a terrain scene to 44 fps. The cost showed up as texture fetch stall and texture-pipes-busy, not as a separate counter. [T]
  - Source: https://github.com/tommy-xr/functor/blob/HEAD/.claude/skills/oculus-profiling/SKILL.md (accessed 2026-09-24) · Applies to: Quest 3 · Evidence: [measured] (setup: Functor engine, not Unity; terrain sample; release APK; 72 Hz; counters via `ovrgpuprofiler --realtime`)
  - Notes: The size will differ in Unity/URP. The method carries over: A/B with anisotropic level 1 and watch `percent_texture_anisotropic_filtered` and `percent_texture_fetch_stall`.

- **Q1-076** A 2025 academic study read 72 GPU metrics from ovrgpuprofiler, and 78 on Quest 3S, sampled at 1 Hz. [T]
  - Source: https://arxiv.org/abs/2509.10703 (accessed 2026-09-24) · Applies to: Quest 3 / 3S · Evidence: [community] (paper; see Q1-C8)
  - Notes: This supports the doc's warning that IDs and counts vary with device and runtime.

### 9.7 ADB setprops documented by Meta

- **Q1-077** System property changes are lost on reboot. A reboot is also the reset. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The page is undated. In capture scripts, record `adb shell getprop | grep debug.oculus` next to every capture.

- **Q1-078** `debug.oculus.refreshRate` accepts 60/72/80/90/120 on Quest 2, 72/80/90 on Quest Pro, and 72/80/90/120 on Quest 3/3S. The default is 72. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Use it to test headroom at 90 or 120 Hz without rebuilding. Ship the refresh rate from the app itself.

- **Q1-079** `debug.oculus.cpuLevel` and `debug.oculus.gpuLevel` override the app's levels, for example `adb shell setprop debug.oculus.gpuLevel 4`. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Pin levels for repeatable A/B timing of content changes, because it removes clock-scaling noise. Unpin them (reboot) before any thermal or consistency soak, since the soak must see the real runtime behaviour.

- **Q1-080** `debug.oculus.textureWidth` and `debug.oculus.textureHeight` default to 1440 x 1584 on Quest 2 and 1680 x 1760 on Quest 3/3S. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Lowering these is a fill-bound test that needs no rebuild; compare with the render-scale 0.01 test in Q1-091. The Quest 3 value conflicts with Meta's agentic skill (Q1-C4).

- **Q1-082** Video capture properties: `debug.oculus.fullRateCapture`, `debug.oculus.enableVideoCapture`, `debug.oculus.capture.width` / `debug.oculus.capture.height` (default 1024), `debug.oculus.capture.bitrate` (default 5000000). [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Recording costs performance. Keep it out of measurement runs (VRC Perf.1 allows only slight dips while recording).

- **Q1-083** `debug.oculus.clockStateLogLevel` (0/1/2) is documented on the logcat page (Q1-036). `persist.debug.dalvik.vm.jdwp.enabled 1` is documented on the RenderDoc capture page and needs root. Meta's `metavr device vrruntime get|reset|set` command writes further `debug.oculus.*` properties, mirroring MQDH's "VrRuntime Debug" tool. Its options: `--cpu-level 0-5`, `--gpu-level 0-5` (0 = runtime decides), `--foveation-level 0-4`, `--dynamic-foveation`, `--gfr-mode`, `--subsampled-layout`, `--asw-mode 0-3`, `--swap-interval 0-3`, `--dyn-res-scaler`, `--local-dimming`, `--layer-filter 0-4`, `--layer-auto-filter 0-3`, `--sysprop-debug`, `--color-space`. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ ; https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-capture/ ; https://github.com/meta-quest/agentic-tools (docs/metavr-cli.md) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The exact property names behind the `metavr` flags such as asw-mode, swap-interval and layer-filter are not published on developers.meta.com. Use the CLI rather than guessing property names.

### 9.8 In-app runtime stats hooks

- **Q1-097** `UnityEngine.XR.XRDisplaySubsystem` (XRModule) offers `TryGetAppGPUTimeLastFrame`, `TryGetCompositorGPUTimeLastFrame`, `TryGetDroppedFrameCount`, `TryGetFramePresentCount`, `TryGetMotionToPhoton` and `TryGetDisplayRefreshRate`. All return `bool` and only report what the XR plugin supplies. Times are in seconds. [T][C]
  - Source: https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRDisplaySubsystem.html ; https://docs.unity3d.com/6000.6/Documentation/ScriptReference/XR.XRDisplaySubsystem.TryGetDroppedFrameCount.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6.x · Evidence: [doc]
  - Notes: No published statement found on which of these the Unity OpenXR provider fills in on Quest. Log the `bool` returns once at startup on a device and cache what is available. [verify on device]

- **Q1-098** The legacy `UnityEngine.XR.XRStats` (VRModule) offers `TryGetGPUTimeLastFrame(out float)`, `TryGetDroppedFrameCount(out int)` and `TryGetFramePresentCount(out int)`. Its docs are not marked obsolete in 2021.3, 2022.3 or 6000.2. From 6000.3 on (checked in 6000.3, 6000.4, 6000.6 and 6000.7) they say "UnityEngine.VRModule is deprecated and will be removed in a future version" and point to XRModule APIs. [T][C]
  - Source: https://docs.unity3d.com/2021.3/Documentation/ScriptReference/XR.XRStats.html ; https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRStats.TryGetGPUTimeLastFrame.html ; https://docs.unity3d.com/6000.5/Documentation/ScriptReference/XR.XRStats.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6.2 (not obsolete), 6.3+ (obsolete) · Evidence: [doc]
  - Notes: For new code, use `XRDisplaySubsystem`. Keep an `#if` path only if you must support pre-2021 projects.

- **Q1-099** In the Oculus XR Plugin (`com.unity.xr.oculus` 4.5.x), `Unity.XR.Oculus.Stats.PerfMetrics` offers AppCPUTime, AppGPUTime, CompositorCPUTime, CompositorGPUTime, GPUUtilization, CPUUtilizationAverage, CPUUtilizationWorst, CPUClockFrequency and GPUClockFrequency. It only tracks after `EnablePerfMetrics(true)`, and Unity's docs state it does not work under the OpenXR runtime: all values return 0. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/api/Unity.XR.Oculus.Stats.PerfMetrics.html (accessed 2026-09-24) · Applies to: Oculus XR Plugin (legacy provider) only; not OpenXR · Evidence: [doc]
  - Notes: A project on Unity OpenXR plus the Meta OpenXR feature gets zeros from this API. Use `OVRPlugin.GetPerfMetrics*` (Q1-101) or OVR Metrics instead.

- **Q1-100** The Oculus XR Plugin's `Stats.AdaptivePerformance` offers GPUAppTime, GPUCompositorTime, MotionToPhoton, CPULevel and GPULevel (range 0–3), BatteryLevel, BatteryTemp, PowerSavingMode and AdaptivePerformanceScale. Its `RefreshRate` is obsolete in favour of `Performance.TryGetDisplayRefreshRate`. [T][C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/api/Unity.XR.Oculus.Stats.AdaptivePerformance.html (accessed 2026-09-24) · Applies to: Oculus XR Plugin 4.5.x · Evidence: [doc]
  - Notes: The page does not say whether these work under OpenXR. Given Q1-099, assume they do not until checked [verify on device]. The 0–3 level range is older than today's 0–5 CPU/GPU levels (see `metavr --cpu-level 0-5`), so treat the values as a legacy mapping.

- **Q1-101** In the Meta XR Core SDK (checked v85.0.0), `OVRPlugin.IsPerfMetricsSupported(PerfMetrics)`, `OVRPlugin.GetPerfMetricsFloat(PerfMetrics)` and `OVRPlugin.GetPerfMetricsInt(PerfMetrics)` return nullable values and need OVRPlugin 1.30+. The `OVRPlugin.PerfMetrics` enum values are:
  - `App_CpuTime_Float` = 0, `App_GpuTime_Float` = 1
  - `Compositor_CpuTime_Float` = 3, `Compositor_GpuTime_Float` = 4, `Compositor_DroppedFrameCount_Int` = 5
  - `System_GpuUtilPercentage_Float` = 7, `System_CpuUtilAveragePercentage_Float` = 8, `System_CpuUtilWorstPercentage_Float` = 9
  - `Device_CpuClockFrequencyInMHz_Float`, `Device_GpuClockFrequencyInMHz_Float`, `Device_CpuClockLevel_Int`, `Device_GpuClockLevel_Int` = 10–13, added in 1.32.0 and marked "Deprecated 1.68.0"
  - `Compositor_SpaceWarp_Mode_Int` = 14
  - `Device_CpuCore0UtilPercentage_Float` to `Device_CpuCore7UtilPercentage_Float` = 32–39 [T][C]
  - Source: https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/OVRPlugin.cs (SDK source mirror) (accessed 2026-09-24) · Applies to: Meta XR Core SDK (v85 checked), Unity 2021.3+ · Evidence: [doc] (SDK source)
  - Notes: Check `IsPerfMetricsSupported` per metric at startup. For levels and frequencies, use OVR Metrics or logcat, since those enums are deprecated.

- **Q1-102** Under OpenXR, the `GetPerfMetrics*` calls map to the `XR_META_performance_metrics` extension. At session start, a 2023 Quest runtime logged `OVRPlugin: Supported Performance Metrics: /perfmetrics_meta/...` for `app/gpu_frametime`, `compositor/gpu_frametime`, `compositor/dropped_frame_count`, `compositor/spacewarp_mode`, `device/gpu_utilization`, `device/cpu_utilization_average`, `device/cpu_utilization_worst` and `device/cpu0_utilization` to `cpu7_utilization`. It did not list `app/cpu_frametime` or `app/motion_to_photon_latency`. [T][C]
  - Source: https://github.com/Fb-dtalker/UnityMetaMRC/blob/HEAD/OVRMrclibUnloadLog.log (device log, Aug 2023) (accessed 2026-09-24) · Applies to: Quest (2023 runtime; device not stated) · Evidence: [community] [verify on device]
  - Notes: Pre-2023 or early-2023 data. Run `adb logcat -s OVRPlugin | grep "Supported Performance Metrics"` on the current OS to get the live list.

- **Q1-103** The `XR_META_performance_metrics` spec (Khronos, Meta-authored):
  - Counter paths sit under `/perfmetrics_meta`: `app/cpu_frametime`, `app/gpu_frametime`, `app/motion_to_photon_latency`, `compositor/cpu_frametime`, `compositor/gpu_frametime`, `compositor/dropped_frame_count`, `compositor/spacewarp_mode`, `device/cpu_utilization_average`, `device/cpu_utilization_worst`, `device/gpu_utilization`, and `device/cpu0_utilization` onward.
  - Functions: `xrEnumeratePerformanceMetricsCounterPathsMETA` lists them, `xrSetPerformanceMetricsStateMETA` enables them per session, `xrQueryPerformanceMetricsCounterMETA` reads a counter.
  - The runtime decides the measurement interval. The spec says apps should not change their behaviour based on counter reads. [T][C]
  - Source: https://github.com/KhronosGroup/OpenXR-Docs/blob/main/specification/sources/chapters/extensions/meta/meta_performance_metrics.adoc (accessed 2026-09-24) · Applies to: OpenXR on Quest 2/3/3S · Evidence: [doc]
  - Notes: Because of that clause, use these counters for telemetry, QA gates and debug HUDs, not as the input to adaptive quality. For adaptive quality, use Meta's dynamic resolution path (lead for the dynres topic).

- **Q1-104** `OVRPlugin.GetAppPerfStats()` and `ResetAppPerfStats()` are unsupported on OpenXR in SDK v85: each logs "…is currently unsupported on OpenXR." once and returns an empty value. On the legacy path, `AppPerfStats` held up to 5 `AppPerfFrameStats`, with fields including AppDroppedFrameCount, AppQueueAheadTime, AppCpuElapsedTime, AppGpuElapsedTime, CompositorDroppedFrameCount, CompositorLatency, CompositorCpuStartToGpuEndElapsedTime and CompositorGpuEndToVsyncElapsedTime, plus AdaptiveGpuPerformanceScale. [T][C]
  - Source: https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/OVRPlugin.cs (accessed 2026-09-24) · Applies to: Meta XR Core SDK v85; OpenXR (unsupported) vs legacy VrApi (supported) · Evidence: [doc] (SDK source)
  - Notes: Older sample code that uses these on OpenXR builds reads zeros without failing. Remove it or gate it.

- **Q1-106** Unity's `FrameTimingManager` (turn on Player Settings > "Frame Timing Stats") returns results four frames late; GPU results are read three frames late. Unity 6.0 and later docs mark XR on Vulkan and on OpenGL ES as partial: CPU render-thread frame time and GPU frame time are not supported. On GLES, recording can itself lower GPU performance. [T]
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/frame-timing-manager.html ; https://docs.unity3d.com/6000.4/Documentation/Manual/frame-timing-manager.html (accessed 2026-09-24) · Applies to: Unity 6.0+ (XR row present); 2022.3 docs have no XR row (Q1-C10) · Evidence: [doc]
  - Notes: On Quest, get GPU time from `XRDisplaySubsystem.TryGetAppGPUTimeLastFrame` (if the provider fills it), `OVRPlugin.GetPerfMetricsFloat(App_GpuTime_Float)`, or OVR Metrics, not from `FrameTiming.gpuFrameTime`. `cpuMainThreadFrameTime` is still usable.

### 9.9 Memory and CPU-hotspot tools

- **Q1-095** `gpumeminfo` reports per-process GPU memory: `adb shell gpumeminfo -p $(pidof <process>)`, plus `-l`. Flags: -h, -m, -o, -p, -s, -d, -l, -t. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-gpumeminfo/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Pair it with the CSV columns `app_gpu_physical_MB`, `app_gpu_virtual_MB` and `app_gpu_allocated_percentage` (2026) to watch memory trends in long sessions.

- **Q1-096** Simpleperf for IL2CPP CPU hotspots:
  - Build requirements: IL2CPP, Development Build, and "Debugging (Full)" symbols.
  - Build the symbol cache: `python <ndk>/simpleperf/binary_cache_builder.py -lib <dir>`.
  - Record: `python <ndk>/simpleperf/app_profiler.py --disable_adb_root --ndk_path <ndk> --app <pkg> -r "-g --duration <s> -e cpu-cycles,cache-misses"`.
  - Report: `report_html.py`. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-simpleperf/ (accessed 2026-09-24) · Applies to: Unity IL2CPP; Quest 2/3/3S · Evidence: [doc]
  - Notes: Adding `cache-misses` helps separate memory-bound job code from ALU-bound code.

## 10. Real headroom after compositor and OS overhead

- **Q2-028** Meta's primary headroom rule: design the steady-state workload to nominal CPU level 4 and GPU level 4. That is what the OS sustains under worst-case thermal and battery conditions. Headroom above nominal (for example while charging) should be spent through adaptive scaling, not relied on. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/optimize-performance/ (accessed 2026-09-24) · Applies to: written for Meta VR Glasses but stated in terms of Quest 3 parity. The same levels apply to Quest 2/3/3S · Evidence: [doc]
  - Notes: Updated Sep 19, 2026. The page recommends scaling LOD bias, view distance, MSAA, shadows and post quality from the measured CPU/GPU level. On Quest, SustainedHigh already pins CPU to level 4 (Q2-045).

- **Q2-029** GPU level 5 is opportunistic: "Target GPU level 4 as your maximum GPU budget." Level 5 is granted only with thermal headroom and dynamic resolution, and never for minimum-frame-rate requirements. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: Updated Sep 2, 2026. Level 5 is tied to dynamic resolution so that throttling back to level 4 lowers resolution instead of dropping frames.

- **Q2-050** GPU level 5 requires dynamic resolution. Throttling is much more common at level 5, and dynamic resolution lets a drop back to level 4 lower resolution instead of dropping frames. Resolution rises automatically when level 5 is granted. Battery Saver disables it. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: In XrPerformanceManager clock logs, the level 5 ceiling appears with a reason string about enabling the dynamic-resolution boost.

- **Q3-049** On Quest 2 and later, enabling dynamic resolution is a prerequisite for the highest GPU levels; for example, GPU level 5 on Quest 3 is available only with it on. During thermal events the OS lowers render scale instead of dropping frames. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: A GPU-bound title that leaves dynamic resolution off gives up both the top GPU clock and graceful thermal degradation.

- **Q4-006** GPU level 5 needs Dynamic Resolution enabled. Meta says to treat L5 as an opportunistic bonus: budget against GPU L4, and expect L5 to be withheld under Battery Saver or when thermal headroom is short. Passthrough apps on Quest 3/3S should budget against GPU L2. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ ; https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24)
  - Applies to: Quest 2, 3 and 3S. OVRManager > Enable Dynamic Resolution (off by default), or `OVRManager.instance.enableDynamicResolution`.
  - Evidence: [doc]
  - Notes: The dynamic resolution scale ranges are Quest 2 0.7–1.3 and Quest 3/3S 0.7–1.6 (see Q4-064).

- **Q2-030** Meta publishes no percentage headroom figure (such as "use 80% of budget") after compositor and OS work. The published signals are:
  - Compositor GPU time (`TW=`) was 1.25 ms in the logcat example.
  - The GPU level rises at 87% or more GPU utilization.
  - Scheduling problems are possible above 0.9 `GPU%`.
  - Boundary GPU time (`GD=`) is reported separately. [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc] [verify on device]
  - Notes: No published number found for net app headroom. To measure it:
    - Lock levels (Q2-039), then read `TW`, `GD` and `App` at your shipping layer count.
    - Keep `App` at or below the frame budget minus `TW`, with margin for the next thermal step.
    - `TW` rises with layer count and type; equirect and cylinder layers cost more than quad and projection layers.

- **Q2-039** For stable GPU measurement:
  - Lock clocks with `adb shell setprop debug.oculus.cpuLevel 4` and `adb shell setprop debug.oculus.gpuLevel 4`.
  - Disable foveation with `debug.oculus.foveation.level 0` and `debug.oculus.foveation.dynamic 0`.
  - Optionally stop compositor rendering with `adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SKIP_RENDERING --ei milliseconds 60000`.
  - Lock the camera, disable Guardian, and use swap interval 2 for apps that cannot hold full rate. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: The camera, Guardian and swap-interval steps are from https://developers.meta.com/horizon/blog/how-to-obtain-stable-gpu-measurements-on-quest/ (Apr 2021). Also disable dynamic resolution (Q2-025). Reset all setprops after profiling.

- **Q2-040** Guardian/boundary and compositor work run at higher priority than the app and can preempt the app's GPU work, so the app's GPU time (`App=`) can include preemption. [T]
  - Source: https://developers.meta.com/horizon/blog/how-to-obtain-stable-gpu-measurements-on-quest/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: 2021 blog; the mechanism is still consistent with the compositor docs. This is another reason to keep margin below the budget.

- **QUEST-GF1-003** Meta's GDC 2026 performance session gave practical headroom thresholds. [T][C]
  - Aim for roughly 70% CPU, 80% GPU, and around 5 GB of memory on Quest 3 (about 3.5 GB on Quest 2), building that headroom in early.
  - Keep hitches below 3%; four or more consecutive missed frames are especially noticeable.
  - The same session restated a 72 FPS minimum on Quest 2 and a 13.9 ms budget at 72 FPS.
  - Source: https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ (Meta blog recap of a GDC 2026 talk, Mar 10, 2026) (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 (3S not named) · Evidence: [doc] [verify on device]
  - Notes:
    - This is the only percentage headroom figure Meta has published. It is a talk recap, not a docs page, and it does not say whether "70% CPU" means per-core utilisation (OVR Metrics `CPU U` reports the busiest core, Q1-025) or share of frame time.
    - Read 80% GPU as `gpu_utilization_percentage` ≤ 0.8 at the shipping refresh rate. That sits below the 87% level-raise threshold (Q2-046 / Q2-047 / Q4-003) and the 0.9 scheduling-risk line (Q2-030), so it leaves room for thermal steps.
    - The memory figures sit below the PSS limits (5.75 GiB / 4.4 GiB, Q2-041). Treat them as working targets that leave margin for Low Memory Kill (Q2-042), not as new limits.
    - "Hitches below 3%" lines up with the `stale_frames_consecutive` and Stale2/5/10 signals (Q1-024 / Q2-066). The recap does not define the denominator (frames or seconds).
    - The 72 FPS minimum conflicts with the 60 fps VRC floor (Q1-C1 / Q2-C3; QUEST-GF1-C3).

- **QUEST-GF2-012** A transcript check of the GDC 2026 talk behind QUEST-GF1-003 (the auto-generated captions of Meta's published video). [T][C]
  - The speakers said to stay below about 70% CPU and 80% GPU because scheduling jitter and "sporadic contending tasks" cause dropped frames above roughly 70–80%.
  - On memory, "more than five gigabytes" is available (context: Quest 3), but stay below it because fragmentation and other sporadic allocations compete with the app.
  - Users notice as few as "two or three" dropped frames in a row.
  - The spoken audio never gives the "hitches below 3%" figure or any denominator. That number appears only in the blog recap, so it was probably on a slide.
  - Source: https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ (Meta talk video (GDC 2026, Mar 10, 2026, David Borel and Neel Bedekar), read from its auto-generated captions; about 2:00–5:50) ; https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ (accessed 2026-09-24) · Applies to: Quest 3/3S (talk title "VR Performance Fundamentals for Quest 3/3S"); Quest 2 memory figure is from the recap only · Evidence: [doc] (Meta talk)
  - Notes: This resolves why 70/80 are the thresholds: margin against OS scheduling contention, not thermal. It does not resolve what "utilization" means. The talk does not say whether CPU utilization is busiest-core (OVR Metrics `CPU U`) or aggregate. The 3% denominator stays unpublished: analyzers should report both definitions (Gaps). Still no developers.meta.com docs page states a percentage; the closest docs statements are "Target GPU level 4 as your maximum GPU budget" (Q2-029) and the level-4 steady-state target (Q2-028, QUEST-GF2-004).

## 11. Store performance requirements (VRCs)

- **Q1-084** VRC.Quest.Performance.1 (required; page updated Oct 22, 2025):
  - **Frame rate floor:** the app must render at 60 fps or more.
  - **Refresh rates:** interactive apps use 72, 80, 90, 96, 100 or 120 Hz. 96 and 100 Hz are listed as planned and not yet available on Quest 2/3/3S. Media apps may use 60 Hz where it is supported.
  - **Exceptions:** loading screens and full-screen fades (added 2025-09-02); AppSW at half rate with motion vectors (for example 36 fps at 72 Hz); slight dips while streaming or recording.
  - **Test:** play for the length of the content or 45 minutes, whichever is shorter, and check the OVR Metrics FPS graph for extended periods under 60 fps (under 30 with AppSW).
  - **Revision history:** 2024-07-31 removed App Lab; 2024-08-07 lowered the floor to 60 fps; 2024-10-29 added 120 Hz. [C]
  - Source: https://developers.meta.com/horizon/resources/vrc-quest-performance-1/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S store apps · Evidence: [doc]
  - Notes: 60 fps is the certification floor, not a quality target. An app rendering 60 fps on a 72 Hz display is producing stale frames every second. Other Meta pages still say 72 (Q1-C1). The current requirement text reads "96 Hz, 100 Hz, and 120 Hz not available on all devices" (QUEST-GF1-009).

- **Q1-085** VRC.Quest.Performance.2, the 45-minute thermal throttling test, was retired on 2024-10-16. [C]
  - Source: https://developers.meta.com/horizon/resources/vrc-quest-performance-2/ ; https://developers.meta.com/horizon/resources/publish-quest-req/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Thermal decay over 20–30 minutes is no longer a store gate. Test it yourself with the CSV method in Q1-016.

- **Q1-086** VRC.Quest.Performance.3 (required; updated Jul 31, 2024): head-tracked graphics must appear within 4 seconds of launch, or the app must show a loading indicator. [C]
  - Source: https://developers.meta.com/horizon/resources/vrc-quest-performance-3/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Measure it with `metavr perf capture --launch` (cold start) or logcat timestamps from app start to the first VrApi stats line.

- **Q1-087** VRC.Quest.Performance.4 (recommended; updated Jul 31, 2024): render scale should be at least 85% for most of the experience. It is measured with OVR Metrics "Render Scale Percent", which is the CSV column `render_scale`. [T]
  - Source: https://developers.meta.com/horizon/resources/vrc-quest-performance-4/ ; column name from the CSVs in Q1-012 (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] + [measured]
  - Notes: This sets the floor for dynamic resolution: do not let it sit below 0.85 for long.

- **Q1-088** Other VRCs that touch performance (guidelines page updated Aug 19, 2026):
  - Functional.1: no crashes, freezes or extended unresponsive states.
  - Input.4: stay focus-aware and keep rendering when focus is lost.
  - Packaging.4: use supported SDK and engine versions.
  - Packaging.5: APK under 1 GB, OBB under 4 GB.
  - Packaging.6: 64-bit.
  
  Meta itself calls the downloadable test plans slightly out of date. [C]
  - Source: https://developers.meta.com/horizon/resources/publish-quest-req/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Freezes during loading (long hitches with no loading indicator) can fail Functional.1 or Performance.3 even when average FPS passes.

- **Q2-016** VRC.Quest.Performance.1 (required, immersive apps):
  - Rendering rate must stay at or above 60 fps, or half the refresh rate for portions using App SpaceWarp (AppSW) with good motion vectors.
  - Interactive apps must use 72, 80, 90, 96, 100 or 120 Hz.
  - Loading screens, full-screen fades, system overlays and streaming/recording are exempt.
  - The test runs for the content length or 45 minutes, whichever is shorter. [C]
  - Source: https://developers.meta.com/horizon/resources/vrc-quest-performance-1/ (accessed 2026-09-24) · Applies to: Store apps, all Quest · Evidence: [doc]
  - Notes: Revision 2025-10-22 added 96/100 Hz and said they were not yet available (Q2-C4). The 45-minute test window makes thermal sustainability a certification issue, not only a quality one.

- **Q2-026** VRC.Quest.Performance.4 is recommended, not required: keep render scale at 85% or more for most of the experience, measured with the OVR Metrics Render Scale Percent graph. The render-scale doc says apps whose render scale is too low will not be approved. [T]
  - Source: https://developers.meta.com/horizon/resources/vrc-quest-performance-4/ (accessed 2026-09-24) · Applies to: Store apps, all Quest · Evidence: [doc]
  - Notes: This effectively sets a floor for dynamic-resolution minimums and low tiers. Sitting at 0.7 for long stretches risks review feedback. The VRC page is dated Jul 31, 2024.

- **Q3-003** VRC.Quest.Performance.4 asks apps to run at 85% render scale or higher for most of the experience. Individual, non-consecutive sequences (the example is a boss battle) may dip below. [C]
  - Source: https://developers.meta.com/horizon/resources/vrc-quest-performance-4/ (accessed 2026-09-24) · Applies to: Store apps, all Quest · Evidence: [doc]
  - Notes: The page was updated Jul 31, 2024, when the check became a recommendation instead of a requirement. Measure with the OVR Metrics Tool metric "Render Scale Percent" over the content length or 45 minutes. Apps whose dynamic-resolution minimum is below 85% are responsible for staying at or above 85% most of the time. In practice, treat 0.85 as the floor for sustained play.

- **QUEST-GF1-009** VRC.Quest.Performance.1 wording, checked 2026-09-24 (page last updated 2025-10-22). [C]
  - The requirement text now reads that 96 Hz, 100 Hz and 120 Hz are "not available on all devices", rather than saying 96/100 are unavailable everywhere. The revision-history entry for 2025-10-22 still says 96/100 Hz were added as unavailable today and planned for a future OS.
  - Full revision history:
    - 2024-03-11: AppSW half-rate exception added.
    - 2024-04-25: streaming/recording allowance.
    - 2024-07-31: App Lab removed.
    - 2024-08-07: floor lowered to 60 fps (30 with AppSW).
    - 2024-10-29: 120 Hz added.
    - 2025-09-02: loading screens and fades exempted.
    - 2025-10-22: 96/100 Hz added.
  - Source: https://developers.meta.com/horizon/resources/vrc-quest-performance-1/ (accessed 2026-09-24) · Applies to: Store apps, Quest 2/3/3S · Evidence: [doc]
  - Notes: Together with the refresh-rate page (Q2-010, Aug 2026), 96 and 100 Hz are now shippable on Quest 2/3/3S. Quest Pro supports neither, and only Quest 2/3/3S support 120 Hz. Gate on the runtime's reported rate list (Q2-011, Q2-089). This softens Q2-C4.

- **QUEST-GF2-013** Store field telemetry (Developer Dashboard > Performance Analytics, page updated Feb 14, 2025) uses 60-second aggregation windows. [C]
  - Device Frame Rate: frames rendered over about 60 s.
  - Max Stale Frames: the maximum stale frames about every 60 s.
  - CPU Utilization and GPU Utilization: the maximum over about 60 s.
  - Start Up Time: launch to the 1000th rendered frame.
  - Memory Utilization: physical, virtual and cross-process allocations. The chart is marked temporarily unavailable.
  - Percentiles and means are offered.
  - Only Store immersive apps are covered (not PCVR, 2D, hybrid, web or Spatial SDK apps).
  - At GDC 2026 Meta added that the field data now spans longer windows (weeks), includes stall types, percentiles and moving averages, and compares against category and ecosystem aggregates. [C]
  - Source: https://developers.meta.com/horizon/resources/publish-performance-analytics/ ; https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ (Meta talk video (GDC 2026, Mar 10, 2026, David Borel and Neel Bedekar), read from its auto-generated captions; about 49:00–50:10) (accessed 2026-09-24) · Applies to: Store apps on Quest 2/3/3S · Evidence: [doc]
  - Notes: None of these metrics is a VRC. They show thermal decay and configuration-specific stalls from real users that QA misses. Max Stale Frames per 60 s is the closest field analogue to a hitch rate. To match it, an OVR Metrics CSV analyzer can emit per-60-s maxima of `stale_frame_count` next to p95/p99 frame time. "Start Up Time to 1000th frame" is a documented cold-start metric to track shader or PSO warm-up work against (QUEST-GF1-004).

## 12. OVR Metrics Tool CSV column format

- **Q1-005** The names accepted by `--es stat <stat>` are the CSV column names. The documented list is:
  - `available_memory_MB`, `app_pss_MB`
  - `battery_level_percentage`, `battery_temperature_celcius`, `battery_current_now_milliamps`, `sensor_temperature_celcius`
  - `power_current`, `power_level_state`, `power_voltage`, `power_wattage`
  - `cpu_level`, `gpu_level`, `cpu_frequency_MHz`, `gpu_frequency_MHz`, `mem_frequency_MHz`
  - `minimum_vsyncs`, `extra_latency_mode`, `average_frame_rate`, `display_refresh_rate`, `average_prediction_milliseconds`
  - `screen_tear_count`, `early_frame_count`, `stale_frame_count`, `maximum_rotational_speed_degrees_per_second`
  - `foveation_level`, `eye_buffer_width`, `eye_buffer_height`
  - `app_gpu_time_microseconds`, `timewarp_gpu_time_microseconds`, `guardian_gpu_time_microseconds`
  - `cpu_utilization_percentage`, `cpu_utilization_percentage_core0` to `cpu_utilization_percentage_core7`, `gpu_utilization_percentage`
  - `spacewarp_motion_vector_type`, `spacewarped_frames_per_second`
  - `app_vss_MB`, `app_rss_MB`, `app_dalvik_pss_MB`, `app_private_dirty_MB`, `app_private_clean_MB`, `app_uss_MB`
  - `stale_frames_consecutive`
  - `avg_vertices_per_frame`, `avg_fill_percentage`, `avg_inst_per_frag`, `avg_inst_per_vert`, `avg_textures_per_frag`
  - `percent_time_shading_frags`, `percent_time_shading_verts`, `percent_time_compute`
  - `percent_vertex_fetch_stall`, `percent_texture_fetch_stall`, `percent_texture_l1_miss`, `percent_texture_l2_miss`
  - `percent_texture_nearest_filtered`, `percent_texture_linear_filtered`, `percent_texture_anisotropic_filtered`
  - `vrshell_average_frame_rate`, `vrshell_gpu_time_microseconds`, `vrshell_and_guardian_gpu_time_microseconds` [T][C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: This documented list is behind real 2026 CSVs. It still shows `average_prediction_milliseconds` and leaves out about 50 newer columns (Q1-012, Q1-013, conflict Q1-C9). "celcius" is misspelled in the actual identifiers, so match it exactly.

- **Q1-008** CSV files go to `/sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/`, one file per app launch. Pull them with `adb pull /sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/ .` or with MQDH File Manager. MQDH's "..." menu next to Metrics Recording also lists the recorded files. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ ; https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ ; https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The `adb pull` form is the standard ADB command applied to the documented path. Meta's pages name the path and MQDH, but do not print the pull command itself.

- **Q1-009** File names seen in real captures:
  - 2023: `<package>-YYYYMMDD_HHMMSS.csv`, for example `com.IRLStudios.GymClass-20231015_201503.csv`.
  - 2026: `<package>#<Activity>-YYYYMMDD_HHMMSS.csv`, for example `com.samples.passthroughcamera#UnityPlayerGameActivity-20260807_142600.csv` and `com.DefaultCompany.lakedemo#UnityPlayerActivity-20260102_033328.csv`. [C]
  - Source: https://github.com/Raiduy/GAS-publication-figures/blob/main/Raw%20Data/Gym%20Class/com.IRLStudios.GymClass-20231015_201503.csv ; https://github.com/batunii/Arjuna/blob/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_142600.csv (accessed 2026-09-24) · Applies to: Quest 2 (2023 file), Quest 3 (2026 files) · Evidence: [measured] (third-party captures committed to GitHub; the device is inferred from the eye- and front-buffer sizes in the CSV)
  - Notes: The activity suffix tells you which Unity entry point ran: GameActivity or the classic UnityPlayerActivity. Escape the `#` (`%23`) when you handle these files in URLs or shell globs.

- **Q1-010** CSV rows arrive about once per 1000 ms. `Time Stamp` is milliseconds since recording started; observed series were 972, 1972, ... and 1000, 2000, 3000, 4000, 5001. Each row's `average_frame_rate` is the average since the previous row. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ (timestamp in ms; each point averages the prior interval) plus the three GitHub CSVs listed in Q1-009 and Q1-012 (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] + [measured]
  - Notes: A 1 Hz average cannot show a single-frame hitch. For consistency [C] work, use the per-interval counters (`stale_frame_count`, `stale_frames_consecutive`, `max_repeated_frames`, `skipped_frames`, `shader_hitches`) and use Perfetto for frame-level pacing. For each segment, compute p95/p99 of `app_gpu_time_microseconds` across rows rather than trusting average FPS.

- **Q1-012** The CSV header changes between tool versions, so parse by column name and never by position. Observed column counts:
  - 2023 Quest 2 capture: 89 columns.
  - Jan 2026 Quest 3 capture: 134 columns.
  - Aug 2026 Quest 3 capture: 129 columns.
  
  Full Aug 2026 header (verbatim): `Time Stamp,available_memory_MB,app_pss_MB,battery_level_percentage,battery_temperature_celcius,battery_current_now_milliamps,power_count_neg,power_count_pos,power_current,power_current_neg,power_current_pos,power_level_state,power_voltage,power_wattage,power_wattage_neg,power_wattage_pos,iad_millimeter,shader_hitches,cpu_level,gpu_level,cpu_frequency_MHz,gpu_frequency_MHz,mem_frequency_MHz,minimum_vsyncs,extra_latency_mode,phase_sync_mode,average_frame_rate,display_refresh_rate,average_prediction_microseconds,icfl_mean_microseconds,icfl_stdev_microseconds,slice_headroom_mean_microseconds,slice_headroom_stdev_microseconds,slice_gpu_start_delay_min_microseconds,slice_gpu_start_delay_max_microseconds,screen_tear_count,early_frame_count,stale_frame_count,direct_render_frame_count,total_layer_count,merged_layer_count,maximum_rotational_speed_degrees_per_second,eye_texture_scale_factor,foveation_mode,foveation_level,dynamic_foveation_enabled,eye_tracked_foveation_latency_milliseconds,symmetric_fov,eye_buffer_width,eye_buffer_height,swap_chain_width,swap_chain_height,front_buffer_width,front_buffer_height,app_gpu_time_microseconds,timewarp_gpu_time_microseconds,guardian_gpu_time_microseconds,local_dimming_enabled,cabc_enabled,temporal_dimming_enabled,temporal_dimming_gain,cpu_utilization_percentage,cpu_utilization_percentage_core0..core7,gpu_utilization_percentage,spacewarp_motion_vector_type,spacewarped_frames_per_second,extrapolation_factor_mean,extrapolation_factor_rms,data_extrapolation_factor_mean,data_extrapolation_factor_rms,app_vss_MB,app_rss_MB,app_uss_MB,app_dalvik_pss_MB,app_private_dirty_MB,app_private_clean_MB,app_gpu_physical_MB,app_gpu_virtual_MB,app_gpu_allocated_percentage,stale_frames_consecutive,max_repeated_frames,skipped_frames,face_tracking_*(5),eye_tracking_*(5),hand_tracking_*(5),dynres_recommendation_percentage,dynres_recommendation_width,dynres_recommendation_height,app_frame_throttle,avg_vertices_per_frame,avg_fill_percentage,avg_inst_per_frag,avg_inst_per_vert,avg_frag_inst_per_pixel,avg_vert_inst_per_pixel,avg_textures_per_frag,percent_time_shading_frags,percent_time_shading_verts,percent_time_compute,percent_vertex_fetch_stall,percent_texture_fetch_stall,percent_texture_l1_miss,percent_texture_l2_miss,percent_texture_nearest_filtered,percent_texture_linear_filtered,percent_texture_anisotropic_filtered,vrshell_average_frame_rate,vrshell_gpu_time_microseconds,vrshell_and_guardian_gpu_time_microseconds,render_scale`. [T][C]
  - Source: https://github.com/batunii/Arjuna/blob/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_142600.csv ; https://github.com/DemoySegment/CubemapRendering/blob/HEAD/Demo/com.DefaultCompany.lakedemo%23UnityPlayerActivity-20260102_033328.csv ; https://github.com/Raiduy/GAS-publication-figures/blob/main/Raw%20Data/Gym%20Class/com.IRLStudios.GymClass-20231015_201503.csv (accessed 2026-09-24) · Applies to: Quest 2 (2023), Quest 3 (2026) · Evidence: [measured] (third-party CSV captures; the tool version was not recorded in the files)
  - Notes: Changes from 2023 to 2026:
    - `sensor_temperature_celcius` was dropped.
    - The `screen_*` columns were removed.
    - Added: `shader_hitches`, `phase_sync_mode`, ICFL and slice-headroom columns, layer counts, `max_repeated_frames`, `skipped_frames`, `app_gpu_*_MB`, `dynres_*`, `app_frame_throttle`.
    
    The Jan 2026 file also has `average_prediction_milliseconds`, `cfl_min_microseconds`, `cfl_min_milliseconds`, `cfl_max_microseconds` and `cfl_max_milliseconds`, which the Aug 2026 file does not. None of the three files had a debug-string column.

- **Q1-013** The prediction column changed unit. In 2023 it was `average_prediction_milliseconds`; in Aug 2026 it is `average_prediction_microseconds`; the Jan 2026 file has both. Column suffixes encode units: `_MB`, `_microseconds`, `_milliseconds`, `_percentage`, `_MHz`, `_celcius`, `_milliamps`. [C]
  - Source: the CSVs in Q1-012; https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (the doc list still says milliseconds) (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [measured]
  - Notes: A parser should read units from the suffix and normalise everything to microseconds. It should not assume a unit per stat name.

- **Q1-014** The 2026 CSV columns that matter most for consistency [C] are:
  - `stale_frame_count`, `stale_frames_consecutive`, `max_repeated_frames`, `skipped_frames`
  - `early_frame_count`, `screen_tear_count`, `shader_hitches`
  - `phase_sync_mode`, `extra_latency_mode`
  - `icfl_mean_microseconds`, `icfl_stdev_microseconds`
  - `slice_headroom_mean_microseconds`, `slice_headroom_stdev_microseconds`
  - `slice_gpu_start_delay_min_microseconds`, `slice_gpu_start_delay_max_microseconds`
  - `app_frame_throttle` [C]
  - Source: the CSVs in Q1-012 (accessed 2026-09-24) · Applies to: Quest 3 (seen); Quest 2/3S [verify on device] · Evidence: [measured]
  - Notes: No published definition found for `shader_hitches`, `max_repeated_frames`, `skipped_frames`, `slice_headroom_*`, `slice_gpu_start_delay_*`, `icfl_*` (the CSV form) or `app_frame_throttle`. The Stats Definition Guide predates them. The logcat page does define ICFLp95 and CFL (Q1-033), so those have a documented meaning. To pin down `shader_hitches`, trigger a known first-use shader (new material on screen) and watch the column move. [verify on device]. The Jan 2026 Quest 3 Unity sample showed `shader_hitches` = 1, `phase_sync_mode` = 1, ICFL mean about 16534 µs and slice headroom mean about 1853 µs.

- **Q1-015** The CSV columns that matter most for throughput [T] are:
  - `app_gpu_time_microseconds`, `gpu_utilization_percentage`
  - `cpu_utilization_percentage` and the per-core columns
  - `cpu_level`, `gpu_level`, `cpu_frequency_MHz`, `gpu_frequency_MHz`, `mem_frequency_MHz`
  - `eye_buffer_width`, `eye_buffer_height`, `swap_chain_*`, `render_scale`
  - `dynres_recommendation_percentage`, `dynres_recommendation_width`, `dynres_recommendation_height`
  - `foveation_mode`, `foveation_level`, `dynamic_foveation_enabled`
  - `total_layer_count`, `merged_layer_count`, `timewarp_gpu_time_microseconds` [T]
  - Source: the CSVs in Q1-012; definitions at https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [measured] + [doc]
  - Notes: The Jan 2026 Quest 3 Unity capture showed eye buffer 1680x1760, which matches the documented Quest 3/3S default (Q1-080). It also showed swap chain 2016x1760, front buffer 4128x2208, `eye_texture_scale_factor` = 10, and 4 layers, all 4 merged. No published definition found for `eye_texture_scale_factor` or for why the swap chain is wider than the eye buffer. [verify on device]

- **Q1-017** Real CSVs contain placeholder and garbage values:
  - `battery_current_now_milliamps` = 9999 (2023 Quest 2 file).
  - Face-tracking latency = 999 when the feature is off (2026).
  - `avg_frag_inst_per_pixel` = -67 (Jan 2026 Quest 3). [C]
  - Source: the CSVs in Q1-012 (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [measured]
  - Notes: Filter negative values and 9999/999 placeholders before computing percentiles.

- **Q1-018** A community source says `app_gpu_time_microseconds` is a 16-bit value that clamps at 65,535 µs. [C]
  - Source: https://github.com/Grizfreak/network-data (accessed 2026-09-24) · Applies to: Quest (device not stated) · Evidence: [community] [verify on device]
  - Notes: This only matters for catastrophic frames of 65 ms or more, such as loading hitches. Use Perfetto GPU render-stage tracks for spikes.

- **QUEST-GF1-008** The five tracking-latency groups that Q1-012 abbreviates as `face_tracking_*(5)`, `eye_tracking_*(5)` and `hand_tracking_*(5)` expand to these 15 columns in the Aug 2026 Quest 3 header (verbatim): `face_tracking_overall_latency_milliseconds`, `face_tracking_processing_latency_milliseconds`, `face_tracking_frame_to_frame_latency_milliseconds`, `face_tracking_frames_dropped`, `face_tracking_frames_per_second`, then the same five suffixes for `eye_tracking_` and `hand_tracking_`. The per-core CPU columns are spelled `cpu_utilization_percentage_core0` to `cpu_utilization_percentage_core7`. [T][C]
  - Source: https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_142600.csv (re-fetched during gap-fill) (accessed 2026-09-24) · Applies to: Quest 3 (Aug 2026 capture); other devices [verify on device] · Evidence: [measured] (third-party CSV; tool version not recorded)
  - Notes:
    - The first data row of that capture starts `Time Stamp` = 1000 and has `eye_buffer_width`/`eye_buffer_height` = 0 while `front_buffer_width`/`height` = 4128x2208. A parser must accept zero eye-buffer sizes in early rows; drop the first few rows, or treat 0 as missing.
    - `hand_tracking_*` columns are the only published per-second hand-tracking cost signal found. Use `hand_tracking_frames_dropped` and the latency columns alongside `cpu_level`/`gpu_level` when A/B testing Hand Tracking Frequency (Q4-038).

- **Q1-020** `AppendCsvDebugString(string)` writes text into the last CSV column. Calling it more often than 1 Hz adds new rows with empty metric columns. `SetOverlayDebugString(string)` shows text at the bottom of the HUD; it needs "Show Debug Data" on, updates once per frame, is not saved, and accepts `<color=#hex>` tags. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Unity; Quest 2/3/3S · Evidence: [doc]
  - Notes: Call `AppendCsvDebugString` at segment boundaries (scene loaded, combat start, cutscene). CSV analysis can then report p95 and stale counts per segment. Do not call it every frame, or it will break the 1 Hz row cadence.

## Conflicts

Topic-level conflicts are kept as the topic researchers wrote them. Cross-topic (QX) and gap-fill (QUEST-GF1) conflicts follow.

### From topic Q1

- **Q1-C1** Minimum frame rate for Performance.1: 60 fps or 72 fps.
  - Side A: the VRC.Quest.Performance.1 page (updated Oct 22, 2025) sets the minimum at 60 fps, lowered from 72 on 2024-08-07. https://developers.meta.com/horizon/resources/vrc-quest-performance-1/ [doc]
  - Side B: the Common VRC Failures page (updated May 1, 2026) still says 72 fps. https://developers.meta.com/horizon/resources/publish-common-vrc-failures/ [doc]
  - Side B: the Basic Optimization Workflow (Dec 9, 2024) says "All Meta Quest apps require a minimum of 72 FPS". https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ [doc]
  - Resolution: the VRC page itself is authoritative for certification. Treat 72 Hz at full rate as the quality target and 60 fps as the certification floor.

- **Q1-C2** Number of draw-call metrics in RenderDoc Meta Fork: 48 or 59.
  - The overview page (Sep 9, 2026) says "up to 48" metrics. https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ [doc]
  - The download page for 68.18 (Jul 28, 2026) says "up to 59". https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ [doc]
  - Likely a version difference. Read the real number from the Performance Counter Viewer.

- **Q1-C3** Draw-call target: under 300 or under 100.
  - The Quest Runtime Optimizer Setup category uses under 300. https://developers.meta.com/horizon/documentation/unity/unity-quest-runtime-optimizer/ [doc]
  - Meta's hz-perfetto-debug skill uses under 100 as good, over 200 as a warning and over 500 as critical. https://github.com/meta-quest/agentic-tools [doc] (agent heuristic)
  - Neither is a VRC.

- **Q1-C4** Quest 3 eye-buffer size: 1680x1760 or 1440x1584.
  - The system properties page gives the Quest 3/3S default as 1680x1760, and a Quest 3 CSV confirms 1680x1760. https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc] ; https://github.com/DemoySegment/CubemapRendering/blob/HEAD/Demo/com.DefaultCompany.lakedemo%23UnityPlayerActivity-20260102_033328.csv [measured]
  - Meta's agentic-tools gpu-analysis.md says "1440x1584 per eye (Quest 3)", which is the Quest 2 value. https://github.com/meta-quest/agentic-tools [doc]
  - The agentic-tools value is wrong.

- **Q1-C5** Default latency mode for Unity.
  - The Stats Definition Guide says extra latency mode is on by default in Unity and may also be in Unreal. https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ [doc]
  - The logcat stats page says it is on by default in Unity and Unreal Engine, and also documents Lat=-1 as the default Phase Sync mode. https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc]
  - Current OpenXR Unity apps are reported to show Lat=-1 (Phase Sync), not extra latency. [community] [verify on device]
  - Check Lat and `phase_sync_mode` in every capture instead of assuming.

- **Q1-C6** Frame-time target: 14.2 ms or 13.9 ms.
  - The Runtime Optimizer Quick Perf target is 14.2 ms (about 70 FPS). https://developers.meta.com/horizon/documentation/unity/unity-quest-runtime-optimizer/ [doc]
  - The 72 Hz budget is 13.888 ms. https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ [doc]
  - A frame at 14.0 ms is "green" in the Optimizer but misses vsync at 72 Hz.

- **Q1-C7** How to count stale frames.
  - Meta's hz-perfetto-debug SQL treats any `PlayerLoop` over 11.1 ms as stale. https://github.com/meta-quest/agentic-tools [doc]
  - The Stats Definition Guide shows 72 FPS can coexist with 72 stale frames per second under extra latency; staleness is a compositor property, not CPU frame duration. https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ [doc]
  - Use the runtime's stale counters.

- **Q1-C8** Number of ovrgpuprofiler real-time metrics.
  - Meta's example shows 47 metrics. https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
  - An arXiv paper reports 72 (78 on Quest 3S). https://arxiv.org/abs/2509.10703 [community]
  - A 2026 community skill reports 81 on Quest 3. https://github.com/tommy-xr/functor [community]
  - These fit with the doc's own note that IDs and counts vary by device and runtime. Never hard-code IDs.

- **Q1-C9** OVR Metrics stat names and units.
  - The stat list on the OVR Metrics page (Jun 2026) gives `average_prediction_milliseconds` and lacks about 50 columns. https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc]
  - A real Aug 2026 CSV uses `average_prediction_microseconds` and has 129 columns. https://github.com/batunii/Arjuna/... [measured]
  - Parse by header.

- **Q1-C10** FrameTimingManager support in XR.
  - Unity 6.0+ docs say XR on Vulkan and GLES is partial, with no render-thread or GPU frame time. https://docs.unity3d.com/6000.0/Documentation/Manual/frame-timing-manager.html [doc]
  - The Unity 2022.3 page lists Android Vulkan and GLES as "Yes" with no XR row. https://docs.unity3d.com/2022.3/Documentation/Manual/frame-timing-manager.html [doc]
  - Probably a documentation gap in 2022.3 rather than a behaviour change. [verify on device] on 2022.3.

- **Q1-C11** Multiview surface lines in ovrgpuprofiler, both on https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc].
  - The page's general statement: one surface line per slice for multiview, and you add both eye surfaces.
  - The device-specific statements: Quest 2, Quest 3 and Quest 3S each print one surface line for both views.
  - For the target devices, follow the device-specific lines.

### From topic Q2

- **Q2-C1** Phase Sync setprop name. The Unity page (Feb 2025) uses `debug.Meta.phaseSync`; the native page (2022) uses `debug.oculus.phaseSync`. This is moot on FrameSync builds, but matters for older OS testing.
- **Q2-C2** Default ProcessorPerformanceLevel. The Unity and native CPU/GPU pages (Sep 2, 2026) say SustainedHigh. The Unreal page (https://developers.meta.com/horizon/documentation/unreal/unreal-blueprints-set-cpu-and-gpu-levels/, Apr 17, 2026) says CPU SustainedLow / GPU SustainedHigh, and that Boost behaves like SustainedHigh and is not recommended. The boost page documents Boost as CPU level 8.
- **Q2-C3** Minimum frame rate. unity-perf (Oct 2024) and po-perf-opt-mobile (Dec 2024) say interactive apps need at least 72 FPS. VRC.Quest.Performance.1 (Oct 2025) requires at least 60 fps rendering, or half rate with AppSW, at 72+ Hz refresh.
- **Q2-C4** 96/100 Hz availability. The VRC revision (2025-10-22) says they are not yet available. The refresh-rate doc (Aug 2026) lists them as supported on Quest 2/3/3S.
- **Q2-C5** Quest 3/3S GPU peak clock. Wikipedia says Adreno 740 at 640 MHz; Meta's maximum at GPU level 5 is 599 MHz.
- **Q2-C6** Quest 3S CPU peak. Wikipedia says 2.05 GHz; Meta's shared Quest 3/3S table goes to 2.36 GHz at level 8 (Boost). 2.05 GHz is Meta's level 5, so Wikipedia may be quoting a sustained level.
- **Q2-C7** CPU Boost runtime cap. The boost page lists a condition that Boost has not been active for 80% of runtime, and elsewhere says only 20% of runtime.
- **Q2-C8** Quest 3/3S CPU level 6. The CPU/GPU page lists it as needing CPU Boost, but the boost page says Boost moves level 4 to 8.
- **Q2-C9** Frame-timing status. The Phase Sync docs (Feb 2025) and the logcat `Lat=` definitions describe PhaseSync as current. The FrameSync doc (May 2026) says PhaseSync calls are no-ops on FrameSync devices, and FrameSync is the default from v203.
- **Q2-C10** Unlisted refresh rates. Meta allows rates not returned by the list API (for example 76 Hz). The Unity OpenXR: Meta `TryRequestDisplayRefreshRate` returns false for values not in the supported list.
- **Q2-C11** Extra latency mode. The logcat doc says it is on by default in Unity and Unreal; the Phase Sync doc says it is ignored when Phase Sync is on, and FrameSync now governs timing.
- **Q2-C12** Stale guidance still live:
  - unity-mobile-performance-intro and older pages use the obsolete `OVRManager.cpuLevel/gpuLevel`.
  - The refresh-rate page says Unity auto-adds `quest|quest2` to supportedDevices, while the compatibility-mode page gives `quest2|questpro|quest3|quest3s` as canonical.
- **Q2-C13** DVFS. The logcat doc (Jul 2025) says the `DVFS` field is never enabled. The Meta VR Glasses optimization page (Sep 2026) describes the OS raising and lowering clocks in real time. This probably differs by device; the Quest behavior is unverified.

### From topic Q3

- **Q3-C1** Layer limit. The native compositor-layers page says up to 16 layers per frame, with extras not rendered (https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/, [doc]). OVROverlay says up to 15 per scene, with at most one cylinder and one cubemap (https://developers.meta.com/horizon/documentation/unity/unity-ovroverlay/, [doc]). Assessment: probably consistent if the eye-buffer projection layer takes one of the 16. Budget 15 app layers in Unity and check `LCnt` in logcat.
- **Q3-C2** Dynamic foveation version. The OpenXR changelog lists the dynamic foveation toggle in 1.18.0 (2026-08-04) (https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html, [doc]). The Unity 6.3 support reference requires OpenXR 1.19 or later (https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-support.html, [doc]). The 1.18 foveation page has no dynamic foveation section; the 1.19 page does. Assessment: plan for 1.19+. If on 1.18.0, check for the "Dynamic Foveation (Vulkan)" gear option.
- **Q3-C3** Minimum Unity for AppSW on stock URP. Meta says stock URP supports it from 6000.0.9f1 with RenderGraph, and still recommends its fork (https://developers.meta.com/horizon/documentation/unity/unity-asw/, [doc]). Unity lists Unity 6.1+, OpenXR 1.11.0+ and URP 17.0.3+, with right-handed NDC needing 6000.1.13f1+ and OpenXR 1.15.1+ (https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-prerequisites.html, [doc]). Unity's 6.2 manual says the fork is no longer needed from URP 17.0.3 (https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html, [doc]). Assessment: on 6.0 use Meta's `6000.0/oculus-app-spacewarp` fork. On 6.1+ stock URP works. Keep the fork only if you need transparent-object motion vectors or Meta's extra optimizations.
- **Q3-C4** Foveation on 2022.3. The Unity 6.3 support reference says foveated rendering needs Unity 2022.3+ and URP (https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-support.html, [doc]). The OpenXR docs say the SRP Foveation API is Unity 6+ only and 2022 has only the Legacy/Meta API (https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/foveatedrendering.html, [doc]). Assessment: 2022.3 gets FFR only through the Meta/Legacy API or the Oculus XR plug-in, which does not foveate intermediate targets.
- **Q3-C5** Which resolution knob to use in URP.
  - Meta says to set `XRSettings.eyeTextureResolutionScale` and possibly also the URP asset `renderScale` (https://developers.meta.com/horizon/documentation/unity/os-render-scale/, [doc]).
  - Unity says `eyeTextureResolutionScale` is not supported in URP and recommends `renderViewportScale`, with the asset Render Scale as the expensive alternative (https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html, [doc]).
  - URP source writes the asset or camera renderScale into `scaleOfAllRenderTargets` every camera, with a ±0.05 snap (https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs, [doc]).
  - Meta's sample and dynamic-resolution page still use `eyeTextureResolutionScale` to reallocate.
  
  Assessment: in URP, set allocation through the URP asset renderScale (set `eyeTextureResolutionScale` to the same value for Meta tooling), change it only at loads, and use `renderViewportScale` for anything per frame. [verify on device] by logging the eye texture size.
- **Q3-C6** Subsampled layout recommendation. Meta says it is available on all Quest devices and strongly recommended with Vulkan FFR (https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/, [doc]). Against that: Meta's own warning that it can hurt with post-processing (same page), Unity issue 17355 with right-eye artifacts on Quest 3 only (https://issuetracker.unity.com/issues/17355, [doc]), and the OpenXR note that it adds compositor cost with AppSW (https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/subsampledlayout.html, [doc]). Assessment: default it on for projects that render straight to the eye texture. A/B it on Quest 3 and Quest 2 separately, and on projects with post-processing or AppSW.
- **Q3-C7** Automatic dynamic resolution device list. The OpenXR Automatic Viewport Dynamic Resolution page lists Quest 2 and Quest 3 only (https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/automaticdynamicresolution.html, [doc]). Meta's dynamic resolution page covers "Quest 2 headsets and later" (https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/, [doc]). Assessment: low confidence that this is a real gap. 3S shares Quest 3's SoC and eye buffer, so it is probably an omission. Confirm with `AutomaticDynamicResolutionFeature.IsAutomaticDynamicResolutionScalingSupported()` on a 3S.
- **Q3-C8** FFR plus renderViewportScale. Unity's resolution page says `renderViewportScale` is compatible with FFR, but the post-processing path (URP Dynamic Resolution on the camera) cannot be used with FFR (https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html, [doc]). The support reference states plain compatibility (https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-support.html, [doc]). The URP 17 changelog disables foveation on intermediate passes when `renderViewportScale` is active (https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.6/changelog/CHANGELOG.html, [doc]). Assessment: compatible only when rendering straight to the eye texture. With intermediates, you lose foveation on those passes.
- **Q3-C9** Composition layers under AppSW. Unity lists composition layers as not warped (https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html, [doc]). Meta says Compositor Layer SpaceWarp smooths layer motion and recommends layers for HUD UI (https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/, [doc]). Assessment: probably different mechanisms (no app motion vectors for layer content, but the compositor reprojects layer poses). [verify on device]
- **Q3-C10** HDR and direct eye-texture rendering. Unity's resolution page says URP renders directly to the eye texture "when you enable HDR" (https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html, [doc]). Unity's 6.6 untethered guidance says to disable HDR and that most untethered devices do not support it (https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html, [doc]). A community report says HDR breaks SRP foveation on Quest (https://discussions.unity.com/t/srp-foveated-rendering-on-quest-broken-with-openxr-urp-hdr/1672458, [community]). Assessment: the wording is likely a doc error. Keep HDR off on Quest and confirm direct rendering in Frame Debugger or the Render Graph Viewer.

### From topic Q4

- **Q4-C1** GPU L5 availability for passthrough apps on Quest 3/3S is ambiguous. The level table says L5 is available if GPU L4 is available and trading is +1, "or dynamic resolution is enabled". Read one way, passthrough apps (which have no L4) can't get L5. Read the other way, dynamic resolution alone unlocks L5 even with passthrough. The boost page ties L5 to dynamic resolution without mentioning passthrough. (Q4-005, Q4-006)
- **Q4-C2** Minimum Oculus XR version for MVRR: the Unity 6.6 manual says Oculus XR 4.6+, but the Oculus XR changelog shows the feature added in 4.5.0, and no 4.6 docs exist (404 as of 2026-09-24). (Q4-058, Q4-076)
- **Q4-C3** Quest 3 resolution: Meta's OpenXR settings reference quotes about 2064x2208 per eye (panel resolution) in its Offscreen Rendering Only discussion. Meta's Quest settings page and the 2023 blog use 1680x1760 as the default eye buffer. Memory-saving figures depend on which one is meant. (Q4-059, Q4-061)
- **Q4-C4** Hand-tracking cost: the 2021 v28 notes give hard downclocks (Low: CPU3/GPU3, High: CPU3/GPU2). Current docs say only that high frequency "reserves some performance headroom" and list no hand-tracking row in the level tables. The 2021 figures are probably superseded, but nothing replaces them. (Q4-038, Q4-039)
- **Q4-C5** Meta's XR plugin page (May 2026) recommends Unity OpenXR 1.15.1 and Oculus XR 4.5.1. Unity has since shipped OpenXR 1.18.0 and Oculus XR 4.5.5. (Q4-051, Q4-052)
- **Q4-C6** Symmetric Projection advice differs. Meta's Unity page says enable it for most apps (5–15% gain), while the native page warns it can hurt with post-processing because intermediate passes aren't foveated. (Q4-072, Q4-073)
- **Q4-C7** Optimize Buffer Discards: Meta's OpenXR page presents it as having no downside, but the Oculus XR manual warns it can break depth-sampling effects such as camera stacking. (Q4-059)
- **Q4-C8** Late Latching is documented by Meta as a Meta Quest Support setting under OpenXR, but Unity's OpenXR 1.18 Meta Quest page doesn't list it (Unity documents only `TrySetControllerLateLatchAction`). (Q4-055, Q4-063)
- **Q4-C9** The boost page (Sep 2, 2026) contradicts itself on the runtime cap. The prose says boost can be active for "only 20%" of runtime, while the condition list says boost stops once it has been active for 80% of runtime. (Q4-007)
- **Q4-C10** Depth API on pre-Unity 6: Meta's XR plugin page says the Depth API isn't supported before Unity 6 and SDK v74. The Depth API get-started table lists Unity 2022.3.15f1+ / 2023.2+ with Oculus XR 4.2.0+ and SDK v67 to below v74 as compatible. The likely reconciliation is that it works on older SDKs, but not on the current SDK line with Unity < 6. (Q4-026)
- **Q4-C11** Core SDK v207 release date: the downloads page says it was updated Sep 22, 2026, while npm shows 207.0.0 published 2026-09-24. (Q4-049)
- **Q4-C12** Oculus XR removal status: Unity (Apr 2026) says it is deprecated from 6.5 with no removal date, while Meta says it is "scheduled for removal". (Q4-051)

### Cross-topic conflicts found during synthesis (QX)

These were referenced in sections 1–4, but the synthesis stopped before it wrote the Conflicts section. Gap-fill round 1 rebuilt them from those references and the underlying findings.

- **QX-C1** `XRDisplaySubsystem.scaleOfAllRenderTargets` semantics.
  - Q2-021 (part) called it the display-subsystem equivalent of `renderViewportScale`, meaning no reallocation (Unity scripting reference, [doc]).
  - Q3-005 says it always reallocates, and that `scaleOfAllViewports` is the per-frame knob (https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem-scaleOfAllRenderTargets.html, [doc]).
  - Assessment: resolved in favour of Q3-005 by reading both Unity pages during synthesis.
- **QX-C2** OVRManager dynamic-resolution default range.
  - Q3-050 found no default min/max on the OVRManager v85 reference page (https://developers.meta.com/horizon/reference/unity/v85/class_o_v_r_manager/, [doc]).
  - Q2-024 / Q2-090 read the SDK source: Quest 2/Pro 0.7–1.3, all other headsets 0.7–1.6 (https://raw.githubusercontent.com/darktable-mirror/com.meta.xr.sdk.core/main/Scripts/OVRManager.cs, [doc]). Q4-064 cites the same ranges from Meta's OVRCameraRig page ([doc]).
  - Assessment: the source values stand. Gap-fill round 1 re-fetched the mirror and confirmed `quest2Min/MaxDynamicResolutionScale = 0.7f/1.3f`, `quest3Min/MaxDynamicResolutionScale = 0.7f/1.6f`, and a switch where only `Oculus_Quest_2` and `Meta_Quest_Pro` take the Quest 2 branch (OVRP 1.207).
- **QX-C3** Unity 6.7 status.
  - Meta's dynamic-resolution page lists a fix in `6000.7.0a3+` (Q3-054), and 6000.7 Scripting API docs exist ([doc]).
  - The Unity issue tracker banner advertises the "Unity 6.7 beta" ([doc]).
  - Assessment: 6.7 has not shipped as a final or LTS release, so it is excluded. QUEST-GF1-002 adds the reported alpha date (Jun 25, 2026) and Unity's support page, which still names 6.3 as the latest LTS.
- **QX-C4** PhaseSync as a headroom gauge.
  - Meta's hz-perfetto-debug agent skill reads PhaseSync idle time at the start of `PlayerLoop` as headroom (Q1-050 / Q1-051; https://github.com/meta-quest/agentic-tools, [doc]).
  - FrameSync replaced Phase Sync from v203, and Phase Sync calls are no-ops (Q2-071; https://developers.meta.com/horizon/essentials/framesync/, [doc]).
  - Assessment: unresolved. Whether the `PhaseSync` marker, and its meaning, survive on FrameSync builds is undocumented [verify on device]. On v203+ use `slice_headroom_*` / `icfl_*` CSV columns and stale counts instead (Q1-014).
- **QX-C5** Refresh-rate lists.
  - The refresh-rate page (Aug 27, 2026) lists Quest 2: 60 (media)/72/80/90/96/100/120, Quest 3 and 3S: 72/80/90/96/100/120, Quest 3: 72–207 (240 in developer mode), and Quest Pro: 72/80/90 (Q2-010, Q2-013; https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/, [doc]).
  - The `debug.oculus.refreshRate` row on the system-properties page (re-checked in gap-fill round 1) lists Quest 2: 60, 72, 80, 90, 120; Quest 3 and 3S: 72, 80, 90, 120; Quest Pro: 72, 80, 90 (https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/, [doc]).
  - Assessment: the system-properties page is stale. Trust the refresh-rate page and the runtime's reported list.
- **QX-C6** Quest 3/3S peak GPU clock.
  - Meta's level table tops out at 599 MHz at GPU L5 on Quest 3/3S (Q2-046, [doc]).
  - Wikipedia gives 640 MHz ([community]).
  - The ovrgpuprofiler page gives 690 MHz for Quest 3 and 492 MHz for Quest 3S (Q1-069 area; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/, [doc]).
  - Assessment: the level table is what an app can be granted. The ovrgpuprofiler values are probably tool or driver readouts, and 492 MHz equals the Quest 3/3S GPU L3 clock. Budget on the level table and read `gpu_frequency_MHz` on device.
- **QX-C7** Whether thermal decay is gated by the store.
  - VRC.Quest.Performance.2, the thermal test, was retired 2024-10-16 (Q1-085, [doc]).
  - VRC.Quest.Performance.1 still tests for 45 minutes or the content length, with a 60 fps floor (Q1-084 / Q2-016, [doc]).
  - Assessment: both statements hold. Thermal decay is gated only indirectly, when it drops the app below 60 fps within the Perf.1 session. Anything above that floor (stale bursts, p99 drift) is not gated.
- **QX-C8** Boost duration limit.
  - Meta's boost page allows up to 45 consecutive seconds (Q2-053 / Q4-007; https://developers.meta.com/horizon/documentation/unity/po-quest-boost/, [doc]).
  - Unity's OpenXR performance-settings docs and the Khronos extension say to keep Boost under 30 s (Q2-055; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/performance-settings.html, [doc]).
  - Assessment: the 45 s figure is Meta's runtime limit. The 30 s figure is generic OpenXR guidance. Design Boost windows under 30 s to satisfy both.
- **QX-C9** Meaning of `Lat=` after FrameSync.
  - The logcat and Phase Sync docs say `Lat=-1` verifies Phase Sync (Q2-073; https://developers.meta.com/horizon/documentation/unity/enable-phase-sync/, [doc]).
  - Under FrameSync (v203+), Phase Sync is replaced (Q2-071, [doc]).
  - Assessment: unresolved. What `Lat=` reports under FrameSync is undocumented [verify on device]. Record `Lat=` and `phase_sync_mode` on a v203+ device before writing any rule that depends on them.

### Gap-fill round 1 conflicts (QUEST-GF1)

- **QUEST-GF1-C1** FrameSync opt-out.
  - The announcement blog (Mar 3, 2026) promises an opt-out for Store apps from v203 (https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/, [doc]). UploadVR reports it as `com.oculus.enable_frame_sync` = `false` ([community]).
  - The FrameSync essentials page (May 13, 2026) documents no opt-out and says FrameSync is on for every app on every supported device (https://developers.meta.com/horizon/essentials/framesync/, [doc]).
  - Assessment: the opt-out is at best undocumented and may no longer exist. Do not build a fix around it. See QUEST-GF1-007.
- **QUEST-GF1-C2** Shader Binary Cache status.
  - Meta's GDC 2026 recap (Mar 10, 2026) promotes SBC as the fix for first-run shader stutter (https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/, [doc]).
  - The SBC doc page (updated Aug 7, 2026) is marked deprecated and no longer actively maintained, with a replacement in development (https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/, [doc]).
  - Assessment: the newer page wins. Treat SBC as legacy and keep in-app warm-up (QUEST-GF1-004).
- **QUEST-GF1-C3** Minimum frame rate, again.
  - The GDC 2026 recap restates a "72 FPS minimum on Meta Quest 2" ([doc], blog).
  - VRC.Quest.Performance.1 (rev. 2025-10-22) requires at least 60 fps, or half rate with AppSW (https://developers.meta.com/horizon/resources/vrc-quest-performance-1/, [doc]).
  - Assessment: this is the same split as Q1-C1 / Q2-C3. 60 fps is the certification floor; 72 fps without stale frames is Meta's quality target.
- **QUEST-GF1-C4** Quad Views version in Unity OpenXR.
  - Q3-090 says the Unity OpenXR option was added in 1.17.0-pre.2.
  - The OpenXR changelog shows that 1.17.0-pre.2 (2026-03-03) changed how Single Pass Instanced renders when Quad Views is enabled, while 1.18.0-pre.1 (2026-06-02) "added and documented" the Quad Views option for Foveated Rendering (https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html, [doc]).
  - Assessment: treat OpenXR 1.18.0 as the first release with the documented, user-facing option. Q3-090 is annotated in place.

### Gap-fill round 2 conflicts (QUEST-GF2)

- **QUEST-GF2-C1** Top CPU level under Boost on Quest 3/3S.
  - The "CPU and GPU levels" essentials page lists Boost as CPU 4–6 on Quest 3/3S (and 4–8 on Quest 2/Pro) (https://developers.meta.com/horizon/essentials/cpu-gpu-levels/, [doc]).
  - Meta's boost page (updated Sep 2, 2026) lists Boost as level 4 to 8 on Quest 3/3S at +23% (https://developers.meta.com/horizon/documentation/unity/po-quest-boost/, Q2-053 / Q4-007, [doc]). +23% is 1.92 to 2.36 GHz, the documented L8 clock (Q2-046).
  - A third-party Aug 2026 Quest 3 CSV shows 2361 MHz samples (QUEST-GF2-009, [measured]).
  - Assessment: the clock evidence supports the native page (L8 / 2.36 GHz reachable). The essentials range probably reflects a different level numbering or a typo. Skills should state Boost as "+23% CPU clock on Quest 3/3S" and check `cpu_frequency_MHz`, not quote a level number. [verify on device]
- **QUEST-GF2-C2** MSAA sample count on Quest 3/3S.
  - Meta's GDC 2026 talk and Unity's 6.6 untethered-XR page recommend 2x on XR2 Gen 2 (QUEST-GF2-006, [doc]).
  - Older Meta settings guidance and PST checks in section 8 recommend 4x in the URP asset. The recommended-MSAA API still returns 4 (Q3-069 / Q4-059 context, [doc]).
  - Assessment: the newer sources win for Quest 3/3S: default to 2x and spend any spare GPU time on render scale or TAA. The 4x advice stays the Quest 2 default until measured. Meta itself says the API value of 4 is kept only so existing apps don't break.
- **QUEST-GF2-C3** Cost of the AppSW motion-vector pass.
  - Meta's GDC 2024 Quest 3 blog says to expect about 30% of the (doubled) frame time to go to motion-vector generation (QUEST-GF2-007, [doc]).
  - The native AppSW page calls the low-resolution MV pass nearly free (Q3-063, [doc]).
  - Assessment: both are unmeasured planning statements. The 30% figure is the safer planning number and matches "up to 70%" savings. Measure the MV pass in RenderDoc Meta Fork per title.
- **QUEST-GF2-C4** GPU L3 with passthrough.
  - The native levels page says Quest 3/3S cannot reach GPU L3/L4 with passthrough on (Q2-038 / Q4-001, [doc]).
  - A third-party Aug 2026 Quest 3 CSV of a passthrough scene shows 34 of 565 samples at GPU L3 (492 MHz) (QUEST-GF2-009, [measured]).
  - Assessment: unresolved and weak. The log does not say whether passthrough was active for every sample. Keep the documented cap as the planning rule. [verify on device]: log `gpu_level` continuously with passthrough forced on for 10 minutes under GPU load.
- **QUEST-GF2-C5** Draw-call guidance, a fourth figure.
  - The GDC 2026 talk: under about 500, "not a hard rule", more than 1,000 is possible (QUEST-GF2-005, [doc]).
  - Meta's per-device ranges (Q2-033), the Runtime Optimizer's under-300 and the agent skill's under-100 (Q1-C3).
  - Assessment: none is a limit. Draw-call cost depends on state changes and the graphics API (Vulkan vs GLES). Skills should present 500 as Meta's current rule of thumb for Quest 3/3S and require the CPU render-thread time from a capture before cutting draw calls.

## Gaps and known unknowns

### Gap-fill round 1: spot-check log (2026-09-24)

Each source was re-fetched and compared with the finding. Nothing was removed.

- Q2-041 (PSS limits): confirmed. Quest 2 and Pro 4.4 GiB; Quest 3, 3S and Meta VR Glasses 5.75 GiB (page updated Aug 31, 2026).
- Q2-045 / Q2-046 / Q2-047 (level ranges, clock tables, hysteresis): confirmed. The native page is dated Sep 2, 2026, the default is SustainedHigh, and CPU rises at ≥83% and falls at ≤77%, GPU rises at ≥87% and falls at ≤81%. The page's own sentence also confirms that Quest 3 and 3S cannot access GPU L3/L4 with passthrough on (Q2-038 / Q4-001).
- Q2-017 / Q3-001 and Q2-018 / Q3-002 (eye-buffer table, panel-match scales 1.09/1.24/1.23, Quest 3 at 0.8 and 1.5): confirmed (page dated Jan 9, 2025).
- Q2-033 / Q2-034 (draw-call and triangle ranges): confirmed (page dated Oct 30, 2024).
- Q2-010 / Q2-013 / Q2-014 (refresh rates, extended rates, thermal steps and simulate command, budgets): confirmed (page dated Aug 27, 2026).
- Q1-084 / Q2-016 (VRC Perf.1): partly corrected. The requirement text now reads "96 Hz, 100 Hz, and 120 Hz not available on all devices". Q1-084's "not yet available on Quest 2/3/3S" is kept as the revision-history wording, and the current wording is added as QUEST-GF1-009.
- Q3-079 / Q3-080 / Q3-083 / Q3-084 (layer costs 0.1 ms and 0.6 ms on Quest 2 at L4, 16-layer limit, setprops, 20.67 PPD): confirmed (page dated Mar 11, 2025).
- Q3-062 / Q3-063 (AppSW up to 70%, 368x400 MV target, 18 MB Quest 3 and 14 MB Quest 2): confirmed on the native page (Aug 16, 2024). The memory figures are on the native page, not the Unity page.
- Q3-064 (AppSW Unity requirements): corrected. The Unity page lists 2022.3.15f1, 6000.0.9f1 or 6000.4.0f1 as minimums and recommends "the latest version of a stable Unity release". The finding had called 6000.4.0f1 "the recommended version"; fixed in place.
- Q3-022 (FFR 6.5/11.5/21%, 16% TimeWarp, headline 25%): confirmed. The page's Quest 3 mention refers to the density and tile maps, not the graph, so "device for the graph not stated" stands.
- Q3-025 / Q3-030 / Q3-033 / Q3-060 / Q3-089 (OpenXR changelog versions and dates): confirmed. Q3-090's Quad Views version needed a note (QUEST-GF1-C4).
- Q2-071 / Q2-072 (FrameSync): confirmed. The blog is dated Mar 3, 2026 and the essentials page May 13, 2026. The opt-out is undocumented (QUEST-GF1-007).
- Q2-029 / Q2-051 / Q2-052 / Q2-053 (boost, dual-core, trading, GPU L5): confirmed (page dated Sep 2, 2026), including the self-contradictory 20% and 80% runtime caps.
- Q2-039 (stable-measurement setprops and `COMPOSITOR_SKIP_RENDERING`): confirmed.
- Q4-059 (Optimize Buffer Discards 90 MB per eye / 180 MB stereo at 1680x1760, 66 MB per eye at 1440x1584): confirmed. Q2-027 (part) / Q4-074 (MVRR 3–8%) and Symmetric Projection (5–15%) were also confirmed (page dated May 11, 2026).
- Q2-080 (SystemHeadset enum) and Q2-024 / Q2-090 (dynamic-resolution defaults): confirmed against the re-fetched SDK mirror (OVRP 1.207).
- Q1-092 / Q1-093 (Runtime Optimizer 14.2 ms, 80%/95% colour bands, 25 s, 200 ms per object, 200 objects, `.roz`, menu path Window > Meta > Tools > Quest Runtime Optimizer): confirmed (page dated Jul 31, 2026).
- Q1-089 / Q2-031 (half-rate example `FPS=36/72, Stale=36, GPU%=0.65, App=18.05ms`, 23% cut): confirmed on os-missed-frames. The ts-ovr-best-practices page carries the budget rule and the >65 fps dip tolerance (Q1-090) but not this example; the source note was fixed in place.
- Q1-012 (Aug 2026 CSV header): confirmed against the raw file; the abbreviated groups are expanded in QUEST-GF1-008.
- Baseline: Unity 6.0 LTS through Oct 2026 and 6.3 LTS to Dec 2027 confirmed (QUEST-GF1-001). Oculus XR deprecated from Unity 6.5 confirmed on the package page.

### Resolved or narrowed by gap-fill round 1

- OVR Metrics Tool version: the SDK package is 2.0.1 (Dec 12, 2025; QUEST-GF1-006). The on-device app version is still read with `dumpsys`.
- OVRManager dynamic-resolution defaults (the Q3 gap): resolved from SDK source (Q2-024 / Q2-090; QX-C2).
- Meta Connect/GDC performance talk (the Q1 gap): the GDC 2026 recap was reviewed (QUEST-GF1-003, QUEST-GF1-005, QUEST-GF1-004 notes). No 2025 Connect performance talk was found.
- Net headroom percentage (the Q2 gap): narrowed. Meta's GDC 2026 recap gives about 70% CPU, 80% GPU and about 5 GB (Quest 3) / 3.5 GB (Quest 2) as working thresholds (QUEST-GF1-003). No docs page states a percentage.
- `XR_EXT_performance_settings` on Horizon OS: community evidence only (QUEST-GF1-010).
- Unity 6.7: confirmed not shipped (QUEST-GF1-002).

### Gap-fill round 2: spot-check log (2026-09-24)

Each source was re-fetched (Meta pages from their CMS page data, the GDC 2026 talk from its caption track) and compared with the finding. One finding was corrected, and nothing was removed.

- Q2-072 (FrameSync forum note): **fixed**. The forum post (thread 1368725, read through Wayback 20260417023528) reports adding `enable_frame_sync=false` "just in case", not a successful opt-out. The reply is from a Start-program partner, not Meta staff. The note was reworded in place (QUEST-GF2-001).
- Q3-079 (layer cost 0.1 ms per layer, 0.6 ms fullscreen, Quest 2 at L4): confirmed (page still dated Mar 11, 2025). No Quest 3/3S figure has been added since.
- Q2-045 / Q2-046 / Q2-047 (level ranges, clock table, hysteresis): confirmed again (Sep 2, 2026). The essentials levels page disagrees on the Boost range (QUEST-GF2-C1).
- Q2-049 / Q2-048 (level availability under passthrough): confirmed. Third-party CSV data partly disagrees (QUEST-GF2-C4).
- Q2-053 / Q4-007 (Boost 4 to 8, +64% / +23%, 45 s, the 20%/80% contradiction): confirmed.
- Q2-041 (PSS limits): confirmed (Aug 31, 2026).
- Q1-092 (Runtime Optimizer 14.2 ms, 80%/95%, about 25 s, v78): confirmed.
- Q2-009 / Q2-013 (refresh rates, extended rates, budgets 4.8/4.2 ms, `forceDisplayScaling`): confirmed (Aug 27, 2026).
- Q3-063 (368x400 MV target, 18 MB / 14 MB): confirmed. The "almost free" wording now carries a conflict (QUEST-GF2-C3).
- Q1-084 / QUEST-GF1-009 (VRC 60 fps floor, 45-minute test, revision wording): confirmed.
- Q2-017 / Q2-088 (eye-buffer sizes, panel-match scales 1.09/1.24/1.23): confirmed.
- Q1-028 (verbatim VrApi logcat line) and Q1-030 / Q2-068 (`Lat=` values -1/-2/-3/>0/0): confirmed on the logcat page (Jul 31, 2025). The native AppSW page's example line shows `Lat=-3`. Neither page mentions FrameSync (QX-C9 stays open).
- QUEST-GF1-003 (recap: 70% CPU, 80% GPU, 5 GB / 3.5 GB, hitches below 3%): the recap text is confirmed word for word. The talk captions confirm 70/80 and "more than five gigabytes" but never say "3%" (QUEST-GF2-012).
- QUEST-GF1-004 (SBC deprecated): confirmed (page still dated Aug 7, 2026). The banner still says a replacement is in development, with no name or date.
- Q2-030 (logcat headroom example): confirmed, with a minor internal inconsistency on the source page. Its example line reads `TW=1.25ms` while its column table shows 1.27 ms. This does not change the finding.

### Resolved or narrowed by gap-fill round 2

- Headroom rationale: narrowed. The talk captions say 70% CPU / 80% GPU are margins against OS scheduling contention (QUEST-GF2-012). Still no developers.meta.com docs page gives a percentage. The closest docs statements are GPU level 4 as the maximum budget (Q2-029) and level 4 as a steady-state target (QUEST-GF2-004).
- FrameSync opt-out: narrowed. Nothing newer than the blog's promise exists, and the forum evidence was weaker than recorded (QUEST-GF2-001; Q2-072 fixed). CSV evidence suggests `phase_sync_mode=4` may mark FrameSync (QUEST-GF2-002).
- Quest 3/3S compositor-layer cost: only an indirect Spatial SDK pixel-cost hint was found (QUEST-GF2-008).

### Still open after gap-fill round 2 (no public source; measure on device)

- FrameSync opt-out effect. Method: on a v203+ Quest 3, sideload two otherwise identical builds, one with `com.oculus.enable_frame_sync` = `false` and one without the key. Record 5 minutes of OVR Metrics CSV and `adb logcat -s VrApi` each, and compare `phase_sync_mode`, `extra_latency_mode`, `Lat=` and p99 `app_gpu_time_microseconds`.
- `Lat=` and the Perfetto `PhaseSync` marker under FrameSync (QX-C9). Method: the same capture, plus a Perfetto trace with the Meta VR data sources enabled. Check whether the PhaseSync slices still appear and which `Lat=` value logcat prints.
- Definition of "hitches below 3%". The captions never say it, and the slide deck is not published. Method: report both candidate ratios from the CSV (stale ÷ rendered frames; seconds with `stale_frames_consecutive` ≥ 4 ÷ total seconds) and the Store-style per-60-s maximum of stale frames (QUEST-GF2-013).
- Hand-tracking cost on Quest 3/3S. No current Meta number exists. The FMM page (Aug 11, 2026) only gives the 60 Hz camera rate (50 Hz on 50 Hz power grids) and the log line `HandTrackingService: ... Processed FPS` for verification. Method: at locked content and fixed levels, A/B controllers-only vs hands at Hand Tracking Frequency Low vs High vs FMM for 10 minutes each. Compare `cpu_level`, `gpu_level`, `app_cpu/gpu_time`, `power_*` and `temperature_*`, and check the time to the first thermal level-down.
- Compositor-layer cost on Quest 3/3S. Method: repeat Meta's Quest 2 method (Q3-079): at fixed levels, add 1..N quad and cylinder layers of known texel size. Read the compositor GPU time from `ovrgpuprofiler` or the Perfetto compositor track, and the headroom change from `GPU%`.
- Shader Binary Cache replacement: the page says it is in development, and no name or date is published. Re-check the page and the Horizon release notes at run time.
- Talk ms figures for the Unity 6.5 Quest shader optimizations (QUEST-GF2-011) come from auto-captions with no device or API stated. Method: A/B a scene in the Meta Quest vs the Android build profile on the same Unity 6.5+ version and compare GPU time in RenderDoc Meta Fork or `ovrgpuprofiler`.

### Still open after gap-fill round 1

Round 2 re-checked every item below. The current status and measurement methods are in "Still open after gap-fill round 2" above. This list is kept as the round-1 record.

- FrameSync opt-out mechanism: undocumented on the current essentials page (QUEST-GF1-C1). To test, build with `com.oculus.enable_frame_sync` = `false` on a v203+ device and compare `phase_sync_mode` and `Lat=`.
- Definition and denominator of Meta's "hitches below 3%" (QUEST-GF1-003). Compute it both ways from the CSV (stale frames ÷ rendered frames, and seconds with `stale_frames_consecutive` ≥ 4 ÷ total seconds) and report both.
- Current hand-tracking cost: nothing newer than the 2021 Quest 2 downclock notes (Q4-039, Q4-C4). To measure, A/B Hand Tracking Frequency Low vs High at locked content and read `cpu_level`, `gpu_level`, `hand_tracking_*` and `app_gpu_time_microseconds` (QUEST-GF1-008).
- The replacement for Shader Binary Cache: announced as "in development" with no date.

### From topic Q1

- The current OVR Metrics Tool version number is not published on the pages read; only "1.5" is named, in an undated guide. Read it from `dumpsys package`.
- The current MQDH version is not found in the pages read.
- There are no published definitions for the 2026 CSV columns `shader_hitches`, `max_repeated_frames`, `skipped_frames`, `slice_headroom_*`, `slice_gpu_start_delay_*`, `icfl_*` (CSV form), `app_frame_throttle` and `eye_texture_scale_factor`. Measure them on device.
- Track names from Perfetto's "XR Runtime Metrics" are undocumented. Enumerate them with SQL on the current OS.
- No Meta page states outright that the VrApi per-second stats line prints for OpenXR apps; this is inferred and community-reported.
- The claimed 16-bit clamp of `app_gpu_time_microseconds` at 65,535 µs is unverified.
- ovrgpuprofiler's stated GPU clocks (Quest 3 690 MHz, Quest 3S 492 MHz) have no second source.
- The RenderDoc docs contain TODOs: Quest 3/3S GL multiview behaviour, and whether the "Received 0 metrics" draw-call trace issue persists on Quest 3.
- The overhead of the OVR Metrics HUD, CSV recording, and ovrgpuprofiler real-time mode is not published. Only detailed mode is quantified (about 10%).
- The unit of `time` in `ENABLE_DROPPED_FRAME_SCREENSHOT` is not documented.
- It is not documented which `XRDisplaySubsystem.TryGet*` stats the Unity OpenXR provider fills in on Quest.
- It is not documented whether `Unity.XR.Oculus.Stats.AdaptivePerformance` works under OpenXR.
- The current Horizon OS list of supported `XR_META_performance_metrics` counters is known only from a 2023 log.
- There is no published dip tolerance for 90 or 120 Hz; only 72 Hz (above 65 fps) is given.
- No published per-device thermal thresholds or time-to-throttle numbers were found.
- No Meta Connect or GDC performance-triage talk was reviewed; the web-search budget ran out. That is a follow-up item.
- Unity 6.7: 6000.7 Scripting API docs exist, but LTS status was not checked because this assignment does not own that baseline fact.

### From topic Q2

- **Net frame headroom.** No Meta percentage exists for headroom after compositor, Guardian and OS work. Measure `TW`, `GD` and `App` with locked levels at the shipping layer count.
- **Thermal decay.** No Meta-published FPS, level or clock curve over 20-30 minutes for any Quest. Run the soak protocol in Q2-060.
- **XR_EXT_performance_settings on Horizon OS.** Unconfirmed, as are its thermal notifications through Unity's `XrPerformanceSettingsFeature`.
- **Reading the current CPU/GPU level in-app.** The OVRPlugin level and clock `PerfMetrics` have been deprecated since 1.68.0, and no documented replacement was found.
- **FrameSync.**
  - No official opt-out doc; the manifest value `false` comes only from a forum post.
  - No published overhead numbers.
  - `Lat=` semantics under FrameSync are undocumented.
- **Quest 3S memory.** Type and bandwidth are unverified. Compare `Mem=` and A/B bandwidth-bound scenes.
- **Fill rate and bandwidth.** No published fill-rate, bandwidth or per-frame byte budgets for any Quest.
- **Texture memory.** No per-device texture budget beyond the PSS limit.
- **Battery Saver detection.** No Unity API found; infer it from a refresh-rate change to 72 Hz. `LP=1` is visible only in logcat.
- **Charging.** Whether charging raises sustained clocks on Quest (stated only for the glasses) is unknown.
- **OS version naming.** "HorizonOS v2.7" versus the v201/v203/v205/v207 numbering is ambiguous.
- **Extended refresh rates.** Whether the Unity OpenXR: Meta path accepts Quest 3 rates from 121 to 207 Hz is untested, as is thermal behavior at 207 Hz.
- **Maximum eye-buffer size.** The OpenXR `maxImageRect` limit per device is unpublished.

### From topic Q3

- FFR savings per level on Quest 2 vs Quest 3 vs 3S in a Unity URP project: Meta publishes only one generic graph (Low 6.5%, Medium 11.5%, High 21%, device not stated). To measure, sweep `debug.oculus.foveation.level` with dynamic foveation, dynamic resolution and AppSW off at fixed CPU/GPU levels.
- Adreno 650 vs 740 FDM tile sizes and density steps: not published. The FFR debug maps on the Meta page are Quest 3 only.
- GLES FFR path in current Unity (QCOM texture foveation): no current doc read. Treat as legacy.
- ms or bandwidth cost of MQSR, normal/quality sharpening, supersampling and bicubic filtering on Quest 3/3S: none published.
- Subsampled layout saving in ms or bandwidth: none published.
- AppSW MV-pass GPU cost in ms, and AppSW gains at 90 and 120 Hz on Quest 3/3S: none published.
- Per-layer compositor costs on Quest 3/3S: only Quest 2 figures published (0.1 ms per layer, 0.6 ms fullscreen).
- OVRManager dynamic-resolution default min/max per device: not on the reference page. GitHub code search needs authentication, so the SDK source was not checked.
- Horizon OS dynamic-resolution controller thresholds and hysteresis: not published.
- Whether Quest 3S supports OpenXR Automatic Viewport Dynamic Resolution: not listed.
- XR Composition Layers package layer limit on Quest: not documented. Assumed to be the runtime limit (15 or 16).
- Quad Views real GPU saving on Quest 3 without eye tracking: only the ~50% pixel figure is published.
- MRR and symmetric projection gains specifically in Unity URP: Meta gives 5–15% for symmetric projection in native terms only.
- Unity issue 22353 has no fixed-in version listed for 2021.3 or 2022.3. Issue 17355 (subsampled layout artifacts on Quest 3) has no fix listed.
- A 2021.3/URP12-era community gist reported crashes when changing the viewport scale per frame with OVRManager dynamic resolution. I saw it only in a search snippet (pre-2023) and did not verify it.

### From topic Q4

- No [measured] (reproducible, third-party) numbers were found for any MR feature cost on Quest 2/3/3S. Every number above comes from Meta or Unity documentation.
- Passthrough: no per-frame GPU ms, memory or bandwidth figure. It is also unknown whether runtime-disabling passthrough restores CPU L4 / GPU L3–4 on Quest 3/3S, and what Quest 2 black-and-white passthrough costs. See Q4-021 for the A/B method.
- The level the OS actually grants under `SustainedHigh` when passthrough removes the requested levels is undocumented (Q4-005). Boost behavior under passthrough is also undocumented (Q4-007).
- Depth API: no ms or % for Hard vs Soft vs None. Depth texture resolution and update rate weren't found in the fetched pages. Hand removal (`TrySetHandRemovalEnabled`) cost is undocumented.
- Scene/MRUK: no global-mesh triangle counts, scene load times, EffectMesh or collider generation hitch figures, or MRUK memory numbers.
- Hand, body and multimodal tracking: no current cost numbers. The only figures are the 2021 Quest 2 downclocks (Q4-039).
- PCA: no data on how cost scales with resolution or `MaxFramerate`, or on memory for stereo capture. The community thread "Performance drops when using Passthrough Camera Access API in Unity" (communityforums.atmeta.com, thread 1357225) sits behind a bot-check page and couldn't be read. An earlier third-party report of lower PCA frame rate and higher latency (UploadVR, 2025) couldn't be re-verified in this pass because its URL wasn't retained, so it isn't used as a conflict.
- PST: the default rule list for a given SDK version isn't published; use the Q4-070 diff method.
- `XR_META_temporal_pixel_synthesis` (v203) and the AI Runtime Optimizer: no behavior or cost documentation was found.
- The last Unity OpenXR version that supports 2022.3 isn't pinned down (1.17.x assumed, Q4-052). Neither is the minimum Oculus XR version for 2021.3.
- Quest 3S: every value comes from grouped "Quest 3 and 3S" docs. Nothing 3S-specific (thermals, memory) was found.
- arXiv 2509.18929 ("Native Mixed Reality Compositing on Meta Quest 3...") is a simulation-based feasibility study, not an on-device measurement, so it was excluded as evidence.
- Unity 6.7: only alpha references (6000.7.0a3) exist, so it is excluded.

## Source list

This is the union of the four topic source lists, de-duplicated by URL, plus URLs added in gap-fill round 1 (last block).

- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (Updated Jun 21, 2026)
- https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ (undated; partly pre-2023)
- https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ (undated)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ (Updated Jul 31, 2025)
- https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ (Updated Jul 31, 2025)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat/ (undated)
- https://developers.meta.com/horizon/documentation/unity/ts-adb/ (Updated Jul 11, 2024)
- https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ (Updated Apr 8, 2026)
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (Updated Sep 3, 2026)
- https://developers.meta.com/horizon/blog/how-to-run-a-perfetto-trace-on-oculus-quest-or-quest-2/ (Apr 21, 2021; pre-2023)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (Updated Sep 9, 2026)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ (Updated Sep 9, 2026)
- https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ (Updated Jul 28, 2026)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ (Updated Sep 9, 2026)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-capture/ (Updated Sep 9, 2026)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-drawcall/ (undated)
- https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (undated)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ (Updated Dec 15, 2024)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ (Updated Dec 1, 2024)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-ai-tools/ (Updated Sep 9, 2026)
- https://developers.meta.com/horizon/documentation/unity/ts-gpumeminfo/ (undated)
- https://developers.meta.com/horizon/documentation/unity/ts-simpleperf/ (undated)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (undated)
- https://developers.meta.com/horizon/documentation/unity/os-fixed-foveated-rendering/ (Updated Dec 4, 2024)
- https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (Updated Sep 2, 2026)
- https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ (Updated Dec 9, 2024)
- https://developers.meta.com/horizon/documentation/unity/unity-quest-runtime-optimizer/ (Updated Jul 31, 2026)
- https://developers.meta.com/horizon/resources/publish-quest-req/ (Updated Aug 19, 2026)
- https://developers.meta.com/horizon/resources/vrc-quest-performance-1/ (Updated Oct 22, 2025)
- https://developers.meta.com/horizon/resources/vrc-quest-performance-2/ (Updated Oct 16, 2024; retired)
- https://developers.meta.com/horizon/resources/vrc-quest-performance-3/ (Updated Jul 31, 2024)
- https://developers.meta.com/horizon/resources/vrc-quest-performance-4/ (Updated Jul 31, 2024)
- https://developers.meta.com/horizon/resources/publish-common-vrc-failures/ (Updated May 1, 2026)
- https://github.com/meta-quest/agentic-tools (docs/metavr-cli.md; skills/hz-perfetto-debug/*; skills/hz-simpleperf-debug/*; skills/hz-vr-debug/*) (last push 2026-09-24)
- https://github.com/KhronosGroup/OpenXR-Docs/blob/main/specification/sources/chapters/extensions/meta/meta_performance_metrics.adoc
- Meta XR Core SDK v85.0.0 source, via the mirror https://github.com/elliot170802/Practicas_AR_TSIC/tree/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0 (OVRPlugin.cs, OVRManager.cs, Scripts/Util/OVRMetricsToolSDK.cs, Scripts/Util/OVRMetricsCore.cs)
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRDisplaySubsystem.html
- https://docs.unity3d.com/6000.6/Documentation/ScriptReference/XR.XRDisplaySubsystem.TryGetDroppedFrameCount.html
- https://docs.unity3d.com/2021.3/Documentation/ScriptReference/XR.XRStats.html (also checked 2022.3, 6000.2, 6000.3, 6000.4, 6000.5, 6000.6, 6000.7)
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRStats.TryGetGPUTimeLastFrame.html
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRStats.TryGetDroppedFrameCount.html
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/api/Unity.XR.Oculus.Stats.PerfMetrics.html
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/api/Unity.XR.Oculus.Stats.AdaptivePerformance.html
- https://docs.unity3d.com/6000.0/Documentation/Manual/frame-timing-manager.html (also 2022.3, 6000.4)
- https://github.com/Raiduy/GAS-publication-figures/blob/main/Raw%20Data/Gym%20Class/com.IRLStudios.GymClass-20231015_201503.csv (Quest 2 CSV, 2023)
- https://github.com/DemoySegment/CubemapRendering/blob/HEAD/Demo/com.DefaultCompany.lakedemo%23UnityPlayerActivity-20260102_033328.csv (Quest 3 CSV, Jan 2026)
- https://github.com/batunii/Arjuna/blob/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_142600.csv (Quest 3 CSV, Aug 2026)
- https://github.com/Grizfreak/network-data (claim of a 16-bit App GPU time clamp)
- https://github.com/Fb-dtalker/UnityMetaMRC/blob/HEAD/OVRMrclibUnloadLog.log (2023 device log, supported perf-metrics list)
- https://github.com/tommy-xr/functor/blob/HEAD/.claude/skills/oculus-profiling/SKILL.md (Jul 2026, ovrgpuprofiler workflow + anisotropy measurement)
- https://github.com/o3de/o3de-extras/wiki/Advanced-GPU-profiling-tools-for-Meta-Quest-2 (undated; `--realtime` long form)
- https://arxiv.org/abs/2509.10703 (2025 paper; ovrgpuprofiler metric counts)
- https://developers.meta.com/horizon/essentials/compare-devices/ (Sep 18, 2026)
- https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ (Sep 2, 2026)
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (Sep 2, 2026)
- https://developers.meta.com/horizon/documentation/unreal/unreal-blueprints-set-cpu-and-gpu-levels/ (Apr 17, 2026)
- https://developers.meta.com/horizon/documentation/unity/optimize-performance/ (Sep 19, 2026)
- https://developers.meta.com/horizon/essentials/thermal/ (Sep 15, 2026)
- https://developers.meta.com/horizon/essentials/performance-hardware/ (Sep 15, 2026)
- https://developers.meta.com/horizon/essentials/memory-ram/ (Aug 31, 2026)
- https://developers.meta.com/horizon/documentation/unity/po-memory-ram/ (Aug 12, 2025)
- https://developers.meta.com/horizon/essentials/battery-saver-mode/ (Apr 8, 2026)
- https://developers.meta.com/horizon/documentation/unity/os-battery-saver-mode/ (Jul 29, 2025)
- https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ (Aug 27, 2026)
- https://developers.meta.com/horizon/documentation/unity/os-compatibility-mode/ (Sep 4, 2026)
- https://developers.meta.com/horizon/documentation/unity/os-missed-frames/ (Mar 9, 2026)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ (Dec 15, 2024)
- https://developers.meta.com/horizon/essentials/framesync/ (May 13, 2026)
- https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ (Mar 2026)
- https://developers.meta.com/horizon/documentation/unity/enable-phase-sync/ (Feb 18, 2025)
- https://developers.meta.com/horizon/documentation/native/android/mobile-phase-sync/ (Sep 29, 2022)
- https://developers.meta.com/horizon/documentation/unity/enable-late-latching/ (Dec 6, 2024)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (May 11, 2026)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings/ (May 11, 2026)
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (Aug 6, 2026)
- https://developers.meta.com/horizon/documentation/native/android/os-render-scale/ (Jan 9, 2025)
- https://developers.meta.com/horizon/documentation/native/android/os-compositor/ (Aug 16, 2024)
- https://developers.meta.com/horizon/documentation/unity/unity-perf/ (Oct 30, 2024)
- https://developers.meta.com/horizon/documentation/unity/unity-mobile-performance-intro/ (stale)
- https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (stale, Quest 1)
- https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/
- https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ (Oct 2023)
- https://developers.meta.com/horizon/blog/how-to-obtain-stable-gpu-measurements-on-quest/ (Apr 2021)
- https://raw.githubusercontent.com/darktable-mirror/com.meta.xr.sdk.core/main/Scripts/OVRPlugin.cs
- https://raw.githubusercontent.com/darktable-mirror/com.meta.xr.sdk.core/main/Scripts/OVRManager.cs
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html (deprecation from Unity 6.5)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.5/manual/features/display-utilities.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/performance-settings.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRSettings-eyeTextureResolutionScale.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRSettings-renderViewportScale.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem-scaleOfAllRenderTargets.html
- https://raw.githubusercontent.com/Unity-Technologies/Graphics/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs
- https://raw.githubusercontent.com/Unity-Technologies/Graphics/master/Packages/com.unity.render-pipelines.core/Runtime/XR/XRSystem.cs
- https://issuetracker.unity.com/issues/11487/oculusxr-phasesync-toggle-is-not-respected-and-its-always-enabled
- https://en.wikipedia.org/wiki/Quest_2
- https://en.wikipedia.org/w/index.php?title=Meta_Quest_3&action=raw
- https://en.wikipedia.org/w/index.php?title=Meta_Quest_3S&action=raw
- https://www.uploadvr.com/qhorizon-os-2-7-adds-gamepad-emulation-and-207-hz-display-mode-240-hz-in-dev-mode/
- https://communityforums.atmeta.com/discussions/Questions_Discussions/app-frame-rate-drop/1368725
- https://developers.meta.com/horizon/documentation/unity/os-render-scale/
- https://developers.meta.com/horizon/blog/vr-image-quality-meta-quest-super-resolution/ (Jul 10, 2023)
- https://developers.meta.com/horizon/documentation/native/android/mobile-openxr-composition-layer-filtering/
- https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (updated Apr 7, 2026)
- https://developers.meta.com/horizon/documentation/unity/unity-fixed-foveated-rendering/ (updated Aug 28, 2026)
- https://developers.meta.com/horizon/documentation/native/android/mobile-ffr/ (VrApi, deprecated; page updated Oct 18, 2024)
- https://developers.meta.com/horizon/documentation/unity/unity-eye-tracked-foveated-rendering/
- https://developers.meta.com/horizon/documentation/native/android/os-app-spacewarp/ (updated Aug 16, 2024)
- https://developers.meta.com/horizon/documentation/unity/unity-asw/ (updated May 13, 2026)
- https://developers.meta.com/horizon/documentation/native/android/os-compositor-layers/ (updated Mar 11, 2025)
- https://developers.meta.com/horizon/documentation/unity/unity-ovroverlay/ (updated Aug 28, 2026)
- https://developers.meta.com/horizon/documentation/native/android/os-symmetric-projection/ (updated Apr 6, 2026)
- https://developers.meta.com/horizon/documentation/native/android/os-tile-properties-hint/ (updated Apr 7, 2026)
- https://developers.meta.com/horizon/documentation/native/android/os-stereo-with-foveated-inset/ (updated Sep 14, 2026)
- https://developers.meta.com/horizon/reference/unity/v85/class_o_v_r_manager/
- https://github.com/oculus-samples/Unity-PerformanceSettings
- https://developers.meta.com/horizon/feedback/vr/investigations/2302986490105678/
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-graphics-resolution-scaling.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-resolution-scaling.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-support.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-introduction.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-enable.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-multiview-render-regions.html
- https://docs.unity3d.com/6000.2/Documentation/Manual/xr-graphics-spacewarp.html
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRDisplaySubsystem-foveatedRenderingLevel.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/foveatedrendering.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/foveatedrendering.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/subsampledlayout.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/automaticdynamicresolution.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/compositionlayers.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-prerequisites.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-shaders.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/spacewarp/spacewarp-ui.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/changelog/CHANGELOG.html
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/changelog/CHANGELOG.html
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.6/changelog/CHANGELOG.html
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.core/Runtime/XR/XRSystem.cs
- https://issuetracker.unity.com/issues/22353
- https://issuetracker.unity.com/issues/17355
- https://discussions.unity.com/t/bug-severe-ffr-glitches-performance-loss-with-unity-6-1-6-2-with-urp-vulkan-openxr-on-quest/1677819 (2025)
- https://discussions.unity.com/t/srp-foveated-rendering-on-quest-broken-with-openxr-urp-hdr/1672458 (Jul 30, 2025)
- Meta, CPU and GPU levels: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/
- Unity, OpenXR plugin Meta Quest feature (1.18): https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.18/manual/features/metaquest.html
- Unity Discussions, OculusXR package deprecation (Unity staff): https://discussions.unity.com/t/oculusxr-package-deprecation/1717655
- Excluded as evidence: arXiv 2509.18929 (simulation-based): https://arxiv.org/abs/2509.18929

### Added in gap-fill round 1

- https://unity.com/releases/unity-6/support : Unity 6 Releases & Support, Unity (LTS windows; accessed 2026-09-24)
- https://gamemakers.jp/article/2026_06_26_140306/ : Unity 6.7 alpha release report, GameMakers (Jun 26, 2026) [community]
- https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ : Highlights from Day 1 at GDC 2026: Hands, Agents, Performance & More, Meta (Mar 10, 2026)
- https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ : Shader Compilation / Shader Binary Cache, Meta (updated Aug 7, 2026; deprecated banner)
- https://developers.meta.com/horizon/downloads/package/ovr-metrics-tool-sdk/ : OVR Metrics Tool SDK download, Meta (v2.0.1, Dec 12, 2025)
- https://www.uploadvr.com/meta-horizon-os-framesync-smoother-vr-quest/ : Meta's FrameSync OS Upgrade Promises Visually Smoother VR On Quest, UploadVR (2026) [community]
- https://github.com/hrydgard/ppsspp/commit/5491a05796863c89051bf9569e1d6597ed13f4a2 : PPSSPP commit "OpenXR - Enable level 5 CPU/GPU performance on Quest 2" [community]
- https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_EXT_performance_settings.html : XR_EXT_performance_settings man page, Khronos
- https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_142600.csv : raw Aug 2026 Quest 3 OVR Metrics CSV (third-party capture) [measured]

### Cited in findings but missing from the topic source lists (indexed in gap-fill round 1)

- https://developers.meta.com/horizon/blog/oculus-developer-release-notes-v28/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-bp/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-customization/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/native/android/native-openxr-hand-tracking-frequency-hint/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/enable-multiview/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/fast-motion-mode/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/move-body-tracking/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-best-practices-intro/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-customize-passthrough-passthrough-occlusions/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-advanced-usage/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-get-started/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-depthapi-xr-oculus/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-environment-raycast/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manage-scene-data/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manipulate-scene-visuals/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-multimodal/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-ovrcamerarig/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-passthrough-bp/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-passthrough-gs/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-pca-documentation/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-pca-migration-from-webcamtexture/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-pca-overview/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-upst-overview/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-wide-motion-mode/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/documentation/unity/unity-xr-plugin/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/201.0/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/203.0/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/205.0/ : cited in findings (see finding text for title and date)
- https://developers.meta.com/horizon/install-cli/windows/ : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/2022.3/Documentation/Manual/frame-timing-manager.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/XR.XRDisplaySubsystem-scaleOfAllViewports.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/6000.4/Documentation/Manual/frame-timing-manager.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/6000.5/Documentation/ScriptReference/XR.XRStats.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-build-profile-settings.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-multiview-render-regions.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/camera/image-capture.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/camera/passthrough.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/display-utilities.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/meshing.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/get-started/graphics-settings.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/whats-new.html : cited in findings (see finding text for title and date)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html : cited in findings (see finding text for title and date)
- https://github.com/batunii/Arjuna/ : cited in findings (see finding text for title and date)
- https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/OVRManager.cs : cited in findings (see finding text for title and date)
- https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/OVRPlugin.cs : cited in findings (see finding text for title and date)
- https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/Util/OVRMetricsCore.cs : cited in findings (see finding text for title and date)
- https://github.com/elliot170802/Practicas_AR_TSIC/tree/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/Util : cited in findings (see finding text for title and date)
- https://github.com/tommy-xr/functor : cited in findings (see finding text for title and date)
- https://npm.developer.oculus.com/com.meta.xr.mrutilitykit : cited in findings (see finding text for title and date)
- https://npm.developer.oculus.com/com.meta.xr.sdk.core : cited in findings (see finding text for title and date)
- https://npm.developer.oculus.com/com.meta.xr.sdk.interaction : cited in findings (see finding text for title and date)

### Added in gap-fill round 2

All accessed 2026-09-24.

- Meta, "VR Performance Fundamentals for Quest 3/3S" (GDC 2026 talk video, David Borel and Neel Bedekar, Mar 10, 2026; read from auto-generated captions): https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ [doc]
- Meta essentials, CPU and GPU levels: https://developers.meta.com/horizon/essentials/cpu-gpu-levels/ [doc]
- Meta blog, "Optimizing for success on Meta Quest 3" (GDC 2024 recap, Mar 21, 2024): https://developers.meta.com/horizon/blog/optimizing-for-success-meta-quest-3-gdc/ [doc]
- Meta blog, MQDH compositor layers visibility (Jan 13, 2025): https://developers.meta.com/horizon/blog/mqdh-compositor-layers-visibility-properties-functions-enhance-visual-quality-performance/ [doc]
- Meta, Performance Analytics for Store apps (Feb 14, 2025): https://developers.meta.com/horizon/resources/publish-performance-analytics/ [doc]
- Meta, Spatial SDK runtime guidelines (Oct 6, 2025): https://developers.meta.com/horizon/documentation/spatial-sdk/spatial-sdk-runtime-guidelines/ [doc]
- Unity 6.6 Manual, Configure shader optimizations for Meta Quest: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html [doc]
- Unity 6.5 Manual, the same page: https://docs.unity3d.com/6000.5/Documentation/Manual/xr-meta-quest-graphics-optimization.html [doc] (the 6000.4 URL returns 404)
- Unity 6.6 Manual, untethered XR device optimization: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc]
- Meta Community Forums, "App frame rate drop" thread 1368725 (Wayback capture 20260417023528): https://web.archive.org/web/20260417023528/https://communityforums.atmeta.com/discussions/Questions_Discussions/app-frame-rate-drop/1368725 [community]
- Meta Core SDK 203.0 download page: https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/203.0/ [doc]
- batunii/Arjuna, Quest 3 OVR Metrics captures (Aug 7, 2026), session log: https://github.com/batunii/Arjuna/blob/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/session-log.md [measured]
- batunii/Arjuna passthrough-scene CSV: https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_144005.csv [measured]
- batunii/Arjuna video-scene CSV: https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block3-video/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_150156.csv [measured]
- DemoySegment/CubemapRendering, Quest 3 OVR Metrics CSV (Jan 2, 2026): https://github.com/DemoySegment/CubemapRendering/blob/HEAD/Demo/com.DefaultCompany.lakedemo%23UnityPlayerActivity-20260102_033328.csv [measured]
- Raiduy/GAS-publication-figures, Gym Class OVR Metrics CSV (Oct 15, 2023): https://github.com/Raiduy/GAS-publication-figures/blob/main/Raw%20Data/Gym%20Class/com.IRLStudios.GymClass-20231015_201503.csv [measured]
- Re-read for spot-checks (already listed above): FrameSync essentials and blog, logcat page, native AppSW page, compositor-layers page, boost page, levels page, SBC page, FMM page, VRC Perf.1, GDC 2026 day-1 recap.

<!-- APPEND-MARKER -->
