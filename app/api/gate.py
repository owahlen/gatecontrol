from fastapi import Depends, APIRouter
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from starlette.responses import Response
from starlette.status import HTTP_200_OK

from app.api import auth
from app.api.auth import NoAuth
from app.api.config import config
from app.api.models import GateOut, GateIn
from app.api.service import request_gate_movement, get_current_gate_state

gate = APIRouter()
security = HTTPBasic if config.is_basic_auth_active() else NoAuth()


@gate.get('', response_model=GateOut)
async def get_gate_state():
    state = await get_current_gate_state()
    return {"currentdoorstate": state}


@gate.post('')
async def move_gate(payload: GateIn, credentials: HTTPBasicCredentials = Depends(security)):
    auth.authorize_request(credentials)
    await request_gate_movement(payload.action)
    return Response(status_code=HTTP_200_OK)
