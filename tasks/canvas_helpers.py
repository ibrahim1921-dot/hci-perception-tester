"""
tasks/canvas_helpers.py - drawing helpers shared by both tasks.

Everything drawn here uses the CURRENT visual condition (contrast, size,
brightness), because the test canvas is the part of the app being tested.
"""

import tkinter.font as tkfont

import config


def fixed_font(size_pt, bold=False):
    """A (family, size, weight) font tuple in the system's default sans-serif."""
    family = tkfont.nametofont("TkDefaultFont").actual("family")
    return (family, size_pt, "bold" if bold else "normal")


def canvas_font(settings, bold=False):
    """Font whose size follows the current Size condition (10 / 16 / 26 pt)."""
    return fixed_font(settings.font_size(), bold)


def clear_canvas(canvas, settings):
    """Remove everything and paint the background in the current colour."""
    canvas.delete("all")
    canvas.configure(bg=settings.background())


def draw_instruction(canvas, settings, text):
    """Draw instruction text centred at the top of the canvas.

    Returns the y coordinate just below the text, so the caller knows where
    the free drawing area starts.
    """
    width = canvas.winfo_width()
    item = canvas.create_text(
        width / 2, 16, text=text, anchor="n", justify="center",
        fill=settings.foreground(), font=canvas_font(settings),
        width=max(100, width - 40),           # wrap long text inside the canvas
    )
    bbox = canvas.bbox(item)                   # (x1, y1, x2, y2) of the text
    return bbox[3] + 10 if bbox else 50


def draw_idle_screen(canvas, settings):
    """Shown between tasks. It still uses the condition, so it doubles as a preview."""
    clear_canvas(canvas, settings)
    draw_instruction(canvas, settings, config.INSTRUCTION_IDLE)
