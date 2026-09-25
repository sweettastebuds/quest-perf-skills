---
name: gles-extensions-multiview
description: "Adreno and Meta OpenGL ES extensions on Quest 2/3/3S and how Unity uses them: OVR_multiview2, framebuffer fetch, QCOM_texture_foveated (FFR mechanics on GLES), shading-rate extensions, tiled-rendering control, ASTC decode mode and other QCOM/EXT extensions, with per-device availability. Use when relying on a GLES extension, when multiview crashes or misrenders on GLES, or checking whether a GLES feature exists on a headset."
---

# GLES extensions and multiview on Quest

Goal served: **Throughput** (multiview cuts render-thread submission; foveation and on-tile tricks cut GPU work). Two items also serve **Consistency**: the OXPB-144 release-build crash and the UUM-102876 GL-error spam that drops FPS in development builds.

Scope: Quest 2 (Adreno 650, driver V@0690.0), Quest 3/3S (Adreno 740, V@0837.0.7), OpenGL ES 3.2 drivers, Unity 2021.3-6000.6 with the Oculus XR plugin (OculusXR 4.x). Unity's documented GLES XR path on Quest is OculusXR, deprecated from Unity 6.5; the OpenXR plugin lists Quest as Vulkan-only (G1-024 / G2-093, G2-055). Every GLES-specific fix here has a limited shelf life.

## When to use / when not

Use when:

- Deciding whether a GLES extension exists on Quest 2 vs Quest 3/3S, or gating native-plugin code on one.
- Multiview on GLES crashes on launch, renders only the left eye, spams GL errors, or does not reduce render-thread time.
- Budgeting vertex work under multiview on GLES.
- A URP effect reads the framebuffer on GLES (`FRAMEBUFFER_INPUT_*`, framebuffer fetch) and you need to know what it compiles to.
- FFR on a GLES build: `QCOM_texture_foveated` mechanics, the level setprops, why the level does nothing.
- VRS, tile control, frame extrapolation, ASTC decode mode, RGB9_E5, LOD bias, clip control, context priority, buffer storage on GLES.

Do not use; go to the sibling instead:

- Bottleneck not yet identified: `quest-perf:quest-triage`.
- Choosing FFR levels, dynamic foveation, subsampled layout, render scale on any API; the full FFR-on-GLES conflict statement: `quest-perf:quest-resolution-foveation`.
- CPU draw-call saving from multiview/SPI in general (API-independent), SRP Batcher, batching: `unity-perf:unity-draw-calls-batching`.
- glClear / glInvalidateFramebuffer / MSRTT load-store behaviour, MSAA cost on tile: `gles3-perf:gles-tile-load-store`.
- URP Render Graph pass merging, on-tile post, framebuffer fetch in URP on Vulkan: `unity-perf:unity-render-graph-tiling`.
- GLES vs Vulkan choice and GLES capture caveats: `gles3-perf:gles-vs-vulkan`.
- GLES versions, `#pragma target`, OculusXR deprecation detail: `gles3-perf:gles-versions-unity-output`.
- State-change cost, Low Overhead Mode / KHR_no_error: `gles3-perf:gles-driver-overhead`.
- Program binaries and `OES_get_program_binary`: `gles3-perf:gles-shader-binaries`.
- GMEM, bins, FlexRender, LRZ hardware: `arm-mobile-hw-perf:xr2-adreno-architecture`.

## Diagnose first

1. **Record API, driver and multiview state with every capture.** Driver line (G2-082):
   ```sh
   adb shell dumpsys SurfaceFlinger | grep GLES
   ```
   Expect `Adreno (TM) 650 ... V@0690.0` (Quest 2) or `Adreno (TM) 740 ... V@0837.0.7` (Quest 3/3S). Results move with OS/driver updates, so a capture without this line is not comparable.

2. **Read what the device actually exposes.** Only seven Quest reports exist on gpuinfo and none for Quest 3S or post-2023 Quest 2 (GLES3-GF1-005), so dump on the device. Paste-ready probe; Unity 2021.3+ (fovCaps logged on 2022.3+ only), IL2CPP or Mono, Android, OpenGLES3 active. It runs `glGetStringi` on the render thread (where Unity's GL context is current) through `GL.IssuePluginEvent`, and also reads `GL_MAX_VIEWS_OVR` (KU-21) and `GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT` (KU-30), which the reports lack. Untested [verify on device].
   ```csharp
   using System;
   using System.Runtime.InteropServices;
   using System.Text;
   using UnityEngine;
   using UnityEngine.Rendering;

   public class GlesExtensionProbe : MonoBehaviour
   {
   #if UNITY_ANDROID && !UNITY_EDITOR
       [DllImport("GLESv3")] static extern IntPtr glGetStringi(uint name, uint index);
       [DllImport("GLESv3")] static extern IntPtr glGetString(uint name);
       [DllImport("GLESv3")] static extern void glGetIntegerv(uint pname, int[] data);
       [DllImport("GLESv3")] static extern uint glGetError();
   #endif
       delegate void RenderEvent(int id);
       static readonly RenderEvent s_Callback = OnRenderEvent; // keep alive vs GC

       void Start()
       {
           string fov = "n/a";
   #if UNITY_2022_3_OR_NEWER
           fov = SystemInfo.foveatedRenderingCaps.ToString();
   #endif
           Debug.Log($"[GLProbe] api={SystemInfo.graphicsDeviceType} ver={SystemInfo.graphicsDeviceVersion} " +
                     $"multiview={SystemInfo.supportsMultiview} fovCaps={fov}");
           if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.OpenGLES3) return;
           GL.IssuePluginEvent(Marshal.GetFunctionPointerForDelegate(s_Callback), 0);
       }

       [AOT.MonoPInvokeCallback(typeof(RenderEvent))]
       static void OnRenderEvent(int id)
       {
   #if UNITY_ANDROID && !UNITY_EDITOR
           const uint GL_RENDERER = 0x1F01, GL_VERSION = 0x1F02, GL_EXTENSIONS = 0x1F03, GL_NUM_EXTENSIONS = 0x821D;
           const uint GL_MAX_SAMPLES = 0x8D57, GL_MAX_VIEWS_OVR = 0x9631, GL_MAX_ANISO_EXT = 0x84FF;
           var sb = new StringBuilder();
           sb.Append(Marshal.PtrToStringAnsi(glGetString(GL_RENDERER))).Append(" | ")
             .Append(Marshal.PtrToStringAnsi(glGetString(GL_VERSION))).Append('\n');
           var v = new int[] { -1 };
           glGetIntegerv(GL_NUM_EXTENSIONS, v);
           for (uint i = 0; i < (uint)Math.Max(v[0], 0); i++)
               sb.Append(Marshal.PtrToStringAnsi(glGetStringi(GL_EXTENSIONS, i))).Append('\n');
           foreach (var (n, e) in new[] { ("MAX_SAMPLES", GL_MAX_SAMPLES), ("MAX_VIEWS_OVR", GL_MAX_VIEWS_OVR), ("MAX_ANISOTROPY", GL_MAX_ANISO_EXT) })
           { v[0] = -1; glGetIntegerv(e, v); sb.Append(n).Append('=').Append(v[0]).Append('\n'); }
           while (glGetError() != 0) { } // do not leave an error for Unity's own GL checks
           Debug.Log("[GLProbe]\n" + sb);
   #endif
       }
   }
   ```
   Read it with `adb logcat -s Unity | grep -A 200 GLProbe` (PowerShell: `adb logcat -s Unity | Select-String -Context 0,200 GLProbe`). Diff against [references/extension-matrix.md](references/extension-matrix.md).

3. **Is multiview actually on, and is the saving on the CPU?** Build twice, Stereo Rendering Mode = Multi Pass vs Multiview (Project Settings > XR Plug-in Management > Oculus > Android > Stereo Rendering Mode; G2-053). Compare, in a non-development build with fixed CPU/GPU levels, OVR Metrics Tool App CPU (CPU frame time) and App GPU time logged over 60 s per variant. Take draw calls per frame (Frame Debugger) and the Profiler render-thread hierarchy from a development build only after step 5 shows zero `INVALID_OPERATION` lines. Expected shape: draws halve, render-thread time drops, App GPU time roughly flat (G2-050, G2-051). If Unity falls back to multi-pass silently (unsupported request), `SystemInfo.supportsMultiview` is the first check (G2-053).

4. **Missing right eye** under multiview = a custom shader breaking the SPI macro contract, not a driver bug (G2-054). Frame Debugger: the offending draw writes slice 0 only.

5. **GL error spam (UUM-102876).** In any development build with OculusXR + Multiview + GLES:
   ```sh
   adb logcat -s Unity | grep -i -E "INVALID_OPERATION|OpenGL"
   ```
   The exact log text is not published; filter case-insensitive. Continuous errors = the known issue; CPU numbers from that build are invalid (G2-057 / G3-046).

6. **Is FFR reaching the GLES main pass?** (G2-064 / G3-054, G1-044)
   ```sh
   adb shell setprop debug.oculus.foveation.dynamic 0
   adb logcat -c
   # per level: settle 5 s, capture per-bin "Fov x/y" / "Fov L R" fields, hold 15 s more
   for l in 0 1 2 3 4; do adb shell setprop debug.oculus.foveation.level $l; sleep 5; adb shell ovrgpuprofiler -t -v > fov_$l.txt; sleep 15; done
   adb logcat -d -s VrApi > vrapi.txt   # "Fov=3" fixed, "Fov=3D" dynamic
   ```
   PowerShell:
   ```powershell
   adb shell setprop debug.oculus.foveation.dynamic 0; adb logcat -c
   foreach ($l in 0..4) { adb shell setprop debug.oculus.foveation.level $l; Start-Sleep 5; adb shell ovrgpuprofiler -t -v > "fov_$l.txt"; Start-Sleep 15 }
   adb logcat -d -s VrApi > vrapi.txt
   ```
   Log App GPU time per level in OVR Metrics. Flat GPU time across levels = the heavy pass is not foveated (intermediate texture, final blit in direct mode, or a Load on the eye buffer; G2-060, G2-061). A single bin covering the whole surface in `ovrgpuprofiler -t -v` = direct mode, no FFR (G2-086). Also log `SystemInfo.foveatedRenderingCaps` (None = unsupported; API needs Unity 2022.3+) before trusting any sweep (GLES3-GF2-006).

7. **Framebuffer-read effects on GLES.** Search compiled GLES shaders (Shader Inspector > Compile and show code, GLES3; or `glShaderSource` in a RenderDoc Meta Fork GL capture) for `_UnityFBInput` (texture `Load` path) vs `gl_LastFragData` / `#extension GL_EXT_shader_framebuffer_fetch` (real fetch) (GLES3-GF1-008, GLES3-GF1-007). In `ovrgpuprofiler -t -v`, the producing surface shows a store stage and the consumer is a separate surface.

## Key numbers

| Item | Value | Applies to | Source |
|---|---|---|---|
| Extensions exposed | Quest 2: 110 GL + 34 EGL (V@0690, 2023); Quest 3: 123 GL + 35 EGL (V@0837, 2026). Conflict GX-C3: G1-015's "157 vs 143" matches neither; use the badges | `Quest 2` `Quest 3` `GLES` | G1-015 / G3-044, GX-C3 [measured] |
| Quest 3 over Quest 2 | +13 GL, +1 EGL extensions | `Quest 3` | G1-015 / G3-044 [measured] |
| Quest reports on gpuinfo | 7 of 8292; newest Quest 2 2023-01-13; no Quest 3S | all | GLES3-GF1-005 [measured] |
| GL_MAX_SAMPLES | 4 (8x MSAA impossible on GLES) | `Quest 2` `Quest 3` `GLES` | G1-007 / G1-010 / G2-035 [measured] |
| GL_MAX_VIEWS_OVR | spec minimum 2; device value not published, read it with the probe | `GLES` | G2-047, KU-21 [doc] |
| Multiview CPU effect | half the draw calls issued; driver records one eye and replays it | `Quest 2` `Quest 3/3S` | G2-050 / G3-045 [doc] |
| Multiview GPU effect | conflict G2-C10: Unity manual says SPI "slightly decreases GPU usage"; UUM-149765 measured no GPU-time difference multi-pass vs multiview on Quest 2/3/3S; OVR_multiview spec allows full per-view duplication. Budget vertex shading at about 2x | `Quest 2` `Quest 3/3S` `Unity 6000.x` | G2-051, G2-C10 [measured] [doc] |
| Multiview vertex saving on Adreno | no published number; measure with a multi-pass vs multiview A/B of ovrgpuprofiler Binning and Render stage times | `Quest 2` `Quest 3/3S` | KU-22 |
| Bin arithmetic under multiview | one bin holds both views: per-view pixels per bin are half a single-view pass. Quest 2 ovrgpuprofiler "135 96x176 bins" = 135 bins of 96x176x2 | `Quest 2` (Quest 3 undocumented, KU-34) | G2-052, G3-047 [doc] |
| FFR gain | Meta cites up to 25% for pixel-heavy apps; simple-shader apps can see a net loss at the low level | `Quest 2` `Quest 3/3S` | G1-044 / G3-053 [doc] |
| FFR levels (setprop) | 0 off, 1 low, 2 medium, 3 high, 4 high-top; set `dynamic 0` first or the level is only a maximum | `Quest 2` `Quest 3/3S` | G2-064 [doc] |
| Framebuffer fetch under 4x MSAA | per-sample shading, up to 4x fragment work without `QCOM_shader_framebuffer_fetch_rate` (derived from sample count, not measured) | `Quest 2` `Quest 3` `GLES` | G3-058 [doc] |
| Framebuffer fetch cost | "expensive", scales per sample; Meta's measurement is Quest 1 / Unity 2018.1.6f1 (stale); no Quest 2/3 number | `GLES` | G2-032 [measured, stale] [verify on device] |
| Anisotropic filtering | a 16x lookup can be 16x slower, paid only where anisotropy occurs; device max not captured (KU-30) | `Quest 2` `Quest 3` | G3-064 [doc] |
| QCOM_shading_rate | per draw, 1x1 to 4x4 | `Quest 2` (V@0582+) `Quest 3` | G3-055 [doc] |
| RGB9_E5 render target | 32 bpp HDR vs 64 bpp RGBA16F | `Quest 3/3S` only | G3-065 [doc] |
| Frame extrapolation | scale 0.5 for every other frame; Qualcomm: "can nearly double" a fragment-bound framerate; not usable by Unity content | `Quest 3/3S` only | G3-062 [doc] |
| Timer query on a binner | about 2-5 us per timed draw per tile; Meta: forces a flush on GLES; Qualcomm: issue inside a render pass; not allowed inside multiview | `GLES` | G2-034 / G3-068, G2-049 [doc]; conflict GX-C9 |

Read [references/extension-matrix.md](references/extension-matrix.md) when you need the full per-extension Quest 2 vs Quest 3 table, the driver build where an extension appeared, the gpuinfo report list, or the native API entry points and spec rules (foveation parameters, tiled rendering, frame extrapolation, MSRTT, timer queries) for a native plugin.

## Fixes, ranked by payoff ÷ effort

### 1. Turn on Multiview on GLES, and smoke-test the release build

- Change: Project Settings > XR Plug-in Management > Oculus > Android > Stereo Rendering Mode = **Multiview** (G2-053). Unity implements it with `GL_OVR_multiview2` plus `GL_OVR_multiview_multisampled_render_to_texture` into a 2-slice array (GLES3-GF2-004, text identical in the 2022.3, 6000.0, 6000.3 and 6000.6 manuals). With the OpenXR Meta Quest feature group multiview is on by default, but that path is Vulkan (G2-055).
- Effect: average render-thread time down (half the draw submissions, G2-050); GPU time about flat (G2-051). Variance: none expected, unless the render thread was the frame-time limiter, in which case fewer late frames.
- Side effects: the MSRTT eye buffer resolves MSAA on tile, so any intermediate pass that samples the eye buffer forces a mid-pass resolve and store (GLES3-GF2-004 notes, G2-028; owned by `gles3-perf:gles-tile-load-store`). Multiview forbids timer queries, geometry/tessellation shaders and multi-view readbacks (G2-049).
- Crash risk: OXPB-144, crash on launch with MultiView + GLES3 in **release** builds (OculusXR 4.2.0; Unity 2022.3.20f1 / 2023.2), Closed Won't Fix (G2-058). Pin a known-good OculusXR version and launch-test a release build on each headset, not only development builds.
- Tags: `Quest 2` `Quest 3/3S` `Unity 2021.3-6000.6` `OculusXR 4.x` `GLES` - **Throughput** (and **Consistency** for the crash check).

### 2. Make every custom shader follow the SPI/multiview macro contract

Missing macros render slice 0 only (left eye); they do not show as a perf regression (G2-054). Stereo shaders carry an eye index into varyings, which needs `OVR_multiview2` semantics on GLES (G2-048, inferred from the macros [verify on device]). URP ShaderLibrary form (URP 14 / Unity 2022.3 and URP 17 / Unity 6); the built-in pipeline's `UNITY_DECLARE_SCREENSPACE_TEXTURE` / `UNITY_SAMPLE_SCREENSPACE_TEXTURE` correspond to `TEXTURE2D_X` / `SAMPLE_TEXTURE2D_X` here:

```hlsl
Shader "Custom/StereoSafeUnlit"
{
    Properties { _BaseColor ("Color", Color) = (1,1,1,1) _FresnelPow ("Fresnel Power", Float) = 4 }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "Unlit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            TEXTURE2D_X(_ScreenTex);           // eye targets are texture arrays under multiview
            SAMPLER(sampler_ScreenTex);

            CBUFFER_START(UnityPerMaterial)    // SRP Batcher compatible
                half4 _BaseColor;
                half  _FresnelPow;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                half3  normalWS   : TEXCOORD0;
                half3  viewDirWS  : TEXCOORD1;  // per-eye output: needs multiview2 on GLES
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                VertexPositionInputs p = GetVertexPositionInputs(input.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.normalWS   = (half3)TransformObjectToWorldNormal(input.normalOS);
                o.viewDirWS  = (half3)GetWorldSpaceViewDir(p.positionWS);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);   // before any TEXTURE2D_X sample
                float2 uv = GetNormalizedScreenSpaceUV(i.positionCS);
                half3 screen = SAMPLE_TEXTURE2D_X(_ScreenTex, sampler_ScreenTex, uv).rgb;
                half f = pow(1.0h - saturate(dot(normalize(i.normalWS), normalize(i.viewDirWS))), _FresnelPow);
                return half4(lerp(_BaseColor.rgb, screen, f), 1.0h);
            }
            ENDHLSL
        }
    }
}
```

- Effect: correctness prerequisite for fix 1; no frame-time change by itself.
- Tags: `Quest 2` `Quest 3/3S` `URP 14+` `GLES` `Vulkan` - **Throughput** (keeps multiview usable).

### 3. Never profile GLES multiview CPU cost in a development build with error spam

- Change: run Diagnose step 5; if errors stream, take CPU timings (OVR Metrics Tool App CPU) from a non-development build and use the development build only for the Profiler hierarchy. UUM-102876: OculusXR 4.4.0 + Multiview + GLES on Unity 6000.0.33f1, continuous `GL_INVALID_OPERATION` on Quest 2/3 with FPS drops, Closed Won't Fix (G2-057 / G3-046). In the spec, multiview INVALID_OPERATION is a program-vs-FBO view-count mismatch (G2-047).
- Effect: removes a measurement artefact (inflated, spiky render-thread time) rather than shipping cost.
- Tags: `Quest 2` `Quest 3` `Unity 6000.0` `OculusXR 4.4.0` `GLES` - **Consistency**.

### 4. Keep the GLES main pass foveatable

On Quest GLES, FFR is a property of the swapchain texture set by the runtime through `QCOM_texture_foveated` per array layer (G2-059, G2-061). It only foveates rendering done directly into that texture. GLES-specific rules (spec rev 5, G2-060):

- Render the main pass straight into the eye texture: no intermediate colour target, no URP final blit. A two-pass Unity GLES pipeline gets **no** FFR, because the final full-screen pass (no depth, no MSAA) runs in direct mode, which also disables FFR (G2-061, G2-086). Which URP settings create the intermediate texture: `quest-perf:quest-resolution-foveation` and `unity-perf:unity-urp-settings`.
- Clear or invalidate every attachment at pass start; a Load on the foveated attachment makes the driver unresolve it and can silently disable FFR for that pass (issue 7). Depth inherits foveation; invalidate it at the end (store rules: `gles3-perf:gles-tile-load-store`).
- Avoid geometry/tessellation shaders and compute inside the foveated pass; they may disable foveation (issue 9).
- Screen-space effects inside a foveated pass see uncorrected dFdx/dFdy, `interpolateAtOffset` and `gl_SamplePosition` (only `gl_FragCoord` is scaled): expect derivative-driven mip or edge artefacts in the periphery.
- Level control: `OVRManager.foveatedRenderingLevel` (and `useDynamicFoveatedRendering`, level becomes a maximum) on the OculusXR path (G1-044 / G3-053). Dynamic foveation through Unity's OpenXR plugin is documented Vulkan-only (OpenXR 1.19+; GLES3-GF2-006).
- Effect: GPU time down in pixel-heavy scenes, up to 25% per Meta (G1-044); no variance effect. Quality: peripheral blockiness.
- Conflict (surface, do not resolve): Q3-039 (quest.md) says no current Meta/Unity doc documents GLES FFR for URP and treats it as unsupported for new work; gles3.md documents it at driver and OculusXR level with the caveats above (G1-044, G2-059 to G2-062). Static FFR on GLES + OpenXR is off-document (GX-C8, KU-10). Trust only the Diagnose step 6 sweep [verify on device].
- Tags: `Quest 2` `Quest 3/3S` `OculusXR 4.x` `GLES` - **Throughput**.

### 5. Budget vertex work at about 2x under multiview

- Change: size LODs, vertex counts and vertex-shader cost as if both eyes were shaded (G2-051, G2-C10). Binning (vertex position work) is a large share of eye-buffer time on Quest 3/3S (UUM-149765: 4.5 ms of 9.7 ms on GLES without MSAA; G2-087, owned by `gles3-perf:gles-tile-load-store`). Hardware side: `arm-mobile-hw-perf:xr2-adreno-architecture` (whether multiview shares the binning pass is ARM-C23, open).
- Effect: GPU average down when vertex/binning bound (render scale 0.01 test leaves GPU time unchanged; `quest-perf:quest-triage`). No published multiview-specific number (KU-22). Variance: none expected unless binning spikes with camera direction.
- Quality: fewer vertices, LOD pops.
- Tags: `Quest 2` `Quest 3/3S` `GLES` - **Throughput**.

### 6. Do not rely on framebuffer fetch or input attachments on GLES

- Fact: on URP 17 (master branch), `PLATFORM_SUPPORTS_NATIVE_RENDERPASS` is defined in Vulkan.hlsl and not in GLES3.hlsl, so `FRAMEBUFFER_INPUT_*` compiles to `TEXTURE2D_FLOAT(_UnityFBInputN)` read with `.Load()` on GLES: an ordinary texture read of a stored target, not `gl_LastFragData` (GLES3-GF1-008; resolves GX-C6; older URP [verify on device]). Native RenderPass has no effect on GLES (G2-022).
- Consequence: every URP pass that reads an input attachment on GLES costs a store of the producer and a sample in the consumer (GLES3-GF1-008 notes).
- Change: on a GLES build, replace read-the-framebuffer effects with fixed-function blending, or fold them into the producing pass. If a custom shader uses Unity's framebuffer-fetch syntax, HLSLcc will emit `#extension GL_EXT_shader_framebuffer_fetch` (GLES3-GF1-007): that is coherent fetch, "expensive" and per-sample under MSAA, and it disables LRZ (G2-032, G2-083). Compare App GPU time against a blend-state version of the same effect [verify on device]. `QCOM_shader_framebuffer_fetch_rate` / `_noncoherent` would fix per-sample cost and per-primitive sync, but Unity does not document enabling either (G3-057, G3-058).
- Effect: removes a store + load per affected pass (DRAM traffic, GPU average); no published number, measure the surface's store stage in `ovrgpuprofiler -t -v`. Variance: none.
- Quality: effects needing true framebuffer reads (programmable blend) must be approximated with fixed-function blending.
- Tags: `Quest 2` `Quest 3/3S` `URP 17` (older [verify on device]) `GLES` - **Throughput**.

### 7. Cap anisotropic filtering where it is not visible

- Change: Texture import > Aniso Level per texture, or Project Settings > Quality > Anisotropic Textures. `EXT_texture_filter_anisotropic` is on both headsets; Qualcomm: a 16x lookup can be 16x slower where anisotropy occurs (G3-064).
- Effect: GPU average down on oblique, texture-heavy surfaces; no Quest number, measure `% Texture L1 Miss` and App GPU time. Quality: blur on grazing-angle floors.
- Tags: `Quest 2` `Quest 3/3S` `GLES` `Vulkan` - **Throughput**.

### 8. Gate every native-plugin extension on a runtime check

- Change: in native code, walk `glGetStringi(GL_EXTENSIONS, i)` once at init and branch; never hardcode per headset. Quest 2 went from 99 to 110 GL extensions across OS updates; Quest 3 gained `GL_EXT_clear_texture` only in the 2026 driver (G1-015, G3-071).
- Effect: avoids GL errors or crashes on a driver that lacks an extension; no average-frame-time change. Quality cost: none.
- Tags: `Quest 2` `Quest 3/3S` `GLES` - **Consistency**.

### 9. Native-plugin-only extensions: low payoff ÷ effort, measure before building

Each needs a native rendering plugin, has no documented Unity path and no published Quest gain. Try only when a capture points at the exact cost.

- `EXT_texture_compression_astc_decode_mode` (Quest 2 V@0690+, Quest 3): decode LDR ASTC to UNORM8 instead of RGBA16F, less texture-cache footprint and power (G3-063). Measure `ovrgpuprofiler -r5,6` texture L1 miss. GPU average only. Quality: UNORM8 precision loss, LDR only. `Quest 2` `Quest 3/3S` `GLES` - **Throughput**.
- `QCOM_shading_rate` (per draw, both) / `EXT_fragment_shading_rate` (+_attachment, +_primitive; Quest 3 only): coarse shading for low-frequency draws; combines with foveation per Qualcomm (G3-055, G3-056). Unity may drive neither on GLES; read `SystemInfo.foveatedRenderingCaps` (Unity 2022.3+) [verify on device]. GPU average only. Quality: coarse-shading blur on the affected draws. `Quest 2` (V@0582+) `Quest 3/3S` `GLES` - **Throughput**.
- `QCOM_texture_foveated2` cutoff density: discards pixels below a density (G3-051). Runtime-owned on the swapchain; app use undocumented. GPU average only, no variance effect. Quality: discarded peripheral pixels. `Quest 2` (V@0582+) `Quest 3/3S` `GLES` - **Throughput**.
- `QCOM_render_shared_exponent` RGB9_E5 HDR target, half the bytes of RGBA16F; no Unity mapping documented (G3-065). Bandwidth / GPU average. Quality: 9-bit mantissa, no alpha. `Quest 3/3S` `GLES` - **Throughput**.
- `QCOM_texture_lod_bias` (Quest 3 only): positive bias may speed filtering; unknown whether `Texture.mipMapBias` maps to it (G3-066) [verify on device]. GPU average. Quality: blur. `Quest 3/3S` `GLES` - **Throughput**.
- `EXT_buffer_storage` persistent coherent maps for native vertex/constant streaming (G3-070); streaming strategy is owned by `gles3-perf:gles-driver-overhead`. CPU average; may reduce map/sync stalls [verify on device]. `Quest 2` `Quest 3/3S` `GLES` - **Throughput**, **Consistency**.

## Verify

- **Multiview (fix 1):** draw calls per frame halve (Frame Debugger); render-thread time drops (Unity Profiler, same scene, same levels; take absolute ms from OVR Metrics Tool App CPU in a non-development build). App GPU time in OVR Metrics should stay within noise (UUM-149765 found no GPU difference). Capture 60 s of a fixed camera path per variant. Then run the release build 20-30 min on Quest 2 and Quest 3/3S for launch and stability (OXPB-144).
- **Macro contract (fix 2):** both eyes render in the headset and in a RenderDoc Meta Fork capture both array slices are written; no frame-time change expected.
- **GL errors (fix 3):** zero `INVALID_OPERATION` lines over a 5-minute logcat of the development build, or CPU numbers taken from OVR Metrics Tool App CPU in a non-development build.
- **FFR (fix 4):** in the setprop sweep (20 s per level), App GPU time should drop at levels 2-4 in pixel-heavy scenes (up to 25%, G1-044). Level 1 may be flat or slightly worse in simple-shader apps. Flat at every level = not foveated. `Fov` fields non-zero in `fov_<level>.txt` for the eye-buffer surface; VrApi `Fov=` matches the set level.
- **Vertex budget (fix 5):** ovrgpuprofiler Binning stage time on the eye-buffer surface drops with vertex count; compare to the Render stage over a 60 s capture.
- **Framebuffer reads (fix 6):** one fewer surface or store stage per removed input-attachment read in `ovrgpuprofiler -t -v`; App GPU time down by an amount you must measure (no published number).
- **Extension probe:** the logged list is saved per headset and OS build next to the `dumpsys SurfaceFlinger` driver line; re-run after every Horizon OS update.

## Pitfalls and myths

- **"Multiview halves GPU time."** Wrong on Quest GLES as measured: the saving is CPU-side (G2-050). G2-C10 conflict: Unity's manual claims a slight GPU decrease; UUM-149765 measured none; the spec allows full duplication. Budget vertex work at 2x.
- **"Use OpenXR for GLES multiview."** The OpenXR plugin (1.5-1.16.1) lists Quest as Vulkan-only, and Symmetric Projection, Optimize Buffer Discards and Multiview Render Regions are Vulkan-only (G2-055). Unity 6000.x GLES repros use OculusXR (G2-C8), deprecated from 6.5 (G1-024 / G2-093). `VK_QCOM_multiview_per_view_viewports` / `_render_areas` (MRR) have no GL equivalent (G3-047 notes).
- **"Dev build works, so release works."** OXPB-144 crashes release builds only (G2-058).
- **"Framebuffer fetch keeps URP passes on tile on GLES."** Not with URP's library: `FRAMEBUFFER_INPUT` becomes `.Load()` on GLES (GLES3-GF1-008). And real coherent fetch is expensive per sample under MSAA (G2-032, Quest 1 era).
- **Mali pixel-local-storage advice.** `EXT_shader_pixel_local_storage` and `EXT_shader_framebuffer_fetch_non_coherent` are absent on both headsets (G3-057).
- **"Force binned or direct mode with `QCOM_binning_control`."** Not exposed on Quest 2 or Quest 3 (G2-092). FlexRender's choice is not controllable; only avoid its triggers (`arm-mobile-hw-perf:xr2-adreno-architecture`).
- **`QCOM_tiled_rendering` for manual tile control.** 2009 extension, no Unity use, mixing with normal rendering can double resolve cost (G2-091 / G3-061). Ignore for Unity.
- **"`QCOM_frame_extrapolation` is AppSW on GLES."** No Meta or Unity doc ties them; AppSW is Vulkan-only (G1-015, G3-062). `quest-perf:quest-appsw`.
- **"The extension exists, so Unity uses it."** Driver presence of `QCOM_texture_foveated_subsampled_layout`, VRS or clip control does not mean Unity drives it: subsampled layout needs Vulkan in Unity (G1-035 / G3-052); Unity GLES keeps -1..1 depth and no reversed Z despite `EXT_clip_control` (G3-035, G3-067).
- **"GL timer queries for per-pass cost."** They sum all bins, cost 2-5 us per timed draw per tile, force a flush on GLES and are illegal inside multiview (G2-034 / G3-068; conflict GX-C9 with Qualcomm's advice). Use ovrgpuprofiler stages (`gles3-perf:gles-vs-vulkan`).
- **Stale Meta native guidance.** The VrApi-era "query `VRAPI_SYS_PROP_MULTIVIEW_AVAILABLE` because of driver issues" (G2-050 notes) and the deprecated VrApi FFR page (Mobile SDK unsupported since 2022-08-31; G1-044) are pre-2023.
- **Context priority.** `EGL_NV_context_priority_realtime` is Quest 3 only; reading the render-stage "Preempt" as the compositor interrupting the app is an inference (G3-069). Preempt time is not app-controllable.
- **Extension counts from G1-015 ("157 vs 143").** Use the report badges, 158 vs 144 including EGL (GX-C3).

## Sources

All accessed 2026-09-24.

- https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview2.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview_multisampled_render_to_texture.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated2.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shading_rate.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_fragment_shading_rate.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shader_framebuffer_fetch_noncoherent.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shader_framebuffer_fetch_rate.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_shader_framebuffer_fetch.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_tiled_rendering.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_binning_control.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_frame_extrapolation.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_texture_compression_astc_decode_mode.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_render_shared_exponent.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_lod_bias.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_clip_control.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_buffer_storage.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_disjoint_timer_query.txt [doc]
- https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_FB_foveation.html [doc]
- https://opengles.gpuinfo.org/displayreport.php?id=6387 [measured]
- https://opengles.gpuinfo.org/displayreport.php?id=8023 [measured]
- https://opengles.gpuinfo.org/displayreport.php?id=7475 [measured]
- https://opengles.gpuinfo.org/displayreport.php?id=5092 [measured]
- https://opengles.gpuinfo.org/backend/reports.php [measured]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://developers.meta.com/horizon/documentation/unity/enable-multiview/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ [measured] (Quest 1, stale)
- https://developers.meta.com/horizon/documentation/unity/unity-fixed-foveated-rendering/ [doc]
- https://developers.meta.com/horizon/documentation/unity/os-fixed-foveated-rendering/ [doc]
- https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ [doc]
- https://developers.meta.com/horizon/documentation/native/android/mobile-multiview/ [doc] (VrApi era, stale)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/Android-SinglePassStereoRendering.html [doc]
- https://docs.unity3d.com/2022.3/Documentation/Manual/Android-SinglePassStereoRendering.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/SinglePassInstancing.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/SinglePassStereoRendering.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsMultiview.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-foveated-rendering-support.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/oculus-plugin.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/foveatedrendering.html [doc]
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl [doc] (source code)
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/GLES3.hlsl [doc] (source code)
- https://github.com/Unity-Technologies/HLSLcc/blob/master/src/toGLSL.cpp [doc] (source code snapshot)
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [measured]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102876 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=OXPB-144 [community]
