from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from .coordinator import KitaCoordinator
from . import modbus

from homeassistant.core import callback

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
    UnitOfPressure,
    UnitOfPower,
    REVOLUTIONS_PER_MINUTE,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory, generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pymodbus.client import AsyncModbusTcpClient
from . import const

_LOGGER = logging.getLogger(__name__)

REG_ADDR_BUFFER_TANK_TEMP = 2
REG_ADDR_HOT_WATER_TEMP = 3
REG_ADDR_HP_INLET_TEMP = 4
REG_ADDR_FLOW = 5
REG_ADDR_COMPRESSOR_HEAD_TEMP = 6
REG_ADDR_HP_OUTLET_TEMP = 7
REG_ADDR_EXTERNAL_TEMP = 8
REG_ADDR_DRAIN_TEMP = 9
REG_ADDR_SUCTION_TEMP = 10
REG_ADDR_HIGH_PRESSURE = 11
REG_ADDR_LOW_PRESSURE = 12
REG_ADDR_EVAPORATION = 13
REG_ADDR_CONDENSATION = 14
REG_ADDR_SH = 15
REG_ADDR_COMPRESSOR_SPEED = 18
REG_ADDR_COOLING_SETPOINT = 65
REG_ADDR_HEATING_SETPOINT = 66
REG_ADDR_HOT_WATER_SETPOINT = 67
REG_ADDR_HEATING_COOLING_SETPOINT = 68
REG_ADDR_EEV = 70
REG_ADDR_INJ = 72
REG_ADDR_TJ = 73
REG_ADDR_ENERGY_CONSUMPTION = 234
REG_ADDR_MODE = 1081

REG_RANGES = [
    (REG_ADDR_BUFFER_TANK_TEMP,REG_ADDR_COMPRESSOR_SPEED),
    (REG_ADDR_COOLING_SETPOINT,REG_ADDR_TJ),
    (REG_ADDR_ENERGY_CONSUMPTION,REG_ADDR_ENERGY_CONSUMPTION),
    (REG_ADDR_MODE,REG_ADDR_MODE),
]

@dataclass
class KitaSensorEntityDescription(SensorEntityDescription):
    multiplier: float | None = None


SENSOR_TYPES = [
    KitaSensorEntityDescription(
        key=REG_ADDR_BUFFER_TANK_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heating/cooling buffer tank temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_HOT_WATER_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Hot water temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_HP_INLET_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heat pump inlet temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_FLOW,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Flow",
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pipe",
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_COMPRESSOR_HEAD_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Compressor head temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_HP_OUTLET_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heat pump outlet temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_EXTERNAL_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="External temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_DRAIN_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Drain temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_SUCTION_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Suction temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_HIGH_PRESSURE,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="High pressure",
        native_unit_of_measurement=UnitOfPressure.BAR,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_LOW_PRESSURE,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Low pressure",
        native_unit_of_measurement=UnitOfPressure.BAR,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_EVAPORATION,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Evaporation",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_CONDENSATION,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Condensation",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_SH,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="SH",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_COMPRESSOR_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        name="Compressor speed",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        multiplier=6,  # RPS * 10
        icon="mdi:fan",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_COOLING_SETPOINT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Cooling setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_HEATING_SETPOINT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heating setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_HEATING_COOLING_SETPOINT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heating/cooling setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_HOT_WATER_SETPOINT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Hot water setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_EEV,
        state_class=SensorStateClass.MEASUREMENT,
        name="EEV",
        native_unit_of_measurement=PERCENTAGE,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_INJ,
        state_class=SensorStateClass.MEASUREMENT,
        name="Injection",
        native_unit_of_measurement=PERCENTAGE,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_TJ,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="TJ",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_ENERGY_CONSUMPTION,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        name="Energy consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    KitaSensorEntityDescription(
        key=REG_ADDR_MODE,
        name="Mode",
        device_class=SensorDeviceClass.ENUM,
    )
]


# for i in [1, 31, 32, 33, 41, 42, 56, 69, 71] + list(range(74, 234)) + list(range(235, 1280)):
#     REG_ADDR_TYPES.append(
#         KitaSensorEntityDescription(
#             key=i,
#             name=f"R{i}",
#             state_class=SensorStateClass.MEASUREMENT,
#         )
#     )

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id]["coordinator"]

    sensors = [
        KitaSensor(hass=hass, coordinator=coordinator, config_entry=config_entry, description=description)
        for description in SENSOR_TYPES
    ] + [
        KitaActiveSensor(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            key="hp-inlet-temp-hc",
            name="Heat pump inlet temperature (heating/cooling)",
            track_modes={1},
            reg_addr=REG_ADDR_HP_INLET_TEMP,
        ),
        KitaActiveSensor(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            key="hp-outlet-temp-hc",
            name="Heat pump outlet temperature (heating/cooling)",
            track_modes={1},
            reg_addr=REG_ADDR_HP_OUTLET_TEMP,
        ),
        KitaActiveSensor(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            key="hp-inlet-temp-dhw",
            name="Heat pump inlet temperature (hot water)",
            track_modes={2, 3},
            reg_addr=REG_ADDR_HP_INLET_TEMP,
        ),
        KitaActiveSensor(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            key="hp-outlet-temp-dhw",
            name="Heat pump outlet temperature (hot water)",
            track_modes={2, 3},
            reg_addr=REG_ADDR_HP_OUTLET_TEMP,
        ),
    ]

    async_add_entities(sensors, True)


def create_device_info():
    return DeviceInfo(
        identifiers={(const.DOMAIN, "heat-pump")},
        name=f"Heat pump",
        manufacturer=const.MANUFACTURER,
        model=const.MODEL,
    )


def get_2comp(value):
    return value - 2 ** 16 if value & 2 ** 15 else value


class KitaSensor(CoordinatorEntity, SensorEntity):
    entity_description: KitaSensorEntityDescription

    def __init__(
            self,
            hass: HomeAssistant,
            coordinator: KitaCoordinator,
            config_entry: ConfigEntry,
            description: KitaSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{description.key}"
        self.entity_id = generate_entity_id("sensor.{}", f"heat-pump-{description.name}", hass=hass)
        self._attr_device_info = create_device_info()

    @callback
    def _handle_coordinator_update(self) -> None:
        descr = self.entity_description
        value = self.coordinator.data[descr.key]
        if value is None:
            self._attr_available = False
            return
        self._attr_available = True
        value = get_2comp(value)  # handle negative values
        if descr.multiplier is not None:
            value *= descr.multiplier
        self._attr_native_value = value
        self.async_write_ha_state()


class KitaActiveSensor(CoordinatorEntity, SensorEntity):
    def __init__(
            self,
            hass: HomeAssistant,
            coordinator: KitaCoordinator,
            config_entry: ConfigEntry,
            key: str,
            name: str,
            track_modes: set,
            reg_addr: int,

    ) -> None:
        super().__init__(coordinator)
        self.track_modes = track_modes
        self.reg_addr = reg_addr
        description = SensorEntityDescription(
            key=key,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            name=name,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        )
        self.entity_description = description
        self._attr_unique_id = f"{description.key}"
        self.entity_id = generate_entity_id("sensor.{}", f"heat-pump-{description.name}", hass=hass)
        self._attr_device_info = create_device_info()

    @callback
    def _handle_coordinator_update(self) -> None:
        descr = self.entity_description
        mode = self.coordinator.data[REG_ADDR_MODE]
        if mode in self.track_modes:
            value = self.coordinator.data[self.reg_addr]
            if value is None:
                self._attr_available = False
                return
            self._attr_available = True
            value = get_2comp(value)
            value *= 0.1
            self._attr_native_value = value
            self.async_write_ha_state()
        else:
            self._attr_native_value = None
            self.async_write_ha_state()
