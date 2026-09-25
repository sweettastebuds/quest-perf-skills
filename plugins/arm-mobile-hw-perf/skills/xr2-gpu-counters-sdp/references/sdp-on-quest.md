# Snapdragon Profiler on Quest: status, evidence, test procedure

All sources accessed 2026-09-24. Applies to Quest 2 (Adreno 650) and Quest 3/3S (Adreno 740v3), any Unity/URP version.

## Working position

Treat Snapdragon Profiler (SDP) as **unsupported on Quest unless proven on the target OS build** (A3-067). Primary stack: ovrgpuprofiler (realtime counters, stage traces), RenderDoc Meta Fork (per-draw bytes, Tile Timeline, shader stats), Perfetto/MQDH (timelines), OVR Metrics (long-session CSVs). Qualcomm's SDP thresholds still apply to same-named counters in those tools (A3-067 notes).

## Evidence, both sides

For "SDP works on Quest":
- Meta's current Unreal "Testing and Performance Analysis" page (updated 2026-04-14) lists SDP for CPU, GPU, DSP, memory, power, thermal and network analysis because Quest "uses a Qualcomm chipset". It gives no Quest setup, API or OS-version caveats; no Unity page mentions SDP (A3-059, GLES3-GF2-008) [doc].
- Meta's archived 2020 SDP page described a working GLES flow: start SDP before the app, only apps declaring the OpenGL requirement in the manifest appear, enable "OpenGL ES > Rendering stages" for traces, snapshots possible, quit SDP before unplugging (G3-084) [doc, pre-2023].
- SDP is still released (2025.8 and 2025.9.0.93022025 seen in search snippets) (A3-066) [community].

For "SDP does not work on Quest":
- Meta's developer-tools index omits SDP (A3-057) [doc]; Meta's dedicated SDP page now returns 404 (G3-084).
- 2019-06-25: Native Tracing API crash during Quest trace capture (SDP 1.0.7006, Unity 2019.1.6f1) (A3-064) [community].
- 2020-03-28: snapshot hung at "Retrieving Snapshot" on Quest; the reply's fix was granting external-storage read/write (A3-064) [community].
- 2020-12-02: SDP did not work with Vulkan apps on Quest; app quit on launch; poster suspected a debugger conflict (A3-063) [community].
- 2021-01-25: a Quest 2 user asked how to enable enhanced capture statistics (MSAA resolves); no answer (A3-064) [community].
- Snapshot captures crash on Quest 2 (G3-085) [community].
- Qualcomm support thread titled "Snapdragon Profiler not able to capture anything on Meta Quest 3/3s" (content unreadable, title only); QDN thread "[Bug report] Quest 2 Unity Vulkan app crashes on startup" (id 69910, title only) (A3-065, G3-085) [community].
- No release note states Quest support, and no last Quest-supported version is published (A3-066).

Dossier assessment (GX-C11, G3-C4): Meta's mention is generic; the failure reports are specific. Keep SDP optional and secondary.

## What only SDP documents

| Signal | Why you might need it | Meta-tool fallback |
|---|---|---|
| Per-surface UBWC "Optimal" / "Linear" (A3-062) | confirm a target kept UBWC (FFR/FDM and compute writes may disable it; ARM-C13, ARM-C14) | none documented; compare RenderDoc `Write Total` on the same content, optimal-tiled vs MUTABLE_FORMAT/LINEAR, and FFR off vs high [verify on device] |
| % Wave Context Occupancy (A2-090) | GPR / instruction-cache pressure | RenderDoc shader stats register footprint and Scratch Memory (Vulkan, Q1-063) |
| % CP Busy (A2-090) | query overhead | per-bin query cost reasoning in `arm-mobile-hw-perf:xr2-adreno-architecture` |
| Rendering Stages: render mode and subpass merge per surface (A2-090) | did subpasses merge | `ovrgpuprofiler -t -v` mode and stages; RenderDoc Tile Timeline (A3-030, A3-035) |
| Fragment ALU Instructions Half/Full (G3-042) | fp16 check | RenderDoc draw-call metrics have the same pair (Q1-062) |
| "Slow To Trace" memory stats (A3-055) | bytes per draw | RenderDoc Read/Write Total, Texture Memory Read BW, Vertex Memory Read (A3-036) |

## SDP modes (Qualcomm)

Realtime: CPU, EGL, GPU, memory, network, power, primitive processing, system memory, thermal. Trace: Vulkan rendering stages and API trace. Snapshot: single-frame draw list, resources, shader analysis, pixel history, overdraw. The Qualcomm guide does not mention Quest (A3-060).

## Overhead

About 5% CPU even when tracing only frame rate (A3-061, G3-084). On a CPU-bound Quest title that can move the CPU level. Never keep SDP attached during CPU timing or thermal runs.

## Test procedure (record the result per device and OS build)

From A3-066, G3-084 and GLES3-GF2-008. [verify on device]
1. Build a debuggable (Development) Unity build. For GLES, make sure the manifest declares the OpenGL requirement (G3-084).
2. Record the OS build and driver: `adb shell dumpsys SurfaceFlinger | grep GLES` (A2-089).
3. Install the current SDP; connect the headset in developer mode. Start SDP before launching the app (G3-084).
4. Try, in order, and note which step fails:
   - Realtime: GPU and Thermal metrics.
   - Trace: Vulkan rendering stages (or "OpenGL ES > Rendering Stages" on GLES).
   - Snapshot. If it hangs at "Retrieving Snapshot", grant the app external-storage read/write (A3-064, 2020 report).
5. Quit SDP before unplugging (G3-084).
6. If nothing is captured, fall back to `adb shell ovrgpuprofiler -t -v` (GLES3-GF2-008).
7. Cross-check any SDP counter against the same-named ovrgpuprofiler or RenderDoc counter before trusting it.

## Related tool status

- **Performance Interface Library (PIL)**: built by Meta with Qualcomm in 2020 to expose GPU data previously only in SDP, through GPU Systrace and ovrgpuprofiler. This is why counter names match Qualcomm's (A3-058) [doc, pre-2023].
- **GPU Systrace**: deprecated 2024-12-02 in favour of Perfetto; it needed `ovrgpuprofiler -e` (G3-083).
- **Perfetto GPU counters**: OS v27-era guidance required `ovrgpuprofiler -r` running in the background; current MQDH offers GPU Metrics as a capture option. Likely changed; confirm in a current trace (A3-046, ARM-C18). Track names on Quest are undocumented (A3-045).
- **AGI**: needs Android 11+ and a debuggable app, lists no Quest headset, and traces GLES through a custom ANGLE-to-Vulkan build, so GL timings do not reflect Adreno's native GL driver; last release v3.3.3 (2025-01-20) (G3-086). Superseded by Android Performance Analyzer (APA); Quest support undocumented (A3-056).
- **Mesa Turnip debug flags** (`sysmem`, `gmem`, `nobin`, `nolrz`, `noubwc`, `forcebin`): not present on Quest's Qualcomm driver (A2-092).
- **Adreno Offline Compiler**: Qualcomm-recommended for static instruction and register counts (A2-089, G3-042); used optionally by Meta's Quest Runtime Optimizer (Q1-093). Match to Quest's Meta-built driver is unverified (A2-089).

## Sources

- https://developers.meta.com/horizon/resources/developer-tools/ [doc]
- https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android/ [doc]
- http://web.archive.org/web/20200513224546/https://developer.oculus.com/documentation/native/android/mobile-snapdragon-profiler/ [doc]
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md (also .../topics/80-78185-2/sdp.html) [doc]
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://www.qualcomm.com/developer/software/snapdragon-profiler [community] (release versions via search snippets)
- https://developers.meta.com/horizon/blog/improving-gpu-profiling-on-oculus-quest/ [doc]
- https://developers.meta.com/horizon/documentation/unreal/ts-gpusystrace/ [doc]
- https://developers.meta.com/horizon/blog/how-to-run-a-perfetto-trace-on-oculus-quest-or-quest-2/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ [doc]
- https://developers.meta.com/horizon/documentation/unity/unity-quest-runtime-optimizer/ [doc]
- https://developer.android.com/agi/sys-trace/memory-efficiency [doc]
- https://developer.android.com/agi/supported-devices and https://developer.android.com/agi/frame-trace/frame-profiler [doc]
- https://communityforums.atmeta.com/discussions/dev-quest/is-any-way-to-make-a-vulkan-gpu-capture-on-quest-/837235 [community]
- https://developer.qualcomm.com/forum/qdn-forums/software/snapdragon-profiler/66963 , /67580 , /68286 (via web.archive.org) [community]
- https://mysupport.qualcomm.com/supportforums/s/question/0D5dK000009EniESAS/snapdragon-profiler-not-able-to-capture-anything-on-meta-quest-33s [community]
- https://developer.qualcomm.com/forum/qdn-forums/software/snapdragon-profiler/69910 [community]
- https://peterthor.se/tag/qualcomm-snapdragon-profiler/ [community] (site unreachable on 2026-09-24; content seen via search snippets only)
- https://docs.mesa3d.org/drivers/freedreno.html [community]

All accessed 2026-09-24.
