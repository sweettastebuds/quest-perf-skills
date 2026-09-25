# ADB setprops, broadcasts and on-device commands (Meta-documented only)

Applies to: Quest 2, Quest 3/3S. Accessed 2026-09-24. All props reset on
reboot, and a reboot is the reset (Q1-077,
https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]).
Record `adb shell getprop | grep debug.oculus` next to every capture
(`quest_adb.py props-snapshot`).

## System properties

| Property | Values | Effect | Source | quest_adb.py |
|---|---|---|---|---|
| `debug.oculus.cpuLevel` | int | override app CPU level | Q1-079 ts-systemproperties | `pin-levels --cpu N` |
| `debug.oculus.gpuLevel` | int | override app GPU level | Q1-079 | `pin-levels --gpu N` |
| `debug.oculus.refreshRate` | Quest 2: 60/72/80/90/120; Quest 3/3S: 72/80/90/120; default 72 | display rate without rebuild | Q1-078 | `refresh-rate N` |
| `debug.oculus.foveation.dynamic` | 0/1 | set 0 first or dynamic foveation overrides the level | Q1-081 / Q3-028 os-fixed-foveated-rendering | `foveation` |
| `debug.oculus.foveation.level` | 0 Off, 1 Low, 2 Medium, 3 High, 4 High Top | FFR level; logcat shows `Fov=3` or `Fov=3D` when dynamic | Q1-081 / Q3-028 | `foveation --level N` |
| `debug.oculus.foveation.subsampled` | 1/0 | Vulkan subsampled layout A/B | Q3-045 native os-fixed-foveated-rendering | `subsampled on|off` |
| `debug.oculus.textureWidth` / `textureHeight` | default 1440x1584 (Quest 2), 1680x1760 (Quest 3/3S) | eye-buffer size, no-rebuild fill test | Q1-080 (conflict Q1-C4 resolved: 1680x1760) | not wrapped |
| `debug.oculus.clockStateLogLevel` | 0/1/2 | 1 logs every CPU/GPU clock change with Min/Max/Current/Final and reason; 2 adds REJECTED/ignored requests | Q1-036 ts-logcat-stats | `clocklog N` |
| `debug.oculus.spaceWarpDebug` | 1 | enable AppSW debug | Q3-074 os-app-spacewarp, unity-asw | `appsw-debug` |
| `debug.oculus.MVOverlay` | 1 MV, 2 depth, 3 MV amplified, 4 amplified with gray at zero | motion-vector overlay (then two power-button presses) | Q3-074 | `appsw-debug --mode N` |
| `debug.oculus.MVOverlay.Alpha` | e.g. 0.8 | overlay alpha | Q3-074 | `appsw-debug --alpha` |
| `debug.oculus.sysPropDebug` + `debug.oculus.swapInterval` | 1 + 2 | force half rate for testing | Q3-074 | `appsw-debug --half-rate` |
| `debug.oculus.fullRateCapture`, `enableVideoCapture`, `capture.width/height` (default 1024), `capture.bitrate` (default 5000000) | | video capture; costs performance, keep out of measurement runs | Q1-082 | not wrapped |
| `persist.debug.dalvik.vm.jdwp.enabled` | 1 (needs root) | RenderDoc capture of non-debuggable builds on API 34+ | Q1-060, A3-044 | not wrapped |

Excluded: `debug.oculus.headlock` appears only in a Unity QA repro recipe
(G2-010, gles3.md), on no Meta page. The properties behind `metavr device
vrruntime` flags are unpublished (Q1-083); use the CLI.

## Broadcasts

| Broadcast | Effect | Source | quest_adb.py |
|---|---|---|---|
| `adb shell am broadcast -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV` | Report Mode (CSV) on; `DISABLE_CSV` off | Q1-003, A3-049 ts-ovrmetricstool | `csv on|off`, `csv-on` |
| same receiver, `ENABLE_OVERLAY` / `DISABLE_OVERLAY` | HUD on/off; extras `--eb headlocked`, `--ef pitch` (-90..90), `--ef yaw` (-180..180), `--ei scale` (1-3), `--ef distance` (0.1+, headlocked) | Q1-003, Q1-004 | `csv overlay-on|overlay-off` |
| same receiver, `ENABLE_GRAPH`, `ENABLE_STATS`, `DISABLE_GRAPH`, `DISABLE_STATS`; one stat: `ENABLE_STAT --es stat <csv column name>` | HUD content | Q1-003, Q1-005 | not wrapped |
| same receiver, `ENABLE_DROPPED_FRAME_SCREENSHOT --ei count <n> --ei time <t>` / `DISABLE_...` | screenshot when n frames missed within t; unit of t undocumented | Q1-003 | not wrapped |
| same receiver, `LOG_STATE` | prints tool config to logcat as JSON; use as a precondition check | Q1-003 | `csv log-state` |
| `adb shell am start omms://app` | open the tool UI | Q1-001 | `csv open` |
| `adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SKIP_RENDERING --ei milliseconds 60000` | compositor stops rendering: TW=0, `App=` is app-only GPU time | A3-051, Q2-039 po-per-frame-gpu | `compositor-skip`, `isolate-gpu --skip-ms` |
| `adb shell am broadcast -a com.oculus.vrruntimeservice.COMPOSITOR_SIMULATE_THERMAL --es subsystem refresh --ei seconds_throttled 10` | rehearse the thermal refresh step (above 72 Hz drops to 72; next step halves app rate) | Q2-014 unity-set-disp-freq | `thermal-sim` |

## metavr device vrruntime (Q1-083)

`metavr device vrruntime get|reset|set` mirrors MQDH's "VrRuntime Debug".
Options: `--cpu-level 0-5`, `--gpu-level 0-5` (0 = runtime decides),
`--foveation-level 0-4`, `--dynamic-foveation`, `--gfr-mode`,
`--subsampled-layout`, `--asw-mode 0-3`, `--swap-interval 0-3`,
`--dyn-res-scaler`, `--local-dimming`, `--layer-filter 0-4`,
`--layer-auto-filter 0-3`, `--sysprop-debug`, `--color-space`.
Wrapper: `quest_adb.py vrruntime set --cpu-level 4 --gpu-level 4`.
Source: https://github.com/meta-quest/agentic-tools (docs/metavr-cli.md).

## Other on-device commands

| Command | Use | Source |
|---|---|---|
| `adb shell gpumeminfo -p $(pidof <process>)` (+ `-l`; flags -h -m -o -p -s -d -l -t) | per-process GPU memory | Q1-095 ts-gpumeminfo |
| `adb shell dumpsys package com.oculus.ovrmonitormetricsservice` (grep versionName) | OVR Metrics version for capture metadata (standard Android command) | Q1-001 |
| `adb logcat > crash.log`; `adb bugreport outputfile.zip`; `ndk-stack -sym <project>/symbols/arm64-v8a -dump crash.log > stack.log` | crash triage (VRC Functional.1) | Q1-039 ts-logcat |

## Stable-measurement recipe (Q2-039, A3-051)

1. `quest_adb.py isolate-gpu --cpu 4 --gpu 4` (pins levels, foveation off).
2. Optional `--skip-ms 60000` to remove compositor GPU work.
3. Disable dynamic resolution in the build (A3-052; GPU L5 is then unavailable).
4. From the 2021 blog: lock the camera, disable Guardian, and use swap
   interval 2 for apps that cannot hold full rate.
5. Pinned levels still throttle when hot: watch `PLS` during the run (A3-051).
6. Reboot afterwards (`quest_adb.py reset --yes`).
