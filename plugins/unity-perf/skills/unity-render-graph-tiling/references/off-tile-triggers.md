# Off-tile triggers, pass-break reasons and load/store reasons

Deep reference for `unity-perf:unity-render-graph-tiling`. Read it when the
Render Graph Viewer or an `ovrgpuprofiler -t` trace shows a pass, store, load
or surface you cannot explain. All sources were accessed 2026-09-24.

## 1. What forces an intermediate, a final blit, or a pass split

URP 14 `RequiresIntermediateColorTexture` returns true for any of the items
below. The logic carries into URP 17 in modified form (U2-030, [doc],
https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderer.cs).
The 6.6 pages add the Render Graph and Tile-Only view (U2-031/032, [doc],
https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html ,
https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html).

| Trigger | What happens | Replacement on Quest | Versions |
| --- | --- | --- | --- |
| Post-processing on (renderer **or** camera checkbox) | Intermediate + Uber "Blit Post Processing" (U2-038); camera ticked while renderer off still blits (Q3-013, issue 22353) | 6.3+ on-tile post; before 6.3, off | all |
| Bloom | Adds "Blit Bloom Mipmaps" passes; never on-tile (U2-038, U2-076) | Baked glow in materials | all |
| FXAA, FSR/non-linear upscaler, TAA + RCAS | Forces a final post blit even with other effects off (U2-038) | MSAA; render scale | 6.3 source ([community]) |
| Depth Texture (asset or camera, or any `ConfigureInput(Depth)`) | Copy Depth pass, depth stored; splits the pass (U2-070) | Depth input attachment (6.6) or Meta fork | all |
| Opaque Texture | Copy Color pass. Default 2x Bilinear downsample gives `TargetSizeMismatch`. On mobile without StoreAndResolve, MSAA is silently ignored (U2-004) | Framebuffer fetch (current pixel only) | all |
| HDR | Intermediate colour; 64-bit colour doubles bytes per pixel (U2-030, U2-035) | HDR off (conflict U2-C6: follow source) | all |
| MSAA explicit resolve | Intermediate (URP 14). On 6.6 Tile-Only it is listed as unsupported (conflict U2-C2) | Let the eye swapchain be multisampled (U2-050) | all |
| Non-default viewport rect / subrectangle viewport | Intermediate | Full viewport | all |
| Camera stacking / base camera that doesn't resolve the final target | Intermediate; unsupported in Tile-Only (U2-039) | Draw UI and hands in the base camera, or use compositor layers (`quest-perf:quest-compositor-layers`) | all |
| Deferred path | Intermediate; off-tile in Tile-Only | Forward / Forward+ | all |
| Upscaling filter; dynamic resolution ("except on Android XR", scope unclear) | Intermediate (U2-032) | Render scale / `renderViewportScale` → `quest-perf:quest-resolution-foveation` | 6.5+ page |
| IMGUI (OnGUI) | Off-tile (U2-032) | Remove from dev builds used for profiling | 6.5+ page |
| FullScreenPass with Fetch Color Buffer = true (default) | `requiresIntermediateTexture = true`, colour copy (U2-026) | Untick it and use framebuffer fetch in the shader | URP 14+ |
| SSAO, Decals | Need intermediates (U2-031) | Baked AO; mesh decals | all |
| TAA | Off-tile (U2-032) | MSAA | 6.5+ page |
| Scene view, camera capture actions, sRGB conversion requirement | Intermediate (U2-030) | Profile on device only | all |
| `OnRenderObject` in any script | `OnRenderObjectCallbackPass` prevents subpass merging (U2-087) | Remove it | fork + all [verify on device] |
| Compute or `AddUnsafePass` on camera colour | `NonRasterPass`, never merges (U2-064) | Raster pass + framebuffer fetch; downsample for histograms | 6.0+ |
| `CommandBuffer.Blit` / `Graphics.Blit` / `RenderingUtils.Blit` | Can break XR and native render passes (U2-068) | `Blitter`, `AddBlitPass`, `AddCopyPass` | URP 14+ |
| Blit back into camera colour | Extra full-screen pass (U2-065) | `resourceData.cameraColor = destination` | 6.0+ |
| Full-screen pass with no depth and no MSAA | May drop to Adreno Direct Mode (one bin, FFR off) (U2-034) | Merge it into the main pass | all [verify on device] |
| Geometry shaders | Extra primitives break the tiled flow (U2-080) | Avoid | all |

Meta also notes that copying or blitting into the swapchain afterwards may stop
FFR and MSAA from applying (U2-033). On the Meta (Legacy) FFR API,
intermediates escape foveation (Q3-013 notes).

## 2. `PassBreakReason` values (Native Pass Compiler)

Source: https://github.com/Unity-Technologies/Graphics/blob/6000.5/staging/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/PassesData.cs
(U2-058, [doc]). Unity 6.0 has only the values up to `FRStateMismatch` plus
`Merged`. The viewer's "Pass break reasoning" prints these names.

| Reason | Cause | Fix |
| --- | --- | --- |
| `NonRasterPass` | Compute or unsafe pass | Rewrite as raster; move compute off camera colour |
| `TargetSizeMismatch` | Different size or MSAA sample count | Full-res targets at the camera sample count; no downsampled opaque texture |
| `NextPassReadsTexture` | Next pass samples this output with `UseTexture` | `SetInputAttachment` (framebuffer fetch) |
| `NextPassTargetsTexture` | Next pass targets a texture this pass uses in a conflicting way | Re-order passes or merge targets |
| `DifferentDepthTextures` | One depth per native pass | Share the camera depth |
| `AttachmentLimitReached` | More than 8 attachments | Pack MRT outputs |
| `SubPassLimitReached` | More than 8 subpasses | Fold passes together |
| `FRStateMismatch` | Foveated-rendering state differs between passes | Keep the same foveation state across the chain [verify on device] |
| `DifferentShadingRateImages` / `DifferentShadingRateStates` | VRS state differs | Same VRS state across the chain |
| `MultisampledShaderResolveMustBeLastPass` | Shader resolve not in the last pass | Resolve last (A2-055) |
| `ExtendedFeatureFlagsIncompatible` | Extended feature flags differ | Match flags |
| `PassMergingDisabled` | The 6.1+ debug switch is on | Turn it off after the A/B |
| `BackbufferInMultipleRenderTargetsNotSupported` | Backbuffer plus user RTs as MRT, where `SystemInfo.supportsBackbufferInMultipleRenderTargets` is false (U2-059) | Log the flag on Quest 2 and Quest 3 [verify on device] |
| `EndOfGraph`, `Merged` | Normal | — |

Exemptions (U2-060):
- A raster pass with no fragment attachments merges without the attachment
  checks.
- Reading a texture whose producer was culled does not break the merge.

## 3. Load and store audit reasons (viewer, per attachment)

Source: same `PassesData.cs` (U2-062, [doc]).

- **Load:** `LoadImported`, `LoadPreviouslyWritten`, `ClearImported`,
  `ClearCreated`, `FullyRewritten`.
- **Store:** `StoreImported`, `StoreUsedByLaterPass`, `DiscardImported`,
  `DiscardUnused`, `DiscardBindMs`, `NoMSAABuffer`.

Target on Quest:
- Every attachment starts `Clear*` or `FullyRewritten`.
- Only the eye colour (Backbuffer) stores.
- `StoreUsedByLaterPass` on depth means a downstream reader, such as a depth
  copy or depth-sampling effect.
- `LoadPreviouslyWritten` on camera colour means a pass split.

Memoryless (U2-061, NativePassCompiler.cs):
- The compiler marks a transient attachment memoryless only if
  `SystemInfo.supportsMemorylessTextures` is true.
- Loading or resolving a memoryless resource throws.
- Input attachments used with multisampled shader resolve must be memoryless.
- DoF and other neighbour-sampling depth effects push `_CameraDepthAttachment`
  out of memoryless (U2-076, [community]).

## 4. Tile-relevant changes by version

Sources: What's New 6.1-6.6 and the upgrade guides (U2-073, U1-023 to 026,
X-C10, U1-C5), plus the Meta subpass page (U2-084). For the full matrix, see
`unity-perf:unity-version-matrix`.

| Version | URP | Tile-relevant state |
| --- | --- | --- |
| 2021.3 | 12 | Native RenderPass toggle (off by default); docs entry missing, so behaviour is unverified; Store Actions |
| 2022.3 | 14 | Native RenderPass (off by default, Vulkan only); Store Actions; input attachments internal; Meta `2022.3/staging-subpass` fork (2022.3.42f1+) |
| 6.0 | 17.0 | Render Graph default; upgraded projects open in Compatibility Mode; UUM-90118 (+~20% GPU) fixed in 6000.0.46f1; Meta forks for 6000.0.23+ |
| 6.1 | 17.1 | Debug switch to disable pass merging; Meta Quest build profile |
| 6.2 | 17.2 | Stricter merging; `VK_QCOM_render_pass_shader_resolve` for Quest MSAA; Visible Triangle Mesh; AfterRendering now runs after the final blit (U1-024) |
| 6.3 | 17.3 | Shared RG compiler; on-device RG Viewer; `AddBlitPass` builder; on-tile post (XR); Vulkan subpasses built in; Compatibility Mode only behind `URP_COMPATIBILITY_MODE`; on-tile only on the Universal Renderer from 6000.3.23f1 |
| 6.4 | 17.4 | Compatibility Mode removed; `StoreActionsOptimization` obsolete; non-RG passes stop working |
| 6.5 | 17.5 | Tile-Only Mode + validation; on-tile post for all platforms; Quest shader optimizations |
| 6.6 | 17.6 | Depth input attachment (DX12/Vulkan); Tile-Only falls back on a non-sRGB backbuffer (6000.6.0b6); URP Settings Analyzer |

The URP versions come from U1-010 (package.json per branch, [doc]). 6.6 → 17.6
is inferred from master. From Unity 6, URP is locked to the Editor version, so
fixes arrive as Editor patches (U1-011).

## 5. Meta subpass fork limits (U2-085, U2-086)

Source: https://developers.meta.com/horizon/documentation/unity/vulkan-subpasses/ [doc]

- Branches (Oculus-VR/Unity-Graphics), for 2022.3.42f1+ and
  6000.0.23f1-6000.2.x (U2-084):
  - `2022.3/staging-subpass`
  - `17.0.3-subpass` (6000.0.23-39)
  - `6000.0/17.0.4-subpass` (6000.0.40-6000.2.x)
- Before 6000.3 these branches are incompatible with Dynamic Resolution and
  AppSW, a real trade for 72 Hz titles that rely on AppSW (U2-084).
- Meta comments out `OnRenderObjectCallbackPass` because it prevents merging.
  Any script using `OnRenderObject` adds that pass (U2-087) [verify on device].

- All subpasses need the same framebuffer size and can read only the current
  pixel.
- Tile-compatible post: Channel Mixer, Color Adjustments, Color Curves, Color
  Lookup, Film Grain, Lift Gamma Gain, Shadows Midtones Highlights, Split
  Toning, Tonemapping, Vignette, White Balance.
- Incompatible: Bloom, Chromatic Aberration, Depth of Field, Lens Distortion,
  Motion Blur, Panini Projection.
- Depth input setup:
  1. Add a `DepthInputSubpass` layer.
  2. Untick Depth and Opaque Texture.
  3. Set Intermediate Texture to Auto.
  4. Add a Render Objects feature at AfterRenderingOpaques/Transparents with
     Depth and Depth Input overrides and Write Depth off.
  5. Use the `_DEPTH_INPUT_ATTACHMENT` keyword and
     `FRAMEBUFFER_INPUT_FLOAT_MS(depth_input)` /
     `LOAD_FRAMEBUFFER_INPUT_MS(depth_input, 0, float2(0,0))`.
- Known issues:
  - OVRManager "Use Recommended MSAA Level" causes a first-frame glitch. Keep
    one MSAA owner, the URP asset (U2-050).
  - The Unity 6 Editor with Vulkan, OpenXR and MSAA renders black.
  - Before 6000.3, the fork is incompatible with Dynamic Resolution and AppSW.
