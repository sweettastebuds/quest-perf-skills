// UNTESTED: written without a Unity editor; verify in your project.
//
// QuestPerfAudit.cs - settings audit for Unity URP projects shipping on Meta Quest 2 / 3 / 3S.
// Owner skill: unity-perf:unity-urp-settings. Each check names the skill whose
// recommendation it enforces and the dossier finding ID it rests on; see
// references/audit-checks.md next to this skill for the full list.
//
// Install: copy into any Editor folder (for example Assets/Editor/). If editor code lives in
// assembly definitions, reference Unity.RenderPipelines.Universal.Runtime and
// Unity.RenderPipelines.Core.Runtime from that asmdef.
// Run:     Tools > Quest Perf > Audit Project
// CI:      Unity -batchmode -quit -projectPath <path> -executeMethod QuestPerfTools.QuestPerfAudit.RunBatch
// Output:  Console + Logs/QuestPerfAudit.txt. RunBatch exits with code 1 when any FAIL is found.
//
// Target: Unity 2021.3 LTS (URP 12) through Unity 6.x (URP 17). Public API is used where it
// exists in all of these versions; everything else goes through SerializedObject or
// reflection with null checks, so a missing field reports "not found" instead of breaking
// compilation. The audit reads asset values, not runtime-effective values: Build Profile
// overrides (6.1+) and Quest capability flags are not applied.

#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace QuestPerfTools
{
    public static class QuestPerfAudit
    {
        enum Sev { PASS, INFO, WARN, FAIL }

        struct Finding
        {
            public Sev sev;
            public string id;
            public string owner;
            public string msg;
        }

        const string kUrp = "unity-perf:unity-urp-settings";
        const string kCpu = "unity-perf:unity-cpu-scripting";
        const string kGles = "gles3-perf:gles-vs-vulkan";
        const string kVer = "unity-perf:unity-version-matrix";
        const string kUpg = "unity-perf:unity-upgrade-risks";
        const string kLight = "unity-perf:unity-lighting";
        const string kBatch = "unity-perf:unity-draw-calls-batching";
        const string kRg = "unity-perf:unity-render-graph-tiling";
        const string kRes = "quest-perf:quest-resolution-foveation";
        const string kPace = "quest-perf:quest-frame-pacing";
        const string kAppSw = "quest-perf:quest-appsw";
        const string kMem = "unity-perf:unity-memory-assets";

        static readonly List<Finding> s_Findings = new List<Finding>();
        static bool s_GlesInApiList;
        static bool s_VulkanFirst;
        static bool s_SpaceWarpOn;
        static bool s_ObdOn;
        static bool s_ObdFound;

        static void Add(Sev sev, string id, string owner, string msg)
        {
            s_Findings.Add(new Finding { sev = sev, id = id, owner = owner, msg = msg });
        }

        [MenuItem("Tools/Quest Perf/Audit Project")]
        public static void Run()
        {
            RunInternal();
        }

        // Batch-mode entry point; exits the editor with 1 when any FAIL is present.
        public static void RunBatch()
        {
            int fails = RunInternal();
            EditorApplication.Exit(fails > 0 ? 1 : 0);
        }

        static int RunInternal()
        {
            s_Findings.Clear();
            s_GlesInApiList = false;
            s_VulkanFirst = false;
            s_SpaceWarpOn = false;
            s_ObdOn = false;
            s_ObdFound = false;

            Safe("Editor version", CheckEditorVersion);
            Safe("Player settings", CheckPlayerSettings);
            Safe("URP assets", CheckUrpAssets);
            Safe("Render Graph", CheckRenderGraphMode);
            Safe("Cameras", CheckSceneCameras);
            Safe("XR management", CheckXrLoaders);
            Safe("OpenXR", CheckOpenXr);
            Safe("Oculus XR", CheckOculusXr);
            Safe("AppSW cross-check", CheckAppSwCrossRules);
            Safe("Refresh rate", CheckRefreshRateRequest);

            return WriteReport();
        }

        static void Safe(string section, Action a)
        {
            try { a(); }
            catch (Exception e)
            {
                Add(Sev.INFO, "ERR", kUrp, section + " check threw " + e.GetType().Name + ": " + e.Message + " (check skipped)");
            }
        }

        // ------------------------------------------------------------------ editor version

        struct UVer { public int major, minor, patch, build; public char kind; public bool ok; }

        static UVer ParseVersion(string s)
        {
            // Formats: 2022.3.35f1, 6000.0.66f2, 6000.7.0b2
            var v = new UVer();
            try
            {
                string[] parts = s.Split('.');
                v.major = int.Parse(parts[0]);
                v.minor = int.Parse(parts[1]);
                string rest = parts[2];
                int i = 0;
                while (i < rest.Length && char.IsDigit(rest[i])) i++;
                v.patch = int.Parse(rest.Substring(0, i));
                v.kind = i < rest.Length ? rest[i] : 'f';
                int j = i + 1;
                int k = j;
                while (k < rest.Length && char.IsDigit(rest[k])) k++;
                v.build = k > j ? int.Parse(rest.Substring(j, k - j)) : 0;
                v.ok = true;
            }
            catch { v.ok = false; }
            return v;
        }

        static bool Below(UVer v, int major, int minor, int patch, int build)
        {
            if (v.major != major) return v.major < major;
            if (v.minor != minor) return v.minor < minor;
            if (v.patch != patch) return v.patch < patch;
            return v.build < build;
        }

        static UVer s_Ver;

        static void CheckEditorVersion()
        {
            s_Ver = ParseVersion(Application.unityVersion);
            Add(Sev.INFO, "V00", kVer, "Editor " + Application.unityVersion);
            if (!s_Ver.ok) return;

            if (s_Ver.major == 6000 && s_Ver.minor == 0 && Below(s_Ver, 6000, 0, 66, 2))
                Add(Sev.WARN, "V01", kVer, "Unity 6.0 below 6000.0.66f2 is off Meta's supported path; Meta recommends 6.1+ (U1-008).");

            if (s_Ver.major == 2022 && s_Ver.minor == 3 && Below(s_Ver, 2022, 3, 35, 1) && PlayerSettings.graphicsJobs)
                Add(Sev.INFO, "V02", kCpu, "Graphics Jobs Legacy mode (Meta's recommendation) needs 2022.3.35f1+ (A1-058).");
        }

        // ------------------------------------------------------------------ player settings

        static object InvokePlayerSettings(string method)
        {
            Type t = typeof(PlayerSettings);
            MethodInfo m = t.GetMethod(method, BindingFlags.Public | BindingFlags.Static, null, new[] { typeof(NamedBuildTarget) }, null);
            if (m != null) return m.Invoke(null, new object[] { NamedBuildTarget.Android });
            m = t.GetMethod(method, BindingFlags.Public | BindingFlags.Static, null, new[] { typeof(BuildTargetGroup) }, null);
            if (m != null) return m.Invoke(null, new object[] { BuildTargetGroup.Android });
            return null;
        }

        static object GetStatic(Type t, string name)
        {
            if (t == null) return null;
            PropertyInfo p = t.GetProperty(name, BindingFlags.Public | BindingFlags.Static);
            if (p != null) return p.GetValue(null, null);
            FieldInfo f = t.GetField(name, BindingFlags.Public | BindingFlags.Static);
            return f != null ? f.GetValue(null) : null;
        }

        static void CheckPlayerSettings()
        {
            // P01 graphics API order
            bool autoApi = PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.Android);
            GraphicsDeviceType[] apis = PlayerSettings.GetGraphicsAPIs(BuildTarget.Android);
            var sb = new StringBuilder();
            foreach (GraphicsDeviceType api in apis)
            {
                if (sb.Length > 0) sb.Append(", ");
                sb.Append(api);
                if (api == GraphicsDeviceType.OpenGLES3) s_GlesInApiList = true;
            }
            s_VulkanFirst = apis.Length > 0 && apis[0] == GraphicsDeviceType.Vulkan;
            if (autoApi)
                Add(Sev.WARN, "P01", kGles, "Android Graphics APIs = Auto. Set an explicit list with Vulkan first (U2-094, U2-091).");
            else if (s_VulkanFirst)
                Add(Sev.PASS, "P01", kGles, "Android Graphics APIs: " + sb + " (Vulkan first; U2-094).");
            else
                Add(Sev.WARN, "P01", kGles, "Android Graphics APIs: " + sb + ". Meta calls Vulkan required; AppSW and GRD are Vulkan-only; FFR on GLES is disputed (see quest-perf:quest-resolution-foveation). Decide with the GLES-vs-Vulkan protocol (U2-094, G1-031, Q3-039).");

            // P03 scripting backend
            object backend = InvokePlayerSettings("GetScriptingBackend");
            if (backend != null)
            {
                bool il2cpp = backend.ToString().IndexOf("IL2CPP", StringComparison.OrdinalIgnoreCase) >= 0;
                Add(il2cpp ? Sev.PASS : Sev.FAIL, "P03", kCpu, "Scripting backend = " + backend + (il2cpp ? "" : ". Quest needs IL2CPP (ARM64 requires IL2CPP; U5-021)."));
            }

            // P04 architectures
            AndroidArchitecture arch = PlayerSettings.Android.targetArchitectures;
            bool arm64 = (arch & AndroidArchitecture.ARM64) != 0;
            bool armv7 = (arch & AndroidArchitecture.ARMv7) != 0;
            if (!arm64) Add(Sev.FAIL, "P04", kCpu, "Target architectures = " + arch + ". Ship ARM64 only (U5-021).");
            else if (armv7) Add(Sev.WARN, "P04", kCpu, "Target architectures include ARMv7. Ship ARM64 only (U5-021).");
            else Add(Sev.PASS, "P04", kCpu, "Target architectures = " + arch + ".");

            // P05 IL2CPP code generation
            object codeGen = InvokePlayerSettings("GetIl2CppCodeGeneration");
            if (codeGen == null) codeGen = GetStatic(typeof(EditorUserBuildSettings), "il2CppCodeGeneration");
            if (codeGen != null)
            {
                bool size = codeGen.ToString().IndexOf("Size", StringComparison.OrdinalIgnoreCase) >= 0;
                Add(size ? Sev.WARN : Sev.PASS, "P05", kCpu, "IL2CPP Code Generation = " + codeGen + (size ? ". Use the runtime-speed option for release builds (U5-016)." : "."));
            }

            // P06 IL2CPP compiler configuration (report only)
            object cfg = InvokePlayerSettings("GetIl2CppCompilerConfiguration");
            if (cfg != null) Add(Sev.INFO, "P06", kCpu, "IL2CPP C++ Compiler Configuration = " + cfg + " (no Quest-specific guidance in the dossiers).");

            // P07 texture compression
            object sub = GetStatic(typeof(EditorUserBuildSettings), "androidBuildSubtarget");
            if (sub != null)
            {
                string s = sub.ToString();
                if (s.IndexOf("ASTC", StringComparison.OrdinalIgnoreCase) >= 0)
                    Add(Sev.PASS, "P07", kMem, "Android texture compression override = " + s + " (U4-046, U4-053).");
                else if (s.IndexOf("Generic", StringComparison.OrdinalIgnoreCase) >= 0)
                    Add(Sev.INFO, "P07", kMem, "Android texture compression override = " + s + " (uses Player setting; ASTC is Unity's Android default, U4-046).");
                else
                    Add(Sev.WARN, "P07", kMem, "Android texture compression override = " + s + ". Meta says ASTC on both Quest 2 and Quest 3 (U4-053).");
            }

            // P08 color space (report only)
            ColorSpace cs = PlayerSettings.colorSpace;
            string csNote = "Color space = " + cs + ".";
            if (cs == ColorSpace.Linear && s_GlesInApiList)
                csNote += " GLES + Linear: blending costs more (U3-063) and from 6000.6.0b6 Tile-Only / on-tile post falls back on a non-sRGB backbuffer (U1-063).";
            Add(Sev.INFO, "P08", kUrp, csNote);

            // P09 multithreaded rendering
            object mt = InvokePlayerSettings("GetMobileMTRendering");
            if (mt is bool)
                Add((bool)mt ? Sev.PASS : Sev.FAIL, "P09", kCpu, "Multithreaded Rendering = " + mt + ((bool)mt ? "." : ". Never ship a Quest build with it off (A1-061)."));

            // P10 graphics jobs
            string gj = "Graphics Jobs = " + PlayerSettings.graphicsJobs;
            object mode = GetStatic(typeof(PlayerSettings), "graphicsJobMode");
            if (mode != null) gj += ", mode = " + mode;
            gj += ". Meta recommends Legacy mode for main-thread-bound apps (2022.3.35f1+ / 6.x; A1-058); unvalidated on 2021.3 (A1-062); Split vs Legacy unmeasured on Quest (A1-059).";
            Add(Sev.INFO, "P10", kCpu, gj);

            // P11 incremental GC
            bool inc = PlayerSettings.gcIncremental;
            Add(inc ? Sev.PASS : Sev.INFO, "P11", kCpu, "Incremental GC = " + inc + (inc ? " (U5-005)." : ". Off only if allocations are near zero and an A/B shows the CPU gain (U5-006)."));

            // P12 Vulkan swapchain buffers
            object bufs = GetStatic(typeof(PlayerSettings), "vulkanNumSwapchainBuffers");
            if (bufs != null)
            {
                int n = Convert.ToInt32(bufs);
                Add(n == 3 ? Sev.PASS : Sev.WARN, "P12", kUrp, "Vulkan swapchain buffers = " + n + (n == 3 ? "." : ". Leave the default (3); the setting only takes effect from 6000.0.83f1 / 6000.3.24f1 / 6000.6.0f1 (U5-025, U1-068, X-C5)."));
            }

            // P13 Vulkan late acquire
            object late = GetStatic(typeof(PlayerSettings), "vulkanEnableLateAcquireNextImage");
            if (late is bool)
                Add((bool)late ? Sev.WARN : Sev.PASS, "P13", kUrp, "Vulkan 'Get swapchain image late as possible' = " + late + ((bool)late ? ". It adds a blit through a staging image; leave it off (U5-025)." : "."));
        }

        // ------------------------------------------------------------------ URP assets

        static string EnumName(SerializedProperty p)
        {
            if (p == null) return null;
            if (p.propertyType == SerializedPropertyType.Enum)
            {
                int i = p.enumValueIndex;
                string[] names = p.enumNames;
                if (i >= 0 && i < names.Length) return names[i];
                return p.intValue.ToString();
            }
            if (p.propertyType == SerializedPropertyType.Integer) return p.intValue.ToString();
            return null;
        }

        static SerializedProperty FindContaining(SerializedObject so, string needle)
        {
            SerializedProperty it = so.GetIterator();
            bool enter = true;
            while (it.Next(enter))
            {
                enter = it.propertyType == SerializedPropertyType.Generic;
                if (it.name.IndexOf(needle, StringComparison.OrdinalIgnoreCase) >= 0)
                    return it.Copy();
            }
            return null;
        }

        static List<SerializedProperty> FindAllContaining(SerializedObject so, string needle)
        {
            var list = new List<SerializedProperty>();
            SerializedProperty it = so.GetIterator();
            bool enter = true;
            while (it.Next(enter))
            {
                enter = it.propertyType == SerializedPropertyType.Generic;
                if (it.name.IndexOf(needle, StringComparison.OrdinalIgnoreCase) >= 0)
                    list.Add(it.Copy());
            }
            return list;
        }

        static string PropValue(SerializedProperty p)
        {
            switch (p.propertyType)
            {
                case SerializedPropertyType.Boolean: return p.boolValue.ToString();
                case SerializedPropertyType.Enum: return EnumName(p);
                case SerializedPropertyType.Integer: return p.intValue.ToString();
                case SerializedPropertyType.Float: return p.floatValue.ToString("0.###");
                case SerializedPropertyType.String: return p.stringValue;
                case SerializedPropertyType.ObjectReference: return p.objectReferenceValue != null ? p.objectReferenceValue.name : "None";
                default: return "(" + p.propertyType + ")";
            }
        }

        static void CheckUrpAssets()
        {
            var assets = new List<KeyValuePair<UniversalRenderPipelineAsset, string>>();
            var seen = new HashSet<UniversalRenderPipelineAsset>();

            var def = GraphicsSettings.defaultRenderPipeline as UniversalRenderPipelineAsset;
            if (def != null && seen.Add(def)) assets.Add(new KeyValuePair<UniversalRenderPipelineAsset, string>(def, "Graphics default"));

            string[] q = QualitySettings.names;
            for (int i = 0; i < q.Length; i++)
            {
                var a = QualitySettings.GetRenderPipelineAssetAt(i) as UniversalRenderPipelineAsset;
                if (a != null && seen.Add(a)) assets.Add(new KeyValuePair<UniversalRenderPipelineAsset, string>(a, "Quality level '" + q[i] + "'"));
            }

            if (assets.Count == 0)
            {
                Add(Sev.FAIL, "U00", kUrp, "No UniversalRenderPipelineAsset assigned in Graphics or any Quality level.");
                return;
            }

            foreach (var kv in assets) CheckOneAsset(kv.Key, kv.Value);
        }

        static void CheckOneAsset(UniversalRenderPipelineAsset a, string where)
        {
            string tag = "[" + a.name + " / " + where + "] ";
            var so = new SerializedObject(a);

            // U01 HDR
            string prec = EnumName(so.FindProperty("m_HDRColorBufferPrecision"));
            if (a.supportsHDR)
            {
                bool is64 = prec != null && prec.IndexOf("64", StringComparison.Ordinal) >= 0;
                Add(is64 ? Sev.FAIL : Sev.WARN, "U01", kUrp, tag + "HDR on" + (prec != null ? " (precision " + prec + ")" : "") +
                    ". HDR forces an intermediate + final blit; turn it off (U2-002, U2-030)." + (is64 ? " 64-bit HDR also adds bins (A2-014)." : ""));
            }
            else Add(Sev.PASS, "U01", kUrp, tag + "HDR off.");

            // U02 depth texture
            Add(a.supportsCameraDepthTexture ? Sev.WARN : Sev.PASS, "U02", kUrp, tag + "Depth Texture = " + a.supportsCameraDepthTexture +
                (a.supportsCameraDepthTexture ? ". Adds Copy Depth and splits the native pass; off unless required, else After Transparents (U2-003, U2-021)." : "."));

            // U03 opaque texture
            int msaa = a.msaaSampleCount;
            if (a.supportsCameraOpaqueTexture)
                Add(Sev.WARN, "U03", kUrp, tag + "Opaque Texture on. Copy Color forces colour off-tile (U2-004)." +
                    (msaa > 1 ? " With MSAA on, Unity ignores MSAA where StoreAndResolve is unsupported (G2-017)." : ""));
            else Add(Sev.PASS, "U03", kUrp, tag + "Opaque Texture off.");

            // U04 MSAA
            if (msaa <= 1) Add(Sev.INFO, "U04", kUrp, tag + "MSAA off. Consider 2x: Qualcomm calls it 'likely to be practically free' (A2-017); measure (U2-C1).");
            else if (msaa == 2) Add(Sev.PASS, "U04", kUrp, tag + "MSAA 2x (starting point; U2-006, A2-017).");
            else if (msaa == 4) Add(Sev.WARN, "U04", kUrp, tag + "MSAA 4x. Measured about +7 ms on Quest 2 and +3.3 ms GLES / +5.0 ms Vulkan on Quest 3/3S in one scene (G2-040, G2-039). Keep 4x for Quest 3/3S only, after an A/B.");
            else Add(Sev.FAIL, "U04", kUrp, tag + "MSAA " + msaa + "x. Meta: do not exceed 4x (U2-093).");

            // U05 upscaling filter
            string up = EnumName(so.FindProperty("m_UpscalingFilter"));
            if (up != null)
            {
                bool bad = up.IndexOf("FSR", StringComparison.OrdinalIgnoreCase) >= 0 || up.IndexOf("STP", StringComparison.OrdinalIgnoreCase) >= 0;
                Add(bad ? Sev.WARN : Sev.PASS, "U05", kUrp, tag + "Upscaling Filter = " + up + (bad ? ". FSR stays active at scale 1.0 and STP forces TAA; use Auto (U2-008)." : "."));
            }

            // U06 render scale
            Add(Sev.INFO, "U06", kRes, tag + "Render Scale = " + a.renderScale.ToString("0.00") + " (values within 0.05 of 1.0 snap to 1.0; do not change per frame; U2-007, U2-047).");

            // U07 store actions
            string store = EnumName(so.FindProperty("m_StoreActionsOptimization"));
            if (store != null)
            {
                string rgNote = s_Ver.ok && s_Ver.major >= 6000 ? " Ignored under Render Graph; applies only in Compatibility Mode (U2-C4)." : "";
                Sev sv = store.IndexOf("Store", StringComparison.OrdinalIgnoreCase) >= 0 && store.IndexOf("Auto", StringComparison.OrdinalIgnoreCase) < 0 ? Sev.FAIL
                    : store.IndexOf("Discard", StringComparison.OrdinalIgnoreCase) >= 0 ? Sev.PASS : Sev.INFO;
                if (rgNote.Length > 0 && sv == Sev.FAIL) sv = Sev.WARN;
                Add(sv, "U07", kUrp, tag + "Store Actions = " + store + ". Store 'significantly increases the memory bandwidth'; Discard after verifying no injected pass reads the target (U2-005)." + rgNote);
            }

            // U08 terrain holes
            SerializedProperty holes = so.FindProperty("m_SupportsTerrainHoles");
            if (holes != null)
                Add(holes.boolValue ? Sev.WARN : Sev.PASS, "U08", kUrp, tag + "Terrain Holes = " + holes.boolValue + (holes.boolValue ? ". Off unless holes are used (U2-011)." : "."));

            // U09 LOD cross fade (URP 14+)
            SerializedProperty lod = so.FindProperty("m_EnableLODCrossFade");
            if (lod != null && lod.boolValue)
            {
                string dt = EnumName(so.FindProperty("m_LODCrossFadeDitheringType"));
                bool stencil = dt != null && dt.IndexOf("Stencil", StringComparison.OrdinalIgnoreCase) >= 0;
                Add(stencil ? Sev.INFO : Sev.WARN, "U09", kUrp, tag + "LOD Cross Fade on (" + (dt ?? "type unknown") + "). Off, or 2x2 Stencil dithering to avoid alpha test (U2-010).");
            }

            // U10 soft shadows
            SerializedProperty soft = so.FindProperty("m_SoftShadowsSupported");
            if (soft != null && soft.boolValue)
                Add(Sev.WARN, "U10", kLight, tag + "Soft Shadows on. High impact on tile GPUs; off or Low quality (U2-009).");

            // U11 volume update mode
            string vol = EnumName(so.FindProperty("m_VolumeFrameworkUpdateMode"));
            if (vol != null)
                Add(vol.IndexOf("Every", StringComparison.OrdinalIgnoreCase) >= 0 ? Sev.INFO : Sev.PASS, "U11", kUrp, tag + "Volume Update Mode = " + vol + ". Via Scripting removes the per-frame volume stack update (U2-015).");

            // U12 SRP batcher
            SerializedProperty srp = so.FindProperty("m_UseSRPBatcher");
            if (srp != null)
                Add(srp.boolValue ? Sev.PASS : Sev.WARN, "U12", kBatch, tag + "SRP Batcher = " + srp.boolValue + (srp.boolValue ? "." : ". Keep it on (U2-016)."));

            // U13 additional lights (report only)
            string addMode = EnumName(so.FindProperty("m_AdditionalLightsRenderingMode"));
            SerializedProperty perObj = so.FindProperty("m_AdditionalLightsPerObjectLimit");
            if (addMode != null)
                Add(Sev.INFO, "U13", kLight, tag + "Additional Lights = " + addMode + (perObj != null ? ", per-object limit " + perObj.intValue : "") + " (ignored in Forward+; U2-012).");

            // U14 GPU Resident Drawer / GPU occlusion culling
            bool grdOn = false;
            bool occOn = false;
            foreach (SerializedProperty p in FindAllContaining(so, "GPUResidentDrawer"))
            {
                string val = PropValue(p);
                if (p.name.IndexOf("Occlusion", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    if (p.propertyType == SerializedPropertyType.Boolean && p.boolValue) occOn = true;
                }
                else if (p.propertyType == SerializedPropertyType.Enum && val != null && val.IndexOf("Disabled", StringComparison.OrdinalIgnoreCase) < 0)
                {
                    grdOn = true;
                }
            }
            if (grdOn)
            {
                if (s_GlesInApiList)
                    Add(Sev.WARN, "U14", kBatch, tag + "GPU Resident Drawer on with OpenGLES3 in the API list. GRD needs a compute API other than GLES and silently falls back on GLES (U3-032).");
                else
                    Add(Sev.INFO, "U14", kBatch, tag + "GPU Resident Drawer on (needs Forward+ and Vulkan on Quest; U3-032, X-C9).");
                if (occOn && s_Ver.ok && s_Ver.major == 6000 && s_Ver.minor == 5 && Below(s_Ver, 6000, 5, 8, 1))
                    Add(Sev.WARN, "U15", kUpg, tag + "GPU occlusion culling on 6.5.0-6.5.7 costs GPU time without culling (UUM-146214, fixed 6000.5.8f1; U1-020).");
            }

            // Renderer data
            SerializedProperty list = so.FindProperty("m_RendererDataList");
            if (list == null || !list.isArray)
            {
                Add(Sev.INFO, "R00", kUrp, tag + "m_RendererDataList not found; renderer checks skipped.");
                return;
            }
            for (int i = 0; i < list.arraySize; i++)
            {
                var rd = list.GetArrayElementAtIndex(i).objectReferenceValue as ScriptableRendererData;
                if (rd != null) CheckRenderer(rd, tag, msaa, a.supportsCameraDepthTexture);
            }
        }

        static void CheckRenderer(ScriptableRendererData rd, string assetTag, int msaa, bool depthTex)
        {
            string tag = assetTag + "{" + rd.name + "} ";
            var so = new SerializedObject(rd);
            bool isUniversal = rd is UniversalRendererData;
            if (!isUniversal)
            {
                Add(Sev.INFO, "R00", kUrp, tag + "Renderer type " + rd.GetType().Name + " is not a Universal Renderer; renderer checks skipped.");
            }
            else
            {
                // R01 rendering path
                string path = EnumName(so.FindProperty("m_RenderingMode"));
                if (path != null)
                {
                    if (path.IndexOf("Deferred", StringComparison.OrdinalIgnoreCase) >= 0)
                        Add(Sev.FAIL, "R01", kUrp, tag + "Rendering Path = " + path + ". Use Forward or Forward+: G-buffer GMEM loads, no MSAA, Tile-Only incompatible (U2-019, U1-034).");
                    else
                    {
                        string note = "";
                        if (path.IndexOf("Plus", StringComparison.OrdinalIgnoreCase) >= 0 && s_GlesInApiList)
                            note = " GLES: visible additional lights are 16 with 'Use OpenGL ES 3.0 shaders' on (6.6), 32 otherwise (X-C6, U1-094).";
                        Add(Sev.PASS, "R01", kUrp, tag + "Rendering Path = " + path + " (Forward+ wins from about 5 real-time lights; U2-027)." + note);
                    }
                }

                // R02 depth priming
                string prime = EnumName(so.FindProperty("m_DepthPrimingMode"));
                if (prime != null)
                    Add(prime.IndexOf("Disabled", StringComparison.OrdinalIgnoreCase) >= 0 ? Sev.PASS : Sev.WARN, "R02", kUrp, tag + "Depth Priming = " + prime +
                        (prime.IndexOf("Disabled", StringComparison.OrdinalIgnoreCase) >= 0 ? "." : ". Disable: unsupported on Android/TBDR and with MSAA; doubles a prepass for two views (U2-020, U3-058)."));

                // R03 copy depth mode
                string copy = EnumName(so.FindProperty("m_CopyDepthMode"));
                if (copy != null && depthTex && copy.IndexOf("Transparent", StringComparison.OrdinalIgnoreCase) < 0)
                    Add(Sev.WARN, "R03", kUrp, tag + "Depth Texture Mode = " + copy + " with Depth Texture on. After Transparents avoids the colour store/reload (URP 14+; U2-021, G2-019).");

                // R04 intermediate texture
                string inter = EnumName(so.FindProperty("m_IntermediateTextureMode"));
                if (inter != null)
                {
                    bool always = inter.IndexOf("Always", StringComparison.OrdinalIgnoreCase) >= 0;
                    Add(always ? Sev.WARN : Sev.PASS, "R04", kUrp, tag + "Intermediate Texture = " + inter + (always ? ". Set Auto; Always forces an intermediate (U2-023)." : "."));
                }

                // R05 native render pass (URP 12/14, 6.0-6.3 Compatibility Mode)
                SerializedProperty nrp = so.FindProperty("m_UseNativeRenderPass");
                if (nrp != null)
                    Add(Sev.INFO, "R05", kRg, tag + "Native RenderPass = " + nrp.boolValue + ". On with Vulkan in URP 12/14 or Compatibility Mode; no effect on GLES; superseded by Render Graph (U2-081, G2-022, U2-C4).");

                // R07 Tile-Only Mode (6.5+)
                SerializedProperty tile = FindContaining(so, "TileOnly");
                if (tile != null)
                {
                    bool on = tile.propertyType == SerializedPropertyType.Boolean && tile.boolValue;
                    Add(Sev.INFO, "R07", kUrp, tag + "Tile-Only Mode (" + tile.name + ") = " + PropValue(tile) + ". Use as a dev-branch guard (U2-025).");
                    if (on && msaa > 1)
                        Add(Sev.WARN, "R08", kUrp, tag + "Tile-Only Mode with MSAA " + msaa + "x: Unity docs say MSAA breaks on-tile; staff report otherwise on device (conflict U2-C2). Confirm in the on-device Render Graph Viewer.");
                }
            }

            // R06 renderer features
            List<ScriptableRendererFeature> feats = rd.rendererFeatures;
            if (feats == null) return;
            foreach (ScriptableRendererFeature f in feats)
            {
                if (f == null) continue;
                string tn = f.GetType().Name;
                string ft = tag + "feature '" + f.name + "' (" + tn + ", active=" + f.isActive + ") ";
                if (!f.isActive) continue;
                if (tn.IndexOf("AmbientOcclusion", StringComparison.OrdinalIgnoreCase) >= 0)
                    Add(Sev.WARN, "R06", kUrp, ft + "SSAO: several passes with high tile cost; disable on Quest (U2-028).");
                else if (tn.IndexOf("Decal", StringComparison.OrdinalIgnoreCase) >= 0)
                    Add(Sev.WARN, "R06", kUrp, ft + "Decal feature requires an intermediate texture (U2-029).");
                else if (tn.IndexOf("FullScreenPass", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    SerializedProperty fetch = new SerializedObject(f).FindProperty("fetchColorBuffer");
                    if (fetch != null && fetch.boolValue)
                        Add(Sev.WARN, "R06", kUrp, ft + "fetchColorBuffer = true forces an intermediate and a colour copy; untick if the effect does not read scene colour (U2-026).");
                    else
                        Add(Sev.INFO, "R06", kRg, ft + "full-screen pass; check merging in the Render Graph Viewer.");
                }
                else
                    Add(Sev.INFO, "R06", kRg, ft + "custom/other feature; check it does not force an intermediate or break merging.");
            }
        }

        // ------------------------------------------------------------------ Render Graph mode

        static void CheckRenderGraphMode()
        {
#if UNITY_6000_0_OR_NEWER && !UNITY_6000_4_OR_NEWER
            Type t = FindType("UnityEngine.Rendering.Universal.RenderGraphSettings");
            if (t == null) return;
            MethodInfo g = null;
            foreach (MethodInfo m in typeof(GraphicsSettings).GetMethods(BindingFlags.Public | BindingFlags.Static))
                if (m.Name == "GetRenderPipelineSettings" && m.IsGenericMethodDefinition && m.GetParameters().Length == 0) { g = m; break; }
            if (g == null) return;
            object settings = g.MakeGenericMethod(t).Invoke(null, null);
            if (settings == null) return;
            PropertyInfo p = t.GetProperty("enableRenderCompatibilityMode", BindingFlags.Public | BindingFlags.Instance);
            if (p == null) return;
            bool compat = (bool)p.GetValue(settings, null);
            Add(compat ? Sev.WARN : Sev.PASS, "G01", kRg, "Render Graph Compatibility Mode = " + compat +
                (compat ? ". Removed in 6.4: custom passes must be ported; Store Actions/Native RenderPass apply only in this mode (U1-025, U1-026, U2-C4)." : "."));
#endif
        }

        // ------------------------------------------------------------------ cameras in open scenes

        static void CheckSceneCameras()
        {
            int count = 0;
            foreach (Camera c in Resources.FindObjectsOfTypeAll<Camera>())
            {
                if (c == null || EditorUtility.IsPersistent(c) || !c.gameObject.scene.IsValid()) continue;
                if ((c.hideFlags & HideFlags.HideInHierarchy) != 0) continue;
                count++;
                var data = c.GetComponent<UniversalAdditionalCameraData>();
                if (data == null) continue;
                string tag = "[camera '" + c.name + "' in " + c.gameObject.scene.name + "] ";
                if (data.requiresDepthOption == CameraOverrideOption.On)
                    Add(Sev.WARN, "C01", kUrp, tag + "Depth Texture override = On; re-enables Copy Depth regardless of the asset (U2-003).");
                if (data.requiresColorOption == CameraOverrideOption.On)
                    Add(Sev.WARN, "C02", kUrp, tag + "Opaque Texture override = On; forces Copy Color (U2-004).");
                if (data.renderPostProcessing)
                    Add(Sev.INFO, "C03", kRg, tag + "Post Processing on: intermediate + final blit unless on-tile post (6.3+) is set up (U2-030, U2-091).");
                if (c.rect.x != 0f || c.rect.y != 0f || c.rect.width != 1f || c.rect.height != 1f)
                    Add(Sev.WARN, "C04", kUrp, tag + "Non-default viewport rect forces an intermediate (U2-030).");
            }
            Add(Sev.INFO, "C00", kUrp, count + " camera(s) in open scenes checked. Open each shipping scene and re-run to cover all cameras.");
        }

        // ------------------------------------------------------------------ XR

        static Type FindType(string fullName)
        {
            foreach (Assembly asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type t = null;
                try { t = asm.GetType(fullName, false); } catch { }
                if (t != null) return t;
            }
            return null;
        }

        static object GetInstance(object o, string name)
        {
            if (o == null) return null;
            Type t = o.GetType();
            PropertyInfo p = t.GetProperty(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (p != null) return p.GetValue(o, null);
            FieldInfo f = t.GetField(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            return f != null ? f.GetValue(o) : null;
        }

        static void CheckXrLoaders()
        {
            Type per = FindType("UnityEditor.XR.Management.XRGeneralSettingsPerBuildTarget");
            if (per == null)
            {
                Add(Sev.WARN, "X01", kUpg, "XR Plug-in Management not installed; no XR loader can be checked.");
                return;
            }
            MethodInfo m = per.GetMethod("XRGeneralSettingsForBuildTarget", BindingFlags.Public | BindingFlags.Static);
            object general = m != null ? m.Invoke(null, new object[] { BuildTargetGroup.Android }) : null;
            object manager = GetInstance(general, "Manager") ?? GetInstance(general, "AssignedSettings");
            var loaders = GetInstance(manager, "activeLoaders") as IEnumerable;
            if (loaders == null) loaders = GetInstance(manager, "loaders") as IEnumerable;
            var names = new List<string>();
            if (loaders != null)
                foreach (object l in loaders)
                    if (l != null) names.Add(l.GetType().Name);

            if (names.Count == 0)
            {
                Add(Sev.WARN, "X01", kUrp, "No active XR loader for Android.");
                return;
            }
            string joined = string.Join(", ", names.ToArray());
            bool oculus = joined.IndexOf("Oculus", StringComparison.OrdinalIgnoreCase) >= 0;
            if (oculus && s_Ver.ok && s_Ver.major == 6000 && s_Ver.minor >= 5)
                Add(Sev.FAIL, "X01", kUpg, "Android XR loaders: " + joined + ". Oculus XR is unsupported from Unity 6.5; use OpenXR (U1-091).");
            else if (oculus)
                Add(Sev.WARN, "X01", kUpg, "Android XR loaders: " + joined + ". Oculus XR is deprecated; on Unity 6.x use OpenXR (U1-091, U1-092).");
            else
                Add(Sev.PASS, "X01", kUrp, "Android XR loaders: " + joined + ".");
        }

        static void CheckOpenXr()
        {
            Type t = FindType("UnityEngine.XR.OpenXR.OpenXRSettings");
            if (t == null) return;
            MethodInfo get = t.GetMethod("GetSettingsForBuildTargetGroup", BindingFlags.Public | BindingFlags.Static);
            object settings = get != null ? get.Invoke(null, new object[] { BuildTargetGroup.Android }) : null;
            if (settings == null)
            {
                Add(Sev.INFO, "X02", kUrp, "OpenXR installed but Android settings not readable via reflection; check Project Settings > XR Plug-in Management > OpenXR by hand.");
                return;
            }

            object renderMode = GetInstance(settings, "renderMode");
            if (renderMode != null)
            {
                string rm = renderMode.ToString();
                bool multiPass = rm.IndexOf("MultiPass", StringComparison.OrdinalIgnoreCase) >= 0;
                Add(multiPass ? Sev.FAIL : Sev.PASS, "X02", kUrp, "OpenXR Render Mode = " + rm + (multiPass ? ". Use Single Pass Instanced (Multiview on Quest); multi-pass doubles CPU draw submission (U2-040; GPU delta disputed, G2-C10)." : "."));
            }

            object depth = GetInstance(settings, "depthSubmissionMode");
            if (depth != null)
                Add(Sev.INFO, "X03", kAppSw, "OpenXR Depth Submission Mode = " + depth + ". Meta: None unless SpaceWarp or composition needs depth (U1-092).");

            object lat = GetInstance(settings, "latencyOptimization");
            if (lat != null)
                Add(Sev.INFO, "X04", kPace, "OpenXR Latency Optimization = " + lat + ". Conflict: Meta recommends Prioritize Input Polling (Q2-076); Unity's 1.18 default is Prioritize Rendering (U5-092).");

            // Features: Meta Quest support (OBD, SpaceWarp, motion-vector format), foveation.
            MethodInfo gf = null;
            foreach (MethodInfo mi in settings.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance))
                if (mi.Name == "GetFeatures" && !mi.IsGenericMethodDefinition && mi.GetParameters().Length == 0) { gf = mi; break; }
            var feats = gf != null ? gf.Invoke(settings, null) as IEnumerable : null;
            if (feats == null) return;
            foreach (object f in feats)
            {
                var uo = f as UnityEngine.Object;
                if (uo == null) continue;
                object en = GetInstance(f, "enabled");
                bool enabled = en is bool && (bool)en;
                string tn = f.GetType().Name;
                var so = new SerializedObject(uo);

                foreach (SerializedProperty p in FindAllContaining(so, "BufferDiscard"))
                {
                    if (p.propertyType != SerializedPropertyType.Boolean) continue;
                    s_ObdFound = true;
                    if (enabled && p.boolValue) s_ObdOn = true;
                    Add(Sev.INFO, "X05", kAppSw, "OpenXR feature " + tn + " (enabled=" + enabled + "): " + p.name + " = " + p.boolValue + " (Q3-069).");
                }
                if (tn.IndexOf("SpaceWarp", StringComparison.OrdinalIgnoreCase) >= 0 && enabled) s_SpaceWarpOn = true;
                foreach (SerializedProperty p in FindAllContaining(so, "SpaceWarp"))
                {
                    if (p.propertyType == SerializedPropertyType.Boolean && p.boolValue && enabled) s_SpaceWarpOn = true;
                    Add(Sev.INFO, "X06", kAppSw, "OpenXR feature " + tn + ": " + p.name + " = " + PropValue(p) + " (RG16f halves motion-vector bandwidth vs RGBA16f; Q3-070, G1-033).");
                }
                if (tn.IndexOf("Foveat", StringComparison.OrdinalIgnoreCase) >= 0)
                    Add(Sev.INFO, "X07", kRes, "OpenXR feature " + tn + " enabled=" + enabled + " (SRP Foveation recommended on Unity 6+; U1-092).");
            }
        }

        static void CheckOculusXr()
        {
            Type t = FindType("Unity.XR.Oculus.OculusSettings");
            if (t == null) return;
            string[] guids = AssetDatabase.FindAssets("t:OculusSettings");
            foreach (string g in guids)
            {
                var o = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(AssetDatabase.GUIDToAssetPath(g));
                if (o == null) continue;
                var so = new SerializedObject(o);
                SerializedProperty stereo = FindContaining(so, "StereoRenderingModeAndroid");
                if (stereo != null)
                {
                    string v = PropValue(stereo);
                    bool mv = v != null && v.IndexOf("Multiview", StringComparison.OrdinalIgnoreCase) >= 0;
                    Add(mv ? Sev.PASS : Sev.FAIL, "X08", kUrp, "Oculus XR Android stereo mode = " + v + (mv ? "." : ". Use Multiview (U2-040)."));
                }
                foreach (SerializedProperty p in FindAllContaining(so, "BufferDiscard"))
                {
                    if (p.propertyType != SerializedPropertyType.Boolean) continue;
                    s_ObdFound = true;
                    if (p.boolValue) s_ObdOn = true;
                    Add(Sev.INFO, "X05", kAppSw, "Oculus XR " + p.name + " = " + p.boolValue + " (Q3-069, U1-076).");
                }
                SerializedProperty low = FindContaining(so, "LowOverheadMode");
                if (low != null)
                    Add(Sev.INFO, "X09", "gles3-perf:gles-driver-overhead", "Oculus XR " + low.name + " = " + PropValue(low) + " (GLES-only; Oculus XR plugin only).");
            }
        }

        static void CheckAppSwCrossRules()
        {
            if (s_SpaceWarpOn && s_ObdFound && !s_ObdOn)
                Add(Sev.FAIL, "X10", kAppSw, "Application SpaceWarp is on but Optimize Buffer Discards is off. Meta calls OBD very important for AppSW (Q3-069, G1-031).");
            if (s_SpaceWarpOn && !s_VulkanFirst)
                Add(Sev.FAIL, "X11", kAppSw, "Application SpaceWarp is on but Vulkan is not the first Android graphics API. AppSW is Vulkan-only (G1-031).");
        }

        // ------------------------------------------------------------------ refresh rate (heuristic)

        static void CheckRefreshRateRequest()
        {
            string[] needles = { "systemDisplayFrequency", "TryRequestDisplayRefreshRate" };
            string self = "QuestPerfAudit.cs";
            bool found = false;
            string where = null;
            foreach (string file in Directory.GetFiles("Assets", "*.cs", SearchOption.AllDirectories))
            {
                if (file.EndsWith(self, StringComparison.OrdinalIgnoreCase)) continue;
                string text;
                try { text = File.ReadAllText(file); } catch { continue; }
                foreach (string n in needles)
                    if (text.IndexOf(n, StringComparison.Ordinal) >= 0) { found = true; where = file + " (" + n + ")"; break; }
                if (found) break;
            }
            if (found)
                Add(Sev.PASS, "X12", kPace, "Refresh-rate request found in " + where + ". Choice and fallback: quest-perf:quest-frame-pacing (Q2-011, Q2-012).");
            else
                Add(Sev.WARN, "X12", kPace, "No refresh-rate request found in Assets/*.cs (heuristic). The app will run at the 72 Hz runtime default; request the rate explicitly (Q2-010, UNITY-GF1-C2).");
        }

        // ------------------------------------------------------------------ report

        static int WriteReport()
        {
            int pass = 0, info = 0, warn = 0, fail = 0;
            foreach (Finding f in s_Findings)
            {
                if (f.sev == Sev.PASS) pass++;
                else if (f.sev == Sev.INFO) info++;
                else if (f.sev == Sev.WARN) warn++;
                else fail++;
            }

            var sb = new StringBuilder();
            sb.AppendLine("Quest Perf Audit - " + DateTime.Now.ToString("yyyy-MM-dd HH:mm") + " - Unity " + Application.unityVersion);
            sb.AppendLine("UNTESTED script: verify findings against the project. Reads asset values, not runtime-effective values.");
            sb.AppendLine(string.Format("FAIL {0}  WARN {1}  INFO {2}  PASS {3}", fail, warn, info, pass));
            sb.AppendLine();
            foreach (Sev level in new[] { Sev.FAIL, Sev.WARN, Sev.INFO, Sev.PASS })
            {
                foreach (Finding f in s_Findings)
                {
                    if (f.sev != level) continue;
                    sb.Append(f.sev.ToString().PadRight(5)).Append(' ').Append(f.id.PadRight(4)).Append(' ')
                      .Append(f.msg).Append("  -> ").AppendLine(f.owner);
                }
            }
            string report = sb.ToString();

            try
            {
                string dir = Path.Combine(Directory.GetCurrentDirectory(), "Logs");
                Directory.CreateDirectory(dir);
                string path = Path.Combine(dir, "QuestPerfAudit.txt");
                File.WriteAllText(path, report.Replace("\r\n", "\n"));
                report += "\nWritten to " + path;
            }
            catch (Exception e)
            {
                report += "\nCould not write Logs/QuestPerfAudit.txt: " + e.Message;
            }

            if (fail > 0) Debug.LogError(report);
            else if (warn > 0) Debug.LogWarning(report);
            else Debug.Log(report);
            return fail;
        }
    }
}
#endif
