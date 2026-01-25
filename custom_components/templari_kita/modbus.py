import time

from pymodbus.client import AsyncModbusTcpClient
from pymodbus import ExceptionResponse
import logging

_LOGGER = logging.getLogger(__name__)

class ClientException(Exception):
    def __init__(self, error):
        self.error = error


async def read_registers(client, address, count) -> [int]:
    rr = await client.read_input_registers(address, count=count, device_id=1)
    if rr.isError() or isinstance(rr, ExceptionResponse):
        _LOGGER.warning(f"Modbus error while reading register {address} ({rr})")
        return None
    return rr.registers


async def read_register(client, address) -> int | None:
    registers = await read_registers(client, address, 1)
    if len(registers) == 0:
        _LOGGER.warning(f"Empty Modbus response while reading register {address}")
        return None
    return registers[0]


async def read_registers_chunked(client, from_adr, to_adr, chunk_size=32):
    starttime = time.time()
    errors = 0
    for adr in range(from_adr, to_adr, chunk_size):
        rr = await client.read_input_registers(adr, count=chunk_size, device_id=1)
        error = False
        if rr.isError():
            error = True
            print(f"regs[{adr}-{adr+chunk_size}] = modbus error({rr})")
            _LOGGER.warning(f"registers[{adr}:{adr+chunk_size}] = modbus error({rr})")
        if isinstance(rr, ExceptionResponse):
            error = True
            _LOGGER.warning(f"registers[{adr}:{adr+chunk_size}] = modbus error({rr})")
        if len(rr.registers) == 0:
            error = True
            _LOGGER.warning(f"registers[{adr}:{adr+chunk_size}] = empty response")
        if error:
            errors += 1
            for i in range(chunk_size):
                if adr + i < to_adr:
                    yield None
        else:
            for r in rr.registers:
                yield r
    _LOGGER.debug(f"registers: {to_adr-from_adr} | chunk:{chunk_size} |  ellapsed time: {(time.time() - starttime):.1f}s | errors: {errors}/{errors*chunk_size}")


async def connect(host: str, port: int) -> AsyncModbusTcpClient:
    client = AsyncModbusTcpClient(host=host, port=port)
    await client.connect()
    if not client.connected:
        raise ClientException("invalid_host")
    # Make sure there is a valid response:
    if await read_register(client, 0) is None:
        raise ClientException("invalid_host")
    return client
