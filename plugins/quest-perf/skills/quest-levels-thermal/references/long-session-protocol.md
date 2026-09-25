# Long-session (thermal) measurement protocol

Built from Meta's method (Q2-060, https://developers.meta.com/horizon/essentials/thermal/), the OVR Metrics recipe (A3-093, https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/) and Qualcomm's thermal-test guidance (A3-095, https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md). All accessed 2026-09-24. Meta publishes no minutes-to-throttle number and no decay curve for any Quest; this protocol is how you produce your own. Applies to Quest 2, Quest 3, Quest 3S; any Unity version; GLES or Vulkan.

## Setup

1. **Build:** the shipping build: shipping refresh rate, shipping `ProcessorPerformanceLevel`, dynamic resolution and foveation as shipped (A3-093). No Development Build, no Profiler connection, no video capture (recording costs performance, Q1-082).
2. **Device state:**
   - Reboot first. That clears any `debug.oculus.*` props left from A/B work (Q1-077), including pinned `cpuLevel`/`gpuLevel`: a soak must see real governor behaviour (Q1-079).
   - Battery above 50%, unplugged during the run (Q2-060). Charging may raise sustained clocks (stated for Meta VR Glasses; Quest unverified, Q2-064).
   - Battery Saver off (it forces 72 Hz, FFR 3, no GPU L5, no Boost; Q2-062). Confirm `LP=0` in logcat.
   - No casting (casting can override levels, A1-036).
   - Fixed ambient temperature, about 21 °C; start cold: at least 20 min idle since the previous run (A3-095).
3. **Snapshot props:**
   ```sh
   adb shell getprop | grep debug.oculus > props_before.txt
   adb shell getprop ro.build.fingerprint > os_build.txt
   ```
   The toolkit's quest_adb.py does the same: `py -3.12 ../quest-profiling-toolkit/scripts/quest_adb.py props-snapshot` (paths relative to this skill's folder; add `--dry-run` before the subcommand to print the commands without running them; `<subcommand> --help` for flags).
4. **Enable logging:**
   ```sh
   adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV
   adb shell setprop debug.oculus.clockStateLogLevel 1
   adb logcat -c
   adb logcat -s VrApi,XrPerformanceManager > levels.log
   ```
   (`logcat -s` needs the device connected; for a wireless or unplugged run, rely on the CSV and pull logcat afterwards with `adb logcat -d`, knowing the buffer may have rolled over.)
5. **Mark segments** in the CSV from the app with `AppendCsvDebugString` (at most 1 Hz; Q1-020) at each scene change and in the `Degraded` callback of the level-policy component.

## Run

- A fixed, representative scene or scripted playthrough for **30 minutes or more** (Q2-060, A3-093). The heaviest steady gameplay, not a menu.
- Separate runs for VR and MR modes (Quest 3/3S MR has lower level caps, Q2-038).
- Same build on each headset: Quest 2, Quest 3, Quest 3S. 3S sustained headroom vs Quest 3 is unpublished; this run is the measurement.
- Repeat at least twice per configuration after a ≥20 min cool-down (A3-095).

## Pull and analyse

```sh
adb pull /sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/ .
adb shell setprop debug.oculus.clockStateLogLevel 0
py -3.12 ../quest-profiling-toolkit/scripts/ovr_metrics_csv.py <file.csv> --hz <shipping Hz> --window-min 5   # run from this skill's folder
```

Omit `--hz` to use the CSV's `display_refresh_rate`.

`ovr_metrics_csv.py` is owned by `quest-perf:quest-profiling-toolkit`. Its rows are 1 Hz interval averages, so its percentiles are per-second, not per-frame (Q1-010); use Perfetto for frame-level pacing.

Fill in this report per run:

| Field | Column / source |
|---|---|
| OS build, device, refresh rate, mode (VR/MR) | `os_build.txt`, `display_refresh_rate` |
| Minute of first `power_level_state` change (0 -> 1, 1 -> 2) | `power_level_state` |
| Minute of first drop in max `cpu_level` / `gpu_level` | `cpu_level`, `gpu_level`, `levels.log` |
| Clock drift, first 5 min vs last 5 min | `cpu_frequency_MHz`, `gpu_frequency_MHz` |
| Refresh-rate changes (thermal step 1) | `display_refresh_rate` |
| Stale frames per minute and max stale in any 60 s window, first vs last 5 min | `stale_frame_count` |
| App GPU time drift | `app_gpu_time_microseconds` (flag 65535 clamps) |
| Render scale drift (dynamic resolution absorbing throttle) | `SF=` in logcat, or the CSV render-scale column when present |
| Battery temperature trend (context only; PLS is the thermal signal, A3-082) | `battery_temperature_celcius` (spelled this way in the CSV) |
| Reasons for each level change | `levels.log` FORCED / REJECTED lines |

## Interpreting

- `power_level_state` stays 0, clocks flat, stale rate flat: thermally sustainable for this scene and ambient.
- Clocks fall while `power_level_state` is still 0 and the scene is steady: the governor is lowering levels (stage 1-2). Check `levels.log` reasons.
- `power_level_state` reaches 1: Meta advises cutting rendering cost (Q2-061). Reaching 2 shows the user an overheat dialog; stage 4 cool-down follows if limits are exceeded (Q2-058).
- A drop only at GPU L5 -> L4 with render scale falling and no stale-rate rise is the designed behaviour of dynamic resolution (Q2-050).
- Store context: Perf.1's 45 min test fails only below 60 fps; everything above that is your own quality bar (QX-C7).

## Rehearsing the thermal response without waiting

Fire the simulated thermal refresh event while the app runs (Q2-014, https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/):

```sh
adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SIMULATE_THERMAL --es subsystem refresh --ei seconds_throttled 10
```

The toolkit's `quest_adb.py thermal-sim` wraps it. Confirm the app's `DisplayRefreshRateChanged` handler fires and the quality tier steps down, and that time-based logic survives a 90/120 -> 72 Hz change. This rehearses only the refresh step; it does not simulate clock throttling, which needs the real soak.
