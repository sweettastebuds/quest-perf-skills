# LRZ / early-Z state table for URP materials on Quest

Read with SKILL.md fix 1 and fix 2. Hardware rules are Qualcomm's
(https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/mobile_best_practices.html,
accessed 2026-09-24, [doc]). The ShaderLab column is this repo's mapping, an
inference [verify on device]: confirm with `ovrgpuprofiler -t3 -x=...` and the
per-draw `LRZ State` line (Q1-073). Mechanics (bins, LRZ build during binning,
direction tracking) belong to `arm-mobile-hw-perf:xr2-adreno-architecture`.

Applies to Quest 2 (Adreno 650) and Quest 3/3S (Adreno 740), GLES and Vulkan,
URP 12/14/17.

## Frame-wide killers (until the next depth clear)

| GPU condition | Effect | Typical ShaderLab / URP cause | Fix | ID |
| --- | --- | --- | --- | --- |
| Depth func ALWAYS or NOT_EQUAL, then a depth write | LRZ test **and** write off | `ZTest Always` + `ZWrite On` (custom sky, x-ray/"on top" object that writes depth) | `ZWrite Off`, or draw after everything that benefits from LRZ | A2-032 |
| Depth compare direction changes, then a depth write | Sources conflict. Qualcomm [doc]: test and write off until next clear. Mesa [community]: A650+ tracks direction on the GPU, so the flip may survive on Quest 2/3/3S (A7xx adds bidirectional LRZ, off by default); the shipping driver's policy is unpublished [verify on device] | `ZTest GEqual`/`Greater` material in a `LEqual` pass; reversed-Z tricks | Keep one direction in the main pass | A2-032, A2-031 [community], U3-059 [community] |
| Fixed-function blend or logic op + depth write | LRZ write off (test still works) | Transparent/Blend material with `ZWrite On` | `ZWrite Off` (URP default for Transparent), or draw last | A2-033 |
| Colour mask or partial MRT write + depth write | LRZ write off | `ColorMask 0`/`ColorMask RGB` pass that writes depth mid-frame | Move before opaques as a real depth prepass, or after them | A2-033 |
| Any stencil op + depth write | LRZ write off | `Stencil { ... }` portal/mask draws, stencil-based renderer features, with `ZWrite On` | Draw after all opaques or `ZWrite Off` | A2-033 |
| Framebuffer fetch / advanced blend + depth write | LRZ write off | Programmable blending via framebuffer fetch with depth write | Keep such passes depth-read-only | A2-033 |
| Reading an attachment written in a previous subpass while writing depth | LRZ write off | Render Graph merged pass reading an input attachment while writing depth | See `unity-perf:unity-render-graph-tiling` | A2-033 |

## Per-draw only (does not poison later draws)

| GPU condition | Effect | Typical cause | ID |
| --- | --- | --- | --- |
| Shader writes UAV, depth or stencil | LRZ test and write off for this draw; early-Z off | `SV_Depth` output, `RWTexture`/`RWStructuredBuffer` in fragment | A2-034, A2-038 |
| `discard` | LRZ write off for this draw; early-Z off | `clip()`, Alpha Clipping, `_ALPHATEST_ON` | A2-034, A2-038, U3-060 |
| Alpha-to-coverage | LRZ write off for this draw; early-Z off | `AlphaToMask On` / `AlphaToMask [_AlphaToMask]`; URP 14+ Lit with Alpha Clipping + MSAA | A2-034, A2-038, U3-061 |
| Sample-mask output | LRZ write off for this draw | `SV_Coverage` output | A2-034 |
| Secondary command buffers | Non-issue on A650+ | n/a | A2-036 |

Mesa describes "LRZ feedback" (A650+): discard draws can still update LRZ
during the rendering pass (A2-035, U3-060,
https://docs.mesa3d.org/drivers/freedreno/hw/lrz.html, [community]). Whether
Qualcomm's shipping driver does the same is not published.

## Draw ordering

- Opaque (queue 2000, front-to-back; Adreno has no FPK, A2-039) -> AlphaTest
  (2450) -> Skybox -> Transparent (3000). URP's BaseShaderGUI puts
  Alpha-Clipped materials in AlphaTest (U3-060/061).
- Never move a large occluder or a discard material into an earlier custom
  queue than solid geometry: Qualcomm says put discard draws after all opaque
  draws (A2-041).

## C# material audit (Editor, untested)

Lists materials whose saved state matches a row above. Uses URP Lit/Simple
Lit/Unlit and Shader Graph (Allow Material Override) property names; custom
shaders are reported only if they use the same names. Unity cannot run here:
**untested**; API used exists in 2021.3 through 6.x.

```csharp
// Assets/Editor/QuestLrzMaterialAudit.cs
#if UNITY_EDITOR
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class QuestLrzMaterialAudit
{
    const int AlphaTestQueue = (int)RenderQueue.AlphaTest; // 2450

    [MenuItem("Tools/Quest Perf/Audit Material LRZ States")]
    public static void Run()
    {
        var sb = new StringBuilder("Quest LRZ material audit\n");
        int flagged = 0;
        foreach (string guid in AssetDatabase.FindAssets("t:Material"))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null || m.shader == null) continue;

            bool transparent = Get(m, "_Surface") > 0.5f;
            bool zwrite      = Get(m, "_ZWrite", transparent ? 0f : 1f) > 0.5f;
            bool clip        = Get(m, "_AlphaClip") > 0.5f || m.IsKeywordEnabled("_ALPHATEST_ON");
            bool a2c         = Get(m, "_AlphaToMask") > 0.5f;
            bool zAlways     = m.HasProperty("_ZTest") &&
                               (int)m.GetFloat("_ZTest") == (int)CompareFunction.Always;

            var issues = new StringBuilder();
            if (transparent && zwrite)
                issues.Append(" [blend+ZWrite: LRZ write off until next clear (A2-033)]");
            if (zAlways && zwrite)
                issues.Append(" [ZTest Always+ZWrite: LRZ off until next clear (A2-032)]");
            if (clip && m.renderQueue < AlphaTestQueue)
                issues.Append($" [clip in queue {m.renderQueue} < 2450: draw after opaques (A2-041)]");
            if (a2c)
                issues.Append(" [AlphaToMask on: check alpha is not constant (U3-061)]");
            else if (clip)
                issues.Append(" [clip(): confirm the texture alpha actually varies]");

            if (issues.Length > 0)
            {
                flagged++;
                sb.Append(path).Append(" (").Append(m.shader.name).Append(')')
                  .Append(issues).Append('\n');
            }
        }
        sb.Insert(0, $"{flagged} material(s) flagged\n");
        Debug.Log(sb.ToString());
    }

    static float Get(Material m, string prop, float fallback = 0f)
        => m.HasProperty(prop) ? m.GetFloat(prop) : fallback;
}
#endif
```

It reads serialized material state only. Hard-coded `ZWrite`/`ZTest`/`Stencil`
in a custom shader's ShaderLab is invisible to it; grep `.shader` files for
`ZTest Always` and `Stencil` as well.
