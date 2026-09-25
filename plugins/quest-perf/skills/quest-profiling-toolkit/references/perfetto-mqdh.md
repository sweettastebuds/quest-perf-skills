# Perfetto and MQDH on Quest

Applies to: Quest 2, Quest 3/3S; Unity 2021.3 through 6.x. Accessed 2026-09-24.

## MQDH (Meta Quest Developer Hub)

https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ (updated Apr 8, 2026) [doc]

- Device Manager > Device Actions: "Install OVR Metrics Tool", "Metrics HUD"
  toggle, "Metrics Recording" toggle; the "..." menu lists recorded files.
  Uninstall the tool with `adb uninstall com.oculus.ovrmonitormetricsservice` (Q1-040).
- Performance Analyzer: play button starts it. Turn the Casting toggle OFF to
  cut overhead. 12 modules: VRCs, CPU, GPU, GPU Memory Access, GPU Render
  Pipeline Stats, Vertex Shading Stats, Fragment Shading Stats, GPU Misc.
  Shader Unit Stats, Frame Rate, Rendering Config, Timings, Memory (Q1-041).
  GPU Memory Access is the only live bandwidth graph in a Meta GUI tool; units
  and sampling rate are undocumented (A3-047).
- Performance flags use thresholds you set under the gear icon; the docs give
  no default. Set them to your refresh-rate budget. The Logs pane is
  expensive; filter it (Q1-042).
- MQDH version: not published on the pages read.
- Since GDC 2026 (Mar 10, 2026) MQDH ships a Perfetto MCP server so an agent
  can query captured traces directly; no MCP tool list is published
  (QUEST-GF1-005, https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/).

## MQDH Perfetto settings (Q1-043, A3-045)

https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (updated Sep 3, 2026) [doc]

- Preference: General, or Custom JSON TraceConfig.
- Auto open trace, Trace duration, Trace buffer size, GPU Trace buffer size.
  A buffer that is too small silently drops data; keep traces short.
- CPU Scheduling, ATrace Categories, **ATrace Apps**, TrackEvent.
- XR Runtime Metrics, GPU Metrics, GPU Render Stage Trace, "Enable high
  precision GPU render stage tracing".
- TrackEvent config (process filter, categories, tags); Callstack Sampling.
- Traces save under File Manager > MQDH Files > Perfetto.

Unity-specific (Q1-044, Q1-045):

- Unity emits only ATrace events. Put the package name in **ATrace Apps** or
  the trace has no Unity markers (the usual cause of an "empty" trace).
- Custom `ProfilerMarker` scopes appear only in a Development Build. A dev
  build changes timing: use it to find where time goes, then measure final
  numbers on a non-dev build with the OVR Metrics CSV.

GPU render stages (Q1-046): enable GPU Render Stage Trace + high precision,
choose GPU traces > Enable in the MQDH menu, run the app, click Record.

Callstack sampling (Q1-047, A1-084): Horizon OS v51+ via `traced_perf`.
Settings: Enabled App(s), symbol folder(s), trigger (`PerfEvents.Counter` or
`PerfEvents.Tracepoint`), Frequency or Period. For IL2CPP release builds point
the symbol folders at the build's symbol output; this is the closest to
shipping timing.

## metavr CLI (Q1-049)

https://github.com/meta-quest/agentic-tools (docs/metavr-cli.md) [doc, Meta-published repo]

```
# install (Windows)
iwr -useb https://developers.meta.com/horizon/install-cli/windows/ | iex
# or
npx -y metavr

metavr perf capture --mode standard|gpu|cpu|memory|lightweight|full|vr/xr|custom \
  --duration <ms, default 5000> --app <pkg> -o <file> \
  [--gpu-render-stage] [--gpu-metrics] [--cpu-scheduling] [--xr-runtime] \
  [--vulkan-layer] [--extended-scheduling] [--launch]
metavr perf analyze-trace --focus overview|gpu|cpu|frames|threads --json-out --report-out --asw
metavr perf query | compare | gpu-counters (>= 20 frames) | thread-state
metavr perf memory-snapshot --app <pkg>
metavr perf simpleperf classify|record|kernel-overhead
```

`-d` or `HZDB_DEVICE` selects the device. `--launch` captures a cold start
(the tool of choice for first-run hitches). Wrapper:
`quest_adb.py perfetto --app <pkg> --mode gpu --flags gpu-render-stage xr-runtime`.

## Raw Perfetto CLI (Q1-048, A3-046; Apr 2021 blog, pre-2023)

https://developers.meta.com/horizon/blog/how-to-run-a-perfetto-trace-on-oculus-quest-or-quest-2/ [doc]

```
adb shell rm -f /data/misc/perfetto-traces/trace
adb shell perfetto -c - --txt -o /data/misc/perfetto-traces/trace < config.txt
adb pull /data/misc/perfetto-traces/trace trace.pftrace
```

Config per the blog: `data_sources: { config { name: "track_event" } }`,
buffers 63488 KB and 2048 KB (DISCARD), `linux.process_stats`,
`duration_ms: 10000`. Perfetto is on by default in developer mode since OS
v27. Wrapper: `quest_adb.py perfetto --legacy-cli`.

Conflict ARM-C18: the 2021 blog says GPU counters appear only while
`adb shell ovrgpuprofiler -r...` runs in the background; the 2026 MQDH guide
offers GPU Metrics as a checkbox with no manual step. Open: confirm the GPU
counter tracks in a current trace with and without `-r` running.

## Reading a Unity trace (Q1-050 to Q1-055, from Meta's hz-perfetto-debug agent skill [doc])

- Markers: `PlayerLoop`, `PhaseSync`, `Gfx.WaitForPresent`,
  `PostLateUpdate.FinishRendering`, `RenderPipelineManager.DoRenderLoop`,
  `BatchRenderer.Flush`. Names differ across Unity/URP versions; check your
  own trace before hard-coding SQL.
- Threads: `UnityMain`, `UnityGfx`, `UnityChoreWorker`, `Job.Worker`,
  `GPU completion`, `OVRPollEvent`.
- Frame calls: OpenXR `xrWaitFrame`, `xrBeginFrame`, `xrEndFrame`; legacy
  VrApi `vrapi_WaitFrame`, `vrapi_BeginFrame`, `vrapi_SubmitFrame`.
- GPU-bound: CPU waits in `FenceChecker::Wait` or the `GPU completion` thread
  waits; GPU work shows as `surface#N` slices on tracks starting `GPU`. The
  skill maps surface#0 to the eye buffer and surface#2+ to shadows/post; that
  is a heuristic, identify surfaces by resolution and MSAA against
  ovrgpuprofiler `-t`.
- CPU-bound: `UnityMain` or `UnityGfx` slices past budget with no fence waits.
- `PhaseSync` 1-4 ms idle at `PlayerLoop` start is normal; near 0 means no
  headroom. Pre-FrameSync semantics: on v203+ whether the marker survives is
  unverified (QX-C4); use `slice_headroom_*` / `icfl_*` CSV columns and stale
  counts instead.
- Trace-processor tables: `slice`, `thread_track`, `thread`, `process`,
  `counter`, `counter_track`, `args`, `sched_slice`.

Per-frame main-thread cost, p95/p99 (Q1-055 method; compute over at least 20 s
of steady play; use the mean for throughput):

```sql
SELECT COUNT(*) AS frames,
       AVG(s.dur) / 1e6 AS mean_ms,
       MAX(s.dur) / 1e6 AS max_ms
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread t USING (utid)
WHERE s.name = 'PlayerLoop' AND t.name = 'UnityMain';
```

Percentiles: export `s.dur` for the same rows and compute p95/p99 offline, or
use `metavr perf analyze-trace --focus frames`.

Do not reuse the skill's stale-frame SQL as is: it counts every `PlayerLoop`
over 11.1 ms as stale, which hard-codes 90 Hz and confuses CPU frame duration
with compositor staleness (Q1-054, conflict Q1-C7). Staleness comes from VrApi
`Stale`, CSV `stale_frame_count`, or the XR runtime tracks.

Agent heuristics from the same skill (Q1-053; not VRC limits):

| Metric | Good | Warning | Critical |
|---|---|---|---|
| Stale frame rate | < 5% | > 10% | > 25% |
| Frame time std dev | < 1 ms | > 2 ms | > 4 ms |
| Main thread, share of budget | < 80% | > 80% | > 95% |
| GPU, share of budget | < 85% | > 85% | > 95% |
| Draw calls per frame | < 100 | > 200 | > 500 |

The draw-call row conflicts with the Runtime Optimizer's under-300 (Q1-C3);
budgets are owned by `quest-perf:quest-budgets-tiers`. The same skill states
the Quest 3 eye buffer as 1440x1584, which is wrong (Q1-C4: 1680x1760).

## XR runtime track names (known unknown)

Not documented on any Meta page (Q1-056, A3-045). Enumerate per Horizon OS
version and record them:

```sql
SELECT DISTINCT name FROM counter_track ORDER BY name;
SELECT DISTINCT name FROM track ORDER BY name;
```

## Contention case study (QUEST-GF2-010, GDC 2026 talk, from auto-captions)

Quest 3 trace: FPS 67 instead of 72; about 5 of 72 frames per second bad;
in those, `UnityMain` slept about 3.3 ms in a blocking wait on a system thread
that was slow to be scheduled. Method: scan the zoomed-out timeline for gaps,
go to the end of the main-thread sleep, follow the wake-up to the signalling
thread, check its scheduling state. The app runs on roughly half the cores
(core IDs differ per device; confirm in the CPU-scheduling track). App-side
fix: remove blocking waits on the main thread (long `JobHandle.Complete`,
synchronous I/O). Core placement: `arm-mobile-hw-perf:xr2-cpu-threads-neon`.
Source: https://developers.meta.com/resources/videos/VR-Performance-Fundamentals-for-Quest/
