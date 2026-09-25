# Batching methods: version × API × constraints

Reference for `unity-perf:unity-draw-calls-batching`. All sources accessed
2026-09-24. IDs point to `research/unity.md` (U*, UNITY-GF*) and
`research/gles3.md` (G*). Quest 3S follows Quest 3 everywhere (same SoC).

## 1. Method matrix

| Method | Unity / URP | GLES on Quest | Vulkan on Quest | What it cuts | What it does not cut | Hard constraints | IDs |
|---|---|---|---|---|---|---|---|
| Multiview (single-pass instanced variant) | all in range (2021.3+, URP 12+) | yes, OculusXR plugin only (deprecated from 6.5); OpenXR lists Quest as Vulkan-only | yes, default with OpenXR Meta Quest feature group | half the draw submissions vs multi-pass | GPU vertex/fragment work: small or nil saving (conflict G2-C10) | shaders need SPI macros or render left eye only; silent fallback to multi-pass if unsupported | U3-040 to 046, G2-050 to 055 |
| SRP Batcher | 2021.3+ (URP 12+) | yes, single-threaded | yes, multithreaded only with Graphics Jobs on | render-state changes (SetPass) | raw draw count | MeshRenderer/SkinnedMeshRenderer only (no particles); single `UnityPerDraw` + single `UnityPerMaterial` CBUFFER; no MPB | U3-009 to 016 |
| Static batching | all | yes | yes, but incompatible with BRG/GRD | draw count for static props | memory (geometry duplicated per instance) | MeshRenderer only; ≤ 64,000 vertices per combined buffer; same vertex attributes; batches split by culling | U3-018 to 022, U3-C1 |
| Classic GPU instancing | all | yes | yes | draw count for many copies of one mesh + material | GPU vertex cost (every instance still transformed) | used by URP only when SRP Batcher is off or shader is SRP-Batcher-incompatible; U3-025 array default 250 (mobile Vulkan) / 500 does not apply on Quest: `UNITY_INSTANCING_SUPPORT_FLEXIBLE_ARRAY_SIZE` (defined for GLES3 and Vulkan) takes precedence, the CB is sized per batch and `maxcount:N` has no effect (only `UNITY_FORCE_MAX_INSTANCE_COUNT` overrides); no published Quest number, read instances per draw in the Frame Debugger [verify on device]; per-material checkbox adds variants | U3-016, U3-017, U3-023, U3-025 |
| Dynamic batching | 6.0-6.5: "no longer recommended"; obsolete in 6.6 | yes | yes | draw count for tiny meshes | adds CPU vertex transform | ≤ 300 vertices, ≤ 900 vertex attributes; first pass only; shared lightmap; no mixed-sign scale | UNITY-GF1-001/002, U1-022 |
| BatchRendererGroup (BRG) API | experimental 2021.3 (old API, rewrite on upgrade); 2022.3+ current API | yes, UBO window (`BatchBufferTarget.ConstantBuffer`) | yes, SSBO (`RawBuffer`) | draw count, CPU submission; you own culling | culling cost (your `OnPerformCulling` job) | SRP Batcher on; BRG Variants = Keep All; URP "Strip Unused Variants" off; unsafe code on; GLES needs `#pragma target 3.5`+ for DOTS instancing | U3-026 to 030, U1-013/014 |
| GPU Resident Drawer (GRD) | 6.0+ (URP 17) | **no** (needs compute, excludes GLES) | yes | draw count and SetPass for GameObjects via BRG | adds GPU work; "lower-end mobile and VR" hit harder | see §2 | U3-032 to 036, U1-016 to 018, X-C9 |
| GPU occlusion culling | 6.0+ (single-pass XR from 6000.0.0b12) | **no** | yes, needs GRD and Render Graph | GPU work for occluded instances | adds depth-pyramid pass; can cost more than it saves with little occlusion | broken 6000.5.0 to 6000.5.7 (UUM-146214) | U3-037/038, U1-019/020, U1-095 |
| Entities Graphics | Entities Graphics 1.x / 6.5 | deprecated, slated for removal | yes | ECS rendering | n/a | URP Forward+ only; XR supported | U3-031, U1-095 |

## 2. GRD eligibility checklist (6.0+, Vulkan)

Project level (all required):
- Graphics API supports compute and is not OpenGL ES: on Quest, Vulkan only (U3-032).
- Rendering path Forward+ (6.0 and 6.3 pages); Forward+ or Deferred+ from 6.1 (X-C9). On Quest use Forward+ in every version (X-C9 resolution; Deferred not recommended on tile GPUs).
- Enlighten realtime GI off.
- Project Settings > Graphics > Shader Stripping > BatchRendererGroup Variants = Keep All.
- SRP Batcher on.
- URP Asset > GPU Resident Drawer = Instanced Drawing.
- Player > Static Batching off (static-batched renderers never reach GRD; U3-018).
- Lighting > Fixed Lightmap Size on; Use Mipmap Limits off (so lightmapped objects batch; U3-035, U4-044).

Per MeshRenderer (anything else silently falls back to the normal path):
- no MaterialPropertyBlock
- no Light Probe Proxy Volume, no Anchor Override
- default sorting layer and sorting order
- BRG-compatible materials, at most 128 materials
- no TextMesh; no MonoBehaviour implementing `OnWillRenderObject`, `OnBecameVisible`, `OnBecameInvisible` (they are not called under GRD)
- animated LOD cross-fade unsupported (falls back to static distance cross-fade)
- `Light.shadowMatrixOverride` ignored for caster culling
- opt out per object with the Disallow GPU Driven Rendering component

Version fixes that gate GRD/BRG on Quest-class hardware:

| Issue | Symptom | Affected | Fixed in | ID |
|---|---|---|---|---|
| UUM-102083 | BRG, GRD and Entities Graphics objects do not render on 16 KiB constant-buffer Android devices | 6.0 before .65, 6.3 before .3 | 6000.0.65f1, 6000.3.3f1, 6000.4.0b3 | U1-015 |
| UUM-146214 | GPU occlusion stops culling occluded instances with GRD on: GPU cost for no gain | 6000.5.0 to 6000.5.7 (seen in 6000.6.0a2) | 6000.5.8f1, 6000.6.0f1 | U1-020 |

Tooling by version (U1-021):
- 6.4: rebuilt Rendering Statistics window with SRP Batcher counts.
- 6.6: GRD telemetry in the Profiler.
- 6000.7.0a3 (alpha): GRD batching stats (unique materials and meshes, single-instance batches) and a "GRD Batches" Profiler chart.

## 3. Precedence when every method is on (6.x)

1. Static meshes: static batching.
2. Dynamic meshes with a compatible shader: SRP Batcher plus GRD/BRG.
3. Remaining compatible meshes: GPU instancing.
4. (6.0-6.5 only) Remaining meshes: dynamic batching. The SRP Batcher takes
   precedence over dynamic batching for SRP-Batcher-compatible shaders.

Source: U3-018, UNITY-GF1-002.

## 4. Unity 6.6 URP recommendation table (general, not XR-specific)

| Feature | Unity 6.6 recommendation | Quest caveat |
|---|---|---|
| SRP Batcher | Enable | Unity also warns unoptimized projects can run faster with it off on low-end devices; A/B (U3-012) |
| GPU Resident Drawer | Enable | Vulkan only; adds GPU cost; A/B on Quest 2 (U3-034, U3-C3) |
| BRG API | Advanced cases only | |
| Per-material GPU Instancing checkbox | Disable (adds variants) | |
| Static batching | Disable (incompatible with BRG/GRD) | Keep it on GLES, on 2021.3/2022.3, or where GRD loses the A/B (U3-C1) |

Source: U3-017.

## 5. BRG buffer modes

| API on Quest | `BatchRendererGroup.BufferTarget` | Shader side | AddBatch rule | IDs |
|---|---|---|---|---|
| GLES 3.x | `ConstantBuffer` (UBO window) | `UNITY_DOTS_INSTANCING_UNIFORM_BUFFER`; `DOTS_INSTANCING_ON` needs `#pragma target 3.5`+ | offset aligned to `GetConstantBufferOffsetAlignment()`; window ≤ `GetConstantBufferMaxWindowSize()` | U1-014, U3-028, U3-029 |
| Vulkan | `RawBuffer` (SSBO) | SSBO path | offset and window size both 0 | U1-014, U3-028, U3-029 |

Window arithmetic (from a Mali-G72 GLES 3.0 phone, not Adreno, U3-030):
instances per window = window bytes ÷ per-instance bytes; the sample saw a
16 KiB window with 4-256 B alignment, 112 B per instance, 146 instances per
window, and 3,200 instances in 22 draws. No Adreno/Quest window size is
published: log the two getters on Quest 2 and Quest 3 under GLES
[verify on device]. BRG does no culling; Unity splits a draw command when the
API limit is below `visibleCount` (U3-027).

## 6. Stereo submission paths

| Path | Draws per object | Instance multiplier | Where it applies | IDs |
|---|---|---|---|---|
| Multi-pass | 2 (one per eye) | none | legacy shaders only; "roughly double" CPU draw processing | U3-041 |
| Single-pass instanced (SPI) | 1, instanced ×2 | URP calls `SetInstanceMultiplier(viewCount)`; indirect draws are NOT multiplied, double your args buffer yourself | only when `SystemInfo.supportsMultiview` is false | U3-043, U3-045 |
| Multiview | 1; driver replicates per view | not applied; instanced and indirect draws keep their own counts | Quest, when multiview is available (GLES: `STEREO_MULTIVIEW_ON` via OVR_multiview2 + multiview MSRTT; Vulkan: core multiview) | U3-042, U3-043, U3-046, GLES3-GF2-004 |

GLES multiview API details (view count, `gl_ViewID_OVR`, restrictions) are
owned by `gles3-perf:gles-extensions-multiview`.

## 7. Batch-break causes (read the Frame Debugger reason)

- Different shader or shader variant (keywords) - SRP Batcher batches by variant (U3-009, U3-011).
- MaterialPropertyBlock on the renderer (U3-010, U3-015).
- Different reflection probe, lightmap index or light probes (U3-008).
- GRD only: non-default sorting layer/order, MPB (U3-008, U3-032).
- `Renderer.material` access creating per-renderer material copies (UNITY-GF1-010).
- Static batch split by culling (U3-020).
- Shader not SRP-Batcher compatible: a Properties entry (often a `_ST` vector) outside `UnityPerMaterial` (U3-010).

## 8. Numbers index (with setup)

| Number | Setup | Evidence | ID |
|---|---|---|---|
| Multi-pass ≈ 2× CPU draw processing vs Multi-View | Meta OpenXR settings reference | [doc] | U3-041 |
| +64% per-draw CPU for a material switch, +175% for a shader switch, ~25% for redrawing the same object | Quest 1, Unity 2018.1.6f1, GLES, 500 quads, MT rendering off | [measured], stale | U3-004 |
| SRP Batcher 1.2×-4× CPU rendering; ×1.47 PS4 HDRP; ×1.23 PC DX11 | Unity 2019 blog | [measured], not Quest | U3-014 |
| 250 (mobile Vulkan) / 500: classic instanced-array default only; overridden on GLES3 and Vulkan by `UNITY_INSTANCING_SUPPORT_FLEXIBLE_ARRAY_SIZE` (CB sized per batch, `maxcount:N` ignored), so no published Quest cap | `UnityInstancing.hlsl` master | [doc] [verify on device] | U3-025 + spot-check |
| 64,000 vertices per static batch buffer | Unity manual | [doc] | U3-019 |
| 300 vertices / 900 attributes dynamic batching cap | Unity 6.0-6.5 manual | [doc] | UNITY-GF1-001 |
| 128 materials max under GRD | Unity 6.6 manual | [doc] | U3-032 |
| 1-1.5 ms fixed GPU resolve for intermediate target + final blit | Meta RenderDoc guide, Quest | [doc] | U3-049 |
| GRD 1,788 to 1,502 draws, CPU 5.8 to 6.1 ms, GPU +1 ms | PC, Unity 6, Nov 2024 | [community] | U3-039 |
| GRD: 200 trees to 5-10 draws | Android XR headset, Unity 6 | [measured], not Quest | U3-098 |
| Up to 1 ms CPU per enabled camera | generic low-end mobile, Unity 6 e-book | [doc] [verify on device] | UNITY-GF1-012 |

No published Quest 2/3/3S number exists for: SRP Batcher on vs off, GRD CPU
saving or GPU cost, GPU occlusion cost, BRG UBO vs SSBO cost, or the
Adreno vertex-shader saving from multiview (U3 numbers index, KU-22).
