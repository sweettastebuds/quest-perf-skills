# Burst settings for Quest (Arm64)

Companion to `arm-mobile-hw-perf:xr2-cpu-threads-neon`. All sources accessed 2026-09-24.
Job and Burst usage patterns (what to put in jobs, scheduling, NativeContainer choice) are
owned by `unity-perf:unity-cpu-scripting`.

## Burst version per Unity line

| Unity | Newest Burst | Note | Source |
|---|---|---|---|
| 2021.3 | 1.8.26 | projects pinned to 1.6/1.7 lack the Arm64 target setting: upgrade | U5-030, A1-082 |
| 2022.3 | 1.8.29 | | U5-030 |
| 6000.0+ | 1.8.30 | 1.8.30 released 2026-07-06 (changelog) / published 2026-07-21 (registry) | U5-030, A1-082 |
| 6000.6 | built-in module | check that the module and any explicit package pin do not conflict | U5-030 |

Arm milestones (A1-082): 1.5.0-pre.1 (2020-11-26) RDMA, crypto and dotprod intrinsics;
1.6.0-pre.1 (2021-04-14) experimental `half`, half-precision Neon, full Armv8.2 Neon;
1.8.0-pre.1 (2022-05-06) Android "Target Arm64 CPU" setting and experimental Armv9 SVE2 target;
since 1.8.0 Burst honours "Enable Armv9 Security Features for Arm64" (PAC + BTI); 1.8.25
(2025-09-16) fixed an Android crash with that flag on, so ship ≥ 1.8.25 if it is enabled.

## Arm64 AOT targets

Setting: Project Settings > Burst AOT Settings > (Android) Target Arm 64Bit CPU Architectures.
With several selected, Burst generates a runtime dispatch that picks the matching variant (A1-078).

| Target | Features (Burst page) | On Quest |
|---|---|---|
| `ARMV8A` (default) | basic Armv8-A | runs, leaves FP16/dotprod codegen unused |
| `ARMV8A_HALFFP` | ARMV8A + fullfp16, dotprod, crypto, crc, rdm, lse; "Cortex A75/A55 and later" | matches every Quest core (A1-076): select it |
| `ARMV9A` | ARMV8A_HALFFP + SVE2; experimental; "Cortex X2/A710/A510 and later" | never selected on Quest 2/3/3S: deselect (A1-079) |

Conflict note: arm-mobile-hw.md A1-079 records the HALFFP feature set as undocumented; unity.md
U5-029 lists it, and the Burst building-projects page re-read on 2026-09-24 confirms the list
above. Still confirm in the Burst Inspector: `.8h` vector ops in `half` code, `sdot`/`udot` where
you use dotprod. Any gain is limited to code that does half-precision arithmetic or dot products.
Keep `ARMV8A` selected as well only if the same APK targets non-Quest Android devices.

## Float settings

| Setting | Values | Effect | Source |
|---|---|---|---|
| `FloatMode` | `Default` (= `Strict`), `Strict`, `Fast`, `Deterministic` | Fast permits reordering, FMUL+FADD to FMLA fusion, reciprocal approximations; Deterministic targets cross-platform determinism (64-bit only, flushes denormals) | A1-080, U5-031 |
| `FloatPrecision` | `Standard` (= `Medium`) 3.5 ulp, `High` 1 ulp, `Low` 350 ulp | applies to sin, cos, exp, log, pow, fmod | A1-080, U5-031 |

Per job: `[BurstCompile(FloatPrecision.Medium, FloatMode.Fast)]`. Use Fast (and Low where the
eye cannot tell) for visual-only math: particles, procedural animation, culling helpers. Keep
Strict or Deterministic for gameplay-critical or networked simulation (A1-080 note). No Quest
speed-up number is published; look for `fmla` in the Inspector and time on device (U5-031).
Why it matters more on Quest cores: FDIV/FSQRT serialise on V0 (A1-069).

## OptimizeFor

Global "Optimize For" defaults to `Balanced`; `Performance` optimises for speed;
`FastCompilation` skips vectorisation, inlining and loop optimisations. A per-job `OptimizeFor`
overrides the global setting (A1-083). Mark hot jobs
`[BurstCompile(OptimizeFor = OptimizeFor.Performance)]` rather than changing the global setting,
and grep the project for `OptimizeFor.FastCompilation` left over from iteration before release.

## Neon intrinsics

Gates (compile-time, evaluated for the target being compiled; no managed fallback, A1-081):

| Property | True when |
|---|---|
| `Arm.Neon.IsNeonSupported` | any Arm64 target |
| `Arm.Neon.IsNeonArmv82FeaturesSupported` | Crypto && DotProd && RDMA |
| `Arm.Neon.IsNeonCryptoSupported` | crypto |
| `Arm.Neon.IsNeonDotProdSupported` | dotprod (ARMV8A_HALFFP or higher) |
| `Arm.Neon.IsNeonRDMASupported` | RDMA |

Rules: always write the `else` path in plain `Unity.Mathematics`/C# (the x64 Editor and
non-matching targets take it). Hand-written Neon rarely beats Burst's auto-vectorisation of
`float4` code; use it for dot product or specific shuffles (A1-081 note).

### Neon dot-product job

int8 dot product via SDOT (2 per cycle, 32 int8 MAC/cycle/core, A1-071). Two accumulators to
cover the 2-cycle latency. Burst 1.8, Unity 2021.3-6000.6. Untested on device.

```csharp
using Unity.Burst;
using Unity.Burst.Intrinsics;
using Unity.Collections;
using Unity.Jobs;

[BurstCompile(OptimizeFor = OptimizeFor.Performance)]
public struct Int8DotJob : IJob
{
    [ReadOnly] public NativeArray<sbyte> A;   // Length must be a multiple of 16
    [ReadOnly] public NativeArray<sbyte> B;
    public NativeArray<int> Result;           // Length 1

    public void Execute()
    {
        int total = 0;
        if (Arm.Neon.IsNeonDotProdSupported)
        {
            NativeArray<v128> va = A.Reinterpret<v128>(1);
            NativeArray<v128> vb = B.Reinterpret<v128>(1);
            v128 acc0 = new v128(0), acc1 = new v128(0);
            int i = 0;
            for (; i + 1 < va.Length; i += 2)
            {
                acc0 = Arm.Neon.vdotq_s32(acc0, va[i], vb[i]);
                acc1 = Arm.Neon.vdotq_s32(acc1, va[i + 1], vb[i + 1]);
            }
            if (i < va.Length) acc0 = Arm.Neon.vdotq_s32(acc0, va[i], vb[i]);
            total = Arm.Neon.vaddvq_s32(Arm.Neon.vaddq_s32(acc0, acc1));
        }
        else
        {
            for (int i = 0; i < A.Length; i++) total += A[i] * B[i];
        }
        Result[0] = total;
    }
}
```
Check: Burst Inspector for the ARMV8A_HALFFP variant shows `sdot`; the ARMV8A variant takes the
scalar path (dotprod is not in the base target). If only ARMV8A is selected, the Neon branch is
compiled out on every Quest.

## Release checklist

- Burst ≥ 1.8 (≥ 1.8.25 with Armv9 security features on).
- Arm64 targets: `ARMV8A_HALFFP` on, `ARMV9A` off.
- Hot jobs: `OptimizeFor.Performance`; none left on `FastCompilation`.
- Visual-only jobs: `FloatMode.Fast` (+ `FloatPrecision.Low` where acceptable); simulation jobs
  that must match across devices: `Strict` or `Deterministic`.
- Every Neon intrinsic has a gated `else` path.
- Job timings re-measured on Quest 2 and Quest 3/3S at a pinned CPU level after each change.

## Sources

- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-projects.html [doc]: targets, HALFFP features, dispatch (A1-078, A1-079, U5-029; re-read 2026-09-24), accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/building-aot-settings.html [doc]: AOT settings, OptimizeFor (A1-078, A1-083), accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstcompile.html [doc]: FloatMode, FloatPrecision (A1-080, U5-031), accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/api/Unity.Burst.Intrinsics.Arm.Neon.html [doc]: Neon gates, dotprod (A1-071, A1-081), accessed 2026-09-24
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/changelog/CHANGELOG.html [doc]: Arm history, 1.8.25 fix (A1-082), accessed 2026-09-24
- https://packages.unity.com/com.unity.burst [doc]: Burst per Unity line (U5-030), accessed 2026-09-24
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc]: Burst built-in module in 6.6 (U5-030), accessed 2026-09-24
- https://documentation-service.arm.com/documentation/102160/latest [doc]: SDOT, FDIV, FCVT costs (A1-069 to A1-071), accessed 2026-09-24
- https://browser.geekbench.com/v6/cpu/19091540 and https://browser.geekbench.com/v6/cpu/19157033 [measured]: neon-fp16 and neon-dotprod on both SoCs (A1-076), accessed 2026-09-24
