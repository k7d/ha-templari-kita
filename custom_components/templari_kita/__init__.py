"""Support to monitor and control Templari Kita heat pump via Modbus TCP + VNC."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.exceptions import ConfigEntryError
from . import modbus
from .coordinator import KitaCoordinator
from .sensor import REG_RANGES

import logging
from .const import DOMAIN

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    try:
        client = await modbus.connect(entry.data[CONF_HOST], entry.data[CONF_PORT])
    except modbus.ClientException as e:
        _LOGGER.error(f"Failed to connect to {entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}")
        raise ConfigEntryError from e

    coordinator = KitaCoordinator(hass, client, REG_RANGES)

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def close_connection(event):
        client.close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close_connection)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN][entry.entry_id]
        data["client"].close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
