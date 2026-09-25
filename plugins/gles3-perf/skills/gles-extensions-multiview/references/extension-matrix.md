# GLES extension matrix: Quest 2 vs Quest 3/3S

All presence values come from user-submitted opengles.gpuinfo.org reports, so the matrix is [measured] but thin: seven Quest reports exist in the whole database (8292 reports walked on 2026-09-24), the newest Quest 2 report is from 2023-01-13 and no report is identifiable as Quest 3S (GLES3-GF1-005). Quest 3S shares the Adreno 740 and UUM-149765 lists the same V@0837.0.7 GLES driver on a Quest 3S (G1-007), so the Quest 3 column is the best available proxy for 3S [verify on device]. Always gate native use on a runtime `glGetStringi` check (SKILL.md, Diagnose step 2).

## Reports behind the matrix

| Report | Device string | GPU | Date | Android | Driver | Extension badge |
|---|---|---|---|---|---|---|
| 5092 | Quest | Adreno 650 | 2020-12-20 | - | V@0514.0 | see note |
| 5278 | Quest | Adreno 650 | 2021-04-03 | - | - | - |
| 5808 | Quest | Adreno 650 | 2022-02-24 | - | V@0582.0 | see note |
| 6387 | Quest | Adreno 650 | 2023-01-13 | 12 | V@0690.0 | 110 GL + 34 EGL |
| 7267 | Quest | Adreno 740 | 2024-03-29 | 12 | V@0757 or V@0767 | 122 GL |
| 7475 | Quest | Adreno 740 | 2024-07-07 | 12 | V@0767.0 | 122 GL |
| 8023 | Quest 3 | Adreno 740 | 2026-02-20 | 14 | V@0837.0.7 | 123 GL + 35 EGL |

Device string is as submitted: only 8023 reads "Quest 3"; the others read "Quest", and the headset is inferred from the GPU (Adreno 650 = Quest 2, Adreno 740 = Quest 3). Sources: G1-001, G1-002, GLES3-GF1-005, G3-071. Across the Quest 2 reports the GL count rose 99 -> 102 -> 110 as drivers updated (G1-002 notes). Extension-count conflict GX-C3: G1-015 says "157 vs 143"; the report badges say 158 (123 + 35) vs 144 (110 + 34). Use the badges. Both drivers report `OpenGL ES 3.2`, GLSL ES 3.20, EGL `1.5 Android META-EGL` (G1-001 to G1-003).

## Matrix

"0582+" / "V@0690+" = present on Quest 2 only from that driver build onward. Finding IDs refer to research/gles3.md.

| Extension | Quest 2 | Quest 3 | What it does | Unity / Meta use | Finding |
|---|---|---|---|---|---|
| GL_OVR_multiview, GL_OVR_multiview2 | yes | yes | single-pass stereo into a 2-slice array | Unity Multiview on GLES (OculusXR) | G2-047, G2-048, G1-010 |
| GL_OVR_multiview_multisampled_render_to_texture | yes | yes | MSAA multiview, resolved on tile | named in Unity's Android single-pass stereo page (2022.3-6000.6); actual call [verify on device] | GLES3-GF2-004 |
| GL_EXT_multisampled_render_to_texture / _2 | yes | yes | MSAA without storing samples | not documented [verify on device] | G2-036 / G3-048 |
| GL_QCOM_texture_foveated | yes | yes | FFR per texture / per array layer | Meta FFR on GLES; mechanism undocumented | G2-059, G2-060 |
| GL_QCOM_texture_foveated2 | 0582+ | yes | cut-off density, discards low-density pixels | not documented | G3-051 |
| GL_QCOM_texture_foveated_subsampled_layout | yes | yes | FFR without upscale bandwidth | Unity path needs Vulkan | G1-035 / G3-052 |
| GL_QCOM_shading_rate | 0582+ | yes | per-draw VRS, 1x1 to 4x4 | not documented | G3-055 |
| GL_EXT_fragment_shading_rate (+_attachment, +_primitive) | no | yes | image / primitive VRS | not documented | G1-012, G3-056 |
| GL_EXT_fragment_invocation_density | yes | yes | shader built-ins under reduced-density shading | not documented | 7.1 matrix |
| GL_EXT_shader_framebuffer_fetch (coherent) | yes | yes | read colour on tile | URP GLES does not use it; custom shaders may | G3-057, GLES3-GF1-008 |
| GL_QCOM_shader_framebuffer_fetch_noncoherent | yes | yes | fetch without per-primitive sync (needs barrier) | not documented | G3-057 |
| GL_QCOM_shader_framebuffer_fetch_rate | yes | yes | fetch at fragment rate under MSAA | not documented | G3-058 |
| GL_ARM_shader_framebuffer_fetch_depth_stencil | yes | yes | read depth on tile | not documented | G1-011, G3-034 |
| GL_EXT_shader_framebuffer_fetch_non_coherent | no | no | - | - | G3-057 |
| GL_EXT_shader_pixel_local_storage | no | no | Mali-only | - | G3-057 |
| GL_EXT_discard_framebuffer (+ core glInvalidateFramebuffer) | yes | yes | skip GMEM loads/stores | owned by gles-tile-load-store | 7.1 matrix |
| GL_QCOM_tiled_rendering | yes | yes | manual tile control (2009) | none; ignore for Unity | G2-091 / G3-061 |
| GL_QCOM_binning_control | no | no | force binned/direct | cannot be used on Quest | G2-092 |
| GL_QCOM_frame_extrapolation | no | yes | `ExtrapolateTex2DQCOM` | none; treat as unavailable | G3-062 |
| GL_QCOM_motion_estimation | yes | yes | block motion vectors | none | G3-062 |
| GL_EXT_texture_compression_astc_decode_mode | V@0690+ | yes | decode LDR ASTC to UNORM8 | none (native plugin only) | G3-063 |
| GL_KHR_texture_compression_astc_ldr / _hdr | yes | yes | ASTC | texture import | 7.1 matrix |
| GL_EXT_texture_compression_bptc / rgtc / s3tc(_srgb) | V@0690+ | yes | BCn formats | - | 7.1 matrix |
| GL_EXT_texture_filter_anisotropic | yes | yes | anisotropic filtering | Unity texture Aniso Level | G3-064 |
| GL_IMG_texture_filter_cubic | 0582+ | yes | cubic filtering | none | 7.1 matrix |
| GL_QCOM_texture_lod_bias | no | yes | per-texture LOD bias | unknown whether `Texture.mipMapBias` maps to it | G3-066 |
| GL_QCOM_render_shared_exponent | no | yes | renderable RGB9_E5 (32 bpp HDR) | not documented | G3-065 |
| GL_QCOM_render_sRGB_R8_RG8, GL_EXT_texture_sRGB_RG8 | no | yes | sRGB R8/RG8 targets | unknown | G1-015 |
| GL_EXT_clip_control | yes | yes | [0,1] depth range | Unity GLES keeps -1..1 (no reversed Z) | G3-067, G3-035 |
| GL_EXT_depth_clamp | no | yes | depth clamp | unknown | G1-015 |
| GL_EXT_disjoint_timer_query | yes | yes | GPU timers | distorts tiled timings; no queries inside multiview | G1-014, G2-034 / G3-068 |
| GL_KHR_debug, GL_EXT_debug_marker / _label | yes | yes | capture markers | tools | G1-014 |
| GL_KHR_no_error | yes | yes | error-free contexts | Low Overhead Mode, owned by gles-driver-overhead | 7.1 matrix |
| GL_EXT_buffer_storage | yes | yes | persistent coherent mapped buffers | Unity use not documented | G3-070 |
| GL_EXT_clear_texture | no | 2026 driver only | glClearTexImage | unknown | G3-071 |
| GL_OES_get_program_binary, GL_QCOM_validate_shader_binary | yes | yes | program binaries | owned by gles-shader-binaries; QCOM spec 404 | G3-072 |
| ES 3.1 AEP set (geometry, tessellation, texture_buffer, cube_map_array, gpu_shader5, sample_shading) | yes | yes | ES 3.2 feature set | Qualcomm: avoid tessellation for performance | G1-013 / G3-043 |
| EGL_IMG_context_priority | yes | yes | context priority | compositor (inferred) | G3-069 |
| EGL_NV_context_priority_realtime | no | yes | realtime priority | compositor (inferred) | G3-069 |
| EGL_ANDROID_native_fence_sync | V@0690+ | yes | fence FDs | runtime | 7.1 matrix |

Quest 3 (V@0837) adds exactly 13 GL + 1 EGL extensions over Quest 2 (V@0690): EXT_clear_texture, EXT_depth_clamp, EXT_fragment_shading_rate (+_attachment, +_primitive), EXT_render_snorm, EXT_shader_implicit_conversions, EXT_texture_sRGB_RG8, KHR_texture_compression_astc_sliced_3d, QCOM_frame_extrapolation, QCOM_render_sRGB_R8_RG8, QCOM_render_shared_exponent, QCOM_texture_lod_bias; EGL_NV_context_priority_realtime (G1-015 / G3-044).

Limits: `GL_MAX_SAMPLES` = 4 on both, so 4x is the GLES MSAA ceiling (G1-007 / G1-010 / G2-035). `GL_MAX_VIEWS_OVR` (spec minimum 2) and `GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT` are not in the reports (KU-21, KU-30); the probe in SKILL.md reads both.

## API details for native-plugin authors

Everything here is reachable only from a native rendering plugin; Unity exposes none of it from C#.

- **OVR_multiview** (G2-047, G2-049): `glFramebufferTextureMultiviewOVR(target, attachment, texture, level, baseViewIndex, numViews)` onto a 2D array texture; VS declares `layout(num_views = 2) in;` and reads `gl_ViewID_OVR`. Program view count != FBO view count is INVALID_OPERATION. Restrictions: no transform feedback, tessellation or geometry shaders; no timer queries; occlusion results between per-view max and sum; one clear, viewport and scissor for all views; `gl_Layer` undefined in FS; ReadPixels / CopyTex* / Blit from a multi-view read FBO is INVALID_FRAMEBUFFER_OPERATION (needs a single-view FBO per layer, i.e. another pass). Tokens: `MAX_VIEWS_OVR` 0x9631, `FRAMEBUFFER_ATTACHMENT_TEXTURE_NUM_VIEWS_OVR` 0x9630, `..._BASE_VIEW_INDEX_OVR` 0x9632, `FRAMEBUFFER_INCOMPLETE_VIEW_TARGETS_OVR` 0x9633.
- **OVR_multiview2** (G2-048): lets outputs other than `gl_Position` depend on `gl_ViewID_OVR`; enabling it enables multiview. Spec status Incomplete (rev 0.5).
- **MSRTT** (G2-036 / G3-048): `glFramebufferTexture2DMultisampleEXT`, `glRenderbufferStorageMultisampleEXT`; multiview variant `glFramebufferTextureMultisampleMultiviewOVR`. Samples resolved on chip at store; `glReadPixels` / `glBlitFramebuffer` forces an implicit flush + resolve mid-frame.
- **QCOM_texture_foveated** (G2-059, G2-060): enable with `TEXTURE_FOVEATED_FEATURE_BITS_QCOM` = `FOVEATION_ENABLE_BIT_QCOM | FOVEATION_SCALED_BIN_METHOD_BIT_QCOM`; per layer `glTextureFoveationParametersQCOM(texture, layer, focalPoint, focalX, focalY, gainX, gainY, foveaArea)`. Rules (spec rev 5): one foveated attachment only; `gl_FragCoord` scaled but dFdx/dFdy, interpolateAtOffset and `gl_SamplePosition` not corrected (issue 4); depth inherits foveation, clear or invalidate every attachment; a Load of the foveated attachment makes the driver unresolve it and can silently disable FFR for the pass (issue 7); tessellation, geometry shaders and compute may disable foveation (issue 9). In a Unity app the runtime/compositor sets this on the swapchain, not app code (G2-061).
- **QCOM_texture_foveated2** (G3-051): `TEXTURE_FOVEATED_CUTOFF_DENSITY_QCOM` 0-1; pixels below the cutoff are discarded. Linking it to the black regions in Meta's FFR maps is the dossier's inference.
- **QCOM_shading_rate** (G3-055): per-draw rate 1x1 to 4x4; Qualcomm says VRS and foveation combine.
- **QCOM_shader_framebuffer_fetch_noncoherent** (G3-057): enable `FRAMEBUFFER_FETCH_NONCOHERENT_QCOM`, call `glFramebufferFetchBarrierQCOM()` where needed; avoids per-primitive pixel-pipe flushes.
- **QCOM_shader_framebuffer_fetch_rate** (G3-058): `gl_LastFragData` / `gl_LastFragDepthARM` reads run per fragment instead of per sample; without it, up to 4x fragment work at 4x MSAA (derived from sample count, not measured).
- **Framebuffer-fetch precision** (G3-034): `gl_LastFragData` defaults to mediump (fp16 at best from RGBA16F); `gl_LastFragDepthARM` is highp, waits for earlier fragments (read late), incompatible with `early_fragment_tests`.
- **QCOM_tiled_rendering** (G2-091): `glStartTilingQCOM(x, y, w, h, preserveMask)` / `glEndTilingQCOM(preserveMask)`; Flush, Finish or FBO rebind ends tiling; mixing with normal rendering can double resolve cost.
- **QCOM_binning_control** (G2-092): `glHint(GL_BINNING_CONTROL_HINT_QCOM, ...)` does not exist on Quest; FlexRender binned/direct choice is not controllable (KU-39).
- **QCOM_frame_extrapolation** (G3-062): `ExtrapolateTex2DQCOM(src1, src2, output, scaleFactor)`, 0.5 for every other frame; RGBA8, RGB8, R8, RGBA16F, RGB16F, RGBA32F, RGB32F. Qualcomm: can nearly double a fragment-bound app's framerate. Not tied to AppSW by any Meta/Unity doc; the Quest runtime owns timing and reprojection.
- **EXT_texture_compression_astc_decode_mode** (G3-063): `TEXTURE_ASTC_DECODE_PRECISION_EXT`; default decode is RGBA16F, UNORM8 cuts texture-cache footprint and power. No Quest number; measure `% Texture L1 Miss` with `ovrgpuprofiler -r5,6`.
- **EXT_disjoint_timer_query** (G2-034 / G3-068): check `GPU_DISJOINT_EXT`; on a binner a query sums all bins and costs about 2-5 us per timed draw per tile; on GLES it forces a flush, after which invalidates are ignored (G2-006). Qualcomm says issue inside a render pass, Meta says queries force a flush (GX-C9). Use ovrgpuprofiler stages instead.
- **EXT_buffer_storage** (G3-070): `MAP_PERSISTENT_BIT_EXT | MAP_COHERENT_BIT_EXT` for native streaming of vertex/constant data.

## Open items (known unknowns)

- KU-11 / GLES3-GF1-005: Quest 2 (2024-2026 drivers), Quest 3S and Quest Pro lists. Dump on device or submit a gpuinfo report from the headset.
- KU-21: `GL_MAX_VIEWS_OVR`. KU-30: `GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT`. Both read by the SKILL.md probe.
- KU-22: vertex-cost saving of multiview on Adreno 650/740. A/B multi-pass vs multiview with ovrgpuprofiler Binning and Render stage times.
- KU-34: how GL multiview surfaces look in Quest 3 render-stage traces (Quest 2: one surface, twice the tiles; G3-047).
- KU-10: whether static FFR takes effect on GLES via OpenXR.
- KU-18 (partly open): which MSAA call Unity uses for non-multiview MSAA render targets on GLES.
