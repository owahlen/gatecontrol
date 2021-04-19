from enum import Enum

import httpx

from app.api.config import config


class TargetState(Enum):
    OPEN = 0
    CLOSED = 1


class CurrentState(Enum):
    OPEN = 0
    CLOSED = 1
    OPENING = 2
    CLOSING = 3
    STOPPED = 4


class GateService:
    async def request_gate_movement(self, target: TargetState) -> None:
        state = await self.get_current_gate_state()
        if target == TargetState.OPEN:
            self._send_target_state(TargetState.OPEN)
            if state == CurrentState.OPEN:
                self._send_current_state(CurrentState.OPEN)
            else:
                self._send_current_state(CurrentState.OPENING)
                self._move_gate(TargetState.OPEN)
        elif target == TargetState.CLOSED:
            self._send_target_state(TargetState.CLOSED)
            if state == CurrentState.CLOSED:
                self._send_current_state(CurrentState.CLOSED)
            else:
                self._send_current_state(CurrentState.CLOSING)
                self._move_gate(TargetState.CLOSED)

    async def get_current_gate_state(self) -> CurrentState:
        return CurrentState.CLOSED
        # todo: implement lookup from hardware

    def _send_target_state(self, target: TargetState) -> bool:
        params = {'accessoryId': config.accessory_id, 'targetdoorstate': target.value}
        r = httpx.get(f'{config.webhook_url}', params=params)
        return True if r.status_code == 200 else False

    def _send_current_state(self, current: CurrentState) -> bool:
        params = {'accessoryId': config.accessory_id, 'currentdoorstate': current.value}
        r = httpx.get(f'{config.webhook_url}', params=params)
        return True if r.status_code == 200 else False

    def _move_gate(self, target: TargetState) -> None:
        return
        # todo: implement operation of hardware
