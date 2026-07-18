"""Tests for the cross-embodiment alignment & mixability tool.

Pure stdlib unittest. No network access. Run with:
    python3 -m unittest discover -s tests -v
"""
import csv
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from align import ingest, normalize, resample, metadata, mixability, run as run_mod, util  # noqa: E402
from data import generate_datasets  # noqa: E402


def make_manifest(**overrides):
    base = {
        "embodiment_id": "test_arm",
        "robot_type": "test_robot",
        "action_dim": 7,
        "control_hz": 20,
        "gripper_convention": "open=1",
        "coord_frame": "robot_base",
        "units": "radians",
        "episode_count": 100,
        "frame_count": 10000,
    }
    base.update(overrides)
    return base


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="align-test-")

    def tearDown(self):
        try:
            shutil.rmtree(self.tmpdir)
        except OSError:
            pass

    def test_validate_flags_missing_field(self):
        m = make_manifest(robot_type="")
        flags = ingest.validate_manifest(m)
        self.assertTrue(any("robot_type" in f for f in flags))

    def test_validate_no_flags_for_complete_manifest(self):
        m = make_manifest()
        flags = ingest.validate_manifest(m)
        self.assertEqual(flags, [])

    def test_validate_flags_negative_counts(self):
        m = make_manifest(episode_count=-5)
        flags = ingest.validate_manifest(m)
        self.assertTrue(any("episode_count" in f for f in flags))

    def test_validate_flags_bad_gripper_convention(self):
        m = make_manifest(gripper_convention="weird")
        flags = ingest.validate_manifest(m)
        self.assertTrue(any("gripper_convention" in f for f in flags))

    def test_validate_flags_action_ranges_length_mismatch(self):
        m = make_manifest(action_dim=7, action_ranges=[[-1, 1], [-1, 1]])
        flags = ingest.validate_manifest(m)
        self.assertTrue(any("action_ranges" in f for f in flags))

    def test_load_all_sorted_deterministic(self):
        for fname, eid in [("b.json", "b_arm"), ("a.json", "a_arm")]:
            util.write_json(os.path.join(self.tmpdir, fname), make_manifest(embodiment_id=eid))
        order, manifests = ingest.load_all(self.tmpdir)
        self.assertEqual(order, ["a_arm", "b_arm"])
        self.assertEqual(set(manifests), {"a_arm", "b_arm"})


class NormalizeTests(unittest.TestCase):
    def test_action_dim_diff_detected(self):
        a = make_manifest(action_dim=7)
        b = make_manifest(action_dim=6)
        self.assertEqual(normalize.action_dim_diff(a, b), 1)

    def test_action_space_plan_infeasible_for_large_gap(self):
        a = make_manifest(action_dim=7)
        b = make_manifest(action_dim=2)
        plan = normalize.action_space_plan(a, b)
        self.assertFalse(plan["feasible"])

    def test_action_space_plan_feasible_for_small_gap(self):
        a = make_manifest(action_dim=7)
        b = make_manifest(action_dim=6)
        plan = normalize.action_space_plan(a, b)
        self.assertTrue(plan["feasible"])

    def test_gripper_plan_flags_conflict(self):
        a = make_manifest(gripper_convention="open=1")
        b = make_manifest(gripper_convention="open=0")
        plan = normalize.gripper_plan(a, b)
        self.assertTrue(plan["conflict"])

    def test_gripper_plan_no_conflict_when_matching(self):
        a = make_manifest(gripper_convention="open=1")
        b = make_manifest(gripper_convention="open=1")
        plan = normalize.gripper_plan(a, b)
        self.assertFalse(plan["conflict"])

    def test_coord_frame_plan_flags_mismatch(self):
        a = make_manifest(coord_frame="robot_base")
        b = make_manifest(coord_frame="world")
        plan = normalize.coord_frame_plan(a, b)
        self.assertTrue(plan["mismatch"])


class ResampleTests(unittest.TestCase):
    def test_downsample_factor_and_warning(self):
        r = resample.compute_resample(native_hz=20, target_hz=5)
        self.assertAlmostEqual(r["factor"], 0.25)
        self.assertEqual(r["action"], "downsample")
        self.assertIsNotNone(r["warning"])

    def test_upsample_factor_and_warning(self):
        r = resample.compute_resample(native_hz=5, target_hz=20)
        self.assertAlmostEqual(r["factor"], 4.0)
        self.assertEqual(r["action"], "upsample")
        self.assertIsNotNone(r["warning"])

    def test_same_hz_no_warning(self):
        r = resample.compute_resample(native_hz=20, target_hz=20)
        self.assertEqual(r["action"], "none")
        self.assertIsNone(r["warning"])

    def test_recommend_target_hz_picks_minimum(self):
        self.assertEqual(resample.recommend_target_hz([20, 20, 5]), 5)

    def test_freq_compatibility_score_symmetric_and_bounded(self):
        s1 = resample.freq_compatibility_score(5, 20)
        s2 = resample.freq_compatibility_score(20, 5)
        self.assertAlmostEqual(s1, s2)
        self.assertAlmostEqual(s1, 0.25)
        self.assertAlmostEqual(resample.freq_compatibility_score(20, 20), 1.0)


class MetadataTests(unittest.TestCase):
    def test_missing_robot_type_detected(self):
        m = make_manifest(robot_type="")
        flags = metadata.missing_metadata_flags(m)
        self.assertTrue(any("robot_type" in f for f in flags))
        self.assertFalse(metadata.has_robot_type(m))

    def test_inconsistent_units_detected(self):
        manifests = {
            "a": make_manifest(embodiment_id="a", units="radians"),
            "b": make_manifest(embodiment_id="b", units="normalized"),
        }
        flags = metadata.inconsistent_units(manifests)
        self.assertEqual(len(flags), 1)

    def test_consistent_units_no_flag(self):
        manifests = {
            "a": make_manifest(embodiment_id="a", units="radians"),
            "b": make_manifest(embodiment_id="b", units="radians"),
        }
        self.assertEqual(metadata.inconsistent_units(manifests), [])

    def test_inherited_label_warning(self):
        manifests = {
            "a": make_manifest(embodiment_id="a", robot_type="shared", action_dim=7),
            "b": make_manifest(embodiment_id="b", robot_type="shared", action_dim=6),
        }
        warnings = metadata.inherited_label_warnings(manifests)
        self.assertEqual(len(warnings), 1)

    def test_no_inherited_label_warning_when_dims_match(self):
        manifests = {
            "a": make_manifest(embodiment_id="a", robot_type="shared", action_dim=7, control_hz=20),
            "b": make_manifest(embodiment_id="b", robot_type="shared", action_dim=7, control_hz=20),
        }
        self.assertEqual(metadata.inherited_label_warnings(manifests), [])


class MixabilityTests(unittest.TestCase):
    def test_pairwise_score_math_identical_manifests(self):
        a = make_manifest(embodiment_id="a")
        b = make_manifest(embodiment_id="b")
        result = mixability.score_pair(a, b)
        self.assertAlmostEqual(result["overall_score"], 1.0)
        self.assertEqual(result["recommendation"], "mix-all")
        self.assertEqual(result["reasons"], [])

    def test_pairwise_score_math_known_value(self):
        a = make_manifest(embodiment_id="a", action_dim=7, control_hz=20,
                           gripper_convention="open=1", coord_frame="robot_base")
        b = make_manifest(embodiment_id="b", action_dim=6, control_hz=20,
                           gripper_convention="open=0", coord_frame="robot_base")
        result = mixability.score_pair(a, b)
        # dim diff=1 -> 0.4*0.30=0.12; freq=1.0*0.25=0.25; gripper conflict -> 0.5*0.15=0.075
        # coord match -> 1.0*0.10=0.10; metadata both present -> 1.0*0.20=0.20
        expected = 0.12 + 0.25 + 0.075 + 0.10 + 0.20
        self.assertAlmostEqual(result["overall_score"], expected, places=4)

    def test_recommendation_mix_all_threshold(self):
        a = make_manifest(embodiment_id="a")
        b = make_manifest(embodiment_id="b")
        result = mixability.score_pair(a, b)
        self.assertEqual(result["recommendation"], "mix-all")

    def test_recommendation_mix_subset_threshold(self):
        a = make_manifest(embodiment_id="a", action_dim=7, control_hz=20,
                           gripper_convention="open=1", coord_frame="robot_base")
        b = make_manifest(embodiment_id="b", action_dim=6, control_hz=20,
                           gripper_convention="open=0", coord_frame="robot_base")
        result = mixability.score_pair(a, b)
        self.assertEqual(result["recommendation"], "mix-subset")

    def test_recommendation_do_not_mix_on_large_dim_gap(self):
        a = make_manifest(embodiment_id="a", action_dim=7)
        b = make_manifest(embodiment_id="b", action_dim=2)
        result = mixability.score_pair(a, b)
        self.assertEqual(result["recommendation"], "do-not-mix")

    def test_recommendation_do_not_mix_on_missing_metadata_plus_freq(self):
        a = make_manifest(embodiment_id="a", control_hz=20)
        b = make_manifest(embodiment_id="b", control_hz=5, robot_type="")
        result = mixability.score_pair(a, b)
        self.assertEqual(result["recommendation"], "do-not-mix")

    def test_do_not_mix_always_cites_reasons(self):
        cases = [
            (make_manifest(embodiment_id="a", action_dim=7), make_manifest(embodiment_id="b", action_dim=2)),
            (make_manifest(embodiment_id="a", control_hz=20),
             make_manifest(embodiment_id="b", control_hz=5, robot_type="")),
        ]
        saw_do_not_mix = False
        for a, b in cases:
            result = mixability.score_pair(a, b)
            if result["recommendation"] == "do-not-mix":
                saw_do_not_mix = True
                self.assertTrue(len(result["reasons"]) > 0)
        self.assertTrue(saw_do_not_mix)

    def test_score_all_pairs_deterministic_order(self):
        manifests = {
            "z_arm": make_manifest(embodiment_id="z_arm"),
            "a_arm": make_manifest(embodiment_id="a_arm"),
        }
        results = mixability.score_all_pairs(manifests)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["embodiment_a"], "a_arm")
        self.assertEqual(results[0]["embodiment_b"], "z_arm")


class GenerateDatasetsTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="align-gen-test-")

    def tearDown(self):
        try:
            shutil.rmtree(self.tmpdir)
        except OSError:
            pass

    def test_generate_datasets_deterministic(self):
        generate_datasets.generate(self.tmpdir)
        contents1 = {}
        for fname in sorted(os.listdir(self.tmpdir)):
            with open(os.path.join(self.tmpdir, fname), "rb") as f:
                contents1[fname] = f.read()
        generate_datasets.generate(self.tmpdir)
        contents2 = {}
        for fname in sorted(os.listdir(self.tmpdir)):
            with open(os.path.join(self.tmpdir, fname), "rb") as f:
                contents2[fname] = f.read()
        self.assertEqual(contents1, contents2)

    def test_generate_datasets_plants_expected_issues(self):
        generate_datasets.generate(self.tmpdir)
        order, manifests = ingest.load_all(self.tmpdir)
        self.assertFalse(metadata.has_robot_type(manifests["bridge_v3_7dof"]))
        hzs = {m["control_hz"] for m in manifests.values()}
        self.assertIn(5, hzs)
        self.assertIn(20, hzs)
        gripper_conventions = {manifests[e]["gripper_convention"] for e in manifests}
        self.assertEqual(gripper_conventions, {"open=1", "open=0"})


class RunPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="align-run-test-")
        self.manifest_dir = os.path.join(self.tmpdir, "manifests")
        self.output_dir = os.path.join(self.tmpdir, "out")
        generate_datasets.generate(self.manifest_dir)

    def tearDown(self):
        try:
            shutil.rmtree(self.tmpdir)
        except OSError:
            pass

    def test_run_writes_all_outputs(self):
        run_mod.run(self.manifest_dir, self.output_dir)
        for fname in ("mixability_report.md", "pairwise.csv", "alignment_plan.csv", "run_summary.txt"):
            self.assertTrue(os.path.isfile(os.path.join(self.output_dir, fname)), fname)

    def test_report_contains_limitations_section(self):
        run_mod.run(self.manifest_dir, self.output_dir)
        with open(os.path.join(self.output_dir, "mixability_report.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("## Limitations", text)
        self.assertIn("does not train", text)

    def test_pairwise_csv_has_expected_row_count(self):
        run_mod.run(self.manifest_dir, self.output_dir)
        with open(os.path.join(self.output_dir, "pairwise.csv"), newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        # header + 3 embodiments -> C(3,2) = 3 pairs
        self.assertEqual(len(rows), 1 + 3)

    def test_run_is_deterministic_md5(self):
        run_mod.run(self.manifest_dir, self.output_dir)
        hashes1 = self._hash_dir(self.output_dir)
        run_mod.run(self.manifest_dir, self.output_dir)
        hashes2 = self._hash_dir(self.output_dir)
        self.assertEqual(hashes1, hashes2)

    def test_run_does_not_delete_unrelated_files_in_output_dir(self):
        os.makedirs(self.output_dir, exist_ok=True)
        sentinel = os.path.join(self.output_dir, "sentinel.txt")
        with open(sentinel, "w", encoding="utf-8") as f:
            f.write("keep me")
        run_mod.run(self.manifest_dir, self.output_dir)
        self.assertTrue(os.path.isfile(sentinel))

    @staticmethod
    def _hash_dir(path):
        hashes = {}
        for fname in sorted(os.listdir(path)):
            fpath = os.path.join(path, fname)
            if os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    hashes[fname] = hashlib.md5(f.read()).hexdigest()
        return hashes


class RunDemoScriptTests(unittest.TestCase):
    def test_run_demo_twice_is_byte_identical(self):
        script = os.path.join(REPO_ROOT, "run_demo.py")
        subprocess.run([sys.executable, script], check=True, cwd=REPO_ROOT, capture_output=True)
        out_dir = os.path.join(REPO_ROOT, "sample_output")
        hashes1 = self._hash_dir(out_dir)
        subprocess.run([sys.executable, script], check=True, cwd=REPO_ROOT, capture_output=True)
        hashes2 = self._hash_dir(out_dir)
        self.assertEqual(hashes1, hashes2)
        self.assertTrue(len(hashes1) > 0)

    @staticmethod
    def _hash_dir(path):
        hashes = {}
        for fname in sorted(os.listdir(path)):
            fpath = os.path.join(path, fname)
            if os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    hashes[fname] = hashlib.md5(f.read()).hexdigest()
        return hashes


if __name__ == "__main__":
    unittest.main()
