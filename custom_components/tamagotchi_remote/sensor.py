"""JSON sensor platform for Tamagotchi Remote."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TamagotchiRemoteConfigEntry
from .const import ATTR_ENTITY_LIST
from .controller import TamagotchiRemoteController
from .entity import device_info


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: TamagotchiRemoteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the generated room JSON sensor."""
    async_add_entities([TamagotchiRoomEntitiesSensor(entry.runtime_data)])


class TamagotchiRoomEntitiesSensor(SensorEntity):
    """Expose the selected room and generated entity list JSON."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:code-json"
    _attr_should_poll = False
    _attr_translation_key = "room_entities"
    _unrecorded_attributes = frozenset({ATTR_ENTITY_LIST})

    def __init__(self, controller: TamagotchiRemoteController) -> None:
        """Initialize the generated JSON sensor."""
        self.controller = controller
        self._attr_unique_id = f"{controller.prefix}_room_entities"
        self._attr_device_info = device_info(controller)

        # Used as the initial suggested entity ID. Home Assistant can still add
        # a suffix if an entity with this ID already exists.
        self.entity_id = f"sensor.{controller.prefix}_room_entities"

    @property
    def native_value(self) -> str:
        """Return the selected room as the sensor state."""
        return self.controller.selected_area_name or STATE_UNKNOWN

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the generated JSON string."""
        return {
            ATTR_ENTITY_LIST: self.controller.entity_list_json,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe for controller updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.controller.async_add_listener(self._handle_controller_update)
        )

    @callback
    def _handle_controller_update(self) -> None:
        """Write the new room and JSON payload."""
        self.async_write_ha_state()
