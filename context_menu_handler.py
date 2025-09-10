# context_menu_handler.py

import sys
from collections import defaultdict
from PyQt6 import QtWidgets, QtCore

from utils import band_sort_key

from constants import (
    CONTEXT_MENU_DARWIN_QSS,
    CONTEXT_MENU_HEADER_QSS,
    CONTEXT_MENU_EXCLUDED_QSS,
    MENU_FONT,
    SLAVE
)

class ContextMenuHandler:
    def __init__(self, main_gui):
        self.main_gui = main_gui

    def show_context_menu(self, widget, position, data, source_type="table"):
        """
            Show context menu for either table or grid clicks
        """
        if not data:
            return

        # Determine context menu band
        if self.main_gui.gui_selected_band is not None:
            context_menu_band = self.main_gui.gui_selected_band
        elif self.main_gui.operating_band is not None:
            context_menu_band = self.main_gui.operating_band
        else:
            return

        # Extract data fields
        formatted_message   = data.get('formatted_message')
        callsign            = data.get('callsign')
        directed            = data.get('directed')
        cq_zone             = data.get('cq_zone')
        history_band        = data.get('band')
        excluded            = data.get('excluded')

        if not callsign:
            return

        # Create menu
        menu = QtWidgets.QMenu()
        if sys.platform == 'darwin':
            menu.setStyleSheet(CONTEXT_MENU_DARWIN_QSS)
            menu.setFont(MENU_FONT)

        actions = {}

        # History table specific actions
        if source_type == "table" and hasattr(widget, 'objectName') and widget.objectName() == 'history_table':
            actions['remove_entry_from_worked_history'] = menu.addAction(f"Remove {callsign} on {history_band} from Worked History")
            
            callsign_bands = defaultdict(set)
            for entry in self.main_gui.worked_callsigns_history:
                callsign_bands[entry['callsign']].add(entry['band'])

            if len(callsign_bands[callsign]) > 1:
                bands_text = ", ".join(sorted(callsign_bands[callsign], key=band_sort_key))
                actions['remove_callsign_from_worked_history'] = menu.addAction(f"Remove {callsign} on all bands from Worked History ({bands_text})")

            menu.addSeparator()

        # Exclusion info
        if excluded:
            label = QtWidgets.QLabel(f"Exclusion for <b>{excluded}</b> and matches with <b>{callsign}</b>")
            label.setStyleSheet(CONTEXT_MENU_EXCLUDED_QSS)

            widget_action = QtWidgets.QWidgetAction(menu)
            widget_action.setDefaultWidget(label)

            menu.addAction(widget_action)
            menu.addSeparator()

        # Band header
        label = QtWidgets.QLabel(f"Apply to <b>{context_menu_band}</b> band")
        label.setStyleSheet(CONTEXT_MENU_HEADER_QSS)

        widget_action = QtWidgets.QWidgetAction(menu)
        widget_action.setDefaultWidget(label)

        menu.addAction(widget_action)
        menu.addSeparator()

        # Wanted Callsigns
        if callsign not in self.main_gui.wanted_callsigns_vars[context_menu_band].text():
            actions['add_callsign_to_wanted'] = menu.addAction(f"Add {callsign} to Wanted Callsigns")
        else:
            actions['remove_callsign_from_wanted'] = menu.addAction(f"Remove {callsign} from Wanted Callsigns")

        if callsign != self.main_gui.wanted_callsigns_vars[context_menu_band].text():
            actions['replace_wanted_with_callsign'] = menu.addAction(f"Make {callsign} your only Wanted Callsign")
            if self.main_gui._instance == SLAVE:
                actions['replace_wanted_with_callsign'].setEnabled(False)

        # Excluded Callsigns
        if callsign not in self.main_gui.excluded_callsigns_vars[context_menu_band].text():
            menu.addSeparator()
            actions['add_callsign_to_temp_excluded'] = menu.addAction(f"Temporarily add {callsign} to Excluded Callsigns")
            actions['add_callsign_to_excluded'] = menu.addAction(f"Add {callsign} to Excluded Callsigns")
        else:
            actions['remove_callsign_from_excluded'] = menu.addAction(f"Remove {callsign} from Excluded Callsigns")
        menu.addSeparator()

        # Monitored Callsigns
        if callsign not in self.main_gui.monitored_callsigns_vars[context_menu_band].text():
            actions['add_callsign_to_monitored'] = menu.addAction(f"Add {callsign} to Monitored Callsigns")
        else:
            actions['remove_callsign_from_monitored'] = menu.addAction(f"Remove {callsign} from Monitored Callsigns")
        menu.addSeparator()

        # Directed Callsigns (output table specific)
        if source_type == "table" and hasattr(widget, 'objectName') and widget.objectName() == 'output_table':
            if directed and directed != self.main_gui.my_call:
                if directed not in self.main_gui.wanted_callsigns_vars[context_menu_band].text():
                    actions['add_directed_to_wanted'] = menu.addAction(f"Add {directed} to Wanted Callsigns")
                else:
                    actions['remove_directed_from_wanted'] = menu.addAction(f"Remove {directed} from Wanted Callsigns")

                if directed != self.main_gui.wanted_callsigns_vars[context_menu_band].text():
                    actions['replace_wanted_with_directed'] = menu.addAction(f"Make {directed} your only Monitored Callsign")

                if directed not in self.main_gui.monitored_callsigns_vars[context_menu_band].text():
                    actions['add_directed_to_monitored'] = menu.addAction(f"Add {directed} to Monitored Callsigns")
                else:
                    actions['remove_directed_from_monitored'] = menu.addAction(f"Remove {directed} from Monitored Callsigns")

                menu.addSeparator()

        # Monitored CQ Zones
        if cq_zone:
            try:
                if str(cq_zone) not in self.main_gui.monitored_cq_zones_vars[context_menu_band].text():
                    actions['add_to_cq_zone'] = menu.addAction(f"Add Zone {cq_zone} to Monitored CQ Zones")
                else:
                    actions['remove_from_cq_zone'] = menu.addAction(f"Remove Zone {cq_zone} from Monitored CQ Zones")
            except ValueError:
                pass
        menu.addSeparator()

        # QRZ.com
        actions['qrz_com_for_wanted_callsign'] = menu.addAction(f"Open QRZ.com for {callsign}")
        menu.addSeparator()

        # Copy message
        actions['copy_message'] = menu.addAction("Copy message to Clipboard")

        # Show menu
        if hasattr(widget, 'viewport'):
            action = menu.exec(widget.viewport().mapToGlobal(position))
        else:
            action = menu.exec(widget.mapToGlobal(position))

        if action is None:
            return

        # Handle actions
        if action == actions.get('copy_message'):
            if formatted_message:
                self.main_gui.copy_message_to_clipboard(formatted_message)
        else:
            update_actions = {
                'remove_entry_from_worked_history': lambda: self.main_gui.remove_worked_callsign(callsign, history_band),
                'remove_callsign_from_worked_history': lambda: self.main_gui.remove_worked_callsign(callsign),
                'add_callsign_to_wanted': lambda: self.main_gui.update_var(self.main_gui.wanted_callsigns_vars[context_menu_band], callsign),
                'remove_callsign_from_wanted': lambda: self.main_gui.update_var(self.main_gui.wanted_callsigns_vars[context_menu_band], callsign, "remove"),
                'qrz_com_for_wanted_callsign': lambda: self.main_gui.open_qrz_com(callsign),
                'replace_wanted_with_callsign': lambda: self.main_gui.update_var(self.main_gui.wanted_callsigns_vars[context_menu_band], callsign, "replace"),
                'add_callsign_to_monitored': lambda: self.main_gui.update_var(self.main_gui.monitored_callsigns_vars[context_menu_band], callsign),
                'remove_callsign_from_monitored': lambda: self.main_gui.update_var(self.main_gui.monitored_callsigns_vars[context_menu_band], callsign, "remove"),
                'add_callsign_to_excluded': lambda: self.main_gui.update_var(self.main_gui.excluded_callsigns_vars[context_menu_band], callsign),
                'add_callsign_to_temp_excluded': lambda: self.main_gui.show_exclusion_time_dialog(callsign),
                'remove_callsign_from_excluded': lambda: self.main_gui.update_var(self.main_gui.excluded_callsigns_vars[context_menu_band], callsign, "remove"),
                'add_directed_to_wanted': lambda: self.main_gui.update_var(self.main_gui.wanted_callsigns_vars[context_menu_band], directed),
                'remove_directed_from_wanted': lambda: self.main_gui.update_var(self.main_gui.wanted_callsigns_vars[context_menu_band], directed, "remove"),
                'replace_wanted_with_directed': lambda: self.main_gui.update_var(self.main_gui.wanted_callsigns_vars[context_menu_band], directed, "replace"),
                'add_directed_to_monitored': lambda: self.main_gui.update_var(self.main_gui.monitored_callsigns_vars[context_menu_band], directed),
                'remove_directed_from_monitored': lambda: self.main_gui.update_var(self.main_gui.monitored_callsigns_vars[context_menu_band], directed, "remove"),
                'qrz_com_for_directed_callsign': lambda: self.main_gui.open_qrz_com(directed),
                'add_to_cq_zone': lambda: self.main_gui.update_var(self.main_gui.monitored_cq_zones_vars[context_menu_band], cq_zone),
                'remove_from_cq_zone': lambda: self.main_gui.update_var(self.main_gui.monitored_cq_zones_vars[context_menu_band], cq_zone, "remove"),
            }

            for key, act in actions.items():
                if action == act:
                    update_func = update_actions.get(key)
                    if update_func:
                        update_func()
                        break