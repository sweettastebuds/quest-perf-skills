# Manifest performance-flag inventory

Inventory only. Each flag's semantics, trade-offs and verification are owned
by the skill in the "Owner" column. All sources accessed 2026-09-24.

Check the merged manifest of the release APK, not your template:

```sh
aapt2 dump xmltree --file AndroidManifest.xml Builds/app.apk \
  | grep -E 'com\.oculus|horizonos|glEsVersion|profileable|QUAD_VIEWS'
```

| Key / element | Values | Effect (one line) | Device scope | Owner skill | Source (finding) | Evidence |
|---|---|---|---|---|---|---|
| `<meta-data android:name="com.oculus.dualcorecpuset">` | `true` | Dual-core mode: one app core off, SustainedHigh becomes CPU 6-6; needs OpenXR backend; logcat `isCPUSingleThreadedBoost is 1` | Quest 2, Quest Pro | quest-perf:quest-levels-thermal | https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (A1-031, Q2-051) | [doc] |
| `<meta-data android:name="com.oculus.trade_cpu_for_gpu_amount">` | `1` / `0` / `-1` | CPU/GPU level trading, fixed at build time; Unity "Processor Favor" on OVRManager; needs OpenXR backend; logcat `tradeCpuForGpu is <n>` | Quest 3, Quest 3S | quest-perf:quest-levels-thermal | https://developers.meta.com/horizon/documentation/unity/po-quest-boost/ (A1-032, Q2-052) | [doc] |
| `<meta-data android:name="com.oculus.enable_frame_sync">` | `true` (opt-in on v201); `false` (claimed opt-out on v203+) | FrameSync test opt-in; the opt-out value is community-reported only and may not exist (QUEST-GF1-C1) | all Quest, OS v201 / v203+ | quest-perf:quest-frame-pacing | https://developers.meta.com/horizon/blog/framesync-meta-horizon-os/ [doc]; https://www.uploadvr.com/meta-horizon-os-framesync-smoother-vr-quest/ [community] (Q2-072, QUEST-GF1-007) | [doc] / [community] |
| `<meta-data android:name="com.oculus.supportedDevices">` | canonical `quest2\|questpro\|quest3\|quest3s` | Missing headset: device reports an older model (compatibility mode) and refresh rates are limited to those both support; clocks unchanged. Driven by OpenXR "Target Devices" | all Quest | quest-perf:quest-frame-pacing (refresh gating); quest-perf:quest-budgets-tiers (tiering) | https://developers.meta.com/horizon/documentation/unity/os-compatibility-mode/ ; https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ (Q2-015, Q2-081, Q2-083) | [doc] |
| `<meta-data android:name="com.oculus.sbcpath">` | cache path relative to app storage, e.g. a `vulkan_pso_cache.bin` path | Shader Binary Cache pre-warming; **deprecated** (doc banner, Aug 7, 2026); also needs Developer Dashboard > Development > Shader Compilation > "Enable Shader Cache Automation" | Store apps on Quest 2/Pro/3/3S; Unity support not guaranteed | quest-perf:quest-sdk-choices (status); unity-perf:unity-shader-hitches (warm-up replacement) | https://developers.meta.com/horizon/documentation/unity/ps-shader-compilation/ (QUEST-GF1-004) | [doc] |
| `<uses-feature android:name="com.oculus.feature.QUAD_VIEWS">` | `required="true"` or not | Quad Views (foveated inset, about 50% fewer pixels); required=true restricts install to Horizon OS v85+; must not combine with FFR | Quest 2/3/3S | quest-perf:quest-resolution-foveation | https://developers.meta.com/horizon/documentation/native/android/os-stereo-with-foveated-inset/ (Q3-090) | [doc] [verify on device] |
| `<uses-feature android:glEsVersion="0x00030001">` | Unity 6.6 GLES floor | Emitted only when Auto Graphics API is on or OpenGLES3 is in the API list; ES 3.1 shaders raise MAX_VISIBLE_LIGHTS 16 to 32 | GLES builds, Unity ≥ 6000.6 | gles3-perf:gles-versions-unity-output | https://docs.unity3d.com/6000.6/Documentation/Manual/UpgradeGuideUnity66.html (U1-094, G1-017) | [doc] |
| `<uses-permission android:name="horizonos.permission.HEADSET_CAMERA">` | present | Passthrough Camera API access; about 45 MB overhead and 20-40 ms capture latency per Meta | Quest 3, Quest 3S; OS v74+ | quest-perf:quest-mr-costs | https://developers.meta.com/horizon/documentation/unity/unity-pca-overview/ (Q4-022; 45 MB: not stated whether per stream, Q4-022 notes) | [doc] |
| Passthrough feature declaration | present / absent | Declaring passthrough features removes CPU L4 and GPU L3-4 on Quest 3/3S; whether runtime-disabling restores them is open. The exact manifest key is not recorded in the dossier; inspect what the Meta SDK / OpenXR Camera (Passthrough) feature emits | Quest 2 (B/W), Quest 3/3S | quest-perf:quest-mr-costs | https://developers.meta.com/horizon/documentation/unity/unity-passthrough-gs/ ; https://developers.meta.com/horizon/documentation/unity/os-cpu-gpu-levels/ (Q4-001, Q4-004, Q4-005) | [doc] [verify on device] |
| `<profileable android:shell="true"/>` | present | Lets Perfetto / simpleperf profile release builds; Unity 6.6 exposes it as the "Profileable Shell" build setting; hand-adding it on older versions is not Unity-documented | all Quest | quest-perf:quest-profiling-toolkit | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html (U5-098) | [doc] (6.6 setting); [verify on device] (manual element) |

## Gaps

- No Meta page publishes a complete list of performance-relevant manifest keys; this table is assembled from per-feature pages.
- The passthrough manifest key and whether its mere presence (with passthrough off at runtime) keeps levels capped are not documented (Q4-005 notes).
- No manifest mechanism replaces SBC; Meta says a replacement is "in development" (QUEST-GF1-004).
