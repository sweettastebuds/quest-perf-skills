# Adaptive quality ladder (C#)

Read from `quest-budgets-tiers` SKILL.md Fix 6 when implementing the frame-time-driven
quality ladder. Unity 2021.3+ (URP 12+), Meta XR Core SDK, Vulkan or GLES, Quest 2 and
Quest 3/3S. Untested on device.

Sources (accessed 2026-09-24):
- Q2-086, Meta's adaptive-quality pattern:
  https://developers.meta.com/horizon/documentation/unity/optimize-performance/ [doc]
- Q1-103, apps should not change behaviour from `XR_META_performance_metrics` counters:
  https://github.com/KhronosGroup/OpenXR-Docs/blob/main/specification/sources/chapters/extensions/meta/meta_performance_metrics.adoc [doc]
- Q2-011, `OVRPlugin.systemDisplayFrequency`:
  https://developers.meta.com/horizon/documentation/unity/unity-set-disp-freq/ [doc]
- QUEST-GF1-003, "hitches under 3%":
  https://developers.meta.com/horizon/blog/gdc-2026-day-1-hands-agents-performance/ [doc]

## Setup

- Author one Quality Settings level per rung, best first; rungs switched mid-play
  should share one URP asset (see Side effects), and list their indices in `rungs`. Rung 0 is the tier chosen at startup
  (SKILL.md Fix 3). Candidate rung contents per Meta: LOD bias, view distance, MSAA
  sample count, shadows, post-processing quality.
- Keep dynamic resolution (SKILL.md Fix 4) on underneath; it absorbs GPU-level changes
  by itself.
- When AppSW is active (see `quest-perf:quest-appsw`), set `appFramesPerRefresh = 2` or
  disable the ladder, or every frame counts as missed.

## Signal and thresholds

- A frame counts as missed when `Time.unscaledDeltaTime` exceeds the refresh budget
  times `missFactor`. This is a heuristic proxy for stale frames, used because Quest
  has no documented in-app API for the current CPU/GPU level.
- `stepDownRatio` starts at 0.03 only because of Meta's "hitches under 3%", whose
  denominator is not published. Every threshold below is a tunable with no published
  value: set it from your own OVR Metrics CSV captures.

```csharp
// Unity 2021.3+ with Meta XR Core SDK. Untested on device. All thresholds are tunables:
// no Meta page publishes step-down/step-up values; set them from your own CSV captures.
using UnityEngine;

public sealed class QuestQualityLadder : MonoBehaviour
{
    [Tooltip("Quality Settings indices, best first. Author one rung per step.")]
    public int[] rungs = { 2, 1, 0 };
    [Tooltip("A frame counts as missed when its delta exceeds budget x this factor.")]
    public float missFactor = 1.5f;
    [Tooltip("Refresh intervals per app frame: 1 normally, 2 while AppSW/half-rate is active.")]
    public int appFramesPerRefresh = 1; // set 2 while AppSW/half-rate is active
    [Tooltip("Missed-frame ratio in a window that triggers a step down (starting value).")]
    public float stepDownRatio = 0.03f;
    public float windowSeconds = 5f;
    [Tooltip("Clean seconds required before stepping back up (hysteresis).")]
    public float stepUpCleanSeconds = 30f;

    int _rung, _frames, _missed;
    float _windowT, _cleanT;

    void Start() { Apply(0); }

    void Update()
    {
        float hz = OVRPlugin.systemDisplayFrequency;
        float budget = appFramesPerRefresh / (hz > 1f ? hz : 72f);
        float dt = Time.unscaledDeltaTime;
        _frames++;
        if (dt > budget * missFactor) _missed++;
        _windowT += dt;
        if (_windowT < windowSeconds) return;

        float ratio = _frames > 0 ? (float)_missed / _frames : 0f;
        if (ratio > stepDownRatio && _rung < rungs.Length - 1)
        {
            Apply(_rung + 1);
            _cleanT = 0f;
        }
        else if (_missed == 0)
        {
            _cleanT += _windowT;
            if (_cleanT >= stepUpCleanSeconds && _rung > 0)
            {
                Apply(_rung - 1);
                _cleanT = 0f;
            }
        }
        else
        {
            _cleanT = 0f;
        }
        _frames = 0;
        _missed = 0;
        _windowT = 0f;
    }

    void Apply(int rung)
    {
        _rung = rung;
        // applyExpensiveChanges = false: skip changes that reallocate (e.g. anti-aliasing).
        QualitySettings.SetQualityLevel(rungs[rung], false);
    }
}
```

## Side effects

- Rungs switched mid-play should share one URP asset and differ only in non-pipeline
  settings (lodBias, maximumLODLevel, particle/pixel-light budgets). `SetQualityLevel(i,
  false)` does not prevent a render-pipeline switch: rungs pointing at different URP
  assets make Unity tear down and recreate the pipeline and its targets, a hitch.
  Otherwise change properties on the active asset directly, e.g.
  `((UniversalRenderPipelineAsset)GraphicsSettings.currentRenderPipeline).shadowDistance = x;`
  (needs `using UnityEngine.Rendering;` and `using UnityEngine.Rendering.Universal;`).
  Switch between different URP assets only at loading screens or fades [verify on device].

- With `applyExpensiveChanges = false`, rungs that differ in MSAA or render-texture
  size do not take full effect mid-play. Apply those differences at loading screens or
  full-screen fades (Perf.1 exempts both) with `SetQualityLevel(index, true)`
  [verify on device].
- Disable the ladder while profiling, as Meta advises for dynamic resolution (Q3-051),
  or captures measure a moving workload.
- Frame delta also rises on main-thread spikes (GC, loading); those are one-frame events
  and should not trip a 5 s ratio, but verify that the ladder does not step down during
  scene loads. Fix spikes at their owner (`unity-perf:unity-cpu-scripting`,
  `unity-perf:unity-shader-hitches`).
