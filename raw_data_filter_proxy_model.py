# raw_data_filter_proxy_model.py

from PyQt6.QtCore import QSortFilterProxyModel

from constants import (
    DEFAULT_FILTER_VALUE
)

class RawDataFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.enable_show_all_decoded    = False
        self.show_cleared_data          = False
        self.current_clear_index        = 0
        self.filters                     = None
        self.default_filters             = {
            'callsign'  : "",
            'country'   : "",
            'cq_zone'   : DEFAULT_FILTER_VALUE,
            'continent' : DEFAULT_FILTER_VALUE,
            'row_color' : None,
            'band'      : DEFAULT_FILTER_VALUE
        }
        self.clearProxyFilters()

    def setEnableShowAllDecoded(self, enabled):
        self.enable_show_all_decoded = enabled
        self.invalidateFilter()

    def setFilter(self, key, value):
        self.filters[key] = value
        self.invalidateFilter()

    def clearProxyFilters(self):
        self.filters = self.default_filters
        self.invalidateFilter()

    def clearTableView(self):    
        model = self.sourceModel()
        self.current_clear_index = model.rowCount()
        self.show_cleared_data = False
        self.invalidateFilter()

    def showAllData(self):
        self.show_cleared_data = True
        self.clearProxyFilters()
        self.invalidateFilter()        

    def hideErasedData(self):
        self.show_cleared_data = False
        self.invalidateFilter()            

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        raw_data = model._data[source_row]

        if not self.show_cleared_data:
            if source_row < self.current_clear_index:
                return False

        if not self.enable_show_all_decoded:
            if not raw_data.get('row_color'):
                return False
    
        if self.filters['callsign']:
            callsign = raw_data.get('callsign', None)
            if callsign and self.filters['callsign'].upper() not in callsign:
                return False
        
        if self.filters['country']:
            entity = raw_data.get('entity', None)
            if entity and self.filters['country'].upper() not in entity.upper():
                return False

        if self.filters['cq_zone'] != DEFAULT_FILTER_VALUE:
            if str(raw_data.get('cq_zone')) != self.filters['cq_zone']:
                return False

        if self.filters['continent'] != DEFAULT_FILTER_VALUE:
            if raw_data.get('continent') != self.filters['continent']:
                return False

        if self.filters['row_color']:
            if raw_data.get('row_color') != self.filters['row_color']:
                return False

        if self.filters['band'] != DEFAULT_FILTER_VALUE:
            if raw_data.get('band') != self.filters['band']:
                return False        

        return True
