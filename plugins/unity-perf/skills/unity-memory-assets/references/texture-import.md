# Texture import and texture memory on Quest (detail)

Read from `SKILL.md` when choosing ASTC block sizes, auditing importer and
Player settings, sizing the mip-streaming budget, or installing the import
rules below. All finding IDs refer to `research/unity.md`,
`research/arm-mobile-hw.md`, `research/gles3.md` and `research/quest.md`
(accessed 2026-09-24).

## 1. Which compression setting wins (U4-047)

Highest priority first. Applies to Unity 2021.3 to 6000.x (the list form of
the Player setting exists from 2023.1).

| Priority | Where | Path |
|---|---|---|
| 1 | Per-texture platform override | Texture Inspector > Android tab > Override for Android > Format |
| 2 | Build Settings / Build Profile | File > Build Settings (2021.3/2022.3) or File > Build Profiles (6.0+) > Android > Texture Compression (default "Use Player Settings") |
| 3 | Player setting | Project Settings > Player > Android > Other Settings > Texture compression formats. For an APK only the first entry is used. |

Quest store uploads are APKs, so only the first list entry matters. A stray
ETC2 value at priority 2 silently changes every texture that has no
per-texture override (U4-047 notes).

A texture in a format the device cannot sample is decompressed at load, which
costs memory and load time (U4-046). That decompression runs in the AUP
post-process step (U4-081), so it also lengthens loads.

## 2. ASTC block size, bitrate and memory

Bitrates are fixed by block size (U4-049). The MiB columns are arithmetic from
those bitrates, for one 2048x2048 texture, ignoring block-edge rounding; a
full mip chain adds about one third (geometric series, arithmetic).

| Block | bpp (U4-049) | 2048x2048 top mip | with full mips | Default importer quality on Android (U4-048) |
|---|---|---|---|---|
| RGBA32 (uncompressed) | 32 | 16 MiB | about 21.3 MiB | - |
| ASTC 4x4 | 8 | 4 MiB | about 5.3 MiB | High |
| ASTC 5x5 | 5.12 | about 2.56 MiB | about 3.4 MiB | - |
| ASTC 6x6 | 3.56 | about 1.78 MiB | about 2.4 MiB | Normal |
| ASTC 8x8 | 2 | 1 MiB | about 1.33 MiB | Low |
| ASTC 10x10 | 1.28 | about 0.64 MiB | about 0.85 MiB | - |
| ASTC 12x12 | 0.89 | about 0.45 MiB | about 0.59 MiB | - |

Guidance:
- Arm (on Meta's blog, 2020): start at 5x5 or 6x6; move to larger blocks for
  assets that cover less of the view (U4-050). Possibly stale, but block-size
  physics has not changed.
- Qualcomm: ASTC first, then ETC2 (A2-086). ASTC in sRGB where applicable;
  4x4-aligned block formats coalesce fetches (A3-015).
- The claim that ASTC stays compressed in L2 and decompresses into L1 is
  stated for Adreno 5xx only; Adreno 650/740 behaviour is unpublished
  (A3-015). [verify on device] with `% Texture L1 Miss` for ASTC vs
  uncompressed on the same draw.
- No per-block-size GPU-ms or bandwidth figure exists for Quest (U4-050
  notes). Method: full-screen material, A/B 4x4 vs 6x6, read
  `Texture Memory Read BW` and `% Texture Fetch Stall` in RenderDoc Meta Fork
  draw metrics (Q1-062) or ovrgpuprofiler realtime (Q1-066).

### ASTC decode mode (GLES)

`GL_EXT_texture_compression_astc_decode_mode` is present on Quest 2 from
driver V@0690 and on Quest 3 (gles3.md section 7.1 matrix, gpuinfo reports,
[measured]). Decoding LDR ASTC to UNORM8 instead of the RGBA16F default
reduces texture-cache footprint and power (G3-063, U4-052). No source says
whether Unity sets it on Quest (U4-052 notes); treat as not used.

### ASTC HDR: conflicting evidence

- unity.md: no source confirms ASTC HDR on Adreno 650/740. Without it, Unity
  decompresses ASTC HDR at load to RGB9E5 (alpha dropped) or RGBA Half, and
  RGBA Half is twice the memory of RGB9E5 (U4-049, U4-038).
- gles3.md section 7.1: the gpuinfo-derived matrix lists
  `GL_KHR_texture_compression_astc_ldr / _hdr` as "yes" on Quest 2 and Quest
  3 ([measured]; the row merges LDR and HDR, so it does not isolate HDR).
- arm-mobile-hw.md: Qualcomm's Adreno overview says "HDR and LDR ASTC
  profiles are supported" (A2-086 [doc],
  https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/overview.html).
- Check on device: `SystemInfo.SupportsTextureFormat(TextureFormat.ASTC_HDR_6x6)`
  at startup, and on Vulkan `adb shell vulkaninfo` for
  `textureCompressionASTC_HDR` (U4-038). [verify on device] Lightmap and reflection-probe HDR formats are
  `unity-perf:unity-lighting`.

## 3. Normal maps (U4-051, U4-052)

- Player > Android > Other Settings > Normal Map Encoding: XYZ or
  DXT5nm-style (Unity 2022.x to 6000.x; check your version has the option).
- DXT5nm-style defines `UNITY_ASTC_NORMALMAP_ENCODING` and decodes with
  `UnpackNormalAG` (Z rebuilt from X and Y, one sqrt). XYZ defines
  `UNITY_NO_DXT5nm` and uses `UnpackNormalRGBNoScale`. Both come from
  `Packing.hlsl`; call `UnpackNormal` / `UnpackNormalScale` in URP shaders
  and the define picks the path.
- Arm's astc-encoder guidance matches DXT5nm-style: store X, Y as L+A
  (`rrrg`), sample `.ga`, rebuild Z (U4-052).
- Trade: better ASTC quality vs a few ALU ops per sample. No Quest GPU-ms
  figure; measure on a normal-map-dominated view.

## 4. Read/Write (U4-054)

- Read/Write on keeps a CPU copy: the texture's memory doubles.
- It also disqualifies the texture from AUP (U4-078).
- Runtime-generated textures: `tex.Apply(updateMipmaps: true,
  makeNoLongerReadable: true)` frees the CPU copy. After that the uploaded
  resolution is fixed and stops following later mipmap-limit changes unless
  it was uploaded at full resolution or sets `ignoreMipmapLimit`
  (2022.2+).

## 5. Mipmaps, mipmap limits, stripping

| Setting | Path | Values | Source |
|---|---|---|---|
| Global Mipmap Limit | Project Settings > Quality > Textures | 0 Full, 1 Half, 2 Quarter, 3 Eighth | U4-057 |
| Mipmap Limit Groups | Project Settings > Quality > Textures | offset -3 to +3, or override (2022.2+) | U4-057 |
| Per-texture opt-out | Texture Inspector > Mipmap Limit checkbox / group | - | U4-057 |
| 2021.3 equivalent | `QualitySettings.masterTextureLimit` (Texture Quality) | - | U4-057 |
| Texture Mipmap Stripping | Player > Android > Other Settings | strips mips no quality level uses | U4-058 |

- Quest 2 tier: Meta says use ASTC on both headsets and lower-resolution
  textures or fewer mips on Quest 2 (6 GB vs 8 GB) (U4-053). The global limit
  or a Mipmap Limit Group per content class is the cheapest lever (U4-057
  notes).
- Stripping cuts build size and load I/O; if a later limit targets a stripped
  level, Unity snaps to the nearest remaining level (U4-058).
- Unity 6.0 change: mipmap limits no longer apply to textures created at
  runtime by default (U1-089). Procedural textures that relied on the global
  limit grow after the 2022.3 -> 6.0 upgrade. [verify on device]
- UI textures: disable mipmaps (UNITY-GF1-017). In VR, world-space UI seen at
  a distance then minifies without mips and can shimmer; keep mips on UI that
  is shown far away.

## 6. Mipmap streaming

Quality settings (U4-059; "Texture Streaming" renamed "Mipmap Streaming" in
newer docs), Unity 2021.3 to 6000.x:

| Setting | Default | Note |
|---|---|---|
| Add All Cameras | - | |
| Memory Budget | 512 MB | not sized for Quest; size from `Texture.desiredTextureMemory` (U4-059, U4-060) |
| Renderers Per Frame | 512 | |
| Max Level Reduction | 2 | also the mip streaming textures load at first |
| Max IO Requests | 1024 | |

Limits (U4-060, U4-062):
- The budget also counts non-streamed textures.
- Not supported: terrain, texture arrays, cubemap arrays, 3D textures.
- `Graphics.DrawMeshNow` draws get the lowest allowed mip.
- The shader needs the texture's `_ST` property; the renderer needs a
  MeshFilter or SkinnedMeshRenderer.
- Procedural or runtime meshes need `Mesh.RecalculateUVDistributionMetrics()`.
- Per texture: Stream Mipmap Levels on; Priority -128..127 is both allocation
  priority and mip bias (priority 2 aims two levels sharper than 0) (U4-061).

Unknown: how streaming picks mips for stereo XR cameras (multiview or two
eyes). No Unity or Meta page says (U4-063). [verify on device]: log
`desiredMipmapLevel` vs `loadedMipmapLevel` for a close-up texture and turn
the head quickly to look for blur.

Debug APIs (U4-066): `Texture.currentTextureMemory`, `desiredTextureMemory`,
`totalTextureMemory`, `targetTextureMemory`, `nonStreamingTextureMemory`,
`streamingMipmapUploadCount`, `streamingTextureCount`; per texture
`Texture2D.desiredMipmapLevel`, `loadingMipmapLevel`, `loadedMipmapLevel`. In
URP the Rendering Debugger visualises streaming.

## 7. Anisotropic filtering

- Quality > Anisotropic Textures: Disabled, Per Texture, Forced On. Unity says
  aniso increases rendering time; importer Aniso Level is best for floors and
  ground (U4-056).
- Meta's guidance moved from "disable" (2018, Mali reason, not Adreno) to "one
  lookup per fragment" (legacy) to "trilinear or anisotropic" (2024)
  (U4-055, conflict U4-C4, resolved as method: Per Texture and measure).
- One measured case: 8x aniso on every mipmapped texture cost 8.9 ms of a
  13.8 ms frame on Quest 3 (Functor engine, not Unity; 72 Hz) (Q1-075,
  [community][measured]). Size in URP will differ; the method carries over:
  A/B at level 1 and watch `percent_texture_anisotropic_filtered` and
  `percent_texture_fetch_stall`.
- Filtering cost model (trilinear, aniso, wide formats): owned by
  `arm-mobile-hw-perf:xr2-shader-cost-model` (A3-017).

## 8. Import rules as code (AssetPostprocessor)

Unity recommends enforcing import settings with `AssetPostprocessor`
(UNITY-GF1-017). This version compiles on Unity 2021.3 through 6000.x
(Editor only). Read/Write off and the Android ASTC default are enforced on
every import (the ASTC rule never overwrites an Android override an artist
already set). Mip and streaming settings are defaults applied only on first
import, so later artist choices (for example mips kept on far world-space
UI) survive reimports.

```csharp
// Assets/Editor/QuestTextureImportRules.cs
// Unity 2021.3 - 6000.x. Editor only.
// Put textures that must stay CPU-readable under any folder named "Readable".
#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public sealed class QuestTextureImportRules : AssetPostprocessor
{
    const string kAndroid = "Android";
    // Arm: start at 5x5 or 6x6, larger blocks for small-on-screen assets (U4-050).
    const TextureImporterFormat kDefaultAstc = TextureImporterFormat.ASTC_6x6;

    void OnPreprocessTexture()
    {
        var ti = (TextureImporter)assetImporter;

        // Lightmaps, cookies and HDR sources are owned by unity-lighting; leave them alone.
        if (ti.textureType == TextureImporterType.Lightmap ||
            ti.textureType == TextureImporterType.Cookie ||
            ti.textureType == TextureImporterType.DirectionalLightmap ||
            ti.textureType == TextureImporterType.Shadowmask)
            return;

        bool isUi = ti.textureType == TextureImporterType.Sprite ||
                    ti.textureType == TextureImporterType.GUI;

        // Read/Write doubles memory and blocks AUP (U4-054, U4-078).
        if (!assetPath.Contains("/Readable/"))
            ti.isReadable = false;

        // Mip + streaming defaults: first import only, so artists can override
        // later (e.g. keep mips on far world-space UI).
        if (assetImporter.importSettingsMissing)
        {
            if (isUi)
            {
                ti.mipmapEnabled = false;      // UNITY-GF1-017
                ti.streamingMipmaps = false;
            }
            else
            {
                ti.mipmapEnabled = true;
                ti.streamingMipmaps = true;    // opt in; enable streaming in Quality settings too
            }
        }

        TextureImporterPlatformSettings s = ti.GetPlatformTextureSettings(kAndroid);
        if (!s.overridden)
        {
            s.overridden = true;
            s.format = kDefaultAstc;
            ti.SetPlatformTextureSettings(s);
        }
    }
}
#endif
```

Notes:
- The rule only fires on (re)import. Reimport the folder after adding it;
  existing textures (which already have .meta files) keep their mip and
  streaming settings and get only the Read/Write and ASTC rules.
- `ASTC_6x6` on an HDR source produces LDR ASTC; HDR sources are excluded
  above only by type, so check `.exr`/`.hdr` files by hand.
- Batch conversion changes the look of every texture: review 4x4 candidates
  (UI text, hero props, faces) before shipping.
