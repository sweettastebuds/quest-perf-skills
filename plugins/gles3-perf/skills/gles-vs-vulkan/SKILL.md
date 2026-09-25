---
name: gles-vs-vulkan
description: "Honest GLES vs Vulkan decision for Unity on Quest 2/3/3S: Vulkan-only Meta features (AppSW, Late Latching, Symmetric Projection, OBD, memoryless), the Vulkan slowdown report UUM-93226, measured comparisons, MSAA cost difference per API, and a single-variable A/B protocol, plus capturing a GLES build (RenderDoc limits, timer queries). Use for \"should I switch to Vulkan\", when Vulkan seems slower than OpenGL ES, or when validating an API switch."
---

# GLES vs Vulkan on Quest (Unity 2022.3 to 6.6)

Goal: **Throughput** (lower App GPU / render-thread time on the API you ship)
and **Consistency** (no MSAA-path stutter, no first-use hitch regressions, and a
supported API for the life of the title). Scope: Quest 2 (XR2, Adreno 650) and
Quest 3/3S (XR2 Gen 2, Adreno 740), Unity 2022.3 (URP 14) to 6000.6 (URP 17),
Oculus XR 4.x or OpenXR 1.x.

There is no measured winner. Meta and Unity docs say Vulkan; every published
community measurement from 2021 to 2025 in MSAA scenes favours GLES; nothing
has been measured on Unity 6.1+ with the recommended Vulkan settings (KU-16).
This skill is therefore a decision rule plus a measurement protocol, not a
verdict (G1-072 to G1-079).

Reference files:
- [references/evidence-table.md](references/evidence-table.md): read before citing any comparison; every GLES-vs-Vulkan data point with setup, device, Unity version, numbers, grade, and the conflicts.
- [references/ab-protocol.md](references/ab-protocol.md): read when running or reviewing an API A/B; step-by-step protocol, adb commands, a C# editor build helper and a runtime API stamp.
- [references/gles-capture.md](references/gles-capture.md): read before profiling or capturing a GLES build; RenderDoc Meta Fork 68.18 limits, timer queries, ovrgpuprofiler on GL, Perfetto, Snapdragon Profiler, AGI, GPU Systrace.

No scripts ship with this skill. The A/B uses two `quest-perf:quest-profiling-toolkit` scripts, run from the repo root: `quest_adb.py` (level pinning, ovrgpuprofiler trace, OVR Metrics CSV, props snapshot; commands in Diagnose first steps 2, 3 and 6) and `ovr_metrics_csv.py` (CSV analysis, step 6). Add `--dry-run` after `quest_adb.py` to print the adb commands without running them.

## When to use / when not

Use when:
- "Should I switch to Vulkan / back to GLES?", "Vulkan is slower than OpenGL ES", "UUM-93226", "Vulkan stutters with MSAA".
- Validating an API switch before shipping, or re-checking after a Horizon OS update.
- Deciding whether a Vulkan-only feature (AppSW, Late Latching, Symmetric Projection, MRR, OBD, memoryless, dynamic foveation, Graphics Jobs modes) is worth the migration.
- Capturing or timing a GLES build (RenderDoc Meta Fork on GL, timer queries, Snapdragon Profiler, AGI).

When not:
- Bottleneck unknown: `quest-perf:quest-triage` first.
- ES 3.0 vs 3.1 vs 3.2, `SHADER_API_GLES3*`, `#pragma target`, GLES limits: `gles3-perf:gles-versions-unity-output`.
- glClear / glInvalidateFramebuffer / MSRTT tuning inside a GLES build: `gles3-perf:gles-tile-load-store`.
- Low Overhead Mode, GL state and driver CPU cost: `gles3-perf:gles-driver-overhead`.
- AppSW setup and tuning: `quest-perf:quest-appsw`. OBD, Symmetric Projection, plugin choice and setting paths: `quest-perf:quest-sdk-choices`.
- Late Latching and stale frames: `quest-perf:quest-frame-pacing`. FFR/dynamic foveation: `quest-perf:quest-resolution-foveation`.
- Choosing 2x vs 4x MSAA as a quality setting: `unity-perf:unity-urp-settings`. Render Graph store minimisation: `unity-perf:unity-render-graph-tiling`.
- Vulkan PSO / GSC warmup: `unity-perf:unity-shader-hitches`. GLES program-binary cache: `gles3-perf:gles-shader-binaries`.
- Regressions from a Unity upgrade: `unity-perf:unity-upgrade-risks`.
- Running ovrgpuprofiler / Perfetto / OVR Metrics in general: `quest-perf:quest-profiling-toolkit`. What Adreno counters mean: `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.

## Diagnose first

The question "is Vulkan slower here?" is only answered by a single-variable
A/B on the current OS build. Before that, confirm what is actually running and
where the gap sits.

1. **Confirm the API and driver of the running build.** Auto Graphics API tries Vulkan first, then GLES 3.2/3.1/3.0 (G1-016), so a build can run on a different API from the one you think you are measuring. At runtime log `SystemInfo.graphicsDeviceType` / `graphicsDeviceVersion` (script in [references/ab-protocol.md](references/ab-protocol.md)). Record the OS build and GLES driver (G2-082, G1-078):
   ```sh
   adb shell getprop ro.build.id
   adb shell dumpsys SurfaceFlinger | grep GLES   # e.g. "GLES: Qualcomm, Adreno (TM) 740, OpenGL ES 3.2 V@0837.0.7"
   ```
2. **Pin levels for the timing A/B** (reboot to reset; record props) (Q1-077, Q1-079):
   ```sh
   adb shell setprop debug.oculus.cpuLevel 3
   adb shell setprop debug.oculus.gpuLevel 3
   adb shell getprop | grep debug.oculus
   ```
   Same via the toolkit: `py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/quest_adb.py pin-levels --cpu 3 --gpu 3`, then `py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/quest_adb.py props-snapshot`.
   Level 3 is what the UUM-149765 recipe used (G2-010); use it for deltas, not absolute budgets.
3. **Read the eye-buffer surface stages** with ovrgpuprofiler on both APIs (G2-010, G3-080):
   ```sh
   adb shell ovrgpuprofiler -e      # detailed mode; run BEFORE launching the app, else restart it
   adb shell ovrgpuprofiler -t2     # 2 s trace; -t2 -v for per-bin stages
   adb shell ovrgpuprofiler -d      # turn detailed mode off afterwards
   ```
   Same via the toolkit: `py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/quest_adb.py gpu-trace --enable` (then restart the app), `py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/quest_adb.py gpu-trace --seconds 2 --verbose`, `py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/quest_adb.py gpu-trace --disable`. UUM-149765 wrote `-t 2` (G2-010); Meta documents `-t<seconds>` (G3-080) [verify on device].
   Compare total, Binning, Render, StoreColor and StoreDepthStencil, plus bin count and Mode, for the eye-buffer surface. The UUM-93226 fingerprint is Vulkan paying many Store* stages per bin with MSAA on while GLES pays one resolved StoreColor (G1-054, G2-041).
4. **Confirm the store pattern in RenderDoc Meta Fork** (development build): Window > Tile Timeline, count StoreColor/StoreDS per bin on each API (G3-078, G1-080). GL capture caveats are in [references/gles-capture.md](references/gles-capture.md).
5. **Split MSAA from API**: rerun both APIs with MSAA off. If the gap collapses to about 1 ms, the problem is the MSAA store/resolve path, not the API as a whole (G1-054, G2-039).
6. **Capture OVR Metrics CSV** on both builds over the same route; compare p50/p95/p99 of `app_gpu_time_microseconds`, stale frames per minute and `shader_hitches` with `quest-perf:quest-profiling-toolkit`'s analyzer (Q1-010):
   ```sh
   py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/quest_adb.py csv on       # start OVR Metrics CSV logging
   py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/quest_adb.py csv off      # stop after the route
   py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/quest_adb.py pull-csv     # pulls CapturedMetrics/ plus a debug.oculus props snapshot
   py -3.12 plugins/quest-perf/skills/quest-profiling-toolkit/scripts/ovr_metrics_csv.py <capture.csv>
   ```
   CSV rows are 1 Hz averages; they cannot show a single-frame hitch. Use Perfetto for frame-level pacing.

Full step list, run counts, cold/warm launches and the C# helpers: [references/ab-protocol.md](references/ab-protocol.md).

## Key numbers

Frame budgets (1000 / Hz, arithmetic): 72 Hz = 13.9 ms, 90 Hz = 11.1 ms, 120 Hz = 8.3 ms.
Every row states its evidence grade; vendor claims are not measurements.

| Number | Meaning | Applies to | Source / tag |
|---|---|---|---|
| +3.3 ms GLES vs +5.0 ms Vulkan | Cost of 4x MSAA on the eye buffer (quote deltas only; the tracker's absolute numbers are internally inconsistent, G2-C9) | `Quest 3/3S` `Unity 6000.0-6000.7a` `URP 17` OBD on | UUM-149765, G2-039 [measured] |
| within about 1 ms | GLES vs Vulkan with MSAA off (table: Vulkan 9.1 vs GLES 9.7 ms) | `Quest 3/3S` `Unity 6000.0-6000.7a` | G2-039 [measured] |
| about +7 ms, APIs within about 1 ms | 4x MSAA on Quest 2 (about 14 to 21 ms on Vulkan; GLES within about 1 ms) | `Quest 2` `Unity 6000.x` | G2-040, gles3.md §3.4 [measured] |
| 0.04 to 0.15 ms vs 0.45 ms | StoreColor, MSAA off to 4x: GLES vs Vulkan 4x | `Quest 3/3S` `Unity 6000.x` | G2-041 [measured] |
| 6+ ms extra; 8 stores per bin at ~15 µs vs 1 at ~2-3 µs; bins 16-18 to 63-66 | Community RenderDoc breakdown of the Vulkan gap with 4x MSAA; gap 1-2 ms without MSAA | `Quest 2` `Quest 3` `Unity 2022.3 / 6000.0` `URP` Forward+ | G1-054 [community] |
| 72 vs 50 fps | UUM-30269, ECS: GLES3 vs Vulkan (only Unity-QA FPS pair) | `Quest 2` `Unity 2022.2.9f1` | G1-057 [community] |
| up to 70% more compute budget | AppSW, Vulkan only | `Quest 2` `Quest 3/3S` `Vulkan` `Unity ≥ 2022.3.15f1` `Unity ≥ 6000.0.9f1` `Unity ≥ 6000.4.0f1` | G1-032 [doc] vendor claim [verify on device] |
| 5-15% | Symmetric Projection GPU gain in GPU-bound scenes; needs Multiview | `Vulkan` | G1-037 [doc] vendor claim [verify on device] |
| 3-8% | Multiview Render Regions gain; no gain with intermediates/post | `Unity ≥ 6000.1` `Vulkan` | G1-039 [doc] vendor claim [verify on device] |
| ~90 MB / ~66 MB per eye | OBD memory saving at 4x MSAA (1680x1760 / 1440x1584); OBD itself is owned by `quest-perf:quest-sdk-choices` | `Quest 3` / `Quest 2` `Vulkan` | G1-038 [doc] |
| up to about 2 FPS | Legacy Graphics Jobs gain; Graphics Jobs modes exist only on Vulkan | `Unity ≥ 2022.3.35f1` `Vulkan` | G1-025, G1-026 [doc] |
| about 10% CPU render cost, no GPU gain | Meta's only expected-gain figure for Unity Vulkan (2020, stale) | Quest 1 era | G1-047 [doc] (pre-2023; stale) |
| 4 | GL_MAX_SAMPLES: 4x is the MSAA ceiling on GLES | `Quest 2` `Quest 3` `GLES` | G1-007 / G2-035 [measured] |
| 16 vs 32 | URP MAX_VISIBLE_LIGHTS: GLES 3.0 shaders vs Vulkan / GLES 3.1+ (A/B confounder) | `URP 14-17` `GLES` | G1-019, G1-020 [doc] |
| 21 votes, Closed Won't Fix, no fix version | UUM-93226 on 2022.3.X, 6000.0.X-6000.3.X, last updated 2025-12-09 | `Unity 2022.3-6000.3` | G1-050, GLES3-GF2-002 [community] |
| no published number | Vulkan PSO vs GLES program-link hitch size | both | KU-03; measure with the hitch step in the A/B protocol |
| no published number | p95/p99 frame time GLES vs Vulkan | both | KU-42; 20-30 min unpinned CSV soak per API |
| no published number | Driver CPU overhead GLES vs Vulkan on XR2 / XR2 Gen 2 | both | G1-068, KU-07; draw sweep 200/500/1000, render-thread ms |
| no published number | 2x MSAA cost per API | both | KU-24; G2-010 recipe at 1x/2x/4x |
| no published number | How much of the UUM-93226 gap OBD recovers | `Vulkan` | U1-076; GLES vs Vulkan vs Vulkan+OBD on a many-mesh scene |

Every published comparison with setup and caveats: [references/evidence-table.md](references/evidence-table.md) (read it before quoting any GLES-vs-Vulkan number to someone else).

## Fixes, ranked by payoff ÷ effort

### 1. Make the API explicit (one API per build)
- **Change:** Project Settings > Player > Android > Other Settings > Rendering: untick **Auto Graphics API**, leave exactly one entry in **Graphics APIs** (G1-016, G1-079). Editor menu script in [references/ab-protocol.md](references/ab-protocol.md).
- **Effect:** removes silent fallback; no frame-time change by itself. Every later measurement depends on it.
- **Cost:** none. On GLES the manifest GLES requirement is added only when Auto is on or OpenGLES3 is listed (G1-016).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2022.3-6000.6` `GLES` `Vulkan`. **Goal:** Throughput and Consistency (valid measurement).

### 2. Decide by feature need first (usually ends the question)
- **Change:** list which of these the project needs. All are Vulkan-only (G1-070 / G2-056, GLES3-GF1-001, GLES3-GF2-006):
  - AppSW: up to 70% more compute budget, vendor claim (G1-031, G1-032). `quest-perf:quest-appsw`.
  - Late Latching: latency, not throughput (G1-036). `quest-perf:quest-frame-pacing`.
  - Symmetric Projection: 5-15%, needs Multiview (G1-037). MRR: 3-8%, Unity 6.1+ (G1-039).
  - OBD: memory, and the UUM-93226 workaround (G1-038).
  - Memoryless render textures (`RenderTexture.memorylessMode`) and memoryless on-tile XR post intermediates; without them an extra final blit (G1-041, GLES3-GF1-001). Depth input attachments (G1-042).
  - Dynamic foveation (OpenXR 1.19+, `XR_FB_foveation_vulkan`) and Subsampled Layout (G1-035, GLES3-GF2-006). Static FFR on GLES + OpenXR is undocumented (GX-C8): `quest-perf:quest-resolution-foveation`.
  - Graphics Jobs Mode Native/Legacy/Split (G1-025); Legacy mode usage is owned by `unity-perf:unity-cpu-scripting`.
  - The Unity OpenXR plugin itself: it lists Quest as Vulkan-only; the Oculus XR GLES path is deprecated from 6.5 (G1-024 / G2-093, G2-C8).
  - Also absent on GLES: GRD, GPU occlusion culling, STP; Entities Graphics GLES support deprecated in 6000.3.12f1 / 6000.4.1f1 (U1-095).
- **Effect:** if any item is needed, ship Vulkan and spend the effort on fixes 3-4 (G1-078). The only GLES-only lever is Low Overhead Mode, in the deprecated Oculus XR plugin (G1-043 / G2-079): `gles3-perf:gles-driver-overhead`. No OpenXR equivalent was found, so moving a GLES build to OpenXR may lose this CPU saving [verify on device]. Check the OpenXR feature list for your plugin version and A/B render-thread ms (KU-43).
- **Cost:** none to decide. Choosing Vulkan means taking on the UUM-93226 MSAA store cost (+5.0 vs +3.3 ms at 4x on Quest 3/3S, G2-039) until fixes 3-4 are applied. Choosing GLES gives up every listed feature and the OpenXR plugin (G1-024).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2022.3-6000.6` `Vulkan`. **Goal:** Throughput (feature gains) and Consistency (long-term support).

### 3. If already on Vulkan with MSAA and it looks slow: turn on Optimize Buffer Discards
- **Change:** OBD in the OpenXR Meta Quest Support or Oculus XR settings; exact paths and the depth-sampling caveat are owned by `quest-perf:quest-sdk-choices`.
- **Effect:** Unity's documented workaround for UUM-93226 (G1-051, G1-053, U1-076). Targets the MSAA store path, so it should lower average GPU time and the MSAA-tied stutter (G1-052). How much of the gap it recovers is unpublished (U1-076). UUM-149765 already had OBD on and still showed Vulkan 4x at +5.0 ms vs +3.3 ms on GLES (G2-039).
- **Cost:** Meta's OpenXR page presents OBD as having no downside. The Oculus XR manual says it can break depth-sampling effects such as camera stacking (Q4-C7, Q4-059). Details: `quest-perf:quest-sdk-choices`. No-op on GLES; the GLES analogue is implicit MSRTT resolve (G1-038 note, G2-036).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2022.3-6000.6` `Oculus XR 4.x` `OpenXR 1.x` `Vulkan` `MSAA on`. **Goal:** Throughput and Consistency.

### 4. Remove Vulkan store/resolve triggers before blaming the API
- **Change:** apply Unity's untethered-XR checklist to **both** builds (G1-048, G1-064): Forward path, depth priming off, Opaque Texture and Depth Texture off, no SSAO, HDR off; keep colour/depth stores to a minimum in Render Graph (G1-055). Store minimisation mechanics: `unity-perf:unity-render-graph-tiling`.
- **Effect:** the community pattern 2021-2026 is that removing depth copies, depth priming, Deferred or MSAA narrows the Vulkan gap (G1-064; G1-061 traced one case to URP PR #4488 being reverted for GLES3 only). Average GPU time; stutter also tied to the MSAA path (G1-052).
- **Cost:** loses effects that need scene depth/colour copies; re-author those.
- **Tags:** `Quest 2` `Quest 3/3S` `URP 14-17` `Unity 2022.3-6000.6` `Vulkan`. **Goal:** Throughput and Consistency.

### 5. Run the single-variable A/B, then apply the decision rule
- **Change:** follow [references/ab-protocol.md](references/ab-protocol.md): one API per build; identical MSAA, renderer, depth priming, Opaque/Depth textures and ES shader level (the 16/32-light difference, G1-020); Vulkan-only features toggled in a separate step; pinned levels for timing; cold and warm launches; OS build and driver strings recorded (G1-079, G1-078, G3-014).
- **Decision rule (G1-078):**
  - Default to **Vulkan** if any Vulkan-only feature is needed, or on Unity 6.1+ with MRR and on-tile post.
  - Consider **GLES** only for a GPU-bound, MSAA-heavy project that needs none of them, and keep it only if it still wins after OBD and store minimisation (fixes 3-4) on Vulkan.
  - Weigh GLES shelf life: Meta calls it legacy with no new features (G1-028); the Oculus XR plugin, its Unity XR path, is deprecated from 6.5 (G1-024).
- **Effect:** no frame-time change by itself. It produces the p50 delta (step A/B) and the p95/p99 and stale-frame delta (step D) that the decision rests on.
- **Cost:** two builds, plus a pinned-level session and a 20-30 min unpinned soak per API, repeated after each Horizon OS update (G1-051).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2022.3-6000.6`. **Goal:** Throughput and Consistency.

### 6. Shrink the MSAA delta on whichever API you keep
- **Change:** the level choice (4x / 2x / off) is owned by `unity-perf:unity-urp-settings`. The per-API input from here: 4x costs about +5.0 ms on Vulkan vs +3.3 ms on GLES on Quest 3/3S, and about +7 ms on Quest 2 on both APIs (G2-039, G2-040). 2x per API is unmeasured (KU-24).
- **Effect:** the largest single GPU lever in the published API comparisons; on Quest 2, treat 4x as a Quest 3-only option unless measured (G2-040).
- **Cost:** image quality (aliasing); the quality trade-off is owned by `unity-perf:unity-urp-settings`.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 6000.x` `GLES` `Vulkan`. **Goal:** Throughput.

### 7. If GLES wins: stay, but pin down the conditions
- **Change:** keep GLES on the Oculus XR plugin, which is deprecated from Unity 6.5 (G1-024); on 6.6, "Use OpenGL ES 3.0 shaders" keeps the 16-light ceiling, and turning it off raises the limit to 32 and adds shader work (G1-018, G1-019, U1-094). Re-run the A/B after each Horizon OS update, because the claimed Qualcomm fix would ship through the OS (G1-051, G1-078).
- **Effect:** keeps the measured GLES win; no new features will arrive (G1-028, G1-076).
- **Cost:** no AppSW, no OpenXR, no dynamic foveation; GLES XR bugs on 6000.x closed Won't Fix (UUM-102876 GL error spam in development builds, UUM-70930, UUM-109377, OXPB-144; G1-075).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2022.3-6000.6` `Oculus XR 4.x` `GLES`. **Goal:** Throughput now, Consistency risk later.

## Verify

- **API switch or OBD for UUM-93226 (Vulkan):** eye-buffer StoreColor/StoreDepthStencil stage time and store count per bin fall toward the GLES pattern (G1-054, G2-041). App GPU time p50 falls; the expected size is unpublished (U1-076). Pinned levels, the same scripted route per build, repeated on a cold and a warm launch (G1-067). For scale: the whole published 4x API gap on Quest 3/3S is +5.0 vs +3.3 ms (G2-039).
- **MSAA-tied stutter:** stale frames per minute and p95/p99 of `app_gpu_time_microseconds` across CSV rows should fall. No baseline exists (KU-42). Run an **unpinned** 20-30 minute soak per API (reboot to clear props) with `ovr_metrics_csv.py`; Perfetto for single-frame pacing (Q1-010, Q1-079).
- **First-use hitches per API:** frames above 1.5x the frame budget on a first-seen-material route, attributed with `Shader.CreateGPUProgram` (GLES) vs pipeline creation markers (Vulkan). Test on the first launch after an OS update and on a second launch, because the EGL blob cache is dropped when `ro.build.id` changes (G1-065, G3-002, G3-014). No published expectation (KU-03).
- **CPU:** render-thread ms (Profiler `Gfx.*` or Perfetto `UnityGfxDeviceW`) over a 200/500/1000 draw sweep; no expected delta published (G1-068).
- **Every A/B record:** Unity version, URP, XR plugin, API, MSAA, OS build, GLES driver string, `getprop | grep debug.oculus` (G1-078, G2-082, Q1-077).

## Pitfalls and myths

- **"Vulkan is always faster on Quest."** Unproven. Doc claims carry no numbers; measurements 2021-2025 favour GLES in MSAA scenes (G1-C1, U1-077). Unity's "Vulkan is more stable" means correctness and crashes, not frame pacing; Unity QA saw more stutter on Vulkan (G1-C5).
- **"GLES is always faster."** With MSAA off, UUM-149765 shows Vulkan slightly faster (9.1 vs 9.7 ms, Quest 3/3S) and the base API is not GPU-faster either way; any Vulkan GPU gain comes from its features (G1-C4). Unity staff reported internal parity with a well set up renderer (G1-055).
- **"UUM-93226 is open / fixed."** It is Closed Won't Fix on 2022.3.X to 6000.3.X with no fixed-in version (G1-050, GX-C1). No Horizon OS note confirms the Qualcomm visibility-stream fix as of 2026-09-24 (GLES3-GF2-002, KU-02).
- **Root cause is contested (G1-C2).** The Dec 2025 tracker note blames a Qualcomm visibility-stream bug plus a Qualcomm-side cost of Vulkan buffer copies. Unity staff in Dec 2024 blamed renderer setup with too many stores. The community traced a 2021 case to URP PR #4488 being reverted only for GLES3. Treat it as layered: engine store choices plus driver cost.
- **"Buffer copies" means vertex/constant buffer updates.** Not supported. The evidence points at render-target stores and resolves on the MSAA path (GX-C2). Buffer-heavy content favouring GLES is a hypothesis to A/B test, nothing more.
- **Switching Multi-pass / Multiview / SPI fixes it.** It made no difference in the UUM-93226 repro (G1-049).
- **"Meta recommends GLES for production."** 2022 advice, superseded; Meta now calls GLES legacy (G1-C6). **"The store requires Vulkan."** No VRC or submission rule requiring Vulkan was found (G1-030). Meta's Advanced GPU Pipelines page calls Vulkan "required" and Unity's Meta Quest build profile defaults to it (U2-094, G2-C1): policy direction, not a runtime block or VRC. Check the current VRC list at submission (KU-14).
- **Quoting absolute UUM-149765 times.** The table (GLES 9.7 / 13.0 ms) and the notes (GLES ~12 / ~15, Vulkan ~11 / ~16) disagree; quote deltas (G2-C9).
- **Confounded comparisons.** Thread 938162 compared Vulkan with OBD + Symmetric Projection + FFR against GLES with Low Overhead Mode (G1-059). Auto Graphics API on, or a different ES shader level, also confounds (G1-016, G1-020).
- **Old Meta numbers.** "About 10% CPU, no GPU gain" and "graphics jobs unstable" are from 2020 (G1-047); "about 3 ms for a wrong MSAA store setup" is 2019 (G1-046). Context only.
- **Extensions are not features.** `GL_QCOM_frame_extrapolation` on the Quest 3 GLES driver is not AppSW (G1-031). `GL_QCOM_texture_foveated_subsampled_layout` is exposed, but Unity's Subsampled Layout path is Vulkan-only (G1-035).
- **GLES timer queries and per-draw GL timings.** A GL timer query forces a flush, after which invalidates are ignored, and per-draw timing on a tiler is inaccurate (G2-006, G2-034, GX-C9). RenderDoc profiling mode costs 5-10% GPU and pins max clock (G3-075, 2020 blog). Details: [references/gles-capture.md](references/gles-capture.md).
- **"No hitch on my headset."** Often just a warm EGL blob cache; measure cold (G3-014).
- **GPU skinning on GLES.** A 2026 forum post says it is unavailable; Unity docs list it with no API restriction and the compute chain supports it. Unresolved; verify with Profiler/Frame Debugger (G1-C3, KU-15) [verify on device].

## Sources

All accessed 2026-09-24.

Meta:
- https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ [doc]
- http://web.archive.org/web/20241011053743/https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-asw/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-fixed-foveated-rendering/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovr-best-practices/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-capture/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc]
- https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ [doc]
- https://developers.meta.com/horizon/documentation/unreal/ts-gpusystrace/ [doc]
- https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android/ [doc]
- https://developers.meta.com/horizon/release-notes/ [doc]
- https://developers.meta.com/horizon/blog/renderdoc-for-oculus/ [doc] (2020; stale)
- https://developers.meta.com/horizon/blog/vulkan-for-mobile-vr-rendering/ [doc] (2019; stale)
- https://developers.meta.com/horizon/blog/vulkan-support-for-oculus-quest-in-unity-experimental/ [doc] (2020; stale)

Unity:
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html [doc]
- https://docs.unity3d.com/6000.1/Documentation/Manual/xr-multiview-render-regions.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-foveated-rendering-support.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/foveatedrendering.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/features/metaquest.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/vulkanapi-graphics-jobs-configuration.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture-memorylessMode.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsMultisampleAutoResolve.html [doc]
- https://docs.unity3d.com/2022.3/Documentation/ScriptReference/SystemInfo-renderingThreadingMode.html [doc]
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc]
- https://unity.com/releases/editor/whats-new/6000.3.12f1 [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/Input.hlsl [doc]
- https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 [community]
- https://issuetracker.unity.com/api/v1.0/issues/1364 [community]
- http://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [measured]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102876 [community]
- https://issuetracker.unity.com/issues/6553/significant-performance-difference-between-vulkan-and-opengles3-when-built-with-ecs [community]
- https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (and ?page=2) [community]
- https://discussions.unity.com/t/1725076 [community]
- https://discussions.unity.com/t/performance-discrepancy-between-vulkan-and-opengl-with-unity-2022-3-17f1-on-meta-quest-3/938162 [community]
- https://discussions.unity.com/t/xr-perf-quest-2022-2-and-trunk-vulkan-vs-gles-perf-disparity-increased-significantly-6223/1726043 [community]
- https://discussions.unity.com/threads/horrible-performance-on-vulkan-with-simple-scene-quest-2.1203082/ [community]
- https://discussions.unity.com/threads/serious-performance-regression-of-using-vulkan-vs-opengl-in-unity-2021-3-8-lts.1322298/ [community]

Khronos, Qualcomm, Android, device data:
- https://opengles.gpuinfo.org/displayreport.php?id=8023 [measured]
- https://opengles.gpuinfo.org/displayreport.php?id=6387 [measured]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_disjoint_timer_query.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture.txt [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html [doc]
- https://mysupport.qualcomm.com/supportforums/s/question/0D5dK000009EniESAS/snapdragon-profiler-not-able-to-capture-anything-on-meta-quest-33s [community]
- https://developer.android.com/agi/supported-devices [doc]
- https://developer.android.com/agi/frame-trace/frame-profiler [doc]
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/BlobCache.cpp [doc]
