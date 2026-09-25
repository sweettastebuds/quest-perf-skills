# Adreno counter glossary for Quest

Counter -> where it appears -> meaning -> healthy range or reading -> source. All sources accessed 2026-09-24. Hardware: Quest 2 (Adreno 650), Quest 3/3S (Adreno 740v3). Counter meanings are driver-level and hold for any Unity/URP version and for Vulkan and GLES unless stated.

Tool keys:
- **RT**: `ovrgpuprofiler -r` realtime. Only the first 11 names are shown in Meta's doc (A3-028, Q1-065); for anything else, check `adb shell ovrgpuprofiler -m -v` on the device [verify on device].
- **Stage**: `ovrgpuprofiler -t3 -s <ids>` per render stage (list with `-m -t`) (A3-032).
- **Draw**: `ovrgpuprofiler -t3 -x=<ids>` per draw (list with `-x -m`) and RenderDoc Meta Fork draw-call metrics (Q1-062, Q1-073). The ovrgpuprofiler per-draw list is device-dependent; RenderDoc's table is documented.
- **OVRM**: OVR Metrics Tool stat (A3-048).
- **SDP**: Snapdragon Profiler (Qualcomm guide). Unsupported on Quest unless proven (A3-067).
- **AGI**: Android GPU Inspector naming (A3-056). AGI itself does not support Quest (G3-086).

Healthy ranges from Qualcomm apply to Adreno in general, not Quest specifically (A3-054).

## Stalls and memory

| Counter | Where | Meaning | Healthy range / reading | Source |
|---|---|---|---|---|
| % Stalled on System Memory | RT, Draw, AGI ("% Stall on System Memory") | share of cycles L2 waits on system memory; with fetch stalls, marks bandwidth- or latency-bound work rather than ALU-bound | under ~2%; short spikes to 30% OK | A3-039, A3-054 [doc] |
| GPU % Bus Busy | RT | memory-bus utilisation; realtime bandwidth proxy | up to ~25% battery-conscious; up to ~90% max-performance | A3-028, A3-054 [doc] |
| % Texture Fetch Stall | RT, Draw, OVRM ("Texture Fetch Stall %") | shader waiting on texture fetch | **Conflict:** Qualcomm under ~2%, sustained ~16%+ too high (A3-054); AGI above ~5% is a concern (A3-056) | [doc] both |
| % Vertex Fetch Stall | RT, Draw, OVRM | waiting on vertex attribute fetch | near 0% | A3-054 [doc] |
| Read Total (Bytes) | Draw (RenderDoc), AGI (Bytes/sec), SDP ("Slow To Trace" group) | all GPU memory reads, whichever block issued them | no threshold; lower is better; capture apart from timing | A3-036, A3-055 [doc] |
| Write Total (Bytes) | Draw (RenderDoc), AGI, SDP (Slow To Trace) | all GPU memory writes; "writes to main memory are expensive" | lower is better; summed over an eye-buffer pass, compare with resolved-colour size (method in `arm-mobile-hw-perf:xr2-bandwidth-power`) | A3-036, A3-037, A3-055 [doc] |
| Texture Memory Read BW (Bytes) | Draw, AGI, SDP (Slow To Trace) | texture-pipe reads incl. vertex textures and compute | rank materials | A3-036, A3-055 [doc] |
| Vertex Memory Read (Bytes) | Draw, AGI, SDP (Slow To Trace) | non-texture vertex fetch; high during binning explains slow binning | rank meshes | A3-036, A3-055 [doc] |
| SP Memory Read (Bytes) | Draw | explicit shader loads (SSBOs) | rank | A3-036 [doc] |
| Avg Memory Latency Cycles | SDP (Slow To Trace) | average memory latency | no published range | A3-055 [doc] |
| Avg Bytes / Fragment | Draw | texture memory read ÷ fragments shaded; Meta calls it imprecise | ranking only | A3-038 [doc] |
| Avg Bytes / Vertex | Draw | Vertex Memory Read ÷ vertices shaded | ranking only | A3-038 [doc] |
| MEM F / `Mem=` | OVRM, VrApi logcat | memory clock; only documented memory-side clock signals | whether it scales with level is undocumented [verify on device] | A3-053, ARM-GF1-004 [doc] |
| GPU Memory Access | MQDH Performance Analyzer | GPU memory read/write bandwidth graph | units, rate, counter undocumented [verify on device] | A3-047 [doc] |

## Texture cache and filtering

| Counter | Where | Meaning | Healthy range / reading | Source |
|---|---|---|---|---|
| % Texture L1 Miss | RT, Draw, OVRM | L1 miss-to-request ratio | under 50% | A3-040, A3-054 [doc] |
| % Texture L2 Miss | RT, Draw, OVRM | L2 miss-to-request ratio | under 40% | A3-040, A3-054 [doc] |
| L1 miss high, L2 miss low | pattern | access-pattern thrash, not DRAM bandwidth | interpretation | Q1-074 [community] |
| L1 Texture Cache Miss Per Pixel | RT, Draw | L1 misses normalised per pixel | no published range | A3-028, A3-040 [doc] |
| % Anisotropic / Linear / Nearest Filtered | Draw, OVRM | share of samples per filter mode | watch aniso share when fetch stall is high; 8x aniso cost 8.9 of 13.8 ms in one non-Unity Quest 3 case | A3-040 [doc], Q1-075 [measured] |
| % Non-Base Level Textures | Draw | share of samples from mips above level 0 | low on minified surfaces suggests missing mips [verify on device] | A3-040 [doc] (interpretation) |
| % Texture Pipes Busy | Draw, SDP | texture unit load; tells whether moving work to textures is safe | no published range | A2-090, A3-040 [doc] |
| Avg Textures per Fragment | OVRM; Draw ("Textures/Fragment") | texture fetches per fragment | no published range | A3-048, Q1-062 [doc] |

## Shader load and occupancy

| Counter | Where | Meaning | Healthy range / reading | Source |
|---|---|---|---|---|
| % Time Shading Fragments / Vertices | Draw, OVRM | which stage owns the time; stage ms ~= App ms × % ÷ 100 | the larger one is the stage to cut | Q1-062 [doc], Q1-074 [community] |
| % Shaders Busy vs % Shader ALU Capacity Utilized | Draw | busy but low ALU use = stalled, not computing | pattern | Q1-062 [doc], Q1-074 [community] |
| % Time ALUs Working / % Time EFUs Working | Draw | ALU and special-function unit activity | no published range | Q1-062 [doc] |
| Fragment ALU Instructions (Full / Half) | Draw, SDP | 32-bit vs 16-bit fragment ALU instructions | Half much higher than Full when fp16 is intended | G3-042 [doc], Q1-062 [doc] |
| Fragment EFU Instructions; EFU/Fragment, EFU/Vertex | Draw | special-function (transcendental) instructions | cost model: `arm-mobile-hw-perf:xr2-shader-cost-model` | Q1-062 [doc] |
| Avg Instructions per Fragment / Vertex | OVRM; Draw (ALU/Fragment, ALU/Vertex) | instruction volume | no published range | A3-048, Q1-062 [doc] |
| % Instruction Cache Miss | Draw | shader instruction-cache misses; pairs with occupancy | no published range | Q1-062 [doc] |
| % Wave Context Occupancy | SDP | resident waves; low = GPR or instruction-cache pressure | no published range or GPR table for 650/740; compare before/after. Meta-tool equivalent unknown [verify on device] | A2-067, A2-090 [doc] |
| % CP Busy | SDP | command-processor load; reveals query overhead | no published range | A2-090 [doc] |
| Vertices Shaded, Fragments Shaded (/Second in RT) | Draw, RT (per community) | work volume; ÷ FPS gives per-frame; overdraw ~= fragments per frame ÷ (2 × eye width × eye height) | ranking | Q1-062 [doc], Q1-074 [community] |
| % Time Compute | Draw | compute share | no published range | Q1-062 [doc] |

## Primitives and binning

| Counter | Where | Meaning | Healthy range / reading | Source |
|---|---|---|---|---|
| Binning stage share | `-t -v` stage trace, RenderDoc Tile Timeline | Binning ms ÷ surface ms | 10-20%; 30% "usually too much" | A3-054, G3-079 [doc] |
| Pre-clipped Polygons/Second | RT, Draw | primitives submitted | no published range | A3-028, Q1-062 [doc] |
| % Prims Trivially Rejected | RT, Draw | primitives rejected before rasterisation | no published range | A2-087, A3-028 [doc] |
| % Prims Clipped | RT, Draw | primitives crossing clip planes | no published range | A3-028 [doc] |
| Average Vertices/Polygon, Reused Vertices/Second, Average Polygon Area | Draw | index reuse and triangle size | no published range | Q1-062 [doc] |
| Average Vertices Per Frame, Average Fill Percentage per Eye | OVRM | frame-level vertex and fill volume | trends | A3-048 [doc] |
| LRZ State | `-t3 -x` per draw | per-draw LRZ status | reading owned by `arm-mobile-hw-perf:xr2-adreno-architecture` | Q1-073 [doc] |

## Clocks and preemption

| Counter | Where | Meaning | Healthy range / reading | Source |
|---|---|---|---|---|
| Clocks / Second | RT | GPU clock | Quest 3/3S: levels table max 599 MHz (L5) vs profiler page 690/492 MHz (ARM-C3). Read on device | A3-028, A3-100 [doc] |
| Clocks | Draw | cycles per draw; sort by this first | relative only (per-draw stalls) | Q1-062, A2-088 [doc] |
| Preemption, Avg Preemption Delay | Draw | compositor preemption | not app work | A3-041 [doc] |
| Preempt stage | `-t` stage trace | compositor preemption | do not charge to app; no published subtraction rule | A3-031, Q1-070 [doc] |

## Shader stats (RenderDoc Meta Fork, Vulkan only)

Fields: Instruction Count All, ALU 32-bit / 16-bit, Complex, Texture Read, Flow Control, Barrier/Fence, Short/Long Latency Sync, register footprints, Scratch Memory, I/O components, Shader Processor Utilization %, Memory Read/Write (Q1-063). Needs a Development build (G3-073) Qualcomm: Vulkan shader stats (SDP example) need driver 636+ (A2-089); whether the same gate applies to RenderDoc Meta Fork shader stats is undocumented [verify on device].

| Field | Reading | Source |
|---|---|---|
| Texture fetches per read group | keep below 15 | Q1-063 [doc] |
| Scratch Memory | any use means poor performance (spill) | Q1-063 [doc] |
| ALU 16-bit vs 32-bit | confirms `half` compiled to 16-bit | Q1-063 [doc] |
| Register footprint | higher = fewer resident waves (A2-067); no 650/740 table | A2-067 [doc] |

GLES: no shader stats in RenderDoc; use the Adreno Offline Compiler, whose output may differ from Quest's Meta-built driver [verify on device] (G3-073, A2-089).

## Metric counts (conflicts)

- ovrgpuprofiler realtime: 47 (Meta example), 72 / 78 on Quest 3S (arXiv), 81 on Quest 3 (community skill). Q1-C8.
- RenderDoc draw-call table: ~48 current vs 59 in a search snippet. ARM-C16.

## Sources

- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-draw-call-metrics/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-drawcall/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-shaderstats/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-ovrmetricstool/ and https://developers.meta.com/horizon/documentation/unity/ts-ovrstats/ [doc]
- https://developers.meta.com/horizon/documentation/unity/ts-mqdh-logs-metrics/ [doc]
- https://developers.meta.com/horizon/documentation/native/android/ts-logcat-stats/ [doc]
- https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ [doc]
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/sdp.md (also .../topics/80-78185-2/sdp.html) [doc]
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html [doc]
- https://developer.android.com/agi/sys-trace/memory-efficiency [doc]
- https://developer.android.com/agi/supported-devices [doc]
- https://github.com/tommy-xr/functor/blob/HEAD/.claude/skills/oculus-profiling/SKILL.md [community] / [measured]
- https://arxiv.org/abs/2509.10703 [community]

All accessed 2026-09-24.
