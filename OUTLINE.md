# Outline

Skill plan for the four plugins. It is built from `research/quest.md`, `research/unity.md`, `research/gles3.md` and `research/arm-mobile-hw.md`, all accessed 2026-09-24. Finding IDs refer to those dossiers. Each skill below owns its topics; other skills link to it and do not repeat its content.

Totals: 33 skills. quest-perf 10, unity-perf 11, gles3-perf 6, arm-mobile-hw-perf 6.

## Decisions made without the user

### Orchestrator decisions

1. **Bundle prefixes.** The prefixes are `quest-`, `unity-`, `gles-` and `xr2-`. Every skill name starts with its bundle prefix.
2. **Description length.** Descriptions run 300-600 characters, with a hard cap of 1024. The key use case comes first. The reason is that Claude Code truncates the skill listing at about 1% of context. This is wider than the 200-400 characters in AGENTS.md; the orchestrator's range wins for this run.
3. **No user at the outline checkpoint.** The user was unavailable at the outline checkpoint. Decisions are therefore listed here at the top, and work proceeds without waiting.
4. **Branch and worktree.** Work happens on branch `claude/finish-skills` in a worktree.
5. **Manifests in scope.** Only the Claude manifests (`.claude-plugin/`) are in scope. Another agent handles the OMP manifests (`.omp-plugin/`).
6. **Tooling location.** Tooling lives in `tools/`.
7. **Plugin versions.** Plugin versions live only in `plugin.json`. They are not repeated in marketplace entries.

### Outline decisions: structure

8. **Skill counts.** Every count is inside its target range:

   | Bundle | Skills | Target |
   |---|---|---|
   | quest-perf | 10 | 8-11 |
   | unity-perf | 11 | 9-12 |
   | gles3-perf | 6 | 5-7 |
   | arm-mobile-hw-perf | 6 | 5-7 |

9. **Split: frame pacing vs levels and thermal.** "Frame pacing, levels and thermal" is split into `quest-frame-pacing` and `quest-levels-thermal`.
   - `quest-frame-pacing`: FrameSync, stale frames, Late Latching, refresh rate.
   - `quest-levels-thermal`: the level system, Boost, dual-core mode, trading, throttling, PLS, Battery Saver.
   - Why: each half has enough Meta-documented content to fill a body. The triggers also differ: "stutter with good average FPS" vs "FPS drops after 10 minutes".
10. **Split: two thermal skills.** Thermals are split between two bundles.
    - `quest-levels-thermal` owns runtime behaviour: levels, the throttling stages, PLS, Battery Saver, and the long-session test protocol.
    - `xr2-bandwidth-power` owns the physics: DRAM energy, power figures, battery-derived draw, and the unpublished thermal envelope.
    - Neither repeats the other.
11. **Merge: bandwidth and thermals in arm-mobile-hw-perf.** These two coverage topics become one skill, `xr2-bandwidth-power`. The arm dossier (§5 and §1.7) treats DRAM traffic as the dominant controllable power cost. The runtime half of thermals already lives in quest-perf, so a separate `xr2-thermals` skill would be a thin wrapper.
12. **Rename: Snapdragon Profiler becomes `xr2-gpu-counters-sdp`.** Its scope widens to Adreno counter interpretation: Qualcomm's healthy ranges, the meaning of each counter, the Adreno Offline Compiler, and driver checks. The dossier's working position is that SDP is unsupported on Quest (A3-067), so a skill only about SDP would be thin. `quest-profiling-toolkit` owns how to run the tools. `xr2-gpu-counters-sdp` owns what the Adreno counters mean.
13. **Merge: GLES capture into `gles-vs-vulkan`.** The GLES capture caveats (§8 of gles3.md) are owned by `gles-vs-vulkan`. They cover:
    - timer queries
    - RenderDoc Meta Fork v68.18 limits
    - SDP unreliability
    - AGI being unsupported
    - GPU Systrace being deprecated

    The main use of a GLES capture is the single-variable API A/B (G1-079). The generic recipes for ovrgpuprofiler, RenderDoc and Perfetto stay in `quest-profiling-toolkit`. A standalone `gles-capture` skill would mostly repeat that toolkit.
14. **Merge: GLES multiview with extensions.** GLES multiview is merged into `gles-extensions-multiview`. On GLES, multiview is the extension OVR_multiview2 plus the multiview MSRTT variant (GLES3-GF2-004). Its GLES-specific content (G2-047 to 055, UUM-102876, OXPB-144, no OpenXR GLES path) is too small for its own skill. The CPU-side draw-call saving from multiview is API-independent, so `unity-draw-calls-batching` owns it.
15. **Split: shaders in unity-perf.** "Shaders and PSO hitches" becomes two skills.
    - `unity-shader-authoring`: throughput. Covers URP HLSL, precision, discard, A2C and keywords.
    - `unity-shader-hitches`: consistency. Covers variants, stripping, PSO/GSC warmup and the Vulkan pipeline cache.
    - Why: the triggers do not overlap ("shader too expensive" vs "hitch on first use"), and each has a large finding set (U3-051 to 097).
16. **Unity's `unity-lighting` covers shadows.** It covers lights, shadows, probes, lightmaps and APV. `unity-urp-settings` keeps only the choice of rendering path (Forward, Forward+ or Deferred) and links to `unity-lighting` for light counts.

### Outline decisions: ownership

17. **CPU/GPU levels and the clock table.**
    - `quest-levels-thermal` owns the level-to-clock table (A1-005 set, Q2-046/047), because apps choose levels, not clocks.
    - `xr2-gen1-vs-gen2` owns the silicon: core types, cluster maximums and the fact that 2.84 GHz is never an app level. It links to the level table and does not copy it.
    - The main-thread cycle budgets per level (A1-026) are owned by `xr2-cpu-threads-neon`.
18. **Tile, GMEM and load/store.** Owned at three layers, each linking downward to the next:
    - `xr2-adreno-architecture` owns the hardware: GMEM, bins, FlexRender, LRZ, UBWC, and the in-tile MSAA resolve.
    - `unity-render-graph-tiling` owns URP and Render Graph load/store and pass merging.
    - `gles-tile-load-store` owns the GLES calls: glClear, glInvalidateFramebuffer and MSRTT.
    - The ovrgpuprofiler surface-line reading rule (G2-009, A3-034) is owned by `quest-profiling-toolkit`.
19. **MSAA.**
    - The choice of MSAA level, and the unresolved 2x vs 4x conflict, are owned by `unity-urp-settings`. The conflict: U2-093 says Meta's numbers are Quest 1 era; A2-017 and A3-020 say 2x is "practically free"; A2-056 has the original-Quest 4x table.
    - The per-API MSAA numbers (UUM-149765) are owned by `gles-vs-vulkan`. The tracker table is internally inconsistent (G2-C9), so skills quote deltas only: on Quest 3/3S, 4x MSAA adds about +3.3 ms on GLES vs +5.0 ms on Vulkan, and the MSAA-off gap is under 1 ms (G2-039 to 041). The Quest 2 4x cost of about +7 ms is cited to gles3.md §3.4.
    - The resolve mechanism is owned by `xr2-adreno-architecture`.
20. **Foveation.** `quest-resolution-foveation` owns FFR and dynamic foveation for all APIs. `gles-extensions-multiview` owns only the QCOM_texture_foveated mechanics and the GLES caveats. The GLES caveats are FFR only on direct swapchain rendering (G2-059 to 061) and the open question KU-10.
21. **Shader compilation.**
    - `unity-shader-hitches` owns PSO/GSC warmup and `vulkan_pso_cache.bin`.
    - `gles-shader-binaries` owns the Android blob cache, glProgramBinary, and the GLES fallback to SVC warmup.
    - Qualcomm's "create pipelines at init" (A2-077) is a Key fact in `unity-shader-hitches`.
22. **Shader cost.** `xr2-shader-cost-model` owns the hardware cost model: fp16 rate, GPRs, waves, cliffs and texture filtering. `unity-shader-authoring` owns how to express it in URP HLSL, and it cites the model without repeating it.
23. **Burst and threads.**
    - `unity-cpu-scripting` owns job-system and Burst usage patterns, GC and IL2CPP.
    - `xr2-cpu-threads-neon` owns core placement, Unity's thread-affinity arguments, job-worker counts, cache/NEON pipeline costs, and the Burst Arm64 targets and FloatMode.
    - Graphics Jobs (Legacy mode, A1-058) and "never ship with Multithreaded Rendering off" (A1-061) are owned by `unity-cpu-scripting`.
24. **Memory.** `quest-budgets-tiers` owns platform memory limits: PSS limits, lmkd, and the headset RAM table. `unity-memory-assets` owns asset-side memory. OBD (90 MB per eye) is owned by `quest-sdk-choices`; `gles-vs-vulkan` lists it as a Vulkan-only feature.
25. **Version facts.**
    - `unity-version-matrix` owns "what exists in which version".
    - `unity-upgrade-risks` owns "what breaks or regresses when moving between versions".
    - Meta's minimum versions (U1-008: 6000.0.66f2 floor, 6.1+ recommended) are owned by `unity-version-matrix`.
    - The practical 6.0 floor of about 6000.0.52f1 (U1-080) is owned by `unity-upgrade-risks`, because it comes from regressions.
26. **The UUM-93226 Vulkan slowdown report.** Owned by `gles-vs-vulkan` (G1-049 to 053, U1-074 to 077). `unity-upgrade-risks` and `quest-triage` link to it.
27. **Refresh rate.** Owned by `quest-frame-pacing`. The 72 Hz default is the Quest runtime's default, not a Unity choice (Q2-010). UNITY-GF1-C2 records the conflict with the Unity e-book's "XR devices enforce 90 Hz or higher". Supported rates are 72/80/90/96/100/120 Hz on Quest 2/3/3S, 60 Hz for media apps on Quest 2 only, and any integer rate to 207 Hz on Quest 3 (240 Hz in developer mode only) (Q2-010, Q2-013). `unity-urp-settings` and its audit script check the setting.
28. **Headroom rules.** The 70% CPU / 80% GPU / hitches under 3% rule (QUEST-GF1-003, GF2-012) is owned by `quest-triage`, because it drives the first routing decision. `quest-budgets-tiers` links to it. Meta's level-based rule, "design steady state to CPU L4 / GPU L4; L5 is opportunistic" (Q2-028, Q2-029), is owned by `quest-levels-thermal`. Meta publishes no headroom percentage after compositor and OS work (Q2-030).
29. **Store VRC performance rules.** Owned by `quest-budgets-tiers`.
30. **Out of scope.** Quest Pro and Meta VR Glasses get one line each where Meta groups them with Quest (A1-035, A3-074, A3-075). HDRP gets one line in `unity-urp-settings`. Eye-tracked foveation gets one line in `quest-resolution-foveation`.

### Outline decisions: references and scripts

31. **What goes in references.** Any per-version or per-device table longer than about 15 rows goes into `references/*.md`. Examples:
    - level tables
    - the extension matrix
    - the Unity version matrix
    - the Render Graph off-tile list
    - the ovrgpuprofiler metric glossary
    - the CSV column map

    Bodies keep the 3-8 lead facts, the ranked fixes and the verify steps. Every reference file is named in its SKILL.md with a "read when" line.
32. **Script placement.**
    - `quest-profiling-toolkit/scripts/ovr_metrics_csv.py`
      - Python 3.10+, stdlib only. Tested on a synthetic CSV built from the verbatim Aug 2026 header (Q1-012) and the documented column list (Q1-005).
      - Parses columns by header name and normalises unit suffixes (`_MB`, `_microseconds`, `_milliseconds`, `_percentage`, `_MHz`, `_celcius`, `_milliamps`) (Q1-013).
      - Treats 9999, 999 and negative values as missing, and treats early rows where the eye buffer reads 0 as missing (QUEST-GF1-008).
      - Rows are 1 Hz interval averages (Q1-010). p50/p95/p99 are therefore percentiles over per-second rows of `app_gpu_time_microseconds` (and CPU time), not per-frame values. The report says so and points to Perfetto for frame-level pacing.
      - Flags `app_gpu_time_microseconds` values clamped at 65535 (Q1-018, [community]).
      - Reports stale frames per minute and the maximum stale frames in any 60 s window, matching Performance Analytics (QUEST-GF2-013).
      - Reports both hitch-rate definitions, because the "hitches under 3%" rule does not define a hitch (QUEST-GF2-012).
      - Reports CPU/GPU levels and utilisation over time, and passes `phase_sync_mode` through raw (QUEST-GF2-002).
      - Splits the report by the `AppendCsvDebugString` segment column when present (Q1-020).
      - Reports thermal drift between the first and last 5 minutes (battery temperature, `power_level_state`, `render_scale`).
    - `quest-profiling-toolkit/scripts/quest_adb.py`
      - Python stdlib, calling `adb` through subprocess.
      - Python rather than shell because the user works on Windows.
      - Uses only setprops, broadcasts and commands documented by Meta (Q1-077 to 083, A3-049, A3-051, A3-084): `debug.oculus.cpuLevel` / `gpuLevel` (Q1-079), `debug.oculus.refreshRate` (Q1-078), the `COMPOSITOR_SIMULATE_THERMAL` broadcast (Q2-014), `debug.oculus.foveation.subsampled` (Q3-045), and the AppSW `spaceWarpDebug`, `MVOverlay` and `swapInterval` props (Q3-074).
      - `metavr device vrruntime` flags go through Meta's CLI when it is installed; the underlying property names are unpublished and are never hard-coded (Q1-083).
      - G2-010 (a Unity QA repro recipe) is not a property source; `debug.oculus.headlock` is excluded because no Meta page documents it.
      - Props reset on reboot. Every capture subcommand records `getprop | grep debug.oculus` next to its output (Q1-077).
    - `unity-urp-settings/scripts/QuestPerfAudit.cs`
      - An editor script, marked untested.
      - Guarded with `#if UNITY_2022_3_OR_NEWER` and `#if UNITY_6000_0_OR_NEWER`.
      - Also checks some settings owned by other skills: refresh rate, Graphics Jobs mode, Multithreaded Rendering, and the XR plugin. Its report names the owning skill for each check.
      - Further checks: GRD or GPU occlusion culling enabled with GLES in the API list (U3-032); OpenXR Latency Optimization mode (Q2-076 vs U5-092); OBD on whenever AppSW is on (Q3-069, G1-031); the Space Warp motion-vector format (G1-033, Q3-070); the Oculus XR plugin on 6.5+ (U1-091); a 6.0 editor below 6000.0.66f2 (U1-008).
33. **No other scripts.** No script was justified for gles3-perf or arm-mobile-hw-perf. The microbenchmarks the arm dossier proposes (pointer-chase, STREAM triad, ALU-bound shader) are described as measurement methods in references. They are not shipped as code, because no dossier finding validates an implementation on Quest.

### Outline decisions: forced by the research

34. **Quest 3/3S CPU is 6x Cortex-A78C, not 2+4 big/little.** Evidence: A1-013, A1-014, ARM-C1. `xr2-gen1-vs-gen2` must lead with this. `xr2-cpu-threads-neon` must warn that Unity's `big`/`little` affinity aliases may not select what users expect on Quest 3 (A1-050).
35. **GLES vs Vulkan has no measured winner.** No 6.1+ A/B exists (KU-16), and UUM-93226 is Closed Won't Fix (G1-049 to 053). So `gles-vs-vulkan` is written as a decision rule (G1-072 to 078) plus a measurement protocol, not a verdict:
    - Default to Vulkan.
    - Consider GLES only for a GPU-bound, MSAA-heavy project that wins a single-variable A/B after OBD and store minimisation.
36. **Snapdragon Profiler is treated as unsupported on Quest** unless proven on the target OS build (A3-067).
37. **Conflicting clock and level claims are kept, not resolved.** They are surfaced with a "measure on device" instruction:
    - ARM-C3: 599 vs 640 vs 690 MHz
    - ARM-C4: Boost level 6 vs 8
    - ARM-C5: level-trading scope
    - ARM-C6: Boost 20% vs 80%
38. **FFR on GLES is contradictory.** quest.md Q3-039 says there is no FFR on GLES. gles3.md documents QCOM_texture_foveated on GLES with caveats (G1-044, G2-059 to 062, KU-10). `quest-resolution-foveation` states the conflict. `gles-extensions-multiview` gives the GLES mechanics.
39. **The VRC frame-rate floor is resolved, not open.** quest.md settles it (Q1-C1 / Q2-C3 / QUEST-GF1-C3): VRC.Quest.Performance.1 sets a 60 fps certification floor (lowered from 72 on 2024-08-07), and 72 fps with no stale frames is the quality target. Older Meta pages that still say 72, including the po-perf-opt-mobile page behind A3-097, are stale on this point. `quest-budgets-tiers` states the resolution and cites the conflict IDs.
40. **Unity 6.7 has not shipped** (6000.7.0b2 at research time). `unity-version-matrix` lists it as beta only, with no performance claims.
41. **Do not quote "65%".** UNITY-GF1-C1: `unity-cpu-scripting` must not quote the "65%" figure as Quest guidance.

### Outline decisions: critique round 1 (Critic A triggers, Critic B coverage)

42. **All descriptions but three rewritten for trigger separation (Critic A, E1-E29).** The 60-prompt simulation found 30 prompts firing two or more non-triage skills. Each rewrite moves a shared symptom to one owner and ends with a hand-off sentence naming the sibling. `gles-versions-unity-output`, `gles-driver-overhead` and `xr2-gpu-counters-sdp` were not changed. `quest-appsw`, `quest-levels-thermal`, `quest-profiling-toolkit`, `quest-frame-pacing`, `quest-budgets-tiers`, `unity-cpu-scripting` and `unity-profiling-workflow` take Critic A's text plus the Critic B facts below. All 33 descriptions are 374-561 characters.
43. **Hand-off sentences kept despite listing length.** The 33 descriptions total about 14.9k characters, above the ~1% listing budget at 200k context. The hand-off sentences are what separate colliding triggers, so they stay. If Phase 3 shows the listing being truncated, drop the hand-off sentences first (saves about 1.3k characters), then trim the object lists.
44. **Declined: renaming generic unity- names** (`unity-lighting` → `unity-urp-lighting` and similar). Claude Code keeps `plugin:skill` separate, the bundle prefix already separates these from the other three bundles, and Critic A rated the omp shadowing risk low and optional. A rename would churn every cross-reference. Revisit only if a same-named skill is observed.
45. **Post-processing cost has one owner: `unity-render-graph-tiling`.** It owns bloom, tonemapping, colour grading and on-tile post cost in URP. `xr2-bandwidth-power` keeps only the DRAM-bytes arithmetic for any full-screen pass and links to it.
46. **Single owners fixed.** The Runtime Optimizer is owned by `quest-profiling-toolkit`; `quest-triage` only links to it. The OpenXR 1.18 timing-unit change is owned by `unity-profiling-workflow`; `unity-upgrade-risks` links to it.
47. **New owned topics (Critic B §B.17).**
    - In-app runtime stats hooks → `unity-profiling-workflow` (Q1-097 to 104, Q1-106, U5-091).
    - OpenXR Latency Optimization → `quest-frame-pacing`, with the Q2-076 / U1-092 vs U5-092 conflict (U5-C2).
    - XR_EXT_performance_settings / XrPerformanceSettingsFeature → `quest-levels-thermal` (Q2-055, QUEST-GF1-010).
    - CoreCLR → one line in `unity-cpu-scripting` (U5-001 / U1-071, U1-072): not in 2021.3-6.6; experimental and desktop-only in 6.7.
    - Simpleperf for IL2CPP hotspots and gpumeminfo → `quest-profiling-toolkit` (Q1-096, Q1-095).
    - Fill-rate and texture-memory budgets → `quest-budgets-tiers`. Meta publishes neither; the skill owns the measurement methods (Q2-036, Q2-037) and the warning that older Meta budget pages are stale (Q2-035). Critic B named "quest-gpu-bound and the memory skill"; budgets stay with the budget owner, and `unity-memory-assets` links to it.
    - Late Latching details (Vulkan and Multiview; never ship Debug Mode) → `quest-frame-pacing` (Q2-075 / Q4-063, G1-036). Low Overhead Mode stays with its existing owner `gles-driver-overhead`, which adds Q2-077 (GLES-only; Oculus XR plugin only).
    - GPU skinning outside GLES compute → `unity-cpu-scripting` under animation (Critic A known gap).
48. **Critic B skill names mapped.** Critic B referred to skills that do not exist in this outline: `quest-gpu-bound` → `quest-triage` (GPU-bound decision tree) and `quest-budgets-tiers` (fill-rate budget); `quest-foveation-resolution` → `quest-resolution-foveation`; `quest-store-vrc` → `quest-budgets-tiers`; `quest-shader-cache` → `unity-shader-hitches`. Some IDs Critic B filed under shader cache were re-filed by content: Q3-093 (6.6 untethered checklist) → `unity-render-graph-tiling`; QUEST-GF1-001/002 (LTS windows, 6.7 status) → `unity-version-matrix`; QUEST-GF2-011 (6.5+ Quest shader-library optimisations) → `unity-shader-authoring`.
49. **Declined: normalising OVR Metrics CSV units by OpenXR plugin version.** The CSV is written by the OVR Metrics service, not by Unity's OpenXR plugin. The 1.18 unit change affects only `XRDisplaySubsystem` reads (U5-091, Q3-060) and is handled in `unity-profiling-workflow`. The analyzer normalises by column-name unit suffix instead (Q1-013).
50. **Not carried: IN-115870.** Critic B cited an FFR regression "IN-115870, fixed in 6000.3.0f1"; no dossier contains that ID. `quest-resolution-foveation` cites the regressions the dossiers do hold: Q3-036 to 038 and UUM-132450 (U1-083 / U2-055).
51. **Draw-call budgets have no single figure.** `quest-budgets-tiers` leads with Meta's per-device table (Q2-033: Quest 2 80-600, Quest 3/3S 200-1000 by simulation load), then lists the other figures with their conflict IDs (QUEST-GF2-C5, Q1-C3, X-C4). A capture of render-thread time comes before any draw-call cut.
52. **AppSW has two setup paths.** Meta's path (URP fork, Unity 2022.3.15f1+ / 6000.0.9f1+ / 6000.4.0f1+, OVRPlugin v34+; Q3-064) and Unity's native path (6.1+, URP 17.0.3+; Q3-065). Both need Vulkan. The XR2 Gen 2 hardware-offload claim (A1-024, [community]) is demoted to a lead.
53. **The Vulkan GSC warmup fix stays a conflict (X-C1).** U1-047 says the fix is in 6.4+ only; U3-091 reads the LTS lines as safe. `unity-shader-hitches` owns the measurement method; `unity-version-matrix` flags the conflict.

## Skills by bundle

### quest-perf

#### quest-triage

- **Description:** Entry point for any Meta Quest 2/3/3S Unity performance problem whose cause is unknown: low FPS, stutter, judder, hitches, "is it CPU-bound or GPU-bound?". Decides CPU main/render thread vs GPU vs pacing vs thermal vs memory with OVR Metrics, logcat and Meta's camera-off / render-scale test, then routes to the owning quest-, unity-, gles- or xr2- skill. Use first when no bottleneck has been identified.
- **Goal:** Both.
- **Owns:**
  - The bottleneck decision tree: CPU main thread, render thread, GPU, pacing, thermal, memory.
  - Meta's two-step isolation workflow (Q1-091): camera off splits CPU-bound from GPU-bound; then, for a GPU-bound app only, render scale 0.01 splits fill-bound from vertex/geometry/submission-bound.
  - The consistency triage sequence (Q1-094).
  - Headroom targets: 70% CPU, 80% GPU, hitches under 3%.
  - The routing table to all 33 skills.
- **Links to (does not repeat):**
  - `quest-perf:quest-profiling-toolkit` (including the Runtime Optimizer)
  - `quest-perf:quest-frame-pacing`
  - `quest-perf:quest-levels-thermal`
  - `quest-perf:quest-budgets-tiers`
  - `quest-perf:quest-resolution-foveation`
  - `unity-perf:unity-profiling-workflow`
  - `unity-perf:unity-cpu-scripting`
  - `unity-perf:unity-draw-calls-batching`
  - `unity-perf:unity-shader-hitches`
  - `gles3-perf:gles-vs-vulkan`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
- **References planned:** `references/routing-table.md` (symptom → metric → owning skill, for all 33 skills).
- **Scripts:** None. It uses `quest-profiling-toolkit` scripts and says when to run them.
- **Primary dossier sources:**
  - quest.md §1 (Q1-050 to 055, Q1-089 to 094), §10 (QUEST-GF1-003, QUEST-GF2-012, Q2-030)
  - unity.md U5-081 (the XR.WaitForGPU rule)
  - arm-mobile-hw.md §6.1 (A1-036), §7.2 (A1-085)
- **Key facts to lead with:**
  - Compare App GPU time (µs) in OVR Metrics against the frame budget: 13.9 / 11.1 / 8.3 ms at 72 / 90 / 120 Hz (Q1-089, Q2-031, A3-097).
  - Meta's isolation workflow has two steps (Q1-091). Step 1: turn the render camera off. Little change means CPU-bound; a big improvement means GPU-bound. Step 2, GPU-bound only: set `eyeTextureResolutionScale` to 0.01. No change means vertex/geometry-bound (culling and draw submission count here); an improvement means fill-bound. Confirm the scale took effect with `SF=` in logcat, because the URP asset's render scale can override it.
  - Headroom rule: keep CPU under about 70%, GPU under about 80%, and hitches under 3% (QUEST-GF1-003, QUEST-GF2-012). The definition of "hitch" behind the 3% is open.
  - Record the granted CPU/GPU level with every capture. Casting or recording overrides levels, and those captures are not comparable (A1-036, A1-085).
  - In the Unity Profiler, XR.WaitForGPU on the main thread means GPU-bound. Do not read it as CPU time (U5-081).
  - Perfetto's stock stale-frame SQL is flawed. Count stale frames from OVR Metrics or logcat instead (Q1-054).

#### quest-budgets-tiers

- **Description:** Per-device budgets and quality tiers for Quest 2 vs Quest 3/3S in Unity: frame-time budget per refresh rate, how many draw calls, triangles, pixels and texture memory each headset affords, app memory limits (PSS, lmkd low-memory kills), runtime headset detection (SystemHeadset), adaptive quality ladders and store VRC performance rules. Use when sizing content per headset, porting Quest 3 content to Quest 2, or when the app is killed for memory. To reduce draw calls, see unity-draw-calls-batching.
- **Goal:** Throughput (budgets) and Consistency (memory kills, adaptive quality).
- **Owns:**
  - Frame budgets.
  - Per-device capability ratios: Quest 3 vs Quest 2 GPU and CPU, MR deltas as numbers only.
  - Draw-call and triangle budgets, with every conflicting Meta figure.
  - Fill-rate and texture-memory budgets: none published; owns the measurement methods (Q2-036, Q2-037).
  - The render-scale floor.
  - Porting content between Quest 3 and Quest 2.
  - Headset RAM and app PSS limits, and lmkd behaviour.
  - SystemHeadset detection and device tiers.
  - Adaptive quality ladders.
  - Quest 3S specifics.
  - Store VRC performance requirements and Performance Analytics field telemetry.
- **Links to (does not repeat):**
  - `quest-perf:quest-triage`
  - `quest-perf:quest-levels-thermal`
  - `quest-perf:quest-mr-costs`
  - `unity-perf:unity-draw-calls-batching`
  - `unity-perf:unity-memory-assets`
  - `arm-mobile-hw-perf:xr2-gen1-vs-gen2`
- **References planned:**
  - `references/device-tiers.md` (per-device table: SoC, eye buffer, RAM, PSS limit, SystemHeadset value)
  - `references/vrc-performance.md`
- **Scripts:** None.
- **Primary dossier sources:**
  - quest.md §2 (Q2-001 to 006, Q2-009, Q2-033 to 037, Q2-041 to 043, Q2-080 to 093), QUEST-GF2-005, QUEST-GF2-C5, Q1-053, Q1-C3
  - quest.md §11: Q1-084 to 088, Q2-016, Q2-026, Q3-003, QUEST-GF1-009, QUEST-GF2-013; resolved floor conflict Q1-C1 / Q2-C3 / QUEST-GF1-C3
  - Q2-085 is a researcher-synthesised tier structure, not Meta guidance; label it so.
  - arm-mobile-hw.md §1.6 (A1-020, ARM-C20), A3-097
  - unity.md X-C4 (the triangle-budget conflict), U1-073 (Adaptive Performance, OpenXR support from 6.6)
- **Key facts to lead with:**
  - Quest 3 has about 2x the GPU of Quest 2 per Meta; Qualcomm claims 2.5x. There is no independent like-for-like measurement (Q2-001 to 006, A1-020, ARM-C20).
  - Draw calls have no single budget. Lead with Meta's per-device table (Q2-033): Quest 2 80-200 / 200-300 / 400-600 and Quest 3/3S 200-300 / 400-600 / 700-1000 for busy / medium / light simulation. Then list the other figures: about 500 per the GDC 2026 talk (QUEST-GF2-005), under 300 per the Runtime Optimizer, under 100 per Meta's agent skill (Q1-053), and the device-comparison page's Quest 3 under 200 / 1.5M triangles and Quest 2 under 100 / 750K (X-C4). None is a limit (QUEST-GF2-C5, Q1-C3). Measure render-thread time before cutting draw calls.
  - Render-scale floor: VRC Perf.4 (recommended, not required) asks for at least 85% for most of the experience, read from the CSV `render_scale` column (Q1-087, Q2-026, Q3-003). The GDC 2026 talk's 0.85 agrees (QUEST-GF2-005).
  - No fill-rate or texture-memory budget is published (Q2-036, Q2-037). Fill rate: measure per-surface time in RenderDoc Meta Fork's Tile Timeline. Texture memory: measure PSS and `app_gpu_*_MB` at peak scene load. Older Meta pages with triangle and texture figures are stale (Q2-035).
  - Triangle budgets differ between Meta pages; quote both (X-C4, Q2-033/034).
  - App PSS limits: about 4.4 GiB on Quest 2 and about 5.75 GiB on Quest 3/3S. lmkd kills above them (Q2-041 to 043).
  - SystemHeadset values: Quest 2 = 9, Quest 3 = 11, Quest 3S = 12. Use them for tiering (Q2-080 to 084). The tier ladder in Q2-085 is researcher synthesis from Meta's groupings.
  - Quest 3S renders the same default eye buffer as Quest 3 (1680x1760), so the default GPU cost is equal (ARM-GF2-004, Q2-087 to 093).
  - VRC Perf.1: the certification floor is 60 fps; 72 fps with no stale frames is the quality target. Pages still saying 72 are stale (Q1-C1 / Q2-C3 / QUEST-GF1-C3, Q1-084). 96/100/120 Hz are "not available on all devices" (QUEST-GF1-009).
  - Perf.2, the 45-minute thermal test, was retired on 2024-10-16 (Q1-085). Perf.3: head-tracked graphics within 4 s of launch (Q1-086). Other VRCs: Q1-088.
  - Store Performance Analytics reports field telemetry in 60 s windows, including Max Stale Frames per window (QUEST-GF2-013).

#### quest-frame-pacing

- **Description:** Frame delivery on Quest 2/3/3S when average frame time already fits the budget: stale frames, repeated or dropped frames, periodic judder, bad p95/p99, FrameSync vs legacy Phase Sync, Late Latching, OpenXR Latency Optimization, choosing 72/90/120 Hz and Unity's Optimized Frame Pacing. Use when OVR Metrics shows stale frames or the image judders with no single CPU/GPU spike. Not for one-off spikes (unity-shader-hitches, unity-cpu-scripting) or drops that grow over a session (quest-levels-thermal).
- **Goal:** Consistency.
- **Owns:**
  - Stale-frame semantics, the Early/Tear/TW/LCnt fields and the order of missed-frame recovery.
  - FrameSync: manifest key, OS versions, opt-out status.
  - Phase Sync as legacy.
  - Late Latching: Vulkan and Multiview required; Debug Mode never ships.
  - OpenXR Latency Optimization (Prioritize Input Polling vs Prioritize Rendering).
  - Refresh-rate choice, the runtime's 72 Hz default, thermal refresh drops and supportedDevices gating.
  - Unity's Optimized Frame Pacing setting.
  - Staggering periodic work across frames.
- **Links to (does not repeat):**
  - `quest-perf:quest-levels-thermal`
  - `quest-perf:quest-profiling-toolkit`
  - `unity-perf:unity-cpu-scripting`
  - `unity-perf:unity-shader-hitches`
  - `gles3-perf:gles-vs-vulkan`
- **References planned:** `references/framesync.md` (OS-version timeline, manifest keys, logcat verification).
- **Scripts:** None. It reads `ovr_metrics_csv.py` output for stale frames per minute and p99.
- **Primary dossier sources:**
  - quest.md §3 (Q1-024, Q1-026, Q2-066, Q2-067, Q2-070 to 078, Q4-057 (OXPB-115), Q4-063, QUEST-GF1-007, QUEST-GF2-001 to 003)
  - quest.md refresh rates: Q2-010 to 015, QUEST-GF1-009
  - arm-mobile-hw.md A1-039, A3-078
  - unity.md UNITY-GF1-C2, UNITY-GF1-009, U5-023, U5-024, U5-C5 (Optimized Frame Pacing), U1-092, U5-092, U5-C2 (Latency Optimization)
  - gles3.md G1-036 (Late Latching is Vulkan-only)
- **Key facts to lead with:**
  - A stale frame means the compositor reused the previous app frame. Track stale frames per minute, not just average FPS (Q1-024, Q2-066).
  - FrameSync replaced Phase Sync and is on by default for every app on Quest 2/3/3S; Phase Sync calls are no-ops (Q2-071, QUEST-GF1-007). It was testable from OS v201 and became the Store default in v203. Meta warns it can slightly raise CPU/GPU utilisation (A1-039).
  - The FrameSync opt-out was announced but is undocumented. The `com.oculus.enable_frame_sync=false` value comes only from community posts, with no confirmation that it works (QUEST-GF1-007, QUEST-GF2-001). CSV `phase_sync_mode=4` probably marks the FrameSync path; no Meta page defines it (QUEST-GF2-002). [verify on device]
  - Quest's runtime defaults to 72 Hz; 80/90/96/100/120 must be requested explicitly (Q2-010, UNITY-GF1-C2). Quest 2 also offers 60 Hz for media apps; Quest 3 accepts any integer rate to 207 Hz, and 240 Hz only in developer mode (Q2-013). Gate on the runtime's reported list, because a rate is available only if `com.oculus.supportedDevices` lists a device that supports it (Q2-015).
  - A thermal event first drops an above-72 Hz app to 72 Hz, then halves the app frame rate (Q2-014).
  - Late Latching needs Vulkan and Multiview. Never ship its Debug Mode (Q2-075 / Q4-063, G1-036).
  - Latency Optimization conflict: Meta recommends Prioritize Input Polling (Q2-076, U1-092); Unity's OpenXR 1.18 default is Prioritize Rendering (U5-092). It is build-time only. Use Meta's setting unless a stale-frame A/B says otherwise.
  - Under thermal stress, FrameSync adaptation is stage 3 of Meta's thermal model. Stale frames late in a session may be thermal; route to `quest-levels-thermal` (A3-078).
  - Unity's Optimized Frame Pacing: default off pending measurement [verify on device]. Unity documents no behaviour under the XR compositor and community reports are mixed (U5-023, U5-024, conflict U5-C5). A/B stale frames per minute with it on and off.

#### quest-levels-thermal

- **Description:** Quest CPU/GPU performance levels and thermal throttling in Unity apps: level-to-clock tables for Quest 2 and Quest 3/3S, suggestedCpuPerfLevel and OpenXR performance-settings hints, CPU Boost, Quest 2 dual-core mode, Quest 3 CPU/GPU level trading, GPU level 5, staged throttling, power level (PLS), Battery Saver and 20-30 minute session tests. Use for FPS drops after 10 minutes, levels that keep changing, thermal throttling warnings, or picking a ProcessorPerformanceLevel. For watts and battery drain, see xr2-bandwidth-power.
- **Goal:** Consistency (primary) and Throughput.
- **Owns:**
  - ProcessorPerformanceLevel ranges, the level APIs and the level-to-clock tables.
  - The OpenXR path: XR_EXT_performance_settings via `XrPerformanceSettingsFeature` hints and change notifications.
  - Meta's level-based headroom rule: design to CPU L4 / GPU L4; L5 is opportunistic.
  - Governor hysteresis.
  - Availability rules, including the passthrough caps as rules. The MR budget impact is in `quest-mr-costs`.
  - CPU Boost, dual-core mode and level trading.
  - GPU L5 and dynamic resolution.
  - The staged throttling model and the minute-ten cliff.
  - PLS / POW L.
  - Battery Saver.
  - clockStateLogLevel and simulated-thermal testing.
  - The long-session measurement recipe.
- **Links to (does not repeat):**
  - `quest-perf:quest-profiling-toolkit`
  - `quest-perf:quest-resolution-foveation`
  - `quest-perf:quest-mr-costs`
  - `arm-mobile-hw-perf:xr2-bandwidth-power`
  - `arm-mobile-hw-perf:xr2-cpu-threads-neon`
- **References planned:**
  - `references/level-tables.md` (clock table, availability per device, conflict notes ARM-C3 to C6)
  - `references/long-session-protocol.md`
- **Scripts:** None. It runs `quest_adb.py` (pin levels, clockStateLogLevel) and `ovr_metrics_csv.py` (drift report).
- **Primary dossier sources:**
  - quest.md §3 (Q2-046/047, Q2-051 to 053, Q2-058 to 064, Q2-014)
  - quest.md §10 headroom: Q2-028 to 030, Q2-039 (stable-measurement recipe), Q2-040 (Guardian and compositor preempt the app), Q2-050
  - quest.md levels API: Q1-105 / Q2-044, Q2-045, Q2-048/049, Q2-054, Q2-055, Q2-057, QUEST-GF1-010, QUEST-GF2-004, Q1-038, Q4-003, Q4-007, Q4-009
  - arm-mobile-hw.md §1.3 (A1-005 set), §6 (A1-028 to 037, A3-068/069 level tables, A3-070 to 096, ARM-GF1-003)
  - Conflicts ARM-C3 to C6, ARM-C17
- **Key facts to lead with:**
  - Default L4 clocks. Quest 2: CPU 1.48 GHz, GPU 525 MHz. Quest 3/3S: CPU 1.92 GHz, GPU 545 MHz. Pre-2023 tables showing 490 MHz at Quest 2 L4 are stale (A1-005, A1-007, Q2-046/047).
  - Hysteresis: CPU level up at ≥83% utilisation, down at ≤77%. GPU up at ≥87%, down at ≤81% (A1-037, A3-070).
  - Boost takes CPU L4 to L8: +64% on Quest 2 (2.42 GHz), +23% on Quest 3/3S (2.36 GHz). Limits: at most 45 s in a row and 20% of runtime; refused while throttling or in Battery Saver (A1-030, Q2-053). The level-label conflict (ARM-C4) and runtime-cap conflict (ARM-C6) are open.
  - Dual-core mode (`com.oculus.dualcorecpuset`) is Quest 2/Pro only. Level trading (`com.oculus.trade_cpu_for_gpu_amount`) is Quest 3/3S only. Both need OpenXR and are fixed at build time (A1-031, A1-032, Q2-051/052).
  - Design the steady-state workload to CPU L4 / GPU L4, which the OS sustains under worst-case thermal and battery conditions (Q2-028). GPU L5 is opportunistic: granted only with thermal headroom and dynamic resolution, never for minimum-frame-rate needs (Q2-029, Q2-050, A1-034, A3-085).
  - Over-requesting levels costs battery and heat without adding frames (Q2-054). An OS update changed GPU L4 performance by 7% with no rebuild (Q2-057), so record the OS build with every capture.
  - OpenXR path: `XrPerformanceSettingsFeature.SetPerformanceLevelHint` per CPU/GPU domain (SustainedHigh is the default; keep Boost under 30 s), and `OnXrPerformanceChangeNotification` for Normal/Warning/Impaired (Q2-055; Quest exposure is community-evidenced, QUEST-GF1-010). [verify on device]
  - Throttling is staged: budgeting, throttling, FrameSync adaptation, forced cool-down. Meta warns of a "thermal cliff at minute ten"; no minutes-to-throttle is published (A3-078, A3-079).
  - PLS is 0 NORMAL, 1 SAVE, 2 DANGER. Battery Saver forces 72 Hz and FFR 3, and disables GPU L5 and Boost (A3-081, A3-092).
  - `adb shell setprop debug.oculus.clockStateLogLevel 1` shows why a level was granted, forced or rejected (A3-084).

#### quest-resolution-foveation

- **Description:** GPU pixel-cost controls on Quest 2/3/3S in Unity URP: eye-buffer size, render scale, dynamic resolution, fixed and dynamic foveated rendering (FFR), subsampled layout, Symmetric Projection, multiview render regions and Meta Quest Super Resolution. Use when GPU-bound on fill rate, choosing an FFR level, when FFR seems to do nothing, for peripheral foveation artifacts, or when URP post-processing or an intermediate texture disables foveation.
- **Goal:** Throughput.
- **Owns:**
  - Eye-buffer defaults and render scale.
  - Dynamic resolution: API, snapping, the GPU L5 link.
  - FFR levels and dynamic foveation.
  - Subsampled layout.
  - Symmetric Projection.
  - Multiview render regions (MVRR).
  - MQSR.
  - URP SRP Foveation.
  - What disables FFR: direct mode, intermediate textures.
  - A one-line note on eye-tracked foveation.
- **Links to (does not repeat):**
  - `quest-perf:quest-appsw`
  - `quest-perf:quest-levels-thermal`
  - `unity-perf:unity-urp-settings`
  - `unity-perf:unity-upgrade-risks`
  - `gles3-perf:gles-extensions-multiview`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
- **References planned:**
  - `references/foveation-levels.md` (per level, device and API)
  - `references/dynamic-resolution.md`
- **Scripts:** None.
- **Primary dossier sources:**
  - quest.md §4 (Q3-001 to 014 eye buffer and render scale, Q3-015 to 023, Q3-024 to 035 FFR APIs and URP history, Q3-036 to 038 regressions, Q3-039, Q3-040 to 047 subsampled layout, Q3-048 to 061, Q3-088 to 091), Q2-007/008, Q2-019, Q4-075 to 078
  - gles3.md G1-035, G1-037, G1-039, G2-059 to 062
  - unity.md U2-054, U1-082 to 085, U1-083 / U2-055 (UUM-132450)
  - arm-mobile-hw.md A2-023, A3-086, ARM-GF2-004
- **Key facts to lead with:**
  - Default eye buffers: Quest 2 is 1440x1584; Quest 3 and 3S are both 1680x1760, about 30% more pixels than Quest 2 (ARM-GF2-004, Q2-019).
  - FFR saves about 6.5 / 11.5 / 21% by level. The Low level can be a net loss (Q3-022, Q3-023). Per-device savings are not published.
  - FFR is per-bin, so a surface rendered in direct mode, or a main pass into a non-swapchain intermediate texture, gets no FFR (A2-023, A3-024).
  - Symmetric Projection saves 5-15% and MVRR 3-8%. Both are Vulkan-only (G1-037, G1-039).
  - FFR does not affect compositor layers, in quality or cost (Q3-024).
  - URP SRP Foveation is 20-30% faster than the older path (U2-054). Foveation regressed in several Unity versions (U1-082 to 085); see `unity-upgrade-risks`. Symptoms to recognise: FFR glitches and a 90→40-60 fps drop on 6.1/6.2 Vulkan (Q3-036, [community]); SRP foveation with URP HDR foveating the top half (Q3-037, [community]); FFR High with 24-bit depth submission on the 6000.4 Meta fork (Q3-038); black view with framebuffer fetch plus FFR, UUM-132450 (U1-083 / U2-055).
  - Subsampled layout is Vulkan/FDM2 only and can hurt when post-processing is on, because intermediate passes are not foveated. No saving is published. A/B it with `adb shell setprop debug.oculus.foveation.subsampled 1|0` (Q3-041 to 047).
  - Dynamic resolution lowers render scale during thermal events, allocates at maximum scale, and snaps in ±0.05 steps (Q3-048 to 061, A3-086).
  - Conflict: Q3-039 says there is no FFR on GLES; gles3.md documents QCOM_texture_foveated with caveats (G2-059 to 062, KU-10).

#### quest-appsw

- **Description:** Application SpaceWarp (AppSW) on Quest 2/3/3S with Unity URP: render at half rate and let the runtime synthesize frames from motion vectors and depth, for up to about 70% GPU headroom. Covers both setup paths (Meta URP fork from 2022.3.15f1 / 6000.0.9f1, Unity-native from 6.1 / URP 17.0.3+), Vulkan and Optimize Buffer Discards requirements, motion-vector passes and format, shader and UI support, artifacts, and runtime toggling. Use for "SpaceWarp", "half frame rate", warping artifacts, or when resolution and foveation cuts are not enough to hold 72/90 Hz.
- **Goal:** Throughput (primary) and Consistency (headroom against spikes).
- **Owns:**
  - AppSW requirements and setup on both paths: Meta's URP fork and Unity-native.
  - The OBD prerequisite on the AppSW path.
  - Motion-vector cost (conflict QUEST-GF2-C3) and format.
  - Shader requirements for custom materials.
  - UI handling by version.
  - Artifacts and mitigations.
  - Runtime on/off policy, including re-arming after a camera change.
  - Frame-rate interaction.
  - AppSW diagnostics (their meaning; `quest_adb.py` wraps the props).
- **Links to (does not repeat):**
  - `quest-perf:quest-resolution-foveation`
  - `quest-perf:quest-frame-pacing`
  - `unity-perf:unity-version-matrix`
  - `unity-perf:unity-shader-authoring`
  - `gles3-perf:gles-vs-vulkan`
- **References planned:** `references/appsw-setup.md` (per-version setup steps, motion-vector shader requirements).
- **Scripts:** None.
- **Primary dossier sources:**
  - quest.md §5 (Q3-062 to 077), QUEST-GF2-007, QUEST-GF2-C3
  - gles3.md G1-031 to 033
  - arm-mobile-hw.md A1-024 (lead only: [community] report of XR2 Gen 2 hardware offload)
- **Key facts to lead with:**
  - AppSW gives up to about 70% extra GPU time (Q3-062, G1-031/032). It is Vulkan-only (G1-031).
  - Motion-vector cost is a conflict: Meta's GDC 2024 guidance says to expect about 30% of the doubled frame (QUEST-GF2-007); Meta's native page calls the low-res pass "almost free" (Q3-063). See QUEST-GF2-C3; measure it.
  - Meta path (Q3-064): Vulkan, OVRPlugin v34+, Unity 2022.3.15f1+, 6000.0.9f1+ or 6000.4.0f1+, on Meta's URP fork branches (`2022.3/14.0.x-oculus-app-spacewarp`, `6000.0/oculus-app-spacewarp`, `6000.4/oculus-app-spacewarp`). Stock URP works from 6000.0.9f1 with Render Graph; the fork is still recommended for transparents.
  - Unity-native path (Q3-065): Unity 6.1+ (6000.1.13f1+ for right-handed NDC), OpenXR 1.11.0+ (1.15.1+ for right-handed NDC), URP 17.0.3+ with Render Graph, Vulkan. Runtime API `SpaceWarpFeature.SetSpaceWarp(bool)` plus per-frame app-space position and rotation.
  - Optimize Buffer Discards is a prerequisite (gles3.md G1-031 notes) and Meta calls it "very important" for AppSW (Q3-069).
  - Motion-vector format is RGBA16f or RG16f; RG16f halves motion-vector bandwidth. The option exists from OpenXR 1.14.0 (G1-033, Q3-070).
  - Custom shaders on stock URP need an `XRMotionVectors` pass writing stencil Ref 1, the `APPLICATION_SPACE_WARP_MOTION` keyword and ObjectMotionVectors.hlsl (Q3-066). The Meta fork filters on `LightMode=MotionVectors` instead (Q3-067).
  - UI: Unity 6.5+ supports uGUI and TMP with the Canvas "Previous Position" channel and SpaceWarp-compatible UI shaders. Before 6.5, UI takes the motion vectors behind it. Screen-space UI is incompatible (Q3-072).
  - Call `SetSpaceWarp(true)` again whenever the main camera changes (Q3-075). AppSW applies to the projection layer only (Q3-076).
  - Diagnostics: logcat `FPS=36/72` with `ASW=72, Type=App`; `debug.oculus.spaceWarpDebug`, `debug.oculus.MVOverlay` and `debug.oculus.swapInterval` (Q3-074).
  - Lead only: UploadVR says XR2 Gen 2 moves some system work to on-chip accelerators (A1-024, [community]). No Meta source ties this to AppSW cost.
  - Behaviour at 90/120 Hz is an open question; test on device.

#### quest-compositor-layers

- **Description:** Compositor layers on Quest 2/3/3S in Unity (OVROverlay, OpenXR composition layers): moving UI, text, video and skyboxes out of the eye buffer for sharper text and lower app GPU cost, per-layer compositor cost, layer limits, and when a layer costs more than it saves. Use for blurry UI text or menus, expensive world-space canvases, video playback cost, or too many overlays.
- **Goal:** Throughput (app GPU) and Consistency (compositor headroom).
- **Owns:**
  - Layer types and when to use each.
  - Per-layer compositor cost.
  - Layer limits.
  - Layer ordering and depth.
  - Video and UI on layers.
  - The compositor-cost unknown on Quest 3.
- **Links to (does not repeat):**
  - `quest-perf:quest-resolution-foveation`
  - `quest-perf:quest-profiling-toolkit`
  - `unity-perf:unity-cpu-scripting`
- **References planned:** `references/layer-types.md`.
- **Scripts:** None.
- **Primary dossier sources:** quest.md §6 (Q3-078 to 086, QUEST-GF2-008), Q3-024.
- **Key facts to lead with:**
  - Each layer costs about 0.1 ms of compositor time; a full-screen layer costs about 0.6 ms (Q3-078 to 086).
  - The layer limit is 16 (15 app-usable) (Q3-078 to 086).
  - Layer cost on Quest 3 is not published. The only other Meta figure is the Spatial SDK's panel cost of about 1% GPU per 480,000 pixels (QUEST-GF2-008). Measure it with the compositor stages in ovrgpuprofiler (open unknown).
  - FFR does not reduce compositor-layer cost (Q3-024).

#### quest-mr-costs

- **Description:** Mixed-reality performance on Quest 3/3S (and Quest 2 passthrough) in Unity: passthrough CPU/GPU cost and its level caps, Depth API occlusion, Scene/MRUK meshes, hand and body tracking cost, and MR vs VR power draw. Use when an MR or passthrough app drops frames or is slower than the same scene in VR, when CPU/GPU levels stop rising with passthrough on, or when budgeting occlusion and scene understanding.
- **Goal:** Throughput and Consistency (the MR thermal load).
- **Owns:**
  - Passthrough cost.
  - The MR budget under level caps.
  - The Depth API occlusion cost model.
  - MRUK and scene-mesh cost.
  - Hand/body tracking cost.
  - MR power delta.
  - Why favour-CPU trading is useless in MR.
- **Links to (does not repeat):**
  - `quest-perf:quest-levels-thermal`
  - `quest-perf:quest-budgets-tiers`
  - `arm-mobile-hw-perf:xr2-bandwidth-power`
  - `unity-perf:unity-shader-authoring`
- **References planned:** `references/mr-features.md` (per-feature cost notes, Q4 IDs).
- **Scripts:** None.
- **Primary dossier sources:**
  - quest.md §7 (Q2-038, Q4-001, Q4-004, Q4-005, Q4-010 to 048)
  - arm-mobile-hw.md A1-018, A1-019, A1-033, ARM-GF2-002, A3-072
- **Key facts to lead with:**
  - Meta: passthrough costs 17% of GPU and 14% of CPU against VR-only. The Depth API adds more GPU cost (A1-019, Q2-001 to 006). These are launch-era figures.
  - With passthrough on, Quest 3/3S caps sustained CPU at L3 (1.65 GHz) and GPU at L2 (456 MHz) (A1-018, A3-072, Q2-038).
  - That gives about 22.9 M main-thread cycles per frame at 72 Hz, against 26.7 M in VR (A1-018, derived).
  - Favour-CPU trading does nothing in MR, because CPU L5 requires L4, and L4 is unavailable with passthrough (A1-033).
  - Measured MR scenarios draw about 2-3 W more than VR on Quest 3 (ARM-GF2-002, [measured], OS v57).
  - The costs of hand tracking and the Depth API are not published; measure them.

#### quest-sdk-choices

- **Description:** Choosing Meta and Unity XR plugins and SDK settings for performance on Quest 2/3/3S: OpenXR plugin vs deprecated Oculus XR plugin, Meta XR Core SDK performance toggles, Optimize Buffer Discards, the manifest performance-flag inventory, Project Setup Tool fixes, and deprecated options such as Shader Binary Cache. Use when picking an XR stack or when a Meta SDK toggle may cost or save frame time or memory. Migration steps after a Unity upgrade: unity-upgrade-risks.
- **Goal:** Throughput and Consistency (memory).
- **Owns:**
  - The plugin-stack choice.
  - Meta XR SDK performance-relevant settings.
  - OBD.
  - An inventory of manifest performance flags. Each flag's semantics are owned by its topic skill.
  - The PST CLI.
  - Deprecated features, and their replacements where known.
- **Links to (does not repeat):**
  - `unity-perf:unity-version-matrix`
  - `unity-perf:unity-upgrade-risks`
  - `quest-perf:quest-levels-thermal`
  - `quest-perf:quest-frame-pacing`
  - `gles3-perf:gles-vs-vulkan`
- **References planned:** `references/manifest-flags.md` (key, owner skill, device scope).
- **Scripts:** None.
- **Primary dossier sources:**
  - quest.md §8 (Q4-049 to 071, Q4-059, QUEST-GF1-004)
  - unity.md U1-009, U1-090 (Offscreen Rendering Only), U1-091 to 093
  - gles3.md G1-024, G1-038, G2-093
- **Key facts to lead with:**
  - The Oculus XR plugin is deprecated; use OpenXR (U1-009). Unity lists it as no longer supported from 6.5 (U1-091). Its GLES path is deprecated from 6.5 (G1-024, G2-093).
  - OpenXR "Offscreen Rendering Only" saves about 10-20 MB on Quest 3 (U1-090).
  - Optimize Buffer Discards saves about 90 MB per eye on Quest 3 and 66 MB per eye on Quest 2. It is Vulkan-only and is also the UUM-93226 workaround (Q4-059, G1-038).
  - Shader Binary Cache is deprecated (QUEST-GF1-004). A replacement is not confirmed.
  - Dual-core mode and level trading need the OpenXR backend (A1-031, A1-032).

#### quest-profiling-toolkit

- **Description:** Exact commands and output formats for Quest profiling tools: OVR Metrics Tool (overlay, CSV columns), VrApi/XrPerformanceManager logcat, MQDH and Perfetto traces, RenderDoc Meta Fork, ovrgpuprofiler, simpleperf, gpumeminfo, and debug setprops that pin levels or disable foveation. Ships a Python OVR Metrics CSV analyzer (p50/p95/p99, stale frames per minute, thermal drift) and an ADB helper. Use to run a capture, pin levels, or parse a CSV/trace; for what a symptom means, start at quest-triage.
- **Goal:** Both (measurement for every fix).
- **Owns:**
  - OVR Metrics: stats, CSV path, broadcasts, SDK tagging.
  - The logcat line fields.
  - MQDH and Perfetto capture options.
  - RenderDoc Meta Fork: tile timeline, draw metrics, CLI, settings.
  - ovrgpuprofiler: modes, trace reading, surface-line and multiview reading.
  - setprops: pin levels, disable foveation, skip compositor.
  - Simpleperf for IL2CPP CPU hotspots (Q1-096) and `gpumeminfo` per-process GPU memory (Q1-095).
  - The Runtime Optimizer (sole owner; `quest-triage` links here).
  - Measurement hygiene: pinned levels, detailed-mode overhead.
- **Links to (does not repeat):**
  - `quest-perf:quest-triage`
  - `arm-mobile-hw-perf:xr2-gpu-counters-sdp`
  - `unity-perf:unity-profiling-workflow`
  - `gles3-perf:gles-vs-vulkan`
  - `quest-perf:quest-levels-thermal`
- **References planned:**
  - `references/ovr-metrics-csv-columns.md`
  - `references/ovrgpuprofiler.md` (commands and surface-line fields)
  - `references/renderdoc-meta-fork.md`
  - `references/perfetto-mqdh.md`
  - `references/setprops.md`
- **Scripts:**
  - `scripts/ovr_metrics_csv.py` (stdlib, Python 3.10+). Usage: `python ovr_metrics_csv.py <csv> [--hz 72] [--window-min 5]`. Requirements are in decision 32: 1 Hz rows, unit-suffix normalisation, 65535 clamp detection, max stale per 60 s window, both hitch-rate definitions, raw `phase_sync_mode`, segment splitting.
  - `scripts/quest_adb.py` (stdlib). Subcommands: `pin-levels`, `refresh-rate`, `foveation-off`, `subsampled`, `compositor-skip`, `thermal-sim`, `appsw-debug`, `csv-on`, `pull-csv`, `gpu-trace`, `clocklog`, `props-snapshot`, `vrruntime` (forwards to Meta's `metavr` CLI).
- **Primary dossier sources:**
  - quest.md §9 (Q1-001 to 023, Q1-027 to 039, Q1-050 to 055, Q1-057 to 083), §12 (CSV columns: Q1-005, Q1-010, Q1-012, Q1-013, Q1-018, Q1-020, QUEST-GF1-008, QUEST-GF2-002, QUEST-GF2-012, QUEST-GF2-013)
  - MQDH: Q1-040 to 043, QUEST-GF1-005. Perfetto: Q1-044 to 049, Q1-056, QUEST-GF2-010. Simpleperf and gpumeminfo: Q1-095, Q1-096.
  - Script props: Q1-077 to 079, Q1-083, Q2-014, Q3-045, Q3-074
  - arm-mobile-hw.md §5.2 (A3-027 to 053), A1-084, A1-085
  - gles3.md G2-009 (surface-line reading). G2-010 is a Unity QA recipe, not a property source.
- **Key facts to lead with:**
  - CSVs are written to `/sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/`. Enable them with the ENABLE_CSV broadcast (A3-049, quest.md §12).
  - Parse CSV columns by header name, not position; the header changes between tool versions (89, 134 and 129 columns observed) (Q1-012). Treat 9999, 999 and negative values as missing. Key columns: `stale_frame_count`, `app_gpu_time_microseconds`, `cpu_level`, `gpu_level`, `power_level_state`, `render_scale`, `shader_hitches` (Q1-005, Q1-012).
  - CSV rows are 1 Hz interval averages and cannot show a single-frame hitch; use Perfetto for frame-level pacing (Q1-010). `app_gpu_time_microseconds` may clamp at 65535 (Q1-018, [community]).
  - Debug props reset on reboot. Record `adb shell getprop | grep debug.oculus` with every capture (Q1-077).
  - Isolate app GPU time:
    1. Pin levels with `debug.oculus.cpuLevel` and `debug.oculus.gpuLevel`.
    2. Turn foveation off with `debug.oculus.foveation.level 0` and `debug.oculus.foveation.dynamic 0`.
    3. Stop compositor rendering with the `COMPOSITOR_SKIP_RENDERING` broadcast (A3-051).
  - ovrgpuprofiler detailed mode (`-e`, then restart the app) costs about 10% GPU. Disable it before thermal runs (A3-029).
  - ovrgpuprofiler metric IDs vary by device and runtime. List them with `-m` first; never hard-code them (A3-027).
  - Reading multiview surface lines: Quest 2 prints one surface with shared bins; Quest 3/3S prints one line for both views (A3-034).
  - Logcat: `adb logcat -s VrApi,XrPerformanceManager` gives levels, clocks, `PLS=`, `Mem=` and `SP=` (Q1-027 to 039, AS-001).

### unity-perf

#### unity-version-matrix

- **Description:** Lookup of which Unity/URP version has which Quest performance feature, 2021.3 LTS (URP 12) through Unity 6.0-6.6 (URP 17), plus 6.7 status: Render Graph, Forward+, GPU Resident Drawer, on-tile post-processing, Tile-Only Mode, Build Profiles and the Meta Quest profile, LTS dates and Meta's minimum versions. Use for "does Unity X have Y" or choosing an engine version for a new Quest project; how to use each feature lives in its owning skill.
- **Goal:** Both (feature availability gates every fix).
- **Owns:**
  - The feature-by-version matrix.
  - Meta's minimum and recommended versions.
  - LTS dates.
  - The OpenXR plugin version floor.
  - Build Profiles and the Meta Quest profile.
  - Compatibility Mode removal (as availability).
  - STP not in XR.
  - Quest shader optimisations in 6.5+.
  - 6.7 beta status.
- **Links to (does not repeat):**
  - `unity-perf:unity-upgrade-risks`
  - `unity-perf:unity-urp-settings`
  - `unity-perf:unity-render-graph-tiling`
  - `quest-perf:quest-sdk-choices`
  - `gles3-perf:gles-versions-unity-output`
- **References planned:** `references/feature-matrix.md` (rows = features, columns = 2021.3 / 2022.3 / 6.0 / 6.1 / 6.2 / 6.3 / 6.4 / 6.5 / 6.6).
- **Scripts:** None.
- **Primary dossier sources:** unity.md version matrix (U1-001 to 009, U1-020 to 056, U1-094 to 098, X-C1, X-C5 to C9), U3-032, quest.md QUEST-GF1-001, QUEST-GF1-002, UNITY-GF1-013 (STP path in the e-book).
- **Key facts to lead with:**
  - Meta's floor is 6000.0.66f2, and Meta recommends 6.1+. The OpenXR plugin must be 1.15.1+; Oculus XR is deprecated (U1-008, U1-009).
  - Render Graph Compatibility Mode is hidden in 6.3 and removed in 6.4 (U1-023, U1-025, U1-026).
  - Dynamic batching is obsolete in 6.6 (U1-022).
  - Quest shader optimisations are 6.5+ (X-C7, QUEST-GF2-011). Tile-Only Mode is 6.5 (U2).
  - Vulkan GSC warmup fix is a conflict (X-C1): U1-047 finds it only in 6000.4.0a4 with no LTS backport; U3-091 reads the LTS lines as safe. Flag it; `unity-shader-hitches` owns the measurement.
  - GRD and GPU occlusion culling are Vulkan-only on Quest ("GLES n/a" in the matrix), because GRD needs a compute-capable non-GLES API (U3-032, U1-095). GLES minimum becomes 3.1 in 6.6 (U1-094).
  - The Oculus XR plugin is no longer supported from 6.5 (U1-091). Minimum Android API and build tools change per version (U1-096 to 098).
  - STP is not supported in XR (U1-042).
  - 6.0 LTS ends Oct 2026. 6.3 LTS runs to Dec 2027. 6.7 is beta only (6000.7.0b2) (U1-002, U1-003, QUEST-GF1-001, QUEST-GF1-002).

#### unity-upgrade-risks

- **Description:** Known performance regressions and breaking changes when upgrading Unity/URP for Quest: Render Graph GPU regressions, foveation breakages, GPU occlusion bugs, Oculus XR to OpenXR migration, removed Compatibility Mode, obsolete APIs, and safe patch floors per version. Use before or after an upgrade, when FPS dropped after moving to Unity 6 or a new patch, or when choosing which patch release to ship.
- **Goal:** Both.
- **Owns:**
  - The regression list with patch fixes.
  - Practical patch floors.
  - Foveation regressions.
  - OpenXR migration steps and risks.
  - API breaks.
  - The upgrade A/B protocol.
- **Links to (does not repeat):**
  - `unity-perf:unity-version-matrix`
  - `gles3-perf:gles-vs-vulkan` (UUM-93226)
  - `quest-perf:quest-resolution-foveation`
  - `quest-perf:quest-sdk-choices`
  - `unity-perf:unity-profiling-workflow`
- **References planned:** `references/regressions.md` (issue ID, versions affected, fixed-in, workaround).
- **Scripts:** None.
- **Primary dossier sources:** unity.md upgrade risks (U1-020, U1-031, U1-074 to 081, U1-082 to 085, U1-091 to 093, U1-099 to 101).
- **Key facts to lead with:**
  - UUM-90118: about +20% GPU with Render Graph, fixed in 6000.0.46f1 (U1-031).
  - The practical Unity 6.0 floor is about 6000.0.52f1 (U1-080).
  - UUM-146214: GPU occlusion culling broken on 6.5.0-6.5.7 (U1-020).
  - Foveation regressed across several versions (U1-082 to 085).
  - Upgrading to 6.4+ removes Render Graph Compatibility Mode. Custom passes must be ported (U1-025/026).
  - Upgrading the OpenXR plugin across 1.18.0-pre.2 changes `XRDisplaySubsystem` GPU timing units; see `unity-profiling-workflow` (U5-091).
  - Other Quest fixes to check against the target patch: multiview blit/copy passes rendering one eye (U1-078), black screen with MSAA + post + SpaceWarp depth (U1-079), GLES fixes (U1-081).

#### unity-urp-settings

- **Description:** URP asset, renderer, Player and XR settings for Quest 2/3/3S: HDR, MSAA 2x vs 4x, upscaling filter, depth and opaque textures, depth priming, store actions, intermediate texture, Forward vs Forward+ vs Deferred, Tile-Only Mode and swapchain. Includes a C# editor audit script that reports a project's settings against these recommendations. Use when configuring or reviewing a Quest URP project, choosing an MSAA level, or asking which URP checkbox adds a pass.
- **Goal:** Throughput (primary) and Consistency.
- **Owns:**
  - Every URP asset and renderer setting that matters on Quest.
  - The Player and XR settings that are not owned elsewhere.
  - The choice of rendering path.
  - The choice of MSAA level, including the 2x vs 4x conflict.
  - Upscaler and FSR behaviour.
  - Store Actions.
  - Intermediate Texture Auto.
  - Depth priming off.
  - Tile-Only Mode.
  - Swapchain buffers.
  - The GLES light-limit implication.
  - The audit script.
  - A one-line HDRP note.
- **Links to (does not repeat):**
  - `unity-perf:unity-render-graph-tiling`
  - `unity-perf:unity-lighting`
  - `unity-perf:unity-version-matrix`
  - `quest-perf:quest-resolution-foveation`
  - `quest-perf:quest-frame-pacing`
  - `gles3-perf:gles-vs-vulkan`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
- **References planned:**
  - `references/urp-asset-settings.md` (per setting: recommended value, version, reason, finding ID)
  - `references/audit-checks.md` (each check the script makes, with its owner skill)
- **Scripts:** `scripts/QuestPerfAudit.cs`. Copy it into `Assets/Editor/`, then run the menu item `Tools/Quest Perf/Audit`. It prints a report to the Console and to `Logs/QuestPerfAudit.txt`. It is untested and guards version differences with `#if`.
- **Primary dossier sources:**
  - unity.md URP settings (U2-001 to 029, U2-040 to 054, U2-090 to 095), U1-032, U1-034, U1-040, U1-061 (VRS), U1-068, X-C5, X-C6, UNITY-GF1-C2
  - Unity e-books: UNITY-GF1-007, UNITY-GF1-011, UNITY-GF1-015, UNITY-GF2-004; U1-104 records that the Unity 6 e-book body could not be read
  - arm-mobile-hw.md A2-014, A2-017, A2-056, A3-020
  - gles3.md G2-013 to 027
- **Key facts to lead with:**
  - HDR off, Depth Texture off and Opaque Texture off, unless a pass needs them. Each forces stores or extra passes (U2-001 to 029, A3-008).
  - FSR upscaling stays active even at render scale 1.0 (U2-008).
  - Depth priming off. Intermediate Texture: Auto. Store Actions: Discard where allowed (U2-020, U2-023, G2-013 to 027).
  - Forward+ wins from about 5 real-time lights per Meta. Deferred is bad on Quest. On GLES, Forward+ is limited to 16 lights instead of 32 (U1-032, U4-006, U1-034, U1-040, X-C6).
  - MSAA conflict:
    - Qualcomm says 2x is "practically free" (A2-017, A3-020).
    - Meta's 4x cost data is from the original Quest: +0.5-1.5 ms (A2-056, U2-093).
    - HDR in R11G11B10 costs no extra bins over RGBA8; RGBA16F does (A2-014).
    - Measure on device.
  - Leave swapchain buffer count at its default (U1-068, X-C5).
  - Quest runs at 72 Hz unless the app requests another rate, so set it explicitly; `quest-frame-pacing` owns the choice (Q2-010, UNITY-GF1-C2).
  - Meta says 4x MSAA is "extremely cheap" on its tile GPUs (U2-092); this is part of the MSAA conflict above.

#### unity-render-graph-tiling

- **Description:** Keeping URP rendering on-tile on Adreno (Vulkan and URP-level GLES): Render Graph pass merging and pass-break reasons, memoryless attachments, load/store actions, native render passes (URP 12/14), on-tile post-processing and post-processing cost, framebuffer fetch, Render Graph Viewer on device, and custom ScriptableRendererFeature passes that break merging. Use when ovrgpuprofiler shows LoadColor or StoreDepthStencil, when a renderer feature or bloom costs milliseconds, or when writing RG passes for Quest.
- **Goal:** Throughput.
- **Owns:**
  - The off-tile trigger list.
  - PassBreakReasons.
  - The raster-pass API for Quest.
  - Memoryless attachments.
  - Framebuffer fetch in Render Graph.
  - On-tile post-processing and its requirements.
  - URP post-processing cost: bloom, tonemapping, colour grading.
  - The depth input attachment (6.6).
  - Native RenderPass (URP 12/14).
  - The Meta subpass fork.
  - The Render Graph Viewer on device.
  - The 6.6 untethered checklist.
- **Links to (does not repeat):**
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
  - `gles3-perf:gles-tile-load-store`
  - `unity-perf:unity-urp-settings`
  - `unity-perf:unity-version-matrix`
  - `quest-perf:quest-profiling-toolkit`
  - `arm-mobile-hw-perf:xr2-bandwidth-power` (bytes per full-screen pass)
- **References planned:**
  - `references/off-tile-triggers.md`
  - `references/rg-pass-template.md` (paste-ready URP 17 raster pass using framebuffer fetch)
- **Scripts:** None. The C# and HLSL snippets live in the reference.
- **Primary dossier sources:**
  - unity.md Render Graph (U2-030 to 039, U2-057 to 068, U2-070 to 073, U2-074 to 087, X-C10)
  - quest.md Q3-093 (6.6 untethered-XR checklist)
  - arm-mobile-hw.md A2-053 to 059, A3-006, A3-012 (bytes per extra full-screen pass, owned by `xr2-bandwidth-power`)
- **Key facts to lead with:**
  - A bad load/store configuration example costs 3.9 ms of load/store alone (U2-036). Meta's surface example spends about 37% of 10.62 ms on GMEM↔DRAM traffic (A2-054).
  - A healthy eye-buffer surface shows only StoreColor, with no Load* stage and no StoreDepthStencil (A3-007).
  - On-tile post-processing is XR-only from 6.3, requires Tile-Only Mode from 6.5, and has no bloom (U2-074 to 078, X-C10).
  - The Render Graph Viewer works on device from 6.3 (U2-070/071).
  - Native RenderPass is the URP 12/14 path (U2-081). URP 17's Render Graph merges passes automatically when PassBreakReasons allow (U2-057 to 068).
  - Resolve MSAA only in the last subpass. An intermediate resolve or vkCmdResolveImage breaks the benefit (A2-055).

#### unity-draw-calls-batching

- **Description:** Cutting CPU render cost in Unity URP on Quest 2/3/3S: too many draw calls, SetPass calls, SRP Batcher compatibility, static batching, GPU instancing, BatchRendererGroup, GPU Resident Drawer, GPU occlusion culling, and single-pass instanced/multiview. Use when the render thread is bound by draw submission, when draw calls exceed budget, or when choosing between batching methods. For the budget numbers, see quest-budgets-tiers.
- **Goal:** Throughput (CPU).
- **Owns:**
  - The SRP Batcher and what breaks it.
  - Static batching.
  - GPU instancing and its limits.
  - BRG: buffer types per API.
  - GRD and GPU occlusion: requirements, A/B.
  - Multiview/SPI draw-call halving (API-independent).
  - The intermediate-texture blit cost.
  - The obsolete dynamic batching.
  - Frame Debugger usage for batching (in the Editor).
- **Links to (does not repeat):**
  - `quest-perf:quest-budgets-tiers`
  - `unity-perf:unity-urp-settings`
  - `unity-perf:unity-upgrade-risks`
  - `gles3-perf:gles-driver-overhead`
  - `gles3-perf:gles-extensions-multiview`
  - `unity-perf:unity-profiling-workflow`
- **References planned:** `references/batching-methods.md` (method × version × API × constraints).
- **Scripts:** None.
- **Primary dossier sources:**
  - unity.md draw calls (U3-001 to 050, X-C2, X-C4, X-C9, U1-015, U1-020, U1-021, U1-022, U1-095), UNITY-GF1-010, UNITY-GF1-012
  - gles3.md G2-047 to 055
- **Key facts to lead with:**
  - Multiview (single-pass instanced) halves draw calls against multi-pass (U3-001 to 050, G2-047 to 055).
  - A MaterialPropertyBlock breaks SRP Batcher compatibility (U3-001 to 050).
  - The GPU instancing limit on mobile Vulkan is 250 per batch (U3-001 to 050).
  - BRG uses UBOs on GLES and SSBOs on Vulkan (U3-001 to 050).
  - GRD needs all of: a compute-capable API other than GLES (so Vulkan-only on Quest), Forward+ (Deferred+ also allowed from 6.1; X-C9 resolves to Forward+ on Quest), Enlighten realtime GI off, and no MaterialPropertyBlocks (U3-032, U1-095). A/B-test GPU occlusion on device; it is broken on 6.5.0-6.5.7 (U1-020).
  - BRG/GRD objects did not render on 16 KiB constant-buffer devices until 6000.0.65f1 / 6000.3.3f1 (U1-015). GRD stats: 6.4 Rendering Statistics, 6.6 Profiler telemetry (U1-021).
  - An intermediate texture plus final blit costs about 1-1.5 ms (U3-001 to 050).
  - Frame Debugger is not supported on device; use it in the Editor for batching analysis (X-C2).

#### unity-shader-authoring

- **Description:** Writing and fixing cheap URP HLSL and Shader Graph for Quest 2/3/3S: half precision and RelaxedPrecision, clip/discard and alpha-to-coverage vs LRZ, depth-write and blend states that disable early-Z, keywords vs uniform branches, single-pass instanced macros, Quest shader keywords, and texture sampling choices. Use when a shader or material is GPU-expensive, when writing or reviewing custom URP shaders, or asking "should I use half". Hardware cost reasoning: xr2-shader-cost-model.
- **Goal:** Throughput.
- **Owns:**
  - URP HLSL conventions for Quest across URP 12/14/17.
  - `half` and REAL_IS_HALF usage.
  - LRZ-safe material states: discard, A2C, ZWrite + blend, stencil, ZTest Always.
  - Keyword vs uniform branching in Unity terms.
  - SPI/multiview macros.
  - Quest keywords such as `META_QUEST_ORTHO_PROJ`.
  - The `_FORWARD_PLUS` shim.
  - Shader Graph precision settings.
  - Draw ordering for alpha-test.
- **Links to (does not repeat):**
  - `arm-mobile-hw-perf:xr2-shader-cost-model`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
  - `unity-perf:unity-shader-hitches`
  - `unity-perf:unity-render-graph-tiling`
  - `gles3-perf:gles-shader-binaries`
- **References planned:**
  - `references/urp-hlsl-templates.md` (paste-ready unlit/lit fragments per URP 12/14/17)
  - `references/lrz-state-table.md`
- **Scripts:** None.
- **Primary dossier sources:**
  - unity.md shaders (U3-051 to 081, X-C8, UNITY-GF2-C1), QUEST-GF2-011
  - Shader Graph overhead: UNITY-GF1-003 to 006, UNITY-GF2-001, UNITY-GF2-002
  - arm-mobile-hw.md A2-032 to 041, A2-065, A2-066, A2-069
  - gles3.md G3-026 to 035, G2-054
- **Key facts to lead with:**
  - `half` becomes RelaxedPrecision on Vulkan and mediump on GLES when the precision model allows. Literals like `2.0h` are still full precision (A2-065, U3-051 to 081).
  - Shader Graph: "Allow Material Override" swaps compile-time defines for `shader_feature` keywords and fixed states for material-property states (UNITY-GF2-002); generated temporaries are usually compiled away (UNITY-GF1-006).
  - A `ZTest Always` + `ZWrite On` draw disables LRZ until the next depth clear. Blend, stencil or colour-mask plus a depth write disables LRZ writes (A2-032, A2-033).
  - `clip()`, A2C and sample-mask outputs disable LRZ writes only for that draw. Draw them after the opaques (A2-034, A2-041).
  - Mixing half and float in one expression chain adds conversion instructions (A2-066).
  - Use `META_QUEST_ORTHO_PROJ`, with no leading underscore (X-C8). The `_FORWARD_PLUS` shim still works (UNITY-GF2-C1).
  - Uniform branches cost a per-wave test, and both sides may run. Keywords behave like compile-time constants (A2-069).

#### unity-shader-hitches

- **Description:** Removing shader and pipeline-compilation hitches in Unity on Quest (Vulkan and API-agnostic): hitch on first use, spike when an object first renders, shader variant explosion, variant stripping, PSO tracing and GraphicsStateCollection warmup, ShaderVariantCollection limits on Vulkan, the Vulkan pipeline cache, and shader build size. Use for one-off spikes when content first renders, or when shader_hitches shows in OVR Metrics. GLES blob cache and program binaries: gles-shader-binaries.
- **Goal:** Consistency.
- **Owns:**
  - Variant counting and stripping.
  - GSC/PSO tracing and warmup: dev build on device, `WarmUpProgressively`.
  - Why SVC warmup is wrong on Vulkan.
  - `vulkan_pso_cache.bin`.
  - Warmup placement: loading screens under Boost.
  - Detecting hitches: OVR Metrics `shader_hitches`, Profiler markers.
- **Links to (does not repeat):**
  - `gles3-perf:gles-shader-binaries`
  - `unity-perf:unity-version-matrix`
  - `unity-perf:unity-profiling-workflow`
  - `quest-perf:quest-levels-thermal` (Boost during loads)
  - `unity-perf:unity-memory-assets`
- **References planned:**
  - `references/gsc-warmup.md` (per-version API, paste-ready C#)
  - `references/variant-stripping.md`
- **Scripts:** None. The C# lives in references.
- **Primary dossier sources:**
  - unity.md PSO/GSC: U3-082 to 097 (pre-GSC tools on 2021.3/2022.3: U3-092, U3-093), U1-047, U1-049 (stereo-instancing variants not prewarmed), U1-086 (Vulkan PSO and pipeline-cache fixes), X-C1; variant counts in Shader Graph: UNITY-GF1-003, UNITY-GF2-001
  - arm-mobile-hw.md A2-077
  - quest.md §12 (`shader_hitches` column)
- **Key facts to lead with:**
  - ShaderVariantCollection warmup does not create Vulkan PSOs correctly. Trace a GraphicsStateCollection in a development build on device and warm it up with `WarmUpProgressively` (U3-082, U3-084, U3-086).
  - Vulkan GSC warmup fix, conflict X-C1: U1-047 finds it only in 6000.4.0a4; U3-091 reads 6.0/6.3 LTS as safe. Method: on the target LTS, trace and warm a GSC, then run a scripted route twice and compare `shader_hitches` and PSO-creation markers on the second pass. [verify on device]
  - Stereo-instancing (multiview/SPI) variants are not prewarmed by the legacy warmup APIs (U1-049).
  - Unity persists PSOs in `vulkan_pso_cache.bin` (U3-094).
  - Qualcomm: create all pipelines at initialisation (A2-077).
  - OVR Metrics logs `shader_hitches`. Use it to verify (quest.md §12).

#### unity-lighting

- **Description:** Lighting and shadow cost in URP on Quest 2/3/3S: baked vs mixed vs realtime lights, per-object light limits, shadow maps and cascades, lightmaps, light probes and Adaptive Probe Volumes, reflection probes, and HDR lightmap formats. Use when lights, shadows or GI cost GPU time, when choosing a lighting setup for a Quest scene, or when additional lights misbehave on device. Forward vs Forward+ choice: unity-urp-settings.
- **Goal:** Throughput.
- **Owns:**
  - Mixed lighting modes.
  - Per-object light limits (1 main + 8 additional).
  - Shadow-map cost and settings.
  - Lightmap formats and encoding.
  - Light probes and APV.
  - Reflection probes.
  - Hardware PCF.
  - Shadow-pass tile behaviour.
- **Links to (does not repeat):**
  - `unity-perf:unity-urp-settings` (rendering path)
  - `unity-perf:unity-memory-assets`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
  - `quest-perf:quest-resolution-foveation`
- **References planned:** `references/lighting-setups.md` (recommended setups per content type and version).
- **Scripts:** None.
- **Primary dossier sources:**
  - unity.md lighting (U4-001 to 045, U4-006)
  - arm-mobile-hw.md A2-085, A3-026, A3-086
- **Key facts to lead with:**
  - URP allows 1 main light + 8 additional lights per object in Forward (U4-001 to 045).
  - Forward+ pays off from about 5 real-time lights per Meta (U4-006, U1-032).
  - Adreno has hardware PCF. Use comparison samplers, not manual multi-tap compares (A2-085).
  - Depth-only shadow passes get Fast-Z at 2x rate when the fragment shader is empty and colour writes are masked (A3-026).
  - Dynamic resolution misaligns additional lights with Forward+ and Deferred+ (A3-086, a Meta known issue).
  - ASTC HDR on Quest is unverified, and APV cost on Quest is unmeasured (unity.md gaps; see Known unknowns below).

#### unity-cpu-scripting

- **Description:** CPU-side Unity scripting cost on Quest 2/3/3S: GC allocations and GC spikes, incremental GC, IL2CPP settings, moving work into jobs and Burst, multithreaded rendering and Graphics Jobs, physics timestep and spikes, UI canvas rebuilds, animation and skinning, and Update-loop overhead. Use when the main thread is bound by scripts, GC, physics, animation or UI, for GC hitches, or when choosing Player scripting settings. Core counts, affinity and NEON: xr2-cpu-threads-neon.
- **Goal:** Throughput (CPU) and Consistency (GC and physics spikes).
- **Owns:**
  - The Boehm GC and a 0 B per frame target.
  - Incremental GC.
  - IL2CPP settings: Master, Managed Code Variant (6.6).
  - Job and Burst usage patterns.
  - Graphics Jobs mode choice (Legacy).
  - Multithreaded Rendering.
  - Physics timestep.
  - UI rebuild cost.
  - Animation cost, including skinning outside GLES compute.
  - Spreading work across frames.
  - A one-line CoreCLR status note.
- **Links to (does not repeat):**
  - `arm-mobile-hw-perf:xr2-cpu-threads-neon`
  - `unity-perf:unity-profiling-workflow`
  - `quest-perf:quest-levels-thermal`
  - `quest-perf:quest-frame-pacing`
  - `gles3-perf:gles-vs-vulkan` (Graphics Jobs is Vulkan-only)
- **References planned:**
  - `references/player-scripting-settings.md`
  - `references/gc-patterns.md` (paste-ready zero-alloc C# patterns)
- **Scripts:** None.
- **Primary dossier sources:**
  - unity.md CPU (U5-001 to 078, U1-072, UNITY-GF1-C1, UNITY-GF1-C3), UNITY-GF1-014 (physics), UNITY-GF1-017 (GC)
  - arm-mobile-hw.md A1-056 to 062, ARM-GF1-001
  - gles3.md G1-025/026
- **Key facts to lead with:**
  - Target 0 B of GC allocation per frame. Unity's GC is Boehm (U5-001 to 078).
  - Meta recommends Graphics Jobs in Legacy mode with Multithreaded Rendering for main-thread-bound apps, measured at up to 2 FPS. It is available from 2022.3.35f1 and is Vulkan-only (A1-058, G1-025/026).
  - Never ship with Multithreaded Rendering off (A1-061).
  - Meta: an app using all 3 cores at CPU L4 beats dual-core mode at L6. Move main-thread work into jobs first (ARM-GF1-001).
  - The physics `fixedDeltaTime` guidance is open (UNITY-GF1-C3). Do not quote "65%" as Quest guidance (UNITY-GF1-C1).
  - CoreCLR is not a Quest option: no 2021.3-6.6 release ships a CoreCLR player, and 6.7's is experimental and desktop-only. Quest stays on IL2CPP with the Boehm GC (U5-001 / U1-071, U1-072).

#### unity-memory-assets

- **Description:** Asset memory and loading cost for Unity on Quest 2/3/3S: texture compression (ASTC block sizes), mipmaps and mip streaming, mesh compression and vertex formats, Async Upload Pipeline, asset-loading and scene-streaming hitches, Addressables, and render-texture memory. Use to shrink texture/mesh memory, for loading stutter, or for texture bandwidth. Memory limits and lmkd kills: quest-budgets-tiers.
- **Goal:** Consistency (loading hitches, OOM) and Throughput (texture bandwidth).
- **Owns:**
  - ASTC choice and block size.
  - Mip streaming.
  - Mesh import: compression, vertex streams, index format.
  - AUP settings.
  - Loading and streaming hitches.
  - Addressables and memory.
  - Render-texture memory.
- **Links to (does not repeat):**
  - `quest-perf:quest-budgets-tiers`
  - `arm-mobile-hw-perf:xr2-bandwidth-power`
  - `arm-mobile-hw-perf:xr2-adreno-architecture` (position-only vertex stream)
  - `unity-perf:unity-shader-hitches`
  - `quest-perf:quest-levels-thermal`
- **References planned:**
  - `references/texture-import.md`
  - `references/mesh-import.md`
  - `references/loading.md`
- **Scripts:** None.
- **Primary dossier sources:**
  - unity.md memory (U4-046 to 095), U1-059/060 (Mesh LOD), U1-087 to 089, UNITY-GF1-016 (audio load types), UNITY-GF1-017
  - arm-mobile-hw.md A2-048, A2-049, A3-018, A2-086, A3-015
- **Key facts to lead with:**
  - ASTC first, then ETC2 (A2-086). ASTC stays compressed in L2 on A5x; this is unconfirmed on 650/740 (A3-015).
  - Put position alone in the first vertex stream. The binning pass fetches only position (A2-048, A3-018).
  - Unity offers only 16- and 32-bit index formats. Prefer 16-bit (A3-018, A2-049).
  - The A7x post-transform cache holds 32 vertices, so vertex-cache-optimised index order pays off (A2-049).
  - For AUP, mip streaming and loading, see U4-046 to 095.

#### unity-profiling-workflow

- **Description:** Profiling a Unity app on Quest with Unity's tools: Profiler attached to a development build, reading XR.WaitForGPU and Gfx.WaitForPresent correctly, custom ProfilerMarkers, FrameTimingManager, in-app XR stats (XRDisplaySubsystem, OVRPlugin perf metrics), Frame Debugger in the Editor, Project Auditor, Profileable builds, and development-build overhead. Use when interpreting a Unity Profiler capture from Quest or instrumenting code for on-device measurement.
- **Goal:** Both (measurement).
- **Owns:**
  - Unity Profiler on device.
  - Marker interpretation rules.
  - FrameTimingManager and its unverified 6.6 GPU times.
  - In-app runtime stats hooks: XRDisplaySubsystem `TryGet*`, XRStats (deprecated from 6.3), `OVRPlugin.GetPerfMetrics*`, Oculus PerfMetrics (returns 0 under OpenXR), `GetAppPerfStats` (unsupported on OpenXR), XR_META_performance_metrics.
  - The OpenXR 1.18.0-pre.2 timing-unit change (sole owner).
  - Profileable Shell (6.6).
  - Project Auditor.
  - Development-build overhead.
  - Correlating with OVR Metrics via `AppendCsvDebugString`.
- **Links to (does not repeat):**
  - `quest-perf:quest-profiling-toolkit`
  - `quest-perf:quest-triage`
  - `unity-perf:unity-cpu-scripting`
  - `unity-perf:unity-draw-calls-batching`
- **References planned:** `references/profiler-markers.md` (marker → meaning → owning skill).
- **Scripts:** None.
- **Primary dossier sources:**
  - unity.md profiling (U5-079 to 102, U5-081, U5-091, X-C2, X-C3), U1-052 to 056
  - quest.md Q1-097 to 104, Q1-106, Q3-060
  - arm-mobile-hw.md A3-050, A1-052
- **Key facts to lead with:**
  - XR.WaitForGPU on the main thread means GPU-bound, not CPU cost (U5-081).
  - FrameTimingManager is partial on XR: CPU render-thread and GPU frame times are not supported on Vulkan or GLES XR; `cpuMainThreadFrameTime` is usable (Q1-106). GPU times on 6.6 are unverified on Quest (X-C3).
  - `XRDisplaySubsystem` times are in seconds, and only what the provider fills is reported [verify on device] (Q1-097). Before OpenXR 1.18.0-pre.2, `GPUAppLastFrameTime` and `GPUCompositorLastFrameTime` were written in milliseconds; from 1.18.0-pre.2 they are in seconds. Normalise by plugin version (U5-091, Q3-060).
  - XR_META_performance_metrics counters must not drive app behaviour; Oculus PerfMetrics returns 0 under OpenXR (Q1-098 to 104).
  - In Perfetto, Unity's render thread is `UnityGfxDeviceW`, not `RenderThread` (A1-052).
  - `OVRMetricsToolSDK` `AppendCsvDebugString` tags CSV rows with game state (A3-050).
  - Frame Debugger works only in the Editor (X-C2).

### gles3-perf

#### gles-versions-unity-output

- **Description:** OpenGL ES 3.0/3.1/3.2 on Quest 2 and Quest 3/3S: what the drivers expose, per-device limits (SSBOs, samples), what Unity emits for GLES (#version, pragma targets, SHADER_API macros), Player settings for OpenGLES3, Unity 6.6's ES 3.1 floor, and the deprecated Oculus XR GLES path. Use when a project ships on GLES, or when a shader or feature behaves differently on GLES than on Vulkan.
- **Goal:** Throughput and Consistency (correctness gates both).
- **Owns:**
  - Driver baseline: versions, driver strings.
  - Per-device GLES limits.
  - Player settings (Auto Graphics API, Require ES3.x).
  - The 6.6 ES 3.1 floor.
  - The "Use OpenGL ES 3.0 shaders" light limit.
  - `#pragma target` mapping.
  - SHADER_API macros.
  - GLES2 removal.
  - The OculusXR GLES path being deprecated.
  - GPU skinning via compute on GLES.
- **Links to (does not repeat):**
  - `gles3-perf:gles-vs-vulkan`
  - `gles3-perf:gles-shader-binaries`
  - `gles3-perf:gles-extensions-multiview`
  - `unity-perf:unity-version-matrix`
  - `unity-perf:unity-urp-settings`
- **References planned:** `references/gles-limits.md` (per-device GL_MAX values and driver strings).
- **Scripts:** None.
- **Primary dossier sources:** gles3.md baseline, §1 (G1-001 to 024, G2-082 driver strings, GLES3-GF1-006, GLES3-GF1-007, GLES3-GF2-001, GLES3-GF2-005), unity.md U1-094, U1-095.
- **Key facts to lead with:**
  - Both headsets expose ES 3.2, GLSL ES 3.20 and ES 3.1+AEP. GL_MAX_SAMPLES = 4. Program binary formats = 1; shader binary formats = 0 (gles3.md baseline).
  - SSBO limits: 4 per vertex/fragment stage on Quest 2 vs 12 on Quest 3; compute 24 vs 36 (G1-001 to 006).
  - Unity 6.6 raises the floor to ES 3.1 (manifest `0x00030001`). "Use OpenGL ES 3.0 shaders" keeps MAX_VISIBLE_LIGHTS at 16 instead of 32 (G1-017 to 020).
  - Macros: `SHADER_API_GLES3`, `SHADER_API_GLES30`, `SHADER_API_GLES31` and `UNITY_PLATFORM_META_QUEST` (G1-022).
  - Compute shaders emit `#version 320 es` on 6.2+ (UUM-60833, GLES3-GF2-005).
  - The Oculus XR GLES path is deprecated from 6.5, and OpenXR has no GLES path (G1-024, G2-093, gles3.md §4).
  - Quest 3S runs its Adreno 740v3 at 492 MHz vs 690 MHz on Quest 3, per the gpuinfo reports (G3-081). This conflicts with Meta's level table (ARM-C3).

#### gles-vs-vulkan

- **Description:** Honest GLES vs Vulkan decision for Unity on Quest 2/3/3S: Vulkan-only Meta features (AppSW, Late Latching, Symmetric Projection, OBD, memoryless), the Vulkan slowdown report UUM-93226, measured comparisons, MSAA cost difference per API, and a single-variable A/B protocol, plus capturing a GLES build (RenderDoc limits, timer queries). Use for "should I switch to Vulkan", when Vulkan seems slower than OpenGL ES, or when validating an API switch.
- **Goal:** Both.
- **Owns:**
  - The decision rule.
  - The inventory of Vulkan-only features.
  - UUM-93226: status, mechanism, OBD workaround.
  - The measured-vs-claimed comparison table.
  - The UUM-149765 MSAA table.
  - Evidence on hitching and CPU overhead.
  - Graphics Jobs modes as a Vulkan-only input.
  - The A/B protocol.
  - GLES capture caveats: timer queries, RenderDoc Meta Fork v68.18, SDP unreliability, AGI unsupported, GPU Systrace deprecated.
- **Links to (does not repeat):**
  - `quest-perf:quest-appsw`
  - `quest-perf:quest-sdk-choices`
  - `quest-perf:quest-profiling-toolkit`
  - `quest-perf:quest-resolution-foveation`
  - `gles3-perf:gles-tile-load-store`
  - `unity-perf:unity-upgrade-risks`
  - `arm-mobile-hw-perf:xr2-gpu-counters-sdp`
- **References planned:**
  - `references/evidence-table.md` (every comparison: setup, device, version, numbers, tag)
  - `references/ab-protocol.md`
  - `references/gles-capture.md`
- **Scripts:** None. The A/B protocol uses `quest_adb.py` and `ovr_metrics_csv.py`.
- **Primary dossier sources:** gles3.md §2 (G1-025 to 079, G1-070 / G2-056, GLES3-GF1-001, GLES3-GF2-002, GLES3-GF2-006, §2.10), §3 (G2-036 to 041, UUM-149765, G2-C9), §8 (G1-080, G2-034, G3-068, G3-073 to 087, GLES3-GF1-004, GLES3-GF2-008), unity.md U1-074 to 077, U1-094, U1-095, U2-094.
- **Key facts to lead with:**
  - Meta calls GLES legacy, and no store rule requires Vulkan (G1-028 to 030). Meta's advanced GPU pipeline page calls Vulkan "the required graphics API", and Unity's Meta Quest build profile defaults to it (U2-094); treat that as guidance, not a VRC.
  - GLES loses features across the range: GRD, GPU occlusion culling and STP never existed on GLES; 6.6 raises the GLES minimum to 3.1, and turning off "Use OpenGL ES 3.0 shaders" raises the light limit from 16 to 32 (U1-094, U1-095).
  - Vulkan-only features:
    - AppSW (about 70%)
    - Late Latching
    - Symmetric Projection (5-15%)
    - OBD (90 MB per eye on Quest 3)
    - MRR (3-8%)
    - memoryless on-tile intermediates
    - Graphics Jobs modes
    - dynamic foveation

    Source: G1-031 to 042, G1-025/026, GLES3-GF2-006.
  - UUM-93226 (Vulkan much slower than GLES because of buffer copies):
    - Closed Won't Fix on 2022.3 through 6000.3.
    - Unity blames a Qualcomm visibility-stream bug.
    - Workaround: OBD.
    - No OS fix confirmed.

    Source: G1-049 to 053, GLES3-GF2-002.
  - UUM-149765 on Quest 3/3S, Unity 6000.0-6000.7a: quote deltas only, because the tracker table is internally inconsistent (G2-C9). 4x MSAA adds about +3.3 ms on GLES vs +5.0 ms on Vulkan; with MSAA off the APIs are within 1 ms; Quest 2 is within about 1 ms (G2-039 to 041).
  - The mechanism is MSAA stores and resolves. The community reports 8 stores per bin vs 1, and bins rising from 16-18 to 63-66 with MSAA (G1-054 to 064).
  - Evidence that GLES hitches less is qualitative only (G1-065 to 067). The CPU-overhead advantage is a vendor claim (G1-068 to 071).
  - Decision rule:
    - Default to Vulkan if any Vulkan-only feature is needed.
    - Consider GLES only for a GPU-bound, MSAA-heavy project that wins a single-variable A/B after OBD and store minimisation.
    - Record the OS and driver strings.

    Source: G1-072 to 079.

#### gles-tile-load-store

- **Description:** Tile-friendly rendering on Quest in OpenGL ES builds only: glClear and glInvalidateFramebuffer placement, avoiding GMEM loads and depth stores, MSAA via multisampled render-to-texture, readbacks, flushes and queries that split passes, and how URP settings map to GL load/store. Use when a GLES build shows LoadColor or StoreDepthStencil stages, when MSAA is expensive on GLES, or when partial clears cost time. Vulkan/Render Graph: unity-render-graph-tiling.
- **Goal:** Throughput.
- **Owns:**
  - GLES clear and invalidate rules.
  - The cost of partial clears.
  - Depth-store cost.
  - Invalidation order.
  - Unity's load/store mapping on GLES: store actions, Opaque Texture dropping MSAA, Depth After Transparents, depth priming, Native RenderPass having no effect, RG on GLES.
  - The MSRTT extensions and resolve behaviour.
  - A2C vs LRZ on GLES.
  - Readbacks, flushes and queries that split passes.
  - GLES XR load/store bugs.
- **Links to (does not repeat):**
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
  - `unity-perf:unity-render-graph-tiling`
  - `unity-perf:unity-urp-settings`
  - `gles3-perf:gles-vs-vulkan`
  - `quest-perf:quest-profiling-toolkit`
- **References planned:**
  - `references/unity-gles-loadstore-map.md` (URP setting → GL calls → stage in ovrgpuprofiler)
  - `references/msrtt.md`
- **Scripts:** None.
- **Primary dossier sources:** gles3.md §3 (G2-001 to 046, G2-083 to 090, GLES3-GF2-003, UUM-45041, UUM-8381, UUM-70930, UUM-109377, UUM-91896), unity.md U2-088 (GLES specifics).
- **Key facts to lead with:**
  - A partial clear costs 37%, and a depth store 50%, in the cited measurements (G2-005, G2-007).
  - Unity does emit `glInvalidateFramebuffer` (GLES3-GF2-003). Invalidation order matters (G2-008).
  - Each extra pass costs a full store (G2-011).
  - Opaque Texture drops MSAA on GLES. Native RenderPass has no effect on GLES. An intermediate texture removes FFR (G2-013 to 027).
  - StoreColor goes from 0.04 to 0.15 ms on GLES vs 0.45 ms on Vulkan with MSAA (G2-041). On Quest 2, 4x costs about +7 ms (gles3.md §3.4; UUM-149765 is internally inconsistent, G2-C9).
  - Binning took 4.5 ms of 9.7 ms in the cited capture. Concurrent binning exists only on A7x (G2-084 to 090).
  - Readbacks, glFlush and queries split passes (G2-028 to 033).

#### gles-extensions-multiview

- **Description:** Adreno and Meta OpenGL ES extensions on Quest 2/3/3S and how Unity uses them: OVR_multiview2, framebuffer fetch, QCOM_texture_foveated (FFR mechanics on GLES), shading-rate extensions, tiled-rendering control, ASTC decode mode and other QCOM/EXT extensions, with per-device availability. Use when relying on a GLES extension, when multiview crashes or misrenders on GLES, or checking whether a GLES feature exists on a headset.
- **Goal:** Throughput.
- **Owns:**
  - The extension matrix per device.
  - OVR_multiview2 and the multiview MSRTT.
  - SPI macros on GLES.
  - Multiview bugs: UUM-102876, OXPB-144.
  - The vertex-work budget under multiview.
  - Framebuffer fetch on GLES, including FRAMEBUFFER_INPUT becoming `.Load()`.
  - QCOM foveation mechanics and setprops.
  - VRS extensions.
  - Tiled-rendering control (no `QCOM_binning_control`).
  - Miscellaneous extensions: frame extrapolation, ASTC decode mode, anisotropy, RGB9_E5, LOD bias, clip control, context priority, buffer storage.
- **Links to (does not repeat):**
  - `quest-perf:quest-resolution-foveation`
  - `unity-perf:unity-draw-calls-batching`
  - `unity-perf:unity-render-graph-tiling`
  - `gles3-perf:gles-tile-load-store`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
- **References planned:** `references/extension-matrix.md` (extension × Quest 2 × Quest 3 × Unity use × finding).
- **Scripts:** None.
- **Primary dossier sources:** gles3.md §4 (G2-047 to 055, G2-057 / G3-046, G2-058, G3-045, G3-047, GLES3-GF2-004), §7 (G1-009 to 015, G1-044, G2-032, G2-059 to 064, G2-091/092, G3-043, G3-044, G3-048, G3-050, G3-051 to 072, GLES3-GF1-005, GLES3-GF1-008, GLES3-GF2-006/007).
- **Key facts to lead with:**
  - Unity uses OVR_multiview2 plus the multiview MSRTT on GLES (GLES3-GF2-004). The win is on the CPU; budget vertex work at about 2x (G2-047 to 055).
  - Multiview + GLES3 crashes in release builds (OXPB-144). Dev builds spam GL errors (UUM-102876) (gles3.md §4).
  - FFR on GLES works only on direct swapchain rendering (G2-059 to 061).
  - FFR is controlled with `debug.oculus.foveation.level` 0-4 and `debug.oculus.foveation.dynamic 0` (G1-044, G2-062, G3-053).
  - FRAMEBUFFER_INPUT compiles to a texture `.Load()` on GLES, not framebuffer fetch (GLES3-GF1-008).
  - There is no `QCOM_binning_control` (G2-091/092).
  - Only 7 gpuinfo reports exist, so per-device availability is thin evidence (GLES3-GF1-005).

#### gles-driver-overhead

- **Description:** CPU-side OpenGL ES driver cost on Quest: state-change and program-switch overhead, uniform buffer limits, buffer streaming and orphaning, instancing and indirect draws, fences, compute interleaving, and Unity's GLES low-overhead options. Use when a GLES build is render-thread-bound, when GL draw or state calls dominate a trace, or when porting native GLES code paths to Quest.
- **Goal:** Throughput (CPU) and Consistency (sync stalls).
- **Owns:**
  - State-change costs.
  - The UBO budget.
  - Instancing and indirect draws.
  - 16-bit indices.
  - The position-only stream.
  - Vertex-shader texture fetches running twice.
  - Buffer streaming and orphaning.
  - Fences.
  - Indirect compute workgroup sizing.
  - Not interleaving compute with graphics.
  - Linear-space blending cost.
  - Low Overhead Mode / KHR_no_error.
- **Links to (does not repeat):**
  - `unity-perf:unity-draw-calls-batching`
  - `unity-perf:unity-cpu-scripting`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
  - `arm-mobile-hw-perf:xr2-shader-cost-model`
  - `gles3-perf:gles-vs-vulkan`
- **References planned:** `references/state-costs.md`.
- **Scripts:** None.
- **Primary dossier sources:** gles3.md §5 (G2-065 to 080, G2-094, G1-043, UUM-102878), quest.md Q2-077.
- **Key facts to lead with:**
  - Meta's Quest 1 measurements: a material change costs +64% and a shader switch +175% (G2-065/066). These are old hardware; treat them as ratios.
  - Keep a shader's total UBO use under 7372 B, so it stays in constant RAM (G2-070, A2-074).
  - Do not interleave compute with graphics (G2-067). Indirect compute workgroups should be ≥ 64 (G2-080).
  - Vertex-shader texture fetches run twice: in the binning pass and in the render pass (G2-077/078).
  - Low Overhead Mode / KHR_no_error exists (G1-043, G2-079). It is an Oculus XR plugin setting, GLES-only, and does nothing on Vulkan (Q2-077). Its status is tracked in UUM-102878.

#### gles-shader-binaries

- **Description:** GLES-only shader compilation and program binaries on Quest 2/3/3S: first-use compile hitches in OpenGL ES builds, the Android blob cache and its limits, glProgramBinary and Unity's shader cache, cache wipes after OS updates, warmup on GLES (SVC fallback, multiview variants), mediump emission and Adreno shader limits. Use for shader hitches in a GLES build, stutter after a Quest OS update, or GLES precision bugs. Vulkan PSO warmup: unity-shader-hitches.
- **Goal:** Consistency (primary) and Throughput (precision).
- **Owns:**
  - First-use compile on GLES and its Profiler markers.
  - Blob cache sizes, eviction and wipes.
  - glProgramBinary and UnityShaderCache.
  - Warmup on GLES: GSC falls back to SVC; multiview variants are missed.
  - Duplicate shaders in AssetBundles.
  - GLES precision emission: mediump, REAL_IS_HALF, depth at float, no reversed Z, `#version`.
  - Adreno instruction and binding cliffs as they appear on GLES.
  - The 31-varying limit.
- **Links to (does not repeat):**
  - `unity-perf:unity-shader-hitches`
  - `unity-perf:unity-shader-authoring`
  - `arm-mobile-hw-perf:xr2-shader-cost-model`
  - `gles3-perf:gles-versions-unity-output`
- **References planned:** `references/blob-cache.md`.
- **Scripts:** None.
- **Primary dossier sources:** gles3.md §6 (G3-001 to 042, G2-069, G2-081 / G3-015, GLES3-GF1-002, GLES3-GF1-003, GLES3-GF1-007).
- **Key facts to lead with:**
  - The Android blob cache holds 64 KB per value and 2 MB in total, with random eviction; the multifile cache is 32 MB. It is wiped on every `ro.build.id` change, i.e. every OS update (G3-009 to 018).
  - GSC warmup falls back to SVC warmup on GLES. `STEREO_MULTIVIEW_ON` variants are missed (G3-019 to 025, GLES3-GF1-002).
  - The Adreno GLES driver never recompiles for state (G3-001 to 008).
  - mediump can be up to 2x faster. Keep depth at float. There is no reversed Z on GLES (G3-026 to 035).
  - A7x cliffs: at multiples of 2000 instructions, 16 UBOs, and 16 textures+SSBOs (G3-037 to 042, A2-070).

### arm-mobile-hw-perf

#### xr2-gen1-vs-gen2

- **Description:** Silicon spec facts for Snapdragon XR2 Gen 1 (Quest 2) vs XR2 Gen 2 (Quest 3/3S): CPU core types and clusters, maximum clocks, Adreno 650 vs 740 generation differences, GMEM, memory type and bandwidth, and Quest 3S vs Quest 3 silicon. Use when checking a spec-sheet claim such as A715 cores, a 690 MHz GPU or LPDDR5 bandwidth, or explaining a hardware difference. Budgets per headset: quest-budgets-tiers.
- **Goal:** Both (context for every device-specific fix).
- **Owns:**
  - The SoC architecture explanation for all bundles.
  - CPU clusters and core types.
  - Why 2.84 GHz is not an app clock.
  - GPU generation differences: register file, concurrent binning, LPAC, vertex cache, cliffs, per-view render areas.
  - GMEM size claims.
  - Memory type and bandwidth claims.
  - Device scaling claims.
  - Out-of-scope SoC disambiguation (XR2+ Gen 2, VR Glasses).
- **Links to (does not repeat):**
  - `quest-perf:quest-levels-thermal` (clock table)
  - `quest-perf:quest-budgets-tiers`
  - `arm-mobile-hw-perf:xr2-cpu-threads-neon`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
  - `arm-mobile-hw-perf:xr2-bandwidth-power`
- **References planned:** `references/soc-comparison.md` (full side-by-side, with conflicts ARM-C1, C2, C9, C10, C20).
- **Scripts:** None.
- **Primary dossier sources:** arm-mobile-hw.md baseline table, §1 (A1-001 to 027, A2-001 to 003, A1-008, A1-023, A3-099, A3-100, ARM-GF1-005, ARM-GF2-004), conflicts ARM-C1, C2, C3, C9, C10, C20.
- **Key facts to lead with:**
  - Quest 2: 1x A77 at 2.84 GHz + 3x A77 at 2.42 GHz + 4x A55 at 1.80 GHz. Apps get 3 cores, and the maximum app clock is 2.42 GHz, Boost only (A1-001, A1-003, A1-004).
  - Quest 3/3S: 6x Cortex-A78C, 4 at 2.36 GHz + 2 at 2.05 GHz. No little cores. The A715/A510 claim is wrong (A1-013, A1-014, ARM-C1).
  - Quest 3 and 3S share SoC, GPU (Adreno 740v3) and level table. Only the board and display differ (A1-015, A2-001).
  - GMEM is 1 MB on Adreno 650 and about 2 MB on Adreno 740 per Meta. The kernel gives 1.125 MiB for the 650 (A2-010, A2-011, ARM-C9, ARM-C10).
  - The A7xx register file per SP is about 1.5x the 650's (reg_size_vec4 96 vs 64). Concurrent binning and LPAC are Quest 3/3S only (A2-003, A2-026, A2-094).
  - Memory: Quest 2 has 6 GB LPDDR4X; Quest 3/3S have 8 GB LPDDR5. The configured data rate and bandwidth are unpublished (A1-008, A1-023, ARM-C2).
  - Neither core has SVE/SVE2. One Armv8.2 + FP16 + dotprod target covers every Quest (A1-075, A1-076).

#### xr2-cpu-threads-neon

- **Description:** ARM CPU behaviour for Unity on Quest 2 (Cortex-A77/A55) and Quest 3/3S (Cortex-A78C): how many cores an app gets, thread placement of UnityMain, render and job workers, affinity arguments, job worker counts, cache lines and data layout, NEON costs, Burst Arm64 targets, FloatMode and Neon intrinsics. Use when making Burst code faster on Quest, when threads land on the wrong cores, or asking how many cores a Quest app gets.
- **Goal:** Throughput (CPU) and Consistency (thread migration, scheduling).
- **Owns:**
  - The app-core set and how to read it (`Cpus_allowed_list`).
  - Thread registration (XR_KHR_android_thread_settings) and the `SP=`/`TA=` fields.
  - Unity's thread-configuration arguments.
  - Job-worker counts.
  - Main-thread cycle budgets per level.
  - Cache lines and false sharing.
  - Unaligned access and store-forwarding.
  - The NEON pipeline: FMA throughput, divide/sqrt, FP16 conversion, dotprod.
  - Burst Arm64 targets.
  - FloatMode and FloatPrecision.
  - Neon intrinsics gating.
  - OptimizeFor.
- **Links to (does not repeat):**
  - `unity-perf:unity-cpu-scripting`
  - `quest-perf:quest-levels-thermal`
  - `arm-mobile-hw-perf:xr2-gen1-vs-gen2`
  - `quest-perf:quest-profiling-toolkit`
- **References planned:**
  - `references/thread-placement.md` (adb and Perfetto recipes)
  - `references/neon-costs.md` (A77/A78 instruction table)
  - `references/burst-settings.md`
- **Scripts:** None. The measurement methods live in references.
- **Primary dossier sources:** arm-mobile-hw.md §1.3 (A1-004, A1-026), §2 (A1-010 to 083, A1-086 VrApi log fields, AS-001, ARM-GF1-001), conflicts ARM-C7, ARM-C19.
- **Key facts to lead with:**
  - Quest 2 apps get 3 cores (probably cpu4-6, the A77 gold cluster). The app-core count on Quest 3/3S is unpublished; a community report says 2 job workers (A1-004, A1-055).
  - Main-thread cycles per frame at L4 and 72 Hz: 20.6 M on Quest 2, 26.7 M on Quest 3/3S (A1-026, derived).
  - Unity's `big`/`little` aliases rely on a 2x capacity rule. On Quest 3/3S every core is A78C, so they may not select what you expect (A1-049, A1-050).
  - `JobWorkerCount` can be lowered but not raised. Setting it disables automatic adaptation (A1-053, A1-054).
  - FMLA: 4-cycle latency, 2 per cycle. That is 23.7 GFLOPS per core on Quest 2 at L4 and 30.7 GFLOPS on Quest 3. Use about 8 independent accumulators (A1-068).
  - Divide and sqrt run only on V0, not fully pipelined, and FP16 does not help them. Use FloatMode.Fast for visual-only math (A1-069, A1-080).
  - The Burst target ARMV8A_HALFFP matches every Quest core. ARMV9A is dead code on Quest (A1-078, A1-079).
  - Use 64-byte cache lines on all Quest cores. Pad per-worker data to avoid false sharing (A1-063).

#### xr2-adreno-architecture

- **Description:** Adreno 650/740 tile-based architecture on Quest: binning pass, FlexRender binned vs direct mode, GMEM size and bin arithmetic, LRZ and early-Z rules, overdraw and sorting, UBWC compression, per-bin vertex cost, MSAA resolve in tile, query costs, async compute, and which Arm Mali advice does not transfer. Use to explain why the Quest GPU behaves as it does, to read bin counts, for heavy overdraw from transparents or particles, or to judge if a technique is tile-friendly.
- **Goal:** Throughput (primary) and Consistency (query and flush stalls).
- **Owns:**
  - The binning/render two-phase model.
  - Bin-sizing arithmetic.
  - FlexRender modes and direct-mode triggers.
  - Concurrent binning.
  - LRZ rules: disable-until-clear, per-draw, direction.
  - Early-Z and Fast-Z.
  - No HSR: sort front-to-back.
  - UBWC and its disablers.
  - Format priorities.
  - Binning-pass vertex cost.
  - Hardware load/store and in-tile MSAA resolve.
  - Input-attachment sample parallelism.
  - Query cost per bin.
  - Compute vs fragment, and LPAC.
  - The Mali-to-Adreno transfer map.
- **Links to (does not repeat):**
  - `unity-perf:unity-render-graph-tiling`
  - `gles3-perf:gles-tile-load-store`
  - `unity-perf:unity-shader-authoring`
  - `arm-mobile-hw-perf:xr2-shader-cost-model`
  - `arm-mobile-hw-perf:xr2-bandwidth-power`
  - `quest-perf:quest-profiling-toolkit`
- **References planned:**
  - `references/bin-math.md` (bytes-per-pixel table, examples)
  - `references/lrz-rules.md`
  - `references/ubwc.md`
  - `references/mali-transfer-map.md`
- **Scripts:** None.
- **Primary dossier sources:** arm-mobile-hw.md §3 (A2-004 to 062, A2-093 to 100, A3-003 to 026, ARM-GF1-006), conflicts ARM-C9 to C14, ARM-C23.
- **Key facts to lead with:**
  - A bin's footprint is (colour B + depth B) × samples × 2 views. At 4x MSAA with RGBA8 and D24S8 that is 32 B/px/view, giving 96x176 bins on Quest 2, or 135 bins for 1440x1584 (A2-013, A3-005, ARM-GF1-006).
  - Each vertex is shaded at least twice per frame (binning + render), and up to 2 × bins + 1 times. Growing the bin count grows vertex cost (A2-046, A2-047).
  - Direct mode (a depthless full-screen pass, few draws, heavy VS texture fetches) skips binning and loses FFR (A2-021 to 023).
  - LRZ is killed until the next clear by a depth-direction change or ZTest Always/NotEqual plus a depth write. Blend, stencil, colour mask or framebuffer fetch plus a depth write freeze LRZ writes (A2-032, A2-033).
  - Adreno has no hidden-surface removal; sort opaques front-to-back (A2-039, A2-097).
  - UBWC is lost with compute writes, LINEAR tiling, CPU readback, MUTABLE_FORMAT and (per Qualcomm) FDM. The FDM case conflicts with Meta FFR (A2-043, ARM-C13, ARM-C14).
  - Timer queries cost 2-5 µs per bin, i.e. 0.27-0.68 ms at 135 bins. A query before an invalidate forces the depth store (A2-060, A2-061).
  - What does not transfer from Mali: 16x16 tiles, the 128 bpp rule, FPK, PLS, Mali counters, malioc (A2-095 to 099).

#### xr2-shader-cost-model

- **Description:** Adreno hardware shader cost model on Quest 2/3/3S: fp16 vs fp32 rate, register (GPR) pressure and wave occupancy, wave64/128 divergence, branch costs, instruction and binding cliffs, varyings and constants, transcendental cost, and texture filtering and cache behaviour. Use when estimating what an instruction or sampler costs, reading shader stats (GPRs, instruction count), or explaining why half precision did or did not help. Writing URP HLSL: unity-shader-authoring.
- **Goal:** Throughput.
- **Owns:**
  - fp16 rate and conversion cost.
  - GPRs and occupancy.
  - Wave size and divergence.
  - The branch cost ladder.
  - A7x cliffs and the sampler limit.
  - Instruction-cache pressure.
  - Special-function rate.
  - Varying and constant packing.
  - The scalar ALU and preamble.
  - Texture filtering cost order.
  - Explicit-gradient sampling cost.
  - Texture cache sizes (proxies).
  - The A5x ALU:TEX ratio.
  - Combined vs separate samplers.
  - Buffer reads via the texture pipe.
  - Hardware PCF.
  - Texture format priority.
- **Links to (does not repeat):**
  - `unity-perf:unity-shader-authoring`
  - `gles3-perf:gles-shader-binaries`
  - `arm-mobile-hw-perf:xr2-gpu-counters-sdp`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
- **References planned:** `references/cost-table.md` (operation → relative cost → source → device applicability).
- **Scripts:** None. The ALU-throughput measurement method (A2-004) lives in the reference.
- **Primary dossier sources:** arm-mobile-hw.md §3.1 (A2-004 to 009), §4 (A2-063 to 092, A3-015, A3-017), conflict ARM-C15.
- **Key facts to lead with:**
  - fp16 can be about 2x the speed and about 2x the power efficiency of fp32. That holds only if the compiler keeps values in half registers; check GPR counts (A2-063, A2-064, ARM-C15).
  - Adreno is scalar: vec4 math buys nothing per ALU op, but packing still matters for varyings and constants (A2-009, A2-073, A2-074).
  - Divergence is paid per 64- or 128-wide wave (A2-068).
  - Branch cost ladder: specialization constant < compile-time constant < uniform < computed value (A2-069).
  - A7x cliffs: 2000 instructions, 16 UBOs, 16 textures+SSBOs, 32 vertex buffers. There are 16 samplers on A6x-A8x (A2-070).
  - Special functions run at about 1/8 rate on the A640 proxy; `pow` costs two (A2-072).
  - 16x anisotropic can cost up to 16x in the worst case, but averages under 2x. SampleGrad gradients are not cached (A2-078, A2-079).
  - Keep total UBO size under 7372 B. Separate sampler objects cost 2-5% fill rate against combined samplers (A2-074, A2-083).

#### xr2-bandwidth-power

- **Description:** Memory bandwidth, power and heat source on XR2 Quest headsets: why DRAM traffic dominates energy, per-frame traffic budgets for eye-buffer stores and extra full-screen passes, measuring bandwidth (RenderDoc byte counters, MQDH GPU Memory Access), battery and whole-headset power figures, and the unknown thermal envelope. Use for battery drain, watts, a bandwidth-bound GPU, or estimating the DRAM bytes of a pass. Throttling behaviour: quest-levels-thermal.
- **Goal:** Consistency (thermal decay) and Throughput (bandwidth-bound frames).
- **Owns:**
  - DRAM energy rules of thumb.
  - Derived traffic budgets: eye-buffer store, broken load/store, extra pass.
  - Bandwidth measurement methods.
  - Memory-clock signals (`Mem=`, MEM F).
  - Power figures: battery capacity, derived average draw, measured per-scenario power.
  - The unpublished thermal envelope and how to measure it.
  - The Meta zero-sum power framing.
- **Links to (does not repeat):**
  - `quest-perf:quest-levels-thermal`
  - `quest-perf:quest-profiling-toolkit`
  - `arm-mobile-hw-perf:xr2-adreno-architecture`
  - `arm-mobile-hw-perf:xr2-gpu-counters-sdp`
  - `unity-perf:unity-urp-settings`
  - `unity-perf:unity-render-graph-tiling` (post-processing cost)
- **References planned:**
  - `references/traffic-budgets.md` (derived tables per device and Hz)
  - `references/power-figures.md`
- **Scripts:** None. It uses `ovr_metrics_csv.py` for BAT C / POW C trends.
- **Primary dossier sources:** arm-mobile-hw.md §1.5 and §1.7 (A1-008, A1-023, A3-098, ARM-GF1-002, ARM-GF2-001 to 003), §5 (A3-001 to 056, ARM-GF1-004, ARM-GF2-004), conflicts ARM-C2, C22, C24, C25.
- **Key facts to lead with:**
  - A DRAM access costs about 100x an on-chip access. Arm's 2014 rule of thumb is about 0.1 W per GB/s; use it as an order of magnitude only (A3-001, A3-002, ARM-C22).
  - One resolved RGBA8 store of the default 1680x1760 stereo buffer is about 23.65 MB/frame: 1.70 GB/s at 72 Hz and 2.84 GB/s at 120 Hz (A3-009, derived).
  - Storing 4x MSAA colour and depth samples instead is about 13.6 GB/s at 72 Hz, roughly 1.6 W against about 0.2 W for a correct setup (A3-011, derived).
  - One extra full-screen RGBA8 pass costs about 3.4 GB/s at 72 Hz; FP16 doubles it (A3-012, derived).
  - Quest 3 battery is 19.44 Wh at about 2 h, i.e. about 9.7 W average for the whole headset. Measured: 7.5-9.0 W for a VR game and 10.5-12.0 W for an MR game (ARM-GF1-002, ARM-GF2-002, [measured], OS v57).
  - No TDP or thermal envelope is published for any Quest. Measure with the long-session recipe (§1.7, A3-093).
  - Only RenderDoc Meta Fork's `Read Total` / `Write Total` give per-draw bytes. Compare the summed Write Total with the derived store size to catch unwanted stores (A3-036, A3-037).

#### xr2-gpu-counters-sdp

- **Description:** Interpreting Adreno GPU counters on Quest, and the status of Snapdragon Profiler: what % Stalled on System Memory, texture miss, fetch stall, Bus Busy, wave occupancy and binning share mean, Qualcomm's healthy ranges, the Adreno Offline Compiler and shader stats, driver-version checks, and why Snapdragon Profiler is treated as unsupported on Quest. Use when a counter value needs a verdict, or when someone asks for Snapdragon Profiler.
- **Goal:** Both (diagnosis).
- **Owns:**
  - Counter meanings and healthy ranges.
  - Mapping counters across ovrgpuprofiler, RenderDoc Meta Fork, OVR Metrics and SDP.
  - SDP status and the test procedure.
  - SDP overhead.
  - UBWC visibility (SDP only).
  - The Adreno Offline Compiler.
  - The driver-version check.
  - The "Slow To Trace" memory counters.
  - AGI/APA status.
  - The lineage of Meta's Performance Interface Library.
- **Links to (does not repeat):**
  - `quest-perf:quest-profiling-toolkit`
  - `arm-mobile-hw-perf:xr2-shader-cost-model`
  - `arm-mobile-hw-perf:xr2-bandwidth-power`
  - `gles3-perf:gles-vs-vulkan`
- **References planned:**
  - `references/counter-glossary.md` (counter → tool → meaning → healthy range → source)
  - `references/sdp-on-quest.md`
- **Scripts:** None.
- **Primary dossier sources:**
  - arm-mobile-hw.md §4.3 (A2-087 to 092), §5.2 (A3-054 to 056), §7.1 (A3-057 to 067, A2-090), ARM-C16
  - gles3.md G3-084/085, GLES3-GF2-008
- **Key facts to lead with:**
  - Qualcomm healthy ranges (A3-054, Adreno in general, not Quest-specific):
    - % Stalled on System Memory under about 2%
    - % Texture Fetch Stall under about 2%
    - % Texture L1 Miss under 50% and L2 Miss under 40%
    - binning at 10-20% of the pass
    - Bus Busy up to about 25% for a battery-conscious app
  - Low % Wave Context Occupancy means GPR or instruction-cache pressure (A2-067, A2-090).
  - ovrgpuprofiler per-draw metrics add stalls. Use them only to compare draws with each other (A2-088).
  - Meta's tool index omits Snapdragon Profiler. Community reports show capture failures on Quest 1/2/3 (A3-057, A3-063 to 065, GLES3-GF2-008). The working position is "unsupported unless proven on your OS build" (A3-067).
  - SDP adds about 5% CPU even when it only traces frame rate (A3-061).
  - Check the driver with `adb shell dumpsys SurfaceFlinger | grep GLES`. Vulkan shader stats need driver 636+ (A2-089).

## Ownership index

| Topic | Owning skill | Linking skills |
|---|---|---|
| Triage and bottleneck routing | quest-triage | all skills |
| Headroom targets (70% CPU / 80% GPU / hitches <3%) | quest-triage | quest-budgets-tiers, quest-levels-thermal |
| Two-step isolation workflow (camera off, then render scale 0.01) | quest-triage | quest-resolution-foveation, unity-profiling-workflow |
| Frame budgets and per-device tiers | quest-budgets-tiers | quest-triage, xr2-gen1-vs-gen2 |
| Draw-call, triangle, fill-rate and texture-memory budgets | quest-budgets-tiers | unity-draw-calls-batching, unity-memory-assets, quest-resolution-foveation |
| Porting content between Quest 3 and Quest 2 | quest-budgets-tiers | xr2-gen1-vs-gen2 |
| App memory limits (PSS, lmkd) | quest-budgets-tiers | unity-memory-assets |
| Headset detection and adaptive quality | quest-budgets-tiers | unity-urp-settings, quest-levels-thermal |
| Store VRC performance requirements and Performance Analytics | quest-budgets-tiers | quest-triage, quest-profiling-toolkit |
| Stale frames, FrameSync, Phase Sync, Late Latching | quest-frame-pacing | quest-triage, quest-profiling-toolkit, gles-vs-vulkan |
| OpenXR Latency Optimization | quest-frame-pacing | unity-urp-settings, quest-sdk-choices |
| Refresh-rate choice, thermal refresh drops, supportedDevices gating | quest-frame-pacing | unity-urp-settings, quest-levels-thermal |
| CPU/GPU level system and level-to-clock tables | quest-levels-thermal | xr2-gen1-vs-gen2, xr2-cpu-threads-neon, quest-mr-costs |
| Level-based headroom (design to L4; L5 opportunistic) | quest-levels-thermal | quest-triage, quest-budgets-tiers |
| XR_EXT_performance_settings / XrPerformanceSettingsFeature | quest-levels-thermal | quest-sdk-choices |
| Boost, dual-core mode, level trading | quest-levels-thermal | xr2-cpu-threads-neon, unity-cpu-scripting, quest-sdk-choices |
| Thermal throttling, PLS, Battery Saver, long-session protocol | quest-levels-thermal | xr2-bandwidth-power, quest-triage |
| Eye-buffer resolution, render scale, dynamic resolution | quest-resolution-foveation | unity-urp-settings, quest-levels-thermal |
| FFR, dynamic foveation, subsampled layout, Symmetric Projection, MVRR, MQSR | quest-resolution-foveation | unity-urp-settings, gles-extensions-multiview, xr2-adreno-architecture, unity-upgrade-risks |
| Application SpaceWarp | quest-appsw | quest-resolution-foveation, gles-vs-vulkan, unity-version-matrix |
| Compositor layers | quest-compositor-layers | quest-resolution-foveation, unity-cpu-scripting |
| Mixed reality costs (passthrough, Depth API, MRUK, hands/body) | quest-mr-costs | quest-levels-thermal, xr2-bandwidth-power |
| SDK/plugin choices, OBD, manifest-flag inventory, PST | quest-sdk-choices | unity-version-matrix, gles-vs-vulkan, unity-upgrade-risks |
| Profiling toolkit (OVR Metrics, logcat, MQDH/Perfetto, RenderDoc Meta Fork, ovrgpuprofiler, simpleperf, gpumeminfo, setprops, Runtime Optimizer) | quest-profiling-toolkit | all skills |
| OVR Metrics CSV analysis and ADB helper scripts | quest-profiling-toolkit | quest-levels-thermal, quest-frame-pacing, gles-vs-vulkan |
| Unity/URP feature-by-version matrix and Meta minimum versions | unity-version-matrix | all unity-perf skills, quest-appsw, quest-sdk-choices |
| Upgrade regressions, patch floors, API breaks | unity-upgrade-risks | unity-version-matrix, quest-resolution-foveation |
| URP asset, Player and XR settings; rendering-path choice | unity-urp-settings | unity-lighting, unity-render-graph-tiling |
| MSAA level choice (2x vs 4x) | unity-urp-settings | xr2-adreno-architecture, gles-vs-vulkan, gles-tile-load-store |
| Unity settings audit script | unity-urp-settings | quest-triage |
| Render Graph on tilers, pass merging, memoryless, on-tile post, Native RenderPass | unity-render-graph-tiling | xr2-adreno-architecture, gles-tile-load-store |
| URP post-processing cost (bloom, tonemapping, colour grading, on-tile post) | unity-render-graph-tiling | xr2-bandwidth-power, quest-resolution-foveation, unity-urp-settings |
| Draw calls and batching (SRP Batcher, static, instancing, BRG, GRD, GPU occlusion) | unity-draw-calls-batching | quest-budgets-tiers, gles-driver-overhead |
| Multiview/SPI draw-call savings | unity-draw-calls-batching | gles-extensions-multiview, xr2-adreno-architecture |
| URP HLSL authoring for Quest (precision, LRZ-safe states, keywords, SPI macros) | unity-shader-authoring | xr2-shader-cost-model, gles-shader-binaries |
| Shader variants, stripping, PSO/GSC warmup, Vulkan PSO cache | unity-shader-hitches | gles-shader-binaries, quest-frame-pacing, quest-triage |
| Lighting, shadows, probes, lightmaps, APV | unity-lighting | unity-urp-settings |
| CPU/scripting (GC, IL2CPP, jobs usage, Graphics Jobs, MT rendering, physics, UI, animation and GPU skinning, CoreCLR status) | unity-cpu-scripting | xr2-cpu-threads-neon, gles-driver-overhead |
| Memory and assets (ASTC, mip streaming, meshes, AUP, loading) | unity-memory-assets | quest-budgets-tiers, xr2-bandwidth-power |
| Unity profiling workflow (Profiler, markers, FrameTimingManager, Frame Debugger, Project Auditor) | unity-profiling-workflow | quest-triage, quest-profiling-toolkit |
| In-app runtime stats hooks (XRDisplaySubsystem, XRStats, OVRPlugin perf metrics) and the OpenXR 1.18 timing-unit change | unity-profiling-workflow | unity-upgrade-risks, quest-profiling-toolkit |
| GLES versions, limits and what Unity emits | gles-versions-unity-output | gles-vs-vulkan, unity-version-matrix |
| GLES-vs-Vulkan decision (UUM-93226, UUM-149765, Vulkan-only features, A/B protocol) | gles-vs-vulkan | quest-triage, unity-upgrade-risks, quest-appsw, quest-sdk-choices |
| GLES capture caveats | gles-vs-vulkan | quest-profiling-toolkit, xr2-gpu-counters-sdp |
| Tile-friendly GLES rendering (clear/invalidate, MSRTT, flush and readback splits) | gles-tile-load-store | unity-render-graph-tiling, xr2-adreno-architecture |
| Multiview on GLES (OVR_multiview2) | gles-extensions-multiview | unity-draw-calls-batching |
| Adreno GLES extensions | gles-extensions-multiview | quest-resolution-foveation, gles-versions-unity-output |
| GLES driver and state overhead, Low Overhead Mode | gles-driver-overhead | unity-draw-calls-batching, unity-cpu-scripting, quest-sdk-choices |
| GLES program binaries, blob cache, GLES warmup, GLES precision emission | gles-shader-binaries | unity-shader-hitches, unity-shader-authoring |
| XR2 Gen 1 vs Gen 2 hardware | xr2-gen1-vs-gen2 | quest-budgets-tiers, quest-levels-thermal, all xr2 skills |
| App cores, thread placement, Unity thread arguments, job-worker counts | xr2-cpu-threads-neon | unity-cpu-scripting, quest-levels-thermal |
| Caches, data layout, NEON costs, Burst targets and float modes | xr2-cpu-threads-neon | unity-cpu-scripting |
| Adreno binning, FlexRender, GMEM, bin math | xr2-adreno-architecture | unity-render-graph-tiling, gles-tile-load-store, quest-resolution-foveation |
| LRZ, early-Z, Fast-Z, overdraw | xr2-adreno-architecture | unity-shader-authoring, unity-lighting |
| UBWC and attachment formats | xr2-adreno-architecture | unity-urp-settings, xr2-bandwidth-power |
| Binning-pass vertex cost and vertex layout | xr2-adreno-architecture | unity-memory-assets, gles-driver-overhead |
| Hardware load/store, in-tile MSAA resolve, subpasses, query cost | xr2-adreno-architecture | unity-render-graph-tiling, gles-tile-load-store, unity-urp-settings |
| Compute on Adreno and LPAC | xr2-adreno-architecture | gles-driver-overhead |
| Mali-to-Adreno transfer map | xr2-adreno-architecture | all gles and unity tiling skills |
| Shader cost model | xr2-shader-cost-model | unity-shader-authoring, gles-shader-binaries |
| DRAM energy and traffic budgets; bandwidth measurement | xr2-bandwidth-power | unity-urp-settings, unity-render-graph-tiling |
| Power figures and thermal envelope | xr2-bandwidth-power | quest-levels-thermal, quest-mr-costs |
| Adreno counter interpretation and Snapdragon Profiler status | xr2-gpu-counters-sdp | quest-profiling-toolkit, xr2-shader-cost-model, gles-vs-vulkan |

Minimum-coverage check. Every required topic is owned exactly once:

- **quest-perf:**
  - triage → quest-triage
  - budgets and tiers → quest-budgets-tiers
  - frame pacing, levels and thermal → quest-frame-pacing + quest-levels-thermal (split, decision 9)
  - resolution and foveation → quest-resolution-foveation
  - AppSW → quest-appsw
  - compositor layers → quest-compositor-layers
  - MR costs → quest-mr-costs
  - SDK/plugin choices → quest-sdk-choices
  - profiling toolkit → quest-profiling-toolkit
- **unity-perf:**
  - version matrix → unity-version-matrix
  - upgrade risks → unity-upgrade-risks
  - URP asset settings → unity-urp-settings
  - Render Graph on tilers → unity-render-graph-tiling
  - draw calls and batching → unity-draw-calls-batching
  - shaders and PSO hitches → unity-shader-authoring + unity-shader-hitches (split, decision 15)
  - lighting → unity-lighting
  - CPU/scripting → unity-cpu-scripting
  - memory/assets → unity-memory-assets
  - profiling workflow → unity-profiling-workflow
- **gles3-perf:**
  - versions and Unity output → gles-versions-unity-output
  - GLES-vs-Vulkan decision → gles-vs-vulkan
  - tile-friendly rendering → gles-tile-load-store
  - multiview → gles-extensions-multiview
  - driver/state overhead → gles-driver-overhead
  - shaders and program binaries → gles-shader-binaries
  - Adreno extensions → gles-extensions-multiview
  - capture → gles-vs-vulkan (decision 13)
- **arm-mobile-hw-perf:**
  - XR2 Gen 1 vs Gen 2 → xr2-gen1-vs-gen2
  - CPU thread placement and NEON/Burst → xr2-cpu-threads-neon
  - Adreno architecture → xr2-adreno-architecture
  - shader cost model → xr2-shader-cost-model
  - bandwidth → xr2-bandwidth-power
  - thermals → xr2-bandwidth-power (physics) with the runtime half in quest-levels-thermal (decision 10)
  - Snapdragon Profiler → xr2-gpu-counters-sdp

## Coverage matrix

Legend:
- "yes" means the topic applies and has sourced content.
- "partial" means some content is sourced and the rest is marked `[verify on device]`.
- "n/a" means the topic does not apply.

Unity versions are the range the skill's content covers.

| Owned topic | Quest 2 | Quest 3/3S | Unity versions | GLES | Vulkan |
|---|---|---|---|---|---|
| Triage and routing | yes | yes | 2021.3-6.6 | yes | yes |
| Headroom targets | yes | yes | any | yes | yes |
| Frame budgets and tiers | yes | yes (3S = Quest 3 eye buffer) | any | yes | yes |
| Draw-call and triangle budgets | yes (Q2-033 ranges) | yes (Q2-033 ranges) | any | yes | yes |
| Fill-rate and texture-memory budgets | partial (none published; measurement method) | partial (none published; measurement method) | any | yes | yes |
| Memory limits (PSS, lmkd) | yes (4.4 GiB) | yes (5.75 GiB) | any | yes | yes |
| Headset detection and adaptive quality | yes (9) | yes (11 / 12) | Meta XR SDK versions | yes | yes |
| VRC requirements | yes | yes | any | yes | yes |
| Stale frames and FrameSync | yes (FrameSync default on; opt-out undocumented) | yes (FrameSync default on; opt-out undocumented) | any | yes (no Late Latching) | yes |
| OpenXR Latency Optimization | yes | yes | OpenXR plugin 1.x (default differs from Meta's advice) | yes | yes |
| Refresh rate | yes (72/80/90/96/100/120; 60 media only) | yes (72/80/90/96/100/120; Quest 3 to 207 Hz, 240 Hz dev only) | any (runtime default 72 Hz) | yes | yes |
| Level system and clock tables | yes | yes (conflicts ARM-C3/C4) | any | yes | yes |
| Boost, dual-core mode, trading | Boost + dual-core | Boost + trading | any (OpenXR backend for dual-core/trading) | yes | yes |
| Thermal, PLS, Battery Saver | yes | yes | any | yes | yes |
| Performance-settings hints (XR_EXT_performance_settings) | partial (community evidence) | partial (community evidence) | OpenXR plugin 1.11.0+ | yes | yes |
| Resolution and dynamic resolution | yes | yes | 2021.3-6.6 | partial (KU-09) | yes |
| FFR and related pixel-cost features | yes | yes | 2021.3-6.6 (SRP Foveation per version) | partial (FFR caveats; no Symmetric Projection/MVRR) | yes |
| AppSW | yes | yes | Meta fork 2022.3.15f1+ / 6000.0.9f1+ / 6000.4.0f1+; Unity-native 6.1+ / URP 17.0.3+ | n/a | yes |
| Compositor layers | yes | partial (cost unpublished) | any | yes | yes |
| MR costs | partial (passthrough only) | yes | any | partial | yes |
| SDK/plugin choices, OBD | yes (66 MB/eye OBD) | yes (90 MB/eye OBD) | 2021.3-6.6 | partial (Oculus XR GLES path deprecated in 6.5) | yes |
| Profiling toolkit and scripts | yes | yes | any | yes | yes |
| Unity version matrix | yes | yes | 2021.3-6.6, 6.7 beta | yes | yes |
| Upgrade risks | yes | yes | 2022.3-6.6 | yes | yes |
| URP settings and audit | yes | yes | 2021.3-6.6 (audit guarded by #if) | yes (16-light limit) | yes |
| Render Graph on tilers | yes | yes | URP 12/14 Native RenderPass; 6.0+ RG; on-tile post 6.3+ | partial (Native RenderPass no effect) | yes |
| URP post-processing cost | yes | yes | 2021.3-6.6 (on-tile post 6.3+, Tile-Only Mode 6.5+) | partial (no on-tile post path) | yes |
| Draw calls and batching | yes | yes | 2021.3-6.6 (GRD 6.0+) | partial (BRG via UBO; GRD and GPU occlusion n/a) | yes (BRG via SSBO) |
| URP HLSL authoring | yes | yes | URP 12/14/17 | yes (mediump) | yes (RelaxedPrecision) |
| Shader hitches (PSO/GSC) | yes | yes | 2021.3-6.6 (GSC 6.0+; Vulkan GSC fix on LTS is conflict X-C1) | partial (falls back to SVC) | yes |
| Lighting | yes | yes | 2021.3-6.6 (APV 6.0+) | yes | yes |
| CPU/scripting | yes | yes | 2021.3-6.6 (Graphics Jobs Legacy 2022.3.35f1+) | partial (no Graphics Jobs modes) | yes |
| Memory and assets | yes | yes | 2021.3-6.6 | yes | yes |
| Unity profiling workflow | yes | yes | 2021.3-6.6 | yes | yes |
| In-app runtime stats hooks | partial (provider coverage unverified) | partial (provider coverage unverified) | 2021.3-6.6 (XRStats deprecated 6.3; unit change at OpenXR 1.18.0-pre.2) | yes | yes |
| GLES versions and Unity output | yes (ES 3.2, driver V@0690) | yes (ES 3.2, driver V@0837) | 2021.3-6.6 (ES 3.1 floor in 6.6) | yes | n/a |
| GLES-vs-Vulkan decision | yes | yes | 2022.3-6.3 evidence; 6.1+ unmeasured | yes | yes |
| GLES capture caveats | yes | yes | any | yes | n/a |
| GLES tile load/store | yes | yes | 2021.3-6.6 | yes | n/a |
| GLES multiview and extensions | yes | yes (thin gpuinfo evidence) | 2021.3-6.6 | yes | n/a |
| GLES driver overhead | yes | yes | any | yes | n/a |
| GLES shader binaries | yes | yes | any | yes | n/a |
| XR2 Gen 1 vs Gen 2 | yes | yes | n/a | n/a | n/a |
| CPU threads, NEON, Burst | yes | partial (app-core count unpublished) | 2021.3-6.6 (Burst 1.8+) | yes | yes |
| Adreno architecture | yes (Adreno 650) | yes (Adreno 740; GMEM approximate) | n/a | yes | yes |
| Shader cost model | partial (A6xx proxies) | partial (A7xx proxies) | n/a | yes | yes |
| Bandwidth and power | partial (no battery-drain data) | yes (measured power, OS v57) | n/a | yes | yes |
| Counters and SDP status | yes | yes | n/a | yes | yes |

## Trigger disambiguation

| Similar skills | Trigger words owned by the first | Trigger words owned by the second |
|---|---|---|
| quest-triage vs quest-profiling-toolkit | "why is it slow", "where do I start", "CPU or GPU bound", "low FPS", "stutter" (unknown cause) | "how do I capture", "OVR Metrics CSV", "ovrgpuprofiler command", "Perfetto trace", "setprop" |
| quest-triage vs unity-profiling-workflow | Quest-wide symptoms, before any tool is chosen | "Unity Profiler", "XR.WaitForGPU", "ProfilerMarker", "FrameTimingManager", "Frame Debugger" |
| quest-triage vs unity-cpu-scripting | "CPU-bound or GPU-bound?", "low FPS" with no cause identified | "GC spike", "physics spike", "UI rebuild", "main thread bound by scripts" |
| quest-frame-pacing vs quest-levels-thermal | "stale frames", "judder", "good FPS but stutters", "p99", "FrameSync", "Phase Sync", "Latency Optimization", "90 Hz / 120 Hz" | "after 10 minutes", "throttling", "thermal throttling warning", "CPU level", "GPU level", "Boost", "dual-core", "Processor Favor", "Battery Saver" |
| quest-frame-pacing vs unity-shader-hitches / unity-cpu-scripting | periodic judder with no single spike | one-off spikes: first render (shader-hitches), GC or physics (cpu-scripting) |
| quest-levels-thermal vs xr2-bandwidth-power | levels, clocks, PLS, throttling behaviour, session test | "battery drain", "watts", "heat source", "bandwidth-bound", "DRAM traffic", "bytes per pass" |
| quest-budgets-tiers vs unity-draw-calls-batching | "how many draw calls can I afford", "draw-call budget" | "reduce draw calls", "SRP Batcher", "batching method" |
| quest-compositor-layers vs quest-resolution-foveation | "blurry text", "blurry UI or menus", "overlay", "video layer" | "peripheral foveation artifacts", "FFR level", "render scale" |
| quest-resolution-foveation vs quest-appsw | "render scale", "FFR", "foveation", "dynamic resolution", "eye buffer size", "super resolution" | "SpaceWarp", "AppSW", "half frame rate", "motion vectors", "warping artifacts" |
| quest-resolution-foveation vs gles-extensions-multiview | foveation on any API, FFR levels, what disables FFR | "QCOM_texture_foveated", "GLES foveation extension", "GL VRS extension" |
| quest-budgets-tiers vs xr2-gen1-vs-gen2 | "how many draw calls", "triangle budget", "memory limit", "quality tiers", "detect headset", "porting Quest 3 content to Quest 2" | "A78C", "A77", "Adreno 650 vs 740", "GMEM size", "LPDDR5", "is Quest 3S slower silicon" |
| quest-mr-costs vs quest-levels-thermal | "passthrough cost", "Depth API", "MRUK", "hand tracking cost", "MR slower than VR" | general level caps and throttling outside MR |
| quest-sdk-choices vs unity-version-matrix | "OpenXR vs Oculus XR", "Meta XR SDK setting", "Optimize Buffer Discards", "manifest flag", "Project Setup Tool" | "which Unity version", "is X available in 2022.3", "Unity 6.x feature", "Meta minimum Unity version" |
| quest-sdk-choices vs unity-upgrade-risks | "choose a plugin", "OpenXR or Oculus XR for a new project" | "migrate a plugin", "Oculus XR to OpenXR migration after upgrade" |
| unity-version-matrix vs unity-upgrade-risks | "does version X have feature Y", "choose engine version" | "slower after upgrade", "regression", "patch release", "migration broke", "Compatibility Mode removed" |
| unity-urp-settings vs unity-render-graph-tiling | "URP asset", "HDR", "MSAA setting", "Forward+ vs Deferred", "which checkbox adds a pass", "audit settings" | "Render Graph", "pass merging", "LoadColor/StoreDepth stage", "renderer feature cost", "bloom cost", "post-processing cost", "memoryless", "framebuffer fetch in URP" |
| unity-render-graph-tiling vs xr2-bandwidth-power | "bloom is expensive", "post-processing cost", how to keep it on-tile | "how many DRAM bytes does this pass move", "bandwidth-bound" |
| unity-lighting vs unity-urp-settings | light setup: baked vs realtime, shadows, probes, lightmaps | rendering-path choice: Forward vs Forward+ vs Deferred |
| unity-render-graph-tiling vs gles-tile-load-store vs xr2-adreno-architecture | URP/Render Graph C# API and pass setup | glClear, glInvalidateFramebuffer, MSRTT, GLES load/store | why the hardware bins, GMEM size, bin math, LRZ rules, UBWC |
| unity-shader-authoring vs xr2-shader-cost-model | "write a URP shader", "should I use half", "clip() cost", "Shader Graph precision", "keyword vs branch in Unity" | "how expensive is this instruction", "GPR", "occupancy", "wave divergence", "fp16 rate", "why half did or did not help", "texture filtering cost" |
| unity-shader-authoring vs xr2-adreno-architecture | "alpha-tested material is expensive", "clip() vs LRZ in a shader" | "overdraw", "transparents or particles tank FPS", "bin count", "is this tile-friendly" |
| unity-shader-hitches vs gles-shader-binaries | "PSO", "GraphicsStateCollection", "shader warmup Vulkan", "variant stripping", "hitch on first use" (Vulkan) | "blob cache", "glProgramBinary", "stutter after OS update", "GLES shader compile hitch" |
| unity-draw-calls-batching vs gles-driver-overhead | "draw calls", "SRP Batcher", "instancing", "BRG", "GPU Resident Drawer", "SetPass" | "GL state changes", "glDraw overhead", "buffer orphaning", "fences", "KHR_no_error" |
| unity-cpu-scripting vs xr2-cpu-threads-neon | "GC", "allocations", "IL2CPP", "Graphics Jobs", "physics timestep", "UI rebuild", "Update loop" | "how many cores", "thread affinity", "job worker count", "NEON", "Burst target", "FloatMode", "cache line" |
| unity-memory-assets vs quest-budgets-tiers | "texture compression", "ASTC", "mip streaming", "loading hitch", "Addressables" | "memory limit", "lmkd kill", "PSS", "how much RAM can my app use", "texture-memory budget" |
| unity-memory-assets vs unity-shader-hitches | spike during a load or scene stream | spike when content first renders |
| gles-vs-vulkan vs gles-versions-unity-output | "should I use GLES or Vulkan", "Vulkan slower", "UUM-93226", "API A/B" | "ES 3.1 vs 3.2", "SHADER_API_GLES3", "#pragma target", "GLES limits" |
| quest-profiling-toolkit vs xr2-gpu-counters-sdp | running tools, commands, capture settings | "what does % Stalled on System Memory mean", "healthy range", "Snapdragon Profiler", "Adreno Offline Compiler" |

## Known unknowns carried from research

Each item is tagged with the skill that must surface it, with a measurement method or a `[verify on device]` tag.

- [quest-frame-pacing] The FrameSync opt-out mechanism: announced, undocumented, community-only value (QUEST-GF1-007, QUEST-GF2-001).
- [quest-frame-pacing] The meaning of CSV `phase_sync_mode` values; `4` probably marks FrameSync (QUEST-GF2-002).
- [quest-frame-pacing] Optimized Frame Pacing under the XR compositor (U5-C5). A/B stale frames per minute.
- [quest-frame-pacing] Latency Optimization: Meta's Prioritize Input Polling vs Unity's Prioritize Rendering default (U5-C2). A/B stale frames and pose latency.
- [quest-triage] How the "hitches under 3%" headroom rule defines a hitch (quest.md open unknowns).
- [quest-mr-costs] The hand-tracking cost on each device.
- [quest-mr-costs] The Depth API cost on each device.
- [quest-mr-costs] The passthrough cost on the current OS; the 17% / 14% figures are launch-era (A1-019).
- [quest-compositor-layers] Per-layer compositor cost on Quest 3/3S.
- [quest-sdk-choices] The replacement for the deprecated Shader Binary Cache (QUEST-GF1-004).
- [quest-levels-thermal] The thermal decay curve and minutes-to-first-throttle on each device. No [measured] source exists (A3-093).
- [quest-levels-thermal] Sustained headroom of Quest 3 vs Quest 3S.
- [quest-levels-thermal] Level-table conflicts:
  - GPU maximum: 599 vs 640 vs 690 MHz (ARM-C3)
  - Boost level 6 vs 8 (ARM-C4)
  - trading scope (ARM-C5)
  - Boost 20% vs 80% (ARM-C6)
- [quest-levels-thermal] Whether trading changes steady-state levels when the device is not throttling (ARM-GF1-003).
- [quest-levels-thermal] Whether the governor uses worst-core or average utilisation.
- [quest-levels-thermal] Whether Horizon OS honours XR_EXT_performance_settings level hints from Unity's OpenXR plugin (QUEST-GF1-010 is community evidence).
- [quest-triage] Net app headroom after compositor and OS overhead on each device. Meta publishes no percentage; Q2-030 gives the 1.25 ms `TW=` example and a measurement method.
- [xr2-bandwidth-power] Quest 3S vs Quest 3 memory bandwidth.
- [xr2-bandwidth-power] The configured DRAM data rate on all devices (ARM-C2).
- [xr2-bandwidth-power] Whether `Mem=` / MEM F scales with level or thermal state (A3-053, ARM-C24).
- [xr2-bandwidth-power] TDP or thermal envelope for any Quest.
- [xr2-bandwidth-power] DRAM energy per GB/s on XR2 Gen 2 / LPDDR5 (ARM-C22).
- [xr2-bandwidth-power] Fan behaviour.
- [xr2-bandwidth-power] Battery drain vs level.
- [quest-profiling-toolkit] Undefined OVR Metrics CSV columns (quest.md §12).
- [quest-profiling-toolkit] XR runtime and GPU counter track names in Perfetto (A3-045).
- [quest-profiling-toolkit] Whether the Perfetto GPU-metrics workflow still needs `ovrgpuprofiler -r` (ARM-C18).
- [quest-profiling-toolkit] Whether a Unity OpenXR build emits the VrApi logcat line with `SP=`/`TA=` (ARM-C19).
- [quest-resolution-foveation] FFR savings per device (Q3-022 is not device-specific).
- [quest-resolution-foveation] FFR on GLES + OpenXR (KU-10, Q3-039 conflict).
- [quest-resolution-foveation] Dynamic-resolution API on GLES, and GPU L5 on GLES (KU-09, G1-045).
- [quest-appsw] AppSW behaviour and savings at 90 and 120 Hz.
- [quest-appsw] Motion-vector pass cost: about 30% of the doubled frame vs "almost free" (QUEST-GF2-C3).
- [quest-appsw] Whether the XR2 Gen 2 accelerators reported by UploadVR affect AppSW cost (A1-024, [community]).
- [quest-budgets-tiers] Draw-call guidance: four Meta figures, none a limit (QUEST-GF2-C5, Q1-C3).
- [quest-budgets-tiers] Differing Meta triangle budgets (X-C4).
- [quest-budgets-tiers] Fill-rate and texture-memory budgets: none published (Q2-036, Q2-037). Measure per-surface time in RenderDoc Meta Fork and PSS at peak load.
- [unity-urp-settings] MSAA 2x vs 4x cost on Quest 2 and Quest 3/3S. Only original-Quest data exists (U2-093, A2-056).
- [unity-urp-settings] Which URP settings Unity's Quest capability flags actually change.
- [unity-urp-settings] VRS availability and cost in URP on Quest.
- [unity-lighting] ASTC HDR support on Quest.
- [unity-lighting] APV cost on Quest.
- [unity-cpu-scripting] IL2CPP code-generation setting impact on Quest.
- [unity-cpu-scripting] Incremental GC behaviour in XR.
- [unity-cpu-scripting] Physics fixedDeltaTime guidance (UNITY-GF1-C3).
- [unity-cpu-scripting] Graphics Jobs Split vs Legacy on Quest (A1-059).
- [unity-cpu-scripting] Graphics Jobs on 2021.3 (A1-062).
- [unity-cpu-scripting] Graphics Jobs vs LRZ interaction.
- [xr2-cpu-threads-neon] The app-core set on Quest 3/3S, and the exact mask on Quest 2 (A1-004).
- [xr2-cpu-threads-neon] Default JobWorkerMaximumCount per device and Unity version (A1-055).
- [xr2-cpu-threads-neon] Whether Unity's OpenXR plugin or Meta's plugins register threads through XR_KHR_android_thread_settings (A1-044).
- [xr2-cpu-threads-neon] Configured cache sizes on both SoCs.
- [xr2-cpu-threads-neon] The ARMV8A_HALFFP feature set (A1-079).
- [xr2-cpu-threads-neon] How the compositor is scheduled today (A1-048).
- [xr2-cpu-threads-neon] `SystemInfo.processorCount` vs usable cores (ARM-C7).
- [unity-profiling-workflow] Which XRDisplaySubsystem stats are filled on Quest (Q1-097).
- [unity-shader-hitches] Whether Vulkan GSC warmup removes hitches on 6.0/6.3 LTS (X-C1). Trace, warm, and compare `shader_hitches` over two passes of a scripted route.
- [unity-shader-hitches] Whether GSC traces stereo-instanced PSOs on Quest (U1-049).
- [unity-profiling-workflow] FrameTimingManager GPU times on 6.6 (X-C3).
- [unity-version-matrix] Unity 6.7 had not shipped at research time (6000.7.0b2). Re-verify before claiming anything.
- [unity-version-matrix] The Adreno model string on each device. Read `SystemInfo.graphicsDeviceName` on device.
- [gles-vs-vulkan] OS or driver fix for UUM-93226 (KU-02).
- [gles-vs-vulkan] No GLES-vs-Vulkan A/B on Unity 6.1+ (KU-16).
- [gles-vs-vulkan] p95/p99 frame time GLES vs Vulkan (KU-42).
- [gles-vs-vulkan] PSO vs program-link hitch size (KU-03).
- [gles-vs-vulkan] 2x MSAA cost per API (KU-24).
- [gles-vs-vulkan] OpenXR equivalent of Low Overhead Mode (KU-43).
- [gles-shader-binaries] Whether META-EGL keeps the blob cache across app updates (KU-04).
- [gles-tile-load-store] Which load/store GL calls Unity emits per URP setting (KU-17/18).
- [gles-tile-load-store] MSRTT behaviour details (KU-17/18).
- [gles-tile-load-store] Concurrent binning triggers on GLES (KU-25/26).
- [gles-extensions-multiview] Per-device extension availability beyond the 7 gpuinfo reports (GLES3-GF1-005).
- [xr2-adreno-architecture] Exact GMEM on Adreno 740v3 (ARM-C9).
- [xr2-adreno-architecture] LRZ block size.
- [xr2-adreno-architecture] Triangle-setup rate on A6x/A7x (A2-052).
- [xr2-adreno-architecture] Whether multiview shares the binning pass (ARM-C23).
- [xr2-adreno-architecture] Whether FDM (FFR) eye buffers keep UBWC (ARM-C13).
- [xr2-adreno-architecture] Whether compute-written targets lose UBWC on Quest's driver (ARM-C14).
- [xr2-adreno-architecture] Adreno 740 multi-sample input-attachment reads (A2-058).
- [xr2-adreno-architecture] Direct mode vs MSAA on current drivers (ARM-C12).
- [xr2-adreno-architecture] Whether Unity emits combined samplers or MUTABLE_FORMAT on Quest.
- [xr2-shader-cost-model] SP/ALU counts and FLOPS for 650/740 (A2-004).
- [xr2-shader-cost-model] Transcendental and integer rates on 650/740.
- [xr2-shader-cost-model] Texture cache sizes on 650/740.
- [xr2-shader-cost-model] A6x instruction cliff.
- [xr2-shader-cost-model] A6x/A7x ALU:TEX ratio.
- [xr2-shader-cost-model] Vulkan subgroup size on Quest.
- [xr2-gpu-counters-sdp] Snapdragon Profiler support on Quest 3/3S in 2026 (A3-066, KU-35).
- [xr2-gpu-counters-sdp] Whether realtime ovrgpuprofiler exposes byte counters (A3-028).
- [xr2-gpu-counters-sdp] Whether the Adreno Offline Compiler matches Quest's Meta-built driver (A2-089).
- [xr2-gpu-counters-sdp] UBWC compression ratio.
- [xr2-gen1-vs-gen2] Independent like-for-like Quest 2 vs Quest 3 GPU measurement (ARM-C20).
- [xr2-gen1-vs-gen2] How much app-core time the XR2 Gen 2 hardware offload frees (A1-024).
- [xr2-gen1-vs-gen2] Quest Pro and VR Glasses GMEM (out of scope beyond one line).
