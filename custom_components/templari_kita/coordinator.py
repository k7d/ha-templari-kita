from datetime import timedelta
import logging
from . import modbus

from pymodbus.client import AsyncModbusTcpClient

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


# FROM_REGISTER_ADDR = 0
# TO_REGISTER_ADDR = 1280
# CHUNK_SIZE = 32

class KitaCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, client: AsyncModbusTcpClient, register_ranges):
        super().__init__(
            hass,
            _LOGGER,
            name="Templari Kita",
            update_interval=timedelta(seconds=30),
        )
        self.client = client
        self.register_ranges = register_ranges

    async def _async_update_data(self):
        data = {}
        for (from_addr, to_addr) in self.register_ranges:
            count = to_addr - from_addr + 1
            regs = await modbus.read_registers(self.client, from_addr, count)
            if regs and len(regs) > 0:
                for i, reg in enumerate(regs):
                    data[from_addr + i] = reg
            else:
                for i in range(count):
                    data[from_addr + i] = None
        return data
