# Multisampled render-to-texture (MSRTT) on Quest GLES

Deep reference for `gles3-perf:gles-tile-load-store`. Read it when writing a
native GL MSAA path, when checking whether Unity's GLES MSAA stays on tile, or
when MSAA quality or cost changes after adding a pass. MSAA level choice is
`unity-perf:unity-urp-settings`; the hardware resolve is
`arm-mobile-hw-perf:xr2-adreno-architecture`. All sources accessed 2026-09-24.

## 1. Availability (device capability dumps)

| | Quest 2 (gpuinfo report 6387) | Quest 3 (gpuinfo report 8023) |
|---|---|---|
| GPU | Adreno 650 | Adreno 740 |
| GLES driver | `OpenGL ES 3.2 V@0690.0` (12/13/22) | `V@0837.0.7` (01/12/26) |
| Android | 12 | 14 |
| `GL_EXT_multisampled_render_to_texture` | yes | yes |
| `GL_EXT_multisampled_render_to_texture2` | yes | yes |
| `GL_OVR_multiview_multisampled_render_to_texture` | yes | yes |
| `GL_OVR_multiview`, `GL_OVR_multiview2` | yes | yes |
| `GL_MAX_SAMPLES` | 4 | 4 |

Quest 3S shares the Adreno 740; UUM-149765 lists the same V@0837.0.7 GLES
driver on a Quest 3S. These are user-submitted dumps; the driver on a given
headset depends on its OS build, so query at runtime (G1-007, G1-010, G2-035,
[measured]). 8x MSAA does not exist on Quest GLES.

## 2. The three extensions

| Extension | Entry point | What it does | Finding |
|---|---|---|---|
| `EXT_multisampled_render_to_texture` | `glFramebufferTexture2DMultisampleEXT`, `glRenderbufferStorageMultisampleEXT` | Single-sample texture with N-sample storage on tile; samples resolved on chip at store, multisample data discarded. DRAM traffic equals no-MSAA; cost moves to GMEM footprint (more bins) and shading/ROP | G2-036 |
| `EXT_multisampled_render_to_texture2` | same | Extends MSRTT to any attachment incl. depth/stencil. A multisampled depth/stencil **texture** is discarded at resolve (equivalent to `glInvalidateFramebuffer`); a **renderbuffer** is not. Client reads before later rendering may downsample early | G2-037 (spec rev 4, 2025-10-22) |
| `OVR_multiview_multisampled_render_to_texture` | `glFramebufferTextureMultisampleMultiviewOVR(target, attachment, texture, level, samples, baseViewIndex, numViews)` | One-pass stereo + on-tile MSAA into a `TEXTURE_2D_ARRAY`. Mid-frame resolve on a tiler may lose the samples | G2-038 (spec rev 0.4, 2015) |

Meta states the same for the Quest GLES path: textures stay non-MSAA with an
MSAA framebuffer, and the hardware resolve sits in the store path (G2-036).

## 3. Implicit resolve triggers (samples lost)

While an MSRTT attachment is bound, any of these resolves and discards the
multisample data; rendering continues from the resolved single-sample image,
so AA quality is lost and the pass is paid twice (G2-028, EXT spec):

- binding another FBO;
- `glReadPixels`, `glCopyTex[Sub]Image`, `glBlitFramebuffer`;
- `Tex*Image` on the attached level;
- `glGenerateMipmap`;
- `glFlush` / `glFinish`;
- drawing with the attached texture bound for sampling.

Unity-side equivalents (inferred, [verify on device]): Opaque Texture copy,
Copy Depth After Opaques, `ReadPixels`/async readback mid-pass, any
full-screen pass that samples the eye buffer (G2-029, GLES3-GF2-004 notes).

## 4. What Unity uses

| Target | Path | Evidence |
|---|---|---|
| Multiview (Single Pass Instanced/Multiview) eye buffer, Android | `GL_OVR_multiview2` + `GL_OVR_multiview_multisampled_render_to_texture`, 2-slice 2D array | Unity manual 2022.3, 6000.0, 6000.3, 6000.6 (GLES3-GF2-004) [doc] |
| Non-multiview MSAA render targets | unknown: `EXT_multisampled_render_to_texture` or real MSAA + explicit resolve | KU-18; look for `glFramebufferTexture2DMultisampleEXT` in a RenderDoc API log [verify on device] |
| RT with `bindTextureMS = true` | real multisample storage, no default resolve | Unity scripting reference (G2-043) [doc] |

Runtime signals: `SystemInfo.supportsMultisampleAutoResolve` true is
consistent with MSRTT (G2-044); `supportsStoreAndResolveAction` false means
StoreAndResolve becomes Resolve and Opaque Texture drops MSAA (G2-015,
G2-017). Log both on each headset/OS build.

## 5. Measured costs

UUM-149765, Quest 3/3S (Adreno 740, GLES driver V@0837.0.7), Unity
6000.0.81f1, 6000.3.21f1, 6000.5.7f1, 6000.6.0b7, 6000.7.0a4; levels locked
at 3; Optimized Buffer Discards on; 63 bins of 192x256 at 4x (G2-039,
[measured]):

| Config | Total | Binning | Render | StoreColor |
|---|---|---|---|---|
| GLES, MSAA off | 9.7 ms | 4.5 | 4.2 | 0.04 |
| GLES, 4x | 13.0 ms | 5.1 | 6.3 | 0.15 |
| Vulkan, MSAA off | 9.1 ms | 4.5 | 3.7 | 0.18 |
| Vulkan, 4x | 14.1 ms | 5.1 | 7.0 | 0.45 |

- Conflict G2-C9: the same report's notes give Quest 3 GLES about 12 / 15 ms
  and Vulkan about 11 / 16 ms (off / 4x). Quote the deltas (+3.3 ms GLES,
  +5.0 ms Vulkan), not the absolutes.
- Quest 2 (report notes): about 14 ms off, about 21 ms at 4x on Vulkan, GLES
  within about 1 ms: roughly +7 ms for 4x (G2-040). 1 MB GMEM forces many more
  bins at 4x (G2-002).
- GLES StoreColor growth (0.04 → 0.15 ms) fits the resolved-only store; the
  GLES MSAA cost is Render + Binning growth (G2-041; inference, KU-18).
- Qualcomm phone sample (Adreno 530, pre-2023): explicit 4x renderbuffer +
  `glBlitFramebuffer` resolve took about 2.5 ms for the blit alone; MSRTT
  saved about 3 ms in total (G2-042, [measured]).
- 2x on Quest GLES: no published number. Qualcomm "likely practically free";
  Meta Quest 1 data shows a real cost; Unity 6.6 checklist calls 2x "a good
  balance" (G2-045, G2-C3, G1-048). Measure 1x/2x/4x with the G2-010 recipe
  (KU-24).

## 6. Native plugin sketch (GLES 3.x, C)

```c
/* Single-view, 4x on tile, colour texture + depth24/stencil8 texture (EXT_..._2). */
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glFramebufferTexture2DMultisampleEXT(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                                     GL_TEXTURE_2D, colorTex, 0, 4);
glFramebufferTexture2DMultisampleEXT(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT,
                                     GL_TEXTURE_2D, depthTex, 0, 4);
const GLenum all[] = { GL_COLOR_ATTACHMENT0, GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 3, all);   /* no per-bin load */
/* draws; no reads, flushes, mip generation or rebinds until done */
const GLenum ds[] = { GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, ds);    /* before any flush */
```

Check the extension string and `GL_MAX_SAMPLES` before use; resolve functions
through `eglGetProcAddress`. Untested sketch [verify on device].

Sources: https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture.txt ;
https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture2.txt ;
https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview_multisampled_render_to_texture.txt ;
https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ ;
https://opengles.gpuinfo.org/displayreport.php?id=6387 ;
https://opengles.gpuinfo.org/displayreport.php?id=8023 ;
https://docs.unity3d.com/6000.6/Documentation/Manual/Android-SinglePassStereoRendering.html ;
https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture-bindTextureMS.html ;
https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsMultisampleAutoResolve.html ;
https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsStoreAndResolveAction.html ;
https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html ;
https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 ;
https://github.com/quic/adreno-gpu-opengl-es-code-sample-framework ;
https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ;
https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ . All accessed 2026-09-24.
