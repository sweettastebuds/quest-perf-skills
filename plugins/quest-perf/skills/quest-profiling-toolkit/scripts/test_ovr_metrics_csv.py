"""Tests for ovr_metrics_csv.py against a synthetic capture.

Run:  python -m unittest discover -s <this scripts dir> -p "test_*.py" -v
"""
from __future__ import annotations

import csv
import io
import json
import statistics
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import make_synthetic_ovr_csv as gen  # noqa: E402
import ovr_metrics_csv as ana  # noqa: E402


def q(values, p):
    """Reference percentile: statistics.quantiles 'inclusive' == linear interpolation."""
    cuts = statistics.quantiles(values, n=100, method="inclusive")
    return cuts[p - 1]


class SyntheticCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "com.example.app#UnityPlayerGameActivity-20260924_120000.csv"
        cls.truth = gen.generate(cls.path, minutes=30, seed=7)
        cls.rep = ana.analyze(cls.path, window_min=5)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_header_is_documented_129_columns(self):
        with self.path.open(encoding="utf-8") as fh:
            header = next(csv.reader(fh))
        self.assertEqual(len(header), 129)
        self.assertEqual(header[0], "Time Stamp")
        self.assertEqual(header[-1], "render_scale")
        self.assertIn("battery_temperature_celcius", header)
        self.assertEqual(self.rep["columns_in_header"], 129)

    def test_refresh_and_budget(self):
        self.assertEqual(self.rep["refresh_hz"], 72)
        self.assertAlmostEqual(self.rep["frame_budget_ms"], 13.889, places=3)

    def test_warmup_rows_dropped(self):
        self.assertEqual(self.rep["warmup_rows_dropped"], gen.WARMUP_ROWS)
        self.assertEqual(self.rep["overall"]["rows"], len(self.truth["app_gpu_us"]))

    def test_gpu_percentiles(self):
        g = self.rep["overall"]["app_gpu_time_ms"]
        vals = self.truth["app_gpu_us"]
        for p in (50, 95, 99):
            self.assertAlmostEqual(g[f"p{p}"], round(q(vals, p) / 1000, 3), places=3, msg=f"p{p}")
        self.assertEqual(g["rows_at_65535_clamp"], 1)
        self.assertGreaterEqual(g["p99"], g["p95"])
        self.assertGreaterEqual(g["p95"], g["p50"])

    def test_frame_interval_percentiles_from_fps(self):
        f = self.rep["overall"]["frame_interval_ms_from_fps"]
        iv = [1e6 / x for x in self.truth["fps"]]
        for p in (50, 95, 99):
            self.assertAlmostEqual(f[f"p{p}"], round(q(iv, p) / 1000, 3), places=3)

    def test_stale_per_minute_and_window(self):
        s = self.rep["overall"]["stale"]
        total = sum(self.truth["stale"])
        minutes = len(self.truth["stale"]) / 60.0
        self.assertEqual(s["total"], total)
        self.assertAlmostEqual(s["per_minute"], round(total / minutes, 2), places=2)
        expected_window = max(per * length for _, length, per, _ in gen.STALE_BURSTS)
        self.assertEqual(s["max_in_any_60s_window"], expected_window)

    def test_hitch_rates(self):
        h = self.rep["overall"]["hitch_rate"]
        n = len(self.truth["consec"])
        ge4 = sum(1 for c in self.truth["consec"] if c >= 4)
        self.assertAlmostEqual(h["B_rows_with_consecutive_ge4_pct"], round(100 * ge4 / n, 3), places=3)
        rendered = sum(self.truth["fps"])
        self.assertAlmostEqual(h["A_stale_over_rendered_frames_pct"],
                               round(100 * sum(self.truth["stale"]) / rendered, 3), places=3)

    def test_drift_direction(self):
        d = self.rep["drift"]
        self.assertEqual(d["thermal_signal"], "battery_temperature_celcius")
        self.assertEqual(d["deltas"]["battery_temperature_celcius"]["direction"], "up")
        self.assertEqual(d["deltas"]["gpu_level"]["direction"], "down")
        self.assertEqual(d["deltas"]["gpu_frequency_MHz"]["direction"], "down")
        self.assertEqual(d["deltas"]["app_gpu_time_ms"]["direction"], "up")
        self.assertEqual(d["power_level_state_max"], 1)
        self.assertNotIn("warning", d)

    def test_placeholders_filtered(self):
        by_col = self.rep["placeholder_or_negative_values_by_column"]
        self.assertIn("battery_current_now_milliamps", by_col)  # 9999
        self.assertIn("face_tracking_overall_latency_milliseconds", by_col)  # 999
        self.assertIn("avg_frag_inst_per_pixel", by_col)  # -67
        self.assertNotIn("app_gpu_time_microseconds", by_col)

    def test_phase_sync_passthrough(self):
        raw = self.rep["overall"]["timing_mode_raw"]["phase_sync_mode"]
        self.assertEqual(list(raw.keys()), ["4"])

    def test_per_minute_table(self):
        pm = self.rep["per_minute"]
        self.assertEqual(len(pm), 30)
        self.assertEqual(pm[0]["gpu_L"], "4")
        self.assertEqual(pm[-1]["gpu_L"], "3")

    def test_json_cli(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ana.main([str(self.path), "--json", "--window-min", "5"])
        self.assertEqual(rc, 0)
        self.assertIn("drift", json.loads(buf.getvalue()))

    def test_text_cli(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ana.main([str(self.path)])
        self.assertEqual(rc, 0)
        self.assertIn("Stale frames", buf.getvalue())


class SegmentAndErrorTest(unittest.TestCase):
    def test_debug_string_segments(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "seg.csv"
            gen.generate(p, minutes=30, seed=3, debug_strings=True)
            rep = ana.analyze(p)
            self.assertEqual(sorted(rep["segments"]), [f"segment_{i}" for i in range(3)])
            self.assertEqual(sum(s["rows"] for s in rep["segments"].values()), rep["overall"]["rows"])

    def test_short_capture_warns(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "short.csv"
            gen.generate(p, minutes=4, seed=1)
            rep = ana.analyze(p, window_min=5)
            self.assertIn("warning", rep["drift"])

    def test_unit_variant_milliseconds(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ms.csv"
            p.write_text("Time Stamp,average_frame_rate,app_gpu_time_milliseconds,stale_frame_count\n"
                         "1000,72,10.0,0\n2000,72,12.0,1\n3000,71,11.0,2\n", encoding="utf-8")
            rep = ana.analyze(p, hz=72)
            self.assertAlmostEqual(rep["overall"]["app_gpu_time_ms"]["p50"], 11.0)
            self.assertEqual(rep["overall"]["stale"]["total"], 3)

    def test_unknown_format_errors(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.csv"
            p.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                rc = ana.main([str(p)])
            self.assertEqual(rc, 2)
            self.assertIn("unrecognised header", err.getvalue())


if __name__ == "__main__":
    unittest.main()
