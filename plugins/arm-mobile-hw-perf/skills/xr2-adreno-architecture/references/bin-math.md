# Bin math on Adreno 650 / 740

All sources accessed 2026-09-24. Applies to any Unity/URP version and both APIs unless tagged. Arithmetic marked "derived" is computed here from the cited numbers; confirm every prediction with the `N WxH bins` field of `adb shell ovrgpuprofiler -t -v` or RenderDoc Meta Fork Surface Information. [verify on device]

## The rule

Meta (A2-013, https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]):

    bytes per pixel = (colour bytes + depth/stencil bytes) × MSAA samples   (× 2 when both multiview views share a bin)
    bin size        = the largest bin whose bytes fit the GMEM budget (chosen by the driver)
    bin count       ≈ ceil(width / bin_w) × ceil(height / bin_h)

Usable GMEM is less than raw GMEM: Mesa reserves a CCU fraction in GMEM mode, a quarter on a6xx and an eighth on a7xx (A2-012, https://docs.mesa3d.org/drivers/freedreno.html [community]). Not confirmed for the Qualcomm driver Quest ships.

Do not predict bin **dimensions** from Mesa's 96-pixel alignment: Qualcomm-driver examples show 128x224 and 320x192 (A2-016). Predict only the **ratio** of bin counts, then read the real layout.

## Bytes per pixel per view (A2-014, derived from Meta's rule)

| Configuration | B/px/view | Bin count vs baseline |
|---|---|---|
| 4x MSAA, RGBA8 / R11G11B10F / RGB10A2 colour, D24S8 or D32F depth | (4+4)×4 = 32 | baseline |
| 4x MSAA, RGBA16F colour | (8+4)×4 = 48 | about 1.5x |
| 4x MSAA, 32-bit colour, D16 depth | (4+2)×4 = 24 | about 0.75x (derived; D16 per A2-045) |
| 2x MSAA, 32-bit colour, 32-bit depth | 16 | about half |
| No MSAA, 32-bit colour, 32-bit depth | 8 | about a quarter |
| Each extra 32-bit MRT at 4x | +16 | more bins |

URP HDR in R11G11B10F costs no bins over LDR RGBA8; HDR in RGBA16F does (A2-014 notes). The URP HDR precision setting is owned by `unity-perf:unity-urp-settings`.

## Worked examples

| Case | Numbers | Source |
|---|---|---|
| Quest 2 default, 4x, RGBA8 + D24S8, multiview | 96x176 bins; 96×176×2×32 B = 1,081,344 B ≈ 1.03 MiB; 1440/96 = 15, 1584/176 = 9 -> 135 bins | A2-013, ARM-GF1-006 [doc] `Quest 2` |
| Meta profiler example, 1216x1344, 32-bit colour, 24-bit depth, 4x | 60 bins of 128x224; 128×224×32×2 ≈ 1.75 MiB, which only fits ~2 MB GMEM, so likely Quest 3. At 128x224, 1680x1760 -> 14×8 = 112 bins (derived) | A2-015 [doc] `Quest 3/3S` (inferred) |
| Unity 6 eye buffer, Quest 3, 4x | 63 bins of 192x256 (UUM-149765). Derived: 1680/192 -> 9, 1760/256 -> 7, 9×7 = 63; 192×256×32×2 = 3,145,728 B = 3 MiB, or 1.5 MiB if views are not doubled | G2-039 [measured] `Quest 3/3S` `Unity 6000.x` |
| Old bad-config example, 1216x1344, 2x MSAA | 28 bins of 320x192 | A2-054 [doc] original-Quest era |
| Direct mode | `1 1216x1344 bins`: one bin covering the surface | A2-022 [doc] |

The last two Quest 3 rows disagree on usable GMEM (about 1.75 MiB vs 3 MiB if both views are doubled). This is conflict ARM-C9 (Meta "approximately 2MB" vs kernel 3 MiB for the SD8 Gen 2 sibling). Resolve it on your device: note the colour/depth format and MSAA from Surface Information, read the bin size, and compute bytes per bin both with and without the ×2 view factor.

## GMEM sizes

| GPU | Meta | Other | Assessment |
|---|---|---|---|
| Adreno 650 (Quest 2) | 1 MB (A2-010) | kernel `SZ_1M + SZ_128K` = 1.125 MiB (A2-011) | 1 MB is rounded (ARM-C10) |
| Adreno 740v3 (Quest 3/3S) | "approximately 2MB" (A2-010) | kernel 3 MiB for chip 0x43050a01, Quest chip 0x43050b00 not listed (A2-011); Chips and Cheese 3 MB on X1-85 (A2-006) | unresolved (ARM-C9) |
| Quest Pro, Meta VR Glasses | not stated (A3-004, A3-025) | | read bin sizes |

Eye buffers never fit: 1440x1584 RGB8 ≈ 6.52 MB, 1680x1760 ≈ 8.46 MB, on-GPU memory of at most ~5 MB (A2-020, https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ [doc]).

## Why bin count matters twice

1. **Per-bin fixed cost:** binning, load/store setup and per-bin query cost (2-5 µs per bin per timer query, A2-060).
2. **Vertex cost:** each vertex is shaded at least twice per frame and up to 2 × bins + 1 times (A2-047, https://developers.meta.com/horizon/documentation/unity/gpu-impaired-algorithms/ [doc]). A triangle is rasterised in every bin it touches (A2-018; ARM-C11 records Meta's "can be split" wording). Growing bytes per pixel grows vertex work.

Qualcomm's levers to cut bin count: lower resolution, VRS/foveation, fewer MSAA samples, fewer MRTs (A2-017, https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]).

## Measuring usable GMEM yourself

1. Pin levels: `adb shell setprop debug.oculus.gpuLevel 4` (Q1-079).
2. `adb shell ovrgpuprofiler -e <package>`, restart the app, `adb shell ovrgpuprofiler -t -v`.
3. For the eye-buffer surface, note colour bits, depth bits, stencil bits, MSAA and `N WxH bins`.
4. bytes per bin = W × H × (colour B + depth/stencil B) × samples × (2 if views share the bin).
5. Repeat at a second MSAA level. The largest product across configurations bounds usable GMEM from below.
