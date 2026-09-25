# Logcat: the per-second VrApi line and XrPerformanceManager

Applies to: Quest 2, Quest 3/3S. Source unless noted:
https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/
(updated Jul 31, 2025; native copy identical) and
https://developers.meta.com/horizon/documentation/unity/ts-logcat/ ,
accessed 2026-09-24 [doc].

## Commands (Q1-027)

```
adb logcat -s VrApi,XrPerformanceManager
adb logcat -c; adb logcat -s XrPerformanceManager      # clean buffer first
adb shell setprop debug.oculus.clockStateLogLevel 1    # clock-change reasons (Q1-036); 2 adds REJECTED
```

Wrapper: `quest_adb.py logcat --clear --seconds 60 --out run/vrapi.log`.

## Example line (Q1-028, verbatim)

```
FPS=72/72,Prd=38ms,Tear=0,Early=0,Stale=0,Stale2/5/10/max=0/0/0/0,VSnc=1,Lat=-1,Fov=0,CPU4/GPU=2/2,1171/441MHz,OC=FF,TA=0/0/0,SP=N/N/N,Mem=2092MHz,Free=2975MB,PLS=0,Temp=32.2C/0.0C,TW=1.25ms,App=4.49ms,GD=0.00ms,CPU&GPU=12.96ms,LCnt=2(DR72,LM2),GPU%=0.43,CPU%=0.37(W0.50),DSF=1.00,CFL=19.79/21.54,ICFLp95=20.94,LD=0,SF=1.00,LP=0,DVFS=0,ShrpLCnt=5,ShrpR=1.000,SSLCnt=3/3
```

Parse as comma-separated `key=value`, with special cases `CPU4/GPU=a/b`, the
bare `1171/441MHz`, `LCnt=n(DRx,LMy)` and `CPU%=a(Wb)`. Tokens come and go
with features (Shrp* only with auto-filtering): parse by key.

## Fields

| Field | Meaning | ID |
|---|---|---|
| `FPS=r/d` | rendered / refresh; with AppSW shows half | Q1-029 |
| `Prd` | prediction time, pose query to photons | Q1-029, Q2-069 |
| `Tear` | tears (compositor too slow) | Q1-029 |
| `Early`, `Stale` | per-second event counts | Q1-029 |
| `Stale2/5/10/max` | runs of 2/5/10 consecutive stale frames, and max run, in the last second; cheapest hitch detector | Q1-029 |
| `VSnc` | swap interval: 1 normal, 2 half rate, 0 AppSW | Q1-029, Q2-068 |
| `Lat` | >0 extra-latency frames, 0 none, -1 Phase Sync (default), -2 fixed-latency phase sync, -3 phase sync tuned for AppSW; FrameSync reporting undocumented | Q1-030, Q2-068 |
| `Fov` | FFR level; `D` suffix = dynamic | Q1-081 |
| `CPU4/GPU=a/b` | CPU/GPU levels; "4" is the core measured, not a level; next token = MHz | Q1-031, Q1-025 |
| `OC` | obsolete | Q1-031 |
| `TA` | affinity of ATW, main, render threads | Q1-031 |
| `SP` | scheduling priority, F = SCHED_FIFO, N = SCHED_NORMAL; set via `XR_KHR_android_thread_settings` | Q1-031 |
| `Mem` | memory clock (2092 MHz in the line, 1804 MHz in the field table; not device specs, ARM-C24) | Q1-031, A3-053 |
| `Free` | free memory | Q1-031 |
| `PLS` | power level 0 NORMAL, 1 SAVE, 2 DANGER | Q1-031, Q1-016 |
| `Temp` | battery/sensor temperature; legacy from phone VR, use `PLS` | Q1-016 |
| `TW` | TimeWarp (compositor) GPU time | Q1-032 |
| `App` | app GPU time (can include preemption, Q2-040) | Q1-032 |
| `GD` | boundary (Guardian) GPU time | Q1-032 |
| `CPU&GPU` | Unity/Unreal only: render-thread frame start to GPU completion; render-thread CPU ≈ `CPU&GPU − App` | Q1-032 |
| `LCnt=n(DRx,LMy)` | layer count incl. system; DR direct-render FPS; LM merged layers | Q1-033 |
| `GPU%` | 0-1; above 0.9 scheduling problems; under-reports at half rate | Q1-033, Q1-089 |
| `CPU%=a(Wb)` | average, W = worst core | Q1-033 |
| `DSF` | DPU scaling factor | Q1-033 |
| `CFL=min/max` | compositor frame latency, ms | Q1-033, Q2-069 |
| `ICFLp95` | p95 integrated compositor frame latency | Q1-033 |
| `LD` | local dimming (Quest Pro) | Q1-033 |
| `SF` | submitted ÷ recommended resolution; confirms render scale reached the compositor | Q1-033 |
| `LP` | Battery Saver on (1) | Q1-031, Q2-062 |
| `DVFS` | documented as never enabled | Q1-031 |

AppSW line (Q1-034): `ASW=90, Type=App E=0.022/0.271,D=0.000/0.000`.

XrPerformanceManager (Q1-035):
`01-19 16:05:56.196  2817  3566 I XrPerformanceManager: perfmgr: SetClockLevels: Apply pending clock request change: 4,3 -> 3,3`.
The buffer can hold history older than your read start; clear first.

## Open: does a Unity OpenXR build print the VrApi line? (Q1-037, ARM-C19)

The logcat page documents the line as current and ties `SP=` to the OpenXR
extension; community reports see `Lat=-1` in OpenXR Unity logs. An older
reading (A1-086, 2019 blog) called `TA`/`SP` VrApi-only. No Meta page says
outright that OpenXR apps print it. Check once per project per OS build:
`adb logcat -s VrApi` [verify on device]. No published statement on which
`SP` values a Unity OpenXR app should show; record `SP` in a known-good build
and treat changes as a regression signal (Q1-031).
