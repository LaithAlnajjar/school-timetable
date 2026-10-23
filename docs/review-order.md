# Review and merge order

The complete application is on **codex/integration**. Main remains at the original
commit until the owner merges the reviewed work. No releases have been published.

| Order | Pull request | Head branch | Current base |
|---|---|---|---|
| 1 | [Project data and safe storage](https://github.com/LaithAlnajjar/school-timetable/pull/1) | codex/project-data | main |
| 2 | [Scheduler and independent validation](https://github.com/LaithAlnajjar/school-timetable/pull/2) | codex/scheduling | codex/project-data |
| 3 | [Desktop, editing and exports](https://github.com/LaithAlnajjar/school-timetable/pull/3) | codex/desktop | codex/scheduling |
| 4 | [Windows delivery and final verification](https://github.com/LaithAlnajjar/school-timetable/pull/4) | codex/integration | codex/desktop |

Merge #1 into main first. Then retarget #2 to main and merge it; do the same for #3
and #4 in order. Do not merge a later PR into its feature-branch base if the intention
is to integrate into main. The final PR includes the packaging smoke and self-review
fixes for fractional search limits and persistent whole-day availability.

All branches have been pushed. The GitHub connector could read repository data but
lacked PR write permission; PRs were created using the existing authenticated Git
credential without changing Git identity or configuration.

The local ZIP is in `dist/SchoolTimetable-1.0.0-windows-x64.zip`. A separately tested
[Windows CI artifact](https://github.com/LaithAlnajjar/school-timetable/actions/runs/39978295834/artifacts/12512875530)
is also available (30-day retention). Manual packaging is available under Actions
after its workflow is merged to main. No credentials or real school data are tracked.
