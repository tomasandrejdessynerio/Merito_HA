"""Constants for MeriTO Technologies integration."""

DOMAIN = "merito_technologies"

# MQTT topic structure: Relay/DEMO/<MAC>/Data  |  Relay/DEMO/<MAC>/SetState
# Topic wildcard we subscribe to for auto-discovery
MQTT_DISCOVERY_TOPIC = "Relay/+/+/Data"

# Topic segments
TOPIC_SEGMENT_DEVICE_TYPE = 0   # e.g. "Relay"
TOPIC_SEGMENT_DOMAIN = 1        # e.g. "DEMO"
TOPIC_SEGMENT_MAC = 2           # e.g. "30-AE-A4-5B-E4-00"
TOPIC_SEGMENT_SUFFIX = 3        # "Data" or "SetState"

# Supported device type keywords in topic
DEVICE_TYPE_RELAY = "Relay"

# Number of relay channels per device
RELAY_COUNT = 4

# Bit-pair values in RELAYS string
RELAY_BIT_ON = "10"
RELAY_BIT_OFF = "01"

# Hex commands for each relay channel ON/OFF
# Format: (on_hex, off_hex) — uses "ponechať" (00) for all other channels
RELAY_COMMANDS = {
    1: {"on": "80", "off": "40"},
    2: {"on": "20", "off": "10"},
    3: {"on": "08", "off": "04"},
    4: {"on": "02", "off": "01"},
}

# Config entry keys
CONF_MQTT_DOMAIN = "mqtt_domain"   # e.g. "DEMO"

# Data keys stored in hass.data[DOMAIN]
DATA_DEVICES = "devices"
DATA_UNSUB = "unsub_mqtt"

# Device info
MANUFACTURER = "MeriTO Technologies"
MODEL_RELAY = "MeriTO Relay"
