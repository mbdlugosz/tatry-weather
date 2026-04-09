from __future__ import annotations

LAT_MIN = 49.17035070524409
LAT_MAX = 49.309555578150245
LON_MIN = 19.76220706945233
LON_MAX = 20.125423430066586

STATION_COORDINATES = {
    "Zakopane": {"lat": 49.2992, "lon": 19.9496},
    "Kasprowy Wierch": {"lat": 49.2322, "lon": 19.9817},
    "Poprad_Tatry": {"lat": 49.0677, "lon": 20.2411},
}

TATRA_PLACE_COORDINATES = {
    "Zakopane": {"lat": 49.2992, "lon": 19.9496, "aliases": ["zakopane"]},
    "Kuznice": {"lat": 49.2693, "lon": 19.9802, "aliases": ["kuznice", "kuznice zakopane", "kuźnice"]},
    "Kasprowy Wierch": {"lat": 49.2322, "lon": 19.9817, "aliases": ["kasprowy", "kasprowy wierch"]},
    "Giewont": {"lat": 49.2506, "lon": 19.9342, "aliases": ["giewont"]},
    "Nosal": {"lat": 49.2858, "lon": 19.9811, "aliases": ["nosal"]},
    "Morskie Oko": {"lat": 49.1988, "lon": 20.0706, "aliases": ["morskie oko"]},
    "Rysy": {"lat": 49.1794, "lon": 20.0881, "aliases": ["rysy"]},
    "Czarny Staw Gasienicowy": {
        "lat": 49.2319,
        "lon": 20.0128,
        "aliases": ["czarny staw gasienicowy", "czarny staw gąsienicowy"],
    },
    "Hala Gasienicowa": {
        "lat": 49.2381,
        "lon": 20.0012,
        "aliases": ["hala gasienicowa", "hala gąsienicowa"],
    },
    "Koscielec": {"lat": 49.2339, "lon": 20.0148, "aliases": ["koscielec", "kościelec"]},
    "Murowaniec": {"lat": 49.2397, "lon": 20.0031, "aliases": ["murowaniec", "schronisko murowaniec"]},
    "Hala Kondratowa": {"lat": 49.2505, "lon": 19.9552, "aliases": ["hala kondratowa"]},
    "Dolina Koscieliska": {
        "lat": 49.2753,
        "lon": 19.8682,
        "aliases": ["dolina koscieliska", "dolina kościeliska", "koscieliska", "kościeliska"],
    },
    "Dolina Chocholowska": {
        "lat": 49.2502,
        "lon": 19.8057,
        "aliases": ["dolina chocholowska", "dolina chochołowska", "chocholowska", "chochołowska"],
    },
    "Dolina Pieciu Stawow": {
        "lat": 49.2017,
        "lon": 20.0518,
        "aliases": ["dolina pieciu stawow", "dolina pięciu stawów", "piec stawow", "pięć stawów"],
    },
    "Palenica Bialczanska": {
        "lat": 49.2558,
        "lon": 20.1073,
        "aliases": ["palenica bialczanska", "palenica białczańska"],
    },
}


def is_inside_bounds(lat: float, lon: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX
