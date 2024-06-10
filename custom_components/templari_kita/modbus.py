from pymodbus.client import AsyncModbusTcpClient
from pymodbus import ExceptionResponse


class ClientException(Exception):
    def __init__(self, error):
        self.error = error


async def read_register(client, address):
    rr = await client.read_input_registers(address, 1, slave=1)
    if rr.isError() or isinstance(rr, ExceptionResponse):
        raise ClientException(f"read_error")
    return rr.registers[0]


async def connect(host: str, port: int):
    client = AsyncModbusTcpClient(host=host, port=port)
    await client.connect()
    if not client.connected:
        raise ClientException("invalid_host")
    await read_register(client, 0) # make sure there is a valid response
    return client
