# Overlay layer audit component

Reference for `quest-perf:quest-compositor-layers` (Fix 1, Diagnose step 6).
Meta XR Core SDK v85 OVROverlay API (field names verified against
https://developers.meta.com/horizon/reference/unity/v85/class_o_v_r_overlay/,
accessed 2026-09-24; not in dossier). Unity range per that SDK. Runtime or
dev build; untested in Unity here. `Quest 2` `Quest 3/3S` `GLES` `Vulkan`;
URP-independent.

Usage: add the script to the project, attach it to any GameObject in a
development build, then read the log with `adb logcat -s Unity | grep OverlayLayerAudit`.
Counts only app OVROverlay instances; system layers (Guardian, OVR Metrics
HUD, passthrough) appear only in the VrApi `LCnt` field.

```csharp
// Requires Meta XR Core SDK v85 (OVROverlay; OVROverlay.instances is a List in v85).
// Attach to any GameObject in a dev build.
using System.Text;
using UnityEngine;

public sealed class OverlayLayerAudit : MonoBehaviour
{
    [SerializeField] float intervalSeconds = 5f;
    const int AppLayerBudget = 15; // OVROverlay page; native limit is 16 incl. projection layer
    float _next;

    void Update()
    {
        if (Time.unscaledTime < _next) return;
        _next = Time.unscaledTime + intervalSeconds;

        var sb = new StringBuilder();
        int active = 0, cylinders = 0, cubemaps = 0;
        foreach (var o in OVROverlay.instances)
        {
            if (o == null || !o.isActiveAndEnabled || o.hidden) continue;
            active++;
            if (o.currentOverlayShape == OVROverlay.OverlayShape.Cylinder) cylinders++;
            if (o.currentOverlayShape == OVROverlay.OverlayShape.Cubemap) cubemaps++;
            Texture t = (o.textures != null && o.textures.Length > 0) ? o.textures[0] : null;
            sb.AppendFormat("  {0}: {1}/{2} tex={3} dyn={4} bicubic={5} ssE={6} ssX={7} shE={8} shX={9} auto={10}\n",
                o.name, o.currentOverlayType, o.currentOverlayShape,
                t != null ? t.width + "x" + t.height : (o.isExternalSurface ? "external" : "none"),
                o.isDynamic, o.useBicubicFiltering,
                o.useEfficientSupersample, o.useExpensiveSuperSample,
                o.useEfficientSharpen, o.useExpensiveSharpen, o.useAutomaticFiltering);
        }
        string warn = (active > AppLayerBudget ? " OVER BUDGET" : "")
                    + (cylinders > 1 ? " >1 CYLINDER" : "")
                    + (cubemaps > 1 ? " >1 CUBEMAP" : "");
        Debug.Log($"[OverlayLayerAudit] active={active}/{AppLayerBudget}{warn}\n{sb}");
    }
}
```
