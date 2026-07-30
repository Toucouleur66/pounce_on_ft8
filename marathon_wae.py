# marathon_wae.py
#
# DX Marathon WAE entities. These are NOT part of the official DXCC list, so DX
# Marathon assigns them internal DXCC codes (901-906). ClubLog codes them either
# under their parent DXCC entity (e.g. 4U1V -> Austria, JW/B -> Svalbard) or with
# a colliding code (Shetland and South Shetland both 241), so we detect them here
# and remap to the DX Marathon internal code for both scoring and display.
#
# Reference: https://dxmarathon.com/resources/data-formats/#adif-log-1
#   901  4U1V   ITU Vienna International Center   -
#   902  GM/s   Shetland Islands                 EU-012
#   903  IG9    African Italy                    AF-018, AF-019
#   904  IT9    Sicily                           EU-025
#   905  JW/b   Bear Island                      EU-027
#   906  TA1    European Turkey                  -
#
# Detection strategy, in order:
#   1. by callsign prefix (needed for ITU Vienna and Bear Island, which ClubLog
#      folds into Austria / Svalbard);
#   2. by the ClubLog entity name (Shetland, African Italy, Sicily, European
#      Turkey are named distinctly by ClubLog).

import re

# Each entry: internal DX Marathon code -> record.
# `prefix_re` matches the START of the callsign (already uppercased); `clublog`
# is the uppercased ClubLog entity name that also identifies this WAE entity.
WAE_ENTITIES = {
    901: {
        "code"     : 901,
        "prefix"   : "4U1V",
        "name"     : "ITU Vienna Int. Center",
        "continent": "EU",
        "cq_zones" : "15",
        "iota"     : "",
        "prefix_re": r"4U1V",
        "clublog"  : None,   # ClubLog reports Austria; prefix-only detection
    },
    902: {
        "code"     : 902,
        "prefix"   : "GM/s",
        "name"     : "Shetland Islands",
        "continent": "EU",
        "cq_zones" : "14",
        "iota"     : "EU-012",
        "prefix_re": None,
        "clublog"  : "SHETLAND ISLANDS",
    },
    903: {
        "code"     : 903,
        "prefix"   : "IG9",
        "name"     : "African Italy",
        "continent": "AF",
        "cq_zones" : "34",
        "iota"     : "AF-018, AF-019",
        "prefix_re": None,
        "clublog"  : "AFRICAN ITALY",
    },
    904: {
        "code"     : 904,
        "prefix"   : "IT9",
        "name"     : "Sicily",
        "continent": "EU",
        "cq_zones" : "15",
        "iota"     : "EU-025",
        "prefix_re": None,
        "clublog"  : "SICILY",
    },
    905: {
        "code"     : 905,
        "prefix"   : "JW/b",
        "name"     : "Bear Island",
        "continent": "EU",
        "cq_zones" : "40",
        "iota"     : "EU-027",
        "prefix_re": r"JW/B",
        "clublog"  : None,   # ClubLog reports Svalbard; prefix-only detection
    },
    906: {
        "code"     : 906,
        "prefix"   : "TA1",
        "name"     : "European Turkey",
        "continent": "EU",
        "cq_zones" : "20",
        "iota"     : "",
        "prefix_re": None,
        "clublog"  : "EUROPEAN TURKEY",
    },
}

# Pre-compiled prefix matchers, longest prefix first so "JW/B" wins over "JW".
_PREFIX_MATCHERS = sorted(
    ((re.compile("^" + rec["prefix_re"]), rec) for rec in WAE_ENTITIES.values() if rec.get("prefix_re")),
    key=lambda pair: -len(pair[1]["prefix_re"]),
)

# ClubLog entity name -> record, for the name-detectable WAE entities.
_BY_CLUBLOG = {rec["clublog"]: rec for rec in WAE_ENTITIES.values() if rec.get("clublog")}


def resolve_wae(callsign, clublog_entity_name):
    """
    Return the DX Marathon WAE record for a QSO, or None if it is not a WAE
    entity. Prefix match first (catches ITU Vienna / Bear Island that ClubLog
    hides), then ClubLog entity name.
    """
    if callsign:
        call = callsign.upper()
        for matcher, record in _PREFIX_MATCHERS:
            if matcher.match(call):
                return record

    if clublog_entity_name:
        record = _BY_CLUBLOG.get(clublog_entity_name.strip().upper())
        if record:
            return record

    return None


def wae_record(code):
    """WAE record for an internal code (901-906), or None."""
    return WAE_ENTITIES.get(code)
