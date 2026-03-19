"""Switch platform for MeriTO Technologies — one switch per relay channel."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    DATA_DEVICES,
    RELAY_COUNT,
    RELAY_BIT_ON,
    RELAY_COMMANDS,
    MANUFACTURER,
    MODEL_RELAY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MeriTO relay switches.

    Called once at startup (entities for already-known devices) and also
    re-triggered via HA event when a new device is discovered at runtime.
    """

    known_macs: set[str] = set()

    def _add_switches_for_mac(mac: str, device_info: dict) -> None:
        if mac in known_macs:
            return
        known_macs.add(mac)
        entities = [
            MeritoRelaySwitch(hass, entry, device_info, relay_num)
            for relay_num in range(1, RELAY_COUNT + 1)
        ]
        async_add_entities(entities, update_before_add=False)
        _LOGGER.info(
            "MeriTO: added %d switch entities for MAC=%s", len(entities), mac
        )

    # Add entities for devices already registered at load time
    entry_data = hass.data[DOMAIN][entry.entry_id]
    for mac, device_info in entry_data[DATA_DEVICES].items():
        _add_switches_for_mac(mac, device_info)

    # Listen for runtime device discovery events
    @callback
    def _on_new_device(event) -> None:
        if event.data.get("entry_id") != entry.entry_id:
            return
        mac = event.data["mac"]
        device_info = hass.data[DOMAIN][entry.entry_id][DATA_DEVICES].get(mac)
        if device_info:
            _add_switches_for_mac(mac, device_info)

    entry.async_on_unload(
        hass.bus.async_listen(f"{DOMAIN}_new_device", _on_new_device)
    )


class MeritoRelaySwitch(RestoreEntity, SwitchEntity):
    """Represents one relay channel on a MeriTO Relay device."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device_info: dict,
        relay_num: int,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._mac = device_info["mac"]
        self._relay_num = relay_num
        self._data_topic = device_info["data_topic"]
        self._set_topic = device_info["set_topic"]
        self._mqtt_domain = device_info["mqtt_domain"]
        self._is_on: bool | None = None
        self._unsub_mqtt: list = []
        self._available = False

        # Sanitise MAC for use in entity/unique IDs (remove dashes/colons)
        mac_clean = self._mac.replace("-", "").replace(":", "").upper()

        self._attr_unique_id = f"{mac_clean}_relay_{relay_num}"
        self._attr_name = f"Relay {relay_num}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name=f"MeriTO Relay {self._mac}",
            manufacturer=MANUFACTURER,
            model=MODEL_RELAY,
        )

    @property
    def is_on(self) -> bool | None:
        return self._is_on

    @property
    def available(self) -> bool:
        return self._available

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic and restore previous state."""
        await super().async_added_to_hass()

        # Restore last known state across HA restarts
        if (last_state := await self.async_get_last_state()) is not None:
            self._is_on = last_state.state == "on"
            self._available = True
            _LOGGER.debug(
                "MeriTO: restored state=%s for %s", last_state.state, self.unique_id
            )

        @callback
        def _on_message(msg: mqtt.ReceiveMessage) -> None:
            """Parse incoming RELAYS payload and update entity state."""
            try:
                payload = json.loads(msg.payload)
            except (json.JSONDecodeError, ValueError):
                _LOGGER.error(
                    "MeriTO: bad JSON on topic '%s': %s", msg.topic, msg.payload
                )
                return

            relays_str = payload.get("RELAYS", "")
            if len(relays_str) != 8:
                _LOGGER.warning(
                    "MeriTO: unexpected RELAYS length (%d) on topic '%s'",
                    len(relays_str),
                    msg.topic,
                )
                return

            # Each relay occupies 2 bits: relay 1 = [0:2], relay 2 = [2:4] …
            start = (self._relay_num - 1) * 2
            bits = relays_str[start : start + 2]

            self._is_on = bits == RELAY_BIT_ON
            self._available = True

            _LOGGER.debug(
                "MeriTO: MAC=%s relay=%d bits=%s → is_on=%s",
                self._mac,
                self._relay_num,
                bits,
                self._is_on,
            )
            self.async_write_ha_state()

        unsub = await mqtt.async_subscribe(
            self.hass, self._data_topic, _on_message, qos=0
        )
        self._unsub_mqtt.append(unsub)
        _LOGGER.debug(
            "MeriTO: subscribed relay=%d to topic '%s'",
            self._relay_num,
            self._data_topic,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe MQTT when entity is removed."""
        for unsub in self._unsub_mqtt:
            unsub()
        self._unsub_mqtt.clear()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn relay ON — publish hex command."""
        cmd = RELAY_COMMANDS[self._relay_num]["on"]
        payload = f"relays={cmd} force=0"
        _LOGGER.debug(
            "MeriTO: TURN ON relay=%d MAC=%s → topic=%s payload=%s",
            self._relay_num,
            self._mac,
            self._set_topic,
            payload,
        )
        await mqtt.async_publish(
            self.hass,
            self._set_topic,
            payload,
            qos=1,
            retain=False,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn relay OFF — publish hex command."""
        cmd = RELAY_COMMANDS[self._relay_num]["off"]
        payload = f"relays={cmd} force=0"
        _LOGGER.debug(
            "MeriTO: TURN OFF relay=%d MAC=%s → topic=%s payload=%s",
            self._relay_num,
            self._mac,
            self._set_topic,
            payload,
        )
        await mqtt.async_publish(
            self.hass,
            self._set_topic,
            payload,
            qos=1,
            retain=False,
        )
