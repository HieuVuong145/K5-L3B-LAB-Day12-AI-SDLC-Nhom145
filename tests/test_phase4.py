"""Unit tests cho Phase 4 (Phát hành v1.0.0, Contract v1.3):

- Kiểm tra contract v1.3, bench_cmd, soak_cmd trong game.contract.json
- Kiểm tra benchmark: xuất đúng 5 trường, đạt ngưỡng avg >= 60, 1% low >= 30, load <= 10s
- Kiểm tra soak: chạy N ngày, lặp kế hoạch D1-D5, crashes == 0, days_completed == days
- Kiểm tra mã thoát 2 cho đầu vào sai của bench và soak
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from chonoi.contract import load_contract


class Phase4Contract(unittest.TestCase):
    def test_contract_version_13_and_commands(self):
        c = load_contract()
        self.assertEqual(c.get("contract_version"), "1.3")
        self.assertIn("bench_cmd", c)
        self.assertIn("soak_cmd", c)
        self.assertEqual(c["bench_cmd"], "python3 -m chonoi.bench")
        self.assertEqual(c["soak_cmd"], "python3 -m chonoi.soak")


class Phase4Benchmark(unittest.TestCase):
    def test_bench_produces_valid_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "bench.json")
            cmd = [sys.executable, "-m", "chonoi.bench", "--seed", "42", "--duration", "1", "--out", out_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}")
            self.assertTrue(os.path.exists(out_path))

            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)

            for key in ("avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"):
                self.assertIn(key, data)

            self.assertGreaterEqual(data["avg_fps"], 60.0)
            self.assertGreaterEqual(data["p1_low_fps"], 30.0)
            self.assertLessEqual(data["load_ms"], 10000)
            self.assertGreater(data["frames"], 0)
            self.assertGreater(data["measured_s"], 0)

    def test_bench_bad_input_exit_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "bench.json")
            cmd = [sys.executable, "-m", "chonoi.bench", "--duration", "0", "--out", out_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 2)


class Phase4Soak(unittest.TestCase):
    def test_soak_runs_and_produces_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "soak.json")
            cmd = [sys.executable, "-m", "chonoi.soak", "--seed", "7", "--days", "2", "--out", out_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}")
            self.assertTrue(os.path.exists(out_path))

            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)

            for key in ("days", "days_completed", "crashes", "results", "duration_s"):
                self.assertIn(key, data)

            self.assertEqual(data["days"], 2)
            self.assertEqual(data["days_completed"], 2)
            self.assertEqual(data["crashes"], 0)
            self.assertEqual(len(data["results"]), 2)
            for r in data["results"]:
                for rk in ("day", "earned", "reputation", "score"):
                    self.assertIn(rk, r)

    def test_soak_cycles_plans_for_days_beyond_5(self):
        from chonoi.day import DaySim
        from chonoi.ids import IdAllocator
        from chonoi.rng import Streams
        tuning = load_contract()["tuning"]
        sim = DaySim(tuning, {}, Streams(1), IdAllocator(), days=6)
        plan1 = sim._plan_for(1)
        plan6 = sim._plan_for(6)
        self.assertEqual(plan6["dishes"], plan1["dishes"])
        self.assertEqual(plan6["day"], 6)

    def test_soak_bad_input_exit_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "soak.json")
            cmd = [sys.executable, "-m", "chonoi.soak", "--days", "0", "--seed", "7", "--out", out_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
