---
name: xr2-gen1-vs-gen2
description: "Silicon spec facts for Snapdragon XR2 Gen 1 (Quest 2) vs XR2 Gen 2 (Quest 3/3S): CPU core types and clusters, maximum clocks, Adreno 650 vs 740 generation differences, GMEM, memory type and bandwidth, and Quest 3S vs Quest 3 silicon. Use when checking a spec-sheet claim such as A715 cores, a 690 MHz GPU or LPDDR5 bandwidth, or explaining a hardware difference. Budgets per headset: quest-perf:quest-budgets-tiers."
---

# XR2 Gen 1 vs XR2 Gen 2 silicon

Hardware facts other Quest skills lean on, with wrong spec-sheet claims flagged. Goal:
**Throughput** and **Consistency**: it stops budgets, thread plans and tiers from being
built on clocks, cores or bandwidth a VR app never gets.

Scope: Quest 2 (XR2 Gen 1, SM8250, Adreno 650, 6 GB) and Quest 3/3S (XR2 Gen 2,
SXR2230P, Adreno 740v3, 8 GB). The silicon facts hold for every Unity version (2021.3
to 6.x), every URP version and both graphics APIs, unless a line says otherwise. Quest
Pro and Meta VR Glasses get one line each.

**Lead fact: Quest 3/3S has 6x Cortex-A78C in a 4 + 2 layout (4 cores at 2.36 GHz, 2 at
2.05 GHz). It has no little cores. The "2x A715 + 4x A510" spec line is wrong.**
(A1-013, A1-014, ARM-C1)

## When to use / when not

Use when:
- Someone quotes a spec-sheet claim: "A715/A510", "2.84 GHz", "690 MHz", "640 MHz",
  "LPDDR5X", "68 GB/s", "Quest 3S is LPDDR4X", "2.5x GPU", "3 MB GMEM".
- You need to explain why a shader, thread plan or render-target setup acts differently
  on Quest 2 and on Quest 3/3S: core types, register file, GMEM, concurrent binning,
  LPAC, vertex cache, per-view render areas.
- You need to know whether Quest 3 and Quest 3S are the same compute target (they are).
- You need to know which CPU ISA features to target (one target covers all Quest).

Do not use; go to the owner instead:
- Level-to-clock table, Boost, level trading, dual-core mode, throttling:
  `quest-perf:quest-levels-thermal`.
- Frame budgets, draw-call/triangle budgets, PSS limits, device tiers, porting content
  Quest 3 to Quest 2: `quest-perf:quest-budgets-tiers`.
- Thread placement, affinity arguments, job-worker counts, Burst targets, NEON costs:
  `arm-mobile-hw-perf:xr2-cpu-threads-neon`.
- GMEM bins, FlexRender, LRZ, UBWC, load/store mechanics:
  `arm-mobile-hw-perf:xr2-adreno-architecture`.
- fp16, GPRs, occupancy, instruction cliffs as a shader cost model:
  `arm-mobile-hw-perf:xr2-shader-cost-model`.
- DRAM traffic, power, bytes-per-frame arithmetic: `arm-mobile-hw-perf:xr2-bandwidth-power`.
- Passthrough/MR cost numbers: `quest-perf:quest-mr-costs`.
- Bottleneck unknown: `quest-perf:quest-triage`.

## Diagnose first

The question here is always "which silicon, which cores and which clocks is this number
from?" Confirm that before you trust any capture or claim.

1. **Record the granted levels and clocks, not the spec clocks.** The app clock is the
   level clock (A1-003, A1-005 set).
   ```sh
   adb logcat -s VrApi
   # read CPU/GPU level and MHz, e.g. "CPU4/GPU=4/4,1478/525MHz", plus "Mem=<MHz>"
   ```
   Or use OVR Metrics CPU L / GPU L / GPU F / MEM F (CSV enable:
   `adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV`)
   (A3-049, A3-053). A GPU number without its clock means nothing: on Quest 3 the range
   from L0 to L5 is 599/285 = about 2.1x (A2-008).
2. **Read the CPU set the app is actually allowed to use.** Meta does not publish it
   (A1-004, Known unknowns).
   ```sh
   adb shell 'cat /proc/$(pidof com.company.app)/status | grep Cpus_allowed_list'
   adb shell cat /dev/cpuset/top-app/cpus
   ```
   Confirm placement on Perfetto's CPU scheduling tracks. On Quest 2, expect about 3
   cores, inferred as cpu4-6 [verify on device]. On Quest 3/3S the count is unpublished.
3. **Log what Unity sees at startup** (paste-ready; Unity 2021.3 to 6.x; any XR plugin;
   untested on device):
   ```csharp
   using UnityEngine;
   using Unity.Jobs.LowLevel.Unsafe;

   public static class QuestSiliconProbe
   {
       [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
       static void Log()
       {
           Debug.Log("[SiliconProbe] " +
               $"model={SystemInfo.deviceModel} " +
               $"cpu={SystemInfo.processorType} cores={SystemInfo.processorCount} " +
               $"cpuFreqMHz={SystemInfo.processorFrequency} " +
               $"gpu={SystemInfo.graphicsDeviceName} api={SystemInfo.graphicsDeviceType} " +
               $"ramMB={SystemInfo.systemMemorySize} " +
               $"jobWorkerMax={JobsUtility.JobWorkerMaximumCount} " +
               $"jobWorkers={JobsUtility.JobWorkerCount}");
       }
   }
   ```
   Read it with `adb logcat -s Unity | findstr SiliconProbe` (Windows) or `| grep`.
   `processorCount` may not equal the app-usable core count (ARM-C7).
   `processorFrequency` is not the level clock. Budget with the level table.
4. **Check the GMEM class from the bin count.** Run `adb shell ovrgpuprofiler -e`,
   restart the app, then run `adb shell ovrgpuprofiler -t -v`. Read the eye-buffer
   surface line ("N WxH bins", mode). Meta's Quest 2 example is 135 bins of 96x176
   (A2-013, ARM-GF1-006). Meta's 128x224 example needs about 2 MB of GMEM, so it
   fits Quest 3 (A2-015, [verify on device]). How to read multiview surface lines per
   device: `quest-perf:quest-profiling-toolkit` (A3-034).

## Key numbers

Tags: [doc] vendor docs, [measured] source's own measurement, [community] lead.
"Derived" means arithmetic on cited inputs. Full side-by-side table with every conflict:
[references/soc-comparison.md](references/soc-comparison.md).

| Fact | Quest 2 (XR2 Gen 1) | Quest 3/3S (XR2 Gen 2) | Source / tag |
|---|---|---|---|
| CPU cores | 1x A77 @ 2.84 + 3x A77 @ 2.42 + 4x A55 @ 1.80 GHz | 6x A78C: 4 @ 2.36 + 2 @ 2.05 GHz | A1-001 [community], A1-002 [measured]; A1-013/014 [measured] |
| App cores | 3 (inferred cpu4-6) [verify on device] | unpublished; one report of 2 Unity job workers fits 3 | A1-004 [doc]; A1-055 [community] |
| Max app CPU clock | 2.42 GHz (L8, Boost only); 2.84 GHz is never an app level | 2.36 GHz (L8 Boost); Boost level label conflicts (ARM-C4) | A1-003 [doc]; A1-005 set [doc] |
| Default CPU clock (L4) | 1.48 GHz = 61% of 2.42 (derived) | 1.92 GHz = 81% of 2.36 (derived) | A1-005 set [doc] |
| Unity 2x capacity rule (big/little) | met: A77 vs in-order A55 (capacity, not clock) | not met: identical A78C cores, clock ratio 2.36/2.05 = 1.15x | A1-049, A1-050 [doc] [verify on device] |
| CPU ISA | Armv8.2 + fp16 + dotprod; no SVE/SVE2, no i8mm | same | A1-075 [doc]; A1-076 [measured] |
| System cache | not published | 8 MB (LLC) | A1-012 [doc] |
| GPU | Adreno 650 (A6xx gen3) | Adreno 740v3 (A7xx), Mesa id 0x43050b00 | A2-002, A2-003 [community]; A2-001 [doc] |
| Max GPU level clock | 587 MHz (L5) | 599 MHz (L5); 640/690/492 MHz claims conflict (ARM-C3) | A1-005 set [doc] |
| Register file per SP | reg_size_vec4 = 64 | reg_size_vec4 = 96 (about 1.5x) | A2-003 [community] |
| GMEM | 1 MB (Meta); 1.125 MiB (kernel) | about 2 MB (Meta); 3 MiB kernel value is the SD8 Gen 2 chip, not Quest | A2-010 [doc]; A2-011 [community]; ARM-C9/C10 |
| Concurrent binning, dual LRZ | no | yes (A7xx) | A2-026 [doc]; A2-027 [community] |
| LPAC async compute | no | yes | A2-094 [doc] |
| Per-view render areas/viewports | no | `VK_QCOM_multiview_per_view_render_areas` / `_viewports` | A3-043 [doc] |
| Post-transform vertex cache | not published | 32 x vec4 vertices | A2-049, A3-019 [doc] |
| Graphics shader instruction cliff | not published | each multiple of 2000 instructions | A2-070 [doc] |
| RAM | 6 GB LPDDR4X (5.70 GB visible) | 8 GB LPDDR5 (7.55-7.58 GB visible) | A1-002, A1-008 [community]; A1-013 [measured], A1-023 [community] |
| Peak DRAM bandwidth | 34.13 GB/s theoretical for the SD865 controller; Meta publishes none | unpublished; candidate figures conflict (ARM-C2) | A1-008 [community]; ARM-C2 |
| Default eye buffer | 1440x1584 | 1680x1760 on both 3 and 3S (1.30x Quest 2 pixels) | ARM-GF2-004 [doc] |
| Panel per eye | n/a here | Quest 3 2064x2208 (25 PPD); Quest 3S 1832x1920 (20 PPD) | A1-025 [doc] |
| Dual-core mode | yes (Quest 2, Pro) | no | ARM-GF1-001 [doc] |

Vendor scaling claims, Quest 3 vs Quest 2 (conflict ARM-C20; neither is a
like-for-like measurement):
- Meta: "twice the GPU power", 33% more CPU, over 30% more memory (A1-020, [doc]).
- Qualcomm: 2.5x GPU for Gen 2 vs Gen 1, or up to 50% power saving at Gen 1-level
  visuals (A1-012, [doc]).
- The L4 CPU clock ratio is 1.92/1.48 = 1.30 (derived), so most of the +33% CPU is
  clock, not IPC. Meta gives no A77 to A78C IPC figure (A1-020).
- Plan with Meta's 2x; measure at matched clocks (Fix 8). No independent measurement.

Quest 3 vs Quest 3S: same SoC, same MIDR, same cluster clocks, same GPU (740v3), same
level table (A1-015, A2-001, [doc]). Only the board ("eureka" vs "panther"), the
display/optics and the chassis differ. Sustained thermal headroom per chassis is
unpublished; measure it with the recipe in `quest-perf:quest-levels-thermal`.

## Fixes, ranked by payoff ÷ effort

A "fix" here corrects a plan or budget built on wrong silicon assumptions; the
frame-time effect comes through the owning skill's work.

### 1. Budget CPU from level clocks on the app cores, never from 2.84 GHz or Geekbench
`Throughput` `Consistency` `Quest 2` `Quest 3/3S` `all Unity`
- Size main-thread and render-thread work at the default L4 clock: 1.48 GHz (Quest 2)
  and 1.92 GHz (Quest 3/3S) (A1-003, A1-005 set). Per-level cycle budgets are in
  `arm-mobile-hw-perf:xr2-cpu-threads-neon`. The full level table is in
  `quest-perf:quest-levels-thermal`.
- Never use Geekbench to size VR budgets. Geekbench runs as a 2D app, sees all 8 cores
  and the prime clock (A1-002). Quest 3 single-core ranges 573-931 across 25 uploads
  of the same silicon (A1-021, [measured]).
- Effect: no direct frame-time change. It stops the gap between planned and real CPU
  time (the spec clock is about 1.9x the L4 clock on Quest 2, derived). That gap turns
  into missed frames once content lands.
- Cost: none.

### 2. Treat Quest 3 and Quest 3S as one compute target; tier on the display, not the SoC
`Throughput` `Consistency` `Quest 3/3S`
- Same CPU, GPU, level table and default eye buffer (1680x1760) (A1-015, ARM-GF2-004).
  At equal settings the default per-frame GPU and bandwidth cost is the same. The
  difference appears only when you scale the eye buffer toward the panel (2064x2208
  vs 1832x1920) (A1-025).
- Compare 3 vs 3S GPU captures per pixel or per bin, not per frame, when their render
  scales differ (A2-001).
- Tiering code and SystemHeadset values: `quest-perf:quest-budgets-tiers`.
- Effect: fewer tiers to test; 3S-only cuts come from display or measured thermals.
- Caveat: the 3S memory type/rate is disputed (ARM-C2). iFixit found an LPDDR5 part,
  not LPDDR4X. Until `Mem=` is compared on both headsets, do not assume equal
  bandwidth either [verify on device].
- Cost: none. The risk is missing a 3S thermal or memory difference, so keep the 3S
  parity check in Verify.

### 3. Remove big/little assumptions from Quest 3/3S thread plans
`Consistency` `Quest 3/3S` `Unity 2021.3-6.6`
- On Quest 3/3S every core is an A78C. The "slow" cluster still runs up to 2.05 GHz
  (A1-014). Unity's `big`/`little` affinity aliases use a 2x-capacity fallback rule
  that no Quest 3 core meets, so they may not select what you expect (A1-050,
  [verify on device]).
- Do not port Quest 2 or phone affinity arguments (`-platform-android-*-affinity big`)
  to Quest 3. If you pin at all, read `Cpus_allowed_list` first and use explicit masks
  inside it. Details and argument syntax: `arm-mobile-hw-perf:xr2-cpu-threads-neon`.
- On Quest 2 the A55s are real little cores (in-order, dual-issue; A1-077). A thread
  that lands there causes a frame-time spike. That is a variance problem, not an
  average one.
- Effect: lower p95/p99 CPU frame time if a thread was being misplaced. No change
  otherwise.
- Cost: none if you only remove affinity arguments. Explicit masks need re-checking
  after each OS update (A1-022).

### 4. Ship one Arm64 CPU target; delete SVE/Armv9 code paths
`Throughput` `Quest 2` `Quest 3/3S` `Burst`
- A77 and A78C both implement Armv8.2 + fp16 + dotprod. Neither has SVE/SVE2, and
  Geekbench shows no i8mm on either (A1-075, A1-076). One code-generation target
  covers every Quest. Per-device CPU dispatch buys nothing.
- Any SVE, Armv9 or i8mm path is dead code on Quest. Guard or remove it.
- Burst target names and FloatMode: `arm-mobile-hw-perf:xr2-cpu-threads-neon`.
- Effect: smaller binaries, no untested fallback. Throughput gain only if a generic
  fallback ran instead of NEON dotprod. Average frame time only, not variance.
- Cost: none on Quest. It removes code paths other Android targets may need, so gate
  them per platform.

### 5. Size render targets for Quest 2's 1 MB GMEM; expect about half the bins on Quest 3
`Throughput` `Quest 2` `Quest 3/3S` `Vulkan` `GLES`
- Meta's rule: bytes per pixel = (colour + depth bytes) × MSAA samples, doubled for
  multiview. The driver picks the largest bin that fits GMEM (A2-013). At 4x MSAA +
  RGBA8 + D24S8 + multiview, Quest 2 gets 96x176 bins, 135 bins for 1440x1584
  (A2-013, ARM-GF1-006).
- Quest 3's about 2 MB of GMEM gives fewer, larger bins at the same footprint (A3-004).
  Wider formats (RGBA16F HDR, extra MRTs, more MSAA samples) cost more bins on both,
  and the per-bin overhead hurts Quest 2 more. The bytes-per-pixel table and
  load/store rules are in `arm-mobile-hw-perf:xr2-adreno-architecture`. The MSAA
  level choice is in `unity-perf:unity-urp-settings`.
- Do not size bins from the kernel's 3 MiB (SD8 Gen 2 phone chip) or from Mesa's
  tile-alignment constants. Meta's driver examples (128x224, 320x192) do not follow
  Mesa's alignment of 96 (A2-011, A2-016).
- Effect: a lower binning and load/store share of GPU time, mostly on Quest 2. No
  published ms figure; measure the bin count and the per-stage times in
  `ovrgpuprofiler -t -v`. Average frame time only; no effect on variance.
- Cost: narrower formats or fewer MSAA samples cost HDR range or AA quality. Owned by
  `unity-perf:unity-urp-settings`.

### 6. Keep A7xx-only features optional; do not let the Quest 2 tier depend on them
`Throughput` `Quest 3/3S` `Vulkan` `GLES`
- Quest 3/3S only: concurrent binning (overlaps the binning of later work with the
  rendering of earlier work; a clear of a depth buffer that is reused within the frame
  prevents it) (A2-026). Also LPAC low-priority async compute via
  `VK_KHR_global_priority` LOW (A2-094) (Vulkan only), per-view render areas (A3-043)
  (Vulkan only), bidirectional
  LRZ (A2-031), and the 32-entry vertex cache (A2-049).
- Unity exposure of LPAC and per-view render areas is unknown (A2-094, A3-043). Do not
  plan around them without a RenderDoc capture showing the extension in use.
- Quest 3 gains: skip clearing a depth target you reuse, or give each pass its own
  depth, so concurrent binning can run (A2-026, [verify on device]). Mechanism:
  `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Effect: Quest 3 throughput only; no published figure. On Quest 2 these changes do
  nothing. Average frame time only; no effect on variance.
- Cost: a separate depth per pass costs memory. Skipping a clear needs full depth
  coverage or artifacts appear.

### 7. Profile shaders at the Quest 2 GPR limit; Quest 3 has about 1.5x the register file
`Throughput` `Quest 2` `Quest 3/3S`
- reg_size_vec4 is 64 on the 650 and 96 on the A7xx base. A shader at the GPR limit on
  Quest 2 has more occupancy headroom on Quest 3 (A2-003, [community]).
- A shader that is fine on Quest 3 can be occupancy-bound on Quest 2. Tune GPR use on
  Quest 2 first. Cost model and tools: `arm-mobile-hw-perf:xr2-shader-cost-model`.
  URP HLSL expression: `unity-perf:unity-shader-authoring`.
- Quest 3 has its own cliffs: each multiple of 2000 instructions, 16 unique UBOs,
  16 textures+SSBOs, 32 vertex buffers. 16 samplers is the limit on both
  generations (A2-070).
- Effect: lower average GPU time on Quest 2 when occupancy-bound. No published ms
  figure. Variance unaffected.
- Cost: fewer temporaries or lower precision can cost shader quality.

### 8. Replace "2x"/"2.5x" with a matched-clock A/B before sizing a Quest 2 port
`Throughput` `Quest 2` `Quest 3/3S`
- Method (A2-004): pin GPU L3 on both (`adb shell setprop debug.oculus.gpuLevel 3`:
  490 MHz on Quest 2 vs 492 MHz on Quest 3/3S, the closest match in the levels table,
  A1-005 set). Or pin any level and normalise by `Clocks / Second`. Render the same
  resolution on both, by setting `debug.oculus.textureWidth/Height` equal
  (ARM-GF2-004), or compare per pixel. Pin the CPU likewise (A3-051). Run a fixed
  full-screen ALU-bound shader with fixed iterations. Read `Clocks / Second` and
  `% Shaders Busy` in ovrgpuprofiler. Then repeat at each device's shipped level.
- Repeat with your real heaviest scene. The ratio differs for ALU-bound, bandwidth-bound
  and binning-bound work. Budget sizing from the result: `quest-perf:quest-budgets-tiers`.
- Effect: a correct Quest 2 tier. Planning from 2.5x (Qualcomm, likely phone-class
  clocks, ARM-C20) over-fills Quest 2.
- Cost: device time only, no runtime cost.

### 9. Treat DRAM bandwidth as unmeasured on every Quest
`Throughput` `Consistency` `Quest 2` `Quest 3/3S`
- No Meta or Qualcomm source gives the configured data rate for any Quest (ARM-C2).
  Meta's own logcat docs show two different `Mem=` examples (2092 and 1804 MHz), tied
  to no headset (ARM-C24).
- Before trusting a bandwidth ceiling: read `Mem=` / MEM F on each headset at several
  levels, and run a STREAM-style copy/triad Burst job at a pinned CPU level (A1-008,
  Known unknowns). The method is in the reference file. Bytes-per-frame arithmetic
  and power: `arm-mobile-hw-perf:xr2-bandwidth-power`.
- Effect: stops bandwidth-heavy content (MSAA stores, wide formats, full-screen passes)
  from being scaled by a GPU ALU ratio it does not follow.
- Cost: device time only, no runtime cost.

## Verify

- **Levels and clocks recorded:** every capture you compare has `CPUn/GPU=n/n,xxx/yyyMHz`
  from logcat or CPU L / GPU L / GPU F from OVR Metrics. Quest 2 L4 should read
  1478/525 MHz (A3-068). If Quest 3 GPU F ever reads above 599 MHz, record it against
  ARM-C3 and do not assume it is sustained.
- **Core set:** `Cpus_allowed_list` and Perfetto CPU tracks agree with your thread
  plan over a capture long enough to include your heaviest scene (no published
  duration; choose one and keep it the same for every A/B). Nothing app-critical runs on Quest 2 cpu0-3.
- **Bin count:** on the main eye-buffer surface at 4x MSAA + RGBA8 + D24S8 + multiview,
  Quest 2 should show 135 bins of 96x176 for 1440x1584 (A2-013). Quest 3 bins should be
  larger despite 1.30x the pixels: at 128x224, 1680x1760 needs about 112 bins (A2-015,
  derived) [verify on device]. More bins than that means your per-pixel footprint is
  wider than 32 B/px/view.
- **Matched-clock ratio (Fix 8):** a Quest 3 / Quest 2 GPU-time ratio at matched MHz
  and at shipped levels, with repeated runs per device. No published run count or
  duration applies; A1-021 shows how large run-to-run spread can be on this silicon.
  For long-session behaviour, run 20-30 min per `quest-perf:quest-levels-thermal`.
- **3 vs 3S parity:** same build, same scene, same levels: app GPU time per frame within
  run-to-run noise at the default eye buffer. A consistent gap points to thermals or
  memory, not the SoC. Re-check `Mem=` on both.
- **Baseline hygiene:** pre-Android 14 CPU baselines may not be comparable (governor
  walt changed to schedutil, A1-022). Re-baseline after major OS updates.

## Pitfalls and myths

- **"Quest 3 is 2x A715 + 4x A510."** Wrong. It is 6x A78C (MIDR part 0xD4B r0p2) at
  4 @ 2.36 + 2 @ 2.05 GHz (ARM-C1). The claim sits uncited in Wikipedia's Quest 3/3S
  infoboxes and is repeated in quest.md Q2-004. UploadVR's "two performance and four
  efficiency cores" is the same mistake: it reads two clock tiers as two core types.
- **"Quest 2 runs at 2.84 GHz."** That is the prime core's clock. It is never an app
  level. The app maximum is 2.42 GHz, Boost only, and the default is 1.48 GHz (A1-003).
- **"Quest 3 GPU is 690 MHz" (or 640).** The levels table stops at 599 MHz (L5). 690 MHz
  is Meta VR Glasses' GPU L5, and 492 MHz is Quest 3/3S L3. That suggests copy errors on
  the ovrgpuprofiler and render-stage pages (A3-100, ARM-C3). 640 MHz is UploadVR's
  "Favor GPU" report (A3-088, [community]) and is not in the current table. Read GPU F
  on device.
- **"Quest 2 L4 is 490 MHz."** Stale since the Dec 2022 OS change: L4 = 525 MHz, and
  490 MHz is now L3 (A1-007).
- **"Adreno 740 has 3 MB GMEM."** That is the kernel value for the Snapdragon 8 Gen 2
  phone chip (0x43050a01), not Quest's 0x43050b00. Meta says about 2 MB (ARM-C9). Mesa
  suggests a CCU carve-out (a quarter on a6xx, an eighth on a7xx), which may explain
  both gaps, but that is unconfirmed for Qualcomm's driver (A2-012).
- **"Quest 3 is LPDDR5X / 68 GB/s" and "Quest 3S is LPDDR4X / 42 GB/s."** Both uncited.
  4200 MT/s on a 64-bit bus is 33.6 GB/s, not 68 (derived). iFixit finds LPDDR5 in the
  3S. Micron's LPDDR5X 8.533 Gbps is a supplier platform claim; if Quest ran it, the
  peak would be about 68.3 GB/s (derived), but no source shows that it does (ARM-C2,
  ARM-GF1-005).
- **"Quest 3S is weaker silicon."** Same SoC and level table (A1-015). Its differences
  are display, optics, chassis and possibly memory parts. Battery-derived average draw
  (about 6.7 W vs 9.7 W, ARM-GF2-001) is whole-headset and must not be read as an SoC
  difference.
- **"Use SD8 Gen 2 phone benchmarks for Quest 3."** Closest proxy (same Mesa topology),
  but clocks, GMEM and driver differ (A2-002). Do not copy phone numbers.
- **"XR2+ Gen 2 specs describe Quest 3."** The XR2+ Gen 2 runs 2.4 GHz on all cores and
  has a 15% higher GPU maximum. It is in no Quest (A1-027). Meta VR Glasses use XR2
  Gen 3 (12 GB) and have their own level table on the same Meta page (A3-074). Quest Pro
  uses the Quest 2 CPU/GPU level table; its GMEM is not stated (A3-004).
- **"Quest 3 offloads tracking/passthrough/SpaceWarp to hardware, so the CPU is free."**
  UploadVR [community] claims the offload (A1-024). How much app-core time it frees is
  unpublished, and Meta still measures a passthrough cost (A1-019; numbers in
  `quest-perf:quest-mr-costs`).
- **Mali advice carried over.** 16x16 tiles, FPK/HSR, PLS and malioc do not apply to
  Adreno; only generic TBR concepts transfer (`arm-mobile-hw-perf:xr2-adreno-architecture`).

## Sources

All accessed 2026-09-24. IDs refer to research/arm-mobile-hw.md unless marked.

- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]
  (A1-003, A1-005 set, A1-015, A2-008, A3-074)
- https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ [doc]
  (A1-004, ARM-GF1-001)
- https://developers.meta.com/horizon/blog/boost-app-performance-525-mhz-gpu-frequency-meta-quest-2/ [doc] (A1-007)
- https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ [doc] (A1-019, A1-020)
- https://developers.meta.com/horizon/resources/compare-devices/ [doc] (A1-025)
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]
  (A2-010, A2-013, A3-004)
- https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ [doc] (ARM-GF1-006, A2-020)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
  (A2-001, A2-015, A2-025, A3-034, A3-100)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc] (A3-043, A3-100)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc] (ARM-GF2-004)
- https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ [doc] (A3-051)
- https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ [doc] (A3-053, ARM-GF1-004)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc] (A3-049)
- https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf [doc] (A1-012, ARM-C1, ARM-C20)
- https://docs.qualcomm.com/bundle/publicresource/87-73622-1_REV_A_Snapdragon_XR2__Gen_2_Platform_Product_Brief.pdf [doc] (A1-027, XR2+ Gen 2)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc] (A2-026, A2-049, A2-094)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html [doc] (A2-004, A2-049, A2-070)
- https://documentation-service.arm.com/documentation/102226/0002/Functional-description/Introduction/Supported-standards-and-specifications [doc] (A1-075)
- https://documentation-service.arm.com/documentation/swog011050/latest [doc] (A1-075)
- https://documentation-service.arm.com/documentation/epm128372/latest [doc] (A1-077)
- https://docs.unity3d.com/6000.0/Documentation/Manual/android-thread-configuration.html [doc] (A1-049, A1-050)
- https://browser.geekbench.com/v6/cpu/19091540 [measured] (A1-002, A1-076)
- https://browser.geekbench.com/v6/cpu/19064415 [measured] (A1-013, A1-022)
- https://browser.geekbench.com/v6/cpu/18989681 [measured] (A1-013, A1-015)
- https://browser.geekbench.com/v6/cpu/19157033 [measured] (A1-076)
- https://browser.geekbench.com/search?k=v6_cpu&q=Oculus+Quest+3 [measured] (A1-021)
- https://browser.geekbench.com/search?k=v6_cpu&q=Oculus+Quest+3S [measured] (A1-021)
- https://browser.geekbench.com/v5/cpu/21825265 [measured] (A1-022)
- https://en.wikipedia.org/wiki/List_of_Qualcomm_Snapdragon_systems_on_chips [community] (A1-001, A1-008, A1-014)
- https://en.wikipedia.org/wiki/Quest_2 [community] (A1-008)
- https://en.wikipedia.org/wiki/Meta_Quest_3 and https://en.wikipedia.org/wiki/Meta_Quest_3S [community] (A3-099, ARM-C1, ARM-C2; quest.md Q2-004)
- https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py [community] (A2-002, A2-003, A2-016)
- https://docs.mesa3d.org/drivers/freedreno.html [community] (A2-012)
- https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html [community] (A2-027, A2-031)
- https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/drivers/gpu/drm/msm/adreno/a6xx_catalog.c [community] (A2-011)
- https://www.ifixit.com/Guide/Meta+Quest+3+Chip+ID/165932 and https://www.ifixit.com/Guide/Meta+Quest+3S+Chip+ID/178132 [community] (A1-023)
- https://www.tweaktown.com/news/93872/microns-low-power-memory-optimized-for-snapdragon-xr2-gen-2-platform-vr-and-mixed-reality/index.html [community] (ARM-GF1-005)
- https://www.uploadvr.com/snapdragon-xr2-gen-2/ [community] (A1-024)
- https://www.uploadvr.com/meta-quest-3-gpu-clock-speed-performance-boost/ [community] (A3-088, ARM-C3)
- https://web.archive.org/web/20260214200619/https://communityforums.atmeta.com/discussions/dev-quest/unity-quest-3-multithreaded-performance/1132006 [community] (A1-055)
- https://www.uploadvr.com/quest-3s-images-leak-reveal-battery-size-no-headphone-jack/ [community] (ARM-GF2-001)
