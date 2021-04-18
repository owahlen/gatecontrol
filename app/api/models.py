from pydantic import BaseModel

from app.api.service import TargetState, CurrentState


class GateIn(BaseModel):
    action: TargetState


class GateOut(BaseModel):
    currentdoorstate: CurrentState
