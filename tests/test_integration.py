import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from episode_fence.cli import main
from episode_fence.demo import demo_clips
from episode_fence.engine import audit
from episode_fence.io import manifest_text, import_lerobot, read_manifest
from episode_fence.model import Clip, Policy
from episode_fence.report import html_report


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "clips.jsonl"
        self.manifest.write_text(manifest_text(demo_clips()), encoding="utf-8")

    def command(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = main([str(a) for a in args])
        return code, output.getvalue()

    def test_cli_conflicts_write_report_and_exit_one(self):
        report = self.root / "report.json"
        code, _ = self.command("audit", self.manifest, "--history", "8", "--future", "24", "--format", "json", "-o", report)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(report.read_text())["summary"]["affected_clips"], 4)

    def test_cli_plan_and_audit_same_policy(self):
        planned, report = self.root / "planned.jsonl", self.root / "plan.json"
        code, _ = self.command("plan", self.manifest, "--history", "8", "--future", "24", "-o", planned, "--report", report)
        self.assertEqual(code, 0)
        self.assertEqual(self.command("audit", planned, "--history", "8", "--future", "24")[0], 0)
        self.assertEqual(json.loads(report.read_text())["verification"]["status"], "clear")

    def test_input_cannot_be_replaced_even_with_force(self):
        original = self.manifest.read_bytes()
        self.assertEqual(self.command("audit", self.manifest, "-o", self.manifest, "--force")[0], 2)
        self.assertEqual(self.command("plan", self.manifest, "-o", self.manifest, "--force")[0], 2)
        self.assertEqual(self.manifest.read_bytes(), original)

    def test_existing_output_protected(self):
        output = self.root / "report.html"
        output.write_text("keep me")
        self.assertEqual(self.command("audit", self.manifest, "-o", output)[0], 2)
        self.assertEqual(output.read_text(), "keep me")
        self.assertEqual(self.command("audit", self.manifest, "--format", "html", "-o", output, "--force")[0], 1)
        self.assertTrue(output.read_text(encoding="utf-8").startswith("<!doctype html>"))

    def test_report_alias_is_rejected_before_plan_write(self):
        planned = self.root / "planned.jsonl"
        self.assertEqual(self.command("plan", self.manifest, "-o", planned, "--report", planned)[0], 2)
        self.assertFalse(planned.exists())

    def test_missing_report_parent_rejected_before_plan_write(self):
        planned = self.root / "planned.jsonl"
        self.assertEqual(self.command("plan", self.manifest, "-o", planned, "--report", self.root / "missing" / "report.json")[0], 2)
        self.assertFalse(planned.exists())

    def test_demo_is_reproducible_and_does_not_overwrite(self):
        first, second = self.root / "one", self.root / "two"
        self.assertEqual(self.command("demo", "-o", first)[0], 0)
        self.assertEqual(self.command("demo", "-o", second)[0], 0)
        self.assertEqual((first / "before.html").read_bytes(), (second / "before.html").read_bytes())
        self.assertEqual(self.command("demo", "-o", first)[0], 2)

    def test_invalid_input_returns_two_without_traceback(self):
        self.manifest.write_text('{"id":', encoding="utf-8")
        code, output = self.command("audit", self.manifest)
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", output)

    def test_duplicate_ratio_is_rejected(self):
        self.assertEqual(self.command("plan", self.manifest, "--ratios", "a=0.5,a=0.5", "-o", self.root / "plan.jsonl")[0], 2)

    def test_html_escapes_labels(self):
        evil = '</title><script>alert("x")</script>'
        clips = [Clip(evil, evil, 0, 10, 10, evil, group=evil)]
        rendered = html_report(clips, audit(clips), title=evil)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("https://", rendered)

    def test_csv_and_bom(self):
        path = self.root / "clips.csv"
        path.write_text("id,source,start,stop,source_frames,split\na,s,0,10,10,train\n", encoding="utf-8-sig")
        self.assertEqual(len(read_manifest(path)), 1)

    def dataset(self, version="v2.1"):
        root = self.root / "dataset"
        (root / "meta").mkdir(parents=True)
        (root / "meta" / "info.json").write_text(json.dumps({"codebase_version": version, "total_episodes": 2}))
        return root

    def test_v2_metadata_import(self):
        root = self.dataset()
        (root / "meta" / "episodes.jsonl").write_text('{"episode_index":0,"length":20,"tasks":["pick"]}\n{"episode_index":1,"length":30}\n')
        rows = import_lerobot(root, "lab/test", {"0": "train", "1": "val"})
        self.assertEqual([r.stop for r in rows], [20, 30])
        self.assertEqual(rows[1].source, "lab/test::1")
        self.assertEqual(audit(rows)["status"], "clear")
        self.assertEqual(self.command("import-lerobot", root, "--dataset-id", "lab/test", "-o", root / "export.jsonl")[0], 2)

    def test_unknown_version_fails(self):
        root = self.dataset("v9.0")
        self.assertEqual(self.command("import-lerobot", root, "--dataset-id", "lab/test", "-o", self.root / "export.jsonl")[0], 2)

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "optional pyarrow not installed")
    def test_v3_sharded_parquet_metadata(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        root = self.dataset("v3.0")
        directory = root / "meta" / "episodes" / "chunk-000"
        directory.mkdir(parents=True)
        for i in range(2):
            pq.write_table(pa.Table.from_pylist([{"episode_index": i, "length": 20 + i, "tasks": ["pick"]}]), directory / f"file-{i:03}.parquet")
        rows = import_lerobot(root, "lab/v3", {"0": "train", "1": "val"})
        self.assertEqual([r.stop for r in rows], [20, 21])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].task, "pick")


if __name__ == "__main__":
    unittest.main()
