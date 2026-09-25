---
name: quest-mr-costs
description: "Mixed-reality performance on Quest 3/3S (and Quest 2 passthrough) in Unity: passthrough CPU/GPU cost and its level caps, Depth API occlusion, Scene/MRUK meshes, Passthrough Camera API, hand and body tracking cost, and MR vs VR power draw. Use when an MR or passthrough app drops frames or is slower than the same scene in VR, when CPU/GPU levels stop rising with passthrough on, or when budgeting occlusion and scene understanding."
---

# Quest mixed-reality costs

On Quest 3/3S, passthrough mostly costs an app throughput through a lower clock
ceiling, not through extra work in the app's own GPU time. Quest 2 has no
documented cap; its passthrough cost is unpublished (Q2-048), so measure it. Depth API occlusion, MRUK
geometry, camera access and tracking services add real per-frame work. Plan MR
as its own performance tier.

Goals: **Throughput** (the MR clock ceiling, occlusion and scene-geometry cost)
and **Consistency** (MR thermal and power load, scene-load and passthrough-start
hitches).

## When to use / when not

Use when:
- An MR/passthrough build is slower than the same scene in VR, or drops frames only in MR.
- OVR Metrics shows `CPU L` stuck at 3 or `GPU L` stuck at 2 on Quest 3/3S with passthrough on.
- You are budgeting Depth API occlusion, MRUK EffectMesh or global mesh, Passthrough Camera API (PCA), hand tracking / Fast Motion Mode, or body tracking.
- MR sessions heat up or drain faster than VR.

Do not use for:
- The level system in general: level-to-clock tables, Boost, trading semantics, throttling stages, the long-session test. Use `quest-perf:quest-levels-thermal`.
- Per-device budgets and tiers in general (draw calls, PSS, SystemHeadset). Use `quest-perf:quest-budgets-tiers`.
- Watts, DRAM traffic and the thermal envelope. Use `arm-mobile-hw-perf:xr2-bandwidth-power`.
- General URP shader authoring (precision, keywords, SRP Batcher). Use `unity-perf:unity-shader-authoring`.
- Unknown cause, first routing. Start at `quest-perf:quest-triage`.
- Symmetric Projection / MVRR / FFR mechanics. Use `quest-perf:quest-resolution-foveation`; only the MR interaction is noted here.

## Diagnose first

1. **Confirm the ceiling, not the content, moved.** Passthrough is drawn by a system service into a compositor layer; its render cost never shows in the app's GPU timings (Unity Profiler or GPU render-stage traces). What the app sees is the lowered level ceiling plus compositor work (Q4-010).
   ```sh
   adb logcat -c; adb logcat -s VrApi,XrPerformanceManager
   ```
   In the VrApi line, `CPU4/GPU=3/2` means CPU level 3, GPU level 2 (the `4` is the measured core, not a level); the next token is the clock pair in MHz (Q1-028, Q1-031). XrPerformanceManager prints `SetClockLevels: Apply pending clock request change: ...` lines.
   To see why a level was refused: `adb shell setprop debug.oculus.clockStateLogLevel 1` (A3-084; details in `quest-perf:quest-levels-thermal`).
2. **Read the CSV at equal level.** Record an OVR Metrics CSV of the same scene in VR and MR. Compare `app_gpu_time_microseconds` and `gpu_utilization_percentage` at the **same** `gpu_level`, plus `cpu_level`, `gpu_frequency_MHz`, `stale_frame_count`. Same App GPU ms and higher GPU% at a lower level = ceiling problem. Higher App GPU ms at the same level = your MR features (occlusion, EffectMesh, PCA) cost frame time (Q4-010, Q4-021).
3. **Main thread in MR.** If `CPU%` is high at `CPU L3`, Unity Profiler main thread vs 22.9 M cycles/frame at 72 Hz (Key numbers). Use Perfetto to see tracking and passthrough services on other cores (Q4-048). Capture commands: `quest-perf:quest-profiling-toolkit`.
4. **Feature A/B.** Toggle one feature at a time at pinned or recorded levels (full protocol in [references/mr-features.md](references/mr-features.md)):
   - Depth API: `EnvironmentDepthManager.OcclusionShadersMode` None / Hard / Soft (Q4-027).
   - Passthrough: feature fully off vs on, then toggled off at runtime (Q4-021).
   - Hand tracking frequency Low vs High / FMM on vs off (Q4-039, Q4-048).
5. **Hitches in MR only.** Bracket `MRUK.Instance.LoadSceneFromDevice()` to `SceneLoadedEvent` with a ProfilerMarker and look for main-thread spikes when EffectMesh and colliders are generated (Q4-032). Passthrough start takes a few hundred ms (Q4-012).
6. **Body tracking silently downgraded?** `adb shell dumpsys activity service com.oculus.bodyapiservice.BodyAPIService` (Q4-046). FMM active? `adb logcat -e FMM` should show `HandTrackingService: FMM: enabled: true; active: true` (Q4-042).

## Key numbers

| Item | Value | Source | Applies to |
|---|---|---|---|
| Passthrough level caps | CPU max L3 (1.65 GHz, not L4 1.92); GPU max L2 (456 MHz, not L4 545) | Q2-038 / Q4-001 / A1-018 / A3-072 [doc] | `Quest 3/3S`, all Unity, both XR stacks |
| Clock loss from caps | GPU −16.3%, CPU −14.1% (arithmetic on the clock table, not measured frame time) | Q2-006 notes, derived | `Quest 3/3S` |
| Launch-era passthrough cost | 17% less GPU, 14% less CPU than VR-only; Depth API adds more GPU, no number | Q2-006 / Q4-002 / A1-019 [doc], blog Oct 2023 | `Quest 3` (3S same SoC); launch-era OS, [verify on device] |
| MR main-thread budget | about 22.9 M cycles/frame at 72 Hz (1.65 GHz × 13.9 ms) vs 26.7 M in VR at L4 | A1-018 / A1-026, derived | `Quest 3/3S` |
| Sustained MR planning level | budget against GPU L2 (456 MHz) and CPU L3 (1.65 GHz) | GPU L2: Q4-006 [doc]; CPU L3: follows from the availability table, A3-072 [doc] | `Quest 3/3S` |
| Quest 2 passthrough level cap | none listed in the current table | Q2-048 / Q4-009 [doc] | `Quest 2`, [verify on device] |
| Passthrough layers | max 3 per app; each adds "non-trivial" overhead, no per-layer number | Q4-011 [doc] | all Quest |
| Passthrough color LUT | max resolution 64; start at 16, stay ≤ 32; creating a 64 LUT takes "a few ms" | Q4-017 [doc] | all Quest |
| PCA | about 1-2% GPU per streamed camera, about 45 MB memory, 20-40 ms latency, 60 Hz, max 1280x1280 | Q4-022 [doc] | `Quest 3/3S`, HzOS v74+ |
| Light MR scene, third-party capture | CPU L2 / GPU L2 most samples, app GPU about 3.1-3.3 ms, 72 fps, 0 stale in 547 of 565 s | QUEST-GF2-009 [measured] | `Quest 3`, OS and Unity not recorded |
| MR vs VR power | MR scenarios draw about 2-3 W more than matching VR (browsing 7.6-8.2 W VR vs 9.6-10.2 W MR; game 7.5-9.0 W vs 10.5-12.0 W) | ARM-GF2-002 [measured] | `Quest 3`, OS v57, 120 Hz, whole device |
| Passthrough latency lock | 72 Hz in flicker-free lighting syncs cameras to display: 13.9 ms budget vs 11.1 ms at 90 Hz | Q4-016 [doc] | `Quest 3/3S` |
| Depth API cost | no published ms or % for Hard or Soft occlusion | Q4-027 [doc] | measure, see references |
| Hand / body tracking cost | no current number. 2021 only: Quest 2 low-freq hands CPU L3/GPU L3, high-freq CPU L3/GPU L2 (stale, Q4-C4) | Q4-038, Q4-039, Q4-048 [doc] | measure |
| Global mesh size | no published triangle count, memory or update rate | Q4-034 [doc] | measure |

For the per-feature table (version requirements, API names, measurement recipe
per feature) read [references/mr-features.md](references/mr-features.md) when
budgeting a specific MR feature or planning an A/B.

## Fixes, ranked by payoff ÷ effort

### 1. Budget MR as a separate tier at CPU L3 / GPU L2
- **Change:** size the MR mode of each scene so it holds frame rate at GPU L2 (456 MHz) and CPU L3 (1.65 GHz) on Quest 3/3S. Use `SystemHeadset` tiering from `quest-perf:quest-budgets-tiers`; add an "MR" axis to the quality ladder (render scale, FFR, effect count). Do not size MR content from VR profiles taken at L4.
- **Effect:** removes the average-frame-time overrun that appears only in MR; keeps GPU utilisation below the 87% level-raise threshold at the cap, avoiding level oscillation and the frame-time variance it causes (Q2-046/Q2-047 notes).
- **Cost:** lower MR content density than VR.
- **Tags:** `Quest 3/3S` `all Unity` `Vulkan` `GLES`. **Goal:** Throughput, Consistency.
- **Conflicts:** GPU L5 with passthrough is ambiguous. The table says L5 needs GPU L4 available and trading +1 "or dynamic resolution is enabled"; one reading lets dynamic resolution alone unlock L5 in MR (Q4-C1). A third-party CSV shows 34 of 565 samples at GPU L3 with passthrough, against the documented cap (QUEST-GF2-C4). Keep the documented cap as the planning rule [verify on device]. Enabling dynamic resolution costs little and is the only candidate path to L5 (`quest-perf:quest-resolution-foveation`).

### 2. Do not enable passthrough when the user or the scene does not need it
- **Change:** at startup, check `OVRManager.IsPassthroughRecommended()` and start in VR when MR is not preferred (Q4-019). In long VR-only sections, disable passthrough at a scene transition (re-enable has a creation delay): `OVRManager.instance.isInsightPassthroughEnabled = false` or `OVRPassthroughLayer.enabled = false` (Q4-013). On OpenXR: Meta, disable the AR Camera Manager component (Q4-014).
- **Effect:** may restore CPU L4 / GPU L3-4 (GPU L2→L4 is 456→545 MHz, +19.5%; CPU L3→L4 is 1.65→1.92 GHz, +16.4%; derived from the Q2-046/Q4-003 clock table). **Unconfirmed:** Meta's condition reads "does not enable passthrough features"; whether a runtime toggle or a manifest-declared feature restores the levels is not documented (Q4-001, Q4-019) [verify on device]: watch `CPU L`/`GPU L` while toggling in a GPU-bound scene.
- **Cost:** a few hundred ms of passthrough start-up on re-enable; gate reveals on `passthroughLayerResumed` (Q4-012). Keep one `OVRPassthroughLayer` alive across scenes (DontDestroyOnLoad owner).
- **Tags:** `Quest 3/3S` `Core SDK`. **Goal:** Throughput, Consistency (no black frame on transitions).

### 3. Passthrough-friendly URP settings
- **Change** (Unity OpenXR: Meta recommendations, Q4-015): Graphics API: Vulkan (Q4-015). URP Asset: HDR off, Terrain Holes off. Universal Renderer: Post-processing off, Intermediate Texture = Auto.
- **Prerequisite (Core SDK path; correctness, not performance):** underlay needs Skybox Material None and camera background (0,0,0,0); wrong alpha shows as haloing (Q4-014).
- **Effect:** lowers average GPU time. Inference (Q4-015 notes): with HDR and post off, URP can skip the intermediate color target and resolve, which also keeps FFR effective (`quest-perf:quest-resolution-foveation`).
- **Cost:** no HDR or post-processing in MR mode.
- **Tags:** `Quest 2` `Quest 3/3S` `Unity ≥ 6000.0` with OpenXR: Meta 2.x (the same URP choices apply on the Core SDK path) `URP 17` `Vulkan`. **Goal:** Throughput.

### 4. Depth API: pay only when an occluder is visible, pick the cheapest mode
- **Change:**
  - `EnvironmentDepthManager.enabled = false` when no occluding content is on screen; on XR.Oculus, `SetEnvironmentDepthRendering(false)`. The Depth API costs something even when no shader samples it (Q4-028).
  - `OcclusionShadersMode = HardOcclusion` where jagged edges are acceptable; Soft needs "slightly more GPU" (Q4-027).
  - Put occlusion only on materials that can actually be behind real objects. Cost scales with pixels covered by occluding materials (Q4-029 inference).
  - For placement only, use MRUK v81+ `EnvironmentRaycastManager`; it no longer needs the Depth API (Q4-031).
  - If still too expensive, fall back to occlusion from scene or hand meshes (fix 5).
- **Effect:** lower average GPU time; no published size.
- **Cost:** Hard occlusion edges are less stable over time.
- **Tags:** `Quest 3/3S` `Vulkan` (required) Multiview (required); Unity 2022.3.15f1+/2023.2+ with Oculus XR 4.2.0+ and Core SDK v67 to below v74, or `Unity ≥ 6000.0` with OpenXR: Meta 2.1.0+ and Core SDK v74+ (Q4-026). Meta's plugin page says no Depth API before Unity 6 / SDK v74; likely it works on older SDKs but not the current SDK line with Unity < 6 (Q4-C10). **Goal:** Throughput.

C# toggle (Core SDK v74+, untested, [verify on device]):

```csharp
using Meta.XR.EnvironmentDepth;
using UnityEngine;

// Turns the Depth API off when no occluding renderer is visible.
// Assign the renderers whose materials use the occlusion keywords.
public sealed class DepthOcclusionGate : MonoBehaviour
{
    [SerializeField] EnvironmentDepthManager depthManager;
    [SerializeField] Renderer[] occludedRenderers;
    [SerializeField] bool hardOcclusion = true;

    void Start()
    {
        if (depthManager == null || !EnvironmentDepthManager.IsSupported) { enabled = false; return; }
        depthManager.OcclusionShadersMode = hardOcclusion
            ? OcclusionShadersMode.HardOcclusion
            : OcclusionShadersMode.SoftOcclusion;
    }

    void LateUpdate()
    {
        bool anyVisible = false;
        for (int i = 0; i < occludedRenderers.Length; i++)
        {
            var r = occludedRenderers[i];
            if (r != null && r.isVisible) { anyVisible = true; break; }
        }
        if (depthManager.enabled != anyVisible)
            depthManager.enabled = anyVisible;
    }
}
```

`Renderer.isVisible` includes shadow-caster visibility and lags one frame; add
hysteresis if the manager flickers. Re-enabling may take frames before depth
textures are valid [verify on device].

Occluding URP shader (URP 17, Core SDK v74+). Macros and include path from
Meta's advanced-usage page (Q4-029). Ship one mode? Replace the multi_compile
with one keyword or strip the other with an `IPreprocessShaders` stripper: the
three-way multi_compile triples variants (Q4-029 notes) [verify on device].

```hlsl
Shader "MR/UnlitOccluded"
{
    Properties
    {
        _BaseMap ("Base Map", 2D) = "white" {}
        _BaseColor ("Base Color", Color) = (1,1,1,1)
        _EnvironmentDepthBias ("Environment Depth Bias", Float) = 0.0
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "Forward"
            Tags { "LightMode"="UniversalForward" }
            Blend One OneMinusSrcAlpha   // premultiplied output from the occlusion macro
            ZWrite Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ HARD_OCCLUSION SOFT_OCCLUSION

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.meta.xr.sdk.core/Shaders/EnvironmentDepth/URP/EnvironmentOcclusionURP.hlsl"

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4  _BaseColor;
                float  _EnvironmentDepthBias;
            CBUFFER_END

            struct Attributes
            {
                float4 vertex : POSITION;
                float2 uv     : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv         : TEXCOORD0;
                META_DEPTH_VERTEX_OUTPUT(1)   // previous TEXCOORD index + 1
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings vert (Attributes v)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_TRANSFER_INSTANCE_ID(v, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.positionCS = TransformObjectToHClip(v.vertex.xyz);
                o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
                META_DEPTH_INITIALIZE_VERTEX_OUTPUT(o, v.vertex);
                return o;
            }

            half4 frag (Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                half4 col = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv) * _BaseColor;
                col.rgb *= col.a;   // premultiply before occlusion
                META_DEPTH_OCCLUDE_OUTPUT_PREMULTIPLY(i, col, _EnvironmentDepthBias);
                return col;
            }
            ENDHLSL
        }
    }
}
```

### 5. Cheaper occlusion and selective passthrough in the eye buffer
- **Change:** if the Depth API is too expensive, draw depth-only scene or hand meshes before opaques: render queue below 2000, `ColorMask 0`, `ZWrite On` (Q4-030). For selective passthrough, punch holes in the app's own eye-buffer alpha with the Core SDK "Selective Passthrough" material (for example on an MRUK EffectMesh), not a separate alpha-mask passthrough layer, which adds "significant overhead" (Q4-018).
- **Effect:** depth-only pre-pass is cheap on a tiler and early-z rejects virtual pixels behind it (Q4-030 notes); lower average GPU time than Depth API occlusion (size not published).
- **Cost:** occlusion only against scanned geometry and hands; no dynamic real objects.
- **Tags:** `Quest 2` `Quest 3/3S` `all Unity` `URP 12+`. **Goal:** Throughput.

```hlsl
Shader "MR/DepthOnlyOccluder"
{
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry-10" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Tags { "LightMode"="UniversalForward" }
            ColorMask 0
            ZWrite On
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            struct Attributes { float4 positionOS : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; UNITY_VERTEX_OUTPUT_STEREO };
            Varyings vert (Attributes v)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                return o;
            }
            half4 frag (Varyings i) : SV_Target { return 0; }
            ENDHLSL
        }
    }
}
```

### 6. One passthrough layer, small precreated LUTs
- **Change:** use one passthrough layer (hard max 3, Q4-011). Color LUT resolution 16, at most 32; create LUTs during load, never per frame at high resolution (Q4-017). Schedule layer creation with `XR_PASSTHROUGH_IS_RUNNING_AT_CREATION_BIT_FB` or first enable during a loading beat (Q4-013).
- **Effect:** less compositor and GPU work; removes a few-ms creation spike (LUT 64).
- **Cost:** a coarser color LUT means less precise color grading of passthrough.
- **Tags:** `Quest 2` `Quest 3/3S`. **Goal:** Throughput, Consistency.

### 7. Run MR at 72 Hz unless you have measured headroom
- **Change:** in flicker-free lighting, 72 Hz lets passthrough cameras sync to the display: stable latency, no judder (Q4-016). On OpenXR: Meta, `TryRequestDisplayRefreshRate(72f)`. Refresh-rate policy lives in `quest-perf:quest-frame-pacing`.
- **Effect:** stable passthrough latency and no judder (Q4-016); the 13.9 ms budget instead of 11.1 ms at the capped clocks should lower stale-frame risk, no published number [verify on device].
- **Cost:** lower display refresh than 90 Hz; Q4-016 names only the 13.9 ms vs 11.1 ms trade-off, no published quality cost.
- **Tags:** `Quest 3/3S`. **Goal:** Consistency, Throughput.

### 8. MRUK and scene geometry
- **Change:**
  - EffectMesh: Cast Shadows off unless the room must cast; Hide Mesh (or a depth-only material) when you need only colliders or occlusion; one EffectMesh per material, since each instance adds draw calls (Q4-033).
  - Global mesh as physics: a simplified or convex collider; log `mesh.triangles.Length / 3` after `SceneLoadedEvent` in several real rooms (Q4-034).
  - DestructibleGlobalMeshSpawner: lower "Segments Density", as each fragment is its own renderer (Q4-035).
  - Cache room and anchor references; queries have overhead (Q4-036).
  - Load scene data during a loading beat; hang dependent work off `SceneLoadedEvent` (Q4-032).
- **Effect:** fewer draw calls and shadow casters (average); fewer main-thread spikes at scene load (variance). No per-option cost published.
- **Cost:** no room shadows. A hidden or convex collider approximates the room, so physics contacts are less precise. Lower Segments Density gives coarser destruction.
- **Tags:** `Quest 2` `Quest 3/3S` (global mesh: Quest 3/3S) MRUK; MRUK 207.0.0 needs Unity 6000.0.66f2+ (Q4-037). **Goal:** Throughput, Consistency.

### 9. Passthrough Camera API
- **Change:** request a concrete resolution (`PassthroughCameraAccess.RequestedResolution`, list 320x240 to 1280x1280) and a `MaxFramerate`, never "largest" (Q4-023). Stream one camera unless you need stereo: cost is per camera (Q4-022; stereo about 2-4% GPU, derived, [verify on device]). Use `PassthroughCameraAccess` (MRUK v81+) instead of `WebCamTexture` (Q4-024). On OpenXR: Meta 2.6 use the GPU image path (zero-copy, Vulkan only; acquire/release inside `beginCameraRendering`/`endCameraRendering`); use the CPU path only for CV, off the main thread (Q4-025).
- **Effect:** lower GPU% and memory. Whether lower resolution reduces the 1-2% / 45 MB is unpublished; measure GPU% at fixed GPU L.
- **Cost:** lower camera resolution or frame rate lowers CV accuracy and update rate. Mono loses stereo depth cues.
- **Tags:** `Quest 3/3S` HzOS v74+; Core SDK/MRUK path: MRUK v81+ `Unity ≥ 2022.3.15f1` (MRUK 207.0.0: `Unity ≥ 6000.0.66f2`); OpenXR: Meta 2.6 image capture: `Unity ≥ 6000.0`, GPU path `Vulkan` only. **Goal:** Throughput.

### 10. Hand and body tracking
- **Change:** ship without Fast Motion Mode first; enable only when fast motion loses tracking (Q4-040). Toggle at runtime with `OVRPlugin.RequestFastMotionMode(bool)` or `OVRManager.instance.fastMotionModeHandPosesEnabled` only for fast-motion segments. Wide Motion Mode runs body tracking under the hood (Q4-045). Request IOBT before enabling other heavy services, or it starts in low fidelity with no error (Q4-046). Leave "Update When Offscreen" off on body-tracked skinned meshes; enlarge SkinnedMeshRenderer bounds instead (Q4-047).
- **Effect:** higher tracking frequency "reserves some performance headroom" (Q4-038); no current number. Update When Offscreen costs CPU every frame.
- **Cost:** FMM adds jitter, which hurts direct touch and typing. Tracking is worse in low light. FMM disables the Dynamic Object Tracker. Multimodal overrides FMM (Q4-040, Q4-041).
- **Tags:** `Quest 2` `Quest 3/3S` (IOBT/WMM: `Quest 3/3S`) Core SDK / Movement SDK. FMM: Core SDK v59+, and `Unity ≥ 6000.0.66f2` per the current page (Q4-040). Multimodal: `Unity ≥ 6000.0.66f2`, SDK v62+ (Q4-044). **Goal:** Throughput.

### 11. CPU-bound MR: do not reach for favour-CPU trading
- **Change:** `com.oculus.trade_cpu_for_gpu_amount = -1` ("Processor Favor") cannot help: CPU L5 needs CPU L4 available, and passthrough removes L4 (A1-033, Q4-004). Move work into jobs or cut main-thread work (`unity-perf:unity-cpu-scripting`). Boost is documented as L4 to L8 and its behaviour under passthrough is undocumented (Q4-007) [verify on device]: log the granted `cpu_level` and `cpu_frequency_MHz` during a Boost request in MR before relying on it (`quest-perf:quest-levels-thermal`).
- **Effect:** none on frame time. The setting is a no-op in MR; a CPU-bound MR app gains only from real main-thread work cuts; Boost in MR is unconfirmed.
- **Cost:** none; it removes a wasted build-time decision.
- **Tags:** `Quest 3/3S` OpenXR backend. **Goal:** Throughput.

## Verify

- **Levels:** with passthrough on, the log should show `CPU L` ≤ 3 and `GPU L` ≤ 2 on Quest 3/3S. A GPU L3 sample means the cap rule did not hold or passthrough was off; record it (QUEST-GF2-C4). After fix 2, levels in VR sections should reach L4 if the runtime restores them [verify on device].
- **Frame time:** at GPU L2, `gpu_utilization_percentage` at or under 0.8 (the 80% GPU headroom rule, owned by `quest-perf:quest-triage`) and `app_gpu_time_microseconds` p95 under the frame budget minus compositor time.
- **Depth API:** the None vs Hard vs Soft A/B should show a GPU% delta at locked GPU L; fix 4 should remove the delta in frames with no visible occluder.
- **Stale frames:** `stale_frame_count` 0 per minute in steady MR play; no stale burst at scene load or passthrough enable.
- **Session length:** MR draws about 2-3 W more than VR on Quest 3 (ARM-GF2-002), so run the 20-30 minute long-session protocol from `quest-perf:quest-levels-thermal` in MR mode, not only in VR. Compare the first and last 5 minutes of level, frequency, `power_wattage` and stale frames.
- Record OS build, SDK versions and granted levels with every capture.

## Pitfalls and myths

- **"MR is slower because passthrough renders in my frame."** It does not appear in app GPU time (Q4-010). The loss is the clock ceiling. Compare GPU% at the same level before touching content.
- **Quoting 17% / 14% as current.** Those are Meta's Oct 2023 launch-blog figures for Meta's content; they match the clock-cap arithmetic, which suggests the caps are how the cost is enforced (A1-019 notes). Re-measure on the current OS.
- **"Favour CPU fixes a CPU-bound MR app."** Unreachable in MR (A1-033).
- **"SustainedHigh gives L4 in MR."** It requests CPU 4-4 / GPU 3-5, which passthrough makes unavailable; the doc does not say what is granted (Q4-005). Log the granted level.
- **Keeping the Depth API on just for placement.** MRUK v81+ raycasts do not need it (Q4-031).
- **Alpha-mask passthrough layer for a window into reality.** Use eye-buffer alpha (Q4-018).
- **Letting PCA auto-pick the largest mode.** 1280x1280 arrived in HzOS v83; apps grabbing the max can break (Q4-023).
- **Using the 2021 hand-tracking downclocks as current rules.** Superseded; current tables list no hand-tracking row (Q4-C4). Hand Tracking Frequency High and Max behave the same (Q4-040).
- **Quest 3S has no depth sensor** (Q2-002, Q2-092), but the passthrough CPU/GPU restrictions are the same as Quest 3. The Depth API support list names Quest 3 and 3S (Q4-026) [verify on device] on 3S.
- **Symmetric Projection / MVRR in MR:** only the generic 5-15% and 3-8% GPU-bound figures exist; no MR measurement, and check edge alpha for passthrough artifacts [verify on device] (Q4-078).
- **FMM side effects:** it disables the Dynamic Object Tracker (MRUK keyboard calls return no anchors); IOBT/WMM will not run with passthrough + FBS + FMM together; multimodal wins over FMM (Q4-041, Q4-044).
- **`passthroughLayerResumed` over Link** does not fire on SDK v203 (Q4-012 notes) (fix scheduled for v204 per the v203 release notes). Test MR reveal on device.

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc] (Q4-001, Q4-003 to 006, A1-018, A1-026, A1-033, A3-072)
- https://developers.meta.com/horizon/documentation/native/android/os-cpu-gpu-levels/ [doc] (Q2-038, Q2-046 to 048)
- https://developers.meta.com/horizon/blog/start-developing-Meta-Quest-3-tips-performance-mixed-reality/ [doc] (Q2-006 / Q4-002, A1-019; Oct 2023)
- https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ [doc] (Q4-004, Q4-006, Q2-050)
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ [doc] (Q4-006)
- https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough/ [doc] (Q4-010, Q4-011, Q4-013, Q4-014, Q4-019)
- https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-bp/ [doc] (Q4-011, Q4-013, Q4-021)
- https://developers.meta.com/horizon/documentation/native/android/mobile-passthrough-customization/ [doc] (Q4-017, Q4-018, Q4-030)
- https://developers.meta.com/horizon/documentation/unity/unity-passthrough-gs/ [doc] (Q4-012, Q4-014, Q4-019)
- https://developers.meta.com/horizon/documentation/unity/unity-passthrough-bp/ [doc] (Q4-013, Q4-016, Q4-021)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/get-started/graphics-settings.html [doc] (Q4-015)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/camera/passthrough.html [doc] (Q4-014)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/camera/image-capture.html [doc] (Q4-025)
- https://developers.meta.com/horizon/documentation/unity/unity-pca-overview/ [doc] (Q4-022, Q4-023)
- https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.6/manual/features/display-utilities.html [doc] (Q4-016 notes, `TryRequestDisplayRefreshRate`)
- https://developers.meta.com/horizon/documentation/unity/unity-pca-documentation/ [doc] (Q4-023, `RequestedResolution`, `MaxFramerate`)
- https://developers.meta.com/horizon/documentation/unity/unity-pca-migration-from-webcamtexture/ [doc] (Q4-024)
- https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-get-started/ [doc] (Q4-026, Q4-027, Q4-028)
- https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions/ [doc] (Q4-027)
- https://developers.meta.com/horizon/documentation/unity/unity-depthapi-occlusions-advanced-usage/ [doc] (Q4-029, shader macros)
- https://developers.meta.com/horizon/documentation/unity/unity-depthapi-xr-oculus/ [doc] (Q4-028)
- https://developers.meta.com/horizon/documentation/unity/unity-customize-passthrough-passthrough-occlusions/ [doc] (Q4-030)
- https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-environment-raycast/ [doc] (Q4-031)
- https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manage-scene-data/ [doc] (Q4-032 to 034, Q4-036)
- https://developers.meta.com/horizon/documentation/unity/unity-mr-utility-kit-manipulate-scene-visuals/ [doc] (Q4-018, Q4-035)
- https://npm.developer.oculus.com/com.meta.xr.mrutilitykit [doc] (Q4-037)
- https://developers.meta.com/horizon/documentation/unity/unity-ovrcamerarig/ [doc] (Q4-038)
- https://developers.meta.com/horizon/blog/oculus-developer-release-notes-v28/ [doc] (Q4-039; 2021, stale)
- https://developers.meta.com/horizon/documentation/unity/fast-motion-mode/ [doc] (Q4-040 to 042, Q4-048)
- https://developers.meta.com/horizon/documentation/native/android/native-openxr-hand-tracking-frequency-hint/ [doc] (Q4-043)
- https://developers.meta.com/horizon/documentation/unity/unity-multimodal/ [doc] (Q4-044)
- https://developers.meta.com/horizon/documentation/unity/unity-wide-motion-mode/ [doc] (Q4-045)
- https://developers.meta.com/horizon/documentation/unity/move-body-tracking/ [doc] (Q4-046, Q4-047)
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ [doc] (Q4-078)
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc] (logcat fields, Q1-028, Q1-031)
- https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ [doc] (A3-084, clockStateLogLevel)
- https://developers.meta.com/horizon/essentials/compare-devices/ [doc] (Q2-001, Q2-002)
- https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_144005.csv [measured] (QUEST-GF2-009)
- https://web.archive.org/web/20250108162626/https://communityforums.atmeta.com/t5/Talk-VR/Quest-3-Power-Usage-Tests-and-Approximate-Battery-Life/td-p/1094433 [measured] (ARM-GF2-002; OS v57)
