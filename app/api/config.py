import os

from app.api.logger import logger

HOST = 'HOST'
PORT = 'PORT'
BASIC_AUTH_USERNAME = 'BASIC_AUTH_USERNAME'
BASIC_AUTH_PASSWORD = 'BASIC_AUTH_PASSWORD'
WEBHOOK_URL = 'WEBHOOK_URL'
ACCESSORY_ID = 'ACCESSORY_ID'

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = "8000"
DEFAULT_WEBHOOK_URL = "http://localhost:51828"
DEFAULT_ACCESSORY_ID = "gatecontrol"


class Config:
    def __init__(self):
        self.reload()

    def reload(self):
        self.host = os.getenv(HOST, DEFAULT_HOST)
        self.port = os.getenv(PORT, DEFAULT_PORT)
        self.basic_auth_username = os.getenv(BASIC_AUTH_USERNAME)
        self.basic_auth_password = os.getenv(BASIC_AUTH_PASSWORD)
        self.webhook_url = os.getenv(WEBHOOK_URL, DEFAULT_WEBHOOK_URL)
        self.accessory_id = os.getenv(ACCESSORY_ID, DEFAULT_ACCESSORY_ID)
        if not self.is_basic_auth_active():
            logger.warn(
                "BasicAuth deactivated. Set BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD environment variables.")

    def is_basic_auth_active(self) -> bool:
        return self.basic_auth_username is not None and self.basic_auth_password is not None


config = Config()
