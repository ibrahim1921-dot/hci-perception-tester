"""
config.py - every constant used by the app, kept in one place.

Changing a value here (for example the number of repeats in a Fitts block)
changes it everywhere, so no "magic numbers" are hidden inside the other files.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Window and layout
# ---------------------------------------------------------------------------
APP_TITLE = "Human Perception & Performance Tester"
WINDOW_START_WIDTH = 1180
WINDOW_START_HEIGHT = 760
WINDOW_MIN_WIDTH = 1100          # wide enough for the furthest, largest Fitts target
WINDOW_MIN_HEIGHT = 720
# These sizes are multiplied by the Windows display scaling (125 %, 150 % ...).
# If the result doesn't fit the screen, main.py shrinks the window to fit.
# Room left above the window for its title bar (in unscaled px):
WINDOW_TITLE_BAR_ALLOWANCE = 40
CONTROL_PANEL_WIDTH = 260        # fixed experimenter panel on the left
GROUP_PADDING = 14               # space between groups of controls (12-16 px)

# ---------------------------------------------------------------------------
# "Chrome" styling (control panel + status bar).
# These colours never change with the experimental conditions, so the
# experimenter can always read and operate the app.
# ---------------------------------------------------------------------------
ACCENT_COLOR = "#2F6FB0"          # muted blue for primary buttons
ACCENT_HOVER_COLOR = "#285E96"
NEUTRAL_BUTTON_COLOR = "#6E6E6E"  # secondary buttons (Cancel, Open folder)
NEUTRAL_BUTTON_HOVER = "#5A5A5A"
DISABLED_BUTTON_COLOR = "#D0D0D0" # clearly greyed-out disabled buttons
DISABLED_TEXT_COLOR = "#8A8A8A"
PANEL_BG_COLOR = "#EBEBEB"
STATUS_BG_COLOR = "#DDDDDD"
CHROME_TEXT_COLOR = "#1E1E1E"
ERROR_TEXT_COLOR = "#B3261E"      # inline validation message

CONTROL_FONT_SIZE = 13            # normal control text
HEADER_FONT_SIZE = 15             # bold section headers
ANSWER_FONT_SIZE = 15             # participant answer buttons (large = easy to hit)

# ---------------------------------------------------------------------------
# Visual conditions (only applied to the test canvas)
# ---------------------------------------------------------------------------
# Contrast: foreground (text / shapes) drawn on background.
CONTRAST_MODES = {
    "High":   {"foreground": "#000000", "background": "#FFFFFF"},
    "Medium": {"foreground": "#4A4A4A", "background": "#BDBDBD"},
    "Low":    {"foreground": "#8C8C8C", "background": "#A6A6A6"},  # meant to be hard to see
}
DEFAULT_CONTRAST = "High"

# Size: font size (points) for canvas text, and a scale factor for figures.
SIZE_MODES = {
    "Small":  {"font_pt": 10, "shape_scale": 0.5},
    "Medium": {"font_pt": 16, "shape_scale": 1.0},
    "Large":  {"font_pt": 26, "shape_scale": 1.6},
}
DEFAULT_SIZE = "Medium"

# Brightness: percentage multiplied into the RGB values of the canvas colours.
BRIGHTNESS_MIN = 20
BRIGHTNESS_MAX = 100
BRIGHTNESS_DEFAULT = 100

# ---------------------------------------------------------------------------
# Identification task (ambiguous figures)
# ---------------------------------------------------------------------------
FIGURE_BASE_HEIGHT_PX = 280       # figure height at shape scale 1.0
FIGURE_LINE_WIDTH_PX = 3          # line width at shape scale 1.0

# Figure name -> the answer buttons shown for it.
# An extra "Other..." button is always added after these.
FIGURES = {
    "Rubin's vase": ["A vase", "Two faces", "Both", "Not sure"],
    "Necker cube": ["Cube seen from above", "Cube seen from below", "Both (it flips)", "Not sure"],
    "Schroeder staircase": ["Stairs going up", "Upside-down stairs", "Both (it flips)", "Not sure"],
}
DEFAULT_FIGURE = "Rubin's vase"
OTHER_CHOICE_LABEL = "Other…"

# ---------------------------------------------------------------------------
# Fitts' Law target-hitting task
# ---------------------------------------------------------------------------
FITTS_DISTANCES_PX = [150, 300, 550]   # centre of Start circle -> centre of target
FITTS_WIDTHS_PX = [24, 48, 90]         # target circle diameters
REPEATS_PER_COMBO = 2                  # 3 x 3 combos x 2 = 18 trials per block
START_CIRCLE_X_PX = 80                 # fixed x position of the Start circle
START_CIRCLE_DIAMETER_PX = 56
VERTICAL_JITTER_PX = 40                # target y = canvas middle +/- up to 40 px

# ---------------------------------------------------------------------------
# Instruction text drawn at the top of the canvas (uses the test colours/size)
# ---------------------------------------------------------------------------
INSTRUCTION_IDLE = "Waiting for the experimenter to start a task."
INSTRUCTION_IDENTIFICATION = "What do you see? Choose the answer below that fits best."
INSTRUCTION_FITTS = "Click the circle on the left, then click the target as fast as you can."

# ---------------------------------------------------------------------------
# Ease-of-use rating (1-5)
# ---------------------------------------------------------------------------
RATING_LABELS = {
    1: "Very difficult",
    2: "Difficult",
    3: "Neutral",
    4: "Easy",
    5: "Very easy",
}

# ---------------------------------------------------------------------------
# Data logging
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
CSV_PATH = DATA_DIR / "results.csv"

TASK_IDENTIFICATION = "Identification"
TASK_TARGET_HITTING = "Target Hitting"

# Column order of the CSV file (do not reorder: analysis.py relies on the names).
CSV_COLUMNS = [
    "timestamp",
    "participant_id",
    "trial_number",
    "task_type",
    "contrast",
    "size",
    "brightness_pct",
    "stimulus",
    "response",
    "target_distance_px",
    "target_width_px",
    "index_of_difficulty",
    "time_taken_s",
    "misses",
    "ease_rating",
]
