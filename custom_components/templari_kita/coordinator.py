from datetime import timedelta
import logging
from . import modbus

from pymodbus.client import AsyncModbusTcpClient

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


FROM_REGISTER_ADDR = 0
TO_REGISTER_ADDR = 1280
CHUNK_SIZE = 32

class KitaCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, client: AsyncModbusTcpClient):
        super().__init__(
            hass,
            _LOGGER,
            name="Templari Kita",
            update_interval=timedelta(seconds=30),
        )
        self.client = client

    async def _async_update_data(self):
        return [reg async for reg in modbus.read_registers_chunked(self.client, FROM_REGISTER_ADDR, TO_REGISTER_ADDR, chunk_size=CHUNK_SIZE)]
