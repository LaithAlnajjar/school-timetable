from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import Room, SchoolClass, Subject, Teacher, delete_record, references, teaching_slots
from .dialogs import RecordDialog, button, label, readonly_table


class RecordsPanel(QWidget):
    def __init__(self, window, collection):
        super().__init__()
        self.window, self.collection = window, collection
        layout = QVBoxLayout(self)
        names = {
            "teachers": "teachers",
            "classes": "classes",
            "subjects": "subjects",
            "rooms": "rooms",
        }
        layout.addWidget(
            label(f"Add your school's {names[collection]}. Double-click a row to edit it.")
        )
        self.table = readonly_table(["Name", "Details"])
        self.table.setMinimumHeight(180)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit())
        layout.addWidget(self.table)
        controls = QHBoxLayout()
        singular = {
            "teachers": "teacher",
            "classes": "class",
            "subjects": "subject",
            "rooms": "room",
        }[collection]
        button(f"Add {singular}", self.add, controls)
        button("Edit selected", self.edit, controls)
        button("Delete selected", self.delete, controls)
        controls.addStretch()
        layout.addLayout(controls)
        self.empty = label("")
        self.empty.setObjectName("hint")
        layout.addWidget(self.empty)

    def selected(self):
        row = self.table.currentRow()
        records = getattr(self.window.project, self.collection)
        return records[row] if 0 <= row < len(records) else None

    def refresh(self):
        p = self.window.project
        records = getattr(p, self.collection)
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            detail = ""
            if self.collection == "teachers":
                count = sum(r.periods for r in p.requirements if r.teacher_id == record.id)
                available = sum(s.id not in record.unavailable for s in teaching_slots(p))
                detail = f"{count} assigned periods / {available} available"
                if record.max_daily:
                    detail += f" | daily limit {record.max_daily}"
                if record.max_consecutive:
                    detail += f" | consecutive limit {record.max_consecutive}"
            elif self.collection == "classes":
                count = sum(r.periods for r in p.requirements if r.class_id == record.id)
                detail = (
                    f"Year {record.year or 'not set'} | {count} required / "
                    f"{len(teaching_slots(p))} available"
                )
            elif self.collection == "rooms":
                detail = f"{len(record.unavailable)} unavailable periods"
            for col, text in enumerate((record.name, detail)):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, record.id)
                self.table.setItem(row, col, item)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.empty.setText("No records yet. Use Add above to get started." if not records else "")

    def add(self):
        constructor = {
            "teachers": Teacher,
            "classes": SchoolClass,
            "subjects": Subject,
            "rooms": Room,
        }[self.collection]
        self.open_dialog(constructor())

    def edit(self):
        record = self.selected()
        if record:
            self.open_dialog(record)
        else:
            self.empty.setText("Select a row to edit.")

    def open_dialog(self, record):
        dialog = RecordDialog(self.window.project, self.collection, record, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            records = getattr(self.window.project, self.collection)
            index = next((i for i, r in enumerate(records) if r.id == record.id), None)
            if index is None:
                records.append(dialog.record)
            else:
                records[index] = dialog.record
            self.window.data_changed()

    def delete(self):
        record = self.selected()
        if not record:
            self.empty.setText("Select a row to delete.")
            return
        affected = references(self.window.project, self.collection, record.id)
        message = f"Delete {record.name}?"
        if affected:
            if self.collection == "rooms":
                message += (
                    f"\n\nThis removes this room from {len(affected)} suitable-room lists. "
                    "A requirement with no suitable rooms left will no longer require a room. "
                    "The existing timetable will be rechecked."
                )
            else:
                message += (
                    f"\n\nThis also deletes {len(affected)} lesson requirements "
                    "and their lessons/locks."
                )
        if (
            QMessageBox.question(
                self,
                "Delete record",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            delete_record(self.window.project, self.collection, record.id, cascade=True)
            self.window.data_changed()
