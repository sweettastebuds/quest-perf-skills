---
name: quest-budgets-tiers
description: "Per-device budgets and quality tiers for Quest 2 vs Quest 3/3S in Unity: frame-time budget per refresh rate, how many draw calls, triangles, pixels and texture memory each headset affords, app memory limits (PSS, lmkd low-memory kills), runtime headset detection (SystemHeadset), adaptive quality ladders and store VRC performance rules. Use when sizing content per headset, porting Quest 3 content to Quest 2, or when the app is killed for memory. To reduce draw calls, see unity-perf:unity-draw-calls-batching."
---

# Quest budgets and device tiers

Sizes content per headset within platform limits. Goals: **Throughput** (budgets that
fit the frame) and **Consistency** (no Low Memory Kills, adaptive quality that drops
resolution instead of frames, store floors met for a whole session).

Scope: Quest 2 (XR2 Gen 1, Adreno 650), Quest 3/3S (XR2 Gen 2, Adreno 740), Unity 2021.3
to 6.6, URP 12-17, Vulkan and GLES unless noted; Quest Pro only where Meta groups it with Quest 2.

## When to use / when not

Use when:
- "How many draw calls / triangles / MB of textures can I afford on Quest 2 vs 3?"
- Sizing a content tier, or porting a Quest 3 build down to Quest 2.
- The app dies after a while with no stack trace, store crash analytics show "Low
  Memory Kill", or you need the PSS limit per headset.
- Detecting the headset at runtime, building Quest 2 / Quest 3 / Quest 3S / MR tiers,
  or an adaptive quality ladder.
- Checking a build against VRC.Quest.Performance.1-4, or reading store Performance
  Analytics.

Do not use; go to the owner instead:
- Bottleneck unknown ("low FPS", "is it CPU or GPU?"), or the 70% CPU / 80% GPU /
  hitches under 3% headroom rule: `quest-perf:quest-triage`.
- Actually cutting draw calls or SetPass calls: `unity-perf:unity-draw-calls-batching`.
- Texture compression, mip streaming, mesh formats, loading hitches:
  `unity-perf:unity-memory-assets`.
- CPU/GPU level-to-clock tables, "design to L4, L5 is opportunistic", throttling,
  Battery Saver: `quest-perf:quest-levels-thermal`.
- Dynamic resolution setup, FFR, eye-buffer scale mechanics: `quest-perf:quest-resolution-foveation`.
- Passthrough / Depth API / scene costs beyond the level caps listed here: `quest-perf:quest-mr-costs`.
- Silicon questions (core types, Adreno 650 vs 740, GMEM, LPDDR type):
  `arm-mobile-hw-perf:xr2-gen1-vs-gen2`.
- Stale-frame semantics and refresh-rate choice: `quest-perf:quest-frame-pacing`.
- Running OVR Metrics, the CSV analyzer and ADB capture scripts: `quest-perf:quest-profiling-toolkit`.

## Diagnose first

Establish which budget is actually binding before resizing content.

1. **Frame budget vs measured app time.** Record an OVR Metrics CSV with the HUD off
   (the HUD adds its own layer and GPU draw, Q1-002):
   ```sh
   adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV
   ```
   Compare `app_gpu_time_microseconds` and the CPU time columns with the budget for
   the refresh rate in use (Key numbers). Or read the per-second line live:
   `adb logcat -s VrApi` (`App=`, `TW=`, `Stale=`, `Free=`). Record `cpu_level` /
   `gpu_level` with every capture; captures at different levels are not comparable.
2. **Draw-call budget.** Capture render-thread time first (Unity Profiler or Perfetto,
   `quest-perf:quest-profiling-toolkit`); a draw budget binds only when the render
   thread is the long pole (QUEST-GF2-C5).
3. **Fill rate.** No budget exists (Q2-036). Capture a render-stage trace in RenderDoc
   Meta Fork; the Tile Timeline gives per-surface duration, render mode and bin count.
   Turn on ovrgpuprofiler support in OVR Metrics for `avg_fill_percentage` (100 = each
   eye pixel touched once; system overlays add to it) (Q1-007).
4. **Memory.** Measure PSS at peak scene load with background apps running, not on a
   clean boot (Q2-042):
   ```sh
   adb shell dumpsys meminfo <your.package.name>
   adb shell gpumeminfo -p $(adb shell pidof <your.package.name>)
   adb shell "logcat -d | grep -i lowmemorykiller"
   ```
   The CSV columns `app_pss_MB`, `app_gpu_physical_MB`, `app_gpu_virtual_MB`,
   `app_gpu_allocated_percentage` give the trend over a session (Q1-005, Q1-095).
   `Free=` in the VrApi line is a leak indicator only, not headroom (Q2-043).
5. **Headset identity.** Log `OVRPlugin.GetSystemHeadsetType()` and the reported
   refresh-rate list once at startup, and inspect the merged AndroidManifest for
   `com.oculus.supportedDevices`. A missing entry makes a newer headset report an
   older model (compatibility mode, Q2-081).

## Key numbers

Full per-device table: read [references/device-tiers.md](references/device-tiers.md)
when building a tier table, porting between headsets, or checking eye-buffer, RAM,
PSS, SystemHeadset or refresh-rate facts per device.

**Frame budgets** (Q2-009, os-missed-frames, unity-set-disp-freq) `all Quest`

| Refresh | Budget | Half rate with AppSW |
|---|---|---|
| 72 Hz | 13.9 ms | 27.8 ms |
| 90 Hz | 11.1 ms | 22.2 ms |
| 120 Hz | 8.3 ms | 16.7 ms |
| 207 / 240 Hz | 4.8 / 4.2 ms | n/a (Quest 3 only) |

80, 96 and 100 Hz: no Meta row; 1000/Hz gives 12.5, 10.4 and 10.0 ms. The app never
owns the whole budget: no net-headroom percentage after compositor and OS work is
published (Q2-030); the logcat example shows compositor GPU `TW=` at 1.25 ms. Headroom
rules: `quest-perf:quest-triage` (70/80%), `quest-perf:quest-levels-thermal` (levels).

**Quest 3/3S vs Quest 2 capability** `Quest 2` `Quest 3/3S` (ratio table in device-tiers.md)
- Meta launch blog (Oct 2023): about 2x GPU, about 33% more CPU, more than 30% more
  memory (Q2-006, A1-020) [doc]. Conflict ARM-C20 / U3-003: Qualcomm's brief and Meta's
  May 2026 comparison page say 2.5x GPU; no independent measurement. Plan with 2x,
  measure at matched levels [verify on device].
- The Quest 3/3S default eye buffer 1680x1760 is about 30% more pixels than Quest 2's
  1440x1584, which spends part of the uplift (Q2-019, ARM-GF2-004).
- MR modifier: passthrough on Quest 3/3S removes CPU L4 and GPU L3-L4 (max CPU L3
  1.65 GHz, GPU L2 456 MHz), about 14% CPU and 17% GPU less than VR-only (Q2-006,
  Q2-038). Depth API costs more GPU with no published number. Detail:
  `quest-perf:quest-mr-costs`.

**Draw calls and triangles: no single budget; none is a limit** (QUEST-GF2-C5, Q1-C3,
X-C4) `Quest 2` `Quest 3/3S`. Five Meta sources give five draw figures; the full
per-source table (with the stale pre-2023 figures) is in
[references/device-tiers.md](references/device-tiers.md#draw-call-and-triangle-figures-by-source).
- Planning start (unity-perf page, Q2-033 / Q2-034): Quest 2/Pro 80-200 / 200-300 /
  400-600 draws (busy / medium / light) and 750k-1M triangles; Quest 3/3S 200-300 /
  400-600 / 700-1000 draws and 1.3M-1.8M triangles.
- The May 2026 comparison page (U3-003) is lower: Quest 2 under 100 draws / under 750K
  triangles, Quest 3 under 200 / under 1.5M. GDC 2026 says about 500, "not a hard and
  fast rule" (QUEST-GF2-005). Unresolved: start from the lower bound and measure.
- Cost is driven by state changes, render-thread load and API choice; no page says
  whether a multiview draw counts once or twice (X-C4). On a tiler a large triangle
  runs vertex work in every bin it covers (Q2-034 notes).

**Fill rate and texture memory: no published budget** (Q2-036, Q2-037) `all Quest`
- Shaded pixels at render scale 1.0, before MSAA and overdraw (arithmetic from Meta's
  defaults): Quest 3/3S 1680x1760x2 per frame, about 532 Mpx/s at 90 Hz; Quest 2
  1440x1584x2 per frame (about 411 Mpx/s at 90 Hz, same arithmetic). This is a
  workload size, not a device limit.
- Texture memory: the only ceiling is the app PSS limit below. Eye buffers and render
  textures count against the same PSS. A dynamic-resolution maximum of 1.6 on Quest
  3/3S allocates 2688x2816 per eye at startup (Q2-024 / Q2-090).

**Memory** (PSS: Q2-041 to 043, memory-ram / po-memory-ram; RAM: Q2-001 compare-devices [doc], Q2-003 Wikipedia [community]) `Quest 2` `Quest 3/3S`

| Headset | RAM | App PSS limit | GDC 2026 working target (QUEST-GF1-003) |
|---|---|---|---|
| Quest 2 | 6 GB | 4.4 GiB | about 3.5 GB |
| Quest 3 / 3S | 8 GB | 5.75 GiB | about 5 GB, "stay below it" (talk title covers 3/3S; recap names Quest 3 only) |

lmkd kills only under memory pressure, so exceeding the limit may not crash on a
clean test device and then shows up as "Low Memory Kill" in store crash analytics from
users with background activity (Q2-042). A shared Quest 2/3 build must fit 4.4 GiB
unless assets are tiered.

**Render-scale floor** (Q1-087, Q2-026, Q3-003, QUEST-GF2-005) `all Quest`
- VRC.Quest.Performance.4 (recommended, not required): render scale at least 85% for
  most of the experience (CSV `render_scale`; non-consecutive dips allowed); GDC 2026
  also gives 0.85. OVRManager's default minimum is 0.7 (Quest 2 range 0.7-1.3, Quest
  3/3S 0.7-1.6, Q2-024 / Q2-090), below that floor.

**Quest 3S** (Q2-087 to 093, ARM-GF2-004) `Quest 3S`
- Same clock table, level rules, 5.75 GiB PSS and draw/triangle ranges as Quest 3, and
  the same 1680x1760 default eye buffer on a 1832x1920 panel: identical default GPU
  cost. 72-120 Hz only.
- Memory bandwidth unpublished. Conflict ARM-C2 (A3-099): Wikipedia lists Quest 3S
  LPDDR4X 2600 MT/s (42 GB/s) vs Quest 3 LPDDR5 4200 MT/s (68 GB/s) [community], but
  4200 MT/s on a 64-bit bus is 33.6 GB/s (derived), and iFixit identifies an LPDDR5 part
  in the 3S (A1-023) [community]. Assessment: LPDDR5-class on both, data rate
  unpublished. Compare `Mem=` in `adb logcat -s VrApi` on both and A/B a bandwidth-bound
  scene at fixed levels [verify on device].
- ovrgpuprofiler lists 492 MHz for 3S vs 690 MHz for Quest 3 (QX-C6 / ARM-C3; 492
  equals the Quest 3/3S GPU L3 clock, 690 equals Meta VR Glasses L5, likely copy
  errors). Use the shared level table: budget at GPU L4 (545 MHz); L5 (599 MHz) is
  opportunistic (Q2-029).

**Store floors** (Q1-084 to 088, QUEST-GF1-009) `store apps` - details in
[references/vrc-performance.md](references/vrc-performance.md); read it when preparing
a store submission, answering a VRC question, or reading Performance Analytics.
- Perf.1 certification floor: 60 fps (lowered from 72 on 2024-08-07), or half the
  refresh rate for AppSW portions (36 fps at 72 Hz); the Perf.1 test flags extended
  periods under 30 fps with AppSW. Quality target: 72 fps with no stale frames.
- Conflict Q1-C1 / Q2-C3 / QUEST-GF1-C3: po-perf-opt-mobile (Dec 2024, A3-097),
  unity-perf (Oct 2024), Common VRC Failures (May 2026) and the GDC 2026 recap still say
  72 fps. The VRC page is authoritative for certification; those pages are stale.
- Perf.2 (45-minute thermal test) retired 2024-10-16. Perf.3: head-tracked graphics
  within 4 s of launch or a loading indicator. Perf.4: the 85% render-scale floor.

## Fixes, ranked by payoff ÷ effort

### 1. Fix the manifest before any tiering logic
`Consistency` `all Quest` `Unity 2021.3+`
- Set OpenXR Target Devices (Project Settings > XR Plug-in Management > OpenXR >
  Meta Quest Support) to include Quest 2, Quest 3, Quest 3S (3S target added in Unity
  OpenXR 1.13.0), then open the merged AndroidManifest and confirm
  `com.oculus.supportedDevices` = `quest2|questpro|quest3|quest3s` (Q2-083, Q2-084).
- Oculus XR Plugin path (Unity 2021.3/2022.3 with Core SDK below v74, Q4-050): Project
  Settings > XR Plug-in Management > Oculus > Target Devices. Either way the merged
  manifest is the ground truth.
- Effect: none on frame time; it makes `GetSystemHeadsetType()` and the refresh-rate
  list truthful. A missing `quest3s` makes 3S report an older model and limits rates to
  those both models support (Q2-015, Q2-081).
- Side effects: none. Compatibility mode never throttles clocks (Q2-084), so a
  mis-tiered Quest 3 simply wastes GPU headroom. The refresh-rate doc's claim that Unity
  auto-adds `quest|quest2` is stale (Q2-C12); check every build.

### 2. Keep peak PSS under the per-headset limit, with margin
`Consistency` `Quest 2` `Quest 3/3S`
- Budget peak PSS at 4.4 GiB (Quest 2) / 5.75 GiB (Quest 3/3S); aim for the GDC
  targets (about 3.5 GB / 5 GB) for fragmentation and other processes (QUEST-GF2-012).
  Measure at the heaviest scene with background apps running (Diagnose step 4).
- Tier assets by headset (texture max size or mip limit per tier, render-texture
  sizes, dynamic-resolution maximum). Asset-side methods: `unity-perf:unity-memory-assets`.
- Effect: removes Low Memory Kills (a session-ending consistency failure); no average
  frame-time change unless texture bandwidth also drops.
- Quality cost: lower texture resolution on the Quest 2 tier.

### 3. Detect the headset and pick a tier once at startup
`Throughput` `Consistency` `Quest 2` `Quest 3/3S` `Meta XR Core SDK` `Unity 2021.3+`
- SystemHeadset values: Quest 2 = 9, Quest Pro = 10, Quest 3 = 11, Quest 3S = 12,
  Meta VR Glasses = 13, placeholders 14-20, Link variants from 0x1000 (Q2-080, Core
  SDK 207 source). Map unknown future values to the highest tier and check
  capabilities, not the lowest.
- Meta: do not key features on `android.os.Build.MODEL` or any single value; no API
  reports whether compatibility mode is active. Combine the enum, the reported
  refresh-rate list and measured frame time (Q2-082).
- Tier layout (Q2-085, researcher synthesis, not Meta guidance): A = Quest 3,
  A-display = Quest 3S, B = Quest 2 (and Pro), MR modifier = Quest 3/3S with
  passthrough (CPU L3 / GPU L2); detail in device-tiers.md.
- Effect: none on its own; it lets each tier fit its budget (lower average frame time,
  fewer stale frames on the lower tier). Choosing once avoids mid-session hitches.
- Quality cost: the Quest 2 tier gets reduced assets and settings. Mis-tiering a newer
  headset low wastes headroom (Q2-084).

```csharp
// Unity 2021.3+ with Meta XR Core SDK (OVRPlugin). Untested on device.
using UnityEngine;

public enum QuestTier { B_Quest2, A_Quest3S, A_Quest3, A_Unknown }

public static class QuestTiering
{
    public static QuestTier Detect()
    {
        // Compare ints so older SDKs without Meta_Quest_3S still compile.
        int headset = (int)OVRPlugin.GetSystemHeadsetType();
        QuestTier tier;
        switch (headset)
        {
            case 9:  tier = QuestTier.B_Quest2;  break; // Oculus_Quest_2
            case 10: tier = QuestTier.B_Quest2;  break; // Meta_Quest_Pro: Quest 2 tables
            case 11: tier = QuestTier.A_Quest3;  break; // Meta_Quest_3
            case 12: tier = QuestTier.A_Quest3S; break; // Meta_Quest_3S
            default:
                // 8 = original Quest (or a headset missing from supportedDevices),
                // 13+ = newer device, >= 0x1000 = Link. Capability-check, do not assume lowest.
                tier = headset > 12 && headset < 0x1000 ? QuestTier.A_Unknown : QuestTier.B_Quest2;
                break;
        }
#pragma warning disable 0618 // the list API is marked deprecated (Q2-011)
        float[] rates = OVRPlugin.systemDisplayFrequenciesAvailable;
#pragma warning restore 0618
        Debug.Log($"[QuestTiering] SystemHeadset={headset} tier={tier} rates=" +
                  (rates != null ? string.Join(",", rates) : "none"));
        return tier;
    }
}
```

Apply the tier by selecting a Quality Settings level (each with its own URP asset)
at the first loading screen: `QualitySettings.SetQualityLevel(index, true);`. The URP
asset per tier carries MSAA, render scale, shadow settings; which values to use there
is owned by `unity-perf:unity-urp-settings`.

### 4. Enable dynamic resolution with a 0.85 floor as the first adaptive rung
`Throughput` `Consistency` `Quest 2` `Quest 3/3S` `Meta XR Core SDK`
- OVRCameraRig > OVR Manager > Enable Dynamic Resolution, then set
  `quest2MinDynamicResolutionScale` / `quest3MinDynamicResolutionScale` to 0.85 in the
  Inspector (Q3-050, QUEST-GF2-005). Minimum Unity versions and URP issues:
  `quest-perf:quest-resolution-foveation`.
- Effect: unlocks GPU L5 (opportunistic; requires dynamic resolution) and makes thermal
  throttling lower resolution instead of dropping frames (Q2-029, Q2-050, Q3-049).
  Mainly a variance fix.
- Quality cost: at the 0.85 minimum, clarity drops visibly on Quest 3/3S, whose scale
  1.0 is already below panel resolution (3S panel match about 1.09, Q2-088). The
  maximum above 1.0 sets the eye-texture allocation at startup (memory, Fix 2). A
  minimum below 0.85 makes you responsible for the Perf.4 expectation.

### 5. Size each tier against the budgets, render thread first
`Throughput` `Quest 2` `Quest 3/3S`
- Start each tier at Meta's per-device ranges (Q2-033 draw calls, both triangle
  tables) and at the frame budget of the shipping refresh rate, then move the numbers
  only from captures: render-thread ms for draws, GPU ms per surface for pixels.
- Porting Quest 3 content to Quest 2: the Quest 2 tier has roughly half the GPU (Meta's
  2x; Qualcomm and the comparison page say 2.5x), about 30% fewer default eye-buffer
  pixels (which offsets part of that), about 1.35 GiB less PSS, and draw/triangle
  ranges roughly half of Quest 3's. No published per-content scaling factor exists:
  run the Quest 3 build on Quest 2 at the target refresh rate, then cut where the
  capture says (draws, surface time, PSS) [verify on device]. Silicon background:
  `arm-mobile-hw-perf:xr2-gen1-vs-gen2`.
- A Quest 2-tier build on Quest 3 leaves GPU headroom unused unless dynamic resolution
  or adaptive quality spends it (Q2-084).
- Effect: mainly average frame time; variance only indirectly (thermal-step headroom).
- Quality cost: content cuts on the lower tier (draws, triangles, surface cost).

### 6. Add a frame-time-driven quality ladder for the remaining rungs
`Consistency` `Quest 2` `Quest 3/3S` `Unity 2021.3+`
- Meta's recommendation: scale LOD bias, view distance, MSAA sample count, shadows and
  post-processing from the measured CPU/GPU level, and turn spare GPU time into pixels
  with dynamic resolution (Q2-086). Quest has no documented in-app API to read the
  current level (the OVRPlugin level/clock PerfMetrics are deprecated since 1.68.0), so
  missed frames are the practical proxy.
- Conflict to know: Q2-086's notes suggest `OVRPlugin.GetPerfMetricsFloat` timings as the
  signal, but the `XR_META_performance_metrics` spec says apps should not change
  behaviour based on counter reads (Q1-103). The reference ladder uses frame delta only.
- Unity 6.6+ alternative: Adaptive Performance gained OpenXR support in 6.6 (U1-073);
  its interaction with Meta dynamic resolution is undocumented [verify on device].
- Implementation: read [references/adaptive-quality-ladder.md](references/adaptive-quality-ladder.md)
  when writing the ladder (paste-ready `QuestQualityLadder`: missed-frame ratio per
  window, hysteresis, AppSW handling; all thresholds are unpublished tunables).
- Effect: lower frame-time variance under load spikes and thermal steps; average frame
  time drops only while on a lower rung. Quality cost: visible LOD and shadow changes.
  Rungs switched mid-play share one URP asset; switch URP assets or reallocate (MSAA,
  render-texture size) only at loading screens or fades (Perf.1-exempt) [verify on device].

### 7. Gate refresh-rate and extended-rate choices per headset
`Consistency` `Quest 2` `Quest 3/3S` `Meta XR Core SDK`
- Pick the rate per tier from the reported list, not from the model: 3S tops out at
  120 Hz; only Quest 3 accepts 121-207 Hz (Q2-013, Q2-089). Rate choice itself is owned
  by `quest-perf:quest-frame-pacing`.
- Effect: prevents requesting unsupported rates; a failed request falls back to a lower
  rate and budgets are sized for the wrong rate. No average-frame-time change.
- Quality cost: none.

## Verify

- **Frame budget:** on each tier, p95 of `app_gpu_time_microseconds` (per-second CSV
  rows) under the refresh budget minus `TW` at the shipping layer count, and
  `stale_frame_count` near zero, over a 20-30 min unplugged session at the shipping
  refresh rate. Run the CSV through `quest-perf:quest-profiling-toolkit`'s
  `ovr_metrics_csv.py` for p50/p95/p99, stale frames per minute and first-vs-last-5-min
  drift.
- **Memory:** peak `app_pss_MB` below 4.4 GiB (Quest 2) / 5.75 GiB (Quest 3/3S), ideally
  under the GDC targets, with background apps running; zero `lowmemorykiller` lines
  naming your process across the whole session; no upward PSS trend (leak) over 30 min.
- **Tiering:** the startup log shows SystemHeadset 9 / 11 / 12 on each lab headset (3S
  reports 12, not 11).
- **Render scale:** `render_scale` column at or above 0.85 for most rows across the
  content length or 45 minutes (Perf.4 method).
- **Store:** no extended periods under 60 fps (under 30 with AppSW) on the OVR Metrics
  FPS graph over the content length or 45 min (Perf.1). After release, track Performance
  Analytics Max Stale Frames per 60 s and CPU/GPU utilization percentiles per device.
- **Ladder:** in a stress scene it steps down within one window, stale frames fall, and
  it steps up only after the clean period, without oscillating.

## Pitfalls and myths

- **"Meta says 72 fps minimum."** Stale for certification; the VRC floor is 60 fps
  since 2024-08-07. 72 fps with no stale frames remains the quality target (Q1-C1).
- **"Quest 3 is 2.5x Quest 2, so double everything."** Meta's own blog says 2x, part of
  it is consumed by a 30% larger eye buffer, and MR removes the top levels (ARM-C20,
  Q2-019, Q2-038).
- **"The draw-call limit is 100 / 200 / 300 / 500."** Five Meta sources, none a limit;
  measure render-thread time first (QUEST-GF2-C5).
- **"50,000 triangles per eye" / "texture memory is nearly free".** Pre-2023 Meta
  pages; stale (Q2-035). Old Quest 1 draw-cost multipliers: relative ordering only.
- **"Quest 3S has a lower-resolution panel, so it is cheaper to render."** It renders
  the same 1680x1760 default eye buffer as Quest 3 (Q2-088).
- **"No crash in QA, so memory is fine."** lmkd kills under pressure; test with
  background apps (Q2-042). `Free=` is not headroom (Q2-043).
- **Tiering on `Build.MODEL` or a single enum** misfires in compatibility mode (Q2-082).
- **"Compatibility mode / Target Devices throttles newer headsets."** It does not (Q2-084).
- **"Perf.2 thermal test will catch thermal decay."** Retired 2024-10-16; the 45-minute
  Perf.1 run still catches decay below 60 fps, nothing more (Q1-085, QX-C7). Soak
  protocol: `quest-perf:quest-levels-thermal`.
- **Budgeting against GPU L5.** L5 is opportunistic and withheld under Battery Saver or
  low thermal headroom; budget against L4, and GPU L2 for passthrough apps on Quest
  3/3S (Q4-006).
- **Meta VR Glasses rules on shared pages** (token-bucket boost, no trading, no
  dual-core) do not apply to Quest (Q2-008).
- **`GetAppPerfStats()` on OpenXR** returns empty values in SDK v85 (Q1-104); do not build
  adaptive quality on it.

## Sources

All accessed 2026-09-24. Pages under one prefix are grouped; each URL is prefix + path.
- Meta Unity docs [doc], prefix https://developers.meta.com/horizon/documentation/unity/ :
  os-missed-frames/, unity-set-disp-freq/, unity-perf/, optimize-performance/,
  po-memory-ram/, ts-logcat-stats/, ts-gpumeminfo/, ts-ovrmetricstool/,
  ts-systemproperties/, po-quest-boost/, dynamic-resolution-unity/,
  os-compatibility-mode/, unity-openxr-settings-quest/, unity-quest-runtime-optimizer/,
  unity-mobile-performance-intro/ (stale), po-draw-call-analysis/ (stale),
  po-perf-opt-mobile/ (stale 72 fps)
- Meta native docs [doc], prefix `developers.meta.com/horizon/documentation/native/android/` + ts-ovrstats/, os-render-scale/,
  os-cpu-gpu-levels/
- Meta store and resources pages [doc], prefix https://developers.meta.com/horizon/resources/ : vrc-quest-performance-1/,
  vrc-quest-performance-2/, vrc-quest-performance-3/, vrc-quest-performance-4/,
  publish-quest-req/, publish-performance-analytics/, device-optimization-comparison/,
  publish-common-vrc-failures/ (stale 72 fps)
- Meta essentials [doc]: https://developers.meta.com/horizon/essentials/compare-devices/ ;
  https://developers.meta.com/horizon/essentials/memory-ram/
- Meta blog [doc]: https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ ;
  https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/
- https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ [doc] (GDC 2026 talk)
- https://github.com/meta-quest/agentic-tools [doc] (Meta agent heuristics)
- https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf [doc]
- https://raw.githubusercontent.com/darktable-mirror/com.meta.xr.sdk.core/main/Scripts/OVRPlugin.cs [doc] (SDK source mirror; also OVRManager.cs in the same folder)
- https://github.com/elliot170802/Practicas_AR_TSIC/blob/HEAD/VR_2026/Library/PackageCache/com.meta.xr.sdk.core@85.0.0/Scripts/OVRPlugin.cs [doc] (SDK v85 source mirror)
- https://npm.developer.oculus.com/com.meta.xr.sdk.core [doc] (Core SDK minimum Unity per version)
- https://github.com/KhronosGroup/OpenXR-Docs/blob/main/specification/sources/chapters/extensions/meta/meta_performance_metrics.adoc [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc]
- iFixit chip IDs [community]: https://www.ifixit.com/Guide/Meta+Quest+3S+Chip+ID/178132 ;
  https://www.ifixit.com/Guide/Meta+Quest+3+Chip+ID/165932
- Wikipedia [community]: https://en.wikipedia.org/w/index.php?title=Meta_Quest_3&action=raw ;
  https://en.wikipedia.org/w/index.php?title=Meta_Quest_3S&action=raw ;
  https://en.wikipedia.org/wiki/Quest_2
