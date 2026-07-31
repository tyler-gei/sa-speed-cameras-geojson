"""Constants for the SA Speed Cameras integration."""

DOMAIN = "sa_speed_cameras"
PLATFORMS = ["geo_location"]

SOURCE_URL = "https://www.police.sa.gov.au/mobile-data/mobile-camera-locations.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ha-sa-speed-cameras/0.1 (Home Assistant custom integration)"

CONF_LOOKUP_PATH = "lookup_file_path"
DEFAULT_LOOKUP_PATH = "sa_street_lookup.json"

CONF_SCAN_INTERVAL = "scan_interval_minutes"
DEFAULT_SCAN_INTERVAL_MINUTES = 60

CONF_RADIUS = "radius_km"
DEFAULT_RADIUS_KM = 25.0

ATTRIBUTION = (
    "Camera locations: SA Police (police.sa.gov.au). "
    "Geocoding: G-NAF (Geoscape Australia, CC BY 4.0) "
    "with OpenStreetMap Nominatim fallback."
)
