# gles3-perf research dossier

**Scope.** This dossier covers OpenGL ES 3.0/3.1/3.2 as used by Unity URP projects on standalone Meta Quest 2 (Snapdragon XR2, Adreno 650, 1 MB GMEM) and Quest 3 / Quest 3S (XR2 Gen 2, Adreno 740, about 2 MB GMEM). It covers:
- **Versions:** which GLES / GLSL ES levels the Quest drivers expose, what Unity emits (`#pragma target`, Require ES3.x, Unity 6.6's GLES 3.1 floor), and the GLES2 removal.
- **API decision:** GLES vs Vulkan today, with measured evidence kept apart from vendor claims. Topics are the Vulkan-only features (AppSW, OBD, Symmetric Projection, MRR, subsampled FFR, Late Latching), the Unity Vulkan buffer-copy issue (UUM-93226), and driver overhead.
- **Tile-friendly rendering:** GMEM load/store, `glInvalidateFramebuffer`, FBO switches and mid-frame readbacks, MSAA resolved on tile, FlexRender binned/direct, LRZ.
- **Multiview:** `OVR_multiview` / `OVR_multiview2` and how Unity maps SPI/Multiview onto them.
- **Driver and state overhead:** state changes, UBOs, instancing, buffer streaming and orphaning, fences.
- **Shaders:** compile/link hitches, program-binary caching (Android EGL blob cache, `OES_get_program_binary`), WarmUp, precision (`mediump`/`half`).
- **Adreno extensions:** those confirmed per headset and whether Unity or Meta use them.
- **Capture:** RenderDoc Meta Fork, ovrgpuprofiler, Perfetto, Snapdragon Profiler, AGI.

Meta recommends Vulkan and treats GLES as legacy. This bundle serves teams still shipping or evaluating GLES, and anyone who needs the evidence behind the API choice. Out of scope: PC VR / Link, HDRP (not supported on Quest), Unreal (numbers appear only as context), Godot, and generic phone advice that does not hold for stereo VR. Eye-tracked foveation (Quest Pro) gets one line. Adreno is not Mali: Arm material is used only for generic tile-based concepts, plus one Arm figure that is explicitly rejected (G3-018).

**Access date.** 2026-09-24 for every source.

**Method.**
- **Topic research.** Three topic researchers wrote notes from web sources:
  - G1: GLES versions and the GLES-vs-Vulkan decision (80 findings, 13 gaps).
  - G2: tile load/store, MSAA on tile, multiview and driver overhead (94 findings, 14 gaps).
  - G3: shader compilation, program binaries, precision, extensions and capture tools (87 findings, 14 gaps).
- **Synthesis.** This dossier merges those notes by coverage area, not by researcher.
  - Every finding keeps its original ID. Duplicates are merged into one finding that lists every original ID, separated by " / ", and carries all of their sources and details.
  - Every topic-level conflict is kept. Conflicts that are the same subject are merged the same way. New cross-topic conflicts found while merging are numbered GX-C1 onward.
- **Gap-fill.** Two quick web checks were made during synthesis, only to settle contradictions between notes files:
  1. The extension-count badges on opengles.gpuinfo.org reports 8023 and 6387 (GX-C3).
  2. The Unity issue-tracker JSON state codes for UUM-93226, calibrated against UUM-149765 (Open) and UUM-102876 (Won't Fix) (GX-C1).

  No other new research was done at synthesis.
- **Round-1 audit (2026-09-24).** A coverage critic and spot-checker:
  - restored §6–§8, Conflicts, Known unknowns and the Source list from the topic notes. They had been cut off at synthesis.
  - added gap-fill findings GLES3-GF1-001 to GLES3-GF1-008.
  - re-checked 20 groups of numeric or version-specific claims against their primary sources. Every fix is noted where it happens and summarised under "Round-1 audit corrections" in Conflicts.
  - reconstructed the KU numbering. Synthesis referred to KU numbers without writing the list, so the list in "Gaps and known unknowns" keeps every referenced number with its referenced meaning and fills the unreferenced numbers with the remaining topic gaps.
- **Round-2 audit (2026-09-24).** It targeted the open items from round 1: KU-01, KU-02, KU-10, KU-15, KU-17 to KU-19 and KU-35. It:
  - added GLES3-GF2-001 to GLES3-GF2-008 and conflicts GX-C10 and GX-C11;
  - re-checked 17 groups of claims ("Round-2 audit spot-checks" in Conflicts);
  - marked the remaining device-only items in the KU list.

  Browser tools were not used, so the JavaScript-rendered Qualcomm forum stayed unreadable.

**Evidence tags.**
- [doc]: official documentation, specs, vendor blogs and engine source. This covers Meta Horizon developer docs and blog, the Unity manual, package docs and Graphics source on GitHub, Qualcomm Adreno docs, the Khronos registry, Android/AOSP source, Android developer docs and Arm docs.
- [measured]: a source reporting its own measurements, with the test setup given. This includes opengles.gpuinfo.org device capability dumps (real device queries submitted by third parties), timing tables in Unity tracker entries that state their setup, and Qualcomm/Meta sample timings.
- [community]: forums, issue-tracker discussion, and blog posts. These are leads; they are confirmed via [doc]/[measured] where both are cited.
- [verify on device]: the claim needs hardware confirmation. The usual reasons are a vendor claim without a measurement, likely Quest 2 vs Quest 3 divergence, inference from phone SoCs, or undocumented Unity behaviour.
- **Tagging conventions inherited from the notes:**
  - G1 tags Unity issue-tracker entries [community], including Unity QA FPS pairs.
  - G2 tags UUM-149765 [measured], because it reports a timing table with a stated setup.
  - Extension exposure taken from gpuinfo reports is device-reported data. Treat it as [measured] even where a finding's primary tag is [doc], which happens when the finding is mainly about spec semantics.

  The original labels are kept.

**Goal tags.**
- [T] Throughput: lower average CPU/GPU frame time.
- [C] Consistency: no stale or dropped frames, tight p95/p99, no hitches (shader compile/link, loading), no thermal decay over a 20–30 minute session. [C] also covers long-term support risk.

**Applicability conventions** (the "Applies to" field).
- **Devices:**
  - "Quest 2": XR2, Adreno 650.
  - "Quest 3/3S": XR2 Gen 2, Adreno 740. Quest 3S differences are called out, for example its GPU clock in G3-081.
  - "Quest Pro": one line only (eye-tracked foveation).
  - "Quest by analogy": measured on a phone Adreno, not on a headset.
- **Unity:** "2021.3" (URP 12), "2022.3" (URP 14), "Unity >= 6000.0" (URP 17), or an explicit range such as "Unity 6000.1–6000.6". Patch floors are written as, for example, `2021.3.9f1+`.
- **URP:** "URP 12", "URP 14", "URP 17"; "URP 14+" means 14 and later.
- **API:** "GLES" is Unity's OpenGLES3 target on the Quest ES 3.2 driver. "Vulkan".
- **Packages:**
  - "OculusXR 4.x": `com.unity.xr.oculus`, the Oculus XR Plugin, deprecated from Unity 6.5.
  - "OpenXR 1.x": `com.unity.xr.openxr`.
  - "OpenXR Meta 2.x".
  - "OVRPlugin vNN".
- **(pre-2023; stale)** marks advice older than 2023.

**Budgets.** Frame budgets referenced in findings: 72 Hz = 13.9 ms, 90 Hz = 11.1 ms, 120 Hz = 8.3 ms. The app never gets the full budget.

**ID prefixes.**
- G1: versions and API decision.
- G2: tile, MSAA, multiview, driver.
- G3: shaders, extensions, capture.
- GX-C*: cross-topic conflicts found at synthesis.
- KU-*: known unknowns.

## Baseline fact re-verification

| Fact | Status | Detail | Source |
|---|---|---|---|
| Quest 2 GPU is Adreno 650 | confirmed | GL_RENDERER `Adreno (TM) 650` in four gpuinfo reports, 2020–2023. The device string is just "Quest", which does not formally exclude a Quest Pro (G1-002, G3 baseline). | https://opengles.gpuinfo.org/displayreport.php?id=6387 |
| Quest 3 GPU is Adreno 740 | confirmed | GL_RENDERER `Adreno (TM) 740`, device "Quest 3", Android 14, driver V@0837.0.7 dated 01/12/26, submitted 2026-02-20 (G1-001). | https://opengles.gpuinfo.org/displayreport.php?id=8023 |
| Quest 3S is an XR2 Gen 2 variant of Quest 3 | confirmed, with one difference | Meta's ovrgpuprofiler page says Quest 3 and Quest 3S both use the Adreno 740v3, but clocked at 690 MHz vs 492 MHz, about 71% (G3-081). UUM-149765 lists the same GLES driver V@0837.0.7 on a Quest 3S (G2-035). There is no gpuinfo report for Quest 3S. [verify on device] | https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ ; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 |
| RAM (6 GB / 8 GB) and frame budgets | not checked by this bundle | Outside the gles3 scope; owned by the quest-perf bundle. | — |
| Highest GLES level on Quest | confirmed | Both headsets report OpenGL ES 3.2 and GLSL ES 3.20, with ES 3.1+AEP. EGL is `1.5 Android META-EGL` (G1-001, G1-002, G1-003, G1-013 / G3-043). | https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://opengles.gpuinfo.org/displayreport.php?id=6387 |
| Meta recommends Vulkan and treats GLES as legacy (supported, no new features) | confirmed | The live page is undated; the earliest Wayback capture is 2024-10-11. The native-docs twin (`/documentation/native/android/os-vulkan-opengl/`) returns 404. Meta's "Advanced GPU Pipelines" page goes further: it calls Vulkan *required* and keeps its GLES content "for historical reference" (G1-028, G2-C1). | https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ ; http://web.archive.org/web/20241011053743/https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ |
| The GPU is Adreno, not Mali; Mali-specific GL features do not apply | confirmed | Neither headset exposes `GL_EXT_shader_pixel_local_storage` or `GL_EXT_shader_framebuffer_fetch_non_coherent` (G3-057, extension matrix). | https://opengles.gpuinfo.org/displayreport.php?id=8023 |
| Unity removed GLES2 in 2023.1 | confirmed | 2022.3 LTS is the last line with GLES2 (G1-023). | https://docs.unity3d.com/2023.1/Documentation/Manual/WhatsNew20231.html |
| Unity 6.6 GLES floor | changed | Unity 6.6 raises the Android GLES minimum from ES 3.0 to ES 3.1 (manifest `0x00030001`). `openGLRequireES31` is deprecated and replaced by "Use OpenGL ES 3.0 shaders" (G1-017, G1-018). | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html |
| Unity 6.6 is current; 6.7 LTS has not shipped | confirmed | Only 6000.7.0a4 (alpha) appears, in UUM-149765 (G2). G1 notes that "6.7 beta docs match 6.6". Both agree 6.7 has not shipped (GX-C7). | https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html |
| Oculus XR Plugin (the documented Unity GLES XR path on Quest) | changed | Deprecated from Unity 6.5; OpenXR Meta 2.1 on OpenXR 1.14 is at feature parity. The OpenXR plugin lists Quest as Vulkan-only (G1-024 / G2-093, G2-055). | https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html |
| Status of UUM-93226 (Vulkan buffer copies on Quest 2/3) | changed | History: Active in Feb 2025, then Third Party Issue by Dec 2025. Now Closed – Won't Fix on the 2022.3.X, 6000.0.X, 6000.1.X, 6000.2.X and 6000.3.X ports, last updated 2025-12-09, with no fixed-in version and no resolution note shown. At synthesis, the tracker JSON showed state 102 / status 4 on every port. Those are the same codes as Won't Fix UUM-102876; Open UUM-149765 shows 101 / 1. Votes: 21 (G1 baseline, G1-050, GX-C1). Round 2 re-check: unchanged. 103 / 3 is Fixed, calibrated on UUM-60833 and UUM-91896. No evidence that the Meta OS fix shipped (GLES3-GF2-002). | https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 ; https://issuetracker.unity.com/api/v1.0/issues/1364 |
| GLES extension list: Quest 3 | confirmed | Report 8023 has 123 GL + 35 EGL extensions (badge counts checked at synthesis). The two 2024 reports have 122 GL; the difference is `GL_EXT_clear_texture` (G3 baseline, G3-071, GX-C3). | https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://opengles.gpuinfo.org/displayreport.php?id=7475 |
| GLES extension list: Quest 2 | confirmed for drivers up to Jan 2023; current list unverifiable | Report 6387 (V@0690, 2023-01-13) has 110 GL + 34 EGL extensions (badge counts checked at synthesis). Across reports the GL count rose 99 → 102 → 110. No report exists from a 2024–2026 Quest 2 driver (G3 baseline, GX-C3). | https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=5092 |
| Quest 2 OS base today | changed | Early gpuinfo reports and UUM-93226's QA devices show Android 12. UUM-149765 (2026) lists a Quest 2 on Android 14, firmware 2.1.1034. AOSP 14 behaviour, including the EGL blob cache in G3-011 to G3-014, therefore applies to Quest 2 as well as Quest 3 (GLES3-GF1-006). | https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 |
| gpuinfo coverage of Quest | confirmed (round-1 audit) | A full walk of the database (8292 reports) finds exactly 7 Quest reports: 5092, 5278, 5808 and 6387 (Adreno 650), 7267 and 7475 (Adreno 740, Android 12), and 8023 (Quest 3, Android 14). None is later than Jan 2023 for Adreno 650, and none is a Quest 3S or Quest Pro (GLES3-GF1-005). | https://opengles.gpuinfo.org/backend/reports.php |
| GLES extension list: Quest 3S and Quest Pro | unverifiable | There is no gpuinfo report for either. Quest 3S shares the Adreno 740v3, so its list should match Quest 3 on the same OS build. [verify on device] | https://opengles.gpuinfo.org/backend/reports.php ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ |
| Quest 3 vs Quest 2 extension sets | confirmed | Quest 3 (V@0837) is a strict superset of Quest 2 (V@0690): 13 more GL extensions plus `EGL_NV_context_priority_realtime` (G1-015 / G3-044). | https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 |
| `EGL_ANDROID_blob_cache` visible to apps | confirmed absent, by design | It appears in no report. The spec reserves it for the Android EGL layer, which caches program binaries automatically (G3-009). Whether Meta's META-EGL keeps that cache is still [verify on device] (GX-C5). | https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_blob_cache.txt |
| Program-binary support | confirmed | `GL_OES_get_program_binary` is present on both headsets. GL_NUM_PROGRAM_BINARY_FORMATS = 1 and GL_NUM_SHADER_BINARY_FORMATS = 0 on both (G1-008 / G3-008). | https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 |
| GLES MSAA ceiling | confirmed | GL_MAX_SAMPLES = 4 on both headsets, so 8x MSAA is not available on GLES (G1-007 / G1-010 / G2-035). | https://opengles.gpuinfo.org/displayreport.php?id=8023 |
| No eye tracking on Quest 2/3/3S | confirmed | ETFR is Quest Pro only and needs Vulkan, Multiview and ARM64 (G1-034, G1-035 / G2-063 / G3-052). | https://developers.meta.com/horizon/documentation/unity/unity-eye-tracked-foveated-rendering/ |

## 1. GLES 3.0 vs 3.1 vs 3.2 on Quest; what Unity emits; GLES2 removal

### 1.1 What the Quest GLES drivers expose

- **G1-001** The Quest 3 GLES driver reports OpenGL ES 3.2 with GLSL ES 3.20. The newest report is #8023 (submitted 2026-02-20, Android 14):
  - GL_VERSION: `OpenGL ES 3.2 V@0837.0.7 (GIT@3dbacedba8…) (Date:01/12/26)`
  - GL_SHADING_LANGUAGE_VERSION: `OpenGL ES GLSL ES 3.20`
  - GL_VENDOR: `Qualcomm`
  - GL_RENDERER: `Adreno (TM) 740`

  ES 3.2 plus the listed extensions is the ceiling for anything Unity can use on GLES. [T]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 3 (Horizon OS build of early 2026); GLES · Evidence: [measured]
  - Notes:
    - The two older Quest 3 reports also give ES 3.2: #7475 (2024-07-07, V@0767.0, driver date 02/29/24) and #7267 (2024-03-29). G3 records both 2024 reports as Android 12 with V@0757/V@0767 (https://opengles.gpuinfo.org/displayreport.php?id=7475 ; https://opengles.gpuinfo.org/displayreport.php?id=7267).
    - No Quest 3S report exists (baseline table).

- **G1-002** The Quest 2 driver also reports OpenGL ES 3.2 with GLSL ES 3.20 (`Adreno (TM) 650`), across four reports from 2020 to 2023. [T]

  | Report | Report date | Driver build | Driver date |
  |---|---|---|---|
  | #5092 | 2020-12-20 | V@0514.0 | 11/06/20 |
  | #5278 | 2021-04-03 | — | — |
  | #5808 | 2022-02-24 | V@0582.0 | 09/03/21 |
  | #6387 | 2023-01-13 (Android 12) | V@0690.0 | 12/13/22 |

  - Source: https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=5092 ; https://opengles.gpuinfo.org/displayreport.php?id=5278 ; https://opengles.gpuinfo.org/displayreport.php?id=5808 (accessed 2026-09-24) · Applies to: Quest 2; GLES · Evidence: [measured]
  - Notes: G3 counts 99 → 102 → 110 GL extensions and 33 → 35 EGL across these reports. The badge on #6387 reads 110 GL / 34 EGL (GX-C3). No report from a 2024–2026 Quest 2 driver exists.

- **G1-003** Both headsets report EGL_VERSION `1.5 Android META-EGL`: Meta ships its own EGL layer on top of the Qualcomm GLES driver. [T]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 · Evidence: [measured]
  - Notes:
    - The Meta layer matters when you read EGL extension lists and context-priority support (G1-015 / G3-044, G3-069).
    - It is also why the AOSP blob-cache behaviour (G3-009) cannot be assumed without checking on device (GX-C5).

- **G1-004** The GLES driver is still being updated on Quest 3: the driver date moved from 02/29/24 (V@0767) to 01/12/26 (V@0837.0.7). "Legacy" does not mean the GLES driver binary is frozen. [C]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=7475 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 3 · Evidence: [measured]
  - Notes:
    - The reports cannot tell a bug-fix-only update from a feature update.
    - The extension count did grow (G3-071: `GL_EXT_clear_texture` appeared in the 2026 driver).

- **G2-082** Driver-version check: `adb shell dumpsys SurfaceFlinger | grep GLES` prints a line such as `GLES: Qualcomm, Adreno (TM) 740, OpenGL ES 3.2 V@0676.0`. Driver builds seen on Quest:
  - Quest 2: V@0690.0 (built 12/13/22).
  - Quest 3/3S: V@0837.0.7 (built 01/12/26).

  Record the driver version with every profiling capture. Qualcomm's own samples warn that newer drivers may optimize anti-patterns away, so results can move with OS updates. [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("Querying the driver version") ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]

- **G1-013 / G3-043** Both headsets satisfy ES 3.1+AEP and ES 3.2. Geometry and tessellation shaders are therefore available on GLES, and Unity's "Require ES3.1+AEP" and "Require ES3.2" checkboxes never exclude a Quest 2 or Quest 3.
  - AEP-related extensions present: `GL_ANDROID_extension_pack_es31a`, `GL_EXT_geometry_shader`, `GL_EXT_tessellation_shader`, `GL_EXT_texture_buffer`, `GL_EXT_texture_cube_map_array`, `GL_EXT_gpu_shader5`, `GL_OES_sample_shading`.
  - Qualcomm lists the hardware tessellation stages among features to avoid for performance.

  [T]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 · Evidence: [measured] (exposure); [doc] (Qualcomm advice)
  - Notes: Other reasons to avoid geometry and tessellation on Quest:
    - Unity's untethered-XR guide says to avoid geometry shaders (G1-048).
    - Tessellation and geometry push FlexRender into direct mode (G2-084).
    - They may disable foveation (G2-060 / G3-050).
    - They are disallowed with multiview (G2-049).

- **G1-005** Storage-buffer limits differ sharply between the headsets. A GLES shader that uses SSBOs in the vertex stage is capped at 4 blocks on Quest 2. [T]

  | Limit | Quest 2 | Quest 3 |
  |---|---|---|
  | GL_MAX_VERTEX_SHADER_STORAGE_BLOCKS | 4 | 12 |
  | GL_MAX_FRAGMENT_SHADER_STORAGE_BLOCKS | 4 | 12 |
  | GL_MAX_SHADER_STORAGE_BUFFER_BINDINGS | 24 | 36 |

  - Source: https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2 vs Quest 3; GLES 3.1+ · Evidence: [measured] [verify on device]
  - Notes:
    - This is a porting hazard for compute-driven or SSBO-heavy renderers on GLES on Quest 2. Test on the lowest device.
    - Unverified: whether a given Unity feature (Entities Graphics/BRG, GPU skinning) stays under the 4-block cap on GLES (KU-33).

- **G1-006** Compute limits are the same on both headsets, so GLES 3.1 compute is fully available on both. [T]
  - GL_MAX_COMPUTE_WORK_GROUP_INVOCATIONS = 1024.
  - GL_MAX_COMPUTE_SHARED_MEMORY_SIZE = 32768 bytes.
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; GLES 3.1+ · Evidence: [measured]

Other device limits live with their topics:
- UBO blocks, texture units, uniform vectors and draw buffers: G2-069 / G3-037 / G3-038 (§6.5).
- GL_MAX_VARYING_VECTORS = 31: G3-041 (§6.5).
- GL_MAX_SAMPLES = 4: G1-007 / G1-010 / G2-035 (§3.4).
- Binary formats: G1-008 / G3-008 (§6.1).
- UBO size: G2-070 (§5.2).

### 1.2 Unity's GLES targets, settings and shader levels

- **G1-016** Unity Android Player settings, 2022.3 through 6.5:
  - Auto Graphics API tries Vulkan first, then falls back to GLES3.2, then 3.1, then 3.0.
  - The "Require ES3.1", "Require ES3.1+AEP" and "Require ES3.2" checkboxes each set the minimum ES 3 minor version the app requires.
  - The manifest GLES requirement is added only when Auto Graphics API is on or OpenGLES3 is in the API list.

  [C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: Unity 2022.3–6000.5; Android/Quest · Evidence: [doc]
  - Notes:
    - For an A/B test, turn Auto off and list a single API. Otherwise the build may run on a different API from the one you think you are measuring.
    - Meta's ETFR page gives the same instruction (keep Vulkan as the only entry).

- **G1-017** Unity 6.6 raises the Android GLES minimum from ES 3.0 to ES 3.1. With OpenGL ES3 selected:
  - The manifest declares `<uses-feature android:glEsVersion="0x00030001" />`.
  - The Player no longer creates an ES 3.0 context.
  - The change cannot be reverted.

  [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (accessed 2026-09-24) · Applies to: Unity >= 6000.6 · Evidence: [doc]
  - Notes:
    - Unity is raising the GLES floor, not removing GLES. This is the only Unity 6.x GLES deprecation found; there is no Unity statement deprecating GLES for Android or XR as a whole.
    - G1 reports that the 6.7 beta docs match 6.6 (6.7 has not shipped; GX-C7).

- **G1-018** In Unity 6.6, `PlayerSettings.openGLRequireES31` is deprecated: its getter always returns true and its setter does nothing. The "Require ES3.1" checkbox is replaced by **Use OpenGL ES 3.0 shaders** (Player > Android > Other Settings). [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (accessed 2026-09-24) · Applies to: Unity >= 6000.6 · Evidence: [doc]
  - Notes:
    - Upgraded projects that never enabled Require ES3.1 get the new setting switched on automatically. They keep compiling `SHADER_API_GLES30` variants instead of `SHADER_API_GLES31`.
    - Turn the setting off to get ES 3.1 shader variants.
    - To require a higher level, use `openGLRequireES31AEP` / `openGLRequireES32` or the matching checkboxes.
    - Referencing the deprecated property is a build error under warnings-as-errors.

- **G1-019** Moving from ES 3.0 to ES 3.1 shaders raises URP's `MAX_VISIBLE_LIGHTS` from 16 to 32, which Unity says increases workload. The "Use OpenGL ES 3.0 shaders" setting exists partly so that upgraded projects do not regress by surprise. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (accessed 2026-09-24) · Applies to: Unity >= 6000.6; URP 17; GLES · Evidence: [doc]

- **G1-020** In URP source, `Input.hlsl` sets `MAX_VISIBLE_LIGHTS` as follows:
  - 16 (LOW_END_MOBILE) when both `SHADER_API_MOBILE` and `SHADER_API_GLES30` are defined.
  - 32 on other mobile targets, including Vulkan and GLES 3.1+.
  - 256 on desktop.

  On the C# side, `UniversalRenderPipeline.maxVisibleAdditionalLights` uses the low-end limit when `Graphics.minOpenGLESVersion <= OpenGLES30`. In the 2022.3 branch the low-end path also covers GLES2. [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/Input.hlsl ; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs ; https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs (accessed 2026-09-24) · Applies to: URP 14–17 · Evidence: [doc]
  - Notes:
    - The per-object light buffer is sized differently when a GLES build lacks Require ES3.1 (≤ 6.5) or keeps "Use OpenGL ES 3.0 shaders" (6.6).
    - A GLES-vs-Vulkan A/B test can therefore be confounded by this lighting difference as well as by the API (G1-079).

- **G1-021** Unity's `#pragma target` mapping for GLES: [T]

  | `#pragma target` | GLES level | Features |
  |---|---|---|
  | 3.0 | "OpenGL ES 3.0+" | — |
  | 3.5 | "OpenGL ES 3+" (the doc's wording; in practice ES 3.0) | — |
  | 4.0 | ES 3.1, or ES 3.1+AEP | geometry |
  | 4.5 | ES 3.1 | compute, randomwrite, msaatex |
  | 4.6 | ES 3.1+AEP | cubearray, tessellation |
  | 5.0 | ES 3.1+AEP | compute and tessellation |

  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/SL-Pragma-target.html (accessed 2026-09-24) · Applies to: Unity >= 6000.0 (the same table has appeared since 2021.3) · Evidence: [doc]
  - Notes:
    - Compute on GLES needs ES 3.1 (target 4.5); geometry and tessellation need AEP.
    - The exact GLSL `#version` string Unity emits per target was not found in docs (KU-01). Unity's public HLSLcc source partly answers it: `#version 300 es` or `310 es`, never `320 es` (GLES3-GF1-007, §6.4). Round 2: UUM-60833 is marked Fixed on 6000.2+ for compute shaders, with `#version 320 es` as the expected output (GLES3-GF2-005, GX-C10).
    - Round-1 audit spot-check: the table was re-read against the live page. The 3.0 row was added and the 3.5 row's wording corrected to the doc's "OpenGL ES 3+"; the other rows matched.

- **G1-022** Shader-side API branching macros:
  - `SHADER_API_GLES3` and `SHADER_API_VULKAN` select the graphics API.
  - `SHADER_API_GLES30` and `SHADER_API_GLES31` select the ES 3.x shader level (6.6).
  - Unity 6.5 adds `UNITY_PLATFORM_META_QUEST` for branching custom shaders on Meta Quest build profiles.

  [T]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/WhatsNewUnity65.html ; https://docs.unity3d.com/6000.5/Documentation/Manual/shader-branching-api.html (accessed 2026-09-24) · Applies to: Unity >= 6000.5 · Evidence: [doc]

- **G1-027** Unity's GPU Skinning setting in Android Player settings offers CPU, GPU and GPU (Batched), with no graphics-API restriction stated. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: Unity 6000.3; Android · Evidence: [doc] [verify on device]
  - Notes:
    - This contradicts a July 2026 forum claim that GPU skinning is unavailable on GLES (G1-C3).
    - To check: enable GPU skinning on a GLES build and see in the Unity Profiler and Frame Debugger whether skinning runs as a compute dispatch or falls back to CPU.
    - If it runs as compute, also see Qualcomm's advice not to interleave compute with graphics on GLES (G2-067).
    - Round-2 gap-fill: GLES3-GF2-001 shows the documented requirement chain (GPU skinning is compute; compute on Android GL needs ES 3.1; Quest exposes ES 3.2). The doc evidence therefore favours GPU skinning being available on GLES on Quest. The on-device check is still needed.

- **GLES3-GF2-001** Unity's GPU skinning runs as compute shaders, and Unity documents compute on Android OpenGL as needing ES 3.1. Both headsets expose ES 3.2, and their compute-stage SSBO limits are far above the 4-block vertex/fragment cap on Quest 2. [T]
  - Unity's `MeshDeformation` enum defines both `GPU` and `GPUBatched` as "using compute shaders". `PlayerSettings.meshDeformation`:
    - `GPU` issues one dispatch per mesh and per active blend shape.
    - `GPUBatched` batches meshes and blend shapes. Unity recommends it "if you build for a graphics API that supports compute shaders" and render many skinned meshes.
    - `PlayerSettings.gpuSkinning` is marked for future deprecation: `true` maps to `GPUBatched` and `false` to `CPU`.
  - Unity's compute-shader page lists "OpenGL ES 3.1 on Android" among the platforms where compute works.
  - Device limits from gpuinfo: GL_MAX_COMPUTE_SHADER_STORAGE_BLOCKS is 24 on Quest 2 (report 6387) and 36 on Quest 3 (report 8023). GL_MAX_COMPUTE_WORK_GROUP_INVOCATIONS is 1024 and GL_MAX_COMPUTE_SHARED_MEMORY_SIZE is 32768 on both.
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/MeshDeformation.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings-meshDeformation.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings-gpuSkinning.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/class-ComputeShader-introduction.html ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Unity 6000.3 docs (enum and settings); Quest 2, Quest 3/3S; GLES 3.1+ · Evidence: [doc] [verify on device]
  - Notes:
    - This is doc-level inference; no Unity page says "GPU skinning works on OpenGL ES on Quest". The July 2026 forum claim (G1-C3) is not backed by any cited source.
    - An ES 3.0-only context would have no compute. That context does not arise on Quest: from Unity 6.6 the Player never creates one (G1-017), and earlier versions create the highest context the driver offers (G1-016). Whether "Use OpenGL ES 3.0 shaders" (6.6) or an unticked "Require ES3.1" (≤ 6.5) drops the ES 3.1 compute variants of Unity's skinning shader is not documented. [verify on device]
    - The compute-stage limit (24 on Quest 2) is the one that applies to skinning dispatches, not the 4-block vertex/fragment cap in G1-005. This narrows KU-33 for skinning; Forward+ and BRG paths still bind SSBOs in graphics stages.
    - Verify: in a GLES development build, look for skinning compute dispatches in the Frame Debugger or RenderDoc, and check in the Profiler Timeline that the skinning samples are no longer on the CPU worker threads. The exact marker names were not checked against a Unity doc.

### 1.3 GLES2 removal

- **G1-023** Unity 2023.1 removed OpenGL ES 2.0 from the engine and from URP, which also dropped WebGL1. 2022.3 LTS is the last line that still has GLES2. [C]
  - Source: https://unity.com/releases/editor/whats-new/2023.1.0 ; https://docs.unity3d.com/2023.1/Documentation/Manual/WhatsNew20231.html (accessed 2026-09-24) · Applies to: Unity 2023.1+ / 6000.x · Evidence: [doc]
  - Notes:
    - Quest advice from before 2023 that mentions "GLES2 vs GLES3" or GLES2 fallbacks is stale (pre-2023; stale).
    - In 2022.3, URP's low-end light path still covers GLES2 (G1-020).

### 1.4 Unity's GLES XR path on Quest

- **G1-024 / G2-093** Unity's documented GLES XR path on Quest is the Oculus XR Plugin (OculusXR), which is deprecated from Unity 6.5. [C][T]
  - The Oculus XR Plugin 4.5.5 docs list display support as "OpenGL ES 3.0" and Vulkan. That is Unity's API family label, not the driver level, which is ES 3.2 (G1-001).
  - The plugin is deprecated from Unity 6.5, not stated as removed. The OpenXR Meta 2.1 package on OpenXR 1.14 is at feature parity, and new Quest features go only to OpenXR.
  - The Unity OpenXR plugin lists Vulkan only for Quest (G2-055).
  - Meta says Vulkan is recommended and GLES is supported but legacy, with no new features (G1-028).

  GLES-specific tuning therefore has a limited shelf life.
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/oculus-plugin.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html ; https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ (accessed 2026-09-24) · Applies to: OculusXR 4.x; Unity 2021.3–6000.6; OpenXR 1.x · Evidence: [doc]
  - Notes:
    - G1-024 was tagged [C] and G2-093 [T].
    - The GLES-only Low Overhead Mode lives in this plugin (G1-043 / G2-079), so the deprecation strands it.
    - Unity's 6000.x GLES XR repros use OculusXR (G2-C8).
    - Whether FFR works on GLES under OpenXR is unresolved (GX-C8).

## 2. GLES vs Vulkan decision today

### 2.1 Meta's stance and store implications

- **G1-028** Meta's "OpenGL ES and Vulkan" page says:
  - Vulkan is the recommended API.
  - OpenGL ES is still supported, but "OpenGL ES is now considered a legacy graphics API" and new Quest features go only to Vulkan.
  - Vulkan is recommended for both mobile and PC VR on Meta headsets, and is described as lower-overhead.

  [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ (accessed 2026-09-24) · Applies to: all Quest devices, all engines · Evidence: [doc]
  - Notes:
    - The page has no date. The earliest Wayback capture found is 2024-10-11 (http://web.archive.org/web/20241011053743/https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/); later captures are 2024-12-23, 2025-01-15 and 2025-04-24.
    - It gives no numbers for "lower overhead".
    - Meta's "Advanced GPU Pipelines" page goes further and calls Vulkan required (G2-C1).
    - Qualcomm's guide also says "Prefer Vulkan to OpenGL ES" (G3-C3, merged into G1-C1 / G2-C7 / G3-C3).

- **G1-029** Meta's history, from the same page:
  - Oculus Go shipped in 2018 with GLES only.
  - Vulkan arrived in 2019.
  - The original Quest launched with both APIs.

  [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ (accessed 2026-09-24) · Applies to: context · Evidence: [doc]
  - Notes: 2022 community advice that Meta recommended GLES for production predates this page and is stale (G1-062, G1-C6) (pre-2023; stale).

- **G1-030** No Meta Horizon Store policy, VRC or submission rule requiring Vulkan was found. Meta's only published position is "recommended" plus "still supported". [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ (accessed 2026-09-24) · Applies to: store submission · Evidence: [doc]
  - Notes:
    - The practical store implication is indirect. Meta's performance guidance leans on AppSW and ETFR, which are Vulkan-only (G1-031, G1-034), so a GLES app cannot use them to hit frame-rate targets.
    - Check the current VRC list before submission (KU-14).

### 2.2 Vulkan-only features (documented)

- **G1-031** Application SpaceWarp (AppSW) is documented as Vulkan-only; Meta states that no other graphics API supports it. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-asw/ (accessed 2026-09-24; page dated 2026-05-13) · Applies to: Quest 2, Quest 3/3S; Unity 2022.3.15f1+, 6000.0.9f1+, or 6000.4.0f1+ (recommended); OVRPlugin v34+; Vulkan · Evidence: [doc]
  - Notes:
    - Optimize Buffer Discards is required.
    - Meta supplies URP fork branches: `2022.3/14.0.8`, `/14.0.9`, `/14.0.10-oculus-app-spacewarp`; `6000.0/oculus-app-spacewarp`; `6000.4/oculus-app-spacewarp`.
    - The runtime toggle is `OVRManager.SetSpaceWarp()`.
    - `GL_QCOM_frame_extrapolation` exists on the Quest 3 GLES driver, but nothing ties it to AppSW (G1-015 / G3-044, G3-062).

- **G1-032** Meta claims AppSW gives an app up to 70% more compute budget by rendering at half rate and synthesising the other frames. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-asw/ (accessed 2026-09-24) · Applies to: Vulkan only · Evidence: [doc] [verify on device]
  - Notes:
    - This is a vendor claim with no published independent measurement.
    - To measure: in OVR Metrics Tool, compare App GPU time and CPU frame time rendering at 36 fps with AppSW against native 72 fps, on the same scene.

- **G1-033** The Space Warp motion-vector format can be RGBA16f or RG16f. Meta says RG16f halves motion-vector bandwidth. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/metaquest.html ; https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (accessed 2026-09-24) · Applies to: OpenXR 1.16+ with AppSW; Vulkan · Evidence: [doc]

- **G1-034** Eye-Tracked Foveated Rendering (ETFR) is Vulkan-only and needs Multiview. The Oculus plugin docs add Quest Pro and ARM64 as requirements. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-eye-tracked-foveated-rendering/ ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/oculus-plugin.html (accessed 2026-09-24) · Applies to: Quest Pro only (eye tracking); Vulkan · Evidence: [doc]
  - Notes:
    - The Meta page tells you to keep Vulkan as the only entry in the Graphics APIs list.
    - Out of scope for Quest 2/3/3S.

- **G1-035 / G2-063 / G3-052** Subsampled Layout needs Vulkan in Unity, even though the GLES driver on both headsets exposes `GL_QCOM_texture_foveated_subsampled_layout`. Subsampled Layout is the FFR companion that stores foveated regions at reduced resolution, which avoids the upscale at store and so cuts bandwidth and periphery artifacts. [T]
  - Meta's Unity FFR page (updated Aug 28, 2026) says it requires Vulkan and the Unity OpenXR Plugin 1.9.0+.
  - The Oculus plugin docs say "Subsampled Layout" is Vulkan-only. Enable it only at FFR level 2 or higher, because it raises Timewarp (compositor) cost.
  - Rules of the GL extension (`FOVEATION_SUBSAMPLED_LAYOUT_METHOD_BIT_QCOM`):
    - Samplers must be declared `layout(subsampled)`.
    - No mipmaps.
    - Only CLAMP_TO_EDGE or BORDER wrapping.
    - Anisotropy of at most 1.
    - ReadPixels, Blit or TexImage on the texture triggers a reconstruction pass.
  - Unity GLES projects cannot enable it without native code.
  - Eye-tracked foveation is Quest Pro only (Vulkan + Multiview + ARM64) and does not apply to Quest 2/3/3S.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-fixed-foveated-rendering/ ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/oculus-plugin.html ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html ; https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated_subsampled_layout.txt ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; the GL extension is exposed on GLES; the Unity/Meta path is Vulkan-only · Evidence: [doc]
  - Notes:
    - The deprecated native VrApi FFR page (updated Oct 18, 2024) covered subsampling on Vulkan via `VRAPI_SWAPCHAIN_CREATE_SUBSAMPLED_BIT` (https://developers.meta.com/horizon/documentation/native/android/mobile-ffr/; see G1-044 / G2-062 / G3-053).
    - For the other foveation extension details, see §7.3.

- **G1-036** Late Latching is Vulkan-only in both the Oculus plugin and the OpenXR Meta Quest Support settings. Meta describes its overhead as negligible and recommends it for most apps. [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/oculus-plugin.html (accessed 2026-09-24) · Applies to: OpenXR / OculusXR; Vulkan · Evidence: [doc]
  - Notes: It is a latency feature, not a throughput one, and is listed here because it is Vulkan-only.

- **G1-037** Symmetric Projection is Vulkan-only and needs Multiview. Meta claims a 5–15% improvement in GPU-bound scenes. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (accessed 2026-09-24; page dated 2026-05-11) · Applies to: OpenXR Meta Quest Support / OculusXR; Vulkan · Evidence: [doc] [verify on device]
  - Notes:
    - This is a vendor claim; no independent numbers were found.
    - Meta advises profiling it against custom shaders that depend on per-eye asymmetry.

- **G1-038** Optimize Buffer Discards (OBD) is Vulkan-only. It makes 4x MSAA attachments lazily allocated (memoryless). [T]
  - Meta's memory savings: about 90 MB per eye on Quest 3 (4x MSAA at 1680x1760) and about 66 MB per eye on Quest 2 (1440x1584).
  - Meta recommends it for virtually every Quest app.
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/features/metaquest.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; Vulkan; MSAA on · Evidence: [doc]
  - Notes:
    - OBD is also Unity's workaround for UUM-93226 (G1-051, G1-053) and a prerequisite for AppSW.
    - The GLES analogue is implicit-resolve MSAA via `GL_EXT_multisampled_render_to_texture` (G2-036 / G3-048). Whether Unity's GLES backend uses it for XR eye buffers is unknown (KU-18); the UUM-149765 StoreColor numbers suggest it does (G2-041). Round 2: for multiview eye buffers, Unity's manual names `GL_OVR_multiview_multisampled_render_to_texture` (GLES3-GF2-004).

- **G1-039** Multiview Render Regions (MRR) is Vulkan-only. [T]
  - It uses `VK_QCOM_multiview_per_view_viewports` and `VK_QCOM_multiview_per_view_render_areas`.
  - It requires Oculus plugin 4.6 or OpenXR 1.14, Unity 6.1+, Multiview and Symmetric Projection.
  - Unity expects no gain when the frame uses intermediate textures or post-processing.
  - Source: https://docs.unity3d.com/6000.1/Documentation/Manual/xr-multiview-render-regions.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/metaquest.html ; https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ (accessed 2026-09-24) · Applies to: Unity >= 6000.1; Quest 2, Quest 3/3S; Vulkan · Evidence: [doc] [verify on device]
  - Notes:
    - OpenXR 1.19 offers None / All Passes / Final Pass modes, with Final Pass on 6.2+.
    - Meta claims a 3–8% gain (vendor claim).
    - The Meta page `unity-multiview-render-regions` returns 404.
    - No GL equivalent of the per-view viewport/render-area extensions is exposed (G3-047).

- **G1-040** Unity's untethered-XR optimization guide (6.6) makes "Use the Vulkan API" its first step. It says Vulkan is more stable and faster than GLES in URP XR projects, and that many new OpenXR features are Vulkan-only. [C]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: Unity >= 6000.0; URP; untethered XR · Evidence: [doc]
  - Notes: Unity's own Won't Fix issues contradict the stability and performance claim (G1-C1 / G2-C7 / G3-C3, G1-C5).

- **G1-041** URP on-tile features have API requirements: [T]
  - Keeping data in tile memory requires a graphics API with native render passes. Without one, the frame still renders correctly but gets no bandwidth savings.
  - Memoryless intermediate textures for on-tile XR post-processing require Vulkan or Metal.
  - Any intermediate that is not memoryless forces an extra final blit.
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-post-processing.html (accessed 2026-09-24) · Applies to: URP 17.3+ (on-tile XR post-processing from 6.3; general on-tile post-processing from 6.5) · Evidence: [doc]
  - Notes:
    - On GLES the on-tile post-processing path cannot use memoryless intermediates.
    - G1 left open whether Unity treats GLES as native-render-pass capable. URP docs say "Native RenderPass" has no effect on OpenGL ES and that `BeginRenderPass` is emulated there (G2-022; resolved in GX-C4).

- **G1-042** URP depth input attachments are supported only on DirectX 12 and Vulkan. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html (accessed 2026-09-24) · Applies to: Unity 6000.6; URP 17 · Evidence: [doc]
  - Notes: How URP's `FRAMEBUFFER_INPUT_X_FLOAT` compiles on GLES is covered by G3-059 and GX-C6.

### 2.3 API-neutral features and checklists

- **G1-045** Meta's dynamic-resolution page (updated Aug 6, 2026) states no graphics-API restriction. [T]
  - It recommends URP 14.0.9+.
  - Settings: `enableDynamicResolution`, `minDynamicResolutionScale`, `maxDynamicResolutionScale`.
  - Dynamic resolution is a prerequisite for the highest GPU levels, such as GPU level 5 on Quest 3.
  - The page warns that when foveation is combined with dynamic resolution, Unity splits RenderObjects work into separate Vulkan render passes, which hurts performance.
  - Source: https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; URP 14.0.9+ · Evidence: [doc]
  - Notes: GLES support is not stated either way (KU-09). If dynamic resolution is Vulkan-only in practice, the highest GPU level is also out of reach on GLES.

- **G1-048** Unity's untethered-XR checklist (6.6) is API-neutral apart from its first step (use Vulkan): [T]
  - Use OpenXR, Render Graph and the Forward path.
  - Avoid geometry shaders.
  - Use MSAA; 2x is "a good balance". MSAA breaks on-tile / Tile-Only mode.
  - Disable depth priming (rely on LRZ), the Opaque and Depth textures, SSAO and HDR.
  - Use resolution scaling, the Meta Quest shader optimizations, and Adaptive Performance for OpenXR (6.6).
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html (accessed 2026-09-24) · Applies to: Unity >= 6000.0; URP 17 · Evidence: [doc]
  - Notes:
    - Several of these steps (depth priming off, no Opaque/Depth texture, Forward) are the same mitigations the community found for Vulkan slowdowns (G1-064). Apply them to both APIs before any A/B test.
    - The GLES-side reasons for the same settings are G2-017 to G2-020.
    - The MSAA 2x advice sits in the MSAA-cost conflict (G2-C3).

Also relevant to the decision, elsewhere in this dossier:
- The GLES-only CPU lever, Low Overhead Mode: G1-043 / G2-079 (§5.7).
- FFR on GLES through the Meta API: G1-044 / G2-062 / G3-053 (§7.3).

### 2.4 Older Meta guidance (context only)

- **G1-046** Meta's 2019 developer blog on Vulkan for mobile VR made these points: [T]
  - Vulkan on Quest required Quest OS v7.
  - Precompiled SPIR-V speeds up loading.
  - A wrong MSAA store/load/resolve setup can cost about 3 ms of GPU time.
  - Vulkan brings RenderDoc and per-frame timer queries.
  - A UE4 render-thread drop from 16 ms to 13 ms was the example (Unreal; context only).

  (pre-2023; stale)
  - Source: https://developers.meta.com/horizon/blog/vulkan-for-mobile-vr-rendering/ (accessed 2026-09-24; posted Aug 2, 2019) · Applies to: Quest 1 era · Evidence: [doc]
  - Notes:
    - The 3 ms MSAA store/load figure is the same failure class as UUM-93226, seven years earlier.
    - Tooling parity today: G1-074, GX-C9.

- **G1-047** Meta's Feb 2020 blog on experimental Vulkan in Unity said: [T][C]
  - Expect about a 10% improvement in CPU render cost, and no GPU improvement in nearly all cases.
  - Some apps may run slightly worse on Vulkan.
  - Known issues: depth resolve cost 1–3 ms of GPU time; MSAA added 150–250 MB of memory; graphics jobs were unstable.

  (pre-2023; stale)
  - Source: https://developers.meta.com/horizon/blog/vulkan-support-for-oculus-quest-in-unity-experimental/ (accessed 2026-09-24; posted Feb 4, 2020) · Applies to: Unity 2019.3-era Oculus plugin; Quest 1 · Evidence: [doc]
  - Notes:
    - This is the only Meta-published expected-gain figure for Unity Vulkan, and it concerns CPU.
    - OBD later addressed the 150–250 MB MSAA memory cost (G1-038).

### 2.5 UUM-93226: the Vulkan buffer-copy issue

- **G1-049 / G2-074 / G3-049** UUM-93226 summary. [T][C]
  - Title: "[Performance] Vulkan performing much worse than OpenGLES due to excessive buffer copies on Quest 2/3". Created Jan 17, 2025; not a regression; 21 votes.
  - Found in: 2022.3.56f1, 6000.0.33f1, 6000.1.0b2, 6000.2.0a1 and 6000.3.0a1 (G1, from the tracker's found-in field). G3's "2022.3.56f1, 6000.0.33f1 and 6000.0.0b2" is not a transcription error: the JSON description's "Reproducible on" line literally reads 2022.3.56f1, 6000.0.33f1, 6000.0.0b2 (round-1 audit; GX-C1). The two lists come from different fields.
  - Unity QA reproduced it on Quest 2 and Quest 3 test devices (the device OS field reads 12), with both the OpenXR and Oculus plugins. Switching between Multi-pass, Multiview and SPI made no difference.
  - QA notes say the problem also occurs on GLES, but Vulkan has lower FPS and much more stutter. RenderDoc captures are attached for both APIs. The tracker text gives no FPS numbers.
  - G2-074 draws a practical reading: buffer-update-heavy content (dynamic meshes, particles, UI) can be a legitimate reason a GLES build outperforms Vulkan on the same Unity version, so measure both before migrating. The mechanism evidence does not support reading "buffer copies" as vertex/constant-buffer updates: it points at render-target stores and resolves (G1-051, G1-054; GX-C2).
  - G3-049's practical advice: keep GLES as the A/B baseline when Vulkan with MSAA misbehaves.
  - Source: https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 (redirect target of https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3) ; https://issuetracker.unity.com/api/v1.0/issues/1364 ; https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (accessed 2026-09-24) · Applies to: Quest 2 (Adreno 650), Quest 3 (Adreno 740); Horizon OS on Android 12 at the time; Unity 2022.3–6000.3; Vulkan vs GLES; MSAA on · Evidence: [community]
  - Notes: G3-049 said the issue was "still open for 6000.0–6000.3 as of Dec 2025". The live tracker and its JSON show Closed – Won't Fix on every port (G1-050; resolved in GX-C1).

- **G1-050** UUM-93226 status history: [C]

  | When | Status |
  |---|---|
  | Feb 2025 | Active / Under Consideration (2022.3.X, 6000.0.X, 6000.1.X, 6000.2.X) |
  | By Dec 2025 | Third Party Issue |
  | Now | Closed – Won't Fix on 6.3.X, 6.2.X, 6.1.X, 6.0.X and 2022.3.X; ports last updated 2025-12-09; no fixed-in version on any stream |

  - Source: http://web.archive.org/web/20250215025510/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 ; http://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 ; https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 ; https://issuetracker.unity.com/api/v1.0/issues/1364 (accessed 2026-09-24) · Applies to: Unity 2022.3–6000.3 · Evidence: [community]
  - Notes:
    - The live page no longer displays a resolution note. The December 2025 note (G1-051) is the last stated rationale.
    - Synthesis check of the JSON: every port shows `state` 102 / `status` 4, `fixedInVersion` null, `resolutionNotes` null, `lastUpdatedUtc` 2025-12-09.
    - Round-1 audit re-check (2026-09-24): unchanged. 21 votes; the JSON also links a discussion thread, https://discussions.unity.com/t/1725076.

- **G1-051** Unity's Dec 2025 resolution note gave these causes and remedies: [T]
  - Vulkan's worse performance in the repro came from a Qualcomm visibility-stream bug. It appears in scenes with many meshes and was expected to be fixed in a future Meta OS release.
  - The extra buffer copies, with or without MSAA, were attributed to Qualcomm's cost of using Vulkan.
  - Recommended workaround: enable Optimize Buffer Discard (OpenXR or Oculus plugin).
  - Source: http://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; Vulkan · Evidence: [community]
  - Notes:
    - No Meta release note confirming the OS-side fix was found (KU-02).
    - Community posts from May–July 2026 say they saw no update (G1-058).
    - Round-2 gap-fill: still unconfirmed as of 2026-09-24 (GLES3-GF2-002).

- **GLES3-GF2-002** No public confirmation exists that the Qualcomm visibility-stream fix named in the UUM-93226 note has shipped in Horizon OS. [T][C]
  - The tracker JSON, re-read on 2026-09-24, is unchanged: every port shows state 102 / status 4 (Won't Fix), no fixed-in version, no resolution note, last update 2025-12-09, 21 votes.
  - The tracker's discussion thread (t/1725076) was created by the issue-tracker bot on 2026-07-02. Its only posts are three user requests for news (Feb 28 and Mar 2, 2025, carried over; May 22, 2026). There is no Unity or Meta staff reply.
  - Page 2 of the originating thread (1561926) has two 2026 user posts (May 22 and Jul 22) and no staff reply.
  - The Horizon developer release-notes index lists SDK and tool releases, not OS builds. A search found no OS note that mentions a visibility-stream or Vulkan binning fix.
  - Source: https://issuetracker.unity.com/api/v1.0/issues/1364 ; https://discussions.unity.com/t/1725076 ; https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926?page=2 ; https://developers.meta.com/horizon/release-notes/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; Vulkan · Evidence: [community]
  - Notes: The fix status can only be settled on device. Re-run a many-mesh 4x MSAA scene on both APIs on the current OS build, and record the OS build, App GPU time and the per-surface Store* stages (KU-02).

- **G1-052** A tracker QA note says that with MSAA disabled on the camera rig, the repro ran at about 30 fps and the stutter disappeared. The stutter is tied to the MSAA path. [C]
  - Source: https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 (accessed 2026-09-24) · Applies to: repro project; Quest 2, Quest 3 · Evidence: [community]
  - Notes:
    - The note does not say which API the 30 fps applies to; treat it as qualitative.
    - G3-049 reports the same note ("hovers around 30").

- **G1-053** Workarounds for UUM-93226, in order of authority: [T]
  1. Enable Optimize Buffer Discards (Unity tracker note, G1-051).
  2. Keep colour/depth store operations to a minimum via Render Graph (Unity staff, G1-055).
  3. Disable MSAA, or remove depth-texture and depth-priming use (community, G1-064).
  4. Wait for the Meta OS driver fix, whose delivery is unverified.
  - Source: https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 ; https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; Vulkan; MSAA · Evidence: [community]

### 2.6 Other GLES-vs-Vulkan comparisons on Quest

- **G1-054** The originating forum thread (1561926), first post Nov 29, 2024. Setup: Quest 2 and Quest 3, URP with 4x MSAA, Entities Graphics and Forward+, tested on Unity 2022 and Unity 6. [T]

  | | GLES | Vulkan |
  |---|---|---|
  | Per-frame overhead | baseline | 6+ ms extra |
  | Store ops per bin (RenderDoc) | one colour store, ~2–3 µs | eight alternating StoreColor/StoreDepthStencil, ~15 µs each |

  - Vulkan often dropped below 60 fps against a 72 fps target.
  - Without MSAA the gap shrank to 1–2 ms, with 4 stores per bin.
  - The poster says MSAA raised the bin count from about 16–18 to about 63–66.
  - Source: https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; URP; Unity 2022.3 / 6000.0 · Evidence: [community]
  - Notes:
    - This is a single project. The per-bin timings come from a RenderDoc tile timeline, and it is the most detailed public description of the mechanism.
    - The 63–66 bin count at 4x matches UUM-149765's 63 bins of 192x256 on Quest 3 (G2-039).

- **G1-055** Unity staff reply in the same thread (ThomasZeng, Dec 9, 2024): [T]
  - Unity's internal tests show Vulkan on par with GLES.
  - Vulkan needs the higher-level renderer to be set up well.
  - Developers should minimise colour/depth stores with the Render Graph API.
  - He pointed to Unity's untethered-XR optimisation page.
  - Source: https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (accessed 2026-09-24) · Applies to: URP 17 / Unity 6 · Evidence: [community]
  - Notes: No internal numbers were published. This contradicts the later tracker note blaming Qualcomm (G1-C2).

- **G1-056** Two more measurements from thread 1561926: [T]
  - **Built-in RP**, Quest 3, Unity 2022.3.61f1 (Apr 24, 2025): GPU utilisation was 25% on GLES and 44% on Vulkan, a 76% relative increase.
  - **Custom SRP**, Quest 3 (Dec 19, 2025 – Jan 12, 2026): RenderDoc's Tile Timeline showed an extra render-to-system-memory blit of about 1.5 ms. It appeared only on Vulkan, had no matching API command, and disappeared on GLES3 with identical code and MSAA off.
  - Source: https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (accessed 2026-09-24) · Applies to: Quest 3 · Evidence: [community]
  - Notes:
    - The BiRP result shows the gap is not URP-only.
    - The SRP result points at a driver- or compositor-side resolve, consistent with Unity attributing the copies to Qualcomm-side cost.

- **G1-057** Unity's QA repro for UUM-30269, "Significant performance difference between Vulkan and OpenGLES3 when built with ECS", on Quest 2: [T]
  - Unity 2022.2.9f1 with ECS 1.0.0-pre.44: 72 fps on GLES3, 50 fps on Vulkan.
  - Also reproduced on 2020.3.46f1, 2021.3.20f1 and 2023.1.0b5.
  - Closed Won't Fix because those streams are unsupported; ports closed 2026-05-06.
  - Source: https://issuetracker.unity.com/issues/6553/significant-performance-difference-between-vulkan-and-opengles3-when-built-with-ecs (redirect target of https://issuetracker.unity3d.com/issues/quest-2-significant-performance-difference-between-vulkan-and-opengles3-when-built-with-ecs) (accessed 2026-09-24) · Applies to: Quest 2 (Adreno 650, Android 10); Unity 2020.3–2023.1; ECS/Entities Graphics · Evidence: [community]
  - Notes:
    - This is the only Unity-QA-measured FPS pair found.
    - The 2023.2 alpha crashed when building with Vulkan.

- **G1-058** Thread 1561926, page 2 (posts of May 22, 2026 and Jul 22, 2026): [C]
  - Posters note that the tracker blamed Quest OS and then moved to Won't Fix, with no follow-up on whether a fix shipped.
  - They question why Unity and Meta push Vulkan while it underperforms.
  - Source: https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926?page=2 (accessed 2026-09-24) · Applies to: Unity 6.x; Quest 2, Quest 3 · Evidence: [community]
  - Notes: No numbers. It records current sentiment: as of July 2026 the issue is unresolved from users' point of view.

- **G1-059** Thread 938162 (Jan 20, 2024). Setup: Quest 3, Unity 2022.3.17f1, baked lighting, no post-processing, ASTC, described as GPU-bound. [T]

  | Refresh rate | Vulkan | GLES |
  |---|---|---|
  | 72 Hz | ~46 fps | ~63 fps |
  | 90 Hz | ~44 fps | ~60 fps |

  - Source: https://discussions.unity.com/t/performance-discrepancy-between-vulkan-and-opengl-with-unity-2022-3-17f1-on-meta-quest-3/938162 (accessed 2026-09-24) · Applies to: Quest 3; Unity 2022.3.17f1 · Evidence: [community]
  - Notes: The comparison is confounded. Vulkan ran with Buffer Discard, Symmetric Projection and FFR; GLES ran with Low Overhead Mode. A single-variable A/B is needed (G1-079).

- **G1-060** Unity issue discussion #6223 ("[XR][Perf][Quest] 2022.2 and trunk Vulkan vs GLES Perf disparity increased significantly"). Unity staff (N7RX_Y, Jul 20, 2023) acknowledged that Vulkan had been slower than GLES3 in many scenarios and said this was being addressed. The same staff member said the regression was inconsistent across projects and unlikely to come from a single change. [T]
  - Source: https://discussions.unity.com/t/xr-perf-quest-2022-2-and-trunk-vulkan-vs-gles-perf-disparity-increased-significantly-6223/1726043 (accessed 2026-09-24) · Applies to: Unity 2022.2 / 2023 trunk; Quest · Evidence: [community]
  - Notes: This is the only explicit Unity admission found. No follow-up closing it was found.

- **G1-061** Thread 1203082. Setup: Quest 2, Unity 2021.2, Oculus XR 3.0-preview, graphics jobs on. [T]
  - Result: 72 fps on GLES vs 24–36 fps on Vulkan. `EarlyUpdate.XRUpdate` took about 85% of the frame.
  - Cause found by a community member: Graphics PR #4488 changed the MSAA depth-copy / depth-prepass strategy, and PR #4705 then reverted it for GLES3 only.
  - Reported fixes:
    - Disable the depth texture and depth priming.
    - Or move from Deferred to Forward (2021.3.10f1, URP 12.1.7).
    - Or return to 2020.3.26f1 with URP 10.8.0, where a Unity-affiliated poster found Vulkan faster than GLES.

  (pre-2023; stale)
  - Source: https://discussions.unity.com/threads/horrible-performance-on-vulkan-with-simple-scene-quest-2.1203082/ (accessed 2026-09-24) · Applies to: Quest 2; Unity 2021.1–2021.3; URP 12 · Evidence: [community]
  - Notes: The same PR (#4488) is cited again in 2024 (G1-054). The URP depth-copy path is a recurring suspect on Vulkan specifically, because the fix was only applied to GLES3.

- **G1-062** Thread 1322298. Setup: Quest, Unity 2021.3.8, 4x MSAA, no depth/opaque textures, no post. [T]
  - Result: GLES App GPU time 4–6 ms vs Vulkan 15 ms.
  - Replies disagreed. One claimed Vulkan had never been faster on Quest and that Meta recommended GLES for production. Another said the two were roughly on par in 2020 LTS, and that AppSW needs Vulkan.

  (pre-2023; stale)
  - Source: https://discussions.unity.com/threads/serious-performance-regression-of-using-vulkan-vs-opengl-in-unity-2021-3-8-lts.1322298/ (accessed 2026-09-24) · Applies to: Quest 2; Unity 2021.3.8 · Evidence: [community]
  - Notes: The "Meta recommends GLES" advice is superseded by G1-028 (G1-C6).

- **G1-063** Two older Unity tracker entries now return "Page not found" on the migrated tracker, so their data is no longer verifiable: [C]
  - "[XR][Vulkan][Quest1] Apps have significantly higher memory consumption on Vulkan compared to GLES3".
  - "Vulkan performance is worse than OpenGLES3 and OpenGLES2".

  (pre-2023; stale)
  - Source: https://issuetracker.unity3d.com/issues/xr-vulkan-quest1-apps-have-significantly-higher-memory-consumption-on-vulkan-compared-to-gles3 ; https://issuetracker.unity3d.com/issues/vulkan-performance-is-worse-than-opengles3-and-opelgles2 (accessed 2026-09-24; both 404) · Applies to: Quest 1 era · Evidence: [community]
  - Notes: The Quest 1 memory issue matches Meta's 2020 note of +150–250 MB for MSAA (G1-047).

- **G1-064** Across 2021–2026 the community reports share a pattern: [T]
  - MSAA is on in almost every one.
  - Stores and resolves are the mechanism.
  - Removing depth copies, depth priming, Deferred or MSAA narrows the gap.
  - Source: https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 ; https://discussions.unity.com/threads/horrible-performance-on-vulkan-with-simple-scene-quest-2.1203082/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; URP / BiRP · Evidence: [community]
  - Notes:
    - This is a synthesis of G1-054 to G1-062. No published measurement shows Vulkan beating GLES on Quest in Unity, apart from the anecdotal 2020.3.26f1 report.
    - The one tracker table with MSAA off (UUM-149765, G2-039) shows Vulkan slightly faster (9.1 vs 9.7 ms) and GLES cheaper at 4x (13.0 vs 14.1 ms). That fits the MSAA-store pattern.

UUM-149765, the eye-buffer tracker table for Unity 6000.0–6000.7a, is in §3.4 (G2-039, G2-040, G2-041).

### 2.7 Hitching: Vulkan PSO creation vs GLES program link

- **G1-065** No published Quest-specific number compares Vulkan pipeline (PSO) creation hitches with GLES program compile/link hitches in Unity. [C]
  - Source: https://developers.meta.com/horizon/blog/vulkan-for-mobile-vr-rendering/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; Unity · Evidence: [doc]
  - Notes:
    - The only related vendor statement is Meta's 2019 blog: precompiled SPIR-V speeds up loading (pre-2023; stale).
    - On GLES the driver always compiles GLSL on device, because there are no shader binary formats (G1-008 / G3-008).
    - To measure: build development players for both APIs and run a scripted camera path through first-seen materials. Count frames above 1.5× the frame budget in OVR Metrics Tool, and attribute each spike with Perfetto / Unity Profiler markers (`Shader.CreateGPUProgram` vs Vulkan pipeline creation; G3-002). Repeat on a second launch to see caching. See KU-03.

- **G1-066** The UUM-93226 QA notes report more stutter on Vulkan than GLES in the repro. This is qualitative Unity-QA evidence that frame pacing, not just average FPS, is worse on Vulkan in MSAA-heavy scenes. [C]
  - Source: https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; Unity 2022.3–6000.0 · Evidence: [community]
  - Notes: The source does not say whether the stutter comes from pipeline creation or bandwidth, and no number is published. Measure frame-time variance (p95/p99 App GPU and CPU time) in OVR Metrics Tool on both APIs (KU-42).

- **G1-067** Thread 1561926 (post of Dec 11, 2024) reports that Vulkan was sometimes better than GLES for no clear reason, and that results differed between a clean install and later runs. [C]
  - Source: https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 · Evidence: [community]
  - Notes:
    - This hints at warm-up effects in the pipeline or shader cache (see G3-014: the EGL blob cache is dropped on every OS build change).
    - Benchmark both APIs on a second and later launch, and report first-launch hitches separately.

### 2.8 CPU-side levers and driver overhead

- **G1-025** "Graphics Jobs Mode" (Native / Legacy / Split) is available only when Graphics Jobs is enabled and Vulkan is the graphics API. [T][C]
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/vulkanapi-graphics-jobs-configuration.html (accessed 2026-09-24) · Applies to: Unity >= 6000.0; Android; Vulkan · Evidence: [doc]
  - Notes:
    - Unity documents per-device control of graphics jobs through the Vulkan Device Filtering Asset (Preferred Graphics Jobs Filter List).
    - Whether GLES builds on Quest get any graphics-jobs mode is not documented (KU-12).

- **G1-026** Meta's "Graphics Jobs in Unity" page (updated Nov 11, 2024) says: [T]
  - Legacy graphics jobs gave up to about 2 FPS in major projects.
  - The mode is available from Unity 2022.3.35f1, via `PlayerSettings.graphicsJobMode = GraphicsJobMode.Legacy` with Multithreaded Rendering on.
  - On Quest, the render thread translates commands into Vulkan commands.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ (accessed 2026-09-24) · Applies to: Unity 2022.3.35f1+ and 6000.x; Vulkan · Evidence: [doc]
  - Notes: The gain is available only on the Vulkan path (G1-025). It is a small, documented CPU-side advantage for Vulkan in main-thread-bound apps.

- **G1-068** No Qualcomm-published number was found for Adreno GLES vs Vulkan driver CPU overhead on XR2 or XR2 Gen 2. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes:
    - Available statements: Meta's page says Vulkan is lower-overhead, with no number; Meta's 2020 blog expected about 10% on CPU render cost (G1-047).
    - To measure: same scene and settings on each API, Multithreaded Rendering on. Compare render-thread time per frame (Unity Profiler `Gfx.*` markers, or Perfetto thread slices for UnityGfxDeviceW) and OVR Metrics "CPU App time" across a fixed draw-call sweep, for example 200, 500 and 1000 draws (KU-07).
    - The only Quest GLES state-change cost data is Meta's Quest 1 study (G2-065).

- **G1-069** Two documented CPU-side levers are API-specific. Neither has a published render-thread ms figure. [T]
  - Legacy graphics jobs: Vulkan-only, up to about 2 FPS (G1-025, G1-026).
  - Low Overhead Mode: GLES-only, in the deprecated Oculus plugin; it skips GLES validation (G1-043 / G2-079).
  - Source: https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/ ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/oculus-plugin.html (accessed 2026-09-24) · Applies to: Unity 2022.3.35f1+ (graphics jobs); OculusXR 4.x (Low Overhead Mode) · Evidence: [doc]

### 2.9 Evidence base per decision criterion

- **G1-070 / G2-056** **Feature access** is strong, doc-backed evidence, and decisive for Vulkan. The following are all documented as Vulkan-only: [T][C]
  - AppSW (G1-031) and ETFR (G1-034).
  - Subsampled Layout (G1-035 / G2-063 / G3-052).
  - Late Latching (G1-036).
  - Symmetric Projection (G1-037). G2-056 describes it as improving GPU performance through more common per-eye workloads.
  - Optimize Buffer Discards (G1-038) and MRR (G1-039).
  - Memoryless on-tile intermediates (G1-041), depth input attachments (G1-042), and the graphics-jobs modes (G1-025).

  The only documented GLES-only feature is Low Overhead Mode, in a deprecated plugin (G1-043 / G2-079). On GLES, depth discard and MSAA resolve at the end of the eye pass depend entirely on the engine's own invalidates (G2-014).
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-asw/ ; https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/ ; https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/features/metaquest.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; Unity 2022.3–6000.6; OculusXR 4.x; OpenXR 1.x · Evidence: [doc]
  - Notes: A project that needs AppSW has no GLES option. A GLES project also forgoes Meta's claimed 5–15% (Symmetric Projection) and 3–8% (MRR) GPU gains, which are vendor claims.

- **G1-071** **CPU overhead** is claimed but not measured. Meta says Vulkan has lower overhead and gave an expected 10% figure in 2020. No published Unity 6.x Quest render-thread comparison was found. [T]
  - Source: https://developers.meta.com/horizon/blog/vulkan-support-for-oculus-quest-in-unity-experimental/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 · Evidence: [doc]
  - Notes: The evidence grade is vendor claim only. Measure it as in G1-068.

- **G1-072** **GPU time** is measured, but only in community sources, and from 2021 to 2025 those consistently favour GLES in MSAA scenes. [T]
  - Quest 2: 72 vs 24–36 fps (2021.2); 4–6 vs 15 ms (2021.3.8); 72 vs 50 fps (2022.2.9, Unity QA).
  - Quest 3: 63 vs 46 fps (2022.3.17); 25% vs 44% GPU (2022.3.61 BiRP); 6+ ms extra (2022/6.0 URP); a 1.5 ms blit (custom SRP).

  Unity's position is parity when the renderer is set up well, and a driver bug otherwise.
  - Source: https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 ; https://issuetracker.unity.com/issues/6553/significant-performance-difference-between-vulkan-and-opengles3-when-built-with-ecs (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; Unity 2021.2–6000.0 · Evidence: [community] [verify on device]
  - Notes:
    - No published comparison uses Unity 6.1–6.6 with OBD, MRR, Symmetric Projection and on-tile post all enabled, which is the configuration Unity and Meta recommend. The gap may be smaller or gone there (KU-16).
    - UUM-149765 (6000.0–6000.7a, eye buffer only) adds a tracker-measured datapoint: 4x MSAA costs +3.3 ms on GLES vs +5.0 ms on Vulkan on Quest 3/3S (G2-039).

- **G1-073** **Hitching and frame pacing**: the evidence is qualitative only. Unity QA saw more stutter on Vulkan (G1-066), and there are no PSO-vs-link numbers (G1-065). [C]
  - Source: https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 · Evidence: [community]

- **G1-074** **Tooling** works on both APIs. [T]
  - Unity's UUM-93226 repro uses the Meta Developer Hub Metrics HUD on both Vulkan and GLES, and RenderDoc captures were taken on both.
  - The GLES driver exposes `GL_EXT_disjoint_timer_query` and `GL_KHR_debug`.
  - Source: https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 · Evidence: [community]
  - Notes:
    - Tooling is not a strong differentiator today, and Meta's 2019 claim that Vulkan has better tooling is stale.
    - Caveats on GLES: RenderDoc shader stats and API validation are Vulkan-only (G3-073). GL timer queries distort tiled timings (G2-034 / G3-068; GX-C9).

- **G1-075** **Stability and bugs**: the evidence conflicts. [C]
  - Unity docs call Vulkan more stable for URP XR (G1-040).
  - Unity closed two Vulkan-vs-GLES performance bugs as Won't Fix without fixes: UUM-93226 and UUM-30269.
  - Meta's 2020 blog flagged Vulkan graphics jobs as unstable (stale).
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html ; https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 (accessed 2026-09-24) · Applies to: Unity 2022.3–6000.6 · Evidence: [doc]
  - Notes: G1 compiled no GLES-specific crash or correctness list. G2 found several GLES XR bugs in Unity 6000.x, all closed Won't Fix: UUM-70930, UUM-109377 (G2-026), UUM-102876 (G2-057 / G3-046), OXPB-144 (G2-058) and UUM-102878 (G1-043 / G2-079). UUM-91896 was fixed (G2-027).

- **G1-076** **Future support**: the direction is clear, and there is no hard deadline. [C]
  - Meta calls GLES legacy, with no new features (G1-028).
  - Unity raised the GLES floor to 3.1 in 6.6 rather than removing GLES (G1-017).
  - The GLES-only Low Overhead Mode sits in the Oculus plugin, which is deprecated from 6.5 (G1-024 / G2-093).
  - The Quest 3 GLES driver was still updated in Jan 2026 (G1-004).
  - Source: https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ ; https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; Unity 6.x · Evidence: [doc]
  - Notes: The risk for GLES is feature starvation, not removal. No end date has been announced.

- **G1-077** **Coverage by device and Unity version**: [T][C]
  - Every published GLES-vs-Vulkan comparison found is on Quest 2 or Quest 3. None covers Quest 3S or Quest Pro.
  - Unity versions covered: 2021.2, 2021.3.8, 2022.2.9, 2022.3.17, 2022.3.56, 2022.3.61 and 6000.0.33.
  - Nothing was found for 6000.1–6000.6, where MRR, on-tile post-processing and the Quest shader optimizations land.
  - Source: https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 ; https://discussions.unity.com/t/performance-discrepancy-between-vulkan-and-opengl-with-unity-2022-3-17f1-on-meta-quest-3/938162 (accessed 2026-09-24) · Applies to: evidence coverage · Evidence: [community]
  - Notes: At synthesis, UUM-149765 (G2-039, G2-040) partly fills this gap. It covers eye-buffer GPU time for 4x MSAA vs off on 6000.0.81f1, 6000.3.21f1, 6000.5.7f1, 6000.6.0b7 and 6000.7.0a4, including a Quest 3S. It still does not test the full recommended Vulkan configuration (MRR, on-tile post).

- **G1-078** Decision rule supported by the evidence: [T][C]
  - **Default to Vulkan** when the project needs any Vulkan-only feature (G1-070 / G2-056), or targets Unity 6.1+ with MRR and on-tile post.
  - **Consider GLES** only for a GPU-bound, MSAA-heavy project that uses none of those features. Keep it only if an on-device A/B test with identical settings shows a GLES win after OBD and store minimisation are applied on Vulkan.
  - Source: https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ ; https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23 ; https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; Unity 2022.3–6000.6 · Evidence: [doc]
  - Notes:
    - This combines vendor guidance with the documented workarounds.
    - Record the Horizon OS version and GLES driver string (G2-082) in every A/B, because the claimed Qualcomm fix is delivered through the OS (G1-051).
    - Also weigh the shelf-life risk of GLES on Unity 6.5+ (G1-024 / G2-093).

- **G1-079** A valid A/B test needs a single variable: [T]
  - Disable Auto Graphics API and list only one API per build (G1-016).
  - Keep MSAA, the renderer (Forward), depth priming, the Opaque/Depth textures and the ES shader level identical. The shader level matters because of the MAX_VISIBLE_LIGHTS 16/32 difference (G1-020).
  - Toggle Vulkan-only features (OBD, Symmetric Projection, FFR subsampling) in a separate step.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html ; https://discussions.unity.com/t/performance-discrepancy-between-vulkan-and-opengl-with-unity-2022-3-17f1-on-meta-quest-3/938162 (accessed 2026-09-24) · Applies to: Unity 2022.3–6000.6 · Evidence: [doc]
  - Notes:
    - Several community comparisons changed several variables at once (G1-059). A community member in 1561926 also advised keeping only one API in the list during testing.
    - Lock clocks while comparing (`debug.oculus.gpuLevel` / `cpuLevel`, G2-010).
    - Use a non-development build or filter GL error spam (G2-057 / G3-046).
    - Test cold and warm shader caches separately (G3-014).

- **G1-080** Meta's per-frame GPU-cost measurement guidance and RenderDoc Meta Fork pages sit in the same "Performance and optimization" section as the GLES/Vulkan page. Use them to capture the tile-timeline store/resolve evidence that explains a Vulkan gap. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ (sidebar: "Accurately measure an app's per-frame GPU cost", "Using RenderDoc Meta fork to optimize your app") (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes:
    - The community mechanism evidence (G1-054, G1-056) came from the RenderDoc tile timeline.
    - The content of those pages is covered in §8 (G3-073 to G3-079).

### 2.10 Measured vs claimed at a glance

Every row restates findings above; no new claims.

| Criterion | What exists | Grade | IDs |
|---|---|---|---|
| Feature access | AppSW, ETFR, Subsampled Layout, Late Latching, Symmetric Projection, OBD, MRR, memoryless on-tile intermediates, depth input attachments and graphics-jobs modes are Vulkan-only. Low Overhead Mode is GLES-only (deprecated plugin). | [doc], decisive | G1-070 / G2-056, G1-031 to G1-042, G1-043 / G2-079 |
| Vulkan-feature GPU gains | Symmetric Projection 5–15%, MRR 3–8%, AppSW "up to 70%" more compute budget | vendor claim, no independent measurement | G1-032, G1-037, G1-039 |
| CPU / driver overhead | "Lower overhead" with no number; ~10% CPU render cost (2020); Legacy graphics jobs ~2 FPS | vendor claim only | G1-028, G1-047, G1-026, G1-068, G1-071 |
| GPU time, MSAA scenes, 2021–2025 | GLES faster in every published case | [community] measurements, confounded in places | G1-054 to G1-062, G1-072 |
| GPU time, eye buffer, Unity 6000.0–6000.7a | 4x MSAA: +3.3 ms GLES vs +5.0 ms Vulkan (Quest 3/3S). MSAA off: Vulkan 9.1 vs GLES 9.7 ms. Quest 2: within ~1 ms | [measured] tracker table, internally inconsistent (G2-C9) | G2-039, G2-040, G2-041 |
| Hitching / pacing | "More stutter on Vulkan" (Unity QA, qualitative); no PSO-vs-link numbers; no GLES compile ms | qualitative | G1-065, G1-066, G1-073, G3-001 |
| Tooling | Both APIs are capturable; shader stats and validation are Vulkan-only in RenderDoc | [doc] / [community] | G1-074, G3-073, G3-080 |
| Stability | Doc says Vulkan is more stable; tracker Won't Fix entries on both APIs | conflicting | G1-075, G1-C5 |
| Future support | GLES legacy; OculusXR deprecated in 6.5; GLES floor 3.1 in 6.6; driver still updated in 2026 | [doc] / [measured] | G1-076, G1-024 / G2-093, G1-004 |

## 3. Tile-friendly rendering on GLES: load/store, invalidate, FBO switches, MSAA on tile

Diagnosis first:
- **Missing clears or invalidates.** On the eye-buffer surface, any non-zero `LoadColor` / `LoadDepthStencil` stage, or any `StoreDepthStencil` stage, in ovrgpuprofiler means a clear or invalidate is missing (G2-009).
- **Pass splits.** Every extra surface in the trace is at least one full-resolution store (G2-011).
- **Mode.** An eye buffer in Direct (Mode 0) or SwBinning (Mode 2) where HwBinning is expected is a red flag (G3-080, G2-085).

### 3.1 GMEM, bins, load and store on Adreno

- **G2-001** GMEM sizes: [T]
  - Adreno 650 (Quest 2): 1 MB of tile memory.
  - Adreno 740 (Quest 3/3S): about 2 MB.

  At equal per-pixel format, Quest 3/3S bins cover about twice the pixels, so there are fewer bins and less per-bin overhead.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES and Vulkan · Evidence: [doc]

- **G2-002** Bin-size arithmetic, from Meta's worked example on XR2 (Quest 2): [T]
  - Setup: multiview, 4x MSAA, RGBA8 colour, D24S8.
  - Per pixel: (4 B colour + 4 B depth) × 4 samples = 32 B, with both eye views in the same tile.
  - Result: 96x176 tiles, because 96 × 176 × 2 views × 32 B ≈ 1 MB.

  The driver picks the tile size that maximises pixels per tile within GMEM. Any change to the per-pixel footprint (MSAA, extra MRTs, depth format) therefore changes the bin count.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2 (the worked example); the same method applies to Quest 3/3S with ~2 MB · Evidence: [doc]
  - Notes: For Quest 3, UUM-149765 reports 63 bins of 192x256 for a Unity 6 eye buffer at 4x MSAA (G2-039).

- **G2-003** Levers that cut the bin count: lower render resolution, fewer MSAA samples, fewer simultaneous render targets. Qualcomm also lists VRS. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("Bin Minimization") (accessed 2026-09-24) · Applies to: Adreno generic (phone guide); Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]

- **G2-004** Each pass runs three steps per bin: [T]
  1. Load ("unresolve") the previous contents from system memory into GMEM.
  2. Render.
  3. Store ("resolve") GMEM back to memory.

  On GLES, skip step 1 by calling `glClear` or `glInvalidateFramebuffer` after binding the FBO and before the first draw. Meta says clearing and invalidating differ very little on Qualcomm, because the GPU hides the clear cost.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES · Evidence: [doc]
  - Notes: A partial clear is a trap; see G2-005 and G2-C4.

- **G2-005** A partial clear still forces a load. [T]
  - In Qualcomm's sample, a D24S8 FBO cleared with only COLOR|DEPTH (stencil left uncleared) ran at 25.15 ms, against 18.24 ms with all three bits cleared: about 37% slower.
  - Diagnosis on Quest: whenever the format has stencil, check that the eye-buffer clear covers depth *and* stencil.
  - Source: https://github.com/quic/adreno-gpu-opengl-es-code-sample-framework (sample "avoid_gmem_loads", README) (accessed 2026-09-24) · Applies to: Adreno (phone, unspecified model); Quest by analogy · Evidence: [measured] [verify on device]
  - Notes: The README warns that newer drivers may optimise this away. The sample is undated, and its Adreno 5xx references suggest pre-2023 data (pre-2023; stale).
  - Round-2 spot-check: the README gives 18.24 ms without and 25.15 ms with GMEM loads ("a 37% difference"). The sample's `Scene.cpp` toggles between `glClear(COLOR|DEPTH|STENCIL)` and `glClear(COLOR|DEPTH)` on a `GL_DEPTH24_STENCIL8` attachment. Confirmed. The GitHub API now serves the sources from the `SnapdragonGameStudios` organisation (https://github.com/SnapdragonGameStudios/adreno-gpu-opengl-es-code-sample-framework); the `quic` URL still resolves.

- **G2-006** To avoid the store, invalidate the attachments you do not need (almost always depth/stencil) at the end of the pass. [T]
  - On GLES the invalidate only takes effect if it is issued before the driver executes the pass, that is, before any `glFlush`.
  - Anything that flushes implicitly also defeats it. Meta's example is a GL timer query: after one, the invalidate is ignored and depth is written to RAM.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES · Evidence: [doc]
  - Notes: How this squares with Qualcomm's advice to issue timer queries inside a render pass is covered in GX-C9.

- **G2-007** Storing an unneeded depth/stencil attachment cost 18.33 ms, against 11.93 ms without it (about 50% more), in Qualcomm's "reduce_gmem_stores" sample. [T]
  - Source: https://github.com/quic/adreno-gpu-opengl-es-code-sample-framework (sample "reduce_gmem_stores") (accessed 2026-09-24) · Applies to: Adreno phone; Quest by analogy · Evidence: [measured] [verify on device]
  - Notes: Same driver-optimisation caveat as G2-005.
  - Round-2 spot-check: the `reduce_gmem_stores` README gives 18.33 ms with and 11.93 ms without the depth/stencil store, which it calls "a 50% difference". Confirmed.

- **G2-008 / G3-060** Qualcomm's preferred order of invalidation tools on GLES. The general rule is to invalidate as early as possible. [T]
  1. `glInvalidateFramebuffer`: no GMEM load or store until the next API call on that FBO.
  2. `glInvalidateSubFramebuffer`: the same, for a sub-rectangle.
  3. `glClear`: minimises loads, writing the clear value as needed.
  4. `EXT_discard_framebuffer` (`glDiscardFramebufferEXT`): the pre-ES3 equivalent, exposed on both headsets.

  In a render-stage trace, LoadColor/LoadDS stages on eye buffers, or StoreDS where depth is not needed later, point to a missing clear or invalidate.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://registry.khronos.org/OpenGL/extensions/EXT/EXT_discard_framebuffer.txt ; https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES 3.x · Evidence: [doc]
  - Notes: G3-060 flagged that Unity does not document how its RenderPass load/store actions become GL invalidates. [verify on device] Look for `glInvalidateFramebuffer` calls in a RenderDoc capture's API log (KU-17).

- **GLES3-GF2-003** Unity's GLES backend does emit `glInvalidateFramebuffer` on Quest. A RenderDoc capture posted on Unity Discussions shows two calls per frame in an empty URP scene. [T]
  - Setup: Quest 2; Unity 2021.3.31f1 and 2022.3.15f1; URP with the Oculus XR plugin and XR Interaction Toolkit; GLES; one camera with a solid-colour clear and no geometry.
  - RenderDoc showed the two calls (EIDs 503 and 517) taking over 90% of the frame's GPU time. The poster, and a second non-staff user, read the second call as marking depth/stencil transient while colour is stored. No Unity staff replied.
  - Source: https://discussions.unity.com/t/multiple-frame-buffer-invalidations-urp/935652 (posts of Dec 14 and 16, 2023) (accessed 2026-09-24) · Applies to: Quest 2; Unity 2021.3–2022.3; URP 12–14; OculusXR; GLES · Evidence: [community] [verify on device]
  - Notes:
    - This answers part of KU-17: Unity uses `glInvalidateFramebuffer`, not only `glClear`, for at least the final eye-buffer pass. It does not show which URP load/store actions map to which call, or where the call sits relative to the flush.
    - Do not read the 90% as the cost of the invalidate itself. On a tiler, GL timestamp attribution tends to charge the deferred bin execution and resolve to whichever event ends the pass (GX-C9). The ovrgpuprofiler per-surface Store*/Load* stages (G2-009) are the right way to attribute that time.
    - It is unknown whether Unity 6.x on GLES keeps the same pattern, including with Render Graph (KU-13).

- **G2-009** Reading ovrgpuprofiler per-surface stages. Meta's GLES example line, in its verbatim format: [T][C]

  `Surface 1 | 1216x1344 | color 32bit, depth 24bit, stencil 8 bit, MSAA 2 | 28 320x192 bins | 10.62 ms | 171 stages : Binning : 0.305ms LoadColor : 0.71ms Render : 2.926ms StoreColor : 1.525ms Preempt : 2.964ms LoadDepthStencil : 0.828ms StoreDepthStencil : 0.871ms`

  - Meta's own text attributes "1.5ms" of waste to LoadColor + StoreDepthStencil (0.71 + 0.871 ms). If LoadDepthStencil (0.828 ms) is also counted as avoidable, which the rule below implies, the total is about 2.4 ms of 10.62 ms. The 2.4 ms figure is this dossier's arithmetic, not Meta's.
  - Rule: on the main eye-buffer surface, any non-zero Load* stage, or any StoreDepthStencil stage, is a missing clear or invalidate.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES and Vulkan · Evidence: [doc]
  - Notes:
    - The device is not stated. 1216x1344 matches the original Quest's default eye buffer, so treat the absolute timings as illustrative.
    - The Preempt stage is discussed in G3-069.

- **G2-011** Every extra render pass (an FBO bind/unbind cycle) adds a fixed store cost proportional to resolution, even when the pass holds a single draw. Budget each intermediate pass (post, copy, UI to RT) as at least one full-resolution store. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]

- **G2-012** Triangle size matters on a binner. [T]
  - Qualcomm's guideline: at least 4 px of screen area, and not much larger than a bin. A triangle that spans several bins is rasterised once per bin, with no clipping at bin edges.
  - Meta's older Quest 1 measurement also shows polygons spanning several tiles adding GPU cost.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]

### 3.2 How Unity/URP settings map to load/store on GLES

- **G2-013** Unity's load and store actions. [T]
  - `RenderBufferLoadAction`:
    - Load: preserves contents; expensive on tilers.
    - Clear: documented as working only with the RenderPass API.
    - DontCare: no load into tile memory.
  - `RenderBufferStoreAction`:
    - Store: stores the unresolved MSAA surface when MSAA is on.
    - Resolve.
    - StoreAndResolve.
    - DontCare: skips the write-out.

  Unity says mobile APIs (OpenGL ES, Metal) honour these actions, but on some platforms they "might be ignored at runtime".
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.RenderBufferLoadAction.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.RenderBufferStoreAction.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6000.x; GLES · Evidence: [doc]

- **G2-014** Unity does not always turn DontCare/Discard into `glInvalidateFramebuffer` on GLES. [T]
  - UUM-45041 reports GLES skipping `glInvalidateFramebuffer` in some render passes with Blit Type Never.
  - It reproduced on 2021.3.29f1, 2022.3.6f1, 2023.1 and 2023.2, on PowerVR and Mali, but not on Adreno 610. It was closed Won't Fix.
  - On Quest, confirm with the ovrgpuprofiler Load*/Store* stages (G2-009) rather than trusting the URP setting.
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-45041 (accessed 2026-09-24) · Applies to: Unity 2021.3–2023.2 (possibly later); GLES; Adreno status unknown · Evidence: [community] [verify on device]
  - Notes: See G2-C2.

- **G2-015** `SystemInfo.supportsStoreAndResolveAction` reports whether StoreAndResolve really stores the MSAA surface. When it is false, StoreAndResolve silently becomes Resolve. Log it once on device before designing any pass that reloads MSAA colour. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsStoreAndResolveAction.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6000.x; GLES · Evidence: [doc] [verify on device]

- **G2-016** The URP asset's **Store Actions** setting has three options: [T]
  - Auto: Discard, but falls back to Store when injected passes are detected.
  - Discard.
  - Store.

  It exists in URP 12.1, 14 and 17; in 17 it is visible only with "Show All Advanced Properties". Prefer **Discard** for Quest. A single renderer feature that injects a pass can silently flip Auto to Store, which costs a full-resolution store and reload per pass.
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/universalrp-asset.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 12, URP 14, URP 17 · Evidence: [doc]

- **G2-017** On mobile platforms without StoreAndResolve support, URP 12.1, 14 and 17 all note that enabling the **Opaque Texture** makes Unity ignore MSAA at runtime. On Quest GLES this can silently drop MSAA: aliasing appears, and the GPU cost changes too. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/universalrp-asset.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/universalrp-asset.html (Opaque Texture note) (accessed 2026-09-24) · Applies to: URP 12, URP 14, URP 17; GLES when `supportsStoreAndResolveAction == false` · Evidence: [doc] [verify on device]

- **G2-018** The Opaque Texture works like a grab pass: a mid-frame copy of the colour target, which ends the tile pass (store) and reloads it afterwards. Opaque Downsampling (None / 2x Bilinear / 4x Box / 4x Bilinear) shrinks only the copy destination, not the store and reload of the main target. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/universalrp-asset.html (accessed 2026-09-24) · Applies to: URP 12, URP 14, URP 17 · Evidence: [doc]

- **G2-019** Depth Texture Mode **After Transparents** is documented to save significant bandwidth on mobile. **After Opaques** inserts a Copy Depth pass between opaques and transparents: the colour buffer is stored and then reloaded, including MSAA data when MSAA is on. On Quest, use After Transparents or no depth texture. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html ; https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: URP 14+ (the option is not documented on the URP 12 renderer page) · Evidence: [doc]

- **G2-020** Depth Priming is not supported with MSAA, or at runtime on mobile TBDR GPUs. "Auto" is unsupported on Android, and "Forced" adds a depth prepass with memory and performance cost. Leave it **Disabled** on Quest. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: URP 14+ · Evidence: [doc]
  - Notes: The same advice appears in Unity's untethered-XR checklist (G1-048). The community traced Vulkan slowdowns to URP depth-copy/prepass paths (G1-061).

- **G2-021** URP once forced a depth prepass on GLES3 (UUM-8381). [T]
  - The fix shipped in 2021.3.9f1, 2022.1.14f1, 2022.2.0b6 and 2023.1.0a5.
  - On an older 2021.3 patch, a "DepthPrepass" in the Frame Debugger that you did not request is this bug: a whole extra geometry pass.
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-8381 (accessed 2026-09-24) · Applies to: Unity 2021.3 before 9f1; GLES · Evidence: [community]

- **G2-022** URP "Native RenderPass" has no effect on OpenGL ES (stated in URP 14 and 17). [T]
  - `ScriptableRenderContext` / `CommandBuffer.BeginRenderPass` is native only on Vulkan and Metal.
  - On other backends Unity emulates it with legacy `SetRenderTarget` calls, and with texel fetches for input attachments.
  - On GLES there is therefore no subpass merging, and each "subpass" read becomes a real render-target switch plus a texture read.
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/urp-universal-renderer.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.ScriptableRenderContext.BeginRenderPass.html (accessed 2026-09-24) · Applies to: URP 14+; GLES · Evidence: [doc]
  - Notes: This answers the question G1-041 left open (GX-C4). It also bears on GX-C6, whether depth input attachments on GLES are emulated by texel fetch or compiled to framebuffer fetch.

- **G2-023** The URP 17 Render Graph docs describe merging passes into one native render pass on TBDR GPUs. [T]
  - Because GLES `BeginRenderPass` is emulated (G2-022), the GLES output is assumed to be the equivalent sequence of FBO binds, with load/store derived from the graph.
  - The NativePassCompiler source sets load/store and StoreAndResolve per attachment.
  - No Unity statement specific to merging on GLES was found.
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/render-graph-introduction.html ; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/NativePassCompiler.cs (accessed 2026-09-24) · Applies to: URP 17 (Unity >= 6000.0); GLES · Evidence: [doc] [verify on device]
  - Notes: Verify with the Render Graph Viewer (merge bars) plus the ovrgpuprofiler surface count (KU-13).

- **G2-024** "Intermediate Texture = Always" forces rendering through an intermediate RT, which Unity says can have a significant performance impact. "Auto" relies on `ScriptableRenderPass.ConfigureInput`. On GLES on Quest, an intermediate texture also removes compositor FFR from the main pass (G2-061). [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html (accessed 2026-09-24) · Applies to: URP 14+ · Evidence: [doc]

- **G2-025** Three RT-level hints. Use them to prove that DontCare/Discard is safe before shipping. [T]
  - `RenderTexture.DiscardContents(color, depth)`: tells the driver the contents are unused. It covers both buffers by default.
  - `RenderTexture.MarkRestoreExpected`: a "restore" means rendering into an RT without a prior clear or discard, which Unity calls costly on mobile.
  - `LoadStoreActionDebugModeSettings`: highlights undefined areas as "INVALIDATED". Game view and development builds only.
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture.DiscardContents.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture.MarkRestoreExpected.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.LoadStoreActionDebugModeSettings.html (accessed 2026-09-24) · Applies to: DiscardContents and MarkRestoreExpected on all versions; the LoadStore debug mode is documented for 2022.3 and 6000.0–6000.6, not 2021.3 · Evidence: [doc]
  - Notes: The MarkRestoreExpected page still mentions a legacy "mobile graphics emulation mode", and the DiscardContents page mentions Xbox 360, so both carry old text.

- **G2-026** Known GLES XR correctness bugs on the passes that already cost a store and reload. Avoiding those passes serves throughput and stability together. [T]

  | Issue | Symptom | Configuration | Status |
  |---|---|---|---|
  | UUM-70930 | Opaque Texture "double vision" | GLES XR; 2021.3 / 2022.3 / 6000.0 | Won't Fix |
  | UUM-109377 | Transparents disappear | FullScreenRenderPass + Multiview/SPI + MSAA on GLES; Quest 3/3S; 6000.0.51f1–6000.2 | Won't Fix across 6000.0–6000.5 |

  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-70930 ; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-109377 (accessed 2026-09-24) · Applies to: the versions listed; GLES; Quest 2, Quest 3/3S · Evidence: [community]

- **G2-027** UUM-91896: render-pass validation fails with "Attachment AA sample counts must match" on GLES multipass when camera HDR/MSAA settings differ from the URP asset. It was seen in 6000.0.23f1 and later, and fixed in the 6000.0 / 6000.1 / 6000.2 ports. Keep per-camera MSAA/HDR consistent with the asset. [C]
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-91896 (accessed 2026-09-24) · Applies to: Unity 6000.0.23f1+ until the fix; GLES · Evidence: [community]

### 3.3 Mid-frame readbacks, FBO switches, flushes and queries

- **G2-028** While an on-tile MSAA texture is attached, any of the following can trigger an implicit resolve that discards the multisample data: [T][C]
  - Binding another FBO.
  - `glReadPixels` or `glCopyTex[Sub]Image`.
  - `Tex*Image` to the attached level.
  - `GenerateMipmap`.
  - `glFlush` or `glFinish`.
  - Drawing with the attached texture bound for sampling.

  Rendering that continues afterwards starts from the resolved single-sample image. Anti-aliasing quality is lost and the pass is paid for twice.
  - Source: https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture.txt (accessed 2026-09-24) · Applies to: GLES with EXT_multisampled_render_to_texture (Quest 2, Quest 3/3S expose it) · Evidence: [doc]

- **G2-029** On QCOM tiling, `glFlush` / `glFinish` and FBO rebinds implicitly end the tiled region, and Meta's GLES guidance requires invalidates before the flush (G2-006). [T][C]
  - Treat any mid-pass `glFlush`, fence with flush, timer query or readback as a pass split: everything is stored, then reloaded.
  - Engine-side triggers to audit on GLES:
    - `CommandBuffer.RequestAsyncReadback` / `ReadPixels`.
    - `Texture2D.ReadPixels`.
    - `GraphicsFence`.
    - Plugin render events that call `glFlush`.
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_tiled_rendering.txt ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES · Evidence: [doc] [verify on device]
  - Notes: The list of Unity APIs that map to a GL flush is inferred; Unity does not document the GL calls.

- **G2-031** On Adreno, upscaling or copying with `glBlitFramebuffer` is faster than a full-screen quad. Unity picks the copy path internally (`CommandBuffer.Blit` vs `Blitter`), and no statement was found on which GL call it uses on GLES. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Adreno GLES · Evidence: [doc] [verify on device]

- **G2-033** Occlusion queries on a binned surface are expensive. [T]
  - Qualcomm saw 20–40% extra command-processor overhead ("% CP Busy"), against 4–6% when the queries run in direct mode.
  - Its recipe is to issue all queries in one batch after a flush: opaque → translucent → flush → queries → switch FBO.
  - This matters only if native code or a plugin issues GL occlusion queries.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("Queries") (accessed 2026-09-24) · Applies to: Adreno GLES · Evidence: [doc]
  - Notes: Under multiview, occlusion query results fall between the per-view maximum and the sum (G2-049).

Fences, compute-dispatch flushes and timer queries are covered in §5.6 (G2-030, G2-080) and §8.3 (G2-034 / G3-068). Framebuffer fetch is covered in §7.2 (G2-032).

### 3.4 MSAA on tile under GLES

- **G1-007 / G1-010 / G2-035** Extension availability and the MSAA ceiling, from device reports. [T]

  | | Quest 2 (report 6387) | Quest 3 (report 8023) |
  |---|---|---|
  | GPU | Adreno 650 | Adreno 740 |
  | Driver | `OpenGL ES 3.2 V@0690.0` (build date 12/13/22) | `V@0837.0.7` (01/12/26) |
  | Android | 12 | 14 |

  - Both expose `GL_EXT_multisampled_render_to_texture`, `GL_EXT_multisampled_render_to_texture2` and `GL_OVR_multiview_multisampled_render_to_texture`.
  - Both also expose `GL_OVR_multiview` and `GL_OVR_multiview2`. Unity's Multiview mode therefore has a native GLES path (G1-010).
  - GL_MAX_SAMPLES = 4 on both, so **4x is the MSAA ceiling on GLES**; 8x is not available.
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3. Quest 3S shares the Adreno 740, and UUM-149765 lists the same V@0837.0.7 GLES driver on a Quest 3S · Evidence: [measured]
  - Notes:
    - G1-007: Meta's Optimize Buffer Discards text mentions 8x MSAA only in general terms; on GLES, 4x is the hard limit.
    - These are user-submitted capability dumps, so the driver on a given headset depends on its OS build. Query at runtime.

- **G2-036 / G3-048** `EXT_multisampled_render_to_texture` renders into a single-sample texture with N-sample storage on tile. [T]
  - Setup: `glFramebufferTexture2DMultisampleEXT` / `glRenderbufferStorageMultisampleEXT`.
  - At store, samples are resolved on chip and the multisample data is discarded.
  - Memory traffic is the same as without MSAA. The cost moves to GMEM footprint (more bins) and to shading/ROP work.
  - `_2` extends this to depth and other attachments. The OVR multiview variant does the same for stereo arrays.
  - `glReadPixels` or `glBlitFramebuffer` on such a framebuffer forces an implicit flush and resolve mid-frame.

  Meta states the same about the Quest GLES path: textures stay non-MSAA even with an MSAA framebuffer, and the hardware resolve sits in the store path.
  - Source: https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture.txt ; https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture2.txt ; https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview_multisampled_render_to_texture.txt ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES · Evidence: [doc]
  - Notes:
    - Unity does not document whether its GLES MSAA eye buffers use these extensions. [verify on device] Look for `glFramebufferTexture2DMultisampleEXT` / `glFramebufferTextureMultisampleMultiviewOVR` in a RenderDoc GL capture's API log (KU-18).
    - A mid-frame copy of the colour buffer, such as the Opaque Texture, costs an extra flush.

- **G2-037** `EXT_multisampled_render_to_texture2` extends on-tile MSAA to any attachment point, including depth/stencil. [T]
  - A multisampled depth/stencil **texture** attachment is discarded at resolve, which is equivalent to `glInvalidateFramebuffer`.
  - A depth/stencil **renderbuffer** is not.
  - The spec warns that client reads (ReadPixels, CopyTexImage, BlitFramebuffer) before later rendering may downsample early.
  - Source: https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture2.txt (rev 4, 2025-10-22) (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES · Evidence: [doc]

- **G2-038** `OVR_multiview_multisampled_render_to_texture` is the one-pass stereo + on-tile MSAA path. It attaches an N-sample, multi-view, on-tile target to a `TEXTURE_2D_ARRAY` with `glFramebufferTextureMultisampleMultiviewOVR(target, attachment, texture, level, samples, baseViewIndex, numViews)`. The spec notes that a mid-frame resolve on a tiler may lose the samples (G2-028). [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview_multisampled_render_to_texture.txt (rev 0.4, 2015) (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES + multiview · Evidence: [doc]

- **G2-039** Measured 4x MSAA cost on the eye-buffer surface, Quest 3/3S, Unity 6 (UUM-149765). [T]
  - Setup: ovrgpuprofiler; gpuLevel/cpuLevel 3 plus `debug.oculus.sysPropDebug 1` and `debug.oculus.headlock 1`; "Optimized Buffer Discards" enabled (the report does not say which XR plugin; an earlier draft wrongly attributed it to OculusXR); 63 bins of 192x256 (the report states this layout for the 4x runs).
  - Unity versions: 6000.0.81f1, 6000.3.21f1, 6000.5.7f1, 6000.6.0b7 and 6000.7.0a4.

  | Config | Total | Binning | Render | StoreColor |
  |---|---|---|---|---|
  | GLES, MSAA off | 9.7 ms | 4.5 | 4.2 | 0.04 |
  | GLES, 4x | 13.0 ms | 5.1 | 6.3 | 0.15 |
  | Vulkan, MSAA off | 9.1 ms | 4.5 | 3.7 | 0.18 |
  | Vulkan, 4x | 14.1 ms | 5.1 | 7.0 | 0.45 |

  4x MSAA added +3.3 ms on GLES and +5.0 ms on Vulkan. At 72 Hz (13.9 ms), 4x alone takes about a quarter of the frame in this scene.
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 ("[Vulkan][XR] Vulkan MSAA costs more GPU time than GLES3 on Meta Quest devices"; Open; updated 2026-09-24) (accessed 2026-09-24) · Applies to: Quest 3/3S (Adreno 740, GLES driver V@0837.0.7); Unity 6000.0–6000.7a · Evidence: [measured]
  - Notes:
    - The report is internally inconsistent: its notes give Quest 3 GLES "~12 ms / ~15 ms" (off / 4x) and Vulkan "~11 / ~16", which differ from the table (G2-C9). Use the deltas.
    - The report also says 6000.0.0f1 was slower in every configuration.
    - With MSAA off, Vulkan is slightly faster than GLES here (9.1 vs 9.7 ms). That datapoint is added to G1-C4.
    - Devices listed in the report: Quest 3S (Android 14, firmware v2.6; its CPU field reads "Google Tensor G2", a data-entry error), Quest 3 (Android 14, firmware 2.4.1031) and Quest 2 (Android 14, firmware 2.1.1034). The Quest 3S Vulkan driver is 512.837.7 (Vulkan 1.3.295). See GLES3-GF1-006.
    - Round-1 audit spot-check: the JSON (Open, state 101, 2 votes, updated 2026-09-24T00:42) matches every table value.

- **G2-040** The same report on Quest 2 (Adreno 650): about 14 ms on Vulkan with MSAA off and about 21 ms at 4x, with GLES within about 1 ms of those. [T]
  - That is roughly +7 ms for 4x on Quest 2, against +3 to +5 ms on Quest 3.
  - Quest 2's 1 MB of GMEM forces many more bins at 4x (G2-002).
  - Treat 4x as a Quest 3-only option unless measured otherwise.
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 (notes) (accessed 2026-09-24) · Applies to: Quest 2; Unity 6000.x · Evidence: [measured]
  - Notes: The note gives approximate figures only; the scene is a user repro project.

- **G2-041** In UUM-149765, GLES StoreColor rose only from 0.04 to 0.15 ms going from MSAA off to 4x, while Vulkan's reached 0.45 ms. [T]
  - This fits the GLES path storing only the resolved single-sample image, via implicit on-tile resolve (G2-036 / G3-048).
  - On Quest 3, GLES MSAA cost is therefore mostly growth in Render and Binning, not bandwidth.
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 (accessed 2026-09-24) · Applies to: Quest 3/3S; Unity 6000.x; GLES · Evidence: [measured]
  - Notes: This is an inference about the GL path; Unity does not document which MSAA extension its GLES backend uses (KU-18).

- **G2-042** Qualcomm phone sample: `EXT_multisampled_render_to_texture` compared against a 4x MSAA renderbuffer followed by a `glBlitFramebuffer` resolve. [T]
  - The explicit blit alone took about 2.5 ms on Adreno 530, and the on-tile path saved about 3 ms in total.
  - The sample also calls `glInvalidateFramebuffer(GL_DEPTH_ATTACHMENT)` after rendering.
  - Treat any Unity path that produces a real MSAA texture plus an explicit resolve on GLES (G2-043) as a multi-ms regression.
  - Source: https://github.com/quic/adreno-gpu-opengl-es-code-sample-framework (sample "msaa") (accessed 2026-09-24) · Applies to: Adreno 530 phone; Quest by analogy · Evidence: [measured] [verify on device]
  - Notes: Pre-2023 hardware (pre-2023; stale). The 2019 Meta blog's "about 3 ms" for a wrong MSAA store/load setup is the same order of magnitude (G1-046).

- **G2-043** `RenderTexture.bindTextureMS = true` with `antiAliasing > 1` stops Unity resolving the RT by default, so it can be sampled as a multisampled texture. This needs real multisample storage and defeats the on-tile resolve path. Avoid it on Quest GLES unless per-sample reads are essential. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture-bindTextureMS.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6000.x; GLES · Evidence: [doc] [verify on device]

- **G2-044** `SystemInfo.supportsMultisampleAutoResolve` is true when a platform resolves MSAA without an explicit intermediate multisampled texture, which saves bandwidth. Log it on device. A true value on Quest GLES is consistent with the `EXT_multisampled_render_to_texture` path. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsMultisampleAutoResolve.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6000.x · Evidence: [doc] [verify on device]

- **G2-045** The sources disagree on how much MSAA costs: [T]
  - Qualcomm: MSAA 2x is "likely to be practically free", and MSAA is preferred over other AA methods.
  - Meta (Quest 1 era): MSAA has a real cost.
  - UUM-149765: +3.3 ms for 4x (GLES, Quest 3).

  No published 2x number for Quest GLES was found. Measure 2x vs 4x with the G2-010 recipe.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ ; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes: Unity's untethered-XR checklist calls 2x "a good balance" (G1-048). See G2-C3.

- **G2-046** Alpha-to-coverage, typical for MSAA foliage and cutouts, disables LRZ, as do the other LRZ killers in G2-083. With MSAA, prefer A2C over `clip()`/discard only after measuring: both paths lose LRZ, and discard also hurts early-Z. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("LRZ") (accessed 2026-09-24) · Applies to: Adreno 5x+; Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]

### 3.5 FlexRender (binned vs direct) and concurrent binning

- **G2-084** FlexRender picks binned (GMEM) or direct (system memory) mode per surface, mid-frame, and its heuristics are not exposed. [T]
  - Known triggers for direct mode:
    - A high ratio of vertex-shader texture samples to vertices.
    - Few vertices or few draws.
    - Tessellation or geometry shaders.
  - Meta adds the typical Unity case: a full-screen pass with no depth and no MSAA, such as a tonemap or the final blit, runs direct.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]

- **G2-085** Spotting direct mode. [T]
  - In ovrgpuprofiler, a direct-mode surface shows one bin covering the whole surface, with a single Render stage. Meta's verbatim example: `Surface 1 | 1216x1344 | color 32bit, depth 0bit, stencil 0 bit, MSAA 1 | 1 1216x1344 bins | 2.01 ms | 1 stages : Render 2.01ms`.
  - Snapdragon Profiler's "Rendering Stages" metric (Trace capture) shows the mode per surface.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes: ovrgpuprofiler also prints Mode 0–3 per surface (G3-080). Snapdragon Profiler is unreliable on current Horizon OS (G3-085).

- **G2-086** What direct mode means in practice: [T]
  - Compositor FFR is disabled (G2-061).
  - LRZ still runs but helps less.
  - There are no GMEM load/store stages, so load/store actions matter less.
  - Occlusion queries are cheaper (G2-033).

  Direct mode suits a full-screen pass with one fragment per pixel. Leave it alone unless it is the swapchain pass where you need FFR.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]

- **G2-087** Binning is a large share of eye-buffer time in Unity 6 on Quest 3/3S. [T]
  - UUM-149765 reports Binning at 4.5 ms of 9.7 ms (GLES, no MSAA) and 5.1 ms of 13.0 ms (GLES 4x). Vulkan shows the same binning figures.
  - Draw count, triangle count and vertex-shader cost (the position-only pass) all feed it.
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 (accessed 2026-09-24) · Applies to: Quest 3/3S; Unity 6000.x · Evidence: [measured] [verify on device]
  - Notes:
    - On Adreno 7x, binning can run concurrently with rendering (G2-088). The report does not say whether ovrgpuprofiler's Binning time overlaps Render or adds to it (KU-26).
    - Qualcomm's guideline is 10–20% binning per render pass (G3-079). These figures are well above it.

- **G2-088** Concurrent binning arrived with the A7x series: Quest 3/3S (A740) have it and Quest 2 (A650, A6x) does not. It needs no enabling, but it can be blocked: [T][C]
  - A pass whose binning depends on the previous pass's output.
  - Clearing or invalidating the same Z-buffer several times within a frame. Qualcomm suggests reusing one Z-buffer across passes without clears, or using separate Z-buffers.
  - A VSYNC-limited app whose first surface carries all the geometry. The fix is to schedule independent work first.

  Profile it in Snapdragon Profiler as "Binning Pipe".
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("Concurrent Binning") ; https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md (accessed 2026-09-24) · Applies to: Quest 3/3S only; not Quest 2 · Evidence: [doc] [verify on device]
  - Notes: This pulls against the invalidate-everything advice (G2-C5). Its absence on Adreno 650 has no Meta confirmation (KU-25).

- **G2-089** Qualcomm's advice for concurrent binning: issue each draw so it produces enough fragment work to overlap the next draw's binning. Many tiny, fragment-cheap draws followed by a heavy one waste the overlap. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc] [verify on device]

- **G2-090** For CPU-bound apps Qualcomm also allows deeper CPU queueing. Keep submitting until the CPU is about to submit frame N+2 while the GPU has not finished frame N; the driver can then bin frame N+1 alongside frame N. The price is up to one extra frame of latency, which on Quest interacts with the compositor's pacing. [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Adreno 7x · Evidence: [doc] [verify on device]
  - Notes: This is phone guidance. Do not apply it on Quest without checking latency and stale frames in the VrApi / OVR Metrics logs.

### 3.6 LRZ (low-resolution Z)

- **G2-083** LRZ (Adreno 5x+) cannot be controlled directly. [T]
  - Qualcomm lists what disables it:
    - A change of depth-compare direction within a pass.
    - Depth func ALWAYS or NOT_EQUAL (disabled until the next clear).
    - Blending with depth writes.
    - Colour-masked writes.
    - Stencil use.
    - Framebuffer fetch.
    - Discard.
    - Alpha-to-coverage.
    - Fragment depth writes.
  - Early-Z rejects at up to 4x fill rate, and Fast-Z writes Z-only at 2x.
  - Depth formats rank D16 > D24S8 > D32.
  - Unity equivalents: `ZTest Always` in overlay/UI shaders; changes in reversed-Z direction; opaque shaders using `clip()`; stencil-based portals.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("LRZ", "Early-Z", "Fast-Z", depth formats) ; https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md (accessed 2026-09-24) · Applies to: Adreno 5x+; Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes:
    - Unity's untethered-XR checklist says to disable depth priming and rely on LRZ (G1-048).
    - `ovrgpuprofiler -x` gives per-draw traces with LRZ state (G3-080).

## 4. Multiview on GLES

Bottom line: on GLES, the multiview win is CPU-side (half the draw submissions). Budget vertex shading at roughly 2x (G2-050 / G3-045, G2-051, G2-C10). On GLES it runs through the deprecated OculusXR plugin (G2-055).

- **G2-047** `OVR_multiview` API essentials. [T]
  - Attach with `glFramebufferTextureMultiviewOVR(target, attachment, texture, level, baseViewIndex, numViews)` to a 2D array texture.
  - The vertex shader declares `layout(num_views = 2) in;` and reads `gl_ViewID_OVR` (mediump uint).
  - The spec minimum for GL_MAX_VIEWS_OVR is 2 (6 is suggested).
  - A draw whose program view count differs from the FBO's view count is INVALID_OPERATION.
  - Both `GL_OVR_multiview` and `GL_OVR_multiview2` are exposed on the Quest 2 and Quest 3 GLES drivers.
  - Source: https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview.txt (rev 6, 2018) ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES 3.x · Evidence: [doc]
  - Notes: The gpuinfo reports do not list GL_MAX_VIEWS_OVR; query it at runtime (KU-21).

- **G2-048** `OVR_multiview` vs `OVR_multiview2`. [T]
  - In base `OVR_multiview`, only `gl_Position` may depend on `gl_ViewID_OVR` in the vertex shader.
  - `OVR_multiview2` relaxes this, so other outputs (for example per-eye reflection vectors or eye-dependent varyings) can depend on the view ID. Enabling multiview2 implicitly enables multiview.
  - Unity stereo shaders pass the eye index (`UNITY_VERTEX_OUTPUT_STEREO`), so on GLES they need view-dependent outputs, i.e. multiview2 semantics.
  - Source: https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview2.txt (rev 0.5, status Incomplete) ; https://docs.unity3d.com/6000.3/Documentation/Manual/SinglePassInstancing.html (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes: That Unity's GLES multiview shaders require multiview2 is inferred from the macro behaviour; it is not documented.

- **G2-049** Multiview restrictions that affect pipeline design: [T][C]
  - No transform feedback, tessellation or geometry shaders.
  - No timer queries.
  - Occlusion query results fall between the per-view maximum and the sum.
  - A clear applies to all views.
  - One viewport and scissor are shared by all views.
  - `gl_Layer` is undefined in the fragment shader.
  - Reading from a read FBO with more than one view via ReadPixels / CopyTex* / Blit is INVALID_FRAMEBUFFER_OPERATION. A readback therefore needs a single-view FBO per layer, which is another pass.
  - Source: https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview.txt (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES · Evidence: [doc]

- **G2-050 / G3-045** The multiview benefit is on the CPU side. [T][C]
  - Meta: with multiview, the CPU issues half as many draw calls.
  - Meta native docs: sequential per-eye stereo doubles app and driver overhead.
  - Qualcomm: the Adreno driver records the command stream for one eye and replays it for the other. This saves CPU time and has "no impact on the GPU".
  - `OVR_multiview2` also lets outputs other than position depend on the view ID, such as per-eye view vectors.

  This is the main reason to use multiview on GLES, because the render thread is usually the GLES bottleneck.
  - Source: https://developers.meta.com/horizon/documentation/unity/enable-multiview/ (updated 2025-11-12) ; https://developers.meta.com/horizon/documentation/native/android/mobile-multiview/ (VrApi era, updated 2022-09-29) ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview.txt ; https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview2.txt (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes: Meta's deprecated native doc told apps to query `VRAPI_SYS_PROP_MULTIVIEW_AVAILABLE` because of driver issues (pre-2023; stale).

- **G2-051** The GPU benefit on vertex and fragment work is small or nil. [T]
  - The `OVR_multiview` spec allows the implementation to duplicate all GPU work per view while still saving the scene traversal. It may also compile per-view program variants.
  - Meta claims only better cache coherence on the GPU side.
  - UUM-149765 saw no GPU-time difference between Multi-pass and Multiview/SPI on Quest 2/3/3S.

  Budget vertex shading as roughly 2x (two views) even with multiview.
  - Source: https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview.txt ; https://developers.meta.com/horizon/documentation/unity/enable-multiview/ ; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [measured] (UUM-149765) [verify on device]
  - Notes: No published number exists for the Adreno vertex-shader saving from multiview (KU-22). See G2-C10.

- **G2-052** With multiview, one bin holds both eye views: this is the ×2 in Meta's GMEM arithmetic (G2-002). The per-view pixel area per bin is therefore half of what a single-view pass would get at the same format. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]

- **G3-047** In captures, Quest 2 shows a GL multiview pass as one surface with twice the tiles; the original Quest showed two surfaces with the same ID. Read ovrgpuprofiler bin counts on Quest 2 as doubled: "135 96x176 bins" means 135 bins of 96x176x2. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2; GLES · Evidence: [doc]
  - Notes:
    - Meta does not describe how GL multiview looks on Quest 3 (KU-34).
    - Quest 3/3S have `VK_QCOM_multiview_per_view_viewports` and `_render_areas`, which MRR uses (G1-039), but they are Vulkan-only. Nothing equivalent is exposed on GL.

- **G2-053** How Unity maps SPI to multiview on GLES. [T]
  - Unity documents Multiview as a variant of single-pass instanced that replaces SPI where supported.
  - SPI support is listed for Android devices with the Multiview extension, including Meta Quest.
  - The OculusXR plugin's "Stereo Rendering Mode = Multiview" converts draw calls in the graphics driver, so Unity issues one draw for both eyes. Set it at Project Settings > XR Plug-in Management > Oculus > Android > Stereo Rendering Mode.
  - `SystemInfo.supportsMultiview` reports availability.
  - If SPI/multiview is requested but unsupported, Unity falls back to multi-pass.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/SinglePassStereoRendering.html ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html ; https://developers.meta.com/horizon/documentation/unity/enable-multiview/ ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsMultiview.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6000.x with OculusXR 4.x; GLES · Evidence: [doc]

- **GLES3-GF2-004** Unity's manual names the two GL extensions behind single-pass stereo on Android: multiview "consists of" `GL_OVR_multiview2` and `GL_OVR_multiview_multisampled_render_to_texture`, rendering into a 2-slice 2D texture array. The page text is the same in the 2022.3, 6000.0, 6000.3 and 6000.6 manuals. [T]
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/Android-SinglePassStereoRendering.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/Android-SinglePassStereoRendering.html ; https://docs.unity3d.com/6000.0/Documentation/Manual/Android-SinglePassStereoRendering.html ; https://docs.unity3d.com/2022.3/Documentation/Manual/Android-SinglePassStereoRendering.html (accessed 2026-09-24) · Applies to: Unity 2022.3–6000.6; Android GLES with Single Pass / Multiview; Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes:
    - This mostly answers KU-18 for the multiview eye buffer. Unity documents its GLES multiview path as built on the OVR multiview MSRTT extension, so MSAA on a multiview eye buffer is resolved on tile. That fits the small GLES StoreColor growth in UUM-149765 (G2-041). It does not say which call is used for non-multiview MSAA render targets (`EXT_multisampled_render_to_texture` vs an explicit resolve). [verify on device] Look for `glFramebufferTextureMultisampleMultiviewOVR` in a RenderDoc GL capture.
    - Practical consequence: on GLES multiview, the eye buffer's MSAA samples never leave GMEM unless something forces a mid-pass resolve (G2-028). Any intermediate pass that samples the eye buffer breaks that.

- **G2-054** Custom HLSL must follow the SPI macro contract, or it renders only to slice 0 (the left eye). Missing macros show up as a missing right eye, not as a performance regression. [T]
  - Vertex input: `UNITY_VERTEX_INPUT_INSTANCE_ID`.
  - Vertex output: `UNITY_VERTEX_OUTPUT_STEREO`.
  - In the vertex shader: `UNITY_SETUP_INSTANCE_ID` and `UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO`.
  - In the fragment shader, when sampling screen-space textures: `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX`.
  - Screen-space textures: `UNITY_DECLARE_SCREENSPACE_TEXTURE` / `UNITY_SAMPLE_SCREENSPACE_TEXTURE`, because the eye targets are texture arrays.
  - Source: https://docs.unity3d.com/6000.3/Documentation/Manual/SinglePassInstancing.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/SinglePassStereoRendering.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6000.x · Evidence: [doc]

- **G2-055** OpenXR has no documented GLES multiview path on Quest. [T]
  - The Unity OpenXR plugin (1.5 through 1.16.1) lists Meta Quest with Vulkan only.
  - The Meta Quest feature settings (Symmetric Projection, Optimize Buffer Discards, Multiview Render Regions) are Vulkan-only.
  - Meta says multiview is on by default with the OpenXR Meta Quest feature group.

  In practice, GLES multiview on Quest is the OculusXR plugin path, which is deprecated from Unity 6.5 (G1-024 / G2-093).
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/features/metaquest.html ; https://developers.meta.com/horizon/documentation/unity/enable-multiview/ (accessed 2026-09-24) · Applies to: Unity 2021.3–6000.x · Evidence: [doc]
  - Notes: See G2-C8 and GX-C8.

- **G2-057 / G3-046** UUM-102876: in development builds with OculusXR 4.4.0 + Multiview + GLES (Unity 6000.0.33f1), GL_INVALID_OPERATION errors are logged continuously on Quest 2/3 and cause FPS drops. Closed Won't Fix; last updated 2026-05-01. [C]
  - Never profile GLES multiview in a development build without checking logcat for GL error spam.
  - The multiview INVALID_OPERATION case in the spec is a view-count mismatch (G2-047).
  - Source: https://issuetracker.unity.com/api/v1.0/issues/14139 (JSON for UUM-102876) ; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102876 (accessed 2026-09-24) · Applies to: Unity 6000.0.33f1 + OculusXR 4.4.0; GLES; Quest 2, Quest 3; development builds · Evidence: [community]
  - Notes: Error logging adds CPU cost to development builds and distorts CPU profiles. Filter logcat, or confirm CPU timings on a non-development build.

- **G2-058** OXPB-144: crash on launch with MultiView + GLES3 in release builds (OculusXR 4.2.0; Unity 2022.3.20f1 / 2023.2). Closed Won't Fix. Pin a known-good OculusXR version and smoke-test release builds, not only development builds. [C]
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=OXPB-144 (accessed 2026-09-24) · Applies to: OculusXR 4.2.0; Unity 2022.3.20f1, 2023.2; GLES · Evidence: [community]

Foveation on multiview arrays (`QCOM_texture_foveated` per-layer parameters) is covered in §7.3.

## 5. Driver and state overhead on Adreno GLES

### 5.1 State changes and draw ordering

- **G2-065** CPU cost of state changes, measured by Meta on Quest 1 with Unity 2018.1.6f1 (single-pass stereo, multithreaded rendering off, ATW off): [T][C]
  - Material switch with the same shader: +64% per-draw time.
  - Shader (program) switch: +175%.
  - Mesh changes cost less than material changes.
  - More textures on the changed material cost more.
  - Redrawing the same object costs about 25% of drawing a different object.
  - Texture size, filtering and compression have negligible CPU cost.

  Sort draws by shader, then material, then mesh.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (accessed 2026-09-24) · Applies to: measured on Quest 1; direction assumed to hold on Quest 2, Quest 3/3S GLES · Evidence: [measured] [verify on device]
  - Notes: Stale data (pre-2023; stale). It is the only Quest GLES state-change cost data found (KU-23).

- **G2-066** The GPU side of the same Meta study: [T]
  - Mesh complexity outweighs material changes.
  - A dependent texture read costs only slightly more than an independent one.
  - Polygons spanning several tiles add cost.
  - Blending costs more in linear colour space.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (accessed 2026-09-24) · Applies to: Quest 1 measurement; Quest 2, Quest 3/3S by analogy · Evidence: [measured] [verify on device]
  - Notes: Stale (2018) (pre-2023; stale).

- **G2-067** Qualcomm's GLES guidance on switching: [T][C]
  - Minimise pipeline (program) switches to avoid internal synchronisation.
  - Do not interleave graphics and compute: issue all graphics work, then all compute.
  - For Unity: on GLES, avoid compute dispatches (GPU skinning, GPU particles, compute-based culling) between opaque draws.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("Shader mode switching") (accessed 2026-09-24) · Applies to: Adreno GLES · Evidence: [doc] [verify on device]

- **G2-094** OpenXR project validation says the OpenGL graphics API requires linear colour space, and the Meta draw-call study found blending more costly in linear space (G2-066). On GLES, linear space plus heavy transparent blending is a known cost multiplier. [T]
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/project-configuration.html ; https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (accessed 2026-09-24) · Applies to: Unity OpenXR 1.16; Quest 2, Quest 3/3S · Evidence: [doc]

### 5.2 Uniform buffers

- **G2-070** UBO sizing on Adreno. [T]
  - GL_MAX_UNIFORM_BLOCK_SIZE is 65536 bytes on both the Quest 2 and Quest 3 GLES drivers.
  - Qualcomm says that value is only a correctness limit. For performance, keep the **sum of all UBOs referenced by one shader under 90% of 8 KB (7372 bytes)**, so they fit in constant RAM.
  - Beyond that, the compiler maps only the portions it can prove are accessed, and dynamic indexing defeats this.
  - Unity implications:
    - Large `UnityPerMaterial` or `UnityPerDraw` cbuffers plus instancing arrays can exceed 7372 B.
    - Indexed instancing arrays (indexed by `unity_InstanceID`) are dynamic indexing, the worst case.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("Buffer Best Practices") ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Adreno (phone guide); Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes:
    - No Quest-specific number was published. Check a shader's constant footprint with the Adreno Offline Compiler or Snapdragon Profiler.
    - `half` in a cbuffer still takes 32-bit size and alignment, so it does not shrink the UBO (G3-033).
    - The per-shader UBO-count thresholds are in G2-069 / G3-037 / G3-038.

### 5.3 Instancing, indirect draws and index/vertex data

- **G2-075** Instancing and indirect draws on GLES 3.x: [T]
  - `glDrawArraysInstanced` / `glDrawElementsInstanced` (ES 3.0).
  - `glDrawArraysIndirect` / `glDrawElementsIndirect` (ES 3.1), with arguments cached in a buffer at load time.

  Qualcomm lists maximising indirect draws as a best practice. In Unity these correspond to `Graphics.RenderMeshInstanced` / `RenderMeshIndirect` (availability varies by Unity version) and to GPU instancing on materials.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("Geometry instancing", "Indirect draw calls") (accessed 2026-09-24) · Applies to: Adreno GLES 3.1+; Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes: The mapping from Unity API to GL call is inferred.

- **G2-076** Index and vertex data: [T]
  - Prefer the smallest index type. Qualcomm lists 8-bit, then 16-bit, and says to avoid 32-bit.
  - Unity offers only `IndexFormat.UInt16` (the default) and `UInt32`, so keep meshes at or under 65535 vertices to stay 16-bit.
  - The A7x vertex cache holds 32 four-component vertices, so vertex-cache optimisation matters.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.IndexFormat.html ; https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/spec_sheets.md (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [doc]

### 5.4 Feeding the binning pass

- **G2-077 / G3-036** Vertex layout for the binning pass. [T]
  - Put position alone in the first stream and interleave the other attributes in a second stream. The binning pass runs a position-only vertex shader, so it then reads the smallest possible stream.
  - Use packed hardware formats to cut vertex-fetch bandwidth in the binning pass: `GL_HALF_FLOAT` (`GL_OES_vertex_half_float`, on both headsets) for attributes, and `GL_INT_2_10_10_10_REV` for normals.
  - In Unity: `Mesh.SetVertexBufferParams` with position on stream 0 and the other attributes on stream 1, plus `VertexAttributeFormat.Float16` / SNorm formats for normals, tangents and UVs.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (vertex buffers, position-only shader) (accessed 2026-09-24) · Applies to: Adreno; Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes: The Unity stream mapping is an inference, and whether Unity's importer splits streams by default is not documented. The mesh/geometry bundle owns this topic in depth.

- **G2-078 / G3-040** Keep vertex-shader texture fetches to a minimum. [T]
  - On Adreno they generally run twice: once in the binning (position-only) shader and again in the full vertex shader.
  - A high ratio of VS texture samples to vertices is a documented trigger for direct mode.
  - If the binning shader stalls on memory, binning slows significantly.
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Adreno; Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes: This affects vertex displacement and wind shaders. ovrgpuprofiler's trace reports the mode per surface (G3-080).

### 5.5 Buffer streaming and orphaning

- **G2-071** Buffer streaming on GLES. The main hazard is implicit synchronisation when you overwrite a buffer the GPU is still reading. Standard mitigations: [T][C]
  1. **Orphan**: `glBufferData(NULL, same size, same usage)`, or `glMapBufferRange` with `GL_MAP_INVALIDATE_BUFFER_BIT`. The driver hands out fresh storage and usually recycles blocks.
  2. **Ring buffer**: use `GL_MAP_UNSYNCHRONIZED_BIT` with non-overlapping writes, and orphan when the ring wraps.
  3. **Persistent mapping** (buffer storage) with a fence per region.

  `GL_EXT_buffer_storage` is exposed on the Quest 2 and Quest 3 GLES drivers, so option 3 is possible in native code (G3-070).
  - Source: https://web.archive.org/web/20250118034434/https://www.khronos.org/opengl/wiki/Buffer_Object_Streaming (Khronos wiki, desktop-GL oriented; the live URL returned 403) ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: GLES 3.x generic; Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes: Option 3's fence usage pulls against Qualcomm's fence advice (G2-030, G2-C6).

- **G2-072** Qualcomm on VBO updates: if VBO contents must change mid-frame, batch **all** updates before any draw that uses the modified buffers. Interleaving update, draw, update, draw may make the driver keep several copies of the entire VBO, which costs CPU time and memory. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("Batch vertex buffer object updates") (accessed 2026-09-24) · Applies to: Adreno GLES · Evidence: [doc]

- **G2-073** Unity-side dynamic buffer controls: [T][C]
  - `Mesh.MarkDynamic` requests "dynamic" GPU buffers, which are faster to update and possibly slightly slower to read.
  - `GraphicsBuffer` with `UsageFlags.LockBufferForWrite`, plus `LockBufferForWrite` / `UnlockBufferAfterWrite`, makes fewer copies than `SetData`. The returned NativeArray points at GPU memory when possible, otherwise at a CPU staging copy. Write linearly and never read, because the memory is write-combined.

  Unity does not document which GL calls its GLES backend uses for these: `glBufferSubData`, map with INVALIDATE/UNSYNCHRONIZED, or orphaning.
  - Round-2 re-check: the 6000.3 `LockBufferForWrite` page still says only that the NativeArray points at GPU memory "if possible", depending on "buffer usage, active graphics device, and hardware support". The flag's page says the GPU may only read such a buffer (no UAV writes, no copy destination). No GLES-specific statement, and no Unity forum or staff post giving the GL call pattern, was found (KU-19 stays open).
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Mesh.MarkDynamic.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GraphicsBuffer.LockBufferForWrite.html ; https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GraphicsBuffer.UsageFlags.LockBufferForWrite.html (accessed 2026-09-24) · Applies to: Unity 2021.3–6000.x (MarkDynamic); the first version with `GraphicsBuffer.LockBufferForWrite` was not verified · Evidence: [doc] [verify on device]
  - Notes: See KU-19.

The UUM-93226 claim that buffer-update-heavy content can favour GLES over Vulkan is in G1-049 / G2-074 / G3-049 (§2.5), and GX-C2 covers what the "buffer copies" actually are.

### 5.6 Fences, sync and compute flushes

- **G2-030** Avoid `glFenceSync` / `glClientWaitSync` on Adreno GLES. Qualcomm says `eglSwapBuffers` already provides the needed CPU/GPU throttling. An explicit client wait blocks the render thread, which is a direct frame-pacing risk. [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (OpenGL ES tab) (accessed 2026-09-24) · Applies to: Adreno GLES; Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes: See G2-C6. `GraphicsFence` is on the audit list of possible pass splits (G2-029).

- **G2-080** According to Qualcomm, a `glDispatchComputeIndirect` with a workgroup smaller than 64 makes the CPU wait on the GPU (a command-buffer flush). On GLES that is also a pass split (G2-029). Keep indirect compute workgroups at 64 or more. [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ("Compute") (accessed 2026-09-24) · Applies to: Adreno GLES 3.1+ · Evidence: [doc] [verify on device]

### 5.7 Validation overhead: KHR_no_error and Low Overhead Mode

- **G1-043 / G2-079** Low Overhead Mode in the Oculus XR Plugin is GLES-only and makes the driver skip GLES validation. It is the only documented GLES-specific CPU optimisation, and the Unity-side equivalent of `GL_KHR_no_error`. [T]
  - Qualcomm recommends `GL_KHR_no_error` in shipping builds. Quest 2 and Quest 3 expose `GL_KHR_no_error` and `EGL_KHR_create_context_no_error`.
  - Caveat: UUM-102878 reports OES external textures (video, camera) rendering black with Low Overhead Mode in release builds. Closed Won't Fix.
  - Source: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/oculus-plugin.html ; https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102878 ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: OculusXR 4.x (deprecated from Unity 6.5); GLES; Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes:
    - The UUM-102878 caveat is community evidence from the issue tracker.
    - No equivalent was found in the OpenXR Meta Quest Support feature list, so moving to OpenXR may remove this GLES CPU saving. [verify on device] Check the OpenXR feature settings in your plugin version (KU-43).
    - No render-thread ms figure is published for it (G1-069).

## 6. Shaders on GLES: compile cost, program-binary caching, WarmUp, precision

### 6.1 The compile/link hitch and binary formats

- **G3-001** Unity does not create GL programs when a scene loads; it creates them the first time a draw needs that variant. The first frame that shows a new material or keyword combination pays for the driver's compile and link inside the frame. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html (accessed 2026-09-24) · Applies to: all Quest, Unity 6.x GLES · Evidence: [doc]
  - Notes: Unity says a scene or resource load puts all of its variants into CPU memory, decompressed by default. The driver then builds the GPU version on first use, and Unity notes there "might be a visible stall". No published millisecond figure exists for glCompileShader/glLinkProgram on Adreno 650 or 740. To measure it, take a development build and compare the Shader.CreateGPUProgram durations on the render thread between a cold launch (app cache cleared, see G3-010) and a warm launch.

- **G3-002** Use four profiler markers to diagnose hitches.
  - Shader.ParseThreaded and Shader.ParseMainThread cover deserializing and decompressing variants.
  - Shader.CreateGPUProgram covers the driver compile/link, which is the hitch itself.
  - Shader.MainThreadCleanup covers unloading.
  - CreateGraphicsGraphicsPipelineImpl covers PSO creation. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html ; https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm.html (accessed 2026-09-24) · Applies to: Unity 6.x · Evidence: [doc]
  - Notes: GLES has no pipeline objects, so CreateGPUProgram is the marker that matters. Unity does not document whether the PSO marker fires on GLES at all. [verify on device]

- **G3-003** Unity removes a variant from CPU and GPU memory once nothing references it. Using it again later, for example after switching scenes, recreates the GPU program. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html (accessed 2026-09-24) · Applies to: Unity 6.x · Evidence: [doc]
  - Notes: Whether that second creation hits the Android blob cache (G3-009) and so costs less is not documented. [verify on device] Look for a second CreateGPUProgram for the same shader after a scene round-trip.

- **G3-004** Shader variant chunk settings live in Player > Other Settings > Shader Variant Loading:
  - "Default chunk size (MB)".
  - "Default chunk count" (0, the default, means no limit).
  - A per-platform Override.
  - Shader.maximumChunksOverride at runtime.

  A lower chunk count keeps less decompressed shader data resident. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/shader-memory.html (accessed 2026-09-24) · Applies to: Unity 6.x Android · Evidence: [doc]
  - Notes: Unity does not quantify the CPU cost of decompressing a chunk again after eviction; that trade-off is my inference. No published number was found. Compare the Shader.ParseThreaded/ParseMainThread times with chunk count 0 and with a small count.

- **G3-005** When a stripped variant is requested, Unity quietly picks a "similar" variant: there is no hitch, but the keywords are wrong. With strict shader variant matching on, you get the magenta error shader instead. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html (accessed 2026-09-24) · Applies to: Unity 6.x · Evidence: [doc]
  - Notes: Turn strict matching on in QA builds when auditing stripping. A silent substitution can make device performance and visuals differ from the editor.

- **G3-006** Qualcomm says compiling and linking at runtime causes framerate hitches. Its advice is to compile everything during initialization and only switch programs with glUseProgram while rendering. [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24; page "Last Published: Sep 22, 2026") · Applies to: Adreno generally (Quest 2/3) · Evidence: [doc]

- **G3-007 / G2-068** Qualcomm states that "Adreno drivers never recompile shaders" because GL state changed. On Adreno, a program linked once is never silently rebuilt at draw time for a new blend, depth or vertex state. Some other GLES drivers do rebuild. [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 2/3/3S GLES · Evidence: [doc]
  - Notes: This is the key reason warming up on GLES works on Quest. On Vulkan a PSO includes render state; on Adreno GLES it does not. The Khronos blob-cache spec treats state-based recompiles as a general driver problem (see G3-C5). Not measured on Quest. [verify on device] Warm a variant, draw it with a different blend mode, and check that no CreateGPUProgram or GPU stall appears.
  - G2-068 draws the same conclusion from the same Qualcomm section: on Quest GLES, hitches come from the first compile/link of a variant or from loading a program binary, not from state-dependent recompiles.
  - Round-1 audit spot-check: the Qualcomm sentence was re-read on the live page (last published Sep 22, 2026). Confirmed.

- **G1-008 / G3-008** Neither headset can load precompiled GPU code. Both report GL_NUM_SHADER_BINARY_FORMATS = 0 and GL_NUM_PROGRAM_BINARY_FORMATS = 1, which is the driver's own opaque format. Every program is compiled on the device at least once per driver or OS build. [C]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 · Evidence: [measured]
  - G1-008 adds that `EGL_ANDROID_blob_cache` is missing from both EGL lists. This is by design, because the extension is private to the Android EGL layer (G3-009).
  - Round-1 audit spot-check: both values were re-read from reports 6387 and 8023. Confirmed.

### 6.2 Program-binary caching: EGL blob cache, `OES_get_program_binary`, Unity's cache

- **G3-009** Android's EGL loader caches the driver's compiled binaries automatically through EGL_ANDROID_blob_cache. Apps never see the extension, which is why it is missing from the Quest EGL lists. A Unity GLES app gets this cache without writing any code. [C]
  - Source: https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_blob_cache.txt ; https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/egl_cache.cpp (accessed 2026-09-24) · Applies to: Quest 2/3/3S (Android-based Horizon OS) · Evidence: [doc]
  - Notes: The spec's rationale cites compiles taking seconds at app start.

- **G3-010** Android's HardwareRenderer (setupDiskCache) sets up the cache for each process. The file is named `com.android.opengl.shaders_cache` and sits in the app's cache directory. egl_cache is process-wide, so Unity's GL context in the same process uses the same file. [C]
  - Source: https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/graphics/java/android/graphics/HardwareRenderer.java (accessed 2026-09-24) · Applies to: Quest (Android base) · Evidence: [doc] [verify on device]
  - Notes: On a debuggable build, run `adb shell run-as <pkg> ls -l cache/`. A file that grows after the first session means the cache is active. Clearing the app's cache or data empties it, which is the way to test a cold start.

- **G3-011** The monolithic blob cache (the AOSP default) has three limits: 12 KB per key, 64 KB per value and 2 MB in total. These values are the same in AOSP main, 14, 15 and 12. BlobCache::set quietly declines any value over the per-value limit (the message is only logged at verbose level). A program whose binary exceeds 64 KB would therefore recompile on every cold launch. [C]
  - Source: https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/egl_cache.cpp ; https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/BlobCache.cpp (accessed 2026-09-24) · Applies to: Quest, if Horizon OS keeps the AOSP defaults · Evidence: [doc] [verify on device]
  - Notes: No published size exists for Adreno program binaries of URP Lit variants. To find one, query GL_PROGRAM_BINARY_LENGTH from a native plugin, or watch the cache file grow.
  - Round-1 audit spot-check: the limits were re-read in AOSP `egl_cache.cpp` (main): `kMaxMonolithicKeySize` 12 KB, value 64 KB, total 2 MB. Confirmed.

- **G3-012** When the monolithic cache passes its maximum, BlobCache evicts random entries until the total is under half the maximum (1 MB). A game with hundreds of variants can thrash this cache. Some programs then recompile on every launch even though a cache file exists. [C]
  - Source: https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/BlobCache.cpp (accessed 2026-09-24) · Applies to: Quest (AOSP behaviour) · Evidence: [doc]

- **G3-013** AOSP also has a multifile cache: 32 MB total, 8 MB per value, 1 MB per key, up to 4096 entries. The build property `ro.egl.blobcache.multifile` gates it (default false), and `debug.egl.blobcache.multifile` / `*_limit` can override it. It is unknown whether Horizon OS turns it on. [C]
  - Source: https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/egl_cache.cpp (accessed 2026-09-24) · Applies to: Quest · Evidence: [doc] [verify on device]
  - Notes: Check with `adb shell getprop ro.egl.blobcache.multifile` and `adb shell getprop ro.build.version.release`. Do not ship debug props; they are a test-only device setting.
  - Round-1 audit spot-check: the multifile limits were re-read in `egl_cache.cpp`: 1 MB key, 8 MB value, 32 MB total, 4096 entries. The mode is gated by `ro.egl.blobcache.multifile` (default false), with debug overrides and a `multifile_limit` property. Confirmed.

- **G3-014** Both cache types record the OS build ID (`ro.build.id`) and throw everything away when it changes. The first launch after every Horizon OS update is therefore cold, and all first-use hitches come back. [C]
  - Source: https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/BlobCache.cpp ; MultifileBlobCache.cpp in the same directory (accessed 2026-09-24) · Applies to: Quest · Evidence: [doc]
  - Notes: So "no hitch on my headset" often just means a warm cache. Always test hitches cold. In-app warmup is still worth doing.

- **G2-081 / G3-015** Qualcomm recommends that apps save their own glGetProgramBinary blobs and reload them next launch with glProgramBinary, which it says can significantly shorten launch. [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Adreno GLES · Evidence: [doc]
  - G2-081 adds that `GL_OES_get_program_binary` is on both headsets (reports 6387 and 8023). It is the GLES lever for first-use hitches when an engine or native plugin owns the program objects. Unity does not expose `glGetProgramBinary` to C#.

- **G3-016** A saved program binary can be rejected, for example after a driver update. After glProgramBinary, the app must check GL_LINK_STATUS and fall back to compiling from source. [C]
  - Source: https://registry.khronos.org/OpenGL/extensions/OES/OES_get_program_binary.txt (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]
  - Notes: Any engine-level binary cache has to handle this. Horizon OS updates change the driver (see G3-044).

- **G3-017** Unity documents its own GLES3 binary shader cache, but only for Embedded Linux:
  - The files live in `[TEMP]/[COMPANY]/[PROJECT]/UnityShaderCache/`.
  - They can be pre-seeded into `Data/UnityShaderCache/`.
  - `-platform-hmi-gfx-cache-path` overrides the location.
  - The cache must be regenerated for each Player build and shared only between identical hardware and software.

  No Android or Quest documentation of this cache was found. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/embedded-linux-optional-features.html (accessed 2026-09-24) · Applies to: Unity 6.x (documented only for Embedded Linux) · Evidence: [doc] [verify on device]
  - Notes: Unity clearly has a GLES program-binary cache in its code. Whether the Android player enables it is unknown. After a session, look for a `UnityShaderCache` folder under `/sdcard/Android/data/<pkg>/cache/` (Application.temporaryCachePath).

- **G3-018** Arm's Mali integration guide says Android's blob cache defaults to about 64 KB per application and suggests raising it to 512 KB-1 MB. AOSP source shows 64 KB is the per-entry limit and 2 MB the total (G3-011). Do not use Arm's figure for Quest. [C]
  - Source: https://developer.arm.com/documentation/101897/0303/System-integration/Android-blob-cache-size-in-OpenGL-ES (accessed 2026-09-24; the direct fetch returned 403 today, content seen earlier via WebFetch) · Applies to: Mali integrators, not Quest · Evidence: [doc]
  - Notes: See G3-C1.

- **GLES3-GF1-006** Current Quest 2 firmware runs on an Android 14 base, so the AOSP 14 EGL blob-cache code (G3-011 to G3-014) applies to Quest 2 as well as Quest 3. UUM-149765's device list gives: [C]
  - Quest 2: Android 14, firmware 2.1.1034.
  - Quest 3: Android 14, firmware 2.4.1031.
  - Quest 3S: Android 14, firmware v2.6, Vulkan driver 512.837.7 (Vulkan 1.3.295).

  The same report's repro recipe also sets `debug.oculus.sysPropDebug 1` and `debug.oculus.headlock 1` (see G2-010).
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3, Quest 3S; Horizon OS builds in use in 2026 · Evidence: [community] [verify on device]
  - Notes:
    - The tracker is a Unity QA device list, not a Meta statement.
    - The Quest 3S CPU field reads "Google Tensor G2", which is clearly a data-entry error. Treat the rest of that row with care.
    - Check the base on your own headset with `adb shell getprop ro.build.version.release`.
    - This resolves the G3 gap "which Android base current Quest 2 firmware uses". Whether META-EGL keeps the AOSP blob cache is a separate question (GX-C5, KU-04).

### 6.3 WarmUp on GLES

- **G3-019** In Unity 6.1 and later, GraphicsStateCollection is the recommended warm-up method on OpenGLES; on GLES it "automatically fallbacks" to shader warmup. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm-other.html (accessed 2026-09-24; page built 2026-09-15) · Applies to: Unity 6.1+ GLES · Evidence: [doc]
  - Round-1 audit spot-check: the page was re-read. The GLES fallback and the 6.1+ requirement are confirmed.

- **G3-020** Four other warm-up methods work on GLES:
  - Experimental.Rendering.ShaderWarmup.
  - Shader.WarmupAllShaders, which warms every variant currently in memory.
  - ShaderVariantCollection.WarmUp.
  - The Preloaded Shaders list, which calls ShaderVariantCollection.WarmUp at startup.

  Unity warns these can create the wrong PSOs on Vulkan, DX12 and Metal because state is missing. That warning does not apply to GLES. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm-other.html (accessed 2026-09-24) · Applies to: Unity 6.x GLES · Evidence: [doc]
  - Notes: WarmupAllShaders can compile far more than a session needs. A traced collection is tighter. Unity publishes no timing.

- **G3-021** Unity documents ShaderVariantCollection.WarmUp as "fully supported on DX11 and OpenGL". Adreno does not recompile on state changes (G3-007). A variant warmed on Quest GLES should therefore not hitch again when later drawn under different states. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/ScriptReference/ShaderVariantCollection.WarmUp.html (accessed 2026-09-24) · Applies to: Quest GLES, Unity 6.x · Evidence: [doc] [verify on device]

- **G3-022** Graphics Settings > Shader loading controls startup warming:
  - "Preload Graphics State Collection" plus "Collection Startup Behavior" (None / BeginTrace / Warmup). PSO tracing only works in development builds.
  - "Preloaded Shaders" with "Preload Shaders After Showing First Scene" and "Preload Time Limit Per Frame (ms)". A time limit of 0 warms everything at once. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/class-GraphicsSettings.html (accessed 2026-09-24) · Applies to: Unity 6.x · Evidence: [doc]
  - Notes: In VR, a blocking warm-up freezes the app's frames. Spread it out with the per-frame limit, or warm during a loading scene.

- **G3-023** GraphicsStateCollection.WarmUp and WarmUpProgressively return a JobHandle, so warming can run synchronously or asynchronously. Setting `traceCacheMisses` records anything created after warmup into a separate cacheMissCollection, which can then be appended to the main collection. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm.html (accessed 2026-09-24) · Applies to: Unity 6.x · Evidence: [doc]

- **G3-024** A 2018 forum report (pre-2023) found ShaderVariantCollection.WarmUp on GLES (Android 7+) caused a long pause, while the same call on Vulkan was fast. [C]
  - Source: https://discussions.unity.com/t/vulcan-and-shadervariantcollection-warmup/700973 (accessed 2026-09-24) · Applies to: older Unity versions; still the right mental model for GLES · Evidence: [community]
  - Notes: My interpretation: warmup on GLES does the real compile and link, so the cost moves into the load. Vulkan warmup of that era did not build complete PSOs. Budget warmup time on GLES inside loading screens. See G3-C2.

- **G3-025** To check whether warmup covered everything: in a development build, play through the content with the Profiler attached and search for Shader.CreateGPUProgram during gameplay. Every hit is a variant the collection missed. With GraphicsStateCollection, `traceCacheMisses` records them for you. [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm.html (accessed 2026-09-24) · Applies to: Unity 6.x · Evidence: [doc]

- **GLES3-GF1-002** Warmup on Quest misses variants that carry the `STEREO_MULTIVIEW_ON` keyword. Several developers found that ShaderVariantCollection warmup still hitched until the multiview keyword was added to the collected variants by hand. Unity 6's GraphicsStateCollection was suggested in the same thread as the better tool. [C]
  - Source: https://discussions.unity.com/t/shadervariantcollection-warmup-not-work-on-oculus-quest-2/920217 (accessed 2026-09-24; posts June 2023 to June 2024) · Applies to: Quest 2 (and Quest by analogy); Unity 2020.3, 2021.3, 2022.3; GLES and Vulkan; Multiview · Evidence: [community] [verify on device]
  - Notes:
    - The mechanism is that an editor-recorded collection holds non-stereo variants, while the device renders with the multiview keyword on.
    - Check it with G3-025: after warmup, any `Shader.CreateGPUProgram` for a variant with `STEREO_MULTIVIEW_ON` means the collection is incomplete.
    - In a GraphicsStateCollection traced on the device, the keyword is captured automatically.

- **GLES3-GF1-003** Warmup can be silently wasted when a shader exists twice: once referenced by the ShaderVariantCollection in the player build and once inside an AssetBundle. The bundle's copy is a different shader object, so its variants are compiled again on first use. A Unity graphics engineer (aleksandrk) advised loading the bundles first and then warming the shaders from the bundle. [C]
  - Source: https://discussions.unity.com/t/shader-warmup-doesnt-seem-to-be-working-on-quest-android/936926 (accessed 2026-09-24; Jan 2024) · Applies to: Quest (model unstated); Unity 2022.3.16f1; GLES3 · Evidence: [community] [verify on device]
  - Notes: The same applies to Addressables. Warm the collection that lives in the same bundle as the shaders.

### 6.4 Precision: `mediump`, `half`, `real` and depth on GLES

- **G3-026** Qualcomm says an Adreno fragment shader running mediump (16-bit) arithmetic can be up to twice as fast and twice as power-efficient as the same shader in highp. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Adreno fragment shaders (Quest 2/3) · Evidence: [doc]
  - Notes: The claim is about fragment shaders; the doc makes no equivalent claim for vertex ALU.
  - Round-1 audit spot-check: Qualcomm's "twice the performance and power efficiency" was re-read. Confirmed.

- **G3-027** Qualcomm recommends strict half-precision types wherever possible. It says relaxed precision (GLSL `mediump` is a hint) "often" produces 16-bit code, which means not always. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest GLES · Evidence: [doc]
  - Notes: GLES has only the mediump hint, not strict 16-bit types. Check the result on device (G3-042).

- **G3-028** Unity maps `half` to `min16float`, which becomes `mediump` on OpenGL and RelaxedPrecision on Vulkan. Player Settings > Shader Precision Model has two modes:
  - "Platform default" gives lower precision on mobile.
  - "Unified" gives lower precision wherever the platform supports it. In Unified, samplers default to full precision unless a texture is declared lower, for example `Texture2D<half4>`. [T] [C]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/SL-Use16BitPrecisionInShaders.html ; https://docs.unity3d.com/6000.5/Documentation/Manual/class-PlayerSettingsAndroid.html (accessed 2026-09-24) · Applies to: Unity 6.x Android/Quest · Evidence: [doc]
  - Notes: In Unity 2021.3 the option was worded "Use full sampler precision by default, lower precision explicitly declared" (pre-2023 naming).

- **G3-029** SRP Core's Common.hlsl turns on HAS_HALF for SHADER_API_MOBILE, SHADER_API_SWITCH or the unified precision model, and PREFER_HALF defaults to 1 (`#ifndef PREFER_HALF`). Together these set REAL_IS_HALF, which makes `half` a `min16float` and `real` a `half`. Most URP math typed `real` therefore runs at mediump on Quest GLES. [T] [C]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl (accessed 2026-09-24) · Applies to: URP on Quest · Evidence: [doc]
  - Notes: If one shader needs `real` at full precision, `#define PREFER_HALF 0` before including Common.hlsl.

- **G3-030** Keep depth data at full float. URP declares `_CameraDepthTexture` with `TEXTURE2D_X_FLOAT` and reads depth input attachments with `FRAMEBUFFER_INPUT_X_FLOAT`; custom shaders that sample depth should use `TEXTURE2D_FLOAT`. On GLES, `TEXTURE2D_FLOAT` expands to `Texture2D<float4>` and `TEXTURE2D_HALF` to `Texture2D<half4>`. [C]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/GLES3.hlsl ; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl (accessed 2026-09-24) · Applies to: URP on Quest GLES · Evidence: [doc]
  - Notes: Unity 2019.4 docs (pre-2023) say a plain `sampler2D` on mobile is a low-precision sampler, with `sampler2D_half` for HDR and `sampler2D_float` for depth. With the "Platform default" model, sampling depth through a plain sampler can cause banding or precision loss.

- **G3-031** Unity's older docs give `half` a range of about ±60000 and about 3 decimal digits. fp16 has a 10-bit mantissa, so the step between values is 0.5 at magnitudes of 512-1024 and 1.0 at 1024-2048. `half` is not safe for world-space positions, large UV tiling, accumulated `_Time`, or depth reconstruction. [C]
  - Source: https://docs.unity3d.com/2019.4/Documentation/Manual/SL-DataTypesAndPrecision.html (accessed 2026-09-24; pre-2023 page) · Applies to: any mediump math on Quest · Evidence: [doc]
  - Notes: The step sizes are IEEE fp16 arithmetic, not a vendor number.

- **G3-032** Unity does not support the `h` literal suffix (`2.0h`); it is treated as float. Qualcomm says type casts, including 32-to-16-bit float conversions, cost ALU instructions. Mixing float literals into half math can add conversions. [T]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/SL-Use16BitPrecisionInShaders.html ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest GLES · Evidence: [doc]
  - Notes: Qualcomm's example is an int4 + 1.0 mistake that grows from one instruction to eight. Look at the actual instruction count in the Adreno Offline Compiler (G3-042).

- **G3-033** A `half` in a constant buffer is stored with 32-bit size and alignment. Using half saves ALU work and registers, not uniform-buffer bytes or bandwidth. [T]
  - Source: https://docs.unity3d.com/6000.5/Documentation/Manual/SL-Use16BitPrecisionInShaders.html (accessed 2026-09-24) · Applies to: Unity 6.x · Evidence: [doc]

- **G3-034** Framebuffer-fetch precision:
  - With EXT_shader_framebuffer_fetch, `gl_LastFragData` defaults to mediump, so reading an RGBA16F target back gives fp16 precision at best.
  - With ARM_shader_framebuffer_fetch_depth_stencil, `gl_LastFragDepthARM` is highp in ESSL 3.00. Reading it waits for earlier fragments, so read it late in the shader. It cannot be combined with `early_fragment_tests`. [C] [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/EXT/EXT_shader_framebuffer_fetch.txt ; https://registry.khronos.org/OpenGL/extensions/ARM/ARM_shader_framebuffer_fetch_depth_stencil.txt (accessed 2026-09-24) · Applies to: Quest 2/3 (both expose both extensions) · Evidence: [doc]

- **G3-035** Unity's GLES path uses OpenGL clip-space depth, not reversed Z:
  - GLES3.hlsl defines `UNITY_NEAR_CLIP_VALUE (-1.0)` and a raw far value of 1.0.
  - Vulkan.hlsl defines `UNITY_REVERSED_Z 1` with near = 1.0.

  Depth precision far from the camera is therefore worse on GLES than on Vulkan for the same near/far planes. [C]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/GLES3.hlsl ; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/Vulkan.hlsl (accessed 2026-09-24) · Applies to: Unity URP on Quest · Evidence: [doc]
  - Notes: EXT_clip_control is exposed on both headsets (G3-067), but the defines show Unity's GLES path does not use it. On GLES, push the near plane out as far as the content allows.
  - Round-1 audit spot-check: the defines were re-read in GLES3.hlsl (`UNITY_NEAR_CLIP_VALUE (-1.0)`, `UNITY_RAW_FAR_CLIP_VALUE (1.0)`, no `UNITY_REVERSED_Z`) and in Vulkan.hlsl (`UNITY_REVERSED_Z 1`, near 1.0, raw far 0.0). Confirmed.

- **GLES3-GF1-007** Unity's public HLSLcc GLSL backend (`toGLSL.cpp`) partly answers KU-01, which GLSL `#version` Unity emits for GLES. [T][C]
  - It writes `#version 100` for GLES2, `#version 300 es` for ES 3.0 and `#version 310 es` for ES 3.1. There is no `320 es` path.
  - An ES 3.x fragment shader gets `precision highp float; precision highp int;` as the default, so only values Unity declared with min-precision (`half`, `min16float`) are emitted as `mediump`.
  - The backend adds `#extension GL_EXT_shader_framebuffer_fetch` only when the shader uses framebuffer fetch.
  - Source: https://github.com/Unity-Technologies/HLSLcc/blob/master/src/toGLSL.cpp (accessed 2026-09-24; repository last pushed 2024-07-16) · Applies to: Unity GLES3 targets, as far as the public HLSLcc matches the shipping compiler · Evidence: [doc] [verify on device]
  - Notes:
    - The public repository is a snapshot. The compiler in Unity 6.x may differ.
    - Consequence for precision: with REAL_IS_HALF on (G3-029), URP `real` math becomes `mediump`, and everything typed `float` stays `highp`.
    - Check it on device: in the Shader Inspector, "Compile and show code" for GLES3, or `glShaderSource` in a RenderDoc Meta Fork GL capture. Read the first line and the precision statements.
    - Because no 320 es path exists, ES 3.2-only GLSL features are not used by Unity-generated shaders even though both headsets expose ES 3.2 (G1-001).
    - Round 2: the shipping compiler has diverged from the public snapshot, at least for compute shaders (GLES3-GF2-005, GX-C10).

- **GLES3-GF2-005** Unity bug UUM-60833: compute shaders compiled for OpenGL ES 3.2 were emitted as `#version 310 es`, which hid ES 3.2-only intrinsics such as `imageAtomicMax`. Unity marks it Fixed on the 2023.3.X (the stream that became 6000.0), 6000.2.X and 6000.3.X ports. [T]
  - Repro: set OpenGLES3 as the graphics API and press "Show compiled code" on a `.compute` asset. Expected `#version 320 es`; actual `#version 310 es` (with `#extension GL_EXT_texture_buffer : require`). Reproduced with 2021.3.34f1, 2022.3.17f1, 2023.2.6f1 and 2023.3.0b3 on macOS.
  - Port status (tracker JSON, re-read 2026-09-24; state 103 / status 3 is Fixed, matching the rendered page):
    - Fixed: 2023.3.X, 6000.2.X, 6000.3.X. No fixed-in patch version is given.
    - Won't Fix: 2021.3.X, 2022.3.X and 2023.2.X (end of life); 6000.1.X, whose note says the issue "has been fixed in Unity 6.0 LTS and on later versions"; and 6000.0.X, with no note.
    - Last updated 2026-05-01.
  - Source: https://issuetracker.unity.com/issues/9889/version-310-es-is-defined-in-compute-shader-instead-of-version-320-es-when-writing-a-compute-shader-in-hlsl-for-opengles-32 ; https://issuetracker.unity.com/api/v1.0/issues/9889 (accessed 2026-09-24) · Applies to: Unity compute shaders on OpenGLES3; broken on 2021.3–2023.2; fixed on 6000.2+ and 6000.3 (6000.0 status inconsistent); Quest 2, Quest 3/3S (ES 3.2 drivers) · Evidence: [community]
  - Notes:
    - This settles part of KU-01. The fix means the compiler shipped in Unity 6.2+ should emit `#version 320 es` for compute on ES 3.2, which the public HLSLcc snapshot (GLES3-GF1-007) cannot. The tracker does not show the emitted text after the fix. For graphics shaders, which `#version` a given `#pragma target` produces on 6.x is still unverified.
    - The 6000.0 port contradicts itself: the 6000.1 note says 6.0 LTS has the fix, but the 6000.0 port is Won't Fix with no fixed-in version. On 6000.0, check "Show compiled code" before relying on ES 3.2 compute intrinsics. [verify on device]
    - Performance relevance: ES 3.2 image atomics let GPU-driven compute (culling, binning, histograms) avoid workarounds on GLES. This matters only to teams writing custom compute for a GLES build.

G3-036 (packed vertex formats for the binning pass) is in §5.4.

### 6.5 Shader cost and per-shader limits

- **G3-037** On A7x GPUs (Quest 3/3S), a graphics shader risks a performance hit each time it passes another multiple of 2000 instructions. Qualcomm says fitting the instruction cache is "usually critical", and a low "% Wave Context Occupancy" can mean long shaders are thrashing it. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 3/3S (A7x); no A6x instruction limit is published for Quest 2 · Evidence: [doc]
  - Round-1 audit spot-check: the Qualcomm spec sheet was re-read. The multiples-of-2000 instructions, 16 UBOs, 16 textures+SSBOs and 32 vertex buffers are confirmed.

- **G3-038** Per-shader resource thresholds, each crossing of which is a potential performance hit:
  - On A7x: every further multiple of 16 unique uniform buffers, 16 textures plus SSBOs combined, and 32 vertex buffers.
  - On A6x through A8x (Quest 2 and Quest 3): every further multiple of 16 unique samplers per pipeline. Fragment and compute shaders share that sampler cache; vertex shaders have their own. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (accessed 2026-09-24) · Applies to: Quest 2 (samplers), Quest 3/3S (all) · Evidence: [doc]

- **G2-069** Adreno 7x per-shader thresholds (Quest 3/3S) and the GLES hard limits on both headsets. The thresholds repeat G3-037 / G3-038: possible performance cliffs at each multiple of 2000 instructions, 32 vertex buffers, 16 unique UBOs and 16 textures+SSBOs, with samplers at N = 16 on A6x to A8x. The GL limits come from the gpuinfo reports. [T]

  | Limit | Quest 2 | Quest 3 |
  |---|---|---|
  | GL_MAX_VERTEX_UNIFORM_BLOCKS | 14 | 14 |
  | GL_MAX_FRAGMENT_UNIFORM_BLOCKS | 14 | 14 |
  | GL_MAX_COMBINED_UNIFORM_BLOCKS | 84 | 84 |
  | GL_MAX_UNIFORM_BLOCK_SIZE | 65536 | 65536 |
  | GL_MAX_TEXTURE_IMAGE_UNITS | 16 | 16 |
  | GL_MAX_VERTEX_UNIFORM_VECTORS | 256 | 256 |
  | GL_MAX_FRAGMENT_UNIFORM_VECTORS | 256 | 256 |
  | GL_MAX_COLOR_ATTACHMENTS / GL_MAX_DRAW_BUFFERS | 8 | 8 |
  | GL_MAX_VARYING_VECTORS | 31 | 31 |

  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (last published 2026-09-22) ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: thresholds for Adreno 7x (Quest 3/3S); limits for Quest 2 and Quest 3; GLES · Evidence: [doc] (thresholds), [measured] (limits)
  - Notes:
    - The GLES limit of 14 UBO blocks per stage sits below the A7x cliff of 16, so a legal GLES shader cannot reach that UBO cliff.
    - Textures are capped at 16 units per fragment stage, exactly at the A7x textures+SSBOs threshold. Adding SSBOs to a shader that already samples 16 textures crosses it.
    - Qualcomm's A6x (Quest 2) instruction-cache limit is not published (KU-29).
    - Round-1 audit spot-check: UBO block size, varyings, vertex UBO blocks and texture units were re-read from both reports. Confirmed.

- **G3-039** GLES has no specialization constants, so an uber-shader that branches on uniforms tends to raise register (GPR) use and reduce occupancy. Qualcomm ranks branch cost from cheapest to worst:
  1. A compile-time constant, which may be free.
  2. A uniform: there is some cost, and both sides may execute.
  3. A value computed per pixel. [T] [C]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest GLES · Evidence: [doc]
  - Notes: My inference for Unity: `dynamic_branch` keywords are uniform branches, while `multi_compile`/`shader_feature` keywords resolve at compile time. You trade register pressure against variant count, and more variants mean more hitches (G3-001) and more blob-cache pressure (G3-012). [verify on device] with Offline Compiler register counts.

- **G3-041** Every interpolated value takes a full 4-component slot and a register. Qualcomm's example is packing two vec2 UVs into one vec4. Both headsets report GL_MAX_VARYING_VECTORS = 31. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]

- **G3-042** How to confirm fp16 is actually used:
  - Snapdragon Profiler: Qualcomm's target is "Fragment ALU Instructions (Half)" much higher than "Fragment ALU Instructions (Full)".
  - Static counts: Qualcomm recommends the Adreno Offline Compiler for instruction and register counts.
  - ovrgpuprofiler: it lists 47 metrics, but Meta's doc shows only the first 11, so whether it has half/full ALU counters is unknown. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc] [verify on device]
  - Notes: Run `adb shell ovrgpuprofiler -m -v` to see the full metric list on your device.

G3-040 (vertex-shader texture fetches run twice on a binner) is in §5.4.

## 7. Adreno extensions per headset

### 7.1 The matrix and what it proves

Rows marked "0582+" or "V@0690+" appeared on Quest 2 only from that driver onward. Every presence value in the matrix comes from gpuinfo device reports, so the matrix as a whole is [measured].

| Extension | Quest 2 | Quest 3 | What it helps | Unity / Meta use (documented?) |
|---|---|---|---|---|
| GL_OVR_multiview, GL_OVR_multiview2 | yes | yes | single-pass stereo (CPU) | yes: Unity Multiview on GLES (G3-046) |
| GL_OVR_multiview_multisampled_render_to_texture | yes | yes | MSAA multiview, resolved on tile | yes, per Unity's Android single-pass stereo manual page (GLES3-GF2-004, round 2); call usage [verify on device] |
| GL_EXT_multisampled_render_to_texture / _2 | yes | yes | MSAA without storing samples | not documented; [verify on device] |
| GL_QCOM_texture_foveated | yes | yes | FFR | Meta FFR on GLES (G3-053); mechanism not documented |
| GL_QCOM_texture_foveated2 | 0582+ | yes | cut-off density (discard) | not documented |
| GL_QCOM_texture_foveated_subsampled_layout | yes | yes | FFR without upscale bandwidth | Unity path needs Vulkan (G3-052) |
| GL_QCOM_shading_rate | 0582+ | yes | per-draw VRS | not documented |
| GL_EXT_fragment_shading_rate (+_attachment, +_primitive) | no | yes | image / primitive VRS | not documented |
| GL_EXT_fragment_invocation_density | yes | yes | shader built-ins under reduced-density shading | not documented |
| GL_EXT_shader_framebuffer_fetch (coherent) | yes | yes | reading color on tile | Unity use on GLES not confirmed; [verify on device] |
| GL_QCOM_shader_framebuffer_fetch_noncoherent | yes | yes | fetch without per-primitive sync | not documented |
| GL_QCOM_shader_framebuffer_fetch_rate | yes | yes | fetch at fragment rate under MSAA | not documented |
| GL_ARM_shader_framebuffer_fetch_depth_stencil | yes | yes | reading depth on tile | not documented |
| GL_EXT_shader_framebuffer_fetch_non_coherent | no | no | — | — |
| GL_EXT_shader_pixel_local_storage | no | no | (Mali-only feature) | — |
| GL_EXT_discard_framebuffer (+ core glInvalidateFramebuffer) | yes | yes | skipping GMEM loads and stores | not documented; [verify on device] |
| GL_QCOM_tiled_rendering | yes | yes | manual tile control (2009 extension) | no |
| GL_QCOM_frame_extrapolation | no | yes | frame extrapolation | no |
| GL_QCOM_motion_estimation | yes | yes | hardware block motion vectors | no |
| GL_EXT_texture_compression_astc_decode_mode | V@0690+ | yes | ASTC decoded to UNORM8 | no |
| GL_KHR_texture_compression_astc_ldr / _hdr | yes | yes | ASTC | yes (texture import) |
| GL_EXT_texture_compression_bptc / rgtc / s3tc(_srgb) | V@0690+ | yes | BCn formats | — |
| GL_EXT_texture_filter_anisotropic | yes | yes | anisotropic filtering | yes (texture settings) |
| GL_IMG_texture_filter_cubic | 0582+ | yes | cubic filtering | no |
| GL_QCOM_texture_lod_bias | no | yes | per-texture LOD bias | unknown |
| GL_QCOM_render_shared_exponent | no | yes | RGB9_E5 render target | unknown |
| GL_QCOM_render_sRGB_R8_RG8, GL_EXT_texture_sRGB_RG8 | no | yes | sRGB R8/RG8 render targets | unknown |
| GL_EXT_clip_control | yes | yes | [0,1] depth range | Unity GLES does not use it (G3-035) |
| GL_EXT_depth_clamp | no | yes | depth clamp | unknown |
| GL_EXT_disjoint_timer_query | yes | yes | GPU timers | profilers / RenderDoc |
| GL_KHR_debug, GL_EXT_debug_marker/label | yes | yes | capture markers | tools |
| GL_KHR_no_error | yes | yes | contexts without error checking | unknown |
| GL_EXT_buffer_storage | yes | yes | persistent mapped buffers | unknown |
| GL_EXT_clear_texture | no | 2026 driver only | glClearTexImage | unknown |
| GL_OES_get_program_binary, GL_QCOM_validate_shader_binary | yes | yes | binary caching | Android EGL cache (G3-009) |
| EGL_IMG_context_priority | yes | yes | context priority | compositor (inferred) |
| EGL_NV_context_priority_realtime | no | yes | realtime priority | compositor (inferred) |
| EGL_ANDROID_native_fence_sync | V@0690+ | yes | fence FDs | runtime |

Round-1 audit spot-check of the matrix, against reports 6387 and 8023:
- Present on both: `EXT_shader_framebuffer_fetch`, `QCOM_shader_framebuffer_fetch_rate`, `QCOM_texture_foveated2`, `QCOM_tiled_rendering`, `OVR_multiview2`, `EXT_multisampled_render_to_texture2`, `KHR_no_error`, `QCOM_shading_rate` and `EXT_texture_filter_anisotropic`.
- Quest 3 only: `QCOM_frame_extrapolation`, `EXT_fragment_shading_rate` and `EXT_clear_texture`.
- Absent on both: `EXT_shader_pixel_local_storage` and `QCOM_binning_control`.

All confirmed.

- **G1-009** Both headsets expose the Qualcomm foveation extensions `GL_QCOM_texture_foveated`, `GL_QCOM_texture_foveated2` and `GL_QCOM_texture_foveated_subsampled_layout`. FFR, and even a subsampled-layout equivalent, therefore exist at the GLES driver level. [T]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; GLES · Evidence: [measured]
  - Notes: Driver support does not mean Unity or Meta expose it. Meta's Unity docs require Vulkan for subsampled layout (G1-036, G3-052).

- **G1-011** Both headsets expose the extensions that let GLES approximate Vulkan load/store and memoryless behaviour: [T]
  - `GL_QCOM_tiled_rendering`;
  - `GL_EXT_multisampled_render_to_texture`, for on-tile MSAA with an implicit resolve;
  - framebuffer fetch: `GL_EXT_shader_framebuffer_fetch`, `GL_ARM_shader_framebuffer_fetch_depth_stencil`, `GL_QCOM_shader_framebuffer_fetch_noncoherent` and `GL_QCOM_shader_framebuffer_fetch_rate`.
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; GLES · Evidence: [measured]
  - Notes: Unity itself offers no memoryless render textures on GLES (GLES3-GF1-001). Its GLES use of the MSRTT and framebuffer-fetch extensions is covered in §3.4 and §7.2.

- **G1-012** Variable-rate shading on GLES: both headsets expose `GL_QCOM_shading_rate`. Only Quest 3 also exposes `GL_EXT_fragment_shading_rate` with `_attachment` and `_primitive`. [T]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://opengles.gpuinfo.org/displayreport.php?id=6387 (accessed 2026-09-24) · Applies to: Quest 2 vs Quest 3; GLES · Evidence: [measured]
  - Notes: No Unity or Meta doc uses these extensions on GLES. See G3-055 and G3-056.

- **G1-014** GPU profiling hooks exist on GLES: both headsets expose `GL_EXT_disjoint_timer_query` and `GL_KHR_debug`. [T]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://opengles.gpuinfo.org/displayreport.php?id=6387 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3; GLES · Evidence: [measured]
  - Notes: Meta's 2019 blog listed per-frame timer queries as a Vulkan benefit. On current drivers the extension exists on GLES too, but timer queries distort tiled timings (G2-034 / G3-068; GX-C9).

- **G1-015 / G3-044** Quest 3 (driver V@0837, 2026) has everything Quest 2 (V@0690, 2023) has, plus these:
  - 13 GL extensions: EXT_clear_texture, EXT_depth_clamp, EXT_fragment_shading_rate (+_attachment, +_primitive), EXT_render_snorm, EXT_shader_implicit_conversions, EXT_texture_sRGB_RG8, KHR_texture_compression_astc_sliced_3d, QCOM_frame_extrapolation, QCOM_render_sRGB_R8_RG8, QCOM_render_shared_exponent and QCOM_texture_lod_bias.
  - 1 EGL extension: EGL_NV_context_priority_realtime.

  Quest 2 itself went from 99 to 110 GL extensions across OS updates (2020 → 2023). Query extensions at runtime rather than hardcoding them per headset. [C]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=5092 ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3 · Evidence: [measured]
  - G1-015 reported the difference as "157 extensions on Quest 3 vs 143 on Quest 2". Those totals do not match the reports' own badge counts, which are 123 GL + 35 EGL for Quest 3 (158) and 110 GL + 34 EGL for Quest 2 (144). Use the badge counts (GX-C3).
  - G1-015 also notes that no Meta or Unity doc ties `GL_QCOM_frame_extrapolation` to AppSW, which is Vulkan-only (G1-031). See G3-062.

- **G3-071** GL_EXT_clear_texture shows up only in the 2026 Quest 3 report (V@0837), not in the 2024 Quest 3 reports (V@0757/V@0767). The same headset gains extensions through OS or driver updates. [C]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=7475 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 3 · Evidence: [measured]
  - Notes: Gate any native-plugin use behind a runtime glGetStringi check.

- **G3-072** GL_QCOM_validate_shader_binary is on both headsets, but the Khronos registry has no public spec for it (404), and no Unity or Meta use is documented. [C]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_validate_shader_binary.txt (404 on 2026-09-24) · Applies to: Quest 2/3 · Evidence: [measured]

- **GLES3-GF1-005** A full walk of the opengles.gpuinfo.org database (8292 reports on 2026-09-24) finds exactly seven Quest reports: [C]
  - Adreno 650 ("Quest"): 5092, 5278, 5808 and 6387. The newest, 6387, was submitted 2023-01-13 (Android 12, driver V@0690).
  - Adreno 740 ("Quest", Android 12, 2024): 7267 and 7475.
  - Adreno 740 ("Quest 3", Android 14, driver V@0837.0.7): 8023, submitted 2026-02-20.

  There is no Quest 2 report after January 2023 and no report identifiable as a Quest 3S or Quest Pro.
  - Source: https://opengles.gpuinfo.org/backend/reports.php (paged listing, filtered by device; accessed 2026-09-24) ; https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://opengles.gpuinfo.org/displayreport.php?id=6387 · Applies to: Quest 2, Quest 3, Quest 3S, Quest Pro · Evidence: [measured]
  - Notes:
    - This confirms the baseline "unverifiable" rows are real gaps and not a search failure.
    - To fill them, dump `glGetString(GL_EXTENSIONS)` / `glGetStringi` on the device. The gpuinfo Android app can also submit a report from the headset (KU-11).

G3-043 (ES 3.2 and AEP on both headsets) is in §1.1.

### 7.2 Framebuffer fetch

- **G2-032** On Quest-class Adreno, `EXT_shader_framebuffer_fetch` (an `inout` color) is expensive and scales per sample with MSAA. The measurement is Meta's, on Quest 1. Meta also discourages emulating Vulkan subpasses on GLES with framebuffer fetch, especially with MSAA. Framebuffer fetch also disables LRZ (G2-083). [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ ; https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES · Evidence: [measured] (the draw-call page: Quest 1, Unity 2018.1.6f1; pre-2023; stale)
  - Notes:
    - The per-sample scaling is what `QCOM_shader_framebuffer_fetch_rate` addresses (G3-058).
    - No Quest 2 or Quest 3 measurement exists. [verify on device] Compare App GPU time with a blend-state version of the same effect.

G3-034 (the precision of `gl_LastFragData` and `gl_LastFragDepthARM`) is in §6.4.

- **G3-057** Framebuffer fetch on Quest:
  - Both headsets expose coherent EXT_shader_framebuffer_fetch, QCOM_shader_framebuffer_fetch_noncoherent and ARM depth/stencil fetch.
  - The QCOM non-coherent mode requires enabling FRAMEBUFFER_FETCH_NONCOHERENT_QCOM and calling glFramebufferFetchBarrierQCOM() where needed. In exchange, it avoids the per-primitive pixel-pipe flushes that coherent fetch implies.
  - EXT_shader_framebuffer_fetch_non_coherent and EXT_shader_pixel_local_storage are not exposed, so Mali-oriented pixel local storage advice does not apply. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shader_framebuffer_fetch_noncoherent.txt ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]

- **G3-058** Under MSAA, QCOM_shader_framebuffer_fetch_rate lets shaders that read `gl_LastFragData` or `gl_LastFragDepthARM` run once per fragment rather than once per sample. Without it, such reads force per-sample shading, up to 4x the fragment work at 4x MSAA. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shader_framebuffer_fetch_rate.txt (accessed 2026-09-24) · Applies to: Quest 2/3 with MSAA · Evidence: [doc]
  - Notes: "Up to 4x" follows from the sample count and is not a measured number. Unity does not document whether it enables this extension.

- **G3-059** URP reads depth input attachments with `FRAMEBUFFER_INPUT_X_FLOAT`. Unity does not document which GL mechanism this compiles to on GLES (EXT framebuffer fetch or ARM depth fetch). [T]
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl (accessed 2026-09-24) · Applies to: URP on Quest GLES · Evidence: [doc] [verify on device]
  - Notes: In a RenderDoc Meta Fork GL capture, open the GLSL of a pass that uses input attachments and search for `gl_LastFragData`, `gl_LastFragDepthARM` or the `#extension` lines.
  - Answered at the library level by GLES3-GF1-008. URP's GLES path does not compile `FRAMEBUFFER_INPUT_*` to framebuffer fetch; it becomes a texture `Load`.

- **GLES3-GF1-008** In SRP Core, `PLATFORM_SUPPORTS_NATIVE_RENDERPASS` is defined in the Vulkan API header (Vulkan.hlsl, line 158) and not in GLES3.hlsl. On GLES, Common.hlsl therefore takes the fallback branch of the `FRAMEBUFFER_INPUT_*` macros: each input attachment is declared as `TEXTURE2D_FLOAT(_UnityFBInputN)` (or the half variant) and read with `.Load()`. [T]
  - That is an ordinary texture read of a resolved render target, not `gl_LastFragData` or `gl_LastFragDepthARM`.
  - Common.hlsl also lists `SHADER_API_GLES3` explicitly in the condition that turns on half-precision types (G3-029).
  - Source: https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl ; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/Vulkan.hlsl ; https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/GLES3.hlsl (accessed 2026-09-24; master branch) · Applies to: URP 17 on GLES (the master branch; older URP versions [verify on device]); Quest 2, Quest 3/3S · Evidence: [doc]
  - Notes:
    - This resolves GX-C6 and agrees with G2-022, which says Native RenderPass has no effect on GLES.
    - Practical consequence: on GLES, any URP pass that reads an input attachment forces the producing pass to store its target to memory and the consumer to sample it. The on-tile saving that Vulkan subpasses give is lost.
    - HLSLcc can emit `GL_EXT_shader_framebuffer_fetch` (GLES3-GF1-007). URP's SRP library does not ask for it on GLES, but a custom shader using Unity's built-in framebuffer-fetch syntax still might. [verify on device]

### 7.3 Foveation and variable-rate shading

- **G1-044 / G2-062 / G3-053** Setting up FFR with the Meta API on GLES:
  - Set `OVRManager.foveatedRenderingLevel`, and optionally `OVRManager.useDynamicFoveatedRendering`; the chosen level then acts as a maximum. Meta's doc does not restrict this to one graphics API.
  - Foveation is not applied to intermediate render targets, such as post-processing, tone mapping and camera stacking.
  - Meta cites up to a 25% gain for pixel-heavy apps. Apps with simple shaders can see a net loss at the low level.
  - For A/B tests, run `adb shell setprop debug.oculus.foveation.level <n>` together with `debug.oculus.foveation.dynamic 0`. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/unity-fixed-foveated-rendering/ ; https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/features/foveatedrendering.html (accessed 2026-09-24) · Applies to: Quest 2/3/3S, Unity with OVRManager · Evidence: [doc]
  - Notes: Eye-tracked foveation (Quest Pro) is out of scope. Unity's foveation page says Unity 6.5+ deprecates the Oculus XR Plug-in; that is a lead for the XR-plugin topic.
  - G1-044 (Oculus plugin docs): FFR without the Unity foveation API works only when the app renders directly into the eye textures. Neither Meta's current Unity FFR page nor the plugin docs restrict FFR itself to Vulkan. Sources: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/oculus-plugin.html ; the deprecated VrApi FFR page https://developers.meta.com/horizon/documentation/native/android/mobile-ffr/ (updated Oct 18, 2024), which covers both GL and Vulkan. The Mobile SDK has been unsupported since Aug 31, 2022.
  - G2-062 (plugin docs): OculusXR legacy FFR breaks when URP does its default final blit. The OpenXR Meta API path gives no FFR when intermediate render targets are used. No Unity or Meta statement says the SRP Foveation API works on GLES on Quest (GX-C8, KU-10). Sources: https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/features/foveatedrendering.html.
  - Round 2: the Unity 6.3/6.6 support reference and OpenXR 1.19 narrow this down (GLES3-GF2-006, GLES3-GF2-007).

- **GLES3-GF2-006** Unity's foveated-rendering docs (Unity 6.3 and 6.6 manuals, OpenXR plug-in 1.19) put the graphics-API restriction on *dynamic* foveation, not on static FFR. [T][C]
  - The "Foveated rendering support reference" lists Unity 2022.3+ and URP as project requirements. Its only graphics-API row applies to Windows standalone XR (DirectX 12 or Vulkan). No API is named for Android standalone. Instead, "both the XR provider plug-in and the device must support foveated rendering".
  - Dynamic foveation, where the level acts as a maximum, requires all of:
    - OpenXR plug-in 1.19 or later;
    - the Vulkan graphics API;
    - the Foveated Rendering feature with Foveated Rendering Method = "Foveated rendering (SRP API)";
    - runtime support for `XR_FB_foveation`, `XR_FB_foveation_configuration`, `XR_FB_foveation_vulkan` and `XR_FB_swapchain_update_state`.
  - The OpenXR plug-in picks its SRP foveation technique in this order: gaze-based fragment density map (FDM), fixed FDM, fragment shading rate (FSR) from a provider texture, then FSR computed in a compute shader from the asymmetric FOVs. The page's only API note is that FDM is disabled on Vulkan devices without `VK_EXT_fragment_density_map`.
  - The Meta ("Legacy") API through the Meta Core XR SDK 68.0+ works on Unity 2022.2+/6+ with OpenXR 1.11.0+, but "does not support foveated rendering when you use intermediate render targets".
  - Source: https://docs.unity3d.com/6000.6/Documentation/Manual/xr-foveated-rendering-support.html ; https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-support.html ; https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/foveatedrendering.html (accessed 2026-09-24; the 6000.6 page was built 2026-09-24) · Applies to: Unity 2022.3–6000.6; URP; OpenXR 1.11+ (static) and 1.19+ (dynamic); Quest 2, Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes:
    - GLES consequence: dynamic foveation through Unity's OpenXR plug-in is documented as Vulkan-only. A GLES build can at most use a fixed level. That makes it a Vulkan-only feature, alongside AppSW, Symmetric Projection, MRR and Subsampled Layout (G1-070 / G2-056).
    - Whether static FFR actually takes effect on GLES through OpenXR is still not stated. Unity lists Quest as Vulkan-only in the OpenXR plug-in (G2-055), so GLES + OpenXR stays off-document (GX-C8, KU-10). On a GLES build, read `SystemInfo.foveatedRenderingCaps` (FoveationImage = VRS, NonUniformRaster = VRR, None = unsupported) before trusting any level sweep.
    - The OculusXR `OVRManager.useDynamicFoveatedRendering` path (G1-044) is a separate, deprecated plug-in and is not covered by this restriction.

- **GLES3-GF2-007** At the OpenXR spec level, Meta's foveation extension is not tied to Vulkan. `XR_FB_foveation` (extension 115) depends only on OpenXR 1.0 and `XR_FB_swapchain_update_state`. The Vulkan-specific part is the separate `XR_FB_foveation_vulkan` (161), which adds `XrSwapchainImageFoveationVulkanFB`, the FDM image. A GLES swapchain-state extension also exists: `XR_FB_swapchain_update_state_opengl_es` (163, which needs `XR_KHR_opengl_es_enable`). [T]
  - Source: https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_FB_foveation.html ; https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_FB_foveation_vulkan.html ; https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_FB_swapchain_update_state_opengl_es.html (accessed 2026-09-24; spec 1.1.63) · Applies to: OpenXR runtimes on Quest; GLES and Vulkan swapchains · Evidence: [doc] [verify on device]
  - Notes:
    - So a GLES OpenXR app *can* request a foveation profile on its swapchain; the runtime would apply it through the Qualcomm GL foveation extensions (G1-009, G2-059). That is my inference; Meta does not document the GLES mechanism.
    - Whether Unity's OpenXR plug-in makes these calls on a GLES swapchain is not documented. Dynamic foveation in Unity additionally requires `XR_FB_foveation_vulkan` (GLES3-GF2-006).
    - Test: GLES + OpenXR build; sweep `debug.oculus.foveation.level` 0–4 with `debug.oculus.foveation.dynamic 0`; watch the `Fov` field in `ovrgpuprofiler -t -v` and App GPU time (G2-064 / G3-054).

- **G2-059** On multiview texture arrays, `QCOM_texture_foveated` sets foveation parameters per array slice with `glTextureFoveationParametersQCOM(texture, layer, focalPoint, focalX, focalY, gainX, gainY, foveaArea)`. The spec names stereo foveated rendering as the main use case. Enable it through `TEXTURE_FOVEATED_FEATURE_BITS_QCOM` (`FOVEATION_ENABLE_BIT_QCOM | FOVEATION_SCALED_BIN_METHOD_BIT_QCOM`). [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated.txt ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES; native code · Evidence: [doc]
  - Notes: In a Unity app this is set by the runtime or compositor on the swapchain texture, not by app code (G2-061).

- **G2-060 / G3-050** QCOM_texture_foveated sets foveation per texture: focal point, gain and fovea area, set per layer for texture arrays. Three limitations matter for Unity:
  - Only one render-target attachment is foveated.
  - `gl_FragCoord` is scaled, but dFdx/dFdy and interpolateAtOffset are not corrected. Screen-space effects inside a foveated pass see distorted derivatives.
  - Depth inherits foveation and should be invalidated. Attachments must be cleared or invalidated before rendering, otherwise the driver reloads ("unresolves") them. [T] [C]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated.txt (accessed 2026-09-24; spec rev 5, 2017) · Applies to: Quest 2/3 GLES · Evidence: [doc]
  - G2-060 adds two spec rules (issue numbers from rev 5). A Load action on the foveated attachment makes the driver unresolve it, which can silently disable FFR for that pass (issue 7). Paths that bypass tiling, such as tessellation, geometry shaders and compute, may also disable foveation (issue 9). `gl_SamplePosition` is not corrected either (issue 4).

- **G2-061** On Quest GLES, FFR is a property of the texture, applied through the compositor swapchain. It affects only rendering directly into the swapchain texture: [T]
  - If URP renders the scene to an intermediate texture and then blits to the swapchain, the main pass gets no FFR.
  - The final full-screen pass (no depth, no MSAA) runs in direct mode, which also turns FFR off (G2-086).
  - So a two-pass Unity GLES pipeline gets no FFR at all.
  - Source: https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES · Evidence: [doc]
  - Notes: Check it with G2-064 / G3-054. If App GPU time does not change across FFR levels, the main pass is not foveated.

- **G3-051** QCOM_texture_foveated2 (Quest 2 from driver V@0582, and Quest 3) adds TEXTURE_FOVEATED_CUTOFF_DENSITY_QCOM (0-1). Pixels whose density falls below the cutoff are discarded. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated2.txt ; https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]
  - Notes: Meta's FFR maps show black regions where the GPU renders nothing. Linking those regions to this cutoff is my inference; Meta does not name the extension.

- **G2-064 / G3-054** Two ways to check that foveation is active:
  - `ovrgpuprofiler -t -v` prints a "Fov x/y" (or per-eye "Fov L R") field for each bin.
  - With dynamic foveation, VrApi logcat lines carry a "Fov=" postfix. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ ; https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/ (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]
  - G2-064 adds the level values for `debug.oculus.foveation.level`: 0 off, 1 low, 2 medium, 3 high, 4 high-top. Set `debug.oculus.foveation.dynamic 0` first, otherwise the level only acts as a maximum. VrApi logcat shows `Fov=3`, or `Fov=3D` when dynamic. Source: https://developers.meta.com/horizon/documentation/unity/os-fixed-foveated-rendering/.

- **G3-055** QCOM_shading_rate (Quest 2 from V@0582, and Quest 3) sets the shading rate per draw, from 1x1 to 4x4, on GLES. Qualcomm says VRS and foveation can be used together. No Unity GLES path is documented for it. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shading_rate.txt ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]

- **G3-056** Only Quest 3 exposes EXT_fragment_shading_rate with its _attachment and _primitive variants, which allow image-based and per-primitive shading rates on GLES. Quest 2 is limited to the per-draw QCOM_shading_rate. [T]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://registry.khronos.org/OpenGL/extensions/EXT/EXT_fragment_shading_rate.txt ; https://docs.unity3d.com/6000.5/Documentation/Manual/xr-foveated-rendering-support.html (accessed 2026-09-24) · Applies to: Quest 3/3S (via the shared GPU) · Evidence: [measured]
  - Notes: Unity's foveated-rendering support page covers URP on 2022.3+ and SystemInfo.foveatedRenderingCaps, but it does not say whether Unity drives either VRS extension on GLES. [verify on device] Read SystemInfo.foveatedRenderingCaps in a GLES build.

G3-052 (subsampled layout needs Vulkan in Unity) is merged under G1-035 in §2.2. Eye-tracked foveation is Quest Pro only and out of scope.

### 7.4 Tile control, Quest 3-only formats and other extensions

- **G2-091 / G3-061** QCOM_tiled_rendering (spec from 2009, pre-2023) exposes manual tile control through StartTilingQCOM/EndTilingQCOM with preserve masks. The spec warns that mixing app-controlled tiling with normal rendering can double resolve cost. There is no documented Unity use; ignore it for Unity projects. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_tiled_rendering.txt (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]
  - G2-091 adds the API detail: `glStartTilingQCOM(x, y, w, h, preserveMask)` and `glEndTilingQCOM(preserveMask)`, with color, depth, stencil and multisample preserve bits. Flush, Finish or rebinding the FBO ends tiling implicitly. It can only be reached from a native rendering plugin.

- **G2-092** `QCOM_binning_control` is NOT in the Quest 2 or Quest 3 GLES extension strings. `glHint(GL_BINNING_CONTROL_HINT_QCOM, …)` with CPU_OPTIMIZED, GPU_OPTIMIZED or RENDER_DIRECT_TO_FRAMEBUFFER therefore cannot force binned or direct mode on Quest. Where the extension does exist, changing the hint anywhere except just before a render-target change or after a swap carries a large penalty. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_binning_control.txt (Draft, 2012) ; https://opengles.gpuinfo.org/displayreport.php?id=6387 ; https://opengles.gpuinfo.org/displayreport.php?id=8023 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S · Evidence: [measured] (absence from the reports) · [verify on device] for current drivers
  - Notes:
    - FlexRender's choice is not exposed. The only lever is to avoid its triggers (§3.5; KU-39).
    - Round-1 audit spot-check: the extension was confirmed absent from both reports.

- **G3-062** QCOM_frame_extrapolation, on Quest 3 only, provides `ExtrapolateTex2DQCOM(src1, src2, output, scaleFactor)`. The scale factor is 0.5 for extrapolating every other frame. Formats are RGBA8, RGB8, R8, RGBA16F, RGB16F, RGBA32F and RGB32F. Qualcomm says frame extrapolation can nearly double a fragment-bound app's framerate. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_frame_extrapolation.txt ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: Neither Meta nor Unity documents any use of it in apps. The Quest runtime handles frame timing and reprojection, so treat this as unavailable to Unity content. QCOM_motion_estimation (both headsets, block motion vectors) has the same status.

- **G3-063** EXT_texture_compression_astc_decode_mode (Quest 2 from driver V@0690, and Quest 3) sets TEXTURE_ASTC_DECODE_PRECISION_EXT. ASTC decodes to RGBA16F by default; decoding LDR textures to UNORM8 reduces texture-cache footprint and power. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/EXT/EXT_texture_compression_astc_decode_mode.txt (accessed 2026-09-24) · Applies to: Quest 2 (newer drivers), Quest 3 · Evidence: [doc]
  - Notes: Unity does not document setting this. It would take a native plugin. No published Quest gain number exists; measure "% Texture L1 Miss" / "L1 Texture Cache Miss Per Pixel" with ovrgpuprofiler `-r5,6`.

- **G3-064** Anisotropic filtering is on both headsets. Qualcomm says its cost scales with the degree of anisotropy: a 16x lookup can be 16x slower, though the cost is only paid where anisotropy actually occurs. Qualcomm also lists trilinear filtering, wide formats, 3D textures and dFdx/dFdy gradients as adding sampling time. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]
  - The value of GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT was not captured for either headset (KU-30).

- **G3-065** QCOM_render_shared_exponent (Quest 3 only) makes RGB9_E5 renderable, giving a 32-bit-per-pixel HDR color target in place of 64-bit RGBA16F. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_render_shared_exponent.txt (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc]
  - Notes: Unity does not document mapping to this format on GLES. It is not available on Quest 2.

- **G3-066** QCOM_texture_lod_bias (Quest 3 only) brings back a per-texture LOD bias, which OpenGL ES dropped after 1.1. The spec says a positive bias may improve filtering performance at the cost of blur. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_lod_bias.txt (accessed 2026-09-24) · Applies to: Quest 3/3S · Evidence: [doc] [verify on device]
  - Notes: Whether Unity's Texture.mipMapBias uses this on Quest 3 GLES, and what it does on Quest 2, is unknown. Test by visual comparison.

- **G3-067** EXT_clip_control (both headsets) allows the D3D-style [0,1] depth range, and the spec says it may improve depth precision. Unity's GLES path keeps the OpenGL -1..1 convention (G3-035), so this benefit goes unused in Unity. [C]
  - Source: https://registry.khronos.org/OpenGL/extensions/EXT/EXT_clip_control.txt (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]

- **G3-069** Context priority: EGL_IMG_context_priority is on both headsets, while EGL_NV_context_priority_realtime appears only on Adreno 740 (Quest 3). Render-stage traces include a "Preempt" stage. [C]
  - Source: https://opengles.gpuinfo.org/displayreport.php?id=8023 ; https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [measured]
  - Notes: Reading Preempt as the compositor's higher-priority context interrupting the app is my inference; Meta does not explain the stage in these pages. Preempt time on app surfaces is time the app does not control.

- **G3-070** EXT_buffer_storage (both headsets) provides persistent, coherent mapped buffers (MAP_PERSISTENT_BIT_EXT, MAP_COHERENT_BIT_EXT). They help native plugins that stream vertex or constant data. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/EXT/EXT_buffer_storage.txt (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]
  - Notes: Unity's use of them on GLES is not documented.

- **GLES3-GF1-001** Unity's `RenderTexture.memorylessMode` works only on Metal (iOS, tvOS, visionOS) and on Vulkan on Android platforms, with Meta Quest named as an example. GLES has no memoryless render textures in Unity. [T]
  - Source: https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture-memorylessMode.html (accessed 2026-09-24) · Applies to: Unity 6000.3 (earlier versions [verify on device]); Quest 2, Quest 3/3S; GLES vs Vulkan · Evidence: [doc]
  - Notes:
    - On GLES the nearest equivalents are an invalidate at the end of the pass (G3-060, §3.2) and MSRTT for MSAA attachments (G3-048). Neither saves the allocation, only the store bandwidth.
    - This is one more Vulkan-only lever to include in the §2.9 decision table. Its value is memory footprint, not frame time.

## 8. Capture and profiling on GLES

### 8.1 RenderDoc Meta Fork

- **G3-073** RenderDoc Meta Fork supports both OpenGL and Vulkan apps. Vulkan shader stats (through KHR_pipeline_executable_properties) and API validation are Vulkan-only. The app must be a development build. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ (accessed 2026-09-24; page reported as updated Sept 9, 2026) · Applies to: Quest 2/3/3S GLES · Evidence: [doc]
  - Notes: On GLES you get no per-shader register or instruction stats inside RenderDoc. Use the Adreno Offline Compiler instead (G3-042).
  - Round-1 audit spot-check: the page (updated 2026-09-09) was re-read. OpenGL and Vulkan support, the Vulkan-only shader stats and validation, and the development-build requirement are confirmed.

- **G3-074** Non-debuggable builds need JDWP, which Android 14 disables by default. Meta's workaround requires root (`adb root`, `setprop persist.debug.dalvik.vm.jdwp.enabled 1`, reboot), which is not available on retail headsets. In practice, capture a Development Build. Use the profiling-mode replay context. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-capture/ (accessed 2026-09-24) · Applies to: Quest on the Android 14 base · Evidence: [doc]

- **G3-075** RenderDoc profiling mode puts the headset into detailed GPU profiling. This costs 5-10% GPU performance and pins the GPU at its maximum clock. Treat absolute times as best-case clocks, not shipping clocks. [T] [C]
  - Source: https://developers.meta.com/horizon/blog/renderdoc-for-oculus/ (accessed 2026-09-24; blog dated 2020-09-03; pre-2023, stale) · Applies to: Quest GLES/Vulkan · Evidence: [doc]
  - Notes: Compare with the level-based clocks the app actually runs at, such as Quest 3 at 690 MHz (G3-081).
  - Round-1 audit spot-check: the blog post is dated 2020-09-03 (pre-2023; stale). The 5–10% GPU cost and the pinned maximum clock are confirmed in its text.

- **G3-076** Three settings under Tools > Settings in RenderDoc Meta Fork:
  - Timer query type defaults to per-renderpass. Meta says per-draw duration queries are inaccurate on tiled GPUs.
  - Enable "Disable TimeWarp on replay".
  - Set "Replay optimisation level" to Fastest. Otherwise the extra GL commands RenderDoc inserts show up as phantom operations in render-stage traces. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ (accessed 2026-09-24) · Applies to: Quest GLES · Evidence: [doc]

- **G3-077** On OpenGL, per-draw time_elapsed queries make the GPU stall between draws within each tile, which inflates per-draw GL timings. Per-renderpass timestamps add no overhead. [T]
  - Source: https://developers.meta.com/horizon/blog/renderdoc-for-oculus/ (accessed 2026-09-24; blog dated 2020-09-03; pre-2023, stale) · Applies to: Quest GLES · Evidence: [doc]
  - Notes: For GL cost per draw, use the draw-call trace counters and the Tile Timeline stage times, not the clock button in per-draw mode.

- **G3-078** RenderDoc's Tile Timeline (Window > Tile Timeline) shows:
  - Per-surface render stages, in microseconds, for each tile: Binning, Render, LoadColor, StoreColor, LoadDS, StoreDS, Blit and Preempt. GLAsyncCompute is the GL-specific stage for compute.
  - Surface info: bin count, bin size, stage count and rendered bins.
  - A draw-call trace in the Performance Counter Viewer with up to 48 metrics. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/ ; https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/ (accessed 2026-09-24) · Applies to: Quest GLES · Evidence: [doc]

- **GLES3-GF1-004** RenderDoc Meta Fork 68.18 (released 2026-07-28) fixes an "Adreno timing hang" and adds `--frame-number` and `--intent-args` capture options. The download page says profiling features need Horizon OS 68 or later. [T][C]
  - Source: https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S on Horizon OS 68+; GLES and Vulkan · Evidence: [doc]
  - Notes:
    - The note does not say whether the timing-hang fix is GL-specific. Earlier versions could hang while collecting GPU timings, so update before profiling GLES content.
    - `--frame-number` makes captures repeatable when comparing API or setting A/Bs.

### 8.2 ovrgpuprofiler

- **G2-010** A repro-grade capture recipe, as used by Unity QA on Quest 2, 3 and 3S: [C]
  1. `adb shell setprop debug.oculus.gpuLevel 3`
  2. `adb shell setprop debug.oculus.cpuLevel 3`
  3. `adb shell setprop debug.oculus.sysPropDebug 1` and `adb shell setprop debug.oculus.headlock 1`. The round-1 audit added these from the report's steps; `headlock` fixes the head pose so the view is repeatable.
  4. `adb shell ovrgpuprofiler -e`, run BEFORE the app starts; otherwise restart the app.
  5. `adb shell ovrgpuprofiler -t 2`.
  6. Read total, Binning, Render and StoreColor for the eye-buffer surface.

  Locking GPU and CPU levels removes clock-scaling noise from the comparison.
  - Source: https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 (accessed 2026-09-24) · Applies to: Quest 2, Quest 3/3S; GLES and Vulkan; Unity 6000.x · Evidence: [community]
  - Notes:
    - The property names come from a Unity QA report, not from a Meta doc page captured here. The skill's ADB helper should cite Meta's own documentation for `gpuLevel`/`cpuLevel` (quest-perf bundle) and treat `sysPropDebug`/`headlock` as [verify on device].
    - Level 3 is not the level a shipping app runs at. Use it for A/B deltas, not absolute budgets.

- **G3-079** Qualcomm's guideline is to keep binning passes at 10-20% of a render pass, with 30% "usually too much". It appears under the Vulkan metrics heading, but Binning time is visible on GL surfaces in RenderDoc and ovrgpuprofiler stage traces. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html (accessed 2026-09-24) · Applies to: Adreno generally · Evidence: [doc]
  - Notes: A high binning share points at vertex cost, including vertex texture fetches (G3-040).
  - Round-1 audit spot-check: Qualcomm's "10–20%" and "30% usually too much" were re-read. Confirmed.

- **G3-080** ovrgpuprofiler works with GLES apps; Meta documents no API restriction. Its options:
  - `-m` lists the metrics (47).
  - `-r<ids>` streams real-time metrics.
  - `-e [package]` turns on detailed mode (restart the app), `-i` queries it, `-d` turns it off. Detailed mode is required for render-stage traces.
  - `-t` traces, 0.1 s by default (`-t1.2` for longer). `-v` expands per-bin stages.
  - `-s` gives per-stage metrics; `-x` gives per-draw traces with LRZ state.

  Each surface line shows resolution, bit depths, MSAA, Mode (0 Direct, 1 HwBinning, 2 SwBinning, 3 HwDirect), bin count and size, milliseconds, and stage totals. [T]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc]
  - Notes: A GL eye buffer that runs in Direct or SwBinning mode where HwBinning is expected is a red flag; see G3-040.
  - Round-1 audit spot-check: the page (updated 2026-09-09) was re-read. The 47 metrics, the flags and Modes 0–3 are confirmed.

- **G3-081** Meta says Quest 3 and Quest 3S both use the Adreno 740v3, clocked at 690 MHz and 492 MHz respectively. A GPU-bound GLES title tuned on Quest 3 therefore has about 71% of the clock on 3S (492/690). [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 3 vs 3S · Evidence: [doc]
  - Notes: The ratio is arithmetic on Meta's numbers. Real performance also depends on other hardware differences, which are out of scope here.
  - Round-1 audit spot-check: 690 MHz and 492 MHz were re-read on the same page. Confirmed.

- **G3-087** Qualcomm's quick-start targets use the same counter names as ovrgpuprofiler, so the thresholds carry over. They are generic Adreno values, not Quest-specific:
  - % Texture Fetch Stall (ovrgpuprofiler id 4): under 2%; a sustained 16% or more is usually too high.
  - % Stalled on System Memory (id 8): under 2%.
  - % Vertex Fetch Stall (id 3): usually 0%.
  - % Shaders Stalled: under 10%.
  - % Wave Context Occupancy: 50% or more.
  - % CP Overhead: near 0%, never above 20%.
  - Average Polygon Area: at least 4 pixels.
  - % Prims Clipped (id 11) and % Prims Trivially Rejected (id 10): under 2%. [T]
  - Source: https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html ; https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/ (accessed 2026-09-24) · Applies to: Quest 2/3 (generic Adreno thresholds) · Evidence: [doc]
  - Notes: The ids are from the first 11 entries shown in Meta's doc. Check the remaining ids with `ovrgpuprofiler -m` on the device.

### 8.3 Timer queries on a binner

- **G2-034 / G3-068** EXT_disjoint_timer_query (both headsets) provides TIME_ELAPSED_EXT and TIMESTAMP_EXT queries. Always check GPU_DISJOINT_EXT. On Adreno in binning mode:
  - A timer query sums over all bins.
  - Each timed draw adds about 2-5 µs of overhead per tile.
  - Issue timer queries inside a render pass.
  - Meta says per-draw timing on Quest's tiled GPU is inaccurate. [T]
  - Source: https://registry.khronos.org/OpenGL/extensions/EXT/EXT_disjoint_timer_query.txt ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html ; https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/ (accessed 2026-09-24) · Applies to: Quest 2/3 · Evidence: [doc]
  - G2-034 adds three distortions:
    - A5x and later trim the tail of the visibility stream, but a final full-screen draw defeats that.
    - On GLES a timer query forces a flush, and later invalidates are then ignored (G2-006).
    - OVR_multiview does not allow timer queries inside multiview rendering.
  - G2-034's rule: use ovrgpuprofiler stages, not `GL_EXT_disjoint_timer_query`, for per-pass cost on Quest.
  - Qualcomm's advice to issue timer queries inside a render pass conflicts with Meta's warning that a query forces a flush. See GX-C9.

### 8.4 Perfetto, Snapdragon Profiler and AGI

- **G3-082** Perfetto through MQDH offers GPU Metrics, GPU Render Stage Trace, "Enable high precision GPU render stage tracing" and a GPU trace buffer size. Unity only emits ATrace events, so enter the app's package name under ATrace Apps. Meta documents no API restriction. [T] [C]
  - Source: https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/ (accessed 2026-09-24) · Applies to: Quest 2/3/3S · Evidence: [doc] [verify on device]
  - Notes: This is the best tool for tying a CreateGPUProgram hitch (Unity markers) to GPU render stages on one timeline. If the trace drops data, increase the buffer size.

- **G3-083** GPU Systrace was deprecated on December 2, 2024 in favour of the Perfetto integration. It needed `adb shell ovrgpuprofiler -e`. Older Quest profiling guides that use it are stale. [T]
  - Source: https://developers.meta.com/horizon/documentation/unreal/ts-gpusystrace/ (accessed 2026-09-24) · Applies to: Quest · Evidence: [doc]

- **G3-084** Meta's Snapdragon Profiler page now returns 404. The 2020 archived version (pre-2023) said:
  - Start SDP before launching the app.
  - Only apps that declare the OpenGL requirement in the manifest appear.
  - Enable "OpenGL ES > Rendering stages" for traces; snapshots are possible.
  - Quit SDP before unplugging.

  Qualcomm's current SDP guide still lists OpenGL ES trace and snapshot, and says SDP adds about 5% CPU overhead even when tracing only framerate. [T]
  - Source: http://web.archive.org/web/20200513224546/https://developer.oculus.com/documentation/native/android/mobile-snapdragon-profiler/ ; https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html (accessed 2026-09-24) · Applies to: Quest 2 era; current status unknown · Evidence: [doc]
  - Round-1 audit spot-check: Qualcomm's "about 5% CPU overhead" was re-read on the SDP page. Confirmed.

- **G3-085** Community sources say three things about SDP on Quest:
  - It does not work with Vulkan on Quest.
  - Snapshot captures crash on Quest 2.
  - A Qualcomm forum thread is titled "Snapdragon Profiler not able to capture anything on Meta Quest 3/3S"; it could not be read here because of a certificate error.

  Treat SDP on current Horizon OS as unreliable, even for GLES. Prefer ovrgpuprofiler, RenderDoc Meta Fork and Perfetto. [T]
  - Source: https://mysupport.qualcomm.com/supportforums/s/question/0D5dK000009EniESAS/snapdragon-profiler-not-able-to-capture-anything-on-meta-quest-33s ; https://peterthor.se/tag/qualcomm-snapdragon-profiler/ (accessed 2026-09-24; content seen via search snippets only) · Applies to: Quest 2/3/3S · Evidence: [community]
  - Round-1 audit: a new search found no current authoritative statement from Meta or Qualcomm on Snapdragon Profiler support for Quest. Status unchanged (KU-35).
  - Round 2: the Qualcomm thread is a JavaScript-rendered Salesforce page. It is still unreadable without a browser (the certificate error persists, and fetching it with certificate checks off returns only the page shell). Browser tools were out of bounds for this audit. See GLES3-GF2-008 for the only current Meta mention.

- **GLES3-GF2-008** Meta's current developer docs still list Snapdragon Profiler as a usable third-party tool, but only generically. The Unreal "Testing and Performance Analysis" page says that because Quest "uses a Qualcomm chipset", SDP can analyse CPU, GPU, DSP, memory, power, thermal and network data. It says nothing about GLES vs Vulkan, rendering-stage traces, snapshots or OS-version limits. No Unity-section page mentions SDP. [T]
  - Source: https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android/ (accessed 2026-09-24) · Applies to: Quest (engine-agnostic statement on an Unreal page) · Evidence: [doc] [verify on device]
  - Notes:
    - This is a generic mention and does not outweigh the specific failure reports in G3-085. Meta's dedicated SDP page is gone (G3-084), and Meta's own capture stack is ovrgpuprofiler, Perfetto and RenderDoc Meta Fork.
    - For a GLES skill: try SDP only as a secondary tool. Launch SDP before the app, enable "OpenGL ES > Rendering Stages", and fall back to ovrgpuprofiler `-t -v` if nothing is captured (KU-35).

- **G3-086** AGI is not usable on Quest:
  - It needs Android 11+ and a debuggable app, and its supported-device list includes no Quest headset.
  - Its frame profiler traces GLES by running the app through a custom ANGLE build that translates to Vulkan, so the timings do not reflect Adreno's native GL driver.
  - The system-profiler page only mentions Vulkan API tracing. The last release is v3.3.3 (2025-01-20). [T]
  - Source: https://developer.android.com/agi/supported-devices ; https://developer.android.com/agi/frame-trace/frame-profiler (accessed 2026-09-24; pages updated 2026-02-26 and later) · Applies to: Quest (not supported) · Evidence: [doc]

## Conflicts

Topic conflicts are kept verbatim from the notes, with their original IDs. Cross-topic conflicts found at synthesis are GX-C1 to GX-C9. The round-1 audit corrections close the section.

### G1 conflicts (versions and API decision)

- **G1-C1** Relative Vulkan vs GLES performance on Quest in Unity.
  - Vulkan is better or equal:
    - Unity's untethered-XR guide says Vulkan is more stable and faster (https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html, [doc]).
    - Meta calls Vulkan lower-overhead and recommends it (https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/, [doc]).
    - Unity staff cite internal tests showing parity (https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926, [community]).
  - Vulkan is worse:
    - Unity QA repros UUM-93226 and UUM-30269 (72 vs 50 fps) (https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23, [community]).
    - Unity staff in 2023 acknowledged Vulkan was slower in many scenarios (https://discussions.unity.com/t/xr-perf-quest-2022-2-and-trunk-vulkan-vs-gles-perf-disparity-increased-significantly-6223/1726043, [community]).
    - Community measurements in threads 1561926, 938162, 1203082 and 1322298 ([community]).
  - Assessment: the measured evidence (2021–2025, MSAA scenes) favours GLES. The doc claims carry no numbers. No measurement exists for the configuration Unity recommends on 6.1+ (OBD + Symmetric Projection + MRR + on-tile). Treat parity as unproven and measure per project.

- **G1-C2** Root cause of the Vulkan gap.
  - Unity's Dec 2025 tracker note blames a Qualcomm visibility-stream bug plus a Qualcomm-side cost for Vulkan buffer copies, to be fixed by Meta OS (http://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3, [community]).
  - Unity staff in Dec 2024 blamed a suboptimal renderer setup (too many stores) (https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926, [community]).
  - The community traced it to URP PR #4488's MSAA depth-copy strategy, which was reverted only for GLES3 by PR #4705 (https://discussions.unity.com/threads/horrible-performance-on-vulkan-with-simple-scene-quest-2.1203082/, [community]).
  - Assessment: the causes are probably layered: engine store/resolve choices plus a driver cost. Both the RenderDoc store-count evidence and the unexplained 1.5 ms blit fit this. None of the fixes is confirmed shipped.

- **G1-C3** GPU skinning on GLES.
  - A July 2026 forum post says GPU skinning is unavailable on OpenGL ES (https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926?page=2, [community]).
  - Unity's Android Player settings list GPU / GPU (Batched) skinning with no API restriction (https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html, [doc]).
  - Assessment: unresolved. Verify on device with the Profiler and Frame Debugger (skinning dispatches vs CPU skinning markers).
  - Round-2 update: the docs lean towards "available". `MeshDeformation.GPU` and `GPUBatched` are compute-shader paths; Unity lists compute on "OpenGL ES 3.1 on Android"; both headsets expose ES 3.2 with 24 (Quest 2) or 36 (Quest 3) compute SSBO blocks (GLES3-GF2-001, [doc] + [measured]). The forum claim cites no source. It stays open only because no source confirms GLES skinning on Quest end to end.

- **G1-C4** Whether Vulkan improves GPU time.
  - Meta in 2020 said Vulkan would bring no GPU improvement in nearly all cases, only CPU (https://developers.meta.com/horizon/blog/vulkan-support-for-oculus-quest-in-unity-experimental/, [doc], stale).
  - Meta's current docs claim GPU wins from Vulkan-only features: Symmetric Projection 5–15% and MRR 3–8% (https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/, [doc]).
  - Community reports show Vulkan costing more GPU: 25% vs 44% utilisation, 6+ ms (https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926, [community]).
  - Assessment: the base API is not GPU-faster. Any GPU gain comes from the Vulkan-only features, which must outweigh the store/resolve cost.

- **G1-C5** Is Vulkan more stable?
  - Unity's 6.6 docs say Vulkan is more stable than GLES for URP XR (https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html, [doc]).
  - Unity QA observed significantly more stutter on Vulkan, and the issue was closed Won't Fix (https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23, [community]).
  - Assessment: "stability" in the docs probably means correctness and crashes, while the tracker is about frame pacing. They are not strictly contradictory, but a skill should not present the stability claim as if it covered frame pacing.

- **G1-C6** Meta's recommended production API over time.
  - 2022 community advice said Meta recommended GLES for production (https://discussions.unity.com/threads/serious-performance-regression-of-using-vulkan-vs-opengl-in-unity-2021-3-8-lts.1322298/, [community], stale).
  - The current Meta page recommends Vulkan and calls GLES legacy (https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/, [doc]).
  - Assessment: the current doc supersedes the old advice. Drop the 2022 advice.

### G2 conflicts (tile, MSAA, multiview, driver)

- **G2-C1** Meta's "Advanced GPU Pipelines" page calls Vulkan the *required* API and keeps its GLES content "for historical reference". Meta's "OpenGL ES and Vulkan" page says Vulkan is recommended and GLES is still supported (legacy). The OculusXR 4.x plugin still lists OpenGL ES 3.0 as supported. Resolution: GLES builds still run, but no new Meta features target GLES; treat "required" as policy direction, not a runtime block.
- **G2-C2** Unity's RenderBufferLoad/StoreAction docs say OpenGL ES takes advantage of load/store actions. UUM-45041 (Won't Fix) shows the GLES backend skipping glInvalidateFramebuffer in some passes. That repro was on PowerVR and Mali, and it did not reproduce on Adreno 610. The Quest behaviour is unverified; check the ovrgpuprofiler Load*/Store* stages.
- **G2-C3** The sources disagree on MSAA cost:
  - Qualcomm: MSAAx2 is "likely practically free".
  - Meta draw-call study (Quest 1, 2018): MSAA has a real cost.
  - UUM-149765: 4x costs +3.3 ms (GLES, Quest 3/3S) and about +7 ms (Quest 2).

  No 2x measurement on Quest was found.
- **G2-C4** Meta says clear and invalidate cost about the same on Qualcomm. Qualcomm's sample shows a *partial* clear (depth without stencil on D24S8) costing 37%. These are consistent once you note that a partial clear still forces a load of the uncleared aspect; the practical rule is "clear or invalidate every aspect".
- **G2-C5** Invalidation advice pulls two ways:
  - "Invalidate as early as possible" and "invalidate depth at the end of every pass" (Meta, Qualcomm) cut GMEM traffic.
  - Qualcomm's concurrent-binning section instead suggests reusing one Z-buffer *without clears or invalidations* across passes.

  This matters only on Adreno 7x (Quest 3/3S); measure both on multi-pass frames.
- **G2-C6** Qualcomm says to avoid glFenceSync/glClientWaitSync on Adreno GLES. The Khronos wiki streaming guidance uses fences to recycle ring-buffer regions. Resolution for Quest: prefer orphaning or a ring sized for the frames in flight. If a fence is unavoidable, poll it without flushing mid-pass.
- **G2-C7** Meta recommends Vulkan for performance, but the measurements are mixed:
  - UUM-149765: GLES 4xMSAA is cheaper than Vulkan on Quest 3 (13.0 vs 14.1 ms) and similar on Quest 2.
  - UUM-93226 (Won't Fix): Vulkan is slower than GLES on Quest 2/3 because of excessive buffer copies.

  Unity's Vulkan backend is not uniformly faster on Quest.
- **G2-C8** OpenXR's documentation lists Quest as Vulkan-only, yet several Unity issue repros (UUM-109377, UUM-102876) exercise GLES XR on Quest in Unity 6000.x. Those use the OculusXR plugin, which is deprecated from Unity 6.5. GLES + OpenXR on Quest is off-document.
- **G2-C9** UUM-149765 is internally inconsistent. The step-7 table gives Quest 3 GLES 9.7 / 13.0 ms (MSAA off / 4x), while its notes give Quest 3 GLES about 12 / 15 ms and Vulkan about 11 / 16. The table may come from the Quest 3S unit whose driver the report lists. Use the deltas, not the absolute numbers.
- **G2-C10** The sources disagree on whether single-pass stereo saves GPU time:
  - Unity's manual: SPI "slightly decreases GPU usage" vs multi-pass.
  - UUM-149765: no GPU-time difference between multi-pass and multiview on Quest 2/3/3S.
  - OVR_multiview spec: GPU work may be fully duplicated per view.

  Treat the multiview win as CPU-side (G2-050 / G2-051).

### G3 conflicts (shaders, extensions, capture)

- **G3-C1** Android blob cache size. Arm's integration guide says the default is 64 KB per application and recommends 512 KB-1 MB (G3-018). AOSP source (main, 14, 15) shows a 2 MB total monolithic cache, with 64 KB as the per-entry limit, and a 32 MB multifile option (G3-011, G3-013). For Quest, trust AOSP and check the file on the device.
- **G3-C2** WarmUp effectiveness on GLES. Unity calls ShaderVariantCollection.WarmUp "fully supported" on OpenGL (G3-021). A 2018 forum thread (pre-2023) reports long WarmUp pauses on GLES (G3-024). These are compatible: warmup works, but it moves the full compile cost into load time, so budget it in loading screens.
- **G3-C3** GLES vs Vulkan. Qualcomm says "Prefer Vulkan to OpenGL ES" (mobile best practices). Unity bug UUM-93226 (open through 6000.3) shows Vulkan much slower than GLES on Quest 2/3 with MSAA because of buffer copies (G3-049). Choose per project, with an A/B test.
- **G3-C4** Snapdragon Profiler on Quest. Meta's 2020 doc says GLES rendering-stage traces and snapshots work (G3-084). Community reports say snapshots crash on Quest 2 and captures fail on Quest 3/3S, and Meta has removed its page (G3-085).
- **G3-C5** State-based program recompiles. The Khronos EGL_ANDROID_blob_cache spec describes driver recompiles triggered by state as a general cause of pauses. Qualcomm says Adreno never recompiles for state (G3-007). The general advice does not apply to Quest's Adreno; only the first-use compile does.

### Cross-topic conflicts (GX)

- **GX-C1** UUM-93226: versions and status.
  - Versions: G1 gives "found in" 2022.3.56f1, 6000.0.33f1, 6000.1.0b2, 6000.2.0a1 and 6000.3.0a1. G3 gives 2022.3.56f1, 6000.0.33f1 and 6000.0.0b2.
  - Status: G3 says it was "still open for 6000.0–6000.3 as of Dec 2025". G1 says Closed – Won't Fix.
  - Resolution:
    - Both version lists are genuine. G1's is the tracker's found-in field. G3's is the literal "Reproducible on" line in the JSON description, which the round-1 audit re-read. At synthesis, "6000.0.0b2" was wrongly called a transcription error; that note has been withdrawn.
    - On status, the live tracker shows Closed – Won't Fix on every port. The JSON shows state 102 / status 4, the same codes as Won't Fix UUM-102876, with no fixed-in version, last updated 2025-12-09. G3's "open" reflected the Feb 2025 Wayback state.
- **GX-C2** What the UUM-93226 "buffer copies" are.
  - G2-074 reads them as vertex and constant buffer updates, so buffer-update-heavy content would favour GLES.
  - G1-051 and G1-054 (Unity's tracker note and the RenderDoc store-count evidence) point at render-target stores and resolves on the MSAA path.
  - Resolution: the mechanism evidence supports stores and resolves. G2-074's buffer-update reading is not supported by any cited source and is kept only as a hypothesis to A/B test.
- **GX-C3** Extension counts.
  - G1-015 says 157 on Quest 3 vs 143 on Quest 2.
  - The report badges say 123 GL + 35 EGL (Quest 3, 8023) and 110 GL + 34 EGL (Quest 2, 6387).
  - Resolution: use the badge counts. G1's totals match neither the sums (158 and 144) nor the GL-only counts. The difference G3-044 lists (13 GL + 1 EGL) is consistent with the badges.
- **GX-C4** Does Unity treat GLES as a native render pass API?
  - G1-041 left it open, because Unity's on-tile docs only say "native render passes".
  - G2-022 cites URP docs saying Native RenderPass has no effect on OpenGL ES and that `BeginRenderPass` is emulated there.
  - Resolution: G2-022 is right. It is confirmed at the shader-library level by GLES3-GF1-008: `PLATFORM_SUPPORTS_NATIVE_RENDERPASS` is not defined for GLES.
- **GX-C5** Does Meta's EGL keep the Android blob cache?
  - G3-009 assumes the AOSP EGL loader's blob cache is active.
  - G1-008 notes that the EGL string is "META-EGL" and that `EGL_ANDROID_blob_cache` is not listed.
  - Resolution: unresolved. The extension is private to the loader by spec, so its absence proves nothing. Whether Meta's EGL build keeps the loader cache needs a device check (KU-04). GLES3-GF1-006 at least establishes that all current headsets run an Android 14 base.
- **GX-C6** On GLES, are `FRAMEBUFFER_INPUT` reads a texel fetch or framebuffer fetch?
  - G3-059 said undocumented. G2-022 implied emulation.
  - Resolution (round-1 audit): texel fetch. Without `PLATFORM_SUPPORTS_NATIVE_RENDERPASS`, Common.hlsl declares each input as a texture and reads it with `.Load()` (GLES3-GF1-008).
- **GX-C7** Unity 6.7 status.
  - G1 says "6.7 beta docs match 6.6". G2 saw only 6000.7.0a4 in UUM-149765.
  - Resolution: both agree 6.7 had not shipped as of 2026-09-24. Whether it is in alpha or beta does not matter here. Re-verify at skill-writing time.
- **GX-C8** Does FFR work on GLES through OpenXR?
  - Meta's Unity FFR page and G3-053 state no API restriction for `OVRManager.foveatedRenderingLevel`.
  - G2-061 and G2-062 say FFR applies only when rendering directly into the swapchain, and the OpenXR plugin lists Quest as Vulkan-only (G2-C8).
  - Resolution: unresolved. GLES + OpenXR on Quest is off-document. Test with G2-064 / G3-054: if App GPU time does not move across levels, FFR is not active (KU-10).
  - Round-2 update: partly narrowed. Unity documents *dynamic* foveation as Vulkan-only (OpenXR 1.19+, `XR_FB_foveation_vulkan`). Its support reference names a graphics-API requirement only for Windows (GLES3-GF2-006, [doc]). At spec level `XR_FB_foveation` is API-agnostic (GLES3-GF2-007, [doc]). Static FFR on a GLES + OpenXR build is still undocumented either way.
- **GX-C9** Timer queries and tooling parity.
  - Meta says a GL timer query forces a flush, after which invalidates are ignored, and that per-draw timing is inaccurate on tiled GPUs (G2-006, G3-076, G3-077).
  - Qualcomm says to issue timer queries inside a render pass (G3-068).
  - G1-074 says tooling "works on both APIs".
  - Resolution:
    - The two pieces of advice fit together. Inside the pass there is no extra flush, but the query still sums over bins. Prefer ovrgpuprofiler and RenderDoc per-renderpass timestamps.
    - Tooling parity is partial. RenderDoc works on GL, but shader stats and validation are Vulkan-only (G3-073). SDP is unreliable (G3-085), and AGI does not support Quest (G3-086).
- **GX-C10** Which GLSL `#version` Unity's shipping compiler emits for ES 3.2 (round 2).
  - Unity's public HLSLcc (`toGLSL.cpp`, last pushed 2024-07-16) has no `320 es` path (GLES3-GF1-007, https://github.com/Unity-Technologies/HLSLcc/blob/master/src/toGLSL.cpp, [doc]).
  - UUM-60833 is marked Fixed on 2023.3.X, 6000.2.X and 6000.3.X, with "#version 320 es" as the expected output for compute on OpenGLES 3.2 (GLES3-GF2-005, https://issuetracker.unity.com/api/v1.0/issues/9889, [community]).
  - Assessment: the public HLSLcc is a stale snapshot, and Unity 6.2+ can emit `320 es` for compute. For graphics shaders, and for the 6000.0 port (Won't Fix, but described as fixed in the 6000.1 note), check with "Show compiled code" on the target version.
- **GX-C11** Snapdragon Profiler on Quest (round 2).
  - Meta's current Unreal debugging page presents SDP as usable on Quest because of the Qualcomm chipset (GLES3-GF2-008, https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android/, [doc]).
  - Community reports say captures fail on Quest 3/3S and snapshots crash on Quest 2 (G3-085, [community]). Meta's dedicated SDP page returns 404 (G3-084).
  - Assessment: Meta's mention is generic and undated in scope, while the failure reports are specific. Keep SDP as an optional secondary tool and ovrgpuprofiler / Perfetto / RenderDoc Meta Fork as primary (KU-35).

### Round-1 audit corrections (2026-09-24)

| Claim | Verdict | Change |
|---|---|---|
| G1-021 | fixed | The Unity doc lists target 3.5 as "OpenGL ES 3+" and target 3.0 as "OpenGL ES 3.0+". The 3.0 row was added and the 3.5 row's wording corrected. The other rows match. |
| G2-009 | fixed | Meta attributes "1.5ms" to LoadColor + StoreDepthStencil. The earlier "about 2.4 ms" is now labelled as this dossier's arithmetic, including LoadDepthStencil. |
| G2-039 | fixed | "OculusXR Optimize Buffer Discards" became "Optimized Buffer Discards enabled", because the report does not name the plugin. The `sysPropDebug`/`headlock` props and the device firmware were added. |
| G1-049 / GX-C1 | fixed | "6000.0.0b2" is literal in the tracker JSON; the claim of a transcription error was withdrawn. |
| G3-075 / G3-077 | fixed (date) | The RenderDoc for Oculus blog is dated 2020-09-03, replacing "date not captured, likely pre-2023". |
| G2-010 | fixed | Two missing setprops were added from the UUM-149765 steps. |
| Baseline table | updated | Rows were added for the Quest 2 Android 14 base and for gpuinfo coverage. |
| Others checked | ok | G1-001, G1-003, G1-005, G1-006, G1-007 / G2-035, G2-070, G3-041, G2-069 limits, G1-008 / G3-008, G2-092, G1-017, G1-018, G1-019, G1-031, G1-033, G1-036 to G1-039, G2-001, G2-002, G2-004, G2-006, G2-040, G3-011, G3-013, G3-019, G3-020, G3-026, G3-007 / G2-068, G2-045, G3-037, G3-079, G3-080, G3-081, G3-084, G3-073. |

No finding was removed or downgraded in this round.

### Round-2 audit spot-checks (2026-09-24)

Each claim below was re-fetched from its cited source and compared for number, version, device and API.

| Claim | Verdict | Detail |
|---|---|---|
| G1-031 / G1-032 (AppSW) | ok | Page "Updated: May 13, 2026". It says AppSW is not supported under any other graphics API. Version floors 2022.3.15f1 / 6000.0.9f1 / 6000.4.0f1 match, and so does the "up to 70 percent additional compute" figure. The page frames 70% as "our initial testing", so the [verify on device] tag stays. |
| G1-037 / G1-038 / G1-039 (OpenXR Quest settings) | ok | Page "Updated: May 11, 2026". The claims match: Symmetric Projection 5–15%, MRR 3–8%, and OBD ~90 MB per eye at 1680x1760 (Quest 3) and ~66 MB per eye at 1440x1584 (Quest 2). |
| G1-017 / G1-019 (Unity 6.6 GLES floor) | ok | Manifest `0x00030001`, no ES 3.0 context, cannot revert, and `MAX_VISIBLE_LIGHTS` 16 → 32 all match the 6.6 upgrade guide. |
| G1-045 (dynamic resolution) | ok | "Updated: Aug 6, 2026", URP ≥ 14.0.9, and GPU Level 5 on Quest 3 needs dynamic resolution. The foveation + dynamic-resolution warning names Vulkan render passes. |
| G1-035 (Subsampled Layout) | ok | FFR page "Updated: Aug 28, 2026". It requires Vulkan and OpenXR 1.9.0+. |
| G1-026 (graphics jobs) | ok | "Updated: Nov 11, 2024", up to 2 FPS, 2022.3.35f1, `GraphicsJobMode.Legacy`. |
| G1-005 / G1-006 (SSBO and compute limits) | ok | Reports 6387 / 8023: vertex and fragment SSBO blocks 4 / 12, bindings 24 / 36, invocations 1024, shared memory 32768. Compute SSBO blocks (24 / 36) added in GLES3-GF2-001. |
| G1-027 / G1-C3 (GPU skinning) | ok, extended | The 6000.3 Android Player page lists CPU / GPU / GPU (Batched) with no API restriction. GLES3-GF2-001 adds the compute requirement chain. |
| G2-005 (partial clear) | ok | 18.24 vs 25.15 ms (37%). The source's `glClear` masks match. The repository now lives under the SnapdragonGameStudios organisation. |
| G2-007 (depth/stencil store) | ok | 18.33 vs 11.93 ms ("a 50% difference"). |
| G2-027 (UUM-91896) | ok | Fixed (state 103 / status 3) on 6000.0.X, 6000.1.X and 6000.2.X, updated 2025-12-10. Repro: 6000.0.23f1, 6000.0.33f1, 6000.1.0b1; not reproducible on 6000.0.22f1; Oculus XR multi-pass; Quest 2/3. |
| G2-039 / G2-041 (UUM-149765 table) | ok | Every table value, the 63 bins of 192x256, OBD enabled and the device firmware match the JSON description. |
| G3-012 / G3-014 (blob-cache eviction and build ID) | ok | `BlobCache::clean()` removes random entries while total > max/2. The header stores and checks `ro.build.id`. |
| G3-083 (GPU Systrace) | ok | "As of December 2nd 2024" no longer officially supported; the page itself was updated Apr 17, 2026. |
| GLES3-GF1-004 (RenderDoc Meta Fork 68.18) | ok | "Updated: Jul 28, 2026 \| Version 68.18". Fixes include the Adreno timing hang; `--frame-number` and `--intent-args` are new; it "requires HzOS version 68+" for profiling. |
| GLES3-GF1-007 (HLSLcc `#version`) | qualified | Correct for the public snapshot, but UUM-60833 shows the shipping compiler was fixed to emit `320 es` for compute on 6000.2+ (GLES3-GF2-005, GX-C10). A cross-reference was added; the finding is kept. |
| UUM-93226 status (baseline, G1-050) | ok | The JSON is unchanged: state 102 / status 4 on all five ports, updated 2025-12-09, 21 votes. |

No finding was removed or downgraded in round 2. Round-2 gap-fill findings are GLES3-GF2-001 to GLES3-GF2-008.

## Gaps and known unknowns

The KU numbering was reconstructed in the round-1 audit. Synthesis cited KU numbers in the text without writing this list. Every number cited above keeps the meaning implied where it is cited. The unreferenced numbers hold the remaining topic gaps. Each entry gives the measurement method.

- **KU-01** The GLSL `#version` Unity emits per `#pragma target`, and the effect of "Use OpenGL ES 3.0 shaders" on it. **Partly answered** by GLES3-GF1-007: the public HLSLcc emits `300 es` or `310 es`, never `320 es`. Round 2: the shipping compiler has diverged. UUM-60833 is Fixed on 6000.2+ so that compute shaders on ES 3.2 get `320 es` (GLES3-GF2-005, GX-C10). Still open: graphics-shader `#version` and default precision on 6.x, and the 6000.0 compute status. Method: Shader Inspector "Compile and show code" for GLES3 at targets 3.5, 4.5 and 5.0, or `glShaderSource` in a RenderDoc GL capture.
- **KU-02** Whether the Meta OS fix for the Qualcomm visibility-stream bug (UUM-93226) shipped. No Horizon OS release note mentions it; the round-1 audit searched the release-notes index. Round 2 (GLES3-GF2-002): the tracker JSON is unchanged since 2025-12-09, and the tracker discussion thread (t/1725076) and forum thread 1561926 have no staff follow-up through Jul 2026. No public source exists; this is unresolvable without a device. Method: rerun a UUM-93226-style scene (many meshes, 4x MSAA) on both APIs on the current OS. Record the OS build, App GPU time and the per-bin store counts.
- **KU-03** Vulkan PSO vs GLES program-link hitch size on Quest. Method: first-seen-material camera paths; count over-budget frames in OVR Metrics; attribute them with Perfetto or Profiler markers (`Shader.CreateGPUProgram` vs pipeline creation); repeat on a second launch.
- **KU-04** Whether Horizon OS's META-EGL keeps the AOSP blob cache, and whether it enables the multifile cache (GX-C5, G3-013). Method: `adb shell getprop ro.egl.blobcache.multifile`; on a debuggable build, `run-as <pkg> ls -l cache/` after a session; compare cold and warm hitch counts.
- **KU-05** The millisecond cost of `glCompileShader` / `glLinkProgram` for URP variants on Adreno 650 and 740. Method: development build, render-thread `Shader.CreateGPUProgram` samples, cold (cache cleared) vs warm launch.
- **KU-06** Whether Unity's Android player uses the GLES3 `UnityShaderCache` documented for Embedded Linux (G3-017). Method: look for `UnityShaderCache` under `Application.temporaryCachePath` after a session.
- **KU-07** Adreno driver CPU overhead, GLES vs Vulkan, on XR2 and XR2 Gen 2. Method: a draw-call sweep (200, 500, 1000) comparing render-thread ms in Perfetto on both APIs, with Low Overhead Mode on and off.
- **KU-08** The Adreno program-binary size of typical URP Lit variants, and whether they fit the 64 KB monolithic per-entry limit (G3-011). Method: `GL_PROGRAM_BINARY_LENGTH` from a native plugin, or the growth of the cache file.
- **KU-09** Whether dynamic resolution works on GLES, and so whether Quest 3 GPU level 5 is reachable (G1-045). Method: enable it on a GLES build; log `XRSettings.renderViewportScale` and the eye-texture size; check the available GPU levels.
- **KU-10** Whether FFR, through `OVRManager.foveatedRenderingLevel` or the SRP Foveation API, takes effect on GLES via OpenXR (GX-C8). Round 2: dynamic foveation is documented as Vulkan-only (GLES3-GF2-006), and `XR_FB_foveation` itself is API-agnostic (GLES3-GF2-007). Static FFR on GLES + OpenXR has no public statement; only a device test can settle it. Method: G2-064 / G3-054 level sweep; App GPU time in OVR Metrics; `Fov` fields in `ovrgpuprofiler -t -v`.
- **KU-11** Current Quest 2 (2024–2026 drivers), Quest 3S and Quest Pro GLES extension lists (GLES3-GF1-005). Method: dump `glGetStringi(GL_EXTENSIONS)` on device, or submit a gpuinfo report from the headset.
- **KU-12** Whether graphics jobs of any mode run on GLES Quest builds. Method: log `SystemInfo.renderingThreadingMode` on a GLES build with Graphics Jobs ticked.
- **KU-13** How Render Graph (URP 17) merged native passes are lowered on GLES: load/store actions, invalidates, pass splits. Method: Render Graph Viewer plus a RenderDoc GL capture and the ovrgpuprofiler Load*/Store* stages.
- **KU-14** Horizon Store / VRC policy on GLES: no rule requiring Vulkan was found. Method: check the current VRC list at submission time.
- **KU-15** GPU skinning on GLES (G1-C3). Round 2: the doc chain (compute skinning; ES 3.1 compute; ES 3.2 drivers; 24/36 compute SSBO blocks) favours availability (GLES3-GF2-001). End-to-end confirmation needs a device. Method: Profiler and Frame Debugger on a GLES build; look for skinning compute dispatches vs CPU skinning markers.
- **KU-16** No Unity 6.1–6.6 GLES-vs-Vulkan measurement with the recommended Vulkan settings (OBD, Symmetric Projection, MRR, on-tile post). Method: the single-variable A/B of G1-079 on 6000.3+.
- **KU-17** Which GL calls Unity's GLES backend emits for URP load/store actions on Quest (`glInvalidateFramebuffer`, `glDiscardFramebufferEXT` or `glClear`), and when relative to the flush. Round 2: a 2023 RenderDoc capture (Quest 2, 2021.3/2022.3, OculusXR) shows two `glInvalidateFramebuffer` calls per frame in an empty URP scene (GLES3-GF2-003, [community]). The mapping from each load/store action to a call, and the 6.x / Render Graph behaviour, need a device. Method: the RenderDoc GL API log, plus the ovrgpuprofiler Load*/Store* stages.
- **KU-18** Whether Unity's GLES backend uses `EXT_multisampled_render_to_texture(2)` or the OVR multiview MSRTT for eye buffers and MSAA render targets. Round 2: answered for multiview eye buffers. Unity's manual (2022.3–6000.6) says Android multiview consists of `GL_OVR_multiview2` and `GL_OVR_multiview_multisampled_render_to_texture` (GLES3-GF2-004). Still open, and device-only: non-multiview MSAA render targets. Method: log `SystemInfo.supportsMultisampleAutoResolve` and `supportsStoreAndResolveAction`; look for `glFramebufferTexture2DMultisampleEXT` / `glFramebufferTextureMultisampleMultiviewOVR` in a RenderDoc capture.
- **KU-19** Unity's GLES buffer-update strategy for constant buffers and dynamic VB/IB: `glBufferSubData`, map with INVALIDATE/UNSYNCHRONIZED, or orphaning. Round 2: no Unity doc, forum or staff post states it (G2-073 re-check). Device-only. Method: a GL call trace in RenderDoc.
- **KU-20** Whether Adreno runs `mediump` vertex-shader math at fp16, as it does for fragments. Method: `glGetShaderPrecisionFormat` for the vertex stage; register and instruction counts from the Adreno Offline Compiler.
- **KU-21** The value of `GL_MAX_VIEWS_OVR` on the Quest drivers; it is not in the gpuinfo reports. Method: query it at runtime from a native plugin.
- **KU-22** The GPU vertex-cost saving of multiview on Adreno 650 and 740; no published number (G2-C10). Method: multi-pass vs multiview A/B, with ovrgpuprofiler Binning and Render stage times.
- **KU-23** The post-2018 CPU cost per state change, program switch and texture bind on Quest GLES; the Meta study is Quest 1 / Unity 2018. Method: a native microbenchmark, or a Unity draw sweep with material-switch patterns, timed in Perfetto.
- **KU-24** The cost of 2x MSAA on Quest GLES: Qualcomm says "likely practically free", with no Quest measurement (G2-C3). Method: the G2-010 recipe at 1x, 2x and 4x.
- **KU-25** Whether Adreno 650 lacks concurrent binning. This is assumed only because Qualcomm says it arrived with A7x. Method: compare Binning and Render stage overlap in Perfetto GPU render stages on Quest 2 vs Quest 3.
- **KU-26** Whether ovrgpuprofiler's Binning time on Adreno 740 overlaps Render (concurrent binning) or adds to it. Method: compare the surface total with the sum of stages in `ovrgpuprofiler -t -v`, and with the Perfetto render-stage timeline.
- **KU-27** The Adreno 6x per-shader performance thresholds for UBO, VB and texture counts; only A7x values are published. Method: an instruction- and resource-count sweep with ovrgpuprofiler "% Wave Context Occupancy".
- **KU-28** The full ovrgpuprofiler 47-metric list and IDs; Meta's doc shows only the first 11. Method: `adb shell ovrgpuprofiler -m -v` on each headset.
- **KU-29** The Adreno 6x (Quest 2) instruction-cache limit; not published by Qualcomm. Method: shader-length sweep while watching occupancy and App GPU time.
- **KU-30** The value of `GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT` on both headsets; not captured from the reports. Method: `glGetFloatv` from a native plugin.
- **KU-31** Whether Unity's GLES backend uses `QCOM_shading_rate`, `EXT_fragment_shading_rate` or `QCOM_texture_lod_bias`. Method: `SystemInfo.foveatedRenderingCaps` on a GLES build; the RenderDoc GL API log.
- **KU-32** How Unity's `RenderBufferStoreAction`/`LoadAction` behave on Adreno GLES compared with UUM-45041 (which did not reproduce on Adreno 610) (G2-C2). Method: the ovrgpuprofiler Load*/Store* stages per surface.
- **KU-33** The Quest 2 SSBO cap (4 per stage, vs 12 on Quest 3) against URP and Unity features that bind SSBOs, such as Forward+ light lists, GPU-resident drawer and VFX Graph. No Unity doc states which features exceed 4. Round 2: the 4-block cap applies to the vertex and fragment stages. The compute-stage cap is 24 on Quest 2 and 36 on Quest 3, so compute-only features such as GPU skinning are not bound by it (GLES3-GF2-001). Method: build each feature for GLES and check for shader compile errors or fallbacks in logcat.
- **KU-34** How GL multiview surfaces look in render-stage traces on Quest 3; Meta describes only Quest 1 and Quest 2 (G3-047). Method: `ovrgpuprofiler -t -v` on a multiview GLES build on Quest 3; compare the bin count with the eye-buffer size.
- **KU-35** Whether Snapdragon Profiler works on current Horizon OS for GLES (G3-C4, G3-085). Round 2: the Qualcomm thread is JavaScript-rendered and could not be read without a browser. Meta's only current mention is generic (GLES3-GF2-008, GX-C11). Device-only. Method: an attempted SDP GLES trace on a development build.
- **KU-36** Whether Perfetto GPU render stages and ovrgpuprofiler per-draw traces behave differently for GLES than for Vulkan; no restriction is stated. Method: the same scene captured on both APIs.
- **KU-37** When Meta's legacy-GLES stance was first published: the page is undated, and the earliest Wayback capture is 2024-10-11. Method: further Wayback checks; this is not needed for the skill.
- **KU-38** Whether Unity's `Texture.mipMapBias` maps to `QCOM_texture_lod_bias` on Quest 3 GLES, and its behaviour on Quest 2 (G3-066). Method: visual comparison plus the RenderDoc API log.
- **KU-39** FlexRender's binned/direct heuristics are not exposed, and `QCOM_binning_control` is absent (G2-092). Method: check the Mode per surface in `ovrgpuprofiler -t`; the only lever is to avoid the triggers.
- **KU-40** Whether a GL multiview pass under `QCOM_texture_foveated2` actually discards below the cutoff density in Meta's FFR maps (G3-051). Method: a RenderDoc capture of a foveated eye buffer with FFR level 4.
- **KU-41** The Adreno GLES program-link cost after a Horizon OS update invalidates the blob cache (G3-014): how many hitches a returning player sees. Method: record hitch counts on the first launch after an OS update vs the second launch.
- **KU-42** Frame-time variance (p95/p99) on GLES vs Vulkan for the same content; no published data. Method: OVR Metrics Tool CSV over a 20–30 minute session on both APIs, analysed with the quest-perf CSV analyzer.
- **KU-43** The OpenXR equivalent of OculusXR's GLES Low Overhead Mode; none found in the OpenXR Meta feature list. Method: check the OpenXR feature settings in your plugin version; A/B render-thread ms.

Unity 6.7 LTS had not shipped as of 2026-09-24 (GX-C7). Re-verify at skill-writing time.

## Source list

All accessed 2026-09-24. Merged from the G1, G2 and G3 notes and the round-1 audit, deduplicated by URL and grouped by publisher.

**Meta**

- https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/ (Meta, "OpenGL ES and Vulkan")
- https://developers.meta.com/horizon/documentation/unity/unity-asw/
- https://developers.meta.com/horizon/documentation/unity/unity-openxr-settings-quest/
- https://developers.meta.com/horizon/documentation/unity/unity-fixed-foveated-rendering/
- https://developers.meta.com/horizon/documentation/unity/unity-eye-tracked-foveated-rendering/
- https://developers.meta.com/horizon/documentation/unity/dynamic-resolution-unity/
- https://developers.meta.com/horizon/documentation/unity/po-graphics-jobs/
- https://developers.meta.com/horizon/documentation/native/android/mobile-ffr/ (deprecated VrApi)
- https://developers.meta.com/horizon/blog/vulkan-for-mobile-vr-rendering/
- https://developers.meta.com/horizon/blog/vulkan-support-for-oculus-quest-in-unity-experimental/
- https://developers.meta.com/horizon/documentation/unity/po-advanced-gpu-pipelines/ (Meta, "Advanced GPU Pipelines and Loads, Stores, and Passes"; undated, mentions Quest 3/3S)
- https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/ (Meta, "Draw Call Cost Analysis for Meta Quest"; Quest 1 / Unity 2018.1.6f1; stale)
- https://developers.meta.com/horizon/documentation/native/android/mobile-multiview/ (Meta native "Multi-View (Deprecated)"; updated 2022-09-29; pre-2023)
- https://developers.meta.com/horizon/documentation/unity/enable-multiview/ (Meta Unity "Enable Multiview"; updated 2025-11-12)
- https://developers.meta.com/horizon/documentation/unity/os-fixed-foveated-rendering/ (Meta Unity FFR)
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-for-oculus/
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-renderstage/
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-capture/
- https://developers.meta.com/horizon/documentation/unity/ts-renderdoc-settings/
- https://developers.meta.com/horizon/blog/renderdoc-for-oculus/ (likely pre-2023)
- https://developers.meta.com/horizon/documentation/unity/ts-ovrgpuprofiler/
- https://developers.meta.com/horizon/documentation/unity/ts-perfettoguide/
- https://developers.meta.com/horizon/documentation/unreal/ts-gpusystrace/
- https://developers.meta.com/horizon/documentation/native/android/os-fixed-foveated-rendering/
- https://developers.meta.com/horizon/downloads/package/renderdoc-oculus/ (RenderDoc Meta Fork 68.18 release notes; round-1 audit)
- https://developers.meta.com/horizon/release-notes/ (searched for the visibility-stream fix; nothing found; round-1 audit)

**Unity manual, packages and scripting API**

- https://docs.unity3d.com/6000.3/Documentation/Manual/class-PlayerSettingsAndroid.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/SL-Pragma-target.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/vulkanapi-graphics-jobs-configuration.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/WhatsNewUnity65.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-branching-api.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-untethered-device-optimization.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-rendering.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/on-tile-post-processing.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-graphics-on-tile-rendering.html
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-meta-quest-graphics-optimization.html
- https://docs.unity3d.com/6000.1/Documentation/Manual/xr-multiview-render-regions.html
- https://docs.unity3d.com/2023.1/Documentation/Manual/WhatsNew20231.html
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/index.html (Oculus XR Plugin 4.5.5; deprecation from Unity 6.5)
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.5/manual/oculus-plugin.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/features/metaquest.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/metaquest.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.RenderBufferLoadAction.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.RenderBufferStoreAction.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.LoadStoreActionDebugModeSettings.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsStoreAndResolveAction.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsMultisampleAutoResolve.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/SystemInfo-supportsMultiview.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture.DiscardContents.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture.MarkRestoreExpected.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture-bindTextureMS.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.ScriptableRenderContext.BeginRenderPass.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.CommandBuffer.BeginRenderPass.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GraphicsBuffer.LockBufferForWrite.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GraphicsBuffer.UsageFlags.LockBufferForWrite.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Mesh.MarkDynamic.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rendering.IndexFormat.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/SinglePassStereoRendering.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/SinglePassInstancing.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/xr-foveated-rendering-support.html
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/universalrp-asset.html
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/universalrp-asset.html
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/universalrp-asset.html
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-universal-renderer.html
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/urp-universal-renderer.html
- https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@17.0/manual/render-graph-introduction.html
- https://docs.unity3d.com/Packages/com.unity.xr.oculus@4.4/manual/index.html (Oculus XR Plugin 4.4)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/index.html (OpenXR 1.16.1)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/features/foveatedrendering.html
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.16/manual/project-configuration.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-loading.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-memory.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/shader-prewarm-other.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/class-GraphicsSettings.html
- https://docs.unity3d.com/6000.5/Documentation/ScriptReference/ShaderVariantCollection.WarmUp.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/embedded-linux-optional-features.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/SL-Use16BitPrecisionInShaders.html
- https://docs.unity3d.com/6000.5/Documentation/Manual/class-PlayerSettingsAndroid.html
- https://docs.unity3d.com/2019.4/Documentation/Manual/SL-DataTypesAndPrecision.html (pre-2023)
- https://docs.unity3d.com/6000.5/Documentation/Manual/xr-foveated-rendering-support.html
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/RenderTexture-memorylessMode.html (round-1 audit)

**Unity source (GitHub)**

- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/Input.hlsl
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs
- https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.render-pipelines.universal/Runtime/UniversalRenderPipeline.cs
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/Runtime/RenderGraph/Compiler/NativePassCompiler.cs (URP/Core source, master)
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/GLES3.hlsl
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/ShaderLibrary/API/Vulkan.hlsl
- https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl
- https://github.com/Unity-Technologies/HLSLcc/blob/master/src/toGLSL.cpp (Unity HLSLcc GLSL backend; repo last pushed 2024-07-16; round-1 audit)

**Unity issue tracker and forums**

- https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3
- https://issuetracker.unity.com/issues/1364/vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-23
- https://issuetracker.unity.com/issues/6553/significant-performance-difference-between-vulkan-and-opengles3-when-built-with-ecs
- https://issuetracker.unity3d.com/issues/xr-vulkan-quest1-apps-have-significantly-higher-memory-consumption-on-vulkan-compared-to-gles3 (now 404)
- https://issuetracker.unity3d.com/issues/vulkan-performance-is-worse-than-opengles3-and-opelgles2 (now 404)
- https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926
- https://discussions.unity.com/t/vulkan-performing-much-worse-than-opengl-es-due-to-excessive-buffer-copies-on-quest-2-3/1561926?page=2
- https://discussions.unity.com/t/performance-discrepancy-between-vulkan-and-opengl-with-unity-2022-3-17f1-on-meta-quest-3/938162
- https://discussions.unity.com/t/xr-perf-quest-2022-2-and-trunk-vulkan-vs-gles-perf-disparity-increased-significantly-6223/1726043
- https://discussions.unity.com/threads/horrible-performance-on-vulkan-with-simple-scene-quest-2.1203082/
- https://discussions.unity.com/threads/serious-performance-regression-of-using-vulkan-vs-opengl-in-unity-2021-3-8-lts.1322298/
- https://issuetracker.unity.com/api/v1.0/issues/1364 (UUM-93226 JSON; re-read in round-1 audit)
- https://issuetracker.unity.com/api/v1.0/issues/14139 (UUM-102876)
- https://discussions.unity.com/t/vulcan-and-shadervariantcollection-warmup/700973 (2018)
- https://discussions.unity.com/t/shadervariantcollection-warmup-not-work-on-oculus-quest-2/920217 (2023-2024; round-1 audit)
- https://discussions.unity.com/t/shader-warmup-doesnt-seem-to-be-working-on-quest-android/936926 (Jan 2024; round-1 audit)
- https://discussions.unity.com/t/1725076 (discussion linked from the UUM-93226 JSON; round-1 audit)
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-149765 (re-read in round-1 audit)

**Qualcomm**

- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html (Qualcomm "Adreno GPU on Mobile: Best Practices", last published 2026-09-22; markdown source https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/mobile_best_practices.md)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/overview.md (Qualcomm Adreno overview: FlexRender, concurrent binning, LRZ)
- https://docs.qualcomm.com/bundle/publicresource/80-78185-2/topics/spec_sheets.md (Qualcomm spec sheets, 2026-09-22)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/spec_sheets.html (Last Published Sep 22, 2026)
- https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/sdp.html (Last Published Sep 22, 2026)
- https://mysupport.qualcomm.com/supportforums/s/question/0D5dK000009EniESAS/snapdragon-profiler-not-able-to-capture-anything-on-meta-quest-33s (unreadable; title only)

**Khronos**

- https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview.txt , OVR_multiview2.txt , OVR_multiview_multisampled_render_to_texture.txt
- https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview2.txt (rev 0.5, 2018-10-19)
- https://registry.khronos.org/OpenGL/extensions/OVR/OVR_multiview_multisampled_render_to_texture.txt (rev 0.4, 2015-06-25)
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture.txt , EXT_multisampled_render_to_texture2.txt , EXT_shader_framebuffer_fetch.txt , EXT_discard_framebuffer.txt , EXT_disjoint_timer_query.txt , EXT_clip_control.txt , EXT_depth_clamp.txt , EXT_buffer_storage.txt , EXT_fragment_shading_rate.txt , EXT_texture_compression_astc_decode_mode.txt , EXT_texture_filter_anisotropic.txt
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture2.txt (rev 4, 2025-10-22)
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_discard_framebuffer.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_tiled_rendering.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_binning_control.txt (Draft, 2012)
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated.txt , QCOM_texture_foveated2.txt , QCOM_texture_foveated_subsampled_layout.txt , QCOM_shader_framebuffer_fetch_noncoherent.txt , QCOM_shader_framebuffer_fetch_rate.txt , QCOM_tiled_rendering.txt , QCOM_shading_rate.txt , QCOM_frame_extrapolation.txt , QCOM_motion_estimation.txt , QCOM_texture_lod_bias.txt , QCOM_render_shared_exponent.txt , QCOM_render_sRGB_R8_RG8.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated2.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_foveated_subsampled_layout.txt
- https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_blob_cache.txt
- https://registry.khronos.org/OpenGL/extensions/OES/OES_get_program_binary.txt
- https://registry.khronos.org/OpenGL/extensions/ARM/ARM_shader_framebuffer_fetch_depth_stencil.txt

**Android / AOSP**

- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/egl_cache.cpp (+ BlobCache.cpp, FileBlobCache.cpp, MultifileBlobCache.cpp)
- https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/graphics/java/android/graphics/HardwareRenderer.java
- https://developer.android.com/agi/supported-devices ; https://developer.android.com/agi/frame-trace/frame-profiler

**Arm**

- https://developer.arm.com/documentation/101897/0303/System-integration/Android-blob-cache-size-in-OpenGL-ES

**Device capability reports (opengles.gpuinfo.org)**

- https://opengles.gpuinfo.org/displayreport.php?id=8023 (Quest 3, Adreno 740, Android 14, V@0837.0.7, submitted 2026-02-20)
- https://opengles.gpuinfo.org/displayreport.php?id=7475
- https://opengles.gpuinfo.org/displayreport.php?id=7267 , 7475 (Quest, Adreno 740) , 8023 (Quest 3, Adreno 740)
- https://opengles.gpuinfo.org/displayreport.php?id=6387 (Quest 2, Adreno 650, Android 12, V@0690.0, submitted 2023-01-13)
- https://opengles.gpuinfo.org/displayreport.php?id=5808
- https://opengles.gpuinfo.org/displayreport.php?id=5278
- https://opengles.gpuinfo.org/displayreport.php?id=5092 , 5278 , 5808 , 6387 (Quest, Adreno 650)
- https://opengles.gpuinfo.org/backend/reports.php (full walk of 8292 reports; round-1 audit)

**Other and archived**

- http://web.archive.org/web/20241011053743/https://developers.meta.com/horizon/documentation/unity/os-vulkan-opengl/
- https://unity.com/releases/editor/whats-new/2023.1.0
- http://web.archive.org/web/20250215025510/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3
- http://web.archive.org/web/20251209102052/https://issuetracker.unity3d.com/issues/performance-vulkan-performing-much-worse-than-opengles-due-to-excessive-buffer-copies-on-quest-2-slash-3
- https://github.com/quic/adreno-gpu-opengl-es-code-sample-framework (Qualcomm GLES samples: avoid_gmem_loads, reduce_gmem_stores, msaa; phone Adreno; undated)
- https://web.archive.org/web/20250118034434/https://www.khronos.org/opengl/wiki/Buffer_Object_Streaming (Khronos OpenGL wiki via Wayback; the live wikis.khronos.org URL returned 403)
- http://web.archive.org/web/20200513224546/https://developer.oculus.com/documentation/native/android/mobile-snapdragon-profiler/ (2020; the live page now returns 404)

**Also cited in the body (full URLs, added at the round-1 audit)**

- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/opengl/libs/EGL/BlobCache.cpp
- https://issuetracker.unity.com/api/v1.0/issues?q=OXPB-144
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102876
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-102878
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-109377
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-45041
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-70930
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-8381
- https://issuetracker.unity.com/api/v1.0/issues?q=UUM-91896
- https://issuetracker.unity3d.com/issues/quest-2-significant-performance-difference-between-vulkan-and-opengles3-when-built-with-ecs
- https://peterthor.se/tag/qualcomm-snapdragon-profiler/
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_buffer_storage.txt
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_clip_control.txt
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_disjoint_timer_query.txt
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_fragment_shading_rate.txt
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_shader_framebuffer_fetch.txt
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_texture_compression_astc_decode_mode.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_frame_extrapolation.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_render_shared_exponent.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shader_framebuffer_fetch_noncoherent.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shader_framebuffer_fetch_rate.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shading_rate.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_texture_lod_bias.txt
- https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_validate_shader_binary.txt (404 on 2026-09-24)

**Round-2 additions (2026-09-24)**

- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/MeshDeformation.html : Unity Scripting API, MeshDeformation enum (6000.3)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings-meshDeformation.html : Unity Scripting API, PlayerSettings.meshDeformation (6000.3)
- https://docs.unity3d.com/6000.3/Documentation/ScriptReference/PlayerSettings-gpuSkinning.html : Unity Scripting API, PlayerSettings.gpuSkinning (6000.3)
- https://docs.unity3d.com/6000.3/Documentation/Manual/class-ComputeShader-introduction.html : Unity Manual, Introduction to compute shaders (6000.3)
- https://docs.unity3d.com/6000.6/Documentation/Manual/Android-SinglePassStereoRendering.html (also the 6000.3, 6000.0 and 2022.3 versions) : Unity Manual, Single-pass stereo rendering for Android
- https://docs.unity3d.com/6000.6/Documentation/Manual/xr-foveated-rendering-support.html : Unity Manual, Foveated rendering support reference (6000.6; page built 2026-09-24)
- https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/foveatedrendering.html : Unity OpenXR Plug-in 1.19, Foveated rendering
- https://issuetracker.unity.com/issues/9889/version-310-es-is-defined-in-compute-shader-instead-of-version-320-es-when-writing-a-compute-shader-in-hlsl-for-opengles-32 : Unity Issue Tracker, UUM-60833 (Fixed on 2023.3/6000.2/6000.3; updated 2026-05-01)
- https://issuetracker.unity.com/api/v1.0/issues/9889 : UUM-60833 tracker JSON
- https://discussions.unity.com/t/1725076 : Unity Discussions, UUM-93226 tracker discussion thread (created 2026-07-02)
- https://discussions.unity.com/t/multiple-frame-buffer-invalidations-urp/935652 : Unity Discussions, "Multiple Frame Buffer Invalidations (URP)" (Dec 2023)
- https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_FB_foveation.html : Khronos OpenXR 1.1 man page, XR_FB_foveation (spec 1.1.63)
- https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_FB_foveation_vulkan.html : Khronos OpenXR 1.1 man page, XR_FB_foveation_vulkan
- https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_FB_swapchain_update_state_opengl_es.html : Khronos OpenXR 1.1 man page, XR_FB_swapchain_update_state_opengl_es
- https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android/ : Meta, "Testing and Performance Analysis" (Unreal)
- https://developers.meta.com/horizon/release-notes/ : Meta Horizon developer release-notes index
- https://github.com/SnapdragonGameStudios/adreno-gpu-opengl-es-code-sample-framework : Qualcomm GLES sample framework (current org; the `quic` URL still resolves)
