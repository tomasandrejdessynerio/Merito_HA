"""MeriTO Technologies integration for Home Assistant.

Subscribes to MQTT topics and auto-discovers MeriTO devices by topic prefix:
  Relay/<domain>/<MAC>/Data  → creates a MeriTO Relay device with 4 switches
"""
from __future__ import annotations

import logging
import json

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.components import mqtt
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    CONF_MQTT_DOMAIN,
    DATA_DEVICES,
    DATA_UNSUB,
    DEVICE_TYPE_RELAY,
    TOPIC_SEGMENT_DEVICE_TYPE,
    TOPIC_SEGMENT_MAC,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MeriTO Technologies from a config entry."""

    mqtt_domain = entry.data[CONF_MQTT_DOMAIN]

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_DEVICES: {},   # mac -> device info dict
        DATA_UNSUB: [],     # list of unsubscribe callables
    }

    # Subscribe to all device data topics for this MQTT domain
    relay_topic = f"Relay/{mqtt_domain}/+/Data"

    _LOGGER.debug("MeriTO: subscribing to '%s'", relay_topic)

    @callback
    def _on_relay_message(msg: mqtt.ReceiveMessage) -> None:
        """Handle incoming MQTT message and register new devices."""
        try:
            parts = msg.topic.split("/")
            # Expected: Relay / <domain> / <MAC> / Data
            if len(parts) != 4:
                return

            device_type = parts[TOPIC_SEGMENT_DEVICE_TYPE]
            mac = parts[TOPIC_SEGMENT_MAC]

            if device_type != DEVICE_TYPE_RELAY:
                _LOGGER.warning(
                    "MeriTO: unknown device type '%s' in topic '%s'",
                    device_type,
                    msg.topic,
                )
                return

            entry_data = hass.data[DOMAIN][entry.entry_id]
            if mac in entry_data[DATA_DEVICES]:
                # Already registered — entity platform handles state updates
                return

            # Parse first message to validate payload
            try:
                payload = json.loads(msg.payload)
            except (json.JSONDecodeError, ValueError):
                _LOGGER.error(
                    "MeriTO: invalid JSON payload on topic '%s': %s",
                    msg.topic,
                    msg.payload,
                )
                return

            if "RELAYS" not in payload:
                _LOGGER.warning(
                    "MeriTO: missing RELAYS key in payload on topic '%s'",
                    msg.topic,
                )
                return

            _LOGGER.info(
                "MeriTO: discovered new Relay device MAC=%s on topic=%s",
                mac,
                msg.topic,
            )

            # Register device in HA device registry
            device_registry = dr.async_get(hass)
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, mac)},
                name=f"MeriTO Relay {mac}",
                manufacturer="MeriTO Technologies",
                model="MeriTO Relay",
                connections={(dr.CONNECTION_NETWORK_MAC, mac)},
            )

            # Store device info so switch platform can create entities
            entry_data[DATA_DEVICES][mac] = {
                "mac": mac,
                "mqtt_domain": mqtt_domain,
                "data_topic": msg.topic,
                "set_topic": f"Relay/{mqtt_domain}/{mac}/SetState",
            }

            # Forward to switch platform to create 4 switch entities
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
                if not entry.state.recoverable
                else _async_add_relay_switches(hass, entry, mac)
            )

        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception(
                "MeriTO: unexpected error processing message on '%s'", msg.topic
            )

    unsub = await mqtt.async_subscribe(
        hass, relay_topic, _on_relay_message, qos=0
    )
    hass.data[DOMAIN][entry.entry_id][DATA_UNSUB].append(unsub)

    # Forward platform setup (switch) — entities are added dynamically
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_add_relay_switches(
    hass: HomeAssistant, entry: ConfigEntry, mac: str
) -> None:
    """Signal the switch platform to add entities for a newly found device."""
    hass.bus.async_fire(
        f"{DOMAIN}_new_device",
        {"entry_id": entry.entry_id, "mac": mac},
    )


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update — reload integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and clean up subscriptions."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})
        for unsub in entry_data.get(DATA_UNSUB, []):
            unsub()

    return unload_ok
