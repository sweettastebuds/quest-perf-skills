# Device tiers: per-headset reference table

Read from `quest-budgets-tiers` SKILL.md when building a tier table, porting between
headsets, or checking a per-device fact. All sources accessed 2026-09-24. Finding IDs
refer to `research/quest.md`, `research/unity.md` and `research/arm-mobile-hw.md`.

## Per-device table

| Fact | Quest 2 | Quest 3 | Quest 3S | Source |
|---|---|---|---|---|
| SoC | Snapdragon XR2 (Gen 1) | XR2 Gen 2 | XR2 Gen 2 | Q2-001, Q2-003 [doc]/[community] |
| GPU | Adreno 650 | Adreno 740 | Adreno 740 | Q2-003, A2-001 |
| RAM | 6 GB LPDDR4X | 8 GB | 8 GB | Q2-001 [doc], Q2-003 [community] |
| Memory type / bandwidth | LPDDR4X | Wikipedia: LPDDR5 4200 MT/s, 68 GB/s (inconsistent: 4200 MT/s x 8 B = 33.6 GB/s, derived); iFixit: LPDDR5 part; data rate unpublished | disputed: Wikipedia LPDDR4X 42 GB/s vs iFixit LPDDR5 part (ARM-C2) | Q2-004, Q2-005, A1-023, A3-099, ARM-C2 [community] [verify on device] |
| App PSS limit | 4.4 GiB | 5.75 GiB | 5.75 GiB | Q2-041 [doc] |
| GDC 2026 memory working target | about 3.5 GB | about 5 GB | not named (talk title covers 3/3S; recap names Quest 3 only) | QUEST-GF1-003, QUEST-GF2-012 [doc] |
| Panel per eye | 1832x1920 | 2064x2208 | 1832x1920 | Q2-002, Q2-017 [doc] |
| Default eye buffer (scale 1.0) | 1440x1584 | 1680x1760 | 1680x1760 | Q2-017, ARM-GF2-004 [doc] |
| Panel-matching scale | not stated | not stated | about 1.09 (arithmetic) | Q2-088 |
| PPD / FOV | not listed (discontinued) | 25 PPD, 110 deg H x 96 deg V, pancake | 20 PPD, 96 deg H x 90 deg V, Fresnel | Q2-002, Q2-091 |
| Dynamic-resolution default range (OVRManager, SDK 207) | 0.7-1.3 | 0.7-1.6 | 0.7-1.6 | Q2-024 / Q2-090 [doc] (SDK source) |
| Eye-texture allocation at max dynres scale | 1872x2059 (1.3, arithmetic) | 2688x2816 (1.6) | 2688x2816 (1.6) | Q2-024 / Q2-090 |
| Refresh rates | 60 (media only), 72, 80, 90, 96, 100, 120 | 72-120 charted, any integer to 207; 240 dev mode only | 72, 80, 90, 96, 100, 120 | Q2-010, Q2-013, Q2-089 [doc] |
| Draw calls, busy / medium / light simulation | 80-200 / 200-300 / 400-600 | 200-300 / 400-600 / 700-1000 | as Quest 3 | Q2-033 [doc] |
| Draw calls, comparison page (May 2026) | under 100 | under 200 | not stated (same SoC as Quest 3) | U3-003 [doc] |
| Triangles, unity-perf page | 750k-1M | 1.3M-1.8M | 1.3M-1.8M | Q2-034 [doc] |
| Triangles, comparison page | under 750K | under 1.5M | not stated | U3-003 [doc] |
| MR level cap (passthrough on) | n/a | CPU L3 / GPU L2 | CPU L3 / GPU L2 | Q2-038 [doc] |
| Depth sensor | no | yes | no (Environment Depth still listed as supported, method undocumented) | Q2-092 |
| `SystemHeadset` value | 9 (`Oculus_Quest_2`) | 11 (`Meta_Quest_3`) | 12 (`Meta_Quest_3S`) | Q2-080 [doc] (Core SDK 207 source) |
| `supportedDevices` ID | `quest2` | `quest3` | `quest3s` | Q2-083, Q2-093 [doc] |
| OpenXR Target Devices entry | Quest 2 | Quest 3 | Quest 3S (Unity OpenXR 1.13.0+) | Q2-084 [doc] |
| Battery life (Meta) | not listed | about 2 h | about 2.5 h | A3-098 [doc] |

Other `SystemHeadset` values (Q2-080): `Oculus_Quest` = 8, `Meta_Quest_Pro` = 10,
`Meta_VR_Glasses` = 13, placeholders 14-20, Link variants from 0x1000. Quest Pro shares
Quest 2's clock tables and 4.4 GiB PSS limit (Q2-007); it loses CPU L4 / GPU L4 whenever
passthrough, eye/face/body tracking or gaze foveation is on.

CPU/GPU level-to-clock tables are owned by `quest-perf:quest-levels-thermal`. Core types
and cluster clocks are owned by `arm-mobile-hw-perf:xr2-gen1-vs-gen2` (note: Wikipedia's
"2x A715 + 4x A510" for Quest 3 in Q2-004 is disputed there).

## Draw-call and triangle figures by source

Read when a draw-call or triangle figure is quoted and you need to know which Meta page it
came from and how current it is.

Draw calls (QUEST-GF2-C5, Q1-C3):

| Source | Quest 2 | Quest 3/3S |
|---|---|---|
| Meta unity-perf page, busy / medium / light simulation (Q2-033) | 80-200 / 200-300 / 400-600 | 200-300 / 400-600 / 700-1000 |
| Meta device-optimization-comparison page, May 2026 (U3-003) | under 100 | under 200 (Quest 3; 3S shares the SoC) |
| Meta GDC 2026 talk (QUEST-GF2-005) | not stated | about 500, "not a hard and fast rule"; above 1,000 possible |
| Quest Runtime Optimizer, Setup category (Q1-C3) | under 300 | under 300 |
| Meta hz-perfetto-debug agent skill (Q1-053) | good under 100, warning over 200, critical over 500 | same |

Busy = multiplayer/social with VoIP and many skinned characters; light = puzzle or
escape room. Cost is driven by state changes, main/render-thread load and API choice.
None of the pages says whether a multiview draw counts once or twice (X-C4).

Triangles per frame, two Meta pages disagree (X-C4):
- unity-perf page (Q2-034): Quest 2/Pro 750k-1M; Quest 3/3S 1.3M-1.8M.
- device-optimization-comparison page (U3-003): Quest 2 under 750K; Quest 3 under 1.5M.
- Unresolved. Start from the lower bound of each and measure. On a tiler, a large
  triangle runs its vertex work in every bin it covers, so cost is not triangle count
  alone (Q2-034 notes).
- Stale, do not cite: "50,000 static triangles per eye" and "texture memory is nearly
  free" (unity-mobile-performance-intro), and the Quest 1 / Unity 2018 draw-cost
  multipliers (po-draw-call-analysis). Use those only for relative ordering (Q2-035).

## Capability ratios, Quest 3/3S vs Quest 2

| Claim | Value | Source | Status |
|---|---|---|---|
| GPU | about 2x | Meta blog, Oct 2023 (Q2-006, A1-020) [doc] | planning figure |
| GPU | 2.5x | Qualcomm XR2 Gen 2 brief (A1-012) [doc]; Meta comparison page, May 2026 (U3-003) [doc] | conflict ARM-C20; no independent measurement |
| CPU | about +33% | Meta blog (Q2-006) [doc] | L4 clock ratio 1.92/1.48 = 1.30 (A1-020, derived): mostly clock |
| Memory | more than +30% | Meta blog (Q2-006) [doc] | PSS difference is about 1.35 GiB |
| Default pixels | about +30% | Q2-019 [doc] | consumes part of the GPU uplift |
| MR vs VR-only on Quest 3 | about -17% GPU, -14% CPU | Q2-006 [doc]; matches GPU L4 to L2 545 to 456 MHz and CPU L4 to L3 1.92 to 1.65 GHz (arithmetic) | Depth API extra cost unpublished |
| AppSW | up to 70% extra compute | Q2-006 [doc] | see `quest-perf:quest-appsw` |

## Tier structure (researcher synthesis, not Meta guidance)

From Q2-085, built on Meta's own groupings (3/3S grouped and 2/Pro grouped in the
draw-call and triangle tables; level-availability rules):

| Tier | Headsets | Notes |
|---|---|---|
| A | Quest 3, VR only | full level table |
| A-display | Quest 3S | same compute and default eye buffer as A; differs in panel, FOV, lenses, possibly memory bandwidth |
| B | Quest 2 (and Quest Pro) | Pro loses levels with passthrough or tracking |
| MR modifier | Quest 3/3S with passthrough on | CPU L3 / GPU L2 ceiling; budget as a separate, lower tier |
| Unknown newer | SystemHeadset 13-20 | map to the highest tier and capability-check (Q2-080 notes) |

Detection rules (Q2-081 to 084):
- Missing headset in `com.oculus.supportedDevices`: APIs report the most recent older
  listed model; missing entry entirely: they report the original Quest (8).
- No API reports compatibility mode. Combine the enum, the refresh-rate list and the
  measured frame time; re-tier on `OVRManager.DisplayRefreshRateChanged`.
- Compatibility mode and Target Devices never change clocks.

## Measurement methods where no budget is published

| Budget | Method | Source |
|---|---|---|
| Fill rate / pixel throughput | RenderDoc Meta Fork render-stage trace; Tile Timeline per-surface duration, render mode, bin count. Compare tiled-forward surfaces with full-screen passes. OVR Metrics `avg_fill_percentage` (needs ovrgpuprofiler support on) for overdraw. | Q2-036, Q1-007 |
| Texture memory | PSS at peak scene load (MQDH, `dumpsys meminfo`, CSV `app_pss_MB`), GPU memory with `gpumeminfo -p <pid>` and `app_gpu_*_MB` columns. Eye buffers and render textures count in the same PSS. | Q2-037, Q1-095 |
| Net app headroom | Lock levels (`adb shell setprop debug.oculus.cpuLevel 4`, `debug.oculus.gpuLevel 4`), read `TW`, `GD`, `App` at the shipping layer count; keep `App` at or below budget minus `TW` with margin for a thermal step. Reset props afterwards. | Q2-030, Q2-039 |
| Quest 3S bandwidth (ARM-C2) | Compare `Mem=` in `adb logcat -s VrApi` on Quest 3 and 3S; A/B a bandwidth-bound scene at fixed levels. | Q2-005 |
| FFR savings on 3S vs 3 | Measure `App` at each FFR level on both devices. | Q2-091 |
