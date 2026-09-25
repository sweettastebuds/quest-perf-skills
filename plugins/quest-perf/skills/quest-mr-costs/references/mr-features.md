# MR feature cost notes (Quest 2 / Quest 3/3S)

Per-feature detail for `quest-mr-costs`. All sources accessed 2026-09-24.
Finding IDs refer to `research/quest.md` (Q*) and `research/arm-mobile-hw.md`
(A*, ARM-*). "No number" means Meta publishes none; use the measurement recipe.

## Feature table

| Feature | Devices | Stack / version requirements | Published cost | Controls | IDs |
|---|---|---|---|---|---|
| Passthrough (underlay) | Quest 2, 3, 3S | `XR_FB_passthrough`; Core SDK `OVRPassthroughLayer`, or OpenXR: Meta "Meta Quest: Camera (Passthrough)" + AR Camera Manager (Unity 6+) | Quest 3/3S: CPU capped at L3, GPU at L2; launch blog 17% GPU / 14% CPU. Quest 2: no cap in current table. No per-frame ms, memory or bandwidth number | `OVRManager.instance.isInsightPassthroughEnabled`, `OVRPassthroughLayer.enabled`, `xrPassthroughLayerPauseFB` | Q2-038, Q4-001, Q2-006/Q4-002, Q2-048, Q4-010, Q4-013, Q4-014, Q4-021 |
| Extra passthrough layers | all | max 3 | "non-trivial" each, no number | use one | Q4-011 |
| Alpha-mask passthrough layer | all | `XR_FB_passthrough` | "significant overhead" | use eye-buffer alpha (Selective Passthrough material) instead | Q4-018 |
| Color LUT | all | `XR_META_passthrough_color_lut` | max res 64; 64 takes a few ms to create; per-frame high-res update "notable" | res 16, max 32; create ahead | Q4-017 |
| Passthrough preference | Quest 3/3S | `OVRManager.IsPassthroughRecommended()` / `XR_META_passthrough_preferences` | start in VR keeps full level range (if passthrough never enabled) | check at startup | Q4-019 |
| Passthrough Camera API | Quest 3/3S | HzOS v74+, `horizonos.permission.HEADSET_CAMERA`; `PassthroughCameraAccess` MRUK v81+; OpenXR: Meta 2.6 image capture | about 1-2% GPU per camera, about 45 MB, 20-40 ms latency, 60 Hz, max 1280x1280 YUV420 | `RequestedResolution`, `MaxFramerate`; GPU path (Vulkan, zero-copy) vs CPU path (API 32) | Q4-022 to Q4-025 |
| Depth API occlusion | Quest 3/3S | Vulkan, Multiview, passthrough on, Scene Support Required, USE_SCENE. Unity 2022.3.15f1+/2023.2+ + Oculus XR 4.2.0+ + Core SDK v67 to below v74, or Unity 6+ + OpenXR: Meta 2.1.0+ + Core SDK v74+ (conflict Q4-C10) | Soft needs "slightly more GPU" than Hard; costs even with no sampling shader; no ms or % | `EnvironmentDepthManager.enabled`, `OcclusionShadersMode` None/Hard/Soft, `SetEnvironmentDepthRendering(false)` (XR.Oculus) | Q4-026 to Q4-029, Q2-006 |
| Mesh-based occlusion | Quest 2, 3, 3S | any | depth-only pre-pass, cheap on a tiler; no number | queue below 2000, ColorMask 0 | Q4-030 |
| Environment raycast | Quest 3/3S | MRUK v81+ (no Depth API needed) | no number | `EnvironmentRaycastManager` | Q4-031 |
| Scene load (MRUK) | Quest 2, 3, 3S | Space Setup on device | no load-time or hitch number | `LoadSceneFromDevice`, `SceneLoadedEvent` | Q4-032 |
| EffectMesh | Quest 2, 3, 3S | MRUK | no per-option cost; colliders, shadows, per-primitive GameObjects add cost | Cast Shadows off, Hide Mesh, one per material | Q4-033 |
| Global mesh | Quest 3/3S | MRUK | no triangle count, memory or update rate | simplified/convex collider | Q4-034 |
| DestructibleGlobalMeshSpawner (beta) | Quest 3/3S | MRUK | draw calls and culling scale with Segments Density | lower density | Q4-035 |
| Hand tracking frequency / FMM | Quest 2, 3, 3S | Core SDK v59+; Unity 6000.0.66f2+ per the current FMM page (Q4-040); native `XR_META_hand_tracking_frequency_hint` | "reserves some performance headroom"; no current number. 2021 Quest 2: Low CPU3/GPU3, High CPU3/GPU2 (stale, Q4-C4) | `OVRPlugin.RequestFastMotionMode(bool)`, `fastMotionModeHandPosesEnabled` | Q4-038 to Q4-043 |
| Multimodal | Quest 2, 3, 3S | Unity 6000.0.66f2+, SDK v62+ | no number | Simultaneous Hands And Controllers | Q4-044 |
| Wide Motion Mode | Quest 3/3S | Body Tracking Support Required | carries body-tracking cost; no number | disable when not needed | Q4-045 |
| IOBT (body tracking High) | Quest 3/3S | Movement SDK | silently drops to low fidelity under load; no number | request before other heavy services | Q4-046, Q4-047 |
| Symmetric Projection / MVRR with passthrough | Quest 3/3S | Vulkan | only generic 5-15% / 3-8% GPU-bound; no MR data | A/B | Q4-078 |

## Level and power context

| Item | Value | Source |
|---|---|---|
| Quest 3/3S clock table L2 / L3 / L4 | CPU 1.38 / 1.65 / 1.92 GHz; GPU 456 / 492 / 545 MHz | Q2-046 / Q2-047 / Q4-003 [doc] |
| Level availability with passthrough | CPU 0-3 always, CPU 4 only without passthrough, CPU 5 only with CPU 4 and trading -1; GPU 0-2 always, GPU 3-4 only without passthrough, GPU 5 with GPU 4 and trading +1 or dynamic resolution | A3-072 [doc] |
| GPU L5 in MR | ambiguous (Q4-C1) | Q4-005, Q4-006 |
| Main-thread cycles per frame | VR L4: 26.7 M (72 Hz), 21.3 M (90 Hz), 15.9 M (120 Hz); MR L3: 22.9 M at 72 Hz (derived) | A1-026, A1-018 |
| Third-party MR capture | Quest 3, 565 s at 72 Hz: CPU L2 549 / L3 16 samples; GPU L2 531 / L3 34; app GPU about 3.1-3.3 ms; 0 stale in 547 samples | QUEST-GF2-009 [measured] |
| Quest 3 power, OS v57, 120 Hz | VR browsing 7.6-8.2 W, MR browsing 9.6-10.2 W; VR game 7.5-9.0 W, MR game 10.5-12.0 W (whole device, one run each) | ARM-GF2-002 [measured] |

## Conflicts to surface

- **Q4-C1:** GPU L5 for passthrough apps: blocked (needs GPU L4) vs unlocked by dynamic resolution alone.
- **QUEST-GF2-C4:** documented "no GPU L3/L4 with passthrough" vs 34/565 GPU L3 samples in a third-party passthrough CSV. Keep the doc as the planning rule.
- **Q4-C4:** 2021 hand-tracking downclocks vs current docs listing no hand-tracking level restriction.
- **Q4-C10:** Depth API before Unity 6: Meta's plugin page says unsupported; the Depth API table lists 2022.3.15f1+ with SDK v67 to below v74.
- **Launch-era vs current:** 17% / 14% (Oct 2023 blog) vs current OS; not re-measured (A1-019 notes).

## Measurement recipes

Run all at a fixed scene, fixed refresh rate, and either pinned levels or the
granted levels logged (`quest-perf:quest-profiling-toolkit` for pinning and CSV
capture). Record OS build and SDK versions.

### Passthrough cost on the current OS (Q4-021)
1. Build A: passthrough feature fully off. Build B: passthrough on.
2. Record OVR Metrics CSV: `cpu_level`, `gpu_level`, `gpu_utilization_percentage`, `app_gpu_time_microseconds`, `stale_frame_count`, free memory.
3. Perfetto trace for compositor and system-service CPU.
4. Build B again, passthrough toggled off at runtime: do CPU L4 / GPU L3-4 come back? (Q4-001 open question.)
5. For QUEST-GF2-C4: force passthrough on for 10 minutes under GPU load and log `gpu_level` continuously.

### Depth API cost (Q4-027)
1. GPU-bound scene with a full-screen occluding material.
2. Locked GPU L (L2 under passthrough).
3. Switch `OcclusionShadersMode` None / Hard / Soft; compare GPU% and App GPU ms.
4. RenderDoc Meta Fork render-stage trace for the per-surface delta.
5. Repeat with `EnvironmentDepthManager.enabled = false` and no occluder visible, to size the "costs even when unused" part (Q4-028).

### Hand / body tracking cost (Q4-048, Q4-039)
1. Fixed scene, fixed levels.
2. Toggle each feature alone (hands Low, hands High/FMM, multimodal, WMM, IOBT), then each combined with passthrough.
3. Record granted CPU L / GPU L, App CPU ms, main-thread timings via `ProfilerRecorder`, stale frames.
4. Perfetto for tracking-service CPU on other cores.
5. Verify FMM with `adb logcat -e FMM` and `adb logcat -e "Camera FPS"` (about 60 Hz, 50 Hz on 50 Hz grids) (Q4-042); IOBT fidelity with `adb shell dumpsys activity service com.oculus.bodyapiservice.BodyAPIService` (Q4-046).

### Scene load hitch (Q4-032) and global mesh size (Q4-034)
1. ProfilerMarker around `LoadSceneFromDevice()` to `SceneLoadedEvent`.
2. Perfetto trace; look for main-thread spikes while EffectMesh and colliders build.
3. Log `mesh.triangles.Length / 3` for the global mesh in several real rooms.

### PCA configuration (Q4-023)
Measure GPU% at fixed GPU L for each `RequestedResolution` and `MaxFramerate`
you ship; also one vs two cameras.

### Symmetric Projection / MVRR in MR (Q4-078)
GPU-bound MR scene with occlusion on; enable Symmetric Projection, then MVRR
All Passes, then Final Pass; record GPU% at GPU L2 and inspect edge alpha for
passthrough artifacts.
