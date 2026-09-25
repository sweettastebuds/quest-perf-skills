---
name: xr2-gpu-counters-sdp
description: "Interpreting Adreno GPU counters on Quest, and the status of Snapdragon Profiler: what % Stalled on System Memory, texture miss, fetch stall, Bus Busy, wave occupancy and binning share mean, Qualcomm's healthy ranges, the Adreno Offline Compiler and shader stats, driver-version checks, and why Snapdragon Profiler is treated as unsupported on Quest. Use when a counter value needs a verdict, or when someone asks for Snapdragon Profiler."
---

# Adreno GPU counters and Snapdragon Profiler on Quest

Goal: **diagnosis for both goals.** A counter verdict tells you whether a GPU-bound frame is bandwidth-, texture-, vertex/binning- or ALU/register-bound (**Throughput**), and whether DRAM traffic is high enough to cost heat over a 20-30 min session (**Consistency**). It also keeps measurement overhead (detailed mode, SDP, per-draw stalls) from contaminating the numbers you act on.

Hardware in scope: Quest 2 = XR2 Gen 1, Adreno 650. Quest 3/3S = XR2 Gen 2, Adreno 740v3. Counters come from the OS and Qualcomm/Meta driver, so the meanings hold for any Unity version (2021.3 / URP 12 to 6000.x / URP 17+) and both Vulkan and GLES unless a tag says otherwise. Shader stats inside RenderDoc are `Vulkan` only (G3-073).

Qualcomm's thresholds are written for Adreno in general, not for Quest (A3-054). Meta's tools use the same counter names because Meta built its Performance Interface Library with Qualcomm in 2020 (A3-058), so the thresholds are a reasonable first verdict, not a Quest spec.

## When to use / when not

Use when:
- You have a counter value (from ovrgpuprofiler, RenderDoc Meta Fork draw-call metrics, OVR Metrics or MQDH) and need to know whether it is healthy and what it points at.
- You need to map a counter name between tools, or know which tool exposes a counter at all.
- Someone asks to "use Snapdragon Profiler", or follows a guide that relies on it.
- You need to check that `half` really compiled to 16-bit, or that a shader spills, using shader stats or the Adreno Offline Compiler.
- You need the driver version before trusting shader stats.

Do not use; go to the sibling instead:
- Bottleneck not yet known (CPU vs GPU vs pacing vs thermal): `quest-perf:quest-triage`.
- How to install, launch and script the tools (MQDH, Perfetto, RenderDoc capture flow, OVR Metrics CSV): `quest-perf:quest-profiling-toolkit`.
- Reading surface lines, bin counts, render modes and LRZ state: `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Per-instruction cost, GPR budget, fp16 rate, filtering cost: `arm-mobile-hw-perf:xr2-shader-cost-model`.
- Bytes-per-frame arithmetic, watts, heat: `arm-mobile-hw-perf:xr2-bandwidth-power`.
- GLES capture caveats (timer queries, RenderDoc GL limits, API A/B): `gles3-perf:gles-vs-vulkan`.
- Unity Profiler / Frame Debugger workflow: `unity-perf:unity-profiling-workflow`.

## Diagnose first

Precondition: `quest-perf:quest-triage` says GPU-bound. Then make counters comparable run to run.

1. **Freeze the conditions.** Pin CPU/GPU levels to 4, turn off foveation and dynamic resolution, and record `getprop | grep debug.oculus` (A3-051, A3-052, Q1-077/079); commands in `quest-perf:quest-profiling-toolkit`.
2. **Record the driver** (A2-089):
   ```sh
   adb shell dumpsys SurfaceFlinger | grep GLES   # prints e.g. "V@0676.0"
   ```
   Qualcomm: Vulkan shader stats (SDP example) need driver 636+; whether the same gate applies to RenderDoc Meta Fork shader stats is undocumented [verify on device].
3. **Resolve metric IDs on this device and OS build** (A3-027, Q1-065). IDs are list positions and change between devices and runtimes:
   ```sh
   adb shell ovrgpuprofiler -m -v                   # realtime metrics with descriptions
   adb shell ovrgpuprofiler -m -t                   # per-render-stage metrics
   adb shell ovrgpuprofiler -x -m                   # per-draw metrics
   ```
4. **First-read realtime set** (A3-028, A3-029, Q1-066). Up to 30 metrics at once, one line per second. Steady scene, at least 30 s:
   ```sh
   adb shell timeout 60 ovrgpuprofiler -r"<ids of: Clocks / Second, GPU % Bus Busy, % Vertex Fetch Stall, % Texture Fetch Stall, % Texture L1 Miss, % Texture L2 Miss, % Stalled on System Memory>"
   ```
   `timeout` runs on the device (toybox `timeout`) so the line works from Windows cmd/PowerShell too [verify on device]. If values do not settle on a static view, the scene has not settled (Q1-066).
5. **Binning share** (A3-030, G3-079). Detailed mode costs about 10% GPU render time (A3-029):
   ```sh
   adb shell ovrgpuprofiler -e <package>   # then restart the app
   adb shell ovrgpuprofiler -t -v          # Binning ms ÷ surface ms for the eye buffer
   adb shell ovrgpuprofiler -d             # turn detailed mode off as soon as the stage trace is done, before any timing or soak (Q1-067)
   ```
6. **Per-draw ranking**: RenderDoc Meta Fork draw-call metrics on a Development build, sorted by Clocks first (Q1-062, G3-073). Byte counters (`Read Total`, `Write Total`) in a separate capture from timing (A3-055).
7. **Per-shader**: RenderDoc Meta Fork shader stats on Vulkan (Q1-063); on GLES, the Adreno Offline Compiler (G3-073 notes, G3-042).

Then read the numbers against Key numbers and the verdict table in Fix 1.

## Key numbers

| Number | Value | Source / tags |
|---|---|---|
| % Stalled on System Memory | under ~2%; short spikes to 30% are acceptable | A3-054 [doc] Qualcomm. `Adreno (general, not Quest spec)` |
| % Texture Fetch Stall | **Conflict.** Qualcomm: under ~2%, sustained ~16% or more too high (A3-054). Android AGI: fetch stalls above ~5% are a concern (A3-056). Working rule, skill interpretation (no published source): 2-5% watch, above 5% act. | [doc] both. `Adreno (general, not Quest spec)` |
| % Texture L1 Miss / L2 Miss | L1 under 50%, L2 under 40% | A3-054 [doc]. `Adreno (general, not Quest spec)` |
| % Vertex Fetch Stall | near 0% | A3-054 [doc]. `Adreno (general, not Quest spec)` |
| Binning share of a render pass | 10-20%; 30% "usually too much" | A3-054, G3-079 [doc]. `Adreno (general, not Quest spec)` |
| GPU % Bus Busy | up to ~25% battery-conscious app; up to ~90% max-performance app. For thermally constrained VR the 25% band is the safer target (dossier interpretation) | A3-054 [doc]. `Adreno (general, not Quest spec)` |
| Shader stats: texture fetches per read group | keep below 15 | Q1-063 [doc] Meta. `Quest 2` `Quest 3/3S` `Vulkan` |
| Shader stats: scratch memory | any use means poor performance (register spill) | Q1-063 [doc] Meta. `Vulkan` |
| fp16 check | Fragment ALU Instructions (Half) much higher than (Full) | G3-042 [doc] Qualcomm; counters in RenderDoc per Q1-062. `Adreno (general, not Quest spec)` `Quest 2` `Quest 3/3S` |
| % Wave Context Occupancy | low = GPR or instruction-cache pressure. No published healthy value or GPR-to-occupancy table for 650/740; compare before/after | A2-067, A2-090 [doc]. `Adreno (general, not Quest spec)` (SDP only) |
| Driver for Vulkan shader stats | Qualcomm: Vulkan shader stats (SDP example) need driver 636+; whether the same gate applies to RenderDoc Meta Fork shader stats is undocumented [verify on device]. `driverVersion` = 10 bits major, 10 minor, 12 patch | A2-089 [doc]. `Adreno (general, not Quest spec)` |
| ovrgpuprofiler realtime cap | 30 metrics per `-r` | A3-029 [doc]. `Quest 2` `Quest 3/3S` |
| ovrgpuprofiler detailed mode | about 10% GPU render time overhead | A3-029, Q1-067 [doc]. `Quest 2` `Quest 3/3S` |
| Snapdragon Profiler overhead | about 5% CPU even when tracing only frame rate | A3-061 [doc] Qualcomm. `Adreno (general, not Quest spec)` |
| Realtime metric count | **Conflict Q1-C8.** Meta example: 47. arXiv study: 72 (78 on Quest 3S). Community skill: 81 on Quest 3. Device/runtime-dependent | Q1-065 [doc], Q1-076 [community] |
| RenderDoc draw-call metric count | **Conflict ARM-C16.** Current table ~48; a search snippet cited 59 | A3-041 [doc] |
| Quest 3/3S GPU clock, for `Clocks / Second` | **Conflict ARM-C3.** Levels table: L5 = 599 MHz max. ovrgpuprofiler page: 690 MHz Quest 3, 492 MHz Quest 3S (likely copy errors). Read `Clocks / Second` or GPU F on device | A3-100 [doc]. `Quest 3/3S` |
| UBWC compression ratio | no published number; measure with RenderDoc `Write Total` on the same content, optimal-tiled vs MUTABLE_FORMAT/LINEAR [verify on device] | arm dossier Known unknowns |

Full counter-by-counter glossary with tool availability: [references/counter-glossary.md](references/counter-glossary.md). Read it when a counter name is not in the table above, when you need to know which tool exposes a counter, or when mapping names between ovrgpuprofiler, RenderDoc, OVR Metrics, SDP and AGI.

## Fixes, ranked by payoff ÷ effort

This skill fixes diagnoses, not content. Each item either routes a counter verdict to the owning fix, or removes an error from the measurement itself.

### 1. Route by counter pattern, not by single counter (Throughput; Consistency for Bus Busy)

Read the first-read set as a pattern (A3-039, A3-054, Q1-074):

| Pattern (pinned level, steady view) | Verdict | Go to |
|---|---|---|
| % Stalled on System Memory above ~2% sustained, Bus Busy high | DRAM bandwidth-bound: stores, extra full-screen passes, uncompressed or large textures | `arm-mobile-hw-perf:xr2-bandwidth-power`, `unity-perf:unity-render-graph-tiling` |
| % Texture Fetch Stall high, L1 miss above 50% and L2 miss above 40% | texture bandwidth: missing mips, uncompressed formats, large texels | `unity-perf:unity-memory-assets`, `arm-mobile-hw-perf:xr2-shader-cost-model` |
| L1 miss high, L2 miss low | access-pattern thrash (dependent or scattered UVs), not DRAM bandwidth (Q1-074 [community]) | `arm-mobile-hw-perf:xr2-shader-cost-model` |
| Fetch stall and % Texture Pipes Busy high, % Anisotropic Filtered high | aniso cost; one measured case lost 8.9 ms of 13.8 ms to 8x aniso on Quest 3 (Q1-075 [measured], non-Unity engine) | `arm-mobile-hw-perf:xr2-shader-cost-model` |
| % Vertex Fetch Stall above ~0, Binning above 20-30% of the surface | vertex/binning-bound: vertex count, attribute layout, vertex texture fetch | `arm-mobile-hw-perf:xr2-adreno-architecture` |
| % Shaders Busy high, % Shader ALU Capacity Utilized low | shaders stalled on memory, not computing (Q1-074 [community]) | back to the stall counters above |
| Stalls low, % Time Shading Fragments dominant, ALU/Fragment high | ALU-bound fragment shading | `unity-perf:unity-shader-authoring`, `quest-perf:quest-resolution-foveation` |
| Low % Wave Context Occupancy (SDP only), or high register footprint / scratch in shader stats | register pressure, spills | `arm-mobile-hw-perf:xr2-shader-cost-model` |

- Effect: picks the fix that moves average GPU ms; guessing from one counter often picks the wrong owner. Bus Busy above ~25% also predicts thermal decay, a Consistency risk (A3-054, interpretation).
- Quality cost: none (diagnosis).
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` `any Unity/URP`.

### 2. Remove profiler overhead before any timing or soak (Consistency, Throughput)

- `adb shell ovrgpuprofiler -i` to check, `-d` to turn off detailed mode. Left on, it inflates GPU render time by about 10% (A3-029, Q1-067) and shifts level behaviour during a long run.
- Do not run Snapdragon Profiler during CPU measurements: about 5% CPU even for frame-rate-only tracing, enough to move the CPU level on a CPU-bound title (A3-061).
- Do not read absolute ms from per-draw metrics (`-x`, RenderDoc per-draw): per-draw measurement adds pipeline stalls; compare draws within one trace only (A2-088, Q1-073). Use `-l` (low overhead) for per-surface timing (A3-030, Q1-068).
- Unpin levels (reboot) before a 20-30 min soak (Q1-079).
- Effect: removes up to ~10% false GPU time (average) and false level rises (variance, thermal).
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` `any Unity/URP`.

### 3. Resolve IDs by name and respect the counter budget (Throughput, Consistency)

- Never hard-code ovrgpuprofiler metric IDs in shared scripts; resolve names from `-m` on the target device and OS (A2-087, A3-027, Q1-C8).
- Per-stage and per-draw captures have a SoC counter budget; output reports e.g. "Captured 2 metrics, 1 rejected by SoC counter budget". Split the list across runs (A3-032, Q1-072). `-s` is ignored when `-x` is present (Q1-072).
- "Failed to retrieve drawcall trace results. Received 0 metrics." is a known RenderDoc error with a Quest 3 TODO on Meta's page (Q1-062) [verify on device].
- Stamp each capture with the build's graphics context so logs from different runs are not mixed. Paste-ready, compiles on Unity 2021.3 to 6000.x:
  ```csharp
  using UnityEngine;

  static class GpuCaptureContext
  {
      [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
      static void Log()
      {
          // Grep logcat for "GpuCaptureContext" and store it next to the capture.
          Debug.Log($"GpuCaptureContext api={SystemInfo.graphicsDeviceType} " +
                    $"device={SystemInfo.graphicsDeviceName} " +
                    $"version={SystemInfo.graphicsDeviceVersion} " +
                    $"unity={Application.unityVersion}");
      }
  }
  ```
  Whether `graphicsDeviceVersion` contains the Qualcomm `V@` driver string on Quest is not documented; keep the SurfaceFlinger line as the driver record [verify on device].
- Effect: prevents misread counters and wrong-owner fixes (avg); no variance effect.
- Quality cost: none.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` `Unity 2021.3+`.

### 4. Capture bytes separately from time (Throughput)

- Qualcomm marks Avg Memory Latency Cycles, Texture Memory Read BW, Vertex Memory Read and Write Total as "Slow To Trace": they add significant overhead (A3-055). Take timing in one capture, bytes in another.
- Per-draw byte counters exist only in RenderDoc Meta Fork: `Read Total`, `Write Total`, `Texture Memory Read BW`, `Vertex Memory Read`, `SP Memory Read` (A3-036). Whether realtime `-r` has byte counters is undocumented; check `-m -v` on device (A3-028) [verify on device].
- `Avg Bytes / Fragment` is imprecise by Meta's own description; use it to rank materials, not as an absolute (A3-038).
- High `Vertex Memory Read` during binning explains slow binning (A3-055).
- Store-traffic method and derived byte budgets: `arm-mobile-hw-perf:xr2-bandwidth-power`.
- Effect: removes Slow-To-Trace overhead from timing captures (avg accuracy).
- Quality cost: an extra capture.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` (RenderDoc Meta Fork supports both, A3-035, G3-073).

### 5. Confirm precision and spills from compiled output (Throughput)

- RenderDoc draw-call metrics: `Fragment ALU Instructions (Full/Half)`. Half should be much higher than Full if `half` / `min16float` compiled to 16-bit (G3-042, Q1-062). Mixed precision chains pay conversion instructions (A2-066); cost model in `arm-mobile-hw-perf:xr2-shader-cost-model`.
- RenderDoc shader stats (Vulkan only, Development build): register footprint, Scratch Memory, ALU 32-bit/16-bit, Texture Read. Scratch above zero means spills; texture fetches per read group: keep below 15 (Meta's line) (Q1-063, G3-073).
- GLES builds: RenderDoc gives no per-shader register or instruction stats; use the Adreno Offline Compiler for static instruction and register counts (G3-073 notes, G3-042).
- Adreno Offline Compiler caveat: Quest drivers are Meta builds; output from the compiler's driver may differ from the headset (A2-089) [verify on device]. Cross-check one shader's counts against on-device shader stats before trusting it for a whole library.
- Driver gate: Qualcomm: Vulkan shader stats (SDP example) need driver 636+ (A2-089); whether the same gate applies to RenderDoc Meta Fork shader stats is undocumented [verify on device]. Decode a raw `VkPhysicalDeviceProperties.driverVersion`:
  ```sh
  py -3.12 -c "v=0x0; print('major', v>>22, 'minor', (v>>12)&0x3FF, 'patch', v&0xFFF)"   # replace 0x0 with the value
  ```
- Effect: confirms or excludes a register-spill or precision fix before shipping (avg GPU ms).
- Quality cost: none. Side effect: the Offline Compiler may disagree with the Meta driver.
- Tags: `Quest 2` `Quest 3/3S`; shader stats `Vulkan`; Offline Compiler `GLES` `Vulkan`; `any Unity/URP`.

### 6. Treat Bus Busy as a thermal signal, then confirm with bytes (Consistency, Throughput)

- `GPU % Bus Busy` is one of two realtime bandwidth proxies (with `% Stalled on System Memory`) (A3-028). Aim for the ~25% battery-conscious band over the ~90% max-performance band on a headset that must hold levels for 20-30 min (A3-054, interpretation).
- MQDH Performance Analyzer's "GPU Memory Access" module is the only live bandwidth graph in a Meta GUI; units, sampling rate and source counter are undocumented (A3-047) [verify on device] against RenderDoc Read/Write Total.
- OVR Metrics exposes no byte or bandwidth stat, only MEM F (A3-048); use it for long-session trends.
- Effect: early warning of thermal decay (variance over 20-30 min).
- Quality cost: none.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES`. Physics and budgets: `arm-mobile-hw-perf:xr2-bandwidth-power`; throttling behaviour: `quest-perf:quest-levels-thermal`.

### 7. Use Snapdragon Profiler only for what nothing else shows, and only after proving it works (Throughput)

Working position: **unsupported on Quest unless proven on your OS build** (A3-067). Meta's tool index omits it (A3-057), Meta's dedicated SDP page returns 404 (G3-084), and community reports show capture failures on Quest 1/2 and a Quest 3/3S "not able to capture anything" thread (A3-063 to A3-065, G3-085). Counter-evidence: Meta's current Unreal debugging page still lists SDP generically because Quest "uses a Qualcomm chipset" (A3-059, GLES3-GF2-008). Assessment in both dossiers: the generic mention does not outweigh the specific failures (GX-C11, G3-C4).

What only SDP documents: per-surface UBWC "Optimal"/"Linear" (A3-062), % Wave Context Occupancy, % CP Busy for query overhead, and subpass-merge status in Rendering Stages (A2-090). If one of these decides a fix, run the test procedure in [references/sdp-on-quest.md](references/sdp-on-quest.md) and record which mode fails. Read that file whenever SDP is requested, a guide assumes it, or you need UBWC status.

Replacements (A3-067): ovrgpuprofiler for realtime counters and stage traces, RenderDoc Meta Fork for per-draw bytes and the Tile Timeline, Perfetto/MQDH for timelines, OVR Metrics for long-session CSVs. How to run them: `quest-perf:quest-profiling-toolkit`.
- Effect: none unless SDP works on your OS build.
- Quality cost: about 5% CPU while attached (A3-061).
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` [verify on device].

## Verify

A counter verdict is verified when the fix it routed to moves both the counter and GPU time, at the same pinned level, on the same view.
- Bandwidth fixes: `% Stalled on System Memory` falls toward under ~2% and `GPU % Bus Busy` falls; `Write Total` for the pass falls. Realtime `-r` at 1 Hz, 30-60 s steady view, before and after.
- Texture fixes: `% Texture Fetch Stall` toward Qualcomm's ~2% (AGI: ~5%; see conflict), L1 miss under 50%, L2 under 40%. Same session length.
- Vertex/binning fixes: Binning share in `-t -v` toward 10-20%; `% Vertex Fetch Stall` toward 0.
- Register fixes: shader stats scratch goes to 0; register footprint falls; Half/Full ratio rises. One capture before, one after.
- No threshold gives a GPU-ms delta; there is no published counter-to-ms conversion. Measure App GPU ms with the compositor skipped (A3-051):
  ```sh
  adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SKIP_RENDERING --ei milliseconds 60000
  ```
- Overhead removed: `ovrgpuprofiler -i` reports detailed mode off; GPU time drops by up to ~10% if it had been left on (A3-029).
- Consistency: after the fix, unpin levels, run 20-30 min with OVR Metrics CSV (A3-049) and confirm GPU level and stale frames hold (owner: `quest-perf:quest-levels-thermal`).

## Pitfalls and myths

- **"Snapdragon Profiler is the Quest GPU profiler."** Pre-2021 guides say so; Meta's current index does not list it and its Meta page is gone (A3-057, G3-084). Old OS-v27-era advice that GPU counters need `ovrgpuprofiler -r` running for Perfetto has likely changed; current MQDH offers GPU Metrics as a checkbox (A3-046, ARM-C18). GPU Systrace was deprecated on 2024-12-02 (G3-083).
- **Qualcomm thresholds as Quest specs.** They are for Adreno in general (A3-054). Use them for a first verdict, then confirm with GPU ms.
- **Hard-coded metric IDs.** Counts range from 47 to 81 across sources (Q1-C8); IDs shift with device and OS (A3-027).
- **Per-draw ms as absolute cost.** Per-draw capture adds stalls (A2-088).
- **Timer queries around invalidates.** A GPU timer query before an invalidate forces a flush and the store happens anyway (A3-023); Qualcomm vs Meta advice on query placement: `gles3-perf:gles-vs-vulkan` (GX-C9). Per-bin query cost: `arm-mobile-hw-perf:xr2-adreno-architecture`.
- **AGI or APA on Quest.** AGI needs Android 11+ and a debuggable app, lists no Quest headset, and profiles GLES through an ANGLE-to-Vulkan layer, so GL timings do not reflect Adreno's native driver (G3-086). AGI is superseded by Android Performance Analyzer (APA); Quest support for either is undocumented (A3-056). Their counter names still match Meta's, which helps map documentation (A3-056 notes).
- **Mali counters or malioc.** Do not transfer to Adreno (A2-099).
- **Mesa Turnip debug flags** (`sysmem`, `gmem`, `nobin`, `nolrz`, `noubwc`, `forcebin`) do not exist on Quest's Qualcomm driver (A2-092).
- **Offline Compiler numbers as ground truth.** Quest's driver is a Meta build (A2-089) [verify on device].
- **Reading `Clocks / Second` against 690 MHz on Quest 3.** Budget with the levels table (599 MHz L5); the profiler page's 690/492 MHz conflict with it (ARM-C3).
- **Preempt time as app cost.** Preempt is compositor preemption, not app work (A3-031); no published guidance on subtracting it (Q1-070).
- **Multiview double counting.** Quest 2 prints one surface with bins shared by both views; Quest 3/3S print one line covering both (A3-034). Details: `arm-mobile-hw-perf:xr2-adreno-architecture`.

## Sources

All accessed 2026-09-24.
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md (same guide also at https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html) [doc]: healthy ranges, Slow To Trace, SDP modes, ~5% overhead, binning share, Half/Full check (A3-054, A3-055, A3-060, A3-061, G3-079, G3-042, G3-084)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]: Offline Compiler, driver 636+, SurfaceFlinger check, driverVersion bits, SDP signals, occupancy, precision conversion (A2-089, A2-090, A2-067, A2-066)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md [doc]: SDP Optimal/Linear UBWC display (A3-062)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]: metric listing, realtime cap, detailed-mode overhead, per-draw stalls, counter budget, 690/492 MHz (A2-087, A2-088, A3-027 to A3-034, A3-100, Q1-065 to Q1-073)
- https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ [doc]: draw-call counters, byte counters, Stalled on System Memory definition (A3-036 to A3-041, Q1-062)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-drawcall/ [doc]: draw-call metrics, 0-metrics error (Q1-062)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ [doc]: shader stats fields, texture fetches per read group, scratch (Q1-063)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ [doc]: GL and Vulkan support, Vulkan-only shader stats (G3-073, A3-035)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ and https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ [doc]: OVR Metrics stats, CSV (A3-048, A3-049)
- https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ [doc]: GPU Memory Access module (A3-047)
- https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ and https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]: pinning, compositor skip (A3-051, Q1-077, Q1-079)
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc]: disable dynamic resolution while profiling (A3-052)
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]: 599 MHz L5 (ARM-C3)
- https://developers.meta.com/horizon/resources/developer-tools/ [doc]: tool index without SDP (A3-057, A3-067)
- https://developers.meta.com/horizon/blog/improving-gpu-profiling-on-oculus-quest/ [doc]: Performance Interface Library lineage (A3-058)
- https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android/ [doc]: generic SDP mention (A3-059, GLES3-GF2-008)
- https://developers.meta.com/horizon/documentation/unreal/ts-gpusystrace/ [doc]: GPU Systrace deprecation (G3-083)
- https://developer.android.com/agi/sys-trace/memory-efficiency [doc]: AGI counters, ~5% fetch-stall concern, APA (A3-056)
- https://developer.android.com/agi/supported-devices and https://developer.android.com/agi/frame-trace/frame-profiler [doc]: AGI not supported on Quest, ANGLE path (G3-086)
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]: timer query before invalidate forces a flush (A3-023)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc]: stage names, Preempt (A3-031)
- https://developers.meta.com/horizon/blog/how-to-run-a-perfetto-trace-on-oculus-quest-or-quest-2/ [doc]: OS v27-era Perfetto GPU counters (A3-046)
- https://docs.vulkan.org/samples/latest/samples/performance/subpasses/README.html [doc]: Mali counters do not transfer (A2-099)
- https://mysupport.qualcomm.com/supportforums/s/question/0D5dK000009EniESAS/snapdragon-profiler-not-able-to-capture-anything-on-meta-quest-33s [community]: Quest 3/3S capture thread, title only (A3-065, G3-085)
- https://communityforums.atmeta.com/discussions/dev-quest/is-any-way-to-make-a-vulkan-gpu-capture-on-quest-/837235 [community]: SDP Vulkan failure 2020 (A3-063)
- https://github.com/tommy-xr/functor/blob/HEAD/.claude/skills/oculus-profiling/SKILL.md [community] / [measured]: counter-pattern reading, aniso case (Q1-074, Q1-075)
- https://arxiv.org/abs/2509.10703 [community]: 72/78 realtime metrics (Q1-076)
- https://docs.mesa3d.org/drivers/freedreno.html [community]: Turnip flags not on Quest (A2-092)
