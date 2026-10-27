"""Explicit sample adapter. 't' is message source/type, NEVER ICAO aircraft type.

Field identities: https://sample.wingbits.com/ (provider historical dictionary).
Units/datum: https://github.com/wiedehopf/readsb/blob/dev/README-json.md
Wingbits altitude example: https://wingbits.com/business-solutions/flight-data-api
The sample follows abbreviated readsb fields. This documented convention remains
a provider-semantic assumption, not an independent calibration of measurements.
"""
MAPPING = {
    "h": ("icao24", "identifier"), "f": ("callsign_raw", "text"),
    "timestamp": ("timestamp_utc", "UTC milliseconds"),
    "la": ("latitude_deg", "WGS84 degrees"), "lo": ("longitude_deg", "WGS84 degrees"),
    "ab": ("barometric_altitude_ft", "ft; pressure altitude, not surveyed AMSL"),
    "ag": ("geometric_altitude_ft", "ft; WGS84 ellipsoid"),
    "gs": ("ground_speed_kt", "knots"), "i": ("indicated_airspeed_kt", "knots"),
    "tr": ("track_deg", "degrees true"), "th": ("true_heading_deg", "degrees true"),
    "mh": ("magnetic_heading_deg", "degrees magnetic"),
    "br": ("barometric_rate_fpm", "ft/min"), "gr": ("geometric_rate_fpm", "ft/min"),
    "og": ("on_ground", "nullable boolean"), "sp": ("position_age_s", "seconds"),
    "t": ("message_type", "message/source type, not aircraft type")
}
REQUIRED = {"h", "timestamp", "la", "lo"}
QUALITY = ["np", "nv", "n", "nb", "s", "sda", "rc", "gv", "rs"]
