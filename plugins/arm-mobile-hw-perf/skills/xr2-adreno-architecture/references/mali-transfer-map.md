# Arm Mali to Adreno transfer map

All sources accessed 2026-09-24. Use this when advice comes from Arm documentation, the Khronos Vulkan-Samples (Arm-authored), or an engine tuned on Mali phones.

## Transfers (A2-095)

| Practice | Adreno status | Source |
|---|---|---|
| `loadOp` CLEAR / DONT_CARE, `storeOp` DONT_CARE | same advice from Qualcomm and Meta | https://docs.vulkan.org/samples/latest/samples/performance/render_passes/README.html [doc]; Qualcomm mobile_best_practices [doc] |
| TRANSIENT_ATTACHMENT + LAZILY_ALLOCATED for pass-local attachments | same (A3-021) | Qualcomm [doc] |
| In-tile MSAA resolve through `pResolveAttachments` | same; resolve on the **last** subpass (A2-055) | Meta po-advanced-gpu-pipelines [doc] |
| No `vkCmdClear*` where a `loadOp` would do | same | Vulkan-Samples [doc] |
| Subpasses so G-buffer data stays on chip | same; merging gives ">10%" only in binning mode, with Qualcomm's merge conditions (A2-057) | Qualcomm [doc] |
| Ratios of bandwidth effects | direction transfers, absolutes do not (A2-100) | https://docs.vulkan.org/samples/latest/samples/performance/msaa/README.html [measured] |

## Does not transfer

| Mali concept | Why not on Quest | Adreno replacement |
|---|---|---|
| 16x16-pixel tiles; tile-aligned screen-space algorithms | Adreno sizes whole bins from the GMEM budget (96x176, 128x224, 320x192 in Meta examples); foveation changes bins (A2-096, A2-019) | bin rule in [bin-math.md](bin-math.md); do not assume bin count or position |
| "Keep G-buffer at ≤ 128 bits per pixel" (256 on newer Malis) for subpass merging | Adreno's limit is total bytes per pixel × samples × views vs GMEM (A2-096) | [bin-math.md](bin-math.md) |
| Forward Pixel Kill / PowerVR HSR | Adreno has no HSR; relies on LRZ + early-Z (A2-097) | sort opaques front-to-back; [lrz-rules.md](lrz-rules.md) |
| Pixel Local Storage (`EXT_shader_pixel_local_storage`) | not listed in gpuinfo GLES reports for Quest 2 or Quest 3 (A2-098, https://opengles.gpuinfo.org/displayreport.php?id=6387 and id=8023 [community]) | GLES: `EXT_shader_framebuffer_fetch`, `QCOM_shader_framebuffer_fetch_noncoherent`, `ARM_shader_framebuffer_fetch_depth_stencil`, `QCOM_tiled_rendering`; Vulkan: subpass input attachments. `VK_QCOM` tile-shading / tile-memory-heap are A8x only |
| Mali counters (PTILES, Streamline templates) and malioc cycle estimates | no Adreno meaning (A2-099) | ovrgpuprofiler, RenderDoc Meta Fork, Adreno Offline Compiler (`arm-mobile-hw-perf:xr2-gpu-counters-sdp`) |
| Mali register-count occupancy thresholds, 16-wide warps | Adreno uses wave64/wave128 and GPR-limited occupancy (A2-099 notes) | `arm-mobile-hw-perf:xr2-shader-cost-model` |
| Arm's absolute bandwidth and energy figures | measured on a Mali-G76 phone: separate 4x resolve +~5 GB/s at 2168x1080/60; ~100 mW per GB/s; in-tile resolve ~3% more bandwidth (A2-100) | order of magnitude only; `arm-mobile-hw-perf:xr2-bandwidth-power` |

## Adreno-only behaviour with no Mali equivalent to borrow

- FlexRender: the driver may render a pass in direct (sysmem) mode, which loses FFR (A2-021 to A2-023).
- Binning-pass vertex cost: position-only VS on every draw, full VS per bin, up to 2 × bins + 1 per vertex (A2-046, A2-047).
- Concurrent binning on A7x (Quest 3/3S only), blocked by re-clearing a shared Z-buffer (A2-026).
- UBWC and its disablers ([ubwc.md](ubwc.md)).
- Query cost per bin (A2-060).
