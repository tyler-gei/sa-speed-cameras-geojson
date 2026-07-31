"""Geolocation platform for SA Speed Cameras."""
from __future__ import annotations

from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.location import distance as calc_distance

from .const import ATTRIBUTION, DOMAIN
from .coordinator import SASpeedCameraCoordinator

UNIT_KM = "km"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SA Speed Camera geo_location entities from a config entry."""
    coordinator: SASpeedCameraCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: dict[str, "SASpeedCameraLocationEvent"] = {}

    @callback
    def _sync_entities() -> None:
        items = {item["unique_id"]: item for item in (coordinator.data or [])}
        current_ids = set(items)
        existing_ids = set(entities)

        new_ids = current_ids - existing_ids
        removed_ids = existing_ids - current_ids

        if new_ids:
            new_entities = []
            for uid in new_ids:
                entity = SASpeedCameraLocationEvent(coordinator, items[uid])
                entities[uid] = entity
                new_entities.append(entity)
            async_add_entities(new_entities)

        for uid in removed_ids:
            entity = entities.pop(uid)
            hass.async_create_task(entity.async_remove(force_remove=True))

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))


class SASpeedCameraLocationEvent(CoordinatorEntity, GeolocationEvent):
    """Represents a currently-active SA mobile speed camera location."""

    _attr_icon = "mdi:speed-camera"
    _attr_should_poll = False
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: SASpeedCameraCoordinator, item: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._unique_id = item["unique_id"]
        self._latitude: float | None = None
        self._longitude: float | None = None
        self._apply(item)

    def _apply(self, item: dict[str, Any]) -> None:
        self._attr_name = item["name"]
        self._latitude = item["latitude"]
        self._longitude = item["longitude"]
        self._attr_extra_state_attributes = {
            "street": item["street"],
            "suburb": item["suburb"],
            "region": item.get("region"),
            "date_start": item.get("date_start"),
            "date_end": item.get("date_end"),
        }

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._unique_id}"

    @property
    def source(self) -> str:
        return DOMAIN

    @property
    def latitude(self) -> float | None:
        return self._latitude

    @property
    def longitude(self) -> float | None:
        return self._longitude

    @property
    def unit_of_measurement(self) -> str:
        return UNIT_KM

    @property
    def distance(self) -> float | None:
        home_lat = self.hass.config.latitude
        home_lon = self.hass.config.longitude
        if None in (home_lat, home_lon, self._latitude, self._longitude):
            return None
        return calc_distance(home_lat, home_lon, self._latitude, self._longitude) / 1000

    @callback
    def _handle_coordinator_update(self) -> None:
        for item in self.coordinator.data or []:
            if item["unique_id"] == self._unique_id:
                self._apply(item)
                break
        self.async_write_ha_state()
