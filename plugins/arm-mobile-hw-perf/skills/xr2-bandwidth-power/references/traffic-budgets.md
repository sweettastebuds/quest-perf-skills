# Derived DRAM traffic budgets per device, refresh rate and format

All figures are **derived**: arithmetic on the eye-texture sizes Meta documents
(ARM-GF2-004, https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/,
[doc]) and panel sizes (A1-025, https://developers.meta.com/horizon/essentials/compare-devices/,
[doc]), accessed 2026-09-24. MB = 10^6 bytes, GB/s = 10^9 bytes/s. They apply to Unity
2021.3 / 2022.3 / 6000.x, URP 12 / 14 / 17+, Vulkan and GLES alike: the bytes are set by
the attachments, not by the engine.

What the figures do not include [verify on device]:
- UBWC compression, which lowers real bytes by an unpublished ratio (A3-013).
- Texture-cache hits on the read side of a full-screen pass (A3-012 notes).
- Binning-pass visibility-stream writes and vertex fetch (A3-003, A3-018).
- Compositor work (TimeWarp reads the eye buffer again; not an app cost).

Which refresh rates each headset offers is not decided here; the Hz columns are
arithmetic. Refresh-rate choice: `quest-perf:quest-frame-pacing`.

## Formula

```
stored bytes/frame   = W × H × 2 views × B        (B = bytes per pixel stored to DRAM)
full-screen pass     ~ 2 × W × H × 2 × B          (store, then sample it back)
GB/s                 = bytes/frame × Hz / 1e9
watts (order of mag) ~ GB/s × 0.10 to 0.12        (Arm 2014 rule, A3-002; ARM-C22)
```

Bytes per pixel stored (B):

| What is stored | B | Source |
|---|---|---|
| Resolved RGBA8 colour only (correct setup) | 4 | A3-009 |
| RGBA8 colour + D24S8 depth store, or FP16 colour only | 8 | A3-011, A3-012 |
| 2x MSAA colour + depth samples stored | 16 | A2-013 rule, derived |
| 4x MSAA colour + depth samples stored | 32 | A3-005, A3-011 |

## Eye-buffer store per frame and per second

| Eye texture (per eye) | B = 4 | B = 8 | B = 16 | B = 32 |
|---|---|---|---|---|
| Quest 2 default 1440x1584 | 18.25 MB | 36.50 MB | 72.99 MB | 145.98 MB |
| Quest 3/3S default 1680x1760 | 23.65 MB | 47.31 MB | 94.62 MB | 189.24 MB |
| Quest 3S at panel 1832x1920 | 28.14 MB | 56.28 MB | 112.56 MB | 225.12 MB |
| Quest 3 at panel 2064x2208 | 36.46 MB | 72.92 MB | 145.83 MB | 291.67 MB |

GB/s at 72 / 90 / 120 Hz:

| Eye texture | B = 4 | B = 8 | B = 16 | B = 32 |
|---|---|---|---|---|
| Quest 2 default | 1.31 / 1.64 / 2.19 | 2.63 / 3.28 / 4.38 | 5.26 / 6.57 / 8.76 | 10.51 / 13.14 / 17.52 |
| Quest 3/3S default | 1.70 / 2.13 / 2.84 | 3.41 / 4.26 / 5.68 | 6.81 / 8.52 / 11.35 | 13.62 / 17.03 / 22.71 |
| Quest 3S panel | 2.03 / 2.53 / 3.38 | 4.05 / 5.07 / 6.75 | 8.10 / 10.13 / 13.51 | 16.21 / 20.26 / 27.01 |
| Quest 3 panel | 2.62 / 3.28 / 4.38 | 5.25 / 6.56 / 8.75 | 10.50 / 13.13 / 17.50 | 21.00 / 26.25 / 35.00 |

The Quest 3/3S default rows reproduce A3-009 and A3-011 (23.65 MB, 1.70 / 2.13 /
2.84 GB/s; ~189 MB, ~13.6 GB/s at 72 Hz). The Quest 3 panel row reproduces A3-010
(36.46 MB; 2.62 / 3.28 / 4.38 GB/s). Panel rows apply only when an app raises the
eye-texture scale; the default workload is the same on Quest 3 and 3S (ARM-GF2-004).

Read the real size from the ovrgpuprofiler surface line, `debug.oculus.textureWidth` /
`debug.oculus.textureHeight`, or the CSV `eye_buffer_width` / `eye_buffer_height`, not
from this table (A3-010 notes, quest.md Q1-015).

## Extra full-screen pass (store + read-back)

| Eye texture | RGBA8 (4 B) MB/frame | GB/s 72 / 90 / 120 Hz | FP16 (8 B) GB/s 72 / 90 / 120 Hz |
|---|---|---|---|
| Quest 2 default | 36.50 | 2.63 / 3.28 / 4.38 | 5.26 / 6.57 / 8.76 |
| Quest 3/3S default | 47.31 | 3.41 / 4.26 / 5.68 | 6.81 / 8.52 / 11.35 |
| Quest 3S panel | 56.28 | 4.05 / 5.07 / 6.75 | 8.10 / 10.13 / 13.51 |
| Quest 3 panel | 72.92 | 5.25 / 6.56 / 8.75 | 10.50 / 13.13 / 17.50 |

The Quest 3/3S default row reproduces A3-012 (~47 MB, ~3.4 GB/s; FP16 ~6.8 GB/s at 72 Hz).
A pass at reduced resolution (half-res bloom chain) scales with its own W × H. Pass fusion
and on-tile post: `unity-perf:unity-render-graph-tiling`.

## Order-of-magnitude watts

Using 0.10-0.12 W per GB/s (A3-002, ARM-C22; Mali 2014, not a Quest measurement):

| Case (Quest 3/3S default, 72 Hz) | GB/s | ~W |
|---|---|---|
| Correct eye-buffer store (RGBA8 resolve) | 1.70 | 0.17-0.20 |
| + depth store | 3.41 | 0.34-0.41 |
| 4x MSAA samples + depth stored | 13.62 | 1.36-1.63 |
| One extra RGBA8 full-screen pass | 3.41 | 0.34-0.41 |
| One extra FP16 full-screen pass | 6.81 | 0.68-0.82 |

For scale only: 1.6 W is about one sixth of the ~9.7 W Quest 3 whole-headset average
(ARM-GF1-002, derived). [verify on device] with the power sweep in
[power-figures.md](power-figures.md).

## Time-domain view: Meta's bad load/store example

A 1216x1344 MSAA 2x surface, 28 bins of 320x192, 10.62 ms total (A3-007 / A2-054,
https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/, [doc]):

| Stage | ms |
|---|---|
| LoadColor | 0.71 |
| StoreColor | 1.525 |
| LoadDepthStencil | 0.828 |
| StoreDepthStencil | 0.871 |
| All GMEM-DRAM traffic (derived sum) | ~3.93 (about 37%) |
| Avoidable part (LoadColor + LoadDS + StoreDS, derived) | 2.41 (about 23%) |

The example is from an older Quest; the stage names are current on all devices (A3-007).

## Checking a capture against the table

1. RenderDoc Meta Fork, draw-call profiling capture of one frame (A3-044).
2. Sum `Write Total (Bytes)` over the draws of the eye-buffer pass (A3-036, A3-037).
3. Compare with the B = 4 figure for the actual eye size:
   - at or below it: no unwanted stores (UBWC may put it well below);
   - about 2x: a depth store or an FP16 target;
   - about 4-8x: MSAA samples stored.
4. Store traffic may be charged to the last draw of a bin, or to no draw at all, so treat
   a low sum with care [verify on device] (A3-037 notes).
5. Cross-check in the tile trace: Load*/StoreDepthStencil stage times (A3-030, A3-031).

## Peak DRAM bandwidth: unpublished, conflicting

Do not divide these budgets by a peak figure until you have measured one.

| Claim | Figure | Status | Source |
|---|---|---|---|
| Quest 2, SD865-family controller, LPDDR4X 4x16-bit at 2133 MHz | 34.13 GB/s theoretical | Wikipedia, not Meta | A1-008 [community] |
| `Mem=2092MHz` x 2 x 8 B | ~33.5 GB/s | one of two Meta examples, no headset named | ARM-C24 |
| `Mem=1804MHz` x 2 x 8 B | ~28.9 GB/s | the other Meta example | ARM-C24 |
| XR2 Gen 2 "4x16 LP-DDR5 up to 3.2 GHz" read as 6400 MT/s x 64 bit | 51.2 GB/s | reading of "3.2 GHz" is an assumption | A1-023 notes, Qualcomm brief https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf [doc] (A1-012) |
| Micron LPDDR5X 8.533 Gbps "optimized for" XR2 Gen 2 | ~68.3 GB/s if Quest ran it | supplier platform claim | ARM-GF1-005, https://www.tweaktown.com/news/93872/microns-low-power-memory-optimized-for-snapdragon-xr2-gen-2-platform-vr-and-mixed-reality/index.html [community] |
| Wikipedia Quest 3 "LPDDR5 @ 4200 MT/s (68 GB/s)" | 4200 MT/s x 8 B = 33.6 GB/s | internally inconsistent | A3-099, ARM-C2 |
| Wikipedia Quest 3S "LPDDR4X @ 2600 MT/s (42 GB/s)" | n/a | contradicted by iFixit's LPDDR5 part | A3-099, ARM-C2 |

Known unknowns: the configured data rate on every Quest; Quest 3S vs Quest 3 bandwidth;
whether `Mem=` / MEM F scales with CPU/GPU level or thermal state (A3-053).

### Measuring an achievable ceiling (CPU-side copy probe)

A STREAM-style copy in Burst jobs at a pinned CPU level, logged next to `Mem=` (dossier
Known unknowns, A1 list). It measures what the CPU cluster can pull, not the GPU path, and
write-allocate may add hidden reads; treat it as a lower bound on the DRAM ceiling
[verify on device]. Run it in an empty scene; it hitches the frame while it runs.

Requires the Burst, Collections and Mathematics packages. Unity 2021.3 to 6.x; untested
on device.

```csharp
using System.Collections;
using System.Diagnostics;
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using Unity.Jobs.LowLevel.Unsafe;
using Unity.Mathematics;
using UnityEngine;
using Debug = UnityEngine.Debug;

public class DramCopyProbe : MonoBehaviour
{
    public int megabytesPerBuffer = 64;   // well above any cache level
    public int iterations = 20;

    [BurstCompile]
    struct CopyJob : IJobParallelFor
    {
        [ReadOnly] public NativeArray<float4> src;
        [WriteOnly] public NativeArray<float4> dst;
        public void Execute(int i) { dst[i] = src[i]; }
    }

    IEnumerator Start()
    {
        yield return new WaitForSeconds(5f);
        int count = megabytesPerBuffer * 1024 * 1024 / 16;
        var src = new NativeArray<float4>(count, Allocator.Persistent);
        var dst = new NativeArray<float4>(count, Allocator.Persistent,
                                          NativeArrayOptions.UninitializedMemory);
        var job = new CopyJob { src = src, dst = dst };
        job.Schedule(count, 16384).Complete();          // warm-up, page-in
        var sw = Stopwatch.StartNew();
        for (int k = 0; k < iterations; k++)
            job.Schedule(count, 16384).Complete();
        sw.Stop();
        double bytes = 2.0 * count * 16.0 * iterations; // read + write
        Debug.Log($"[DramCopyProbe] {bytes / sw.Elapsed.TotalSeconds / 1e9:F2} GB/s copy " +
                  $"(buffers {megabytesPerBuffer} MB, workers {JobsUtility.JobWorkerCount})");
        src.Dispose();
        dst.Dispose();
    }
}
```

Protocol: pin `debug.oculus.cpuLevel` to each level in turn (A3-051), run the probe, and
record `Mem=` from `adb logcat -s VrApi` at the same time. Repeat on Quest 2, Quest 3 and
Quest 3S with the same build. Report GB/s per level per device.
