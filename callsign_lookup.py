import xml.etree.ElementTree as ET
import datetime
import json
import os
import threading
import sys
import re

from collections import OrderedDict
from shapely.geometry import shape, Point, Polygon
from shapely.ops import unary_union

from functools import lru_cache

from utils import get_data_file_path, latlon_to_grid
from logger import get_logger

log = get_logger(__name__)

@lru_cache(maxsize=5000)
class CallsignLookup:
    def __init__(
        self,
        xml_file_path       = get_data_file_path("cty.xml"),
        # https://raw.githubusercontent.com/logocomune/go-cq-zone/refs/heads/main/data.go
        cq_zones_file_path  = get_data_file_path("cq-zones.go"),
        cache_file          = get_data_file_path("lookup_cache.json"),
        lotw_cache_file     = get_data_file_path("lotw_cache.json"),
        cty_dat_file        = get_data_file_path("CTY_WT_MOD.DAT"),
        cache_size         = 2_000,
        lookup_debug       = False
    ):
        self.callsign_exceptions = {}
        self.prefixes             = {}
        self.entities            = {}
        self.invalid_operations  = {}
        self.zone_exceptions     = {}
        self.cty_entities        = {}
        self.cty_prefixes         = {}
        self.cty_exact_calls     = {}

        self.xml_file_path        = xml_file_path
        self.cq_zones_file_path   = cq_zones_file_path
        self.cache_file           = cache_file
        self.lotw_cache_file      = lotw_cache_file
        self._cache_dirty         = False
        self.cty_dat_file         = cty_dat_file

        # Add destructor to save cache when object is destroyed
        import atexit
        atexit.register(self._save_cache_if_dirty)
        self.cache_size          = cache_size
        self.lookup_debug        = lookup_debug

        self.sorted_prefixes      = []
        self.cache               = OrderedDict()
        self.zone_polygons       = []
        self.lotw_cache          = {}

        self.cache_lock          = threading.Lock()
        self.zone_polygons       = self.load_cq_zones(self.cq_zones_file_path)

        self.load_clublog_xml(self.xml_file_path)
        self.load_cty_mod_dat(self.cty_dat_file)
        self.load_cache_from_disk()
        self.load_lotw_cache()

    def load_cache_from_disk(self):
        if not os.path.exists(self.cache_file):
            log.info(f"Cache file '{self.cache_file}' does not exist. Skipping load.")
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
            f"File {self.cache_file} loading is complete with {len(self.cache):,} entries."
        )

    def load_lotw_cache(self):
        if not os.path.exists(self.lotw_cache_file):
            log.warning(f"'{self.lotw_cache_file}' does not exist. Skipping load.")    
            return

        try:
            with open(self.lotw_cache_file, "r", encoding="utf-8") as f:
                self.lotw_cache = json.load(f)

            log.info(f"File {self.lotw_cache_file} loading is complete with {len(self.lotw_cache):,} entries.")                
        except Exception as e:
            log.error(f"Failed to load LoTW cache file '{self.lotw_cache_file}': {e}")
            self.lotw_cache = {}

    def save_cache(self):
        data_to_save = {}
        with self.cache_lock: 
            for callsign, info in self.cache.items():
                data_to_save[callsign] = self._serialize_info(info)

        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save cache to {self.cache_file}: {e}")

    def save_grid_update_to_cache(self):
        self._cache_dirty = True

    def _save_cache_if_dirty(self):
        if hasattr(self, '_cache_dirty') and self._cache_dirty:
            try:
                self.save_cache()
                self._cache_dirty = False
            except Exception:
                pass  

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
            # Keep grid_updated as string, don't convert to datetime
            if k == 'grid_updated':
                new_dict[k] = v
            elif isinstance(v, str) and len(v) >= 10 and v[4] == '-':
                try:
                    new_dict[k] = datetime.datetime.fromisoformat(v)
                    continue
                except ValueError:
                    pass
            else:
                new_dict[k] = v
        return new_dict

    def load_clublog_xml(self, xml_file_path):
        if not os.path.exists(xml_file_path):
            log.info(f"Clublog XML file '{self.cache_file}' does not exist. Skipping load.")
            return
        
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
                        "entity": name,
                        "adif": adif,
                        "deleted": deleted,
                        "cqz": cqz,
                        "cont": cont,
                        "lat": lat,
                        "long": longitude,
                        "start": start,
                        "end": end,
                    }
                    self.entities[adif] = entity_data

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

    def load_cty_mod_dat(self, cty_dat_file):
        if not os.path.exists(cty_dat_file):
            log.info(f"CTY DAT file '{cty_dat_file}' does not exist. Skipping load.")
            return
        
        try:
            with open(cty_dat_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Remove comments and empty lines first
            cleaned_lines = []
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    cleaned_lines.append(line)
            
            # Join back and split by semicolons
            cleaned_content = '\n'.join(cleaned_lines)
            records = cleaned_content.split(';')
            
            for record in records:
                record = record.strip()
                if not record:
                    continue
                
                # Split the record into lines
                lines = [line.strip() for line in record.split('\n') if line.strip()]
                if not lines:
                    continue
                
                # Find the main country line (contains colons for the format)
                main_line = None
                prefix_lines = []
                
                for line in lines:
                    if ':' in line and line.count(':') >= 7:
                        main_line = line
                    else:
                        prefix_lines.append(line)
                
                if not main_line:
                    if self.lookup_debug:
                        log.debug(f"No main line found in record: {lines}")
                    continue
                
                # Parse main country information
                # Format: Country Name:CQ:ITU:Continent:Latitude:Longitude:GMT offset:Main prefix:
                try:
                    if self.lookup_debug:
                        log.debug(f"Processing main line: {main_line}")
                    parts = main_line.split(':')
                    if len(parts) < 8:
                        continue
                    
                    country_name = parts[0].strip()
                    cq_zone = int(parts[1]) if parts[1].strip() else None
                    itu_zone = int(parts[2]) if parts[2].strip() else None
                    continent = parts[3].strip()
                    latitude = float(parts[4]) if parts[4].strip() else None
                    longitude = -float(parts[5]) if parts[5].strip() else None  # CTY format: + for West, so negate
                    gmt_offset = float(parts[6]) if parts[6].strip() else None
                    main_prefix = parts[7].strip()
                    
                    # Create entity data
                    entity_data = {
                        'entity': country_name,
                        'call': main_prefix,
                        'cqz': cq_zone,
                        'itu': itu_zone,
                        'cont': continent,
                        'lat': latitude,
                        'long': longitude,
                        'gmt_offset': gmt_offset
                    }
                    
                    # Store main entity
                    self.cty_entities[main_prefix] = entity_data
                    
                    # Also add main prefix to the prefix list
                    self.cty_prefixes[main_prefix.upper()] = entity_data.copy()
                    
                    # Parse prefixes from prefix lines
                    prefixes = []
                    for line in prefix_lines:
                        # Remove trailing comma and spaces
                        line = line.rstrip(',').strip()
                        if line:
                            # Split by comma to get individual prefixes
                            line_prefixes = [p.strip() for p in line.split(',') if p.strip()]
                            prefixes.extend(line_prefixes)
                    
                    if self.lookup_debug and len(prefixes) > 0:
                        log.debug(f"Found {len(prefixes)} prefixes for {country_name}: {prefixes[:5]}")
                    
                    # Process each prefix
                    for prefix in prefixes:
                        if not prefix:
                            continue
                        
                        # Handle special prefixes with multiple overrides
                        # Format: =W1UL(4)[7]<32.93/97.25>~6.0~
                        base_prefix = prefix
                        override_data = entity_data.copy()
                        is_exact_call = False
                        
                        # Handle exact callsign match (starts with =)
                        if base_prefix.startswith('='):
                            base_prefix = base_prefix[1:]
                            is_exact_call = True
                        
                        # Parse all override patterns
                        working_prefix = base_prefix
                        
                        # Check for CQ zone override in parentheses: (4)
                        if '(' in working_prefix and ')' in working_prefix:
                            zone_match = working_prefix.find('(')
                            zone_end = working_prefix.find(')')
                            if zone_match != -1 and zone_end != -1:
                                zone_str = working_prefix[zone_match+1:zone_end]
                                try:
                                    override_data['cqz'] = int(zone_str)
                                except ValueError:
                                    pass
                                working_prefix = working_prefix[:zone_match] + working_prefix[zone_end+1:]
                        
                        # Check for ITU zone override in square brackets: [7]
                        if '[' in working_prefix and ']' in working_prefix:
                            bracket_match = working_prefix.find('[')
                            bracket_end = working_prefix.find(']')
                            if bracket_match != -1 and bracket_end != -1:
                                bracket_content = working_prefix[bracket_match+1:bracket_end]
                                # Check if it's coordinates (contains /) or just ITU zone
                                if '/' in bracket_content:
                                    try:
                                        lat_str, lon_str = bracket_content.split('/')
                                        override_data['lat'] = float(lat_str)
                                        override_data['long'] = -float(lon_str)  # CTY format: + for West, so negate
                                    except (ValueError, IndexError):
                                        pass
                                else:
                                    try:
                                        override_data['itu'] = int(bracket_content)
                                    except ValueError:
                                        pass
                                working_prefix = working_prefix[:bracket_match] + working_prefix[bracket_end+1:]
                        
                        # Check for lat/lon override in angle brackets: <32.93/97.25>
                        if '<' in working_prefix and '>' in working_prefix:
                            coord_match = working_prefix.find('<')
                            coord_end = working_prefix.find('>')
                            if coord_match != -1 and coord_end != -1:
                                coord_str = working_prefix[coord_match+1:coord_end]
                                try:
                                    lat_str, lon_str = coord_str.split('/')
                                    override_data['lat'] = float(lat_str)
                                    override_data['long'] = -float(lon_str)  # CTY format: + for West, so negate
                                except (ValueError, IndexError):
                                    pass
                                working_prefix = working_prefix[:coord_match] + working_prefix[coord_end+1:]
                        
                        # Check for GMT offset override in tildes: ~6.0~
                        if '~' in working_prefix:
                            first_tilde = working_prefix.find('~')
                            second_tilde = working_prefix.find('~', first_tilde + 1)
                            if first_tilde != -1 and second_tilde != -1:
                                offset_str = working_prefix[first_tilde+1:second_tilde]
                                try:
                                    override_data['gmt_offset'] = float(offset_str)
                                except ValueError:
                                    pass
                                working_prefix = working_prefix[:first_tilde] + working_prefix[second_tilde+1:]
                        
                        # Clean up the working prefix (remove any trailing characters)
                        base_prefix = working_prefix.strip()
                        
                        # Store prefix data
                        override_data['call'] = base_prefix
                        
                        if is_exact_call:
                            self.cty_exact_calls[base_prefix.upper()] = override_data
                        else:
                            self.cty_prefixes[base_prefix.upper()] = override_data
                
                except (ValueError, IndexError) as e:
                    log.debug(f"Error parsing CTY record: {e}")
                    continue
            
            log.info(f"File {cty_dat_file} loading is complete with {len(self.cty_entities):,} entities, {len(self.cty_prefixes):,} prefixes, and {len(self.cty_exact_calls):,} exact callsigns.")
            
            if self.lookup_debug and len(self.cty_entities) == 0:
                log.debug(f"No entities parsed. First few cleaned lines: {cleaned_lines[:5]}")
            
        except Exception as e:
            log.error(f"Failed to load CTY DAT file '{cty_dat_file}': {e}")

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

    def load_cq_zones(self, go_file_path: str):
        if os.path.exists(go_file_path):
            try:
                with open(go_file_path, 'r') as f:
                    content = f.read()
                
                zone_polygons = []
                
                zone_entries = re.split(r'(?=\{name: `)', content)[1:]  
                
                for entry in zone_entries:
                    number_match = re.search(r'number: (\d+)', entry)
                    if not number_match:
                        continue
                        
                    zone_number = int(number_match.group(1))                
                    polygon_match = re.search(r'polygon: \[]Coordinate\{(.+?)\}\}', entry, re.DOTALL)
                    if not polygon_match:
                        continue
                        
                    polygon_data = polygon_match.group(1)
                
                    coord_matches = re.findall(r'\{Lat: ([^,]+), Lng: ([^}]+)\}', polygon_data)
                    
                    coordinates = []
                    for lat_str, lng_str in coord_matches:
                        try:
                            lat = float(lat_str.strip())
                            lng = float(lng_str.strip())
                            coordinates.append((lng, lat))  
                        except ValueError:
                            continue
                    
                    if len(coordinates) >= 3: 
                        try:
                            polygon = Polygon(coordinates)
                            if not polygon.is_valid:
                                polygon = polygon.buffer(0) 
                            zone_polygons.append((zone_number, polygon))
                        except Exception as e:
                            log.debug(f"Error creating polygon for zone {zone_number}: {e}")
                            continue
                
                log.info(f"File {go_file_path} loading is complete with {len(zone_polygons)} zones.")
                return zone_polygons
            except Exception as e:
                log.warning(f"Failed to load Go zone data from {go_file_path}: {e}, falling back to GeoJSON")        

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
        
        # First try exact containment
        for zone_id, poly in self.zone_polygons:
            if poly.contains(pt):
                return zone_id
                
        # If not contained in any polygon, find the closest zone
        # This handles gaps in polygon boundaries
        closest_zone = None
        min_distance = float('inf')
        
        for zone_id, poly in self.zone_polygons:
            distance = pt.distance(poly)
            if distance < min_distance:
                min_distance = distance
                closest_zone = zone_id
                
        # Only use closest zone if it's reasonably close (within ~0.5 degrees)
        if min_distance < 0.5:
            return closest_zone
            
        return None

    def grid_to_cq_zone(self, grid: str):
        lat, lon = self.locator_to_lat_lon_partial(grid)
        zone = self.lat_lon_to_cq_zone(lat, lon)
        return zone

    def lookup_callsign(
        self, callsign, grid=None, date=None, enable_cache=True
    ):
        try:
            callsign = callsign.strip().upper()
            if date is None:
                date = datetime.datetime.now(datetime.timezone.utc)

            if enable_cache and callsign in self.cache:
                with self.cache_lock:
                    cached_result = self.cache[callsign].copy()
                    self.cache.move_to_end(callsign)
                    
                    if grid and cached_result:                    
                        cached_result["grid"] = grid
                        cached_result["grid_updated"] = date.strftime("%Y-%m-%d")
                        new_zone = self.grid_to_cq_zone(grid)
                        if new_zone is not None:
                            if cached_result.get("cqz") != new_zone:
                                cached_result["cqz"] = new_zone
                        self.cache[callsign] = cached_result
                        # Save cache to disk when grid is updated
                        self.save_grid_update_to_cache()
                    
                    # Update LoTW information in cached result
                    if callsign in self.lotw_cache:
                        cached_result['lotw'] = self.lotw_cache[callsign]
                    
                    if self.lookup_debug:
                        log.debug(f"Cache hit for {callsign}")
                    return cached_result

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
                        result = exception_data.copy()

                        if grid and result:
                            result["grid"] = grid
                            result["grid_updated"] = date.strftime("%Y-%m-%d")
                            new_zone = self.grid_to_cq_zone(grid)
                            if new_zone is not None and result.get("cqz") != new_zone:
                                result["cqz"] = new_zone
                        
                        # Add LoTW information if available
                        if callsign in self.lotw_cache:
                            result['lotw'] = self.lotw_cache[callsign]
                        
                        self._update_cache(callsign, result, enable_cache)
                        return result

            cty_result = self._lookup_cty_data(callsign, grid, date)
            if cty_result:
                # log.debug(f"CTY data found for {callsign}: {cty_result}")
                if callsign in self.lotw_cache:
                    cty_result['lotw'] = self.lotw_cache[callsign]
                
                self._update_cache(callsign, cty_result, enable_cache)
                
                return cty_result

            result = None
            for prefix in self.sorted_prefixes:
                if callsign.startswith(prefix):
                    for entry in self.prefixes.get(prefix, []):
                        if self.is_valid_for_date(entry, date):
                            result = entry.copy()
                            break
                if result:
                    break

            if not result:
                if self.lookup_debug:
                    log.debug(f"No information found for {callsign}.")
                result = {}

            if grid and result:
                result["grid"] = grid
                result["grid_updated"] = date.strftime("%Y-%m-%d")
                new_zone = self.grid_to_cq_zone(grid)
                if new_zone is not None and result.get("cqz") != new_zone:
                    result["cqz"] = new_zone

            # Add LoTW information if available
            if callsign in self.lotw_cache:
                result['lotw'] = self.lotw_cache[callsign]

            self._update_cache(callsign, result, enable_cache)
            return result

        except Exception as e:
            log.error(f"Fail to extract '{callsign}': {e}")
            return None

    def _lookup_cty_data(self, callsign, grid=None, date=None):
        """
            Lookup callsign in CTY data with exact and prefix matching.
            Updates CQ zone, latitude, longitude, and recalculates grid if needed.
        """
        # First try exact callsign match
        if callsign.upper() in self.cty_exact_calls:
            result = self.cty_exact_calls[callsign.upper()].copy()
            
            # Update with provided grid if available
            if grid:
                result["grid"] = grid
                if date:
                    result["grid_updated"] = date.strftime("%Y-%m-%d")
                new_zone = self.grid_to_cq_zone(grid)
                if new_zone is not None and result.get("cqz") != new_zone:
                    result["cqz"] = new_zone
            elif result.get("lat") is not None and result.get("long") is not None:
                # Calculate grid from lat/lon if not provided
                try:
                    calculated_grid = latlon_to_grid(result["lat"], result["long"])
                    result["grid"] = calculated_grid
                except:
                    pass
            
            return result
        
        # Then try exact prefix match
        if callsign.upper() in self.cty_prefixes:
            result = self.cty_prefixes[callsign.upper()].copy()
            
            # Update with provided grid if available
            if grid:
                result["grid"] = grid
                if date:
                    result["grid_updated"] = date.strftime("%Y-%m-%d")
                new_zone = self.grid_to_cq_zone(grid)
                if new_zone is not None and result.get("cqz") != new_zone:
                    result["cqz"] = new_zone
            elif result.get("lat") is not None and result.get("long") is not None:
                try:
                    calculated_grid = latlon_to_grid(result["lat"], result["long"])
                    result["grid"] = calculated_grid
                except:
                    pass
            
            return result
        
        sorted_cty_prefixes = sorted(self.cty_prefixes.keys(), key=lambda x: -len(x))
        for prefix in sorted_cty_prefixes:
            if callsign.upper().startswith(prefix):
                result = self.cty_prefixes[prefix].copy()
                result["call"] = prefix 
                
                # Update with provided grid if available
                if grid:
                    result["grid"] = grid
                    if date:
                        result["grid_updated"] = date.strftime("%Y-%m-%d")
                    new_zone = self.grid_to_cq_zone(grid)
                    if new_zone is not None and result.get("cqz") != new_zone:
                        result["cqz"] = new_zone
                elif result.get("lat") is not None and result.get("long") is not None:
                    # Calculate grid from lat/lon if not provided
                    try:
                        calculated_grid = latlon_to_grid(result["lat"], result["long"])
                        result["grid"] = calculated_grid
                    except:
                        pass
                
                return result
        
        return None

    def _update_cache(self, callsign, info, enable_cache):
        if enable_cache and info is not None:
            with self.cache_lock:
                self.cache[callsign] = info
                if len(self.cache) > self.cache_size:
                    self.cache.popitem(last=False)
                # Mark cache dirty if this entry has grid_updated field
                if 'grid_updated' in info:
                    self.save_grid_update_to_cache()  

    def is_valid_for_date(self, info, date):
        start = info.get("start")
        end = info.get("end")
        if start and date < start:
            return False
        if end and date > end:
            return False
        return True
