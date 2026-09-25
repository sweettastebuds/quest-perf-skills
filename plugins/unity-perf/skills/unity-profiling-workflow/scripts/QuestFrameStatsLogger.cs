// QuestFrameStatsLogger.cs. Unity 2021.3+ with an XR plug-in. Untested on device.
// Add to one GameObject in the first scene. CSV goes to Application.persistentDataPath
// (/sdcard/Android/data/<pkg>/files/); fetch with adb pull.
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.XR;

public sealed class QuestFrameStatsLogger : MonoBehaviour
{
    public int capacity = 216000; // rows in memory: 120 Hz x 30 min
    struct Row { public float t, mainMs, ftmMainMs, ftmGpuMs, appGpuMs, compGpuMs, gcMB; public int dropped; }
    Row[] _rows; int _count; bool _loggedCaps, _warnedUnits;
    ProfilerRecorder _main, _gc;
    XRDisplaySubsystem _display;
    static readonly List<XRDisplaySubsystem> s_Displays = new List<XRDisplaySubsystem>();
#if UNITY_2022_3_OR_NEWER
    readonly FrameTiming[] _ft = new FrameTiming[1];
#endif

    void OnEnable()
    {
        _rows = new Row[capacity];
        _main = ProfilerRecorder.StartNew(ProfilerCategory.Internal, "Main Thread", 1);    // ns
        _gc   = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC Reserved Memory", 1); // bytes
    }
    void OnDisable() { Flush(); _main.Dispose(); _gc.Dispose(); }
    void OnApplicationPause(bool paused) { if (paused) Flush(); }

    XRDisplaySubsystem Display()
    {
        if (_display != null && _display.running) return _display;
        SubsystemManager.GetSubsystems(s_Displays);
        _display = null;
        foreach (var d in s_Displays) if (d.running) { _display = d; break; }
        return _display;
    }

    float GpuToMs(float raw)
    {
#if OPENXR_GPU_TIME_IN_MS
        return raw;                                  // OpenXR < 1.18.0-pre.2 wrote ms (Q3-060)
#else
        if (raw > 1f && !_warnedUnits)               // > 1 s of GPU per frame is impossible: it is ms
        { _warnedUnits = true; Debug.LogWarning("[FrameStats] XR GPU time looks like ms; define OPENXR_GPU_TIME_IN_MS."); }
        return raw * 1000f;                          // documented unit: seconds (Q1-097)
#endif
    }

    void Update()
    {
        if (_count >= _rows.Length) return;
        var r = new Row { t = Time.realtimeSinceStartup, mainMs = -1, ftmMainMs = -1, ftmGpuMs = -1,
                          appGpuMs = -1, compGpuMs = -1, dropped = -1, gcMB = -1 };
        if (_main.Valid) r.mainMs = _main.LastValue * 1e-6f;
        if (_gc.Valid)   r.gcMB   = _gc.LastValue / (1024f * 1024f);
#if UNITY_2022_3_OR_NEWER
        // Non-dev builds need Player > Other Settings > Rendering > Frame Timing Stats (U5-027).
        FrameTimingManager.CaptureFrameTimings();
        if (FrameTimingManager.GetLatestTimings(1, _ft) > 0)
        {
            r.ftmMainMs = (float)_ft[0].cpuMainThreadFrameTime; // usable on XR, 4 frames late (Q1-106)
            r.ftmGpuMs  = (float)_ft[0].gpuFrameTime;           // 0 on XR before 6.6; 6.6 unverified (X-C3)
        }
#endif
        var d = Display();
        if (d != null)
        {
            bool okApp  = d.TryGetAppGPUTimeLastFrame(out float app);
            bool okComp = d.TryGetCompositorGPUTimeLastFrame(out float comp);
            bool okDrop = d.TryGetDroppedFrameCount(out int dropped);
            if (okApp)  r.appGpuMs  = GpuToMs(app);
            if (okComp) r.compGpuMs = GpuToMs(comp);
            if (okDrop) r.dropped   = dropped;           // raw; diff offline [verify on device]
            if (!_loggedCaps)                            // which stats this provider fills (Q1-097)
            {
                _loggedCaps = true;
                bool okM2P = d.TryGetMotionToPhoton(out _);
                bool okHz  = d.TryGetDisplayRefreshRate(out float hz);
                Debug.Log($"[FrameStats] caps appGpu={okApp} compGpu={okComp} dropped={okDrop} m2p={okM2P} hz={(okHz ? hz : -1f)}");
            }
        }
        _rows[_count++] = r;
    }

    void Flush()
    {
        if (_rows == null || _count == 0) return;
        var ci = CultureInfo.InvariantCulture;
        var sb = new StringBuilder(_count * 64);
        sb.Append("t_s,main_ms,ftm_main_ms,ftm_gpu_ms,app_gpu_ms,comp_gpu_ms,dropped_raw,gc_reserved_mb\n");
        for (int i = 0; i < _count; i++)
        {
            var r = _rows[i];
            sb.Append(string.Format(ci, "{0:F4},{1:F3},{2:F3},{3:F3},{4:F3},{5:F3},{6},{7:F1}\n",
                r.t, r.mainMs, r.ftmMainMs, r.ftmGpuMs, r.appGpuMs, r.compGpuMs, r.dropped, r.gcMB));
        }
        string path = Path.Combine(Application.persistentDataPath, $"framestats_{System.DateTime.Now:yyyyMMdd_HHmmss}.csv");
        File.WriteAllText(path, sb.ToString());
        Debug.Log($"[FrameStats] wrote {_count} rows to {path}");
        _count = 0;
    }
}
