# URP setting → GL calls → ovrgpuprofiler stage (GLES, Quest)

Deep reference for `gles3-perf:gles-tile-load-store`. Read it when an
`ovrgpuprofiler -t -v` trace of a GLES build shows a Load*/Store* stage or an
extra surface you cannot explain, or before adding a renderer feature to a
GLES project. All sources accessed 2026-09-24.

Evidence column: **doc** = Unity/Meta/Khronos states it; **inferred** = follows
from documented behaviour but Unity does not document the GL call; **unknown**
= no source, measure. Unity does not document which GL call each URP
load/store action becomes (KU-17). Every "GL calls" cell except the first row
is therefore inferred; confirm in a RenderDoc Meta Fork API log.

## 1. URP asset and renderer settings

| URP setting (path) | Versions | GL-level effect on GLES | Stage it shows in ovrgpuprofiler | Evidence | Finding |
|---|---|---|---|---|---|
| Final eye-buffer pass, empty URP scene | 2021.3.31f1, 2022.3.15f1; URP 12-14; OculusXR | Two `glInvalidateFramebuffer` per frame; read by posters as depth/stencil marked transient while colour stored | StoreColor only, if working | community (RenderDoc capture) | GLES3-GF2-003 |
| URP asset > Store Actions = Auto | URP 12.1, 14, 17 (17: Show All Advanced Properties) | Discard until a renderer feature injects a pass, then Store: full store + reload per pass | StoreDepthStencil and Load* on following surfaces | doc | G2-016 |
| URP asset > Store Actions = Discard | URP 12.1, 14, 17 | Expected invalidate of unneeded attachments; UUM-45041 shows GLES sometimes skips it (PowerVR/Mali, not Adreno 610) | StoreDepthStencil = 0 if honoured | doc + community; Quest unverified (KU-32) | G2-014, G2-C2 |
| URP asset > Opaque Texture = on | URP 12.1, 14, 17 | Mid-frame colour copy: FBO switch, store, reload. Without StoreAndResolve, MSAA ignored at runtime | Extra surface; LoadColor on the continuation; MSAA field may read 1 | doc | G2-017, G2-018 |
| URP asset > Opaque Downsampling | URP 12.1, 14, 17 | Shrinks only the copy destination | No change to the main-target store/reload | doc | G2-018 |
| Renderer > Depth Texture Mode = After Opaques | URP 14+ | Copy Depth between opaques and transparents: colour stored and reloaded, including MSAA data | Extra surface + LoadColor | doc | G2-019 |
| Renderer > Depth Texture Mode = After Transparents | URP 14+ | Copy after transparents; documented to save significant bandwidth on mobile | Fewer splits than After Opaques | doc | G2-019 |
| Renderer > Depth Priming = Forced | URP 14+ | Adds a depth prepass (whole extra geometry pass). Auto unsupported on Android | Extra surface with Binning + Render | doc | G2-020 |
| (URP internal) depth priming with GLES + MSAA | URP source 6000.3 | Priming turned off where GLES with MSAA cannot copy depth; MSAA depth not bound as a texture | n/a | doc (source) | U2-088 |
| Unity 2021.3 older than 9f1, any GLES3 | 2021.3 < 9f1, 2022.1 < 14f1 | Forced depth prepass (UUM-8381) | Unrequested DepthPrepass surface | community | G2-021 |
| Renderer > Native RenderPass = on | URP 14, 17 | No effect on GLES. `BeginRenderPass` emulated with `SetRenderTarget`; input attachments become texel fetches (`.Load()`) | Each subpass = its own surface | doc | G2-022, GLES3-GF1-008, GX-C6 |
| Render Graph merged native pass | URP 17 (Unity ≥ 6000.0) | Assumed lowered to FBO binds with graph-derived load/store; no Unity statement for GLES | unknown | unknown (KU-13) | G2-023 |
| Renderer > Intermediate Texture = Always | URP 14+ | Forces an intermediate RT + final blit; main pass loses compositor FFR on GLES | Extra full-screen surface, often Mode 0 (direct, one bin) | doc | G2-024, G2-061, G2-085 |
| Camera MSAA/HDR differs from URP asset | 6000.0.23f1+ until ported fix | GLES multipass validation error "Attachment AA sample counts must match" | n/a (error) | community | G2-027 |
| FullScreenRenderPass + Multiview + MSAA | 6000.0.51f1-6000.2; Won't Fix 6000.0-6000.5 | Transparents disappear on Quest 3/3S | n/a (correctness) | community | G2-026 (UUM-109377) |
| Opaque Texture in GLES XR | 2021.3, 2022.3, 6000.0 | "Double vision" | n/a (correctness) | community | G2-026 (UUM-70930) |

## 2. Script-level APIs

| API | GL-level effect | Evidence | Finding |
|---|---|---|---|
| `RenderBufferLoadAction.Load` | Preserves contents → per-bin load | doc | G2-013 |
| `RenderBufferLoadAction.Clear` | Documented to work only with the RenderPass API; issue an explicit clear on GLES | doc | G2-013 |
| `RenderBufferLoadAction.DontCare` | No load into tile memory | doc | G2-013 |
| `RenderBufferStoreAction.Store` | Stores the unresolved MSAA surface when MSAA is on | doc | G2-013 |
| `RenderBufferStoreAction.StoreAndResolve` | Silently becomes Resolve when `supportsStoreAndResolveAction` is false | doc | G2-015 |
| `RenderBufferStoreAction.DontCare` | Skips write-out; "might be ignored at runtime" on some platforms | doc | G2-013 |
| `RenderTexture.DiscardContents(color, depth)` | Hint that contents are unused (both buffers by default) | doc | G2-025 |
| `RenderTexture.MarkRestoreExpected` | Marks an intended restore (render without prior clear/discard), which Unity calls costly on mobile | doc | G2-025 |
| `LoadStoreActionDebugModeSettings` | Highlights "INVALIDATED" regions; Game view and dev builds; 2022.3 and 6000.0-6000.6 | doc | G2-025 |
| `RenderTexture.bindTextureMS = true` + `antiAliasing > 1` | Real multisample storage; defeats on-tile resolve | doc | G2-043 |
| `Texture2D.ReadPixels`, `CommandBuffer.RequestAsyncReadback` | Mid-pass: implicit flush/resolve, pass split | inferred | G2-028, G2-029 |
| `GraphicsFence` | Possible pass split; client waits block the render thread | inferred | G2-029, G2-030 |
| Blit copy path (`CommandBuffer.Blit` vs `Blitter`) | Which GL call is used is undocumented; on Adreno `glBlitFramebuffer` beats a full-screen quad | unknown | G2-031 |

## 3. Load/store stage names

| Stage | Meaning on GLES | Action |
|---|---|---|
| LoadColor / LoadDepthStencil | GMEM filled from DRAM at bin start | Missing clear/invalidate (G2-009) |
| StoreColor | Resolve/write-out of colour; with MSRTT only the resolved image | Expected on the eye buffer |
| StoreDepthStencil | Depth written to DRAM | Missing invalidate, or invalidate issued after a flush (G2-006) |

Binning, Render, Preempt, the Mode legend and RenderDoc's Tile Timeline:
`quest-perf:quest-profiling-toolkit`.

## 4. Confirming a row on device

1. Enable detailed mode, run `adb shell ovrgpuprofiler -t2 -v`, record the
   eye-buffer surface stages.
2. Capture one frame in RenderDoc Meta Fork (Horizon OS 68+; timer query type
   per-renderpass; replay optimisation Fastest) and list GL calls between the
   eye-FBO bind and the next bind.
3. Toggle the one setting, repeat 1-2. Record Unity version, URP version, XR
   plugin and OS build with the result, since KU-13/KU-17 are open.

Sources: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ ;
https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ ;
https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ ;
https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ ;
https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html ;
https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture.DiscardContents.html ;
https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture.MarkRestoreExpected.html ;
https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/urp-universal-renderer.html ;
https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/render-graph-introduction.html ;
https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/NativePassCompiler.cs ;
https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRendererRenderGraph.cs ;
https://discussions.unity.com/t/multiple-frame-buffer-invalidations-urp/935652 ;
https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ;
https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html ;
Unity issue tracker UUM-45041, UUM-8381, UUM-70930, UUM-109377, UUM-91896
(https://issuetracker.unity.com/api/v1.0/issues?q={id}). All accessed 2026-09-24.
