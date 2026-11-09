"""
ui/rating_dialog.py - the modal 1-5 "how easy was that?" prompt.

Usage:
    rating = ask_ease_rating(window, "How easy was that?")
    # rating is 1..5, or None if the dialog was closed without answering.

HCI notes:
  * Five large buttons (big targets are faster to hit - Fitts' Law applied to our own UI).
  * Every button shows its number AND its meaning, so nobody has to remember the scale
    (recognition rather than recall).
  * Keys 1-5 also work, for speed (flexibility and efficiency of use).
  * The dialog is modal, so the participant can't click the test area by accident.
"""

import customtkinter as ctk

import config
from ui import style


class RatingDialog(ctk.CTkToplevel):
    def __init__(self, master, question):
        super().__init__(master)
        self.rating = None                         # filled in when a button is chosen

        self.title("Ease of use")
        self.resizable(False, False)
        self.configure(fg_color=config.PANEL_BG_COLOR)
        self.transient(master)                     # stays on top of the main window
        self.protocol("WM_DELETE_WINDOW", lambda: self.choose(None))  # closing = no rating

        pad = config.GROUP_PADDING
        ctk.CTkLabel(self, text=question, font=style.header_font(),
                     text_color=config.CHROME_TEXT_COLOR).pack(padx=pad * 2, pady=(pad * 2, 4))
        ctk.CTkLabel(self, text="Click a button or press a key from 1 to 5.",
                     font=style.control_font(),
                     text_color=config.CHROME_TEXT_COLOR).pack(padx=pad * 2, pady=(0, pad))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(padx=pad * 2, pady=(0, pad * 2))
        for value, meaning in config.RATING_LABELS.items():
            button = style.primary_button(
                row, text=f"{value}\n{meaning}",
                command=lambda v=value: self.choose(v),
                width=120, height=72,
            )
            button.pack(side="left", padx=6)
            # Keyboard shortcut: pressing "3" is the same as clicking "3 Neutral".
            self.bind(str(value), lambda event, v=value: self.choose(v))

        # Make the dialog modal. The short delay is needed on Windows because a
        # CustomTkinter window can't grab input before it is actually visible.
        self.after(50, self._make_modal)

    def _make_modal(self):
        self._place_over_master()
        self.lift()
        self.focus_force()
        self.grab_set()

    def _place_over_master(self):
        """Centre the dialog over the main window."""
        self.update_idletasks()
        master = self.master
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
        # wm_geometry is plain tkinter positioning in real screen pixels.
        self.wm_geometry(f"+{max(0, x)}+{max(0, y)}")

    def choose(self, value):
        self.rating = value
        self.grab_release()
        self.destroy()


def ask_ease_rating(master, question="How easy was that?"):
    """Show the dialog, wait until it closes, and return the rating (or None)."""
    dialog = RatingDialog(master, question)
    master.wait_window(dialog)
    return dialog.rating
