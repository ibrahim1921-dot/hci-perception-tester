"""
tests/test_core.py - unit tests for the non-GUI logic. No window is opened.

Run from the project folder:
    python -m unittest discover -s tests -v
"""

import csv
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config                                                   # noqa: E402
from data_logger import DataLogger                              # noqa: E402
from tasks.fitts_task import index_of_difficulty, make_block    # noqa: E402
from visual_settings import VisualSettings, apply_brightness    # noqa: E402


class ApplyBrightnessTests(unittest.TestCase):
    def test_100_percent_leaves_colour_unchanged(self):
        for colour in ("#000000", "#FFFFFF", "#4A4A4A", "#BDBDBD", "#8C8C8C", "#A6A6A6"):
            self.assertEqual(apply_brightness(colour, 100), colour)

    def test_50_percent_halves_each_channel(self):
        self.assertEqual(apply_brightness("#FFFFFF", 50), "#808080")   # 255 / 2 = 127.5 -> 128
        self.assertEqual(apply_brightness("#BDBDBD", 50), "#5F5F5F")   # 189 / 2 = 94.5 -> 95
        self.assertEqual(apply_brightness("#204060", 50), "#102030")   # each channel exactly halved

    def test_never_below_zero(self):
        self.assertEqual(apply_brightness("#000000", 20), "#000000")
        self.assertEqual(apply_brightness("#FFFFFF", 0), "#000000")
        self.assertEqual(apply_brightness("#FFFFFF", -50), "#000000")  # clamped

    def test_never_above_original(self):
        self.assertEqual(apply_brightness("#A6A6A6", 150), "#A6A6A6")  # clamped to 100 %

    def test_accepts_lowercase_and_rejects_bad_input(self):
        self.assertEqual(apply_brightness("#ffffff", 100), "#FFFFFF")
        with self.assertRaises(ValueError):
            apply_brightness("#FFF", 50)


class VisualSettingsTests(unittest.TestCase):
    def test_contrast_lookup(self):
        s = VisualSettings()
        s.set_contrast("Low")
        self.assertEqual(s.foreground(), "#8C8C8C")
        self.assertEqual(s.background(), "#A6A6A6")
        s.set_contrast("Medium")
        self.assertEqual(s.foreground(), "#4A4A4A")
        self.assertEqual(s.background(), "#BDBDBD")

    def test_size_lookup(self):
        s = VisualSettings()
        expected = {"Small": (10, 0.5), "Medium": (16, 1.0), "Large": (26, 1.6)}
        for mode, (font, scale) in expected.items():
            s.set_size(mode)
            self.assertEqual(s.font_size(), font)
            self.assertEqual(s.shape_scale(), scale)

    def test_brightness_applies_to_both_colours(self):
        s = VisualSettings()             # High contrast: black on white
        s.set_brightness(50)
        self.assertEqual(s.foreground(), "#000000")
        self.assertEqual(s.background(), "#808080")

    def test_brightness_clamped_to_slider_range(self):
        s = VisualSettings()
        s.set_brightness(5)
        self.assertEqual(s.brightness, config.BRIGHTNESS_MIN)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            VisualSettings().set_contrast("Extreme")

    def test_get_condition(self):
        s = VisualSettings()
        s.set_contrast("Low")
        s.set_size("Small")
        s.set_brightness(60)
        self.assertEqual(s.get_condition(),
                         {"contrast": "Low", "size": "Small", "brightness_pct": 60})


class FittsTests(unittest.TestCase):
    def test_index_of_difficulty(self):
        self.assertEqual(index_of_difficulty(150, 50), 2.0)       # log2(3 + 1)
        self.assertEqual(index_of_difficulty(48, 48), 1.0)        # log2(1 + 1)
        self.assertEqual(index_of_difficulty(550, 24), 4.58)      # log2(23.917) = 4.5799...

    def test_block_contains_every_combination_repeated(self):
        block = make_block([150, 300, 550], [24, 48, 90], 2, rng=random.Random(0))
        self.assertEqual(len(block), 18)
        for d in (150, 300, 550):
            for w in (24, 48, 90):
                self.assertEqual(block.count((d, w)), 2)


class DataLoggerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        # A sub-folder that doesn't exist yet: the logger must create it.
        self.csv_path = Path(self.temp_dir.name) / "data" / "results.csv"

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_lines(self):
        with open(self.csv_path, newline="", encoding="utf-8") as f:
            return list(csv.reader(f))

    def identification_row(self):
        return DataLogger.make_row(
            "P01", config.TASK_IDENTIFICATION,
            {"contrast": "High", "size": "Medium", "brightness_pct": 100},
            stimulus="Necker cube", response="Cube seen from above",
            time_taken_s=1.23456, ease_rating=None,
        )

    def test_header_written_once_and_rows_appended(self):
        logger = DataLogger(self.csv_path)
        logger.write_row(self.identification_row())
        logger.write_row(self.identification_row())
        # A new logger on the same file (= app restarted) must not add a second header.
        DataLogger(self.csv_path).write_row(self.identification_row())

        lines = self.read_lines()
        self.assertEqual(lines[0], config.CSV_COLUMNS)
        self.assertEqual(len(lines), 4)                      # header + 3 rows
        self.assertEqual(sum(1 for line in lines if line == config.CSV_COLUMNS), 1)

    def test_trial_numbers_continue_after_restart(self):
        DataLogger(self.csv_path).write_rows([self.identification_row()] * 2)
        number = DataLogger(self.csv_path).write_row(self.identification_row())
        self.assertEqual(number, 3)

    def test_non_applicable_fields_are_empty_not_none(self):
        DataLogger(self.csv_path).write_row(self.identification_row())
        with open(self.csv_path, newline="", encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        for column in ("target_distance_px", "target_width_px", "index_of_difficulty",
                       "misses", "ease_rating"):
            self.assertEqual(row[column], "", column)
        self.assertNotIn("None", self.csv_path.read_text(encoding="utf-8"))
        self.assertEqual(row["time_taken_s"], "1.235")       # rounded to 3 decimals
        self.assertEqual(row["task_type"], "Identification")
        self.assertEqual(row["trial_number"], "1")

    def test_target_hitting_row(self):
        row = DataLogger.make_row(
            "P01", config.TASK_TARGET_HITTING,
            {"contrast": "Low", "size": "Small", "brightness_pct": 40},
            target_distance_px=300, target_width_px=48,
            index_of_difficulty=index_of_difficulty(300, 48),
            time_taken_s=0.5, misses=1, ease_rating=4,
        )
        DataLogger(self.csv_path).write_row(row)
        with open(self.csv_path, newline="", encoding="utf-8") as f:
            saved = next(csv.DictReader(f))
        self.assertEqual(saved["task_type"], "Target Hitting")
        self.assertEqual(saved["stimulus"], "")
        self.assertEqual(saved["response"], "")
        self.assertEqual(saved["index_of_difficulty"], "2.858")

    def test_unknown_task_type_rejected(self):
        with self.assertRaises(ValueError):
            DataLogger.make_row("P01", "Typing", {})


if __name__ == "__main__":
    unittest.main()
