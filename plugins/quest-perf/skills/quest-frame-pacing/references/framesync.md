# FrameSync and Phase Sync: timeline, keys, verification

Reference for `quest-perf:quest-frame-pacing`. All sources were accessed 2026-09-24.

## OS-version timeline

| OS build | Frame timing | How it gets there | Source |
|---|---|---|---|
| Before v201 | Phase Sync (or extra-latency mode) | Phase Sync set up per plugin (see below) | Q2-073 [doc] |
| v201 | Phase Sync by default; FrameSync testable | Manifest opt-in: `<meta-data android:name="com.oculus.enable_frame_sync" android:value="true"/>` | Q2-072, A1-039 [doc] |
| v203+ | FrameSync, the default for every app on every supported device | No integration. Phase Sync calls are no-ops. It cannot run side by side with Phase Sync | Q2-071, QUEST-GF1-007 [doc] |

- The Mar 3, 2026 blog says an opt-out "will be available" for Store apps from v203, and never shows the `false` value. The essentials page (May 13, 2026) documents no opt-out, key or OS version. The Core SDK 203.0/205.0 pages and the release-notes index contain no FrameSync text (QUEST-GF2-001 [doc]).
- `com.oculus.enable_frame_sync=false` as the opt-out comes only from UploadVR and a forum thread (1368725). In that thread the poster added `false` "just in case" and never reported the result; the only reply came from a Start-program partner, not Meta staff (QUEST-GF1-007, QUEST-GF2-001 [community]). Conflict: QUEST-GF1-C1. [verify on device]

## What FrameSync does (Meta's description)

- Sliding-window statistics with equal weighting; Phase Sync used exponential decay (Q2-071).
- Handles early and late frames symmetrically, and trims the highest and lowest samples before averaging (Q2-071).
- Phase Sync's three modes (adaptive, fixed latency, AppSW) are gone (Q2-071).
- A frame-start scheduler that trades rendering latency against the GPU time the app gets, aiming to finish each frame just before display. It works together with AppSW, which is not deprecated (QUEST-GF2-003, GDC 2026 Q&A at about 55:30).
- Stage 3 of Meta's thermal model is FrameSync adapting to variable cost under throttling (Q2-058, A3-078).
- Claimed benefits: fewer stale frames (especially long runs) and lower motion-to-photon latency. No numbers are published (Q2-071).
- Stated trade-offs: possibly slightly higher CPU/GPU use, battery drain and heat. No numbers are published (Q2-072).

## Verifying which mode is active

| Signal | Reading | Status |
|---|---|---|
| logcat `Lat=` | >0 extra-latency frames; 0 neither; -1 Phase Sync (default); -2 fixed-latency Phase Sync; -3 Phase Sync tuned for AppSW | Documented (Q1-030, Q2-068), but the page predates FrameSync. Its value under FrameSync is undocumented (QX-C9) [verify on device] |
| CSV `phase_sync_mode` | `4` in Aug 2026 Quest 3 captures (979 rows, 72 Hz); `1` in a Jan 2026 Quest 3 capture; column absent in an Oct 2023 capture | Inference only: `4` probably marks FrameSync, but no Meta page defines the values, and neither capture records its OS build (QUEST-GF2-002 [measured]) [verify on device] |
| CSV `extra_latency_mode` | `0` in both 2026 captures; `1` in the Oct 2023 capture | QUEST-GF2-002 [measured] |
| Perfetto `PhaseSync` marker | 1-4 ms idle at the start of `PlayerLoop` is normal on Phase Sync | Whether it survives on v203+ is unverified (Q1-051, QX-C4) |

Procedure, once per OS build:
1. `adb logcat -s VrApi` and note `Lat=` (Q1-027).
2. Record an OVR Metrics CSV and note `phase_sync_mode` and `extra_latency_mode`.
3. To test the opt-out, build once with `com.oculus.enable_frame_sync=false` and once without, on the same OS build, and compare `phase_sync_mode` (QUEST-GF2-001). Trust an A/B result only if the value actually changed.
4. Flag any change of `phase_sync_mode` within one capture (QUEST-GF2-002).

The VrApi-tagged line is believed to print for OpenXR Unity apps too, but no Meta page says so outright. Check once per project (Q1-037 [community]) [verify on device].

## Legacy Phase Sync setup (pre-FrameSync OS builds only)

- Properties: no added overhead; more stale frames under spiky load; pairs well with Late Latching; overrides extra-latency mode. Verify with `Lat=-1` (Q2-073 [doc]).
- Unity 6+ with Meta XR SDK v74+: OpenXR provider. Unity versions before 6 with SDK versions before v74: Oculus provider (Q2-073).
- Oculus XR plugin history: Phase Sync added in 1.7.0; always on since 4.2.0, which removed the setting (Q4-057 [doc]).
- OXPB-115: in Oculus XR 3.3.0 to 4.0.0 the PhaseSync toggle was ignored and Phase Sync was always on. It reproduced on 2021.3.28f1, 2022.3.4f1, 2023.1.2f1 and 2023.2.0a21, and the tracker lists the fix in the Oculus XR 3.3.0 and 4.0.0 releases (Q2-074 [doc]). Check `Lat=`, not the checkbox.
- Debug setprop: `debug.Meta.phaseSync` (Unity page, Feb 2025) vs `debug.oculus.phaseSync` (native page, 2022). The pages conflict (Q2-C1). This is moot on FrameSync builds.
- Extra-latency mode default: the Stats guide and logcat page say it is on by default in Unity, but OpenXR Unity apps report `Lat=-1`, and Phase Sync/FrameSync override it (Q1-C5, Q2-C11). Read the mode from each capture; do not assume it.

## Sources

- https://developers.meta.com/horizon/essentials/framesync/ [doc]
- https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ [doc]
- https://developers.meta.com/horizon/downloads/package/meta-xr-core-sdk/203.0/ [doc]
- https://www.uploadvr.com/meta-horizon-os-framesync-smoother-vr-quest/ [community]
- https://web.archive.org/web/20260417023528/https://communityforums.atmeta.com/discussions/Questions_Discussions/app-frame-rate-drop/1368725 [community]
- https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/ [doc]
- https://developers.meta.com/horizon/essentials/thermal/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-logcat-stats/ [doc]
- https://developers.meta.com/horizon/documentation/native/android/ts-ovrstats/ [doc]
- https://developers.meta.com/horizon/documentation/unity/enable-phase-sync/ [doc]
- https://developers.meta.com/horizon/documentation/native/android/mobile-phase-sync/ [doc]
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/changelog/CHANGELOG.html [doc]
- https://issuetracker.unity.com/issues/11487/oculusxr-phasesync-toggle-is-not-respected-and-its-always-enabled [doc]
- https://github.com/meta-quest/agentic-tools [doc]
- https://raw.githubusercontent.com/batunii/Arjuna/HEAD/Dissertation/authored/raw/technical-T1-T3-20260807/ovr-metrics-block2-passthrough/CapturedMetrics/com.samples.passthroughcamera%23UnityPlayerGameActivity-20260807_144005.csv [measured]
- https://github.com/DemoySegment/CubemapRendering/blob/HEAD/Demo/com.DefaultCompany.lakedemo%23UnityPlayerActivity-20260102_033328.csv [measured]
- https://github.com/Raiduy/GAS-publication-figures/blob/main/Raw%20Data/Gym%20Class/com.IRLStudios.GymClass-20231015_201503.csv [measured]
