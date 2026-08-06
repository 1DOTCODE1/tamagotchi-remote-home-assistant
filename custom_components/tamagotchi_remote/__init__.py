"""Tamagotchi Remote integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .controller import TamagotchiRemoteController


type TamagotchiRemoteConfigEntry = ConfigEntry[TamagotchiRemoteController]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TamagotchiRemoteConfigEntry,
) -> bool:
    """Set up Tamagotchi Remote from a config entry."""
    controller = TamagotchiRemoteController(hass, entry)
    entry.runtime_data = controller

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    controller.async_start()

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: TamagotchiRemoteConfigEntry,
) -> bool:
    """Unload a Tamagotchi Remote config entry."""
    entry.runtime_data.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
