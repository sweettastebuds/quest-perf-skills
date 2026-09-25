# Lighting setups for Quest (by content type and Unity version)

Reference for `unity-perf:unity-lighting`. Evidence IDs refer to
`research/unity.md` (U*), `research/quest.md` (Q*, QUEST-GF*) and
`research/arm-mobile-hw.md` (A*), all accessed 2026-09-24. Every setup below is
a **starting point to verify** with the A/B in SKILL.md "Diagnose first"; no
source publishes a per-setup ms figure for Quest.

## 1. Setups per content type

### A. Static environment, no moving lights (interiors, menus, most VR worlds)

| Setting | Value | Why |
|---|---|---|
| Lights | Baked; static geometry Contribute GI | Meta: avoid realtime GI, limit per-pixel lights (U4-008) |
| Realtime Global Illumination | Off | U4-008, Q4-071 |
| Dynamic objects | Light Probe Groups (one L2 probe per object) | U4-011; Meta legacy page: probes for dynamic objects (U4-008) |
| SH Evaluation Mode | Auto (resolves to Per Vertex on mobile XR) or explicit Per Vertex | U4-013 |
| Main light shadows | Off, or blob shadows for characters | U4-034 (2018 note, possibly stale) |
| Lightmap Encoding | Normal (RGBM) or Low (dLDR) | U4-035, U4-036, U4-038 |
| Directional Mode | Decide by measurement (U4-C2) | U4-039 |
| Reflections | Baked probes, compressed; Probe Blending and Box Projection off | U4-022, U2-013 |

Applies to: `Quest 2` `Quest 3/3S` `Unity 2021.3+` `URP 12+` `Vulkan` `GLES`.

### B. Sun or key light plus dynamic characters/props (outdoor, arenas)

| Setting | Value | Why |
|---|---|---|
| Lighting Mode | Subtractive (cheapest; one directional realtime shadow) | U4-001, U4-002 |
| Alternative | Baked Indirect if statics must receive realtime shadows from moving lights; cost scales with Max Distance | U4-003 |
| Shadowmask Mode (if Shadowmask) | Shadowmask, not Distance Shadowmask | U4-001, U4-004 |
| Main light shadows | 1 cascade, short Max Distance, lowest acceptable resolution | U4-028, U4-029 |
| Soft shadows | Off, or Low | U2-009, U4-025 |
| Casters | Cast Shadows off on props; Shadows Only proxies for complex meshes | U4-032 |
| Rendering path | Forward (Subtractive and Shadowmask are Forward-optimised) | U4-007 |

Applies to: `Quest 2` `Quest 3/3S` `Unity 2021.3+` `URP 12+`.

### C. Many dynamic lights (about 5+ realtime lights on screen)

| Setting | Value | Why |
|---|---|---|
| Rendering path | Forward+ (choice owned by `unity-perf:unity-urp-settings`) | Meta: wins from about 5 lights (U2-027) |
| Unity version | Prefer 6000.0+; Forward+ XR on 2022.3 unresolved | U1-032, U1-C4 |
| Probe Blending / Probe Atlas Blending | Off (Meta: atlas too costly on Quest) | U2-013 |
| Shadowed lights | Spot only; no shadowed point lights | U4-031 |
| Dynamic resolution | Camera `allowDynamicResolution = true` | Q3-053 |
| Debug | Shader `Universal Render Pipeline > Debug > ForwardPlus` | U2-027 |

Applies to: `Quest 2` `Quest 3/3S` `URP 14+` (`Unity ≥ 6000.0` preferred) `Vulkan` `GLES`.

### D. Few lights, Unity 6.5+ with the Meta Quest build profile

| Setting | Value | Why |
|---|---|---|
| Per Object Limit | 1, if one additional light per object is acceptable | Unrolls the light loop; Meta measured 4.63 -> 4.25 ms (QUEST-GF2-011, device unstated) |
| Custom shaders | Call URP library lighting/shadow functions to inherit the Quest optimisations | U1-036, U3-066 |
| Orthographic cameras | Add the ortho keyword override or lighting is wrong | U1-037 (spelling conflict X-C8, owned by `unity-perf:unity-shader-authoring`) |

Applies to: `Quest 2` `Quest 3/3S` `Unity ≥ 6000.5` `URP 17`. Cost: more variants and build time (U3-068).

### E. Unity 6 with Adaptive Probe Volumes

| Setting | Value | Why |
|---|---|---|
| Light Probe System | APV only if light-probe leaking on large objects is a real problem; otherwise Light Probe Groups | U4-011 |
| SH Evaluation Mode | Per Vertex or Mixed, set explicitly | U4-014, U4-C6 |
| Memory Budget / SH Bands | Low / L1 as the Quest 2 starting point | U4-016 note |
| Probe spacing | Raise the minimum spacing | U4-017 |
| Lighting Scenario blending | Do not plan on it for Quest (conflict: U4-019 documents it, U1-041 says URP on mobile does not support it) | U4-019, U1-041 |
| Streaming | GPU streaming; disk streaming needs it; watch traversal spikes | U4-018 |
| Ambient update | Never `DynamicGI.UpdateEnvironment` per frame | U4-019 |
| GLES | Test for magenta/unlit objects; APV on GLES disputed | U4-020 |

Applies to: `Quest 2` `Quest 3/3S` `Unity ≥ 6000.0` `URP 17` `Vulkan` (GLES unverified). APV runtime cost on Quest: no published number; measure GPU ms with APV per-pixel, APV per-vertex and legacy probes on one scene (U1-041 note).

### F. Mixed reality (passthrough)

Lighting choices as in A or B; the MR-specific cost owner is
`quest-perf:quest-mr-costs`. MRUK EffectMesh has a Cast Shadows option that adds
shadow casters; turn it off unless the room mesh must cast (Q4-033).

## 2. Feature availability by URP version

| Feature | URP 12 (2021.3) | URP 14 (2022.3) | URP 17.0 (6000.0) | Later | Source |
|---|---|---|---|---|---|
| Forward+ | no | yes (XR completeness unresolved) | yes, XR support listed as new | Deferred+ in 6.1 | U1-032, U1-C4, U1-034 |
| Soft-shadow quality tiers | on/off only | tiers; per-light quality from 14.0.3 | per-light ignored on Quest (asset setting only) | - | U2-018, U4-025, U4-026 |
| SH Evaluation Mode | no toggle | yes | yes | - | U4-013 |
| APV | no | no | yes (Lighting Scenario baking from 17.0.2) | - | U4-012 |
| Clustered reflection probes (more than 2 per object) | no | Forward+ | Forward+ | Probe Atlas Blending built in from 6000.3 (Meta fork "Probe Atlas" before) | U1-032, U2-013 |
| Conservative Enclosing Sphere | no | no (URP 15+) | yes | - | U4-033 |
| Quest additional-light perf regression fix | - | check your patch (fix in URP 15.0.0) | included | - | U4-010 |
| Meta Quest build profile | - | - | - | 6.1+; shader optimisations 6.5+ (X-C7) | U2-056, U1-036 |
| `_FORWARD_PLUS` -> `_CLUSTER_LIGHT_LOOP` | - | - | - | 6.1 (shim still sets both) | U1-033 |
| `DistanceAttenuation` 3 arguments on Quest | - | - | - | 6.6 | U1-038 |
| GLES MAX_VISIBLE_LIGHTS 16 -> 32 when "Use OpenGL ES 3.0 shaders" off | - | - | - | 6.6 (UUM-148728 fixed in 6000.6.0f1) | U1-040 |
| Deferred soft shadows on Quest ("variant not found") | - | - | broken | fixed only in 6000.7.0a3 | U1-035 |

## 3. Shadow arithmetic

| Item | Value | Source |
|---|---|---|
| New URP Asset | main and additional shadow maps 2048, Max Distance 50, 1 cascade, soft off | U2-001 |
| Resolution vs texels | halving resolution quarters texels, bandwidth and memory | U4-029 note |
| Distance vs resolution | 1 cascade, Max Distance 40 -> 10: 1024 replaces 2048 and near-field quality improves | U4-029 |
| Additional-light atlas | maps at 256: 1024 atlas holds 16, 512 atlas holds 4 | U4-030 |
| Maps per light | spot 1, point 6 | U4-030 |
| Unity example | 4 shadowed spots + 1 point = 10 maps at 256: fits 1024, not 512 | U4-030 |
| Point light cost | about 6 spot lights | U4-031 |
| Soft filter | Low 4 PCF taps (6000.3 docs) or PCF 3x3 (URP 14.0.3 changelog), Medium 5x5 tent, High 7x7 tent | U4-025, U4-C3 |
| Depth-only caster | Fast-Z at 2x rate with empty fragment and colour writes masked | A3-026 |
| Filtering | hardware PCF (bilinear shadow compare) on Adreno | A2-085 |

Shadow passes store their map by nature (it is sampled later); budget them by
resolution, not by pass-merge state (U2-014). Pass merging:
`unity-perf:unity-render-graph-tiling`.

## 4. Lightmap formats and memory

| Encoding (Player > Other Settings > Lightmap Encoding) | ASTC target | ETC2 target | Range | Source |
|---|---|---|---|---|
| Low: dLDR | ASTC 6x6, 3.56 bpp | ETC2 RGB, 4 bpp | [0, 2], clamps above; decode factor 4.59482 | U4-035, U4-036 |
| Normal: RGBM | ASTC 6x6, 3.56 bpp | ETC2 RGBA, 8 bpp | 0 to 34.49 linear | U4-035, U4-036 |
| High: HDR | ASTC HDR, 3.56 bpp | ASTC HDR | HDR | U4-035 |
| HDR without ASTC HDR support | decompressed at load to RGB9E5 (alpha dropped) or RGBA Half (2x RGB9E5) | - | - | U4-038, U4-049 |

ASTC HDR on Quest: Qualcomm lists HDR and LDR ASTC profiles as supported on
Adreno generally (A2-086); no source confirms it on Quest 2 (Adreno 650) or
Quest 3/3S (Adreno 740) (U4-038). Probe with `AstcHdrProbe.cs`
([lighting-code.md](lighting-code.md)) [verify on device].

| Multiplier | Effect | Source |
|---|---|---|
| Directional Mode = Directional | second texture, about 2x memory, two samples | U4-039 |
| Shadowmask mode | one extra lightmap-sized texture per atlas (RGBA = up to 4 lights) | U4-043 |
| Lightmap Resolution x2 | 4x texels | U4-040 |
| Fixed Lightmap Size | every atlas at Max Lightmap Size (default 1024); recommended with GPU Resident Drawer | U4-040, U4-041, U4-044 |
| Repack Underused Lightmaps | shrinks sparse atlases | U4-041 |
| Lightmap Compression | None, Low, Normal, High Quality | U4-041 |
| Enlighten realtime GI output | RGB9E5 where supported, else RGBM | U4-037 |

The shadowmask texture's compression format on Android is not given by the docs
read; check it in the Memory Profiler (U4-043).

## 5. APV memory (URP 17)

| Memory Budget | Brick-pool texture | L1 (derived) | L2 (derived) |
|---|---|---|---|
| Low | 512 x 512 x 4 | ~16 MiB | ~32 MiB |
| Medium | 1024 x 1024 x 4 | ~64 MiB | ~128 MiB |
| High | 2048 x 2048 x 4 | ~256 MiB | ~512 MiB |

Per-probe storage: L0+L1 red RGBA16F (8 B), L1 green and blue RGBA8 (4 B each),
L2 four more RGBA8 textures; validity R8, or RGBA8 on GLES 3.x (U4-016). The
L1/L2 columns are derived arithmetic from the dossier, not published figures,
and exclude validity, sky occlusion and the scenario-blending pool. Trust the
URP Asset's "Estimated GPU Memory Cost" and the Memory Profiler on device.
Platform memory limits: `quest-perf:quest-budgets-tiers`.

## 6. Reflection probe update cost

| Refresh / slicing | Behaviour | Source |
|---|---|---|
| Every Frame | most expensive | U4-023 |
| On Awake | renders once | U4-023 |
| Via Scripting | on demand | U4-023 |
| All Faces at Once | update spread over 9 frames | U4-023 |
| Individual Faces | spread over 14 frames, lowest per-frame impact | U4-023 |
| No Time Slicing | whole update in one frame; can hitch | U4-023 |

Realtime probes are stored uncompressed; memory scales with resolution and HDR
(U4-022). HDR Cubemap Encoding follows lightmap encoding (U4-024).
