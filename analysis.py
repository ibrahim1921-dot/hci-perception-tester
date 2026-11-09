"""
analysis.py - summarise the results CSV. Separate from the app; run it after a session:

    python analysis.py                      # reads data/results.csv
    python analysis.py path/to/other.csv    # reads another file

It prints plain-text tables, and if matplotlib is installed it also saves three
charts next to the CSV:
    time_vs_width.png, time_vs_distance.png, time_vs_id.png
Only the csv module is needed for the tables (no pandas).
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import config


# ---------------------------------------------------------------- small helpers
def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_number(text):
    """CSV text -> float, or None for an empty/invalid cell."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def fmt(value, decimals=3):
    return "-" if value is None else f"{value:.{decimals}f}"


def print_table(title, headers, rows):
    """Print a simple aligned text table."""
    print(f"\n{title}")
    table = [headers] + [[str(cell) for cell in row] for row in rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(headers))]
    for n, row in enumerate(table):
        print("  " + "  ".join(cell.rjust(width) for cell, width in zip(row, widths)))
        if n == 0:
            print("  " + "  ".join("-" * width for width in widths))


def sort_key(value):
    """Sort numbers numerically and text alphabetically."""
    number = to_number(value)
    return (0, number, "") if number is not None else (1, 0, str(value))


def linear_fit(xs, ys):
    """Least-squares straight line y = intercept + slope * x. None if not possible."""
    n = len(xs)
    if n < 2:
        return None
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return None                     # all x values equal: no line can be fitted
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return slope, mean_y - slope * mean_x


# ----------------------------------------------------------------- Fitts tables
def summarise_fitts(rows):
    fitts = [r for r in rows if r["task_type"] == config.TASK_TARGET_HITTING]
    print(f"\n=== Target Hitting ({len(fitts)} trials) ===")
    if not fitts:
        print("  No Target Hitting trials yet.")
        return

    for column, label in (("target_width_px", "Width (px)"), ("target_distance_px", "Distance (px)")):
        groups = defaultdict(list)
        for r in fitts:
            groups[r[column]].append(r)
        table = []
        for key in sorted(groups, key=sort_key):
            group = groups[key]
            table.append([key, len(group),
                          fmt(mean(to_number(r["time_taken_s"]) for r in group)),
                          fmt(mean(to_number(r["misses"]) for r in group), 2)])
        print_table(f"Grouped by target {label.split()[0].lower()}:",
                    [label, "n", "Mean time (s)", "Mean misses"], table)

    # 3 x 3 grid: one row per width, one column per distance.
    widths = sorted({r["target_width_px"] for r in fitts}, key=sort_key)
    distances = sorted({r["target_distance_px"] for r in fitts}, key=sort_key)
    grid = []
    for w in widths:
        line = [w]
        for d in distances:
            cell = [r for r in fitts if r["target_width_px"] == w and r["target_distance_px"] == d]
            t = mean(to_number(r["time_taken_s"]) for r in cell)
            m = mean(to_number(r["misses"]) for r in cell)
            line.append(f"{fmt(t)} s / {fmt(m, 1)}" if cell else "-")
        grid.append(line)
    print_table("Width x distance grid (mean time / mean misses):",
                ["Width \\ Distance"] + [f"D={d}" for d in distances], grid)


# -------------------------------------------------------- Identification tables
def summarise_identification(rows):
    ident = [r for r in rows if r["task_type"] == config.TASK_IDENTIFICATION]
    print(f"\n=== Identification ({len(ident)} trials) ===")
    if not ident:
        print("  No Identification trials yet.")
        return

    # Response counts, one table per figure (each figure has its own answers).
    for stimulus in sorted({r["stimulus"] for r in ident}):
        trials = [r for r in ident if r["stimulus"] == stimulus]
        responses = sorted({r["response"] for r in trials})
        for column, order in (("contrast", list(config.CONTRAST_MODES)), ("size", list(config.SIZE_MODES))):
            counts = defaultdict(Counter)           # level -> Counter of responses
            for r in trials:
                counts[r[column]][r["response"]] += 1
            levels = [lv for lv in order if lv in counts] + sorted(set(counts) - set(order))
            table = [[lv] + [counts[lv][resp] for resp in responses] + [sum(counts[lv].values())]
                     for lv in levels]
            print_table(f"Response counts per {column} - {stimulus}:",
                        [column.capitalize()] + responses + ["Total"], table)

    # Mean ease rating (and time) per full condition.
    groups = defaultdict(list)
    for r in ident:
        groups[(r["contrast"], r["size"], r["brightness_pct"])].append(r)
    contrast_order = list(config.CONTRAST_MODES)
    size_order = list(config.SIZE_MODES)

    def condition_order(key):
        contrast, size, brightness = key
        return (contrast_order.index(contrast) if contrast in contrast_order else 99,
                size_order.index(size) if size in size_order else 99,
                -(to_number(brightness) or 0))

    table = []
    for key in sorted(groups, key=condition_order):
        group = groups[key]
        table.append([key[0], key[1], f"{key[2]}%", len(group),
                      fmt(mean(to_number(r["ease_rating"]) for r in group), 2),
                      fmt(mean(to_number(r["time_taken_s"]) for r in group))])
    print_table("Mean ease rating per condition:",
                ["Contrast", "Size", "Brightness", "n", "Mean ease (1-5)", "Mean time (s)"], table)


# ----------------------------------------------------------------------- charts
def save_charts(rows, out_dir):
    try:
        import matplotlib
        matplotlib.use("Agg")          # draw to files only, no window needed
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nmatplotlib is not installed, so no charts were made. "
              "Install it with:  pip install matplotlib")
        return []

    fitts = [r for r in rows if r["task_type"] == config.TASK_TARGET_HITTING]
    if not fitts:
        print("\nNo Target Hitting trials, so no charts were made.")
        return []

    # (CSV column, chart title, x-axis label, file name)
    charts = [
        ("target_width_px", "Time vs target width", "Target width W (px)", "time_vs_width.png"),
        ("target_distance_px", "Time vs target distance", "Target distance D (px)",
         "time_vs_distance.png"),
        ("index_of_difficulty", "Time vs index of difficulty",
         "Index of difficulty ID = log2(D/W + 1) (bits)", "time_vs_id.png"),
    ]
    saved = []
    for column, title, x_label, filename in charts:
        points = [(to_number(r[column]), to_number(r["time_taken_s"])) for r in fitts]
        points = [(x, y) for x, y in points if x is not None and y is not None]
        xs = [x for x, _ in points]
        ys = [y for _, y in points]

        fig, ax = plt.subplots(figsize=(6.4, 4.4))
        fig.patch.set_facecolor("#FCFCFB")
        ax.set_facecolor("#FCFCFB")
        ax.scatter(xs, ys, s=36, color="#2A78D6", alpha=0.7, edgecolors="#FCFCFB",
                   linewidths=1, label="One trial", zorder=3)

        fit = linear_fit(xs, ys)
        if fit:
            slope, intercept = fit
            line_x = [min(xs), max(xs)]
            ax.plot(line_x, [intercept + slope * x for x in line_x], color="#52514E",
                    linewidth=2, label=f"Linear trend: y = {intercept:.3f} + {slope:.4f}x", zorder=2)

        ax.set_title(title, loc="left", fontsize=12, color="#0B0B0B")
        ax.set_xlabel(x_label, color="#52514E")
        ax.set_ylabel("Time taken (s)", color="#52514E")
        ax.grid(True, color="#E1E0D9", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#C3C2B7")
        ax.tick_params(colors="#52514E")
        ax.legend(frameon=False, fontsize=9)
        fig.tight_layout()

        path = Path(out_dir) / filename
        fig.savefig(path, dpi=120)
        plt.close(fig)
        saved.append(path)
        print(f"Saved chart: {path}")
    return saved


# ------------------------------------------------------------------------- main
def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    csv_path = Path(argv[0]) if argv else config.CSV_PATH
    if not csv_path.exists():
        print(f"No results file found at {csv_path}. Run some trials first.")
        return 1

    rows = load_rows(csv_path)
    participants = sorted({r["participant_id"] for r in rows})
    print(f"Read {len(rows)} trials from {csv_path}")
    print(f"Participants: {', '.join(participants) if participants else '(none)'}")

    summarise_fitts(rows)
    summarise_identification(rows)
    print()
    save_charts(rows, csv_path.parent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
