import secrets

from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from starlette import status
from starlette.requests import Request

from app.api.config import config


class NoAuth():
    async def __call__(self, request: Request):
        return


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
