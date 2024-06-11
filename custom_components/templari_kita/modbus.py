from pymodbus.client import AsyncModbusTcpClient
from pymodbus import ExceptionResponse
import logging

_LOGGER = logging.getLogger(__name__)

class ClientException(Exception):
    def __init__(self, error):
        self.error = error


async def read_register(client, address) -> int | None:
    rr = await client.read_input_registers(address, 1, slave=1)
    if rr.isError() or isinstance(rr, ExceptionResponse):
        _LOGGER.warning(f"Modbus error while reading register {address} ({rr})")
        return None
    if len(rr.registers) == 0:
        _LOGGER.warning(f"Empty Modbus response while reading register {address}")
        return None
    return rr.registers[0]


async def connect(host: str, port: int) -> AsyncModbusTcpClient:
    client = AsyncModbusTcpClient(host=host, port=port)
    await client.connect()
    if not client.connected:
        raise ClientException("invalid_host")
    # Make sure there is a valid response:
    if await read_register(client, 0) is None:
        raise ClientException("invalid_host")
    return client
