# School Timetable: your first week

Everything works on your computer without the internet. Your school file belongs to
you. Save it in Documents or another folder you can find again.

1. **School week:** enter your school name. Add each operating day. In Edit day,
   use the starter pattern or add your own periods, start/end times and breaks.
   Copy a daily pattern to other days, then adjust them. Breaks and lunch never hold lessons.
2. **Teachers:** add teachers' names. Advanced rules are optional: mark unavailable
   days/periods and set daily or consecutive teaching limits only when needed.
   A whole-day block stays in force if you later add or copy periods on that day.
3. **Classes & subjects:** add teaching groups (for example 7A) and subjects. Year
   groups are optional labels. Renaming a record keeps its lesson assignments.
4. **Lesson requirements:** add one row for each class and subject. Choose the
   assigned teacher and teaching periods per week. Five periods means five timetable
   cells. A double lesson uses two of those periods. For example, five periods with
   one double means one double and three single lessons.
5. **Generate:** read the setup checklist and choose Generate timetable. You can
   cancel. The old timetable stays safe when a search fails or is cancelled. A valid
   result is usable even if the program has not finished improving preferences.
6. **Review & edit:** switch between class, teacher and school views. Select a lesson,
   choose Move / swap, then click a destination teaching period. An occupied destination
   tries a swap. Rejected changes explain why and leave everything as it was. Doubles
   always move as a block. Lock lessons you want to keep, then regenerate the rest.
   Unlock before moving a locked lesson. Undo and Redo apply to timetable edits and locks.
7. **Export:** choose class or teacher timetables, all or one, and Excel or PDF.
   Exports include your latest edits without regenerating. Save the school project too
   so you can edit it later. Invalid/incomplete timetables cannot be exported as final.

## Save and reopen

Use **Save** regularly. The `.schooltimetable` file contains all setup, rules, lessons
and locks. Open it later using **Open**. Use **Save As** to create a copy for a new term.
Each save keeps the previous file beside it as a `.bak` backup; Open can read backups.
Keep the project file when sharing editable work. Excel/PDF exports are for reading.

Unsaved work is automatically copied to local application data after a short pause
and at least every 30 seconds while the app is running. After an unexpected shutdown,
the next start offers recovery. Recover a copy, then Save As. Cancel leaves recovery
files available for another start. Regular saves and external backups are still useful.

## If a timetable cannot be made

Read the actual names and counts in the message. A class may need more lessons than
its available periods, or a teacher may be unavailable too often. Check requirements,
teacher limits, room restrictions and locks. A double needs two teaching periods that
touch in time on the same day; it cannot cross lunch, a break or a gap.

**Search time expired** means no solution was found in the allowed time; it does not
prove the requirements are impossible. Try a longer search under Advanced planning
settings. **Rules cannot all be satisfied** means a contradiction was established.
Possible-cause suggestions are labelled when the program cannot identify an exact cause.

If you edit school data while generating, that generation result is discarded. Generate
again using your latest data. Changing setup clears timetable undo history so older
edits cannot restore lessons based on different requirements.

## Rooms, preferences and changed school data

Advanced planning settings under Generate let you add rooms and enable room planning.
Select suitable rooms under a lesson requirement's advanced options. One selected room
requires that room; several allow a choice; none means no room needed. A double uses
the same room for both periods. Unavailable room periods are set in Edit room.

Availability, configured maximums, doubles, rooms and locks are mandatory. Subject
spreading and reducing teacher idle gaps are preferences; they may not be fully improved
when the search limit is reached. Free periods are allowed and clearly labelled.

When you change setup, the current timetable is checked again. Read the Review status
and correct reported problems or regenerate. Removing/copying periods can invalidate
old locks and availability rules. Edit the relevant teacher/room to uncheck obsolete
restrictions. Unlock all lessons can clear incompatible locks before regeneration.
Deleting a referenced teacher, class or subject explicitly also deletes its requirements
and lessons; read the confirmation first. Deleting a room removes it from suitable-room
lists and can leave a requirement without a room restriction.

## Windows folder distribution

Extract the entire ZIP first. Open the extracted SchoolTimetable folder and double-click
SchoolTimetable.exe. Keep the supporting `_internal` folder with the EXE. You do not need
Python, Excel, an account, an internet connection or administrator rights.
If Windows asks about an unsigned application, only continue if you trust its source.
This project does not provide a code-signing certificate. Windows 10 1809+ x64 is the
minimum; Windows 11 is recommended.

Recovery and rotating logs are stored under your local Windows application-data folder
(`SchoolTimetable/School Timetable`), separate from the application. School projects
are saved wherever you choose. The application does not send your school data anywhere.
