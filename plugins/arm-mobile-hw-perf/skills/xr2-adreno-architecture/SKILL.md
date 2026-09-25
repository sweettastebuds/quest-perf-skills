---
name: xr2-adreno-architecture
description: "Adreno 650/740 tile-based architecture on Quest: binning pass, FlexRender binned vs direct mode, GMEM size and bin arithmetic, LRZ and early-Z rules, overdraw and sorting, UBWC compression, per-bin vertex cost, MSAA resolve in tile, query costs, async compute, and which Arm Mali advice does not transfer. Use to explain why the Quest GPU behaves as it does, to read bin counts, for heavy overdraw from transparents or particles, or to judge if a technique is tile-friendly."
---

# Adreno 650 / 740 architecture on Quest

Goal: **Throughput** (primary: fewer bins, fewer re-shaded vertices, fewer rejected-too-late fragments, fewer DRAM bytes) and **Consistency** (no query or flush stalls; less DRAM traffic means less heat over a 20-30 min session).

Hardware in scope: Quest 2 = XR2 Gen 1, Adreno 650 (A6x). Quest 3/3S = XR2 Gen 2, Adreno 740v3 (A7x). Everything here is hardware behaviour under Qualcomm's proprietary driver, so it holds for any Unity version (2021.3 to 6.x), any URP version and both Vulkan and GLES unless a tag says otherwise. The Unity-side levers are owned by the linked skills.

## When to use / when not

Use when:
- You need to explain a surface line in `ovrgpuprofiler -t -v` or the RenderDoc Meta Fork Tile Timeline: mode, bin count, bin size, and Binning, Render, Load*, Store* stages.
- Transparents, particles, foliage or a sky make the GPU cost jump (overdraw), or a per-draw trace shows `LRZ State: Disabled`.
- You need to judge whether a technique (extra MRT, HDR format, depth prepass, compute post, readback, screen-space tile culling) is tile-friendly on Adreno.
- The Binning stage is a large share of eye-buffer time, or vertex cost grows with MSAA or resolution.
- Someone applies Arm Mali advice (16x16 tiles, 128 bpp, FPK, PLS, malioc) to Quest.

Do not use; go to the sibling instead:
- The bottleneck (CPU vs GPU vs pacing vs thermal) is not yet known: `quest-perf:quest-triage`.
- Setting URP/Render Graph load/store actions, pass merging, memoryless targets, post-processing cost: `unity-perf:unity-render-graph-tiling`.
- The GLES calls themselves (glClear, glInvalidateFramebuffer, MSRTT): `gles3-perf:gles-tile-load-store`.
- Choosing MSAA 2x vs 4x or the URP HDR setting: `unity-perf:unity-urp-settings`.
- Writing the URP shader (clip(), A2C, half, keywords): `unity-perf:unity-shader-authoring`. Per-instruction cost, GPRs, fp16 rate, texture filtering: `arm-mobile-hw-perf:xr2-shader-cost-model`.
- DRAM bytes-per-frame arithmetic, power and heat: `arm-mobile-hw-perf:xr2-bandwidth-power`.
- Meaning and healthy ranges of Adreno counters: `arm-mobile-hw-perf:xr2-gpu-counters-sdp`. Running the tools: `quest-perf:quest-profiling-toolkit`.
- FFR and dynamic resolution settings: `quest-perf:quest-resolution-foveation`.

## Diagnose first

Pin the GPU level for every A/B, or the governor (up at ≥ 87% utilisation, down at ≤ 81%) hides the change (A2-008): `adb shell setprop debug.oculus.gpuLevel 4` and `debug.oculus.cpuLevel` (Q1-079). Unpin (reboot) before any soak.

1. **Surface trace: mode, bins, stages** (A2-025, A3-030, A3-033).
   ```sh
   adb shell ovrgpuprofiler -e <package>    # enable detailed mode, then restart the app (~10% GPU overhead)
   adb shell ovrgpuprofiler -t -v           # one trace, per-bin breakdown
   adb shell ovrgpuprofiler -d              # disable before any thermal / long-session run
   ```
   For each surface read: `Mode:` (0 Direct, 1 HwBinning, 2 SwBinning, 3 HwDirect), `N WxH bins`, total ms, and the stages Binning, Render, LoadColor, StoreColor, LoadDepthStencil, StoreDepthStencil. How multiview surfaces print per headset (for example, Quest 2 `135 96x176 bins` means 135 × 2 view-bins): `quest-perf:quest-profiling-toolkit`.
   - Healthy eye buffer: Mode 1, StoreColor only (that is the in-tile MSAA resolve), no Load* and no StoreDepthStencil (A3-007 notes).
   - Eye buffer in Mode 0/3: it lost binning and FFR (A2-023).
   - Binning above 20% of the surface (Qualcomm guideline 10-20%; 30% 'usually too much', G3-079): vertex/binning-bound.
2. **Per-draw LRZ state** (A2-037, A3-032, Q1-073).
   ```sh
   adb shell ovrgpuprofiler -x -m                                   # list per-draw metric ids
   adb shell ovrgpuprofiler -t3 -x="<ids incl. Fragments Shaded>"   # per-draw trace with LRZ State
   ```
   Walk the draws in submission order. The first draw after which later opaque draws read `Disabled` or write-disabled is the LRZ killer (Fix 2). `Unknown(old driver?)` means the driver does not report it. Per-draw timings compare draws within one trace only (Q1-073).
3. **Overdraw estimate** (Q1-074, [community] derivation on [doc] counter names): overdraw ≈ (Fragments Shaded/Second ÷ FPS) ÷ (2 × eye width × eye height). Use it to rank views, not as an absolute.
4. **RenderDoc Meta Fork** for the same data with attachment formats: Tile Timeline (mode, bins, LoadDS/StoreDS, VKLoadInput) and Surface Information (A3-035). Sum `Write Total (Bytes)` over the eye-buffer draws and compare with the resolved-colour size; several times that figure means depth or MSAA samples are being stored (A3-037, [verify on device]). Use per-render-pass timer queries only (Q1-059).

## Key numbers

| Number | Value | Source / tag |
|---|---|---|
| GMEM, Quest 2 (Adreno 650) | Meta: 1 MB. Kernel catalog: 1 MiB + 128 KiB. Treat 1 MB as rounded (ARM-C10). | A2-010 [doc], A2-011 [community]. `Quest 2` |
| GMEM, Quest 3/3S (Adreno 740v3) | **Conflict ARM-C9.** Meta: "approximately 2MB". Kernel: 3 MiB for the SD8 Gen 2 chip, not the Quest chip. Derived from UUM-149765's 63 bins of 192x256 at 4x on Quest 3: 192×256×32 B×2 views = 3 MiB (assumes RGBA8 + D24S8 and both views per bin; the report gives no formats; 1.5 MiB without the ×2). Derived from Meta's 128x224 example: about 1.75 MiB. Infer from your own bin sizes. [verify on device] | A2-010 [doc], A2-011, A2-015, G2-039 [measured]. `Quest 3/3S` |
| Bin footprint | (colour B + depth/stencil B) × samples, × 2 when both views share a bin | A2-013 [doc]. all |
| Worked example | 4x MSAA, RGBA8 + D24S8, multiview = 32 B/px/view -> 96x176 bins, 135 bins (15 × 9) for 1440x1584 | A2-013, ARM-GF1-006 [doc]. `Quest 2` |
| Quest 3 observed | 63 bins of 192x256 at 4x MSAA, Unity 6000.0-6000.7a; consistent with 1680x1760 (9 × 7, derived; resolution and formats not stated in the report; device may be Quest 3S, G2-C9) | G2-039 [measured]. `Quest 3/3S` `Unity 6000.x` |
| Eye buffer vs GMEM | 1440x1584 RGB8 ≈ 6.52 MB; 1680x1760 ≈ 8.46 MB. On-GPU memory of at most ~5 MB (A2-020): tiling is mandatory | A2-020 [doc]. all |
| Vertex shading per frame | at least 2 (1 binning + 1 render), up to 2 × bins + 1 | A2-047 [doc]. all |
| Binning share of a render pass | Qualcomm guideline 10-20%; 30% "usually too much" | G3-079 [doc]. all |
| Binning share observed | 4.5 ms of 9.7 ms (GLES, no MSAA), 5.1 of 13.0 ms (GLES 4x); Vulkan same binning | G2-087 [measured]. `Quest 3/3S` `Unity 6000.x` |
| Early-Z rejection rate | up to 4x normal fill rate | A2-038 [doc]. all |
| Fast-Z (depth-only, empty FS, colour masked) | 2x normal Z rate | A2-040 [doc]. all |
| Load/store example (bad config) | 1216x1344, MSAA 2, 28 bins 320x192, 10.62 ms; Load*+StoreDS = 2.41 ms (~23%); all GMEM-DRAM 3.93 ms (~37%) | A2-054 [doc], original-Quest era |
| Reading a prior pass from DRAM vs tile | about an order of magnitude slower | A2-059 [doc]. all |
| Timer query | 2-5 µs per bin -> 0.27-0.68 ms at 135 bins (2-5% of 13.9 ms) | A2-060 [doc], derived. all |
| Occlusion query CP overhead | 20-40% binned vs 4-6% direct | A2-060 [doc]. all |
| A7x post-transform vertex cache | 32 four-component vertices | A2-049 [doc]. `Quest 3/3S` |
| Triangle-setup rate | A5x: 1 prim/clock. **No published number** for A6x/A7x; measure with Binning time and `Pre-clipped Polygons/Second` at a locked level | A2-052 [doc] |
| LRZ block size | **No published number**; measure indirectly with per-draw `Fragments Shaded` | A2-029 [doc] |
| MSAA input-attachment reads | 2 samples in parallel on 540/650 (2x free, 4x not); 740 unknown [verify on device] | A2-058 [doc]. `Quest 2` |
| Compute shared memory | 32 KB per workgroup, 650 and 740 | A2-093 notes [community] |

## Fixes, ranked by payoff ÷ effort

### 1. Make the eye-buffer surface store only the resolved colour (Throughput, Consistency)

Hardware rule (A3-006, A2-053, A2-055): every attachment starts with CLEAR or DONT_CARE (glInvalidateFramebuffer on GLES); depth and MSAA store DONT_CARE; MSAA resolves in the tile store path through `pResolveAttachments` on the **last** subpass. An intermediate resolve, an intermediate store, a separate `vkCmdResolveImage`/`glBlitFramebuffer`, or a conservative subpass dependency spills to DRAM. Transient MSAA/depth attachments can be lazily allocated (GMEM-only) (A3-021).
- Effect: removes the Load*/StoreDS stages; Meta's bad example lost ~23% of the surface to them (A2-054). Less DRAM traffic also lowers power, which serves Consistency over long sessions (see `arm-mobile-hw-perf:xr2-bandwidth-power`).
- How in Unity: `unity-perf:unity-render-graph-tiling` (URP/Render Graph, Optimize Buffer Discards, memoryless); `gles3-perf:gles-tile-load-store` (GLES calls).
- Quality cost: none. Side effect: any feature that samples camera depth or the opaque texture after the pass forces a store (A3-006 notes).
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` `any Unity/URP`.

### 2. Find and move the LRZ killer (Throughput)

LRZ is coarse Z built in the binning pass; it rejects at block granularity before full-resolution Z, order-independently (A2-029). Three severities (A2-032 to A2-034, Qualcomm [doc]):

| Draw does | LRZ effect |
|---|---|
| Depth-direction change, or ZTest Always / NotEqual, **followed by a depth write** | test + write off **until next depth clear** |
| Blend/logic op, colour mask or partial MRT write, any stencil op, framebuffer fetch, or reading a previous-subpass attachment, **and writes depth** | write off until next clear (test still on) |
| FS writes UAV, depth or stencil | test + write off for this draw only |
| Alpha-to-coverage, `discard`/`clip()`, sample-mask output | write off for this draw only |

What to change (Unity mapping is inference, [verify on device] with the per-draw LRZ line):
- Anything drawn mid-pass with `ZTest Always` + `ZWrite On` (custom sky, "always on top" gizmo, HUD mesh): make it `ZWrite Off`, or move it after all opaques.
- Blended or stencil materials with `ZWrite On` (portal masks, stencil effects, fade-out opaques): set `ZWrite Off`, or queue them after all depth-writing opaques.
- Do not flip depth direction (reversed-Z tricks) inside the main pass.

ShaderLab state for a sky or background that must not freeze LRZ, drawn after opaques:
```shaderlab
Tags { "Queue" = "Geometry+500" "RenderType" = "Opaque" }   // after opaques and AlphaTest (2450)
ZWrite Off
ZTest LEqual
```
- Effect: restores coarse rejection for every later draw in the pass; biggest on overdraw-heavy views. No published ms figure; measure `Fragments Shaded` and surface Render ms before/after.
- Quality cost: none if sort order is kept correct. Full rule set and direction tracking by generation: [references/lrz-rules.md](references/lrz-rules.md). Read it when a draw shows `Disabled` and the cause is not in the table above.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` `any Unity/URP`.

### 3. Sort for LRZ and early-Z: opaque front-to-back, then alpha-test, then blend (Throughput)

Adreno has no hidden-surface removal (no FPK equivalent); Qualcomm says sort opaques front-to-back even with early-Z (A2-039, A2-097). Early-Z (up to 4x fill rate) is off for draws that write Z, discard, write depth/stencil or use A2C (A2-038). Discard draws cost their own LRZ write but do not poison later draws (A2-034); put them after all opaques (A2-041, U3-060: URP queue 2000 before AlphaTest 2450).
- What to change: keep URP's default opaque sorting; do not force arbitrary render queues on large occluders; do not put large alpha-clipped surfaces in the Geometry queue.
- Effect: fewer fragments shaded; average frame time only. Quality cost: none.
- Alpha-tested shading cost and the per-material depth prepass (U3-062): `unity-perf:unity-shader-authoring`.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` `any Unity/URP`.

### 4. Cut bytes per pixel to cut the bin count (Throughput)

Bin count scales roughly with bytes per pixel (A2-014), and vertex cost scales with bin count (A2-047). Levers (A2-017, A2-045):
- Colour: RGB10A2 first (hardware-optimised), then R11G11B10F, then RGBA16F. R11G11B10F costs no bins over RGBA8; RGBA16F at 4x MSAA is 48 vs 32 B/px, about 1.5x the bins.
- Depth: D16 when precise enough, D24S8 only if stencil is needed, then D32.
- Each extra 32-bit MRT at 4x adds 16 B/px.
- Fewer MSAA samples (choice owned by `unity-perf:unity-urp-settings`), lower resolution or foveation (`quest-perf:quest-resolution-foveation`).

Custom intermediate target with the cheapest formats (compiles on 2021.3 to 6.x):
```csharp
using UnityEngine;
using UnityEngine.Experimental.Rendering;

public static class TileFriendlyRT
{
    public static RenderTextureDescriptor Describe(int width, int height, int msaa)
    {
        RenderTextureFormat color = SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.ARGB2101010)
            ? RenderTextureFormat.ARGB2101010   // RGB10A2: Qualcomm's first choice (A2-045)
            : RenderTextureFormat.ARGB32;
        var desc = new RenderTextureDescriptor(width, height, color, 0);
        desc.msaaSamples = msaa;
#if UNITY_2021_2_OR_NEWER
        desc.depthStencilFormat = GraphicsFormat.D16_UNorm;  // no stencil needed; halves depth B/px
#else
        desc.depthBufferBits = 16;
#endif
        return desc;
    }
}
```
- Effect: fewer bins -> less binning and per-bin overhead; average frame time only. Quality cost: RGB10A2 has 2-bit alpha; D16 needs a tuned near/far or reverse-Z. [verify on device] with the `N WxH bins` field.
- Arithmetic table and worked examples: [references/bin-math.md](references/bin-math.md). Read it before changing a format, MSAA level or MRT count, or when a bin count looks wrong.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` `Unity ≥ 2021.3`.

### 5. Cut binning-pass vertex cost (Throughput)

The binning pass runs a driver-generated position-only VS over every draw; the render pass runs the full VS again per bin (A2-046). A triangle is rasterised in full in every bin it touches (A2-018; conflict ARM-C11: Meta says triangles "can be split", Qualcomm's wording is more specific).
- Position alone in vertex stream 0, everything else in stream 1, so the position-only VS fetches the minimum (A2-048, A3-018).
- 16-bit indices whenever `vertexCount ≤ 65535` (Unity exposes only UInt16/UInt32; A3-018 notes). Vertex-cache-optimised index order still pays off on A7x's 32-entry cache (A2-049).
- No texture fetches in the VS (vertex animation textures, texture-driven skinning, heightmap displacement): they run twice, and too many push the pass to direct mode (A2-050).
- Fat triangles, at least ~4 px, and normal maps over extra geometry (A2-018, A2-047).
- Avoid tessellation, primitive restart, user clip planes, `VK_EXT_vertex_input_dynamic_state` (A2-051).

Procedural mesh with a position-only stream 0 (Unity 2019.3+ API; compiles on 2021.3 to 6.x):
```csharp
using UnityEngine;
using UnityEngine.Rendering;

public static class SplitStreamMesh
{
    public static void Apply(Mesh mesh, Vector3[] positions, Vector3[] normals, Vector2[] uvs, ushort[] indices)
    {
        var layout = new[]
        {
            new VertexAttributeDescriptor(VertexAttribute.Position,  VertexAttributeFormat.Float32, 3, stream: 0),
            new VertexAttributeDescriptor(VertexAttribute.Normal,    VertexAttributeFormat.Float32, 3, stream: 1),
            new VertexAttributeDescriptor(VertexAttribute.TexCoord0, VertexAttributeFormat.Float32, 2, stream: 1),
        };
        mesh.SetVertexBufferParams(positions.Length, layout);
        mesh.SetVertexBufferData(positions, 0, 0, positions.Length, stream: 0);
        var rest = new StreamData[positions.Length];
        for (int i = 0; i < rest.Length; i++) { rest[i].normal = normals[i]; rest[i].uv = uvs[i]; }
        mesh.SetVertexBufferData(rest, 0, 0, rest.Length, stream: 1);
        mesh.SetIndexBufferParams(indices.Length, IndexFormat.UInt16);
        mesh.SetIndexBufferData(indices, 0, 0, indices.Length);
        mesh.subMeshCount = 1;
        mesh.SetSubMesh(0, new SubMeshDescriptor(0, indices.Length));
        mesh.RecalculateBounds();
    }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    struct StreamData { public Vector3 normal; public Vector2 uv; }
}
```
Whether Unity's importer or SRP ever splits streams for imported meshes is not documented (A2-048 notes); audit with `Mesh.GetVertexAttributeStream(VertexAttribute.Position)` and `Mesh.indexFormat` in an editor script, and check `Avg Bytes / Vertex` in RenderDoc Meta Fork (A3-038).
- Effect: lower Binning ms; the gain grows with bin count (4x MSAA, high resolution). No published ms figure. Quality cost: none.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES` `Unity ≥ 2021.3`. Vertex-format compression on import: `unity-perf:unity-memory-assets`.

### 6. Keep the expensive pass binned; know when direct mode is fine (Throughput)

FlexRender picks binned or direct mode per pass; heuristics are hidden (A2-021). Direct-mode triggers: high VS-texture-sample to vertex ratio, few vertices or draws, tessellation/geometry shaders. A depthless full-screen pass with no MSAA (tonemap, final blit) runs direct and shows `1 WxH bins` (A2-022). Direct mode disables FFR for that surface (A2-023, A3-024).
- If the main scene renders to an intermediate and a depthless blit writes the swapchain, the main pass gets no compositor FFR. Render the main pass to the swapchain, or use on-tile post: `unity-perf:unity-render-graph-tiling`.
- Tiny utility passes going direct is expected and fine (A2-028 mechanism).
- **Conflict ARM-C12:** Meta's old MSAA analysis quotes Qualcomm that direct mode happens only with MSAA off (A2-024); the current Qualcomm guide does not list MSAA as a trigger. Read the mode per surface.
- Effect: average frame time; FFR savings return on the eye buffer (size: `quest-perf:quest-resolution-foveation`).
- Quality cost: none; rendering the main pass to the swapchain can constrain post-processing.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES`.

### 7. Keep hot render targets UBWC-compressed (Throughput, Consistency)

UBWC is lossless bandwidth compression on every Adreno since A5x; optimal-tiled images generally get it (A2-042, A3-013). Qualcomm: compute access, LINEAR tiling, any CPU readback, `VK_KHR_fragment_shading_rate`, `VK_EXT_fragment_density_map`, ALIAS, MUTABLE_FORMAT and sparse resources "almost certainly" disable it (A2-043). On A6x, R8_UNORM, R9G9B9E5, ASTC and ETC2 have no UBWC (A2-044).
- Keep `ReadPixels`/`AsyncGPUReadback` sources and compute-written targets separate from hot render targets.
- On Quest 2, avoid R8 for large per-frame targets (SSAO/mask buffers) if bandwidth-bound.
- **Conflict ARM-C13:** FDM is on the list, but Meta's Vulkan FFR is FDM-based; whether FFR eye buffers lose UBWC is unpublished. **Conflict ARM-C14:** Mesa marks the 740v3 as supporting UAV UBWC under Turnip; Quest's driver is unverified; assume loss. Whether Unity sets MUTABLE_FORMAT on sRGB RenderTextures is unknown (needs a RenderDoc capture).
- Effect: fewer DRAM bytes; no published compression ratio. Quality cost: none. Details and the measurement method: [references/ubwc.md](references/ubwc.md). Read it before adding compute post, readback or a new RT format.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` (UBWC rules are stated for Vulkan; GLES unpublished).

### 8. Strip GPU queries from shipping builds; never time before an invalidate (Throughput, Consistency)

Timer queries cost 2-5 µs per bin (0.27-0.68 ms at 135 bins); occlusion queries cost 20-40% CP overhead in binned mode (A2-060). A timer query forces a flush; one placed before an invalidate makes the depth buffer store (A2-061, A3-023). Qualcomm advises issuing timer queries inside a render pass (G3-068); the two fit together: inside the pass there is no extra flush, but the query still sums over bins (GX-C9).
- What to change: remove custom timestamp/occlusion queries from native plugins and shipping builds; profile with ovrgpuprofiler stages instead.
- Effect: average frame time (removes a fixed per-frame cost and a flush that can add a store), plus removal of flush-induced spikes (variance).
- Quality cost: none; you lose in-app GPU timing, so use ovrgpuprofiler instead.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES`.

### 9. Let concurrent binning run on Quest 3/3S (Throughput)

A7x overlaps binning of later work with rendering of earlier work (A2-026, A2-027). Blocked by: clearing a Z-buffer that is reused within the frame, a pass whose binning depends on the previous pass's output, and a VSYNC-limited app whose first surface carries all geometry (G2-088).
- Reuse one depth buffer without re-clearing it, or give each pass its own; schedule independent work before the geometry-heavy pass. Keep URP Depth Priming Disabled (U2-020, G2-020): it doubles vertex/binning work, and LRZ already rejects order-independently.
- Effect: average frame time only; no published figure; UUM-149765 does not say whether Binning ms overlaps Render (KU-26). [verify on device]
- Quality cost: none.
- Tags: `Quest 3/3S` only `Vulkan` `GLES`.

### 10. Prefer fragment over compute for image work; LPAC on Quest 3/3S only (Throughput)

Fragment output uses the resolve hardware and keeps UBWC; compute writes tend to lose it (A2-093). Keep graphics submits and compute dispatches separate. On A7x size local groups in multiples of 64/128 and workgroup counts in multiples of 16 (8 with shared memory). On GLES, `glDispatchIndirect` with a workgroup smaller than 64 causes a CPU wait. LPAC (low-priority async compute via `VK_KHR_global_priority` LOW) exists on Adreno 740 only; whether Unity exposes it is unknown (A2-094).
- Effect: average frame time via UBWC retention; no published figure; measure `Write Total (Bytes)` before/after.
- Quality cost: none; porting compute post to fragment can cost flexibility.
- Tags: `Quest 2` `Quest 3/3S` `Vulkan` `GLES`; `Quest 3/3S` only for A7x sizing and LPAC; Unity exposure of LPAC unknown [verify on device]. CPU cost of compute dispatch on GLES: `gles3-perf:gles-driver-overhead`.

## Verify

Same scene, same pose, GPU and CPU levels pinned (Q1-079), detailed mode on for traces only.
- Fix 1: Load* and StoreDepthStencil stages disappear from the eye-buffer surface; surface ms falls by roughly their sum (A2-054 shape). One trace before, one after.
- Fix 2/3: the per-draw LRZ line reads `TestEnabled, WriteEnabled` for opaque draws after the former killer; per-frame `Fragments Shaded` and surface Render ms fall. No published size; expect the gain in overdraw-heavy views only.
- Fix 4: `N WxH bins` falls roughly in proportion to bytes per pixel (A2-014); Binning ms follows.
- Fix 5: Binning ms falls toward the 10-20% guideline (G3-079); `Avg Bytes / Vertex` falls.
- Fix 6: the swapchain surface shows Mode 1 and per-bin `Fov x/y` factors (A2-025).
- Fix 7: `Write Total (Bytes)` for the target falls when a readback/compute alias is removed. [verify on device]
- Throughput fixes: then run OVR Metrics at unpinned levels for 20-30 min and confirm App GPU time, GPU level and stale frames hold, because lower DRAM traffic should show as a lower or later level rise (owner: `quest-perf:quest-levels-thermal`).

## Pitfalls and myths

- **Mali advice on Quest.** 16x16 tiles, the 128 bpp subpass rule, FPK, Pixel Local Storage, Mali counters and malioc do not transfer. Generic TBR load/store and subpass rules do (A2-095 to A2-100). Full map: [references/mali-transfer-map.md](references/mali-transfer-map.md). Read it whenever the advice source is Arm or a Mali-tuned engine.
- **"Quest 3 has 3 MB GMEM" or "2 MB".** Both have support (ARM-C9). Read bin sizes; do not hard-code.
- **Predicting bin sizes from Mesa.** Mesa's 96-pixel alignment does not match Qualcomm-driver bins (128x224, 320x192) (A2-016). Do not assume a bin count or positions either: foveation changes them, and 16x16 screen-tile algorithms will not line up (A2-019).
- **"Multiview halves GPU cost."** Qualcomm: multiview saves CPU only, no GPU impact (A2-062). Both views share a bin in GMEM, but whether binning work is shared is unmeasured (ARM-C23). CPU-side saving: `unity-perf:unity-draw-calls-batching`.
- **"Depth priming reduces overdraw on Quest."** Unity's GRD page suggests it for desktop/console only; the XR page says disable it and rely on LRZ (U3-C2). A depth prepass doubles binning and vertex work (A2-040 notes).
- **"clip() gives an early exit."** If only some pixels of a thread are killed, the whole thread still runs; Qualcomm says the gain is rarely real (A2-041).
- **"vec4 math is faster."** Adreno is scalar per ALU op (A2-009); packing matters for varyings/constants only (`arm-mobile-hw-perf:xr2-shader-cost-model`).
- **"MSAA is practically free."** Qualcomm says 2x is "likely to be practically free" (A2-017, A3-020), true only when samples are not stored. UUM-149765 measured +3.3 ms (GLES) / +5.0 ms (Vulkan) for 4x on Quest 3/3S and about +7 ms on Quest 2 (G2-039, G2-040). The level choice is owned by `unity-perf:unity-urp-settings`.
- **Graphics Jobs.** A 2021.2-era Unity staff reply says Graphics Jobs implicitly disables Adreno LRZ/HSR (U5-038, [community]); current status unverified. Owner: `unity-perf:unity-cpu-scripting`.
- **Secondary command buffers kill LRZ.** Only before Adreno 650; a non-issue on Quest (A2-036).
- **Reading ms without the GPU level.** The Quest 3 L0-L5 clock range is about 2.1x (A2-008); the profiler page's 690/492 MHz figures conflict with the levels table (A3-100, ARM-C3).
- **Qualcomm and Meta do not publish** SP/ALU counts, FLOPS or clocks for the 650/740 (A2-004); treat any such figure as unsourced.

## Sources

All accessed 2026-09-24.
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]: bin levers, 2x MSAA, triangles per bin, FlexRender triggers, concurrent binning, LRZ rules, early-Z, Fast-Z, discard, UBWC disablers, formats, vertex layout, indices, VS fetches, slow features, load/store, lazily allocated, subpass merging, queries, multiview, compute, LPAC (A2-017, A2-018, A2-021, A2-026, A2-032 to A2-034, A2-036, A2-038, A2-040, A2-041, A2-043, A2-045, A2-048 to A2-051, A2-053, A2-057, A2-060, A2-062, A2-093, A2-094, A3-014, A3-018, A3-020, A3-021, A3-026, G3-068)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html [doc]: two-phase model, LRZ, no HSR, UBWC, binning VS (A3-003, A2-009, A2-029, A2-039, A2-042, A2-046, A3-013)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html [doc]: no published SP/GMEM/clock, A6x UBWC formats, A7x vertex cache, A5x setup rate (A2-004, A2-044, A2-049, A2-052)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html [doc]: binning share 10-20% (G3-079)
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]: GMEM sizes, bin rule, direct mode and FFR, load/store rules, resolve, input-attachment samples, timer query flush (A2-010, A2-013, A2-022 to A2-024, A2-054, A2-055, A2-058, A2-061, A3-004 to A3-007, A3-022 to A3-024)
- https://developers.meta.com/horizon/documentation/unity/gpu-tiled/ [doc]: 135 bins, eye buffer vs GMEM (ARM-GF1-006, A2-020)
- https://developers.meta.com/horizon/documentation/unity/gpu-impaired-algorithms/ [doc]: 2 × bins + 1 vertex shading, bin positions, DRAM vs tile reads (A2-019, A2-047, A2-059)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]: modes, stages, per-draw LRZ, multiview reading, 128x224 example (A2-015, A2-025, A2-037, A3-029 to A3-034, Q1-073)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ and https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ [doc]: Tile Timeline, Surface Information (A3-035)
- https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ [doc]: Write Total, Avg Bytes / Vertex (A3-036 to A3-038)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ [doc]: per-render-pass timer queries (Q1-059)
- https://developers.meta.com/horizon/documentation/unity/ts-systemproperties/ [doc]: level pinning (Q1-079)
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]: governor thresholds, clock range (A2-008)
- https://developers.meta.com/horizon/documentation/native/android/mobile-msaa-analysis/ [measured]: direct mode only with MSAA off (original Quest) (A2-024, A2-056)
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [measured]: 63 bins of 192x256, binning share, MSAA deltas (G2-039, G2-040, G2-087)
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html [doc]: depth priming off, rely on LRZ (U3-058, U3-C2)
- https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer-performance.html [doc]: depth priming for non-tiled GPUs (U3-036)
- https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html [community]: LRZ format, direction tracking, LRZ feedback, dual LRZ on A7xx (A2-027, A2-030, A2-031, A2-035, U3-059, U3-060)
- https://docs.mesa3d.org/drivers/freedreno.html and https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py [community]: CCU carve-out, tile alignment, sysmem choice (A2-012, A2-016, A2-028)
- https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/drivers/gpu/drm/msm/adreno/a6xx_catalog.c [community]: kernel GMEM values (A2-011)
- https://discussions.unity.com/threads/vulkan-bug-quest-2-urp-graphics-jobs-no-multithreaded-rendering-slow.1208908/ [community]: Graphics Jobs vs LRZ (U5-038)
- https://docs.vulkan.org/samples/latest/samples/performance/render_passes/README.html, .../subpasses/README.html, .../msaa/README.html [doc]/[measured]: Mali transfer map (A2-095, A2-096, A2-099, A2-100)
- https://opengles.gpuinfo.org/displayreport.php?id=6387 and https://opengles.gpuinfo.org/displayreport.php?id=8023 [community]: no PLS on Quest GLES (A2-098)
