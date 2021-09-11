from pydantic import BaseModel

from app.api.gate_service import TargetState, CurrentState


class GateIn(BaseModel):
    action: TargetState


class GateOut(BaseModel):
    currentdoorstate: CurrentState


class Health(BaseModel):
    load1: float
    load5: float
    load15: float
    cpu_temp: float
    total_mem: int
    available_mem: int
    system_uptime: float
    process_uptime: float
