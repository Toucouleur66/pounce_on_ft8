import xml.etree.ElementTree as ET
import datetime
from collections import OrderedDict
import json
import os

from shapely.geometry import shape, Point
from shapely.ops import unary_union

from constants import CURRENT_DIR  

from logger import get_logger

log = get_logger(__name__)

class CallsignLookup:
    def __init__(
            self,
            xml_file_path           = f"{CURRENT_DIR}/cty.xml",
            cq_zones_geojson_path  = f"{CURRENT_DIR}/cq-zones.geojson",
            cache_file              = f"{CURRENT_DIR}/lookup_cache.json",              
            cache_size             = 1_0_00,
        ):
        self.callsign_exceptions = {}
        self.prefixes             = {}
        self.entities            = {}
        self.invalid_operations  = {}
        self.zone_exceptions     = {}

        self.cache               = OrderedDict()
        self.cache_size          = cache_size
        self.cache_file           = cache_file

        self.load_clublog_xml(xml_file_path)

        self.zone_polygons = self.load_cq_zones(cq_zones_geojson_path)

        self.load_cache_from_disk()

    def load_cache_from_disk(self):
        """
            Loads the cache from self.cache_file if it exists.
            Reconstructs date fields from ISO8601 strings, and stores them in self.cache.
        """
        if not os.path.exists(self.cache_file):
            return  # no existing cache

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log.error(f"Failed to load cache file '{self.cache_file}': {e}")
            return

        # 'data' is a dict: { callsign: {...}, callsign2: {...}, ... }
        # Rebuild into an OrderedDict
        for callsign, info in data.items():
            # Convert date fields back to datetime if they exist
            deserialized = self._deserialize_info(info)
            self.cache[callsign] = deserialized

        for k in list(self.cache.keys()):
            self.cache.move_to_end(k)

        log.info(f"File {self.cache_file} loading is complete with {len(self.cache)} entries.")

    def save_cache(self):
        """
            Saves the in-memory self.cache to a JSON file on disk.
            This must be called explicitly if you want to persist the updated data.
        """
        # Convert the OrderedDict to a normal dict for JSON
        data_to_save = {}
        for callsign, info in self.cache.items():
            data_to_save[callsign] = self._serialize_info(info)

        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2)
            # log.info(f"Cache file {self.cache_file} saved with {len(self.cache)} entries")
        except Exception as e:
            log.error(f"Failed to save cache to {self.cache_file}: {e}")

    def _serialize_info(self, info: dict) -> dict:
        """
            Convert any non-JSON-serializable fields (e.g., datetime) into strings.
            Returns a JSON-friendly dict
        """
        # Make a shallow copy so we don't mutate the original
        safe_dict = {}
        for k, v in info.items():
            if isinstance(v, datetime.datetime):
                # store as ISO8601 string
                safe_dict[k] = v.isoformat()
            else:
                safe_dict[k] = v
        return safe_dict

    def _deserialize_info(self, info: dict) -> dict:
        """
            Convert serialized fields (like ISO8601 date strings) back into datetime objects if needed. Returns a Python dict with corrected fields.
        """
        new_dict = {}
        for k, v in info.items():
            if isinstance(v, str):
                # Attempt to parse if it looks like an ISO date
                # We'll just do a quick check
                if self._looks_like_iso8601(v):
                    try:
                        new_dict[k] = datetime.datetime.fromisoformat(v)
                        continue
                    except ValueError:
                        pass
            new_dict[k] = v
        return new_dict

    def _looks_like_iso8601(self, s: str) -> bool:
        if len(s) >= 10 and s[4] == '-':
            return True
        return False

    def load_clublog_xml(self, xml_file_path):
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()

            exceptions_elem = root.find('exceptions')
            for exception in exceptions_elem.findall('exception'):
                call_elem = exception.find('call')
                if call_elem is None:
                    continue  
                call = call_elem.text.upper()

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
                start = self.parse_date(start_elem.text) if start_elem is not None else None

                end_elem = exception.find('end')
                end = self.parse_date(end_elem.text) if end_elem is not None else None

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
                if call not in self.callsign_exceptions:
                    self.callsign_exceptions[call] = []
                self.callsign_exceptions[call].append(exception_data)

            invalid_elem = root.find('invalid_operations')
            for invalid_op in invalid_elem.findall('invalid'):
                call_elem = invalid_op.find('call')
                if call_elem is None:
                    continue
                call = call_elem.text.upper()
                start_elem = invalid_op.find('start')
                end_elem = invalid_op.find('end')
                start = self.parse_date(start_elem.text) if start_elem is not None else None
                end = self.parse_date(end_elem.text) if end_elem is not None else None
                data = {'start': start, 'end': end}
                if call not in self.invalid_operations:
                    self.invalid_operations[call] = []
                self.invalid_operations[call].append(data)

            zone_exceptions_elem = root.find('zone_exceptions')
            for zone_exception in zone_exceptions_elem.findall('zone_exception'):
                call_elem = zone_exception.find('call')
                if call_elem is None:
                    continue
                call = call_elem.text.upper()

                zone_elem = zone_exception.find('zone')
                if zone_elem is None:
                    continue
                cqz = int(zone_elem.text)
                self.zone_exceptions[call] = cqz

            prefixes_elem = root.find('prefixes')
            for prefix_elem in prefixes_elem.findall('prefix'):
                call_elem = prefix_elem.find('call')
                if call_elem is None:
                    continue
                call = call_elem.text.upper()

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
                start = self.parse_date(start_elem.text) if start_elem is not None else None

                end_elem = prefix_elem.find('end')
                end = self.parse_date(end_elem.text) if end_elem is not None else None

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
                self.prefixes.setdefault(call, []).append(prefix_data)

            entities_elem = root.find('entities')
            for entity in entities_elem.findall('entity'):
                adif_elem = entity.find('adif')
                if adif_elem is None:
                    continue
                adif = int(adif_elem.text)

                name_elem = entity.find('name')
                name = name_elem.text if name_elem is not None else ''

                prefix_elem = entity.find('prefix')
                prefix_str = prefix_elem.text if prefix_elem is not None else ''

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
                start = self.parse_date(start_elem.text) if start_elem is not None else None

                end_elem = entity.find('end')
                end = self.parse_date(end_elem.text) if end_elem is not None else None

                entity_data = {
                    'name': name,
                    'prefix': prefix_str,
                    'deleted': deleted,
                    'cqz': cqz,
                    'cont': cont,
                    'lat': lat,
                    'long': longitude,
                    'start': start,
                    'end': end,
                }
                self.entities[adif] = entity_data

                expanded_prefixes = self.expand_prefixes(prefix_str)
                for prefix in expanded_prefixes:
                    prefix = prefix.upper()
                    prefix_data = entity_data.copy()
                    prefix_data['call'] = prefix
                    self.prefixes.setdefault(prefix, []).append(prefix_data)

            log.info(f"File {xml_file_path} loading is complete.")
        except Exception as e:
            log.error(f"Fail to load file: {e}")

    def expand_prefixes(self, prefix_str):
        prefixes = []
        parts = prefix_str.replace(',', ' ').split()
        for part in parts:
            if '-' in part:
                start, end = part.split('-')
                prefixes.extend(self.expand_prefix_range(start.strip().upper(), end.strip().upper()))
            else:
                prefixes.append(part.strip().upper())
        return prefixes

    def expand_prefix_range(self, start, end):
        prefixes = []
        if len(start) != len(end):
            return [start.upper(), end.upper()]
        else:
            common_part = start[:-1]
            start_char = start[-1]
            end_char = end[-1]
            for c in range(ord(start_char.upper()), ord(end_char.upper()) + 1):
                prefixes.append((common_part + chr(c)).upper())
        return prefixes

    def parse_date(self, date_str):
        try:
            return datetime.datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=datetime.timezone.utc)
        except Exception as e:
            log.error(f"Fail to extract date '{date_str}': {e}")
            return None

    def load_cq_zones(self, geojson_path: str):
        """
            Load CQ zone polygons from a local GeoJSON file,
            fix invalid polygons if needed, and return a list of (zone_id, fixed_polygon).
        """
        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            log.error(f"Failed to load {geojson_path}: {e}")
            return []

        zone_polygons = []
        for feature in data.get("features", []):
            zone_id = feature.get("properties", {}).get("cq_zone_number")
            geom = shape(feature.get("geometry", {}))
            if not geom.is_valid:
                geom = geom.buffer(0)
            zone_polygons.append((zone_id, geom))

        log.info(f"File {geojson_path} loading is complete.")

        return zone_polygons

    def locator_to_lat_lon_partial(self, grid: str):
        """
            Decodes a 2-, 4-, or 6-character locator into (lat, lon), 
            placing the coordinate in the center of the corresponding area.
        """
        grid = grid.strip().upper()
        if len(grid) < 2:
            raise ValueError("Locator must have >= 2 characters (e.g. AB)")

        # Field
        field_lon = (ord(grid[0]) - ord('A')) * 20 - 180
        field_lat = (ord(grid[1]) - ord('A')) * 10 - 90
        lon = field_lon
        lat = field_lat

        # If 4+ chars => decode square
        if len(grid) >= 4:
            square_lon = int(grid[2]) * 2
            square_lat = int(grid[3]) * 1
            lon += square_lon
            lat += square_lat
        else:
            # Only 2 chars => center of 10° x 20°
            lon += 10.0
            lat += 5.0
            return (lat, lon)

        # If 6+ chars => decode subsquare
        if len(grid) >= 6:
            subsq_lon = (ord(grid[4]) - ord('A')) * (2.0 / 24.0)
            subsq_lat = (ord(grid[5]) - ord('A')) * (1.0 / 24.0)
            lon += subsq_lon
            lat += subsq_lat
            # Center offset for final cell
            lon += (2.0/24.0)/2.0
            lat += (1.0/24.0)/2.0
        else:
            # Exactly 4 chars => center of 1° x 2°
            lon += 1.0
            lat += 0.5

        return (lat, lon)

    def lat_lon_to_cq_zone(self, lat: float, lon: float):
        """
            Returns the zone_id if the point is contained 
            in a polygon from self.zone_polygons, else None.
        """
        pt = Point(lon, lat)
        for (zone_id, poly) in self.zone_polygons:
            if poly.contains(pt):
                return zone_id
        return None

    def grid_to_cq_zone(self, grid: str):
        """
            High-level function:
            1) Convert a Maidenhead locator (2,4,6 chars) to lat/lon (center).
            2) Return (lat, lon, zone)
        """
        lat, lon = self.locator_to_lat_lon_partial(grid)
        zone = self.lat_lon_to_cq_zone(lat, lon)
        return (lat, lon, zone)

    def lookup_callsign(
            self,
            callsign,
            grid = None,
            date = None,
            enable_cache = True
        ):
        try:
            callsign = callsign.strip().upper()

            if callsign in self.cache and date is None:
                cached_info = self.cache[callsign]
                if grid is not None:
                    lat, lon, new_zone = self.grid_to_cq_zone(grid)
                    if new_zone is not None and cached_info.get('cqz') != new_zone:
                        cached_info['cqz'] = new_zone
                        self.cache.move_to_end(callsign)
                        if new_zone:
                            self.save_cache()
                return cached_info
            
            if date is None:
                date = datetime.datetime.now(datetime.timezone.utc)
            
            lookup_result = None

            if callsign in self.invalid_operations:
                invalid_data_list = self.invalid_operations[callsign]
                if isinstance(invalid_data_list, bool):
                    log.debug(f"{callsign} is invalid for date {date}")
                    return {}
                for inv_data in (invalid_data_list if isinstance(invalid_data_list, list) else [invalid_data_list]):
                    if self.is_valid_for_date(inv_data, date):
                        log.debug(f"{callsign} is invalid for date {date}")
                        return {}
                    
            if callsign in self.callsign_exceptions:
                for exception_data in self.callsign_exceptions[callsign]:
                    if self.is_valid_for_date(exception_data, date):
                        lookup_result = exception_data
                        break

            if lookup_result is None:
                sorted_prefixes = sorted(self.prefixes.keys(), key=lambda x: -len(x))
                for prefix in sorted_prefixes:
                    if callsign.startswith(prefix):
                        for entry in self.prefixes[prefix]:
                            if self.is_valid_for_date(entry, date):
                                lookup_result = entry
                                break
                        if lookup_result:
                            break

            if lookup_result is None:
                log.debug(f"No information found for {callsign}.")
                lookup_result = {}

            if grid is not None and lookup_result:
                lat, lon, new_zone = self.grid_to_cq_zone(grid)
                if new_zone is not None and lookup_result.get('cqz') != new_zone:
                    lookup_result['cqz'] = new_zone
                    self.cache[callsign] = lookup_result
                    if len(self.cache) > self.cache_size:
                        self.cache.popitem(last=False)
                    self.save_cache()

            if lookup_result and enable_cache:
                self.cache[callsign] = lookup_result
                if len(self.cache) > self.cache_size:
                    self.cache.popitem(last=False)
                self.save_cache()

            return lookup_result
        
        except Exception as e:
            log.error(f"Fail to extract '{callsign}': {e}")
            return None

    def is_valid_for_date(self, info, date):
        start = info.get('start')
        end = info.get('end')
        if start and date < start:
            return False
        if end and date > end:
            return False
        return True
