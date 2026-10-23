"""Validated snapshot exports; workbook needs no Excel, PDF uses Qt's print engine."""

from __future__ import annotations

import html
import os
import re
import tempfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.pagebreak import Break
from PySide6.QtCore import QRectF
from PySide6.QtGui import (
    QColor,
    QFont,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QTextDocument,
    QTextOption,
)

from .models import Project
from .storage import atomic_write
from .validation import validate_schedule
from .views import timetable


class ExportError(ValueError):
    pass


def export_snapshot(project: Project, kind: str, ids: list[str] | None):
    p = deepcopy(project)
    issues = validate_schedule(p)
    if issues:
        raise ExportError(
            "Correct the timetable before exporting:\n"
            + "\n".join(dict.fromkeys(i.message for i in issues))
        )
    if kind not in ("classes", "teachers"):
        raise ExportError("Choose classes or teachers.")
    selected = ids if ids is not None else [r.id for r in getattr(p, kind)]
    if not selected:
        raise ExportError("Select at least one timetable to export.")
    if any(p.lookup(kind, record_id) is None for record_id in selected):
        raise ExportError("A selected class or teacher no longer exists.")
    return p, [timetable(p, kind, record_id) for record_id in selected]


def sheet_title(name, used):
    stem = re.sub(r"[\\/*?:\[\]\x00-\x1f]", "_", name).strip(" '") or "Timetable"
    candidate = stem[:31]
    n = 2
    while candidate.casefold() in used:
        suffix = f" ({n})"
        candidate = stem[: 31 - len(suffix)] + suffix
        n += 1
    used.add(candidate.casefold())
    return candidate


def write_text(cell, value):
    # Treat school-supplied names as literal text, including Excel formula prefixes.
    cell.value = value
    cell.data_type = "s"


def export_excel(project: Project, path: str | Path, kind="classes", ids=None):
    p, tables = export_snapshot(project, kind, ids)
    workbook = Workbook()
    index = workbook.active
    index.title = "Index"
    write_text(index["A1"], p.school_name)
    write_text(index["A2"], "Timetable index")
    index.column_dimensions["A"].width = 55
    index["A1"].font = Font(size=16, bold=True, color="173650")
    used = {"index"}
    thin = Side(style="thin", color="C9D1DC")
    for number, table in enumerate(tables, 4):
        ws = workbook.create_sheet(sheet_title(table.name, used))
        write_text(index.cell(number, 1), f"{table.kind}: {table.name}")
        escaped = ws.title.replace("'", "''")
        index.cell(number, 1).hyperlink = f"#'{escaped}'!A1"
        index.cell(number, 1).style = "Hyperlink"
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(table.days))
        write_text(ws.cell(1, 1), p.school_name)
        ws.cell(1, 1).font = Font(size=16, bold=True, color="173650")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(table.days))
        write_text(ws.cell(2, 1), f"{table.kind} timetable: {table.name}")
        ws.cell(2, 1).font = Font(size=13, bold=True)
        ws.cell(2, 1).alignment = Alignment(wrap_text=True)
        chars = max(20, 32 * len(table.days))
        ws.cell(1, 1).alignment = Alignment(wrap_text=True)
        ws.row_dimensions[1].height = max(28, 22 * (1 + len(p.school_name) // chars))
        ws.row_dimensions[2].height = max(28, 20 * (1 + (len(table.name) + 20) // chars))
        ws.row_dimensions[4].height = max(24, 17 * max(1 + len(day) // 30 for day in table.days))
        for c, day in enumerate(table.days, 1):
            write_text(ws.cell(4, c), day)
            ws.cell(4, c).fill = PatternFill("solid", fgColor="173650")
            ws.cell(4, c).font = Font(bold=True, color="FFFFFF")
            ws.cell(4, c).alignment = Alignment(wrap_text=True, vertical="center")
            ws.column_dimensions[ws.cell(4, c).column_letter].width = 34
            for row, cell in enumerate(table.columns[c - 1], 5):
                target = ws.cell(row, c)
                text = cell.heading + "\n" + cell.text
                write_text(target, text)
                target.alignment = Alignment(wrap_text=True, vertical="top")
                target.fill = PatternFill("solid", fgColor=cell.color.lstrip("#"))
                target.border = Border(left=thin, right=thin, top=thin, bottom=thin)
                target.font = Font(name="Calibri", size=11)
                lines = sum(max(1, (len(line) + 31) // 32) for line in text.splitlines())
                ws.row_dimensions[row].height = max(
                    ws.row_dimensions[row].height or 0, 16 * lines + 8
                )
        ws.freeze_panes = "A5"
        ws.print_title_rows = "1:4"
        ws.print_options.horizontalCentered = True
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = ws.PAPERSIZE_A3 if len(table.days) > 5 else ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1 if len(table.days) <= 5 else 0
        ws.page_setup.fitToHeight = 0
        if len(table.days) > 5:
            for col in range(5, len(table.days), 5):
                ws.col_breaks.append(Break(id=col))
        ws.print_area = ws.dimensions
        ws.oddFooter.center.text = "Page &P of &N"
    buffer = BytesIO()
    workbook.save(buffer)
    atomic_write(Path(path), buffer.getvalue())


def _document(text, width, writer, *, heading=False):
    doc = QTextDocument()
    doc.documentLayout().setPaintDevice(writer)
    doc.setDefaultFont(QFont("Arial", 11 if heading else 10))
    doc.setDocumentMargin(0)
    option = doc.defaultTextOption()
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    doc.setDefaultTextOption(option)
    doc.setTextWidth(width)
    escaped = html.escape(text).replace("\n", "<br/>")
    doc.setHtml(f'<div style="color:#173650; word-wrap:break-word;">{escaped}</div>')
    return doc


def export_pdf(project: Project, path: str | Path, kind="classes", ids=None):
    p, tables = export_snapshot(project, kind, ids)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=target.parent, suffix=".pdf")
    os.close(handle)
    writer = QPdfWriter(temp)
    writer.setResolution(96)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QPageLayout.Orientation.Landscape)
    writer.setTitle(p.school_name + " - Timetables")
    writer.setCreator("School Timetable")
    painter = QPainter()
    try:
        if not painter.begin(writer):
            raise ExportError("Cannot create the PDF. Choose a writable folder.")
        width, height = writer.width(), writer.height()
        margin, pad, page = 20, 8, 0

        def draw_document(doc, x, y, clip_height, offset=0):
            painter.save()
            painter.setClipRect(QRectF(x, y, doc.textWidth(), clip_height))
            painter.translate(x, y - offset)
            doc.drawContents(painter)
            painter.restore()

        for table in tables:
            # Three columns per page keep a readable fixed font even for a long school week.
            for start in range(0, len(table.days), 3):
                days = table.days[start : start + 3]
                columns = table.columns[start : start + 3]
                col_width = (width - 2 * margin) / len(days)
                title = _document(
                    f"{p.school_name}\n{table.kind} timetable: {table.name}",
                    width - 2 * margin,
                    writer,
                    heading=True,
                )
                title_height = title.size().height()
                day_docs = [
                    _document(day, col_width - 2 * pad, writer, heading=True) for day in days
                ]
                header_height = max(doc.size().height() for doc in day_docs) + 2 * pad
                top = margin + title_height + 12 + header_height
                bottom = height - margin - 25
                if bottom - top < 100:
                    raise ExportError(
                        "The school/timetable title is too long for a printable page. "
                        "Shorten the name before exporting."
                    )

                def new_page(
                    writer=writer,
                    title=title,
                    title_height=title_height,
                    day_docs=day_docs,
                    col_width=col_width,
                    top=top,
                    header_height=header_height,
                    bottom=bottom,
                ):
                    nonlocal page
                    if page:
                        writer.newPage()
                    page += 1
                    draw_document(title, margin, margin, title_height)
                    for c, doc in enumerate(day_docs):
                        x = margin + c * col_width
                        painter.fillRect(
                            QRectF(x, top - header_height, col_width, header_height),
                            QColor("#E3EAF3"),
                        )
                        draw_document(
                            doc, x + pad, top - header_height + pad, header_height - 2 * pad
                        )
                    painter.setFont(QFont("Arial", 9))
                    painter.setPen(QColor("#46566D"))
                    painter.drawText(
                        QRectF(margin, bottom + 6, width - 2 * margin, 22),
                        f"School Timetable | Page {page} | Free periods and breaks are labelled",
                    )
                    return top

                y = new_page()
                for row in range(max((len(col) for col in columns), default=0)):
                    cells = [col[row] if row < len(col) else None for col in columns]
                    docs = [
                        _document(
                            cell.heading + "\n" + cell.text if cell else "No period",
                            col_width - 2 * pad,
                            writer,
                        )
                        for cell in cells
                    ]
                    row_height = max(doc.size().height() for doc in docs) + 2 * pad
                    if row_height <= bottom - top and y + row_height > bottom:
                        y = new_page()
                    offset = 0.0
                    # Very long cell contents continue across pages, at the same readable font.
                    while offset < row_height:
                        if y + min(row_height - offset, 70) > bottom:
                            y = new_page()
                        segment = min(row_height - offset, bottom - y)
                        for c, (cell, doc) in enumerate(zip(cells, docs, strict=True)):
                            x = margin + c * col_width
                            painter.fillRect(
                                QRectF(x, y, col_width, segment),
                                QColor(cell.color if cell else "#F5F6F8"),
                            )
                            painter.setPen(QColor("#C9D1DC"))
                            painter.drawRect(QRectF(x, y, col_width, segment))
                            painter.save()
                            painter.setClipRect(QRectF(x + pad, y, col_width - 2 * pad, segment))
                            painter.translate(x + pad, y + pad - offset)
                            doc.drawContents(painter)
                            painter.restore()
                        y += segment
                        offset += segment
                        if offset < row_height:
                            y = new_page()
        painter.end()
        # Release the writer before replacing on Windows (which disallows open-file renames).
        del writer
        os.replace(temp, target)
    finally:
        if painter.isActive():
            painter.end()
        Path(temp).unlink(missing_ok=True)
