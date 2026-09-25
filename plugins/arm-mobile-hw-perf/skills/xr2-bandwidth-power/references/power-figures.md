# Power figures, energy sources and the unpublished thermal envelope

Every figure below is whole-device or generic unless stated. None is a Quest SoC power
rating: Meta and Qualcomm publish no TDP, sustained SoC power or thermal envelope for
Quest 2, Quest 3 or Quest 3S (arm-mobile-hw.md section 1.7). All sources accessed
2026-09-24.

## Energy per byte (generic)

| Figure | Value | Scope | Source / tag |
|---|---|---|---|
| Off-chip DRAM access | ~1-2 nJ | 45 nm, 0.9 V; absolute values stale, ratio durable | A3-001, https://gwern.net/doc/cs/hardware/2014-horowitz-2.pdf [doc] |
| DRAM I/O | > 20 pJ/bit, improved I/O ~10 pJ/bit (~0.6 nJ per 8 B) | same | A3-001 [doc] |
| On-chip cache access / ALU op | ~10-20 pJ | same | A3-001 [doc] |
| DRAM traffic power | ~120 mW per GB/s; on-chip tile access ~10x cheaper | Mali-era rule; "depends on system design" | A3-002, https://web.archive.org/web/20191215124148/https://community.arm.com/developer/tools-software/graphics/b/blog/posts/the-mali-gpu-an-abstract-machine-part-2---tile-based-rendering [doc] |
| Variant | ~100 mW per GB/s, attributed to Arm guide 101897 | seen only in search snippets; page unreadable | A3-002 notes |

Conflict ARM-C22, both sides: 120 mW per GB/s (Arm 2014 blog, read) vs 100 mW per GB/s
(Arm best-practices guide, snippet only). Both are Mali-phone-era rules. Use ~0.1 W per
GB/s as an order of magnitude. Cross-check: 120 mW per GB/s is ~15 pJ/bit, between
Horowitz's 10 and 20 pJ/bit I/O figures (derived). No XR2 Gen 2 / LPDDR5 figure exists.

## Battery and derived average draw

| Headset | Battery | Meta battery life | Derived average whole-headset draw | Source / tag |
|---|---|---|---|---|
| Quest 3 | 19.44 Wh (teardown) | ~2 h | ~9.7 W | ARM-GF1-002, https://www.uploadvr.com/quest-3-teardown-battery/ [community]; A3-098, https://developers.meta.com/horizon/essentials/compare-devices/ [doc] |
| Quest 3 (alt.) | 18.9 Wh (later UploadVR article) | ~2 h | ~9.5 W | ARM-C25, https://www.uploadvr.com/quest-3s-images-leak-reveal-battery-size-no-headphone-jack/ [community] |
| Quest 3S | 16.74 Wh (leaked regulatory label) | ~2.5 h | ~6.7 W | ARM-GF2-001, same UploadVR leak article [community] |
| Quest 2 | 14 Wh | not in the dossier | no derived figure | ARM-GF1-002 [community] |

Conflict ARM-C25: 19.44 Wh (teardown-based) vs 18.9 Wh (later comparison table). Use
19.44 Wh; the 3% gap barely moves the estimate.

Reading rules:
- The averages include displays, cameras, tracking, audio and radios. They bound SoC power
  from above; they are not a thermal design power (ARM-GF1-002).
- Meta's battery-life figures are rounded and their workloads unstated, so the 3S/3 ratio
  (~0.7) is not an SoC difference: both run the same SoC and level table (ARM-GF2-001,
  A1-015). The 3S label was a pre-release leak; retail capacity is unconfirmed.

## Measured Quest 3 power per scenario

One Meta-forum user, inline USB-C meter, fully charged headset (input ~ system draw),
Quest 3 on OS 57.0.0.279, 120 Hz, one run per scenario (ARM-GF2-002,
https://web.archive.org/web/20250108162626/https://communityforums.atmeta.com/t5/Talk-VR/Quest-3-Power-Usage-Tests-and-Approximate-Battery-Life/td-p/1094433,
[measured] [verify on device]):

| Scenario | Measured input power | Author's implied battery life at 19.44 Wh |
|---|---|---|
| Standby | 0.17-0.7 W @ 5 V | 44.7 h |
| Browsing in VR | 7.6-8.2 W @ 9 V | 2.5 h |
| Standalone VR game (Into the Radius, Quest 3-enhanced) | 7.5-9.0 W @ 9 V | 2.4 h |
| Browsing in MR (passthrough) | 9.6-10.2 W @ 9 V | 2.0 h |
| Air Link PC VR (out of scope, same table) | 10.5-10.7 W @ 9 V | 1.8 h |
| Standalone MR game (First Encounters) | 10.5-12.0 W @ 9 V | 1.7 h |

- Charging rows (12-20 W) are omitted: they include charge current.
- Derived deltas: MR draws ~2-3 W more than the matching VR scenario, consistent with
  Meta's passthrough cost statement (A1-019) and passthrough level caps (A1-018). MR
  budgets: `quest-perf:quest-mr-costs`.
- A VR game at ~8-9 W agrees with the ~9.7 W battery-life average.
- Launch-era OS; re-measure on the current OS before quoting.

## Meta's framing and other Meta figures

| Statement | Scope | Source / tag |
|---|---|---|
| Most of Quest 3's battery power goes to the CPU and GPU; performance is a zero-sum budget, so lower clock levels when the CPU or GPU is not fully used. Extra passes (blur, bloom, HDR, realtime shadows, deferred) cost more on this architecture. No share or wattage given. | Quest 3 (3S shares the SoC) | ARM-GF2-003, https://developers.meta.com/horizon/blog/optimizing-for-success-meta-quest-3-gdc/ [doc] |
| Quest-class GPUs have "5mb or less" of on-GPU memory and typically draw 3-6 W | generic "phones and Meta Quest devices" | ARM-GF1-006, https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ [doc] |
| Lowering clocks all the way gives only ~25% less power for the same work; CPU load seemed to cause more thermal trouble than GPU load; two cores at 1 GHz beat one at 2 GHz | Quest 1/2 era, deprecated VrApi page (2022-09-29), stale | A3-094, https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/ [doc] |
| Thermal-pressure patterns: heavy shaders + high-res post, full-res passthrough + heavy 3D, always-on physics/particles/dynamic lighting, no FFR or AppSW | all current Meta VR devices | A3-079, https://developers.meta.com/horizon/essentials/thermal/ [doc] |
| For battery drain, optimise against CPU/GPU levels rather than Battery Current (BAT C) or Power Current (POW C) | all current Quest | A3-082, https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ [doc] |

## Power signals you can log

| Signal | Where | Notes |
|---|---|---|
| `power_wattage`, `power_current`, `power_voltage` (+ `_neg` / `_pos` variants in 2026 CSVs) | OVR Metrics CSV | Units and sign convention not documented; use as A/B trend only (quest.md Q1-005, Q1-012) |
| `battery_level_percentage`, `battery_current_now_milliamps` | OVR Metrics CSV | `battery_current_now_milliamps` = 9999 placeholder seen in a 2023 Quest 2 file (Q1-017) |
| `mem_frequency_MHz` / MEM F, `Mem=` | CSV / overlay / `adb logcat -s VrApi` | Only documented memory-side clock signals; scaling with level or heat unknown (A3-053) |
| `power_level_state` / POW L / `PLS=` | CSV / logcat | Thermal state 0/1/2; runtime meaning owned by `quest-perf:quest-levels-thermal` (A3-081) |

CSV enable and pull commands: A3-049,
https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc]. Summaries:
`python ovr_metrics_csv.py <csv> --hz 72 --window-min 5` from
`quest-perf:quest-profiling-toolkit` (reports first-vs-last-window `power_wattage` and
`mem_frequency_MHz`).

## Known unknowns and how to measure each

| Unknown | Method |
|---|---|
| TDP / thermal envelope, any Quest | At pinned levels, log the power columns over 20-30 min for a fixed scene and record time to first level drop or PLS change (A3-093 recipe); compare Quest 3 and 3S, whose chassis differ. Soak protocol: `quest-perf:quest-levels-thermal` |
| DRAM energy per GB/s on XR2 Gen 2 / LPDDR5 (ARM-C22) | Fixed levels, sweep a synthetic full-screen store pass count (0, 1, 2, 4); slope of `power_wattage` vs added GB/s ([traffic-budgets.md](traffic-budgets.md)). Noisy; Meta discourages optimising on these metrics |
| Battery drain vs CPU/GPU level | Fixed-level runs of the same scene, one per level pair, 20-30 min each, battery above 50%, unplugged; log `battery_level_percentage` and `power_wattage` |
| Whether `Mem=` / MEM F scales with level or heat (A3-053, ARM-C24) | Log it across PowerSavings and SustainedHigh runs and through a throttle event |
| Configured DRAM data rate; Quest 3S vs Quest 3 bandwidth (ARM-C2) | `Mem=` on each headset plus the copy probe in [traffic-budgets.md](traffic-budgets.md) |
| Fan behaviour | No Meta doc and no metric exposes fan speed. Only indirect: PLS transitions under controlled conditions. Blocking the fan is not recommended |
| Sustained headroom Quest 3 vs 3S | Same build, same scene, A3-093 recipe on both |

Test hygiene for every power run (A3-029, A3-095, ARM-GF2-002 notes): no ovrgpuprofiler
detailed mode (~10% GPU overhead); unplugged; room ~21 C; ≥ 20 min cool-down between
runs; record the OS build.
