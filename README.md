# SA Speed Cameras (Home Assistant / HACS)

Shows **currently-active** South Australian mobile speed camera locations
as `geo_location` entities in Home Assistant, so they appear on your map
and can be used in automations (e.g. "notify me if a camera is within
2km while driving").

Data source: SA Police's live mobile camera feed
(`police.sa.gov.au/mobile-data/mobile-camera-locations.json`), which lists
street + suburb + active date range for each camera. This integration:

1. Fetches that feed on a schedule (default hourly)
2. Filters it down to only entries whose date range covers **today**
   (Australia/Adelaide time)
3. Resolves each street/suburb to coordinates using a local lookup table
   you build once from G-NAF (see below), falling back to live
   OpenStreetMap Nominatim geocoding for anything not in the table
4. Creates/updates/removes `geo_location.sa_speed_cameras_*` entities to
   match

## Installation (HACS)

1. HACS -> Integrations -> ⋮ -> Custom repositories -> add this repo URL,
   category "Integration"
2. Install "SA Speed Cameras", restart Home Assistant
3. Settings -> Devices & Services -> Add Integration -> "SA Speed Cameras"
4. (Optional) set the lookup file path and update interval

## Building the local lookup table (recommended)

Without a local lookup table, every camera location is geocoded live via
Nominatim on each update, which is slow (rate-limited to ~1 request/sec)
and depends on an external service being up. Building a one-time local
table from G-NAF avoids that:

1. Download the current G-NAF release from
   <https://data.gov.au/data/dataset/geocoded-national-address-file-g-naf>
2. From the "Standard" extract, grab the three SA files:
   `SA_STREET_LOCALITY_psv.psv`, `SA_STREET_LOCALITY_POINT_psv.psv`,
   `SA_LOCALITY_psv.psv`
3. Run the builder in `tools/build_gnaf_lookup.py`:

   ```
   python3 tools/build_gnaf_lookup.py \
       SA_STREET_LOCALITY_psv.psv \
       SA_STREET_LOCALITY_POINT_psv.psv \
       SA_LOCALITY_psv.psv
   ```

4. Copy the resulting `sa_street_lookup.json` into your Home Assistant
   `/config` directory (or wherever you point the integration's
   "lookup file path" option -- default is `sa_street_lookup.json`
   directly under `/config`)

Re-run step 3 each quarter against the latest G-NAF release if you want
to pick up new streets/suburbs.

## Attribution

- Camera locations: SA Police (police.sa.gov.au)
- Geocoding: G-NAF, © Geoscape Australia, licensed CC BY 4.0, with
  OpenStreetMap Nominatim (© OpenStreetMap contributors, ODbL) as fallback

## Notes / limitations

- This is a community project, not affiliated with or endorsed by SAPOL
  or Geoscape Australia.
- Geocoding is at street level (a representative point on the street),
  not the exact camera position -- treat entity locations as
  approximate.
- The upstream feed itself only updates roughly daily, so polling more
  often than hourly won't get you fresher data.
