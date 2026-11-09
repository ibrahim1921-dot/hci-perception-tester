"""
ui/style.py - small helpers so every button and label in the "chrome"
(control panel, status bar, dialogs) looks the same.

Consistency is an HCI principle: the same kind of control always looks and
behaves the same way, so the experimenter learns it once.
"""

import customtkinter as ctk

import config


def control_font():
    """13 pt system sans for normal controls."""
    return ctk.CTkFont(size=config.CONTROL_FONT_SIZE)


def header_font():
    """15 pt bold for section headers ("Participant", "Visual conditions", "Tasks")."""
    return ctk.CTkFont(size=config.HEADER_FONT_SIZE, weight="bold")


def _make_button(master, text, command, color, hover_color, **kwargs):
    button = ctk.CTkButton(
        master,
        text=text,
        command=command,
        font=kwargs.pop("font", control_font()),
        fg_color=color,
        hover_color=hover_color,
        text_color="#FFFFFF",
        text_color_disabled=config.DISABLED_TEXT_COLOR,
        corner_radius=6,
        **kwargs,
    )
    # Remember the normal colour so set_enabled() can restore it.
    button.normal_color = color
    return button


def primary_button(master, text, command, **kwargs):
    """Main actions (start a task) use the single accent colour."""
    return _make_button(master, text, command, config.ACCENT_COLOR, config.ACCENT_HOVER_COLOR, **kwargs)


def secondary_button(master, text, command, **kwargs):
    """Less important actions (Cancel, Open folder) use neutral grey."""
    return _make_button(master, text, command, config.NEUTRAL_BUTTON_COLOR, config.NEUTRAL_BUTTON_HOVER, **kwargs)


def set_enabled(button, enabled: bool):
    """Enable/disable a button made above. Disabled buttons are clearly greyed out."""
    if enabled:
        button.configure(state="normal", fg_color=button.normal_color)
    else:
        button.configure(state="disabled", fg_color=config.DISABLED_BUTTON_COLOR)
