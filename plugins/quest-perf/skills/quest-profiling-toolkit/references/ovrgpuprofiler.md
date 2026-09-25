# ovrgpuprofiler: commands and surface-line reading

Applies to: Quest 2, Quest 3/3S; GLES and Vulkan. Source for everything below
unless noted: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/
(page updated 2026-09-09, accessed 2026-09-24) [doc]. Counter meanings and
healthy ranges live in `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.

The binary ships with the OS; a community skill puts it at
`/system_ext/bin/ovrgpuprofiler` (Q1-065, [community]).

## Commands

| Goal | Command | Notes | ID |
|---|---|---|---|
| List real-time metrics | `adb shell ovrgpuprofiler -m` (`-m -v` for descriptions) | IDs are list positions; they vary by device and runtime. Resolve names on the target device every time | Q1-065, A3-027 |
| Real-time sampling | `adb shell ovrgpuprofiler -r4`, `-r"4,5,6"`, `--realtime="4,6"` | once per second; at most 30 metrics | Q1-066, A3-029 |
| Detailed mode on | `adb shell ovrgpuprofiler -e [package]` | applies to apps started afterwards: restart the app. Costs about 10% of GPU render time | Q1-067, A3-029 |
| Detailed mode state / off | `-i` / `-d` | always `-d` when done | Q1-067 |
| Render-stage trace | `-t` (100 ms default), `-t1.2` (seconds), `-c` continuous until Ctrl-C | needs detailed mode | Q1-068 |
| Low-overhead trace | `-t2 -l` | one line per surface, more accurate timings | Q1-068 |
| Per-bin / per-stage detail | `-t -v` | only for bin or stage costs | Q1-068 |
| Per-stage counters | list `-m -t`; capture `-t3 -s "1,2,3"` | `-s` requires `-t`; ignored with `-x`; SoC counter budget can reject some ("Captured 2 metrics, 1 rejected by SoC counter budget"); re-queue rejected ones in another run | Q1-072, A3-032 |
| Per-draw counters | list `-x -m`; capture `-t3 -x="1,2,3,..."` | prints `LRZ State: TestEnabled, WriteEnabled <0x03>`, `Disabled` or `Unknown(old driver?)`; per-draw timing adds stalls, compare draws within one trace only | Q1-073, A3-032 |

Scripted wrapper: `quest_adb.py gpu-metrics`, `gpu-realtime --ids`,
`gpu-trace --enable|--disable|--seconds N --low-overhead`.

Metric counts differ by source (conflict Q1-C8): Meta's example lists 47; an
arXiv paper read 72 (78 on Quest 3S) at 1 Hz (Q1-076, [community]); a 2026
community skill reports 81 on Quest 3. Consistent with "IDs vary"; never
hard-code IDs.

## Surface line format (Q1-069, verbatim)

```
Surface 1 | 1216x1344 | color 32bit, depth 24bit, stencil 0 bit, MSAA 4, Mode: 1 (HwBinning) | 60 128x224 bins ( 60 rendered) | 5.08 ms | 130 stages : Binning : 0.623ms Render : 1.877ms StoreColor : 0.309ms Blit : 0.002ms Preempt : 1.286ms
```

- Mode: 0 Direct, 1 HwBinning, 2 SwBinning, 3 HwDirect (Q1-069, A3-033). An
  eye-buffer surface in direct mode loses FFR (A3-033 note; mechanism in
  `arm-mobile-hw-perf:xr2-adreno-architecture`).
- Compute prints `Compute N | ... | x ms`.
- Bin lines: `Bin 0 | topLeft 0 x0 | 1x1 logical bins | Fov 8/8`, or
  `Fov L<x>/<y> R<x>/<y>` for multiview.
- Stage names (Q1-070): Binning, Render, LoadColor, StoreColor,
  LoadDepthStencil, StoreDepthStencil, Blit, Preempt, Load/Store,
  Dispatch/GLAsyncCompute, VKQueue, VKRenderClear, VKLoadInput, Workload,
  RayTracingBuild/Update/Copy, Unknown.
- Preempt is compositor preemption, not app work (A3-031). Meta's example
  spends 1.286 ms of 5.08 ms in Preempt; no published guidance on whether to
  subtract it when budgeting (Q1-070).

## Reading rule for the eye-buffer surface (G2-009, gles3.md)

Meta's GLES example (https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/, [doc]):

```
Surface 1 | 1216x1344 | color 32bit, depth 24bit, stencil 8 bit, MSAA 2 | 28 320x192 bins | 10.62 ms | 171 stages : Binning : 0.305ms LoadColor : 0.71ms Render : 2.926ms StoreColor : 1.525ms Preempt : 2.964ms LoadDepthStencil : 0.828ms StoreDepthStencil : 0.871ms
```

- Rule: on the main eye-buffer surface, any non-zero Load* stage, or any
  StoreDepthStencil stage, is a missing clear or invalidate.
- Meta attributes "1.5ms" of waste to LoadColor + StoreDepthStencil
  (0.71 + 0.871 ms). Counting LoadDepthStencil too gives about 2.4 ms of
  10.62 ms; that total is the gles3 dossier's arithmetic, not Meta's.
- Fix owners: URP/Render Graph `unity-perf:unity-render-graph-tiling`; GLES
  calls `gles3-perf:gles-tile-load-store`.

Also check format, MSAA and mode against what URP should allocate. An extra
surface at eye resolution is the classic sign of an intermediate texture
(Q1-069 note).

## Multiview: do not double count (Q1-071, A3-034, conflict Q1-C11)

| Device | Output |
|---|---|
| Original Quest | one surface per eye: add them |
| Quest 2 (Adreno 650) | one surface for both views, shared bins shown as `135 96x176x2 bins` (read as 135 x 2) |
| Quest 3 / 3S (Adreno 740) | one surface line covering both views |

The page's general sentence ("one line per slice, add both eye surfaces")
conflicts with its device-specific lines; follow the device-specific lines.
The same page gives Quest 3 at 690 MHz and Quest 3S at 492 MHz, which conflicts
with the levels table (ARM-C3); read clocks on device.

## Counters to read first (Q1-074, derivations [community])

- Which stage owns the frame: % Time Shading Fragments vs % Time Shading
  Vertices.
- Stalled or computing: % Shaders Busy high with % Shader ALU Capacity
  Utilized low means stalled shaders.
- Stall source: % Texture Fetch Stall, % Texture L1 Miss vs % Texture L2 Miss,
  % Vertex Fetch Stall, % Stalled on System Memory, GPU % Bus Busy.
- Work volume: Vertices/Fragments Shaded per second ÷ FPS = per frame.
  Overdraw ≈ fragments per frame ÷ (2 × eye width × eye height).
  Stage ms ≈ App ms × % time shading ÷ 100.
- Measured example (Q1-075, [measured], Functor engine not Unity, Quest 3,
  72 Hz): 8x anisotropic on every mipmapped texture cost 8.9 ms of a 13.8 ms
  frame; it showed as texture fetch stall and texture-pipes-busy. Method
  transfers: A/B aniso 1 and watch `percent_texture_anisotropic_filtered`.

Real-time counters should be stable on a steady scene; if not, the scene has
not settled (Q1-066 note).
