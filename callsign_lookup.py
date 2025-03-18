import xml.etree.ElementTree as ET
import datetime
import json
import os
import threading

from collections import OrderedDict
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from functools import lru_cache

from constants import CURRENT_DIR
from logger import get_logger

log = get_logger(__name__)

@lru_cache(maxsize=5000)
class CallsignLookup:
    def __init__(
        self,
        xml_file_path=f"{CURRENT_DIR}/cty.xml",
        cq_zones_geojson_path=f"{CURRENT_DIR}/cq-zones.geojson",
        cache_file=f"{CURRENT_DIR}/lookup_cache.json",
        cache_size=1_000,
        lookup_debug=False
    ):
        self.callsign_exceptions = {}
        self.prefixes = {}
        self.entities = {}
        self.invalid_operations = {}
        self.zone_exceptions = {}

        self.xml_file_path = xml_file_path
        self.cq_zones_geojson_path = cq_zones_geojson_path
        self.cache_file = cache_file
        self.cache_size = cache_size
        self.lookup_debug = lookup_debug

        self.sorted_prefixes = []
        self.cache = OrderedDict()
        self.zone_polygons = []

        self.cache_lock = threading.Lock()

        self.load_clublog_xml(self.xml_file_path)
        self.load_cache_from_disk()
        self.zone_polygons = self.load_cq_zones(self.cq_zones_geojson_path)

    def load_cache_from_disk(self):
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log.error(f"Failed to load cache file '{self.cache_file}': {e}")
            return

        for callsign, info in data.items():
            deserialized = self._deserialize_info(info)
            self.cache[callsign] = deserialized

        for k in list(self.cache.keys()):
            self.cache.move_to_end(k)

        log.info(
            f"File {self.cache_file} loading is complete with {len(self.cache)} entries."
        )

    def save_cache(self):
        data_to_save = {}
        with self.cache_lock:  # On protège l'accès en lecture
            for callsign, info in self.cache.items():
                data_to_save[callsign] = self._serialize_info(info)

        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save cache to {self.cache_file}: {e}")

    def _serialize_info(self, info: dict) -> dict:
        safe_dict = {}
        for k, v in info.items():
            if isinstance(v, datetime.datetime):
                safe_dict[k] = v.isoformat()
            else:
                safe_dict[k] = v
        return safe_dict

    def _deserialize_info(self, info: dict) -> dict:
        new_dict = {}
        for k, v in info.items():
            if isinstance(v, str) and len(v) >= 10 and v[4] == '-':
                try:
                    new_dict[k] = datetime.datetime.fromisoformat(v)
                    continue
                except ValueError:
                    pass
            new_dict[k] = v
        return new_dict

    def load_clublog_xml(self, xml_file_path):
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()

            exceptions_elem = root.find("exceptions")
            if exceptions_elem is not None:
                for exception in exceptions_elem.findall("exception"):
                    call_elem = exception.find("call")
                    if call_elem is None:
                        continue
                    call = call_elem.text.upper()

                    entity_elem = exception.find("entity")
                    entity_name = entity_elem.text if entity_elem is not None else ""

                    adif_elem = exception.find("adif")
                    adif = int(adif_elem.text) if adif_elem is not None else None

                    cqz_elem = exception.find("cqz")
                    cqz = int(cqz_elem.text) if cqz_elem is not None else None

                    cont_elem = exception.find("cont")
                    cont = cont_elem.text if cont_elem is not None else ""

                    lat_elem = exception.find("lat")
                    lat = float(lat_elem.text) if lat_elem is not None else None

                    long_elem = exception.find("long")
                    longitude = float(long_elem.text) if long_elem is not None else None

                    start_elem = exception.find("start")
                    start = self.parse_date(start_elem.text) if start_elem is not None else None

                    end_elem = exception.find("end")
                    end = self.parse_date(end_elem.text) if end_elem is not None else None

                    exception_data = {
                        "call": call,
                        "entity": entity_name,
                        "adif": adif,
                        "cqz": cqz,
                        "cont": cont,
                        "lat": lat,
                        "long": longitude,
                        "start": start,
                        "end": end,
                    }
                    self.callsign_exceptions.setdefault(call, []).append(exception_data)

            invalid_elem = root.find("invalid_operations")
            if invalid_elem is not None:
                for invalid_op in invalid_elem.findall("invalid"):
                    call_elem = invalid_op.find("call")
                    if call_elem is None:
                        continue
                    call = call_elem.text.upper()

                    start_elem = invalid_op.find("start")
                    end_elem = invalid_op.find("end")
                    start = self.parse_date(start_elem.text) if start_elem is not None else None
                    end = self.parse_date(end_elem.text) if end_elem is not None else None

                    data = {"start": start, "end": end}
                    self.invalid_operations.setdefault(call, []).append(data)

            zone_exceptions_elem = root.find("zone_exceptions")
            if zone_exceptions_elem is not None:
                for zone_exception in zone_exceptions_elem.findall("zone_exception"):
                    call_elem = zone_exception.find("call")
                    zone_elem = zone_exception.find("zone")
                    if call_elem is None or zone_elem is None:
                        continue

                    call = call_elem.text.upper()
                    cqz = int(zone_elem.text)
                    self.zone_exceptions[call] = cqz

            prefixes_elem = root.find("prefixes")
            if prefixes_elem is not None:
                for prefix_elem in prefixes_elem.findall("prefix"):
                    call_elem = prefix_elem.find("call")
                    if call_elem is None:
                        continue
                    call = call_elem.text.upper()

                    entity_elem = prefix_elem.find("entity")
                    entity_name = entity_elem.text if entity_elem is not None else ""

                    adif_elem = prefix_elem.find("adif")
                    adif = int(adif_elem.text) if adif_elem is not None else None

                    cqz_elem = prefix_elem.find("cqz")
                    cqz = int(cqz_elem.text) if cqz_elem is not None else None

                    cont_elem = prefix_elem.find("cont")
                    cont = cont_elem.text if cont_elem is not None else ""

                    lat_elem = prefix_elem.find("lat")
                    lat = float(lat_elem.text) if lat_elem is not None else None

                    long_elem = prefix_elem.find("long")
                    longitude = float(long_elem.text) if long_elem is not None else None

                    start_elem = prefix_elem.find("start")
                    end_elem = prefix_elem.find("end")
                    start = self.parse_date(start_elem.text) if start_elem is not None else None
                    end = self.parse_date(end_elem.text) if end_elem is not None else None

                    prefix_data = {
                        "call": call,
                        "entity": entity_name,
                        "adif": adif,
                        "cqz": cqz,
                        "cont": cont,
                        "lat": lat,
                        "long": longitude,
                        "start": start,
                        "end": end,
                    }
                    self.prefixes.setdefault(call, []).append(prefix_data)

            entities_elem = root.find("entities")
            if entities_elem is not None:
                for entity in entities_elem.findall("entity"):
                    adif_elem = entity.find("adif")
                    if adif_elem is None:
                        continue
                    adif = int(adif_elem.text)

                    name_elem = entity.find("name")
                    name = name_elem.text if name_elem is not None else ""

                    prefix_elem = entity.find("prefix")
                    prefix_str = prefix_elem.text if prefix_elem is not None else ""

                    deleted_elem = entity.find("deleted")
                    deleted = deleted_elem is not None and (deleted_elem.text == "true")

                    cqz_elem = entity.find("cqz")
                    cqz = int(cqz_elem.text) if cqz_elem is not None else None

                    cont_elem = entity.find("cont")
                    cont = cont_elem.text if cont_elem is not None else ""

                    lat_elem = entity.find("lat")
                    lat = float(lat_elem.text) if lat_elem is not None else None

                    long_elem = entity.find("long")
                    longitude = float(long_elem.text) if long_elem is not None else None

                    start_elem = entity.find("start")
                    start = self.parse_date(start_elem.text) if start_elem is not None else None
                    end_elem = entity.find("end")
                    end = self.parse_date(end_elem.text) if end_elem is not None else None

                    entity_data = {
                        "name": name,
                        "prefix": prefix_str,
                        "deleted": deleted,
                        "cqz": cqz,
                        "cont": cont,
                        "lat": lat,
                        "long": longitude,
                        "start": start,
                        "end": end,
                    }
                    self.entities[adif] = entity_data

                    # On étend la liste de préfixes
                    expanded_prefixes = self.expand_prefixes(prefix_str)
                    for pfx in expanded_prefixes:
                        pfx = pfx.upper()
                        pfx_data = entity_data.copy()
                        pfx_data["call"] = pfx
                        self.prefixes.setdefault(pfx, []).append(pfx_data)

            log.info(f"File {xml_file_path} loading is complete.")

            self.sorted_prefixes = sorted(self.prefixes.keys(), key=lambda x: -len(x))

        except Exception as e:
            log.error(f"Fail to load file: {e}")

    def expand_prefixes(self, prefix_str):
        prefixes = []
        parts = prefix_str.replace(",", " ").split()
        for part in parts:
            if "-" in part:
                start, end = part.split("-")
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
            return datetime.datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=datetime.timezone.utc
            )
        except Exception as e:
            log.error(f"Fail to extract date '{date_str}': {e}")
            return None

    def load_cq_zones(self, geojson_path: str):
        from shapely.geometry import shape

        if not os.path.exists(geojson_path):
            log.error(f"GeoJSON not found: {geojson_path}")
            return []

        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
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
        grid = grid.strip().upper()
        if len(grid) < 2:
            raise ValueError("Locator must have >= 2 characters (e.g. AB)")

        field_lon = (ord(grid[0]) - ord("A")) * 20 - 180
        field_lat = (ord(grid[1]) - ord("A")) * 10 - 90
        lon = field_lon
        lat = field_lat

        if len(grid) >= 4:
            square_lon = int(grid[2]) * 2
            square_lat = int(grid[3]) * 1
            lon += square_lon
            lat += square_lat
        else:
            lon += 10.0
            lat += 5.0
            return (lat, lon)

        if len(grid) >= 6:
            subsq_lon = (ord(grid[4]) - ord("A")) * (2.0 / 24.0)
            subsq_lat = (ord(grid[5]) - ord("A")) * (1.0 / 24.0)
            lon += subsq_lon
            lat += subsq_lat
            lon += (2.0 / 24.0) / 2.0
            lat += (1.0 / 24.0) / 2.0
        else:
            lon += 1.0
            lat += 0.5

        return (lat, lon)

    def lat_lon_to_cq_zone(self, lat: float, lon: float):
        pt = Point(lon, lat)
        for zone_id, poly in self.zone_polygons:
            if poly.contains(pt):
                return zone_id
        return None

    def grid_to_cq_zone(self, grid: str):
        lat, lon = self.locator_to_lat_lon_partial(grid)
        zone = self.lat_lon_to_cq_zone(lat, lon)
        return (lat, lon, zone)

    def lookup_callsign(
        self, callsign, grid=None, date=None, enable_cache=True
    ):
        try:
            callsign = callsign.strip().upper()
            if date is None:
                date = datetime.datetime.now(datetime.timezone.utc)

            if callsign in self.invalid_operations:
                for inv_data in self.invalid_operations[callsign]:
                    if self.is_valid_for_date(inv_data, date):
                        if self.lookup_debug:
                            if self.lookup_debug:
                                log.debug(f"{callsign} is invalid for date {date}")
                        return {}

            if callsign in self.callsign_exceptions:
                for exception_data in self.callsign_exceptions[callsign]:
                    if self.is_valid_for_date(exception_data, date):
                        result = exception_data
                        self._update_cache(callsign, result, enable_cache)
                        return result

            result = None
            for prefix in self.sorted_prefixes:
                if callsign.startswith(prefix):
                    for entry in self.prefixes.get(prefix, []):
                        if self.is_valid_for_date(entry, date):
                            result = entry
                            break
                if result:
                    break

            if not result:
                if self.lookup_debug:
                    log.debug(f"No information found for {callsign}.")
                result = {}

            if grid and result:
                lat, lon, new_zone = self.grid_to_cq_zone(grid)
                if new_zone is not None and result.get("cqz") != new_zone:
                    result["cqz"] = new_zone

            self._update_cache(callsign, result, enable_cache)
            return result

        except Exception as e:
            log.error(f"Fail to extract '{callsign}': {e}")
            return None

    def _update_cache(self, callsign, info, enable_cache):
        if enable_cache and info is not None:
            with self.cache_lock:
                self.cache[callsign] = info
                if len(self.cache) > self.cache_size:
                    self.cache.popitem(last=False)  

    def is_valid_for_date(self, info, date):
        start = info.get("start")
        end = info.get("end")
        if start and date < start:
            return False
        if end and date > end:
            return False
        return True
