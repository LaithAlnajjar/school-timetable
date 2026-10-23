# Interface repair — 24 October 2026

The repair is on `codex/interface-repair`, stacked above `codex/integration`
(`d1f62a7`). [PR #5](https://github.com/LaithAlnajjar/school-timetable/pull/5)
depends on #4; the existing review order is preserved. The checkout was clean.

## Observed defects and repairs

The baseline was launched on the native Windows Qt platform with the actual
Windows app appearance set to dark. Screenshots were opened and examined before
editing. Windows supplied a dark Fusion palette while the old stylesheet forced
dark text and selected white surfaces. Dialog bodies, tabs and advanced planning
areas became dark with dark text. Selected table/lesson text was pale on pale blue,
including when inactive. Spin arrows were barely visible; availability was cramped;
export choices had no labels; six editing actions crowded one row; empty tables
gave little direction and keyboard lesson selection did not update edit actions.

The application now deliberately uses a light Fusion palette with explicit active,
inactive and disabled roles. Segoe UI 11 pt, consistent spacing, readable boundaries,
visible focus, larger check marks and explicit arrow symbols apply to all controls
and dialogs. Advanced settings remain collapsed by default. Errors explain the
problem in text, focus the relevant field and reveal hidden advanced fields.

Forms use full-width labeled fields. Pages and forms scroll on smaller screens;
action rows wrap. Native frame checks exposed advanced dialogs expanding below the
desktop, which now reposition into the available screen. Help also fits the screen.
Notice margins are explicit because Qt dynamic styles could repaint colors without
reserving text padding.

Timetables emphasize subjects, retain readable teacher/class/room/time text and
label free periods, breaks, doubles and locks. Selecting either half of a double
highlights its complete block. Move mode uses a written instruction panel, outlined
source and destinations, a cross cursor and an enabled Cancel action. Rejections
explain the reason and preserve the timetable. Locks retain selection and expose
Unlock immediately. Long names wrap; resizing a column recalculates row heights;
large grids scroll in both directions. Longer school-view headings wrap, with full
names in tooltips. Export controls explain unavailable/invalid schedules.

Scheduling, independent validation, storage, project schema, stable IDs and shared
Excel/PDF presentation code were not changed.

## Visual evidence

Before: [availability](images/before-availability.png),
[selected lesson](images/before-review.png).
The [side-by-side comparison](images/ui-comparison.png) preserves the original
screenshots at their captured sizes. [Palette/contrast report](images/ui/report.json).

After, all seven pages: [School week](images/ui/week.png),
[Teachers](images/ui/teachers.png), [Classes](images/ui/classes.png),
[Subjects](images/ui/subjects.png), [Lesson requirements](images/requirements.png),
[Generate](images/ui/generate.png), [Review and edit](images/review.png),
[Export](images/ui/export.png).

Representative states: [availability](images/ui/availability.png),
[advanced planning](images/ui/generate-advanced.png),
[selected lesson](images/ui/review-selected.png), [move mode](images/ui/review-moving.png),
[rejected move](images/ui/review-rejected.png), [locked lesson](images/ui/review-locked.png),
[long names](images/ui/review-long-names.png), [inactive selection](images/ui/selection-inactive.png),
[invalid form](images/ui/invalid-name.png), [busy](images/ui/generate-busy.png),
[combo popup](images/ui/combo-popup.png), [Help](images/ui/help.png),
[message box](images/ui/message-unsaved.png),
[200% actions](images/ui/scale-200-review-actions.png).

Full local capture sets and contact sheets are in `build/ui-before`,
`build/ui-final-light-100` and `build/ui-final-dark-{100,125,150,200}`. Each includes
empty/populated pages, add/edit forms, availability, advanced settings, errors,
selections, focus, disabled controls, popups, tooltips, Help, warning/unsaved message
boxes, all review views, long names, and busy/cancelled/invalid generation. These
are native Qt widget captures using QTest, with synthetic school data only. The
desktop computer-use helper could not start because of a Windows sandbox setup
error; no visual result is inferred from the stylesheet alone.

## Measured contrast

Ratios use WCAG sRGB relative luminance. They describe foreground/background color
pairs, not antialiased edge pixels. Palette roles and real rendered surface/selection
pixels are also checked in regression tests. Normal text exceeds 4.5:1; boundaries
and focus exceed 3:1. The complete measurements accompany the local capture reports.

| Use | Foreground | Background | Contrast |
|---|---|---|---:|
| Original dark dialog | `#20344D` | `#323232` | **1.01:1** |
| Original selected lesson | `#F0F0F0` | `#CBDFF3` | **1.20:1** |
| Body text | `#20344D` | `#FFFFFF` | **12.65:1** |
| Supporting text | `#4B5E71` | `#F4F6F9` | **6.18:1** |
| Active/inactive selection, primary action | `#FFFFFF` | `#205C86` | **7.15:1** |
| Disabled label | `#536273` | `#E9EDF2` | **5.31:1** |
| Subject cells (six backgrounds) | `#20344D` | pastel subject colors | **9.93–10.66:1** |
| Control boundary | `#718096` | `#FFFFFF` | **4.02:1** |
| Focus indicator | `#1458A8` | `#F4F6F9` | **6.48:1** |
| Error message | `#A12B24` | `#FFF1EF` | **6.61:1** |
| Valid timetable | `#215B37` | `#EDF7F0` | **7.32:1** |
| Move instruction | `#654700` | `#FFF4D6` | **7.81:1** |
| Move outline | `#826000` | `#FFF4D6` | **5.29:1** |
| Scrollbar thumb | `#697D90` | `#EDF1F5` | **3.75:1** |

## Appearance, scaling and keyboard checks

Actual Windows `AppsUseLightTheme` was temporarily set to light and dark and restored
after each run, including exception cleanup. Qt detected native Light and Dark,
respectively; the deliberate application theme remained Light. Active, inactive
and disabled palettes were inspected. Selections remained readable with another
window active. Combo popups, spin boxes, checks, tooltips and scrollbars were opened
and visually examined.

| Qt scale / measured DPR | Main window, logical pixels | Method |
|---|---|---|
| 100% / 1.0 | 1280 × 860 | Native Windows, light and dark appearance |
| 125% / 1.25 | 1280 × 786 | Native Windows, `QT_SCALE_FACTOR=1.25` |
| 150% / 1.5 | 1250 × 648 | Native Windows, `QT_SCALE_FACTOR=1.5` |
| 200% / 2.0 | 930 × 476 | Native Windows, `QT_SCALE_FACTOR=2` |

The monitor's Windows display scale stayed at 100%; the higher scales are real Qt
renders in fresh native processes, not separate Windows Display settings runs.
Per-monitor DPI transitions and separate Windows accessibility text-size settings
were not exercised. At compact sizes, some controls require page scrolling; tests
scroll every page action fully into view. Table scrolling remains independent.

Keyboard checks cover Tab/Shift+Tab, field-error focus, opening setup rows with
Enter, arrow selection, Alt+M move, Enter destination/rejection, Escape cancellation,
Ctrl+Z undo and redo availability. Standard project shortcuts, F1 and Alt+1…7 are
provided. Qt accessible names are checked for labeled form controls and key tables.
No independent Narrator or other screen-reader session was run.

## Checks and delivery

Thirteen interface regressions supplement the original 48 tests. Checks include
behavior and rendered pixels, rather than assertions duplicating stylesheet text.
All 31 installed locked dependencies match their exact pins.

Build/smoke results, ZIP checksum and remote CI status are recorded in
[verification.md](verification.md). The Windows folder and extracted ZIP use the
same committed UI source and include the control symbol resources. Generated
distributions, full audit captures, smoke reports and PDFs remain outside Git.
