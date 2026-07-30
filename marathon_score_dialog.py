# marathon_score_dialog.py
#
# Window showing the operator's DX Marathon score: entities and CQ zones worked
# per band this year, the official all-bands score, and a year-to-date comparison
# with the same date last year. The logbook is parsed on demand in a worker
# thread so the UI stays responsive.

from datetime import datetime, timezone

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QSpacerItem
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal

from custom_button import CustomButton

from constants import CUSTOM_FONT, CUSTOM_FONT_SMALL
from style import get_main_table_qss, set_macos_window_appearance, EVEN_COLOR, STATUS_TRX_COLOR

from marathon_score import build_scorer
from marathon_diff_dialog import MarathonDiffDialog

from translatable_strings import MarathonScoreStrings, CommonStrings

# Header CSS shared with the rest of the app (Antenna Rotator, Priority Manager…).
_HEADER_QSS = """
    QHeaderView::section {
        font-weight: normal;
        border: none;
        padding: 10 4px 4px 4px;
    }
"""


def _style_header(table):
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setFont(CUSTOM_FONT_SMALL)
    header.setStyleSheet(_HEADER_QSS)

from logger import get_logger

log = get_logger(__name__)


class MarathonScoreWorker(QObject):
    finished = pyqtSignal(object)          # MarathonScorer or None on error
    progress = pyqtSignal(int, int)        # files_done, files_total

    def __init__(self, adif_file_paths, ignore_sat_entries):
        super().__init__()
        self._paths = adif_file_paths
        self._ignore_sat = ignore_sat_entries

    def run(self):
        try:
            scorer = build_scorer(
                self._paths,
                ignore_sat_entries=self._ignore_sat,
                progress_callback=lambda done, total: self.progress.emit(done, total),
            )
            self.finished.emit(scorer)
        except Exception as e:
            log.error(f"Marathon score worker failed: {e}")
            self.finished.emit(None)


class MarathonScoreDialog(QDialog):
    def __init__(self, adif_file_paths, ignore_sat_entries=False, dark_mode=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(MarathonScoreStrings.WINDOW_TITLE())
        self.setModal(True)
        self.resize(620, 640)
        self.dark_mode = dark_mode
        self.adif_file_paths = adif_file_paths
        self.ignore_sat_entries = ignore_sat_entries
        self.scorer = None
        self.comparison_band = None  # None = all bands (official score)

        now = datetime.now(timezone.utc)
        self.current_year = str(now.year)
        self.previous_year = str(now.year - 1)
        self.today_cutoff = (now.month, now.day)

        set_macos_window_appearance(self, dark_mode)

        self.main_layout = QVBoxLayout(self)

        title_label = QLabel(f"<b>{MarathonScoreStrings.TITLE(self.current_year)}</b>")
        title_font = QFont()
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(title_label)

        # Busy placeholder + progress bar shown while parsing.
        self.status_label = QLabel(MarathonScoreStrings.ANALYZING())
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.main_layout.addWidget(self.progress_bar)

        # Container that receives the results once parsing is done. It carries a
        # stretch factor so the band table (which is set to expand) grows when the
        # window is made taller.
        self.results_container = QVBoxLayout()
        self.main_layout.addLayout(self.results_container, 1)

        self.ok_button = CustomButton(CommonStrings.OK())
        self.ok_button.setFixedWidth(80)
        self.ok_button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addStretch()
        self.main_layout.addLayout(button_layout)

        self._start_parsing()

    """
        Parsing (worker thread)
    """
    def _start_parsing(self):
        self._thread = QThread(self)
        self._worker = MarathonScoreWorker(self.adif_file_paths, self.ignore_sat_entries)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_parsing_finished)
        self._thread.start()

    def _on_progress(self, done, total):
        if total:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(done)
        else:
            self.progress_bar.setRange(0, 0)  # indeterminate when total unknown

    def _on_parsing_finished(self, scorer):
        self._thread.quit()
        self._thread.wait()
        self._worker = None
        self._thread = None

        # Parsing done: hide the busy indicators.
        self.status_label.hide()
        self.progress_bar.hide()

        self.scorer = scorer
        if scorer is None:
            self.status_label.setText(MarathonScoreStrings.NO_FILES())
            self.status_label.show()
            return

        self._build_results()

    """
        Results UI
    """
    def _clear_results(self):
        while self.results_container.count():
            child = self.results_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _build_results(self):
        self._clear_results()

        subtitle = QLabel(MarathonScoreStrings.SUBTITLE())
        subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.results_container.addWidget(subtitle)

        # The band table takes the extra vertical space when the window grows.
        self.results_container.addWidget(self._build_band_table(), 1)
        self.results_container.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.results_container.addWidget(self._build_comparison_group(), 0)

    def _build_band_table(self):
        bands = self.scorer.bands_worked(self.current_year) or []

        table = QTableWidget()
        table.setColumnCount(4)
        table.setRowCount(len(bands) + 1)  # +1 for the totals row
        table.setHorizontalHeaderLabels([
            MarathonScoreStrings.HEADER_BAND(),
            MarathonScoreStrings.HEADER_ENTITIES(),
            MarathonScoreStrings.HEADER_ZONES(),
            MarathonScoreStrings.HEADER_SCORE(),
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setFont(CUSTOM_FONT)
        table.setShowGrid(False)
        table.setStyleSheet(get_main_table_qss(self.dark_mode))
        _style_header(table)

        def cell(text, highlight=False):
            item = QTableWidgetItem(str(text))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if highlight:
                item.setBackground(QColor(EVEN_COLOR))
                item.setForeground(QColor("#555BC2"))
            return item

        for row, band in enumerate(bands):
            n_ent, n_zone = self.scorer.band_counts(self.current_year, band)
            table.setItem(row, 0, cell(band))
            table.setItem(row, 1, cell(n_ent))
            table.setItem(row, 2, cell(n_zone))
            table.setItem(row, 3, cell(n_ent + n_zone, highlight=True))

        # Totals row = official all-bands unique score (not a column sum).
        tot_ent, tot_zone, tot_total = self.scorer.overall_score(self.current_year)
        totals_row = len(bands)
        table.setItem(totals_row, 0, cell(MarathonScoreStrings.LABEL_TOTAL(), highlight=True))
        table.setItem(totals_row, 1, cell(tot_ent, highlight=True))
        table.setItem(totals_row, 2, cell(tot_zone, highlight=True))
        table.setItem(totals_row, 3, cell(tot_total, highlight=True))

        return table

    def _score_for(self, year, band):
        """
        (entities, zones, total) YTD (today's cutoff) for `year`. band=None means
        the official all-bands unique score; otherwise that single band.
        """
        if band is None:
            return self.scorer.overall_score(year, self.today_cutoff)
        n_ent, n_zone = self.scorer.band_counts(year, band, self.today_cutoff)
        return n_ent, n_zone, n_ent + n_zone

    def _build_comparison_group(self):
        group = QGroupBox(MarathonScoreStrings.GROUP_COMPARISON())
        group.setFont(CUSTOM_FONT)
        layout = QVBoxLayout()

        # Band selector as the app's usual checkable band buttons: "All" + each
        # band worked this year. Clicking one updates the comparison table and
        # opens the difference window for that band.
        selector_label = QLabel(MarathonScoreStrings.LABEL_COMPARE_BAND())
        selector_label.setFont(CUSTOM_FONT)
        layout.addWidget(selector_label)

        bands_grid = QGridLayout()
        self.comparison_band_buttons = {}   # band (None for All) -> CustomButton
        entries = [(None, MarathonScoreStrings.OPTION_ALL())] + [
            (b, b) for b in self.scorer.bands_worked(self.current_year)
        ]
        max_cols = 6
        for i, (band, label) in enumerate(entries):
            btn = CustomButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked=False, b=band: self._select_comparison_band(b))
            self.comparison_band_buttons[band] = btn
            bands_grid.addWidget(btn, i // max_cols, i % max_cols)
        layout.addLayout(bands_grid)

        # Reflect the current selection's checked style (survives rebuilds).
        self._apply_comparison_band_style()

        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(4)
        self.comparison_table.setRowCount(3)
        self.comparison_table.setHorizontalHeaderLabels([
            "",
            MarathonScoreStrings.COL_THIS_YEAR(self.current_year),
            MarathonScoreStrings.COL_LAST_YEAR(self.previous_year),
            MarathonScoreStrings.COL_CHANGE(),
        ])
        self.comparison_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.comparison_table.verticalHeader().setVisible(False)
        self.comparison_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.comparison_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.comparison_table.setFont(CUSTOM_FONT)
        self.comparison_table.setShowGrid(False)
        self.comparison_table.setStyleSheet(get_main_table_qss(self.dark_mode))
        _style_header(self.comparison_table)
        self.comparison_table.setFixedHeight(
            self.comparison_table.verticalHeader().defaultSectionSize() * 3
            + self.comparison_table.horizontalHeader().height() + 4
        )

        layout.addWidget(self.comparison_table)
        group.setLayout(layout)

        self._fill_comparison_table()
        return group

    def _apply_comparison_band_style(self):
        # Highlight the selected band button; reset the others.
        for band, btn in self.comparison_band_buttons.items():
            checked = (band == self.comparison_band)
            btn.setChecked(checked)
            label = MarathonScoreStrings.OPTION_ALL() if band is None else band
            if checked:
                btn.updateStyle(label, STATUS_TRX_COLOR, "#FFFFFF")
            else:
                btn.resetStyle()

    def _select_comparison_band(self, band):
        # Selecting a band updates the comparison table AND opens the difference
        # window for that band.
        self.comparison_band = band
        self._apply_comparison_band_style()
        self._fill_comparison_table()
        self._open_difference()

    def _open_difference(self):
        if self.scorer is None:
            return
        dialog = MarathonDiffDialog(
            self.scorer,
            self.current_year,
            self.previous_year,
            self.comparison_band,
            self.today_cutoff,
            self.dark_mode,
            self,
        )
        dialog.exec()

    def _fill_comparison_table(self):
        this_ent, this_zone, this_total = self._score_for(self.current_year, self.comparison_band)
        last_ent, last_zone, last_total = self._score_for(self.previous_year, self.comparison_band)

        def delta_str(cur, prev):
            d = cur - prev
            return f"+{d}" if d > 0 else str(d)

        def cell(text, align=Qt.AlignmentFlag.AlignCenter, highlight=False):
            item = QTableWidgetItem(str(text))
            item.setTextAlignment(align)
            if highlight:
                item.setBackground(QColor(EVEN_COLOR))
                item.setForeground(QColor("#555BC2"))
            return item

        rows = [
            (MarathonScoreStrings.ROW_ENTITIES(), this_ent,   last_ent,   False),
            (MarathonScoreStrings.ROW_ZONES(),    this_zone,  last_zone,  False),
            (MarathonScoreStrings.ROW_TOTAL(),    this_total, last_total, True),
        ]
        for row, (label, cur, prev, highlight) in enumerate(rows):
            self.comparison_table.setItem(row, 0, cell(label, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, highlight=highlight))
            self.comparison_table.setItem(row, 1, cell(cur, highlight=highlight))
            self.comparison_table.setItem(row, 2, cell(prev, highlight=highlight))
            self.comparison_table.setItem(row, 3, cell(delta_str(cur, prev), highlight=highlight))
