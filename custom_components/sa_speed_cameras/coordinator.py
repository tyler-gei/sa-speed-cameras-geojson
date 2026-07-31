"""Data update coordinator for SA Speed Cameras."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_LOOKUP_PATH,
    DEFAULT_LOOKUP_PATH,
    DOMAIN,
    NOMINATIM_URL,
    SOURCE_URL,
    USER_AGENT,
)

try:
    from zoneinfo import ZoneInfo

    ADELAIDE_TZ: ZoneInfo | None = ZoneInfo("Australia/Adelaide")
except Exception:  # pragma: no cover - fallback if tzdata isn't available
    ADELAIDE_TZ = None

_LOGGER = logging.getLogger(__name__)

FALLBACK_STORE_VERSION = 1
FALLBACK_STORE_KEY = f"{DOMAIN}_geocode_fallback_cache"
NOMINATIM_DELAY_SECONDS = 1.1


def _normalise(text: str) -> str:
    return " ".join(text.strip().upper().split())


def _parse_ddmmyyyy(text: str) -> date:
    return datetime.strptime(text, "%d/%m/%Y").date()


def _is_active_today(cam: dict, today: date) -> bool:
    try:
        start = _parse_ddmmyyyy(cam["date_start"])
        end = _parse_ddmmyyyy(cam["date_end"])
    except (KeyError, ValueError):
        return False
    return start <= today <= end


class SASpeedCameraCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Fetches active SA mobile speed camera locations and resolves coordinates."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, update_interval: timedelta
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.entry = entry
        self._session = async_get_clientsession(hass)
        self._fallback_store: Store = Store(
            hass, FALLBACK_STORE_VERSION, FALLBACK_STORE_KEY
        )
        self._fallback_cache: dict[str, Any] | None = None
        self._local_lookup: dict[str, Any] | None = None

    async def _async_load_local_lookup(self) -> dict[str, Any]:
        options = {**self.entry.data, **self.entry.options}
        path_str = options.get(CONF_LOOKUP_PATH, DEFAULT_LOOKUP_PATH)
        path = Path(path_str)
        if not path.is_absolute():
            path = Path(self.hass.config.path(path_str))

        def _read() -> dict[str, Any]:
            if not path.exists():
                return {}
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        try:
            return await self.hass.async_add_executor_job(_read)
        except (OSError, json.JSONDecodeError) as err:
            _LOGGER.warning("Could not read local lookup file %s: %s", path, err)
            return {}

    async def _async_nominatim_geocode(
        self, street: str, suburb: str
    ) -> dict[str, float] | None:
        query = f"{street}, {suburb}, South Australia, Australia"
        params = {"q": query, "format": "json", "limit": 1, "countrycodes": "au"}
        try:
            async with self._session.get(
                NOMINATIM_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            ) as resp:
                results = await resp.json(content_type=None)
        except Exception as err:  # noqa: BLE001 - log and continue, don't fail update
            _LOGGER.warning("Nominatim geocoding failed for %s: %s", query, err)
            return None

        if not results:
            return None
        return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}

    async def _async_update_data(self) -> list[dict[str, Any]]:
        if self._local_lookup is None:
            self._local_lookup = await self._async_load_local_lookup()
            if not self._local_lookup:
                _LOGGER.warning(
                    "No local G-NAF lookup table found (or it was empty) -- "
                    "every location will be geocoded live via Nominatim, which "
                    "is slower on first run. See the integration README for how "
                    "to build sa_street_lookup.json."
                )

        if self._fallback_cache is None:
            self._fallback_cache = await self._fallback_store.async_load() or {}

        try:
            async with self._session.get(
                SOURCE_URL, headers={"User-Agent": USER_AGENT}, timeout=30
            ) as resp:
                all_cameras = await resp.json(content_type=None)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error fetching SAPOL camera feed: {err}") from err

        today = datetime.now(ADELAIDE_TZ).date() if ADELAIDE_TZ else date.today()
        active = [cam for cam in all_cameras if _is_active_today(cam, today)]
        _LOGGER.debug(
            "%d of %d feed entries are active today (%s)",
            len(active),
            len(all_cameras),
            today.isoformat(),
        )

        unique_locations: dict[tuple[str, str], list[dict]] = {}
        for cam in active:
            key = (cam["street_name"], cam["suburb"])
            unique_locations.setdefault(key, []).append(cam)

        results: list[dict[str, Any]] = []
        cache_dirty = False

        for (street, suburb), entries in unique_locations.items():
            lookup_key = f"{_normalise(street)}|{_normalise(suburb)}"
            coords = self._local_lookup.get(lookup_key)

            if coords is None:
                cache_key = f"{street}|{suburb}"
                if cache_key in self._fallback_cache:
                    coords = self._fallback_cache[cache_key]
                else:
                    coords = await self._async_nominatim_geocode(street, suburb)
                    self._fallback_cache[cache_key] = coords
                    cache_dirty = True
                    await asyncio.sleep(NOMINATIM_DELAY_SECONDS)

            if not coords:
                _LOGGER.debug(
                    "Could not resolve coordinates for %s, %s", street, suburb
                )
                continue

            for cam in entries:
                results.append(
                    {
                        "unique_id": lookup_key,
                        "name": f"Mobile speed camera - {street}, {suburb}",
                        "street": street,
                        "suburb": suburb,
                        "region": cam.get("region"),
                        "date_start": cam.get("date_start"),
                        "date_end": cam.get("date_end"),
                        "latitude": coords["lat"],
                        "longitude": coords["lon"],
                    }
                )

        if cache_dirty:
            await self._fallback_store.async_save(self._fallback_cache)

        return results
