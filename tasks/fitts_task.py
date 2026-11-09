"""
tasks/fitts_task.py - the Fitts' Law target-hitting task.

One trial:
    1. a ring labelled "Start" appears on the left-middle of the canvas
    2. the participant clicks it -> the timer starts and the target appears
       D pixels to the right (with a small random up/down jitter)
    3. clicks that miss the target add 1 to `misses`
    4. clicking the target stops the timer

A block = every distance x width combination, REPEATS_PER_COMBO times each,
in random order (3 x 3 x 2 = 18 trials by default).

After the block ONE ease rating is asked and written into every row of the
block, so the rows are kept in memory until then. If the block is cancelled,
the trials completed so far are still written (with an empty ease rating).
"""

import math
import random
import time

import config
from data_logger import DataLogger
from tasks.canvas_helpers import clear_canvas, draw_instruction, fixed_font
from ui.rating_dialog import ask_ease_rating


def index_of_difficulty(distance, width):
    """Fitts' index of difficulty in bits: ID = log2(D / W + 1), rounded to 3 decimals."""
    return round(math.log2(distance / width + 1), 3)


def make_block(distances, widths, repeats, rng=random):
    """Every (distance, width) pair `repeats` times, shuffled into random order."""
    trials = [(d, w) for d in distances for w in widths] * repeats
    rng.shuffle(trials)
    return trials


def _inside_circle(x, y, cx, cy, diameter):
    """True if the point (x, y) lies inside the circle centred at (cx, cy)."""
    return (x - cx) ** 2 + (y - cy) ** 2 <= (diameter / 2) ** 2


class FittsTask:
    # The task is always in one of these states:
    IDLE = "idle"                  # no block running
    WAITING = "waiting_for_start"  # Start circle shown, timer not running
    MOVING = "moving"              # target shown, timer running
    RATING = "rating"              # block finished, rating dialog open

    def __init__(self, app, canvas):
        self.app = app
        self.canvas = canvas
        self.state = self.IDLE
        self.trials = []          # list of (distance, width) for this block
        self.index = 0            # which trial we are on (0-based)
        self.rows = []            # finished trials, waiting for the block rating
        self.condition = None
        self.start_y = 0
        self.target_x = self.target_y = 0
        self.misses = 0
        self.start_time = None

    # ------------------------------------------------------------ block flow
    def start(self):
        self.trials = make_block(config.FITTS_DISTANCES_PX, config.FITTS_WIDTHS_PX,
                                 config.REPEATS_PER_COMBO)
        self.index = 0
        self.rows = []
        self.condition = self.app.settings.get_condition()   # same for the whole block
        self.canvas.bind("<Button-1>", self.on_click)
        self._show_start_circle()

    def _show_start_circle(self):
        self.state = self.WAITING
        self.start_y = self.canvas.winfo_height() / 2        # vertically centred
        self.app.set_status(f"Fitts block running: trial {self.index + 1} of {len(self.trials)}")
        self.redraw()

    def on_click(self, event):
        if self.state == self.WAITING:
            # Only a click on the Start circle starts the trial; other clicks are ignored.
            if _inside_circle(event.x, event.y, config.START_CIRCLE_X_PX, self.start_y,
                              config.START_CIRCLE_DIAMETER_PX):
                self._begin_trial()

        elif self.state == self.MOVING:
            distance, width = self.trials[self.index]
            if _inside_circle(event.x, event.y, self.target_x, self.target_y, width):
                self._finish_trial()
            else:
                self.misses += 1        # any canvas click that isn't on the target

    def _begin_trial(self):
        distance, _width = self.trials[self.index]
        self.misses = 0
        self.target_x = config.START_CIRCLE_X_PX + distance
        jitter = random.randint(-config.VERTICAL_JITTER_PX, config.VERTICAL_JITTER_PX)
        self.target_y = self.start_y + jitter
        self.state = self.MOVING
        self.start_time = time.perf_counter()      # timer starts on the Start click
        self.redraw()

    def _finish_trial(self):
        elapsed = time.perf_counter() - self.start_time
        distance, width = self.trials[self.index]
        self.rows.append(DataLogger.make_row(
            self.app.participant_id, config.TASK_TARGET_HITTING, self.condition,
            target_distance_px=distance,
            target_width_px=width,
            index_of_difficulty=index_of_difficulty(distance, width),
            time_taken_s=elapsed,
            misses=self.misses,
        ))
        self.index += 1
        if self.index < len(self.trials):
            self._show_start_circle()
        else:
            self._finish_block()

    def _finish_block(self):
        self.state = self.RATING
        self.canvas.unbind("<Button-1>")
        self.redraw()
        rating = ask_ease_rating(self.app, "How easy was this block of targets?")
        for row in self.rows:
            row["ease_rating"] = "" if rating is None else rating
        self._save_and_stop("Saved trials")

    def cancel(self):
        """Stop the block early. Completed trials are still saved (no ease rating)."""
        if self.state == self.RATING:
            return
        self.canvas.unbind("<Button-1>")
        self._save_and_stop("Block cancelled - saved completed trials")

    def _save_and_stop(self, message):
        self.state = self.IDLE
        numbers = self.app.save_rows(self.rows) if self.rows else []
        if numbers:
            message += f" {numbers[0]}" if len(numbers) == 1 else f" {numbers[0]}–{numbers[-1]}"
        elif self.rows:
            message = "Fitts trials NOT saved"
        else:
            message = "Block cancelled - no completed trials to save"
        self.rows = []
        self.app.task_finished(message)

    # --------------------------------------------------------------- drawing
    def redraw(self):
        settings = self.app.settings
        fg = settings.foreground()
        clear_canvas(self.canvas, settings)
        top = draw_instruction(self.canvas, settings, config.INSTRUCTION_FITTS)

        # Progress, e.g. "Trial 4 of 18" (visibility of system status).
        shown = min(self.index + 1, len(self.trials))
        self.canvas.create_text(self.canvas.winfo_width() / 2, top, anchor="n",
                                text=f"Trial {shown} of {len(self.trials)}",
                                fill=fg, font=fixed_font(11))

        if self.state == self.WAITING:
            # Start circle: an outlined ring with a small "Start" label.
            r = config.START_CIRCLE_DIAMETER_PX / 2
            x, y = config.START_CIRCLE_X_PX, self.start_y
            self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=fg, width=3)
            self.canvas.create_text(x, y, text="Start", fill=fg, font=fixed_font(10, bold=True))

        elif self.state == self.MOVING:
            # Target: a filled circle whose diameter is the target width W.
            _distance, width = self.trials[self.index]
            r = width / 2
            x, y = self.target_x, self.target_y
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=fg, outline=fg)
