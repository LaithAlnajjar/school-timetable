"""Small forms with inline errors. Edit copies so cancelling never changes a project."""

from copy import deepcopy

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..examples import example_school
from ..models import Project, Requirement, Slot, new_id
from ..validation import validate_setup


def label(text):
    widget = QLabel(text)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def button(text, callback, layout):
    result = QPushButton(text)
    result.clicked.connect(callback)
    layout.addWidget(result)
    return result


def readonly_table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    table.horizontalHeader().setStretchLastSection(True)
    table.verticalHeader().hide()
    table.setWordWrap(True)
    return table


class FormDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(470)
        self.resize(560, 480)
        self.layout_box = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        self.form = QFormLayout(body)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        scroll.setWidget(body)
        self.layout_box.addWidget(scroll)
        self.error = label("")
        self.error.setObjectName("fieldError")
        self.layout_box.addWidget(self.error)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout_box.addWidget(self.buttons)

    def advanced(self, text="Advanced rules (optional)"):
        toggle = QCheckBox(text)
        body = QWidget()
        body.setVisible(False)
        form = QFormLayout(body)
        toggle.toggled.connect(body.setVisible)
        self.form.addRow(toggle)
        self.form.addRow(body)
        return form


class AvailabilityTree(QTreeWidget):
    def __init__(self, project, unavailable):
        super().__init__()
        self.setHeaderHidden(True)
        self.setMinimumHeight(160)
        self.setMaximumHeight(270)
        self.slot_items = []
        self.day_items = []
        self.hidden_slots = []
        known = set()
        for day in project.days:
            known.add(day.id)
            parent = QTreeWidgetItem([day.name + " (select to block the whole day)"])
            parent.setFlags(
                parent.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable
            )
            self.addTopLevelItem(parent)
            parent.setData(0, Qt.ItemDataRole.UserRole, day.id)
            self.day_items.append((day.id, parent))
            for slot in day.slots:
                known.add(slot.id)
                if slot.teaching:
                    item = QTreeWidgetItem(parent, [f"{slot.name}  {slot.start}-{slot.end}"])
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(
                        0,
                        Qt.CheckState.Checked
                        if slot.id in unavailable or day.id in unavailable
                        else Qt.CheckState.Unchecked,
                    )
                    self.slot_items.append((slot.id, item))
                elif slot.id in unavailable:
                    self.hidden_slots.append((day.id, slot.id))
            if day.id in unavailable:
                parent.setCheckState(0, Qt.CheckState.Checked)
        for sid in sorted(set(unavailable) - known):
            item = QTreeWidgetItem(["Removed day or period - uncheck this obsolete restriction"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked)
            self.addTopLevelItem(item)
            self.slot_items.append((sid, item))

    def selected(self):
        days = [
            day_id for day_id, item in self.day_items if item.checkState(0) == Qt.CheckState.Checked
        ]
        periods = [
            sid
            for sid, item in self.slot_items
            if item.checkState(0) == Qt.CheckState.Checked
            and (
                item.parent() is None or item.parent().data(0, Qt.ItemDataRole.UserRole) not in days
            )
        ]
        hidden = [sid for day_id, sid in self.hidden_slots if day_id not in days]
        return days + periods + hidden


def limit_spin(value=None):
    spin = QSpinBox()
    spin.setRange(0, 999)
    spin.setSpecialValueText("No limit")
    spin.setValue(value or 0)
    return spin


class RecordDialog(FormDialog):
    def __init__(self, project, collection, record, parent=None):
        super().__init__(
            "Edit "
            + {"teachers": "teacher", "classes": "class", "subjects": "subject", "rooms": "room"}[
                collection
            ],
            parent,
        )
        self.project, self.collection, self.record = project, collection, deepcopy(record)
        self.name = QLineEdit(record.name)
        self.name.setMaxLength(180)
        self.name.setPlaceholderText(
            {
                "teachers": "For example, Mrs Smith",
                "classes": "For example, 7A",
                "subjects": "For example, Mathematics",
                "rooms": "For example, Science laboratory",
            }[collection]
        )
        self.form.addRow("Name", self.name)
        self.year = None
        if collection == "classes":
            self.year = QLineEdit(record.year)
            self.year.setMaxLength(60)
            self.form.addRow("Year group (optional)", self.year)
        self.availability = None
        if collection in ("teachers", "rooms"):
            advanced = self.advanced()
            advanced.addRow(
                label(
                    "Mandatory when configured. A checked whole day stays unavailable "
                    "if periods are added or copied later. Individual periods can also be blocked."
                )
            )
            self.availability = AvailabilityTree(project, record.unavailable)
            advanced.addRow("Unavailable", self.availability)
            if collection == "teachers":
                self.daily = limit_spin(record.max_daily)
                self.consecutive = limit_spin(record.max_consecutive)
                advanced.addRow("Maximum periods per day", self.daily)
                advanced.addRow("Maximum consecutive periods", self.consecutive)
                advanced.addRow(label("Breaks and gaps between times reset consecutive teaching."))
        self.name.setFocus()

    def accept(self):
        name = self.name.text().strip()
        if not name:
            self.error.setText("Please enter a name.")
            self.name.setFocus()
            return
        if any(
            r.id != self.record.id and r.name.casefold() == name.casefold()
            for r in getattr(self.project, self.collection)
        ):
            self.error.setText("That name is already used. Choose a different name.")
            return
        self.record.name = name
        if self.year is not None:
            self.record.year = self.year.text().strip()
        if self.availability is not None:
            self.record.unavailable = self.availability.selected()
        if self.collection == "teachers":
            self.record.max_daily = self.daily.value() or None
            self.record.max_consecutive = self.consecutive.value() or None
        super().accept()


class SlotDialog(FormDialog):
    def __init__(self, slot, parent=None):
        super().__init__("Edit time period", parent)
        self.slot = deepcopy(slot)
        self.name = QLineEdit(slot.name)
        self.name.setMaxLength(60)
        self.start = QTimeEdit(QTime.fromString(slot.start, "HH:mm"))
        self.end = QTimeEdit(QTime.fromString(slot.end, "HH:mm"))
        for widget in (self.start, self.end):
            widget.setDisplayFormat("HH:mm")
        self.kind = QComboBox()
        self.kind.addItems(["Teaching period", "Break / lunch / blocked"])
        self.kind.setCurrentIndex(0 if slot.teaching else 1)
        for text, widget in (
            ("Name", self.name),
            ("Start", self.start),
            ("End", self.end),
            ("Use", self.kind),
        ):
            self.form.addRow(text, widget)

    def accept(self):
        if not self.name.text().strip() or self.end.time() <= self.start.time():
            self.error.setText("Enter a period name and an end time later than the start time.")
            return
        self.slot.name = self.name.text().strip()
        self.slot.start, self.slot.end = (
            self.start.time().toString("HH:mm"),
            self.end.time().toString("HH:mm"),
        )
        self.slot.teaching = self.kind.currentIndex() == 0
        super().accept()


class DayDialog(FormDialog):
    def __init__(self, project, day, parent=None):
        super().__init__("Edit school day", parent)
        self.project, self.day = project, deepcopy(day)
        self.resize(660, 590)
        self.name = QLineEdit(day.name)
        self.name.setMaxLength(180)
        self.form.addRow("Day name", self.name)
        self.form.addRow(
            label(
                "List every lesson period and break in time order. Days can have "
                "different patterns."
            )
        )
        self.table = readonly_table(["Period", "Start", "End", "Use"])
        self.table.setMinimumHeight(260)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_slot())
        self.form.addRow(self.table)
        row = QHBoxLayout()
        button("Add period", self.add_slot, row)
        button("Edit", self.edit_slot, row)
        button("Delete", self.delete_slot, row)
        button("Use starter pattern", self.starter, row)
        self.form.addRow(row)
        self.refresh()

    def refresh(self):
        self.day.slots.sort(key=lambda s: s.start)
        self.table.setRowCount(len(self.day.slots))
        for r, slot in enumerate(self.day.slots):
            for c, text in enumerate(
                (
                    slot.name,
                    slot.start,
                    slot.end,
                    "Teaching" if slot.teaching else "Break / blocked",
                )
            ):
                self.table.setItem(r, c, QTableWidgetItem(text))
        self.table.resizeColumnsToContents()

    def add_slot(self):
        start = QTime.fromString(self.day.slots[-1].end, "HH:mm") if self.day.slots else QTime(8, 0)
        dialog = SlotDialog(
            Slot(
                name=f"Period {len(self.day.slots) + 1}",
                start=start.toString("HH:mm"),
                end=start.addSecs(45 * 60).toString("HH:mm"),
            ),
            self,
        )
        if dialog.exec():
            self.day.slots.append(dialog.slot)
            self.refresh()

    def edit_slot(self):
        row = self.table.currentRow()
        if row < 0:
            self.error.setText("Select a period to edit.")
            return
        dialog = SlotDialog(self.day.slots[row], self)
        if dialog.exec():
            self.day.slots[row] = dialog.slot
            self.refresh()

    def delete_slot(self):
        row = self.table.currentRow()
        if row >= 0:
            self.day.slots.pop(row)
            self.refresh()

    def starter(self):
        if self.day.slots:
            self.error.setText("Delete existing periods first, or add/edit them individually.")
            return
        self.day.slots = deepcopy(example_school().days[0].slots)
        for slot in self.day.slots:
            slot.id = new_id()
        self.refresh()

    def accept(self):
        self.day.name = self.name.text().strip()
        issues = [i for i in validate_setup(Project(days=[self.day])) if i.path.startswith("days")]
        if any(
            d.id != self.day.id and d.name.casefold() == self.day.name.casefold()
            for d in self.project.days
        ):
            self.error.setText("That day name is already used.")
            return
        if issues:
            self.error.setText("\n".join(i.message for i in issues))
            return
        super().accept()


class RequirementDialog(FormDialog):
    def __init__(self, project, requirement=None, parent=None):
        super().__init__("Lesson requirement", parent)
        self.project = project
        self.requirement = deepcopy(requirement) if requirement else Requirement()
        r = self.requirement
        self.selectors = {}
        for collection, key, text in (
            ("classes", "class_id", "Class"),
            ("subjects", "subject_id", "Subject"),
            ("teachers", "teacher_id", "Assigned teacher"),
        ):
            combo = QComboBox()
            combo.setMinimumContentsLength(25)
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            for record in getattr(project, collection):
                combo.addItem(record.name, record.id)
            index = combo.findData(getattr(r, key))
            if index >= 0:
                combo.setCurrentIndex(index)
            self.selectors[key] = combo
            self.form.addRow(text, combo)
        self.periods = QSpinBox()
        self.periods.setRange(1, 9999)
        self.periods.setValue(r.periods)
        self.form.addRow("Teaching periods per week", self.periods)
        self.form.addRow(label("For example: 7A | Mathematics | Mrs Smith | 5 periods each week."))
        advanced = self.advanced()
        self.doubles = QSpinBox()
        self.doubles.setRange(0, 4999)
        self.doubles.setValue(r.doubles)
        advanced.addRow("Double lessons per week", self.doubles)
        self.double_help = label("")
        advanced.addRow(self.double_help)
        self.daily = limit_spin(r.max_per_day)
        advanced.addRow("Maximum subject periods per day", self.daily)
        self.spread = QCheckBox("Prefer spreading this subject across the week")
        self.spread.setChecked(r.spread)
        advanced.addRow(self.spread)
        self.rooms = QListWidget()
        self.rooms.setMaximumHeight(130)
        for room in project.rooms:
            item = QListWidgetItem(room.name, self.rooms)
            item.setData(Qt.ItemDataRole.UserRole, room.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if room.id in r.room_ids else Qt.CheckState.Unchecked
            )
        advanced.addRow("Suitable rooms", self.rooms)
        advanced.addRow(
            label(
                "Check one room to require it, or several to allow a choice. No "
                "selection means no room required. Rooms apply only when room "
                "planning is enabled under Generate."
            )
        )
        self.periods.valueChanged.connect(self.update_double_help)
        self.doubles.valueChanged.connect(self.update_double_help)
        self.update_double_help()

    def update_double_help(self):
        remaining = self.periods.value() - self.doubles.value() * 2
        self.double_help.setText(
            f"{self.doubles.value()} doubles use {self.doubles.value() * 2} of the weekly "
            f"periods; {remaining} single periods remain."
        )

    def accept(self):
        r = deepcopy(self.requirement)
        for key, combo in self.selectors.items():
            if combo.currentData() is None:
                self.error.setText(
                    "Add classes, subjects and teachers before entering requirements."
                )
                return
            setattr(r, key, combo.currentData())
        r.periods, r.doubles = self.periods.value(), self.doubles.value()
        r.max_per_day, r.spread = self.daily.value() or None, self.spread.isChecked()
        r.room_ids = [
            self.rooms.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.rooms.count())
            if self.rooms.item(i).checkState() == Qt.CheckState.Checked
        ]
        if r.doubles * 2 > r.periods:
            self.error.setText(
                "Each double uses two periods. Reduce doubles or increase the weekly total."
            )
            return
        if any(
            old.id != r.id and (old.class_id, old.subject_id) == (r.class_id, r.subject_id)
            for old in self.project.requirements
        ):
            self.error.setText("That class and subject already have a row. Edit the existing row.")
            return
        self.requirement = r
        super().accept()
