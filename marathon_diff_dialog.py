# marathon_diff_dialog.py
#
# Shows which DX Marathon entities (or CQ zones) are common, newly gained this
# year, or only present last year, for the band/scope currently selected in the
# Marathon score window. Year-to-date cutoff is honoured.

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QHBoxLayout, QCheckBox, QRadioButton,
    QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt

from custom_button import CustomButton

from constants import CUSTOM_FONT, CUSTOM_FONT_SMALL
from style import get_main_table_qss, set_macos_window_appearance, EVEN_COLOR

# Header CSS shared with the rest of the app (Antenna Rotator, Priority Manager…).
_HEADER_QSS = """
    QHeaderView::section {
        font-weight: normal;
        border: none;
        padding: 10 4px 4px 4px;
    }
"""

from translatable_strings import MarathonDiffStrings, CommonStrings


# Gained entries: dark-blue text on a cyan fill (same highlight as the score
# window's totals row) so they stay readable on Windows, where plain cyan text
# on the white background is washed out. Lost entries: white text on a red fill.
_COLOR_GAINED_FG = "#555BC2"    # dark blue, same as the score highlight text
_COLOR_GAINED_BG = EVEN_COLOR   # cyan (#9DFFFE), same as the score highlight fill
_COLOR_LOST_FG   = "#FFFFFF"    # white
_COLOR_LOST_BG   = "#C5221F"    # red


class _NumericItem(QTableWidgetItem):
    """Table item that displays its text but sorts by its leading number, so
    e.g. "8" sorts before "16" (and "3, 4, 5" sorts by 3)."""

    def _sort_value(self):
        digits = ""
        for ch in self.text().strip():
            if ch.isdigit():
                digits += ch
            elif digits:
                break
        return int(digits) if digits else -1

    def __lt__(self, other):
        if isinstance(other, _NumericItem):
            return self._sort_value() < other._sort_value()
        return super().__lt__(other)


class MarathonDiffDialog(QDialog):
    def __init__(self, scorer, current_year, previous_year, band, cutoff,
                 compare_full_year=False, dark_mode=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(MarathonDiffStrings.WINDOW_TITLE())
        self.setModal(True)
        self.resize(760, 620)
        self.dark_mode = dark_mode
        self.scorer = scorer
        self.current_year = current_year
        self.previous_year = previous_year
        self.band = band            # None = all bands
        self.cutoff = cutoff              # current-year cutoff (always to-date)
        # Previous year: the full year when comparing to "Full {prev}", else the
        # same to-date cutoff as the current year.
        self.prev_cutoff = None if compare_full_year else cutoff
        self.show_zones = False      # False = entities, True = zones
        self.hide_common = True       # show only differences by default

        set_macos_window_appearance(self, dark_mode)

        layout = QVBoxLayout(self)

        scope = band if band else MarathonDiffStrings.SCOPE_ALL_BANDS()
        prev_label = (
            MarathonDiffStrings.PREV_FULL_YEAR(previous_year)
            if compare_full_year else previous_year
        )
        title = QLabel(f"<b>{MarathonDiffStrings.TITLE(current_year, prev_label, scope)}</b>")
        title_font = QFont()
        title_font.setPointSize(13)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Entities / Zones switch.
        switch_layout = QHBoxLayout()
        self.entities_radio = QRadioButton(MarathonDiffStrings.TOGGLE_ENTITIES())
        self.zones_radio = QRadioButton(MarathonDiffStrings.TOGGLE_ZONES())
        self.entities_radio.setFont(CUSTOM_FONT)
        self.zones_radio.setFont(CUSTOM_FONT)
        self.entities_radio.setChecked(True)
        self._switch_group = QButtonGroup(self)
        self._switch_group.addButton(self.entities_radio)
        self._switch_group.addButton(self.zones_radio)
        self.entities_radio.toggled.connect(self._on_switch)
        switch_layout.addWidget(self.entities_radio)
        switch_layout.addWidget(self.zones_radio)
        switch_layout.addStretch()

        self.hide_common_check = QCheckBox(MarathonDiffStrings.CHECK_HIDE_COMMON())
        self.hide_common_check.setFont(CUSTOM_FONT)
        self.hide_common_check.setChecked(self.hide_common)
        self.hide_common_check.toggled.connect(self._on_hide_common)
        switch_layout.addWidget(self.hide_common_check)
        layout.addLayout(switch_layout)

        self.summary_label = QLabel("")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFont(CUSTOM_FONT)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(get_main_table_qss(self.dark_mode))
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setFont(CUSTOM_FONT_SMALL)
        header.setStyleSheet(_HEADER_QSS)
        header.setSortIndicatorShown(True)
        layout.addWidget(self.table)

        button = CustomButton(CommonStrings.OK())
        button.setFixedWidth(80)
        button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self._rebuild()

    def _on_switch(self, _checked):
        self.show_zones = self.zones_radio.isChecked()
        self._rebuild()

    def _on_hide_common(self, checked):
        self.hide_common = checked
        self._rebuild()

    def _label_for(self, key):
        if self.show_zones:
            return str(key)
        return self.scorer.entity_name(key)

    @staticmethod
    def _fmt_date(qso_date):
        # ADIF date "YYYYMMDD" -> "YYYY-MM-DD".
        if qso_date and len(qso_date) >= 8:
            return f"{qso_date[0:4]}-{qso_date[4:6]}-{qso_date[6:8]}"
        return qso_date or ""

    def _columns_for_row(self, key, date, callsign):
        """Cell texts for one row, matching the current mode's columns."""
        date_str = self._fmt_date(date)
        call_str = callsign or ""
        if self.show_zones:
            # Zone | Date | Callsign
            return [str(key), date_str, call_str]
        # Date | Callsign | Prefix | Name | Continent | CQ Zones
        rec = self.scorer.entity_record(key)
        return [date_str, call_str, rec["prefix"], rec["name"], rec["continent"], rec["cq_zones"]]

    def _configure_columns(self):
        if self.show_zones:
            headers = [
                MarathonDiffStrings.COL_ZONE(),
                MarathonDiffStrings.COL_DATE(),
                MarathonDiffStrings.COL_CALLSIGN(),
            ]
            stretch_col = 2
        else:
            headers = [
                MarathonDiffStrings.COL_DATE(),
                MarathonDiffStrings.COL_CALLSIGN(),
                MarathonDiffStrings.COL_PREFIX(),
                MarathonDiffStrings.COL_NAME(),
                MarathonDiffStrings.COL_CONTINENT(),
                MarathonDiffStrings.COL_CQ_ZONES(),
            ]
            stretch_col = 3  # Name column stretches
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        header = self.table.horizontalHeader()
        for col in range(len(headers)):
            mode = QHeaderView.ResizeMode.Stretch if col == stretch_col else QHeaderView.ResizeMode.ResizeToContents
            header.setSectionResizeMode(col, mode)

    def _rebuild(self):
        if self.show_zones:
            cur_info = self.scorer.zone_info(self.current_year, self.band, self.cutoff)
            prev_info = self.scorer.zone_info(self.previous_year, self.band, self.prev_cutoff)
        else:
            cur_info = self.scorer.entity_info(self.current_year, self.band, self.cutoff)
            prev_info = self.scorer.entity_info(self.previous_year, self.band, self.prev_cutoff)

        cur = set(cur_info)
        prev = set(prev_info)
        common = cur & prev
        gained = cur - prev
        lost = prev - cur

        self.summary_label.setText(
            MarathonDiffStrings.SUMMARY(len(common), len(gained), len(lost), self.current_year, self.previous_year)
        )

        # Rows: (key, date, callsign, fg, bg). Gained first, then lost, then
        # common (unless hidden). Gained/common use this year's QSO, lost uses
        # last year's.
        rows = []
        for key in sorted(gained, key=self._label_for):
            date, call = cur_info[key]
            rows.append((key, date, call, _COLOR_GAINED_FG, _COLOR_GAINED_BG))
        for key in sorted(lost, key=self._label_for):
            date, call = prev_info[key]
            rows.append((key, date, call, _COLOR_LOST_FG, _COLOR_LOST_BG))
        if not self.hide_common:
            for key in sorted(common, key=self._label_for):
                date, call = cur_info[key]
                rows.append((key, date, call, None, None))

        # Disable sorting while (re)building columns and filling, then restore it,
        # otherwise the table re-sorts on every setItem and rows misalign.
        self.table.setSortingEnabled(False)
        self._configure_columns()
        self.table.setRowCount(len(rows))

        # Numeric-sortable columns (per mode) so "8" sorts before "16".
        # Zones mode: Zone is column 0; entities mode: CQ Zones is column 5.
        numeric_cols = {0} if self.show_zones else {5}

        for row, (key, date, call, fg, bg) in enumerate(rows):
            for col, text in enumerate(self._columns_for_row(key, date, call)):
                if col in numeric_cols:
                    item = _NumericItem(text)
                else:
                    item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if fg:
                    item.setForeground(QColor(fg))
                if bg:
                    item.setBackground(QColor(bg))
                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)

        # Default sort: Zone (col 0) ascending in zones mode, Prefix (col 2)
        # ascending in entities mode.
        default_sort_col = 0 if self.show_zones else 2
        self.table.sortItems(default_sort_col, Qt.SortOrder.AscendingOrder)

        # Zones mode has only 3 narrow columns, so shrink the window; entities
        # mode needs the full width for its 6 columns.
        self.resize(460 if self.show_zones else 760, self.height())
