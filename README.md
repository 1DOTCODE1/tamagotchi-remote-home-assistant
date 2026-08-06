# Tamagotchi Remote

A HACS-compatible Home Assistant helper integration that creates configurable entity pairs for an ESPHome Tamagotchi Remote UI.

Each integration entry creates:

- `select.<prefix>_current_room`
- `sensor.<prefix>_room_entities`

The select contains only the Home Assistant areas chosen in the integration configuration. The sensor state is the selected room name and its `entity_list` attribute contains compact JSON describing entities that:

1. belong to the selected area, and
2. carry the configured Home Assistant label.

## Example

With prefix `tr1`, label `show_in_tamagotchi`, and the allowed areas Living Room, Kitchen, and Bedroom, the integration initially creates:

```text
select.tr1_current_room
sensor.tr1_room_entities
```

Example sensor attribute:

```json
{
  "room": "Living Room",
  "entities": [
    {
      "name": "Living Room Cover",
      "id": "cover.living_room",
      "type": "cover",
      "icon": "mdi:window-shutter",
      "attributes": [
        "current_position",
        "device_class",
        "friendly_name",
        "supported_features"
      ],
      "uom": ""
    }
  ]
}
```

## Installation with HACS

1. Push this project to a public GitHub repository.
2. In HACS, open the menu and choose **Custom repositories**.
3. Add the repository URL with category **Integration**.
4. Install **Tamagotchi Remote**.
5. Restart Home Assistant.
6. Open **Settings → Devices & services → Add integration**.
7. Search for **Tamagotchi Remote**.

## Create a pair

When adding the integration, choose:

- **Entity ID prefix** — for example `tr1`.
- **Entity visibility label** — for example `show_in_tamagotchi`.
- **Areas available in the room select** — select and order the rooms that should be available.

Add the integration again to create `tr2`, `tr3`, or any other pair.

## Change or delete a pair

Open **Settings → Devices & services → Tamagotchi Remote**.

- Open a pair and choose **Configure** to change its label or available areas.
- Delete that config entry to remove only that pair and its two entities.

The prefix is intentionally immutable because changing it would change entity unique IDs. Delete and recreate a pair to use a different prefix.

## ESPHome native API subscription

Subscribe to the generated sensor's `entity_list` attribute:

```cpp
this->api_server->subscribe_home_assistant_state(
    "sensor.tr1_room_entities",
    std::optional<std::string>{"entity_list"},
    [weak_this](esphome::StringRef value) {
        const auto self = weak_this.lock();
        if (!self) return;

        const std::string json_payload = value.str();

        self->defer(
            "entity_manager.entity_list_update",
            [weak_this, json_payload]() {
                const auto self = weak_this.lock();
                if (!self) return;

                self->update_entity_list(json_payload);
            }
        );
    }
);
```

Your ESPHome configuration must enable Home Assistant state subscriptions:

```yaml
api:
  homeassistant_states: true
```

## Area and label behavior

The integration follows the behavior of the original template:

- Entities assigned directly to the selected area are included.
- Entities inherit their device's area unless the entity has its own area assignment.
- The visibility label must be assigned directly to the entity.
- Entities without a current Home Assistant state are omitted until their state appears.
- The JSON updates when the selected room, registry metadata, or relevant entity attributes change.

## Development

The repository contains HACS and Hassfest validation workflows. Before publishing, update the GitHub URLs and `codeowners` value in `manifest.json` if your repository or username differs.
