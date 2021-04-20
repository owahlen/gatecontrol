import secrets

from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from starlette import status
from starlette.requests import Request

from app.api.config import config


class ConfigurableHTTPBasic:
    def __init__(self):
        self.http_basic = HTTPBasic()

    async def __call__(self, request: Request):
        if config.is_basic_auth_active():
            return await self.http_basic(request)
        else:
            return None


def authorize_request(credentials: HTTPBasicCredentials):
    if credentials is not None and config.is_basic_auth_active():
        correct_username = secrets.compare_digest(credentials.username, config.basic_auth_username)
        correct_password = secrets.compare_digest(credentials.password, config.basic_auth_password)
        if not (correct_username and correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
