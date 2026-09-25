# quest-perf-skills

A plugin marketplace of four skill bundles, 33 skills in all, for frame rate and frame-time consistency in **Unity URP apps on Meta Quest 2 and Quest 3/3S**. They are written for an AI agent working alongside a senior technical artist: diagnosis first, with numbers, exact settings, and paste-ready C#, HLSL and shell.

Every skill serves one or both goals below, and tags each fix with the goal it serves:

- **Throughput**: more FPS, through lower average CPU and GPU frame time.
- **Consistency**: smooth frame delivery. That means:
  - no stale or dropped frames
  - tight p95/p99 frame times
  - no hitches from GC, shader/PSO compilation, loading or physics
  - no thermal decay over a 20–30 minute session

Every claim carries a source URL, an evidence tag (`[doc]`, `[measured]` or `[community]`), and the devices, Unity/URP versions and graphics API it applies to. Anything that needs hardware confirmation is tagged `[verify on device]`. Where sources conflict, the skill shows both sides.

## Plugins and skills

Start with **`quest-perf:quest-triage`** when the cause is unknown. It routes to the skill that owns the bottleneck.

### `quest-perf`: Meta Horizon OS platform, runtime, Meta SDK features, tooling

| Skill | Covers |
|---|---|
| `quest-triage` | Entry point: CPU- vs GPU-bound vs pacing vs thermal, and routing to the owning skill |
| `quest-budgets-tiers` | Frame budgets per refresh rate, draw-call/triangle/memory budgets, PSS/lmkd limits, headset detection and quality tiers, VRC requirements |
| `quest-frame-pacing` | Stale frames, judder, p95/p99, FrameSync vs Phase Sync, Late Latching, OpenXR Latency Optimization, refresh-rate choice |
| `quest-levels-thermal` | CPU/GPU levels and clock tables, Boost, dual-core mode, trading, thermal throttling, 20–30 min session tests |
| `quest-resolution-foveation` | Eye-buffer size, render scale, dynamic resolution, FFR / dynamic foveation, subsampled layout, Symmetric Projection |
| `quest-appsw` | Application SpaceWarp setup, motion-vector cost, artifacts, version minimums |
| `quest-compositor-layers` | OVROverlay / OpenXR composition layers for UI, text, video; per-layer cost |
| `quest-mr-costs` | Passthrough, Depth API, Scene/MRUK, Passthrough Camera API, hand/body tracking costs |
| `quest-sdk-choices` | OpenXR vs deprecated Oculus XR plugin, Meta XR SDK settings, Optimize Buffer Discards, manifest flags |
| `quest-profiling-toolkit` | OVR Metrics Tool, logcat, MQDH/Perfetto, RenderDoc Meta Fork, ovrgpuprofiler. **Scripts:** OVR Metrics CSV analyzer and ADB helper |

### `unity-perf`: Unity 2021.3 LTS through Unity 6.6, URP-focused

| Skill | Covers |
|---|---|
| `unity-version-matrix` | Which Unity/URP version has which Quest performance feature (2021.3/URP 12 → 6.6/URP 17, 6.7 beta status) |
| `unity-upgrade-risks` | Known regressions and breaking changes when upgrading Unity/URP for Quest |
| `unity-urp-settings` | URP asset, renderer, Player and XR settings. **Script:** `QuestPerfAudit.cs` editor audit |
| `unity-render-graph-tiling` | Render Graph pass merging, memoryless, load/store, native render passes, on-tile post-processing |
| `unity-draw-calls-batching` | SRP Batcher, static batching, instancing, BRG, GPU Resident Drawer, GPU occlusion culling |
| `unity-shader-authoring` | Cheap URP HLSL / Shader Graph: half precision, clip vs LRZ, early-Z, keywords vs branches |
| `unity-shader-hitches` | First-use hitches, variant stripping, PSO tracing, GraphicsStateCollection warmup |
| `unity-lighting` | Baked/mixed/realtime, shadows, probes, APV, lightmaps |
| `unity-cpu-scripting` | GC, IL2CPP, jobs/Burst, Graphics Jobs, physics timestep, UI rebuilds |
| `unity-memory-assets` | ASTC, mip streaming, mesh formats, Async Upload Pipeline, loading hitches |
| `unity-profiling-workflow` | Unity Profiler on device, XR.WaitForGPU, ProfilerMarkers, FrameTimingManager, in-app XR stats |

### `gles3-perf`: OpenGL ES 3.x on Quest, and the GLES-vs-Vulkan decision

| Skill | Covers |
|---|---|
| `gles-vs-vulkan` | An honest GLES vs Vulkan decision: Vulkan-only features, UUM-93226 buffer-copy slowdown, A/B protocol |
| `gles-versions-unity-output` | ES 3.0/3.1/3.2 exposure and limits, what Unity emits for GLES, the ES 3.1 floor in Unity 6.6 |
| `gles-tile-load-store` | glClear/glInvalidateFramebuffer placement, MSRTT, avoiding GMEM loads and stores |
| `gles-extensions-multiview` | OVR_multiview2, framebuffer fetch, QCOM_texture_foveated, tiled-rendering extensions |
| `gles-driver-overhead` | State changes, program switches, buffer streaming, fences, Unity's GLES low-overhead options |
| `gles-shader-binaries` | GLES compile hitches, EGL blob cache and its limits, cache wipes after OS updates |

### `arm-mobile-hw-perf`: Snapdragon XR2 ARM CPU cores, Adreno GPU, memory, bandwidth, thermals

| Skill | Covers |
|---|---|
| `xr2-gen1-vs-gen2` | XR2 Gen 1 (Quest 2) vs XR2 Gen 2 (Quest 3/3S) silicon facts |
| `xr2-cpu-threads-neon` | Cores available to the app, thread placement, job worker counts, NEON/Burst |
| `xr2-adreno-architecture` | Binning, FlexRender, GMEM and bin math, LRZ, UBWC, MSAA resolve |
| `xr2-shader-cost-model` | fp16 rate, GPR pressure and occupancy, divergence, instruction and binding cliffs |
| `xr2-bandwidth-power` | DRAM traffic as the energy cost, per-pass traffic budgets, measuring bandwidth |
| `xr2-gpu-counters-sdp` | Adreno counter meanings and healthy ranges, Snapdragon Profiler status on Quest |

## Install (Claude Code)

Add the marketplace, from a local clone or from the Git host:

```bash
claude plugin marketplace add ./quest-perf-skills
```

```bash
claude plugin marketplace add sweettastebuds/quest-perf-skills
```

Then install the bundles you want:

```bash
claude plugin install quest-perf@quest-perf-skills
```

```bash
claude plugin install unity-perf@quest-perf-skills
```

```bash
claude plugin install gles3-perf@quest-perf-skills
```

```bash
claude plugin install arm-mobile-hw-perf@quest-perf-skills
```

In an interactive session, `/plugin` opens the same browser. The skills load on demand when a request matches their descriptions, for example "stale frames on Quest 3" or "FPS drops after 10 minutes". You can also name one directly, such as `quest-perf:quest-triage`.

The omp manifests (`.omp-plugin/`) are maintained separately and mirror `.claude-plugin/`.

## Scripts

| Script | Run | Tested |
|---|---|---|
| `plugins/quest-perf/skills/quest-profiling-toolkit/scripts/ovr_metrics_csv.py` | `python ovr_metrics_csv.py capture.csv [--json] [--window-min 5] [--hz 90]`: p50/p95/p99, stale frames per minute and max per 60 s, CPU/GPU utilization and levels per minute, drift between the first and last 5 minutes, hitch rates, segments from `AppendCsvDebugString` | Yes: 17 unittests against a synthetic CSV using the documented Aug 2026 header (`make_synthetic_ovr_csv.py`, `test_ovr_metrics_csv.py`). Stdlib only, Python 3.10+ |
| `plugins/quest-perf/skills/quest-profiling-toolkit/scripts/quest_adb.py` | `python quest_adb.py [--dry-run] <subcommand>`: levels, refresh rate, foveation, GPU isolation, thermal simulation, OVR Metrics CSV capture/pull, ovrgpuprofiler, Perfetto, reset | `--dry-run` only (no headset available). Only Meta-documented properties, each cited to a finding ID |
| `plugins/unity-perf/skills/unity-urp-settings/scripts/QuestPerfAudit.cs` | Editor script, menu `Tools/Quest Perf/Audit Project` | **Untested**: written without a Unity editor, with `#if UNITY_2022_3_OR_NEWER` / `UNITY_6000_0_OR_NEWER` guards |

## Repository layout

```
.claude-plugin/marketplace.json     Claude Code marketplace
plugins/<bundle>/.claude-plugin/    plugin manifests
plugins/<bundle>/skills/<name>/     SKILL.md, references/, scripts/
research/                           source dossiers (quest, unity, gles3, arm-mobile-hw)
OUTLINE.md                          skill plan, ownership index, trigger disambiguation, decisions
tools/lint_skills.py                frontmatter, sections, links, cross-references, trigger overlap
tools/check_links.py                URL and relative-link checker
```

Validate after editing:

```bash
python tools/lint_skills.py
```

```bash
python tools/check_links.py
```

```bash
claude plugin validate --strict .
```

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

## Known unknowns

No source we found answers these. Each skill names the ones it owns and gives a measurement method or a `[verify on device]` tag. IDs refer to findings in `research/`.

- **quest-frame-pacing**: The FrameSync opt-out mechanism: announced, undocumented, community-only value (QUEST-GF1-007, QUEST-GF2-001).
- **quest-frame-pacing**: The meaning of CSV `phase_sync_mode` values; `4` probably marks FrameSync (QUEST-GF2-002).
- **quest-frame-pacing**: Optimized Frame Pacing under the XR compositor (U5-C5). A/B stale frames per minute.
- **quest-frame-pacing**: Latency Optimization: Meta's Prioritize Input Polling vs Unity's Prioritize Rendering default (U5-C2). A/B stale frames and pose latency.
- **quest-triage**: How the "hitches under 3%" headroom rule defines a hitch (quest.md open unknowns).
- **quest-mr-costs**: The hand-tracking cost on each device.
- **quest-mr-costs**: The Depth API cost on each device.
- **quest-mr-costs**: The passthrough cost on the current OS; the 17% / 14% figures are launch-era (A1-019).
- **quest-compositor-layers**: Per-layer compositor cost on Quest 3/3S.
- **quest-sdk-choices**: The replacement for the deprecated Shader Binary Cache (QUEST-GF1-004).
- **quest-levels-thermal**: The thermal decay curve and minutes-to-first-throttle on each device. No [measured] source exists (A3-093).
- **quest-levels-thermal**: Sustained headroom of Quest 3 vs Quest 3S.
- **quest-levels-thermal**: Level-table conflicts:
  - GPU maximum: 599 vs 640 vs 690 MHz (ARM-C3)
  - Boost level 6 vs 8 (ARM-C4)
  - trading scope (ARM-C5)
  - Boost 20% vs 80% (ARM-C6)
- **quest-levels-thermal**: Whether trading changes steady-state levels when the device is not throttling (ARM-GF1-003).
- **quest-levels-thermal**: Whether the governor uses worst-core or average utilisation.
- **quest-levels-thermal**: Whether Horizon OS honours XR_EXT_performance_settings level hints from Unity's OpenXR plugin (QUEST-GF1-010 is community evidence).
- **quest-triage**: Net app headroom after compositor and OS overhead on each device. Meta publishes no percentage; Q2-030 gives the 1.25 ms `TW=` example and a measurement method.
- **xr2-bandwidth-power**: Quest 3S vs Quest 3 memory bandwidth.
- **xr2-bandwidth-power**: The configured DRAM data rate on all devices (ARM-C2).
- **xr2-bandwidth-power**: Whether `Mem=` / MEM F scales with level or thermal state (A3-053, ARM-C24).
- **xr2-bandwidth-power**: TDP or thermal envelope for any Quest.
- **xr2-bandwidth-power**: DRAM energy per GB/s on XR2 Gen 2 / LPDDR5 (ARM-C22).
- **xr2-bandwidth-power**: Fan behaviour.
- **xr2-bandwidth-power**: Battery drain vs level.
- **quest-profiling-toolkit**: Undefined OVR Metrics CSV columns (quest.md §12).
- **quest-profiling-toolkit**: XR runtime and GPU counter track names in Perfetto (A3-045).
- **quest-profiling-toolkit**: Whether the Perfetto GPU-metrics workflow still needs `ovrgpuprofiler -r` (ARM-C18).
- **quest-profiling-toolkit**: Whether a Unity OpenXR build emits the VrApi logcat line with `SP=`/`TA=` (ARM-C19).
- **quest-resolution-foveation**: FFR savings per device (Q3-022 is not device-specific).
- **quest-resolution-foveation**: FFR on GLES + OpenXR (KU-10, Q3-039 conflict).
- **quest-resolution-foveation**: Dynamic-resolution API on GLES, and GPU L5 on GLES (KU-09, G1-045).
- **quest-appsw**: AppSW behaviour and savings at 90 and 120 Hz.
- **quest-appsw**: Motion-vector pass cost: about 30% of the doubled frame vs "almost free" (QUEST-GF2-C3).
- **quest-appsw**: Whether the XR2 Gen 2 accelerators reported by UploadVR affect AppSW cost (A1-024, [community]).
- **quest-budgets-tiers**: Draw-call guidance: four Meta figures, none a limit (QUEST-GF2-C5, Q1-C3).
- **quest-budgets-tiers**: Differing Meta triangle budgets (X-C4).
- **quest-budgets-tiers**: Fill-rate and texture-memory budgets: none published (Q2-036, Q2-037). Measure per-surface time in RenderDoc Meta Fork and PSS at peak load.
- **unity-urp-settings**: MSAA 2x vs 4x cost on Quest 2 and Quest 3/3S. Only original-Quest data exists (U2-093, A2-056).
- **unity-urp-settings**: Which URP settings Unity's Quest capability flags actually change.
- **unity-urp-settings**: VRS availability and cost in URP on Quest.
- **unity-lighting**: ASTC HDR support on Quest.
- **unity-lighting**: APV cost on Quest.
- **unity-cpu-scripting**: IL2CPP code-generation setting impact on Quest.
- **unity-cpu-scripting**: Incremental GC behaviour in XR.
- **unity-cpu-scripting**: Physics fixedDeltaTime guidance (UNITY-GF1-C3).
- **unity-cpu-scripting**: Graphics Jobs Split vs Legacy on Quest (A1-059).
- **unity-cpu-scripting**: Graphics Jobs on 2021.3 (A1-062).
- **unity-cpu-scripting**: Graphics Jobs vs LRZ interaction.
- **xr2-cpu-threads-neon**: The app-core set on Quest 3/3S, and the exact mask on Quest 2 (A1-004).
- **xr2-cpu-threads-neon**: Default JobWorkerMaximumCount per device and Unity version (A1-055).
- **xr2-cpu-threads-neon**: Whether Unity's OpenXR plugin or Meta's plugins register threads through XR_KHR_android_thread_settings (A1-044).
- **xr2-cpu-threads-neon**: Configured cache sizes on both SoCs.
- **xr2-cpu-threads-neon**: The ARMV8A_HALFFP feature set (A1-079).
- **xr2-cpu-threads-neon**: How the compositor is scheduled today (A1-048).
- **xr2-cpu-threads-neon**: `SystemInfo.processorCount` vs usable cores (ARM-C7).
- **unity-profiling-workflow**: Which XRDisplaySubsystem stats are filled on Quest (Q1-097).
- **unity-shader-hitches**: Whether Vulkan GSC warmup removes hitches on 6.0/6.3 LTS (X-C1). Trace, warm, and compare `shader_hitches` over two passes of a scripted route.
- **unity-shader-hitches**: Whether GSC traces stereo-instanced PSOs on Quest (U1-049).
- **unity-profiling-workflow**: FrameTimingManager GPU times on 6.6 (X-C3).
- **unity-version-matrix**: Unity 6.7 had not shipped at research time (6000.7.0b2). Re-verify before claiming anything.
- **unity-version-matrix**: The Adreno model string on each device. Read `SystemInfo.graphicsDeviceName` on device.
- **gles-vs-vulkan**: OS or driver fix for UUM-93226 (KU-02).
- **gles-vs-vulkan**: No GLES-vs-Vulkan A/B on Unity 6.1+ (KU-16).
- **gles-vs-vulkan**: p95/p99 frame time GLES vs Vulkan (KU-42).
- **gles-vs-vulkan**: PSO vs program-link hitch size (KU-03).
- **gles-vs-vulkan**: 2x MSAA cost per API (KU-24).
- **gles-vs-vulkan**: OpenXR equivalent of Low Overhead Mode (KU-43).
- **gles-shader-binaries**: Whether META-EGL keeps the blob cache across app updates (KU-04).
- **gles-tile-load-store**: Which load/store GL calls Unity emits per URP setting (KU-17/18).
- **gles-tile-load-store**: MSRTT behaviour details (KU-17/18).
- **gles-tile-load-store**: Concurrent binning triggers on GLES (KU-25/26).
- **gles-extensions-multiview**: Per-device extension availability beyond the 7 gpuinfo reports (GLES3-GF1-005).
- **xr2-adreno-architecture**: Exact GMEM on Adreno 740v3 (ARM-C9).
- **xr2-adreno-architecture**: LRZ block size.
- **xr2-adreno-architecture**: Triangle-setup rate on A6x/A7x (A2-052).
- **xr2-adreno-architecture**: Whether multiview shares the binning pass (ARM-C23).
- **xr2-adreno-architecture**: Whether FDM (FFR) eye buffers keep UBWC (ARM-C13).
- **xr2-adreno-architecture**: Whether compute-written targets lose UBWC on Quest's driver (ARM-C14).
- **xr2-adreno-architecture**: Adreno 740 multi-sample input-attachment reads (A2-058).
- **xr2-adreno-architecture**: Direct mode vs MSAA on current drivers (ARM-C12).
- **xr2-adreno-architecture**: Whether Unity emits combined samplers or MUTABLE_FORMAT on Quest.
- **xr2-shader-cost-model**: SP/ALU counts and FLOPS for 650/740 (A2-004).
- **xr2-shader-cost-model**: Transcendental and integer rates on 650/740.
- **xr2-shader-cost-model**: Texture cache sizes on 650/740.
- **xr2-shader-cost-model**: A6x instruction cliff.
- **xr2-shader-cost-model**: A6x/A7x ALU:TEX ratio.
- **xr2-shader-cost-model**: Vulkan subgroup size on Quest.
- **xr2-gpu-counters-sdp**: Snapdragon Profiler support on Quest 3/3S in 2026 (A3-066, KU-35).
- **xr2-gpu-counters-sdp**: Whether realtime ovrgpuprofiler exposes byte counters (A3-028).
- **xr2-gpu-counters-sdp**: Whether the Adreno Offline Compiler matches Quest's Meta-built driver (A2-089).
- **xr2-gpu-counters-sdp**: UBWC compression ratio.
- **xr2-gen1-vs-gen2**: Independent like-for-like Quest 2 vs Quest 3 GPU measurement (ARM-C20).
- **xr2-gen1-vs-gen2**: How much app-core time the XR2 Gen 2 hardware offload frees (A1-024).
- **xr2-gen1-vs-gen2**: Quest Pro and VR Glasses GMEM (out of scope beyond one line).

## Research and method

The `research/` dossiers hold every finding behind the skills. Each has a source URL, access date, applicability and evidence tag, and the dossiers record conflicts explicitly. Each skill was written from its dossier, then reviewed by an independent agent that checked its claims against the dossier and refetched sources, and then fixed. `OUTLINE.md` lists every authoring decision made without the owner's input.
