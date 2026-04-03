from __future__ import annotations

LAT_MIN = 49.17035070524409
LAT_MAX = 49.309555578150245
LON_MIN = 19.76220706945233
LON_MAX = 20.125423430066586


def is_inside_bounds(lat: float, lon: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX
