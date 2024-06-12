from __future__ import annotations

import logging
from dataclasses import dataclass
from . import modbus

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

SENSOR_BUFFER_TANK_TEMP = 2
SENSOR_HOT_WATER_TEMP = 3
SEONSOR_HP_INLET_TEMP = 4
SENSOR_FLOW = 5
SENSOR_COMPRESSOR_HEAD_TEMP = 6
SENSOR_HP_OUTLET_TEMP = 7
SENSOR_EXTERNAL_TEMP = 8
SENSOR_DRAIN_TEMP = 9
SENSOR_SUCTION_TEMP = 10
SENSOR_HIGH_PRESSURE = 11
SENSOR_LOW_PRESSURE = 12
SENSOR_EVAPORATION = 13
SENSOR_CONDENSATION = 14
SENSOR_SH = 15
SENSOR_COMPRESSOR_SPEED = 18
SENSOR_COOLING_SETPOINT = 65
SENSOR_HEATING_SETPOINT = 66
SENSOR_HOT_WATER_SETPOINT = 67
SENSOR_HEATING_COOLING_SETPOINT = 68
SENSOR_EEV = 70
SENSOR_INJ = 72
SENSOR_TJ = 73
SENSOR_ENERGY_CONSUMPTION = 234


@dataclass
class KitaSensorEntityDescription(SensorEntityDescription):
    multiplier: float | None = None


SENSOR_TYPES = [
    KitaSensorEntityDescription(
        key=SENSOR_BUFFER_TANK_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heating/cooling buffer tank temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_HOT_WATER_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Hot water temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=SEONSOR_HP_INLET_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heat pump inlet temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_FLOW,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Flow",
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pipe",
    ),
    KitaSensorEntityDescription(
        key=SENSOR_COMPRESSOR_HEAD_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Compressor head temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_HP_OUTLET_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heat pump outlet temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_EXTERNAL_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="External temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_DRAIN_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Drain temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_SUCTION_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Suction temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_HIGH_PRESSURE,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="High pressure",
        native_unit_of_measurement=UnitOfPressure.BAR,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_LOW_PRESSURE,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Low pressure",
        native_unit_of_measurement=UnitOfPressure.BAR,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_EVAPORATION,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Evaporation",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_CONDENSATION,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Condensation",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_SH,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="SH",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_COMPRESSOR_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        name="Compressor speed",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        multiplier=6, # RPS * 10
        icon="mdi:fan",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_COOLING_SETPOINT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Cooling setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_HEATING_SETPOINT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heating setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_HEATING_COOLING_SETPOINT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Heating/cooling setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_HOT_WATER_SETPOINT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Hot water setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_EEV,
        state_class=SensorStateClass.MEASUREMENT,
        name="EEV",
        native_unit_of_measurement=PERCENTAGE,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_INJ,
        state_class=SensorStateClass.MEASUREMENT,
        name="Injection",
        native_unit_of_measurement=PERCENTAGE,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_TJ,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="TJ",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KitaSensorEntityDescription(
        key=SENSOR_ENERGY_CONSUMPTION,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        name="Energy consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
]

for i in [1, 16, 17] + list(range(19, 65)):
    SENSOR_TYPES.append(
        KitaSensorEntityDescription(
            key=i,
            name=f"R{i}",
            state_class=SensorStateClass.MEASUREMENT,
        )
    )

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    client = hass.data[const.DOMAIN][config_entry.entry_id]

    sensors = [
        KitaSensor(client=client, config_entry=config_entry, description=description)
        for description in SENSOR_TYPES
    ]

    async_add_entities(sensors, True)

def get_2comp(value):
    return value-2**16 if value & 2**15 else value

class KitaSensor(SensorEntity):
    entity_description: KitaSensorEntityDescription

    def __init__(
            self,
            client: AsyncModbusTcpClient,
            hass: HomeAssistant,
            config_entry: ConfigEntry,
            description: KitaSensorEntityDescription,
    ) -> None:
        self._client = client
        self.entity_description = description
        self._attr_unique_id = f"{description.key}"
        self.entity_id = generate_entity_id("sensor.{}", f"heat-pump-{description.name}", hass=hass)
        self._attr_device_info = DeviceInfo(
            identifiers={(const.DOMAIN, "heat-pump")},
            name=f"Heat pump",
            manufacturer=const.MANUFACTURER,
            model=const.MODEL,
        )

    async def async_update(self) -> None:
        descr = self.entity_description
        value = await modbus.read_register(self._client, descr.key)
        value = get_2comp(value) # handle negative values
        if descr.multiplier is not None:
            value *= descr.multiplier

        _LOGGER.debug(
            "Handle update for sensor %s (%d): %s",
            self.entity_description.name,
            self.entity_description.key,
            value,
        )

        self._attr_native_value = value
