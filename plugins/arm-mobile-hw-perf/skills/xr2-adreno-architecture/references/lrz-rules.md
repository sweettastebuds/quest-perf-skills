# LRZ, early-Z and Fast-Z rules

All sources accessed 2026-09-24. Qualcomm rules are [doc] from https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html and https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html. Mesa/Freedreno rules are [community] from https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html and describe the open Turnip driver; Quest ships Qualcomm's proprietary driver, so treat them as architecture, not exact driver policy. Unity mappings are inference; confirm each with the per-draw LRZ line. [verify on device]

## What LRZ is

- Low-resolution Z, built during the binning pass; rejects work at LRZ-block granularity before the full-resolution depth test in the rendering pass. Draw-order independent; the app cannot control it directly. Present since A5x (A2-029, Qualcomm).
- Buffer format Z16_UNORM, stores the farthest Z per block; unusable when late-Z is required; one buffer is valid for one depth-compare direction (A2-030, Mesa).
- Block size: **no published number**. Measure indirectly with the per-draw `Fragments Shaded` metric (A2-029).
- LRZ still runs in direct mode but gives much less benefit there (A2-036).

## Disable rules (Qualcomm)

| Severity | Trigger | Unity examples (inference) |
|---|---|---|
| Test + write off until next depth clear | depth-direction change, or depth func ALWAYS / NOT_EQUAL, **followed by a depth write** (A2-032) | `ZTest Always` + `ZWrite On` sky, "always on top" object; reversed-Z tricks mid-pass |
| Write off until next clear (test still on) | blending or logic ops; colour-masked or partial MRT writes; any stencil op; framebuffer fetch or advanced blending; reading a previous-subpass attachment, each **while writing depth** (A2-033) | blended material with `ZWrite On`; URP stencil effects or portal masks that write depth; `ColorMask 0` depth-writers mid-pass |
| Test + write off, this draw only | FS writes a UAV, depth or stencil (A2-034) | `SV_Depth` output, `RWTexture` writes in a fragment shader |
| Write off, this draw only | alpha-to-coverage, `discard`, sample-mask output (A2-034) | URP Alpha Clipping (`clip()`); URP 14+ Lit sets `AlphaToMask` on alpha-clipped opaques when MSAA > 1 (U3-061) |

Secondary command buffers disable LRZ only on GPUs older than Adreno 650: a non-issue on Quest (A2-036).

Community report: a Unity staff reply (2021.2-era Vulkan backend) says Graphics Jobs implicitly disables Adreno LRZ/HSR (U5-038, https://discussions.unity.com/threads/vulkan-bug-quest-2-urp-graphics-jobs-no-multithreaded-rendering-slow.1208908/ [community]). Status on 2022.3.35f1+ Legacy mode is unverified; A/B with the per-draw LRZ line.

## Direction tracking by generation (Mesa, A2-031)

| GPU | Behaviour |
|---|---|
| before A650 | direction tracked on CPU; a change disables LRZ for the rest of the pass |
| A650+ (Quest 2, Quest 3/3S) | GPU-side direction byte plus depth-view parameters let LRZ survive across render passes that use the same depth view |
| A7xx (Quest 3/3S) | adds bidirectional LRZ, off by default; two LRZ buffer sets so binning (BV) and rendering (BR) use LRZ at the same time (A2-027) |

LRZ feedback (A650+, Mesa, A2-035): draws that write depth but cannot feed LRZ during binning (e.g. `discard`) can still update LRZ during the rendering pass; helps most when such draws come early. Not published for the Qualcomm driver.

## Early-Z and Fast-Z (Qualcomm)

- Early-Z rejects occluded pixels at up to 4x the normal fill rate. Disabled when the FS writes Z, uses `discard`, writes depth/stencil, or uses alpha-to-coverage (A2-038).
- No hidden-surface removal: sort opaque geometry front-to-back even with early-Z (A2-039).
- Fast-Z: a depth-only pass with an empty FS and colour writes disabled writes Z at twice the normal rate. For indirect draws declare `layout(early_fragment_tests) in;` (A2-040). A full depth prepass also doubles binning and vertex work; URP Depth Priming stays Disabled on Quest (U2-020, U3-058, G2-020).
- Discard: if only some pixels of a thread are killed, the shader still runs for the whole thread; put discard draws after all opaque draws (A2-041).
- A2C and `clip()` both lose LRZ write; discard also loses early-Z. With MSAA prefer A2C over `clip()` only after measuring (G2-046, https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]).

## Recommended draw order in URP

1. Opaque, queue 2000, front-to-back (URP default sorting). Nothing that writes depth with blend/stencil/colour-mask here.
2. Alpha-tested, queue 2450 (URP's BaseShaderGUI assigns alpha-clipped materials here; U3-060/U3-061).
3. Sky/background with `ZWrite Off`, `ZTest LEqual`.
4. Transparents with `ZWrite Off`.

Shader-side work for alpha-tested foliage (per-material depth prepass with ZTest Equal, U3-062) is owned by `unity-perf:unity-shader-authoring`.

## Finding the killer

```sh
adb shell ovrgpuprofiler -e <package>          # then restart the app
adb shell ovrgpuprofiler -x -m                 # list per-draw metric ids
adb shell ovrgpuprofiler -t3 -x="<ids>"        # per-draw trace; prints LRZ State per draw
```
Output per draw: `LRZ State: TestEnabled, WriteEnabled <0x03>`, `Disabled`, or `Unknown(old driver?)` (A2-037, Q1-073, https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]). `-s` is ignored when `-x` is present; the SoC counter budget can reject metrics, so split long lists across runs. Per-draw timings compare draws within one trace only.
