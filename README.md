# MeriTO Technologies — Home Assistant Integration

Custom integrácia pre zariadenia MeriTO Technologies komunikujúce cez MQTT.

## Podporované zariadenia

| Typ zariadenia | Topic prefix | Popis |
|---|---|---|
| MeriTO Relay | `Relay/` | 4-kanálové relé pole |

## Inštalácia cez HACS

1. V HACS klikni na **Custom repositories**
2. Pridaj URL tohto repozitára, kategória: **Integration**
3. Nainštaluj **MeriTO Technologies**
4. Reštartuj Home Assistant

## Konfigurácia

1. Choď do `Settings → Devices & Services → Add Integration`
2. Vyhľadaj **MeriTO Technologies**
3. Zadaj **MQTT doménu** (napr. `DEMO`) — zodpovedá druhému segmentu v topicu

## Štruktúra MQTT topicov

```
Relay/<DOMAIN>/<MAC>/Data       ← zariadenie posiela stav každú sekundu
Relay/<DOMAIN>/<MAC>/SetState   ← HA posiela príkazy
```

### Payload — Data topic
```json
{"ts": 1578844846, "RELAYS": "10100101", "ALARMS": "10100101"}
```
- `RELAYS`: 8 bitov, 4x 2-bitová dvojica (relé 1–4): `10`=ON, `01`=OFF

### Payload — SetState topic
```
relays=<HEX> force=0
```

## Auto-discovery

Integrácia počúva na `Relay/<DOMAIN>/+/Data`. Keď príde prvá správa od nového zariadenia (nová MAC adresa), automaticky sa vytvorí:
- **Device** v HA device registry
- **4 switch entity** (Relay 1 – Relay 4)

Žiadna manuálna konfigurácia zariadení nie je potrebná.

## Pridanie ďalšieho typu zariadenia

Stačí rozšíriť `__init__.py` o nový topic wildcard a nový event, potom pridať novú platformu (napr. `sensor.py`).

## Požiadavky

- Home Assistant 2023.6+
- Mosquitto broker add-on (alebo iný MQTT broker nakonfigurovaný v HA)
