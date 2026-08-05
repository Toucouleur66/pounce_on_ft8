# reply_decision_dialog.py
#
# Shows, for a station in the output table, WHY the app replied to (or skipped) it:
# the winning candidate and its reason, the full list of candidates that competed
# in the same process_reply_packet_buffer cycle, the tie-break note when priorities
# were equal, and the neighbouring log context (marathon/wanted/exclusion/reply).
#
# Fed by log_reply_analyzer (pure parsing); this file is display-only.

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QTextEdit, QLayout
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from custom_button import CustomButton

from constants import CUSTOM_FONT, CUSTOM_FONT_SMALL
from style import get_main_table_qss, set_macos_window_appearance, BG_COLOR_BLACK_ON_YELLOW

from translatable_strings import ReplyDecisionStrings, CommonStrings

_HEADER_QSS = """
    QHeaderView::section {
        font-weight: normal;
        border: none;
        padding: 10 4px 4px 4px;
    }
"""


class ReplyDecisionDialog(QDialog):
    def __init__(self, analysis, dark_mode=False, is_slave=False, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.dark_mode = dark_mode

        self.setWindowTitle(ReplyDecisionStrings.WINDOW_TITLE())
        self.setModal(True)
        set_macos_window_appearance(self, dark_mode)

        has_details = bool(analysis.get('candidates') or analysis.get('context'))

        layout = QVBoxLayout(self)

        # On a SLAVE the reply is decided by the MASTER; this "Selected messages"
        # block was computed from the SLAVE's OWN (possibly divergent) settings/ADIF,
        # so warn that the analysis is local and not the authoritative decision.
        if is_slave:
            warning = QLabel(ReplyDecisionStrings.SLAVE_WARNING())
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #FFCC00; padding: 6px;")
            warning.setFont(CUSTOM_FONT_SMALL)
            # Give the wrap a width so the compact (no-details) layout stays readable.
            warning.setMinimumWidth(420)
            layout.addWidget(warning)

        # Headline: replied-to + reason, or not-found / not-selected.
        self.summary_label = QLabel(self._headline_text())
        self.summary_label.setFont(CUSTOM_FONT)
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.summary_label)

        candidates = analysis.get('candidates') or []
        if candidates:
            caption = QLabel(ReplyDecisionStrings.CANDIDATES_HEADER())
            caption.setFont(CUSTOM_FONT_SMALL)
            layout.addWidget(caption)
            self._table = self._build_table(candidates, analysis.get('selected'))
            layout.addWidget(self._table)

            tie_note = analysis.get('tie_break_note')
            if tie_note:
                tie_label = QLabel(tie_note)
                tie_label.setFont(CUSTOM_FONT_SMALL)
                tie_label.setWordWrap(True)
                layout.addWidget(tie_label)

        # Neighbouring log context (marathon/wanted/exclusion/Sent ReplyPacket…).
        context = analysis.get('context') or []
        if context:
            ctx_caption = QLabel(ReplyDecisionStrings.CONTEXT_HEADER())
            ctx_caption.setFont(CUSTOM_FONT_SMALL)
            layout.addWidget(ctx_caption)

            ctx_view = QTextEdit()
            ctx_view.setReadOnly(True)
            ctx_view.setFont(CUSTOM_FONT_SMALL)
            ctx_view.setPlainText("\n".join(context))
            ctx_view.setMaximumHeight(160)
            # Match the candidate table exactly: same width AND the same 1px frame,
            # so both boxes line up at the same left/right edges. Qt's default
            # QTextEdit frame differs from the table's, which looked misaligned.
            ctx_view.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            ctx_bg = '#353535' if self.dark_mode else '#FFFFFF'
            ctx_view.setStyleSheet(
                f"QTextEdit {{ background-color: {ctx_bg}; "
                f"border: 1px solid palette(Mid); }}"
            )
            ctx_view.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            layout.addWidget(ctx_view)

        # Buttons: Copy (only when there is something worth copying) + Close.
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        if has_details:
            copy_button = CustomButton(ReplyDecisionStrings.COPY())
            copy_button.setFixedWidth(100)
            copy_button.clicked.connect(self._copy_to_clipboard)
            button_layout.addWidget(copy_button)
        close_button = CustomButton(CommonStrings.CLOSE())
        close_button.setFixedWidth(100)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Size to content: a full analysis (candidate table + context) gets a roomy
        # window; a bare "no decision found" message stays compact instead of a huge
        # mostly-empty box.
        if has_details:
            self.setMinimumWidth(560)
            self.resize(720, 560)
        else:
            self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
            self.setMinimumWidth(360)

    def _headline_text(self):
        a = self.analysis
        callsign = a.get('callsign', '')
        if not a.get('found'):
            return ReplyDecisionStrings.NO_DECISION(callsign)

        selected = a.get('selected') or {}
        winner = selected.get('callsign', '')
        raw_reason = a.get('reason')
        reason = self._format_reason(raw_reason) if raw_reason else ReplyDecisionStrings.REASON_UNKNOWN()

        if a.get('is_selected'):
            return f"<b>{ReplyDecisionStrings.REPLIED_TO(callsign, reason)}</b>"
        # The queried station was a candidate but lost to `winner`.
        return f"<b>{ReplyDecisionStrings.NOT_SELECTED(callsign, winner)}</b>"

    # Human labels for the internal priority_type keys (acronyms kept correct).
    _REASON_LABELS = {
        'wanted'         : "Wanted",
        'wanted_grid'    : "Wanted Grid",
        'wanted_cq_zone' : "Wanted CQ Zone",
        'marathon'       : "Marathon",
        'dxcc_entity'    : "DXCC",
        'pota'           : "POTA",
        'polite_reply'   : "Politeness",
    }

    @classmethod
    def _format_reason(cls, priority_type):
        # "wanted_grid" -> "Wanted Grid"; empty stays empty. Unknown keys fall
        # back to a title-cased form.
        if not priority_type:
            return ""
        return cls._REASON_LABELS.get(priority_type, priority_type.replace('_', ' ').title())

    def _build_table(self, candidates, selected):
        # No "selected" star column: the winning row is already highlighted.
        headers = [
            ReplyDecisionStrings.COL_PRIORITY(),
            ReplyDecisionStrings.COL_REASON(),
            ReplyDecisionStrings.COL_CALLSIGN(),
            ReplyDecisionStrings.COL_DIRECTED(),
            ReplyDecisionStrings.COL_SNR(),
            ReplyDecisionStrings.COL_WKB4(),
            ReplyDecisionStrings.COL_LOTW(),
            ReplyDecisionStrings.COL_PID(),
        ]
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(candidates))
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # No focus: prevents the dotted focus rectangle Windows draws on the
        # clicked cell (the table is read-only, cells are never selectable).
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setFont(CUSTOM_FONT_SMALL)
        table.setShowGrid(False)
        table.setStyleSheet(get_main_table_qss(self.dark_mode))
        header = table.horizontalHeader()
        header.setHighlightSections(False)
        header.setFont(CUSTOM_FONT_SMALL)
        header.setStyleSheet(_HEADER_QSS)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        selected_call = (selected or {}).get('callsign')
        highlight = QColor(BG_COLOR_BLACK_ON_YELLOW)

        for row, c in enumerate(candidates):
            is_winner = c.get('callsign') == selected_call
            values = [
                str(c.get('priority', '')),
                self._format_reason(c.get('priority_type')),
                c.get('callsign', ''),
                c.get('directed', ''),
                (f"+{c['snr']}" if c.get('snr', 0) >= 0 else str(c.get('snr'))),
                (str(c['wkb4_year']) if c.get('wkb4_year') is not None else ""),
                "*" if c.get('lotw') else "",
                str(c.get('packet_id', '')),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                # Read-only, non-selectable cells (belt-and-suspenders with the
                # table-level NoSelection / NoFocus).
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                if is_winner:
                    item.setBackground(highlight)
                    item.setForeground(QColor("#000000"))
                table.setItem(row, col, item)

        table.resizeColumnsToContents()
        # Stretch the last column to the right edge so the table fills its full
        # width and lines up with the Log context box below it.
        header.setStretchLastSection(True)
        table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        return table

    def _plain_text_summary(self):
        a = self.analysis
        lines = [self.summary_label.text().replace("<b>", "").replace("</b>", "")]
        for c in (a.get('candidates') or []):
            mark = "*" if c.get('callsign') == (a.get('selected') or {}).get('callsign') else " "
            snr = f"+{c['snr']}" if c.get('snr', 0) >= 0 else str(c.get('snr'))
            lines.append(
                f"{mark} [{c.get('priority')}] {c.get('callsign')} "
                f"dir:{c.get('directed')} snr:{snr} "
                f"why:{c.get('priority_type') or '?'} pid:{c.get('packet_id')}"
            )
        if a.get('tie_break_note'):
            lines.append(a['tie_break_note'])
        if a.get('context'):
            lines.append("")
            lines.extend(a['context'])
        return "\n".join(lines)

    def _copy_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._plain_text_summary())
