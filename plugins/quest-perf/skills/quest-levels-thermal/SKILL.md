---
name: quest-levels-thermal
description: "Quest CPU/GPU performance levels and thermal throttling in Unity apps: level-to-clock tables for Quest 2 and Quest 3/3S, suggestedCpuPerfLevel and OpenXR performance-settings hints, CPU Boost, Quest 2 dual-core mode, Quest 3/3S CPU/GPU level trading, GPU level 5, staged throttling, power level (PLS), Battery Saver and 20-30 minute session tests. Use for FPS drops after 10 minutes, levels that keep changing, thermal throttling warnings, or picking a ProcessorPerformanceLevel. For watts and battery drain, see arm-mobile-hw-perf:xr2-bandwidth-power."
---

# Quest CPU/GPU levels and thermal behaviour

Goal: **Consistency** first (no thermal decay across a 20-30 min session, no level
oscillation), **Throughput** second (the right level ceiling for the workload).
Applies to Quest 2 (XR2 Gen 1) and Quest 3/3S (XR2 Gen 2), every Unity version from
2021.3 to 6.6, both GLES and Vulkan: levels are an OS policy, not an engine or API
feature. Quest Pro gets one line (A3-073): CPU/GPU L4 disappear with passthrough,
eye/face/body tracking or eye-tracked foveation.

## When to use / when not

Use when:
- FPS, stale frames or p99 are fine at start and degrade after about 10 minutes.
- OVR Metrics `CPU L` / `GPU L` keep changing, or a requested level never shows up.
- The user sees a thermal or overheat dialog, or `PLS`/`POW L` leaves 0.
- Choosing a `ProcessorPerformanceLevel`, Boost windows, dual-core mode (Quest 2) or
  Processor Favor / level trading (Quest 3/3S).
- Planning or reading a long-session (20-30+ min) soak.

Do not use; go to the sibling instead:
- First CPU- vs GPU-bound split, the 70% CPU / 80% GPU headroom rule: `quest-perf:quest-triage`.
- Stale frames or judder with good average FPS, FrameSync, refresh-rate choice, the thermal 72 Hz refresh drop itself, staggering periodic work: `quest-perf:quest-frame-pacing`.
- Dynamic-resolution setup, render scale, FFR: `quest-perf:quest-resolution-foveation`.
- Passthrough / Depth API / MRUK budgets (the level caps are stated here as rules only): `quest-perf:quest-mr-costs`.
- Watts, battery drain, DRAM energy, the unpublished thermal envelope: `arm-mobile-hw-perf:xr2-bandwidth-power`.
- Main-thread cycle budgets per level, thread placement, job-worker counts: `arm-mobile-hw-perf:xr2-cpu-threads-neon`.
- How to install and run OVR Metrics, Perfetto, the helper scripts: `quest-perf:quest-profiling-toolkit`.
- Per-tier quality settings and headset detection: `quest-perf:quest-budgets-tiers`.

## Diagnose first

Confirm that the degradation is level/thermal driven, not content, before changing anything.

1. **Read the granted level and power state every second** (Quest 2/3/3S, all stacks; Q2-056, A3-083):
   ```sh
   adb logcat -s VrApi,XrPerformanceManager
   ```
   The log tag carrying `clockStateLogLevel` output (step 2) is not documented (Q1-036): if no FORCED/REJECTED lines appear under this filter, capture unfiltered `adb logcat` and grep for them [verify on device].
   - `CPU4/GPU=a/b,cccc/dddMHz`: the digit after `CPU` is the measured core, not a level; `a/b` are the CPU/GPU levels, then the clocks (Q1-025).
   - `PLS=` power level: 0 NORMAL, 1 SAVE, 2 DANGER (DANGER shows the overheat dialog). `LP=1` is Battery Saver. `SF=` is the dynamic-resolution multiplier. Ignore `Temp=`; Meta says use PLS on Quest (Q2-061, A3-082).
   - `XrPerformanceManager ... SetClockLevels: Apply pending clock request change: 4,3 -> 3,3` marks every level change (Q1-035).
2. **See why a level was granted, forced or refused** (A3-084, Q1-036):
   ```sh
   adb shell setprop debug.oculus.clockStateLogLevel 1   # Min/Max/Final + reason per change
   adb shell setprop debug.oculus.clockStateLogLevel 2   # also REJECTED / ignored requests
   adb shell setprop debug.oculus.clockStateLogLevel 0   # off (a reboot also resets)
   ```
   FORCED "Enabling the dynamic resolution boost" = GPU L5 granted; REJECTED "Clamp to max allowed hardware level." = your request exceeded what is available (passthrough cap, missing dynamic resolution, Battery Saver).
3. **Log a session CSV** with OVR Metrics (A3-049): `adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV`, then pull `/sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/`. Columns that matter here (Q1-005): `cpu_level`, `gpu_level`, `cpu_frequency_MHz`, `gpu_frequency_MHz`, `power_level_state`, `display_refresh_rate`, `stale_frame_count`, `app_gpu_time_microseconds`, `gpu_utilization_percentage`, `cpu_utilization_percentage`. Run the toolkit's `ovr_metrics_csv.py` (owned by `quest-perf:quest-profiling-toolkit`, `py -3.12 ../quest-profiling-toolkit/scripts/ovr_metrics_csv.py <csv> --hz <shipping Hz> --window-min 5`, path relative to this skill's folder; omit `--hz` to use the CSV's `display_refresh_rate`) for the first-vs-last-5-minute drift report.
4. **Confirm build-time manifest options reached the runtime** (Q1-038): at startup logcat prints `CreateClient: Value of isCPUSingleThreadedBoost is 1` (dual-core) and `CreateClient: Value of tradeCpuForGpu is <n>` (trading).

Read the result:

| Pattern in the capture | Meaning | Go to |
|---|---|---|
| `power_level_state` 0 -> 1/2, `*_frequency_MHz` falls in a steady scene, stale frames rise after it | Thermal throttling (stage 2 of 4) | Fixes 1-3, 6 |
| `display_refresh_rate` 90/120 -> 72, then app FPS halves | Thermal refresh step (Q2-014) | Fix 5; `quest-perf:quest-frame-pacing` |
| `LP=1`, 72 Hz, no GPU L5, no Boost | Battery Saver (user setting) | Fix 5 |
| Level flips N <-> N+1 every few seconds, frame-time variance at matching times, `PLS=0` | Governor hysteresis band (GPU ~81-87%, CPU ~77-83%) | Fixes 1, 3 |
| Requested level never appears, clockStateLog shows REJECTED | Availability rule (passthrough, no dynamic resolution, Battery Saver, casting) | Key numbers; [level-tables.md](references/level-tables.md) |
| Persistently high `Early` frames | Levels higher than needed: heat and battery for nothing (Q2-054) | Fix 3 |

For repeatable content A/B timing (not soaks), pin levels: `adb shell setprop debug.oculus.cpuLevel 4` / `debug.oculus.gpuLevel 4` (Q1-079, Q2-039). Pinned levels still throttle when hot, so watch PLS (A3-051). Unpin (reboot) before any thermal soak (Q1-077, Q1-079). The toolkit's `quest_adb.py` wraps these as `pin-levels`, `clocklog`, `thermal-sim`, `csv-on`, `pull-csv` and `props-snapshot`; run `py -3.12 ../quest-profiling-toolkit/scripts/quest_adb.py <subcommand> --help` for flags. `--dry-run` is a top-level flag that goes before the subcommand and prints the adb commands without running them (`py -3.12 ../quest-profiling-toolkit/scripts/quest_adb.py --dry-run pin-levels ...`).

## Key numbers

All [doc] from Meta's levels page (https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/, updated 2026-09-02) unless marked. The full per-level table, availability rows and conflicts are in [references/level-tables.md](references/level-tables.md); read it when you need a clock for a level other than L4, the availability rule for a specific feature combination, or the conflict details.

| Fact | Value | Applies to | Source |
|---|---|---|---|
| Default level (SustainedHigh) | CPU 4-4, GPU 3-5 | all Quest | Q2-045, A1-028 |
| L4 clocks | Quest 2: CPU 1.48 GHz / GPU 525 MHz. Quest 3/3S: CPU 1.92 GHz / GPU 545 MHz | `Quest 2` `Quest 3/3S` | Q2-046/047, A1-005 |
| GPU L5 | Quest 2 587 MHz, Quest 3/3S 599 MHz; opportunistic. Quest 2: needs dynamic resolution. Quest 3/3S: availability table also allows trading +1, Boost page says dynamic resolution on every model (conflict, Q4-C1) | `Quest 2` `Quest 3/3S` | Q2-029, Q2-048, Q2-049, Q2-050, A1-034 |
| Stale tables | Quest 2 GPU L4 = 490 MHz is pre-Dec-2022; now 525 MHz (+7%) | `Quest 2` | A1-007, A3-087 |
| Governor hysteresis | CPU up ≥83%, down ≤77%. GPU up ≥87%, down ≤81% | Quest 2/Pro/3/3S | A1-037, A3-070 |
| Utilisation that risks scheduling problems | `GPU%` above 0.9 (90%) | all Quest | Q2-030, A3-083 |
| Design target | Steady state at CPU L4 / GPU L4; "Target GPU level 4 as your maximum GPU budget" | all Quest | Q2-029 / A1-034 (Quest, GPU); Q2-028 (VR Glasses page, Quest 3 parity) |
| Boost | CPU L4 -> L8: +64% Quest 2 (2.42 GHz), +23% Quest 3/3S (2.36 GHz); max 45 s in a row; refused under throttling or Battery Saver | `Quest 2` `Quest 3/3S` | Q2-053, A1-030 |
| Boost runtime share | 20% of runtime **and** "not active for 80%" on the same page: conflict ARM-C6 / Q2-C7, 20% most likely [verify on device] | all Quest | ARM-C6 |
| Boost duration (OpenXR guidance) | under 30 s | `com.unity.xr.openxr` ≥ 1.11 | Q2-055, QX-C8 |
| Dual-core mode | SustainedHigh CPU 6-6 = 2.15 GHz on two cores | `Quest 2` OpenXR only | Q2-051, A1-031 |
| Level trading | -1: CPU L5 2.05 GHz (+7%, derived). +1: GPU L5 599 MHz (+10%, derived) | `Quest 3/3S` OpenXR only | A1-032 (scope); A1-005 (clocks) |
| Passthrough caps | CPU max L3 (1.65 GHz), GPU max L2 (456 MHz); GPU L4 -> L2 is -16% (derived) | `Quest 3/3S` | Q2-038, A1-018 |
| PLS / POW L | 0 NORMAL, 1 SAVE, 2 DANGER | all Quest | A3-081 |
| Battery Saver | 40% brightness, FFR 3, 72 Hz, no GPU L5, no Boost, `LP=1` | all Quest | Q2-062, A3-092 |
| OS drift | An OS update (v49) gave +7% GPU at L4 with no rebuild (the Quest 2 490 -> 525 MHz change); re-check tables after every OS update on any Quest | `Quest 2` | Q2-057, A1-007 |
| Minutes to first throttle | **No published number.** "Thermal cliff at minute ten" is guidance, not a measurement. Measure with [references/long-session-protocol.md](references/long-session-protocol.md) | all Quest | Q2-059, Q2-060, A3-079 |
| Quest 3 vs 3S sustained headroom | **No published number.** Same level table; different chassis. Measure both with the same build | `Quest 3/3S` | arm dossier gaps |
| Cool-down between soaks | ≥20 min at about 21 °C; run ≥10 min, trace after minute ten | Snapdragon generic ([doc], Qualcomm) | A3-095 |
| Store gating | Perf.2 (thermal) retired 2024-10-16; Perf.1 tests 45 min with a 60 fps floor, so decay above 60 fps is not gated | all Quest | QX-C7 |

Conflicts to surface, not resolve (details in the reference file): Quest 3/3S peak GPU clock 599 (levels table) vs 690 (ovrgpuprofiler page) vs 640 MHz (UploadVR, [community]) (ARM-C3); Quest 3/3S Boost level labelled 8 (Boost page, clock table) vs 6 (availability table, essentials page) (ARM-C4, QUEST-GF2-C1); trading scope, Quest 3/3S only vs a levels-page row that lists Quest 2 (ARM-C5); Boost 20% vs 80% (ARM-C6); default level SustainedHigh (Unity/native pages) vs CPU SustainedLow (Unreal page) (Q2-C2). In every case, read `cpu_frequency_MHz` / `gpu_frequency_MHz` on device instead of trusting a level number.

## Fixes, ranked by payoff ÷ effort

### 1. Size the steady state to CPU L4 / GPU L4, not to L5 or Boost

- **Change:** profile at pinned L4 (`debug.oculus.cpuLevel 4`, `debug.oculus.gpuLevel 4`) and cut content until the target rate holds there with `gpu_utilization_percentage` clear of the 81-87% (0.81-0.87) hysteresis band: below 81% (0.81) and never above 90% (0.9) (interpretation of the A1-037/A3-070 thresholds; no published target). The percentage target itself is `quest-perf:quest-triage`'s rule. On Quest 3/3S MR, the same rule applies at CPU L3 (Q2-038) / GPU L2 (Q2-038, Q4-006).
- **Effect:** removes the thermal cliff at its source; the OS sustains L4 "under worst-case thermal and battery conditions" (Q2-028; stated on a page written for Meta VR Glasses; the Quest-specific statement is the Boost page's 'Target GPU level 4 as your maximum GPU budget', Q2-029 / A1-034). Lowers variance more than average frame time. Keeping utilisation out of the band stops N <-> N+1 flips that FrameSync then has to absorb (Q2-046 notes).
- **Cost:** content or resolution cuts, owned by the relevant skills.
- **Tags:** `Quest 2` `Quest 3/3S` `all Unity` `GLES` `Vulkan`; **Consistency**, Throughput.

### 2. Turn on dynamic resolution so GPU L5 is a bonus and throttling costs pixels, not frames

- **Change:** OVRManager > Enable Dynamic Resolution (off by default), or `OVRManager.instance.enableDynamicResolution = true;` (Q4-006). Minimum versions (from the Meta XR SDK's `OVRManager.cs`, not the dynamic-resolution page): OpenXR loader needs Unity 2021.3.45f1 / 2022.3.49f1 / 6000.0.25f1; Oculus loader on Vulkan needs Oculus XR 3.3.0+ (or OpenXR 1.12.1+) (Q2-025). Setup, URP known issues and snapping: `quest-perf:quest-resolution-foveation`.
- **Effect:** without it, GPU L5 is never granted on Quest 2 (Q2-048). On Quest 3/3S the availability table also allows L5 with trading +1 (Q2-049), while the Boost page says L5 needs dynamic resolution on every model (A1-034). Conflict; see Q4-C1 in [level-tables.md](references/level-tables.md). With it, a thermal drop from L5 to L4 lowers render scale instead of dropping frames (Q2-050, A3-086). Mainly cuts stale-frame bursts late in the session.
- **Cost:** resolution softens while hot. Eye textures are allocated at the maximum scale, so memory follows the maximum (A3-086). Disable it while profiling (Q3-051).
- **Tags:** `Quest 2` `Quest 3/3S` `Unity 2021.3.45f1+ / 2022.3.49f1+ / 6000.0.25f1+ (OpenXR loader)` `Oculus XR 3.3.0+ (Oculus loader, Vulkan)` `GLES` `Vulkan`; **Consistency**, Throughput.

### 3. Request the lowest level that holds frame rate; drop it in light scenes

- **Change:** menus, lobbies, pause, static loading screens: `OVRManager.suggestedCpuPerfLevel = OVRManager.ProcessorPerformanceLevel.SustainedLow;` (or `PowerSavings`), and back to `SustainedHigh` for gameplay. See the component below.
- **Effect:** banks thermal headroom for later (Q2-054, A3-080). Does not change gameplay frame time.
- **Cost:** during gameplay, SustainedLow lets the CPU range move 2-4, so a load hovering near 80% CPU oscillates; SustainedHigh is fixed at CPU 4-4 and cannot (A1-037). Keep SustainedHigh wherever frame-time consistency matters.
- **Tags:** `Quest 2` `Quest 3/3S` `all Unity (2021.3-6.x)` `Meta XR Core SDK` `GLES` `Vulkan`; **Consistency** (thermal).

### 4. Boost only for bounded bursts (loads, transitions, room/scene setup)

- **Change:** set `ProcessorPerformanceLevel.Boost` on the CPU domain, then revert to `SustainedHigh` within 30 s (satisfies Meta's 45 s and OpenXR's under-30 s guidance, QX-C8). Verify with the `CPU L` jump or `cpu_frequency_MHz` near 2420 (Quest 2) / 2361 (Quest 3) MHz (QUEST-GF2-C1).
- **Effect:** shorter CPU-bound load hitches: about +64% CPU clock on Quest 2, +23% on Quest 3/3S. No steady-state gain.
- **Cost:** heat and battery; refused while throttling or in Battery Saver, where it acts as SustainedHigh (Q2-053), so it cannot rescue a hot device (A3-089). Behaviour when passthrough has already removed CPU L4 is undocumented [verify on device].
- **Tags:** `Quest 2` `Quest 3/3S` `all Unity (2021.3-6.x)` `Meta XR Core SDK` or `com.unity.xr.openxr ≥ 1.11` `GLES` `Vulkan`; Throughput (load time), **Consistency** (shorter hitch).

### 5. React to thermal and Battery Saver state at runtime

- **Change:** subscribe to `OVRManager.DisplayRefreshRateChanged` (the only practical Battery Saver signal, Q2-062) and, on OpenXR, `XrPerformanceSettingsFeature.OnXrPerformanceChangeNotification` (Q2-055). Step a quality tier down on a drop to 72 Hz or a Warning/Impaired notification. There is no Unity C# API for PLS (A3-081). An app that already ships at 72 Hz gets no refresh-change signal for Battery Saver or the first thermal step; there it must rely on the OpenXR notification or on logged clocks. Rehearse with the simulated thermal broadcast (Q2-014):
  ```sh
  adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SIMULATE_THERMAL --es subsystem refresh --ei seconds_throttled 10
  ```
- **Effect:** avoids the stage-4 forced cool-down and the half-rate step; keeps p99 flat as clocks fall.
- **Cost:** visible quality steps; tier contents are `quest-perf:quest-budgets-tiers`. Unity 6.6 Adaptive Performance for OpenXR (Basic provider, `Unity ≥ 6000.6`) is an alternative; its interaction with Meta dynamic resolution is undocumented (U1-073).
- **Tags:** `Quest 2` `Quest 3/3S` `all Unity (2021.3-6.x)` `Meta XR Core SDK` or `com.unity.xr.openxr ≥ 1.11` `GLES` `Vulkan`; **Consistency**.

### 6. Spread periodic heavy work across frames

One line; owned by `quest-perf:quest-frame-pacing` and `unity-perf:unity-cpu-scripting`. Meta ties predictable per-frame cost to the lowest sustained heat (Q2-063, A3-080). Tags: `Quest 2` `Quest 3/3S` `all Unity (2021.3-6.x)`; **Consistency**.

### 7. Quest 3/3S: set Processor Favor (level trading) from long-session data

- **Change:** Unity: Processor Favor on OVRManager/OVRCameraRig, or the manifest entry (OpenXR backend only, build-time):
  ```xml
  <meta-data android:name="com.oculus.trade_cpu_for_gpu_amount" android:value="-1" />
  ```
  `-1` = +1 CPU / -1 GPU (CPU L5 2.05 GHz), `1` = +1 GPU / -1 CPU (GPU L5 599 MHz), `0` = none.
- **Effect:** Meta frames it as choosing which processor keeps its speed when throttling downclocks (ARM-GF1-003). Whether it changes steady-state levels when *not* throttling is not documented; A/B 20-30 min runs with and without it [verify on device]. GPU L5 is also reachable through dynamic resolution alone, so try Fix 2 before `+1`. Effect on average frame time vs variance: under throttle, keeps the favoured processor's frame time from rising (Consistency); outside throttle, unknown.
- **Cost:** the other processor loses a level. Useless for CPU in passthrough apps: CPU L5 needs L4, which passthrough removes (A1-033, Q4-004). UploadVR reports Favor GPU costs 16% of max CPU clock ([community], A3-088).
- **Tags:** `Quest 3/3S` `all Unity (2021.3-6.x)` `OpenXR backend`; Throughput, **Consistency** under throttle.

### 8. Quest 2: dual-core mode only for a single-thread-bound main thread

- **Change:** only if Perfetto shows UnityMain saturating one core with the other app cores under 50% (Q2-051, A1-057):
  ```xml
  <meta-data android:name="com.oculus.dualcorecpuset" android:value="true" />
  ```
- **Effect:** SustainedHigh becomes CPU L6 (2.15 GHz) on two cores. Lowers main-thread average frame time only when single-thread bound; no variance benefit documented.
- **Cost:** no visual quality cost. One app core is lost (A1-031), and with it one job-worker slot (inferred). Meta says three cores at L4 beat dual-core at L6 when the app is truly multithreaded; for the comparison, pin `adb shell setprop debug.oculus.cpuLevel 5` (dual-core off) against dual-core L6; how a shipping app reaches Quest 2 CPU L5 is undocumented (ARM-C5). Thread and worker details: `arm-mobile-hw-perf:xr2-cpu-threads-neon`.
- **Tags:** `Quest 2` `all Unity (2021.3-6.x)` `OpenXR backend`; Throughput (main thread).

### Paste-ready level policy component

Meta XR Core SDK path is the documented one (Q1-105/Q2-044). The OpenXR path compiles only when you add a Version Define in the asmdef (`com.unity.xr.openxr`, expression `1.11.0`, define `QLT_OPENXR_PERF`); on Horizon OS it is community-evidenced only (QUEST-GF1-010) [verify on device]. Add a second Version Define `com.meta.xr.sdk.core` -> `QLT_META_SDK` (any version). The asmdef must also reference `Oculus.VR` (Meta XR Core SDK runtime assembly, confirmed in the SDK's `Oculus.VR.asmdef`) and, for the OpenXR path, `Unity.XR.OpenXR`. Version Defines do not work from Assembly-CSharp. Enable the XR Performance Settings feature under Project Settings > XR Plug-in Management > OpenXR (Android). Untested in this repo; APIs checked against SDK source and Unity OpenXR 1.19 docs.

```csharp
using System;
using System.Collections;
using UnityEngine;
#if QLT_OPENXR_PERF
using UnityEngine.XR.OpenXR.Features.Extensions.PerformanceSettings;
#endif

// Quest level policy: SustainedHigh in gameplay, lower in light scenes,
// bounded Boost bursts, and a callback when thermal/battery state degrades.
public sealed class QuestLevelPolicy : MonoBehaviour
{
    public const float MaxBoostSeconds = 25f;  // under OpenXR's 30 s and Meta's 45 s
    public event Action<string> Degraded;       // hook your quality-tier step here

    Coroutine _boost;

    void OnEnable()
    {
#if QLT_META_SDK
        OVRManager.DisplayRefreshRateChanged += OnRefreshChanged;
#endif
#if QLT_OPENXR_PERF
        XrPerformanceSettingsFeature.OnXrPerformanceChangeNotification += OnXrPerf;
#endif
    }

    void OnDisable()
    {
#if QLT_META_SDK
        OVRManager.DisplayRefreshRateChanged -= OnRefreshChanged;
#endif
#if QLT_OPENXR_PERF
        XrPerformanceSettingsFeature.OnXrPerformanceChangeNotification -= OnXrPerf;
#endif
        // Disabling/destroying stops the coroutine; never leave the CPU hint at Boost.
        if (_boost != null) { StopCoroutine(_boost); _boost = null; SetGameplay(); }
    }

    public void SetGameplay()   { CancelBoost(); SetCpu(light: false); }
    public void SetLightScene() { CancelBoost(); SetCpu(light: true); }

    void CancelBoost() { if (_boost != null) { StopCoroutine(_boost); _boost = null; } }

    public void BoostFor(float seconds)
    {
        if (_boost != null) StopCoroutine(_boost);
        _boost = StartCoroutine(BoostRoutine(Mathf.Min(seconds, MaxBoostSeconds)));
    }

    IEnumerator BoostRoutine(float seconds)
    {
#if QLT_META_SDK
        OVRManager.suggestedCpuPerfLevel = OVRManager.ProcessorPerformanceLevel.Boost;
#elif QLT_OPENXR_PERF
        XrPerformanceSettingsFeature.SetPerformanceLevelHint(PerformanceDomain.Cpu, PerformanceLevelHint.Boost);
#endif
        yield return new WaitForSecondsRealtime(seconds);
        _boost = null;
        SetCpu(light: false);
    }

    static void SetCpu(bool light)
    {
#if QLT_META_SDK
        OVRManager.suggestedCpuPerfLevel = light
            ? OVRManager.ProcessorPerformanceLevel.SustainedLow
            : OVRManager.ProcessorPerformanceLevel.SustainedHigh;
#elif QLT_OPENXR_PERF
        XrPerformanceSettingsFeature.SetPerformanceLevelHint(PerformanceDomain.Cpu,
            light ? PerformanceLevelHint.SustainedLow : PerformanceLevelHint.SustainedHigh);
#endif
    }

#if QLT_META_SDK
    void OnRefreshChanged(float from, float to)
    {
        // Thermal step 1 or Battery Saver both land on 72 Hz (Q2-014, Q2-062).
        if (to < from && Mathf.Approximately(to, 72f))
            Degraded?.Invoke($"refresh {from}->{to} Hz (thermal or Battery Saver)");
    }
#endif

#if QLT_OPENXR_PERF
    void OnXrPerf(PerformanceChangeNotification n)
    {
        if (n.toLevel != PerformanceNotificationLevel.Normal)
            Degraded?.Invoke($"{n.domain}/{n.subDomain} -> {n.toLevel}");
    }
#endif
}
```

Usage: call `BoostFor(10f)` before a scene load, `SetLightScene()` on entering a menu, `SetGameplay()` on leaving it. Log every `Degraded` message into the OVR Metrics CSV (`AppendCsvDebugString`, owned by `quest-perf:quest-profiling-toolkit`) so a thermal step is never mistaken for a code regression (U5-094).

## Verify

Run the long-session recipe in [references/long-session-protocol.md](references/long-session-protocol.md); read it before any soak, for the exact setup, commands and the report to fill in. Criteria (no Meta pass numbers exist; these are A/B comparisons):

- **Session length:** 30 min minimum at the shipping refresh rate, unplugged, battery above 50%, unpinned levels, dynamic resolution as shipped (Q2-060, A3-093). Repeat on Quest 2 and on both Quest 3 and 3S, VR and MR modes separately.
- **Metrics that should move after a fix:** minute of first `power_level_state` change later or never; `gpu_frequency_MHz` / `cpu_frequency_MHz` in the last 5 min equal to the first 5 min; stale frames per minute and max stale in any 60 s window no higher in the last 5 min than the first 5; `display_refresh_rate` constant. Magnitude: no published figure; report the before/after delta.
- **Level-oscillation fix:** count `SetClockLevels` changes per minute in `adb logcat -s XrPerformanceManager`; it should fall toward zero in steady gameplay.
- **Boost / trading / dual-core:** the `CreateClient` lines appear once per build; `cpu_frequency_MHz` reaches the expected clock during Boost; the Boost window ends within 30 s.
- **Record** the OS build with every capture: levels and clocks change across OS updates without a rebuild (Q2-057).

## Pitfalls and myths

- **"Request Boost / L5 for more FPS."** Boost is a 45 s burst refused under throttling; GPU L5 is opportunistic and where throttling is "much more common" (A3-085). Neither can hold a minimum frame rate (Q2-029).
- **"Higher levels are free."** Over-requesting costs battery and heat with no extra frames (Q2-054).
- **"Levels are clocks."** They are hints inside a range; the OS keeps the lowest level that holds frame rate, and casting or other OS features can override them (A1-028, A1-036). Same level number != same throughput across headsets (Q2-046 notes).
- **"Profile for 3 minutes."** Meta names profiling only the session start as the most common shipping mistake (A3-079).
- **"Profile while charging."** Charging can raise sustained clocks (stated for Meta VR Glasses, Quest unverified, Q2-064) [verify on device]. Soak on battery.
- **"Pin levels for the soak."** Pinning hides the governor. Pin for A/B timing, unpin for soaks (Q1-079).
- **Stale tables and APIs.** Quest 2 GPU L4 = 490 MHz is stale (A1-007). `vrapi_SetClockLevels`, `debug.oculus.adaclocks.force 0` and the "power-save levels = (0,0)" throttle model are VrApi-era and stale (A3-096, ARM-C17). `OVRManager.cpuLevel` / `gpuLevel` are `[Obsolete]` (Q1-105). The `PerfMetrics` clock-level fields are deprecated since OVRPlugin 1.68.0 with no replacement (Q2-056).
- **"Use battery / sensor temperature as the thermal signal."** Meta says use PLS; temperatures are a phone-VR legacy (A3-082).
- **"Trading or dual-core is a runtime toggle."** Both are manifest, build-time, OpenXR-backend only, and device-specific (A1-031, A1-032).
- **"Favor CPU in an MR app."** Passthrough removes CPU L4, so trading cannot reach CPU L5 (A1-033).
- **"GPU L3 never appears with passthrough."** A third-party Quest 3 capture shows 34 GPU L3 samples in a passthrough scene (QUEST-GF2-009, [measured]; conflict QUEST-GF2-C4); cause unknown [verify on device]. Budget at L2 anyway.
- **"Store review catches thermal decay."** Only when it drops below 60 fps within Perf.1's 45 min run (QX-C7).
- **Old power figure.** "Lowering clocks gives only ~25% less power for the same work" and "CPU load causes more thermal trouble than GPU" come from a deprecated 2022 page (A3-094); treat as a hint, not a Quest 2026 number.
- **Governor metric.** Whether the 83%/77% CPU thresholds use the busiest core or the average is undocumented; OVR Metrics `CPU U` shows the busiest core (Q1-025). Do not assume a main-thread-bound app will ever earn a CPU level rise.

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]: ranges, clock tables, availability, hysteresis (Q2-045 to Q2-049, A1-005, A1-028, A3-070 to A3-073)
- https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ [doc]: native mirror; OS v49 +7% (Q2-057)
- https://developers.meta.com/horizon/essentials/cpu-gpu-levels/ [doc]: alternative range table (QUEST-GF2-004)
- https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ [doc]: Boost, dual-core, trading, GPU L5 (Q2-029, Q2-050 to Q2-053, A1-030 to A1-034, ARM-GF1-003)
- https://developers.meta.com/horizon/documentation/unity/optimize-performance/ [doc]: design to L4 (Q2-028, Q2-064)
- https://developers.meta.com/horizon/essentials/thermal/ [doc]: staged throttling, minute-ten cliff (Q2-058 to Q2-060, Q2-063, A3-078 to A3-080)
- https://developers.meta.com/horizon/essentials/battery-saver-mode/ and https://developers.meta.com/horizon/documentation/unity/os-battery-saver-mode/ [doc]: Battery Saver (Q2-062, A3-092)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ and https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ [doc]: VrApi line, PLS, clockStateLogLevel (Q1-036, Q2-061, A3-083, A3-084)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat/ [doc]: XrPerformanceManager lines (Q1-035)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ [doc]: POW L, temperature guidance (A3-081, A3-082)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc]: CSV commands and columns (Q1-005, A3-049, A3-093)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]: `debug.oculus.cpuLevel` / `gpuLevel` (Q1-077, Q1-079)
- https://developers.meta.com/horizon/documentation/unity/po-per-frame-gpu/ [doc]: stable measurement (Q2-039, A3-051)
- https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ [doc]: thermal refresh step and simulation broadcast (Q2-014)
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc]: dynamic resolution and thermal (Q2-025, Q3-049, Q3-051, A3-086)
- https://developers.meta.com/horizon/documentation/unity/unity-ovrcamerarig/ [doc]: Enable Dynamic Resolution, ranges (Q4-064)
- https://developers.meta.com/horizon/blog/boost-app-performance-525-mhz-gpu-frequency-meta-quest-2/ [doc]: Quest 2 490 -> 525 MHz (A1-007)
- https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/ [doc]: deprecated 2022 power page, stale (A3-094, A3-096)
- https://raw.githubusercontent.com/darktable-mirror/com.meta.xr.sdk.core/main/Scripts/OVRManager.cs [doc]: `OVRManager.ProcessorPerformanceLevel`, `suggestedCpuPerfLevel` (Q1-105)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/performance-settings.html [doc]: `XrPerformanceSettingsFeature`, under-30 s Boost (Q2-055)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/changelog/CHANGELOG.html [doc]: API since 1.11.0 (A1-045)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc]: Adaptive Performance for OpenXR (U1-073)
- https://github.com/hrydgard/ppsspp/commit/5491a05796863c89051bf9569e1d6597ed13f4a2 [community]: XR_EXT_performance_settings enumerated on Quest 2 (QUEST-GF1-010)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md [doc]: 10 min run, 20 min cool-down at ~21 °C (A3-095)
- https://www.uploadvr.com/meta-quest-3-gpu-clock-speed-performance-boost/ [community]: 599/640 MHz, Favor GPU -16% CPU (A3-088)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]: 690/492 MHz readouts (ARM-C3)
- https://developers.meta.com/horizon/documentation/unreal/unreal-blueprints-set-cpu-and-gpu-levels/ [doc], accessed 2026-09-24: Unreal default-level conflict (Q2-C2)
- https://developers.meta.com/horizon/resources/vrc-quest-performance-2/ [doc], accessed 2026-09-24: Perf.2 retirement, Store gating (Q1-085, QX-C7)
- https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_EXT_performance_settings.html [doc], accessed 2026-09-24: extension spec, Boost duration (QX-C8)
- https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_144005.csv [measured]: Quest 3 MR level samples, 2361 MHz Boost clock (QUEST-GF2-009)
