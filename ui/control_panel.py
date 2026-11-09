"""
ui/control_panel.py - the experimenter's panel on the left of the window.

It contains:
  Participant        - ID entry (+ inline error message if it's empty)
  Visual conditions  - contrast, size, brightness
  Tasks              - figure choice, Start Identification Trial, Start Fitts Block, Cancel
  Open results folder

The panel itself doesn't run tasks. It calls the functions ("callbacks") it was given
by main.py, which keeps this file purely about layout and input.

HCI decision: this panel is NOT affected by the contrast/size/brightness
conditions. It keeps the same readable styling all the time, so the
experimenter can always operate the app, even in the "Low" condition.
"""

import customtkinter as ctk

import config
from ui import style


class ControlPanel(ctk.CTkFrame):
    def __init__(self, master, settings, on_condition_changed, on_participant_changed,
                 on_start_identification, on_start_fitts, on_cancel, on_open_folder):
        super().__init__(master, width=config.CONTROL_PANEL_WIDTH,
                         fg_color=config.PANEL_BG_COLOR, corner_radius=0)
        self.settings = settings
        self.on_condition_changed = on_condition_changed
        self.on_participant_changed = on_participant_changed

        pad = config.GROUP_PADDING
        inner_width = config.CONTROL_PANEL_WIDTH - 2 * pad

        # ------------------------------------------------------------ Participant
        self._header("Participant", top=pad)
        self.participant_entry = ctk.CTkEntry(self, placeholder_text="e.g. P01",
                                              font=style.control_font(), width=inner_width)
        self.participant_entry.pack(padx=pad, anchor="w")
        self.participant_entry.bind("<KeyRelease>", self._participant_typed)

        # Inline message (instead of a popup) when the ID is missing.
        self.participant_error = ctk.CTkLabel(self, text="", font=style.control_font(),
                                              text_color=config.ERROR_TEXT_COLOR,
                                              wraplength=inner_width, justify="left", height=18)
        self.participant_error.pack(padx=pad, anchor="w")

        # ------------------------------------------------------- Visual conditions
        self._header("Visual conditions")

        self._label("Contrast")
        self.contrast_buttons = self._segmented(list(config.CONTRAST_MODES),
                                                settings.contrast, self._contrast_chosen)

        self._label("Size")
        self.size_buttons = self._segmented(list(config.SIZE_MODES),
                                            settings.size, self._size_chosen)

        # Brightness label shows the live value, e.g. "Brightness: 60%".
        self.brightness_label = self._label(f"Brightness: {settings.brightness}%")
        self.brightness_slider = ctk.CTkSlider(
            self,
            from_=config.BRIGHTNESS_MIN,
            to=config.BRIGHTNESS_MAX,
            number_of_steps=config.BRIGHTNESS_MAX - config.BRIGHTNESS_MIN,  # 1 % steps
            command=self._brightness_moved,
            width=inner_width,
            button_color=config.ACCENT_COLOR,
            button_hover_color=config.ACCENT_HOVER_COLOR,
            progress_color=config.ACCENT_COLOR,
        )
        self.brightness_slider.set(settings.brightness)
        self.brightness_slider.pack(padx=pad, pady=(2, 0), anchor="w")

        # ------------------------------------------------------------------ Tasks
        self._header("Tasks")

        self._label("Figure for identification")
        self.figure_menu = ctk.CTkOptionMenu(
            self, values=list(config.FIGURES), font=style.control_font(),
            dropdown_font=style.control_font(), width=inner_width,
            fg_color=config.NEUTRAL_BUTTON_COLOR, button_color=config.NEUTRAL_BUTTON_COLOR,
            button_hover_color=config.NEUTRAL_BUTTON_HOVER,
        )
        self.figure_menu.set(config.DEFAULT_FIGURE)
        self.figure_menu.pack(padx=pad, pady=(2, 8), anchor="w")

        self.start_identification_button = style.primary_button(
            self, "Start Identification Trial", on_start_identification, width=inner_width)
        self.start_identification_button.pack(padx=pad, pady=(0, 8), anchor="w")

        self.start_fitts_button = style.primary_button(
            self, "Start Fitts Block", on_start_fitts, width=inner_width)
        self.start_fitts_button.pack(padx=pad, pady=(0, 8), anchor="w")

        self.cancel_button = style.secondary_button(self, "Cancel", on_cancel, width=inner_width)
        self.cancel_button.pack(padx=pad, anchor="w")
        style.set_enabled(self.cancel_button, False)    # nothing to cancel yet

        # ------------------------------------------------------- Results folder
        self.open_folder_button = style.secondary_button(
            self, "Open results folder", on_open_folder, width=inner_width)
        # Packed straight under Cancel (not at the very bottom), so it stays visible
        # when display scaling makes the window short.
        self.open_folder_button.pack(padx=pad, pady=(pad, 0), anchor="w")

        # Keep the panel at its fixed width instead of shrinking to its contents.
        self.pack_propagate(False)

    # ----------------------------------------------------------- layout helpers
    def _header(self, text, top=None):
        top = config.GROUP_PADDING if top is None else top     # 14 px between groups
        ctk.CTkLabel(self, text=text, font=style.header_font(),
                     text_color=config.CHROME_TEXT_COLOR).pack(padx=config.GROUP_PADDING,
                                                              pady=(top, 6), anchor="w")

    def _label(self, text):
        label = ctk.CTkLabel(self, text=text, font=style.control_font(),
                             text_color=config.CHROME_TEXT_COLOR)
        label.pack(padx=config.GROUP_PADDING, pady=(4, 0), anchor="w")
        return label

    def _segmented(self, values, current, command):
        buttons = ctk.CTkSegmentedButton(
            self, values=values, command=command, font=style.control_font(),
            width=config.CONTROL_PANEL_WIDTH - 2 * config.GROUP_PADDING,
            selected_color=config.ACCENT_COLOR,
            selected_hover_color=config.ACCENT_HOVER_COLOR,
        )
        buttons.set(current)
        buttons.pack(padx=config.GROUP_PADDING, pady=(2, 4), anchor="w")
        return buttons

    # ---------------------------------------------------------- input handlers
    def _contrast_chosen(self, value):
        self.settings.set_contrast(value)
        self.on_condition_changed()

    def _size_chosen(self, value):
        self.settings.set_size(value)
        self.on_condition_changed()

    def _brightness_moved(self, value):
        self.settings.set_brightness(value)
        self.brightness_label.configure(text=f"Brightness: {self.settings.brightness}%")
        self.on_condition_changed()

    def _participant_typed(self, _event):
        if self.participant_id:
            self.show_participant_error("")       # clear the message once an ID is typed
        self.on_participant_changed()

    # ---------------------------------------------------- used by main.py
    @property
    def participant_id(self) -> str:
        return self.participant_entry.get().strip()

    @property
    def selected_figure(self) -> str:
        return self.figure_menu.get()

    def show_participant_error(self, message):
        self.participant_error.configure(text=message)

    def set_running(self, running: bool):
        """Lock the controls while a trial/block runs, unlock them afterwards.

        Error prevention: the condition (and participant) can't change mid-trial,
        and a second task can't be started on top of the first one.
        """
        state = "disabled" if running else "normal"
        self.participant_entry.configure(state=state)
        self.contrast_buttons.configure(state=state)
        self.size_buttons.configure(state=state)
        self.brightness_slider.configure(state=state)
        self.figure_menu.configure(state=state)
        style.set_enabled(self.start_identification_button, not running)
        style.set_enabled(self.start_fitts_button, not running)
        style.set_enabled(self.cancel_button, running)
