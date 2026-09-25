---
name: gles-driver-overhead
description: "CPU-side OpenGL ES driver cost on Quest: state-change and program-switch overhead, uniform buffer limits, buffer streaming and orphaning, instancing and indirect draws, fences, compute interleaving, and Unity's GLES low-overhead options. Use when a GLES build is render-thread-bound, when GL draw or state calls dominate a trace, or when porting native GLES code paths to Quest."
---

# GLES driver and state overhead on Quest (Adreno)

Scope: Unity projects shipping OpenGL ES 3.x on Quest 2 (Adreno 650) and Quest 3/3S (Adreno 740). The GLES XR path in Unity is the Oculus XR plugin 4.x (Project Settings > XR Plug-in Management > Oculus, Android tab). Q4-056 lists it for Unity 2021.3-6.4; G1-024 / G2-093 apply it to Unity 2021.3-6000.6, deprecated but not stated as removed from 6.5, and Unity's OpenXR plugin documents Quest as Vulkan-only (G1-024 / G2-093, G2-C8). Treat every GLES-specific lever here as having a limited shelf life.

Goals served: Throughput (render-thread ms per frame) and Consistency (implicit sync stalls, fence waits and flushes that produce p99 spikes).

## When to use / when not

Use when:
- The build's primary Android graphics API is `OpenGLES3` and the render thread (`UnityGfxDeviceWorker` / `UnityGfx`) is the long pole.
- A RenderDoc GL call trace shows many program binds, per-draw uniform/buffer uploads, `glClientWaitSync`, or compute dispatches between draws.
- You are porting a native GLES plugin or renderer path (buffer streaming, fences, indirect draws) into a Quest app.
- You are deciding whether to turn on Low Overhead Mode.

When not:
- Cause of the slowdown still unknown: `quest-perf:quest-triage`.
- Reducing draw count or SetPass calls with SRP Batcher, static batching, instancing, BRG, GRD: `unity-perf:unity-draw-calls-batching`.
- Main-thread scripting, GC, graphics jobs, multithreaded rendering settings: `unity-perf:unity-cpu-scripting`.
- Whether to be on GLES at all: `gles3-perf:gles-vs-vulkan`.
- Load/store, invalidates, pass splits from readbacks and `glFlush`: `gles3-perf:gles-tile-load-store`.
- Program-link and first-use shader hitches on GLES: `gles3-perf:gles-shader-binaries`.
- Binning-pass hardware, vertex cache, compute/LPAC internals: `arm-mobile-hw-perf:xr2-adreno-architecture`.
- ALU/register cost of a shader: `arm-mobile-hw-perf:xr2-shader-cost-model`.
- What the ovrgpuprofiler counters mean in depth: `arm-mobile-hw-perf:xr2-gpu-counters-sdp`.
- Oculus XR vs OpenXR plugin choice as a whole: `quest-perf:quest-sdk-choices`.

## Diagnose first

1. **Prove the render thread is the long pole, not game logic or GPU.**
   - `adb logcat -s VrApi`: render-thread CPU time is roughly `CPU&GPU - App` (Q1-032). If that difference is near the frame budget while `App` GPU time has headroom, you are render-thread-bound.
   - Perfetto (MQDH, add the package under ATrace Apps): `UnityGfx` slices running past budget with no `FenceChecker::Wait` = CPU/render-thread-bound; fence waits = GPU-bound (Q1-052, G3-082).
   - Unity Profiler (development build): `cpuRenderThreadFrameTime = RenderLoop - Gfx.PresentFrame` (U5-090). Do not use `FrameTimingManager` for this on XR: it does not measure render-thread time on GLES or Vulkan XR (U5-090). `Gfx.WaitForPresentOnGfxThread` inside `Camera.Render` means render-thread-bound, inside `Gfx.PresentFrame` means GPU-bound (U5-082) (Unity documents these as non-XR marker semantics; on XR confirm with `CPU&GPU - App` from VrApi or Perfetto).
   - Meta's camera-off test: disable cameras; if frame time barely moves, CPU-bound. Turn Multithreaded Rendering off while debugging so render cost is visible on one thread (U3-001 / U5-083) (camera-off also removes culling cost; re-enable Multithreaded Rendering before shipping, U5-039 / A1-061).
2. **Separate Unity-side batching cost from GL driver cost.** Rendering Statistics / Frame Debugger: SetPass count is state changes, draw count is submissions (U3-002). High SetPass with modest draws points at program/material switches (this skill, fix 2). High draws with low SetPass points at instancing/batching (`unity-perf:unity-draw-calls-batching`). Note the SRP Batcher is single-threaded on GLES (U3-013).
3. **Look at the GL stream itself.** RenderDoc Meta Fork, development build (G3-073). Settings: Tools > Settings > Replay optimisation level = Fastest, otherwise RenderDoc's inserted GL commands appear as phantom work (G3-076). Count per eye pass: `glUseProgram`, `glBindBufferRange`/`glBufferSubData`/`glMapBufferRange`, `glFenceSync`/`glClientWaitSync`, `glDispatchCompute*` positions relative to draws, `glFlush`. Use `--frame-number` (RenderDoc Meta Fork 68.18+, Horizon OS 68+) for repeatable A/Bs (GLES3-GF1-004).
4. **GPU-side symptoms of driver-side problems** (ovrgpuprofiler, detailed mode needs an app restart):
   ```sh
   adb shell setprop debug.oculus.cpuLevel 3     # lock clocks for A/B only [verify on device]
   adb shell setprop debug.oculus.gpuLevel 3
   adb shell ovrgpuprofiler -e                   # then restart the app
   adb shell ovrgpuprofiler -t 2 -v              # per-surface Mode, Binning/Render stage times
   adb shell ovrgpuprofiler -m                   # list metric ids, then -r<ids> to stream
   ```
   Level-lock recipe is from a Unity QA report, [community] (G2-010). Read: `% CP Overhead` (should be near 0, never above 20%; G3-087); Binning share of the eye surface (10-20% normal, 30% usually too much; G3-079); surface Mode 0/2 (Direct/SwBinning) on the eye buffer where 1 (HwBinning) is expected, a direct-mode trigger being high VS-texture-sample-to-vertex ratio (G3-080, G2-078).

## Key numbers

| Number | Meaning | Source | Applies to |
|---|---|---|---|
| +64% per-draw CPU time | material switch, same shader | G2-065, po-draw-call-analysis [measured] | Quest 1, Unity 2018.1.6f1, GLES; ratios only [verify on device] |
| +175% per-draw CPU time | shader (program) switch | G2-065 [measured] | same; stale (2018) |
| ~25% of a new object | cost of redrawing the same object | G2-065 [measured] | same |
| 7372 B | max sum of all UBOs referenced by one shader to stay in constant RAM (0.9 × 8 KB) | G2-070, A2-074, Qualcomm [doc] | Adreno generic; `Quest 2` `Quest 3/3S` [verify on device] |
| 65536 B | `GL_MAX_UNIFORM_BLOCK_SIZE` (correctness limit only) | G2-070, gpuinfo reports | `Quest 2` `Quest 3` |
| 14 / 14 / 84 | max vertex / fragment / combined uniform blocks | G2-069, gpuinfo | `Quest 2` `Quest 3` |
| 16 UBOs, 16 textures+SSBOs, 32 vertex buffers, each multiple of 2000 instructions; samplers at N = 16 (A6x-A8x) | possible per-shader perf cliffs | G2-069 / G3-037 / G3-038 | Adreno 7x = `Quest 3/3S` |
| 65535 vertices | max per mesh to keep `IndexFormat.UInt16` | G2-076 | all |
| 32 four-component vertices | A7x vertex cache holds 32 four-component vertices | G2-076, Qualcomm spec sheets | `Quest 3/3S` |
| ≥ 64 | indirect compute workgroup size; smaller forces a CPU wait (command-buffer flush) | G2-080, Qualcomm [doc] | `GLES` 3.1+ [verify on device] |
| 10-20% (30% too much) | binning time as share of render pass | G3-079 | Adreno generic |
| near 0, never > 20% | `% CP Overhead` | G3-087 | Adreno generic |
| no published number | Low Overhead Mode render-thread saving | G1-069 | measure with the draw sweep in Verify |
| no published number | post-2018 per-state-change cost on Quest 2/3 GLES | KU-23 | measure with the draw sweep in Verify |
| no published number | Adreno GLES vs Vulkan driver CPU overhead | G1-068, KU-07 | Meta's 2020 "about 10% CPU render cost" for Vulkan is stale (G1-047); owned by `gles3-perf:gles-vs-vulkan` |

Full state-cost detail, GL limits per headset, the streaming-option matrix and the Unity API to GL call mapping: read [references/state-costs.md](references/state-costs.md) when you need per-limit values, a native streaming design, or the open questions with their measurement methods.

## Fixes, ranked by payoff ÷ effort

### 1. Turn on Low Overhead Mode (GLES validation off)

- **Change:** Project Settings > XR Plug-in Management > Oculus (Android tab) > Low Overhead Mode = on (Q4-056). It makes the GLES driver skip validation, Unity's equivalent of `GL_KHR_no_error`; both Quest 2 and Quest 3 expose `GL_KHR_no_error` and `EGL_KHR_create_context_no_error` (G1-043 / G2-079). Oculus docs: "Disable this if you experience graphics instabilities" (Q2-077).
- **Effect:** lowers average render-thread time; no variance effect documented. No ms figure is published (G1-069).
- **Cost / side effects:** UUM-102878: OES external textures (video player, camera feeds) render black with Low Overhead Mode in release builds, Closed Won't Fix [community]. Validation errors become undefined behaviour, so keep it off in development builds you debug with.
- **Does nothing on Vulkan** (Q2-077). No OpenXR equivalent was found in the OpenXR Meta feature list; migrating to OpenXR may lose this saving (KU-43) [verify on device].
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `Oculus XR 1.4.0+` (Q4-057) `Unity 2021.3-6.6 (deprecated, not removed, from 6.5)` (Q4-056 lists 2021.3-6.4; G1-024 applies to 6.5-6.6 as deprecated, not removed). Goal: **Throughput**.

Editor audit (paste into an `Editor/` folder; compiles on 2021.3+; reads the setting by serialized name so it does not depend on the plugin's C# field name):

```csharp
#if UNITY_EDITOR
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class GlesOverheadAudit
{
    [MenuItem("Tools/Perf/GLES Overhead Audit")]
    static void Run()
    {
        var apis = PlayerSettings.GetGraphicsAPIs(BuildTarget.Android);
        var primary = apis.FirstOrDefault();
        Debug.Log($"[GLES audit] Android primary graphics API: {primary}");
        if (primary != GraphicsDeviceType.OpenGLES3)
            Debug.Log("[GLES audit] Not on GLES: Low Overhead Mode has no effect.");

        // Oculus XR settings asset (only present when the Oculus XR plugin is installed).
        foreach (var guid in AssetDatabase.FindAssets("t:OculusSettings"))
        {
            var asset = AssetDatabase.LoadMainAssetAtPath(AssetDatabase.GUIDToAssetPath(guid));
            var so = new SerializedObject(asset);
            var it = so.GetIterator();
            while (it.NextVisible(true))
                if (it.name.IndexOf("LowOverhead", System.StringComparison.OrdinalIgnoreCase) >= 0
                    && it.propertyType == SerializedPropertyType.Boolean)
                    Debug.Log($"[GLES audit] {asset.name}.{it.name} = {it.boolValue}");
        }

        // Models forced to 32-bit indices although they would fit 16-bit (fix 6).
        foreach (var guid in AssetDatabase.FindAssets("t:Model"))
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            if (AssetImporter.GetAtPath(path) is ModelImporter mi
                && mi.indexFormat == ModelImporterIndexFormat.UInt32)
                Debug.LogWarning($"[GLES audit] 32-bit indices forced: {path} (use Auto or UInt16 if every mesh has ≤ 65535 vertices)", mi);
        }
    }
}
#endif
```

### 2. Cut program switches first, then material switches

- **Change:** order and author content so the GL stream changes program least often: shader first, then material, then mesh (G2-065). Qualcomm: minimise pipeline (program) switches to avoid internal synchronisation (G2-067). Practical levers: fewer shader variants per frame, a small set of uber shaders (U3-007), SRP Batcher-compatible materials so switches become cheap cbuffer binds. The Unity-side mechanics (SRP Batcher, sorting, instancing) are in `unity-perf:unity-draw-calls-batching`.
- **Why program first:** +175% vs +64% per draw in Meta's study (G2-065). More textures on the changed material cost more; texture size, filtering and compression have negligible CPU cost (G2-065). Adreno drivers do not recompile programs because GL state changed, so blend/depth state changes do not cause hitches here (G3-007 / G2-068).
- **Effect:** average render-thread time; indirectly Consistency when a scene's variant count spikes. Quality cost: none if merged shaders keep the same features; uber shaders can raise ALU/register cost (`arm-mobile-hw-perf:xr2-shader-cost-model`).
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` (ratios measured on Quest 1, [verify on device]). Goal: **Throughput**.

### 3. Keep each shader's UBO footprint under 7372 B and avoid dynamic indexing

- **Change:** the sum of `UnityPerDraw` + `UnityPerMaterial` + global/light cbuffers referenced by one shader should stay under 7372 B (G2-070, A2-074). Beyond that the compiler maps only portions it can prove are accessed, and dynamic indexing defeats this. Instancing arrays indexed by `unity_InstanceID` are dynamic indexing, the worst case (G2-070). `half` in a cbuffer still takes 32-bit size and alignment, so it does not shrink the UBO (G3-033). Pack scalars into `float4` (A2-074).
- HLSL, URP 14+ (2022.3) to URP 17 (6000.x), SRP Batcher-compatible, lean per-material block:

```hlsl
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

TEXTURE2D(_BaseMap);  SAMPLER(sampler_BaseMap);

CBUFFER_START(UnityPerMaterial)
    float4 _BaseMap_ST;
    half4  _BaseColor;          // still 16 B in the UBO: half does not save cbuffer bytes (G3-033)
    float4 _Params;             // x: cutoff, y: smoothness, z: metallic, w: wind frequency (used in fix 6) (pack scalars, A2-074)
    // Avoid: float4 _Palette[128];  2 KB, and indexing it by a varying defeats partial mapping (G2-070)
CBUFFER_END
```

- **Measure the footprint:** no Quest-specific tool output is published; check with the Adreno Offline Compiler on the GLSL Unity emits (G2-070 notes; `arm-mobile-hw-perf:xr2-gpu-counters-sdp`).
- **Effect:** GPU-side constant fetch efficiency, not render-thread CPU; serves average frame time. Quality cost: none.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `URP 14+` [verify on device]. Goal: **Throughput**.

### 4. Collapse repeated draws into instanced or indirect draws

- **Change:** draw repeated meshes with one GLES 3.0 `glDrawElementsInstanced` (or `glDrawArraysInstanced`) instead of N `glDrawElements`; on GLES 3.1 use `glDrawElementsIndirect` / `glDrawArraysIndirect` with the arguments cached in a buffer at load time. Qualcomm lists maximising indirect draws as a best practice (G2-075). Unity side (mapping to GL calls is inferred, G2-075): `Graphics.RenderMeshInstanced` / `Graphics.RenderMeshIndirect` and material GPU instancing (Enable GPU Instancing on the material); availability of these APIs varies by Unity version (G2-075).
- **Interaction with fix 3:** instancing arrays indexed by `unity_InstanceID` are dynamic indexing and push the UBO past 7372 B (G2-070). Keep the per-instance payload small.
- **Effect:** fewer GL submissions: lower average render-thread time. No published ms figure; measure with the draw sweep in Verify. Quality cost: none; per-instance variation must move into instance data.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` 3.0 (instanced) / 3.1+ (indirect) [verify on device]. Goal: **Throughput**. Which Unity batching path to pick: `unity-perf:unity-draw-calls-batching`.

### 5. Stream dynamic buffers without implicit sync

- **Change (Unity content):** batch **all** buffer updates for a frame before any draw that uses them; interleaving update, draw, update, draw can make the driver keep several copies of the entire VBO (G2-072). In practice: update dynamic meshes and `GraphicsBuffer`s in one place (for example `LateUpdate` or one early `ScriptableRenderPass`), not from per-object render callbacks. Call `Mesh.MarkDynamic()` on meshes rewritten every frame (G2-073). For structured data use `LockBufferForWrite`, which makes fewer copies than `SetData`; write linearly, never read (write-combined memory), and the GPU may only read that buffer (G2-073):

```csharp
using Unity.Collections;
using UnityEngine;

public sealed class StreamedInstanceData : MonoBehaviour
{
    const int k_Count = 1024;
    GraphicsBuffer m_Buffer;

    void OnEnable()
    {
#if UNITY_2022_3_OR_NEWER
        m_Buffer = new GraphicsBuffer(GraphicsBuffer.Target.Structured,
            GraphicsBuffer.UsageFlags.LockBufferForWrite, k_Count, sizeof(float) * 4);
#endif
    }

    void LateUpdate()   // all writes for the frame, before rendering starts (G2-072)
    {
#if UNITY_2022_3_OR_NEWER
        NativeArray<Vector4> dst = m_Buffer.LockBufferForWrite<Vector4>(0, k_Count);
        for (int i = 0; i < k_Count; i++)                 // linear writes only, never read dst
            dst[i] = new Vector4(i, Time.time, 0f, 1f);
        m_Buffer.UnlockBufferAfterWrite<Vector4>(k_Count);
#endif
    }

    void OnDisable() { m_Buffer?.Release(); m_Buffer = null; }
}
```

  The first Unity version with `LockBufferForWrite` was not verified (G2-073); the guard assumes 2022.3 [verify on device]. Unity does not document which GL calls its GLES backend uses for these paths (KU-19).
- **Change (native plugin):** pick one of: orphan (`glBufferData(NULL, same size, same usage)` or `glMapBufferRange` with `GL_MAP_INVALIDATE_BUFFER_BIT`); ring buffer with `GL_MAP_UNSYNCHRONIZED_BIT` and non-overlapping writes, orphan on wrap; or persistent mapping via `GL_EXT_buffer_storage` (exposed on Quest 2 and 3) with a fence per region (G2-071, G3-070). See the conflict in fix 7 before choosing the fenced option.
- **Effect:** removes implicit CPU/GPU sync, which is mostly a **Consistency** win (render-thread stalls show as spikes), plus lower average CPU time and memory from avoided VBO copies. Quality cost: none; ring buffers cost memory for frames in flight.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `Unity ≥ 2022.3`. Goal: **Consistency**, **Throughput**.

### 6. Feed the binning pass: position-only stream, 16-bit indices, no VS texture fetches

- **Change:** position alone in stream 0, other attributes interleaved in stream 1, packed formats (`GL_HALF_FLOAT` attributes, `GL_INT_2_10_10_10_REV` normals). The binning pass runs a position-only vertex shader and then reads the smallest stream (G2-077 / G3-036). Unity's stream mapping is an inference, and whether the importer splits streams by default is undocumented (G2-077) [verify on device].

```csharp
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

public static class BinningFriendlyMesh
{
    [StructLayout(LayoutKind.Sequential)]
    struct Attr // stream 1 (28 B): Normal (12 B), Tangent half4 (8 B), Color unorm8x4 (4 B), UV0 half2 (4 B)
    {
        public Vector3 n;
        public ushort tx, ty, tz, tw;
        public byte r, g, b, a;
        public ushort u, v;
    }

    // Mesh must be Read/Write enabled. Call once at load on the runtime mesh.
    // Drops any attribute not listed; do not use on skinned meshes.
    public static void SplitPositionStream(Mesh mesh)
    {
        bool extraUV = false;
        for (var a = VertexAttribute.TexCoord1; a <= VertexAttribute.TexCoord7; a++)
            extraUV |= mesh.HasVertexAttribute(a);
        if (mesh.HasVertexAttribute(VertexAttribute.BlendWeight) || extraUV)
        { Debug.LogWarning($"{mesh.name}: skinned or uses UV1+; not split (attributes would be dropped)"); return; }

        var pos = mesh.vertices; var nrm = mesh.normals; var tan = mesh.tangents;
        var col = mesh.colors32; bool hasCol = col.Length == pos.Length;
        var uv = new List<Vector2>(); mesh.GetUVs(0, uv);
        int n = pos.Length;
        if (nrm.Length != n || tan.Length != n || uv.Count != n)
        { Debug.LogWarning($"{mesh.name}: needs normals, tangents and UV0"); return; }

        var attrs = new Attr[n];
        for (int i = 0; i < n; i++)
        {
            attrs[i].n = nrm[i];
            attrs[i].tx = Mathf.FloatToHalf(tan[i].x); attrs[i].ty = Mathf.FloatToHalf(tan[i].y);
            attrs[i].tz = Mathf.FloatToHalf(tan[i].z); attrs[i].tw = Mathf.FloatToHalf(tan[i].w);
            Color32 c = hasCol ? col[i] : new Color32(255, 255, 255, 255);
            attrs[i].r = c.r; attrs[i].g = c.g; attrs[i].b = c.b; attrs[i].a = c.a;
            attrs[i].u = Mathf.FloatToHalf(uv[i].x);   attrs[i].v = Mathf.FloatToHalf(uv[i].y);
        }

        mesh.SetVertexBufferParams(n,
            new VertexAttributeDescriptor(VertexAttribute.Position,  VertexAttributeFormat.Float32, 3, 0),
            new VertexAttributeDescriptor(VertexAttribute.Normal,    VertexAttributeFormat.Float32, 3, 1),
            new VertexAttributeDescriptor(VertexAttribute.Tangent,   VertexAttributeFormat.Float16, 4, 1),
            new VertexAttributeDescriptor(VertexAttribute.Color,     VertexAttributeFormat.UNorm8,  4, 1),
            new VertexAttributeDescriptor(VertexAttribute.TexCoord0, VertexAttributeFormat.Float16, 2, 1));
        var flags = MeshUpdateFlags.DontRecalculateBounds | MeshUpdateFlags.DontValidateIndices;
        mesh.SetVertexBufferData(pos, 0, 0, n, 0, flags);
        mesh.SetVertexBufferData(attrs, 0, 0, n, 1, flags);
    }
}
```

  Normals are left at Float32 here for layout safety; packing them to 10:10:10:2 or SNorm is the further step Qualcomm describes (G2-077). The mesh/geometry detail is owned by `arm-mobile-hw-perf:xr2-adreno-architecture`.
- **Indices:** prefer 16-bit; Unity offers only `UInt16` (default) and `UInt32`, so keep meshes ≤ 65535 vertices (G2-076). Model importer: Index Format = Auto or 16 bits (audit in fix 1).
- **Vertex-shader texture fetches:** on Adreno they generally run twice, in the binning shader and in the full vertex shader; a high VS-sample-to-vertex ratio is a documented trigger for direct mode (G2-078 / G3-040). Wind and displacement shaders are the usual offenders. Prefer vertex-colour or UV-baked weights:

```hlsl
// URP 14+ vertex stage, XR-safe. Wind weight from vertex colour instead of SAMPLE_TEXTURE2D_LOD in the VS.
// Uses the Core.hlsl include and the UnityPerMaterial block (_BaseMap_ST, _Params) from fix 3.
struct Attributes { float4 positionOS : POSITION; half4 color : COLOR; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
struct Varyings   { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };

Varyings vert(Attributes IN)
{
    Varyings OUT;
    UNITY_SETUP_INSTANCE_ID(IN);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(OUT);
    float3 posWS = TransformObjectToWorld(IN.positionOS.xyz);
    posWS.x += sin(_Time.y * _Params.w + posWS.z) * IN.color.r;   // weight baked in vertex colour R
    OUT.positionCS = TransformWorldToHClip(posWS);
    OUT.uv = TRANSFORM_TEX(IN.uv, _BaseMap);
    return OUT;
}
```

- **Effect:** GPU binning time (average frame time); no CPU effect. Quality cost: half-precision UVs lose precision on large atlases [verify on device].
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` (the hardware facts also hold on Vulkan) `URP 14+`. Goal: **Throughput**.

### 7. Remove client-side fences; do not flush mid-pass

- **Change:** avoid `glFenceSync` / `glClientWaitSync`; `eglSwapBuffers` already throttles CPU vs GPU, and a client wait blocks the render thread (G2-030). In Unity, audit `GraphicsFence` use and native plugin render events. Any mid-pass fence-with-flush, `glFlush`, timer query or readback also splits the tiled pass (G2-029); that tile cost is owned by `gles3-perf:gles-tile-load-store`.
- **Conflict (G2-C6):** Qualcomm says avoid fences on Adreno GLES; the Khronos streaming guidance uses fences to recycle ring-buffer regions (fix 5, option 3). Dossier resolution for Quest: prefer orphaning or a ring sized for the frames in flight; if a fence is unavoidable, poll it (timeout 0) without flushing mid-pass. Measure both if you must choose.
- **Effect:** primarily **Consistency**: removes render-thread blocking spikes. Quality cost: none.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` [verify on device]. Goal: **Consistency**.

### 8. Do not interleave compute with graphics; indirect workgroups ≥ 64

- **Change:** issue all graphics work, then all compute (or all compute up front); on GLES avoid GPU skinning, GPU particles or compute culling dispatches between opaque draws (G2-067). In URP, put all custom `DispatchCompute` calls in one `ScriptableRenderPass` at a single event (for example `RenderPassEvent.BeforeRendering`) rather than spread across opaque/transparent events. For `glDispatchComputeIndirect` / `CommandBuffer.DispatchCompute(shader, kernel, argsBuffer, offset)`, use `[numthreads(64,1,1)]` or larger: smaller workgroups make the CPU wait on the GPU (G2-080), which on GLES is also a pass split (G2-029).
- **Effect:** removes internal sync and flushes: **Consistency** first, **Throughput** second. Quality cost: none; may add a frame of latency to compute results if moved after graphics.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` 3.1+ [verify on device]. Goal: **Consistency**, **Throughput**. Compute hardware (LPAC) detail: `arm-mobile-hw-perf:xr2-adreno-architecture`.

### 9. Budget linear-space blending on GLES

- **Change:** Meta's study found blending costs more in linear space because colours are converted on sample and on write (G2-066, Quest 1 [measured]). Unity OpenXR 1.16 validation requires linear for OpenGL (G2-094), but OpenXR supports Quest on Vulkan only (G1-024 / G2-093, G2-055). Whether Oculus XR GLES builds may use gamma is not documented [verify on device]. Either way, cut transparent overdraw (particle counts, layered UI, full-screen fades) on a GLES build.
- **Effect:** GPU average frame time. Quality cost: fewer layers or smaller particles.
- **Tags:** `Quest 2` `Quest 3/3S` `GLES` `Oculus XR 4.x`. Goal: **Throughput**. Overdraw budgets: `quest-perf:quest-budgets-tiers`.

## Verify

- **Metric:** render-thread ms (`CPU&GPU - App` in `adb logcat -s VrApi`, or Perfetto `UnityGfx` slice length), plus OVR Metrics stale-frame count and p95/p99 frame time for Consistency fixes.
- **Protocol:** lock CPU/GPU levels for A/B only (G2-010), same scene, same head pose (`adb shell setprop debug.oculus.sysPropDebug 1` and `adb shell setprop debug.oculus.headlock 1` (G2-010, [community], [verify on device])). For fixes 1, 2 and 4 run a draw sweep at 200, 500 and 1000 draws, with the setting on and off, and compare render-thread ms (the KU-07 / KU-23 method). Expected magnitude: no published number for any fix here; record your own delta.
- **Session length:** 3-5 minute captures for average render-thread ms; 20-30 minutes at shipping (unlocked) levels for fixes 5, 7 and 8, because their payoff is p99 and stale frames, not the mean.
- **GPU-side checks:** fix 6 should lower the eye surface's Binning stage time and keep Mode = 1 (HwBinning) in `ovrgpuprofiler -t -v` (G3-080); fix 8 should remove extra surfaces/stage splits and GLAsyncCompute stages between draws in RenderDoc Tile Timeline (G3-078).
- **Regression check for fix 1:** play every video/camera texture in a release build (UUM-102878).

## Pitfalls and myths

- **"Meta's +64%/+175% numbers are Quest 2/3 budgets."** They were measured on Quest 1, Unity 2018.1.6f1, single-pass, MT rendering off, ATW off (G2-065). Use them as an ordering, not as ms.
- **"Low Overhead Mode helps Vulkan."** It is GLES-only and does nothing on Vulkan (Q2-077). It also lives in the Oculus XR plugin, deprecated from Unity 6.5; no OpenXR equivalent was found (KU-43).
- **"Declaring uniforms as half shrinks the UBO."** It does not; 32-bit size and alignment remain (G3-033).
- **"GL_MAX_UNIFORM_BLOCK_SIZE = 64 KB means large cbuffers are fine."** That is a correctness limit; the performance limit is 7372 B summed per shader (G2-070).
- **"Changing blend or depth state causes a recompile hitch on Quest."** Not on Adreno; hitches come from first compile/link or binary load (G3-007 / G2-068), owned by `gles3-perf:gles-shader-binaries`.
- **"Fences are the correct way to stream on GLES."** Contested on Adreno (G2-C6); orphaning or a frames-in-flight ring avoids the render-thread wait.
- **"UUM-93226 proves buffer updates are cheaper on GLES."** The mechanism evidence points at render-target stores and resolves, not vertex/constant buffer updates; the buffer-update reading is a hypothesis to A/B (GX-C2). Owned by `gles3-perf:gles-vs-vulkan`.
- **"Graphics Jobs will parallelise GLES submission."** Graphics Jobs modes are Vulkan-only; whether GLES Quest builds get any mode is undocumented (G1-025, KU-12). The SRP Batcher is single-threaded on GLES (U3-013).
- **"Per-draw GL timer queries show the cost of each draw."** On Quest's binner they are inaccurate, add 2-5 µs per tile per timed draw and force a flush (G2-034 / G3-068, G3-077). (Qualcomm advises issuing them inside a render pass; Meta/G2-034 says a GL timer query forces a flush. Conflict GX-C9; prefer ovrgpuprofiler stages.)
- **"Snapdragon Profiler is the GLES driver tool."** Reported unreliable on current Horizon OS (G3-085, KU-35); prefer RenderDoc Meta Fork, ovrgpuprofiler and Perfetto.

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ [measured] (Quest 1, 2018; stale)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/spec_sheets.md [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html [doc]
- https://opengles.gpuinfo.org/displayreport.php?id=6387 [community]
- https://opengles.gpuinfo.org/displayreport.php?id=8023 [community]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html [doc] (returned 404 on a re-check the same day; the 4.4 page carries the same Low Overhead Mode text)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html [doc]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102878 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [community]
- https://web.archive.org/web/20250118034434/https://www.khronos.org/opengl/wiki/Buffer_Object_Streaming [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_buffer_storage.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_tiled_rendering.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_disjoint_timer_query.txt [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Mesh.MarkDynamic.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GraphicsBuffer.LockBufferForWrite.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GraphicsBuffer.UsageFlags.LockBufferForWrite.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.IndexFormat.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/optimizing-draw-calls-choose-method.html [doc]
- https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-markers.html [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/frame-timing-manager.html [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/project-configuration.html [doc]
- https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc]
- https://github.com/meta-quest/agentic-tools [doc] (Meta-published agent skill, hz-perfetto-debug)
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ [doc]
- https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ [doc]
- https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ [doc]
- https://developers.meta.com/horizon/documentation/unity/po-renderdoc-optimizations-2/ [doc] (U3-007)
- https://docs.unity3d.com/6000.5/Documentation/Manual/SL-Use16BitPrecisionInShaders.html [doc] (G3-033)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc] (G3-078)
- https://developers.meta.com/horizon/blog/renderdoc-for-oculus/ [doc] (G3-077; stale, 2020)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html [doc] (G1-025)
- https://docs.unity3d.com/6000.3/Documentation/Manual/vulkanapi-graphics-jobs-configuration.html [doc] (G1-025)
- https://developers.meta.com/horizon/blog/vulkan-support-for-oculus-quest-in-unity-experimental/ [doc] (G1-047; stale, 2020)
- https://mysupport.qualcomm.com/supportforums/s/question/0D5dK000009EniESAS/snapdragon-profiler-not-able-to-capture-anything-on-meta-quest-33s [community] (G3-085)
- https://peterthor.se/tag/qualcomm-snapdragon-profiler/ [community] (site unreachable on 2026-09-24; content seen via search snippets only) (G3-085)
