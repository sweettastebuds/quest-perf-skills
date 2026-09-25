# Routing table: symptom -> confirming signal -> owning skill

Applies to Quest 2 and Quest 3/3S, Unity 2021.3-6.6, GLES and Vulkan unless a row says otherwise. Finding IDs refer to `research/quest.md`, `research/unity.md`, `research/gles3.md` and `research/arm-mobile-hw.md` (accessed 2026-09-24). Where a row's signal has no documented threshold, the row says what to compare instead of giving a number.

Read the first table to turn a raw signal into a verdict. Read the second to hand the verdict to exactly one owner.

## 1. Signal -> verdict

Synthesis index from quest.md section 1; each row points at sourced findings.

| Signal | Verdict | Findings |
|---|---|---|
| `App=` / `app_gpu_time_microseconds` above the frame budget | GPU-bound | Q1-089 / Q2-031 |
| App GPU time within budget, but FPS below target or `Stale` > 0 | CPU-bound (main or render thread) | Q1-089 / Q2-031 |
| `CPU&GPU - App` close to the budget | Unity render thread | Q1-032 |
| `CPU L` high, `GPU L` low (e.g. 4/2) while missing frames | CPU-bound | Q1-025 / Q2-032 |
| `GPU%` > 0.9 | GPU saturated; scheduling risk | Q1-025 / Q2-032, Q2-030 |
| `GPU%` at half rate | under-reports load; use App ms | Q2-031 |
| `Stale` between 0 and refresh; `Stale2/5/10` non-zero; `stale_frames_consecutive` > 0 | pacing hitch (visible judder) | Q1-024 / Q2-066, Q1-029, Q1-014 |
| `Stale` = refresh with steady FPS | extra-latency mode, not a failure | Q1-024 / Q2-066 |
| `Early` about FPS | extra-latency mode, or levels higher than needed | Q1-026 / Q2-067 |
| `Tear` > 0, `TW` rising, high `LCnt` | compositor-bound (layers) | Q1-026 / Q2-067 / Q2-070 |
| Perfetto `FenceChecker::Wait`, or waits on the `GPU completion` thread | GPU-bound | Q1-052 |
| `UnityMain` / `UnityGfx` slices over budget with no fence waits | CPU-bound | Q1-052 |
| Unity Profiler `XR.WaitForGPU` longer than one frame | GPU-bound | U5-081 |
| `PhaseSync` idle near 0 ms at the start of `PlayerLoop` | no headroom (pre-FrameSync semantics) [verify on device] | Q1-051, QX-C4 |
| Clock drop, or `PLS` / `power_level_state` 1-2, aligned with a stale burst | thermal | Q1-035, Q1-036, Q1-016 / Q2-061 |
| Refresh drops to 72 Hz mid-session, or app forced to half rate | thermal refresh step | Q2-014 |
| `LP=1` in logcat | Battery Saver on: 72 Hz, FFR 3, no GPU L5 | Q2-062 |
| `shader_hitches` increments; hitches on first run only | shader/PSO compilation | Q1-011, Q1-014 |
| Render scale at minimum changes nothing | vertex/geometry/submission-bound | Q1-091 |
| FFR sweep 0->4 gives a large drop in App GPU time | fragment-bound | Q1-081 / Q3-028 |
| `Fov=0` while the app believes it set a level | foveation not taking effect | Q1-081 |
| `SF=` differs from the scale you set (on Unity ≥ 6000.3 with an IUpscaler it stays 1.00, Q3-007) | render scale did not reach the compositor | Q1-033, Q2-022 |
| GPU-bound only in MR; levels capped at CPU L3 / GPU L2 | lower clock ceiling, not slower shaders | Q4-010, Q2-038 / Q4-001 |
| Memory trend rising, then `lowmemorykiller` / Low Memory Kill | PSS over limit under pressure | Q2-041, Q2-042, Q1-095 |
| Levels differ between captures with casting/recording on | OS override; capture not comparable | A1-036 |

## 2. Verdict or symptom -> owning skill (all 33)

### quest-perf

| Symptom or question | Confirming signal | Owner |
|---|---|---|
| Cause unknown: low FPS, stutter, "CPU or GPU bound?" | this skill's steps 0-3 | `quest-perf:quest-triage` |
| "How many draw calls / triangles can I afford", porting Quest 3 content to Quest 2, app killed for memory, store VRC rules | PSS vs 4.4 / 5.75 GiB; `lowmemorykiller`; Performance Analytics | `quest-perf:quest-budgets-tiers` |
| Good average frame time but judder; stale frames; bad p99; 72/90/120 Hz choice | irregular `Stale`, `Stale2/5/10`, `Lat=`, `phase_sync_mode` | `quest-perf:quest-frame-pacing` |
| FPS drops after 10+ minutes; levels keep changing; throttling warning | `power_level_state`, `*_frequency_MHz` falling, XrPerformanceManager clock lines | `quest-perf:quest-levels-thermal` |
| GPU fill-bound; FFR level choice; FFR seems to do nothing | render-scale test improves; FFR sweep; `Fov=`, `SF=` | `quest-perf:quest-resolution-foveation` |
| GPU-bound and resolution/foveation cuts are not enough | App GPU time still over budget at acceptable scale; Vulkan build | `quest-perf:quest-appsw` |
| Blurry UI text, many overlays, video cost, tears | `Tear` > 0, `TW`, `LCnt` | `quest-perf:quest-compositor-layers` |
| MR / passthrough slower than VR; levels stop rising with passthrough | `CPU4/GPU=` capped at 3/2 on Quest 3/3S | `quest-perf:quest-mr-costs` |
| OpenXR vs Oculus XR, Meta SDK toggles, Optimize Buffer Discards, manifest flags | settings inventory, not a metric | `quest-perf:quest-sdk-choices` |
| "How do I capture / pin levels / parse the CSV / run ovrgpuprofiler"; Runtime Optimizer | n/a (tooling) | `quest-perf:quest-profiling-toolkit` |

### unity-perf

| Symptom or question | Confirming signal | Owner |
|---|---|---|
| "Does Unity X have feature Y", choosing an engine version | version lookup | `unity-perf:unity-version-matrix` |
| FPS dropped after a Unity/URP upgrade or patch | same scene A/B, old vs new version, same device and levels | `unity-perf:unity-upgrade-risks` |
| Reviewing URP asset / Player / XR settings; MSAA, HDR, which checkbox adds a pass | settings audit | `unity-perf:unity-urp-settings` |
| LoadColor / StoreDepthStencil in ovrgpuprofiler; a renderer feature or bloom costs ms | per-surface stages and pass count | `unity-perf:unity-render-graph-tiling` |
| Render thread bound; render-scale test changes nothing; SetPass/draw calls high | `CPU&GPU - App` near budget; long `UnityGfx` | `unity-perf:unity-draw-calls-batching` |
| One shader or material is GPU-expensive | per-draw cost comparison, FFR sweep | `unity-perf:unity-shader-authoring` |
| Spike when content first renders (Vulkan or API-agnostic) | `shader_hitches` increments; gone on warm run | `unity-perf:unity-shader-hitches` |
| Lights, shadows or GI cost GPU time | A/B with shadows / additional lights off | `unity-perf:unity-lighting` |
| Main thread bound by scripts, GC, physics, UI or animation | long `UnityMain` / `PlayerLoop`; camera-off test shows little change | `unity-perf:unity-cpu-scripting` |
| Loading or scene-stream hitches; texture/mesh memory | spike aligned with load markers; `app_gpu_physical_MB` trend | `unity-perf:unity-memory-assets` |
| Reading a Unity Profiler capture from Quest; instrumenting code | `XR.WaitForGPU`, `Gfx.WaitForPresent`, ProfilerMarkers | `unity-perf:unity-profiling-workflow` |

### gles3-perf

| Symptom or question | Confirming signal | Owner |
|---|---|---|
| Project ships GLES; shader/feature differs from Vulkan; ES 3.1 vs 3.2 | Player settings API list, emitted `#version` | `gles3-perf:gles-versions-unity-output` |
| "Should I switch API", Vulkan slower than GLES, UUM-93226 | single-variable API A/B (G1-079) | `gles3-perf:gles-vs-vulkan` |
| GLES build shows LoadColor / StoreDepthStencil; MSAA expensive on GLES | per-surface stages on a GLES build | `gles3-perf:gles-tile-load-store` |
| GLES multiview misrenders or crashes; is extension X available | extension list per headset | `gles3-perf:gles-extensions-multiview` |
| GLES build render-thread-bound; GL state calls dominate | long `UnityGfx` on GLES; trace dominated by GL calls | `gles3-perf:gles-driver-overhead` |
| GLES first-use compile hitch; stutter after a Quest OS update | first-run-only spikes on a GLES build | `gles3-perf:gles-shader-binaries` |

### arm-mobile-hw-perf

| Symptom or question | Confirming signal | Owner |
|---|---|---|
| Spec-sheet claim (cores, GPU clock, LPDDR5); Quest 2 vs 3 silicon | n/a (spec facts) | `arm-mobile-hw-perf:xr2-gen1-vs-gen2` |
| Burst code slow on Quest; threads on the wrong cores; how many cores | `TA=` affinities in logcat; Perfetto `sched_slice` | `arm-mobile-hw-perf:xr2-cpu-threads-neon` |
| Heavy overdraw from transparents/particles; bin counts; is it tile-friendly | `avg_fill_percentage` (needs ovrgpuprofiler support in OVR Metrics, Q1-007) | `arm-mobile-hw-perf:xr2-adreno-architecture` |
| What an instruction or sampler costs; GPRs; why half did not help | shader stats (GPRs, instruction count) | `arm-mobile-hw-perf:xr2-shader-cost-model` |
| Battery drain, watts, bandwidth-bound GPU, DRAM bytes of a pass | `power_*` CSV columns; RenderDoc byte counters | `arm-mobile-hw-perf:xr2-bandwidth-power` |
| A counter value needs a verdict; someone asks for Snapdragon Profiler | ovrgpuprofiler / OVR Metrics `percent_*` counters | `arm-mobile-hw-perf:xr2-gpu-counters-sdp` |

## 3. Tie-breaks between owners

- One-off spike on first render -> `unity-perf:unity-shader-hitches`; one-off spike during a load -> `unity-perf:unity-memory-assets`; periodic judder with no single spike -> `quest-perf:quest-frame-pacing`; decay over the session -> `quest-perf:quest-levels-thermal`.
- "How do I reduce draw calls" -> `unity-perf:unity-draw-calls-batching`; "how many can I afford" -> `quest-perf:quest-budgets-tiers`.
- Running a tool -> `quest-perf:quest-profiling-toolkit`; interpreting an Adreno counter -> `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
- GLES build: the GLES-specific owner wins for load/store, driver overhead, shader binaries and extensions; the Unity owner wins for Vulkan and API-agnostic cases.
