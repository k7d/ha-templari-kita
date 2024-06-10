from pymodbus.client import AsyncModbusTcpClient
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN
import voluptuous as vol
from . import modbus
from typing import Any
import logging


_LOGGER = logging.getLogger(__name__)

class KitaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self):
        self.client: AsyncModbusTcpClient | None = None

    async def configure_host(self, step_id: str, user_input: dict[str, Any]) -> FlowResult:
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            logging.warning(f"configured: {host}:{port}")
            if host is not None and port is not None:
                try:
                    self.client = await modbus.connect(host, port)
                    logging.warning(f"client: {self.client}")
                    return self.async_create_entry(
                        title=host,
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                        },
                    )
                except modbus.ClientException as e:
                    errors = {"base": e.error}

        return self.async_show_form(step_id=step_id, errors=errors, data_schema=vol.Schema({
            vol.Required(CONF_HOST, default="10.0.42.207"): str,
            vol.Required(CONF_PORT, default=4196): int, # 502
        }))

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        return await self.configure_host("user", user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        return await self.configure_host("reconfigure", user_input)
