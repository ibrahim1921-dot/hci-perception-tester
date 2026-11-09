# Human Perception & Performance Tester

A desktop app for an HCI experiment. The **experimenter** changes the visual
condition of the test area (contrast, size, brightness), and a **participant** does
two tasks:

1. **Identification**: say what they see in an ambiguous figure (Rubin's vase,
   Necker cube, Schroeder staircase).
2. **Target hitting (Fitts' Law)**: click a Start circle, then a target circle,
   as fast as possible.

Every trial is saved automatically to `data/results.csv`.

## Install

Needs Python 3.10 or newer.

```bash
python -m pip install -r requirements.txt
```

`customtkinter` is required. `matplotlib` is optional and only used by
`analysis.py` to draw charts.

## Run

```bash
python main.py
```

## Running a test session

1. Type a **participant ID** (e.g. `P01`) in the top-left box. No task can start
   without one; a red message under the box explains why.
2. Choose the **visual condition**: contrast (High / Medium / Low), size
   (Small / Medium / Large) and brightness (20–100 %). The canvas on the right
   updates straight away as a preview. The status bar at the bottom always shows
   the active condition.
3. **Identification trial**: pick a figure under *Tasks*, then press
   **Start Identification Trial**. The figure appears and the timer starts. The
   participant clicks the answer that matches what they see (or **Other…** to type
   their own). They then rate how easy it was (1–5, by clicking or pressing a key 1–5),
   and the row is saved. To repeat the same figure under another condition, change
   the condition and press Start again.
4. **Fitts block**: press **Start Fitts Block**. For each of the 18 trials
   (3 distances × 3 widths × 2 repeats, random order), the participant clicks the
   **Start** ring, then the filled target. Missed clicks are counted. After the last
   trial they give one ease rating for the whole block, and all 18 rows are saved.
5. **Cancel** stops the running task. A cancelled identification trial is not saved
   (there is no answer). A cancelled Fitts block saves the completed trials with an
   empty ease rating.
6. **Open results folder** opens `data/` in your file manager.

The condition controls are locked while a trial or block is running, so the
condition can't change halfway through.

## Analyse the results

```bash
python analysis.py                  # summarises data/results.csv
python analysis.py other_file.csv   # or any other results file
```

It prints tables (Fitts' trials by width, by distance and a width × distance grid;
identification responses per contrast and size; mean ease rating per condition).
If matplotlib is installed it also saves `time_vs_width.png`, `time_vs_distance.png`
and `time_vs_id.png` next to the CSV.

To try it without running a session:

```bash
python tests/make_fake_data.py fake_results.csv
python analysis.py fake_results.csv
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## CSV columns

| Column | Meaning |
|---|---|
| `timestamp` | When the trial finished (ISO format) |
| `participant_id` | ID typed by the experimenter |
| `trial_number` | 1, 2, 3 … per participant (continues if the app is restarted) |
| `task_type` | `Identification` or `Target Hitting` |
| `contrast`, `size`, `brightness_pct` | The condition during the trial |
| `stimulus`, `response` | Identification only: figure and chosen answer |
| `target_distance_px`, `target_width_px` | Fitts only: D and W in screen pixels |
| `index_of_difficulty` | Fitts only: log2(D/W + 1), in bits |
| `time_taken_s` | Seconds, 3 decimals, measured with `time.perf_counter()` |
| `misses` | Fitts only: clicks that missed the target |
| `ease_rating` | 1 (very difficult) to 5 (very easy); empty if not given |

Columns that don't apply to a task are left empty.

## Project structure

```
main.py                     window layout + shared services for the tasks
config.py                   every constant (colours, sizes, distances, trial counts, CSV path)
visual_settings.py          current condition -> final colours / font size / shape scale
data_logger.py              CSV writing
tasks/identification_task.py  ambiguous figures + identification trial
tasks/fitts_task.py         Fitts' Law block and trials
tasks/canvas_helpers.py     drawing helpers shared by both tasks
ui/control_panel.py         experimenter controls
ui/rating_dialog.py         modal 1–5 ease rating
ui/style.py                 shared fonts and button styles
analysis.py                 summary tables + charts
tests/                      unit tests and the fake-data generator
data/                       results (created when the app runs)
```

## HCI principles used

| Principle | Where |
|---|---|
| Visibility of system status | Status bar shows the condition, participant and last action ("Saved trial 12"); "Trial 4 of 18" during a Fitts block |
| Recognition rather than recall | Condition always visible in the status bar; rating buttons show the number *and* its meaning; answers are buttons, not typed |
| Error prevention | Tasks can't start without a participant ID; condition controls lock during a trial; Start buttons disabled while a task runs |
| Help users recover from errors | If the CSV can't be written (e.g. open in Excel) a Retry dialog appears instead of losing the data; Cancel saves completed Fitts trials |
| Consistency | One accent colour for main actions, grey for secondary ones; same rating dialog for both tasks |
| Fitts' Law applied to our own UI | Large answer and rating buttons spread across the width |
| Flexibility and efficiency | Keys 1–5 work in the rating dialog |
| Separation of test and controls | Only the test canvas is affected by the conditions; the control panel and status bar stay readable so the experimenter can always operate the app |
| Minimalist design | Neutral greys, one accent colour, no decoration |

## Notes and assumptions

- The third ambiguous figure is the **Schroeder staircase**: a staircase seen from
  above, or the same shape seen upside down from below.
- Fitts' distances and widths are in **real screen pixels** and do **not** change with
  the Size setting, so D and W stay the controlled variables. The Size setting affects
  the instruction text. Contrast and brightness also change the target colours.
  `target_distance_px` stores the planned horizontal distance D; the small vertical
  jitter (±40 px) isn't included in it.
- On a display with Windows scaling above 100 %, the window and its controls are
  scaled, but the canvas still draws in physical pixels. If the scaled window
  would be bigger than the screen (e.g. 150 % on a 1920×1080 screen), the app
  shrinks it at startup so the whole window, including the status bar, stays visible.
- Identification time is measured up to the click on an answer. If **Other…** is
  chosen, the time stops at that click (typing time isn't counted). If the text box
  is cancelled, the trial simply continues.
