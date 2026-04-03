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


def is_inside_bounds(lat: float, lon: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX
