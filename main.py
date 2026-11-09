"""
main.py - entry point. Run with:  python main.py

Builds the main window:
    +------------------+--------------------------------------+
    | Control panel    | Test canvas (affected by conditions) |
    | (experimenter)   |                                      |
    |                  +--------------------------------------+
    |                  | Answer buttons (identification task) |
    +------------------+--------------------------------------+
    | Status bar: current condition · participant | last action |
    +---------------------------------------------------------+

The App class also offers a few shared "services" the tasks use:
    settings, participant_id, save_rows(), set_status(), task_finished()
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import config
from data_logger import DataLogger
from tasks.canvas_helpers import draw_idle_screen
from tasks.fitts_task import FittsTask
from tasks.identification_task import IdentificationTask
from ui import style
from ui.control_panel import ControlPanel
from visual_settings import VisualSettings


def screen_work_area(window):
    """Usable screen area without the taskbar, in real pixels: (left, top, right, bottom)."""
    if sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes
        rect = wintypes.RECT()
        SPI_GETWORKAREA = 0x0030
        ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
        return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, window.winfo_screenwidth(), window.winfo_screenheight()


class App(ctk.CTk):
    def __init__(self):
        # Light, neutral chrome. Set before the window is created.
        ctk.set_appearance_mode("light")
        super().__init__()
        self.title(config.APP_TITLE)
        self._fit_window_to_screen()

        self.settings = VisualSettings()
        self.logger = DataLogger(config.CSV_PATH)
        self.active_task = None          # the task that is running, or None

        # Grid: column 0 = fixed control panel, column 1 = test area (grows),
        # row 0 = main content (grows), row 1 = status bar.
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----- Left: experimenter control panel
        self.panel = ControlPanel(
            self, self.settings,
            on_condition_changed=self.condition_changed,
            on_participant_changed=self.update_status_bar,
            on_start_identification=self.start_identification,
            on_start_fitts=self.start_fitts,
            on_cancel=self.cancel_task,
            on_open_folder=self.open_results_folder,
        )
        self.panel.grid(row=0, column=0, sticky="ns")

        # ----- Right: test canvas + answer button row
        test_area = ctk.CTkFrame(self, fg_color="transparent")
        test_area.grid(row=0, column=1, sticky="nsew", padx=config.GROUP_PADDING,
                       pady=(config.GROUP_PADDING, 0))
        # A plain tkinter Canvas, so we draw in real screen pixels (important for Fitts).
        self.canvas = tk.Canvas(test_area, highlightthickness=1,
                                highlightbackground="#B5B5B5", cursor="arrow")
        self.canvas.pack(fill="both", expand=True)
        self.answer_frame = ctk.CTkFrame(test_area, fg_color="transparent", height=64)
        self.answer_frame.pack(fill="x")
        self.answer_frame.pack_propagate(False)       # keep a steady height

        # ----- Bottom: status bar (always visible, never affected by the conditions)
        status_bar = ctk.CTkFrame(self, fg_color=config.STATUS_BG_COLOR, corner_radius=0, height=32)
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(config.GROUP_PADDING, 0))
        self.condition_label = ctk.CTkLabel(status_bar, text="", font=style.control_font(),
                                            text_color=config.CHROME_TEXT_COLOR)
        self.condition_label.pack(side="left", padx=config.GROUP_PADDING)
        self.action_label = ctk.CTkLabel(status_bar, text="Ready", font=style.control_font(),
                                         text_color=config.CHROME_TEXT_COLOR)
        self.action_label.pack(side="right", padx=config.GROUP_PADDING)

        # ----- Tasks (they draw on the shared canvas)
        self.identification = IdentificationTask(self, self.canvas, self.answer_frame)
        self.fitts = FittsTask(self, self.canvas)

        # Redraw when the canvas changes size (e.g. window resized / first shown).
        self.canvas.bind("<Configure>", lambda _event: self.redraw_canvas())
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_status_bar()

    def _fit_window_to_screen(self):
        """Keep the whole window on screen, also with Windows display scaling.

        CustomTkinter multiplies window sizes by the display scaling, so at 150 %
        1180x760 becomes 1770x1140 real pixels: taller than a 1080p screen, and the
        status bar would end up behind the taskbar. So the start size (and, if needed,
        the minimum size) is reduced to the free screen area.
        The Fitts distances and widths are NOT affected: the canvas always draws in
        real screen pixels, so the logged px values stay true.
        """
        scaling = ctk.ScalingTracker.get_window_scaling(self)
        left, top, right, bottom = screen_work_area(self)        # real pixels
        free_width = (right - left) / scaling                    # in CustomTkinter units
        free_height = (bottom - top) / scaling - config.WINDOW_TITLE_BAR_ALLOWANCE

        width = int(min(config.WINDOW_START_WIDTH, free_width))
        height = int(min(config.WINDOW_START_HEIGHT, free_height))
        self.minsize(min(config.WINDOW_MIN_WIDTH, width), min(config.WINDOW_MIN_HEIGHT, height))
        # Width/height are scaled by CustomTkinter; the +x+y position is in real pixels.
        x = left + int((right - left) - width * scaling) // 2
        self.geometry(f"{width}x{height}+{x}+{top}")

    # ------------------------------------------------------------ shared services
    @property
    def participant_id(self):
        return self.panel.participant_id

    def set_status(self, text):
        """Show the last action on the right of the status bar."""
        self.action_label.configure(text=text)

    def update_status_bar(self):
        """Show the current condition, so nobody has to remember it (recognition over recall)."""
        participant = self.participant_id or "(none)"
        self.condition_label.configure(text=f"{self.settings.describe()} · Participant: {participant}")

    def save_rows(self, rows):
        """Write rows to the CSV. Returns their trial numbers, or [] if not saved.

        If the file can't be written (e.g. it's open in Excel), the experimenter
        can fix the problem and press Retry, so the data isn't lost (error recovery).
        """
        while True:
            try:
                return self.logger.write_rows(rows)
            except OSError as error:
                retry = messagebox.askretrycancel(
                    "Could not save",
                    f"The results file could not be written:\n{error}\n\n"
                    "If results.csv is open in another program, close it and press Retry.",
                    parent=self,
                )
                if not retry:
                    return []

    def task_finished(self, message):
        """Called by a task when it ends: unlock the controls and report what happened."""
        self.active_task = None
        self.panel.set_running(False)
        self.set_status(message)
        self.redraw_canvas()

    # --------------------------------------------------------------- handlers
    def condition_changed(self):
        self.update_status_bar()
        self.redraw_canvas()          # live preview of the new condition

    def redraw_canvas(self):
        if self.active_task is None:
            draw_idle_screen(self.canvas, self.settings)
        else:
            self.active_task.redraw()

    def _participant_ok(self):
        """A task may only start once a participant ID has been typed."""
        if not self.participant_id:
            self.panel.show_participant_error("Enter a participant ID first.")
            return False
        self.panel.show_participant_error("")
        return True

    def start_identification(self):
        if self.active_task is not None or not self._participant_ok():
            return
        self.active_task = self.identification
        self.panel.set_running(True)
        self.set_status(f"Identification trial running: {self.panel.selected_figure}")
        self.identification.start(self.panel.selected_figure)

    def start_fitts(self):
        if self.active_task is not None or not self._participant_ok():
            return
        self.active_task = self.fitts
        self.panel.set_running(True)
        self.fitts.start()

    def cancel_task(self):
        if self.active_task is not None:
            self.active_task.cancel()

    def open_results_folder(self):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        folder = str(config.DATA_DIR)
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)
        self.set_status(f"Opened {folder}")

    def on_close(self):
        # Closing in the middle of a Fitts block still saves the completed trials.
        self.cancel_task()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
