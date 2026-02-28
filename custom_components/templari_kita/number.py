"""Number entities for controlling Templari Kita heat pump setpoints."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import const, vnc
from .coordinator import KitaCoordinator
from .sensor import (
    REG_ADDR_COOLING_SETPOINT,
    REG_ADDR_HEATING_SETPOINT,
    REG_ADDR_HOT_WATER_SETPOINT,
    create_device_info,
    get_2comp,
)

_LOGGER = logging.getLogger(__name__)

# Lock to serialise VNC operations (single-connection VNC server)
_VNC_LOCK = asyncio.Lock()


SETPOINT_ENTITIES = [
    {
        "key": "heating_setpoint",
        "name": "Heating setpoint",
        "vnc_key": "winter",
        "reg_addr": REG_ADDR_HEATING_SETPOINT,
        "min_value": 20.0,
        "max_value": 55.0,
        "icon": "mdi:fire",
    },
    {
        "key": "hot_water_setpoint",
        "name": "Hot water setpoint",
        "vnc_key": "dhw",
        "reg_addr": REG_ADDR_HOT_WATER_SETPOINT,
        "min_value": 30.0,
        "max_value": 60.0,
        "icon": "mdi:water-boiler",
    },
    {
        "key": "cooling_setpoint",
        "name": "Cooling setpoint",
        "vnc_key": "summer",
        "reg_addr": REG_ADDR_COOLING_SETPOINT,
        "min_value": 5.0,
        "max_value": 25.0,
        "icon": "mdi:snowflake",
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities for heat pump setpoint control."""
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id]["coordinator"]
    hmi_host = config_entry.data.get(const.CONF_HMI_HOST, const.DEFAULT_HMI_HOST)

    entities = [
        KitaSetpointNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            hmi_host=hmi_host,
            **desc,
        )
        for desc in SETPOINT_ENTITIES
    ]

    async_add_entities(entities, True)


class KitaSetpointNumber(CoordinatorEntity, NumberEntity):
    """A number entity that reads setpoints from Modbus and writes via VNC."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: KitaCoordinator,
        config_entry: ConfigEntry,
        hmi_host: str,
        key: str,
        name: str,
        vnc_key: str,
        reg_addr: int,
        min_value: float,
        max_value: float,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._hmi_host = hmi_host
        self._vnc_key = vnc_key
        self._reg_addr = reg_addr

        self._attr_unique_id = f"setpoint_{key}"
        self.entity_id = generate_entity_id(
            "number.{}", f"heat-pump-{name}", hass=hass
        )
        self._attr_device_info = create_device_info()
        self._attr_has_entity_name = False
        self._attr_name = name
        self._attr_icon = icon

        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = const.SETPOINT_STEP
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_mode = NumberMode.BOX

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update state from coordinator Modbus data."""
        raw = self.coordinator.data.get(self._reg_addr)
        if raw is None:
            self._attr_available = False
        else:
            self._attr_available = True
            self._attr_native_value = get_2comp(raw) * 0.1
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set new setpoint value via VNC to the HMI."""
        current = self._attr_native_value
        if current is None:
            _LOGGER.error("Cannot set %s: current value unknown", self._vnc_key)
            return

        # Round to step
        value = round(value / const.SETPOINT_STEP) * const.SETPOINT_STEP

        diff = value - current
        clicks = int(round(diff / const.SETPOINT_STEP))

        if clicks == 0:
            return

        if abs(clicks) > const.MAX_SETPOINT_CLICKS:
            _LOGGER.error(
                "Setpoint change too large for %s: %s -> %s (%d clicks, max %d)",
                self._vnc_key,
                current,
                value,
                abs(clicks),
                const.MAX_SETPOINT_CLICKS,
            )
            return

        _LOGGER.info(
            "Setting %s setpoint: %.1f -> %.1f (%+d clicks)",
            self._vnc_key,
            current,
            value,
            clicks,
        )

        async with _VNC_LOCK:
            try:
                await vnc.adjust_setpoint(self._hmi_host, self._vnc_key, clicks)
            except Exception:
                _LOGGER.exception("Failed to set %s via VNC", self._vnc_key)
                return

        # Optimistically update local state so the UI reflects the change
        # immediately instead of waiting for the next coordinator poll.
        self._attr_native_value = value
        self.async_write_ha_state()

        # Schedule a coordinator refresh after the HMI writes to PLC (~30 s)
        self.hass.loop.call_later(
            35, lambda: self.hass.async_create_task(
                self.coordinator.async_request_refresh()
            )
        )
