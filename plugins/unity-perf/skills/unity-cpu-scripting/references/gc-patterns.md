# Zero-allocation and job C# patterns for Quest

Read this when a Call Stacks capture shows `GC.Alloc` samples in gameplay, or
when writing per-frame code that must hold the 0 B per frame target (U5-004),
or when moving work into Burst jobs (pattern 11) or setting `fixedDeltaTime`
(pattern 12).
All snippets compile against Unity 2021.3 through 6.6 unless a `#if` says
otherwise; they are not device-measured. Sources accessed 2026-09-24; IDs refer
to research/unity.md.

Goal tags: every pattern here serves **Consistency** (fewer GC collections and
spikes); patterns 6-9 and 11 also serve **Throughput**.

## 1. Replace array-returning APIs (U5-010, U5-070)

| Allocates every call | Non-allocating substitute |
|---|---|
| `mesh.vertices` | `mesh.GetVertices(List<Vector3>)` with a reused list |
| `Animator.parameters` | `animator.parameterCount` + `animator.GetParameter(i)` |
| `renderer.sharedMaterials` | `renderer.GetSharedMaterials(List<Material>)` |
| `Physics.RaycastAll`, `OverlapSphere`, `SphereCastAll` | `*NonAlloc` with a preallocated buffer (U5-058) |
| `new T[0]` | `System.Array.Empty<T>()` or a cached static empty array |
| `Input.touches` | `Input.touchCount` + `Input.GetTouch(i)` |

```csharp
using System.Collections.Generic;
using UnityEngine;

public sealed class MeshReader : MonoBehaviour
{
    static readonly List<Vector3> s_Verts = new List<Vector3>(4096);
    static readonly List<Material> s_Mats = new List<Material>(8);

    void Sample(Mesh mesh, Renderer r)
    {
        mesh.GetVertices(s_Verts);        // fills, no new array
        r.GetSharedMaterials(s_Mats);     // fills, no new array
    }
}
```

## 2. Physics queries without allocation (U5-058, U5-042)

Excess hits beyond the buffer are silently dropped: size for the typical case.

```csharp
using UnityEngine;

public sealed class ProximitySensor : MonoBehaviour
{
    readonly Collider[] _hits = new Collider[16];
    [SerializeField] LayerMask mask;

    int Scan(float radius) =>
        Physics.OverlapSphereNonAlloc(transform.position, radius, _hits, mask,
                                      QueryTriggerInteraction.Ignore);
}
```

Batched raycasts on workers, completed next frame (schedule early, complete late):

```csharp
using Unity.Collections;
using Unity.Jobs;
using UnityEngine;

public sealed class BatchedRays : MonoBehaviour
{
    const int Count = 64;
    NativeArray<RaycastCommand> _cmds;
    NativeArray<RaycastHit> _results;
    JobHandle _handle;
    bool _pending;

    void OnEnable()
    {
        _cmds = new NativeArray<RaycastCommand>(Count, Allocator.Persistent);
        _results = new NativeArray<RaycastHit>(Count, Allocator.Persistent);
    }

    void Update()
    {
        if (_pending) { _handle.Complete(); Consume(); _pending = false; }

        Vector3 origin = transform.position;
        for (int i = 0; i < Count; i++)
        {
            Vector3 dir = Quaternion.Euler(0f, i * (360f / Count), 0f) * Vector3.forward;
#if UNITY_2022_2_OR_NEWER
            _cmds[i] = new RaycastCommand(origin, dir, QueryParameters.Default, 10f);
#else
            _cmds[i] = new RaycastCommand(origin, dir, 10f);
#endif
        }
        _handle = RaycastCommand.ScheduleBatch(_cmds, _results, 8);
        _pending = true;
    }

    void Consume()
    {
        for (int i = 0; i < Count; i++)
        {
            if (_results[i].colliderInstanceID == 0) continue; // no hit
            // use _results[i].point / .distance
        }
    }

    void OnDisable()
    {
        _handle.Complete();
        if (_cmds.IsCreated) _cmds.Dispose();
        if (_results.IsCreated) _results.Dispose();
    }
}
```

`RaycastHit.colliderInstanceID` exists on 2021.3+; if your version lacks it, test
`_results[i].collider != null` (this touches a managed object but does not allocate).

## 3. Strings and text (U5-010, U5-013, U5-014)

```csharp
using TMPro;
using UnityEngine;

public sealed class AmmoCounter : MonoBehaviour
{
    [SerializeField] TMP_Text label;
    int _last = int.MinValue;

    public void Show(int ammo)
    {
        if (ammo == _last) return;           // no rebuild if unchanged
        _last = ammo;
        label.SetText("{0}", ammo);          // no string allocation
    }
}
```

- `SetText` accepts StringBuilder and `char[]` on all versions, and
  `ReadOnlySpan<char>` on 6.6+ (U5-014). `label.text = ammo.ToString()` allocates.
- Guard hot-path logging so the format string is never built in release:

```csharp
using System.Diagnostics;

public static class DevLog
{
    [Conditional("DEVELOPMENT_BUILD"), Conditional("UNITY_EDITOR")]
    public static void Log(string msg) => UnityEngine.Debug.Log(msg);
}
```

On 6.6 `DEVELOPMENT_BUILD` is deprecated (removed in 6.8) in favour of the Managed
Code Variant defines; use `UNITY_ENABLE_CHECKS` or `UNITY_INCLUDE_INSTRUMENTATION`
there (U5-018). When the call is compiled out, its argument expression (and any
string building inside it) is not evaluated either, which is the point.

## 4. Closures, delegates, boxing, params (U5-010)

```csharp
using System;
using System.Collections.Generic;
using UnityEngine;

public sealed class EnemyRegistry : MonoBehaviour
{
    readonly List<Enemy> _enemies = new List<Enemy>(256);
    Action<Enemy> _onDeathCached;           // method group converted ONCE

    void Awake() => _onDeathCached = OnDeath;

    public void Register(Enemy e)
    {
        _enemies.Add(e);
        e.Died += _onDeathCached;           // not "e.Died += OnDeath;" each time
    }

    void OnDeath(Enemy e) => _enemies.Remove(e);

    // Closure-free search: a for loop instead of _enemies.Find(x => x.Id == id)
    public Enemy FindById(int id)
    {
        for (int i = 0; i < _enemies.Count; i++)
            if (_enemies[i].Id == id) return _enemies[i];
        return null;
    }
}

public sealed class Enemy : MonoBehaviour
{
    public int Id;
    public event Action<Enemy> Died;
    public void Kill() => Died?.Invoke(this);
}
```

- Boxing shows as `Box`/`_Box` frames in allocation call stacks (U5-010). Common
  sources: enums as `Dictionary` keys on older runtimes, structs passed as `object`
  or non-generic interfaces, `string.Format` with value-type args.
- `params` methods allocate an array per call; add fixed-arity overloads for hot paths.

## 5. Collision callbacks (U5-057)

Keep Project Settings > Physics > Reuse Collision Callbacks on. The `Collision`
object is then valid only inside the callback: copy what you need, never store it.
Use `collision.GetContacts(List<ContactPoint>)` with a reused list instead of
`collision.contacts`.

## 6. Pool, do not Instantiate/Destroy per event (U5-061, U5-074)

```csharp
using System.Collections.Generic;
using UnityEngine;

public sealed class SimplePool : MonoBehaviour
{
    [SerializeField] GameObject prefab;
    [SerializeField] int prewarm = 32;
    readonly Stack<GameObject> _free = new Stack<GameObject>(64);

    void Awake()
    {
        for (int i = 0; i < prewarm; i++)
        {
            var go = Instantiate(prefab, transform);
            go.SetActive(false);
            _free.Push(go);
        }
    }

    public GameObject Get(Transform parent)
    {
        var go = _free.Count > 0 ? _free.Pop() : Instantiate(prefab);
        go.transform.SetParent(parent, false);  // reparent, update, then enable (U5-074)
        go.SetActive(true);
        return go;
    }

    public void Release(GameObject go)
    {
        go.SetActive(false);                    // disable first, then reparent (U5-074)
        go.transform.SetParent(transform, false);
        _free.Push(go);
    }
}
```

On 2021.3+ `UnityEngine.Pool.ObjectPool<T>` is an alternative; pass its callbacks
as cached delegates.

## 7. One manager instead of N Update() calls (U5-043, U5-044)

```csharp
using UnityEngine;

public interface ITickable { void Tick(float dt); }

public sealed class TickManager : MonoBehaviour
{
    ITickable[] _items = new ITickable[256];   // T[] over List<T> (U5-043)
    int _count;

    public void Add(ITickable t)
    {
        if (_count == _items.Length) System.Array.Resize(ref _items, _count * 2); // grow at load, not per frame
        _items[_count++] = t;
    }

    public void Remove(ITickable t)
    {
        for (int i = 0; i < _count; i++)
            if (ReferenceEquals(_items[i], t)) { _items[i] = _items[--_count]; _items[_count] = null; return; }
    }

    void Update()
    {
        float dt = Time.deltaTime;
        for (int i = 0; i < _count; i++) _items[i].Tick(dt);
    }
}
```

Tickables must not declare `Update()`. Remove empty magic methods and empty virtual
`Update` in base classes (U5-044).

## 8. Time-slice bursty work (Consistency)

```csharp
using System.Collections.Generic;
using Unity.Profiling;
using UnityEngine;

public sealed class SlicedReplanner : MonoBehaviour
{
    static readonly ProfilerMarker s_Marker = new ProfilerMarker("Game.Replan");
    [SerializeField] int perFrame = 8;          // tune from the marker on device
    readonly Queue<Agent> _queue = new Queue<Agent>(512);

    public void Request(Agent a) => _queue.Enqueue(a);

    void Update()
    {
        using (s_Marker.Auto())
        {
            int n = Mathf.Min(perFrame, _queue.Count);
            for (int i = 0; i < n; i++) _queue.Dequeue().Replan();
        }
    }
}

public sealed class Agent : MonoBehaviour { public void Replan() { /* ... */ } }
```

`ProfilerMarker` compiles out of Release builds (U5-079); on 6.6 it also needs a
non-Release Managed Code Variant to appear in a Development build (inference,
U5-018) [verify on device].

## 9. Manual GC control around a no-hitch section (U5-009)

GCMode is not supported in the Editor; this only does anything in a player.

```csharp
using UnityEngine;
using UnityEngine.Scripting;

public static class GcWindow
{
    public static void BeginCritical()
    {
#if !UNITY_EDITOR
        GarbageCollector.GCMode = GarbageCollector.Mode.Disabled; // heap only grows now (U5-003)
#endif
    }

    // Call at a fade or loading screen.
    public static void EndCritical()
    {
#if !UNITY_EDITOR
        GarbageCollector.GCMode = GarbageCollector.Mode.Enabled;
#endif
        System.GC.Collect();
    }

    // Manual mode: spend at most sliceNs per call (whole ms steps, U5-007).
    public static bool StepIncremental(ulong sliceNs = 1_000_000UL)
    {
#if !UNITY_EDITOR
        return GarbageCollector.CollectIncremental(sliceNs); // true while work remains
#else
        return false;
#endif
    }
}
```

Watch "GC Reserved Memory" while disabled; no safe heap ceiling for Quest is
published (U5-009). PSS limits: `quest-perf:quest-budgets-tiers`.

## 10. Release-build GC watchdog (U5-080)

"GC Reserved Memory" and "GC Used Memory" are readable in Release players; "GC
Allocated In Frame" is not (profiler counters reference,
https://docs.unity3d.com/6000.3/Documentation/Manual/profiler-counters-reference.html,
accessed 2026-09-24).

```csharp
using Unity.Profiling;
using UnityEngine;

public sealed class GcWatchdog : MonoBehaviour
{
    ProfilerRecorder _reserved, _used;
    long _lastUsed;
    int _collections;

    void OnEnable()
    {
        _reserved = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC Reserved Memory");
        _used = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC Used Memory");
    }

    void Update()
    {
        long used = _used.LastValue;
        if (used < _lastUsed) _collections++;   // used heap dropped: a collection ran
        _lastUsed = used;
    }

    public string Report() =>
        $"reserved={_reserved.LastValue / (1024 * 1024)}MB used={_lastUsed / (1024 * 1024)}MB collections={_collections}";

    void OnDisable() { _reserved.Dispose(); _used.Dispose(); }
}
```

Log `Report()` once per second (for example into OVR Metrics via
`AppendCsvDebugString`, owned by `unity-perf:unity-profiling-workflow`) across a
20-30 min session: reserved should plateau and collections should stay near zero
during gameplay.

## 11. Burst job over transforms, scheduled early and completed late (U5-041, U5-042)

Throughput. `TransformAccessArray` works on 2021.3-6.6; on 6.3+ `TransformHandle`
is the unmanaged alternative (U5-041). Check in Timeline that the job runs on
worker threads [verify on device]. Keep targets under separate root transforms (or
unparented): transforms sharing a root are processed on one thread [verify on device].

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using UnityEngine;
using UnityEngine.Jobs;

public sealed class BobManager : MonoBehaviour
{
    [SerializeField] Transform[] targets;
    TransformAccessArray _taa;
    NativeArray<float> _phase;
    JobHandle _handle;

    [BurstCompile]
    struct BobJob : IJobParallelForTransform
    {
        [ReadOnly] public NativeArray<float> Phase;
        public float Time;
        public void Execute(int i, TransformAccess t)
        {
            var p = t.localPosition;
            p.y = Mathf.Sin(Time + Phase[i]) * 0.05f;
            t.localPosition = p;
        }
    }

    void OnEnable()
    {
        _taa = new TransformAccessArray(targets);
        _phase = new NativeArray<float>(targets.Length, Allocator.Persistent);
        for (int i = 0; i < _phase.Length; i++) _phase[i] = i * 0.37f;
    }

    void Update()      { _handle = new BobJob { Phase = _phase, Time = Time.time }.Schedule(_taa); }
    void LateUpdate()  { _handle.Complete(); }

    void OnDisable()
    {
        _handle.Complete();
        if (_taa.isCreated) _taa.Dispose();
        if (_phase.IsCreated) _phase.Dispose();
    }
}
```

## 12. fixedDeltaTime from the runtime refresh rate (U5-051, conflict U5-C4)

Only if your A/B picks 1/refresh (SKILL.md fix 6 gives both sides). Call after
any refresh-rate change; then log `Time.fixedDeltaTime` and FixedUpdate calls per
frame on device, because a 2024 report saw no effect on Quest (U5-053).

```csharp
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR;

public static class FixedStepFromRefresh
{
    static readonly List<XRDisplaySubsystem> s_Displays = new List<XRDisplaySubsystem>();
    public static void Apply()
    {
        SubsystemManager.GetSubsystems(s_Displays);
        if (s_Displays.Count > 0 && s_Displays[0].TryGetDisplayRefreshRate(out float hz) && hz > 0f)
            Time.fixedDeltaTime = 1f / hz;
    }
}
```
