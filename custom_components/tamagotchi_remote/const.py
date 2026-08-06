"""Constants for the Tamagotchi Remote integration."""

from homeassistant.const import Platform

DOMAIN = "tamagotchi_remote"
NAME = "Tamagotchi Remote"
VERSION = "1.0.0"

PLATFORMS: tuple[Platform, ...] = (
    Platform.SELECT,
    Platform.SENSOR,
)

CONF_PREFIX = "prefix"
CONF_LABEL_ID = "label_id"
CONF_ALLOWED_AREA_IDS = "allowed_area_ids"

ATTR_ENTITY_LIST = "entity_list"
ATTR_SELECTED_AREA_ID = "selected_area_id"

DEFAULT_ENTITY_LIST = '{"room":"","entities":[]}'
