"""Readable tables and timetable painting; no scheduling decisions live here."""

from html import escape

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen, QTextDocument, QTextOption
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QLayout,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionHeader,
    QStyleOptionViewItem,
    QTableWidget,
)

from .theme import TEXT

CELL_ROLE = Qt.ItemDataRole.UserRole + 1


class ActionFlow(QLayout):
    """Action buttons wrap onto another row when scaling leaves less space."""

    def __init__(self):
        super().__init__()
        self.items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(8)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.arrange(QRect(0, 0, width, 0), test=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        return size

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.arrange(rect)

    def arrange(self, rect, test=False):
        x, y, height = rect.x(), rect.y(), 0
        for item in self.items:
            size = item.sizeHint()
            if x > rect.x() and x + size.width() > rect.right() + 1:
                x, y, height = rect.x(), y + height + self.spacing(), 0
            if not test:
                item.setGeometry(QRect(x, y, size.width(), size.height()))
            x += size.width() + self.spacing()
            height = max(height, size.height())
        return y + height - rect.y()


class ReadableTable(QTableWidget):
    def __init__(self, columns):
        super().__init__(0, columns)
        self.empty_label = QLabel(self.viewport())
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMargin(24)
        self.empty_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.set_empty("No rows yet. Use Add to get started.")
        self.setMinimumHeight(180)
        self.verticalHeader().setMinimumSectionSize(42)
        self.setHorizontalScrollMode(self.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(self.ScrollMode.ScrollPerPixel)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_empty(self, text):
        self.empty_label.setText(text)
        self.empty_label.setAccessibleName(text)
        self.empty_label.setVisible(self.rowCount() == 0)

    def setRowCount(self, count):
        super().setRowCount(count)
        self.empty_label.setVisible(count == 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.empty_label.setGeometry(self.viewport().rect())


def fit_setup_table(table):
    """Wrap long records without letting a single name consume the entire grid."""
    table.resizeColumnsToContents()
    for col in range(table.columnCount()):
        table.setColumnWidth(col, min(360, max(100, table.columnWidth(col))))
    table.resizeRowsToContents()


class WrappedHeader(QHeaderView):
    def __init__(self, parent):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSectionResizeMode(self.ResizeMode.Interactive)
        self.setMinimumSectionSize(150)
        self.sectionResized.connect(lambda *_: self.updateGeometry())

    def sizeHint(self):
        font = self.font()
        font.setBold(True)
        metrics = QFontMetrics(font)
        height = 44
        for col in range(self.count()):
            text = str(self.model().headerData(col, self.orientation()) or "")
            bounds = metrics.boundingRect(
                QRect(0, 0, max(40, self.sectionSize(col) - 20), 10000),
                Qt.TextFlag.TextWordWrap,
                text,
            )
            height = max(height, bounds.height() + 20)
        return QSize(super().sizeHint().width(), min(140, height))

    def paintSection(self, painter, rect, index):
        option = QStyleOptionHeader()
        self.initStyleOption(option)
        option.rect = rect
        option.section = index
        self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)
        painter.save()
        font = self.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(TEXT))
        painter.drawText(
            rect.adjusted(10, 6, -10, -6),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            str(self.model().headerData(index, self.orientation()) or ""),
        )
        painter.restore()


class LessonDelegate(QStyledItemDelegate):
    def __init__(self, window):
        super().__init__(window.review_table)
        self.window = window

    def document(self, option, index, selected):
        cell = index.data(CELL_ROLE)
        lines = str(index.data() or "").split("\n")
        # Time stays above the lesson; the subject is the strongest line.
        subject_line = 1 if cell and self.window.view_kind.currentIndex() != 2 else 0
        lines = [
            f"<b>{escape(line)}</b>"
            if cell and cell.lesson_id and i == subject_line
            else escape(line)
            for i, line in enumerate(lines)
        ]
        document = QTextDocument()
        document.setDefaultFont(option.font)
        document.setDocumentMargin(0)
        document.setDefaultStyleSheet(f"body {{ color: {'white' if selected else TEXT}; }}")
        document.setHtml("<body>" + "<br>".join(lines) + "</body>")
        text_option = document.defaultTextOption()
        text_option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        document.setDefaultTextOption(text_option)
        document.setTextWidth(max(40, option.rect.width() - 24))
        return document

    def sizeHint(self, option, index):
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        option.rect.setWidth(self.window.review_table.columnWidth(index.column()))
        return QSize(
            option.rect.width(),
            max(76, int(self.document(option, index, False).size().height()) + 24),
        )

    def paint(self, painter: QPainter, option, index):
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        cell = index.data(CELL_ROLE)
        chosen = cell and cell.lesson_id and cell.lesson_id == self.window.selected_lesson
        if chosen:
            option.state |= QStyle.StateFlag.State_Selected
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        option.text = ""
        self.window.review_table.style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem, option, painter, self.window.review_table
        )
        painter.save()
        painter.setClipRect(option.rect)
        painter.translate(option.rect.left() + 12, option.rect.top() + 12)
        self.document(option, index, selected).drawContents(painter)
        painter.restore()
        if self.window.pending_lesson and cell:
            source = cell.lesson_id == self.window.pending_lesson
            if source or cell.teaching:
                painter.save()
                painter.setPen(
                    QPen(
                        QColor("#826000"),
                        3 if source else 1,
                        Qt.PenStyle.SolidLine if source else Qt.PenStyle.DashLine,
                    )
                )
                painter.drawRect(option.rect.adjusted(2, 2, -2, -2))
                painter.restore()
