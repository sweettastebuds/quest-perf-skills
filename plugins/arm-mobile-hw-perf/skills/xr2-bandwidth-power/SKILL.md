---
name: xr2-bandwidth-power
description: "Memory bandwidth, power and heat source on XR2 Quest headsets: why DRAM traffic dominates energy, per-frame traffic budgets for eye-buffer stores and extra full-screen passes, measuring bandwidth (RenderDoc byte counters, MQDH GPU Memory Access), battery and whole-headset power figures, and the unknown thermal envelope. Use for battery drain, watts, a bandwidth-bound GPU, or estimating the DRAM bytes of a pass. Throttling behaviour: quest-levels-thermal."
---

# XR2 bandwidth and power

DRAM bytes per frame, their watts, and how to measure both. Goals: **Consistency** (less
heat, later or no throttle over 20-30 min) and **Throughput** (traffic-bound frames).
Scope: Quest 2 (XR2 Gen 1, Adreno 650, 6 GB LPDDR4X), Quest 3/3S (XR2 Gen 2, Adreno
740v3, 8 GB LPDDR5). The byte arithmetic holds for Unity 2021.3 (URP 12) to 6000.x
(URP 17+), Vulkan and GLES; *how* to stop a store per API/URP lives in the owners below.

**Lead facts.**
- An off-chip DRAM access costs about 100x an on-chip access (A3-001). Arm's rule of
  thumb is about 0.1-0.12 W per GB/s of DRAM traffic; use it as an order of magnitude
  only (A3-002, ARM-C22).
- One resolved RGBA8 store of the default 1680x1760 stereo eye buffer (Quest 3 and 3S)
  is 23.65 MB/frame = 1.70 GB/s at 72 Hz, 2.84 GB/s at 120 Hz (A3-009, derived).
  Storing 4x MSAA colour+depth samples instead is 8x that: about 13.6 GB/s at 72 Hz,
  roughly 1.6 W against about 0.2 W (A3-011, derived).
- Each extra full-screen RGBA8 pass (store + read-back) is about 3.4 GB/s at 72 Hz;
  FP16 doubles it (A3-012, derived).
- Quest 3 averages about 9.7 W for the whole headset (19.44 Wh / ~2 h). A community
  USB-C measurement gives 7.5-9.0 W for a VR game and 10.5-12.0 W for an MR game
  (ARM-GF1-002, ARM-GF2-002, [measured], OS v57).
- No TDP or thermal envelope is published for any Quest (section 1.7 of the dossier).
- Only RenderDoc Meta Fork's `Read Total` / `Write Total` give bytes per draw (A3-036).

## When to use / when not

Use when:
- Someone asks about watts, battery drain, "what is heating the headset", or how many
  DRAM bytes a pass, a render target or a setting costs.
- The GPU looks bandwidth-bound: `% Stalled on System Memory` or `GPU % Bus Busy` high,
  Load*/Store* stages visible in the tile trace, frame time scales with resolution
  more than with shader complexity.
- You need to turn a pipeline change (drop a pass, narrow a format, stop a depth store)
  into bytes per frame, GB/s and an order-of-magnitude watt figure.
- You need to measure bandwidth, the memory clock (`Mem=`, MEM F) or whole-headset
  power, or you are asked for a TDP or peak bandwidth figure (answer: unpublished;
  here is how to measure).

Do not use; go to the owner instead:
- Levels, clocks, throttling, PLS, soak protocol: `quest-perf:quest-levels-thermal`.
- Installing and running the profilers and `ovr_metrics_csv.py`: `quest-perf:quest-profiling-toolkit`.
- Binning, GMEM, load/store mechanics, UBWC formats: `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Counter meanings and healthy ranges, Snapdragon Profiler: `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
- Post-processing cost and Render Graph pass merging: `unity-perf:unity-render-graph-tiling`.
- URP settings that add a store or pass (HDR, Depth/Opaque Texture, MSAA): `unity-perf:unity-urp-settings`.
- GLES `glInvalidateFramebuffer` / clear discipline: `gles3-perf:gles-tile-load-store`.
- Passthrough / Depth API budgets: `quest-perf:quest-mr-costs`.
- Render scale, FFR, dynamic resolution: `quest-perf:quest-resolution-foveation`.
- Texture compression and mip streaming: `unity-perf:unity-memory-assets`.
- Spec-sheet memory type and data rate disputes: `arm-mobile-hw-perf:xr2-gen1-vs-gen2`.

## Diagnose first

Confirm that traffic, not ALU or CPU, is the problem, and get a byte count to compare
against the derived budget. Pin levels and disable foveation for A/B timing (A3-051):
`adb shell setprop debug.oculus.cpuLevel 4`, `adb shell setprop debug.oculus.gpuLevel 4`,
`adb shell setprop debug.oculus.foveation.level 0`,
`adb shell setprop debug.oculus.foveation.dynamic 0`. Disable dynamic resolution while
profiling (A3-052). Unpin for soaks.

1. **Realtime bandwidth proxies** (all Quest; A3-027 to A3-029). Look up metric IDs on
   the device first; they vary by device and runtime, so never hard-code them:
   ```sh
   adb shell ovrgpuprofiler -m -v          # list metrics with descriptions
   adb shell ovrgpuprofiler -r<id>,<id>,<id>   # e.g. GPU % Bus Busy, % Stalled on System Memory,
                                               # % Texture L2 Miss, % Texture Fetch Stall
   ```
   Bandwidth-bound signs (Qualcomm healthy ranges, Adreno in general, A3-054):
   `% Stalled on System Memory` above ~2% sustained; `GPU % Bus Busy` above ~25% (the
   battery-conscious band); `% Texture L2 Miss` above 40%. Meanings and the other
   ranges: `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
2. **Tile trace for unwanted loads and stores** (A3-030, A3-031):
   ```sh
   adb shell ovrgpuprofiler -e com.company.app   # detailed mode, then restart the app
   adb shell ovrgpuprofiler -t -v                 # surface lines with per-stage times
   adb shell ovrgpuprofiler -d                    # turn detailed mode off afterwards
   ```
   A healthy eye-buffer surface shows `StoreColor` (the resolve) and no `LoadColor`,
   `LoadDepthStencil` or `StoreDepthStencil` (A3-007 notes). Detailed mode costs about
   10% GPU; never leave it on for a power or thermal run (A3-029).
3. **Bytes per draw** with RenderDoc Meta Fork draw-call metrics (A3-036, A3-044):
   ```sh
   renderdoccmd adb-list
   renderdoccmd adb-launch-drawcall-profiling --device <SERIAL> --package com.company.app
   renderdoccmd adb-capture --device <SERIAL> --ident <IDENT> --frames 1
   ```
   Sum `Write Total (Bytes)` over the draws of the eye-buffer pass and compare it with
   the derived store for your eye texture (table below). Several times the derived
   figure means stored MSAA samples or depth (A3-037, [verify on device]: store traffic
   may be charged to the last draw of a bin, or to none). Capture byte counters in a
   separate run from timing; Qualcomm marks them "Slow To Trace" (A3-055).
4. **Live bandwidth graph.** MQDH Performance Analyzer > GPU Memory Access module
   (A3-047). Units, sampling rate and counter are undocumented; calibrate once against
   RenderDoc Read/Write Total [verify on device].
5. **Memory clock and power** (A3-053, A3-082, quest.md Q1-005):
   ```sh
   adb logcat -s VrApi,XrPerformanceManager      # per-second line: Mem=<MHz>, PLS=, CPU/GPU levels
   adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver \
     -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV
   ```
   CSV columns: `mem_frequency_MHz`, `power_wattage`, `power_current`, `power_voltage`,
   `battery_level_percentage`, `battery_current_now_milliamps`, `power_level_state`.
   Pull from `/sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/`
   and summarise with `python ovr_metrics_csv.py <csv> --hz 72 --window-min 5` (script
   owned by `quest-perf:quest-profiling-toolkit`); it reports first-vs-last-window
   `power_wattage` and `mem_frequency_MHz`. Filter `9999` placeholders (Q1-017).
6. **Derive your own budget** from the live eye texture. Paste-ready probe (Unity 2021.3
   to 6.x, OpenXR or Oculus XR plugin, Vulkan or GLES; untested on device):
   ```csharp
   using System.Collections;
   using System.Collections.Generic;
   using UnityEngine;
   using UnityEngine.XR;

   public class EyeBufferTrafficProbe : MonoBehaviour
   {
       [Tooltip("Bytes stored to DRAM per eye-buffer pixel: 4 = resolved RGBA8 only, " +
                "8 = plus D24S8 depth store (or FP16 colour), 32 = 4x MSAA colour+depth samples.")]
       public int storedBytesPerPixel = 4;

       IEnumerator Start()
       {
           yield return new WaitForSeconds(3f); // let the XR display start
           var displays = new List<XRDisplaySubsystem>();
   #if UNITY_2023_1_OR_NEWER
           SubsystemManager.GetSubsystems(displays);
   #else
           SubsystemManager.GetInstances(displays);
   #endif
           float hz = 0f;
           foreach (var d in displays)
               if (d.running && d.TryGetDisplayRefreshRate(out hz) && hz > 0f) break;
           // Dynamic resolution scales the viewport, not the allocation (A3-086).
           float vs = XRSettings.renderViewportScale;
           double w = XRSettings.eyeTextureWidth * vs, h = XRSettings.eyeTextureHeight * vs;
           double mbPerFrame = w * h * 2.0 * storedBytesPerPixel / 1e6;
           double gbPerSec = mbPerFrame * hz / 1000.0;
           Debug.Log($"[BWProbe] eye={XRSettings.eyeTextureWidth}x{XRSettings.eyeTextureHeight} " +
                     $"viewportScale={vs:F2} hz={hz:F0} bpp={storedBytesPerPixel} -> " +
                     $"{mbPerFrame:F2} MB/frame, {gbPerSec:F2} GB/s, " +
                     $"~{gbPerSec * 0.10:F2}-{gbPerSec * 0.12:F2} W (2014 Arm rule, order of magnitude)");
       }
   }
   ```
   Read with `adb logcat -s Unity | grep BWProbe`. It ignores UBWC, which lowers real
   bytes by an unpublished ratio (A3-013).

## Key numbers

"Derived" = arithmetic on cited inputs (MB = 10^6 B). Per-device, per-Hz and per-format
tables, the Quest 2 and panel-resolution rows, and the watt conversions:
read [references/traffic-budgets.md](references/traffic-budgets.md) before quoting any
GB/s figure for a device or refresh rate not listed here. Battery, measured power per
scenario and the energy sources: read
[references/power-figures.md](references/power-figures.md) before quoting any watt figure.

| Quantity | Value | Applies to | Source / tag |
|---|---|---|---|
| DRAM vs on-chip energy | DRAM ~1-2 nJ/access, ~10-20 pJ/bit I/O; on-chip ~10-20 pJ; ~100x ratio | all SoCs (45 nm figures; ratio is the durable part) | A3-001 [doc] |
| DRAM traffic power | ~120 mW per GB/s (2014); ~100 mW per GB/s variant unread | Mali-era rule, order of magnitude only | A3-002 [doc]; ARM-C22 conflict |
| Default eye buffer per eye | 1440x1584 (Quest 2); 1680x1760 (Quest 3 and 3S) | render scale 1.0 | ARM-GF2-004 [doc] |
| Resolved RGBA8 store, both eyes | 23.65 MB/frame: 1.70 / 2.13 / 2.84 GB/s at 72 / 90 / 120 Hz | `Quest 3/3S` default | A3-009 [doc], derived |
| Same, Quest 2 default | 18.25 MB/frame: 1.31 / 1.64 / 2.19 GB/s | `Quest 2` default | ARM-GF2-004 inputs, derived |
| Same, Quest 3 at panel res 2064x2208 | 36.46 MB/frame: 2.62 / 3.28 / 4.38 GB/s | `Quest 3`, only if you raise the eye-texture scale | A3-010 [doc], derived |
| + D24S8 depth store | doubles the resolved figure (8 B/px) | all | A3-011, derived |
| 4x MSAA colour+depth samples stored | 32 B/px: ~189 MB/frame, ~13.6 GB/s at 72 Hz, ~1.6 W vs ~0.2 W | `Quest 3/3S` default | A3-011, derived [verify on device] |
| Extra full-screen pass (store + read) | RGBA8 ~47 MB/frame, ~3.4 GB/s at 72 Hz; FP16 ~6.8 GB/s | `Quest 3/3S` default | A3-012, derived [verify on device] |
| Bad load/store example | 10.62 ms surface; LoadColor 0.71, StoreColor 1.525, LoadDS 0.828, StoreDS 0.871 ms = ~3.9 ms of GMEM-DRAM traffic | older Quest, 1216x1344 MSAA 2x | A3-007 [doc] |
| Qualcomm healthy ranges | Stalled on System Memory < ~2%; Bus Busy ≤ ~25% battery-conscious, ≤ ~90% max-perf | Adreno in general | A3-054 [doc] |
| Quest 3 battery / average draw | 19.44 Wh / ~2 h = ~9.7 W whole headset (18.9 Wh in a later article = ~9.5 W) | `Quest 3` | ARM-GF1-002 [community]; ARM-C25 |
| Quest 3S battery / average draw | 16.74 Wh (leaked label) / ~2.5 h = ~6.7 W whole headset | `Quest 3S` | ARM-GF2-001 [community] |
| Quest 2 battery | 14 Wh; battery life not in the dossier, so no derived draw | `Quest 2` | ARM-GF1-002 [community] |
| Measured Quest 3 power | VR game 7.5-9.0 W; MR game 10.5-12.0 W; VR browse 7.6-8.2 W; MR browse 9.6-10.2 W | `Quest 3`, 120 Hz, OS v57 | ARM-GF2-002 [measured] [verify on device] |
| Mobile GPU class | "typically" 3-6 W, generic, not a Quest rating | phones and Quest | ARM-GF1-006 [doc] |
| Clocks all the way down | only ~25% less power for the same work | Quest 1/2 era, deprecated 2022 page | A3-094 [doc], stale |
| TDP / thermal envelope | not published for any Quest; measure (Fix 8) | all Quest | dossier section 1.7 |
| Peak DRAM bandwidth | not published; 34.13 GB/s theoretical for the SD865 controller (Quest 2); Quest 3/3S candidates conflict | all Quest | A1-008 [community]; ARM-C2 |
| `Mem=` examples | 2092 MHz and 1804 MHz on the same Meta page, no headset named | all Quest | ARM-GF1-004 [doc]; ARM-C24 |

Formula for any render target: `bytes/frame = W × H × views × bytes-per-pixel stored`;
an extra pass that is stored then sampled costs about 2x that; `GB/s = bytes/frame × Hz`;
`W ~ GB/s × 0.1` as an order of magnitude only.

## Fixes, ranked by payoff ÷ effort

Each fix states bytes, not milliseconds: the ms effect depends on whether the frame is
bandwidth-bound, so measure it. The watt effect is the reason the fixes matter for
**Consistency** even when frame rate is already met: fewer bytes means less heat and a
later or no throttle. Mechanics are owned elsewhere and linked.

### 1. Stop storing depth and MSAA samples to DRAM
`Throughput` `Consistency` `Quest 2` `Quest 3/3S` `Unity 2021.3-6.x` `URP 12+` `Vulkan` `GLES`
- Store only the resolved colour of the eye buffer. Depth and MSAA attachments: store op
  DONT_CARE; resolve MSAA in the tile store path (`pResolveAttachment`), never store
  samples (A3-006). Payoff: from 8x to 1x the resolved-colour store, about 13.6 to
  1.7 GB/s at 72 Hz on the Quest 3/3S default, on the order of 1.6 W to 0.2 W (A3-011).
  A depth store alone doubles the store (A3-011).
- In URP, anything that samples camera depth or the opaque texture after the pass forces a
  store (A3-006 notes): which settings do this, `unity-perf:unity-urp-settings`; how to
  keep a Render Graph pass on-tile, `unity-perf:unity-render-graph-tiling`; GLES
  invalidate/clear, `gles3-perf:gles-tile-load-store`.
- Effect: lower average GPU time when the Load*/Store* stages were visible (Meta's
  example spent ~3.9 ms of 10.62 ms on them, A3-007); lower sustained power, so less
  thermal decay. Quality cost: none, unless a later pass really needs depth.
- Verify with summed `Write Total` falling toward the derived resolved-colour figure.

### 2. Remove or merge full-screen passes; count each one as ~3.4 GB/s
`Throughput` `Consistency` `Quest 2` `Quest 3/3S` `Unity 2021.3-6.x` `URP 12+` `Vulkan` `GLES`
- Each full-screen pass stores the whole target and the next pass reads it back, even
  when its shader is trivial (A3-008). At the Quest 3/3S default that is ~47 MB/frame,
  ~3.4 GB/s at 72 Hz and ~5.7 GB/s at 120 Hz for RGBA8 (A3-012, derived).
- Meta lists blur, bloom, HDR, realtime shadows and deferred as extra-pass costs on
  Quest 3 (ARM-GF2-003), and "heavy shaders plus high-resolution post-processing" as a
  thermal-pressure pattern (A3-079).
- Which post effects to keep and how to fuse them on-tile:
  `unity-perf:unity-render-graph-tiling`. This skill only supplies the bytes.
- Effect: average GPU time and power both drop per pass removed. Quality cost: the effect
  itself. Side effect: none on pacing.

### 3. Halve bytes per pixel on every intermediate you keep
`Throughput` `Consistency` `Quest 2` `Quest 3/3S` `Unity 2021.3-6.x` `URP 12+` `Vulkan` `GLES`
- An FP16 (8 B/px) intermediate doubles the store and read of an RGBA8 (4 B/px) one:
  ~6.8 vs ~3.4 GB/s per pass at 72 Hz on the Quest 3/3S default (A3-012). A 32-bit HDR
  format (R11G11B10) has the RGBA8 footprint; its per-bin effect and UBWC support are in
  `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Wider formats also shrink bins, adding per-bin overhead (A3-005).
- URP HDR toggle and colour-format settings: `unity-perf:unity-urp-settings`.
- Effect: lower average GPU time only when the pass is bandwidth-bound (measure); lower
  sustained power, so less thermal decay (Consistency); no direct effect on frame-time
  variance. Quality cost: banding or clamped highlights, check on device.

### 4. Keep UBWC on hot render targets
`Throughput` `Consistency` `Quest 2` `Quest 3/3S` `Unity 2021.3-6.x` `URP 12+` `Vulkan`
- UBWC is lossless compression that lowers bytes moved and saves power (A3-013). Qualcomm
  lists compute-shader access, `VK_IMAGE_TILING_LINEAR`, any CPU readback (in Unity
  terms, likely `ReadPixels` / `AsyncGPUReadback`, [verify on device]),
  `VK_KHR_fragment_shading_rate`, FDM, `ALIAS`, `MUTABLE_FORMAT` and sparse binding as
  "almost certainly" disabling it (A3-014). Keep read-back and compute-written RenderTextures separate from the eye
  buffer and post chain.
- No compression ratio is published: no published number; measure with RenderDoc
  `Write Total` for the same content in an optimal-tiled vs a `MUTABLE_FORMAT`/linear
  target. Whether FFR eye buffers (FDM) keep UBWC is unresolved (ARM-C13); compute
  writes vs UBWC on the Quest driver also conflict (ARM-C14). Format tables:
  `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Effect: fewer DRAM bytes, so lower average GPU time when bandwidth-bound and lower
  sustained power (Consistency); no variance effect. Quality cost: none, since the
  compression is lossless; the side effect is giving up compute or readback on that
  target.

### 5. Cut texture and vertex bytes where the counters point
`Throughput` `Quest 2` `Quest 3/3S` `all Unity` `Vulkan` `GLES`
- Qualcomm names cache misses as the usual route into a bandwidth limit: many primitives,
  or shaders touching scattered texture locations (A3-016). Levers: block-compressed
  formats (ASTC), mipmaps, cheaper filtering (A3-015, A3-017); interleaved position-first
  vertex streams, packed attributes, 16-bit indices (A3-018).
- Owners: ASTC and mips `unity-perf:unity-memory-assets`; filtering cost
  `arm-mobile-hw-perf:xr2-shader-cost-model`; binning-pass vertex cost
  `arm-mobile-hw-perf:xr2-adreno-architecture`.
- Rank materials by RenderDoc `Texture Memory Read BW` and `Avg Bytes / Fragment` (Meta
  calls the latter imprecise; use it to rank, not as an absolute, A3-038).
- Effect: lower average GPU time on draws with high `% Texture Fetch Stall` / L2 miss;
  fewer bytes also lowers power. No variance effect. Quality cost: ASTC block artefacts,
  blur from mips or filtering, and loss of normal precision when packing; check on device.

### 6. Treat pixels × Hz as the bandwidth dial
`Throughput` `Consistency` `Quest 2` `Quest 3/3S` `all Unity`
- Every store and full-screen pass scales linearly with stored pixels and refresh rate:
  120 Hz costs 1.67x the bytes per second of 72 Hz for the same frame (A3-009, derived).
  Raising Quest 3 to panel resolution costs 1.54x the default store (36.46 vs 23.65 MB,
  A3-010, derived).
- FFR changes the shaded area, not the stored size (A3-009 notes): it does not cut the
  eye-buffer store bytes. Dynamic resolution scales the viewport, so bandwidth follows
  the viewport while memory stays at the maximum allocation (A3-086).
- Render scale, FFR and dynamic resolution setup: `quest-perf:quest-resolution-foveation`;
  refresh-rate choice: `quest-perf:quest-frame-pacing`.
- Effect: bandwidth and power scale linearly with pixels × Hz, so lower average GPU time
  when bandwidth-bound. Dynamic resolution also absorbs thermal events, which helps
  Consistency. Quality cost: resolution and sharpness, or motion smoothness at lower Hz.
  Details are in the linked owners.

### 7. Spend less work, then request lower levels: power is zero-sum
`Consistency` `Quest 2` `Quest 3/3S` `all Unity`
- Meta: most Quest 3 battery power goes to the CPU and GPU; lower clock levels when they
  are not fully used (ARM-GF2-003). The deprecated 2022 page says lowering clocks all the
  way saves only ~25% power for the same work, so savings must come from doing less work
  (A3-094, stale, VrApi era).
- Order: remove bytes and passes first (Fixes 1-3), then let the governor or your level
  request drop. Level APIs and the design-to-L4 rule: `quest-perf:quest-levels-thermal`.
- Effect: lower sustained power and later throttling; no average-frame-time gain.
  Quality cost: none from requesting lower levels once the work fits. The side effect is
  less headroom for spikes, so check p99 frame time at the lower level.

### 8. Measure the power budget and the thermal envelope yourself
`Consistency` `Quest 2` `Quest 3/3S` `all Unity`
- Nothing is published: TDP, envelope, fan behaviour, drain vs level, DRAM energy on
  LPDDR5 (Known unknowns). Method:
  1. Unplugged, battery above 50%, room ~21 C, no ovrgpuprofiler detailed mode.
  2. Pin CPU/GPU levels (A3-051), fixed scene, OVR Metrics CSV on.
  3. 20-30 min per variant; log `power_wattage`, `power_current`, `power_voltage`,
     `battery_level_percentage`, `mem_frequency_MHz`, `power_level_state`.
  4. Sweep a synthetic count of full-screen store passes (0, 1, 2, 4) at fixed levels:
     the slope of watts per added GB/s is your device's DRAM energy figure
     (A3 known unknowns; noisy).
  5. Repeat after ≥ 20 min cool-down (A3-095). Unpinned soak and minute-to-first-throttle:
     `quest-perf:quest-levels-thermal`.
- Meta says to optimise battery against CPU/GPU levels, not `BAT C` / `POW C` (A3-082).
  Use the power columns for A/B trends only. Details:
  [references/power-figures.md](references/power-figures.md).

## Verify

- **Bytes (single-frame captures, 3 per variant):** summed `Write Total` of the eye-buffer
  pass moves toward the derived resolved-colour store (23.65 MB Quest 3/3S default,
  18.25 MB Quest 2 default) and ends at or below it (UBWC lowers it by an unpublished
  ratio). Removing a depth or sample store should cut it by roughly the table ratio
  (2x or 8x) [verify on device].
- **Tile trace:** `LoadColor`, `LoadDepthStencil`, `StoreDepthStencil` gone from the eye
  surface in `ovrgpuprofiler -t -v`; the count of full-screen surfaces equals the passes
  you intend.
- **Realtime counters (2-5 min steady scene, pinned levels):** `% Stalled on System
  Memory` toward ~2% and `GPU % Bus Busy` toward the ≤ ~25% band (A3-054); MQDH GPU
  Memory Access down by roughly the removed GB/s.
- **Power (20-30 min, unpinned for the soak, repeated after cool-down):** mean
  `power_wattage` lower in A/B; the expected size is delta GB/s × ~0.1 W as an order of
  magnitude, for example ~0.34-0.41 W per removed RGBA8 pass at 72 Hz on the Quest 3/3S
  default (A3-002, A3-012, derived) [verify on device]. No published expected delta.
- **Thermal:** first `power_level_state` change later or never, and last-5-min clocks
  equal to first-5-min (protocol and report: `quest-perf:quest-levels-thermal`).
- **Memory clock:** record `mem_frequency_MHz` / `Mem=` at each level and during a
  throttle; whether it scales is unknown (A3-053, ARM-C24).

## Pitfalls and myths

- **"0.1 W per GB/s is the Quest number."** It is a Mali-phone rule from 2014 (Arm's blog
  gives 120 mW; a 100 mW variant was seen only in search snippets). Order of magnitude
  only; no Quest figure exists (ARM-C22).
- **"MSAA costs bandwidth."** MSAA resolves on-chip with no extra DRAM traffic; Qualcomm
  calls 2x "likely to be practically free" (A3-020). The 8x cost comes only from storing
  samples. No 4x MSAA cost figure exists for Adreno 740.
- **"FFR cuts eye-buffer bandwidth."** It cuts shading, not the stored size (A3-009
  notes), and FDM may disable UBWC (ARM-C13, unresolved).
- **"Quest 3 has 68 GB/s" / "Quest 3S is LPDDR4X at 42 GB/s."** Uncited and internally
  inconsistent (4200 MT/s on 64 bits is 33.6 GB/s); iFixit finds LPDDR5 in the 3S. Do not
  budget from any peak figure (ARM-C2, A3-099).
- **"Mem=2092MHz is the Quest 2 memory clock."** Meta's page shows 2092 and 1804 MHz
  examples with no headset named (ARM-C24). Read it on your device.
- **"9.7 W is the Quest 3 TDP."** It is whole-headset average from rounded battery life:
  displays, cameras, radios included. It bounds SoC power from above (ARM-GF1-002).
- **"Quest 3S draws ~6.7 W, so its SoC is cooler or weaker."** Same SoC and level table;
  the gap is display, optics and a leaked-label battery figure (ARM-GF2-001). Measure
  sustained headroom per chassis.
- **"The 3-6 W GPU figure is the Quest GPU rating."** It is Meta's generic mobile-GPU class
  statement (ARM-GF1-006).
- **"Optimise battery current (BAT C)."** Meta says optimise against levels (A3-082);
  `battery_current_now_milliamps` has shipped as the `9999` placeholder (Q1-017).
- **"Measure power while charging."** Charging rows in the forum test were 12-20 W and
  include charge current (ARM-GF2-002 notes). Measure on battery.
- **"Lower clocks and you are done."** ~25% at best for the same work (A3-094, stale);
  bytes and passes are the controllable cost.
- **Measurement artefacts.** ovrgpuprofiler detailed mode adds ~10% GPU (A3-029); byte
  counters are "Slow To Trace" (A3-055); a GPU timer query placed before an invalidate
  forces the flush it was meant to measure (A3-023). The MR scenarios' +2-3 W
  (ARM-GF2-002) is launch-era OS v57 data: re-measure on your OS.

## Sources

All accessed 2026-09-24. IDs refer to research/arm-mobile-hw.md unless marked quest.md.

- https://gwern.net/doc/cs/hardware/2014-horowitz-2.pdf [doc] (A3-001)
- https://web.archive.org/web/20191215124148/https://community.arm.com/developer/tools-software/graphics/b/blog/posts/the-mali-gpu-an-abstract-machine-part-2---tile-based-rendering [doc] (A3-002, ARM-C22)
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc] (A3-005 to A3-008, A3-011, A3-012)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc] (A3-009, ARM-GF2-004, A3-051)
- https://developers.meta.com/horizon/essentials/compare-devices/ [doc] (A3-010, A3-098)
- https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ [doc] (ARM-GF1-006)
- https://developers.meta.com/horizon/blog/optimizing-for-success-meta-quest-3-gdc/ [doc] (ARM-GF2-003)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc] (A3-027 to A3-034)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc] (A3-031)
- https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ [doc] (A3-036 to A3-039)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-ai-tools/ [doc] (A3-044)
- https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ [doc] (A3-047)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc] (A3-048, A3-049, A3-093; quest.md Q1-005)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ [doc] (A3-048, A3-082)
- https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ [doc] (A3-053, A3-083, ARM-GF1-004)
- https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ [doc] (A3-051)
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc] (A3-052, A3-086)
- https://developers.meta.com/horizon/essentials/thermal/ [doc] (A3-079)
- https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/ [doc], deprecated 2022 (A3-094)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md [doc] (A3-013, A3-020)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md [doc] (A3-014 to A3-018, A3-026)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md [doc] (A3-054, A3-055, A3-095)
- https://www.uploadvr.com/quest-3-teardown-battery/ [community] (ARM-GF1-002)
- https://www.uploadvr.com/quest-3s-images-leak-reveal-battery-size-no-headphone-jack/ [community] (ARM-GF2-001, ARM-C25)
- https://web.archive.org/web/20250108162626/https://communityforums.atmeta.com/t5/Talk-VR/Quest-3-Power-Usage-Tests-and-Approximate-Battery-Life/td-p/1094433 [measured] (ARM-GF2-002)
- https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf [doc] (A1-012, ARM-C2)
- https://www.tweaktown.com/news/93872/microns-low-power-memory-optimized-for-snapdragon-xr2-gen-2-platform-vr-and-mixed-reality/index.html [community] (ARM-GF1-005, ARM-C2)
- https://www.ifixit.com/Guide/Meta+Quest+3+Chip+ID/165932 and https://www.ifixit.com/Guide/Meta+Quest+3S+Chip+ID/178132 [community] (A1-023, ARM-C2)
- https://en.wikipedia.org/wiki/List_of_Qualcomm_Snapdragon_systems_on_chips [community] (A1-008)
- https://en.wikipedia.org/wiki/Meta_Quest_3 and https://en.wikipedia.org/wiki/Meta_Quest_3S [community] (A3-099, ARM-C2)
- https://github.com/Raiduy/GAS-publication-figures/blob/main/Raw%20Data/Gym%20Class/com.IRLStudios.GymClass-20231015_201503.csv [measured] (quest.md Q1-017 placeholder values)
