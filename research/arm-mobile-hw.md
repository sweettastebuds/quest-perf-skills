# arm-mobile-hw-perf research dossier

**Scope.** This dossier covers the hardware under Meta Quest 2 (Snapdragon XR2 Gen 1: Cortex-A77/A55 CPU, Adreno 650 GPU, 6 GB LPDDR4X) and Quest 3 / Quest 3S (Snapdragon XR2 Gen 2: 6x Cortex-A78C CPU, Adreno 740v3 GPU, 8 GB LPDDR5). It is written for an AI agent that assists a senior technical artist who ships Unity URP content on Quest over Vulkan and OpenXR. The coverage areas are:

- the cores and clocks an app can actually use, and how CPU/GPU levels map to clocks and throttle
- where Unity's threads land and what that means for Burst/NEON code
- Adreno tile-based rendering (GMEM, FlexRender, LRZ, UBWC, the binning pass)
- the Adreno shader cost model
- DRAM bandwidth as the dominant power and thermal cost, and how to measure it
- what works and what does not with Snapdragon Profiler on Quest, and the Meta tools that replace it

Quest Pro and Meta VR Glasses appear only where Meta groups them with the target devices. The dossier is out of scope for PC VR/Link, HDRP, Unreal, Godot and Mali specifics; Arm material is used only for generic TBR concepts and Arm CPU cores.

**Access date:** 2026-09-24 for every source unless a finding says otherwise.

**Method:**
1. Three topic researchers wrote notes: A1 on SoC, CPU and threads; A2 on Adreno architecture and shader cost; A3 on bandwidth, thermals and profilers.
2. This synthesis merged the notes by coverage area (not by researcher). Duplicates became one finding that lists every original ID and every source. No sourced finding was dropped.
3. One gap-fill check (AS-001) was made during synthesis to resolve a contradiction between A1 and A3. The synthesis also added cross-topic conflicts (ARM-C19 to ARM-C24).
4. Round-1 coverage pass (2026-09-24): the synthesis output had stopped after section 2, so sections 3-7, Conflicts, Known unknowns and the Source list were restored from the A1/A2/A3 topic notes with their original IDs. Gap-fill findings were added as `ARM-GF1-NNN`, and numeric and version claims were spot-checked against the live sources. Corrections are noted in each finding and in ARM-C24.
5. Round-2 gap-fill and spot-check pass (2026-09-24): targeted the three items left open in round 1 (the Connect 2023 "State of Compute" talk, the Meta forum power-usage thread, the Quest 3S battery capacity). Gap-fill findings are `ARM-GF2-NNN`. Twenty numeric or version-specific findings were re-checked against their live sources; corrections were made in place in A3-009, A3-010, A3-053, A1-055 and ARM-C21, and a new conflict ARM-C25 was recorded.

**ID conventions:**
- `A1-NNN`, `A2-NNN` and `A3-NNN` are the original topic findings.
- `AS-NNN` is a finding added during synthesis gap-fill.
- `ARM-GF1-NNN` is a finding added in the round-1 coverage pass.
- `ARM-GF2-NNN` is a finding added in the round-2 gap-fill pass.
- `ARM-Cn` is a dossier conflict, which lists the original conflict IDs it merges.
- In a merged finding, the ID line lists all original IDs, for example `A2-013 / A3-005`.

**Evidence tags (exactly one per finding):**
- [doc]: official documentation from Meta, Unity, Qualcomm, Khronos, Arm or Android, an official sample, or a spec.
- [measured]: a source that reports its own measurements. The Notes summarise the test setup.
- [community]: forums, issue trackers, press, wikis, open-source driver code and user-submitted databases. These are leads.

In a merged finding, the tag is that of the strongest source supporting the core claim, and the Notes give per-source tags where they differ. "Derived" in Notes means arithmetic or inference on cited inputs, never a new measurement.

**Goal tags:**
- [T] throughput: more FPS through lower average CPU/GPU frame time.
- [C] consistency: smooth frame delivery, tight p95/p99, no hitches, no thermal decay across a 20-30 minute session.

**[verify on device]** marks a claim that needs hardware confirmation before a skill relies on it. Typical reasons: a vendor claim without a measurement, an inference from phone SoCs or Mesa, or behaviour likely to differ between Quest 2 and Quest 3.

**Applicability conventions used in "Applies to":**
- Devices:
  - `Quest 2` = XR2 Gen 1 / Adreno 650.
  - `Quest 3/3S` = XR2 Gen 2 / Adreno 740v3. The two share one SoC and one level table, and a note is added where the display differs.
  - `Quest Pro` = XR2+ with the Quest 2 level table, one-line scope.
  - `all Quest` = Quest 2 + Quest 3/3S (+ Pro where Meta groups it).
- Unity versions: `Unity 2021.3` (URP 12), `Unity 2022.3` (URP 14), `Unity >= 6000.0` (URP 17+). Individual 6.x versions are named where it matters.
- Other: `URP 14+`; `GLES` and `Vulkan` where the API matters (Vulkan is the default assumption); `OpenXR` when the finding needs the OpenXR backend.

---

## Baseline fact re-verification

| Fact | Status | Detail | Source |
|---|---|---|---|
| Quest 2 CPU = XR2 Gen 1 (SM8250): 1x Cortex-A77 @ 2.84 GHz + 3x A77 @ 2.42 GHz + 4x A55 @ 1.80 GHz | confirmed | Geekbench 6 on Android 14 reports SM8250 with clusters 4 @ 1.80, 3 @ 2.42 and 1 @ 2.84 GHz, and CPU0 = A55 r1p0. Wikipedia's SoC list names the core types (A1-001, A1-002). | https://browser.geekbench.com/v6/cpu/19091540 |
| Quest 2 app CPU clocks | confirmed | Default SustainedHigh is L4 = 1.48 GHz. The app maximum is L8 = 2.42 GHz, Boost only. The 2.84 GHz prime clock is never an app level (A1-003). | https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ |
| Quest 2 apps get 3 CPU cores | confirmed (core IDs inferred) | Dual-core mode "disables one CPU core", CPU L5 is described as the three-core option, and the Perfetto example shows app threads on cores #4-#6. The exact core mask is not published (A1-004). | https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ |
| Quest 2 GPU (Adreno 650) clock; L4 = 525 MHz (older sources say 490 MHz) | confirmed / changed | L4 has been 525 MHz since OS v47/v49 (it was 490 MHz, which is now L3). L5 = 587 MHz and needs dynamic resolution. Pre-2023 tables that show 490 MHz at L4 are stale (A1-007 / A3-087). | https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ ; https://developers.meta.com/horizon/blog/boost-app-performance-525-mhz-gpu-frequency-meta-quest-2/ |
| Quest 2 memory 6 GB (LPDDR4X) | confirmed (type from press) | 6 GB, of which 5.70 GB is visible to Geekbench. The LPDDR4X type rests on Wikipedia citing UploadVR 2020. Meta publishes no memory clock or bandwidth. Meta's logcat page shows `Mem=2092MHz` in its example line and `Mem=1804MHz` in its field table, neither tied to a device (ARM-C24). | https://en.wikipedia.org/wiki/Quest_2 |
| Quest 2 = XR2 / Adreno 650; Quest 3 = XR2 Gen 2 / Adreno 740 ("740v3") | confirmed | Meta names both SoC/GPU pairs. The ovrgpuprofiler doc says "Adreno 740v3", and Mesa lists chip 0x43050b00 "FD740v3" with the comment "Quest 3" (A2-001, A2-002). | https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ ; https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py |
| Quest 3/3S CPU = XR2 Gen 2 with 6 cores | confirmed | Geekbench reports SXR2230P with 6 cores: 2 @ 2.05 GHz + 4 @ 2.36 GHz (A1-013). | https://browser.geekbench.com/v6/cpu/19064415 |
| XR2 Gen 2 core types (commonly quoted as "2 big + 4 little" or A715/A510) | changed | All six cores are Cortex-A78C (MIDR part 0xD4B r0p2). Qualcomm describes them as "4 + 2 performance cores". There are no little cores (ARM-C1). | https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf |
| Quest 3/3S app CPU clocks and Boost level | confirmed / conflicting | Default L4 = 1.92 GHz. Boost is L8 = 2.36 GHz (+23%) per the clock table and the Boost page, but the availability table labels the Boost row as level 6 (2.21 GHz) (ARM-C4). | https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ ; https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ |
| Quest 3S CPU identical to Quest 3 | confirmed | Same Meta level table. Geekbench shows the same SoC, MIDR and cluster clocks; only the board differs ("panther" vs "eureka") (A1-015). | https://browser.geekbench.com/v6/cpu/18989681 |
| Quest 3S GPU identical to Quest 3 | confirmed | Both are Adreno 740v3 with one CPU/GPU level table (A2-001). | https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ |
| Number of app cores on Quest 3/3S | unverifiable | No Meta page states it. The only hint is a community report of 2 Unity job workers on Quest 3, which fits 3 app cores (A1-055; the thread was read via the Wayback Machine in round 2 and has no replies). The Connect 2023 "State of Compute" talk could not be transcribed in round 2 (captions blocked). Needs on-device measurement (Known unknowns). | https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ |
| Quest 3/3S GPU (Adreno 740) clock | confirmed (table) / conflicting (other pages) | Levels table: L4 = 545 MHz, L5 = 599 MHz. Other figures: 640 MHz (UploadVR "Favor GPU", Wikipedia, vr-compare); 690 MHz for Quest 3 and 492 MHz for Quest 3S (Meta ovrgpuprofiler and RenderDoc render-stage pages) (ARM-C3). | https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ |
| Quest 3/3S memory 8 GB | confirmed | 7.55-7.58 GB visible. iFixit identifies LPDDR5 parts. The data rate is not published; Micron press claims LPDDR5X at 8.533 Gbps for the XR2 Gen 2 platform (ARM-GF1-005, ARM-C2). | https://developers.meta.com/horizon/resources/compare-devices/ |
| Quest 3S has a Quest 2-class display | confirmed | Quest 3S is 1832x1920 per eye (20 PPD); Quest 3 is 2064x2208 (25 PPD). Both run at up to 120 Hz on Android 14 (A1-025). | https://developers.meta.com/horizon/resources/compare-devices/ |
| Frame budgets 72/90/120 Hz = 13.9/11.1/8.3 ms | confirmed | Arithmetic, also stated on Meta's mobile performance page. The VRC minimum is 72 FPS (A3-097). | https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ |
| GMEM: Adreno 650 = 1 MB, Adreno 740 = ~2 MB | changed / conflicting | Meta says 1 MB and "approximately 2MB". The Linux kernel gives the A650 1 MiB + 128 KiB and the SD8 Gen 2 A740 (a different chip id from Quest 3) 3 MiB (ARM-C9, ARM-C10). | https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ ; https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/drivers/gpu/drm/msm/adreno/a6xx_catalog.c |
| Graphics API: Vulkan preferred, GLES legacy | changed (stronger) | Meta now calls Vulkan "the required graphics API for Meta Quest development" and keeps its GLES content only for historical reference. Qualcomm also recommends Vulkan over GLES. | https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ |
| The GPU is Adreno, not Mali: only generic TBR concepts transfer | confirmed | These transfer: load/store ops, transient/lazily allocated attachments, in-tile MSAA resolve, subpass merging, overdraw and bandwidth cost. These do not: Mali 16x16 tiles and tile colour budgets, FPK/HSR, Pixel Local Storage, Mali counters, malioc (section 3.8). | https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html ; https://docs.vulkan.org/samples/latest/samples/performance/subpasses/README.html |
| Default ProcessorPerformanceLevel = SustainedHigh (CPU 4-4, GPU 3-5) | confirmed | Level trading makes the CPU range 5-5 and dual-core mode 6-6. See ARM-C5 for which devices support each. | https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ |
| Quest 2 still a current Meta device | changed (docs) | Meta's device comparison page (2026-09-18) lists only Quest 3, Quest 3S and Meta VR Glasses. Quest 2 and Pro remain in the CPU/GPU level tables (A1-025). | https://developers.meta.com/horizon/resources/compare-devices/ |

---

## 1. XR2 Gen 1 vs XR2 Gen 2: CPU layout, app-usable cores and clocks, GPU generation, memory, thermal envelope

### 1.1 XR2 Gen 1 (Quest 2): CPU hardware

- **A1-001** Quest 2 uses the Snapdragon XR2 (Gen 1), a Snapdragon 865 (SM8250) derivative. It has 8 Kryo 585 cores in three clusters:
  - 1x Cortex-A77 "prime" at 2.84 GHz
  - 3x Cortex-A77 "gold" at 2.42 GHz
  - 4x Cortex-A55 "silver" at 1.80 GHz

  [T]
  - Source: https://en.wikipedia.org/wiki/List_of_Qualcomm_Snapdragon_systems_on_chips (accessed 2026-09-24) · Applies to: Quest 2 (Meta gives Quest Pro the same CPU level table) · Evidence: [community]
  - Notes: Geekbench measurements confirm the layout (A1-002, [measured]). The Wikipedia XR table lists TSMC N7+, while its SD865 row lists N7P. The process node does not matter for app tuning.
- **A1-002** A Geekbench 6 run on Quest 2 (Android 14, board "hollywood", uploaded Aug 2026) reports:
  - SoC "Qualcomm SM8250" with 8 cores in clusters of 4 @ 1.80 GHz, 3 @ 2.42 GHz and 1 @ 2.84 GHz
  - 5.70 GB visible memory and governor "performance"
  - CPU0 MIDR part 0xD05 (Cortex-A55 r1p0)
  - single-core 593, multi-core 1747

  [T]
  - Source: https://browser.geekbench.com/v6/cpu/19091540 (accessed 2026-09-24) · Applies to: Quest 2 on current Horizon OS · Evidence: [measured]
  - Notes: Test setup: Geekbench 6 CPU benchmark on a retail Quest 2, Android 14. Geekbench runs as a 2D Android app, not a VR app, so it sees all 8 cores and the prime clock. VR apps are held to Meta's CPU levels (section 1.3) and a 3-core set (A1-004), so do not use Geekbench scores to size VR CPU budgets. Other Quest 2 GB6 uploads score 593-613 single-core.
- **A1-009** Meta's internal tests found that Quest 2's CPU runs about 80% more instructions per cycle than Quest 1's, even though Quest 1's app cores clock higher (2.30 GHz vs 1.48 GHz at level 4). [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 1 → Quest 2 comparison · Evidence: [doc]
  - Notes: Compare devices by clock × IPC, not clock alone. Meta gives no equivalent IPC figure for A77 → A78C (see A1-020).

### 1.2 XR2 Gen 2 (Quest 3/3S): CPU hardware

- **A1-012** Qualcomm's XR2 Gen 2 product brief lists:
  - CPU: "4 + 2 performance cores, up to 2.4/2.0 GHz"
  - memory: 4x16-bit LPDDR5 up to 3.2 GHz
  - an 8 MB system cache, labelled "(LLC)" in the brief
  - UFS 3.1 storage
  - GPU: 2.5x the performance of Gen 1, or up to 50% power savings at Gen 1-level visuals

  [T]
  - Source: https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf (accessed 2026-09-24; 87-73689-1 Rev A, ©2024) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: Calling all six cores "performance cores" contradicts the widely repeated "2 big + 4 little" description (ARM-C1). The brief does not say whether the GPU shares the system cache. Round-1 spot-check (2026-09-24): the brief's text reads "4 + 2 performance cores, up to 2.4/2.0 GHz", "4x16 LP-DDR5 memory, up to 3.2 GHz" and "8 MB system cache (LLC)", as stated.
- **A1-013** Geekbench on Quest 3 and Quest 3S reports:
  - SoC "Qualcomm SXR2230P" with 6 cores
  - Cluster 1 = 2 cores @ 2.05 GHz; Cluster 2 = 4 cores @ 2.36 GHz
  - identifier "ARM implementer 65 … part 3403 revision 2", i.e. MIDR 0x41 / part 0xD4B = Cortex-A78C r0p2
  - 7.55-7.58 GB visible memory

  [T]
  - Source: https://browser.geekbench.com/v6/cpu/19064415 (Quest 3, board "eureka", Android 14) and https://browser.geekbench.com/v6/cpu/18989681 (Quest 3S, board "panther", Android 14) (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [measured]
  - Notes: Test setup: Geekbench 6 CPU on retail units, Android 14, run as a 2D app. In Arm's MIDR scheme 0xD4B is the Cortex-A78C part number. Geekbench reads only CPU0's MIDR. Qualcomm calls both clusters "performance", and Wikipedia's SoC list gives 4x A78C @ 2.36 GHz + 2x A78C @ 2.05 GHz.
- **A1-014** Working conclusion: XR2 Gen 2 in Quest 3/3S is 6x Cortex-A78C, all out-of-order big-class cores, split 4 @ 2.36 GHz + 2 @ 2.05 GHz. There are no little cores, and every core implements Armv8.2-A plus dot product (A1-075). [T] [C]
  - Source: https://en.wikipedia.org/wiki/List_of_Qualcomm_Snapdragon_systems_on_chips (accessed 2026-09-24), confirmed by https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf ([doc]) and https://browser.geekbench.com/v6/cpu/19064415 ([measured]) · Applies to: Quest 3/3S · Evidence: [measured]
  - Notes: Three independent sources agree: the Qualcomm brief, the Geekbench MIDR and the Wikipedia SoC list. The A715/A510 claim on Wikipedia's Quest 3 and 3S pages is uncited and contradicted (ARM-C1). Implication: which cluster a thread lands on matters less than on Quest 2, because the "slow" cluster is still A78C at up to 2.05 GHz. (The original A1-014 tag was [community]; it is raised to [measured] here because the Geekbench MIDR confirms it.)
- **A1-015** Quest 3 and Quest 3S share one CPU/GPU level table in Meta's docs. Geekbench shows the same SoC, MIDR and cluster clocks on both; only the board names differ ("eureka" vs "panther"). Treat them as one CPU target. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: The displays differ (A1-025), so GPU fill cost differs, but CPU budgets are the same. The thermal envelopes are chassis-specific and unpublished (section 1.7).
- **A1-021** CPU benchmarks vary widely from run to run on the same SoC. [C]
  - Geekbench 6 single-core on Quest 3: 573-931 (median 671, 25 results).
  - Quest 3S: 649-977 (median 887, 25 results), on identical silicon.
  - Quest 2: 593-613.
  - Source: https://browser.geekbench.com/search?k=v6_cpu&q=Oculus+Quest+3 and https://browser.geekbench.com/search?k=v6_cpu&q=Oculus+Quest+3S (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [measured]
  - Notes: Test setup: user-uploaded Geekbench 6 results, first results page per query; the medians are derived. The spread comes from OS version, governor and thermal state, and Geekbench runs outside Meta's VR level system. For A/B work, use on-device frame timing at a pinned level, never benchmark aggregates. A Geekbench 7 Quest 3S result (850/2955) also exists: https://browser.geekbench.com/v7/cpu/181337.
- **A1-022** The Quest 3 kernel's CPU governor changed between OS generations. Geekbench reported "walt" under Android 12 (2023) and "schedutil" under Android 14 (2026). [C]
  - Source: https://browser.geekbench.com/v5/cpu/21825265 (Quest 3, Android 12, walt) and https://browser.geekbench.com/v6/cpu/19064415 (Android 14, schedutil) (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [measured] [verify on device]
  - Notes: Meta's level system sets the clock range for VR apps, but thread scheduling within that range comes from the kernel. CPU baselines captured before the Android 14 update may not be comparable.
- **A1-024** According to UploadVR, the XR2 Gen 2 moves several system tasks onto on-chip hardware accelerators, taking them off the CPU and GPU:
  - positional tracking
  - camera passthrough (latency about 50 ms → about 12 ms)
  - SpaceWarp motion extrapolation
  - Super Resolution sharpening

  The same article puts the CPU gain at only 33%, and it describes the CPU as "two performance cores and four efficiency cores". [T]
  - Source: https://www.uploadvr.com/snapdragon-xr2-gen-2/ (accessed 2026-09-24; Sep 27, 2023) · Applies to: Quest 3/3S · Evidence: [community]
  - Notes: The A78C MIDR contradicts the core-type description (ARM-C1). The offload list explains why Quest 3's system services may use less CPU than Quest 2's, yet Meta still measures a 14% CPU cost for passthrough (A1-019). How much app-core time the offload frees is not published.
- **A1-025** Meta's device comparison page (Sep 18, 2026) lists only Quest 3 and Quest 3S in the Quest line. Both use XR2 Gen 2 with 8 GB, run at up to 120 Hz and ship Android 14. Per-eye resolution is 2064x2208 (25 PPD) on Quest 3 and 1832x1920 (20 PPD) on Quest 3S. [T]
  - Source: https://developers.meta.com/horizon/resources/compare-devices/ (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: Quest 2 is no longer on the comparison page but is still in the CPU/GPU level tables. The same page is also reachable at https://developers.meta.com/horizon/essentials/compare-devices/ (cited by A3), which additionally lists Meta VR Glasses (XR2 Gen 3, 12 GB, 2412x2288 per eye).

### 1.3 Cores and clocks an app can actually use on Quest (not phone-SoC configurations)

- **A1-004** VR apps on Quest 2 get three CPU cores. Three statements on Meta's boost page support this:
  - dual-core mode "disables one CPU core" in exchange for higher clocks on the remaining two
  - CPU level 5 is described as the three-core option
  - the Perfetto example shows app threads on cores #4, #5 (UnityMain) and #6

  Combined with the 2.42 GHz cap (A1-003), this points to the app set being cpu4-6, the A77 gold cluster. cpu7 (prime) and cpu0-3 (A55) would then be left for the compositor, tracking and system. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24; updated Sep 2, 2026) · Applies to: Quest 2, Quest Pro · Evidence: [doc] [verify on device]
  - Notes: The core IDs are inferred from Meta's screenshot description and the clock table; Meta does not publish the mask. To check: `adb shell cat /proc/<pid>/status | grep Cpus_allowed_list`, plus Perfetto CPU tracks. The app-core count on Quest 3/3S is unpublished (Known unknowns).
- **A1-003** On Quest 2 the highest CPU clock an app can get is 2.42 GHz (CPU level 8, Boost only). That is the gold-cluster maximum; the prime core's 2.84 GHz never appears as an app level. The default SustainedHigh clock is level 4 = 1.48 GHz, about 61% of 2.42 GHz. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24; page updated Sep 2, 2026) · Applies to: Quest 2, Quest Pro; all Unity versions · Evidence: [doc]
  - Notes: The 61% ratio is derived. Budget the main thread at 1.48 GHz, not the spec-sheet 2.84 GHz.
- **A1-005 / A1-006 / A1-016 / A1-017 / A2-007 / A3-068 / A3-069** CPU and GPU level-to-clock tables. Apps choose levels, not clocks (section 6.1), and these are the only clocks an app gets. [T] [C]

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

  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24; page updated 2026-09-02; native mirror https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/) · Applies to: Quest 2 and Quest Pro (identical tables); Quest 3/3S (shared table); all Unity versions · Evidence: [doc]
  - Notes:
    - Default SustainedHigh uses CPU L4: 1.48 GHz on Quest 2 (61% of 2.42 GHz) and 1.92 GHz on Quest 3/3S (81% of the 2.36 GHz cluster maximum). Both ratios are derived.
    - Governor thresholds are in A1-037 / A2-008 / A3-070. Availability conditions are in A3-071 (Quest 2) and A1-018 / A3-072 (Quest 3/3S); A1-005 and A1-017 carry the same availability rows.
    - Quest 2 GPU L5 (587 MHz) equals the SD865 phone's Adreno 650 maximum on Wikipedia's SoC list, so L5 is the full phone clock (A1-006).
    - Quest 3/3S CPU L5 (2.05 GHz) equals the 2-core cluster's maximum. L6 (2.21 GHz) and L8 (2.36 GHz) exceed it, so a thread running at those clocks must be on the 4-core cluster (derived, A1-016) [verify on device].
    - The Quest 3/3S GPU clock range from L0 to L5 is 599/285 ≈ 2.1x (derived, A2-008).
    - Meta's MQDH screenshot (Quest 2 at CPU L4 / 1.478 GHz, GPU L3 / 490 MHz) and its dynamic-resolution log `CPU4/GPU=4/4,1478/525MHz` match the table (A3-068).
    - The top Quest 3 GPU clock is contested elsewhere (640/690 MHz): ARM-C3. The Quest 3/3S Boost level label is contested: ARM-C4. The Quest 2 L4 clock changed from 490 to 525 MHz (A1-007 / A3-087).
    - The same page also carries a Meta VR Glasses table (A3-074), which is out of scope. Meta warns that the same numeric level on different headsets does not mean the same clock, throughput or sustained thermal behaviour.
- **A1-026** Main-thread cycle budgets at the default level-4 clock (clock × frame time, derived): [T]

  | Device (L4 clock) | 72 Hz | 90 Hz | 120 Hz |
  |---|---|---|---|
  | Quest 2 (1.48 GHz) | 20.6 M | 16.4 M | 12.3 M |
  | Quest 3/3S (1.92 GHz) | 26.7 M | 21.3 M | 15.9 M |

  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes: Derived. The main thread cannot use the whole frame: it needs slack for the render thread and the compositor handoff. Use these figures to turn a microbenchmark cycle count into a share of the frame (for example, 1 M cycles ≈ 0.52 ms on Quest 3 at L4). In MR on Quest 3/3S the CPU is capped at L3 (A1-018 / A3-072), which gives about 22.9 M cycles per frame at 72 Hz.
- **A3-097** Frame budgets are 13.9 ms at 72 Hz, 11.1 ms at 90 Hz and 8.3 ms at 120 Hz. The VRC minimum is 72 FPS. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ (accessed 2026-09-24; page updated 2024-12-09) · Applies to: all Quest · Evidence: [doc]
  - Notes: When throttling cuts GPU clocks, for example from L4 545 MHz to L2 456 MHz on Quest 3 (-16%, derived), a frame that used 90% of the budget will miss. Battery Saver forces 72 Hz (A3-092), which changes every per-frame budget.

### 1.4 GPU generation: Adreno 650 (A6xx) vs Adreno 740v3 (A7xx)

- **A2-001** Quest 3 and Quest 3S use the same GPU, the Adreno 740v3. On Quest 2, Quest 3 and Quest 3S, ovrgpuprofiler prints one surface line that covers both views of a multiview surface. Frame costs from a 3 and a 3S are therefore GPU-comparable at equal clocks. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 3/3S; any Unity version · Evidence: [doc]
  - Notes: The eye-buffer resolution differs between the 3 and the 3S, so compare ms per bin or per pixel, not ms per frame. How to read multiview surfaces per device is in A3-034.
- **A2-002** Mesa lists the Quest 3 GPU as chip id 0x43050b00 "FD740v3"; the Snapdragon 8 Gen 2 Adreno 740 is 0x43050a01. The Quest part has the same topology parameters as the phone 740:
  - 6 colour cache units (CCUs)
  - tile alignment 96x32 and maximum tile 2016x2032
  - 32 visibility-stream pipes
  - 32 KB compute shared memory
  - fibers_per_sp = 128*2*16

  It differs only in a render-backend debug register and a texture-pipe UBWC flag hint. SD8 Gen 2 phone data is therefore the closest proxy for Quest 3, but it is not identical. [T] [C]
  - Source: https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [community] [verify on device]
  - Notes: Do not copy phone-740 numbers (GMEM 3 MiB, clocks, benchmarks) to Quest without checking.
- **A2-003** Mesa parameters for the Adreno 650:
  - a6xx gen3, 3 CCUs
  - tile alignment 96x16, maximum tile 1024x1024
  - reg_size_vec4 = 64
  - scalar ALU present; no 8-bpp UBWC

  The a7xx base (Adreno 740) has reg_size_vec4 = 96, about 1.5x the per-SP register budget, plus LPAC, "early preamble" and attachment shading-rate support. [T]
  - Source: https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py (accessed 2026-09-24) · Applies to: Quest 2 (650), Quest 3/3S (740) · Evidence: [community]
  - Notes: This matches Chips and Cheese's 64 KB (A730) vs 96 KB (X1, "741") register file per scheduler partition (A2-006). Implication: a shader at the GPR limit on Quest 2 has more occupancy headroom on Quest 3.
- Qualcomm's public docs give no shader-processor count, FLOPS, GMEM size or clock for either GPU (A2-004, section 3.1). The architecture-level differences that matter for tuning are:
  - GMEM: about 1 MB vs about 2 MB (A2-010 / A3-004)
  - concurrent binning and dual LRZ buffers, A7xx only (A2-026, A2-027)
  - bidirectional LRZ, A7xx (A2-031)
  - LPAC async compute, 740 only (A2-094)
  - the 32-entry A7x vertex cache (A2-049 / A3-019)
  - A7x instruction and binding cliffs (A2-070)
  - `VK_QCOM_multiview_per_view_render_areas` / `_viewports`, Quest 3/3S only (A3-043)

### 1.5 Memory type and bandwidth

- **A1-008** Quest 2 has 6 GB of LPDDR4X. For the SD865-family memory controller (LPDDR4X, 4x16-bit at 2133 MHz), Wikipedia gives a theoretical peak of 34.13 GB/s. Meta publishes no memory clock or bandwidth for Quest 2. [T]
  - Source: https://en.wikipedia.org/wiki/Quest_2 and https://en.wikipedia.org/wiki/List_of_Qualcomm_Snapdragon_systems_on_chips (accessed 2026-09-24) · Applies to: Quest 2 · Evidence: [community]
  - Notes:
    - No published number was found for the DRAM data rate Meta actually configures. To measure it, run a Burst streaming-copy microbenchmark pinned to the app cores.
    - Meta's current logcat-stats example line shows `Mem=2092MHz` next to Quest 2-consistent CPU/GPU clocks, but the same page's field table shows `Mem=1804MHz` (AS-001, A3-053, ARM-GF1-004; ARM-C24). If 2092 MHz is a Quest 2 LPDDR4X clock, the derived peak is 2092 MHz × 2 transfers × 8 B ≈ 33.5 GB/s, close to the 34.13 GB/s figure; 1804 MHz would give about 28.9 GB/s (derived). The devices are unnamed [verify on device].
    - No iFixit chip ID was found for the Quest 2 RAM: iFixit teardown guide 148713 has no steps in its API.
- **A1-023** Quest 3 and Quest 3S use 8 GB of LPDDR5. iFixit's chip IDs list:
  - Quest 3: likely an SK hynix H58G66BK8BX105
  - Quest 3S: a Micron MT62F1G64D4EK-026 WT:B
  - both: an SK hynix HN8T05DEHKX073 128 GB NAND

  [T]
  - Source: https://www.ifixit.com/Guide/Meta+Quest+3+Chip+ID/165932 and https://www.ifixit.com/Guide/Meta+Quest+3S+Chip+ID/178132 (accessed 2026-09-24 via the iFixit API) · Applies to: Quest 3/3S · Evidence: [community]
  - Notes: Qualcomm specifies 4x16-bit LPDDR5 up to 3.2 GHz (A1-012). If "3.2 GHz" means 6400 MT/s on a 64-bit bus, the peak is 51.2 GB/s. That figure is derived, and this reading of "3.2 GHz" is an assumption. The data rate Meta actually configures is not published. Conflicting LPDDR5X and LPDDR4X claims are in ARM-C2.
- **A3-099** Uncited community specs list Quest 3 memory as LPDDR5 at 4200 MT/s (68 GB/s) and Quest 3S as LPDDR4X at 2600 MT/s (42 GB/s). If correct, Quest 3S would have about 40% less peak DRAM bandwidth than Quest 3 (derived) for a smaller eye buffer. [T] [C]
  - Source: https://en.wikipedia.org/wiki/Meta_Quest_3 and https://en.wikipedia.org/wiki/Meta_Quest_3S (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [community] [verify on device]
  - Notes: Meta and Qualcomm publish neither figure. Both claims are contested (ARM-C2):
    - 4200 MT/s on a 64-bit bus gives 33.6 GB/s, not 68 GB/s (derived).
    - iFixit identifies an LPDDR5 part in the Quest 3S (A1-023), not LPDDR4X.

    Check `Mem=` in logcat or MEM F in OVR Metrics on each device (A3-053).
- **ARM-GF1-005** Micron press coverage (Oct 2023) says Micron's 8 GB LPDDR5X at 8.533 Gbps and its UFS 3.1 storage are "optimized for" the XR2 Gen 2 and links them to Quest 3. [T]
  - Source: https://www.tweaktown.com/news/93872/microns-low-power-memory-optimized-for-snapdragon-xr2-gen-2-platform-vr-and-mixed-reality/index.html (accessed 2026-09-24; 2023-10-19) · Applies to: XR2 Gen 2 platform; Quest 3 link asserted by the press piece · Evidence: [community] [verify on device]
  - Notes: This is a supplier's platform-validation claim, not proof of the rate Quest runs at. It conflicts with Qualcomm's own brief ("4x16 LP-DDR5 memory, up to 3.2 GHz") and with iFixit's SK hynix part in Quest 3; iFixit's Micron part is in Quest 3S (ARM-C2). If Quest ran 8533 MT/s on a 64-bit bus, the peak would be about 68.3 GB/s (derived), which matches the "68 GB/s" in Wikipedia's Quest 3 infobox but not its "4200 MT/s". Do not budget from any of these numbers until a Quest measurement exists.

### 1.6 Device-to-device scaling claims

- **A1-020** Meta states that Quest 3 has twice the GPU power, 33% more CPU and over 30% more memory than Quest 2. The default eye buffer became 1680x1760, about 30% larger than Quest 2's. [T]
  - Source: https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ (accessed 2026-09-24; Oct 11, 2023) · Applies to: Quest 3 vs Quest 2 · Evidence: [doc]
  - Notes: The level-4 clock ratio is 1.92/1.48 = 1.30 (derived), so most of the +33% CPU gain is clock, not IPC. Qualcomm's GPU claim (2.5x, A1-012) is higher than Meta's (2x). UploadVR (A1-024) also puts the CPU gain at 33%. No independent like-for-like GPU measurement was found (Known unknowns). The Quest 3 default eye buffer of 1680x1760 is also stated on Meta's tiled-GPU page (A2-020), which resolves the A3 gap on the Quest 3 default (ARM-C21).

### 1.7 Thermal envelope

No source gives a TDP, sustained SoC power or thermal envelope for Quest 2, Quest 3 or Quest 3S; a round-1 targeted search (2026-09-24) found none either. A1-015 notes the envelopes are chassis-specific and unpublished. What is published is the behaviour of the level system under heat (section 6.3) and the power signals (section 6.4). For the power budget, the only device-level figures are battery life and battery capacity (below), one community power-meter measurement per scenario on Quest 3 (ARM-GF2-002), Meta's generic 3-6 W mobile-GPU class (ARM-GF1-006) and the DRAM energy rules of thumb (section 5.1).

- **A3-098** Meta lists roughly 2 hours of battery life for Quest 3 and about 2.5 hours for Quest 3S, and 8 GB RAM on both. No published battery-drain-versus-level curve exists. [C]
  - Source: https://developers.meta.com/horizon/essentials/compare-devices/ (accessed 2026-09-24; page updated 2026-09-18) · Applies to: Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes: Measure drain against level with the BAT C / POW C CSV columns, keeping Meta's caveat in mind (A3-082).
- **ARM-GF1-002** iFixit's teardown, as reported by UploadVR, found a 19.44 Wh battery in Quest 3, against 14 Wh in Quest 2. Combined with Meta's roughly 2 hours of Quest 3 battery life (A3-098), that implies an average whole-headset draw of about 9.7 W (derived: 19.44 Wh / 2 h). This covers displays, cameras, tracking, audio and radios as well as the SoC, so it is an upper bound on SoC power, not a thermal design power. [C]
  - Source: https://www.uploadvr.com/quest-3-teardown-battery/ (accessed 2026-09-24; 2023-10-13) and https://developers.meta.com/horizon/essentials/compare-devices/ (accessed 2026-09-24) · Applies to: Quest 3 (Quest 2 battery for contrast; Quest 3S in ARM-GF2-001) · Evidence: [community] [verify on device]
  - Notes: No Meta or Qualcomm TDP exists (Known unknowns). Meta's tiled-GPU page gives 3-6 W as the typical mobile-GPU class (ARM-GF1-006), which is consistent with the GPU taking a large share of a ~10 W budget, but that split is not published. Use BAT C / POW C at pinned levels to measure the app's share. Round-2 spot-check (2026-09-24): UploadVR's teardown article still reads 19.44 Wh (Quest 3) and 14 Wh (Quest 2). A later UploadVR article gives Quest 3 as 18.9 Wh (ARM-C25). A per-scenario measured power table now exists (ARM-GF2-002).
- **ARM-GF2-001** Quest 3S battery: a leaked regulatory label gives 16.74 Wh, which UploadVR places between Quest 2 (14 Wh) and Quest 3. Combined with Meta's roughly 2.5 hours for Quest 3S (A3-098), the implied average whole-headset draw is about 6.7 W (derived: 16.74 Wh / 2.5 h), against about 9.7 W for Quest 3 (ARM-GF1-002). [C]
  - Source: https://www.uploadvr.com/quest-3s-images-leak-reveal-battery-size-no-headphone-jack/ (accessed 2026-09-24; 2024-09-14) and https://developers.meta.com/horizon/essentials/compare-devices/ (accessed 2026-09-24; page updated 2026-09-18) · Applies to: Quest 3S · Evidence: [community] [verify on device]
  - Notes: The label was seen in leaked pre-release photos, not in a teardown; the retail capacity was not confirmed by iFixit or Meta in the sources read, and Wikipedia's Quest 3S infobox leaves the power field empty. Secondary sites quote 4,324 mAh, which was not found in a primary source. The two derived averages come from Meta's rounded battery-life figures, whose workloads are unstated, so the 3S/3 power ratio (about 0.7) must not be read as an SoC power difference: the SoC and level table are identical (A1-015), and the display, optics and passthrough resolution differ. Both chassis run the same app-level clocks, so any difference in sustained thermal headroom must be measured (A3-093 recipe, run on each device).
- **ARM-GF2-002** A Meta community-forum user measured Quest 3 power at the USB-C input with a fully charged headset (so input ≈ system draw) on OS 57.0 (2023-10-18), at 120 Hz. Results: [C]

  | Scenario (Quest 3, 120 Hz, v57) | Measured input power | Author's implied battery life (19.44 Wh) |
  |---|---|---|
  | Standby | 0.17-0.7 W @5 V | 44.7 h |
  | Browsing in VR | 7.6-8.2 W @9 V | 2.5 h |
  | Standalone VR game (Into the Radius, Quest 3-enhanced) | 7.5-9.0 W @9 V | 2.4 h |
  | Browsing in MR (passthrough) | 9.6-10.2 W @9 V | 2.0 h |
  | Air Link PC VR (Fallout 4 VR) | 10.5-10.7 W @9 V | 1.8 h |
  | Standalone MR game (First Encounters) | 10.5-12.0 W @9 V | 1.7 h |

  - Source: https://web.archive.org/web/20250108162626/https://communityforums.atmeta.com/t5/Talk-VR/Quest-3-Power-Usage-Tests-and-Approximate-Battery-Life/td-p/1094433 (results table is an image in the first post; live URL https://communityforums.atmeta.com/t5/Talk-VR/Quest-3-Power-Usage-Tests-and-Approximate-Battery-Life/td-p/1094433 returns 403) (accessed 2026-09-24; posted 2023-10-18, edited 2024-04-07) · Applies to: Quest 3, Horizon OS v57 (launch era), 120 Hz · Evidence: [measured] [verify on device]
  - Notes: Test setup: a retail Quest 3 on OS 57.0.0.279, fully charged and powered through an inline USB-C power meter, one run per scenario, results shown as ranges. The battery-life column is the author's arithmetic from stated capacity, not a timed rundown. Charging rows (12-20 W) are omitted because they include charge current. Useful deltas (derived): MR scenarios draw about 2-3 W more than the matching VR scenario, which is consistent with Meta's statement that passthrough costs GPU and CPU headroom (A1-019) and with passthrough capping the levels (A1-018). A VR game at about 8-9 W agrees with the ~9.7 W battery-life average (ARM-GF1-002). The measurement is whole-device (displays, cameras, radios), taken on a launch-era OS; re-measure on the current OS. Out-of-scope rows (Air Link) are listed only because they sit in the same table.
- **ARM-GF2-003** Meta states that most of Quest 3's battery power goes to running the CPU and GPU, and it frames performance as a zero-sum budget: developers should lower clock levels when the CPU or GPU is not fully used. The same post notes that extra render passes (blur, bloom, HDR, realtime shadows, deferred) cost more on this architecture. [T] [C]
  - Source: https://developers.meta.com/horizon/blog/optimizing-for-success-meta-quest-3-gdc/ (accessed 2026-09-24; 2024-03-21) · Applies to: Quest 3 (3S shares the SoC) · Evidence: [doc]
  - Notes: No share or wattage is given. Taken with ARM-GF2-002 and the DRAM energy rules (section 5.1), this is Meta's own support for treating SoC power, including DRAM traffic, as the controllable part of the thermal budget.

### 1.8 Out-of-scope SoCs (disambiguation)

- **A1-027** The XR2+ Gen 2 is not in any Quest. It runs "2.4 GHz on all CPU cores" and has a 15% higher GPU maximum than XR2 Gen 2, with the same memory specification. Spec sheets and benchmarks for the XR2+ Gen 2 do not describe Quest 3/3S. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/87-73622-1_REV_A_Snapdragon_XR2__Gen_2_Platform_Product_Brief.pdf (accessed 2026-09-24) · Applies to: disambiguation only · Evidence: [doc]
  - Notes: Also out of scope are Meta VR Glasses (XR2 Gen 3, 12 GB; A3-074) and Qualcomm's Snapdragon Reality Elite (Q2 2026).
- **A3-074** Meta VR Glasses (XR2 Gen 3) levels:
  - CPU: L0 0.81, L1 1.23, L2 1.52, L3 1.79, L4 2.09, L5 2.15, L6 2.29 and L8 2.71 GHz
  - GPU: L0 318, L1 366, L2 495, L3 576, L4 633 and L5 690 MHz
  - CPU 4 and GPU 3-4 are unavailable with passthrough
  - there is no trading or dual-core mode

  [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Meta VR Glasses only (out of scope; recorded because it sits on the same page as the Quest tables) · Evidence: [doc]
  - Notes: Meta warns that the same numeric level on different headsets does not mean the same clock, throughput or sustained thermal behaviour. The Glasses' 690 MHz GPU L5 is the likely origin of the "Quest 3 at 690 MHz" statement (ARM-C3). Agents reading that page can confuse the tables.

---

## 2. ARM CPU: thread placement, job workers, caches, data layout, NEON via Burst

The CPU measurement tools (Perfetto CPU scheduling, OVR Metrics CPU L, the logcat TA/SP fields) are in section 7. Pin a known level before any CPU A/B test (A1-085).

### 2.1 OS core reservation and thread registration

- **A1-010** Quest 1 (Snapdragon 835) set the precedent:
  - Apps had full access to 3 of the 4 gold cores; the fourth was reserved for TimeWarp and system services.
  - The silver cores were reserved for tracking and system software.
  - Of 4 GB RAM, 2.75 GB was available to apps.

  [C]
  - Source: https://developers.meta.com/horizon/blog/down-the-rabbit-hole-w-oculus-quest-the-hardware-software/ (accessed 2026-09-24; May 2, 2019) · Applies to: Quest 1 (historical precedent) · Evidence: [doc]
  - Notes: Pre-2023, and a different device. It is cited only because Meta kept the same pattern of 3 app cores plus a reserved compositor core on Quest 2 (A1-004).
- **A1-011** A 2019 VrApi log from Quest 1 shows `TA=0/E0/0` and `SP=N/F/N`. The main thread's affinity mask was 0xE0 (cores 5-7) and it ran under SCHED_FIFO, while TimeWarp ran under SCHED_NORMAL. [C]
  - Source: https://developers.meta.com/horizon/blog/ovr-metrics-tool-vrapi-what-do-these-metrics-mean/ (accessed 2026-09-24; Oct 25, 2019) · Applies to: Quest 1 with VrApi (deprecated) · Evidence: [doc]
  - Notes: Pre-2023. This is the only Meta-published log with an explicit app core mask. The current logcat-stats page still documents the TA/SP fields (AS-001), so the same check may work for OpenXR apps [verify on device].
- **A1-042** The OpenXR extension XR_KHR_android_thread_settings (extension #4, revision 6) defines `xrSetAndroidApplicationThreadKHR(XrSession, XrAndroidThreadTypeKHR, uint32_t threadId)`. [C]
  - Thread types:
    - APPLICATION_MAIN (1): time-critical CPU work
    - APPLICATION_WORKER (2): background CPU work
    - RENDERER_MAIN (3): time-critical graphics work
    - RENDERER_WORKER (4)
  - Errors: XR_ERROR_ANDROID_THREAD_SETTINGS_FAILURE_KHR and XR_ERROR_ANDROID_THREAD_SETTINGS_ID_INVALID_KHR.
  - Source: https://registry.khronos.org/OpenXR/specs/1.1/html/xrspec.html#XR_KHR_android_thread_settings (accessed 2026-09-24; spec 1.1.63) · Applies to: all OpenXR Android runtimes, including Quest · Evidence: [doc]
  - Notes: The spec leaves the runtime's response (priority, scheduling class, core placement) undefined. Meta documents one effect: registration sets the scheduling priority shown in `SP=` (AS-001).
- **A1-043** Meta's own OpenXR sample framework registers its threads explicitly. In XR_SESSION_STATE_READY, right after `xrBeginSession` succeeds, it calls `xrSetAndroidApplicationThreadKHR` for APPLICATION_MAIN (the main thread's `gettid()`) and for RENDERER_MAIN. It sets the XR_EXT_performance_settings CPU/GPU levels at the same point. [C]
  - Source: https://raw.githubusercontent.com/meta-quest/Meta-OpenXR-SDK/main/Samples/SampleXrFramework/Src/XrApp.cpp (accessed 2026-09-24; last commit Feb 12, 2026, "v85") · Applies to: native OpenXR on all Quest · Evidence: [doc]
  - Notes: The Quest runtime therefore supports the extension, and Meta treats registration as standard practice. A native plugin that owns a time-critical thread of its own (for example audio or physics) should register it as APPLICATION_WORKER.
- **A1-044** No Unity documentation or changelog says that Unity's OpenXR plugin or Meta's OVRPlugin registers UnityMain or UnityGfxDeviceW through XR_KHR_android_thread_settings. The com.unity.xr.openxr changelog, up to 1.16, mentions the extension only once: a spelling fix to the AndroidThreadSettingsFailureKHR enum in 1.14.0 (2024-12-13). [C]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: Unity 2021.3 through 6.6 with the OpenXR plugin · Evidence: [doc] [verify on device]
  - Notes: No published statement was found. Two ways to measure:
    - During play, run `adb shell ps -T -p <pid> -o TID,NAME,SCH,RTPRIO,PRI,NI,PSR`. Check whether UnityMain and UnityGfxDeviceW show a real-time policy (SCH 1/2 with an RTPRIO) or normal scheduling, and cross-check thread states in Perfetto. Field support depends on the toybox version.
    - A cheaper check is the `SP=` field of the VrApi logcat line (AS-001).
- **AS-001** Meta's current "Logcat stats" page (updated 2025-07-31) sits under Native and OpenXR > OpenXR Mobile SDK, and it still documents the VrApi logcat line.
  - `TA=`: the ATW, main and render thread affinities. Meta says they help verify that threads run on big cores, and advises against setting affinity by hand.
  - `SP=`: the scheduling priority of the same three threads. `F` = SCHED_FIFO (highest), `N` = SCHED_NORMAL. Main and render thread priority can be set with `vrapi_SetPerfThread` or through the OpenXR `XR_KHR_android_thread_settings` extension.
  - `OC=`: no longer used, because current Quest CPUs cut core energy without taking cores offline.
  - Other fields: `Mem=` = speed of the memory; `Free=` = available memory as reported by Android; `PLS=` = power level (NORMAL 0, SAVE 1, DANGER 2); `Temp=` = battery and sensor temperature; `LP=` = Battery Saver on (1) or off (0); `DVFS=` is currently never enabled.
  - Example line: `FPS=72/72,Prd=38ms,Tear=0,Early=0,Stale=0,Stale2/5/10/max=0/0/0/0,VSnc=1,Lat=-1,Fov=0,CPU4/GPU=2/2,1171/441MHz,OC=FF,TA=0/0/0,SP=N/N/N,Mem=2092MHz,Free=2975MB,PLS=0,Temp=32.2C/0.0C,TW=1.25ms,App=4.49ms,GD=0.00ms,CPU&GPU=12.96ms,LCnt=2(DR72,LM2),GPU%=0.43,CPU%=0.37(W0.50),DSF=1.00,CFL=19.79/21.54,ICFLp95=20.94,LD=0,SF=1.00,LP=0,DVFS=0,ShrpLCnt=5,ShrpR=1.000,SSLCnt=3/3`

  [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ (accessed 2026-09-24; page updated 2025-07-31) · Applies to: all Quest (OpenXR Mobile SDK section of Meta's docs) · Evidence: [doc] [verify on device]
  - Notes:
    - This was a gap-fill check during synthesis, made to resolve ARM-C19. The page does not say in so many words that OpenXR apps emit the line, so confirm with `adb logcat -s VrApi` on a Unity OpenXR build.
    - If the line is present, `SP=` answers the A1-044 question directly: F in the main/render slots means registered real-time threads; `N/N/N` means normal scheduling.
    - The example's `CPU4/GPU=2/2,1171/441MHz` is close to the Quest 2 L2 clocks (1.17 GHz / 442 MHz). Its `Mem=2092MHz` is one of two memory-clock values on the page: the field-definition table uses `Mem=1804MHz` (round-1 spot-check, ARM-GF1-004, ARM-C24). Neither is tied to a named headset.
- **A1-046** Legacy VrApi had `vrapi_SetPerfThread`, which put the main and render threads on SCHED_FIFO; UE4 called it automatically. VrApi and the Mobile SDK have been unsupported since Aug 31, 2022. [C]
  - Source: https://developers.meta.com/horizon/blog/ovr-metrics-tool-vrapi-what-do-these-metrics-mean/ (accessed 2026-09-24; Oct 25, 2019) · Applies to: legacy only · Evidence: [doc]
  - Notes: Pre-2023. Forum advice that mentions `vrapi_SetPerfThread` is stale for OpenXR apps; the OpenXR equivalent is A1-042. The original note also called the `TA=`/`SP=` log fields stale for OpenXR apps. The 2025 logcat-stats page contradicts that: it still documents those fields and ties `SP=` to the OpenXR extension (AS-001, ARM-C19).
- **A1-047** Meta's 2019 advice on thread affinity: binding the main/render threads to a core makes the CPU% metric easier to read, but it makes the whole system less efficient, because the scheduler is good at keeping throughput high. Bind threads only while debugging. The same post notes that VrApi CPU% reported the worst core. [C]
  - Source: https://developers.meta.com/horizon/blog/ovr-metrics-tool-vrapi-what-do-these-metrics-mean/ (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Pre-2023, but consistent with Unity's 2026 guidance (A1-049) and with the 2025 logcat page's advice against manual affinity (AS-001). A main thread that migrates between cores can hide in averaged utilization.
- **A1-048** In the VrApi era, the Quest compositor thread (TimeWarp) reported SCHED_NORMAL and affinity 0, unlike other Android VR devices, where it ran SCHED_FIFO. That fits a design where the compositor owns a reserved core instead of preempting app threads. [C]
  - Source: https://developers.meta.com/horizon/blog/ovr-metrics-tool-vrapi-what-do-these-metrics-mean/ (accessed 2026-09-24) · Applies to: Quest 1 (VrApi era) · Evidence: [doc]
  - Notes: Pre-2023. How the compositor is scheduled on Quest 2/3 today is not published (Known unknowns).

### 2.2 Unity main, render and job-worker threads on big/little (Quest 2) and all-big (Quest 3/3S) CPUs

- **A1-049** Unity sets Android thread affinity and priority from the device's CPU topology. It normally takes core capacity and the big/little assignment from the OS. When the OS does not provide them, Unity classifies a core as "big" if its capacity is at least 2x the slowest core's, adjustable with `-platform-android-cpucapacity-threshold [0-1024]`. Unity advises keeping its defaults, because changes can hurt other devices or later OS versions. [T] [C]
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/android-thread-configuration.html (accessed 2026-09-24; same text at /2021.3/, /2022.3/, /6000.6/) · Applies to: Unity 2021.3 through 6.6 Android players on Quest · Evidence: [doc]
  - Notes: Horizon OS updates change the scheduler (A1-022) and frame timing (A1-039), so custom affinities are a maintenance liability on Quest.
- **A1-050** On Quest 3/3S every core is an A78C, and the two clusters' maximum clocks differ by only 1.15x (2.36 vs 2.05 GHz). Under Unity's 2x fallback rule no core would count as big, so the `big` / `little` affinity aliases may not select what you expect. On Quest 2 the A77/A55 split does meet the 2x rule. [C]
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/android-thread-configuration.html (accessed 2026-09-24) · Applies to: Quest 3/3S (Quest 2 for contrast) · Evidence: [doc] [verify on device]
  - Notes: This is an inference from the documented rule plus A1-013; capacity values provided by the OS may change the outcome. Geekbench lists the 2 @ 2.05 GHz cluster first, which suggests it is cpu0-1 and the 4 @ 2.36 GHz cluster is cpu2-5. If you use affinity arguments on Quest at all, read the app's allowed CPU set first (`Cpus_allowed_list`) and use explicit masks within it.
- **A1-051** Unity's configurable threads and their startup arguments: [T] [C]

  | Thread | Arguments |
  |---|---|
  | Main | `-platform-android-unitymain-priority` / `-platform-android-unitymain-affinity` |
  | Job workers | `-platform-android-jobworker-priority` / `-platform-android-jobworker-affinity [v] [v1 v2 …]`, plus `-job-worker-count` |
  | Render thread | `-platform-android-gfxdeviceworker-priority` / `-platform-android-gfxdeviceworker-affinity` |

  Priority ranges from −20 (highest) to 19. Affinity accepts `any` / `little` / `big` or a hex/binary mask, with bit index = CPU index.
  - Source: https://docs.unity3d.com/6000.0/Documentation/Manual/android-thread-configuration.html (accessed 2026-09-24) · Applies to: Unity 2021.3 through 6.6 · Evidence: [doc]
  - Notes: Pass these arguments from a custom UnityPlayerActivity (https://docs.unity3d.com/6000.0/Documentation/Manual/android-custom-activity-command-line.html). Unity warns that some devices and OS versions ignore them. With Graphics Jobs on, job workers also call the graphics API. The only case where `-job-worker-count` obviously applies is reducing workers in Quest 2 dual-core builds (derived).
- **A1-052** A Unity Discussions report (Jul 2026, Unity 2022.3, a OnePlus phone) found that render-thread affinity arguments gave inconsistent placement. The arguments were passed with `adb shell am start … -e unity '-platform-android-gfxdeviceworker-affinity big'`. The threads seen in traces were UnityMain, UnityGfxDeviceW (Unity's render thread) and RenderThread (Android's HWUI thread, not Unity's). [C]
  - Source: https://discussions.unity.com/t/android-thread-configuration-render/1731103 (accessed 2026-09-24) · Applies to: Unity 2022.3 on Android (not Quest-specific) · Evidence: [community] [verify on device]
  - Notes: In Perfetto on Quest, UnityGfxDeviceW is the Unity render thread to watch, not "RenderThread". The report's `-e unity '<args>'` intent extra is a quick way to try arguments without writing a custom activity.
- **A1-053** `JobsUtility.JobWorkerCount` defaults to `JobWorkerMaximumCount`. [T] [C]
  - On Android, Unity adjusts it automatically when the OS reports a change in available cores, for example in power-saving mode.
  - Setting it manually stops the automatic adjustment until `ResetJobWorkerCount()` is called.
  - It can be lowered at runtime but not raised above the maximum.
  - Source: https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerCount.html (accessed 2026-09-24; identical in 2021.3) · Applies to: Unity 2021.3 through 6.6 · Evidence: [doc]
  - Notes: Do not hard-set JobWorkerCount on Quest without a measured win. Doing so disables the automatic response to changes in core availability (dual-core mode, OS features).
- **A1-054** `JobWorkerMaximumCount` is read-only at runtime and can be set only with `-job-worker-count`. Unity ignores values above the runtime's platform default, so on Quest the worker count can be lowered but never raised. [T]
  - Source: https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerMaximumCount.html (accessed 2026-09-24; identical in 2021.3) · Applies to: Unity 2021.3 through 6.6 · Evidence: [doc]
  - Notes: Unity's job system overview says the job system creates only as many worker threads as the CPU cores can use, and balances work between them by work stealing (https://docs.unity3d.com/6000.0/Documentation/Manual/job-system-overview.html).
- **A1-055** Unity publishes no default JobWorkerMaximumCount for Quest. A Meta community forum thread reported 2 job workers on Quest 3 with Unity 2022.3.15. Two workers fits a 3-core app set minus the main thread. [T]
  - Source: https://web.archive.org/web/20260214200619/https://communityforums.atmeta.com/discussions/dev-quest/unity-quest-3-multithreaded-performance/1132006 (live forum returns 403; archived copy read in round 2) (accessed 2026-09-24) · Applies to: Quest 3, Unity 2022.3.15 · Evidence: [community] [verify on device]
  - Notes: Round-2 check: the archived thread (posted about two years before the Feb 2026 snapshot, forum now read-only) contains only the question, "only 2 Job workers available" in Unity 2022.3.15 on Quest 3, with no replies and no Meta answer. It does not say how the count was read or whether the build used OpenXR or OVRPlugin. Unconfirmed. To measure, log `JobsUtility.JobWorkerMaximumCount`, `JobWorkerCount` and `SystemInfo.processorCount` at startup on each device and Unity version. If the count is 2, IJobParallelFor scaling tops out near 3x (main + 2 workers). Wide jobs would then mainly hide latency rather than add throughput (derived).
- **A1-056** Meta's Unity-PerformanceSettings sample shows the parallel-versus-serial trade-off. [T]
  - With "Use all cores" on, PushCPUJob runs an IJobParallelFor of 10,000 items at batch size 32 across the application cores.
  - With it off, the same work runs on the main thread.
  - The README says dual-core mode allows more work per frame with "use all cores" off, and less with it on.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-sample-performance-settings/ (accessed 2026-09-24; updated Aug 11, 2026) and https://github.com/oculus-samples/Unity-PerformanceSettings (accessed 2026-09-24) · Applies to: all Quest; Unity >= 6000.0 · Evidence: [doc]
  - Notes: A ready-made harness for measuring how worker scaling and levels behave on each device. The doc and the README disagree on the minimum Unity version (ARM-C8).
- **A1-057** Meta calls Unity apps good candidates for dual-core mode, because the Update() loop is single-threaded and often holds up the frame. In Perfetto's per-core view this shows as UnityMain saturating one core while the other app cores sit below 50%. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2/Pro (the diagnosis applies to all Quest) · Evidence: [doc]
  - Notes: Quest 3/3S has no dual-core mode. The same Perfetto pattern there means moving work off UnityMain into jobs, or trading −1 for CPU level 5 in VR-only apps (A1-033).
- **ARM-GF1-001** Meta's Boost page states that an app using all 3 cores at CPU level 4 will outperform a dual-core-mode app at CPU level 6. Dual-core mode pays off only when the frame is one long sequential chain; work that does not fit two cores at level 4-5 may fit at level 6. Distributing work across cores at lower clocks is "generally more power-efficient". Dual-core mode is supported only on Quest 2 and Quest Pro, "due to their hardware characteristics". [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24; page updated 2026-09-02) · Applies to: Quest 2 / Pro (dual-core mode); the parallel-over-clock principle applies to all Quest · Evidence: [doc]
  - Notes: This is Meta's own ranking of job parallelism over single-thread clock, and it confirms the 3-app-core model on Quest 2 (A1-004). For Unity: prefer moving main-thread work into Burst jobs across the app cores before reaching for dual-core mode; enable dual-core mode only when Perfetto shows UnityMain saturated and the other app cores under 50% (A1-057). Keep `JobWorkerCount` automatic so Unity adapts when dual-core mode removes a core (A1-053).

### 2.3 Multithreaded rendering and Graphics Jobs

- **A1-058** Meta recommends Unity Graphics Jobs in Legacy mode, together with Multithreaded Rendering, for main-thread-bound apps. Meta measured up to 2 FPS in major projects. Legacy Graphics Jobs are available from Unity 2022.3.35f1. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ (accessed 2026-09-24; updated Nov 11, 2024) · Applies to: all Quest; Unity 2022.3.35f1+ and Unity >= 6000.0 · Evidence: [doc]
  - Notes:
    - Unity 6: enable Player > Other Settings > Graphics Jobs and set Graphics Jobs Mode = Legacy.
    - Unity 2022.3: use an editor script, `PlayerSettings.graphicsJobs = true; PlayerSettings.graphicsJobMode = GraphicsJobMode.Legacy;`, in an IPreprocessBuildWithReport.
    - Verify on device with `SystemInfo.renderingThreadingMode` and `adb shell logcat -s Unity`. The Editor always reports MultiThreaded.
- **A1-059** Unity 6 offers three Graphics Jobs modes: Native, Legacy and Split. In Split mode (Vulkan only), the render thread translates Unity commands and then starts worker threads to write native commands. Unity 2022.3 offers only Native and Legacy. Meta's Nov 2024 guidance does not cover Split. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html and https://docs.unity3d.com/6000.0/Documentation/ScriptReference/GraphicsJobMode.html (accessed 2026-09-24; the /2022.3/ GraphicsJobMode page was also checked) · Applies to: Unity 6.0 through 6.6 on Vulkan · Evidence: [doc]
  - Notes: No Quest measurement comparing Split with Legacy was found. A/B them on device at a pinned CPU level. With only about 2 workers (A1-055), the extra worker fan-out may not pay off.
- **A1-060** In Unity 6.x, a Vulkan Device Filtering Asset can pick the graphics jobs mode per device. It replaces the deprecated Allow/Deny filter lists in Player settings. Graphics jobs modes can be selected only for Vulkan apps. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: Unity >= 6000.0, Quest on Vulkan · Evidence: [doc] [verify on device]
  - Notes: This makes it possible to use different modes on Quest 2 and Quest 3 if measurements disagree (for example Legacy on Quest 2, Split on Quest 3).
- **A1-061** Multithreaded Rendering moves graphics API calls off the main thread onto a separate thread. Meta suggests turning it off only while debugging, to see frame time more clearly. Meta also lists main- and render-thread capacity among the limits on draw calls: animation, skinning and networking delay the start of the render thread. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-perf/ (accessed 2026-09-24; updated Oct 30, 2024) and https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: Unity 2021.3 through 6.6 · Evidence: [doc]
  - Notes: Never ship a Quest build with Multithreaded Rendering off. With about 3 app cores, a serialized main and render thread loses a whole core of parallelism (derived). Meta's 2022 power guidance gives the power rationale (A1-040 / A3-094, section 6.3).
- **A1-062** Unity 2021.3's Android Player settings describe Graphics Jobs as moving render loops to worker threads to cut Camera.Render time on the main thread. There is no mode selector. [T]
  - Source: https://docs.unity3d.com/2021.3/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: Unity 2021.3 · Evidence: [doc]
  - Notes: Meta's Legacy-mode recommendation (A1-058) starts at 2022.3.35f1, and Meta gives no guidance for 2021.3. Treat Graphics Jobs as unvalidated on Quest with that version.

### 2.4 Caches, memory access and data-oriented layout

- **A1-063** All three Quest core types use 64-byte cache lines. The A55 SWOG says all A55 caches use 64-byte lines. The A77 and A78 SWOGs describe the penalty for loads that cross a 64-byte line boundary. The A78C TRM gives 64-byte lines for its L2. [T]
  - Source: https://documentation-service.arm.com/documentation/epm128372/latest (A55 SWOG) and https://documentation-service.arm.com/documentation/102226/0002/Functional-description/L2-memory-system/About-the-L2-memory-system (A78C TRM) (accessed 2026-09-24) · Applies to: Quest 2 (A77/A55), Quest 3/3S (A78C) · Evidence: [doc]
  - Notes: Derived application: align hot per-thread data to 64 bytes to avoid false sharing between job workers. For example, pad per-worker counters in a NativeArray to 64-byte strides.
- **A1-064** Cortex-A78C (r0p2 TRM): [T]
  - L1: 32 or 64 KB instruction cache and 32 or 64 KB data cache.
  - L2: private, 256 or 512 KB, 8-way, strictly inclusive of the L1 data cache.
  - The core sits in a DynamIQ Shared Unit (DSU-MP135).
  - Arm's product page allows a big-core-only cluster of up to 8 cores with up to 8 MB of L3.
  - Source: https://documentation-service.arm.com/documentation/102226/0002/Functional-description/Introduction/About-the-core and https://documentation-service.arm.com/documentation/102226/0002/Functional-description/L1-memory-system/About-the-L1-memory-system and https://www.arm.com/products/silicon-ip-cpu/cortex-a/cortex-a78c (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: None of the sources reached publishes the sizes Qualcomm configured in XR2 Gen 2 (L1, L2, L3). No published number found; see Known unknowns for how to measure. Qualcomm's separate 8 MB "system cache" (A1-012) is SoC-level and distinct from any DSU L3.
- **A1-065** Cortex-A77, per Arm's product page: [T]
  - out-of-order core; Armv8.2 plus LDAPR and dot product
  - 64 KB L1 instruction and 64 KB L1 data cache
  - 256-512 KB private L2
  - optional 512 KB-4 MB L3 in the DynamIQ cluster
  - up to 4 A77 cores per cluster
  - Source: https://www.arm.com/products/silicon-ip-cpu/cortex-a/cortex-a77 (accessed 2026-09-24) · Applies to: Quest 2 app cores · Evidence: [doc]
  - Notes: None of the Qualcomm or Meta sources reached gives the configured sizes for XR2 Gen 1. The commonly quoted SD865 cache layout comes from phone reviews that are no longer reachable (AnandTech now redirects), so it is not repeated here.
- **A1-072** On the A78, unaligned-access penalties apply in only three cases: loads that cross a 64-byte line, Q-word loads that are not 4-byte aligned, and stores that cross a 32-byte boundary. Other unaligned accesses are mostly free. [T]
  - Source: https://documentation-service.arm.com/documentation/102160/latest (accessed 2026-09-24) · Applies to: Quest 3/3S; the A77 SWOG lists the same 64-byte line-crossing case for Quest 2 · Evidence: [doc]
  - Notes: Derived Burst advice:
    - Allocate hot float4 and matrix streams with at least 16-byte alignment (64-byte is better).
    - Avoid packed 12-byte float3 arrays in hot SIMD loops, where loads straddle cache lines.
- **A1-073** On the A78, store-to-load forwarding works only under three conditions: [T]
  - The load must start at the start or middle address of the older store.
  - A load wider than 8 bytes can take data from at most 2 stores, each covering one half.
  - A load of 8 bytes or less can take data from only 1 store.
  - Source: https://documentation-service.arm.com/documentation/102160/latest (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: Writing a struct field by field and immediately reading it back as a float4 (or through `UnsafeUtility.As` / reinterpret) can miss forwarding and stall (derived).
- **A1-074** The A78 SWOG's advice for memory copy is to unroll with several non-writeback LDP/STP Q-register pairs per iteration. For zeroing memory it recommends `DC ZVA` instead of STP loops. [T]
  - Source: https://documentation-service.arm.com/documentation/102160/latest (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: Whether `UnsafeUtility.MemCpy/MemClear` or bionic's memcpy use these patterns on Quest is undocumented. Prefer the engine and libc routines over hand-written byte loops, and check hot copies in the Burst Inspector.

### 2.5 Core pipelines, instruction costs and ISA features

- **A1-066** Cortex-A78 pipeline (A78 SWOG r1p2, used as a stand-in for A78C): [T]
  - Dispatch handles up to 6 MOPs and 12 µOPs per cycle.
  - µOPs issue to 13 pipelines: 2 branch, 2 single-cycle integer, 2 single/multi-cycle integer, 2 FP/ASIMD (V0, V1), 2 load/store, 1 load-only and 2 store-data.
  - Dispatch limits: 2 µOPs per cycle to each V pipe and up to 6 to the load pipes.
  - Source: https://documentation-service.arm.com/documentation/102160/latest (Arm Cortex-A78 Core Software Optimization Guide r1p2, PDF-only) (accessed 2026-09-24) · Applies to: Quest 3/3S (A78C is an A78 derivative) · Evidence: [doc]
  - Notes: Arm's documentation service has no A78C-specific SWOG. The A78C TRM lists the same Armv8.2 + v8.4 dot-product baseline plus extra security features. Per-core SIMD throughput is capped by the two 128-bit V pipes.
- **A1-067** Cortex-A77 pipeline (A77 SWOG, rev c): up to 6 MOPs and 10 µOPs dispatched per cycle into 12 issue pipelines. [T]
  - Source: https://documentation-service.arm.com/documentation/swog011050/latest (Arm Cortex-A77 Core Software Optimization Guide, PDF-only) (accessed 2026-09-24) · Applies to: Quest 2 app cores · Evidence: [doc]
  - Notes: The A78 adds a load pipe (13 vs 12 pipelines) and wider dispatch (12 vs 10 µOPs). Load-heavy Burst loops, such as gathers and SoA streaming, should gain the most on Quest 3 (derived).
- **A1-068** On both the A77 and the A78, ASIMD FP FMLA has a 4-cycle latency and a throughput of 2 per cycle, one on each V pipe. That gives a peak of 16 FP32 FLOP per cycle per core: about 23.7 GFLOPS per core on Quest 2 at L4 (1.48 GHz) and 30.7 GFLOPS on Quest 3 at L4 (1.92 GHz). [T]
  - Source: https://documentation-service.arm.com/documentation/102160/latest and https://documentation-service.arm.com/documentation/swog011050/latest (accessed 2026-09-24) · Applies to: Quest 2 app cores (A77), Quest 3/3S (A78C, via the A78 SWOG) · Evidence: [doc]
  - Notes: The GFLOPS figures are derived. With latency 4 and throughput 2, both pipes stay busy only with about 8 independent FMA chains in flight. Unroll Burst reductions (for example 4 × float4 accumulators) instead of using a single float4 accumulator. With accumulator forwarding, the SWOG gives a latency of 2.
- **A1-069** On the A78, FP divide and square root execute only on V0 and are not fully pipelined. [T]
  - Scalar single-precision FDIV: 7-10 cycles.
  - Q-form (128-bit) F32 vector FDIV: 1/9 to 1/7 per cycle.
  - Q-form F16 vector FDIV is slower: 10-13 cycles, 1/13 to 1/10 per cycle.
  - Q-form F16 FSQRT is slower than F32 in the same way.
  - Source: https://documentation-service.arm.com/documentation/102160/latest (accessed 2026-09-24) · Applies to: Quest 3/3S; the A77 SWOG gives the same 7-10-cycle scalar FDIV on V0 for Quest 2 · Evidence: [doc]
  - Notes: Half precision does not speed up divide or square root on these cores. Prefer a reciprocal estimate plus Newton steps: FRECPE runs only on V0, FRECPS on both V pipes. Alternatively use FloatMode.Fast (A1-080).
- **A1-070** On the A78, FP16↔FP32 vector conversions (FCVTL/FCVTN, Q-form) run only on V0, with a 4-cycle latency and a throughput of 1 every 2 cycles. [T]
  - Source: https://documentation-service.arm.com/documentation/102160/latest (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: Derived layout advice: storing `half` in NativeArrays but computing in `float` costs single-pipe conversions on every load and store. That pays off for memory-bound code (half the bandwidth), not ALU-bound code. Native FP16 arithmetic needs Armv8.2 FP16 code generation (A1-079).
- **A1-071** On the A78, ASIMD SDOT/UDOT have a latency of 2 (1 with accumulator forwarding) and a throughput of 2 per cycle. On the A77 they have latency 2 and throughput 2. Burst exposes them through Neon intrinsics gated by `IsNeonDotProdSupported`. [T]
  - Source: https://documentation-service.arm.com/documentation/102160/latest and https://docs.unity3d.com/Packages/com.unity.burst@1.8/api/Unity.Burst.Intrinsics.Arm.Neon.html (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: That is 16 int8 multiply-accumulates per instruction × 2 pipes = 32 int8 MACs per cycle per core (derived). Relevant for CPU-side quantized inference or for int8 mask and audio math.
- **A1-075** Instruction-set features of the Quest cores: [T]
  - Cortex-A78C: Armv8.2-A, plus v8.3 LDAPR and pointer authentication, v8.4 dot product, v8.5 SSBS and v8.6 enhanced pointer authentication. AArch32 is supported at EL0 only.
  - Cortex-A77: Armv8.2-A (including RAS), plus v8.3 LDAPR and v8.4 dot product.
  - Neither core has SVE or SVE2.
  - Source: https://documentation-service.arm.com/documentation/102226/0002/Functional-description/Introduction/Supported-standards-and-specifications and https://documentation-service.arm.com/documentation/swog011050/latest (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc]
  - Notes: Any Armv9/SVE code path is dead code on Quest.
- **A1-076** Geekbench reports the same instruction-set line on Quest 2 (SM8250) and Quest 3/3S (SXR2230P): neon, aes, sha1, sha2, neon-fp16, neon-dotprod. Neither shows SVE or i8mm. [T]
  - Source: https://browser.geekbench.com/v6/cpu/19091540 and https://browser.geekbench.com/v6/cpu/19157033 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [measured]
  - Notes: Test setup: Geekbench 6 system-information readout on retail units. One Burst code-generation target (Armv8.2 + FP16 + dotprod) covers every supported Quest, so there is no reason to dispatch per device for CPU code.
- **A1-077** Cortex-A55, the system cluster on Quest 2, is an in-order, dual-issue core with an 8-stage integer pipeline and a 10-stage FP/NEON pipeline. It implements the same Armv8.2 + dot-product ISA as the big cores. [C]
  - Source: https://documentation-service.arm.com/documentation/epm128372/latest (Arm Cortex-A55 Software Optimization Guide, PDF-only) (accessed 2026-09-24) · Applies to: Quest 2 (system cores) · Evidence: [doc]
  - Notes: This matters only if an app thread lands on cpu0-3, for example through a `little` affinity argument or an unregistered helper thread. Throughput then collapses and frame time spikes. Detect it with Perfetto's CPU tracks.

### 2.6 Burst settings and NEON for Quest cores

- **A1-078** Burst's Android Arm64 targets are ARMV8A (the default), ARMV8A_HALFFP and ARMV9A. When several are selected, Burst generates a dispatch that detects the device's CPU at runtime and picks the matching target. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-projects.html and https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-aot-settings.html (accessed 2026-09-24; Burst 1.8.30) · Applies to: Unity 2021.3 through 6.6 with Burst ≥1.8 · Evidence: [doc]
  - Notes: The setting is "Target Arm 64Bit CPU Architectures" under Project Settings > Burst AOT Settings (Android).
- **A1-079** ARMV8A_HALFFP matches the Quest hardware, since every Quest core implements Armv8.2 FP16 (A1-075, A1-076). ARMV9A will never be selected at runtime on Quest 2/3/3S; choosing it only adds build time and binary size. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-projects.html (accessed 2026-09-24) · Applies to: all Quest · Evidence: [doc] [verify on device]
  - Notes: Unity does not document exactly which features ARMV8A_HALFFP enables: FP16 arithmetic only, or also dotprod and RDMA. Check the Burst Inspector for `.8h` FP16 vector operations in `half`-heavy code, then measure. Any gain is limited to code that actually does half-precision arithmetic.
- **A1-080** Burst float settings: [T]
  - FloatMode Default = Strict.
  - FloatMode Fast permits fused multiply-add and reciprocal approximations.
  - FloatMode Deterministic targets cross-platform determinism.
  - FloatPrecision Standard (= Medium) allows 3.5 ulp; High allows 1 ulp; Low allows 350 ulp for sin, cos, exp, log, pow and fmod.
  - Per-job syntax: `[BurstCompile(FloatPrecision.Medium, FloatMode.Fast)]`.
  - Source: https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstcompile.html (accessed 2026-09-24) · Applies to: Unity 2021.3 through 6.6, Burst 1.8.x · Evidence: [doc]
  - Notes: Divide and sqrt serialize on V0 on the A77 and A78 (A1-069). For visual-only math (particles, procedural animation), FloatMode.Fast with FloatPrecision.Low is the throughput choice. Keep Strict or Deterministic for gameplay-critical or networked simulation (derived).
- **A1-081** Burst Neon intrinsics are gated at compile time, and there is no managed reference implementation. The checks, evaluated for the selected target, are: [T]
  - `IsNeonSupported`
  - `IsNeonArmv82FeaturesSupported` (= Crypto && DotProd && RDMA)
  - `IsNeonCryptoSupported`
  - `IsNeonDotProdSupported`
  - `IsNeonRDMASupported`
  - Source: https://docs.unity3d.com/Packages/com.unity.burst@1.8/api/Unity.Burst.Intrinsics.Arm.Neon.html (accessed 2026-09-24) · Applies to: Unity 2021.3 through 6.6, Burst 1.8.x · Evidence: [doc]
  - Notes: Always write an `else` path in plain `Unity.Mathematics` for the x64 Editor and for non-matching targets. Hand-written Neon rarely beats Burst's auto-vectorization of `float4` code unless you need dot product or specific shuffles.
- **A1-082** Burst's Arm support history: [T]
  - 1.5.0-pre.1 (2020-11-26): RDMA, crypto and dot-product intrinsics.
  - 1.6.0-pre.1 (2021-04-14): experimental `half` (f16) support, half-precision Neon intrinsics and full Armv8.2 Neon.
  - 1.8.0-pre.1 (2022-05-06): the Android "Target Arm64 CPU" setting, plus an experimental Armv9 SVE2 target.
  - 1.8.30 (2026-07-06): the current release.
  - Source: https://docs.unity3d.com/Packages/com.unity.burst@1.8/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: Unity 2021.3 through 6.6 · Evidence: [doc]
  - Notes: Unity 2021.3 projects pinned to Burst 1.6 or 1.7 lack the Arm64 target setting; upgrade to 1.8.x. Since 1.8.0, Burst respects "Enable Armv9 Security Features for Arm64" (pointer authentication and branch target identification). 1.8.25 (2025-09-16) fixed an Android crash with that flag enabled, so ship with at least 1.8.25 if you use it.
- **A1-083** Burst's global "Optimize For" setting defaults to Balanced. Performance optimizes jobs to run as fast as possible, while FastCompilation skips vectorization, inlining and loop optimizations. A per-job `OptimizeFor` overrides the global setting. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-aot-settings.html (accessed 2026-09-24) · Applies to: Burst 1.8.x · Evidence: [doc]
  - Notes: For Quest release builds, mark hot jobs `[BurstCompile(OptimizeFor = OptimizeFor.Performance)]` rather than changing the global setting, which slows every build. Make sure no hot job is left on FastCompilation from iteration work (derived).

---

## 3. Adreno architecture: binned vs direct rendering (FlexRender), GMEM, LRZ, UBWC, early-Z, binning-pass vertex cost, overdraw

Sections 3 to 7 and the closing sections were restored in the round-1 coverage pass from the A1/A2/A3 topic notes, because the synthesis output stopped after section 2. Findings keep their original IDs; where A2 and A3 found the same fact, the two findings sit next to each other instead of being merged. Gap-fill findings from that pass carry `ARM-GF1-NNN` IDs.

### 3.1 Shader-core hierarchy, published limits and the GPU level governor

- **A2-004** Qualcomm's public Adreno developer docs publish no count of shader processors (SP), ALUs or FLOPS, no GMEM size and no clock for either the Adreno 650 or the Adreno 740. The spec sheet gives only per-generation limits (A6x/A7x/A8x). No published number found. [T] [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: how to measure the relative throughput yourself:
    1. Lock the GPU level (A2-008).
    2. Run a fixed full-screen ALU-bound shader with fixed iterations.
    3. Read `Clocks / Second` and `% Shaders Busy` in ovrgpuprofiler.
    4. Compare Quest 2 and Quest 3 at matched MHz.
- **A2-005** Chips and Cheese (corrected analysis) describes the Adreno 6xx hierarchy as SP → uSPTP (micro shader processor + texture processor). On the Adreno 640 each uSPTP has:
  - a pair of 64-wide FP32 ALUs
  - a pair of 128-wide FP16 ALUs (double-rate FP16)
  - tracking for 16 wave128 waves (8 per ALU partition). [T]
  - Source: https://chipsandcheese.com/p/correction-on-qualcomm-igpus (accessed 2026-09-24) · Applies to: Adreno 6xx family. The 640 is the SD855 sibling of the 650; the 650 itself was not measured. · Evidence: [measured]
  - Notes: the article's first version reported the "SP" count wrongly; use the correction.
- **A2-006** Chips and Cheese on the Adreno X1 (an A7xx part, internally "741", a scaled Adreno 730):
  - 2 uSPTPs per SP and 2 scheduler partitions per uSPTP, each with a 64-wide FP32 ALU
  - wave64 and wave128 modes
  - 192 KB register file per uSPTP (96 KB per partition, up from 64 KB on the 730)
  - 2 KB texture L1 per uSPTP
  - GMEM 3 MB on the X1-85
  - double-rate FP16. [T]
  - Source: https://chipsandcheese.com/p/the-snapdragon-x-elites-adreno-igpu (accessed 2026-09-24) · Applies to: A7xx family as a proxy for the Quest 3 Adreno 740 · Evidence: [measured]
  - Notes: the X1 is a laptop SKU with more SPs and a different GMEM. Use it for per-uSPTP ratios, not totals.
- **A2-008** The OS raises the GPU level when GPU utilisation is at or above 87% and lowers it at or below 81%. On Quest 3 the range between levels 0 and 5 is 599/285 ≈ 2.1x in clock (derived). Any millisecond number is meaningless unless the GPU level/clock is recorded with it. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3, Quest 3S · Evidence: [doc]
  - Notes: when comparing shader variants, pin the level (via the OVRPlugin/OpenXR suggested-performance-level APIs) or read the `Clocks / Second` metric alongside timings. [verify on device]
- **A2-009** Adreno is a unified, scalar shader architecture:
  - vertex, fragment and compute share the same ALUs
  - pixels are processed in groups of four (quads)
  - a stalled wave is swapped for another ready wave, and how many waves are resident is limited mainly by GPRs. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: "scalar" means vec4 math buys nothing per ALU op. Vector packing still matters for varyings and constants (A2-073, A2-074).
- **A3-100** The ovrgpuprofiler and RenderDoc render-stage pages state that Quest 3 runs its Adreno 740v3 at 690 MHz and Quest 3S at 492 MHz. This contradicts the levels table (599 MHz maximum for both). 690 MHz equals VR Glasses GPU L5, and 492 MHz equals Quest 3/3S L3. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ and https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [doc]
  - Notes: The render-stage page carries a visible TODO in the same paragraph, which lowers confidence. Treat the levels table as authoritative (ARM-C3). [verify on device] with GPU F in OVR Metrics.

### 3.2 GMEM and bin sizing

- **A3-003** Adreno renders in two phases. A binning pass computes positions and writes a per-bin visibility stream to system memory. Each bin is then rendered into on-chip GMEM, which holds its color and depth, and resolved (stored) to system memory at the end of the bin. Load and store at bin boundaries are the main controllable DRAM traffic for render targets. [T] [C]
  - Source: Qualcomm Adreno GPU guide 80-78185-2, overview, https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md (accessed 2026-09-24) · Applies to: all Quest devices (Adreno 540/650/740) · Evidence: [doc]
  - Notes: Qualcomm notes that Vulkan render passes let several passes run inside GMEM, which minimises costly resolves.
- **A2-010** Meta: the XR2 (Adreno 650) has 1 MB of tile memory (GMEM); the XR2 Gen 2 (Adreno 740) has "approximately 2MB". [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes: this conflicts with kernel values; see A2-011, ARM-C9 and ARM-C10.
- **A3-004** GMEM size: Adreno 540 (Quest 1) and Adreno 650 (Quest 2) have 1 MB. Adreno 740 (Quest 3/3S) has about 2 MB. With a fixed per-pixel footprint, a larger GMEM means fewer, larger bins. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24; no date on page) · Applies to: Quest 1/2/3/3S · Evidence: [doc]
  - Notes: Quest Pro (XR2+) GMEM is not stated. It is presumably the same as Adreno 650, but [verify on device] by checking the bin count in ovrgpuprofiler.
- **A2-011** Linux kernel msm GPU catalog:
  - Adreno 650 (chip 0x06050002): `.gmem = SZ_1M + SZ_128K` (1.125 MiB)
  - Snapdragon 8 Gen 2 Adreno 740 (chip 0x43050a01): `.gmem = 3 * SZ_1M`
  - The Quest 3 chip id 0x43050b00 is not in the upstream catalog. [T]
  - Source: https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/drivers/gpu/drm/msm/adreno/a6xx_catalog.c (mirror of upstream drivers/gpu/drm/msm/adreno/a6xx_catalog.c; accessed 2026-09-24) · Applies to: Quest 2 (exact chip); Quest 3 (proxy only) · Evidence: [community]
  - Notes: Quest 3's GMEM is not published by Qualcomm or the kernel. The only direct statement is Meta's "approximately 2MB". [verify on device] using the bin arithmetic in A2-013.
- **A2-012** Freedreno: part of GMEM is carved out for the CCU, which caches colour/depth for system-memory ("sysmem") rendering and for resolves in GMEM mode. The amount reserved depends on whether the pass renders to GMEM or sysmem. Mesa sets the GMEM-mode CCU fraction to a QUARTER on a6xx and an EIGHTH on a7xx. So bin storage is less than raw GMEM. [T]
  - Source: https://docs.mesa3d.org/drivers/freedreno.html (accessed 2026-09-24); https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py · Applies to: all · Evidence: [community]
  - Notes: this is one plausible reason for "1 MB vs 1.125 MiB" and "~2 MB vs 3 MiB". It is not confirmed for the Qualcomm blob driver that Quest ships.
- **A2-013** Meta's bin-sizing rule:
  - bytes per pixel = (colour bytes + depth/stencil bytes) × MSAA samples, doubled for multiview when both views share a bin
  - the driver picks the largest bin that fits the GMEM budget
  - worked example on XR2: 4x MSAA + RGBA8 + D24S8 + multiview = 32 B/px/view, giving 96x176 bins (96×176×2×32 ≈ 1 MB). [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2 (example); the rule applies to all · Evidence: [doc]
  - Notes (derived): 96×176×2×32 = 1,081,344 B = 1.03 MiB. That is slightly more than 1 MiB, which is consistent with the kernel's 1.125 MiB (A2-011).
  - 135 bins = 15 × 9 bins for Quest 2's default 1440x1584 eye buffer. This matches the "135 96x176 bins" example in Meta's docs.
- **A3-005** Bin footprint math for XR2: 4x MSAA with 32-bit color and 24/8 depth-stencil needs (4+4) bytes x 4 samples = 32 B per pixel. That gives 96x176 bins, because 96 x 176 x 2 views x 32 B is about 1 MB of GMEM. More MSAA samples or wider formats shrink bins, which increases the bin count and the fixed per-bin binning and load/store overhead. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2 (Adreno 650); scale by roughly 2x GMEM for Quest 3/3S · Evidence: [doc]
  - Notes: A Unity HDR color target (R11G11B10 or FP16) changes the per-pixel footprint. [verify on device] via the bin size in `ovrgpuprofiler -t -v` or the RenderDoc Surface Information.
- **ARM-GF1-006** Meta's tiled-GPU explainer gives the worked bin count for the Quest 2 default eye buffer: 1440x1584 cut into 135 tiles of 96x176. It also says Quest-class GPUs have "5mb or less" of on-GPU memory and typically draw 3-6 W. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ (accessed 2026-09-24) · Applies to: Quest 2 (tile example); all Quest for the power/memory range · Evidence: [doc]
  - Notes: 1440/96 = 15 and 1584/176 = 9, so 15 x 9 = 135 (derived check). The page's 96x176 tile matches the 4x MSAA multiview example in A3-005. The 3-6 W figure is a generic class statement for "phones and Meta Quest devices", not a Quest 2 or Quest 3 GPU power rating (see section 1.7).
- **A2-014** Derived bytes-per-pixel table using Meta's rule. Use it to predict relative bin count, which scales roughly with bytes per pixel. [T]

  | Configuration | Bytes per pixel per view | Relative bin count |
  |---|---|---|
  | 4x MSAA, RGBA8 or R11G11B10F or RGB10A2 colour, D24S8 or D32F depth | (4+4)×4 = 32 | baseline |
  | 4x MSAA, RGBA16F colour | (8+4)×4 = 48 | about 1.5x the bins |
  | 2x MSAA, 32-bit colour | 16 | half of 4x |
  | No MSAA | 8 | a quarter of 4x |
  | Each extra 32-bit MRT at 4x MSAA | adds 16 | more bins |

  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (rule); format sizes are standard (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; Unity URP any version · Evidence: [doc]
  - Notes:
    - URP HDR in R11G11B10F costs no bins over LDR RGBA8. HDR in RGBA16F does.
    - This is arithmetic on Meta's rule, not a measurement. Confirm with the ovrgpuprofiler "N WxH bins" field. [verify on device]
- **A2-015** Meta's ovrgpuprofiler example surface line: 1216x1344, 32-bit colour, 24-bit depth, MSAA 4, Mode 1 (HwBinning), 60 bins of 128x224, 5.08 ms. [T]
  - Derived: 128×224×32 B × 2 views ≈ 1.75 MiB per bin if both views share the bin.
    - That only fits a GPU with roughly 2 MB of usable GMEM, so the example is consistent with Quest 3, not Quest 2.
    - At 128x224, Quest 3's default 1680x1760 would need 14 × 8 = 112 bins (derived).
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 3/3S (inferred) · Evidence: [doc]
  - Notes: the page does not name the device behind the example. [verify on device]
- **A2-016** Mesa's tile-alignment constants do not predict Qualcomm-driver bin sizes.
  - Mesa uses width alignment 96 on both the 650 and the 740.
  - Meta's Qualcomm-driver examples show 128x224 and 320x192 bins, and 128 and 320 are not multiples of 96.
  - Do not predict bin dimensions from Mesa. Read them from ovrgpuprofiler. [C]
  - Source: https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: all · Evidence: [community]
  - Notes: Quest runs Qualcomm's proprietary driver, not Turnip.
- **A2-017** Qualcomm's levers to cut bin count:
  - lower render resolution
  - use VRS/foveation
  - use fewer MSAA samples
  - use fewer MRTs

  Qualcomm says 2x MSAA "is likely to be practically free" and recommends MSAA over other AA techniques. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24; page published 2026-09-22) · Applies to: all · Evidence: [doc]
- **A2-018** A triangle that covers several bins is fully rasterised in every bin it touches; the driver adds no vertices at bin borders. Qualcomm asks for triangles of at least ~4 pixels that are not much larger than a bin. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: Meta says triangles "can be split" (ARM-C11).
- **A2-019** Meta: do not assume a bin count or bin positions, because foveation changes the bins. Algorithms that depend on screen tiling (e.g. screen-space tile culling written for 16x16 Mali tiles) will not line up with Adreno bins. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/gpu-impaired-algorithms/ (accessed 2026-09-24; page updated 2024-09-20) · Applies to: all · Evidence: [doc]
- **A2-020** Meta: a default eye buffer does not fit in on-chip memory.
  - Quest 2 1440x1584 RGB8 ≈ 6.52 MB; Quest 3 1680x1760 ≈ 8.46 MB.
  - On-GPU memory is "5mb or less"; mobile GPUs typically run at 3 to 6 W (round-1 spot-check corrected the earlier "1 to 5 MB" paraphrase).
  - So tiling is mandatory, and every full-resolution load/store is a DRAM round trip. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ (accessed 2026-09-24; page updated 2024-12-04) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]

### 3.3 FlexRender: binned vs direct mode, concurrent binning

- **A2-021** FlexRender: the driver chooses per render pass between binned and direct mode (direct = render straight to system memory like an immediate-mode GPU). Qualcomm does not expose the heuristics. Documented triggers for direct mode:
  - a high ratio of vertex-shader texture samples to vertices
  - a small number of vertices or draws
  - tessellation or geometry shaders. [T] [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-022** Meta: a full-screen pass with no depth and no MSAA (e.g. Unity's tonemap/final blit) runs in Direct Mode. It appears as a single bin covering the surface, for example "1 1216x1344 bins". [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A3-024** FlexRender/direct mode: the driver can run a full-screen pass with no depth in direct mode, which skips binning. Direct mode disables FFR for that pass. It appears as a single bin covering the whole surface (for example `1 1216x1344 bins`). [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ and https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: The trace mode field shows 0 Direct or 3 HwDirect (A3-033).
- **A3-025** On Meta VR Glasses, the larger GMEM gives fewer bins, so full-screen passes gain little from tiling. Meta says to check the share with RenderDoc Surface Information. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/optimize-performance/ (accessed 2026-09-24; page updated 2026-09-19) · Applies to: Meta VR Glasses (XR2 Gen 3) · Evidence: [doc]
  - Notes: The Glasses GMEM size is not stated.
- **A2-023** Meta: fixed foveated rendering (FFR) is a per-tile effect, so it is deactivated for any surface rendered in Direct Mode. [T]
  - If the final pass into the compositor swapchain is a depthless full-screen blit (URP post-processing or an intermediate-texture resolve), that pass gets no FFR.
  - The expensive main pass also gets no FFR if it renders to a non-swapchain intermediate target.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; URP with post-processing or an intermediate texture · Evidence: [doc]
  - Notes: check each surface with the ovrgpuprofiler mode field and the per-bin "Fov x/y" field (A2-025). [verify on device]
- **A2-024** Meta's MSAA analysis quotes Qualcomm as saying direct rendering happens only with MSAA off. The current Qualcomm guide does not list MSAA among the direct-mode triggers (ARM-C12). [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-msaa-analysis/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: in practice, enabling MSAA on a pass is a documented, if old, way to keep it binned. [verify on device]
- **A2-025** Reading the mode per surface. [C]
  - `ovrgpuprofiler -t -v`, after `-e` and an app restart, prints each surface with:
    - its mode: 0 Direct, 1 HwBinning, 2 SwBinning, 3 HwDirect
    - bin count and size
    - per-stage times: Binning, Render, Load/Store Color, Load/Store DepthStencil
  - Per-bin lines show "Fov x/y" foveation factors.
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24; page updated 2026-09-09) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
- **A2-026** Concurrent binning (introduced with A7x, so Quest 3/3S only) overlaps the binning pass of later work with rendering of earlier work. [T]
  - Clears of a Z-buffer that is reused within the frame prevent it. Either reuse the depth buffer without clearing it or give each pass its own.
  - The driver may try concurrent binning when GPR use is low.
  - For VSYNC-limited apps, schedule independent work before the geometry-heavy pass.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [doc]
  - Notes: relevant to URP passes that clear a shared depth target (e.g. a depth-only pre-pass followed by a cleared main pass). [verify on device]
- **A2-027** Freedreno: A7xx keeps two sets of LRZ buffers so the binning (BV) and rendering (BR) pipes can use LRZ at the same time. This is the hardware side of concurrent binning. [T]
  - Source: https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [community]
- **A2-028** Mesa's Turnip driver defaults small render passes (few draws) to sysmem because tiling overhead outweighs the gain. It picks sysmem vs GMEM by estimated bandwidth. [T]
  - Source: https://docs.mesa3d.org/drivers/freedreno.html (accessed 2026-09-24) · Applies to: mechanism illustration only (Quest uses the Qualcomm driver) · Evidence: [community]
  - Notes: this matches Qualcomm's own "few vertices or draws → direct" trigger (A2-021). Expect tiny URP utility passes to run direct.

### 3.4 LRZ, early-Z, Fast-Z, discard and overdraw (no hidden-surface removal)

- **A2-029** LRZ (low-resolution Z) is built during the binning pass. It rejects work at LRZ-block granularity before the full-resolution depth test in the rendering pass. It is draw-order independent and not directly controllable by the app. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) · Applies to: all (added in A5x) · Evidence: [doc]
  - Notes: no published LRZ block size. Measure indirectly with the per-draw "Fragments Shaded" metric.
- **A2-030** Freedreno: the LRZ buffer is always Z16_UNORM and stores the farthest Z per block. LRZ cannot be used when late-Z is required, and one LRZ buffer is valid for only one depth-compare direction. [T]
  - Source: https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html (accessed 2026-09-24) · Applies to: all · Evidence: [community]
- **A2-031** LRZ direction tracking differs by generation. [T] [C]
  - Before A650: tracked on the CPU. A direction change disables LRZ for the rest of the pass, and secondary command buffers cannot know the state.
  - A650 and later: a GPU-side direction byte plus depth-view parameters let LRZ survive across render passes that use the same depth view.
  - A7xx: adds bidirectional LRZ, off by default.
  - Source: https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [community]
- **A2-032** LRZ is disabled for **both test and write until the next depth clear** when either of these is followed by a depth write: [T]
  - changing the depth direction
  - setting the depth function to ALWAYS or NOT_EQUAL
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: in Unity, a mid-frame `ZTest Always` + `ZWrite On` draw (e.g. a custom sky or "always on top" object that writes depth) kills LRZ for the rest of the pass. Unity mapping is an inference. [verify on device]
- **A2-033** LRZ **write** is disabled until the next clear (the test still works) when a draw does any of the following **and also writes depth**: [T]
  - fixed-function blending or logic ops
  - colour-masked writes or partial MRT writes
  - any stencil operation
  - framebuffer fetch or advanced blending
  - reading an attachment written in a previous subpass while writing depth
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes (Unity inference):
    - A blended material with `ZWrite On`, or a stencil-using draw that writes depth (e.g. URP stencil-based effects or portal masks), freezes LRZ for everything after it in that pass.
    - Draw such materials after all opaque geometry, or turn ZWrite off. [verify on device]
- **A2-034** LRZ is disabled **for the current draw only** in two cases: [T]
  - test and write both disabled: the fragment shader writes a UAV, depth or stencil
  - write only disabled: alpha-to-coverage, `discard`, or a sample-mask output
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: alpha-clipped foliage (`clip()`) costs its own LRZ write but does not poison later draws. Freedreno's "LRZ feedback" (A650+) lets such draws still update LRZ during the rendering pass (A2-035).
- **A2-035** Freedreno "LRZ feedback" (A650+): draws that write depth but cannot feed LRZ during binning (e.g. discard) can still update LRZ during the rendering pass. This helps when such draws come early in the pass. It also works in sysmem mode. [T]
  - Source: https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [community]
  - Notes: documented for Turnip. Whether the Qualcomm blob does the same is not published.
- **A2-036** Secondary command buffers disable LRZ only on GPUs older than the Adreno 650. It is a non-issue on Quest 2/3/3S. LRZ still runs in direct mode but gives much less benefit there. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
- **A2-037** LRZ state can be verified per draw. [C]
  - `ovrgpuprofiler -x` per-draw traces print an LRZ State line per draw, e.g. "TestEnabled, WriteEnabled <0x03>", alongside metrics such as Clocks, % Shaders Busy and Fragments Shaded.
  - Old drivers print "Unknown(old driver?)".
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes: this is the fastest way to find the draw that killed LRZ (A2-032/033).
- **A2-038** Early-Z rejects occluded pixels at up to 4x the normal fill rate. It is disabled when the fragment shader:
  - writes Z
  - uses `discard`
  - writes depth/stencil
  - uses alpha-to-coverage. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-039** Adreno has no hidden-surface removal in the PowerVR/Mali Forward Pixel Kill sense. Qualcomm says to sort opaque geometry front-to-back even with early Z. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: in Unity, keep opaque queues sorted front-to-back (URP's default opaque sorting). Avoid forcing arbitrary render-queue orders on large occluders.
- **A2-040** Fast-Z: a depth-only pass with an empty fragment shader and colour writes disabled writes Z at twice the normal rate. For indirect draws, declare `layout(early_fragment_tests) in;`. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: a full depth pre-pass also doubles binning and vertex work (A2-046). With LRZ already giving order-independent rejection, measure before adopting URP depth priming on Quest. No Quest number published. [verify on device]
- **A2-041** Discard (`clip()`): if only some pixels of a thread are killed, the shader still runs for the whole thread. Qualcomm says the early-exit gain is rarely real and varies by driver. Put discard draws after all opaque draws. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]

### 3.5 UBWC and attachment formats

- **A2-042** UBWC (Universal Bandwidth Compression) has been on every Adreno since A5x. Images with VK_IMAGE_TILING_OPTIMAL generally get it. Snapdragon Profiler shows surfaces as "Optimal" vs "Linear". [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A3-013** Universal Bandwidth Compression (UBWC) has been on every Adreno since A5x. It is a lossless, predictive compression that raises effective memory throughput and saves power. `VK_IMAGE_TILING_OPTIMAL` images generally get UBWC, and UBWC also works across the display, video and camera blocks. [T] [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md and https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: Qualcomm publishes no compression ratio (see Known unknowns).
- **A2-043** Qualcomm lists features that "almost certainly" disable UBWC: [T]
  - compute shaders
  - VK_IMAGE_TILING_LINEAR
  - any CPU readback, including host_image_copy
  - VK_KHR_fragment_shading_rate
  - VK_EXT_fragment_density_map
  - VK_IMAGE_CREATE_ALIAS_BIT
  - MUTABLE_FORMAT
  - sparse resources
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes:
    - The FDM and compute entries clash with Quest practice and with Mesa flags (ARM-C13, ARM-C14).
    - Keep Unity RenderTextures that are read back (`ReadPixels`, `AsyncGPUReadback`) or written by compute separate from hot render targets. [verify on device]
- **A3-014** Qualcomm lists Vulkan features that almost certainly disable UBWC: compute-shader access, `VK_IMAGE_TILING_LINEAR`, any CPU readback including host image copy, `VK_KHR_fragment_shading_rate`, `VK_EXT_fragment_density_map`, `VK_IMAGE_CREATE_ALIAS_BIT`, `VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT`, and sparse residency or binding. [T] [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md (accessed 2026-09-24) · Applies to: all Quest devices (Adreno, Vulkan) · Evidence: [doc]
  - Notes: The FDM entry conflicts with how Meta implements FFR on Vulkan (see ARM-C13). Compute-written targets, such as a compute-based post chain or GPU readback of a render texture, lose UBWC. [verify on device]
- **A2-044** A6x UBWC support by format (optimal layout): [T]

  | UBWC | Formats |
  |---|---|
  | Yes | R5G6B5, RGBA8, RGB10A2, R11G11B10F, RG16F, R32F |
  | Yes, to 8x MSAA | RGBA16F |
  | Yes, to 4x MSAA | RGBA32F |
  | Yes (depth) | D24 variants |
  | No | R8_UNORM, R9G9B9E5, ASTC, ETC2 |

  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (accessed 2026-09-24) · Applies to: Quest 2 (A6x table); Quest 3 likely similar but its table is not given · Evidence: [doc]
  - Notes:
    - Mesa agrees that the A650 lacks 8-bpp UBWC.
    - Single-channel R8 render targets (e.g. an SSAO or mask buffer) are uncompressed on Quest 2. RG8 is not listed.
- **A2-045** Qualcomm's format priorities: [T]
  - colour: R10G10B10A2 first (the hardware is optimised for it), then R11G11B10, then RGBA16
  - depth: D16 when precise enough (e.g. with tuned reverse-Z), then D24S8 if stencil is needed, then D32
  - UBWC supports all of these depth formats
  - avoid VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT before the Adreno 750, which covers both Quest GPUs
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: D16 halves depth bytes per pixel. Combined with A2-014, that allows more pixels per bin.

### 3.6 Binning pass and vertex cost

- **A2-046** The binning pass runs a driver-generated position-only vertex shader over every draw and writes a visibility stream to system memory. The rendering pass then runs the full vertex shader again for each bin, to produce the interpolants. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-047** Meta: each vertex is shaded at least twice per frame, and up to 2 × (number of tiles) + 1 times when its triangles touch many bins. Meta recommends fat triangles and normal maps over extra geometry. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/gpu-impaired-algorithms/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes (derived):
    - At 135 bins (Quest 2 default, 4x MSAA), large screen-spanning meshes can be shaded dozens of times.
    - Vertex cost is therefore multiplied by bin count. Anything that grows bins (A2-014) also grows vertex cost.
- **A2-048** Vertex layout advice: [T]
  - put position alone in the first interleaved stream and the other attributes in a second stream, so the position-only VS fetches the minimum
  - Vulkan does not yet support half precision in vertex shaders; GLES has GL_OES_vertex_half_float
  - use the smallest vertex format that keeps acceptable precision
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: in Unity this maps to Mesh vertex streams (a position-only stream 0). Whether Unity's importer or SRP ever splits streams by default is not documented here. Lead for the mesh topic.
- **A3-018** Vertex bandwidth: use a single vertex buffer with the position-only attributes interleaved first, followed by all other attributes interleaved. Pack attributes (for example 2_10_10_10 normals, or half floats where the API allows). Use indexed draws with the smallest index type; Adreno supports 8-bit, 16-bit and 32-bit indices. The binning pass runs a position-only vertex shader, so a separate position stream cuts binning reads. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: Unity's `IndexFormat` offers only UInt16 and UInt32, so 8-bit indices are not available from C#. Qualcomm says Vulkan does not yet support half precision in vertex shaders, but the storage format can still be half.
- **A2-049** Adreno natively supports 8-, 16- and 32-bit indices. Prefer 8-bit where possible, otherwise 16-bit, and avoid 32-bit. The A7x post-transform vertex cache holds 32 four-component vertices. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (accessed 2026-09-24) · Applies to: all (the cache size is for A7x, i.e. Quest 3/3S) · Evidence: [doc]
  - Notes: a 32-entry cache means vertex-cache-optimised index order (as done by mesh optimisation tools) still pays off.
- **A3-019** The A7x vertex cache holds 32 4D vertices. Index order that reuses recent vertices reduces vertex re-fetch. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/spec_sheets.md (accessed 2026-09-24) · Applies to: Quest 3/3S (Adreno 740 is A7x) · Evidence: [doc]
  - Notes: Unity's mesh import "Optimize Mesh" reorders indices, but its target cache size is not documented. [verify on device] with Avg Bytes / Vertex (A3-038).
- **A2-050** Texture fetches in a vertex shader run twice, once in the position-only VS and once in the full VS. If the position-only VS stalls on memory, binning slows down. Too many VS fetches make the driver fall back to Direct Mode (A2-021). [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: vertex-animation textures, GPU-skinning-from-texture and heightmap displacement in VS are the Unity cases to watch.
- **A2-051** Qualcomm lists these as slow and to be avoided: [T]
  - tessellation stages
  - primitive restart (use multiple draws instead)
  - VK_EXT_vertex_input_dynamic_state (static pipelines are faster)
  - conditional rendering, unless it skips a large amount of work
  - user clip planes
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-052** The only published triangle-setup rate is for A5x: 1 primitive per clock. No published number was found for A6x (650) or A7x (740). [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (accessed 2026-09-24) · Applies to: n/a for Quest (A5x only) · Evidence: [doc]
  - Notes: to measure, draw N off-screen-culled vs on-screen tiny triangles. Compare the ovrgpuprofiler Binning stage time and `Pre-clipped Polygons/Second` at a locked GPU level.

### 3.7 Load/store traffic, MSAA resolve, subpasses and queries

- **A2-053** Start every attachment with LOAD_OP_CLEAR or DONT_CARE (glInvalidateFramebuffer on GLES). Store depth and MSAA with DONT_CARE, and back transient MSAA/depth attachments with LAZILY_ALLOCATED memory. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A3-006** Meta's rules for GMEM load/store: clear or invalidate every attachment every frame. Use `VK_ATTACHMENT_STORE_OP_DONT_CARE` for depth and for MSAA attachments. Never store MSAA samples to memory; resolve through `pResolveAttachment`, which runs in the hardware store path. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: all Quest devices, Vulkan · Evidence: [doc]
  - Notes: Qualcomm gives the same advice: invalidate early with `LOAD_OP_CLEAR`/`DONT_CARE` so the driver does not resolve GMEM to system memory. In URP, any feature that samples the camera depth or opaque texture after the pass forces a store. Map this in the URP topic.
- **A2-054** Meta's profiler example (MSAA 2, 28 bins of 320x192, 10.62 ms): [T]
  - LoadColor 0.71 ms, StoreColor 1.525 ms, LoadDepthStencil 0.828 ms, StoreDepthStencil 0.871 ms
  - Derived: the avoidable part (LoadColor + LoadDS + StoreDS) is 2.41 ms, about 23% of the surface time. All GMEM↔DRAM traffic is 3.93 ms, about 37%.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: original-Quest-era example; the mechanism applies to all · Evidence: [doc]
  - Notes: in URP, anything that makes a pass load (no clear, a camera stack without clear, render-pass breaks) shows up as Load* stages.
- **A3-007** Meta's example of a bad load/store pattern: a 1216x1344 MSAA 2x surface with 28 bins of 320x192 took 10.62 ms. Of that, LoadColor was 0.71 ms, StoreColor 1.525 ms, LoadDepthStencil 0.828 ms and StoreDepthStencil 0.871 ms. That is about 3.9 ms of pure GMEM-to-DRAM traffic in one surface (derived sum). [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: example is from an older Quest (the 1216x1344 surface suggests Quest 1 or Quest 2 at low scale); the stage names are current on all devices · Evidence: [doc]
  - Notes: A healthy eye-buffer surface should show StoreColor (the resolve) and no Load* or StoreDepthStencil stages.
- **A2-055** Never store MSAA samples to DRAM. Resolve through pResolveAttachments on the **last** subpass, which uses the hardware resolve built into the tile store path. [T]
  - Resolving in an intermediate subpass breaks the benefit.
  - So does a separate vkCmdResolveImage.
  - So does an over-conservative subpass dependency (plain SHADER_READ instead of BY_REGION / input-attachment access).
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A3-020** MSAA resolves on-chip in tile memory with no extra system-memory traffic or blit. Qualcomm calls MSAA 2x "likely to be practically free": it may create more bins, but the extra binning and resolve cost is usually hidden. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md and https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: This holds only when samples are not stored (A3-006). Qualcomm publishes no 4x MSAA cost figure for Adreno 740.
- **A3-021** Qualcomm recommends allocating MSAA and transient depth attachments with `VK_MEMORY_PROPERTY_LAZILY_ALLOCATED_BIT` when they are never read outside the render pass. That keeps them GMEM-only. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md (accessed 2026-09-24) · Applies to: all Quest devices, Vulkan · Evidence: [doc]
  - Notes: The Unity equivalent is `RenderTextureMemoryless` (a lead for the URP topic).
- **A2-056** Measured MSAA cost on the original Quest (Adreno 540, 1216x1344 eye buffer): [T]
  - 4x MSAA adds roughly 0.5 to 1.5 ms per frame, about 10 to 15% for medium apps; do not exceed 4x
  - normal scene render: 2.65 → 3.15 ms
  - resolve: 0.17 → 0.44 ms
  - heavy-vertex binning: 1.419 → 1.534 ms

  Meta's improved-algorithms page calls 4x MSAA "extremely cheap".
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-msaa-analysis/ ; https://developers.meta.com/horizon/documentation/unity/gpu-improved-algorithms/ (accessed 2026-09-24) · Applies to: measured on the original Quest (stale hardware); directionally valid for Quest 2/3 · Evidence: [measured]
  - Notes: no Quest 2 or Quest 3 MSAA cost table is published. Measure with ovrgpuprofiler Render/Resolve stages at 1x/2x/4x and a locked GPU level. [verify on device]
- **A2-057** Subpass merging keeps intermediate results in GMEM and gives ">10%" frame-time gains, but only in binning mode. Qualcomm's merge conditions:
  - more than one subpass, with input attachments
  - each resolve attachment used in exactly one subpass
  - srcAccessMask without SHADER_WRITE and dstAccessMask without SHADER_READ
  - dstAccessMask = INPUT_ATTACHMENT_READ from the second subpass on

  Snapdragon Profiler's Rendering Stages view shows whether passes merged. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: URP's Native RenderPass / Render Graph subpass merging is the Unity path. Unity-side conditions belong to the URP topic.
- **A2-058** On the Adreno 540 and 650, a subpass can read 2 MSAA input-attachment samples in parallel, but not 4. A 2x MSAA subpassLoad is effectively free; 4x is not. Meta says the 740's behaviour may differ and does not state it. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2 (confirmed); Quest 3 unknown · Evidence: [doc]
- **A3-022** Input attachments and subpasses: Adreno 540 and 650 read two MSAA subsamples of an input attachment in parallel, so 2x reads are free and 4x are not. Meta has not confirmed the behaviour on Adreno 740. Common subpass mistakes that silently spill to DRAM are an intermediate resolve, an intermediate store, and over-conservative dependencies. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 1/2 (confirmed), Quest 3/3S unconfirmed · Evidence: [doc]
  - Notes: [verify on device] on Adreno 740. A VKLoadInput stage in the RenderDoc Tile Timeline shows input-attachment loads.
- **A2-059** Meta: reading a texture produced by a previous pass from main memory is about an order of magnitude slower than reading it from tile memory. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/gpu-impaired-algorithms/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-060** Query costs scale with bin count. [T] [C]
  - Occlusion queries: command-processor overhead is 20 to 40% in binned mode vs 4 to 6% in direct mode.
  - Timer queries: add 2 to 5 µs per tile.
  - Derived: at 135 bins, one timer query costs about 0.27 to 0.68 ms, which is 2 to 5% of a 13.9 ms (72 Hz) budget.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: strip GPU timer markers from shipping builds. The overhead shows up as higher "% CP Busy" in Snapdragon Profiler.
- **A2-061** Meta: a timer query forces a flush. If a timer query sits before the invalidate, the invalidate is ignored and the depth buffer gets stored. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A3-023** A GPU timer query placed before an invalidate forces a flush, so the invalidate no longer saves the store. Place timestamps with care when measuring load/store. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: This matters when adding custom GPU profiling markers from C#.
- **A2-062** Qualcomm: multiview saves CPU work only and has no GPU impact. Combine foveated rendering with VRS for GPU savings. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: Meta states that on Quest 2 both views share bins (hardware multiview). Whether that shares binning work is unpublished (see Known unknowns).

### 3.8 Arm/Mali to Adreno transfer map

- **A2-095** These generic TBR practices **transfer**: [T]
  - loadOp CLEAR/DONT_CARE and storeOp DONT_CARE
  - TRANSIENT_ATTACHMENT + LAZILY_ALLOCATED for pass-local attachments
  - in-tile MSAA resolve through pResolveAttachments
  - no vkCmdClear* where a loadOp would do
  - subpasses so G-buffer data stays on chip

  Arm's Khronos Vulkan-Samples and Qualcomm/Meta give the same advice.
  - Source: https://docs.vulkan.org/samples/latest/samples/performance/render_passes/README.html ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-096** Mali tile geometry does **not** transfer.
  - Mali renders 16x16-pixel tiles, and subpass merging requires at most 128 bits per pixel of tile colour storage (256 on newer Malis).
  - Adreno sizes whole bins from the GMEM budget: 96x176, 128x224 and 320x192 appear in Meta examples. [T]
  - Source: https://docs.vulkan.org/samples/latest/samples/performance/subpasses/README.html ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Mali-only rule; Adreno uses A2-013 · Evidence: [doc]
  - Notes: do not apply "fit G-buffer in 128 bpp" on Quest. The Adreno constraint is the total bytes per pixel × samples × views versus GMEM.
- **A2-097** Mali Forward Pixel Kill (FPK) and PowerVR-style hidden-surface removal do **not** transfer. Adreno relies on LRZ (binning-pass coarse Z) plus early-Z, and Qualcomm tells you to keep sorting front-to-back (A2-039). [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-098** Mali Pixel Local Storage does **not** transfer. [T]
  - gpuinfo GLES reports for Quest 2 (Adreno 650) and Quest 3 (Adreno 740) list no EXT_shader_pixel_local_storage.
  - They do list:
    - EXT_shader_framebuffer_fetch
    - QCOM_shader_framebuffer_fetch_noncoherent
    - ARM_shader_framebuffer_fetch_depth_stencil
    - QCOM_tiled_rendering
    - QCOM_texture_foveated / foveated2
    - QCOM_shading_rate
  - On Vulkan the on-chip path is subpass input attachments.
  - VK_QCOM tile-shading / tile-memory-heap extensions are A8x only (A840+), not Quest.
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [community]
- **A2-099** Mali counters and the Mali Offline Compiler do **not** transfer.
  - Examples: PTILES, Streamline templates, Mali cycle estimates from malioc.
  - Quest equivalents are ovrgpuprofiler metrics, Snapdragon Profiler, RenderDoc Meta Fork and the Adreno Offline Compiler. [C]
  - Source: https://docs.vulkan.org/samples/latest/samples/performance/subpasses/README.html (Mali PTILES usage) ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: Mali "arithmetic/load-store/texture cycles" from malioc have no Adreno meaning. Mali register-count occupancy thresholds and 16-wide warps do not map to Adreno wave64/128 either.
- **A2-100** Arm's measured bandwidth figures are Mali-phone numbers and transfer only as ratios, not as absolutes. [T]
  - On a Mali-G76 phone (2168x1080 at 60 fps), a separate vkCmdResolveImage for 4x MSAA added about 5 GB/s.
  - Arm estimates that DDR traffic costs about 100 mW per GB/s.
  - In-tile resolve cost about 3% more bandwidth.
  - Source: https://docs.vulkan.org/samples/latest/samples/performance/msaa/README.html (accessed 2026-09-24) · Applies to: Mali-G76 phone; the direction of the effect transfers to Quest · Evidence: [measured]
  - Notes: no published Quest DRAM energy per GB/s. `% Stalled on System Memory` and `GPU % Bus Busy` are the closest Quest-side proxies.

### 3.9 Compute on Quest

- **A2-093** Qualcomm prefers fragment shaders to compute for image work, because fragment output uses the concurrent resolve hardware (and compute writes tend to cost UBWC; see A2-043). [T]
  - Keep graphics submits and compute dispatches separate.
  - On GLES, glDispatchIndirect with a workgroup smaller than 64 causes a CPU wait.
  - On A7x, size local groups in multiples of 64/128 and workgroup counts in multiples of 16 (8 when groups share memory).
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (accessed 2026-09-24) · Applies to: all (A7x sizing applies to Quest 3/3S) · Evidence: [doc]
  - Notes: compute shared memory is 32 KB per workgroup on both the 650 and the 740 (Mesa).
- **A2-094** LPAC (a low-priority async compute queue, exposed through VK_KHR_global_priority LOW) exists on the Adreno 740 and later: Quest 3/3S but not Quest 2. LPAC shaders get a slightly higher instruction limit. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [doc]
  - Notes: whether Unity exposes a LOW global-priority queue on Quest is unknown. Lead for the compute topic.

---

## 4. Adreno shader cost model: fp16, register pressure and occupancy, texture fetch and filtering

### 4.1 fp16, GPRs, occupancy, wave size and instruction limits

- **A2-063** Qualcomm: a fragment shader using mediump (fp16) can be about twice as power-efficient and about twice as fast as highp (fp32). Use strict half types where possible; relaxed precision "often" yields fp16 code. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-064** Chips and Cheese measured double-rate FP16 on the A6xx Adreno 640 (after correction) and on the A7xx X1. The first A640 test showed no fp16 gain because vectorised test code caused register pressure. [T]
  - Source: https://chipsandcheese.com/p/correction-on-qualcomm-igpus ; https://chipsandcheese.com/p/the-snapdragon-x-elites-adreno-igpu (accessed 2026-09-24) · Applies to: Adreno 6xx/7xx family (proxy for 650/740) · Evidence: [measured]
  - Notes: fp16 gains depend on the compiler keeping values in half registers. Check GPR counts, not just the source code.
- **A2-065** Unity: `half` compiles to RelaxedPrecision on Vulkan (mediump on GLES) when the Shader Precision Model allows 16-bit.
  - Mobile targets get this by default; Player Settings > Shader Precision Model > Uniform forces it on all platforms.
  - Literals like `2.0h` are treated as full-precision float.
  - `half` values in buffers still take 32 bits.
  - `Texture2D<half4>` requests half sampling. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/SL-Use16BitPrecisionInShaders.html ; https://docs.unity3d.com/2022.3/Documentation/Manual/SL-Use16BitPrecisionInShaders.html (accessed 2026-09-24) · Applies to: Unity 2022.3 through 6.x (2021.3 page not checked) · Evidence: [doc]
  - Notes: RelaxedPrecision is the "relaxed" path Qualcomm says often yields fp16 (A2-063). Whether a given shader actually runs in fp16 must be checked in compiled output or shader stats. [verify on device]
- **A2-066** Converting between fp32 and fp16, or between int and float, costs instructions. Qualcomm's example: `int4 + 1.0` becomes about 8 instructions instead of 1. Implicit vec4 → vec3 truncation of a texture result adds one. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: mixing half and float in one expression chain in HLSL pays conversion cost. Keep a chain in one precision.
- **A2-067** GPRs decide occupancy: more GPRs per wave means fewer resident waves and worse latency hiding. [T]
  - A low "% Wave Context Occupancy" means GPR or instruction-cache thrash.
  - Loop unrolling raises GPRs, because it pulls texture fetches to the top of the shader.
  - Each interpolated varying occupies a GPR.
  - Split shaders that spill.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: no published GPR-to-occupancy table for the 650 or 740. Measure with Snapdragon Profiler shader stats or Wave Context Occupancy (A2-088).
- **A2-068** Wave size: [T]
  - A6xx and A7xx run wave64 and wave128 (Mesa `supports_double_threadsize`; Chips and Cheese).
  - Mesa uses wave_granularity = 2 and fibers_per_sp = 128*2*16 for both the 650 and the 740.
  - Qualcomm's later laptop GPU, the Adreno X2, moved to wave64 only (Chips and Cheese); it is not a Quest part.
  - Source: https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py ; https://chipsandcheese.com/p/the-snapdragon-x-elites-adreno-igpu (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [community]
  - Notes:
    - Divergence is paid per 64- or 128-wide wave, far wider than Mali's 16-wide warps. Per-pixel divergent branches are relatively costlier on Adreno.
    - The Vulkan subgroup size on Quest has no published number. Query `VkPhysicalDeviceSubgroupProperties` / `SubgroupSizeControl` on device.
- **A2-069** Uber-shader branches, from cheapest to most expensive: [T]
  1. branch on a Vulkan specialization constant: free, stripped at compile time
  2. branch on a compile-time constant: possibly free
  3. branch on a uniform: per-wave load and test, and both sides may run
  4. branch on a shader-computed value: likely both sides run

  Uber-shaders without specialization constants often raise GPRs.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: Unity keyword variants behave like compile-time constants. Uniform-driven dynamic branching is case 3. Unity-specific mapping belongs to the shader-variants topic.
- **A2-070** A7x performance cliffs: [T]
  - graphics-queue shaders take a potential penalty at each multiple of 2000 instructions (2256 for LPAC compute)
  - penalties also at each multiple of 32 vertex buffers, 16 unique UBOs, and 16 textures+SSBOs combined
  - 16 samplers on A6x through A8x: fragment and compute share one sampler cache, the vertex stage has its own
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (accessed 2026-09-24) · Applies to: Quest 3/3S (A7x limits); Quest 2 sampler limit (A6x) · Evidence: [doc]
  - Notes: no published A6x instruction-count threshold. Big URP Lit variants with many texture slots can cross the 16-texture line.
- **A2-071** Instruction cache: a shader that does not fit causes stalls. Split long shaders, especially ones that rarely stall on texture fetches (with few stalls, the scheduler has no chance to swap waves). [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-072** Special functions and integer math on the Adreno 640 (OpenCL microbenchmarks): [T]
  - special functions (rsqrt, exp, log, sin and similar) run at 1/8 rate
  - integer adds run at half rate, and 64-bit integer halves it again
  - The X1 (A7xx) article describes eight special-function units alongside the 64-wide FP32 ALUs. If that count is per 64-wide partition, the ratio is again 1/8; the article's exact grouping was not confirmed here.
  - Source: https://chipsandcheese.com/p/inside-the-snapdragon-855s-igpu ; https://chipsandcheese.com/p/the-snapdragon-x-elites-adreno-igpu (accessed 2026-09-24) · Applies to: A6xx/A7xx proxies · Evidence: [measured]
  - Notes:
    - Budget each transcendental at about 8 FMA-equivalents of throughput.
    - `pow` expands to exp2(log2), so it costs two.
    - No published number for the 650/740 themselves. [verify on device]
- **A2-073** Pack varyings: every interpolated value occupies a 4-component slot, so for example put two float2 UVs in one float4. Use constants rather than varyings for uniform values. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-074** Constants: [T]
  - pack scalar constants into vec4 (or at least vec2) for fetch efficiency
  - keep the sum of UBOs referenced by one shader under about 0.9 × 8192 = 7372 bytes so they stay in constant RAM
  - prefer UBOs to push constants
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: in Unity, the combined size of UnityPerDraw, UnityPerMaterial, the global and light constant buffers is what counts. Large per-material CBUFFERs push toward the limit. [verify on device]
- **A2-075** Mesa records a scalar ALU (`has_scalar_alu`) on the 650 and the A7xx, and an "early preamble" on the A7xx. Wave-uniform math can run on scalar hardware or be hoisted into a per-draw preamble, so math on uniforms only is cheaper than per-pixel math. [T]
  - Source: https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py (accessed 2026-09-24) · Applies to: Quest 2 (scalar ALU); Quest 3/3S (both) · Evidence: [community]
  - Notes: this is how Turnip uses the hardware. Qualcomm-driver behaviour is not published. [verify on device]
- **A2-076** Qualcomm prefers GLSL built-in functions over hand-written equivalents. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-077** Qualcomm's pipeline-creation advice: [T] [C]
  - create all graphics and compute pipelines at initialisation to avoid hitches
  - pass VK_PIPELINE_CREATE_LINK_TIME_OPTIMIZATION_BIT_EXT in shipping builds
  - use specialization constants rather than runtime uber-branches
  - the Adreno GLES driver never recompiles programs
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: Unity PSO warm-up and pipeline caching belong to the shader-compilation topic.

### 4.2 Texture fetch and filtering cost

- **A2-078** Filtering cost order is nearest/bilinear < trilinear < anisotropic. [T]
  - 16x anisotropic can be up to 16x the cost of an isotropic lookup.
  - Because aniso is adaptive, the real-world average is under 2x isotropic.
  - Mip clamping reduces the average cost of trilinear.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: an aniso-heavy view (floors at grazing angles, which are common in VR) is the worst case. Cap aniso per texture rather than setting a global 16x.
- **A2-079** Explicit-gradient sampling (dFdx/dFdy fed into textureGrad or SampleGrad) costs more than a normal sample. The gradients are not cached, so every repeated lookup with the same gradients pays again. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: triplanar mapping, parallax and virtual-texture shaders in Unity often use SampleGrad.
- **A2-080** Qualcomm's texture advice: [T]
  - the hardware works on 2x2 quads, so keep neighbouring pixels sampling neighbouring texels
  - avoid 3D textures (their filtering is expensive)
  - compress all textures
  - use mipmaps for fetch coalescing
  - wide formats, gradients that vary across a quad, and differing LODs within a quad all slow sampling
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-081** Texture caches are tiny, so dependent or random reads thrash L1 quickly. [T]
  - Adreno 640: 1 KB texture L1 per uSPTP, 68.1% hit rate in 3DMark Wild Life Extreme; 128 KB L2 (UCHE) at about 47 cycles; about 30 GB/s DRAM.
  - X1 (A7xx): 2 KB L1 per uSPTP.
  - Source: https://chipsandcheese.com/p/inside-the-snapdragon-855s-igpu ; https://chipsandcheese.com/p/the-snapdragon-x-elites-adreno-igpu (accessed 2026-09-24) · Applies to: A6xx/A7xx proxies · Evidence: [measured]
  - Notes:
    - No 650/740 cache sizes published.
    - Watch `% Texture L1 Miss`, `L1 Texture Cache Miss Per Pixel` and `% Texture Fetch Stall` in ovrgpuprofiler (A2-087).
- **A2-082** A5x published ratios (latest generation with numbers): [T]
  - one texture fetch per fragment at full rate balances about 16 full-precision ALU ops
  - ASTC stays compressed in L2 and is decompressed into L1
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (accessed 2026-09-24) · Applies to: A5x only. No published number was found for A6x/A7x. · Evidence: [doc]
  - Notes: use 16:1 only as a rough starting point. Measure the ALU:TEX balance with `% Shaders Busy` vs `% Texture Fetch Stall`.
- **A2-083** Qualcomm: combined image samplers use the bindless path. Separate sampler objects showed 2 to 5% lower fill rate. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: Unity HLSL declares a separate Texture2D and SamplerState. How Unity's SPIR-V cross-compile emits them on Quest (combined or separate) is not documented here (see Known unknowns).
- **A2-084** How buffers reach the texture pipe: [T]
  - read-only storage buffers are converted to texture-pipe fetches, which hides latency but loads the texture pipe
  - DXC/glslang may turn HLSL buffers into SSBOs
  - GPU-driven designs tend to bottleneck the texture pipe
  - prefer vertex buffers, then UBOs, over storage buffers where the data fits
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: Unity StructuredBuffer reads (GPU instancing data, BRG/Entities Graphics) go through this path. [verify on device]
- **A2-085** Adreno has hardware percentage-closer filtering (bilinear shadow compare), so use comparison samplers rather than manual multi-tap depth compares. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A2-086** Texture-format priorities: ASTC first, then ETC2; HDR and LDR ASTC profiles are supported. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A3-015** Texture bandwidth: Qualcomm's main levers are block-compressed formats (4x4 blocks aligned to pixel boundaries, so fetches coalesce), with ASTC preferred in sRGB where applicable. On A5x, ASTC stays compressed in L2 and is decompressed into L1, while ETC stays compressed in L1. [T] [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md and https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/spec_sheets.md (accessed 2026-09-24) · Applies to: all Quest devices; the L1/L2 detail is stated only for A5x (Quest 1) · Evidence: [doc]
  - Notes: The L1/L2 behaviour of Adreno 650 and 740 is not published. [verify on device] via % Texture L1 Miss for ASTC vs uncompressed on the same draw.
- **A3-017** These increase texture sampling time: trilinear and anisotropic filtering, wide texture formats, 3D textures, and gradient or LOD variation across a quad. Mipmaps help coalesce fetches, and bilinear or nearest filtering can be cheaper. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: Qualcomm publishes no per-filter cost on Adreno 740. Measure with the % Anisotropic/Linear/Nearest Filtered and % Non-Base Level Textures draw metrics (A3-040). [verify on device]

### 4.3 Shader-cost tools: compilers, counters, shader stats

- **A2-087** ovrgpuprofiler exposes real-time metrics (`-m` lists them, `-r` streams them), including:
  - Clocks / Second
  - % Vertex Fetch Stall, % Texture Fetch Stall
  - % Texture L1 Miss, % Texture L2 Miss, L1 Texture Cache Miss Per Pixel
  - % Stalled on System Memory
  - % Prims Trivially Rejected

  Metric IDs are list positions and vary by device and runtime, so always list them first. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes: never hard-code metric IDs in scripts shared across devices.
- **A2-088** Use ovrgpuprofiler per-draw metrics (`-x`) only to compare draws against each other: they add pipeline stalls, so absolute times are skewed. [C]
  - Per-pass metric limits apply. Split large metric sets across runs.
  - The trace flags include a low-overhead mode for more accurate stage timing.
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
- **A2-089** Qualcomm tooling: [C]
  - Qualcomm recommends the Adreno Offline Compiler for shader optimisation.
  - Vulkan shader stats (e.g. in Snapdragon Profiler) need driver version 636 or later.
  - Check the driver with `adb shell dumpsys SurfaceFlinger | grep GLES`, which prints e.g. "V@0676.0".
  - In VkPhysicalDeviceProperties, driverVersion encodes 10 bits major, 10 minor, 12 patch.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
  - Notes: Quest drivers are Meta builds. Offline-compiler output from a phone driver may differ from Quest. [verify on device]
- **A2-091** RenderDoc Meta Fork has a Tile Timeline view for inspecting per-bin work. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
- **A2-092** Mesa's Turnip debug flags (`sysmem`, `gmem`, `nobin`, `nolrz`, `noubwc`, `forcebin`) mirror the hardware levers in this document. They do not exist on Quest's Qualcomm driver, so do not recommend them for Quest. [C]
  - Source: https://docs.mesa3d.org/drivers/freedreno.html (accessed 2026-09-24) · Applies to: none on Quest (reference only) · Evidence: [community]

---

## 5. Bandwidth as the dominant power and thermal cost

### 5.1 DRAM energy and derived traffic budgets

- **A3-001** An off-chip DRAM access costs about 1-2 nJ. An on-chip cache access or ALU operation costs about 10 pJ, roughly two orders of magnitude less. Most of the gap comes from DRAM I/O at over 20 pJ/bit, and even improved I/O stays around 10 pJ/bit (about 0.6 nJ per 8 bytes). A cache fetch is about 20 pJ. [T] [C]
  - Source: Horowitz, "Computing's Energy Problem", ISSCC 2014, https://gwern.net/doc/cs/hardware/2014-horowitz-2.pdf (accessed 2026-09-24) · Applies to: all SoCs (figures are for 45 nm, 0.9 V) · Evidence: [doc]
  - Notes: The paper is pre-2023 and on an old node, so the absolute values are stale. The ratio between off-chip and on-chip energy is the durable part. No XR2 Gen 2 / LPDDR5 energy-per-bit figure has been published (see Known unknowns).
- **A3-002** Arm's rule of thumb: external DRAM traffic costs roughly 120 mW per 1 GB/s of bandwidth, and on-chip tile memory access is about an order of magnitude cheaper. [T] [C]
  - Source: Peter Harris (Arm), "The Mali GPU: An Abstract Machine, Part 2 - Tile-based Rendering", 2014-02-20, archived copy https://web.archive.org/web/20191215124148/https://community.arm.com/developer/tools-software/graphics/b/blog/posts/the-mali-gpu-an-abstract-machine-part-2---tile-based-rendering (accessed 2026-09-24) · Applies to: any tile-based mobile GPU with LPDDR, used here for the Adreno energy model only · Evidence: [doc]
  - Notes: The source is Mali-era (2014) and Arm says the figure depends on system design. Stale as an absolute number. As a check, 120 mW per GB/s is about 15 pJ/bit, which sits between Horowitz's 10 and 20 pJ/bit I/O figures (derived). A "100 mW per GB/s" variant attributed to Arm's current best-practices guide (developer.arm.com 101897) appeared only in search snippets; the page is JS-rendered and could not be read.
- **A3-008** Every extra full-screen pass adds a fixed store of the whole target, proportional to resolution, and the next pass usually reads it back as a texture. This is why post-processing is costly on tilers even when its shader is cheap. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: Meta's thermal page lists "heavy shaders plus high-resolution post-processing" as a thermal-pressure pattern (A3-079).
- **A3-009** Derived eye-buffer store on Quest 3S: the default eye texture is 1680x1760 per eye. A single resolved RGBA8 store for both eyes is 23.65 MB per frame, which is about 1.70 GB/s at 72 Hz, 2.13 GB/s at 90 Hz and 2.84 GB/s at 120 Hz. [T] [C]
  - Source: default texture size from https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (accessed 2026-09-24) · Applies to: Quest 3S and Quest 3 (same default, ARM-GF2-004) · Evidence: [doc]
  - Notes: Derived arithmetic (1680 x 1760 x 2 x 4 B x Hz). UBWC reduces the bytes actually moved (ratio unpublished), and FFR/FDM changes the shaded area but not the stored size. At Arm's 2014 rule of ~120 mW per GB/s (A3-002), 1.7 GB/s is on the order of 0.2 W. That is an order-of-magnitude estimate only. [verify on device]
- **A3-010** Derived eye-buffer store on Quest 3 at panel resolution: 2064x2208 per eye gives 36.46 MB per frame for one RGBA8 store of both eyes. That is about 2.62 GB/s at 72 Hz, 3.28 GB/s at 90 Hz and 4.38 GB/s at 120 Hz. [T] [C]
  - Source: panel resolution from https://developers.meta.com/horizon/essentials/compare-devices/ (accessed 2026-09-24) · Applies to: Quest 3 · Evidence: [doc]
  - Notes: Derived. Round-2 correction: the sysprops page does list a Quest 3 default, 1680x1760, the same as Quest 3S (ARM-GF2-004, ARM-C21). These panel-resolution figures are therefore an upper bound for apps that raise the eye-texture scale, not the default workload; the default-resolution figures are those in A3-009, which apply to Quest 3 as well. Read the real surface size from the ovrgpuprofiler surface line or `debug.oculus.textureWidth/Height`. [verify on device]
- **ARM-GF2-004** Meta's system-properties page gives device-specific defaults for the eye-texture override properties: `debug.oculus.textureWidth` = 1216 (Quest), 1440 (Quest 2 and Pro), 1680 (Quest 3 and Quest 3S); `debug.oculus.textureHeight` = 1344 (Quest), 1584 (Quest 2 and Pro), 1760 (Quest 3 and Quest 3S). [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3, Quest 3S (per-eye default at render scale 1.0) · Evidence: [doc]
  - Notes: Found in the round-2 spot-check of A3-009/A3-010. Quest 3 and 3S render the same default eye buffer despite different panels (2064x2208 vs 1832x1920, A1-025), so default per-frame GPU and bandwidth cost is the same on both at equal settings; the difference appears only when an app scales resolution to the panel. Derived: 1680x1760 is 1.30x the pixels of Quest 2's 1440x1584, matching Meta's "about 30% larger" (A1-020).
- **A3-011** Derived cost of breaking the load/store rules on Quest 3S. Also storing a D24S8 depth buffer (4 B/px) doubles the A3-009 figure. Storing 4x MSAA color and depth samples (32 B/px) is 8x the resolved-color figure: about 189 MB per frame, or about 13.6 GB/s at 72 Hz. At the Arm rule of thumb that is on the order of 1.6 W, compared with about 0.2 W for a correct setup. [T] [C]
  - Source: inputs from https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ and https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (accessed 2026-09-24) · Applies to: Quest 3S (scale for other devices) · Evidence: [doc]
  - Notes: Derived. UBWC may compress depth (D16, D24_S8 and D32 support UBWC per Qualcomm), so real bytes are lower. [verify on device] with Write Total (A3-037).
- **A3-012** Derived cost of one extra full-screen RGBA8 pass at the Quest 3S default resolution: a store plus a read-back is about 47 MB per frame, or about 3.4 GB/s at 72 Hz. An FP16 (8 B/px) intermediate doubles that to about 6.8 GB/s. [T] [C]
  - Source: inputs from https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ and https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 3S · Evidence: [doc]
  - Notes: Derived. Texture-cache hit rates and UBWC change the read side, so [verify on device].
- **A3-016** Qualcomm names cache misses as the usual route into a bandwidth limit. They come from drawing many primitives or from shaders touching many scattered texture locations. The fix is to reduce the data each draw or dispatch touches. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: Diagnose with % Texture L1/L2 Miss and % Stalled on System Memory (A3-039).
- **A3-026** Qualcomm's other bandwidth levers: keep intermediates in GMEM, and reuse the Z-buffer across passes, which allows concurrent binning. Depth-only passes with an empty fragment shader and color writes masked get Fast-Z, which writes Z-only pixels at twice the normal rate. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md and https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: Relevant to shadow-map passes in URP.

### 5.2 Measuring bandwidth on Quest (counters, tools, commands)

- **A3-027** `adb shell ovrgpuprofiler -m` lists the supported metrics, and `-m -v` shows descriptions. Meta's example lists 47 metrics. Metric IDs vary by device and runtime, so look them up on each device before scripting `-r`. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24; page updated 2026-09-09) · Applies to: Quest 2/3/3S/Pro, VR Glasses · Evidence: [doc]
  - Notes: Never hard-code metric IDs in a skill.
- **A3-028** Meta's example realtime list starts with: Clocks / Second, GPU % Bus Busy, % Vertex Fetch Stall, % Texture Fetch Stall, L1 Texture Cache Miss Per Pixel, % Texture L1 Miss, % Texture L2 Miss, % Stalled on System Memory, Pre-clipped Polygons/Second, % Prims Trivially Rejected, % Prims Clipped. The realtime bandwidth proxies are Bus Busy and Stalled on System Memory. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: The page does not show whether byte counters (Read Total, Write Total) exist in the realtime set. [verify on device] with `ovrgpuprofiler -m -v`.
- **A3-029** Realtime mode: `ovrgpuprofiler -r<id,id,...>` samples up to 30 metrics at once. Detailed mode is enabled per package with `-e [package]`, then the app must be restarted. It costs about 10% GPU overhead and is turned off with `-d`. Use `-i` to query its state. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: Disable detailed mode before any thermal or long-session run, because the ~10% overhead distorts clock-level behaviour.
- **A3-030** Trace mode: `ovrgpuprofiler -t[sec]` (default 0.1 s), `-c` continuous, `-l` low overhead, `-v` per-bin breakdown. Each surface line shows the size, the color/depth/stencil bit depth, MSAA, the render mode, the bin count and size, the total time, and per-stage times, for example `Mode: 1 (HwBinning) | 60 128x224 bins | 5.08 ms | ... StoreColor : 0.309ms`. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: This is the fastest command-line check for unwanted Load*/Store* stages.
- **A3-031** Render stage names worth tracking for bandwidth: Binning, Render, LoadColor, StoreColor, LoadDepthStencil, StoreDepthStencil, Blit, Preempt, Load Store, and on Vulkan VKQueue, VKRenderClear and VKLoadInput. Load and store stage times are the direct, time-domain view of GMEM-to-DRAM traffic. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ and https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: Preempt time is compositor preemption, not app work.
- **A3-032** Per-stage and per-draw counters: `ovrgpuprofiler -m -t` lists per-render-stage metrics, and `-t3 -s <ids>` captures them. The SoC counter budget can reject some requested metrics, and the tool reports how many were rejected. `-x -m` lists per-draw metrics, and `-t3 -x=<ids>` traces per draw and prints the LRZ state. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: When counters are rejected, split the capture into several runs.
- **A3-033** Render modes in the trace: 0 Direct, 1 HwBinning, 2 SwBinning, 3 HwDirect. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: An eye-buffer surface in direct mode loses FFR (A3-024).
- **A3-034** Reading multiview output: the original Quest prints one surface per eye (add them). Quest 2 prints one surface whose bins are shared by both views, so read `135 96x176 bins` as 135 x 2. Quest 3/3S and VR Glasses print one surface line covering both views. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 1/2/3/3S, VR Glasses · Evidence: [doc]
  - Notes: The RenderDoc render-stage page still carries an unresolved TODO about how Quest 3/3S multiview appears there.
- **A3-035** RenderDoc Meta Fork adds a Tile Timeline (render-stage trace) showing, per surface, the render mode, bin count and size, and stage timings including LoadDS/StoreDS and VKLoadInput. Surface Information lists the attachment attributes. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ and https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ (accessed 2026-09-24; both updated 2026-09-09) · Applies to: Quest 1/2/Pro/3/3S · Evidence: [doc]
  - Notes: Meta positions RenderDoc Meta Fork as the tile-renderer profiler for the XR2 family.
- **A3-036** RenderDoc Meta Fork draw-call bandwidth metrics:
  - `Read Total (Bytes)` and `Write Total (Bytes)`: all GPU memory traffic, whichever block issued it.
  - `Texture Memory Read BW (Bytes)`: texture-pipe reads, including vertex textures and compute.
  - `Vertex Memory Read (Bytes)`: non-texture vertex fetch.
  - `SP Memory Read (Bytes)`: explicit shader loads, for example SSBOs. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) · Applies to: Quest devices supported by RenderDoc Meta Fork · Evidence: [doc]
  - Notes: These are the only documented per-draw byte counters on Quest.
- **A3-037** Summing `Write Total (Bytes)` across the draws of an eye-buffer pass and comparing it with the derived resolved-color size (A3-009, A3-010) reveals unwanted depth or MSAA stores. A value several times the derived figure points to stored samples or depth. [T] [C]
  - Source: metric definitions from https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: This is a method built from documented metrics. It is not a Meta recipe. Store traffic may be charged to the last draw in a bin, or to no draw at all. [verify on device]
- **A3-038** `Avg Bytes / Fragment` is texture memory read divided by fragments shaded. Meta itself calls it imprecise. `Avg Bytes / Vertex` is Vertex Memory Read divided by vertices shaded. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) · Applies to: Quest devices supported by RenderDoc Meta Fork · Evidence: [doc]
  - Notes: Useful for ranking materials by texture bandwidth, not as an absolute.
- **A3-039** `% Stalled on System Memory` is the share of draw cycles in which L2 waits on system memory. Together with `% Texture Fetch Stall` and `% Vertex Fetch Stall`, it identifies draws that are bandwidth- or latency-bound rather than ALU-bound. All draw-call percentages are shares of that draw's clock cycles. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) · Applies to: Quest devices supported by RenderDoc Meta Fork · Evidence: [doc]
  - Notes: For thresholds see A3-054.
- **A3-040** Texture-side draw metrics:
  - `% Texture L1 Miss` and `% Texture L2 Miss` (miss-to-request ratios)
  - `L1 Texture Cache Miss Per Pixel`
  - `% Anisotropic Filtered`, `% Linear Filtered`, `% Nearest Filtered`
  - `% Non-Base Level Textures`
  - `% Texture Pipes Busy` [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) · Applies to: Quest devices supported by RenderDoc Meta Fork · Evidence: [doc]
  - Notes: A high % Non-Base Level share together with a high L1 miss rate usually means mips are working. A low % Non-Base Level on minified surfaces suggests missing mips (interpretation, [verify on device]).
- **A3-041** The draw-call metrics table currently lists about 48 metrics, including `Preemption` and `Avg Preemption Delay`. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ (accessed 2026-09-24) · Applies to: Quest devices supported by RenderDoc Meta Fork · Evidence: [doc]
  - Notes: A search snippet cited 59 metrics (ARM-C16). The count depends on the device.
- **A3-042** RenderDoc Meta Fork settings Meta recommends for profiling: a timer query per render pass, "Disable TimeWarp on replay", and replay optimisation level "Fastest". [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ (accessed 2026-09-24; page updated 2024-12-15) · Applies to: Quest devices supported by RenderDoc Meta Fork · Evidence: [doc]
  - Notes: See A3-023 for how timer queries interact with invalidates.
- **A3-043** On Quest 3, Vulkan multiview shows in RenderDoc as one surface with 2 render targets. Quest 3/3S (Adreno 740) support `VK_QCOM_multiview_per_view_viewports` and `VK_QCOM_multiview_per_view_render_areas`, which Quest 2 does not. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: Per-view render areas let the driver skip bins outside each eye's visible area. Unity exposure is unknown (lead).
- **A3-044** Scripted capture (2026): the RenderDoc Meta Fork install ships Claude Code skills at `C:\Program Files\RenderDocForMetaQuest\.claude\skills`. The CLI flow is `renderdoccmd adb-list`, then `renderdoccmd adb-launch-drawcall-profiling --device <SERIAL> --package <pkg>`, then `renderdoccmd adb-capture --device <SERIAL> --ident <IDENT> --frames 1`. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-ai-tools/ (accessed 2026-09-24; page updated 2026-09-09) · Applies to: Quest devices supported by RenderDoc Meta Fork · Evidence: [doc]
  - Notes: The same page says non-debuggable builds on API 34 and above need `adb root; adb shell setprop persist.debug.dalvik.vm.jdwp.enabled 1; adb reboot`. [verify on device] on retail units.
- **A3-045** Perfetto via MQDH records GPU counters and render stages. The options are GPU Metrics, GPU Render Stage Trace, "Enable high precision GPU render stage tracing", XR Runtime Metrics, and ATrace Apps, which must include the Unity package name. CPU callstack sampling is available from v51. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (accessed 2026-09-24; page updated 2026-09-03) · Applies to: Quest 2/3/3S/Pro · Evidence: [doc]
  - Notes: The exact GPU counter track names Perfetto shows on Quest are not documented (Known unknowns).
- **A3-046** Older Perfetto workflow (OS v27 era): VrApi and GPU metrics are emitted as `track_event` data. GPU metrics appear only while `adb shell ovrgpuprofiler -r...` runs in the background. Perfetto has been on by default in developer mode since v27. [T]
  - Source: https://developers.meta.com/horizon/blog/how-to-run-a-perfetto-trace-on-oculus-quest-or-quest-2/ (accessed 2026-09-24) · Applies to: Quest 1/2 at the time · Evidence: [doc]
  - Notes: Pre-2023, possibly stale. Current MQDH exposes GPU Metrics as a checkbox (ARM-C18).
- **A3-047** The MQDH Performance Analyzer includes a "GPU Memory Access" module that reports GPU memory read/write bandwidth. This is the only live bandwidth graph documented in a Meta GUI tool. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ (accessed 2026-09-24; page updated 2026-04-08) · Applies to: Quest devices supported by MQDH · Evidence: [doc]
  - Notes: Units, sampling rate and the underlying counter are not documented. [verify on device] against RenderDoc Read Total and Write Total.
- **A3-048** OVR Metrics Tool exposes no bytes or bandwidth stat. Its ovrgpuprofiler-backed stats are:
  - Average Vertices Per Frame and Average Fill Percentage per Eye
  - Avg Instructions per Fragment and per Vertex, and Avg Textures per Fragment
  - % Time Shading Fragments and % Time Shading Vertices
  - Vertex Fetch Stall % and Texture Fetch Stall %
  - L1 and L2 Texture Miss %
  - % samples using Nearest, Linear or Anisotropic filtering

  It also shows memory frequency (MEM F). [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ and https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ (accessed 2026-09-24) · Applies to: all current Quest devices · Evidence: [doc]
  - Notes: Use OVR Metrics for trends and RenderDoc for bytes.
- **A3-049** OVR Metrics commands:
  - Launch: `adb shell am start omms://app`
  - Enable CSV: `adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV`
  - Other actions: ENABLE_OVERLAY, DISABLE_OVERLAY, ENABLE_GRAPH and ENABLE_STAT (`--es stat <stat>`), ENABLE_DROPPED_FRAME_SCREENSHOT, LOG_STATE.
  - CSVs are written to `/sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/`. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24; page updated 2026-06-21) · Applies to: all current Quest devices · Evidence: [doc]
  - Notes: This is the documented path for unattended long-session thermal logging (A3-093).
- **A3-050** From Unity, `OVRMetricsToolSDK.Instance.GetLatestMetricsSnapshot()` reads live metrics. `AppendCsvDebugString`, `SetOverlayDebugString` and `DefineAppMetric`/`UpdateAppMetric` tag CSV rows or the overlay with app state, for example the scene or quality tier. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Unity on Quest · Evidence: [doc]
  - Notes: This makes it possible to correlate level drops with content in the CSV.
- **A3-051** Isolating app GPU cost for repeatable measurement:
  - Pin levels with `adb shell setprop debug.oculus.cpuLevel 4` and `debug.oculus.gpuLevel 4`.
  - Disable foveation with `debug.oculus.foveation.level 0` and `debug.oculus.foveation.dynamic 0`.
  - Stop compositor rendering with `adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SKIP_RENDERING --ei milliseconds 60000`, so that TW=0 and `App=` shows only the app's GPU time. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ and https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S/Pro · Evidence: [doc]
  - Notes: Pinned levels still throttle when hot, so check PLS during the run.
- **A3-052** Meta says to disable dynamic resolution while profiling, because it changes the rendered viewport and so the per-frame cost. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24; page updated 2026-08-06) · Applies to: Quest 2 and later · Evidence: [doc]
  - Notes: The trade-off is that GPU level 5 is then unavailable (A3-085).
- **A3-053** The VrApi logcat line includes `Mem=<MHz>` (memory clock; Meta's examples show 2092 MHz in the full line and 1804 MHz in the field table, see ARM-GF1-004; corrected in the round-2 spot-check), and OVR Metrics shows MEM F. These are the only documented memory-side clock signals. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ and https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S/Pro · Evidence: [doc]
  - Notes: Meta does not document whether the memory clock scales with the CPU/GPU level or under throttling. [verify on device]
- **ARM-GF1-004** Meta's logcat-stats page shows two different `Mem=` values: the full example line has `Mem=2092MHz`, while the per-field table defines the field with `Mem=1804MHz` ("Speed of the memory."). Neither value is tied to a named headset. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ (accessed 2026-09-24; page updated 2025-07-31) · Applies to: all Quest (device for each example not stated) · Evidence: [doc] [verify on device]
  - Notes: Found in the round-1 spot-check of AS-001; it corrects the earlier statement that 2092 MHz is the only published memory-clock value (ARM-C24). Treat both as examples of the field format, not as device specifications. Read `Mem=` (logcat) or MEM F (OVR Metrics) on each headset, at several CPU/GPU levels, before deriving any bandwidth ceiling from it.
- **A3-054** Qualcomm's healthy ranges for Adreno counters that share names with Meta's tools:
  - % Stalled on System Memory under ~2% (short spikes to 30%).
  - % Texture Fetch Stall under ~2% (sustained ~16% or more is too high).
  - % Texture L1 Miss under 50% and % Texture L2 Miss under 40%.
  - % Vertex Fetch Stall near 0%.
  - Binning at 10-20% of the render pass (30% is too much).
  - GPU % Bus Busy up to ~25% for a battery-conscious app, and up to ~90% for a max-performance app. [T] [C]
  - Source: Qualcomm guide 80-78185-2, Snapdragon Profiler chapter (last published 2026-09-22), https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md (accessed 2026-09-24) · Applies to: Adreno in general, not Quest-specific · Evidence: [doc]
  - Notes: For thermally constrained VR, the battery-conscious Bus Busy band is the safer target (interpretation).
- **A3-055** Qualcomm marks the GPU memory stats as "Slow To Trace" because they add significant overhead. They are Avg Memory Latency Cycles, Texture Memory Read BW, Vertex Memory Read (high reads during binning explain slow binning) and Write Total (writes to main memory are expensive, lower is better). [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md (accessed 2026-09-24) · Applies to: Adreno in general · Evidence: [doc]
  - Notes: Capture bytes counters in a separate pass from timing.
- **A3-056** Android's AGI documents Adreno memory counters as Read Total (Bytes/sec), Write Total (Bytes/sec), Vertex Memory Read (Bytes/Second), Texture Memory Read (Bytes/Second) and % Stall on System Memory. It flags fetch stalls above ~5% as a concern. AGI is now superseded by Android Performance Analyzer (APA). [T]
  - Source: https://developer.android.com/agi/sys-trace/memory-efficiency (accessed 2026-09-24; page updated 2026-05-19) · Applies to: Adreno Android devices; Quest support for AGI/APA is not documented · Evidence: [doc]
  - Notes: The names match Meta's RenderDoc metrics, which suggests the same Qualcomm counter library (inference).

---

## 6. Thermals: how CPU/GPU levels map to clocks, and throttling behaviour

The level-to-clock tables are in section 1.3 (A1-005 / A3-068 / A3-069). This section covers the level APIs, availability rules, Boost/dual-core/trading, the governor, throttling and the power signals.

### 6.1 The level system and its APIs

- **A1-028** Apps do not set clocks directly. They choose a ProcessorPerformanceLevel, and the OS keeps the CPU/GPU levels at the lowest value in that range that holds the frame rate. [T] [C]

  | ProcessorPerformanceLevel | CPU levels | GPU levels |
  |---|---|---|
  | PowerSavings | 0–4 | 0–4 |
  | SustainedLow | 2–4 | 1–4 |
  | SustainedHigh (default) | 4–4* | 3–5 |
  | Boost | 4 to device max | 3–5 |

  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S; Unity 2021.3–6.6 with Meta XR Core SDK · Evidence: [doc]
  - Notes: *The SustainedHigh CPU range becomes 5–5 with level trading and 6–6 with dual-core mode. The "Essentials" version of this page gives different ranges (ARM-C4, ARM-C5). Meta's rule is to pick the lowest levels that hold the target frame rate consistently.
- **A1-029** API surface for requesting levels: [T] [C]
  - Unity: `OVRPlugin.suggestedCpuPerfLevel` / `suggestedGpuPerfLevel`, exposed as `OVRManager.suggestedCpuPerfLevel`.
  - Native: `ovrp_SetSuggestedCpuPerformanceLevel` / `ovrp_SetSuggestedGpuPerformanceLevel`.
  - OpenXR: XR_EXT_performance_settings. Meta's native sample calls `xrPerfSettingsSetPerformanceLevelEXT` for the CPU and GPU domains.
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ and https://raw.githubusercontent.com/meta-quest/Meta-OpenXR-SDK/main/Samples/SampleXrFramework/Src/XrApp.cpp (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The sample maps values 0–3 to POWER_SAVINGS / SUSTAINED_LOW / SUSTAINED_HIGH / BOOST. For Unity projects on OpenXR without the Meta SDK, see A1-045.
- **A1-045** The Unity OpenXR plugin exposes performance levels without the Meta SDK. [T] [C]
  - 1.11.0 (2024-05-01) added `XrPerformanceSettings.SetPerformanceLevelHint` (XR_EXT_performance_settings) and `OnXrPerformanceChangeNotification`.
  - 1.7.0 (2023-02-21) enabled XR_META_performance_metrics.
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/changelog/CHANGELOG.html (accessed 2026-09-24) · Applies to: Unity projects on com.unity.xr.openxr ≥1.11 · Evidence: [doc]
  - Notes: Performance-change notifications fire when the runtime throttles, which gives a hook for shedding CPU work. Check that your Unity version supports package 1.11+.
- **A3-076** ProcessorPerformanceLevel ranges:
  - PowerSavings: CPU 0-4, GPU 0-4.
  - SustainedLow: CPU 2-4, GPU 1-4.
  - SustainedHigh: CPU 4-4, GPU 3-5. This is the default. With trading, CPU becomes 5-5; with dual-core mode, 6-6.
  - Boost: CPU 4 to the device maximum, GPU 3-5.

  The OS picks a level inside the range and stays as low as possible while holding frame rate. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: Levels are hints, not guaranteed clocks.
- **A3-077** Level APIs: Unity uses `OVRPlugin.suggestedCpuPerfLevel` and `OVRPlugin.suggestedGpuPerfLevel` (also exposed through `OVRManager`). Native uses `ovrp_SetSuggestedCpuPerformanceLevel` and `ovrp_SetSuggestedGpuPerformanceLevel`. Spatial SDK uses `spatial.setPerformanceLevel`. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ and https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: For Boost, the Unity sample sets `OVRManager.suggestedCpuPerfLevel = ProcessorPerformanceLevel.Boost` and later reverts to `SustainedHigh`.
- **A1-041** Meta describes CPU and GPU levels as hints: a request does not guarantee a processor clock speed. Battery saver mode reduces performance, and apps should detect it and lower their fidelity. [C]
  - Source: https://developers.meta.com/horizon/essentials/performance-hardware/ (accessed 2026-09-24; updated Sep 15, 2026) · Applies to: all Quest · Evidence: [doc]
  - Notes: Drive a runtime quality ladder from the measured frame time and the level actually granted, not from the requested level.
- **A1-036** OS features running in the background (Meta's example is casting) can override which levels an app gets. Check the level actually granted during a capture with XrPerformanceManager logcat lines and the OVR Metrics "CPU L / GPU L" overlay. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Record the CPU/GPU level with every perf capture. Captures taken while casting or recording are not comparable.

### 6.2 Level availability, passthrough caps, Boost, dual-core mode and level trading

- **A3-071** Quest 2 level availability: CPU 0-4 always, CPU 5 when dual-core mode is off, CPU 6 when dual-core mode is on, and CPU 8 only while the CPU Boost hint is active. GPU 0-4 always, and GPU 5 only with dynamic resolution enabled. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 2 · Evidence: [doc]
  - Notes: See ARM-C5 about the level-trading row that lists Quest 2.
- **A3-072** Quest 3/3S level availability: CPU 0-3 always; CPU 4 only when the app does not enable passthrough; CPU 5 only with CPU 4 available and trading set to -1 (favour CPU). GPU 0-2 always; GPU 3-4 only without passthrough; GPU 5 only with GPU 4 available and either trading +1 or dynamic resolution. With passthrough on, an MR app is therefore capped at CPU L3 (1.65 GHz) and GPU L2 (456 MHz). [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [doc]
  - Notes: The passthrough cap is a large budget cut for MR titles (lead for the MR topic). The availability table labels the boost level "6" (ARM-C4).
- **A1-018** With passthrough enabled on Quest 3/3S, the availability table caps sustained CPU at level 3 (1.65 GHz) and GPU at level 2 (456 MHz). CPU level 4 and GPU levels 3–4 are listed as available only without passthrough. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S, mixed reality (MR) apps · Evidence: [doc]
  - Notes: The caps are derived from the availability table. The Boost row carries no passthrough condition. [verify on device] with OVR Metrics "CPU L / GPU L" in an MR scene. Derived budget: an MR main thread gets about 22.9 M cycles per frame at 72 Hz (1.65 GHz × 13.9 ms), against 26.7 M in VR.
- **A1-019** Meta says passthrough costs 17% of GPU and 14% of CPU performance compared with a VR-only app, and the Depth API adds further GPU cost. Even a full MR app on Quest 3 still has more compute left over than a Quest 2 has in total. [T]
  - Source: https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ (accessed 2026-09-24; Oct 11, 2023) · Applies to: Quest 3 (3S assumed the same, since the SoC is identical) · Evidence: [doc]
  - Notes: These percentages are from the launch-era OS. The level caps in A1-018 may be how the cost is enforced. Re-measure on the current OS.
- **A1-033** On Quest 3/3S, favoring the CPU buys nothing in passthrough apps. CPU level 5 is available only "if CPU level 4 is available", and level 4 is unavailable with passthrough. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S MR apps · Evidence: [doc]
  - Notes: Derived by combining two availability rows. For a CPU-bound MR app, the options are moving work into jobs, using Boost for bursts, or cutting CPU work. The trading setting is not one of them. [verify on device]
- **A3-073** Quest Pro uses the Quest 2 clock table, but CPU 4 and GPU 4 are available only when the app does not enable passthrough, eye tracking, face tracking, body tracking or gaze-based foveated rendering. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest Pro · Evidence: [doc]
  - Notes: None.
- **A1-035** Quest Pro (one line, eye-tracked foveation): CPU and GPU level 4 are unavailable when passthrough, eye/face/body tracking or gaze-based foveated rendering is enabled. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest Pro only · Evidence: [doc]
  - Notes: Out of scope beyond this line.
- **A1-030** CPU Boost raises the CPU from level 4 to level 8: +64% on Quest 2 and Pro (1.48 → 2.42 GHz) and +23% on Quest 3/3S (1.92 → 2.36 GHz). [T] [C]
  - It activates only while Battery Saver is off and the device is not throttling.
  - It lasts at most 45 consecutive seconds and at most 20% of app runtime.
  - To use it, set `OVRManager.suggestedCpuPerfLevel = ProcessorPerformanceLevel.Boost;` and revert to `SustainedHigh` when done.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24; updated Sep 2, 2026) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: Use Boost for loading screens, scene transitions and bursts of simulation, never for steady-state frames. While inactive, Boost behaves like SustainedHigh. The same page is inconsistent about the runtime cap (ARM-C6) and the Quest 3 ceiling (ARM-C4).
- **A3-089** The CPU Boost hint raises CPU level 4 to 8: +64% on Quest 2 and Pro, +23% on Quest 3/3S, and +30% on VR Glasses. It activates only when Battery Saver is off and thermal management is not throttling. On Quest it is limited to 45 consecutive seconds and 20% of app runtime. VR Glasses instead use a token bucket: a full 45 s budget that refills at about 15 s per minute. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S, VR Glasses · Evidence: [doc]
  - Notes: Boost is refused while throttling, so it cannot rescue a hot device.
- **A1-031** Dual-core mode disables one app core and gives its thermal budget to the remaining two, raising SustainedHigh to CPU level 6–6 (2.15 GHz). [T]
  - It exists on Quest 2 and Pro only, and needs the OpenXR backend (not legacy OVRPlugin).
  - Enable it in the manifest with `<meta-data android:name="com.oculus.dualcorecpuset" android:value="true" />`.
  - Verify it with the logcat line `CreateClient: Value of isCPUSingleThreadedBoost is 1`.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2, Quest Pro · Evidence: [doc]
  - Notes: Meta says 3 cores at level 4 beat dual-core mode at level 6, and advises profiling level 5 (three cores) against dual-core. Losing a core also removes one job-worker slot (A1-051).
- **A3-090** Dual-core mode disables one app CPU core and gives its thermal budget to the other two. It is available on Quest 2 and Pro only, and requires the OpenXR backend. Enable it with the manifest entry `<meta-data android:name="com.oculus.dualcorecpuset" android:value="true" />`; SustainedHigh then becomes CPU 6-6. Meta says three cores at level 4 beat dual-core mode at level 6 when the app is truly multithreaded. Check logcat for `isCPUSingleThreadedBoost is 1`. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2, Quest Pro · Evidence: [doc]
  - Notes: None.
- **A1-032** CPU/GPU level trading is Quest 3/3S only, needs the OpenXR backend and is fixed at build time. [T]
  - Manifest key: `com.oculus.trade_cpu_for_gpu_amount`.
  - Values: 1 = +1 GPU / −1 CPU; 0 = no change; −1 = −1 GPU / +1 CPU.
  - Unity exposes it as "Processor Favor" on OVRManager/OVRCameraRig.
  - Verify it with the logcat line `CreateClient: Value of tradeCpuForGpu is <n>`.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S (not Meta VR Glasses) · Evidence: [doc]
  - Notes: With −1 (favor CPU), CPU level 5 (2.05 GHz, +7% over L4) becomes available. With +1 (favor GPU), GPU level 5 (599 MHz, +10% over L4) becomes available. Percentages are derived. Changing the setting needs a new build.
- **A3-091** CPU/GPU level trading is available on Quest 3/3S only, requires the OpenXR backend, and is fixed at build time. Set it with the manifest entry `<meta-data android:name="com.oculus.trade_cpu_for_gpu_amount" android:value="1" />`. Values: 1 gives +1 GPU and -1 CPU; -1 gives the reverse; 0 means no change. In Unity it is "Processor Favor" on OVRManager/OVRCameraRig. Meta frames it as choosing which processor keeps its speed when thermal throttling downclocks. Check logcat for `tradeCpuForGpu is 1`. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [doc]
  - Notes: The levels page contradicts the device scope (ARM-C5).
- **ARM-GF1-003** Meta frames CPU/GPU level trading as a thermal-throttling preference: when throttling forces the governor to downclock, the app's manifest setting says whether to preserve CPU or GPU speed. The choice is set in the app manifest and can change only with a new build. Meta VR Glasses do not support trading. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24; page updated 2026-09-02) · Applies to: Quest 3/3S only (Meta says no other headset supports it) · Evidence: [doc] [verify on device]
  - Notes: This wording sits alongside the availability-table conditions (CPU 5 needs trading -1; GPU 5 needs trading +1 or dynamic resolution; A3-072). Whether trading changes the steady-state level when the device is not throttling is not stated on the Boost page; confirm by logging CPU L / GPU L in OVR Metrics with and without the manifest entry over a 20-30 minute run.
- **A1-034** On every Quest model, GPU level 5 needs dynamic resolution and is blocked by Battery Saver. Meta says to treat GPU level 4 as the maximum budget and L5 as an opportunistic quality bump, because throttling is much more common at L5. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: This is the GPU counterpart of the CPU guidance: size the app for L4.
- **A3-085** GPU level 5 requires dynamic resolution because Meta says thermal throttling is much more common at level 5. When the headset drops back to level 4, dynamic resolution keeps the frame rate by lowering resolution. Battery Saver also blocks level 5. Meta's advice is to target GPU level 4 as the maximum budget and treat 5 as an opportunistic quality bump. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (accessed 2026-09-24; page updated 2026-09-02) · Applies to: Quest 2/Pro/3/3S · Evidence: [doc]
  - Notes: This is Meta's explicit statement that levels are lowered when the device heats.

### 6.3 Governor hysteresis, staged throttling and stale guidance

- **A1-037** Level changes use hysteresis: CPU goes up at ≥83% and down at ≤77%; GPU goes up at ≥87% and down at ≤81%. Under PowerSavings or SustainedLow, an app hovering near 80% CPU utilization can see its level, and therefore its frame time, oscillate. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: The SustainedHigh CPU range is 4–4, so it cannot oscillate. Choosing SustainedLow to save battery trades away frame-time consistency (derived).
- **A3-070** Governor thresholds on Quest 2, Pro, 3/3S and VR Glasses: the CPU level rises at 83% utilisation or more and falls at 77% or less. The GPU level rises at 87% or more and falls at 81% or less. The original Quest used 91% and 85% for the GPU. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: An app that sits just under 87% GPU never earns a higher GPU level, and one that sits at ~84% can oscillate. Keep GPU utilisation well clear of the band (interpretation).
- **A3-078** Horizon OS thermal management is staged:
  1. Sustained workload budgeting of CPU and GPU levels.
  2. Throttling, where clocks drop, per-frame cost rises and frame timing becomes more variable.
  3. FrameSync adaptation to absorb the variability.
  4. A forced low-power cool-down state with a user notification. [C]
  - Source: https://developers.meta.com/horizon/essentials/thermal/ (accessed 2026-09-24; page updated 2026-09-15) · Applies to: all current Meta VR devices · Evidence: [doc]
  - Notes: Sensors cover the SoC, the battery and the surface. On VR Glasses the glasses and the compute puck are separate thermal domains.
- **A1-038** Meta's thermal guidance (Sep 2026): as sensors approach their limits, the system lowers clocks, so per-frame cost rises and frame timing becomes more variable. Meta advises three things. [C]
  - Profile long sessions; Meta warns about a "thermal cliff at minute ten".
  - Stay below the sustained level you actually need.
  - Stagger expensive work across frames.
  - Source: https://developers.meta.com/horizon/essentials/thermal/ (accessed 2026-09-24; updated Sep 15, 2026) · Applies to: all Quest devices · Evidence: [doc]
  - Notes: For CPU work, spread periodic jobs (streaming decode, physics substeps) across frames rather than spiking one frame. More detail is in sibling A3.
- **A3-079** Meta names the most common shipping mistake: profiling only the start of a session and missing the thermal cliff at minute ten. It lists these thermal-pressure patterns:
  - heavy shaders combined with high-resolution post-processing
  - continuous full-resolution passthrough alongside a heavy 3D scene
  - always-on physics, particles or dynamic lighting
  - not using foveated rendering or App Spacewarp [C]
  - Source: https://developers.meta.com/horizon/essentials/thermal/ (accessed 2026-09-24) · Applies to: all current Meta VR devices · Evidence: [doc]
  - Notes: Meta publishes no minutes-to-throttle number. "Minute ten" is guidance, not a measurement.
- **A3-080** Meta's thermal guidance: stay below the sustained level you actually need. Keep Boost for short bursts such as loading, transitions or physics spikes. Spread expensive work evenly across frames, because predictable per-frame cost produces the lowest sustained heat. React to battery saver. Test on device. [C]
  - Source: https://developers.meta.com/horizon/essentials/thermal/ (accessed 2026-09-24) · Applies to: all current Meta VR devices · Evidence: [doc]
  - Notes: None.
- **A3-086** With dynamic resolution enabled, Horizon OS lowers the app's render scale during a thermal event to avoid dropped frames. Eye textures are allocated once at the maximum scale and the viewport is scaled, so memory use is set by the maximum while bandwidth follows the viewport. Unity controls are `OVRManager.instance.enableDynamicResolution`, `XRSettings.renderViewportScale` and `XRSettings.eyeTextureResolutionScale`. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24; page updated 2026-08-06) · Applies to: Quest 2 and later · Evidence: [doc]
  - Notes: The same page lists a URP known issue: additional lights are misaligned under dynamic resolution (Forward+ and Deferred+). This is a lead for the URP topic.
- **A1-007** A December 2022 OS change raised Quest 2 GPU level 4 from 490 to 525 MHz (+7%). On OS v47 the new clock needed a doff/don or sleep cycle; from v49 it applies immediately. When dynamic foveation is enabled, the system raises the clock before raising foveation. [T]
  - Source: https://developers.meta.com/horizon/blog/boost-app-performance-525-mhz-gpu-frequency-meta-quest-2/ (accessed 2026-09-24; Dec 21, 2022) · Applies to: Quest 2 · Evidence: [doc]
  - Notes: The post is pre-2023, but the current table still shows 525 MHz at L4. Any table that lists 490 MHz as L4 is stale.
- **A3-087** Quest 2 GPU level 4 was raised from 490 to 525 MHz (+7%). On OS v47 a doff/don or sleep cycle was needed before the new clock applied; from v49 it applied immediately. [T]
  - Source: https://developers.meta.com/horizon/blog/boost-app-performance-525-mhz-gpu-frequency-meta-quest-2/ (OS v47 era, accessed 2026-09-24) · Applies to: Quest 2 · Evidence: [doc]
  - Notes: Pre-2023 tables showing 490 MHz at L4 are stale (baseline table).
- **A3-088** UploadVR (2024-10-31) reported that unannounced firmware raised the Quest 3 default maximum GPU clock from 545 to 599 MHz and the Favor GPU mode clock from 599 to 640 MHz, also for Quest 3S. The higher clock needs dynamic resolution, and when hot the OS falls back to the previous maximum and lowers resolution. Meta told UploadVR that Red Matter 2 held the higher clock for 85% of playtime, and that Favor GPU costs 16% of maximum CPU clock. [T] [C]
  - Source: https://www.uploadvr.com/meta-quest-3-gpu-clock-speed-performance-boost/ (2024-10-31, accessed 2026-09-24) · Applies to: Quest 3, Quest 3S · Evidence: [community]
  - Notes: The 85% sustain figure is Meta-supplied through the press, for one title, with no test conditions. The 640 MHz figure is not in the current levels table (ARM-C3).
- **A1-039** FrameSync replaces PhaseSync as Horizon OS frame timing. [C]
  - Test it from OS v201 with `<meta-data android:name="com.oculus.enable_frame_sync" android:value="true"/>`.
  - From v203 it is the default for Store apps, with an opt-out.
  - Meta warns it can slightly raise CPU/GPU utilization.
  - Source: https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ (accessed 2026-09-24; Mar 3, 2026) · Applies to: Quest 3/3S on Horizon OS v201+ · Evidence: [doc]
  - Notes: FrameSync changes when the app's frame starts relative to vsync, so it affects main/render-thread timing. Re-baseline CPU frame timings across v203. Details belong to the frame-pacing topic.
- **A1-040** Meta's 2022 power guidance said Unity apps should always use multithreaded rendering, because two cores at 1 GHz work more efficiently than one core at 2 GHz. The current Boost page says the same: spreading work across cores at lower clocks is generally more power-efficient. [C] [T]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/ (accessed 2026-09-24; updated Sep 29, 2022) · Applies to: all Quest; the principle only · Evidence: [doc]
  - Notes: Pre-2023, from the deprecated VrApi docs. Its clock-level API (`vrapi_SetClockLevels`, default 2/2) is obsolete. Only the parallelism principle carries forward.
- **A3-094** Deprecated Meta power page (2022, VrApi era): lowering clocks all the way gives only about 25% less power for the same work, so most savings must come from doing less work. Poor performance after about ten minutes is typical of hitting the thermal governor. Meta also said CPU load seems to cause more thermal trouble than GPU load, and that two cores at 1 GHz are more efficient than one at 2 GHz. [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/ (page updated 2022-09-29; accessed 2026-09-24) · Applies to: Quest 1/2 era · Evidence: [doc]
  - Notes: Pre-2023 and deprecated, so possibly stale. Its throttling model (power-save levels equal to (0,0), VRAPI_SYS_STATUS_THROTTLED) predates the 2026 staged model (ARM-C17). The "25%" is the only Meta figure found on power versus clock level.
- **A3-096** The deprecated power page gave `adb shell setprop debug.oculus.adaclocks.force 0` to disable dynamic clock throttling during testing. [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/ (page updated 2022-09-29; accessed 2026-09-24) · Applies to: Quest 1/2 era · Evidence: [doc]
  - Notes: Stale. The current docs instead pin levels with `debug.oculus.cpuLevel`/`gpuLevel` (A3-051). [verify on device] whether the property still has any effect.
- **A3-095** Qualcomm's testing protocol: play for at least 10 minutes while tracking CPU and GPU clocks. Thermal throttling usually hits both processors or neither. Trace expensive frames after about the tenth minute, and allow at least 20 minutes of cool-down at room temperature (about 21 °C) between sessions. [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md (accessed 2026-09-24) · Applies to: Snapdragon devices in general · Evidence: [doc]
  - Notes: Matches Meta's "minute ten" guidance (A3-079).
- **A3-093** Recipe for measuring long-session throttling:
  1. Start the OVR Metrics CSV (A3-049), including CPU L, GPU L, CPU F, GPU F, POW L, stale frames and app GPU time.
  2. Run a fixed, representative scene for 30 minutes or more, with dynamic resolution and the ProcessorPerformanceLevel as shipped.
  3. Mark the first minute at which POW L leaves 0 or the maximum level drops.
  4. Repeat after a cool-down of at least 20 minutes at about 21 °C (A3-095). [C]
  - Source: tool capabilities from https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S/Pro · Evidence: [doc]
  - Notes: No published Quest measurement of minutes-to-throttle was found (Known unknowns). [verify on device]
- **A3-075** On Meta VR Glasses, Meta says to design the steady state against the "nominal" level (CPU 4 / GPU 4), which the OS sustains under worst-case thermal and battery conditions. Clocks may rise above nominal when there is headroom, for example while charging. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/optimize-performance/ (accessed 2026-09-24; page updated 2026-09-19) · Applies to: Meta VR Glasses · Evidence: [doc]
  - Notes: This is the clearest Meta statement of a sustainable level. No equivalent statement was found for Quest 2/3/3S, though "target GPU level 4" (A3-085) is similar.

### 6.4 Power and thermal signals

- **A3-081** Power level is the thermal signal. It is PLS in VrApi logcat and Power Level (POW L) in OVR Metrics, with values 0 NORMAL, 1 SAVE and 2 DANGER. It rises automatically as the headset heats, and DANGER shows an overheat dialog. Meta says apps should monitor it and reduce their cost. [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ and https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S/Pro · Evidence: [doc]
  - Notes: No Unity C# API for reading PLS directly was found. Read it through the OVR Metrics SDK snapshot or from logcat ([verify on device] which snapshot field carries it).
- **A3-082** Meta says the temperature stats (Sensor Temperature and Battery Temperature, B TEM) mattered for phone-based VR, and that current headsets should use Power Level instead. For battery drain, Meta says to optimise against CPU/GPU levels rather than Battery Current (BAT C, mA) or Power Current (POW C, mA). [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ (accessed 2026-09-24; page updated 2024-12-15) · Applies to: all current Quest devices · Evidence: [doc]
  - Notes: BAT C, POW V and POW C are still logged and are the only documented raw power signals.
- **A3-083** VrApi logcat (`adb logcat -s VrApi,XrPerformanceManager`) prints the levels and clocks every second, for example `CPU4/GPU=2/2,1171/441MHz`, along with `Mem=`, `PLS=`, `Temp=`, `GPU%=`, `CPU%=`, `LP=` (battery saver) and `DVFS=`. Meta says DVFS is currently never enabled, and that GPU% above 0.9 risks scheduling problems. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ (accessed 2026-09-24; page updated 2025-07-31) · Applies to: Quest 2/3/3S/Pro · Evidence: [doc]
  - Notes: Meta's own example shows 1171/441 MHz. 1171 MHz is Quest 2 CPU L2 (1.17 GHz); 441 MHz is close to Quest 2 GPU L2 (442 MHz). The example is consistent with the Quest 2 table.
- **A3-084** Seeing why the OS chose a level:
  - `XrPerformanceManager` logs changes such as `SetClockLevels: Apply pending clock request change: 4,3 -> 3,3`.
  - `adb shell setprop debug.oculus.clockStateLogLevel 1` (or 2) prints Min, Max and Final levels with reasons, including FORCED and REJECTED entries, for example a max of 5 forced by the dynamic-resolution boost, or a level clamped to the hardware maximum.
  - Reset with 0, or reboot. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S/Pro · Evidence: [doc]
  - Notes: This is the best tool for confirming thermal-driven level drops versus app-requested ones.
- **A3-092** Battery Saver (Settings > General > Power) does the following:
  - lowers brightness to 40%
  - forces FFR level 3
  - forces 72 Hz
  - disables GPU level 5 and CPU boost

  VrApi logcat shows it as `LP=`. No app-facing detection API is documented, although Meta tells apps to detect it and adapt. [C]
  - Source: https://developers.meta.com/horizon/essentials/battery-saver-mode (accessed 2026-09-24; page updated 2026-04-08) and https://developers.meta.com/horizon/documentation/unity/os-battery-saver-mode/ (page updated 2025-07-29) · Applies to: current Quest devices · Evidence: [doc]
  - Notes: A 120 Hz title silently runs at 72 Hz under Battery Saver, which changes every per-frame budget.

---

## 7. Profilers on Quest: Snapdragon Profiler status and the Meta tools that replace it

### 7.1 Snapdragon Profiler on Quest: what works and what does not

- **A3-057** Meta's current developer-tools index does not list Snapdragon Profiler. It points to MQDH, RenderDoc Meta Fork, OVR Metrics Tool, Perfetto, gpumeminfo, Performance Analyzer and ovrgpuprofiler. [T] [C]
  - Source: https://developers.meta.com/horizon/resources/developer-tools/ (accessed 2026-09-24; page updated 2024-12-17) · Applies to: all current Quest devices · Evidence: [doc]
  - Notes: This is the effective "Meta-recommended alternative" set.
- **A3-058** In 2020 Meta built a Performance Interface Library (PIL) with Qualcomm. It exposes GPU data that was previously available only in Snapdragon Profiler through GPU Systrace and ovrgpuprofiler. [T]
  - Source: https://developers.meta.com/horizon/blog/improving-gpu-profiling-on-oculus-quest/ (2020-06-19; accessed 2026-09-24) · Applies to: Quest 1/2 at publication; the tool lineage continues · Evidence: [doc]
  - Notes: Pre-2023. It explains why counter names match Qualcomm's.
- **A3-059** The only current Meta page found that still mentions Snapdragon Profiler is the Unreal testing page (updated 2026-04-14). It lists the tool for CPU, GPU, DSP, memory, power, thermal and network analysis but gives no Quest-specific setup or caveats. [T]
  - Source: https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android/ (accessed 2026-09-24) · Applies to: Quest (Unreal page; the tool statement is engine-agnostic) · Evidence: [doc]
  - Notes: It is not referenced from any Unity page read.
- **A3-060** Snapdragon Profiler has three modes. Realtime covers CPU, EGL, GPU, memory, network, power, primitive processing, system memory and thermal. Trace includes Vulkan rendering stages and the API trace. Snapshot is a single-frame capture with draw list, resources, shader analysis, pixel history and overdraw. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md (accessed 2026-09-24; last published 2026-09-22) · Applies to: Snapdragon devices in general; Qualcomm names no Quest-specific support · Evidence: [doc]
  - Notes: The Qualcomm guide does not mention Quest.
- **A3-061** Snapdragon Profiler adds roughly 5% CPU overhead even when it traces only frame rate. [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md (accessed 2026-09-24) · Applies to: Snapdragon devices in general · Evidence: [doc]
  - Notes: On a CPU-bound Quest title, 5% can move the CPU level.
- **A3-062** Snapdragon Profiler shows each surface as "Optimal" (UBWC) or "Linear". No documented Meta tool reports UBWC status per surface. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md (accessed 2026-09-24) · Applies to: Adreno in general · Evidence: [doc]
  - Notes: This is a gap for checking UBWC on Quest (see Known unknowns).
- **A2-090** Snapdragon Profiler signals: [C]
  - Rendering Stages shows the render mode per surface and whether subpasses merged
  - % Wave Context Occupancy flags GPR or instruction-cache pressure
  - % CP Busy reveals query overhead
  - % Texture Pipes Busy tells you whether moving work to textures is safe
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: all · Evidence: [doc]
- **A3-063** Community report, Meta forum, 2020-12-02: Snapdragon Profiler did not work with Vulkan apps on Quest, and the app quit immediately on launch. The poster suspected a debugger conflict. [T]
  - Source: https://communityforums.atmeta.com/discussions/dev-quest/is-any-way-to-make-a-vulkan-gpu-capture-on-quest-/837235 (accessed 2026-09-24) · Applies to: Quest 1/2, 2020 · Evidence: [community]
  - Notes: Pre-2023, possibly stale. The thread shows no Meta staff answer.
- **A3-064** Community reports, Qualcomm QDN forum (archived):
  - 2019-06-25: the Native Tracing API crashed during Oculus Quest trace capture (SDP 1.0.7006, Unity 2019.1.6f1).
  - 2020-03-28: a snapshot hung at "Retrieving Snapshot" on Quest. The reply's fix was granting the app external-storage read/write.
  - 2021-01-25: a Quest 2 user asked how to enable enhanced capture statistics, such as MSAA resolves, and got no answer. [T]
  - Source: https://developer.qualcomm.com/forum/qdn-forums/software/snapdragon-profiler/66963 , /67580 , /68286 (via web.archive.org; accessed 2026-09-24) · Applies to: Quest 1/2, 2019-2021 · Evidence: [community]
  - Notes: Pre-2023, possibly stale. The QDN forums are retired.
- **A3-065** Community signals for Quest 3/3S: a Qualcomm support-forum thread titled "Snapdragon Profiler not able to capture anything on Meta Quest 3/3s" exists, but its content is JS-only and could not be read. A QDN thread titled "[Bug report] Quest 2 Unity Vulkan app crashes on startup" (id 69910) also exists, but it is not archived. [T]
  - Source: https://mysupport.qualcomm.com/supportforums/s/question/0D5dK000009EniESAS/snapdragon-profiler-not-able-to-capture-anything-on-meta-quest-33s and https://developer.qualcomm.com/forum/qdn-forums/software/snapdragon-profiler/69910 (titles only; accessed 2026-09-24) · Applies to: Quest 3/3S, Quest 2 · Evidence: [community]
  - Notes: Evidence is only the thread titles. [verify on device]
- **A3-066** Snapdragon Profiler is still actively released: search results referenced versions 2025.8 and 2025.9.0.93022025. No release note found states Quest support, and no last Quest-supported version has been published. [T]
  - Source: Qualcomm Snapdragon Profiler product and release pages (JS-only; seen only in search snippets), https://www.qualcomm.com/developer/software/snapdragon-profiler (accessed 2026-09-24) · Applies to: all Quest devices · Evidence: [community]
  - Notes: To test: install the current SDP, connect a Quest 3 in developer mode, and try Realtime (GPU, Thermal), then Trace (Vulkan rendering stages), then Snapshot on a debuggable Vulkan Unity build. Record which mode fails. [verify on device]
- **A3-067** Working position for the skill: treat Snapdragon Profiler as unsupported on Quest unless it is proven on the target OS build. Use ovrgpuprofiler for realtime counters and stage traces, RenderDoc Meta Fork for per-draw bytes and the Tile Timeline, Perfetto/MQDH for timelines, and OVR Metrics for long-session CSVs. [T] [C]
  - Source: synthesis of https://developers.meta.com/horizon/resources/developer-tools/ and https://developers.meta.com/horizon/blog/improving-gpu-profiling-on-oculus-quest/ (accessed 2026-09-24) · Applies to: all current Quest devices · Evidence: [doc]
  - Notes: Qualcomm's SDP thresholds (A3-054) still apply to the same-named counters.

### 7.2 CPU-side verification tools (Perfetto, OVR Metrics, logcat)

- **A1-084** Perfetto, launched from Meta Quest Developer Hub (MQDH), puts several data sources on one timeline: CPU Scheduling (per-core thread placement), XR runtime metrics, GPU metrics and TrackEvent markers. Since OS v51 it can also record callstack samples through traced_perf. For Unity, use a Development build or supply symbol files. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: This is the main tool for the open questions in this file: which cores UnityMain, UnityGfxDeviceW and the workers run on, and how often they migrate. Simpleperf has its own page: https://developers.meta.com/horizon/documentation/unity/ts-simpleperf/.
- **A1-085** The OVR Metrics Tool overlay shows the current CPU and GPU levels ("CPU L", "GPU L"). MQDH's Performance Analyzer shows both levels and frequencies; Meta's example shows a Quest 2 at CPU L4 / 1.478 GHz and GPU L3 / 490 MHz. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ and https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: Pin a known ProcessorPerformanceLevel before CPU A/B tests. Otherwise level changes (A1-037) swamp code-level differences.
- **A1-086** The old VrApi log line had the form `CPU{core}/GPU={lvl}/{lvl},{MHz}/{MHz}MHz,OC=..,TA=..,SP=..,Mem={MHz}MHz,...`. [C]
  - `OC` was the mask of online cores.
  - `TA` and `SP` gave the affinity and scheduling policy of the TimeWarp, main and render threads.
  - `Mem` was the memory clock.
  - CPU utilization was reported for the worst core.
  - Source: https://developers.meta.com/horizon/blog/ovr-metrics-tool-vrapi-what-do-these-metrics-mean/ (accessed 2026-09-24) · Applies to: VrApi apps only (legacy) · Evidence: [doc]
  - Notes: Pre-2023. OpenXR apps don't emit this line. See Gaps for the adb commands that give equivalent information, and use XrPerformanceManager logcat for levels.

---

## Conflicts

ARM-C1 to ARM-C18 merge the topic-note conflicts (A1-Cn, A2-Cn, A3-Cn). ARM-C19 to ARM-C24 are cross-topic conflicts found during synthesis and in the round-1 coverage pass. The round-1 spot-check re-read the Meta pages behind ARM-C3, C4, C5, C6 and C24 on 2026-09-24; all of those conflicts still appear on the live pages. The round-2 spot-check re-read the levels page (ARM-C4: the Quest 3/3S availability table still labels the Boost row "6"), the Boost page (ARM-C6: both the 20% and the 80% wording remain), the ovrgpuprofiler page (ARM-C3: 690/492 MHz remain) and the logcat page (ARM-C24: both 2092 and 1804 MHz remain). ARM-C25 was added in round 2.

- **ARM-C1** Quest 3/3S CPU core types (A1-C1). Wikipedia's Quest 3 and 3S infoboxes say 2x Cortex-A715 + 4x Cortex-A510, uncited ([community]), and UploadVR says "two performance cores and four efficiency cores" (https://www.uploadvr.com/snapdragon-xr2-gen-2/, [community]). Qualcomm's brief says "4 + 2 performance cores, up to 2.4/2.0 GHz" (https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf, [doc]; re-read 2026-09-24), and Geekbench's MIDR identifies Cortex-A78C r0p2 in clusters of 4 @ 2.36 GHz + 2 @ 2.05 GHz (https://browser.geekbench.com/v6/cpu/19064415, [measured]). Assessment: 6x Cortex-A78C. The 2+4 description confuses the two clock tiers with core types.
- **ARM-C2** Quest 3/3S memory type and data rate (A1-C2, A3-099, ARM-GF1-005).
  - Qualcomm brief: "4x16 LP-DDR5 memory, up to 3.2 GHz" ([doc]).
  - iFixit: LPDDR5 parts, SK hynix on Quest 3 and Micron MT62F1G64D4EK-026 on Quest 3S ([community]).
  - Micron press coverage (TweakTown, Oct 2023): 8 GB LPDDR5X at 8.533 Gbps "optimized for" XR2 Gen 2 and linked to Quest 3 (https://www.tweaktown.com/news/93872/microns-low-power-memory-optimized-for-snapdragon-xr2-gen-2-platform-vr-and-mixed-reality/index.html, [community]). Wikipedia's SoC list also says LPDDR5X.
  - Wikipedia infoboxes: Quest 3 "LPDDR5 @ 4200MT/s (68GB/s)" (internally inconsistent: 4200 MT/s x 8 B = 33.6 GB/s, derived) and Quest 3S "LPDDR4X @ 2600MT/s (42GB/s)", contradicted by iFixit ([community]).
  - Assessment: LPDDR5-class memory on both headsets; the controller may support LPDDR5X, but no source shows that Quest runs it at LPDDR5X rates. The configured data rate is unpublished. Measure (Known unknowns).
- **ARM-C3** Quest 3/3S peak GPU clock (A1-C3, A2-C3, A3-C1). Levels table: L5 = 599 MHz (https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/, [doc], updated 2026-09-02, re-read 2026-09-24). ovrgpuprofiler page: Quest 3 at 690 MHz and Quest 3S at 492 MHz (https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/, [doc], updated 2026-09-09, re-read 2026-09-24). UploadVR: 640 MHz in Favor GPU mode (https://www.uploadvr.com/meta-quest-3-gpu-clock-speed-performance-boost/, [community]). Assessment: budget with the levels table. 690 MHz equals Meta VR Glasses GPU L5 and 492 MHz equals Quest 3/3S GPU L3, which suggests copy errors on the profiler page. Read `Clocks / Second` or GPU F on device.
- **ARM-C4** Quest 3/3S CPU Boost level (A1-C4, A3-C2). The clock table lists L8 = 2.36 GHz and the Boost page gives 4 → 8, +23% (https://developers.meta.com/horizon/documentation/unity/po-quest-boost/, [doc]). The Quest 3/3S availability table on the levels page labels the Boost row "6" (2.21 GHz, which would be only +15%) ([doc]). The Essentials page gives "4 to 6 (Quest 3/3S)". Assessment: unresolved; the 23% figure matches 2.36/1.92. Read CPU L in OVR Metrics during Boost.
- **ARM-C5** Level-trading scope and the Quest 2 CPU 5 path (A1-C5, A3-C3). The levels page's SustainedHigh table lists CPU 5-5 for "Quest 2, Quest Pro, Quest 3 or 3S with CPU level trading" ([doc]). The Boost page says trading is supported only on Quest 3 and 3S (re-read 2026-09-24, [doc]). The Quest 2 availability table ties CPU 5 to dual-core mode being off. Assessment: trust the Boost page on device scope.
- **ARM-C6** Boost runtime cap (A1-C6). The Boost page says Boost may be active "for only 20% of your app's runtime" and, in the condition list, that it activates only if it "has not been active for 80%" of total runtime (both re-read 2026-09-24, [doc]). Assessment: 20% is most likely correct. [verify on device]
- **ARM-C7** Core count seen by apps on Quest 2 (A1-C7). Meta's docs imply 3 app cores ([doc]); Geekbench as a 2D app sees all 8 ([measured]). Assessment: 2D and VR apps may get different cpusets; `SystemInfo.processorCount` may not equal the usable core count. Measure.
- **ARM-C8** Minimum Unity version for Meta's Unity-PerformanceSettings sample (A1-C8). README: 6000.3.15f1 ([doc], GitHub). Meta doc page: 6000.0.66f2 ([doc]). Assessment: follow the README.
- **ARM-C9** Quest 3 / Adreno 740 GMEM (A2-C1). Meta: "approximately 2MB" (https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/, [doc], re-read 2026-09-24). Linux kernel: 3 MiB for the SD8 Gen 2 chip 0x43050a01, not the Quest chip 0x43050b00 ([community]). Chips and Cheese: 3 MB on the X1-85 ([measured]). Assessment: trust Meta for Quest; infer from ovrgpuprofiler bin sizes.
- **ARM-C10** Quest 2 / Adreno 650 GMEM (A2-C2). Meta: 1 MB ([doc]). Kernel: 1 MiB + 128 KiB ([community]). Meta's own 96x176 example needs about 1.03 MiB. Assessment: treat "1 MB" as rounded.
- **ARM-C11** Triangles crossing bin borders (A2-C4). Meta says a triangle "can be split" to fit a bin ([doc]); Qualcomm says no vertices are added at tile boundaries and the triangle is rasterised in full per tile ([doc]). Assessment: Qualcomm's wording is more specific; cost scales with bins touched.
- **ARM-C12** Direct mode and MSAA (A2-C5). Meta's MSAA analysis quotes Qualcomm: direct rendering only with MSAA off ([measured] page, original Quest). The current Qualcomm guide (2026-09-22) lists other direct-mode triggers and does not mention MSAA ([doc]). Assessment: unknown on current drivers; read the render mode per surface (A2-025, A3-033).
- **ARM-C13** Fragment density map (FFR) vs UBWC (A2-C6, A3-C5). Qualcomm lists VK_EXT_fragment_density_map among features that "almost certainly disable" UBWC (https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md, [doc], re-read 2026-09-24). Meta's Vulkan FFR is a per-bin density effect ([doc]). Whether the eye buffers rendered with FDM lose UBWC is not published. [verify on device] with Write Total, FFR off vs high.
- **ARM-C14** Compute writes vs UBWC (A2-C7). Qualcomm: compute shaders almost certainly disable UBWC ([doc]). Mesa marks a7xx_gen2 (Quest 3's 740v3) `supports_uav_ubwc` under Turnip ([community]). Assessment: Quest's Qualcomm driver behaviour is unverified; assume UBWC loss.
- **ARM-C15** FP16 rate on A6xx (A2-C8). Chips and Cheese's first A640 article found fp16 at fp32 rate; its 2024-05-06 correction shows double rate ([measured]). Resolved in favour of double rate, which matches Qualcomm's "twice the performance" ([doc]).
- **ARM-C16** RenderDoc Meta Fork draw-call metric count (A3-C4). The current table lists about 48 metrics; a search snippet cited 59 ([doc] vs snippet). Probably device- or version-dependent.
- **ARM-C17** Throttling model (A3-C6). The deprecated 2022 power page describes a thermal trip to power-save levels equivalent to (0,0) and says CPU load causes more thermal trouble than GPU load ([doc], stale). The 2026 thermal page describes staged budgeting, throttling, FrameSync and cool-down, and the Boost page names GPU level 5 as where throttling is most common ([doc]). Assessment: treat the 2022 page as stale.
- **ARM-C18** Perfetto GPU metrics workflow (A3-C7). The OS v27-era blog says GPU counters appear only while `ovrgpuprofiler -r` runs in the background ([doc], old). The 2026 MQDH Perfetto guide offers GPU Metrics as a capture option with no manual step ([doc]). Assessment: the workflow has likely changed; confirm the counters in a current trace.
- **ARM-C19** Are the VrApi `TA=`/`SP=` logcat fields stale for OpenXR apps? A1-046 (from the 2019 blog, [doc]) treated them as VrApi-only. The logcat-stats page (updated 2025-07-31, re-read 2026-09-24, [doc]) still documents them and ties `SP=` to `XR_KHR_android_thread_settings` (AS-001). Assessment: the fields are documented as current; whether a Unity OpenXR build emits the line needs `adb logcat -s VrApi`. [verify on device]
- **ARM-C20** Quest 3 vs Quest 2 GPU gain. Meta: "twice the GPU power" (https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/, [doc], re-read 2026-09-24). Qualcomm: "2.5x higher GPU performance" for XR2 Gen 2 vs Gen 1 (product brief, [doc], re-read 2026-09-24). Assessment: vendor claims measured under different conditions (Qualcomm's likely at unrestricted phone-class clocks); no independent like-for-like Quest measurement exists. Use Meta's 2x for planning and measure at matched levels (A2-004).
- **ARM-C21** Quest 3 default eye-buffer size. A3-010 could not find the Quest 3 default and used the 2064x2208 panel resolution; A3-009 attributes 1680x1760 to Quest 3S via `debug.oculus.textureWidth/Height`. Meta's Quest 3 blog and tiled-GPU page both give 1680x1760 as the Quest 3 default ([doc], both re-read 2026-09-24; A1-020, A2-020). Assessment: 1680x1760 is the Quest 3 default; A3-010's panel-resolution figures are an upper bound, not the default workload. Round-2 update: the sysprops page lists 1680x1760 for both Quest 3 and Quest 3S (ARM-GF2-004, [doc]), so A3-010's statement that it listed only the Quest 3S default was wrong and has been corrected. Resolved.
- **ARM-C22** DRAM energy per GB/s. Arm's 2014 abstract-machine blog gives about 120 mW per GB/s (A3-002, [doc], archived). A search snippet attributed about 100 mW per GB/s to Arm's current best-practices guide (A3-002 notes; A2 gaps), which could not be read. Assessment: both are Mali-phone-era rules of thumb; use them only as an order of magnitude (about 0.1 W per GB/s). No Quest figure exists.
- **ARM-C23** Does multiview share the binning pass between views? Qualcomm says multiview saves CPU work only and has "no GPU impact" (A2-062, [doc]). Meta describes a multiview bin as holding both eyes' views (A3-005, A2-013, [doc]). Assessment: not contradictory for GMEM (both views share a bin), but Qualcomm's statement implies no vertex-side saving. The binning-pass cost with and without multiview on Quest is unmeasured.
- **ARM-C24** Memory clock value in Meta's logcat docs. The dossier previously said `Mem=2092MHz` was the only published memory-clock value. The round-1 re-read of the logcat-stats page (2026-09-24, [doc]) shows 2092 MHz in the full example line and `Mem=1804MHz` in the field-definition table (ARM-GF1-004). Neither is tied to a headset. The derived 2092 MHz x 2 x 8 B ≈ 33.5 GB/s peak (A1-008) is therefore only one of two example values and must not be used as a Quest 2 specification. [verify on device]
- **ARM-C25** Quest 3 battery capacity. UploadVR's teardown report (2023-10-13, citing iFixit) gives 19.44 Wh (https://www.uploadvr.com/quest-3-teardown-battery/, [community]); the forum measurement header also uses 19.44 Wh (ARM-GF2-002). UploadVR's Quest 3S leak article (2024-09-14) lists Quest 3 as 18.9 Wh in its comparison (https://www.uploadvr.com/quest-3s-images-leak-reveal-battery-size-no-headphone-jack/, [community]). Assessment: use 19.44 Wh (teardown-based); the 3% gap does not change the ~9.7 W estimate materially (18.9 Wh / 2 h ≈ 9.5 W, derived).

## Gaps and known unknowns

Gaps are grouped by the topic note that raised them. Round-1 additions and status changes come first.

### Round-2 gap-fill pass (2026-09-24)

- **Connect 2023 "State of Compute: Maximizing Performance on Meta Quest" (Bedekar, Meta; Holztrattner, Qualcomm).** Unresolvable by automated retrieval. The YouTube upload (https://www.youtube.com/watch?v=M6RKMXQbtWk) lists caption tracks, but every timedtext request returned an empty body; YouTube's player API returned LOGIN_REQUIRED; the developers.facebook.com video page (2023-10-05) and Meta's Connect 2023 on-demand blog (2023-10-06) carry only the abstract; third-party transcript sites are JS-rendered or return 403. No press summary of the talk's core or thread statements was found. A human can watch the video and note any app-core count or thread-placement statement. The question it might answer (app cores on Quest 3/3S) stays open; measure it with the `Cpus_allowed_list` / cpuset / Perfetto recipe in the A1 list below.
- **Meta forum "Quest 3 Power Usage Tests and Approximate Battery Life".** Resolved: read via the Wayback Machine (snapshot 2025-01-08); its results table is ARM-GF2-002.
- **Quest 3S battery capacity.** Resolved at [community] level: 16.74 Wh from a leaked regulatory label (ARM-GF2-001). No teardown or Meta figure confirms it; iFixit's Quest 3S chip-ID guide (A1-023) does not state the battery.
- **Quest 3 vs Quest 3S sustained thermal headroom.** Still unpublished. Both run the same level table; the 3S has a different chassis and optics, and a lower implied average draw (ARM-GF2-001). Measure with the A3-093 recipe on both devices using the same build and scene.
- **Resolved in round 2:** the Quest 3 default eye texture is listed on the sysprops page (1680x1760, same as 3S; ARM-GF2-004, ARM-C21).

### Round-1 coverage pass (2026-09-24)

- **Thermal envelope (TDP or sustained SoC power) for Quest 2, Quest 3 and Quest 3S.** Unresolvable from public sources: Meta, Qualcomm and the teardowns publish no SoC or GPU power rating. The only figures are Meta's generic "3-6 W" mobile-GPU class (ARM-GF1-006) and a battery-derived whole-headset average of about 9.7 W on Quest 3 (ARM-GF1-002). How to measure: at pinned CPU/GPU levels, log BAT C / POW C (OVR Metrics) over 20-30 minutes for a fixed scene, and record the time to the first level drop or PLS change (A3-093 recipe). Compare Quest 3 and Quest 3S, because the chassis and cooling differ.
- **XR2 Gen 1 and Gen 2 configured cache sizes.** Unresolvable from public sources after a targeted search: Arm gives only the ranges (A1-064, A1-065), Qualcomm gives only the 8 MB system cache (LLC) on Gen 2, and Geekbench's Quest pages list topology and clocks but no cache sizes. Measure with the pointer-chase sweep in the A1 list below.
- **DRAM data rate on Quest 3/3S.** Still open (ARM-C2). The Micron LPDDR5X claim (ARM-GF1-005) adds a candidate but not a Quest measurement. Measure with a Burst STREAM-style copy/triad job at a pinned CPU level, and read `Mem=` / MEM F at the same time (ARM-C24).
- **Default job-worker count on Quest 3/3S.** Still only a community snippet (A1-055). Log `JobsUtility.JobWorkerMaximumCount`, `JobWorkerCount` and `SystemInfo.processorCount` at startup per device and Unity version.
- **Snapdragon Profiler on Quest 3/3S in 2026.** A fresh search (2026-09-24) found no Meta or Qualcomm statement of support or non-support. Keep the A3-067 working position and the A3-066 on-device test.
- **Resolved in round 1:** the Quest 3 default eye-buffer size is 1680x1760 (ARM-C21). The `Mem=` value in Meta's docs is not a single published figure (ARM-C24).

### SoC, CPU and threads (A1)

- **Which cores a VR app may use on Quest 3/3S; the exact set on Quest 2.** No Meta page states either. To measure, on each device:
  1. While the app runs, read `adb shell cat /proc/<pid>/status | grep Cpus_allowed_list` and the per-thread `/proc/<pid>/task/<tid>/status`.
  2. Read `adb shell cat /dev/cpuset/top-app/cpus`, and the other cpuset groups, if readable.
  3. Confirm placement from Perfetto's CPU Scheduling tracks.
- **Default `JobWorkerMaximumCount` and `SystemInfo.processorCount` per device and Unity version.** Only a community snippet reports 2 workers on Quest 3 (2022.3.15). To measure, log both values plus `JobWorkerCount` at startup on each device for 2021.3, 2022.3, 6000.0 and 6000.3+.
- **Whether Unity's OpenXR plugin, Meta's OpenXR plugin or OVRPlugin register UnityMain/UnityGfxDeviceW via XR_KHR_android_thread_settings, and with what scheduling result.** To measure, compare `adb shell ps -T -p <pid> -o TID,NAME,SCH,RTPRIO,PRI,NI,PSR` against a native OpenXR sample that registers its threads (A1-043). Also look for runtime logcat lines after session start.
- **Compositor core and scheduling on Quest 2/3 today.** Only VrApi-era descriptions exist (A1-010, A1-011, A1-048).
- **Configured cache sizes on XR2 Gen 1 and Gen 2.** Unknown for per-core L2, cluster L3 and system-cache sharing. Also unknown whether XR2 Gen 2 is one DSU cluster or two. To measure:
  1. Try `adb shell cat /sys/devices/system/cpu/cpu0/cache/index*/size`; the nodes are often absent on arm64 Android.
  2. Otherwise, run a pointer-chase latency sweep (working set from 16 KB to 64 MB) in a Burst job pinned to one app core, and read the L1, L2 and L3 steps.
- **DRAM data rate and achievable bandwidth on Quest 2 and Quest 3/3S.** No Meta figures. Qualcomm's "3.2 GHz" reading is an assumption. To measure, run a STREAM-style copy/triad Burst job at a pinned CPU level, and cross-check with sibling A3's bandwidth counters.
- **The exact feature set of the Burst ARMV8A_HALFFP target.** It is undocumented. Inspect the Burst Inspector output and diff the ARMV8A and ARMV8A_HALFFP code for `half` math.
- **Utilization metric behind the 83%/77% CPU thresholds.** Whether Meta's level governor uses worst-core or average utilization is undocumented. It matters for main-thread-bound apps.
- **How Quest 2 reaches CPU level 5 under SustainedHigh** without trading (ARM-C5), and the Quest 3/3S Boost ceiling (ARM-C4).
- **Graphics Jobs Split vs Legacy on Quest (Unity 6), and Graphics Jobs on Unity 2021.3.** No Meta or Unity measurements.
- **Independent GPU comparison of XR2 Gen 2 and Gen 1.** Only vendor claims exist (Meta 2x, Qualcomm 2.5x). This belongs to sibling A2/A3.
- **Connect 2023 talk "State of Compute: Maximizing Performance on Meta Quest"** (Neel Bedekar, Meta; Rodrigo Holztrattner, Qualcomm). The transcript could not be retrieved; YouTube captions returned nothing. It likely covers core and thread details. Video: https://developers.facebook.com/videos/2023/state-of-compute-maximizing-performance-on-meta-quest/. Round 2 retried and marked this unresolvable by automated retrieval (see the round-2 list above).
- **Meta community forums (communityforums.atmeta.com)** returned 403 to automated fetches, and the Wayback Machine was offline in round 1. Round 2 read two threads through the Wayback Machine (A1-055, ARM-GF2-002); other forum reports stay unverified.
- **XR2 Gen 2 hardware offload** (A1-024). It is unknown how much app-core time the offload of tracking and passthrough frees on Quest 3 compared with Quest 2.

### Adreno architecture and shader cost (A2)

- No official SP/ALU counts, FLOPS or per-clock throughput for the Adreno 650 or 740. Measure relative ALU throughput per A2-004.
- Exact GMEM of the Quest 3 740v3 is not published (see ARM-C9). Infer it from ovrgpuprofiler bin sizes at known formats.
- Vulkan subgroup size on the Quest driver is not published. Query VkPhysicalDeviceSubgroupProperties and subgroup-size-control on device.
- Transcendental and integer rates for the 650/740 are not measured; only proxies from the A640 and X1.
- Texture L1/L2 sizes for the 650/740 are not published; only proxies from the A640 and X1.
- LRZ block granularity, early-Z and Fast-Z rates for the 650/740 are not published beyond "up to 4x" and "2x".
- Instruction-count thresholds for A6x (Quest 2) are not published; A7x is 2000.
- The ALU:TEX balance ratio for A6x/A7x is not published; A5x is 16:1.
- The 740's subpassLoad parallelism for MSAA inputs (the 2x vs 4x rule) is unknown; Meta says to consult Qualcomm, and Qualcomm has not published it.
- Whether hardware multiview on Quest 2 shares the binning pass between views (Qualcomm says "no impact on the GPU"; Meta says bins are shared).
- Whether Unity's Vulkan backend on Quest emits combined image samplers (Qualcomm's 2-5% fill-rate note) and whether it sets MUTABLE_FORMAT on sRGB-capable RenderTextures (a UBWC risk). Needs a RenderDoc capture.
- No Quest 2 or Quest 3 MSAA cost table; the only measured table is from the original Quest (Adreno 540).
- The Adreno Offline Compiler version matching Quest's Meta-built driver, and whether its GPR/instruction stats match on-device stats.
- A Quest-specific DRAM energy per GB/s figure; Arm's ~100 mW/GB/s is from a Mali phone.
- UploadVR's "Quest 3 GPU may be twice as powerful" article was found but not read. No Meta-published per-clock Quest 2 vs Quest 3 ratio.

### Bandwidth, thermals and profilers (A3)

- **Full metric list for ovrgpuprofiler on Quest 3/3S.** It is unknown whether byte counters (Read Total, Write Total) exist in realtime `-r` mode or only in draw-call traces. How to measure: run `adb shell ovrgpuprofiler -m -v`, `-m -t` and `-x -m` on each device and OS build.
- **UBWC compression ratio and per-surface UBWC status on Quest.** No published number and no Meta tool to show it. How to measure: compare RenderDoc Write Total for a surface created with MUTABLE_FORMAT or LINEAR against an optimal-tiled one of the same content.
- **Whether FFR (FDM) eye buffers keep UBWC (ARM-C13).** How to measure: measure Write Total with FFR off and at high, normalised per stored pixel.
- **DRAM energy per byte for XR2 Gen 2 / LPDDR5.** No published number found. Only generic figures exist (Horowitz 2014; Arm 2014, ~120 mW per GB/s). How to measure: use the POW C/POW V CSV while sweeping a synthetic full-screen store pass count at fixed levels. This is noisy, and Meta discourages using these metrics for optimisation.
- **Peak DRAM bandwidth and memory type for Quest 3 and 3S.** Not published by Meta or Qualcomm; the community figures are uncited.
- **Whether the memory clock (Mem=, MEM F) scales with CPU/GPU level or thermal state.** How to measure: log both across PowerSavings and SustainedHigh runs and during a throttle event.
- **Long-session throttling measurements on Quest 2/3/3S.** No [measured] source found for minutes-to-first-level-drop or sustained levels. How to measure: follow the A3-093 recipe.
- **Fan behaviour on Quest 2/3/3S.** No Meta developer doc describes fan curves, and no documented metric exposes fan speed. No published number found. How to measure: only indirectly, by recording surface-temperature-proxy PLS transitions with and without the fan blocked, which is not recommended.
- **Battery drain versus CPU/GPU level.** No published curve; Meta says to optimise against levels. How to measure: use BAT C over fixed-level runs.
- **Snapdragon Profiler on Quest 3/3S in 2025-2026.** Only a Qualcomm forum thread title was found; there is no Meta or Qualcomm statement and no last-supported version. How to measure: follow the A3-066 test on device.
- **Perfetto GPU counter track names on Quest.** Not documented. How to measure: record with MQDH and list the tracks in ui.perfetto.dev.
- **Adreno 740 behaviour.** Unconfirmed for input-attachment multi-sample reads, the ASTC L1/L2 decompression point, and the MSAA 4x resolve cost. (The Quest 3 default eye-texture size, also listed here in round 1, is resolved: ARM-GF2-004.)
- **Quest Pro GMEM size and the VR Glasses GMEM size.** Not stated.

## Source list

Grouped by the topic note that cited each source; the gap-fill and spot-check sources from round 1 come first. Every source was accessed 2026-09-24.

### Round-2 gap-fill and spot-check sources

- https://www.uploadvr.com/quest-3s-images-leak-reveal-battery-size-no-headphone-jack/ : UploadVR, Quest 3S leaked photos reveal battery size, 2024-09-14 (ARM-GF2-001, ARM-C25)
- https://web.archive.org/web/20250108162626/https://communityforums.atmeta.com/t5/Talk-VR/Quest-3-Power-Usage-Tests-and-Approximate-Battery-Life/td-p/1094433 : Meta Community Forums, "Quest 3 Power Usage Tests and Approximate Battery Life", 2023-10-18 (edited 2024-04-07), archived copy (ARM-GF2-002) [measured]
- https://web.archive.org/web/20260214200619/https://communityforums.atmeta.com/discussions/dev-quest/unity-quest-3-multithreaded-performance/1132006 : Meta Community Forums, "Unity Quest 3 Multithreaded performance", archived copy (A1-055) [community]
- https://developers.meta.com/horizon/blog/optimizing-for-success-meta-quest-3-gdc/ : Meta blog, Optimizing for success on Meta Quest 3 (GDC), 2024-03-21 (ARM-GF2-003)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ : Meta, System properties, eye-texture defaults (ARM-GF2-004; A3-009/A3-010 spot-check)
- https://www.youtube.com/watch?v=M6RKMXQbtWk : Meta, "State of Compute: Maximizing Performance on Meta Quest", Connect 2023 video (captions not retrievable)
- https://developers.facebook.com/videos/2023/state-of-compute-maximizing-performance-on-meta-quest/ : Meta for Developers video page, 2023-10-05 (abstract only)
- https://developers.meta.com/horizon/blog/watch-meta-connect-2023-sessions-on-demand-quest-3-developers/ : Meta blog, Connect 2023 sessions on demand, 2023-10-06 (abstract only)
- https://developers.facebook.com/m/meta-connect-developer-sessions/maximizing-performance-on-meta-quest/ : Meta, Connect 2024 "State of compute 2024" session page, 2024-10-17 (abstract only)
- Re-read for spot-checks: https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ , https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ , https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ , https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ , https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ , https://developers.meta.com/horizon/essentials/thermal/ , https://developers.meta.com/horizon/essentials/compare-devices/ , https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ , https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ , https://www.uploadvr.com/quest-3-teardown-battery/ , https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/spec_sheets.md , https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md , https://docs.unity3d.com/Packages/com.unity.burst@1.8/changelog/CHANGELOG.html

### Round-1 gap-fill and spot-check sources

- https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ : Meta, Tiled GPU explainer (ARM-GF1-006; re-read for the A2-020 spot-check)
- https://www.uploadvr.com/quest-3-teardown-battery/ : UploadVR, "Quest 3 Teardown Reveals It's Mostly Battery Inside", 2023-10-13 (ARM-GF1-002)
- https://www.ifixit.com/News/84572/meta-quest-3-teardown-and-the-future-of-vr-repairability-en : iFixit, Meta Quest 3 teardown news post, 2023-10-13 (context for ARM-GF1-002; gives no battery figure)
- https://www.tweaktown.com/news/93872/microns-low-power-memory-optimized-for-snapdragon-xr2-gen-2-platform-vr-and-mixed-reality/index.html : TweakTown, Micron LPDDR5X and UFS 3.1 for XR2 Gen 2, 2023-10-19 (ARM-GF1-005)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/spec_sheets.md and https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md : Qualcomm Adreno guide 80-78185-2, markdown sources re-read for the A2-063, A2-070, A2-083 and A3-014 spot-checks
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerMaximumCount.html : Unity, JobWorkerMaximumCount (re-read for the A1-054 spot-check)

### SoC, CPU and threads (A1)

Meta:
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (updated Sep 2, 2026)
- https://developers.meta.com/horizon/essentials/cpu-gpu-levels/ (updated Sep 11, 2026)
- https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (updated Sep 2, 2026; native twin https://developers.meta.com/horizon/documentation/native/android/po-quest-boost/)
- https://developers.meta.com/horizon/essentials/performance-hardware/ (updated Sep 15, 2026)
- https://developers.meta.com/horizon/essentials/thermal/ (updated Sep 15, 2026)
- https://developers.meta.com/horizon/resources/compare-devices/ (updated Sep 18, 2026)
- https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ (updated Nov 11, 2024)
- https://developers.meta.com/horizon/documentation/unity/unity-perf/ (updated Oct 30, 2024)
- https://developers.meta.com/horizon/documentation/unity/unity-sample-performance-settings/ (updated Aug 11, 2026)
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/
- https://developers.meta.com/horizon/documentation/unity/ts-simpleperf/
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/
- https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/ (Sep 29, 2022; deprecated VrApi)
- https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ (Oct 11, 2023)
- https://developers.meta.com/horizon/blog/boost-app-performance-525-mhz-gpu-frequency-meta-quest-2/ (Dec 21, 2022)
- https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ (Mar 3, 2026)
- https://developers.meta.com/horizon/blog/down-the-rabbit-hole-w-oculus-quest-the-hardware-software/ (May 2, 2019)
- https://developers.meta.com/horizon/blog/ovr-metrics-tool-vrapi-what-do-these-metrics-mean/ (Oct 25, 2019)
- https://developers.meta.com/horizon/blog/optimizing-for-success-meta-quest-3-gdc/ (Mar 21, 2024; context only)
- https://raw.githubusercontent.com/meta-quest/Meta-OpenXR-SDK/main/Samples/SampleXrFramework/Src/XrApp.cpp (v85, Feb 12, 2026)
- https://github.com/oculus-samples/Unity-PerformanceSettings

Qualcomm:
- https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf
- https://docs.qualcomm.com/bundle/publicresource/87-73622-1_REV_A_Snapdragon_XR2__Gen_2_Platform_Product_Brief.pdf

Arm:
- A78C TRM 102226 r0p2: https://documentation-service.arm.com/documentation/102226/0002/Functional-description/Introduction/About-the-core (plus the L1, L2 and Supported-standards topics)
- A78 SWOG 102160 r1p2: https://documentation-service.arm.com/documentation/102160/latest
- A77 SWOG swog011050 rev c: https://documentation-service.arm.com/documentation/swog011050/latest
- A55 SWOG epm128372: https://documentation-service.arm.com/documentation/epm128372/latest
- A77 TRM 101111 and A55 TRM 100442, via the same service (existence only)
- https://www.arm.com/products/silicon-ip-cpu/cortex-a/cortex-a78c
- https://www.arm.com/products/silicon-ip-cpu/cortex-a/cortex-a77

Khronos:
- https://registry.khronos.org/OpenXR/specs/1.1/html/xrspec.html#XR_KHR_android_thread_settings

Unity:
- https://docs.unity3d.com/6000.0/Documentation/Manual/android-thread-configuration.html (same page under /2021.3/, /2022.3/, /6000.6/)
- https://docs.unity3d.com/6000.0/Documentation/Manual/android-custom-activity-command-line.html
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerCount.html
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerMaximumCount.html
- https://docs.unity3d.com/6000.0/Documentation/Manual/job-system-overview.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html
- https://docs.unity3d.com/2021.3/Documentation/Manual/class-PlayerSettingsAndroid.html
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/GraphicsJobMode.html (and the /2022.3/ version)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/changelog/CHANGELOG.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-projects.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-aot-settings.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstcompile.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/api/Unity.Burst.Intrinsics.Arm.Neon.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/changelog/CHANGELOG.html
- https://discussions.unity.com/t/android-thread-configuration-render/1731103 (community)

Measurements and community:
- Geekbench 6: https://browser.geekbench.com/v6/cpu/19091540 (Quest 2), https://browser.geekbench.com/v6/cpu/19064415 and https://browser.geekbench.com/v6/cpu/19157033 (Quest 3), https://browser.geekbench.com/v6/cpu/18989681 (Quest 3S)
- Geekbench 5 (Quest 3, Android 12): https://browser.geekbench.com/v5/cpu/21825265
- Geekbench 6 searches: https://browser.geekbench.com/search?k=v6_cpu&q=Oculus+Quest+3 and https://browser.geekbench.com/search?k=v6_cpu&q=Oculus+Quest+3S
- Geekbench 7 Quest 3S result (850/2955): https://browser.geekbench.com/v7/cpu/181337
- https://www.ifixit.com/Guide/Meta+Quest+3+Chip+ID/165932
- https://www.ifixit.com/Guide/Meta+Quest+3S+Chip+ID/178132
- https://www.uploadvr.com/snapdragon-xr2-gen-2/ (Sep 27, 2023)
- https://en.wikipedia.org/wiki/List_of_Qualcomm_Snapdragon_systems_on_chips
- https://en.wikipedia.org/wiki/Quest_2
- https://en.wikipedia.org/wiki/Meta_Quest_3
- https://en.wikipedia.org/wiki/Meta_Quest_3S

### Adreno architecture and shader cost (A2)

Qualcomm:
1. Qualcomm, Adreno GPU on Mobile: Best Practices (published 2026-09-22). https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
2. Qualcomm, Adreno GPU overview (2026-09-22). https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html [doc]
3. Qualcomm, Adreno spec sheets (2026-09-22). https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html [doc]

Meta:

4. Meta, Advanced GPU pipelines. https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]
5. Meta, ovrgpuprofiler (updated 2026-09-09). https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
6. Meta, CPU and GPU levels (updated 2026-09-02). https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]
7. Meta, GPU-impaired algorithms (2024-09-20). https://developers.meta.com/horizon/documentation/unity/gpu-impaired-algorithms/ [doc]
8. Meta, GPU-improved algorithms (2024-08-16). https://developers.meta.com/horizon/documentation/unity/gpu-improved-algorithms/ [doc]
9. Meta, Tiled GPU (2024-12-04). https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ [doc]
10. Meta, Mobile MSAA analysis (original Quest). https://developers.meta.com/horizon/documentation/native/android/mobile-msaa-analysis/ [measured]

Unity:

11. Unity Manual, Use 16-bit precision in shaders (6000.3 and 2022.3). https://docs.unity3d.com/6000.3/Documentation/Manual/SL-Use16BitPrecisionInShaders.html ; https://docs.unity3d.com/2022.3/Documentation/Manual/SL-Use16BitPrecisionInShaders.html [doc]

Mesa and Linux kernel:

12. Mesa freedreno device table. https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py [community]
13. Mesa freedreno docs. https://docs.mesa3d.org/drivers/freedreno.html [community]
14. Mesa freedreno LRZ doc. https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html [community]
15. Mesa freedreno FDM doc. https://docs.mesa3d.org/drivers/freedreno/fdm.html [community]
16. Linux kernel a6xx_catalog.c (Android common kernel mirror). https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/drivers/gpu/drm/msm/adreno/a6xx_catalog.c [community]

Chips and Cheese:

17. Chips and Cheese, Inside the Snapdragon 855's iGPU (2024-05-01). https://chipsandcheese.com/p/inside-the-snapdragon-855s-igpu [measured]
18. Chips and Cheese, Correction on Qualcomm iGPUs (2024-05-06). https://chipsandcheese.com/p/correction-on-qualcomm-igpus [measured]
19. Chips and Cheese, The Snapdragon X Elite's Adreno iGPU (2024-07-04). https://chipsandcheese.com/p/the-snapdragon-x-elites-adreno-igpu [measured]

Other:

20. UploadVR, Quest 3 GPU clock boost (2024-10-31). https://www.uploadvr.com/meta-quest-3-gpu-clock-speed-performance-boost/ [community]
21. Khronos Vulkan-Samples (Arm-authored performance samples): render passes, MSAA, subpasses. https://docs.vulkan.org/samples/latest/samples/performance/render_passes/README.html ; https://docs.vulkan.org/samples/latest/samples/performance/msaa/README.html ; https://docs.vulkan.org/samples/latest/samples/performance/subpasses/README.html [doc / measured on Mali]
22. gpuinfo.org OpenGL ES reports: Quest 2 / Adreno 650 (id 6387), Quest / Adreno 740 (id 7475) and Quest 3 / Adreno 740 (id 8023). https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=7475 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 [community]

Not used as evidence (unreliable or unread):
- Wikipedia "Adreno" table
- Notebookcheck Adreno 650/740 pages
- Beyond3D thread "Hardware details about Adreno 740"
- azhirnov cpu-gpu-arch Adreno_Guide.md, which hit GitHub rate limits
- kernel.org and elixir.bootlin, which served bot challenges that were not bypassed

### Bandwidth, thermals and profilers (A3)

- Meta, CPU and GPU levels (updated 2026-09-02): https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (native mirror: https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/)
- Meta, Boosting CPU and GPU levels (2026-09-02): https://developers.meta.com/horizon/documentation/unity/po-quest-boost/
- Meta, Thermal management (2026-09-15): https://developers.meta.com/horizon/essentials/thermal/
- Meta, Performance and hardware (2026-09-15): https://developers.meta.com/horizon/essentials/performance-hardware/
- Meta, Battery saver mode (2026-04-08): https://developers.meta.com/horizon/essentials/battery-saver-mode ; Unity page (2025-07-29): https://developers.meta.com/horizon/documentation/unity/os-battery-saver-mode/
- Meta, Logcat stats definitions (2025-07-31): https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/
- Meta, OVR Metrics Tool (2026-06-21): https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ ; OVR Metrics stats (2024-12-15): https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/
- Meta, ovrgpuprofiler (2026-09-09): https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/
- Meta, Advanced GPU pipelines (undated): https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/
- Meta, RenderDoc Meta Fork (2026-09-09): https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ ; draw call metrics: https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ ; render stage trace: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ ; settings (2024-12-15): https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ ; AI tools (2026-09-09): https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-ai-tools/
- Meta, Perfetto guide (2026-09-03): https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ ; MQDH logs and metrics (2026-04-08): https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/
- Meta blog, Perfetto on Quest (OS v27 era): https://developers.meta.com/horizon/blog/how-to-run-a-perfetto-trace-on-oculus-quest-or-quest-2/
- Meta blog, Improving GPU profiling on Oculus Quest (2020-06-19): https://developers.meta.com/horizon/blog/improving-gpu-profiling-on-oculus-quest/
- Meta blog, 525 MHz GPU on Quest 2 (OS v47 era): https://developers.meta.com/horizon/blog/boost-app-performance-525-mhz-gpu-frequency-meta-quest-2/
- Meta, Developer tools index (2024-12-17): https://developers.meta.com/horizon/resources/developer-tools/
- Meta, Unreal testing and performance analysis (2026-04-14): https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android/
- Meta, System properties: https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ ; Per-frame GPU profiling: https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/
- Meta, Deprecated power management page (2022-09-29): https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/
- Meta, Optimize performance for Meta VR Glasses (2026-09-19): https://developers.meta.com/horizon/documentation/unity/optimize-performance/ ; Mobile performance basics (2024-12-09): https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/
- Meta, Dynamic resolution (2026-08-06): https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/
- Meta, Compare devices (2026-09-18): https://developers.meta.com/horizon/essentials/compare-devices/
- Qualcomm Adreno GPU guide 80-78185-2, markdown topics (SDP chapter last published 2026-09-22): https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md , .../overview.md , .../spec_sheets.md , .../sdp.md
- Android AGI memory efficiency (2026-05-19): https://developer.android.com/agi/sys-trace/memory-efficiency
- Horowitz, Computing's Energy Problem, ISSCC 2014: https://gwern.net/doc/cs/hardware/2014-horowitz-2.pdf
- Arm, The Mali GPU: An Abstract Machine, Part 2 (2014-02-20), archived: https://web.archive.org/web/20191215124148/https://community.arm.com/developer/tools-software/graphics/b/blog/posts/the-mali-gpu-an-abstract-machine-part-2---tile-based-rendering
- UploadVR, Quest 3 GPU clock increase (2024-10-31): https://www.uploadvr.com/meta-quest-3-gpu-clock-speed-performance-boost/
- Meta community forum thread 837235 (2020-12-02): https://communityforums.atmeta.com/discussions/dev-quest/is-any-way-to-make-a-vulkan-gpu-capture-on-quest-/837235
- Qualcomm QDN archive threads 66963, 67580, 68286: https://developer.qualcomm.com/forum/qdn-forums/software/snapdragon-profiler/66963 (and /67580, /68286; read via web.archive.org)
- Qualcomm support forum thread (title only): https://mysupport.qualcomm.com/supportforums/s/question/0D5dK000009EniESAS/snapdragon-profiler-not-able-to-capture-anything-on-meta-quest-33s
- Wikipedia, Meta Quest 3 and Meta Quest 3S (uncited specs): https://en.wikipedia.org/wiki/Meta_Quest_3 , https://en.wikipedia.org/wiki/Meta_Quest_3S

### Synthesis gap-fill (AS-001)

- https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ : Meta, Logcat stats definitions (updated 2025-07-31)
