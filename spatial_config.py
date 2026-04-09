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
    "Zakopane": {"lat": 49.2992, "lon": 19.9496, "aliases": ["zakopane", "zakopanego"]},
    "Kuznice": {
        "lat": 49.2693,
        "lon": 19.9802,
        "aliases": ["kuznice", "kuznice zakopane", "kuznic", "kuznicach", "kuznicami", "kuznicach"],
    },
    "Kasprowy Wierch": {
        "lat": 49.2322,
        "lon": 19.9817,
        "aliases": ["kasprowy", "kasprowy wierch", "kasprowego", "kasprowego wierchu"],
    },
    "Giewont": {"lat": 49.2506, "lon": 19.9342, "aliases": ["giewont", "giewontu"]},
    "Nosal": {"lat": 49.2858, "lon": 19.9811, "aliases": ["nosal", "nosala"]},
    "Morskie Oko": {"lat": 49.1988, "lon": 20.0706, "aliases": ["morskie oko", "morskiego oka"]},
    "Rysy": {"lat": 49.1794, "lon": 20.0881, "aliases": ["rysy", "rysow"]},
    "Czarny Staw Gasienicowy": {
        "lat": 49.2319,
        "lon": 20.0128,
        "aliases": [
            "czarny staw gasienicowy",
            "czarnego stawu gasienicowego",
        ],
    },
    "Hala Gasienicowa": {
        "lat": 49.2381,
        "lon": 20.0012,
        "aliases": ["hala gasienicowa", "hali gasienicowej"],
    },
    "Koscielec": {"lat": 49.2339, "lon": 20.0148, "aliases": ["koscielec", "koscielca"]},
    "Murowaniec": {
        "lat": 49.2397,
        "lon": 20.0031,
        "aliases": ["murowaniec", "murowanca", "schronisko murowaniec", "schroniska murowaniec"],
    },
    "Hala Kondratowa": {"lat": 49.2505, "lon": 19.9552, "aliases": ["hala kondratowa", "hali kondratowej"]},
    "Dolina Koscieliska": {
        "lat": 49.2753,
        "lon": 19.8682,
        "aliases": ["dolina koscieliska", "doliny koscieliskiej", "koscieliska"],
    },
    "Dolina Chocholowska": {
        "lat": 49.2502,
        "lon": 19.8057,
        "aliases": ["dolina chocholowska", "doliny chocholowskiej", "chocholowska"],
    },
    "Dolina Pieciu Stawow": {
        "lat": 49.2017,
        "lon": 20.0518,
        "aliases": ["dolina pieciu stawow", "doliny pieciu stawow", "piec stawow"],
    },
    "Palenica Bialczanska": {
        "lat": 49.2558,
        "lon": 20.1073,
        "aliases": ["palenica bialczanska", "palenicy bialczanskiej"],
    },
}

ROUTE_TEMPLATES = {
    ("Zakopane", "Morskie Oko"): ["Zakopane", "Palenica Bialczanska", "Morskie Oko"],
    ("Morskie Oko", "Zakopane"): ["Morskie Oko", "Palenica Bialczanska", "Zakopane"],
    ("Zakopane", "Kasprowy Wierch"): ["Zakopane", "Kuznice", "Kasprowy Wierch"],
    ("Kasprowy Wierch", "Zakopane"): ["Kasprowy Wierch", "Kuznice", "Zakopane"],
    ("Zakopane", "Hala Gasienicowa"): ["Zakopane", "Kuznice", "Murowaniec", "Hala Gasienicowa"],
    ("Hala Gasienicowa", "Zakopane"): ["Hala Gasienicowa", "Murowaniec", "Kuznice", "Zakopane"],
    ("Zakopane", "Murowaniec"): ["Zakopane", "Kuznice", "Murowaniec"],
    ("Murowaniec", "Zakopane"): ["Murowaniec", "Kuznice", "Zakopane"],
    ("Palenica Bialczanska", "Morskie Oko"): ["Palenica Bialczanska", "Morskie Oko"],
    ("Morskie Oko", "Palenica Bialczanska"): ["Morskie Oko", "Palenica Bialczanska"],
}

ROUTE_GRAPH = {
    "Zakopane": ["Kuznice", "Dolina Koscieliska", "Dolina Chocholowska", "Palenica Bialczanska"],
    "Kuznice": ["Zakopane", "Kasprowy Wierch", "Murowaniec", "Hala Kondratowa", "Nosal"],
    "Kasprowy Wierch": ["Kuznice", "Hala Gasienicowa"],
    "Hala Kondratowa": ["Kuznice", "Giewont"],
    "Giewont": ["Hala Kondratowa"],
    "Nosal": ["Kuznice"],
    "Murowaniec": ["Kuznice", "Hala Gasienicowa", "Koscielec", "Czarny Staw Gasienicowy"],
    "Hala Gasienicowa": ["Murowaniec", "Kasprowy Wierch", "Czarny Staw Gasienicowy"],
    "Czarny Staw Gasienicowy": ["Hala Gasienicowa", "Koscielec", "Murowaniec"],
    "Koscielec": ["Murowaniec", "Czarny Staw Gasienicowy"],
    "Palenica Bialczanska": ["Zakopane", "Morskie Oko", "Dolina Pieciu Stawow"],
    "Morskie Oko": ["Palenica Bialczanska", "Rysy", "Dolina Pieciu Stawow"],
    "Rysy": ["Morskie Oko"],
    "Dolina Pieciu Stawow": ["Palenica Bialczanska", "Morskie Oko"],
    "Dolina Koscieliska": ["Zakopane"],
    "Dolina Chocholowska": ["Zakopane"],
}


def is_inside_bounds(lat: float, lon: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX
