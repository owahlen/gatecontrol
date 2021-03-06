from fastapi import Depends, APIRouter, BackgroundTasks
from fastapi.security import HTTPBasicCredentials
from starlette.responses import Response
from starlette.status import HTTP_200_OK

from app.api import auth
from app.api.auth import ConfigurableHTTPBasic
from app.api.gate_service import GateService
from app.api.models import GateOut, GateIn

gate_router = APIRouter()
security = ConfigurableHTTPBasic()
gate_service = GateService()


@gate_router.get('', response_model=GateOut)
async def get_gate_state():
    state = await gate_service.get_current_gate_state()
    return {"currentdoorstate": state}


@gate_router.post('')
async def move_gate(payload: GateIn,
                    background_tasks: BackgroundTasks,
                    credentials: HTTPBasicCredentials = Depends(security)):
    auth.authorize_request(credentials)
    background_tasks.add_task(gate_service.request_gate_movement, payload.action)
    return Response(status_code=HTTP_200_OK)
