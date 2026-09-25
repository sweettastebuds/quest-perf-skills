---
name: gles-versions-unity-output
description: "OpenGL ES 3.0/3.1/3.2 on Quest 2 and Quest 3/3S: what the drivers expose, per-device limits (SSBOs, samples), what Unity emits for GLES (#version, pragma targets, SHADER_API macros), Player settings for OpenGLES3, Unity 6.6's ES 3.1 floor, and the deprecated Oculus XR GLES path. Use when a project ships on GLES, or when a shader or feature behaves differently on GLES than on Vulkan."
---

# GLES versions and what Unity emits on Quest

Goal: **Consistency** first (the build must run the API and ES level you think it runs, and shaders must compile on the lowest headset), then **Throughput** (ES level sets URP's light-loop size and which compute paths exist). Correctness gates both: a shader that fails or falls back on Quest 2 is a hitch or a missing effect, not a tuning problem.

Scope: Unity 2021.3 (URP 12) through 6000.6 (URP 17), Unity's `OpenGLES3` target on the Quest ES 3.2 driver. Meta calls GLES "legacy" with no new features; Vulkan is recommended (G1-028). This skill does not argue the API choice.

## When to use / when not

Use when:
- The project ships or tests on OpenGLES3 and you need the real driver level, limits or driver string for a headset.
- A shader compiles or behaves differently on GLES than on Vulkan, or only fails on Quest 2 (SSBO counts, `#pragma target`, `SHADER_API_*` branches).
- Upgrading to Unity 6.6 on GLES: the ES 3.1 floor, "Use OpenGL ES 3.0 shaders", the 16 vs 32 light ceiling.
- Setting Player settings for GLES: Auto Graphics API, Require ES3.x, GPU skinning mode.
- Auditing old advice that mentions GLES2 or the Oculus XR plugin's GLES path.

Do not use; go to the sibling:
- "Should we ship GLES or Vulkan", UUM-93226, the API A/B protocol, GLES capture tooling: `gles3-perf:gles-vs-vulkan`.
- Program binaries, blob cache, WarmUp on GLES, `mediump` / REAL_IS_HALF emission, the 31-varying and Adreno instruction cliffs: `gles3-perf:gles-shader-binaries`.
- Per-extension matrix, OVR_multiview2, QCOM foveation, framebuffer fetch: `gles3-perf:gles-extensions-multiview`.
- glClear / glInvalidateFramebuffer / MSRTT: `gles3-perf:gles-tile-load-store`.
- GL state and UBO overhead, Low Overhead Mode, compute/graphics interleave: `gles3-perf:gles-driver-overhead`.
- What exists in which Unity version generally: `unity-perf:unity-version-matrix`. URP asset settings (MSAA, render path): `unity-perf:unity-urp-settings`.
- Cause of low FPS still unknown: `quest-perf:quest-triage`.

## Diagnose first

Confirm what is actually running before touching shaders. Every A/B and every bug report needs these five facts.

1. **Driver string** (G2-082). Record with every capture.

   ```sh
   adb shell "dumpsys SurfaceFlinger | grep GLES"
   # expect e.g.: GLES: Qualcomm, Adreno (TM) 740, OpenGL ES 3.2 V@0837.0.7
   ```

2. **API, ES level and limits the player sees.** Drop this on any object in the first scene of a development build and read `adb logcat -s Unity`. Compiles on 2021.3+; the URP line needs the URP runtime assembly referenced.

   ```csharp
   using UnityEngine;
   using UnityEngine.Rendering;

   public sealed class GlesCapsLogger : MonoBehaviour
   {
       void Start()
       {
           Debug.Log(
               $"[GlesCaps] api={SystemInfo.graphicsDeviceType} " +
               $"ver='{SystemInfo.graphicsDeviceVersion}' gpu='{SystemInfo.graphicsDeviceName}' " +
               $"shaderLevel={SystemInfo.graphicsShaderLevel} minGLES={Graphics.minOpenGLESVersion} " +
               $"compute={SystemInfo.supportsComputeShaders} " +
               $"ssboVS={SystemInfo.maxComputeBufferInputsVertex} " +
               $"ssboFS={SystemInfo.maxComputeBufferInputsFragment} " +
               $"ssboCS={SystemInfo.maxComputeBufferInputsCompute} " +
               $"model='{SystemInfo.deviceModel}'");
           // URP light ceiling actually in use (16 = ES 3.0 low-end path, 32 = ES 3.1+/Vulkan mobile).
           Debug.Log($"[GlesCaps] urpMaxAdditionalLights=" +
               $"{UnityEngine.Rendering.Universal.UniversalRenderPipeline.maxVisibleAdditionalLights}");
       }
   }
   ```

   Read: `api=OpenGLES3` (not Vulkan: Auto Graphics API may have picked Vulkan first, G1-016); `ver` should say `OpenGL ES 3.2`; `ssboVS/ssboFS` should read 4 on Quest 2 and 12 on Quest 3 if Unity maps these properties to the GL storage-block limits [verify on device].

3. **Manifest floor.** On 6.6 an OpenGLES3 build must declare ES 3.1 (G1-017):

   ```sh
   aapt2 dump xmltree --file AndroidManifest.xml app.apk | grep -i glEsVersion
   # 6.6+: glEsVersion ... 0x30001 (= 0x00030001). The requirement is only added when Auto Graphics API is on or OpenGLES3 is listed (G1-016).
   ```

4. **What the compiler emitted.** Shader Inspector, "Compile and show code" with GLES3 selected; for `.compute` assets, "Show compiled code". Read the first line (`#version 300 es` / `310 es` / `320 es`) and the `precision` statements (GLES3-GF1-007, GLES3-GF2-005). On device, `glShaderSource` in a RenderDoc Meta Fork GL capture shows the same (tool owned by `gles3-perf:gles-vs-vulkan`).

5. **Shader failures on Quest 2 only.** `adb logcat -s Unity` (PowerShell: `adb logcat -s Unity | Select-String -Pattern shader`) while loading each scene; look for compile/link errors or fallback messages from shaders that bind SSBOs in vertex or fragment stages (KU-33 method). No published list says which Unity features exceed 4 blocks.

## Key numbers

| Number | Value | Applies to | Source |
|---|---|---|---|
| Highest ES / GLSL level | ES 3.2, GLSL ES 3.20, ES 3.1+AEP | `Quest 2` `Quest 3` `GLES` | G1-001, G1-002, G1-013 [measured] |
| GL_MAX_SAMPLES | 4 (no 8x MSAA on GLES) | `Quest 2` `Quest 3` `GLES` | G1-007 / G2-035 [measured] |
| Vertex / fragment SSBO blocks | 4 vs 12 | `Quest 2` vs `Quest 3` `GLES 3.1+` | G1-005 [measured] [verify on device] |
| Compute SSBO blocks / SSBO bindings | 24 vs 36 / 24 vs 36 | `Quest 2` vs `Quest 3` | GLES3-GF2-001, G1-005 [measured] |
| Compute invocations / shared memory | 1024 / 32768 B, both headsets | `GLES 3.1+` | G1-006 [measured] |
| Program / shader binary formats | 1 / 0 (every program compiled on device) | `Quest 2` `Quest 3` | G1-008 / G3-008 [measured] |
| URP MAX_VISIBLE_LIGHTS | 16 with `SHADER_API_GLES30` on mobile; 32 on GLES 3.1+ and Vulkan mobile | `URP 14-17` | G1-020 [doc] |
| 6.6 manifest floor | `glEsVersion 0x00030001`, irreversible | `Unity ≥ 6000.6` | G1-017, U1-094 [doc] |
| Driver builds | Quest 2 V@0690.0 (12/13/22, last public report); Quest 3/3S V@0837.0.7 (01/12/26) | per OS build | G2-082 [measured] |
| Quest 3 vs 3S GPU clock | 690 vs 492 MHz (about 71%) per ovrgpuprofiler page; **conflict**: levels table says L5 = 599 MHz, and 492 MHz equals Quest 3/3S GPU L3 | `Quest 3/3S` | G3-081 [doc] vs ARM-C3 [doc]; read `Clocks / Second` or GPU F on device |

Full per-device GL_MAX table, all driver strings and the per-Unity-version settings table: read [references/gles-limits.md](references/gles-limits.md) when you need a limit not listed above, when a report cites an unfamiliar driver build, or when mapping a setting across Unity versions.

`#pragma target` to GLES level (G1-021, Unity 6000.3 manual; same table since 2021.3):

| `#pragma target` | GLES level | Adds |
|---|---|---|
| 3.0 / 3.5 | ES 3.0 | - |
| 4.0 | ES 3.1 or 3.1+AEP | geometry |
| 4.5 | ES 3.1 | compute, randomwrite, msaatex |
| 4.6 | ES 3.1+AEP | cubearray, tessellation |
| 5.0 | ES 3.1+AEP | compute + tessellation |

## Fixes, ranked by payoff ÷ effort

### 1. Pin the API list; never measure with Auto Graphics API on (Consistency)

With Auto on, Unity tries Vulkan, then GLES 3.2, 3.1, 3.0 (G1-016). You can ship or profile a different API than you think. Turn Auto off and list exactly one API per test build; for shipping, list the API you validated first.

Editor utility (2021.3+; guards the 6.6 property change so it compiles on every version):

```csharp
#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class QuestGlesPlayerSettings
{
    const BuildTarget Android = BuildTarget.Android;

    [MenuItem("Tools/Quest GLES/Pin OpenGLES3 only")]
    static void PinGles() => Pin(GraphicsDeviceType.OpenGLES3);

    [MenuItem("Tools/Quest GLES/Pin Vulkan only")]
    static void PinVulkan() => Pin(GraphicsDeviceType.Vulkan);

    static void Pin(GraphicsDeviceType api)
    {
        PlayerSettings.SetUseDefaultGraphicsAPIs(Android, false);
        PlayerSettings.SetGraphicsAPIs(Android, new[] { api });
        Report();
    }

    [MenuItem("Tools/Quest GLES/Report GLES settings")]
    static void Report()
    {
        var apis = string.Join(", ", PlayerSettings.GetGraphicsAPIs(Android));
        var auto = PlayerSettings.GetUseDefaultGraphicsAPIs(Android);
#if UNITY_6000_6_OR_NEWER
        // openGLRequireES31 is deprecated in 6.6 (getter always true). Check
        // Player > Android > Other Settings > "Use OpenGL ES 3.0 shaders" by hand.
        var es31 = "n/a (6.6: see 'Use OpenGL ES 3.0 shaders')";
#else
        var es31 = PlayerSettings.openGLRequireES31.ToString();
#endif
#if UNITY_6000_0_OR_NEWER
        var skin = PlayerSettings.meshDeformation.ToString();
#else
        var skin = PlayerSettings.gpuSkinning ? "GPU" : "CPU";
#endif
        Debug.Log($"[QuestGles] auto={auto} apis=[{apis}] requireES31={es31} " +
                  $"requireES31AEP={PlayerSettings.openGLRequireES31AEP} " +
                  $"requireES32={PlayerSettings.openGLRequireES32} skinning={skin}");
    }
}
#endif
```

- Effect: none on average frame time by itself; removes the largest confound in every GLES measurement (G1-079).
- Cost: none. Side effect: with Auto off and only OpenGLES3 listed, Vulkan-only features silently do nothing (owned by `gles3-perf:gles-vs-vulkan`).
- `Unity ≥ 2022.3` `URP 14+` `GLES` `Vulkan` `Quest 2` `Quest 3/3S`. Goal: Consistency.

### 2. Choose the ES shader level on purpose: 16 vs 32 URP lights (Throughput)

The ES shader level changes URP's per-object light buffer, not only features. `Input.hlsl` uses the 16-light low-end path when `SHADER_API_MOBILE` and `SHADER_API_GLES30` are both defined, 32 otherwise; the C# side uses the low-end limit when `Graphics.minOpenGLESVersion <= OpenGLES30` (G1-020).

- **Unity ≤ 6000.5**: "Require ES3.1" (Player > Android > Other Settings) unticked keeps ES 3.0 shaders and 16 lights; ticked gives ES 3.1 shaders and 32 lights.
- **Unity 6000.6**: "Require ES3.1" is replaced by **Use OpenGL ES 3.0 shaders**. Projects upgraded without Require ES3.1 get it switched on automatically and keep `SHADER_API_GLES30` variants (16 lights). Turning it off gives ES 3.1 shaders and 32 lights, which Unity says "increases the application's workload" (G1-018, G1-019, U1-094). Projects that already required ES 3.1 get 32 immediately.
- Rule: if content never needs more than 16 additional lights per object, keep ES 3.0 shaders for the lighter loop. If you need compute or SSBOs in the same build, you need ES 3.1 shaders; then cap lights in the URP asset (owned by `unity-perf:unity-lighting`).
- Effect: average GPU time only; no published ms delta. Measure: App GPU time in OVR Metrics with levels pinned, same scene, setting on vs off.
- Pre-release trap: UUM-148728 forced 16 to 32 on GLES in 6.6 betas (first seen 6000.6.0b9), fixed in 6000.6.0f1 (U1-040). Do not measure on 6.6 betas.
- Quality cost: fewer per-object lights at ES 3.0 level. Whether ES 3.0 shaders also drop the ES 3.1 compute variants of Unity's skinning shader is undocumented [verify on device] (GLES3-GF2-001).
- Also: referencing `openGLRequireES31` on 6.6 is a build error under warnings-as-errors (G1-018); use the guard above.
- `Unity ≥ 2022.3` (≤ 6.5 setting) / `Unity ≥ 6000.6` (new setting) `URP 14+` `GLES`. Goal: Throughput. A/B hazard: also a Consistency issue, because a GLES-vs-Vulkan comparison is confounded unless the ES level is held fixed (G1-079).

### 3. Stay under 4 vertex/fragment SSBOs for Quest 2 (Consistency, correctness)

Quest 2 allows 4 storage blocks per vertex or fragment stage; Quest 3 allows 12 (G1-005). Compute stages get 24 / 36 (GLES3-GF2-001). A shader authored and tested on Quest 3 can fail to compile or fall back on Quest 2.

```hlsl
// URP 14+/17 custom pass, GLES + Vulkan. StructuredBuffer in a graphics stage needs ES 3.1 (target 4.5).
#pragma target 4.5
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

// Budget: at most 4 StructuredBuffer/RWStructuredBuffer bindings visible to the
// fragment stage and 4 to the vertex stage, or the program exceeds
// GL_MAX_*_SHADER_STORAGE_BLOCKS on Quest 2 (expect a link error or fallback [verify on device]).
StructuredBuffer<float4> _InstanceData;   // 1 of 4 (vertex)
StructuredBuffer<uint>   _ClusterMask;    // 1 of 4 (fragment)
```

- Test on the lowest device: build each SSBO-using feature (Forward+ light lists, GPU-resident paths, VFX Graph) for GLES and check logcat on a Quest 2 (KU-33 method). GPU Resident Drawer and GPU occlusion culling are not available on GLES at all (U1-095, U3-032).
- Runtime gate: branch on `SystemInfo.maxComputeBufferInputsFragment < N` to pick a fallback material [verify on device that Unity reports 4 on Quest 2].
- Effect: prevents a missing effect or first-use compile failure; no frame-time change otherwise.
- Quality cost: the fallback material on Quest 2 loses the SSBO-driven effect.
- `Quest 2` `GLES` `Unity ≥ 2022.3` `URP 14+`. Goal: Consistency.

### 4. Branch shaders with the right macros and targets (Throughput)

G1-022 macros: `SHADER_API_GLES3` / `SHADER_API_VULKAN` select the API; `SHADER_API_GLES30` / `SHADER_API_GLES31` the ES level; `UNITY_PLATFORM_META_QUEST` (Unity 6.5+) the Meta Quest build profile.

```hlsl
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

#if defined(SHADER_API_GLES3) && defined(SHADER_API_GLES30)
    // ES 3.0 shader level: no SSBO, no compute, URP 16-light loop.
    #define MY_USE_SSBO 0
#else
    #define MY_USE_SSBO 1   // GLES 3.1+ or Vulkan
#endif

#if defined(UNITY_PLATFORM_META_QUEST)   // Unity 6000.5+ only; undefined on older editors
    #define MY_QUEST_CHEAP_PATH 1
#endif
```

- Keep `#pragma target` at the lowest level that works: 3.5 for plain URP surfaces, 4.5 only for SSBO/compute/`randomwrite`. Avoid 4.6/5.0 (tessellation): Qualcomm lists hardware tessellation among features to avoid, Unity's untethered-XR guide says avoid geometry shaders, and both push FlexRender to direct mode and are disallowed with multiview (G1-013, G1-048, G2-084, G2-049).
- Geometry and tessellation *are* exposed (ES 3.1+AEP), so "Require ES3.1+AEP" / "Require ES3.2" never excludes a Quest 2 or 3; that is not a reason to use them (G1-013).
- Effect: average GPU time (shader cost), and fewer variants if you branch with compile-time macros rather than uniforms (variant cost is owned by `gles3-perf:gles-shader-binaries`).
- Quality cost: none if the ES 3.0 path is visually equivalent; otherwise the reduced path is visible on ES 3.0-level builds.
- `Unity ≥ 2022.3` (API/level macros as used by URP 14-17 `Input.hlsl`, G1-020) `Unity ≥ 6000.5` (`UNITY_PLATFORM_META_QUEST`) `URP 14+` `GLES`. Goal: Throughput.

### 5. Check the `#version` before using ES 3.2 intrinsics in compute (Consistency, correctness)

- Public HLSLcc emits `#version 300 es` or `310 es`, never `320 es`; ES 3.x fragment shaders default to `precision highp` (GLES3-GF1-007).
- UUM-60833: `.compute` on OpenGLES3 was emitted as `310 es`, hiding ES 3.2 intrinsics such as `imageAtomicMax`. Fixed on 2023.3.X (became 6000.0), 6000.2.X and 6000.3.X; Won't Fix on 2021.3/2022.3/2023.2 (GLES3-GF2-005).
- **Conflict (GX-C10):** the 6000.1 port note says 6.0 LTS has the fix, but the 6000.0 port is Won't Fix with no fixed-in version. On 6000.0 and 6000.1, open "Show compiled code" and confirm `#version 320 es` before relying on ES 3.2 image atomics [verify on device]. On 2021.3/2022.3 do not use them on GLES.
- Graphics-shader `#version` per `#pragma target` on 6.x is still unverified (KU-01); read it in "Compile and show code".
- Effect: enables GPU-driven compute (culling, histograms) without workarounds; matters only for custom compute on GLES.
- Quality cost: none.
- `Unity ≥ 6000.2` `GLES` `Quest 2` `Quest 3/3S`. Goal: Consistency.

### 6. GPU skinning via compute on GLES: enable and verify (Throughput, CPU)

- Setting: Player > Android > Other Settings > GPU Skinning = GPU (Batched), or `PlayerSettings.meshDeformation = MeshDeformation.GPUBatched` (`Unity ≥ 6000.0`; `PlayerSettings.gpuSkinning = true` maps to GPUBatched and is marked for future deprecation) (GLES3-GF2-001).
- Evidence: both `GPU` and `GPUBatched` are compute paths; Unity lists compute on "OpenGL ES 3.1 on Android"; both headsets expose ES 3.2 with 24 (Quest 2) / 36 (Quest 3) compute SSBO blocks, so the 4-block graphics cap does not apply (GLES3-GF2-001).
- **Conflict (G1-C3):** a July 2026 forum post says GPU skinning is unavailable on GLES [community]; Unity's Player settings list GPU / GPU (Batched) with no API restriction [doc]. Docs lean "available"; no source confirms end to end on Quest.
- Verify on device: in a GLES development build, skinning compute dispatches appear in the Frame Debugger or RenderDoc, and skinning samples leave the CPU worker threads in the Profiler Timeline (marker names not checked against a Unity doc).
- Side effect: on GLES, Qualcomm advises not interleaving compute with graphics (G2-067); dispatch placement is owned by `gles3-perf:gles-driver-overhead`. GPU skinning outside GLES compute is owned by `unity-perf:unity-cpu-scripting`.
- Effect: lower main/worker CPU time; adds GPU compute time. No published Quest number; measure CPU and GPU ms with levels pinned.
- `Unity ≥ 6000.0` (API and setting; pre-6000 `gpuSkinning` bool: compute path on GLES not documented [verify on device]) `GLES` `Quest 2` `Quest 3/3S`. Goal: Throughput.

### 7. Plan off the Oculus XR GLES path (Consistency, long-term)

- Unity's documented GLES XR path on Quest is the Oculus XR plugin, deprecated from Unity 6.5. Its docs label display support "OpenGL ES 3.0", which is Unity's API-family label, not the driver level (ES 3.2) (G1-024 / G2-093).
- The Unity OpenXR plugin lists Meta Quest as Vulkan-only; OpenXR Meta 2.1 on OpenXR 1.14 is at feature parity and gets all new features (G1-024, G2-055).
- GLES-only Low Overhead Mode lives in the Oculus XR plugin, so the deprecation strands it (owned by `gles3-perf:gles-driver-overhead`).
- Action: treat every GLES-specific tuning as having a shelf life ending with your last Oculus XR-based release. The switch decision is owned by `gles3-perf:gles-vs-vulkan`; plugin choice by `quest-perf:quest-sdk-choices`.
- Effect: no frame-time change; removes long-term support risk (Consistency). Cost: a future API/plugin migration.
- `Unity ≥ 6000.5` `OculusXR 4.x` `OpenXR 1.x` `GLES`. Goal: Consistency.

### 8. Budget Quest 3S separately from Quest 3 (Throughput)

- Same Adreno 740v3 and same GLES driver V@0837.0.7 (G2-035, baseline), but Meta's ovrgpuprofiler page gives 690 MHz (Quest 3) vs 492 MHz (Quest 3S), about 71% (G3-081).
- **Conflict (ARM-C3):** Meta's levels table gives Quest 3/3S L5 = 599 MHz; 492 MHz equals Quest 3/3S GPU L3, suggesting a copy error on the profiler page. The arm dossier says budget with the levels table (owned by `quest-perf:quest-levels-thermal`). Either way, do not assume a GPU-bound GLES title tuned on Quest 3 holds on 3S.
- Action: profile on a 3S; read `Clocks / Second` or GPU frequency on device (`quest-perf:quest-profiling-toolkit`).
- Effect: average GPU time headroom on 3S; no variance effect by itself. Cost: may need a lower 3S quality tier.
- `Quest 3/3S` `GLES` `Vulkan`. Goal: Throughput.

## Verify

| Change | Metric | Expected movement | Session |
|---|---|---|---|
| Fix 1 (pinned API) | `[GlesCaps] api=` line; manifest `glEsVersion` | exactly the API/level you listed, every launch | one launch per build |
| Fix 2 (ES level) | `urpMaxAdditionalLights` 16 vs 32; App GPU time in OVR Metrics, levels pinned | light ceiling flips; GPU ms delta has no published number, measure p50 and p95 over the same camera path | 5 min steady scene per variant, then a 20-30 min run of the winner for thermal drift |
| Fix 3 (SSBO cap) | logcat shader errors on Quest 2 | zero compile/link errors or fallbacks in every scene | full scene walk on Quest 2 |
| Fix 4 (macros/target) | compiled code: expected branch present; variant count | GLES30 path has no SSBO code; target ≤ 4.5 | build-time |
| Fix 5 (`#version`) | first line of compiled `.compute` | `#version 320 es` on 6.2+ | build-time; device run to confirm intrinsics work |
| Fix 6 (GPU skinning) | Profiler Timeline CPU skinning samples; Frame Debugger dispatches | CPU skinning work leaves worker threads; compute dispatches appear | 2-5 min crowd scene |
| Fix 7 (Oculus XR path) | `Packages/manifest.json` XR plugin and version; Unity version | you know which releases still depend on OculusXR GLES | one-time audit per release |
| Fix 8 (3S) | App GPU time on 3S vs 3 | 3S higher; margin must stay under the budget at p95 | 20-30 min on each headset |

Pin levels for every A/B (`adb shell setprop debug.oculus.gpuLevel <n>`, owned by `quest-perf:quest-profiling-toolkit`) and record the driver string from Diagnose step 1.

## Pitfalls and myths

- **"GLES2 fallback" advice is dead.** Unity 2023.1 removed GLES2 from the engine and URP; 2022.3 is the last line with it (G1-023). Any pre-2023 Quest post weighing GLES2 vs GLES3 is stale.
- **"Unity 6.6 removes GLES."** No: it raises the floor to ES 3.1 (irreversibly) and replaces Require ES3.1; there is no Unity statement deprecating GLES for Android or XR as a whole (G1-017).
- **"The Oculus plugin only supports ES 3.0."** That is Unity's API-family label; the driver is ES 3.2 (G1-024).
- **"Require ES3.2 / AEP will cut off Quest 2."** Both headsets satisfy ES 3.1+AEP and ES 3.2 (G1-013).
- **"8x MSAA on GLES."** GL_MAX_SAMPLES = 4 on both headsets; Meta's 8x wording is generic (G1-007). MSAA level choice: `unity-perf:unity-urp-settings`.
- **"Legacy means the GLES driver is frozen."** The Quest 3 driver moved from 02/29/24 to 01/12/26 (G1-004). Record the driver per capture.
- **Testing SSBO shaders only on Quest 3.** 12 blocks there, 4 on Quest 2 (G1-005).
- **Measuring with Auto Graphics API on.** The build may run Vulkan (G1-016).
- **Assuming a GLES A/B holds the light loop constant.** ES 3.0 vs 3.1 shaders change MAX_VISIBLE_LIGHTS (G1-020, G1-079).
- **Expecting GPU Resident Drawer, GPU occlusion culling, STP or Entities Graphics on GLES.** GRD, GPU occlusion culling and STP are unavailable on GLES; Entities Graphics GLES support is deprecated from 6000.3.12f1 / 6000.4.1f1; Tile-Only falls back on non-sRGB GLES backbuffers in 6000.6.0b6 (U1-095).
- **Trusting the public HLSLcc for `#version`.** It is a 2024 snapshot; the shipping compiler diverged (GX-C10).
- **"Precompiled GLES shader binaries ship in the APK."** Shader binary formats = 0; every program compiles on device (G1-008). Caching: `gles3-perf:gles-shader-binaries`.
- **Unity's "Vulkan is more stable" means frame pacing.** The 6.6 docs' claim probably means correctness; the frame-pacing evidence is in `gles3-perf:gles-vs-vulkan` (G1-C5).

## Sources

All accessed 2026-09-24.

- https://opengles.gpuinfo.org/displayreport.php?id=8023 [measured]: Quest 3 ES 3.2 driver string, limits (G1-001, G1-005, G1-006, G2-069)
- https://opengles.gpuinfo.org/displayreport.php?id=6387 [measured]: Quest 2 driver string, limits, binary formats (G1-002, G1-005, G1-008)
- https://opengles.gpuinfo.org/displayreport.php?id=7475 [measured]: Quest 3 2024 driver (G1-004)
- https://opengles.gpuinfo.org/displayreport.php?id=5092 [measured]: Quest 2 driver history (G1-002)
- https://opengles.gpuinfo.org/listreports.php [measured]: Quest report coverage (GLES3-GF1-005)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]: driver-version query, tessellation to avoid, compute/graphics interleave (G2-082, G1-013, G2-067)
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [community]: Quest 2/3/3S OS and driver versions, Unity QA device list (GLES3-GF1-006, G2-082)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html [doc]: Auto Graphics API order, Require ES3.x, GPU skinning modes (G1-016, G1-027)
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html [doc]: ES 3.1 floor, Use OpenGL ES 3.0 shaders, 16 to 32 lights (G1-017 to G1-019, U1-094)
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc]: 6.6 GLES floor (G1-017)
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/Input.hlsl [doc]: MAX_VISIBLE_LIGHTS (G1-020)
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs [doc]: maxVisibleAdditionalLights (G1-020)
- https://docs.unity3d.com/6000.3/Documentation/Manual/SL-Pragma-target.html [doc]: `#pragma target` mapping (G1-021)
- https://docs.unity3d.com/6000.5/Documentation/Manual/WhatsNewUnity65.html [doc]: UNITY_PLATFORM_META_QUEST (G1-022)
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-branching-api.html [doc]: SHADER_API macros (G1-022)
- https://github.com/Unity-Technologies/HLSLcc/blob/master/src/toGLSL.cpp [doc]: `#version` and precision emission (GLES3-GF1-007)
- https://issuetracker.unity.com/api/v1.0/issues/9889 [community]: UUM-60833 compute `#version 320 es` (GLES3-GF2-005)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings-meshDeformation.html [doc]: MeshDeformation modes (GLES3-GF2-001)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings-gpuSkinning.html [doc]: gpuSkinning mapping (GLES3-GF2-001)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-ComputeShader-introduction.html [doc]: compute on OpenGL ES 3.1 Android (GLES3-GF2-001)
- https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926?page=2 [community]: GPU skinning unavailable claim (G1-C3)
- https://unity.com/releases/editor/whats-new/2023.1.0 and https://docs.unity3d.com/2023.1/Documentation/Manual/WhatsNew20231.html [doc]: GLES2 removal (G1-023)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc]: Oculus XR plugin deprecation, "OpenGL ES 3.0" label (G1-024)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html [doc]: OpenXR Quest Vulkan-only (G2-055)
- https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ [doc]: GLES legacy, Vulkan recommended (G1-028)
- https://unity.com/releases/editor/whats-new/6000.3.12f1 [doc]: Entities Graphics GLES deprecation (U1-095)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc]: untethered-XR checklist, Vulkan stability claim, avoid geometry shaders (U1-095, G1-048, G1-C5)
- https://unity.com/releases/editor/whats-new/6000.6.0f1 [doc]: UUM-148728 light-count regression fix (U1-040)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]: Quest 3 690 MHz vs 3S 492 MHz (G3-081)
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]: level table L5 = 599 MHz, conflict ARM-C3
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html [doc]: GRD not on OpenGL ES (U3-032)
- https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview.txt [doc]: no tessellation/geometry with multiview (G2-049)
- https://discussions.unity.com/t/performance-discrepancy-between-vulkan-and-opengl-with-unity-2022-3-17f1-on-meta-quest-3/938162 [community]: single-variable A/B (G1-079)
