---
name: gles-tile-load-store
description: "Tile-friendly rendering on Quest 2/3/3S in OpenGL ES builds only: glClear and glInvalidateFramebuffer placement and order, avoiding GMEM loads and depth stores, partial-clear cost, MSAA via multisampled render-to-texture (MSRTT), readbacks, flushes, fences and queries that split passes, and how URP settings map to GL load/store. Use when a GLES build shows LoadColor, LoadDepthStencil or StoreDepthStencil stages, when MSAA is expensive on GLES, or when partial clears cost time. For Vulkan or Render Graph pass setup use unity-perf:unity-render-graph-tiling."
---

# GLES load/store on Adreno (Quest 2 / Quest 3/3S)

Goal: **Throughput** (lower average GPU frame time by removing GMEM loads, unneeded stores and pass
splits). Two items also serve **Consistency**: CPU waits on fences and implicit flushes stall the
render thread (fix 4).

Scope: OpenGL ES 3.x builds with URP 12/14/17 on Unity 2021.3-6000.x. On GLES, URP "Native
RenderPass" has no effect and `BeginRenderPass` is emulated with `SetRenderTarget` (G2-022, GX-C4),
so every URP pass boundary is a real FBO switch. What the tiler does in hardware (bins, GMEM size,
LRZ, resolve) is `arm-mobile-hw-perf:xr2-adreno-architecture`.

Target state: the eye-buffer surface in `ovrgpuprofiler` shows only Binning, Render, StoreColor
(plus Preempt, not app-controlled) and one eye-buffer surface per frame (G2-009, G2-011).

## When to use / when not

Use when:
- A GLES build's `ovrgpuprofiler -t` trace shows non-zero `LoadColor` / `LoadDepthStencil`, any
  `StoreDepthStencil` on the eye-buffer surface, or more eye-resolution surfaces than expected.
- MSAA costs more than expected on GLES, MSAA silently disappears, or transparents vanish with MSAA
  + multiview.
- A readback, `GraphicsFence`, timer or occlusion query, or native plugin `glFlush` lands mid-frame
  on GLES.
- You write a native GL plugin or a custom `CommandBuffer` pass for a GLES build and need the right
  clear/invalidate order.

Do not use for:
- Unknown bottleneck, or not yet GPU-bound → `quest-perf:quest-triage`.
- Vulkan builds, Render Graph C# pass setup, pass merging, memoryless, on-tile post →
  `unity-perf:unity-render-graph-tiling`.
- Choosing the MSAA level (2x vs 4x) and the URP asset/renderer settings audit →
  `unity-perf:unity-urp-settings`.
- Whether to ship GLES at all, per-API MSAA A/B, GLES capture caveats → `gles3-perf:gles-vs-vulkan`.
- Bin math, GMEM sizes, FlexRender, LRZ rules, in-tile resolve hardware →
  `arm-mobile-hw-perf:xr2-adreno-architecture`.
- OVR_multiview2, FFR mechanics on GLES, other extensions → `gles3-perf:gles-extensions-multiview`.
- GL state-change and draw overhead → `gles3-perf:gles-driver-overhead`.
- Running the profiling tools in general → `quest-perf:quest-profiling-toolkit`.

## Diagnose first

**1. Per-surface render stages (the confirming capture).** Works on GLES; Meta documents no API
restriction (G3-080).

```sh
adb shell ovrgpuprofiler -e com.company.app   # detailed mode; restart the app afterwards
adb shell ovrgpuprofiler -t2 -v               # 2 s trace, per-bin stage detail
adb shell ovrgpuprofiler -d                   # turn detailed mode off when done
```

Load/store rules for the eye-buffer surface (G2-009, G2-011):
- Any non-zero Load* stage, or any StoreDepthStencil = a missing clear or invalidate.
- Each extra surface = at least one full-resolution store.
- Binning above 10-20% points at vertex cost, not load/store (G3-079) →
  `arm-mobile-hw-perf:xr2-adreno-architecture`.

Full surface-line format, Mode legend and stage names: `quest-perf:quest-profiling-toolkit`.

A/B recipe (G2-010, Unity QA): lock `debug.oculus.gpuLevel 3` / `cpuLevel 3`, detailed mode before
launch, `ovrgpuprofiler -t 2`, read total / Binning / Render / StoreColor. Level 3 is for deltas, not
budgets; `sysPropDebug`/`headlock` are from a Unity QA report [verify on device].

**2. Which GL calls Unity emitted.** RenderDoc Meta Fork (68.18 needs Horizon OS 68+,
GLES3-GF1-004): search the API log for `glInvalidateFramebuffer`, `glDiscardFramebufferEXT`,
`glClear`, `glFlush`, `glReadPixels`, `glFramebufferTexture2DMultisampleEXT`,
`glFramebufferTextureMultisampleMultiviewOVR`. Set timer query type to per-renderpass and replay
optimisation to Fastest, or inserted commands show up as phantom stages (G3-076). Do not trust the
per-event time on the invalidate: GL timestamps charge the deferred bin execution to whichever event
ends the pass (GLES3-GF2-003, GX-C9).

**3. Capability flags.** Log once on device (script in fix 5):
`SystemInfo.supportsStoreAndResolveAction` (false means StoreAndResolve silently becomes Resolve,
G2-015) and `SystemInfo.supportsMultisampleAutoResolve` (true is consistent with the MSRTT path,
G2-044). [verify on device]

**4. Unity-side view.** Frame Debugger on a development build: an unrequested `DepthPrepass` on a
2021.3 patch older than 9f1 is UUM-8381 (G2-021); `CopyColor` / `CopyDepth` passes are pass splits
(G2-018, G2-019).

## Key numbers

| Number | Value | Source | Applies to |
|---|---|---|---|
| Partial clear (COLOR\|DEPTH on D24S8, stencil left) | 25.15 vs 18.24 ms, about 37% slower | G2-005, Qualcomm sample `avoid_gmem_loads` [measured] | Adreno phone, pre-2023; Quest by analogy [verify on device] |
| Storing an unneeded depth/stencil | 18.33 vs 11.93 ms, about 50% more | G2-007, Qualcomm sample `reduce_gmem_stores` [measured] | Adreno phone, pre-2023; Quest by analogy [verify on device] |
| Avoidable Load/Store in Meta's example line | Meta: "1.5ms" (LoadColor + StoreDS); about 2.4 ms of 10.62 ms if LoadDS is counted (dossier arithmetic) | G2-009 [doc] | Device unstated; 1216x1344 matches original Quest; illustrative |
| Explicit MSAA resolve blit vs MSRTT | blit about 2.5 ms; MSRTT saved about 3 ms total | G2-042 [measured] | Adreno 530 phone, pre-2023 |
| Wrong MSAA store/load/resolve setup | about 3 ms GPU | G1-046, Meta 2019 blog [doc] | Quest 1 era, stale |
| 4x MSAA on the eye buffer, GLES | +3.3 ms (9.7 → 13.0 ms); Vulkan +5.0 ms (9.1 → 14.1) | G2-039 [measured] | Quest 3/3S, Unity 6000.0-6000.7a; table internally inconsistent (G2-C9): quote deltas only |
| GLES StoreColor, MSAA off → 4x | 0.04 → 0.15 ms (Vulkan 0.45 ms) | G2-041 [measured] | Quest 3/3S, Unity 6000.x |
| 4x MSAA, Quest 2 | about +7 ms (Vulkan about 14 → 21 ms; GLES within about 1 ms) | G2-040 [measured] | Quest 2, Unity 6000.x; approximate |
| MSAA ceiling on GLES | `GL_MAX_SAMPLES` = 4 | G1-007/G2-035 [measured] | Quest 2 driver V@0690, Quest 3 V@0837.0.7 |
| Binning share of eye buffer | 4.5 of 9.7 ms (no MSAA), 5.1 of 13.0 ms (4x) | G2-087 [measured] | Quest 3/3S, Unity 6000.x, GLES and Vulkan alike |
| Binning guideline | 10-20% of a render pass; 30% "usually too much" | G3-079 [doc] | Adreno generic |
| Occlusion queries on a binned surface | 20-40% extra "% CP Busy" vs 4-6% in direct mode | G2-033 [doc] | Adreno GLES |
| Timer query overhead | about 2-5 µs per timed draw per tile | G2-034 [doc] | Adreno binning mode, Quest 2/3 |
| Indirect compute workgroup | below 64 forces a CPU-GPU flush | G2-080 [doc] | Adreno GLES 3.1+ [verify on device] |
| GMEM | 1 MB (Adreno 650), about 2 MB (Adreno 740) | G2-001 [doc] | Quest 2 / Quest 3/3S |
| Frame budget reference | 13.9 ms at 72 Hz | G2-039 | all |

No published number exists for 2x MSAA on Quest GLES (KU-24, G2-C3); measure 1x/2x/4x with the
G2-010 recipe.

## Fixes, ranked by payoff ÷ effort

### 1. Clear or invalidate every aspect at pass start — Throughput

On GLES the only ways to skip the per-bin load are `glClear` or `glInvalidateFramebuffer` after
binding the FBO and before the first draw (G2-004). Meta says clear and invalidate cost about the
same on Qualcomm. Qualcomm's sample shows a partial clear still loads the uncleared aspect (G2-005).
The two agree once you clear every aspect (G2-C4).

- Base camera: Environment > Background Type = Skybox or Solid Color, so the eye pass starts with a
  clear (the GLES3-GF2-003 capture used Solid Color). Confirm LoadColor = 0 in the trace [verify on
  device].
- Custom `CommandBuffer` passes into your own RT: set DontCare loads, then clear colour, depth
  **and** stencil when the format has stencil:

```csharp
// Unity 2021.3+ (URP 12+). Custom pass into an RT that is fully overwritten.
using UnityEngine;
using UnityEngine.Rendering;

public static class GlesTilePass
{
    public static void BeginFullOverwrite(CommandBuffer cmd, RenderTargetIdentifier color, RenderTargetIdentifier depth)
    {
        cmd.SetRenderTarget(color, RenderBufferLoadAction.DontCare, RenderBufferStoreAction.Store,
                            depth, RenderBufferLoadAction.DontCare, RenderBufferStoreAction.DontCare);
        cmd.ClearRenderTarget(RTClearFlags.All, Color.clear, 1f, 0u);   // colour + depth + stencil; Unity 2021.3+
    }
}
```

- Effect: removes LoadColor/LoadDepthStencil from the average GPU time. No variance effect.
- Quality cost: none if the pass really overwrites every pixel. Use
  `LoadStoreActionDebugModeSettings` (2022.3, 6000.x; Game view and dev builds) to highlight
  "INVALIDATED" areas before shipping (G2-025). Depth store DontCare is only safe if no later pass
  reads this depth, for example a Copy Depth or soft particles. Otherwise use Store.
- Tags: `Quest 2` `Quest 3/3S` `GLES` `Unity ≥ 2021.3` `URP 12+`.

### 2. URP Store Actions = Discard; do not trust Auto — Throughput

URP asset > Rendering > **Store Actions**: Auto / Discard / Store (URP 12.1, 14, 17; in 17 visible
only with Show All Advanced Properties). Auto falls back to Store as soon as a renderer feature
injects a pass, which costs a full-resolution store and reload per pass (G2-016). Set **Discard**.

- Unity does not always turn DontCare/Discard into `glInvalidateFramebuffer`: UUM-45041 (Won't Fix,
  2021.3-2023.2) skipped it on PowerVR and Mali, not on Adreno 610 (G2-014, G2-C2). Quest behaviour
  is unverified (KU-32): confirm StoreDepthStencil = 0 in the trace, not in the inspector.
- A 2023 capture shows Unity does emit two `glInvalidateFramebuffer` per frame in an empty URP scene
  (Quest 2, 2021.3/2022.3, OculusXR) (GLES3-GF2-003, [community]). Whether 6.x / Render Graph keeps
  that is unknown (KU-13, KU-17).
- Effect: removes StoreDepthStencil and inter-pass reloads. No variance effect.
- Quality cost: none, unless a custom renderer feature reads an attachment from an earlier pass.
  That read then returns undefined data, so check with `LoadStoreActionDebugModeSettings` (G2-025).
- Tags: `Quest 2` `Quest 3/3S` `GLES` `URP 12+`.

### 3. Remove GLES pass splits from URP settings — Throughput

Each of these is an extra FBO switch on GLES because Native RenderPass does nothing there (G2-022).
Setting paths and the full audit are in `unity-perf:unity-urp-settings`; the GL-level effect of each
is in [references/unity-gles-loadstore-map.md](references/unity-gles-loadstore-map.md) (read it when
a trace shows a surface or store you cannot explain).

- **Opaque Texture off.** It is a mid-frame colour copy (store + reload); downsampling shrinks only
  the copy (G2-018). Without StoreAndResolve it also makes URP ignore MSAA (G2-017), and on GLES XR
  it can render double (UUM-70930, Won't Fix) (G2-026).
- **Depth Texture Mode = After Transparents**, or no depth texture. After Opaques stores and reloads
  colour including MSAA data (G2-019; URP 14+).
- **Depth Priming = Disabled.** Unsupported with MSAA and on mobile TBDR; Forced adds a prepass
  (G2-020). U2-088: URP turns priming off where GLES with MSAA cannot copy depth, and does not bind
  MSAA depth as a texture.
- **Intermediate Texture = Auto**, not Always. Always forces an intermediate RT, and on GLES the
  main pass then loses compositor FFR (G2-024, G2-061).
- **Unity 2021.3 older than 9f1:** unrequested GLES3 depth prepass (UUM-8381, G2-021); upgrade.
- Effect: each removed split saves at least one full-resolution store (G2-011). No variance effect.
- Quality cost: effects that sample scene colour/depth (refraction, soft particles) need another
  approach; on GLES depth input attachments are texel-fetch copies, not framebuffer fetch (U2-088,
  GX-C6).
- Tags: `Quest 2` `Quest 3/3S` `GLES` `URP 12+` (After Transparents, Depth Priming, Intermediate
  Texture: `URP 14+`).

### 4. Move readbacks, flushes, fences and queries out of the pass — Throughput + Consistency

`glFlush`/`glFinish` (including in native plugin render events) and FBO rebinds end the tiled region; invalidates issued after a flush are
ignored and depth goes to RAM (G2-006, G2-029). Audit (inferred mapping; Unity documents no GL
calls, [verify on device]):

- `Texture2D.ReadPixels`, `CommandBuffer.RequestAsyncReadback`: issue after the eye pass, never
  between opaques and transparents.
- `GraphicsFence` / `glClientWaitSync`: `eglSwapBuffers` already throttles; an explicit client wait
  blocks the render thread (G2-030). Prefer orphaning or a ring sized to frames in flight; if a
  fence is unavoidable, poll it without a mid-pass flush (G2-C6). Goal: **Consistency**.
- `GL_EXT_disjoint_timer_query`: forces a flush on GLES, after which invalidates are ignored
  (G2-006, G2-034). Qualcomm says issue queries inside the pass (G3-068); Meta says per-draw timing
  on the tiler is inaccurate. Both hold: no extra flush inside the pass, but the query still sums
  bins (GX-C9). Strip timer queries from shipping builds; use ovrgpuprofiler. Multiview forbids
  timer queries inside multiview rendering (G2-034).
- GL occlusion queries (native/plugins): batch after a flush, opaque → translucent → flush → queries
  → switch FBO (G2-033).
- `glDispatchComputeIndirect`: workgroups ≥ 64, or the CPU waits and the pass splits (G2-080).
- Effect: average GPU time falls by the removed store/reload; render-thread stalls disappear from
  the p95/p99 tail. Verify on device.
- Quality cost: readback results arrive one pass or frame later. None otherwise.
- Tags: `Quest 2` `Quest 3/3S` `GLES`.

### 5. Keep MSAA on tile (MSRTT); never create a real MSAA texture — Throughput

Unity's GLES multiview eye buffer uses `GL_OVR_multiview2` +
`GL_OVR_multiview_multisampled_render_to_texture` (GLES3-GF2-004, Unity 2022.3-6000.6 manual):
samples live in GMEM and are resolved in the store path, which fits GLES StoreColor rising only 0.04
→ 0.15 ms at 4x (G2-041). MSAA cost on GLES is therefore Render + Binning growth, not bandwidth.

- Do not set `RenderTexture.bindTextureMS = true` with `antiAliasing > 1` unless per-sample reads
  are essential: it needs real multisample storage and an explicit resolve (G2-043). The explicit
  path cost multiple ms in Qualcomm's sample (G2-042).
- Anything that binds another FBO, reads pixels, generates mips, flushes or samples the attached
  texture mid-pass triggers an implicit resolve that discards the samples; later draws render into
  the resolved image (G2-028).
- Keep per-camera MSAA and HDR equal to the URP asset: UUM-91896 fails with "Attachment AA sample
  counts must match" on GLES multipass with OculusXR Multi Pass (found in 6000.0.23f1, 6000.0.33f1,
  6000.1.0b1; fixed in the 6000.0/6000.1/6000.2 ports per dossier G2-027 [verify on your patch]).
- FullScreenRenderPass + Multiview + MSAA on GLES makes transparents disappear on Quest 3/3S
  (UUM-109377, Won't Fix 6000.0-6000.5) (G2-026).
- Level choice (2x vs 4x) is `unity-perf:unity-urp-settings`; 4x is the GLES ceiling (G2-035); on
  Quest 2 treat 4x as unaffordable unless measured (G2-040). Extension details:
  [references/msrtt.md](references/msrtt.md) (read it when writing a native MSAA path or checking
  what Unity emits).
- Effect: avoids a multi-ms explicit resolve (G2-042, G2-043) on average GPU time; no variance
  effect. Quality cost: none. Mid-pass implicit resolves lose AA quality (G2-028).

Log the flags once per build:

```csharp
// Unity 2021.3+. Attach to any bootstrap object; development builds only.
using UnityEngine;

public class GlesTileCaps : MonoBehaviour
{
    void Start()
    {
#if DEVELOPMENT_BUILD || UNITY_EDITOR
        Debug.Log($"[GlesTileCaps] api={SystemInfo.graphicsDeviceType} " +
                  $"ver={SystemInfo.graphicsDeviceVersion} " +
                  $"storeAndResolve={SystemInfo.supportsStoreAndResolveAction} " +
                  $"msaaAutoResolve={SystemInfo.supportsMultisampleAutoResolve}");
#endif
    }
}
```

`adb logcat -s Unity | findstr GlesTileCaps` (Windows) or `grep` elsewhere.

- Tags: `Quest 2` `Quest 3/3S` `GLES` `Unity ≥ 2022.3` for the MSRTT eye-buffer path (GLES3-GF2-004
  covers 2022.3-6000.6; 2021.3 [verify on device]); GlesTileCaps logger: `Unity ≥ 2021.3`.

### 6. Native GL plugins: invalidate order — Throughput

For C/C++ plugins rendering their own FBOs (G2-008, G2-006):

```c
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
const GLenum all[] = { GL_COLOR_ATTACHMENT0, GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 3, all);          /* or glClear(COLOR|DEPTH|STENCIL) */
/* ... draws ... */
const GLenum ds[] = { GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, ds);           /* before any flush, query or rebind */
glBindFramebuffer(GL_FRAMEBUFFER, 0);
```

Preference order: `glInvalidateFramebuffer` > `glInvalidateSubFramebuffer` > `glClear` >
`glDiscardFramebufferEXT` (both headsets expose it) (G2-008). A multisampled depth **texture** under
`EXT_multisampled_render_to_texture2` is discarded at resolve; a depth **renderbuffer** is not
(G2-037). Effect: removes Load*/StoreDepthStencil for plugin FBOs (average GPU time), no variance
effect; quality cost: none if the pass overwrites every pixel. Tags: `Quest 2` `Quest 3/3S` `GLES`.

### 7. Quest 3/3S only: do not starve concurrent binning — Throughput

Adreno 7x bins concurrently with rendering; Adreno 650 (Quest 2) is assumed not to (G2-088; KU-25
unconfirmed by Meta). It is blocked by a pass whose binning depends on the previous pass, and by
clearing or invalidating the same Z-buffer several times per frame. Qualcomm suggests reusing one
Z-buffer across passes without clears, or separate Z-buffers.

**Conflict G2-C5:** "invalidate depth at the end of every pass" (Meta, Qualcomm, fix 6) vs "reuse
one Z-buffer without clears or invalidations" (Qualcomm concurrent binning). Relevant only to
multi-pass frames on Quest 3/3S; A/B both. Effect: unknown size, since no published number exists;
whether Binning overlaps Render is unknown, so measure the surface total against the sum of stages
(KU-26). Quality cost: none. Tags: `Quest 3/3S` `GLES` [verify on device].

### 8. A2C vs discard with MSAA — Throughput

Both disable LRZ; discard also hurts early-Z. Prefer A2C over `clip()` only after measuring
(G2-046). LRZ rules: `arm-mobile-hw-perf:xr2-adreno-architecture`; authoring:
`unity-perf:unity-shader-authoring`. Effect: average GPU time; size unknown, measure with
`ovrgpuprofiler -x` LRZ state. Quality cost: A2C changes cutout edge look. Tags: `Quest 2` `Quest 3/3S` `GLES`
[verify on device].

## Verify

- Same scene, same pose, levels locked (G2-010 recipe), `ovrgpuprofiler -t2 -v` before and after,
  three captures each.
- Expected: LoadColor, LoadDepthStencil, StoreDepthStencil on the eye-buffer surface go to 0;
  surface count drops by one per removed split. The surface total should fall by roughly the removed
  stage times. No published Quest number for the saving; phone samples show 37% (partial clear) and
  50% (depth store) (G2-005, G2-007) [verify on device].
- MSAA: StoreColor on GLES with MSAA should stay near the MSAA-off value (0.04 → 0.15 ms in G2-041).
  A multi-ms StoreColor or a separate resolve surface means an explicit resolve slipped in.
- RenderDoc API log: `glInvalidateFramebuffer` precedes any `glFlush` for the eye pass; no
  `glReadPixels` between eye-pass draws.
- Fences/flush fixes (Consistency): OVR Metrics Tool CSV over a 20-30 min session; stale frames per
  minute and p95/p99 App GPU time should not rise; analyse with
  `quest-perf:quest-profiling-toolkit`'s CSV script. No published GLES variance data exists (KU-42).
- Turn detailed mode off (`ovrgpuprofiler -d`) before any shipping-level measurement.

## Pitfalls and myths

- **"Enabling Native RenderPass fixes GLES."** No effect on OpenGL ES (URP 14, 17);
  `PLATFORM_SUPPORTS_NATIVE_RENDERPASS` is not defined in GLES3.hlsl (G2-022, GLES3-GF1-008).
- **"RenderBufferLoadAction.Clear clears."** Documented as working only with the RenderPass API
  (G2-013). Issue an explicit clear.
- **"The inspector says Discard, so depth is not stored."** Unity says actions "might be ignored at
  runtime" (G2-013); UUM-45041 shows skipped invalidates on some GPUs (G2-014). Trust the trace.
- **"Clearing depth is enough."** On D24S8, stencil left uncleared still loads (G2-005).
- **"The invalidate costs 90% of the frame"** (RenderDoc event timing). The deferred bin work is
  charged to the event that ends the pass (GLES3-GF2-003, GX-C9).
- **"Opaque Downsampling makes the Opaque Texture cheap."** It shrinks the copy, not the store and
  reload of the main target (G2-018).
- **"2x MSAA is free."** Qualcomm says "likely practically free"; Meta's Quest 1 data shows cost; no
  Quest GLES 2x number exists (G2-045, G2-C3).
- **Absolute UUM-149765 numbers.** Table and notes disagree (9.7/13.0 vs about 12/15 ms); quote
  deltas only (G2-C9).
- **Old Meta GLES pages.** Meta's advanced-GPU page keeps its GLES content "for historical
  reference" (G2-C1); the numbers are Quest 1-era examples.
- **Phone guidance on CPU queue depth** (bin frame N+1 with N, G2-090) adds a frame of latency; do
  not apply on Quest without checking stale frames.
- **`QCOM_binning_control`** is absent on both headsets; you cannot force binned or direct mode
  (G2-092).
- **Known unknowns (measure, do not assume):** MSRTT use for non-multiview MSAA RTs (KU-18), plus
  KU-13, KU-17, KU-32 (fix 2) and KU-25, KU-26 (fix 7).

## Sources

All accessed 2026-09-24.

- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ [doc]
- https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ [doc]
- https://developers.meta.com/horizon/blog/vulkan-for-mobile-vr-rendering/ [doc] (2019, stale)
- https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ [doc] (Quest 1, stale)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html [doc]
- https://github.com/quic/adreno-gpu-opengl-es-code-sample-framework [measured] (samples avoid_gmem_loads, reduce_gmem_stores, msaa; pre-2023)
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_discard_framebuffer.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture2.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview_multisampled_render_to_texture.txt
  [doc]
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_tiled_rendering.txt [doc]
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_disjoint_timer_query.txt [doc]
- https://opengles.gpuinfo.org/displayreport.php?id=6387 [measured]
- https://opengles.gpuinfo.org/displayreport.php?id=8023 [measured]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.RenderBufferLoadAction.html
  [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.RenderBufferStoreAction.html
  [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsStoreAndResolveAction.html
  [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsMultisampleAutoResolve.html
  [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture-bindTextureMS.html
  [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.LoadStoreActionDebugModeSettings.html
  [doc]
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.ScriptableRenderContext.BeginRenderPass.html
  [doc]
- https://docs.unity3d.com/6000.6/Documentation/Manual/Android-SinglePassStereoRendering.html [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/universalrp-asset.html
  [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html
  [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/universalrp-asset.html
  [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html
  [doc]
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/urp-universal-renderer.html
  [doc]
- https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRendererRenderGraph.cs
  [doc]
- https://discussions.unity.com/t/multiple-frame-buffer-invalidations-urp/935652 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 [measured]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-45041 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-8381 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-70930 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-109377 [community]
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-91896 [community]
