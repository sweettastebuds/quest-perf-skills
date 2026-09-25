#!/usr/bin/env python3
"""ADB helper for Meta Quest 2 / 3 / 3S performance toggles and captures.

Stdlib only, Python 3.10+. Calls `adb` (and optionally Meta's `metavr` CLI)
through subprocess. Every property, broadcast and command below appears in
Meta documentation as recorded in research/quest.md or
research/arm-mobile-hw.md; the finding ID is next to each one.
Undocumented property names are never used: `metavr device vrruntime` flags go
through Meta's CLI because the properties behind them are unpublished (Q1-083),
and `debug.oculus.headlock` is excluded because no Meta page documents it.

Debug properties reset on reboot (Q1-077). Every capture subcommand writes a
`getprop` snapshot of debug.oculus.* next to its output.

Global options (before the subcommand):
    --dry-run        print the adb commands instead of running them
    -s/--serial SN   target one device (adb -s)

Examples:
    python quest_adb.py --dry-run pin-levels --cpu 4 --gpu 4
    python quest_adb.py isolate-gpu --cpu 4 --gpu 4
    python quest_adb.py csv-on
    python quest_adb.py pull-csv --out captures/run01
    python quest_adb.py logcat --seconds 60 --out captures/run01/vrapi.log
    python quest_adb.py gpu-trace --package com.example.app --seconds 2 --low-overhead
    python quest_adb.py perfetto --app com.example.app --mode gpu --duration-ms 10000 -o run01.pftrace
"""
from __future__ import annotations

import argparse
import datetime as _dt
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

CSV_DIR = "/sdcard/Android/data/com.oculus.ovrmonitormetricsservice/files/CapturedMetrics/"  # Q1-008, A3-049
OMMS_RECEIVER = "com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver"  # Q1-003
OMMS_ACTION = "com.oculus.ovrmonitormetricsservice."  # Q1-003
VRRUNTIME = "com.oculus.vrruntimeservice."  # Q2-014, A3-051
REFRESH_RATES = {  # Q1-078 (system-properties page); the app-side list is wider (Q2-010)
    "quest2": {60, 72, 80, 90, 120},
    "quest3": {72, 80, 90, 120},
}
PERFETTO_TRACE = "/data/misc/perfetto-traces/trace"  # Q1-048 (2021 blog)


class Runner:
    def __init__(self, dry: bool, serial: str | None):
        self.dry = dry
        self.serial = serial

    def adb(self, *args: str) -> list[str]:
        base = ["adb"] + (["-s", self.serial] if self.serial else [])
        return base + list(args)

    def run(self, cmd: list[str], capture: bool = False, stdin_path: Path | None = None,
            timeout: float | None = None, ok_codes: tuple[int, ...] = (0,)) -> str:
        shown = " ".join(shlex.quote(c) for c in cmd) + (f" < {stdin_path}" if stdin_path else "")
        if self.dry:
            print(shown)
            return ""
        print(f"+ {shown}", file=sys.stderr)
        if shutil.which(cmd[0]) is None:
            sys.exit(f"error: '{cmd[0]}' not found on PATH")
        stdin = stdin_path.open("rb") if stdin_path else None
        try:
            p = subprocess.run(cmd, stdin=stdin, capture_output=capture, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            return (e.stdout or "") if isinstance(e.stdout, str) else ""
        finally:
            if stdin:
                stdin.close()
        if p.returncode not in ok_codes:
            msg = (p.stderr or "").strip() if capture else ""
            sys.exit(f"error: command failed ({p.returncode}): {shown} {msg}")
        return p.stdout if capture else ""

    def shell(self, *args: str, capture: bool = False, timeout: float | None = None,
              ok_codes: tuple[int, ...] = (0,)) -> str:
        return self.run(self.adb("shell", *args), capture=capture, timeout=timeout, ok_codes=ok_codes)

    def setprop(self, name: str, value: str) -> None:
        self.shell("setprop", name, value)

    def broadcast_omms(self, action: str, *extra: str) -> None:
        # Q1-003: am broadcast -n <receiver> -a com.oculus.ovrmonitormetricsservice.<ACTION>
        self.shell("am", "broadcast", "-n", OMMS_RECEIVER, "-a", OMMS_ACTION + action, *extra)

    def stream(self, cmd: list[str], out: Path | None, seconds: float | None) -> None:
        """Run a long-lived command (logcat) for N seconds, teeing to a file."""
        shown = " ".join(shlex.quote(c) for c in cmd)
        if self.dry:
            print(shown + (f" > {out}" if out else "") + (f"   # stop after {seconds:g} s" if seconds else ""))
            return
        if shutil.which(cmd[0]) is None:
            sys.exit(f"error: '{cmd[0]}' not found on PATH")
        print(f"+ {shown}", file=sys.stderr)
        fh = out.open("w", encoding="utf-8") if out else None
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="replace")
        t_end = time.monotonic() + seconds if seconds else None
        try:
            assert p.stdout is not None
            for line in p.stdout:
                (fh.write(line) if fh else sys.stdout.write(line))
                if t_end and time.monotonic() > t_end:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            p.terminate()
            if fh:
                fh.close()


def props_snapshot(r: Runner, out_dir: Path | None) -> None:
    """Record debug.oculus.* props next to a capture (Q1-077)."""
    if r.dry:
        r.shell("getprop")
        print(f"#   -> filter lines containing 'debug.oculus' into {(out_dir or Path('.')) / 'props-snapshot.txt'}")
        return
    text = r.shell("getprop", capture=True)
    lines = [ln for ln in text.splitlines() if "debug.oculus" in ln]
    stamp = _dt.datetime.now().isoformat(timespec="seconds")
    body = f"# getprop debug.oculus.* at {stamp}\n" + "\n".join(lines) + "\n"
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "props-snapshot.txt").write_text(body, encoding="utf-8")
        print(f"props snapshot -> {out_dir / 'props-snapshot.txt'}", file=sys.stderr)
    else:
        sys.stdout.write(body)


# ---- subcommands ---------------------------------------------------------------

def cmd_pin_levels(r: Runner, a) -> None:
    # Q1-079: debug.oculus.cpuLevel / debug.oculus.gpuLevel override the app's levels.
    if a.cpu is not None:
        r.setprop("debug.oculus.cpuLevel", str(a.cpu))
    if a.gpu is not None:
        r.setprop("debug.oculus.gpuLevel", str(a.gpu))
    print("# Levels stay pinned until reboot (Q1-077). Unpin (reboot) before any thermal soak (Q1-079).",
          file=sys.stderr)


def cmd_refresh_rate(r: Runner, a) -> None:
    # Q1-078: debug.oculus.refreshRate; Quest 2: 60/72/80/90/120, Quest 3/3S: 72/80/90/120.
    allowed = REFRESH_RATES.get(a.device) if a.device else None
    if allowed and a.hz not in allowed:
        print(f"warning: {a.hz} Hz is not in the system-properties list for {a.device}: {sorted(allowed)}",
              file=sys.stderr)
    r.setprop("debug.oculus.refreshRate", str(a.hz))


def cmd_foveation(r: Runner, a) -> None:
    # Q1-081 / Q3-028: set dynamic 0 first, or dynamic foveation overrides the level. 0 Off .. 4 High Top.
    r.setprop("debug.oculus.foveation.dynamic", "0")
    r.setprop("debug.oculus.foveation.level", str(a.level))


def cmd_subsampled(r: Runner, a) -> None:
    # Q3-045: debug.oculus.foveation.subsampled 1|0 (Vulkan subsampled layout A/B).
    r.setprop("debug.oculus.foveation.subsampled", "1" if a.state == "on" else "0")


def cmd_compositor_skip(r: Runner, a) -> None:
    # A3-051 / Q2-039: compositor stops rendering so TW=0 and App= is app-only GPU time.
    r.shell("am", "broadcast", "-a", VRRUNTIME + "COMPOSITOR_SKIP_RENDERING", "--ei", "milliseconds", str(a.ms))


def cmd_isolate_gpu(r: Runner, a) -> None:
    # A3-051 / Q2-039 recipe: pin levels, foveation off, optional compositor skip.
    cmd_pin_levels(r, a)
    r.setprop("debug.oculus.foveation.dynamic", "0")
    r.setprop("debug.oculus.foveation.level", "0")
    if a.skip_ms:
        r.shell("am", "broadcast", "-a", VRRUNTIME + "COMPOSITOR_SKIP_RENDERING", "--ei", "milliseconds",
                str(a.skip_ms))
    print("# Also disable dynamic resolution in the build (A3-052); it is an app setting, not a prop.",
          file=sys.stderr)


def cmd_thermal_sim(r: Runner, a) -> None:
    # Q2-014: simulate the thermal refresh-rate step.
    r.shell("am", "broadcast", "-a", VRRUNTIME + "COMPOSITOR_SIMULATE_THERMAL", "--es", "subsystem", "refresh",
            "--ei", "seconds_throttled", str(a.seconds))


def cmd_appsw_debug(r: Runner, a) -> None:
    # Q3-074: motion-vector overlay and forced half rate.
    if a.off:
        # Meta documents no "off" values for these props; reboot is the documented reset (Q1-077).
        print("# To clear the AppSW debug props, reboot: quest_adb.py reset --yes (Q1-077).", file=sys.stderr)
        return
    r.setprop("debug.oculus.spaceWarpDebug", "1")
    r.setprop("debug.oculus.MVOverlay", str(a.mode))
    r.setprop("debug.oculus.MVOverlay.Alpha", str(a.alpha))
    if a.half_rate:
        r.setprop("debug.oculus.sysPropDebug", "1")
        r.setprop("debug.oculus.swapInterval", "2")
    print("# Meta's steps finish with two power-button presses (Q3-074). Modes: 1 MV, 2 depth, "
          "3 MV amplified, 4 amplified with gray at zero.", file=sys.stderr)


def cmd_csv(r: Runner, a) -> None:
    # Q1-002 / Q1-003 / A3-049: Report Mode on/off, overlay on/off, LOG_STATE.
    if a.action == "on":
        r.broadcast_omms("ENABLE_CSV")
    elif a.action == "off":
        r.broadcast_omms("DISABLE_CSV")
    elif a.action == "overlay-on":
        r.broadcast_omms("ENABLE_OVERLAY")
    elif a.action == "overlay-off":
        r.broadcast_omms("DISABLE_OVERLAY")
    elif a.action == "log-state":
        r.broadcast_omms("LOG_STATE")  # prints the configuration to logcat as JSON
    elif a.action == "open":
        r.shell("am", "start", "omms://app")  # Q1-001


def cmd_pull_csv(r: Runner, a) -> None:
    # Q1-008: CSVs land in CapturedMetrics/, one per app launch; the pull is standard adb.
    out = Path(a.out)
    if not r.dry:
        out.mkdir(parents=True, exist_ok=True)
    r.run(r.adb("pull", CSV_DIR, str(out)))
    props_snapshot(r, out)
    # Q1-001 / QUEST-GF1-006: record the on-device tool version with the capture.
    info = r.shell("dumpsys", "package", "com.oculus.ovrmonitormetricsservice", capture=not r.dry)
    if r.dry:
        print(f"#   -> versionName lines into {out / 'ovr-metrics-version.txt'}")
    else:
        ver = [ln.strip() for ln in (info or "").splitlines() if "versionName" in ln]
        (out / "ovr-metrics-version.txt").write_text("\n".join(ver) + "\n", encoding="utf-8")


def cmd_logcat(r: Runner, a) -> None:
    # Q1-027: adb logcat -s VrApi,XrPerformanceManager (per-second stats line, level changes).
    out = Path(a.out) if a.out else None
    if a.clear:
        r.run(r.adb("logcat", "-c"))
    if out and not r.dry:
        out.parent.mkdir(parents=True, exist_ok=True)
    r.stream(r.adb("logcat", "-s", *a.tags.split()), out, a.seconds)
    if out:
        props_snapshot(r, out.parent)


def cmd_clocklog(r: Runner, a) -> None:
    # Q1-036: debug.oculus.clockStateLogLevel 0/1/2 logs every CPU/GPU clock change with its reason.
    r.setprop("debug.oculus.clockStateLogLevel", str(a.level))


def cmd_gpu_metrics(r: Runner, a) -> None:
    # Q1-065 / A3-027: list real-time metrics; IDs vary per device and runtime, never hard-code them.
    args = ["ovrgpuprofiler", "-m"] + (["-v"] if a.verbose else [])
    if a.stage:
        args.append("-t")  # Q1-072: per-render-stage metric list
    if a.draw:
        args.insert(1, "-x")  # Q1-073: per-draw metric list
    r.shell(*args)


def cmd_gpu_realtime(r: Runner, a) -> None:
    # Q1-066: -r"<ids>" prints chosen metrics once per second; no more than 30 at once.
    ids = [x for x in a.ids.split(",") if x.strip()]
    if len(ids) > 30:
        sys.exit("error: ovrgpuprofiler accepts at most 30 real-time metrics at once (Q1-066)")
    r.shell("timeout", str(a.seconds), "ovrgpuprofiler", f"-r{','.join(ids)}", timeout=a.seconds + 10,
            ok_codes=(0, 124))  # 124 = timeout expired, the normal stop


def cmd_gpu_trace(r: Runner, a) -> None:
    # Q1-067 / Q1-068 / A3-029 / A3-030: detailed mode (-e, ~10% GPU cost, restart app), trace, then -d.
    if a.disable:
        r.shell("ovrgpuprofiler", "-d")
        return
    if a.enable:
        r.shell("ovrgpuprofiler", "-e", *( [a.package] if a.package else []))
        print("# Detailed mode applies to apps started afterwards: restart the app, then run gpu-trace "
              "without --enable. Run 'gpu-trace --disable' when finished (Q1-067).", file=sys.stderr)
        return
    r.shell("ovrgpuprofiler", "-i")  # state check
    args = ["ovrgpuprofiler", f"-t{a.seconds:g}"]
    if a.low_overhead:
        args.append("-l")
    if a.verbose:
        args.append("-v")
    out = r.shell(*args, capture=not r.dry)
    if a.out and not r.dry:
        p = Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out, encoding="utf-8")
        props_snapshot(r, p.parent)
    elif out:
        sys.stdout.write(out)


def cmd_gpumeminfo(r: Runner, a) -> None:
    # Q1-095: adb shell gpumeminfo -p $(pidof <process>)
    if r.dry:
        r.shell("pidof", a.package)
        r.shell("gpumeminfo", "-p", "<pid>", *(["-l"] if a.l else []))
        return
    pid = r.shell("pidof", a.package, capture=True).strip().split()
    if not pid:
        sys.exit(f"error: {a.package} is not running")
    sys.stdout.write(r.shell("gpumeminfo", "-p", pid[0], *(["-l"] if a.l else []), capture=True))


def cmd_perfetto(r: Runner, a) -> None:
    out = Path(a.out)
    if a.legacy_cli:
        # Q1-048 (Apr 2021 blog, pre-2023): raw perfetto CLI with a track_event config.
        cfg = out.with_suffix(".config.txt")
        text = (
            "buffers: { size_kb: 63488 fill_policy: DISCARD }\n"
            "buffers: { size_kb: 2048 fill_policy: DISCARD }\n"
            'data_sources: { config { name: "track_event" } }\n'
            'data_sources: { config { name: "linux.process_stats" target_buffer: 1 } }\n'
            f"duration_ms: {a.duration_ms}\n"
        )
        if r.dry:
            print(f"# write {cfg}:\n" + "".join("#   " + ln + "\n" for ln in text.splitlines()))
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(text, encoding="utf-8")
        r.shell("rm", "-f", PERFETTO_TRACE)
        r.run(r.adb("shell", "perfetto", "-c", "-", "--txt", "-o", PERFETTO_TRACE), stdin_path=cfg)
        r.run(r.adb("pull", PERFETTO_TRACE, str(out)))
        if a.gpu_metrics:
            print("# Q1-048/A3-046 (2021): GPU metrics needed 'ovrgpuprofiler -r' running in the background; "
                  "whether current OS builds still need it is open (ARM-C18).", file=sys.stderr)
    else:
        # Q1-049: Meta's metavr CLI (formerly hzdb).
        exe = shutil.which("metavr")
        base = [exe or "metavr"] if (exe or r.dry) else ["npx", "-y", "metavr"]
        cmd = base + ["perf", "capture", "--mode", a.mode, "--duration", str(a.duration_ms), "--app", a.app,
                      "-o", str(out)]
        if a.serial_metavr:
            cmd += ["-d", a.serial_metavr]
        elif r.serial:
            cmd += ["-d", r.serial]
        if a.launch:
            cmd.append("--launch")
        for flag in a.flags or []:
            cmd.append(flag if flag.startswith("--") else "--" + flag)
        if not r.dry:
            out.parent.mkdir(parents=True, exist_ok=True)
        r.run(cmd)
    props_snapshot(r, out.parent if str(out.parent) else Path("."))


def cmd_vrruntime(r: Runner, a) -> None:
    # Q1-083: metavr device vrruntime get|reset|set --cpu-level 0-5 --gpu-level 0-5 --foveation-level 0-4 ...
    exe = shutil.which("metavr")
    base = [exe or "metavr"] if (exe or r.dry) else ["npx", "-y", "metavr"]
    rest = list(a.rest)
    if rest and rest[0] == "--":
        rest = rest[1:]
    if r.serial and "-d" not in rest:
        rest = rest + ["-d", r.serial]
    r.run(base + ["device", "vrruntime"] + rest)


def cmd_props(r: Runner, a) -> None:
    props_snapshot(r, Path(a.out) if a.out else None)


def cmd_reset(r: Runner, a) -> None:
    # Q1-077: property changes are lost on reboot; reboot is the reset.
    if not a.yes and not r.dry:
        sys.exit("refusing to reboot without --yes")
    r.run(r.adb("reboot"))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Quest perf toggles and captures over adb (Meta-documented only).")
    ap.add_argument("--dry-run", action="store_true", help="print commands, do not run them")
    ap.add_argument("-s", "--serial", default=None, help="adb device serial")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("pin-levels", help="setprop debug.oculus.cpuLevel/gpuLevel (Q1-079)")
    p.add_argument("--cpu", type=int)
    p.add_argument("--gpu", type=int)
    p.set_defaults(fn=cmd_pin_levels)

    p = sp.add_parser("refresh-rate", help="setprop debug.oculus.refreshRate (Q1-078)")
    p.add_argument("hz", type=int)
    p.add_argument("--device", choices=sorted(REFRESH_RATES), help="warn if the rate is not listed for it")
    p.set_defaults(fn=cmd_refresh_rate)

    p = sp.add_parser("foveation", help="dynamic off + fixed level 0-4 (Q1-081)")
    p.add_argument("--level", type=int, default=0, choices=range(5))
    p.set_defaults(fn=cmd_foveation)

    p = sp.add_parser("subsampled", help="debug.oculus.foveation.subsampled on/off (Q3-045)")
    p.add_argument("state", choices=["on", "off"])
    p.set_defaults(fn=cmd_subsampled)

    p = sp.add_parser("compositor-skip", help="COMPOSITOR_SKIP_RENDERING broadcast (A3-051)")
    p.add_argument("--ms", type=int, default=60000)
    p.set_defaults(fn=cmd_compositor_skip)

    p = sp.add_parser("isolate-gpu", help="pin levels + foveation off (+ compositor skip) (A3-051, Q2-039)")
    p.add_argument("--cpu", type=int, default=4)
    p.add_argument("--gpu", type=int, default=4)
    p.add_argument("--skip-ms", type=int, default=0, help="also skip compositor rendering for N ms")
    p.set_defaults(fn=cmd_isolate_gpu)

    p = sp.add_parser("thermal-sim", help="COMPOSITOR_SIMULATE_THERMAL refresh step (Q2-014)")
    p.add_argument("--seconds", type=int, default=10)
    p.set_defaults(fn=cmd_thermal_sim)

    p = sp.add_parser("appsw-debug", help="AppSW MV overlay / forced half rate (Q3-074)")
    p.add_argument("--mode", type=int, default=4, choices=[1, 2, 3, 4])
    p.add_argument("--alpha", type=float, default=0.8)
    p.add_argument("--half-rate", action="store_true", help="sysPropDebug 1 + swapInterval 2")
    p.add_argument("--off", action="store_true")
    p.set_defaults(fn=cmd_appsw_debug)

    p = sp.add_parser("csv", help="OVR Metrics broadcasts: on/off/overlay-on/overlay-off/log-state/open (Q1-003)")
    p.add_argument("action", choices=["on", "off", "overlay-on", "overlay-off", "log-state", "open"])
    p.set_defaults(fn=cmd_csv)

    p = sp.add_parser("csv-on", help="alias of 'csv on' (A3-049)")
    p.set_defaults(fn=lambda r, a: r.broadcast_omms("ENABLE_CSV"))

    p = sp.add_parser("pull-csv", help="pull CapturedMetrics/ + props snapshot (Q1-008)")
    p.add_argument("--out", default="CapturedMetrics")
    p.set_defaults(fn=cmd_pull_csv)

    p = sp.add_parser("logcat", help="adb logcat -s VrApi,XrPerformanceManager (Q1-027)")
    p.add_argument("--tags", default="VrApi,XrPerformanceManager")
    p.add_argument("--seconds", type=float, default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--clear", action="store_true", help="adb logcat -c first")
    p.set_defaults(fn=cmd_logcat)

    p = sp.add_parser("clocklog", help="debug.oculus.clockStateLogLevel 0/1/2 (Q1-036)")
    p.add_argument("level", type=int, choices=[0, 1, 2])
    p.set_defaults(fn=cmd_clocklog)

    p = sp.add_parser("gpu-metrics", help="ovrgpuprofiler -m [-v] [-t|-x] (Q1-065, Q1-072, Q1-073)")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--stage", action="store_true")
    p.add_argument("--draw", action="store_true")
    p.set_defaults(fn=cmd_gpu_metrics)

    p = sp.add_parser("gpu-realtime", help="ovrgpuprofiler -r<ids> for N seconds (Q1-066)")
    p.add_argument("--ids", required=True, help="comma-separated IDs resolved from gpu-metrics on THIS device")
    p.add_argument("--seconds", type=int, default=20)
    p.set_defaults(fn=cmd_gpu_realtime)

    p = sp.add_parser("gpu-trace", help="ovrgpuprofiler -e / -t / -d render-stage trace (Q1-067, Q1-068)")
    p.add_argument("--package", default=None)
    p.add_argument("--enable", action="store_true", help="enable detailed mode (-e), then restart the app")
    p.add_argument("--disable", action="store_true", help="disable detailed mode (-d)")
    p.add_argument("--seconds", type=float, default=0.1)
    p.add_argument("--low-overhead", action="store_true", help="-l: one line per surface")
    p.add_argument("--verbose", action="store_true", help="-v: per-bin and per-stage detail")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_gpu_trace)

    p = sp.add_parser("gpumeminfo", help="per-process GPU memory (Q1-095)")
    p.add_argument("package")
    p.add_argument("-l", action="store_true")
    p.set_defaults(fn=cmd_gpumeminfo)

    p = sp.add_parser("perfetto", help="trace via metavr perf capture (Q1-049) or --legacy-cli (Q1-048)")
    p.add_argument("--app", required=True)
    p.add_argument("--mode", default="standard",
                   choices=["standard", "gpu", "cpu", "memory", "lightweight", "full", "vr/xr", "custom"])
    p.add_argument("--duration-ms", type=int, default=10000)
    p.add_argument("-o", "--out", default="trace.pftrace")
    p.add_argument("--launch", action="store_true", help="capture a cold start")
    p.add_argument("--flags", nargs="*", help="extra metavr flags, e.g. gpu-render-stage gpu-metrics xr-runtime")
    p.add_argument("--serial-metavr", default=None, help="metavr -d device")
    p.add_argument("--legacy-cli", action="store_true", help="raw perfetto CLI (2021 recipe)")
    p.add_argument("--gpu-metrics", action="store_true", help="with --legacy-cli: print the ovrgpuprofiler note")
    p.set_defaults(fn=cmd_perfetto)

    p = sp.add_parser("vrruntime", help="forward to 'metavr device vrruntime' (Q1-083)")
    p.add_argument("rest", nargs=argparse.REMAINDER, help="get | reset | set --cpu-level N ...")
    p.set_defaults(fn=cmd_vrruntime)

    p = sp.add_parser("props-snapshot", help="getprop | debug.oculus.* (Q1-077)")
    p.add_argument("--out", default=None, help="directory for props-snapshot.txt")
    p.set_defaults(fn=cmd_props)

    p = sp.add_parser("reset", help="adb reboot: clears all debug props (Q1-077)")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_reset)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    r = Runner(a.dry_run, a.serial)
    a.fn(r, a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
