from enum import Enum

import httpx

from app.api.config import config

CAST_SERVICE_HOST_URL = 'http://localhost:8002/api/v1/casts/'

class TargetState(Enum):
    OPEN = 0
    CLOSED = 1

class CurrentState(Enum):
    OPEN = 0
    CLOSED = 1
    OPENING = 2
    CLOSING = 3
    STOPPED = 4

async def request_gate_movement(target: TargetState) -> None:
    state = await get_current_gate_state()
    if target == TargetState.OPEN:
        send_target_state(TargetState.OPEN)
        if state == CurrentState.OPEN:
            send_current_state(CurrentState.OPEN)
        else:
            send_current_state(CurrentState.OPENING)
            move_gate(TargetState.OPEN)
    elif target == TargetState.CLOSED:
        send_target_state(TargetState.CLOSED)
        if state == CurrentState.CLOSED:
            send_current_state(CurrentState.CLOSED)
        else:
            send_current_state(CurrentState.CLOSING)
            move_gate(TargetState.CLOSED)


async def get_current_gate_state() -> CurrentState:
    return CurrentState.CLOSED
    # todo: implement lookup from hardware


def send_target_state(target: TargetState) -> bool:
    params = {'accessoryId': config.accessory_id, 'targetdoorstate': target.value}
    r = httpx.get(f'{config.webhook_url}', params=params)
    return True if r.status_code == 200 else False


def send_current_state(current: CurrentState) -> bool:
    params = {'accessoryId': config.accessory_id, 'currentdoorstate': current.value}
    r = httpx.get(f'{config.webhook_url}', params=params)
    return True if r.status_code == 200 else False


def move_gate(target: TargetState) -> None:
    return
    # todo: implement operation of hardware
