# School Timetable specification

An offline Windows desktop planner for a headteacher with no technical background.
Python 3.12, PySide6, OR-Tools CP-SAT, openpyxl and Qt PDF; no accounts or services.
Delivery: Windows x64 folder distribution in a ZIP, Windows 10 1809+ / Windows 11.

Guided setup: school week, teachers, classes and subjects, lesson requirements,
generation, review/edit, export. CRUD uses stable IDs, explicit reference deletion,
inline validation, setup checklist and hidden advanced controls. Examples are synthetic.

Configure arbitrary named operating days with different daily slots, times and blocked
periods; copy patterns. Requirements specify class, subject, assigned teacher and exact
weekly periods. Show class capacity and teacher load. Empty slots stay free.

Mandatory rules: class/teacher clashes, exact counts, assigned teachers, teaching slots,
availability, configured daily/consecutive teacher limits, daily subject caps, double
blocks, enabled room restrictions and locks. Doubles count twice, stay in one room and
must be adjacent in real time without breaks. Optional preferences spread subjects and
reduce idle gaps. Disabled room scheduling needs no room data.

Generation runs off the Qt UI thread on a snapshot, supports cancellation and a search
limit, and reports feasible/optimal, impossible, timeout, cancelled or error honestly.
Independently validate results. Explain obvious conflicts with names and counts; label
harder diagnostic suggestions as suggestions. Preserve old schedules on failure and
reject stale results. No fabricated percentage or silent rule relaxation.

Class, teacher and whole-school views share one schedule. Atomic moves/swaps and
whole-block locks have undo/redo. Revalidate after data changes and block invalid exports.
Versioned portable JSON project file includes all setup, rules, timetable and locks.
Atomic saves, backup, application-data recovery/logs, Save As and unsaved-change prompts.

Export selected/all class or teacher timetables to genuine XLSX or multipage landscape
PDF using the current edited snapshot. Readable labels, repeated headings, long-name
wrapping, safe sheet names, free/break distinctions, titles and times. No Excel required.

Verification covers constraints, doubles/rooms, locks, edits, serialization, worker
outcomes, views, XLSX/PDF rendering and packaged smoke. Benchmark a representative larger
synthetic school; configurable size is no promise of unlimited scale. Reproduce checks
on Linux and Windows CI and expose manual Windows packaging as an artifact workflow.

Review order: project data → scheduler → desktop/edit/export → Windows delivery.
No PR merging or release publication is authorized.
