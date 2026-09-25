# Variant counting and stripping: per-version controls and C#

Deep reference for `unity-perf:unity-shader-hitches`. Read it when a build's
variant count or shader size is high, when you need to write or audit a
stripper, or when you change URP assets or quality tiers. Fewer variants means
fewer PSOs to trace and warm (Consistency) and shorter builds. The GPU cost of
keyword vs `dynamic_branch` choices belongs to `unity-perf:unity-shader-authoring`.
All sources were accessed 2026-09-24.

## 1. Where variant counts come from

| Source of variants | Rule | Applies to | Source |
|---|---|---|---|
| `multi_compile` | Every combination compiles. Unity's example: 8 keyword sets of 3 can exceed 6,000 variants (U3-071). | all | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-conditionals-choose-a-type.html [doc] |
| `shader_feature` | Only combinations used by materials in the build (U3-071). | all | same |
| `dynamic_branch` | One variant; keyword becomes a per-draw uniform (U3-071). Cost trade: `unity-perf:unity-shader-authoring`. | 2022.1+ | same |
| Keyword totals | More than 128 keywords per shader carries a small runtime penalty; Unity reserves 4 per shader. 2022.3 ceilings: about 4.29 billion global, 65,534 local per shader. Use `_local` and `_vertex`/`_fragment` scopes (U3-072). | 2021.2+ keyword system | https://docs.unity3d.com/6000.6/Documentation/Manual/SL-MultipleProgramVariants-declare.html ; https://docs.unity3d.com/2022.3/Documentation/Manual/shader-keywords.html [doc] |
| XR default keywords | `STEREO_INSTANCING_ON`, `STEREO_MULTIVIEW_ON`, `STEREO_CUBEMAP_RENDER_ON`, `UNITY_SINGLE_PASS_STEREO` are added to every graphics shader; URP strips XR variants when the XR modules are disabled (U3-048). | all | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-keywords-default.html [doc] |
| Several URP Assets | URP strips by the features enabled across EVERY URP Asset in the build; mixed rendering paths or features multiply variants. Unity advises against mixing rendering paths (U3-078). | URP 12+ | https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-features.html [doc] |
| Shader Graph keyword Definition | Shader Feature strips unused combos; Multi Compile compiles all; Predefined reuses a defined keyword. Stage can be All/Vertex/Fragment (UNITY-GF1-003). | Shader Graph 12+ | https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Keywords-reference.html [doc] |
| Shader Graph Allow Material Override | Replaces defines with `shader_feature` keywords `_SURFACE_TYPE_TRANSPARENT`, `_ALPHAPREMULTIPLY_ON`, `_ALPHAMODULATE_ON`, `_ALPHATEST_ON`, and on Lit `_SPECULAR_SETUP`, `_RECEIVE_SHADOWS_OFF`; render states become material-driven, so every distinct material configuration is a variant and every render-state combination a distinct Vulkan PSO. DepthOnly and Lit ShadowCaster passes are always generated (UNITY-GF2-002). | URP 12 (no `_ALPHAMODULATE_ON`), 14, 17.x | https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Targets/UniversalTarget.cs [doc] |

## 2. Shader Graph variant limit by branch (UNITY-GF2-001)

A build-time tripwire, not a runtime cost.

| Unity / Shader Graph | Where | Effective default |
|---|---|---|
| 2021.3 / SG 12 | Preferences > Shader Graph > Shader Variant Limit (per user, EditorPrefs `UnityEditor.ShaderGraph.VariantLimit`) | 128 (field initializer says 2048; `GetInt(..., 128)` wins). Differs per machine: put the value in the team setup doc. |
| 2022.3 / SG 14 | Project Settings > Shader Graph > Shader Variant Limit | 2048, no override toggle; per-user Preview Variant Limit 128 |
| 6000.0-6000.6 / SG 17.x | Project Settings > Shader Graph; Override Variant Limit toggle | 2048 (`defaultVariantLimit`) unless overridden (6000.6 inferred from master) |

Sources: https://github.com/Unity-Technologies/Graphics/blob/2021.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphPreferences.cs ;
https://github.com/Unity-Technologies/Graphics/blob/2022.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs ;
https://github.com/Unity-Technologies/Graphics/blob/6000.3/staging/Packages/com.unity.shadergraph/Editor/ShaderGraphProjectSettings.cs [doc].
A graph near 2048 variants is far past what a Quest title should ship
(UNITY-GF1-004 notes).

## 3. URP stripping controls by version (U3-077)

| URP | Location | Controls |
|---|---|---|
| 12 (2021.3) | URP Global Settings | Strip Debug Variants, Strip Unused Post Processing Variants, Strip Unused Variants |
| 14 (2022.3) | URP Global Settings | as 12, plus Strip Screen Coord Override Variants and Shader Variant Log Level |
| 17.x (6.x) | Project Settings > Graphics > Additional Shader Stripping Settings | Strip Unused Variants, Strip Unused Post Processing Variants, Strip Screen Coord Override Variants, Shader Variant Log Level, Export Shader Variants |

- Export writes `Temp/graphics-settings-stripping.json` and
  `Temp/shader-stripping.json`. The log prints lines such as
  `Universal Render Pipeline/Lit - Total=8/39(20.51%)`.
- Strip Unused Variants also strips DOTS instancing variants, which conflicts
  with BRG/GPU Resident Drawer. GRD projects keep them with Graphics >
  BatchRendererGroup Variants (U3-077 notes).
- Sources: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-features.html ;
  https://docs.unity3d.com/6000.6/Documentation/Manual/urp/shader-stripping-check.html ;
  https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@14.0/manual/urp-global-settings.html [doc]

## 4. Engine-level controls by version

| Control | Unity | Effect | Source |
|---|---|---|---|
| Player > Strict shader variant matching | 2022.3+ (not on 2021.3 Android page) | Missing variant renders the error shader and logs shader, subshader, pass, keywords, instead of silently using the closest match (U3-073). Turn on in test builds after any stripping change. | https://docs.unity3d.com/6000.6/Documentation/Manual/class-PlayerSettingsAndroid.html [doc] |
| Graphics > Shader Build Settings | 6.3+ | Add keywords and set a Type Override (`shader_feature` or `dynamic_branch`) per build profile, overriding shader source; cheapest way to shrink URP `multi_compile` sets on Quest without forking URP (U3-074). | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html [doc] |
| Build Profile per-profile keyword exclusion | 6.3+ | Per-profile exclusion of shader code for keywords (U1-052). | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity63.html [doc] |
| Shader Constant Defines | 6.6 only (not in 6.0-6.5 manual) | Per-profile compile-time constant, for example `NUMBER_OF_MSAA_SAMPLES 2`, guarded by `#ifndef` in the shader: no variant created (U3-075/U1-051) [verify on device]. | https://docs.unity3d.com/6000.6/Documentation/Manual/WhatsNewUnity66.html [doc] |
| Always Included Shaders | all | Forces every variant; Unity warns against it in favour of GSCs (U3-089). | https://docs.unity3d.com/6000.6/Documentation/Manual/class-GraphicsSettings.html [doc] |
| `IPreprocessShaders` / `IPreprocessComputeShaders` | all | Project-specific stripping before each pass or kernel compiles (U3-076). | https://docs.unity3d.com/6000.6/Documentation/Manual/shader-variant-stripping.html [doc] |

Shader Constant Defines pattern (6.6; HLSL side, any URP 17 shader):

```hlsl
// Value comes from the build profile's Shader Constant Defines; fallback for other profiles.
#ifndef NUMBER_OF_MSAA_SAMPLES
    #define NUMBER_OF_MSAA_SAMPLES 4
#endif
```

## 5. Quest XR keyword stripper (Unity 2021.3+, URP 12+)

Editor-only; put it in an `Editor` folder. Strips XR default keywords a
Quest build never uses (U3-048). On Quest, URP's XR pass enables
`STEREO_MULTIVIEW_ON` when `SystemInfo.supportsMultiview` is true and
`STEREO_INSTANCING_ON` otherwise (U3-043,
https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.core/Runtime/XR/XRPass.cs [doc]);
Quest supports multiview (U3-042). So never strip `STEREO_MULTIVIEW_ON`.
`STEREO_INSTANCING_ON` is a strip candidate only after logging
`supportsMultiview == true` on Quest 2 and Quest 3 [verify on device]. After
enabling it, build with Strict shader variant matching on (2022.3+) and look
at both eyes. Stripping the active keyword gives left-eye-only rendering or
the error shader (U3-048 notes).

```csharp
// Editor/QuestXrKeywordStripper.cs -- Unity 2021.3+. Untested.
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Rendering;
using UnityEngine;
using UnityEngine.Rendering;

sealed class QuestXrKeywordStripper : IPreprocessShaders
{
    // Opt-in: flip ONLY after logging SystemInfo.supportsMultiview == true on Quest 2 and Quest 3.
    const bool StripStereoInstancing = false; // STEREO_INSTANCING_ON
    const bool StripStereoMultiview  = false; // STEREO_MULTIVIEW_ON: never set true on Quest (active keyword, U3-043)

    static readonly ShaderKeyword kCubemap    = new ShaderKeyword("STEREO_CUBEMAP_RENDER_ON");
    static readonly ShaderKeyword kDoubleWide = new ShaderKeyword("UNITY_SINGLE_PASS_STEREO");
    static readonly ShaderKeyword kInstancing = new ShaderKeyword("STEREO_INSTANCING_ON");
    static readonly ShaderKeyword kMultiview  = new ShaderKeyword("STEREO_MULTIVIEW_ON");

    public int callbackOrder => 0;

    public void OnProcessShader(Shader shader, ShaderSnippetData snippet, IList<ShaderCompilerData> data)
    {
        if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.Android) return;
        int before = data.Count;
        for (int i = data.Count - 1; i >= 0; --i)
        {
            ShaderKeywordSet ks = data[i].shaderKeywordSet;
            bool strip = ks.IsEnabled(kCubemap) || ks.IsEnabled(kDoubleWide)
                      || (StripStereoInstancing && ks.IsEnabled(kInstancing))
                      || (StripStereoMultiview  && ks.IsEnabled(kMultiview));
            if (strip) data.RemoveAt(i);
        }
        if (before != data.Count)
            Debug.Log($"[QuestXrKeywordStripper] {shader.name} {snippet.passName} {snippet.shaderType}: {before} -> {data.Count}");
    }
}
```

If the project also ships non-Quest Android targets from the same project,
gate on a build profile or scripting define instead of `BuildTarget.Android`.

## 6. Counting workflow

1. Set Shader Variant Log Level to "All" (URP 14+) or use Export Shader
   Variants (6.x). Build once. Record per-shader `Total=kept/all` lines.
2. Sort by kept count. The top shaders are where stripping pays off.
3. For each top shader, check: `multi_compile` sets that could be
   `shader_feature` or retyped via Shader Build Settings (6.3+); keywords that
   could be `_local`/stage-scoped; Allow Material Override on high-count
   environment graphs (prefer separate opaque and alpha-clipped graph assets,
   UNITY-GF2-002 notes); extra URP Assets whose feature toggles differ.
4. Rebuild with Strict shader variant matching on and play the full route:
   any error-shader material means a variant you still need was stripped.
5. Re-trace the GSC: fewer variants should mean a smaller
   `totalGraphicsStateCount` and a shorter warm window.

No dossier gives a runtime ms cost per variant or a MB figure for shader
data in the build; measure build size and warm time before and after.
