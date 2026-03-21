import os

from app.api.logger import logger

LOG_LEVEL = 'LOG_LEVEL'
HOST = 'HOST'
PORT = 'PORT'
BASIC_AUTH_USERNAME = 'BASIC_AUTH_USERNAME'
BASIC_AUTH_PASSWORD = 'BASIC_AUTH_PASSWORD'
WEBHOOK_URL = 'WEBHOOK_URL'
ACCESSORY_ID = 'ACCESSORY_ID'
SPI_BUS = 'SPI_BUS'
SPI_CHIP_SELECT = 'SPI_CHIP_SELECT'
SPI_HARDWARE_ADDR = 'SPI_HARDWARE_ADDR'
DIDO_RELAY_PIN = 'DIDO_RELAY_PIN'

DEAULT_LOG_LEVEL = "INFO"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = "8000"
DEFAULT_WEBHOOK_URL = "http://localhost:51828"
DEFAULT_ACCESSORY_ID = "gatecontrol"
DEFAULT_SPI_BUS = 0
DEFAULT_SPI_CHIP_SELECT = 0
DEFAULT_SPI_HARDWARE_ADDR = 0
DEFAULT_DIDO_RELAY_PIN = 0


class Config:
    def __init__(self):
        self.reload()

    def reload(self):
        log_level = os.getenv(LOG_LEVEL, DEAULT_LOG_LEVEL)
        logger.setLevel(log_level)
        self.host = os.getenv(HOST, DEFAULT_HOST)
        self.port = os.getenv(PORT, DEFAULT_PORT)
        self.basic_auth_username = os.getenv(BASIC_AUTH_USERNAME)
        self.basic_auth_password = os.getenv(BASIC_AUTH_PASSWORD)
        self.webhook_url = os.getenv(WEBHOOK_URL, DEFAULT_WEBHOOK_URL)
        self.accessory_id = os.getenv(ACCESSORY_ID, DEFAULT_ACCESSORY_ID)
        self.spi_bus = int(os.getenv(SPI_BUS, DEFAULT_SPI_BUS))
        self.spi_chip_select = int(os.getenv(SPI_CHIP_SELECT, DEFAULT_SPI_CHIP_SELECT))
        self.spi_hardware_addr = int(os.getenv(SPI_HARDWARE_ADDR, DEFAULT_SPI_HARDWARE_ADDR))
        self.dido_relay_pin = int(os.getenv(DIDO_RELAY_PIN, DEFAULT_DIDO_RELAY_PIN))
        if not self.is_basic_auth_active():
            logger.warning(
                "BasicAuth deactivated. Set BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD environment variables.")

    def is_basic_auth_active(self) -> bool:
        return self.basic_auth_username is not None and self.basic_auth_password is not None


config = Config()
