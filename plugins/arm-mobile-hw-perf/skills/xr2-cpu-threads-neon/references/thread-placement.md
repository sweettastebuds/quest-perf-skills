# Thread placement on Quest: recipes

Companion to `arm-mobile-hw-perf:xr2-cpu-threads-neon`. All sources accessed 2026-09-24.
Everything here is a measurement or a debug-only lever; the ship default is Unity's own
thread configuration (A1-049, AS-001).

## What is published and what is not

| Question | Quest 2 | Quest 3/3S | Source |
|---|---|---|---|
| App core count | 3 (dual-core mode "disables one CPU core"; L5 = three-core option) | unpublished | A1-004 [doc] |
| App core IDs | probably cpu4-6 (Perfetto example: #4, #5 = UnityMain, #6) [verify on device] | GDC 2026 auto-captions are self-contradictory: the trace shows the app on cores 3-5 (the top three on a 6-core part), but the speakers say the bottom half is app and the top three are system; A1-050 separately guesses cpu2-5 is the 2.36 GHz cluster. No published mask. Read `Cpus_allowed_list` [verify on device] | A1-004, QUEST-GF2-010, A1-050 |
| Compositor core and policy today | unpublished (VrApi era: SCHED_NORMAL, affinity 0, reserved core) | unpublished | A1-048 |
| Default job workers | unpublished; stale community claim main + render + 2 workers | unpublished; one report of 2 (Unity 2022.3.15) | U5-034, A1-055 [community] |
| Unity OpenXR / Meta plugin registers UnityMain via XR_KHR_android_thread_settings | undocumented | undocumented | A1-044 |
| `SystemInfo.processorCount` vs usable cores | Geekbench 2D sees 8; VR docs imply 3 | not measured | ARM-C7 |

Historical precedent (Quest 1, 2019): 3 of 4 gold cores for the app, the fourth reserved for
TimeWarp and system; log line `TA=0/E0/0` (main thread mask 0xE0 = cores 5-7) and
`SP=N/F/N` (main thread SCHED_FIFO) (A1-010, A1-011). Do not transfer the masks to Quest 2/3.

## Recipe 1: allowed CPU set

```sh
adb shell pidof <your.package>                       # -> PID
adb shell cat /proc/<PID>/status | grep -E "Cpus_allowed_list|Threads"
adb shell ls /proc/<PID>/task                        # thread IDs
adb shell cat /proc/<PID>/task/<TID>/status | grep -E "Name|Cpus_allowed_list"
adb shell cat /dev/cpuset/top-app/cpus               # if readable
adb shell cat /dev/cpuset/foreground/cpus /dev/cpuset/background/cpus /dev/cpuset/system-background/cpus
```
Run while the app is in VR (not the 2D launcher), at a pinned CPU level, on each device and
Horizon OS version you ship to (A1-004 notes, Known unknowns). Record OS build with the result.

## Recipe 2: per-thread policy and last core

```sh
adb shell ps -T -p <PID> -o TID,NAME,SCH,RTPRIO,PRI,NI,PSR
```
- Rows to find: `UnityMain`, `UnityGfxDeviceW` (Unity render thread), job workers (several;
  `Worker Thread`, or `Job.Worker N` in some Unity versions; OS-level name unpublished
  [verify on device]), `UnityChoreograph`, audio threads. `RenderThread` is Android's HWUI
  thread, not Unity's (A1-052).
- `SCH` 1 or 2 with an `RTPRIO` = real-time (FIFO/RR), i.e. the thread was probably registered;
  0 = SCHED_NORMAL (A1-044). `PSR` = the core it last ran on; sample a few times.
- Toybox builds differ in which `-o` fields they support; drop unsupported fields and retry.

## Recipe 3: VrApi logcat line (`TA=`, `SP=`)

```sh
adb logcat -s VrApi
```
Example (Meta, 2025 page): `...CPU4/GPU=2/2,1171/441MHz,OC=FF,TA=0/0/0,SP=N/N/N,Mem=2092MHz,...` (AS-001).

| Field | Meaning |
|---|---|
| `CPU4/GPU=a/b,c/dMHz` | digit after CPU = measured core; a/b = CPU/GPU levels; then clocks |
| `TA=x/y/z` | affinity masks of TimeWarp / main / render threads; Meta says they help verify big-core placement |
| `SP=x/y/z` | scheduling policy of the same three: `F` = SCHED_FIFO, `N` = SCHED_NORMAL |
| `OC=` | no longer used; current Quest CPUs cut core energy without taking cores offline |

Conflict ARM-C19: the 2019 blog (A1-046) treated `TA=`/`SP=` as VrApi-only; the 2025 logcat
page documents them and ties `SP=` to `XR_KHR_android_thread_settings`. Whether a Unity OpenXR
build prints the line is [verify on device]. If it does, `F` in the main/render slots means
registered real-time threads, `N/N/N` means normal scheduling.

## Recipe 4: Perfetto CPU scheduling

- Capture from MQDH with CPU Scheduling enabled (plus XR runtime metrics); Development build or
  symbol files for Unity; callstack sampling via traced_perf since OS v51 (A1-084).
- Read the per-core tracks: which cores UnityMain, UnityGfxDeviceW and workers occupy, and how
  often they migrate. A main thread that migrates can hide in averaged utilisation (A1-047).
- Dual-core candidate pattern (Quest 2/Pro only): UnityMain saturating one core, other app
  cores under 50% (A1-057). On Quest 3/3S the same pattern means move work into jobs.
- Contention pattern (Meta GDC 2026, Quest 3): zoom out, find frames with gaps, go to the end
  of the UnityMain sleep, follow the wake-up to the thread that signalled it, check that
  thread's scheduling state. Meta's case: FPS 67 instead of 72, about 5 bad frames per second,
  UnityMain blocked about 3.3 ms on a late-scheduled system thread (QUEST-GF2-010). An
  in-engine profiler only shows the main thread stalled.
- Useful trace-processor query for per-thread core residency:
  ```sql
  SELECT t.name, s.cpu, COUNT(*) AS slices, SUM(s.dur)/1e6 AS ms
  FROM sched s JOIN thread t USING (utid)
  WHERE t.name IN ('UnityMain','UnityGfxDeviceW') OR t.name LIKE '%Worker%'
  GROUP BY t.name, s.cpu ORDER BY t.name, s.cpu;
  ```

## Startup log

Logs the numbers the dossiers could not find (A1-055, U5-032, ARM-C7). Drop into any runtime
assembly; compiles on Unity 2021.3 through 6000.6.

```csharp
using System.IO;
using Unity.Jobs.LowLevel.Unsafe;
using UnityEngine;

public static class QuestCpuTopologyLog
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Log()
    {
        string allowed = "n/a";
#if UNITY_ANDROID && !UNITY_EDITOR
        try
        {
            foreach (var line in File.ReadAllLines("/proc/self/status"))
                if (line.StartsWith("Cpus_allowed_list")) { allowed = line.Substring(line.IndexOf(':') + 1).Trim(); break; }
        }
        catch (System.Exception e) { allowed = "error: " + e.GetType().Name; }
#endif
        Debug.Log($"[CpuTopo] model={SystemInfo.deviceModel} unity={Application.unityVersion} " +
                  $"processorCount={SystemInfo.processorCount} cpusAllowed={allowed} " +
                  $"jobWorkerMax={JobsUtility.JobWorkerMaximumCount} jobWorkerCount={JobsUtility.JobWorkerCount} " +
                  $"threading={SystemInfo.renderingThreadingMode}");
    }
}
```
Read with `adb logcat -s Unity | grep CpuTopo`. Run once per device (Quest 2, Quest 3, Quest 3S)
and per Unity line you ship (2021.3, 2022.3, 6000.0, 6000.3+), and once with dual-core mode on
(Quest 2) to see the automatic worker adjustment (A1-053).

## Unity thread arguments

| Thread | Priority | Affinity |
|---|---|---|
| Main (UnityMain) | `-platform-android-unitymain-priority <-20..19>` | `-platform-android-unitymain-affinity <v>` |
| Job workers | `-platform-android-jobworker-priority <-20..19>` | `-platform-android-jobworker-affinity <v> [v1 v2 ...]` |
| Render (UnityGfxDeviceW) | `-platform-android-gfxdeviceworker-priority <-20..19>` | `-platform-android-gfxdeviceworker-affinity <v>` |
| Worker count | `-job-worker-count <n>` (lower only) | |
| Big-core classification | `-platform-android-cpucapacity-threshold [0-1024]` | |

- `<v>` = `any`, `little`, `big`, or a hex/binary mask with bit index = CPU index (A1-051).
  `0x70` = cpu4-6; `0x38` = cpu3-5. Build the mask from `Cpus_allowed_list`, never from a guess.
- `big`/`little` rely on OS capacity data, or Unity's fallback rule of capacity ≥ 2x the
  slowest core (A1-049). Quest 2's A77/A55 split meets it; Quest 3/3S (1.15x) may classify no
  core as big (A1-050) [verify on device].
- Unity says some devices and OS versions ignore these arguments, and advises keeping defaults
  (A1-049, A1-051). Page present in the 2021.3, 2022.3, 6000.0 and 6000.6 manuals (A1-049);
  unity.md U5-033 marks 2021.3/2022.3 availability as unverified.
- With Graphics Jobs on, job workers also call the graphics API (A1-051 note).

Quick test without code (A1-052, U5-033):
```sh
adb shell "am start -n <your.package>/com.unity3d.player.UnityPlayerActivity -e unity '-job-worker-count 1'"
```
The outer double quotes keep the whole command in one argument so the device shell sees the
single-quoted Unity extra intact; this form works from bash and PowerShell.
With GameActivity the activity class name differs; check the merged manifest.

Persistent (debug builds only): extend the player activity and override
`updateUnityCommandLineArguments`, per
https://docs.unity3d.com/6000.0/Documentation/Manual/android-custom-activity-command-line.html .
Place in `Assets/Plugins/Android/` and point the manifest's launcher activity at it.

```java
package com.yourstudio.questdebug;

import com.unity3d.player.UnityPlayerActivity;

public class ThreadDebugActivity extends UnityPlayerActivity {
    @Override
    protected String updateUnityCommandLineArguments(String cmdLine) {
        String extra = "-job-worker-count 1";   // example: Quest 2 dual-core experiment
        return (cmdLine == null || cmdLine.isEmpty()) ? extra : cmdLine + " " + extra;
    }
}
```

## Registering native threads

`XR_KHR_android_thread_settings` (spec 1.1.63): `xrSetAndroidApplicationThreadKHR(XrSession,
XrAndroidThreadTypeKHR, uint32_t threadId)`, types APPLICATION_MAIN (1), APPLICATION_WORKER (2),
RENDERER_MAIN (3), RENDERER_WORKER (4); errors `XR_ERROR_ANDROID_THREAD_SETTINGS_FAILURE_KHR`,
`XR_ERROR_ANDROID_THREAD_SETTINGS_ID_INVALID_KHR` (A1-042). The runtime's response is
undefined by the spec; Meta documents only the `SP=` priority effect (AS-001). Meta's sample
registers APPLICATION_MAIN and RENDERER_MAIN right after `xrBeginSession` (A1-043).

Native plugin sketch (C, untested; the extension must be enabled at instance creation, e.g. by
a Unity `OpenXRFeature` that lists `XR_KHR_android_thread_settings` in its
`OpenxrExtensionStrings` and hands `xrInstance`/`xrSession` and `xrGetInstanceProcAddr` to the plugin):

```c
#include <jni.h>
#include <unistd.h>
#define XR_USE_PLATFORM_ANDROID
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>

/* Call on the thread to register, after xrBeginSession succeeded. */
XrResult RegisterCurrentThreadAsWorker(XrInstance instance, XrSession session,
                                       PFN_xrGetInstanceProcAddr getProcAddr)
{
    PFN_xrSetAndroidApplicationThreadKHR setThread = NULL;
    XrResult r = getProcAddr(instance, "xrSetAndroidApplicationThreadKHR",
                             (PFN_xrVoidFunction*)&setThread);
    if (XR_FAILED(r) || setThread == NULL) return r;
    return setThread(session, XR_ANDROID_THREAD_TYPE_APPLICATION_WORKER_KHR, (uint32_t)gettid());
}
```
Verify with Recipe 2 (`SCH`/`RTPRIO` of that TID) before and after. Do not register Unity's own
threads from a plugin: whether Unity or Meta's plugin already does is undocumented (A1-044),
and double registration is untested.

## Dual-core mode and worker count (Quest 2 / Pro)

Dual-core mode removes one app core and raises SustainedHigh to CPU L6 (2.15 GHz) on two
(A1-031); Unity lowers the worker count automatically if `JobWorkerCount` was never set
(A1-053). Meta: 3 cores at L4 beat dual-core at L6 unless the frame is one long sequential
chain (ARM-GF1-001). Enabling it and choosing levels: `quest-perf:quest-levels-thermal`.
