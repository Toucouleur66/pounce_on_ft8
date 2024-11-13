# callsign_lookup.py

import xml.etree.ElementTree as ET
import datetime

from collections import OrderedDict


from constants import (    
    CURRENT_DIR
)

class CallsignLookup:
    def __init__(self):
        self.callsign_exceptions       = {}
        self.prefixes                   = {}
        self.entities                  = {}
        self.invalid_operations        = {}
        self.zone_exceptions           = {}

        self.cache                      = OrderedDict()
        self.cache_size                 = 2_00

        self.load_clublog_xml()

    def load_clublog_xml(self, xml_file_path=f"{CURRENT_DIR}/cty.xml"):
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()

            entities_elem = root.find('entities')
            for entity in entities_elem.findall('entity'):
                adif_elem = entity.find('adif')
                if adif_elem is None:
                    continue  
                adif = int(adif_elem.text)

                name_elem = entity.find('name')
                name = name_elem.text if name_elem is not None else ''

                prefix_elem = entity.find('prefix')
                prefix = prefix_elem.text if prefix_elem is not None else ''

                deleted_elem = entity.find('deleted')
                deleted = (deleted_elem.text == 'true') if deleted_elem is not None else False

                cqz_elem = entity.find('cqz')
                cqz = int(cqz_elem.text) if cqz_elem is not None else None

                cont_elem = entity.find('cont')
                cont = cont_elem.text if cont_elem is not None else ''

                lat_elem = entity.find('lat')
                lat = float(lat_elem.text) if lat_elem is not None else None

                long_elem = entity.find('long')
                longitude = float(long_elem.text) if long_elem is not None else None

                start_elem = entity.find('start')
                start = self._parse_date(start_elem.text) if start_elem is not None else None

                end_elem = entity.find('end')
                end = self._parse_date(end_elem.text) if end_elem is not None else None

                entity_data = {
                    'name': name,
                    'prefix': prefix,
                    'deleted': deleted,
                    'cqz': cqz,
                    'cont': cont,
                    'lat': lat,
                    'long': longitude,
                    'start': start,
                    'end': end,
                }
                self.entities[adif] = entity_data

            exceptions_elem = root.find('exceptions')
            for exception in exceptions_elem.findall('exception'):
                call_elem = exception.find('call')
                if call_elem is None:
                    continue  
                call = call_elem.text

                entity_elem = exception.find('entity')
                entity_name = entity_elem.text if entity_elem is not None else ''

                adif_elem = exception.find('adif')
                adif = int(adif_elem.text) if adif_elem is not None else None

                cqz_elem = exception.find('cqz')
                cqz = int(cqz_elem.text) if cqz_elem is not None else None

                cont_elem = exception.find('cont')
                cont = cont_elem.text if cont_elem is not None else ''

                lat_elem = exception.find('lat')
                lat = float(lat_elem.text) if lat_elem is not None else None

                long_elem = exception.find('long')
                longitude = float(long_elem.text) if long_elem is not None else None

                start_elem = exception.find('start')
                start = self._parse_date(start_elem.text) if start_elem is not None else None

                end_elem = exception.find('end')
                end = self._parse_date(end_elem.text) if end_elem is not None else None

                exception_data = {
                    'call': call,
                    'entity': entity_name,
                    'adif': adif,
                    'cqz': cqz,
                    'cont': cont,
                    'lat': lat,
                    'long': longitude,
                    'start': start,
                    'end': end,
                }
                self.callsign_exceptions[call] = exception_data

            prefixes_elem = root.find('prefixes')
            for prefix_elem in prefixes_elem.findall('prefix'):
                call_elem = prefix_elem.find('call')
                if call_elem is None:
                    continue
                call = call_elem.text

                entity_elem = prefix_elem.find('entity')
                entity_name = entity_elem.text if entity_elem is not None else ''

                adif_elem = prefix_elem.find('adif')
                adif = int(adif_elem.text) if adif_elem is not None else None

                cqz_elem = prefix_elem.find('cqz')
                cqz = int(cqz_elem.text) if cqz_elem is not None else None

                cont_elem = prefix_elem.find('cont')
                cont = cont_elem.text if cont_elem is not None else ''

                lat_elem = prefix_elem.find('lat')
                lat = float(lat_elem.text) if lat_elem is not None else None

                long_elem = prefix_elem.find('long')
                longitude = float(long_elem.text) if long_elem is not None else None

                start_elem = prefix_elem.find('start')
                start = self._parse_date(start_elem.text) if start_elem is not None else None

                end_elem = prefix_elem.find('end')
                end = self._parse_date(end_elem.text) if end_elem is not None else None

                prefix_data = {
                    'call': call,
                    'entity': entity_name,
                    'adif': adif,
                    'cqz': cqz,
                    'cont': cont,
                    'lat': lat,
                    'long': longitude,
                    'start': start,
                    'end': end,
                }
                self.prefixes[call] = prefix_data

            invalid_elem = root.find('invalid_operations')
            for invalid_op in invalid_elem.findall('invalid'):
                call_elem = invalid_op.find('call')
                if call_elem is None:
                    continue
                call = call_elem.text
                self.invalid_operations[call] = True

            zone_exceptions_elem = root.find('zone_exceptions')
            for zone_exception in zone_exceptions_elem.findall('zone_exception'):
                call_elem = zone_exception.find('call')
                if call_elem is None:
                    continue
                call = call_elem.text

                zone_elem = zone_exception.find('zone')
                if zone_elem is None:
                    continue
                cqz = int(zone_elem.text)
                self.zone_exceptions[call] = cqz

            print(f"File {xml_file_path} loading is complete.")
        except Exception as e:
            print(f"Fail to load file: {e}")

    def _parse_date(self, date_str):
        try:
            return datetime.datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=datetime.timezone.utc)
        except Exception as e:
            print(f"Fail to extract date '{date_str}': {e}")
            return None

    def lookup_callsign(self, callsign, date=None):
        try:
            callsign = callsign.strip().upper()
            if date is None:
                date = datetime.datetime.now(datetime.timezone.utc)

            if callsign in self.cache:
                self.cache.move_to_end(callsign)
                return self.cache[callsign]

            lookup_result = None

            if callsign in self.callsign_exceptions:
                exception = self.callsign_exceptions[callsign]
                if self._is_valid_for_date(exception, date):
                    lookup_result = exception

            elif callsign in self.invalid_operations:
                print(f"{callsign} set as invalid.")
                lookup_result = None

            else:
                for prefix in sorted(self.prefixes.keys(), key=lambda x: -len(x)):
                    if callsign.startswith(prefix):
                        prefix_info = self.prefixes[prefix]
                        if self._is_valid_for_date(prefix_info, date):
                            lookup_result = prefix_info
                            break

            if lookup_result is None:
                print(f"No information found for {callsign}.")

            self.cache[callsign] = lookup_result
            if len(self.cache) > self.cache_size:
                self.cache.popitem(last=False)

            return lookup_result
        
        except Exception as e:
                print(f"Fail to extract '{callsign}': {e}")
                return None

    def _is_valid_for_date(self, info, date):
        start = info.get('start')
        end = info.get('end')
        if start and date < start:
            return False
        if end and date > end:
            return False
        return True
