# UBWC and attachment formats

All sources accessed 2026-09-24. Primary source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html, overview.html and spec_sheets.html (same bundle) [doc].

## What UBWC is

- Universal Bandwidth Compression: lossless, predictive; on every Adreno since A5x. Raises effective memory throughput and saves power. Images with `VK_IMAGE_TILING_OPTIMAL` generally get it; it also works across the display, video and camera blocks (A2-042, A3-013).
- Compression ratio: **no published number**. Measure (below).
- Snapdragon Profiler shows surfaces as "Optimal" vs "Linear" (A2-042), but SDP is treated as unsupported on Quest (see `arm-mobile-hw-perf:xr2-gpu-counters-sdp`).

## Features that "almost certainly" disable UBWC (A2-043, A3-014)

| Feature | Unity situation (inference, [verify on device]) |
|---|---|
| compute-shader access | RTs written by compute (compute post chains, `enableRandomWrite`) |
| `VK_IMAGE_TILING_LINEAR` | not normally chosen by Unity for RTs |
| any CPU readback, incl. host image copy | `Texture2D.ReadPixels`, `AsyncGPUReadback` sources |
| `VK_KHR_fragment_shading_rate` | VRS |
| `VK_EXT_fragment_density_map` | Meta's Vulkan FFR (conflict ARM-C13) |
| `VK_IMAGE_CREATE_ALIAS_BIT` | aliased transient resources |
| `VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT` | possibly sRGB-capable RTs; unknown whether Unity sets it on Quest |
| sparse resources | not used by URP |

Avoid MUTABLE_FORMAT before Adreno 750, which covers both Quest GPUs (A2-045).

### Conflicts

- **ARM-C13, FDM vs UBWC.** Qualcomm lists `VK_EXT_fragment_density_map`; Meta's Vulkan FFR is a per-bin density effect. Whether FFR eye buffers lose UBWC is unpublished. Measure `Write Total (Bytes)` with FFR off vs high, normalised per stored pixel.
- **ARM-C14, compute writes vs UBWC.** Qualcomm: compute almost certainly disables UBWC. Mesa marks a7xx_gen2 (Quest 3's 740v3) `supports_uav_ubwc` under Turnip [community]. Quest's driver is unverified; assume loss.

## A6x UBWC by format (A2-044, spec sheet; Quest 2. Quest 3 likely similar, table not given)

| UBWC | Formats |
|---|---|
| Yes | R5G6B5, RGBA8, RGB10A2, R11G11B10F, RG16F, R32F |
| Yes, to 8x MSAA | RGBA16F |
| Yes, to 4x MSAA | RGBA32F |
| Yes (depth) | D24 variants |
| No | R8_UNORM, R9G9B9E5, ASTC, ETC2 |

Mesa agrees the A650 lacks 8-bpp UBWC. RG8 is not listed. Single-channel R8 render targets (SSAO or mask buffers) are uncompressed on Quest 2.

## Format priorities (A2-045)

- Colour: R10G10B10A2 first (the hardware is optimised for it), then R11G11B10, then RGBA16.
- Depth: D16 when precise enough (e.g. with tuned reverse-Z), then D24S8 if stencil is needed, then D32. UBWC supports all of these depth formats.
- D16 halves depth bytes per pixel, which also allows larger bins ([bin-math.md](bin-math.md)).

## Measuring UBWC loss on Quest

No Meta tool shows per-surface UBWC status. Method (A3 gaps, built from documented metrics):
1. RenderDoc Meta Fork, draw-call profiling (`renderdoccmd adb-list`, then `renderdoccmd adb-launch-drawcall-profiling --device <SERIAL> --package <pkg>`, then `renderdoccmd adb-capture --device <SERIAL> --ident <IDENT> --frames 1`; A3-044).
2. Sum `Write Total (Bytes)` for the draws writing the target (A3-036).
3. Compare against the same content written to a target without the suspect feature (no readback alias, no compute write, no MUTABLE_FORMAT). A higher total for the suspect target at equal content indicates lost compression.
4. Store traffic may be charged to the last draw in a bin or to no draw (A3-037). Compare totals, not single draws.

DRAM bytes-per-frame and power arithmetic for the result: `arm-mobile-hw-perf:xr2-bandwidth-power`.
