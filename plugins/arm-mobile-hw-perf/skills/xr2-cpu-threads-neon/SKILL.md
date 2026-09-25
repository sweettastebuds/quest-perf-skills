---
name: xr2-cpu-threads-neon
description: "ARM CPU behaviour for Unity on Quest 2 (Cortex-A77/A55) and Quest 3/3S (Cortex-A78C): how many cores an app gets, thread placement of UnityMain, render and job workers, affinity arguments, job worker counts, cache lines and data layout, NEON costs, Burst Arm64 targets, FloatMode and Neon intrinsics. Use when making Burst code faster on Quest, when threads land on the wrong cores, or asking how many cores a Quest app gets. GC, IL2CPP, Graphics Jobs and job usage patterns: unity-perf:unity-cpu-scripting."
---

# XR2 CPU: cores, threads, caches and NEON for Unity on Quest

Goal: **Throughput** (fewer CPU cycles per frame on UnityMain, UnityGfxDeviceW and the
job workers) and **Consistency** (no thread migration onto the wrong cores, no
scheduling stalls, no hand-set affinity that breaks on the next Horizon OS update).

Scope: Quest 2 (XR2 Gen 1, SM8250) and Quest 3/3S (XR2 Gen 2, SXR2230P, one CPU target).
Unity 2021.3 (URP 12), 2022.3 (URP 14), 6000.0-6000.6 (URP 17+), Burst 1.8.x, OpenXR.
Graphics API does not change anything in this skill except where Graphics Jobs make job
workers issue API calls (A1-051); Vulkan is the assumed default.

Reference files (loaded on demand):
- Read [references/thread-placement.md](references/thread-placement.md) when you need the full
  adb/Perfetto recipes, the startup C# logger, the Unity thread-argument table with the custom
  activity code, `TA=`/`SP=` decoding, or the native thread-registration sketch.
- Read [references/neon-costs.md](references/neon-costs.md) when estimating the cycle cost of a
  Burst loop: A77/A78 pipelines and instruction latencies, cache hierarchy ranges, unaligned
  access and store-forwarding rules, memcpy advice, and the pointer-chase / STREAM methods for
  the unpublished cache sizes and DRAM rate.
- Read [references/burst-settings.md](references/burst-settings.md) when setting Burst AOT
  targets, FloatMode/FloatPrecision, OptimizeFor, choosing a Burst version per Unity version, or
  writing gated Neon intrinsics.

No scripts ship with this skill: the measurements are adb commands and in-project C# (see references).

## When to use / when not

Use when:
- A Burst job is slower on device than its op count suggests, or you want the cycle cost of a loop.
- Perfetto shows UnityMain, UnityGfxDeviceW or job-worker threads on unexpected cores, migrating, or sleeping in a wait.
- Someone asks how many cores a Quest app gets, what `SystemInfo.processorCount` means, or whether to set `-job-worker-count` / affinity arguments.
- Choosing Burst AOT targets, `FloatMode`, `FloatPrecision`, `OptimizeFor`, or writing Neon intrinsics.
- Turning a microbenchmark cycle count into a share of the frame at a given CPU level.

Do not use; go to the sibling instead:
- GC spikes, IL2CPP settings, job/Burst usage patterns, Graphics Jobs mode, Multithreaded Rendering, physics, UI, animation: `unity-perf:unity-cpu-scripting`.
- The level-to-clock table, Boost, dual-core mode, level trading, thermal throttling: `quest-perf:quest-levels-thermal`.
- Core types, cluster maximum clocks, Gen 1 vs Gen 2 silicon comparison: `arm-mobile-hw-perf:xr2-gen1-vs-gen2`.
- How to install and drive Perfetto, OVR Metrics, simpleperf, MQDH: `quest-perf:quest-profiling-toolkit`.
- First CPU- vs GPU-bound split: `quest-perf:quest-triage`.
- Stale frames with a good average, FrameSync: `quest-perf:quest-frame-pacing`.
- DRAM bandwidth and power cost of memory traffic: `arm-mobile-hw-perf:xr2-bandwidth-power`.
- Passthrough CPU level caps as an MR budget: `quest-perf:quest-mr-costs`.

## Diagnose first

Pin a known CPU level before any CPU A/B, and record the granted level with every capture;
casting or other OS features can override levels (A1-085, A1-036). Level control is in
`quest-perf:quest-levels-thermal`.

1. **Which cores the app may use** (all Quest; the set is unpublished, A1-004):
   ```sh
   PID=$(adb shell pidof <your.package>)
   adb shell cat /proc/$PID/status | grep Cpus_allowed_list
   adb shell cat /dev/cpuset/top-app/cpus          # if readable
   ```
2. **Where each Unity thread runs and with what scheduling policy** (A1-044):
   ```sh
   adb shell ps -T -p $PID -o TID,NAME,SCH,RTPRIO,PRI,NI,PSR
   ```
   Look at `UnityMain`, `UnityGfxDeviceW` (Unity's render thread; `RenderThread` is Android
   HWUI, not Unity, A1-052) and the job-worker rows (`Worker Thread`, or `Job.Worker N` in some
   Unity versions; OS-level name unpublished [verify on device]). `SCH` 1/2 with an `RTPRIO` =
   real-time; 0 = normal. `PSR` = last core. Field support depends on the toybox build.
3. **Scheduling priority as the runtime sees it** (AS-001, ARM-C19):
   `adb logcat -s VrApi` and read `SP=` (TimeWarp/main/render: `F` = SCHED_FIFO, `N` =
   SCHED_NORMAL) and `TA=` (affinities). Whether a Unity OpenXR build emits this line at all
   is [verify on device].
4. **Placement over time**: Perfetto from MQDH with CPU Scheduling on (A1-084). Per-core tracks
   show migration, and gaps where UnityMain sleeps. For a gap, follow the wake-up back to the
   thread that signalled it and check its scheduling state (QUEST-GF2-010).
5. **Worker count and visible cores**: log at startup with the snippet in
   [references/thread-placement.md](references/thread-placement.md#startup-log) (A1-055, U5-032).
6. **Burst codegen**: open Jobs > Burst > Open Inspector, pick the Arm64 target, and look for
   `fmla` (fused), `fdiv`/`fsqrt` (V0-only), `fcvtl`/`fcvtn` (half conversions) and `.8h`
   (native FP16) in hot loops (A1-069, A1-070, A1-079, U5-031).

| Pattern | Meaning | Fix |
|---|---|---|
| UnityMain at 100% of one core, other app cores under 50% | Serial main thread (A1-057) | 1, then 9 |
| UnityMain sleeping mid-frame, woken late by another thread | Blocking wait / system contention (QUEST-GF2-010) | 1 |
| App thread seen on a core outside `Cpus_allowed_list`, or on cpu0-3 on Quest 2 | Hand-set affinity or unregistered helper thread on A55 (A1-077) | 10, 11 |
| Job-worker threads (name [verify on device]) contend on one cache line (per-worker counters adjacent) | False sharing (A1-063) | 5 |
| Hot loop full of `fdiv`/`fsqrt`, or a single accumulator chain | V0-serialised divide, latency-bound FMA (A1-068, A1-069) | 2, 3, 4 |
| `fcvtl`/`fcvtn` around every load/store in an ALU-bound loop | `half` storage in compute-bound code (A1-070) | 6 |

## Key numbers

| Number | Value | Applies to | Source |
|---|---|---|---|
| App cores | 3 (Meta: dual-core mode "disables one CPU core"); probably cpu4-6 (A77 gold) [verify on device] | `Quest 2` | A1-004 [doc] |
| App cores | Unpublished. GDC 2026 auto-captions are self-contradictory: the trace shows the app on cores 3-5 (the top three on a 6-core part), but the speakers say the bottom half is app and the top three are system; A1-050 separately guesses cpu2-5 is the 2.36 GHz cluster. No published mask. Read `Cpus_allowed_list` [verify on device] | `Quest 3/3S` | QUEST-GF2-010 [doc], A1-004, A1-050 |
| Core types | 1x A77 2.84 GHz + 3x A77 2.42 GHz + 4x A55 1.80 GHz; apps never get 2.84 GHz | `Quest 2` | A1-001, A1-003 |
| Core types | 6x Cortex-A78C: 4 @ 2.36 GHz + 2 @ 2.05 GHz, no little cores | `Quest 3/3S` | A1-013, A1-014, ARM-C1 |
| Cluster clock ratio | 2.36 / 2.05 = 1.15x, under Unity's 2x "big" rule | `Quest 3/3S` | A1-050 (derived) |
| L4 (default) CPU clock | 1.48 GHz / 1.92 GHz | `Quest 2` / `Quest 3/3S` | A1-005 [doc] |
| Main-thread cycles per frame at L4 | 72 Hz: 20.6 M / 26.7 M; 90 Hz: 16.4 M / 21.3 M; 120 Hz: 12.3 M / 15.9 M | `Quest 2` / `Quest 3/3S` | A1-026 (derived) |
| Same, MR with passthrough (CPU capped at L3 = 1.65 GHz) | about 22.9 M at 72 Hz | `Quest 3/3S` | A1-018, A1-026 (derived) |
| 1 M cycles | about 0.52 ms at L4 | `Quest 3/3S` | A1-026 (derived) |
| Default job workers | No published number. One unanswered report: 2 workers, Unity 2022.3.15 | `Quest 3` | A1-055 [community] [verify on device] |
| `-job-worker-count` | Can lower, never raise above platform default | `Unity 2021.3`-`6000.6` | A1-054 [doc] |
| Thread priority range | -20 (highest) to 19 | `Unity 2021.3`-`6000.6` | A1-051 [doc] |
| Cache line | 64 bytes on A55, A77, A78C | all Quest | A1-063 [doc] |
| FMLA (ASIMD FP32) | latency 4 (2 with accumulator forwarding), 2 per cycle (V0+V1) | `Quest 2` `Quest 3/3S` | A1-068 [doc] |
| Peak FP32 per core at L4 | 16 FLOP/cycle: 23.7 GFLOPS / 30.7 GFLOPS | `Quest 2` / `Quest 3/3S` | A1-068 (derived) |
| Independent FMA chains to saturate | about 8 | A77, A78 | A1-068 |
| Scalar FP32 FDIV | 7-10 cycles, V0 only, not fully pipelined | A77, A78 | A1-069 [doc] |
| Q-form F32 FDIV throughput | 1/9 to 1/7 per cycle; F16 slower (1/13 to 1/10) | A78 | A1-069 [doc] |
| FCVTL/FCVTN (Q-form) | latency 4, 1 per 2 cycles, V0 only | A78 | A1-070 [doc] |
| SDOT/UDOT | latency 2, 2 per cycle = 32 int8 MAC/cycle/core | A77, A78 | A1-071 [doc] |
| Configured L1/L2/L3 sizes | No published number; measure with the pointer-chase sweep in [references/neon-costs.md](references/neon-costs.md#measuring-what-is-not-published) | both | A1-064, A1-065 |
| SVE / SVE2 / i8mm | absent on every Quest core | all Quest | A1-075, A1-076 |

## Fixes, ranked by payoff ÷ effort

### 1. Take serial and blocking work off UnityMain first
- Change: move main-thread loops into Burst `IJobParallelFor` across the app cores, and remove
  blocking waits (`JobHandle.Complete()` on long jobs in the same frame, synchronous I/O) from
  UnityMain. Patterns and job APIs: `unity-perf:unity-cpu-scripting`.
- Why this ranks first: Meta states an app using all 3 cores at CPU L4 outperforms a
  dual-core-mode app at L6, and spreading work at lower clocks is "generally more
  power-efficient" (ARM-GF1-001, A1-040). The GDC 2026 case lost 5 of 72 frames per second to
  a 3.3 ms main-thread wait on a late-scheduled thread (QUEST-GF2-010).
- Effect: lowers average main-thread time; removing waits cuts p99 spikes. With about 2 workers
  (if A1-055 holds) parallel speed-up tops out near 3x, so wide jobs mainly hide latency.
- Cost: job scheduling overhead for tiny batches; measure batch size.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3`+ `Burst 1.8`. Goal: **Throughput**, **Consistency**.

### 2. Per-job Burst float mode and optimisation level for visual-only math
```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using Unity.Mathematics;

// Visual-only: particles, procedural wobble, culling helpers. Not for networked or
// gameplay-critical simulation: keep Strict/Deterministic there.
[BurstCompile(FloatPrecision.Low, FloatMode.Fast, OptimizeFor = OptimizeFor.Performance)]
public struct WobbleJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<float4> Rest;   // xyz = position, w = phase
    public NativeArray<float4> Output;
    public float Time;
    public float Amplitude;

    public void Execute(int i)
    {
        float4 p = Rest[i];
        float s = math.sin(Time + p.w);            // Low precision: 350 ulp for sin
        float inv = math.rsqrt(math.dot(p.xyz, p.xyz) + 1e-6f);
        Output[i] = new float4(p.xyz + p.xyz * inv * (s * Amplitude), p.w);
    }
}
```
- Effect: `FloatMode.Fast` permits FMUL+FADD to FMLA fusion and reciprocal approximations;
  `FloatPrecision.Low` allows 350 ulp on sin/cos/exp/log/pow/fmod (A1-080, U5-031). No Quest
  speed-up number is published; measure the job in the Profiler on device at a pinned level.
  `OptimizeFor.Performance` per job avoids slowing every build with a global change, and makes
  sure no hot job is left on `FastCompilation` (A1-083).
- Cost: results change in the last bits; `FloatMode.Deterministic` is the one to keep for
  lockstep networking.
- Tags: `Quest 2` `Quest 3/3S` `Burst 1.8` `Unity 2021.3`-`6000.6`. Goal: **Throughput**.

### 3. Break FMA dependency chains with independent accumulators
FMLA has latency 4 and throughput 2 per cycle, so a single `float4` accumulator uses about
1/8 of peak; about 8 independent chains keep both V pipes busy (A1-068).
```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using Unity.Mathematics;

[BurstCompile(FloatMode.Fast, OptimizeFor = OptimizeFor.Performance)]
public struct WeightedSumJob : IJob
{
    [ReadOnly] public NativeArray<float4> A;
    [ReadOnly] public NativeArray<float4> B;
    public NativeArray<float> Result;              // Length 1

    public void Execute()
    {
        float4 s0 = 0, s1 = 0, s2 = 0, s3 = 0;     // 4 x float4 = the dossier's example; try 8
        int n = A.Length, i = 0;
        for (; i + 3 < n; i += 4)
        {
            s0 += A[i] * B[i];
            s1 += A[i + 1] * B[i + 1];
            s2 += A[i + 2] * B[i + 2];
            s3 += A[i + 3] * B[i + 3];
        }
        for (; i < n; i++) s0 += A[i] * B[i];
        Result[0] = math.csum((s0 + s1) + (s2 + s3));
    }
}
```
- Effect: lower average job time on reductions, dot products, skinning-like sums. Under
  `FloatMode.Strict` Burst may not reassociate a single-accumulator loop itself, so the manual
  split is what exposes the parallelism (U5-031: Fast is what allows reordering).
- Cost: summation order changes the result slightly. Check `fmla` in the Burst Inspector.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3`-`6000.6` `Burst 1.8`. Goal: **Throughput**.

### 4. Hoist divides and square roots out of hot loops
- Change: replace `x / d` with `x * invD` where `invD = math.rcp(d)` is computed once; use
  `math.rsqrt` and `math.normalize` rather than `v / math.length(v)`. Do not switch to `half`
  hoping to speed up divide: F16 FDIV/FSQRT are slower than F32 (A1-069).
- Effect: FDIV/FSQRT issue only on V0 and are not pipelined (scalar FDIV 7-10 cycles), so a
  divide-heavy loop idles V1. FRECPE runs only on V0, FRECPS on both (A1-069). No Quest timing
  published; measure.
- Cost: `math.rcp` under `FloatMode.Strict` is still a divide; the approximation needs `FloatMode.Fast` (A1-080).
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3`-`6000.6` `Burst 1.8`. Goal: **Throughput**.

### 5. Pad per-worker data to 64 bytes (false sharing)
- Change: give each worker's hot counter its own 64-byte line with an explicit-layout struct
  indexed by `[NativeSetThreadIndex]`. Paste-ready `PaddedCounter`/`CountJob` (guarded for
  `ThreadIndexCount` vs `MaxJobThreadCount`, Unity 2021.3-6000.6):
  [references/neon-costs.md](references/neon-costs.md#false-sharing-padding-job).
- Effect: all Quest cores use 64-byte lines (A1-063); two workers writing adjacent `int`s in
  one line bounce it between cores. Any two addresses 64 bytes apart sit in different lines,
  so a 64-byte stride isolates the hot field even if the array base is not 64-aligned.
- Related layout rules (A1-072, A1-073): keep hot SIMD streams as 16-byte (better 64-byte)
  aligned `float4`, avoid packed 12-byte `float3` arrays in hot loops, and do not write a struct
  field by field and read it straight back as a `float4` via `UnsafeUtility.As`/reinterpret
  (store-to-load forwarding can fail and stall). Details in
  [references/neon-costs.md](references/neon-costs.md#memory-access-rules).
- Cost: memory per counter x16. Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3`-`6000.6` `Burst 1.8`. Goal: **Throughput**, **Consistency** (fewer contention spikes).

### 6. Store `half` only where the loop is memory-bound
- Change: keep `half` in `NativeArray`s for large, streamed, bandwidth-bound data; compute in
  `float` or native FP16 in ALU-bound loops. FCVTL/FCVTN run only on V0 at 1 per 2 cycles
  (A1-070), so load-convert-compute-convert-store adds single-pipe work per element.
- Effect: halves bytes moved for memory-bound code; adds cost for ALU-bound code. Native FP16
  arithmetic needs the ARMV8A_HALFFP target (fix 7). Measure both.
- Cost: `half` storage keeps an 11-bit significand, so precision loss is visible for positions
  or large ranges. Use it only for data that tolerates it.
- Tags: `Quest 2` `Quest 3/3S` `Burst 1.8`. Goal: **Throughput**.

### 7. Burst AOT target: ARMV8A_HALFFP, drop ARMV9A
- Change: Project Settings > Burst AOT Settings > Android > Target Arm 64Bit CPU Architectures:
  select `ARMV8A_HALFFP` (keep `ARMV8A` too if you ship to non-Quest Android; Burst dispatches at
  runtime when several are selected). Deselect `ARMV9A` (A1-078, A1-079).
- Effect: every Quest core has fullfp16 and dotprod (A1-076), so HALFFP is the matching tier.
  ARMV9A (SVE2) is never selected on Quest; it adds build time and binary size only. Gains are
  limited to code that actually does `half` arithmetic; check `.8h` ops in the Inspector.
- Needs Burst ≥ 1.8 (the Android target setting arrived in 1.8.0-pre.1, A1-082). If you enable
  "Enable Armv9 Security Features for Arm64", ship Burst ≥ 1.8.25 (Android crash fix, A1-082).
- Cost: no visual change; one extra Burst variant (longer build, larger binary) if ARMV8A is kept
  alongside HALFFP.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3`-`6000.6` `Burst 1.8`. Goal: **Throughput**.
  Version detail and the HALFFP feature list: [references/burst-settings.md](references/burst-settings.md).

### 8. Neon intrinsics only for dot product or special shuffles, always with a fallback
Hand-written Neon rarely beats Burst auto-vectorisation of `float4` code; the exception is
int8 dot product (32 int8 MAC/cycle/core, A1-071). Intrinsics are compile-time gated and have
no managed fallback, so the `else` path is mandatory for the x64 Editor (A1-081). Paste-ready
`vdotq_s32` job: [references/burst-settings.md](references/burst-settings.md#neon-dot-product-job).
- Effect: lowers average job time only for int8 dot-product loops; no variance effect; no Quest
  timing published, so measure on device at a pinned level.
- Cost: two code paths to maintain; results are exact integer math, so there is no quality cost.
- Tags: `Quest 2` `Quest 3/3S` `Burst 1.8`. Goal: **Throughput**.

### 9. Leave job-worker count automatic; lower it only on measured evidence
- Default: `JobWorkerCount` = `JobWorkerMaximumCount`, and Unity adapts it on Android when
  available cores change (power saving, dual-core mode). Setting it by hand turns adaptation off
  until `JobsUtility.ResetJobWorkerCount()`; it can be lowered, never raised (A1-053, A1-054).
- The one obvious case to lower it: Quest 2 dual-core builds, where one app core is removed
  (A1-051 note, derived); test with
  `adb shell "am start -n <your.package>/com.unity3d.player.UnityPlayerActivity -e unity '-job-worker-count 1'"`
  (quoting works from bash and PowerShell). Unity 6 defaults to GameActivity
  (`com.unity3d.player.UnityPlayerGameActivity`); check the merged manifest for the activity name.
  Whether dual-core mode is worth it at all: `quest-perf:quest-levels-thermal`.
- Effect: over-subscribed workers preempt UnityMain/UnityGfxDeviceW on a 3-core set (U5-034,
  [community], stale); the fix is a variance fix, not an average one.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3`-`6000.6`. Goal: **Consistency**.

### 10. Register your own time-critical native threads with the runtime
- Change: a native plugin that owns a time-critical thread (audio, physics) registers it via
  `xrSetAndroidApplicationThreadKHR(session, XR_ANDROID_THREAD_TYPE_APPLICATION_WORKER_KHR, gettid())`
  after `xrBeginSession` (A1-042, A1-043). Sketch and the Unity OpenXR feature hook:
  [references/thread-placement.md](references/thread-placement.md#registering-native-threads).
- Whether Unity's OpenXR plugin or Meta's plugins register UnityMain/UnityGfxDeviceW is not
  documented (A1-044); read `SP=` or `ps -T` (Diagnose steps 2-3) before assuming.
- Effect: the runtime sets scheduling priority (`SP=`); placement is runtime-defined.
- Cost/side effects: needs a native plugin plus an OpenXRFeature that enables the extension; the
  runtime's response is undefined by the spec (A1-042); a real-time thread that spins can starve
  other app threads; untested with Unity's own threads (A1-044).
- Tags: `Quest 2` `Quest 3/3S` `OpenXR` [verify on device]. Goal: **Consistency**.

### 11. Do not hand-set affinity; if you must debug with it, use explicit masks
- Meta advises against manual affinity (AS-001) and says the scheduler keeps throughput high;
  bind threads only while debugging (A1-047). Unity advises keeping its defaults (A1-049), and
  Horizon OS updates change the scheduler (A1-022 walt to schedutil) and frame timing (A1-039).
- On Quest 3/3S never use `big`/`little`: all six cores are A78C at a 1.15x clock ratio, so the
  2x capacity rule may classify nothing as big (A1-050) [verify on device]. On Quest 2 a `little`
  mask puts threads on in-order A55s (A1-077) and frame time collapses.
- For a debug run: read `Cpus_allowed_list` first, then pass a hex mask inside it, e.g.
  `-platform-android-jobworker-affinity 0x70` only if the list reads `4-6`. Argument table and
  custom-activity code: [references/thread-placement.md](references/thread-placement.md#unity-thread-arguments).
- Effect: none on average when defaults are kept; a mis-set mask raises p95/p99 (A55 placement
  on Quest 2) or silently fails (Quest 3/3S aliases).
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3`-`6000.6`. Goal: **Consistency** (by not doing it).

## Verify

- Pin CPU level (L4 VR; note L3 cap with passthrough on Quest 3/3S) and refresh rate; run the
  same scene 3+ times per variant, 2-5 min each for code-level changes. For fixes 1 and 9, run a
  20-30 min session because worker contention and thermal state interact.
- Burst fixes 2-6: the job's ms in a Development-build Profiler capture (or Perfetto slice)
  should drop; convert with the cycle table (1 M cycles about 0.52 ms on Quest 3/3S at L4,
  about 0.68 ms on Quest 2 at L4, derived from A1-026). No published expected gain: report
  what you measured, with device, Unity, Burst version and level.
- Fix 1: UnityMain busy time per frame in Perfetto falls; the Perfetto gap pattern
  (UnityMain sleeping mid-frame) disappears; OVR Metrics stale frames per minute and p99 CPU
  frame time fall.
- Fixes 9-11: `ps -T` shows no app thread outside `Cpus_allowed_list`; Perfetto shows fewer
  migrations of UnityMain; p95/p99 frame time tightens, average may not move.
- Fix 7: Burst Inspector shows `.8h` FP16 ops in `half` code for the HALFFP target; binary size
  drops after removing ARMV9A.

## Pitfalls and myths

- **"Quest 3 is 2 big + 4 little (A715/A510)."** Wrong: 6x Cortex-A78C, 4 @ 2.36 + 2 @ 2.05 GHz
  (ARM-C1, A1-014). The "slow" cluster is still a big core.
- **"Quest 2 has 2.84 GHz."** Apps never get it; max 2.42 GHz at Boost-only L8, default 1.48 GHz
  (A1-003). Budget the main thread at the level clock, not the spec sheet.
- **`SystemInfo.processorCount` = usable cores.** Not established: Geekbench as a 2D app sees all
  8 cores on Quest 2, Meta's docs imply 3 for VR apps (ARM-C7). Log both and read `Cpus_allowed_list`.
- **App core IDs on Quest 3/3S.** GDC 2026 auto-captions are self-contradictory: the trace shows
  the app on cores 3-5 (the top three on a 6-core part), but the speakers say the bottom half is
  app and the top three are system (QUEST-GF2-010); A1-050 separately guesses cpu2-5 is the
  2.36 GHz cluster. No published mask. Read `Cpus_allowed_list` [verify on device].
- **Geekbench scores size VR budgets.** They run outside the level system and vary 573-931
  single-core on identical Quest 3 silicon (A1-021). Use on-device frame timing at a pinned level.
- **`vrapi_SetPerfThread` / VrApi thread advice.** VrApi is unsupported since Aug 31, 2022; the
  OpenXR equivalent is `XR_KHR_android_thread_settings` (A1-046, A1-042). Conflict ARM-C19: the
  2019 blog implies `TA=`/`SP=` are VrApi-only, the 2025 logcat page still documents them for
  OpenXR. Check `adb logcat -s VrApi` on your build.
- **"Set -job-worker-count to cores minus one."** From Quest 1 era posts (U5-034, [community]);
  on Quest it can only lower the count and it disables automatic adaptation (A1-053, A1-054).
- **"half makes math faster on the CPU."** Not for divide/sqrt (slower in F16) and not when
  every element pays single-pipe FCVT conversions (A1-069, A1-070).
- **"Enable ARMV9A for newer chips."** No Quest core has SVE/SVE2; it is dead code (A1-075, A1-079).
- **ARMV8A_HALFFP feature set.** arm-mobile-hw.md A1-079 records it as undocumented; unity.md
  U5-029 and a 2026-09-24 re-read of the Burst page list fullfp16, dotprod, crypto, crc, rdm,
  lse ("Cortex A75/A55 and later"). Trust the Burst page; confirm in the Inspector.
- **Render-thread affinity arguments work reliably.** A 2022.3 phone report saw inconsistent
  placement (A1-052, [community]); Unity says some devices and OS versions ignore them (A1-051).
- **Unity 2021.3 with Burst 1.6/1.7** has no Arm64 target setting; upgrade to 1.8.x (A1-082).
- Owned elsewhere, one line each: never ship with Multithreaded Rendering off, and Graphics Jobs
  Legacy mode from 2022.3.35f1: `unity-perf:unity-cpu-scripting` (A1-058, A1-061).

## Sources

All accessed 2026-09-24.
- https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ [doc]: 3 app cores on Quest 2, dual-core mode, parallel beats clock (A1-004, A1-057, ARM-GF1-001)
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]: level clocks, passthrough caps (A1-003, A1-005, A1-018, A1-026)
- https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ [doc]: `TA=`/`SP=` fields, no manual affinity (AS-001)
- https://developers.meta.com/horizon/blog/ovr-metrics-tool-vrapi-what-do-these-metrics-mean/ [doc]: 2019 affinity advice, VrApi-era fields (A1-011, A1-046, A1-047, A1-048)
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ [doc]: Perfetto CPU scheduling (A1-084)
- https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ [doc]: GDC 2026 Quest 3 trace, cores 3-5, wake-up chain (QUEST-GF2-010)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ [doc]: CPU L overlay (A1-085)
- https://developers.meta.com/horizon/documentation/native/android/mobile-power-overview/ [doc]: two cores at 1 GHz beat one at 2 GHz, stale page (A1-040)
- https://registry.khronos.org/OpenXR/specs/1.1/html/xrspec.html#XR_KHR_android_thread_settings [doc]: thread registration (A1-042)
- https://raw.githubusercontent.com/meta-quest/Meta-OpenXR-SDK/main/Samples/SampleXrFramework/Src/XrApp.cpp [doc]: Meta sample registers threads (A1-043)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/changelog/CHANGELOG.html [doc]: no registration statement (A1-044)
- https://docs.unity3d.com/6000.0/Documentation/Manual/android-thread-configuration.html [doc]: 2x capacity rule, thread arguments (A1-049, A1-050, A1-051)
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerCount.html [doc]: automatic adaptation (A1-053)
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerMaximumCount.html [doc]: lower only (A1-054)
- https://web.archive.org/web/20260214200619/https://communityforums.atmeta.com/discussions/dev-quest/unity-quest-3-multithreaded-performance/1132006 [community]: 2 workers on Quest 3 (A1-055)
- https://thegamedev.guru/unity-performance/job-system-excessive-multithreading/ [community]: Quest 1 over-subscription, stale (U5-034)
- https://discussions.unity.com/t/android-thread-configuration-render/1731103 [community]: inconsistent render-thread affinity (A1-052)
- https://documentation-service.arm.com/documentation/102160/latest [doc]: A78 SWOG, FMLA/FDIV/FCVT/SDOT, alignment, forwarding (A1-066, A1-068 to A1-074)
- https://documentation-service.arm.com/documentation/swog011050/latest [doc]: A77 SWOG (A1-067, A1-068, A1-075)
- https://documentation-service.arm.com/documentation/epm128372/latest [doc]: A55 SWOG, 64-byte lines, in-order (A1-063, A1-077)
- https://documentation-service.arm.com/documentation/102226/0002/Functional-description/L2-memory-system/About-the-L2-memory-system [doc]: A78C L2 lines (A1-063, A1-064)
- https://browser.geekbench.com/v6/cpu/19091540 and https://browser.geekbench.com/v6/cpu/19064415 [measured]: topology, MIDR, ISA flags (A1-002, A1-013, A1-076)
- https://browser.geekbench.com/v6/cpu/19157033 [measured]: Quest 3/3S ISA flags (A1-076)
- https://browser.geekbench.com/search?k=v6_cpu&q=Oculus+Quest+3 [measured]: Geekbench spread (A1-021)
- https://en.wikipedia.org/wiki/List_of_Qualcomm_Snapdragon_systems_on_chips [community]: core types (A1-001, A1-014)
- https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf [doc]: "4 + 2 performance cores" (A1-012, ARM-C1)
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-projects.html [doc]: Arm64 targets, HALFFP feature list (A1-078, A1-079, U5-029)
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstcompile.html [doc]: FloatMode, FloatPrecision (A1-080, U5-031)
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-aot-settings.html [doc]: OptimizeFor, AOT settings (A1-083)
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/api/Unity.Burst.Intrinsics.Arm.Neon.html [doc]: Neon gating (A1-071, A1-081)
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/changelog/CHANGELOG.html [doc]: Burst Arm history, 1.8.25 fix (A1-082)
