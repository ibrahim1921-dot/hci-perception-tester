"""
tests/test_analysis.py - writes 20 fake rows to a temporary CSV and checks that
analysis.py prints its tables (and makes its charts, if matplotlib is installed)
without errors.
"""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis                          # noqa: E402
from make_fake_data import write_fake_data  # noqa: E402


class AnalysisTests(unittest.TestCase):
    def test_analysis_runs_on_fake_data(self):
        with tempfile.TemporaryDirectory() as folder:
            csv_path = Path(folder) / "results.csv"
            self.assertEqual(write_fake_data(csv_path), 20)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = analysis.main([str(csv_path)])
            text = output.getvalue()

            self.assertEqual(exit_code, 0)
            self.assertIn("Read 20 trials", text)
            self.assertIn("Grouped by target width", text)
            self.assertIn("Grouped by target distance", text)
            self.assertIn("Width x distance grid", text)
            self.assertIn("Response counts per contrast", text)
            self.assertIn("Response counts per size", text)
            self.assertIn("Mean ease rating per condition", text)

            try:
                import matplotlib  # noqa: F401
            except ImportError:
                self.assertIn("matplotlib is not installed", text)
            else:
                for name in ("time_vs_width.png", "time_vs_distance.png", "time_vs_id.png"):
                    self.assertTrue((Path(folder) / name).exists(), name)

    def test_missing_file_is_reported_not_crashed(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = analysis.main(["does_not_exist.csv"])
        self.assertEqual(exit_code, 1)
        self.assertIn("No results file found", output.getvalue())


if __name__ == "__main__":
    unittest.main()
