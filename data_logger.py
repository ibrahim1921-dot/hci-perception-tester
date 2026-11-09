"""
data_logger.py - appends every trial to a CSV file.

Rules it follows:
  * the header row is written only when the file is new (or empty);
  * the file is flushed after every row, so a crash loses nothing already saved;
  * columns that don't apply to a task are left empty - never the text "None".
"""

import csv
import os
from datetime import datetime
from pathlib import Path

import config


class DataLogger:
    def __init__(self, csv_path=config.CSV_PATH):
        self.csv_path = Path(csv_path)
        # Create the data folder at runtime if it doesn't exist yet.
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        # participant_id -> last trial number used. Loaded from the existing file
        # so numbering continues correctly if the app is restarted mid-session.
        self._last_trial = self._read_existing_trial_numbers()

    def _read_existing_trial_numbers(self) -> dict:
        last = {}
        if not self.csv_path.exists():
            return last
        with open(self.csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    number = int(row.get("trial_number") or 0)
                except ValueError:
                    continue
                pid = row.get("participant_id", "")
                last[pid] = max(last.get(pid, 0), number)
        return last

    def next_trial_number(self, participant_id: str) -> int:
        """The number the next saved trial for this participant will get."""
        return self._last_trial.get(participant_id, 0) + 1

    @staticmethod
    def make_row(participant_id, task_type, condition, **fields) -> dict:
        """Build a complete row (every column present) for one trial.

        `condition` comes from VisualSettings.get_condition(); `fields` holds the
        task-specific values (stimulus, response, time_taken_s, ...).
        The timestamp is taken now, i.e. when the trial finished.
        """
        if task_type not in (config.TASK_IDENTIFICATION, config.TASK_TARGET_HITTING):
            raise ValueError(f"Unknown task type: {task_type}")

        row = {column: "" for column in config.CSV_COLUMNS}   # start with all empty
        row["timestamp"] = datetime.now().isoformat(timespec="seconds")
        row["participant_id"] = participant_id
        row["task_type"] = task_type
        row.update(condition)
        row.update(fields)

        if row["time_taken_s"] != "":
            row["time_taken_s"] = round(float(row["time_taken_s"]), 3)

        # Replace None with "" so a missing value is an empty cell.
        return {key: ("" if value is None else value) for key, value in row.items()}

    def write_rows(self, rows) -> list:
        """Append rows to the CSV. Trial numbers are assigned here.

        Returns the list of trial numbers that were written.
        May raise OSError (e.g. PermissionError if the file is open in Excel);
        the caller shows the error to the experimenter.
        """
        is_new_file = not self.csv_path.exists() or self.csv_path.stat().st_size == 0
        written = []

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=config.CSV_COLUMNS)
            if is_new_file:
                writer.writeheader()
            for row in rows:
                row = dict(row)
                number = self.next_trial_number(row["participant_id"])
                row["trial_number"] = number
                writer.writerow(row)
                f.flush()                 # push Python's buffer to the OS ...
                os.fsync(f.fileno())      # ... and the OS buffer to the disk
                self._last_trial[row["participant_id"]] = number
                written.append(number)
        return written

    def write_row(self, row) -> int:
        """Append a single row; returns its trial number."""
        return self.write_rows([row])[0]
