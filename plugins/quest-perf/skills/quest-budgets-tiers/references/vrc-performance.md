# Store VRC performance requirements and Performance Analytics

Read from `quest-budgets-tiers` SKILL.md when preparing a Horizon Store submission,
answering a VRC question, or reading field telemetry. All sources accessed 2026-09-24.
Finding IDs refer to `research/quest.md`.

## VRC.Quest.Performance.1 (required)

Source: https://developers.meta.com/horizon/resources/vrc-quest-performance-1/ [doc]
(page updated 2025-10-22). Findings Q1-084, Q2-016, QUEST-GF1-009.

- **Floor:** render at 60 fps or more; for AppSW portions with good motion vectors,
  half the refresh rate (36 fps at 72 Hz); the Perf.1 test flags extended periods under
  30 fps with AppSW.
- **Refresh rates for interactive apps:** 72, 80, 90, 96, 100 or 120 Hz. Current text:
  96, 100 and 120 Hz are "not available on all devices". Media apps may use 60 Hz where
  supported (Quest 2 only).
- **Exempt:** loading screens and full-screen fades (added 2025-09-02), system
  overlays, slight dips while streaming or recording.
- **Test:** play for the content length or 45 minutes, whichever is shorter, and check
  the OVR Metrics FPS graph for extended periods under 60 fps (under 30 with AppSW).
- **Revision history:** 2024-03-11 AppSW half-rate exception; 2024-04-25
  streaming/recording allowance; 2024-07-31 App Lab removed; 2024-08-07 floor lowered to
  60 fps; 2024-10-29 120 Hz added; 2025-09-02 loading screens and fades exempted;
  2025-10-22 96/100 Hz added.

### Resolved conflict: 60 vs 72 fps (Q1-C1 / Q2-C3 / QUEST-GF1-C3)

| Side | Page | Says |
|---|---|---|
| A | VRC.Quest.Performance.1 (Oct 2025) | 60 fps floor |
| B | Common VRC Failures (May 2026), https://developers.meta.com/horizon/resources/publish-common-vrc-failures/ | 72 fps |
| B | Basic Optimization Workflow (Dec 2024), https://developers.meta.com/horizon/documentation/unity/po-perf-opt-mobile/ (also behind A3-097) | "All Meta Quest apps require a minimum of 72 FPS" |
| B | unity-perf (Oct 2024), https://developers.meta.com/horizon/documentation/unity/unity-perf/ | 72 FPS for interactive apps |
| B | GDC 2026 recap, https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ | "72 FPS minimum on Meta Quest 2" |

Resolution: the VRC page is authoritative for certification. 60 fps is the
certification floor; 72 fps at full rate with no stale frames is Meta's quality target.
A 60 fps app on a 72 Hz display produces stale frames every second.

### Softened conflict: 96/100 Hz availability (Q2-C4)
The 2025-10-22 revision-history entry says 96/100 Hz were added as not yet available;
the requirement text and the refresh-rate page (Aug 2026) list them on Quest 2/3/3S.
Quest Pro supports neither. Gate on the runtime's reported rate list.

## VRC.Quest.Performance.2 (retired)

The 45-minute thermal throttling test was retired on 2024-10-16 (Q1-085).
https://developers.meta.com/horizon/resources/vrc-quest-performance-2/ [doc]. Thermal
decay is no longer a store gate on its own; the 45-minute Perf.1 run still catches decay
that pushes the app under 60 fps (QX-C7). Soak protocol: `quest-perf:quest-levels-thermal`.

## VRC.Quest.Performance.3 (required)

Head-tracked graphics must appear within 4 seconds of launch, or the app must show a
loading indicator (Q1-086, updated 2024-07-31).
https://developers.meta.com/horizon/resources/vrc-quest-performance-3/ [doc].
Measure with `metavr perf capture --launch` (cold start) or logcat timestamps from app
start to the first VrApi stats line.

## VRC.Quest.Performance.4 (recommended)

Render scale at least 85% for most of the experience, measured with OVR Metrics
"Render Scale Percent" (CSV `render_scale`) over the content length or 45 minutes.
Individual, non-consecutive sequences (the example is a boss battle) may dip below.
The render-scale doc says apps whose render scale is too low will not be approved
(Q1-087, Q2-026, Q3-003; page updated 2024-07-31, when it became a recommendation).
https://developers.meta.com/horizon/resources/vrc-quest-performance-4/ [doc].
Consequence: a dynamic-resolution minimum below 0.85 (OVRManager default 0.7) makes the
app responsible for staying at or above 85% most of the time.

## Other VRCs that touch performance (Q1-088)

Source: https://developers.meta.com/horizon/resources/publish-quest-req/ [doc]
(guidelines page updated 2026-08-19). Meta calls its downloadable test plans slightly
out of date.

| VRC | Rule | Performance angle |
|---|---|---|
| Functional.1 | no crashes, freezes or extended unresponsive states | long loading freezes without an indicator, Low Memory Kills |
| Input.4 | stay focus-aware, keep rendering when focus is lost | do not stop submitting frames on focus loss |
| Packaging.4 | supported SDK and engine versions | see `unity-perf:unity-version-matrix` |
| Packaging.5 | APK under 1 GB, OBB under 4 GB | asset tiering size limits |
| Packaging.6 | 64-bit | ARM64 builds |

## Performance Analytics (field telemetry, not a VRC)

Source: https://developers.meta.com/horizon/resources/publish-performance-analytics/
[doc] (page updated 2025-02-14); GDC 2026 talk,
https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/
[doc]. Finding QUEST-GF2-013.

Developer Dashboard > Performance Analytics, about 60 s aggregation windows:

| Metric | Definition |
|---|---|
| Device Frame Rate | frames rendered over about 60 s |
| Max Stale Frames | maximum stale frames about every 60 s |
| CPU / GPU Utilization | maximum over about 60 s |
| Start Up Time | launch to the 1000th rendered frame |
| Memory Utilization | physical, virtual and cross-process allocations (chart marked temporarily unavailable) |

- Percentiles and means are offered. Only Store immersive apps are covered (not PCVR,
  2D, hybrid, web or Spatial SDK apps).
- GDC 2026: field data now spans weeks, includes stall types, percentiles and moving
  averages, and compares against category and ecosystem aggregates.
- Use: Max Stale Frames per 60 s is the closest field analogue to a hitch rate; match it
  in QA by emitting per-60-s maxima of `stale_frame_count` from the OVR Metrics CSV
  (`quest-perf:quest-profiling-toolkit` analyzer). Start Up Time to the 1000th frame is
  the documented cold-start metric to track shader/PSO warm-up against
  (`unity-perf:unity-shader-hitches`).
