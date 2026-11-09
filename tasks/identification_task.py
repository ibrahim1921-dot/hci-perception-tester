"""
tasks/identification_task.py - the ambiguous-figure identification task.

One trial:
    1. the figure is drawn and the timer starts (time.perf_counter)
    2. the participant clicks the answer that matches what they see
    3. the timer stops, the 1-5 ease rating is asked
    4. the row is written to the CSV

The figures are drawn with canvas shapes (no image files), so they grow and
shrink with the Size setting and recolour with the Contrast/Brightness settings.

How the figures are described:
    Each figure is designed on paper in "design units", centred on (0, 0)
    and about 360 units tall. `_to_canvas` converts design units to pixels:
        pixel = centre + design_value * (figure_height_px / 360)
"""

import time

import customtkinter as ctk

import config
from data_logger import DataLogger
from tasks.canvas_helpers import clear_canvas, draw_instruction
from ui import style
from ui.rating_dialog import ask_ease_rating

DESIGN_HEIGHT = 360   # every figure below is designed about 360 units tall


def _to_canvas(points, cx, cy, k):
    """[(x, y), ...] in design units -> flat [x1, y1, x2, y2, ...] in pixels."""
    flat = []
    for x, y in points:
        flat.extend([cx + x * k, cy + y * k])
    return flat


# ---------------------------------------------------------------------------
# Figure 1: Rubin's vase - a vase, or two faces looking at each other.
# ---------------------------------------------------------------------------
# Right-hand edge of the vase, from top to bottom, as (x, y).
# Where the edge comes IN towards the middle, the right-hand face sticks OUT
# (forehead, nose, lips, chin). The left edge is the mirror image.
VASE_RIGHT_EDGE = [
    (100, -180), (100, -180), (100, -165), (100, -165),   # rim (points doubled = sharp corner)
    (78, -158), (62, -140),                                # under the rim / top of forehead
    (48, -105), (44, -80),                                 # forehead, brow
    (56, -68), (52, -55),                                  # eye socket
    (20, -25), (26, -15),                                  # nose tip
    (38, -8), (32, 2), (38, 8), (33, 14),                  # under nose, upper lip, mouth, lower lip
    (44, 24), (34, 42),                                    # below the lip, chin
    (60, 62), (88, 95), (80, 125),                         # neck -> body of the vase
    (45, 145), (40, 160),                                  # stem
    (85, 168), (85, 168), (85, 180), (85, 180),            # foot (doubled = sharp corner)
]
VASE_FRAME_HALF_WIDTH = 130   # the faces are the background between vase and frame


def draw_rubin_vase(canvas, cx, cy, k, fg, bg, line_width):
    right = VASE_RIGHT_EDGE
    left = [(-x, y) for x, y in reversed(right)]          # mirror image
    outline = right + left                                 # go down the right, up the left

    # Frame: its inside is background colour = the two faces.
    w = VASE_FRAME_HALF_WIDTH
    frame = _to_canvas([(-w, -180), (w, 180)], cx, cy, k)
    canvas.create_rectangle(*frame, outline=fg, fill=bg, width=line_width)

    # Vase: a filled, smoothed polygon in the foreground colour.
    canvas.create_polygon(_to_canvas(outline, cx, cy, k), fill=fg, outline=fg, smooth=True)


# ---------------------------------------------------------------------------
# Figure 2: Necker cube - seen from above, or from below.
# ---------------------------------------------------------------------------
CUBE_SIDE = 200     # side of each square
CUBE_OFFSET = 90    # how far the back square is shifted up and to the right


def draw_necker_cube(canvas, cx, cy, k, fg, bg, line_width):
    s, o = CUBE_SIDE, CUBE_OFFSET
    left, bottom = -(s + o) / 2, (s + o) / 2            # centre the whole cube on (0, 0)

    # Corners of the front square, then the same corners shifted for the back square.
    front = [(left, bottom - s), (left + s, bottom - s), (left + s, bottom), (left, bottom)]
    back = [(x + o, y - o) for x, y in front]

    edges = []
    for i in range(4):
        j = (i + 1) % 4
        edges.append((front[i], front[j]))   # 4 edges of the front square
        edges.append((back[i], back[j]))     # 4 edges of the back square
        edges.append((front[i], back[i]))    # 4 edges joining front to back

    # Plain line segments only: no hidden lines, so the depth is ambiguous.
    for start, end in edges:
        canvas.create_line(_to_canvas([start, end], cx, cy, k),
                           fill=fg, width=line_width, capstyle="round")


# ---------------------------------------------------------------------------
# Figure 3: Schroeder staircase - stairs going up, or the same stairs seen
# upside down from below (an overhang).
# ---------------------------------------------------------------------------
STAIR_STEPS = 5
STAIR_STEP_SIZE = 46          # height and depth of one step
STAIR_DEPTH = (-80, -55)      # direction of the "into the page" edges


def staircase_profile():
    """Zig-zag edge of the stairs from bottom-left to top-right, in design units."""
    a = STAIR_STEP_SIZE
    total = STAIR_STEPS * a
    x, y = -total / 2, total / 2              # start bottom-left so the stairs are centred
    points = [(x, y)]
    for _ in range(STAIR_STEPS):
        y -= a
        points.append((x, y))                 # riser: go up
        x += a
        points.append((x, y))                 # tread: go right
    return points


def draw_schroeder_staircase(canvas, cx, cy, k, fg, bg, line_width):
    front = staircase_profile()
    dx, dy = STAIR_DEPTH
    # Shift the whole figure so the front and back edges together are centred.
    front = [(x - dx / 2, y - dy / 2) for x, y in front]
    back = [(x + dx, y + dy) for x, y in front]

    def line(points):
        canvas.create_line(_to_canvas(points, cx, cy, k), fill=fg, width=line_width,
                           capstyle="round", joinstyle="round")

    line(front)                                # front zig-zag edge
    line(back)                                 # back zig-zag edge
    for f, b in zip(front, back):              # the edge of every step, front -> back
        line([f, b])
    # Close the side face: down from the top step, along the floor, back to the start.
    bottom_right = (front[-1][0], front[0][1])
    line([front[-1], bottom_right, front[0]])
    line([bottom_right, (bottom_right[0] + dx, bottom_right[1] + dy), back[-1]])


# Figure name (as in config.FIGURES) -> drawing function.
FIGURE_DRAWERS = {
    "Rubin's vase": draw_rubin_vase,
    "Necker cube": draw_necker_cube,
    "Schroeder staircase": draw_schroeder_staircase,
}


# ---------------------------------------------------------------------------
# The task itself
# ---------------------------------------------------------------------------
class IdentificationTask:
    def __init__(self, app, canvas, answer_frame):
        self.app = app                    # main window: settings, saving, status bar
        self.canvas = canvas
        self.answer_frame = answer_frame  # row under the canvas where answer buttons go
        self.answer_buttons = []
        self.figure_name = None
        self.condition = None
        self.start_time = None
        self.running = False
        self._show_answer_placeholder()

    # ----------------------------------------------------------- trial flow
    def start(self, figure_name):
        self.figure_name = figure_name
        self.condition = self.app.settings.get_condition()   # condition for this trial
        self._build_answer_buttons(config.FIGURES[figure_name])
        self.redraw()
        self.canvas.update_idletasks()       # make sure the figure is on screen ...
        self.running = True
        self.start_time = time.perf_counter()  # ... before the timer starts

    def redraw(self):
        """Draw instruction + figure with the current colours and size."""
        settings = self.app.settings
        clear_canvas(self.canvas, settings)
        top = draw_instruction(self.canvas, settings, config.INSTRUCTION_IDENTIFICATION)

        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        figure_height = config.FIGURE_BASE_HEIGHT_PX * settings.shape_scale()
        # Safety net for very small windows: never draw outside the canvas.
        figure_height = min(figure_height, height - top - 10)
        k = figure_height / DESIGN_HEIGHT                 # design units -> pixels
        cx, cy = width / 2, (top + height) / 2
        line_width = max(1, round(config.FIGURE_LINE_WIDTH_PX * settings.shape_scale()))

        draw = FIGURE_DRAWERS[self.figure_name]
        draw(self.canvas, cx, cy, k, settings.foreground(), settings.background(), line_width)

    def on_answer(self, choice):
        if not self.running:
            return
        elapsed = time.perf_counter() - self.start_time   # time to the decision click

        if choice == config.OTHER_CHOICE_LABEL:
            dialog = ctk.CTkInputDialog(title="Other answer", text="Describe what you see:")
            typed = dialog.get_input()
            if typed is None:          # dialog cancelled: the trial simply carries on
                return
            response = "Other: " + (typed.strip() or "(blank)")
        else:
            response = choice

        self.running = False
        self._set_answers_enabled(False)
        rating = ask_ease_rating(self.app, "How easy was it to see the figure?")

        row = DataLogger.make_row(
            self.app.participant_id, config.TASK_IDENTIFICATION, self.condition,
            stimulus=self.figure_name,
            response=response,
            time_taken_s=elapsed,
            ease_rating=rating,          # None (closed without rating) becomes empty
        )
        numbers = self.app.save_rows([row])
        self._show_answer_placeholder()
        message = f"Saved trial {numbers[0]}" if numbers else "Trial NOT saved"
        self.app.task_finished(message)

    def cancel(self):
        """Stop an unfinished trial. Nothing is saved because there is no answer."""
        self.running = False
        self._show_answer_placeholder()
        self.app.task_finished("Identification trial cancelled (not saved)")

    # ------------------------------------------------------- answer buttons
    def _clear_answer_frame(self):
        for widget in self.answer_frame.winfo_children():
            widget.destroy()
        self.answer_buttons = []

    def _show_answer_placeholder(self):
        self._clear_answer_frame()
        ctk.CTkLabel(self.answer_frame, text="Answer buttons appear here during an identification trial.",
                     font=style.control_font(), text_color=config.DISABLED_TEXT_COLOR).pack(expand=True)

    def _build_answer_buttons(self, choices):
        self._clear_answer_frame()
        for choice in list(choices) + [config.OTHER_CHOICE_LABEL]:
            button = style.primary_button(
                self.answer_frame, choice, lambda c=choice: self.on_answer(c),
                font=ctk.CTkFont(size=config.ANSWER_FONT_SIZE), height=48,
            )
            # Large buttons spread over the full width: easy to hit, hard to miss.
            button.pack(side="left", expand=True, fill="x", padx=6, pady=8)
            self.answer_buttons.append(button)

    def _set_answers_enabled(self, enabled):
        for button in self.answer_buttons:
            style.set_enabled(button, enabled)
