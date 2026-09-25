# XR2 Gen 1 vs XR2 Gen 2: full side-by-side, conflicts and measurement methods

Read this when a spec-sheet claim is not settled by the Key numbers table in SKILL.md,
when you need the conflict history behind a number, or when you need to measure
something no source publishes. All sources accessed 2026-09-24. IDs refer to
research/arm-mobile-hw.md unless marked. The level-to-clock table is not copied here;
it is owned by `quest-perf:quest-levels-thermal`.

## 1. Side-by-side

### CPU

| Item | Quest 2 (XR2 Gen 1, SM8250) | Quest 3/3S (XR2 Gen 2, SXR2230P) | Source / tag |
|---|---|---|---|
| Core types and clusters | 1x A77 prime @ 2.84 GHz, 3x A77 gold @ 2.42 GHz, 4x A55 silver @ 1.80 GHz | 4x A78C @ 2.36 GHz + 2x A78C @ 2.05 GHz | A1-001 [community], A1-002 [measured]; A1-013, A1-014 [measured] |
| MIDR seen by Geekbench (CPU0) | part 0xD05 (A55 r1p0) | part 0xD4B (A78C r0p2) | A1-002, A1-013 [measured] |
| Qualcomm wording | n/a | "4 + 2 performance cores, up to 2.4/2.0 GHz" | A1-012 [doc] |
| Likely core numbering | app set inferred cpu4-6 (A77 gold) | Geekbench lists the 2 @ 2.05 cluster first: likely cpu0-1, with the 4 @ 2.36 cluster as cpu2-5 | A1-004 [doc] [verify on device]; A1-050 [verify on device] |
| App cores | 3 | unpublished | A1-004 [doc]; Known unknowns |
| Clusters implied by level | L8 2.42 GHz = gold-cluster max; prime never used | L5 2.05 GHz = 2-core cluster max; L6 2.21 and L8 2.36 GHz imply the 4-core cluster | A1-003 [doc]; A1-016 derived [verify on device] |
| Default L4 as share of cluster max | 1.48/2.42 = 61% | 1.92/2.36 = 81% | A1-005 set, derived |
| Unity 2x "big" rule | met (A77 vs A55) | not met (1.15x) | A1-050 [doc] [verify on device] |
| Dual-core mode | supported (Quest 2, Pro) | not supported | ARM-GF1-001 [doc] |
| ISA | Armv8.2-A (incl. RAS) + v8.3 LDAPR + v8.4 dotprod | Armv8.2-A + v8.3 LDAPR/PAuth + v8.4 dotprod + v8.5 SSBS + v8.6 enhanced PAuth; AArch32 at EL0 only | A1-075 [doc] |
| Geekbench feature line | neon, aes, sha1, sha2, neon-fp16, neon-dotprod | same | A1-076 [measured] |
| SVE/SVE2, i8mm | no | no | A1-075 [doc], A1-076 [measured] |
| System cache | not published | 8 MB, labelled LLC | A1-012 [doc] |
| Per-core L2, cluster L3 | not published | not published; one or two DSU clusters unknown | Known unknowns |
| Kernel governor (2D benchmark view) | "performance" (GB6, Android 14) | "walt" on Android 12, "schedutil" on Android 14 | A1-002, A1-022 [measured] [verify on device] |
| Geekbench 6 single-core | 593-613 | Quest 3 573-931 (median 671); 3S 649-977 (median 887) | A1-021 [measured] |

Geekbench runs as a 2D app outside Meta's VR level system and sees all cores, so none of
its scores size a VR budget (A1-002).

### GPU

| Item | Adreno 650 (Quest 2) | Adreno 740v3 (Quest 3/3S) | Source / tag |
|---|---|---|---|
| Generation | a6xx gen3 | a7xx (Mesa "FD740v3", chip 0x43050b00; SD8 Gen 2 phone is 0x43050a01) | A2-002, A2-003 [community] |
| CCUs | 3 | 6 | A2-002, A2-003 [community] |
| Mesa tile alignment / max tile | 96x16 / 1024x1024 | 96x32 / 2016x2032 | A2-002, A2-003 [community]; do not predict Qualcomm-driver bins from these (A2-016) |
| reg_size_vec4 | 64 | 96 (about 1.5x) | A2-003 [community] |
| Register file proxy | no direct figure; Chips and Cheese A730 (A7xx) 64 KB per partition, which matches reg_size_vec4 64 only by ratio | 96 KB per partition (X1 "741") | A2-006 [measured] proxy |
| Visibility-stream pipes, compute shared memory | shared memory 32 KB | 32 pipes, 32 KB | A2-002 [community]; compute note under A2-094 section |
| GMEM | 1 MB (Meta); 1 MiB + 128 KiB (kernel) | about 2 MB (Meta); Quest chip not in kernel catalog | A2-010 [doc], A2-011 [community] |
| GMEM-mode CCU carve-out (Mesa) | a quarter | an eighth | A2-012 [community]; unconfirmed for Qualcomm's driver |
| Max level clock | 587 MHz (L5, equals the SD865 phone max) | 599 MHz (L5) | A1-005 set, A1-006 [doc] |
| Concurrent binning | no | yes | A2-026 [doc] |
| Dual LRZ buffers (BV/BR pipes) | no | yes | A2-027 [community] |
| LRZ direction tracking | GPU-side direction byte (A650+), LRZ survives across passes on the same depth view | same, plus bidirectional LRZ (off by default) | A2-031 [community] |
| LPAC async compute | no | yes (`VK_KHR_global_priority` LOW); slightly higher instruction limit | A2-094 [doc] |
| Early preamble, attachment shading rate | no | yes (a7xx base) | A2-003 [community] |
| Multiview per-view render areas / viewports | no | `VK_QCOM_multiview_per_view_render_areas`, `VK_QCOM_multiview_per_view_viewports` | A3-043 [doc] |
| Post-transform vertex cache | not published | 32 x vec4 vertices | A2-049, A3-019 [doc] |
| Instruction cliff | not published | each multiple of 2000 (2256 for LPAC compute) | A2-070 [doc] |
| Binding cliffs | 16 samplers | 16 samplers; also each multiple of 32 vertex buffers, 16 unique UBOs, 16 textures+SSBOs | A2-070 [doc] |
| FP16 rate | double rate (A640 proxy, corrected) | double rate (X1 proxy) | A2-005, A2-006 [measured]; ARM-C15 |
| SP/ALU counts, FLOPS | not published | not published | A2-004 [doc] |
| ovrgpuprofiler multiview surface | see `quest-perf:quest-profiling-toolkit` | see `quest-perf:quest-profiling-toolkit` | A3-034 [doc] |

### Memory and display

| Item | Quest 2 | Quest 3 | Quest 3S | Source / tag |
|---|---|---|---|---|
| RAM | 6 GB (5.70 GB visible) | 8 GB (7.55-7.58 GB visible) | 8 GB | A1-002, A1-013 [measured] |
| Memory type | LPDDR4X (press via Wikipedia) | LPDDR5 (iFixit: likely SK hynix H58G66BK8BX105) | LPDDR5 (iFixit: Micron MT62F1G64D4EK-026 WT:B) | A1-008, A1-023 [community] |
| Controller spec | SD865 family 4x16-bit @ 2133 MHz, 34.13 GB/s theoretical | 4x16-bit LPDDR5 "up to 3.2 GHz" | same SoC | A1-008 [community]; A1-012 [doc] |
| Configured data rate | not published | not published | not published | ARM-C2 |
| Storage | n/a | UFS 3.1, 128 GB NAND (SK hynix HN8T05DEHKX073) | same NAND part | A1-012 [doc], A1-023 [community] |
| Default eye buffer (scale 1.0) | 1440x1584 | 1680x1760 | 1680x1760 | ARM-GF2-004 [doc] |
| Panel per eye | n/a | 2064x2208, 25 PPD | 1832x1920, 20 PPD | A1-025 [doc] |
| Max refresh | n/a here | 120 Hz | 120 Hz | A1-025 [doc] |

### Power and battery (context only; thermal behaviour is owned by quest-perf:quest-levels-thermal)

| Item | Quest 2 | Quest 3 | Quest 3S | Source / tag |
|---|---|---|---|---|
| Battery | 14 Wh | 19.44 Wh (teardown) or 18.9 Wh (later UploadVR) | 16.74 Wh (leaked label) | ARM-GF1-002, ARM-C25, ARM-GF2-001 [community] |
| Meta battery life | n/a | about 2 h | about 2.5 h | A3-098 [doc] |
| Implied average whole-headset draw | n/a | about 9.7 W (derived) | about 6.7 W (derived) | ARM-GF1-002, ARM-GF2-001 |
| SoC TDP / sustained power | not published | not published | not published | section 1.7 of the dossier |

The 3S/3 draw ratio is whole-headset (display, optics, cameras) and must not be read as
an SoC difference (ARM-GF2-001). Meta's generic mobile-GPU class is 3-6 W
(ARM-GF1-006, [doc]).

## 2. Conflicts relevant to this skill (both sides kept)

- **ARM-C1, CPU core types.** Wikipedia's Quest 3/3S infoboxes say 2x A715 + 4x A510
  (uncited, [community]); quest.md Q2-004 repeats it. UploadVR says "two performance
  cores and four efficiency cores" ([community]). Qualcomm's brief: "4 + 2
  performance cores, up to 2.4/2.0 GHz" ([doc]). Geekbench MIDR: A78C r0p2 in 4 @ 2.36
  + 2 @ 2.05 GHz ([measured]). Dossier assessment: 6x A78C. The 2+4 claim confuses clock
  tiers with core types.
- **ARM-C2, Quest 3/3S memory type and data rate.**
  - Qualcomm brief: "4x16 LP-DDR5 memory, up to 3.2 GHz" ([doc]). Reading "3.2 GHz" as
    6400 MT/s on 64 bits gives 51.2 GB/s. That reading is an assumption (A1-023).
  - iFixit: LPDDR5 parts on both headsets ([community]).
  - Micron via TweakTown: 8 GB LPDDR5X at 8.533 Gbps "optimized for" XR2 Gen 2
    ([community]). At 64 bits that would be about 68.3 GB/s (derived). Wikipedia's SoC
    list also says LPDDR5X.
  - Wikipedia Quest 3: "LPDDR5 @ 4200MT/s (68GB/s)". This is internally inconsistent:
    4200 MT/s x 8 B = 33.6 GB/s (derived). Wikipedia Quest 3S: "LPDDR4X @ 2600MT/s
    (42GB/s)", contradicted by iFixit. If it were true, the 3S would have about 40% less
    peak bandwidth than the 3 (A3-099, derived).
  - Dossier assessment: LPDDR5-class memory on both; the rate is unpublished; measure.
- **ARM-C3, Quest 3/3S peak GPU clock.** Levels table: L5 = 599 MHz ([doc]). The
  ovrgpuprofiler and render-stage pages say 690 MHz for Quest 3 and 492 MHz for Quest 3S
  ([doc]; the render-stage page has a visible TODO in that paragraph). UploadVR says
  640 MHz in Favor GPU mode, after a 2024 firmware change that also raised the default
  maximum from 545 to 599 MHz (A3-088, [community]). Dossier assessment: budget with the
  levels table. 690 = VR Glasses L5 and 492 = Quest 3/3S L3, which suggests copy
  errors. Read `Clocks / Second` or GPU F on device.
- **ARM-C4, Quest 3/3S Boost level** (touches the "max app clock" row). The clock table
  and Boost page give L8 = 2.36 GHz (+23%). The availability table labels the Boost row
  "6" (2.21 GHz, +15%). Unresolved; owned by `quest-perf:quest-levels-thermal`.
- **ARM-C7, core count seen by apps on Quest 2.** Meta implies 3 app cores ([doc]).
  Geekbench as a 2D app sees 8 ([measured]). `SystemInfo.processorCount` may not equal
  the usable count.
- **ARM-C9, Quest 3 GMEM.** Meta: "approximately 2MB" ([doc]). Kernel: 3 MiB for the SD8
  Gen 2 chip 0x43050a01, not Quest's 0x43050b00 ([community]). Chips and Cheese: 3 MB on
  the X1-85 ([measured]). Dossier assessment: trust Meta for Quest; infer from
  ovrgpuprofiler bin sizes.
- **ARM-C10, Quest 2 GMEM.** Meta: 1 MB ([doc]). Kernel: 1 MiB + 128 KiB ([community]).
  Meta's own 96x176 multiview 4x MSAA example needs 96 x 176 x 2 x 32 B = 1,081,344 B
  = about 1.03 MiB (derived), more than 1 MiB. Dossier assessment: "1 MB" is rounded.
- **ARM-C20, Quest 3 vs Quest 2 GPU gain.** Meta: "twice the GPU power" ([doc]).
  Qualcomm: "2.5x higher GPU performance" ([doc]). Probably measured under different
  conditions (Qualcomm likely at unrestricted phone-class clocks). No independent
  like-for-like Quest measurement. Use 2x for planning; measure at matched levels.
- **ARM-C24, `Mem=` value in Meta's logcat docs.** The example line shows 2092 MHz, the
  field table 1804 MHz, and neither names a device. If 2092 MHz were Quest 2 LPDDR4X,
  the derived peak would be 2092 x 2 x 8 B = about 33.5 GB/s. With 1804 MHz it would be about
  28.9 GB/s (A1-008, derived). Do not use either as a spec.
- **ARM-C25, Quest 3 battery.** 19.44 Wh (teardown) vs 18.9 Wh (later UploadVR
  article). The ~9.7 W estimate changes to about 9.5 W at most (derived).

## 3. Out-of-scope SoCs (disambiguation)

- **XR2+ Gen 2**: in no Quest. "2.4 GHz on all CPU cores", 15% higher GPU maximum than
  XR2 Gen 2, same memory specification (A1-027, [doc]).
- **Meta VR Glasses (XR2 Gen 3, 12 GB, 2412x2288 per eye)**: separate level table on
  the same Meta page. CPU L8 2.71 GHz, GPU L5 690 MHz. No trading or dual-core mode.
  GMEM not stated (A3-074, A1-025 notes, [doc]).
- **Quest Pro (XR2+)**: uses the Quest 2 level table. CPU 4 / GPU 4 require
  passthrough, eye, face and body tracking and gaze-based foveation to be off. GMEM not
  stated (A3-073, A3-004, [doc]).
- **Snapdragon 8 Gen 2 phones (Adreno 740, 0x43050a01)**: closest public proxy for
  Quest 3's GPU topology, but GMEM (3 MiB kernel value), clocks and driver differ
  (A2-002).

## 4. Measurement methods for unpublished silicon facts

None of these is shipped as code. No dossier finding validates an implementation on
Quest (OUTLINE decision 33). Pin levels first with
`adb shell setprop debug.oculus.cpuLevel 4` and `adb shell setprop debug.oculus.gpuLevel 4`
(A3-051). Props reset on reboot.

- **App core set and placement (both devices).** While the app runs, read
  `adb shell 'cat /proc/$(pidof <package>)/status | grep Cpus_allowed_list'`, the
  per-thread `/proc/<pid>/task/<tid>/status`, and `adb shell cat /dev/cpuset/top-app/cpus`.
  Confirm on Perfetto CPU scheduling tracks (dossier Known unknowns, A1 list).
- **Job-worker count.** Log `JobsUtility.JobWorkerMaximumCount`, `JobWorkerCount` and
  `SystemInfo.processorCount` at startup per device and Unity version (A1-055). The
  SKILL.md probe does this.
- **Cache sizes.** Try `adb shell cat /sys/devices/system/cpu/cpu0/cache/index*/size`
  (often absent on arm64 Android). Otherwise run a pointer-chase latency sweep (working
  set 16 KB to 64 MB) in a Burst job pinned to one app core, and read the L1, L2 and L3
  steps (Known unknowns, A1 list).
- **DRAM data rate and achievable bandwidth.** Run a STREAM-style copy/triad Burst job at
  a pinned CPU level. At the same time read `Mem=` (`adb logcat -s VrApi`) or MEM F (OVR
  Metrics) at several levels and during a throttle event. Whether the memory clock
  scales with level is undocumented (A1-008, A3-053, Known unknowns). Compare Quest 3
  and 3S to settle ARM-C2 for your units.
- **Relative GPU throughput (A2-004).** Lock the GPU level, run a fixed full-screen
  ALU-bound shader with fixed iterations, read `Clocks / Second` and `% Shaders Busy` in
  ovrgpuprofiler, and compare Quest 2 and Quest 3 at matched MHz. This is the only
  route to a like-for-like number (ARM-C20).
- **GMEM on Quest 3.** Read the eye-buffer bin size from `ovrgpuprofiler -t -v` (after
  `-e` and an app restart) at a known footprint. Multiply bin width x height x views x
  bytes per pixel (A2-013). Meta's 128x224 example at 32 B/px with two views is about
  1.75 MiB per bin (A2-015, derived), consistent with about 2 MB of usable GMEM.
- **Quest 3 vs 3S sustained headroom.** Same build, same scene, pinned levels, 30 min or
  more of OVR Metrics CSV. Record the first minute POW L leaves 0 or the maximum level
  drops, and repeat after a 20-minute cool-down at about 21 C (A3-093, A3-095). The full
  recipe is owned by `quest-perf:quest-levels-thermal`.

## 5. Known unknowns assigned to this skill

- An independent like-for-like Quest 2 vs Quest 3 GPU measurement (ARM-C20). Only
  vendor claims exist (2x Meta, 2.5x Qualcomm). UploadVR's "Quest 3 GPU may be twice as
  powerful" article was found but not read by the dossier.
- How much app-core time the XR2 Gen 2 hardware offload of tracking, passthrough,
  SpaceWarp extrapolation and Super Resolution frees (A1-024, [community]). UploadVR
  also puts the CPU gain at 33% and claims passthrough latency fell from about 50 ms to
  about 12 ms. No Meta figure exists.
- Quest Pro and Meta VR Glasses GMEM: not stated (A3-004, A3-025).
- App-core count on Quest 3/3S, configured cache sizes, DRAM data rate on all Quest,
  thermal envelope per chassis: see section 4 for the methods.

## Sources

All accessed 2026-09-24. The SKILL.md Sources list carries every URL used here. These
are the additional ones:

- https://chipsandcheese.com/p/correction-on-qualcomm-igpus [measured] (A2-005)
- https://chipsandcheese.com/p/the-snapdragon-x-elites-adreno-igpu [measured] (A2-006, ARM-C9)
- https://www.uploadvr.com/quest-3-teardown-battery/ [community] (ARM-GF1-002)
- https://developers.meta.com/horizon/essentials/compare-devices/ [doc] (A3-098)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md [doc] (A3-095)
