# A77 / A78C cost table for Burst code on Quest

Companion to `arm-mobile-hw-perf:xr2-cpu-threads-neon`. All sources accessed 2026-09-24.
Arm publishes no A78C-specific Software Optimization Guide; the A78 SWOG r1p2 stands in for
Quest 3/3S (A1-066). Quest 2 app threads run on Cortex-A77 (A77 SWOG); the A55 only matters if
a thread lands on the system cluster.

## Cores

| | Quest 2 app cores | Quest 3/3S | Quest 2 system cores |
|---|---|---|---|
| Core | Cortex-A77 (gold, 2.42 GHz max, 1.48 GHz at L4) | Cortex-A78C r0p2 (4 @ 2.36, 2 @ 2.05 GHz; 1.92 GHz at L4) | Cortex-A55 r1p0 (1.80 GHz) |
| Pipeline | OoO, 6 MOPs / 10 uOPs dispatch, 12 issue pipes | OoO, 6 MOPs / 12 uOPs dispatch, 13 pipes | in-order, dual-issue, 8-stage int, 10-stage FP/NEON |
| FP/ASIMD pipes | 2 (V0, V1), 128-bit | 2 (V0, V1), 128-bit | |
| Load pipes | fewer than A78 (12 pipes total) | 2 load/store + 1 load-only | |
| ISA | Armv8.2-A + RAS, v8.3 LDAPR, v8.4 dotprod | Armv8.2-A, v8.3 LDAPR + PAC, v8.4 dotprod, v8.5 SSBS, v8.6 enhanced PAC; AArch32 at EL0 only | Armv8.2 + dotprod |
| SVE/SVE2 | no | no | no |
| Source | A1-001, A1-003, A1-065, A1-067, A1-075 | A1-013, A1-014, A1-066, A1-075 | A1-002, A1-077 |

A78 pipe detail (A1-066): 2 branch, 2 single-cycle integer, 2 single/multi-cycle integer,
2 FP/ASIMD (V0, V1), 2 load/store, 1 load-only, 2 store-data; at most 2 uOPs per cycle to each
V pipe, up to 6 to the load pipes. Derived consequence (A1-067): load-heavy Burst loops (gathers,
SoA streaming) should gain the most going from Quest 2 to Quest 3.

Geekbench ISA line on both SoCs: neon, aes, sha1, sha2, neon-fp16, neon-dotprod; no SVE, no
i8mm (A1-076, [measured]).

## Instruction costs

| Instruction class | Latency | Throughput | Pipes | Core | Source |
|---|---|---|---|---|---|
| ASIMD FP FMLA (F32) | 4 (2 with accumulator forwarding) | 2 / cycle | V0, V1 | A77, A78 | A1-068 |
| Scalar FP32 FDIV | 7-10 cycles | not fully pipelined | V0 only | A77, A78 | A1-069 |
| Q-form F32 vector FDIV | | 1/9 to 1/7 per cycle | V0 only | A78 | A1-069 |
| Q-form F16 vector FDIV | 10-13 cycles | 1/13 to 1/10 per cycle | V0 only | A78 | A1-069 |
| Q-form F16 FSQRT | slower than F32 FSQRT | | V0 only | A78 | A1-069 |
| FRECPE (reciprocal estimate) | | | V0 only | A78 | A1-069 |
| FRECPS (Newton step) | | | V0, V1 | A78 | A1-069 |
| FCVTL / FCVTN (F16 to/from F32, Q-form) | 4 | 1 per 2 cycles | V0 only | A78 | A1-070 |
| SDOT / UDOT | 2 (1 with accumulator forwarding) | 2 / cycle | V0, V1 | A78 | A1-071 |
| SDOT / UDOT | 2 | 2 / cycle | | A77 | A1-071 |

Blank cells: not given in the dossier; read the SWOG PDF or measure.

Derived throughput (A1-068, A1-071):
- Peak FP32 per core = 2 FMLA x 4 lanes x 2 FLOP = 16 FLOP/cycle: about 23.7 GFLOPS on Quest 2 at
  L4 (1.48 GHz), 30.7 GFLOPS on Quest 3/3S at L4 (1.92 GHz). Not a sustained number.
- Saturating FMLA needs latency x throughput = about 8 independent chains in flight.
- SDOT: 16 int8 MACs per instruction x 2 pipes = 32 int8 MAC/cycle/core.

Cycle-to-time conversion at L4 (A1-026, derived): Quest 2 1 M cycles about 0.68 ms;
Quest 3/3S about 0.52 ms. Main-thread budget per frame at L4: 72 Hz 20.6 M / 26.7 M, 90 Hz
16.4 M / 21.3 M, 120 Hz 12.3 M / 15.9 M (Quest 2 / Quest 3/3S). Quest 3/3S with passthrough
(CPU L3, 1.65 GHz): about 22.9 M at 72 Hz (A1-018). The main thread cannot use the whole frame;
it needs slack for render-thread and compositor handoff (A1-026 note).

## Caches

| Level | A77 (Quest 2) | A78C (Quest 3/3S) | Configured on the SoC |
|---|---|---|---|
| Line size | 64 B | 64 B | same (A1-063) |
| L1 I / D | 64 KB / 64 KB (Arm product page) | 32 or 64 KB / 32 or 64 KB | not published |
| L2 (private) | 256-512 KB | 256 or 512 KB, 8-way, strictly inclusive of L1D | not published |
| L3 (DynamIQ cluster) | optional 512 KB-4 MB | up to 8 MB in a big-core-only cluster (DSU-MP135) | not published |
| System cache | | Qualcomm: 8 MB "system cache (LLC)" (SoC-level, distinct from DSU L3) | A1-012 |

Sources: A1-064, A1-065, A1-012. Phone-review SD865 cache figures are not repeated because the
source is unreachable (A1-065 note). Whether XR2 Gen 2 is one DSU cluster or two is unknown.

## Memory access rules

- **Unaligned access (A78, A1-072):** penalties only for loads crossing a 64-byte line, Q-word
  (16-byte) loads not 4-byte aligned, and stores crossing a 32-byte boundary. The A77 SWOG lists
  the same 64-byte line-crossing case. Burst advice: 16-byte (better 64-byte) alignment for hot
  `float4`/matrix streams; avoid packed 12-byte `float3` arrays in hot SIMD loops.
- **Store-to-load forwarding (A78, A1-073):** works only if the load starts at the start or middle
  address of the older store; a load wider than 8 bytes can take data from at most 2 stores
  (each covering one half); a load of 8 bytes or less from only 1 store. Writing a struct field
  by field and reading it back at once as a `float4` (or via `UnsafeUtility.As`/reinterpret)
  can miss forwarding and stall (derived).
- **False sharing (A1-063):** pad per-worker hot data to 64-byte strides.
- **Copy and clear (A1-074):** the A78 SWOG recommends unrolled non-writeback LDP/STP Q-pairs
  for copy and `DC ZVA` for zeroing. Whether `UnsafeUtility.MemCpy/MemClear` or bionic memcpy
  use these on Quest is undocumented: prefer the engine/libc routines over byte loops and check
  hot copies in the Burst Inspector.
- **`half` storage (A1-070):** halves memory traffic but adds V0-only FCVT per element; a win
  only for memory-bound loops.

## False-sharing padding job

All Quest cores use 64-byte lines (A1-063). One padded counter per job-worker thread index;
compiles on Unity 2021.3 through 6000.6 with Burst 1.8.

```csharp
using System.Runtime.InteropServices;
using Unity.Burst;
using Unity.Collections;
using Unity.Collections.LowLevel.Unsafe;
using Unity.Jobs;
using Unity.Jobs.LowLevel.Unsafe;

[StructLayout(LayoutKind.Explicit, Size = 64)]    // one 64-byte line per hot counter
public struct PaddedCounter { [FieldOffset(0)] public int Value; }

[BurstCompile]
public struct CountJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<float> Values;
    [NativeDisableParallelForRestriction] public NativeArray<PaddedCounter> PerThread;
    [NativeSetThreadIndex] int m_ThreadIndex;

    public void Execute(int i)
    {
        if (Values[i] > 0f)
        {
            var c = PerThread[m_ThreadIndex];
            c.Value++;
            PerThread[m_ThreadIndex] = c;
        }
    }
}

public static class CountJobAlloc
{
    public static NativeArray<PaddedCounter> Create(Allocator a) =>
#if UNITY_2022_2_OR_NEWER
        new NativeArray<PaddedCounter>(JobsUtility.ThreadIndexCount, a);
#else
        new NativeArray<PaddedCounter>(JobsUtility.MaxJobThreadCount, a);
#endif
}
```

## Measuring what is not published

No script ships for these (OUTLINE decision 33: no dossier finding validates an implementation
on Quest). Methods, from the dossier's Known unknowns:

1. **Cache sizes.** First try `adb shell cat /sys/devices/system/cpu/cpu0/cache/index*/size`
   (often absent on arm64 Android). Otherwise a pointer-chase latency sweep: a Burst job walking
   a random cyclic permutation of 64-byte-spaced indices, working set 16 KB to 64 MB in powers
   of two, timed per step on one app core at a pinned CPU level. L1, L2, L3 and system-cache
   sizes show as steps in ns per load.
2. **DRAM data rate.** A STREAM-style copy/triad Burst job at a pinned CPU level, while reading
   `Mem=` from `adb logcat -s VrApi` (Meta's page shows two example values, 2092 and 1804 MHz,
   neither tied to a headset, ARM-C24). Bandwidth interpretation belongs to
   `arm-mobile-hw-perf:xr2-bandwidth-power`.
3. **Instruction cost in context.** Time the real job on device in a Development build at a
   pinned level, 3+ runs, and convert to cycles with the clock of the granted level. Compare
   against the table above to see whether the loop is latency-bound (single chain), V0-bound
   (divide, sqrt, conversions) or load-bound.
4. **Geekbench is not a substitute:** it runs as a 2D app outside the level system and varies
   573-931 single-core on identical Quest 3 silicon (A1-021).

## Sources

- https://documentation-service.arm.com/documentation/102160/latest [doc] (A78 SWOG r1p2): A1-066, A1-068 to A1-074, accessed 2026-09-24
- https://documentation-service.arm.com/documentation/swog011050/latest [doc] (A77 SWOG): A1-067, A1-068, A1-075, accessed 2026-09-24
- https://documentation-service.arm.com/documentation/epm128372/latest [doc] (A55 SWOG): A1-063, A1-077, accessed 2026-09-24
- https://documentation-service.arm.com/documentation/102226/0002/Functional-description/Introduction/About-the-core [doc]: A1-064, accessed 2026-09-24
- https://documentation-service.arm.com/documentation/102226/0002/Functional-description/L1-memory-system/About-the-L1-memory-system [doc]: A1-064, accessed 2026-09-24
- https://documentation-service.arm.com/documentation/102226/0002/Functional-description/L2-memory-system/About-the-L2-memory-system [doc]: A1-063, accessed 2026-09-24
- https://documentation-service.arm.com/documentation/102226/0002/Functional-description/Introduction/Supported-standards-and-specifications [doc]: A1-075, accessed 2026-09-24
- https://www.arm.com/products/silicon-ip-cpu/cortex-a/cortex-a78c [doc]: A1-064, accessed 2026-09-24
- https://www.arm.com/products/silicon-ip-cpu/cortex-a/cortex-a77 [doc]: A1-065, accessed 2026-09-24
- https://docs.qualcomm.com/doc/87-73689-1/87-73689-1_REV_A_Snapdragon_XR2_Gen_2_Platform_Product_Brief.pdf [doc]: A1-012, accessed 2026-09-24
- https://browser.geekbench.com/v6/cpu/19091540 , https://browser.geekbench.com/v6/cpu/19064415 , https://browser.geekbench.com/v6/cpu/19157033 [measured]: A1-002, A1-013, A1-076, accessed 2026-09-24
- https://browser.geekbench.com/search?k=v6_cpu&q=Oculus+Quest+3 [measured]: A1-021, accessed 2026-09-24
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]: A1-005, A1-018, A1-026, accessed 2026-09-24
- https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ [doc]: `Mem=` values, ARM-C24, accessed 2026-09-24
