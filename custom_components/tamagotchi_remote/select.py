"""Room select platform for Tamagotchi Remote."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import TamagotchiRemoteConfigEntry
from .const import ATTR_SELECTED_AREA_ID
from .controller import TamagotchiRemoteController
from .entity import device_info


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: TamagotchiRemoteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the room select entity."""
    async_add_entities([TamagotchiRoomSelect(entry.runtime_data)])


class TamagotchiRoomSelect(SelectEntity, RestoreEntity):
    """Choose one of the configured Home Assistant areas."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:floor-plan"
    _attr_should_poll = False
    _attr_translation_key = "current_room"

    def __init__(self, controller: TamagotchiRemoteController) -> None:
        """Initialize the room select."""
        self.controller = controller
        self._attr_unique_id = f"{controller.prefix}_current_room"
        self._attr_device_info = device_info(controller)

        # Used as the initial suggested entity ID. Home Assistant can still add
        # a suffix if an entity with this ID already exists.
        self.entity_id = f"select.{controller.prefix}_current_room"

    @property
    def available(self) -> bool:
        """Return whether at least one configured area still exists."""
        return bool(self.controller.area_options)

    @property
    def options(self) -> list[str]:
        """Return only the areas selected in the integration options."""
        return self.controller.area_options

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Store the stable area ID for reliable restore after area renames."""
        return {ATTR_SELECTED_AREA_ID: self.controller.selected_area_id}

    @property
    def current_option(self) -> str | None:
        """Return the selected area name."""
        return self.controller.selected_area_name

    async def async_added_to_hass(self) -> None:
        """Restore the last selected area and subscribe for updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.controller.async_add_listener(self._handle_controller_update)
        )

        last_state = await self.async_get_last_state()
        restored_area_id = (
            last_state.attributes.get(ATTR_SELECTED_AREA_ID)
            if last_state is not None
            else None
        )
        self.controller.async_restore_selected_area(
            restored_area_id if isinstance(restored_area_id, str) else None,
            last_state.state if last_state is not None else None,
        )

    async def async_select_option(self, option: str) -> None:
        """Select a room."""
        self.controller.async_set_selected_option(option)

    @callback
    def _handle_controller_update(self) -> None:
        """Write updated options and selected state."""
        self.async_write_ha_state()
