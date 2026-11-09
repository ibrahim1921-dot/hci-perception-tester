"""
tests/make_fake_data.py - write ~20 made-up trials to a CSV so analysis.py can be tried
without running a real session.

    python tests/make_fake_data.py fake_results.csv
    python analysis.py fake_results.csv

The rows are written with the real DataLogger, so they have exactly the same format
as rows from the app.
"""

import random
import sys
from pathlib import Path

# Allow "python tests/make_fake_data.py" from the project folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config                                    # noqa: E402
from data_logger import DataLogger               # noqa: E402
from tasks.fitts_task import index_of_difficulty  # noqa: E402


def write_fake_data(csv_path, seed=1):
    rng = random.Random(seed)            # fixed seed -> same fake data every time
    logger = DataLogger(csv_path)
    rows = []

    # 9 Fitts trials: every distance x width once. Time roughly follows Fitts' Law.
    condition = {"contrast": "Medium", "size": "Medium", "brightness_pct": 80}
    for distance in config.FITTS_DISTANCES_PX:
        for width in config.FITTS_WIDTHS_PX:
            difficulty = index_of_difficulty(distance, width)
            rows.append(DataLogger.make_row(
                "FAKE01", config.TASK_TARGET_HITTING, condition,
                target_distance_px=distance, target_width_px=width,
                index_of_difficulty=difficulty,
                time_taken_s=0.25 + 0.15 * difficulty + rng.uniform(-0.05, 0.05),
                misses=rng.choice([0, 0, 0, 1]),
                ease_rating=4,
            ))

    # 11 identification trials under different conditions.
    conditions = [("High", "Large", 100), ("Medium", "Medium", 80), ("Low", "Small", 40)]
    for i in range(11):
        contrast, size, brightness = conditions[i % 3]
        figure = list(config.FIGURES)[i % 3]
        choices = config.FIGURES[figure]
        rows.append(DataLogger.make_row(
            "FAKE01", config.TASK_IDENTIFICATION,
            {"contrast": contrast, "size": size, "brightness_pct": brightness},
            stimulus=figure,
            response=rng.choice(choices[:3]) if i != 10 else "Other: a lamp",
            time_taken_s=rng.uniform(1.0, 4.0) + (1.5 if contrast == "Low" else 0),
            ease_rating=rng.randint(3, 5) if contrast != "Low" else rng.randint(1, 3),
        ))

    logger.write_rows(rows)
    return len(rows)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "fake_results.csv"
    count = write_fake_data(target)
    print(f"Wrote {count} fake rows to {target}")
