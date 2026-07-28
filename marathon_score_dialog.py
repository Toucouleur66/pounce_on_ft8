# marathon_score_dialog.py
#
# Window showing the operator's DX Marathon score: entities and CQ zones worked
# per band this year, the official all-bands score, and a year-to-date comparison
# with the same date last year. The logbook is parsed on demand in a worker
# thread so the UI stays responsive.

from datetime import datetime, timezone

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QSpacerItem
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal

from custom_button import CustomButton
from custom_qlabel import CustomQLabel
from animated_toggle import AnimatedToggle

from utils import AMATEUR_BANDS
from constants import CUSTOM_FONT
from style import get_main_table_qss, set_macos_window_appearance, EVEN_COLOR

from marathon_score import build_scorer

from translatable_strings import MarathonScoreStrings, CommonStrings

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
        self.resize(760, 640)
        self.dark_mode = dark_mode
        self.adif_file_paths = adif_file_paths
        self.ignore_sat_entries = ignore_sat_entries
        self.show_all_bands = False
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

        # Busy placeholder shown while parsing.
        self.status_label = QLabel(MarathonScoreStrings.ANALYZING())
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # Container that receives the results once parsing is done.
        self.results_container = QVBoxLayout()
        self.main_layout.addLayout(self.results_container)

        self.main_layout.addStretch()

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
            self.status_label.setText(f"{MarathonScoreStrings.ANALYZING()} ({done}/{total})")

    def _on_parsing_finished(self, scorer):
        self._thread.quit()
        self._thread.wait()
        self._worker = None
        self._thread = None

        self.scorer = scorer
        if scorer is None:
            self.status_label.setText(MarathonScoreStrings.NO_FILES())
            return

        self.status_label.setText(MarathonScoreStrings.SUBTITLE())
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

        # Show-all-bands toggle row.
        toggle_layout = QHBoxLayout()
        toggle_layout.addStretch()
        self.show_all_bands_label = CustomQLabel(MarathonScoreStrings.TOGGLE_SHOW_ALL_BANDS())
        toggle_layout.addWidget(self.show_all_bands_label)
        self.show_all_bands_toggle = AnimatedToggle()
        self.show_all_bands_toggle.setChecked(self.show_all_bands)
        self.show_all_bands_toggle.stateChanged.connect(self._toggle_show_all_bands)
        self.show_all_bands_toggle.setFixedSize(self.show_all_bands_toggle.sizeHint())
        toggle_layout.addWidget(self.show_all_bands_toggle)
        self.results_container.addLayout(toggle_layout)

        self.results_container.addWidget(self._build_band_table())
        self.results_container.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.results_container.addWidget(self._build_comparison_group())

    def _toggle_show_all_bands(self, state):
        self.show_all_bands = bool(state)
        self._build_results()

    def _build_band_table(self):
        all_bands = list(AMATEUR_BANDS.keys())
        if self.show_all_bands:
            bands = all_bands
        else:
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

        # Band selector: "All bands (official)" + each band worked this year.
        selector_layout = QHBoxLayout()
        selector_label = QLabel(MarathonScoreStrings.LABEL_COMPARE_BAND())
        selector_label.setFont(CUSTOM_FONT)
        selector_layout.addWidget(selector_label)

        self.comparison_combo = QComboBox()
        self.comparison_combo.setFont(CUSTOM_FONT)
        self.comparison_combo.addItem(MarathonScoreStrings.OPTION_ALL_BANDS(), None)
        for band in self.scorer.bands_worked(self.current_year):
            self.comparison_combo.addItem(band, band)
        # Restore any previous selection (survives the show-all-bands toggle).
        index = self.comparison_combo.findData(self.comparison_band)
        if index >= 0:
            self.comparison_combo.setCurrentIndex(index)
        self.comparison_combo.currentIndexChanged.connect(self._on_comparison_band_changed)
        selector_layout.addWidget(self.comparison_combo)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)

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
        self.comparison_table.setFixedHeight(
            self.comparison_table.verticalHeader().defaultSectionSize() * 3
            + self.comparison_table.horizontalHeader().height() + 4
        )

        layout.addWidget(self.comparison_table)
        group.setLayout(layout)

        self._fill_comparison_table()
        return group

    def _on_comparison_band_changed(self, _index):
        self.comparison_band = self.comparison_combo.currentData()
        self._fill_comparison_table()

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
