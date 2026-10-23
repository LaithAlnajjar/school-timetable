# Observed performance

Run: `.venv\Scripts\python scripts/benchmark.py --classes 20 --seconds 15`

Observed on 23 October 2026: Windows 11 build 22631, CPython 3.12.14 x64,
AMD64 Family 25 Model 80 Stepping 0 (AuthenticAMD), OR-Tools 9.15.6755.
CPU: AMD Ryzen 7 5800H, 16 logical processors; 16,487,870,464 bytes physical RAM
(approximately 15.4 GiB).
Four CP-SAT search workers, seed 42. Synthetic example generator, 20 classes,
20 teachers, 100 requirements, 380 requested periods, five days with 30 teaching
slots, one science double per class, daily subject caps and subject-spread preferences.
Rooms and idle-gap preferences disabled for this larger example.

Result: **feasible**, 15.351 seconds end to end with a 15-second solver limit;
independent schedule validation found **zero issues**. All mandatory rules were met;
preference optimization had not finished. Model preparation/validation adds time
outside the solver limit. Solver timing/placement can vary with hardware and load.

This demonstrates a representative case, not an unlimited-size or instant-solution
guarantee. Dense room/availability constraints, many locks, long weeks and preference
optimization can substantially increase time and memory. A timeout without a solution
is not proof of impossibility. Use the script's JSON output to record further runs.

A second real run of the same 20-class fixture with a 0.01-second solver limit
returned **timeout** in 0.227 seconds end to end, without a timetable. No claim of
impossibility was made. Automated controlled-status tests also cover this distinction.
