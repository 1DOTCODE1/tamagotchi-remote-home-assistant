"""Config flow for Tamagotchi Remote."""

from __future__ import annotations

from typing import Any
import re

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.selector import (
    AreaSelector,
    AreaSelectorConfig,
    LabelSelector,
    LabelSelectorConfig,
    TextSelector,
)

from .const import (
    CONF_ALLOWED_AREA_IDS,
    CONF_LABEL_ID,
    CONF_PREFIX,
    DOMAIN,
)

PREFIX_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def _options_schema(
    *,
    label_id: str | None = None,
    allowed_area_ids: list[str] | None = None,
) -> vol.Schema:
    """Build the label and allowed-area schema."""
    label_key = (
        vol.Required(CONF_LABEL_ID, default=label_id)
        if label_id is not None
        else vol.Required(CONF_LABEL_ID)
    )
    areas_key = (
        vol.Required(CONF_ALLOWED_AREA_IDS, default=allowed_area_ids)
        if allowed_area_ids is not None
        else vol.Required(CONF_ALLOWED_AREA_IDS)
    )

    return vol.Schema(
        {
            label_key: LabelSelector(LabelSelectorConfig(multiple=False)),
            areas_key: AreaSelector(
                AreaSelectorConfig(
                    multiple=True,
                    reorder=True,
                )
            ),
        }
    )


def _validate_selection(
    hass: HomeAssistant,
    user_input: dict[str, Any],
) -> dict[str, str]:
    """Validate label and allowed areas."""
    errors: dict[str, str] = {}
    area_ids = list(user_input.get(CONF_ALLOWED_AREA_IDS, []))

    if not area_ids:
        errors[CONF_ALLOWED_AREA_IDS] = "no_areas"
    else:
        area_registry = ar.async_get(hass)
        if any(area_registry.async_get_area(area_id) is None for area_id in area_ids):
            errors[CONF_ALLOWED_AREA_IDS] = "area_missing"

    label_id = user_input.get(CONF_LABEL_ID)
    if not label_id or lr.async_get(hass).async_get_label(label_id) is None:
        errors[CONF_LABEL_ID] = "label_missing"

    return errors


class TamagotchiRemoteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Tamagotchi Remote config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Create a new select/sensor pair."""
        errors: dict[str, str] = {}

        if user_input is not None:
            prefix = str(user_input[CONF_PREFIX]).strip().lower()

            if not PREFIX_PATTERN.fullmatch(prefix):
                errors[CONF_PREFIX] = "invalid_prefix"

            errors.update(_validate_selection(self.hass, user_input))

            if not errors:
                await self.async_set_unique_id(prefix)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=prefix.upper(),
                    data={CONF_PREFIX: prefix},
                    options={
                        CONF_LABEL_ID: user_input[CONF_LABEL_ID],
                        CONF_ALLOWED_AREA_IDS: list(
                            user_input[CONF_ALLOWED_AREA_IDS]
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_PREFIX): TextSelector(),
            }
        ).extend(_options_schema().schema)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: ConfigEntry,
    ) -> TamagotchiRemoteOptionsFlow:
        """Return the options flow."""
        return TamagotchiRemoteOptionsFlow()


class TamagotchiRemoteOptionsFlow(OptionsFlowWithReload):
    """Allow changing the label and available areas at any time."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage the pair options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_selection(self.hass, user_input)
            if not errors:
                return self.async_create_entry(
                    data={
                        CONF_LABEL_ID: user_input[CONF_LABEL_ID],
                        CONF_ALLOWED_AREA_IDS: list(
                            user_input[CONF_ALLOWED_AREA_IDS]
                        ),
                    }
                )

        current_label_id = self.config_entry.options[CONF_LABEL_ID]
        current_area_ids = list(
            self.config_entry.options[CONF_ALLOWED_AREA_IDS]
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(
                label_id=current_label_id,
                allowed_area_ids=current_area_ids,
            ),
            errors=errors,
        )
