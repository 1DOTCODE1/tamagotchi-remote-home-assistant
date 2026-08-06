"""Base entity helpers for Tamagotchi Remote."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, NAME, VERSION
from .controller import TamagotchiRemoteController


def device_info(controller: TamagotchiRemoteController) -> DeviceInfo:
    """Return shared device information for one generated pair."""
    return DeviceInfo(
        identifiers={(DOMAIN, controller.prefix)},
        name=f"{NAME} {controller.prefix.upper()}",
        manufacturer="1DOTCODE1",
        model="Room entity pair",
        sw_version=VERSION,
    )
