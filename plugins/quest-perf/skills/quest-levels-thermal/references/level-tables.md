# Level tables, availability rules and open conflicts

All rows from Meta's levels page (https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/, updated 2026-09-02, native mirror https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/), accessed 2026-09-24, [doc], unless marked. Levels and clocks depend on the OS build (Q2-057); record the build with every capture and re-check after major OS updates.

## Level-to-clock table (A1-005, Q2-046/047)

| Level | Quest 2 / Pro CPU | Quest 3/3S CPU | Quest 2 / Pro GPU (Adreno 650) | Quest 3/3S GPU (Adreno 740) |
|---|---|---|---|---|
| 0 | 0.71 GHz | 0.69 GHz | 305 MHz | 285 MHz |
| 1 | 0.94 GHz | 1.09 GHz | 400 MHz | 350 MHz |
| 2 | 1.17 GHz | 1.38 GHz | 442 MHz | 456 MHz |
| 3 | 1.38 GHz | 1.65 GHz | 490 MHz | 492 MHz |
| 4 (default) | 1.48 GHz | 1.92 GHz | 525 MHz | 545 MHz |
| 5 | 1.86 GHz | 2.05 GHz | 587 MHz | 599 MHz |
| 6 | 2.15 GHz | 2.21 GHz | n/a | n/a |
| 7 | none | none | n/a | n/a |
| 8 | 2.42 GHz (Boost only) | 2.36 GHz (Boost) | n/a | n/a |

Notes:
- GPU clocks per level are nearly equal across generations; the Quest 3 GPU uplift is architectural, not clock. Meta warns that equal level numbers do not mean equal throughput (Q2-046 notes).
- Quest 2 GPU L4 was 490 MHz before a Dec 2022 OS change (+7%); any table showing 490 MHz at L4 is stale (A1-007, A3-087).
- Derived ratios (arm dossier A1-005 notes): Quest 2 L4 CPU is about 61% of 2.42 GHz; Quest 3/3S L4 CPU about 81% of 2.36 GHz; Quest 3/3S GPU L0-L5 range about 2.1x. A GPU drop from L4 to L2 on Quest 3/3S is about -16% (Q2-038 / Q4-001 notes, derived).
- Main-thread cycle budgets per level are owned by `arm-mobile-hw-perf:xr2-cpu-threads-neon`.

## ProcessorPerformanceLevel ranges

Levels page (Q2-045, A1-028, A3-076):

| ProcessorPerformanceLevel | CPU range | GPU range |
|---|---|---|
| PowerSavings | 0-4 | 0-4 |
| SustainedLow | 2-4 | 1-4 |
| SustainedHigh (default) | 4-4 (5-5 with Quest 3/3S trading -1; 6-6 with Quest 2/Pro dual-core) | 3-5 |
| Boost | 4 to device max | 3-5 |

Essentials page, https://developers.meta.com/horizon/essentials/cpu-gpu-levels/ (QUEST-GF2-004, [doc], undated):

| ProcessorPerformanceLevel | CPU range | GPU range |
|---|---|---|
| PowerSavings | 0-4 | 0-4 |
| SustainedLow | 2-4 | 1-4 |
| SustainedHigh | 4-4 Quest 3/3S; 4-6 Quest 2/Pro with dual-core | 3-5 |
| Boost | 4-6 Quest 3/3S; 4-8 Quest 2/Pro | 3-5 |

The OS keeps the lowest level inside the range that holds frame rate. Levels are hints, not guaranteed clocks (A1-041). Background OS features such as casting can override them (A1-036).

## Availability rules

Quest 2 (Q2-048, A3-071):
- CPU 0-4 always. CPU 5 only without dual-core mode. CPU 6 only with dual-core mode. CPU 8 only while Boost is active.
- GPU 0-4 always. GPU 5 only with dynamic resolution.
- No passthrough restriction listed for Quest 2.

Quest 3/3S (Q2-049, A3-072):
- CPU 0-3 always. CPU 4 only when the app does not enable passthrough. CPU 5 only with CPU 4 available and trading -1. CPU 6 listed as "needs Boost" (see ARM-C4).
- GPU 0-2 always. GPU 3-4 only without passthrough. GPU 5 only with GPU 4 available and either trading +1 or dynamic resolution.
- Result for MR: capped at CPU L3 (1.65 GHz) and GPU L2 (456 MHz) (A1-018, Q2-038). Whether turning passthrough off at runtime restores L3-L4 is undocumented (Q4-001) [verify on device].

Quest Pro (one line): Quest 2 table, but CPU/GPU L4 are unavailable with passthrough, eye/face/body tracking or eye-tracked foveation (A3-073).

Everywhere: Battery Saver disables GPU L5 and Boost (Q2-062). Boost is refused under thermal throttling (Q2-053).

## Build-time options

| Option | Devices | Backend | Manifest | Logcat proof |
|---|---|---|---|---|
| Dual-core mode | Quest 2, Pro | OpenXR only | `<meta-data android:name="com.oculus.dualcorecpuset" android:value="true"/>` | `CreateClient: Value of isCPUSingleThreadedBoost is 1` |
| Level trading (Processor Favor) | Quest 3, 3S | OpenXR only | `<meta-data android:name="com.oculus.trade_cpu_for_gpu_amount" android:value="1\|0\|-1"/>` | `CreateClient: Value of tradeCpuForGpu is <n>` |

Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (Q2-051, Q2-052, Q1-038, A1-031, A1-032), [doc].

## Open conflicts (surface both sides; measure on device)

- **ARM-C3 / QX-C6 / Q2-C5, Quest 3/3S peak GPU clock.** Levels table: L5 = 599 MHz ([doc]). ovrgpuprofiler page (https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/, updated 2026-09-09): Quest 3 690 MHz, Quest 3S 492 MHz ([doc]). UploadVR (https://www.uploadvr.com/meta-quest-3-gpu-clock-speed-performance-boost/, 2024-10-31): default max 545 -> 599 MHz and Favor GPU 599 -> 640 MHz ([community]); Wikipedia 640 MHz ([community]). Dossier assessment: budget on the levels table; 690 equals Meta VR Glasses GPU L5 and 492 equals Quest 3/3S L3, which suggests copy errors. Measure: read `gpu_frequency_MHz` with trading +1 and dynamic resolution on.
- **ARM-C4 / QUEST-GF2-C1 / Q2-C8, Quest 3/3S Boost level.** Boost page: level 4 -> 8, +23% (1.92 -> 2.36 GHz). Levels-page availability table and essentials page: Boost row labelled 6 (2.21 GHz, only +15%). A third-party Quest 3 CSV shows 2361 MHz samples (QUEST-GF2-009, [measured]). Assessments: QUEST-GF2-C1 says the clock evidence supports L8 / 2.36 GHz; ARM-C4 leaves it unresolved. Both agree: quote +23% CPU clock and read `cpu_frequency_MHz`, not the level number.
- **ARM-C5, trading scope.** Levels page SustainedHigh row lists CPU 5-5 for "Quest 2, Quest Pro, Quest 3 or 3S with CPU level trading". Boost page: trading is Quest 3/3S only. Dossier assessment: trust the Boost page. How Quest 2 reaches CPU L5 under SustainedHigh is unexplained.
- **ARM-C6 / Q2-C7 / Q4-C9, Boost runtime share.** Boost page prose: active "for only 20% of your app's runtime". Same page's condition list: activates only if it "has not been active for 80%". Dossier assessment: 20% most likely [verify on device].
- **QX-C8, Boost duration.** Meta runtime limit 45 consecutive s; Unity OpenXR docs and Khronos: under 30 s. Design windows under 30 s.
- **Q2-C2, default level.** Unity/native pages: SustainedHigh. Unreal page (https://developers.meta.com/horizon/documentation/unreal/unreal-blueprints-set-cpu-and-gpu-levels/): CPU SustainedLow / GPU SustainedHigh. For Unity, follow the Unity page; confirm the granted level with `clockStateLogLevel`.
- **Q4-C1, GPU L5 with passthrough on Quest 3/3S.** "Available if GPU L4 is available and trading +1, or dynamic resolution is enabled" reads two ways. Related: the Boost page says GPU L5 needs dynamic resolution on every model (A1-034, Q2-050), while the Quest 3/3S availability table also allows it with trading +1 and no dynamic resolution (Q2-049). Measure: MR scene, dynamic resolution on, `clockStateLogLevel 2`, look for L5 FORCED or REJECTED.
- **QUEST-GF2-C4, GPU L3 in passthrough.** A Quest 3 capture shows 34 GPU L3 samples out of 565 in a passthrough scene ([measured]); the table says L3 is unavailable. Cause not recorded.

## Unknowns with a measurement method

- Governor utilisation metric (worst core vs average) for the 83%/77% CPU thresholds: undocumented. Method: a main-thread-only load at SustainedLow; log `cpu_utilization_percentage_core0..7` vs `cpu_level` changes.
- Whether trading changes steady-state levels when not throttling (ARM-GF1-003): A/B 20-30 min runs, logging `cpu_level`/`gpu_level` with and without the manifest entry.
- Whether Horizon OS honours `XR_EXT_performance_settings` hints from Unity's OpenXR plugin and sends its notifications: community evidence only (QUEST-GF1-010). Method: log `xrEnumerateInstanceExtensionProperties`, then watch `CPU L`/`GPU L` after each `SetPerformanceLevelHint`, and fire the simulated thermal broadcast while subscribed to `OnXrPerformanceChangeNotification`.
