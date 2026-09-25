# AGENTS.md — quest-perf-skills

Authoring rules for this repository. Every agent working here — researcher,
writer, auditor, fixer — must follow this file. Read it before touching
anything.

This repo is a marketplace of four plugins (skill bundles) about frame rate and
frame-time consistency for Unity URP apps on Meta Quest 2 and Quest 3/3S:

| Plugin | Domain |
| --- | --- |
| `quest-perf` | Meta Horizon OS platform, runtime, Meta SDK features, tooling |
| `unity-perf` | Unity 2021.3 LTS through latest Unity 6.x, URP-focused |
| `gles3-perf` | OpenGL ES 3.x on Quest, and the GLES-vs-Vulkan decision |
| `arm-mobile-hw-perf` | Snapdragon XR2: ARM CPU cores, Adreno GPU, memory, bandwidth, thermals |

## The two goals

Every skill, and every fix inside a skill, must serve at least one of these and
must say which:

- **Throughput** — more FPS, through lower average CPU and GPU frame time.
- **Consistency** — smooth frame delivery:
  - no stale or dropped frames
  - tight p95/p99 frame times
  - no hitches (GC, shader/PSO compilation, loading, physics spikes)
  - no thermal decay across a 20–30 minute session

Anything that serves neither goal stays out.

## The reader

An AI agent assisting a senior technical artist who owns a Unity URP pipeline,
writes HLSL, builds C# editor tooling, and ships on Quest. Consequences:

- No beginner explanations.
- Lead with diagnosis, numbers, and concrete settings.
- State exactly which headset, Unity version, URP version, and graphics API
  each claim applies to.

## Baseline facts (verified Sept 2026 — re-verify at run time)

**Hardware**
- Quest 2: Snapdragon XR2 (Gen 1), Adreno 650, 6 GB RAM.
- Quest 3: Snapdragon XR2 Gen 2, Adreno 740, 8 GB RAM.
- Quest 3S: XR2 Gen 2 with a Quest 2-class display — treat as a Quest 3 variant.
- None of these headsets has eye tracking. Eye-tracked foveation gets a
  one-line note only.

**Frame budgets**
- 72 Hz = 13.9 ms, 90 Hz = 11.1 ms, 120 Hz = 8.3 ms.
- The app never gets the whole budget; find Meta's current guidance on real
  headroom after compositor and OS overhead.

**Unity range**
- 2021.3 LTS (URP 12), 2022.3 LTS (URP 14), 2023.1/3.2 (brief), 6.0 LTS
  (URP 17, LTS ends Oct 2026), 6.1, 6.2, 6.3 LTS (to Dec 2027), 6.4, 6.5,
  6.6 (current as of Sept 2026), 6.7 LTS if shipped by run time.

**Graphics API**
- Meta recommends Vulkan; OpenGL ES is legacy: supported, no new features.
- Unity's issue tracker has a report of Vulkan performing much worse than GLES
  on Quest 2/3 due to excessive buffer copies (reproduced on 2022.3.56f1 and
  6000.0.33f1). Establish current status; the gles3 bundle needs an honest
  GLES-vs-Vulkan decision skill.

**GPU vendor**
- The Quest GPU is Qualcomm Adreno, not Arm Mali. Arm's GPU material teaches
  tile-based rendering concepts well; its Mali-specific counters, tools, and
  tile details do not transfer.

**Out of scope**
PC VR / Link, HDRP (one-line note), Unreal, Godot, and generic phone advice
that doesn't hold for stereo VR.

## Repo layout

```
quest-perf-skills/
├── .omp-plugin/marketplace.json      # omp catalog (primary)
├── .claude-plugin/marketplace.json   # identical copy for Claude Code
├── AGENTS.md                         # this file
├── README.md
├── OUTLINE.md
├── research/                         # dossiers: quest.md, unity.md, gles3.md, arm-mobile-hw.md
├── tools/                            # lint_skills.py, check_links.py
└── plugins/
    ├── quest-perf/
    │   ├── .omp-plugin/plugin.json   # omp reads this first
    │   ├── .claude-plugin/plugin.json
    │   └── skills/<skill-name>/      # SKILL.md, references/, scripts/
    ├── unity-perf/
    ├── gles3-perf/
    └── arm-mobile-hw-perf/
```

Keep `.omp-plugin/*.json` and `.claude-plugin/*.json` byte-identical.

## Research dossiers (`research/*.md`)

Format:

- Group findings by topic.
- Each finding carries: source URL, access date, the versions and devices it
  applies to, and exactly one evidence tag:
  - `[doc]` — official documentation (Meta, Unity, Qualcomm, Khronos, Arm,
    Android)
  - `[measured]` — a source reporting its own measurements, with its setup
  - `[community]` — forums, issue trackers, posts; leads, confirm or keep the
    label
- Record conflicts between sources explicitly. Never pick one silently.

Source priorities:

1. **Meta Horizon OS developer docs** — performance guidelines; OVR Metrics
   Tool; Meta Quest Developer Hub + Perfetto; RenderDoc Meta Fork;
   ovrgpuprofiler; CPU/GPU performance levels; FFR and dynamic foveation;
   dynamic resolution; Application SpaceWarp; compositor layers; Passthrough /
   Depth API / scene costs; store performance requirements; Connect and GDC
   talks.
2. **Unity** — manual and URP docs per version; What's New pages and upgrade
   guides; the Unity 6 mobile/XR optimization e-book; issue tracker; Unite
   talks.
3. **Qualcomm** — Snapdragon Profiler docs; Adreno GPU developer guides (GLES
   and Vulkan); Adreno-specific features.
4. **Khronos** — GLES 3.0/3.1/3.2 specs; extension registry (OVR_multiview2,
   QCOM_texture_foveated, EXT_shader_framebuffer_fetch, QCOM tiled-rendering);
   confirm which extensions each headset actually exposes.
5. **Arm** — CPU core docs matching each XR2's cores; big.LITTLE/DynamIQ
   scheduling; NEON; GPU best-practice guides for tile-based concepts only.
6. **Android** — Perfetto, thermal behavior, ADB tooling.

Research method: `web_search` to find, `read <url>` to pull (handles PDFs,
GitHub, docs sites). If `read` returns a thin or empty page — common on
developers.meta.com — fall back to the `browser` tool.

## Skill format (plugins/<bundle>/skills/<name>/)

- **Location:** `skills/<name>/SKILL.md`, exactly one level deep. omp does not
  discover nested skill folders.
- **Name:** the directory name is the invocation name (`/skill:<name>`);
  `name:` in frontmatter must equal it. Prefix by bundle: `quest-`, `unity-`,
  `gles-`, `xr2-`. Names must be globally distinctive — omp keeps one
  same-named skill and shadows the rest.
- **Description:** required, the only trigger. omp lists every description at
  session start, so 200–400 characters (hard cap 1024). Include actions,
  objects (headset, engine, API), and symptom phrases users type: "stutter",
  "GPU-bound", "stale frames", "FPS drops after 10 minutes", "too many draw
  calls", "hitch on first use".
- **Body:** under ~400 lines (linter errors past 500). Deep tables and
  per-version detail go in `references/*.md`; executables in `scripts/`.
  Supporting files never load or run on their own — SKILL.md must say when to
  read each reference and how to run each script.
- **Cross-references:** refer to sibling skills as `skill://<name>`. The linter
  also accepts `plugin:skill` notation (`quest-perf:skill-name`).

### Body structure — every skill, in order

1. **When to use / when not.** If not, name the sibling skill instead.
2. **Diagnose first.** The metric or capture that confirms this is the
   bottleneck, with the exact tool and command.
3. **Key numbers.** Budgets, costs, thresholds, each with source and
   applicability tag.
4. **Fixes, ranked by payoff ÷ effort.** Each fix states:
   - what to change: exact setting path, C#, HLSL, or shell
   - effect on average frame time vs frame-time variance
   - quality cost and side effects
   - applicability tags, e.g. `Quest 2`, `Quest 3/3S`, `Unity ≥ 6000.0`,
     `URP 14+`, `GLES`, `Vulkan`
5. **Verify.** Which metric should move, by roughly how much, over what
   session length.
6. **Pitfalls and myths.** Especially popular advice that is outdated or wrong
   for Quest.
7. **Sources.**

The linter (`tools/lint_skills.py`) enforces these seven sections, so keep
the headings discoverable: "When to use", "Diagnose", "Key numbers", "Fixes",
"Verify", "Pitfalls", "Sources".

### Content rules

- No invented numbers. If no source gives one, say so and give the method to
  measure it.
- Tag anything needing hardware confirmation with `[verify on device]`.
- Code must be paste-ready. HLSL follows the URP ShaderLibrary conventions of
  the stated version.
- Line endings: LF only (`.gitattributes` enforces this on commit).

## Scripts

Build each script only if the research supports it.

- **OVR Metrics CSV analyzer (Python, stdlib only)** — reports p50/p95/p99
  frame time, stale frames per minute, CPU/GPU utilization and levels over
  time, thermal drift between first and last 5 minutes. Must run with
  Python 3.10+, no third-party imports.
- **ADB helper** — Quest perf toggles and captures. Property names only from
  Meta docs.
- **Unity editor audit script (C#)** — checks URP asset, Player, and XR
  settings against these skills' recommendations, prints a report. Unity
  cannot run here: mark untested, keep API-conservative, guard version
  differences with `#if UNITY_6000_0_OR_NEWER` etc.

## Git rules

- Atomic commits, one per concern: scaffold, each research dossier, each
  skill, the README, each fix are separate commits. Never batch several
  skills into one commit.
- Conventional messages, e.g. `feat(quest-perf): add quest-appsw skill`,
  `docs(research): add gles3 dossier`.
- **Only the main orchestrator agent runs git.** Subagents never stage,
  commit, push, or run `git restore`/`git clean`.

## Subagent conduct

- Own only the files your task names. Do not touch other files.
- Do not run formatters, linters, or the link checker; the orchestrator runs
  `tools/lint_skills.py` and `tools/check_links.py` once per phase across all
  changed files.
- Do not run git (see above).
- Report gaps honestly — `topics_missing`, `conflicts`, `open_questions` exist
  so the orchestrator can send follow-ups, not so work can be hidden.
