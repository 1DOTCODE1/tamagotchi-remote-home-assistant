"""Shared controller for a Tamagotchi Remote entity pair."""

from __future__ import annotations

import json
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import (
    ATTR_ENTITY_LIST,
    CONF_ALLOWED_AREA_IDS,
    CONF_LABEL_ID,
    CONF_PREFIX,
    DEFAULT_ENTITY_LIST,
)

_LOGGER = logging.getLogger(__name__)


class TamagotchiRemoteController:
    """Coordinate the select and sensor entities for one configured pair."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the controller."""
        self.hass = hass
        self.entry = entry

        self.prefix: str = entry.data[CONF_PREFIX]
        self.label_id: str = entry.options[CONF_LABEL_ID]
        self.allowed_area_ids: list[str] = list(
            entry.options[CONF_ALLOWED_AREA_IDS]
        )

        self.selected_area_id: str | None = None
        self.entity_list_json: str = DEFAULT_ENTITY_LIST

        self._listeners: set[CALLBACK_TYPE] = set()
        self._registry_unsubs: list[CALLBACK_TYPE] = []
        self._state_unsub: CALLBACK_TYPE | None = None
        self._visible_entity_ids: frozenset[str] = frozenset()
        self._started = False

    @property
    def selected_area_name(self) -> str | None:
        """Return the selected area's current display name."""
        if self.selected_area_id is None:
            return None

        area = ar.async_get(self.hass).async_get_area(self.selected_area_id)
        return area.name if area is not None else None

    @property
    def area_options(self) -> list[str]:
        """Return current names for the configured allowed areas."""
        area_registry = ar.async_get(self.hass)
        return [
            area.name
            for area_id in self.allowed_area_ids
            if (area := area_registry.async_get_area(area_id)) is not None
        ]

    @callback
    def async_start(self) -> None:
        """Start registry and state listeners."""
        if self._started:
            return

        self._started = True
        self._registry_unsubs.extend(
            (
                self.hass.bus.async_listen(
                    ar.EVENT_AREA_REGISTRY_UPDATED,
                    self._handle_registry_update,
                ),
                self.hass.bus.async_listen(
                    dr.EVENT_DEVICE_REGISTRY_UPDATED,
                    self._handle_registry_update,
                ),
                self.hass.bus.async_listen(
                    er.EVENT_ENTITY_REGISTRY_UPDATED,
                    self._handle_registry_update,
                ),
                self.hass.bus.async_listen(
                    lr.EVENT_LABEL_REGISTRY_UPDATED,
                    self._handle_registry_update,
                ),
            )
        )

        self._ensure_valid_selected_area()
        self._refresh_payload(force_notify=True)

    @callback
    def async_stop(self) -> None:
        """Stop all listeners."""
        if self._state_unsub is not None:
            self._state_unsub()
            self._state_unsub = None

        for unsub in self._registry_unsubs:
            unsub()

        self._registry_unsubs.clear()
        self._listeners.clear()
        self._started = False

    @callback
    def async_add_listener(self, listener: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Register an entity update listener."""
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    @callback
    def async_set_selected_option(self, option: str) -> None:
        """Select an area by its displayed name."""
        area_registry = ar.async_get(self.hass)

        for area_id in self.allowed_area_ids:
            area = area_registry.async_get_area(area_id)
            if area is not None and area.name == option:
                self.async_set_selected_area(area_id)
                return

        raise ValueError(f"Unknown configured area: {option}")

    @callback
    def async_set_selected_area(self, area_id: str) -> None:
        """Select an allowed area by ID."""
        if area_id not in self.allowed_area_ids:
            raise ValueError(f"Area is not configured for {self.prefix}: {area_id}")

        if ar.async_get(self.hass).async_get_area(area_id) is None:
            raise ValueError(f"Area no longer exists: {area_id}")

        if self.selected_area_id == area_id:
            return

        self.selected_area_id = area_id
        self._refresh_payload(force_notify=True)


    @callback
    def async_restore_selected_area(
        self,
        area_id: str | None,
        option: str | None,
    ) -> None:
        """Restore by stable area ID, falling back to the old displayed name."""
        area_registry = ar.async_get(self.hass)

        if (
            area_id in self.allowed_area_ids
            and area_id is not None
            and area_registry.async_get_area(area_id) is not None
        ):
            self.selected_area_id = area_id
            self._refresh_payload(force_notify=True)
            return

        self.async_restore_selected_option(option)

    @callback
    def async_restore_selected_option(self, option: str | None) -> None:
        """Restore a previously selected area name, or choose the first allowed area."""
        if option:
            area_registry = ar.async_get(self.hass)
            for area_id in self.allowed_area_ids:
                area = area_registry.async_get_area(area_id)
                if area is not None and area.name == option:
                    self.selected_area_id = area_id
                    self._refresh_payload(force_notify=True)
                    return

        self._ensure_valid_selected_area()
        self._refresh_payload(force_notify=True)

    @callback
    def _ensure_valid_selected_area(self) -> bool:
        """Ensure the selected area still exists and is allowed."""
        area_registry = ar.async_get(self.hass)

        if (
            self.selected_area_id in self.allowed_area_ids
            and self.selected_area_id is not None
            and area_registry.async_get_area(self.selected_area_id) is not None
        ):
            return False

        previous = self.selected_area_id
        self.selected_area_id = next(
            (
                area_id
                for area_id in self.allowed_area_ids
                if area_registry.async_get_area(area_id) is not None
            ),
            None,
        )
        return previous != self.selected_area_id

    @callback
    def _handle_registry_update(self, _event: Event) -> None:
        """Rebuild when areas, devices, entities, or labels change."""
        self._ensure_valid_selected_area()
        self._refresh_payload(force_notify=True)

    @callback
    def _handle_state_update(self, _event: Event) -> None:
        """Rebuild when a visible entity changes state or attributes."""
        self._refresh_payload(force_notify=False)

    @callback
    def _refresh_payload(self, *, force_notify: bool) -> None:
        """Rebuild JSON, refresh tracked entities, and notify entities."""
        payload, visible_entity_ids = self._build_payload()

        payload_changed = payload != self.entity_list_json
        visible_changed = visible_entity_ids != self._visible_entity_ids

        self.entity_list_json = payload
        self._visible_entity_ids = visible_entity_ids

        if visible_changed or self._state_unsub is None:
            self._refresh_state_listener()

        if force_notify or payload_changed or visible_changed:
            self._notify_listeners()

    @callback
    def _refresh_state_listener(self) -> None:
        """Track state changes only for entities currently in the generated list."""
        if self._state_unsub is not None:
            self._state_unsub()
            self._state_unsub = None

        if not self._started:
            return

        self._state_unsub = async_track_state_change_event(
            self.hass,
            self._visible_entity_ids,
            self._handle_state_update,
        )

    @callback
    def _notify_listeners(self) -> None:
        """Notify the select and sensor entities."""
        for listener in tuple(self._listeners):
            listener()

    @callback
    def _base_url(self) -> str:
        """Return the address the device reaches Home Assistant at, such as http://192.168.1.10:8123.

        The device downloads pictures from it, for example the cover of what a media player plays, which Home
        Assistant reports as a path. The internal address is preferred, since the device is on the local network;
        an external one is used only when no internal one is known, and Home Assistant Cloud never.
        """
        try:
            return get_url(
                self.hass,
                allow_internal=True,
                allow_external=True,
                allow_cloud=False,
                prefer_external=False,
            ).rstrip("/")
        except NoURLAvailableError:
            _LOGGER.debug("No Home Assistant URL available for %s", self.prefix)
            return ""

    @callback
    def _build_payload(self) -> tuple[str, frozenset[str]]:
        """Build the JSON payload matching the original Jinja template."""
        area_id = self.selected_area_id
        area_registry = ar.async_get(self.hass)
        area = area_registry.async_get_area(area_id) if area_id else None

        if area is None:
            return DEFAULT_ENTITY_LIST, frozenset()

        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        area_entity_ids = {
            entry.entity_id
            for entry in er.async_entries_for_area(
                entity_registry,
                area.id,
            )
        }

        for device in dr.async_entries_for_area(
            device_registry,
            area.id,
        ):
            for entry in er.async_entries_for_device(
                entity_registry,
                device.id,
            ):
                # A direct entity area assignment overrides the device's area.
                if entry.area_id is None or entry.area_id == area.id:
                    area_entity_ids.add(entry.entity_id)

        labeled_entity_ids = {
            entry.entity_id
            for entry in er.async_entries_for_label(
                entity_registry,
                self.label_id,
            )
        }

        visible_entity_ids = frozenset(
            area_entity_ids & labeled_entity_ids
        )

        visible_states = [
            state
            for entity_id in visible_entity_ids
            if (
                state := self.hass.states.get(entity_id)
            ) is not None
        ]

        visible_states.sort(
            key=lambda state: (
                str(
                    state.attributes.get(
                        "friendly_name",
                        state.entity_id,
                    )
                ).casefold(),
                state.entity_id.casefold(),
            )
        )

        entities: list[dict[str, object]] = []

        for state in visible_states:
            entity_id = state.entity_id
            attributes = state.attributes

            entities.append(
                {
                    "name": attributes.get(
                        "friendly_name",
                        entity_id,
                    ),
                    "id": entity_id,
                    "type": entity_id.split(".", 1)[0],
                    "icon": attributes.get("icon") or "",
                    "attributes": sorted(
                        str(key)
                        for key in attributes
                    ),
                    "uom": attributes.get(
                        "unit_of_measurement"
                    ) or "",
                }
            )

        payload = json.dumps(
            {
                "room": area.name,
                "base_url": self._base_url(),
                "entities": entities,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

        _LOGGER.debug(
            "Generated %s for %s using label %s",
            ATTR_ENTITY_LIST,
            self.prefix,
            self.label_id,
        )

        return payload, visible_entity_ids