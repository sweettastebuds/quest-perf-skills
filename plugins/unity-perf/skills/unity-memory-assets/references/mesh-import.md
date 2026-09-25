# Mesh import, vertex formats and index formats on Quest (detail)

Read from `SKILL.md` when auditing model importer and Player mesh settings,
when vertex fetch or binning cost shows up in counters, or before splitting
the position stream. Finding IDs refer to `research/unity.md` and
`research/arm-mobile-hw.md` (accessed 2026-09-24). The hardware reason
(binning pass, bins, vertex re-shading) is owned by
`arm-mobile-hw-perf:xr2-adreno-architecture`; this file covers what to set in
Unity.

## 1. Settings that change mesh memory and fetch cost

| Setting | Path | What it does | Runtime memory? | Source |
|---|---|---|---|---|
| Vertex Compression | Player > Android > Other Settings > Vertex Compression | FP32 -> FP16 for selected channels. Default: Normal, Tangent, TexCoord0, TexCoord2, TexCoord3. Position and TexCoord1 (lightmap UV) stay FP32. | yes (about 1.45x smaller in Unity's example mesh with normals, tangents, colour, 3 UV sets) | U4-068 |
| Mesh Compression | Model importer > Model > Mesh Compression (Off/Low/Medium/High) | Quantises on disk only. High: vertices about 3.2x, normals about 7.4x. Costs CPU and temp memory at load. | no | U4-069 |
| Optimize Mesh Data | Player > Android > Other Settings (`PlayerSettings.stripUnusedMeshComponents`) | Strips vertex attributes no material in the build uses | yes | U4-070 |
| Index Format | Model importer > Model > Index Format (Auto/16-bit/32-bit) | 16-bit splits meshes over 64k vertices into chunks | yes (half the index bytes) | U4-071 |
| Optimize Mesh | Model importer > Model > Optimize Mesh (default Everything) | Reorders vertices and polygons | no | U4-071, A3-019 |
| Weld Vertices | Model importer > Model (default on) | Merges identical vertices | yes | U4-071 |
| Read/Write | Model importer > Model > Read/Write (default off) | Keeps a CPU copy | yes (CPU copy) | U4-073 |

Vertex Compression applies only when all hold (U4-068): Read/Write off, mesh
not skinned, platform supports FP16, Mesh Compression Off, mesh not
dynamic-batched.

Consequences:
- Mesh Compression On disables vertex compression and AUP for that mesh
  (U4-069). For Quest: leave it Off on runtime meshes and rely on LZ4 build
  compression for disk size (U4-069 notes).
- Optimize Mesh Data + a runtime material swap to a shader that needs a
  stripped channel (for example tangents) renders wrong (U4-070).
- Skinned meshes: position, normal and tangent are forced to Float32 (U4-072),
  so they get neither vertex compression nor FP16 positions, and bone
  weights force the synchronous upload path (U4-078).

## 2. Index format and vertex-cache order

- Adreno supports 8-, 16- and 32-bit indices; Qualcomm: prefer 8-bit, else
  16-bit, avoid 32-bit (A2-049, A3-018).
- Unity's `IndexFormat` is only `UInt16` or `UInt32`: 8-bit is not available
  (A3-018 notes). Use 16-bit where possible (U4-071).
- A7x (Adreno 740, Quest 3/3S) post-transform vertex cache: 32 four-component
  vertices (A2-049, A3-019). Vertex-cache-optimised index order still pays
  off. Unity's Optimize Mesh reorders indices but does not document its
  target cache size (A3-019 notes). [verify on device] with
  `Avg Bytes/Vertex` and `Reused Vertices/Second` in RenderDoc Meta Fork
  draw metrics (Q1-062).

## 3. Custom vertex layouts (`VertexAttributeDescriptor`, U4-072)

- Each attribute's byte size must be a multiple of 4: Float16 x3 is invalid,
  use x4.
- Up to 4 vertex streams per mesh.
- Attributes inside one stream follow the `VertexAttribute` enum order
  (Position, Normal, Tangent, Color, TexCoord0..7, BlendWeight,
  BlendIndices).
- Check format support at runtime with
  `SystemInfo.SupportsVertexAttributeFormat(format, dimension)`.
- Qualcomm: Vulkan does not yet support half precision in vertex shaders;
  GLES has `GL_OES_vertex_half_float`. The storage format can still be half
  (A2-048, A3-018 notes). This is storage, not ALU precision.

## 4. Position-only stream 0

Qualcomm (A2-048, A3-018): the binning pass runs a driver-generated
position-only vertex shader over every draw (A2-046), so put position alone
in the first stream (or first in the interleave) and everything else in a
second stream. Meta gives the same advice: position and skinning data in
their own stream, unused channels removed, half precision for non-position
attributes (Q2-034 notes, quest.md).

Whether Unity's importer or URP ever splits streams by default is not
documented (A2-048 notes). Imported meshes should be assumed single-stream.
No Quest ms figure exists for the split. [verify on device]: RenderDoc Meta
Fork `Vertex Memory Read` and `% Vertex Fetch Stall` before and after, on a
vertex-heavy view.

The Editor tool below writes a two-stream copy of a static mesh. Unity
2021.3 to 6000.x. It refuses skinned meshes, blend shapes and meshes using
TexCoord2+ (extend it if you need them). Mesh LOD data (6.2+) is not copied.

```csharp
// Assets/Editor/QuestPositionStreamSplitter.cs
// Unity 2021.3 - 6000.x. Editor only.
// Select a Mesh asset (expand the model and pick the mesh sub-asset), then
// Assets > Quest > Split Position Stream. Enable Read/Write on the source model
// while converting, then turn it off again.
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class QuestPositionStreamSplitter
{
    [MenuItem("Assets/Quest/Split Position Stream")]
    static void Split()
    {
        var src = Selection.activeObject as Mesh;
        if (src == null) { Debug.LogError("Select a Mesh asset."); return; }
        if (!src.isReadable) { Debug.LogError($"{src.name}: enable Read/Write on the model importer first."); return; }
        if (src.HasVertexAttribute(VertexAttribute.BlendWeight) || src.blendShapeCount > 0)
        { Debug.LogError($"{src.name}: skinned/blend-shape meshes keep FP32 and the sync path (U4-072, U4-078)."); return; }
        for (int uv = 2; uv < 8; uv++)
            if (src.HasVertexAttribute(VertexAttribute.TexCoord0 + uv))
            { Debug.LogError($"{src.name}: uses TexCoord{uv}; extend the tool first."); return; }

        int vc = src.vertexCount;
        bool hasN = src.HasVertexAttribute(VertexAttribute.Normal);
        bool hasT = src.HasVertexAttribute(VertexAttribute.Tangent);
        bool hasC = src.HasVertexAttribute(VertexAttribute.Color);
        bool hasUv0 = src.HasVertexAttribute(VertexAttribute.TexCoord0);
        bool hasUv1 = src.HasVertexAttribute(VertexAttribute.TexCoord1);

        // Stream 0: position only, FP32. Stream 1: everything else, packed.
        var attrs = new List<VertexAttributeDescriptor>
        {
            new VertexAttributeDescriptor(VertexAttribute.Position, VertexAttributeFormat.Float32, 3, 0)
        };
        int stride1 = 0;
        if (hasN)   { attrs.Add(new VertexAttributeDescriptor(VertexAttribute.Normal,    VertexAttributeFormat.Float16, 4, 1)); stride1 += 8; }
        if (hasT)   { attrs.Add(new VertexAttributeDescriptor(VertexAttribute.Tangent,   VertexAttributeFormat.Float16, 4, 1)); stride1 += 8; }
        if (hasC)   { attrs.Add(new VertexAttributeDescriptor(VertexAttribute.Color,     VertexAttributeFormat.UNorm8,  4, 1)); stride1 += 4; }
        if (hasUv0) { attrs.Add(new VertexAttributeDescriptor(VertexAttribute.TexCoord0, VertexAttributeFormat.Float16, 2, 1)); stride1 += 4; }
        // Lightmap UVs stay FP32, as Unity's own vertex compression does (U4-068).
        if (hasUv1) { attrs.Add(new VertexAttributeDescriptor(VertexAttribute.TexCoord1, VertexAttributeFormat.Float32, 2, 1)); stride1 += 8; }

        Vector3[] pos = src.vertices;
        Vector3[] nrm = hasN ? src.normals : null;
        Vector4[] tan = hasT ? src.tangents : null;
        Color32[] col = hasC ? src.colors32 : null;
        var uv0 = new List<Vector2>(); if (hasUv0) src.GetUVs(0, uv0);
        var uv1 = new List<Vector2>(); if (hasUv1) src.GetUVs(1, uv1);

        var s1 = new byte[Math.Max(1, vc * stride1)];
        int o = 0;
        for (int i = 0; i < vc; i++)
        {
            if (hasN)   { H(s1, ref o, nrm[i].x); H(s1, ref o, nrm[i].y); H(s1, ref o, nrm[i].z); H(s1, ref o, 0f); }
            if (hasT)   { H(s1, ref o, tan[i].x); H(s1, ref o, tan[i].y); H(s1, ref o, tan[i].z); H(s1, ref o, tan[i].w); }
            if (hasC)   { s1[o++] = col[i].r; s1[o++] = col[i].g; s1[o++] = col[i].b; s1[o++] = col[i].a; }
            if (hasUv0) { H(s1, ref o, uv0[i].x); H(s1, ref o, uv0[i].y); }
            if (hasUv1) { F(s1, ref o, uv1[i].x); F(s1, ref o, uv1[i].y); }
        }

        var dst = new Mesh { name = src.name + "_q2s" };
        dst.SetVertexBufferParams(vc, attrs.ToArray());
        dst.SetVertexBufferData(pos, 0, 0, vc, 0);
        if (stride1 > 0) dst.SetVertexBufferData(s1, 0, 0, vc * stride1, 1);

        dst.indexFormat = vc <= 65535 ? IndexFormat.UInt16 : IndexFormat.UInt32; // U4-071, A2-049
        dst.subMeshCount = src.subMeshCount;
        for (int sm = 0; sm < src.subMeshCount; sm++)
            dst.SetTriangles(src.GetTriangles(sm), sm, false);
        dst.bounds = src.bounds;
        dst.RecalculateUVDistributionMetrics(); // needed by mip streaming (U4-062)

        string path = AssetDatabase.GenerateUniqueAssetPath(
            System.IO.Path.GetDirectoryName(AssetDatabase.GetAssetPath(src)).Replace('\\', '/') + "/" + dst.name + ".asset");
        AssetDatabase.CreateAsset(dst, path);

        // Ship it non-readable (U4-073). [verify in Editor] that the field name exists in your version.
        var so = new SerializedObject(dst);
        var readable = so.FindProperty("m_IsReadable");
        if (readable != null) { readable.boolValue = false; so.ApplyModifiedPropertiesWithoutUndo(); }
        AssetDatabase.SaveAssets();
        Debug.Log($"{src.name}: wrote {path} (stream0 12 B/vtx, stream1 {stride1} B/vtx, {dst.indexFormat}).");
    }

    static void H(byte[] b, ref int o, float v)
    {
        ushort h = Mathf.FloatToHalf(v);
        b[o++] = (byte)h; b[o++] = (byte)(h >> 8);
    }

    static void F(byte[] b, ref int o, float v)
    {
        byte[] bytes = BitConverter.GetBytes(v); // little-endian on all Unity targets
        b[o++] = bytes[0]; b[o++] = bytes[1]; b[o++] = bytes[2]; b[o++] = bytes[3];
    }
}
#endif
```

Caveats:
- Static batching combines meshes at build or load time; whether the combined
  mesh keeps two streams is not documented. [verify on device] in RenderDoc
  Meta Fork (vertex input bindings of a static-batched draw).
- The copy is a new asset: re-point MeshFilters to it, and re-run after every
  source change. Mesh LOD (6.2+) data on the source is lost.
- Normal FP16 precision is enough for shading; FP16 UV0 loses precision on
  large tiling UVs (values far from 0). Keep UV0 FP32 for world-space-tiled
  terrain-like meshes.

## 5. Read/Write and activation cost

Runtime cases that need a readable mesh (U4-073): runtime
`StaticBatchingUtility.Combine`, `CanvasRenderer.SetMesh`, runtime NavMesh
baking, some MeshCollider cases (negative scale with convex, skewed
transforms, non-default cooking options), particle mesh emission without GPU
instancing. Everything else: Read/Write off. `Mesh.UploadMeshData(true)`
frees the CPU copy of a runtime-built mesh.

Meta's 2021 Quest 2 profiling (Unity 2020.3.8f1, possibly stale) (U4-075,
[measured], relative only):
- Activation cost grows linearly with GameObject count.
- TextMeshPro > ParticleSystem > MeshFilter/MeshRenderer.
- CPU-readable meshes (Read/Write on, or skinned with bones or blend shapes)
  have a steep activation cost. Meta advises splitting modular characters
  into separate meshes.

## 6. Mesh LOD (Unity 6.2+) vs LOD Group

- Mesh LOD generates LODs on import and stores them in the index buffer of
  the original mesh, with no extra GameObjects; Unity says less memory and
  lower overhead than LOD Group (U1-059). 6.4 added an inspector preview, 6.5
  Entities Graphics support.
- Inference to verify: the full LOD0 vertex buffer stays resident and bound
  for every LOD, so triangle and raster cost drop but vertex memory does not
  (U1-059 notes). [verify on device]
- Limits (U1-060): Particle System, VFX Graph and static batching always use
  LOD0; cross-fade needs GPU Resident Drawer; skinned meshes still deform
  LOD0; simplifier ignores skin weights and blend shapes; triangles only; do
  not mix with LOD Group; `RenderMeshInstanced` / `RenderMeshPrimitives`
  need an explicit `forceMeshLod`.
- On Quest: no saving on skinning cost, and static-batched environments get
  no LOD selection (U1-060 notes). Draw-call and batching trade-offs:
  `unity-perf:unity-draw-calls-batching`.
