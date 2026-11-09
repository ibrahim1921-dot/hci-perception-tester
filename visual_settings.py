"""
visual_settings.py - the current visual condition of the test canvas.

It stores three things chosen by the experimenter:
    contrast   ("High" / "Medium" / "Low")
    size       ("Small" / "Medium" / "Large")
    brightness (20 - 100 %)
and turns them into the final colours, font size and shape scale that the
tasks use when drawing.
"""

import config


def apply_brightness(hex_color: str, percent: float) -> str:
    """Dim a colour to simulate a darker screen.

    Each of the red, green and blue values is multiplied by percent / 100.
    100 % leaves the colour unchanged, 50 % halves every channel.
    The result is rounded half-up and clamped to 0-255, so it is always valid.

    Example: apply_brightness("#FFFFFF", 50) -> "#808080"
    """
    digits = hex_color.lstrip("#")
    if len(digits) != 6:
        raise ValueError(f"Expected a colour like '#RRGGBB', got {hex_color!r}")

    # Keep the percentage within 0-100 so we never go below black or above the original.
    percent = max(0.0, min(100.0, float(percent)))
    factor = percent / 100.0

    new_channels = []
    for start in (0, 2, 4):                          # RR, GG, BB
        value = int(digits[start:start + 2], 16)     # hex text -> 0..255
        scaled = int(value * factor + 0.5)           # round half up
        new_channels.append(max(0, min(255, scaled)))

    return "#{:02X}{:02X}{:02X}".format(*new_channels)


class VisualSettings:
    """Holds the current condition and works out colours and sizes from it."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Go back to the default condition (High contrast, Medium size, 100 %)."""
        self.contrast = config.DEFAULT_CONTRAST
        self.size = config.DEFAULT_SIZE
        self.brightness = config.BRIGHTNESS_DEFAULT

    # ----- setters (with validation, so a typo can't create an unknown condition) -----
    def set_contrast(self, mode: str):
        if mode not in config.CONTRAST_MODES:
            raise ValueError(f"Unknown contrast mode: {mode}")
        self.contrast = mode

    def set_size(self, mode: str):
        if mode not in config.SIZE_MODES:
            raise ValueError(f"Unknown size mode: {mode}")
        self.size = mode

    def set_brightness(self, percent: float):
        # Store a whole number and keep it inside the slider's range.
        percent = int(round(percent))
        self.brightness = max(config.BRIGHTNESS_MIN, min(config.BRIGHTNESS_MAX, percent))

    # ----- values the tasks use for drawing -----
    def foreground(self) -> str:
        """Final text/shape colour: contrast colour dimmed by the brightness."""
        base = config.CONTRAST_MODES[self.contrast]["foreground"]
        return apply_brightness(base, self.brightness)

    def background(self) -> str:
        """Final canvas background colour: contrast colour dimmed by the brightness."""
        base = config.CONTRAST_MODES[self.contrast]["background"]
        return apply_brightness(base, self.brightness)

    def font_size(self) -> int:
        """Canvas text size in points."""
        return config.SIZE_MODES[self.size]["font_pt"]

    def shape_scale(self) -> float:
        """Multiplier for figure sizes (0.5, 1.0 or 1.6)."""
        return config.SIZE_MODES[self.size]["shape_scale"]

    # ----- the one place every logged row gets its condition from -----
    def get_condition(self) -> dict:
        """Return the current condition. Keys match the CSV column names."""
        return {
            "contrast": self.contrast,
            "size": self.size,
            "brightness_pct": self.brightness,
        }

    def describe(self) -> str:
        """Human-readable condition for the status bar."""
        return f"Contrast: {self.contrast} · Size: {self.size} · Brightness: {self.brightness}%"
