from asyncio import sleep
from enum import Enum

import httpx
import pifacedigitalio

from app.api.config import config

PULSE_LENGTH = 0.5


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

    def __init__(self):
        self._init_piface()
        self.last_stable_state = None
        self.last_stable_state = self._get_current_gate_state()

    async def request_gate_movement(self, target: TargetState) -> None:
        state = self._get_current_gate_state()
        if target == TargetState.OPEN:
            self._send_target_state(TargetState.OPEN)
            if state == CurrentState.OPEN:
                self._send_current_state(CurrentState.OPEN)
            else:
                self._send_current_state(CurrentState.OPENING)
                await self._move_gate(TargetState.OPEN)
        elif target == TargetState.CLOSED:
            self._send_target_state(TargetState.CLOSED)
            if state == CurrentState.CLOSED:
                self._send_current_state(CurrentState.CLOSED)
            else:
                self._send_current_state(CurrentState.CLOSING)
                await self._move_gate(TargetState.CLOSED)

    async def get_current_gate_state(self) -> CurrentState:
        return self._get_current_gate_state()

    def _init_piface(self):
        self.piface = pifacedigitalio.PiFaceDigital()
        # relay[0] sends a short pulse to operate the gate. 0 is the inactive state.
        self.piface.relays[0].value = 0
        # register event listener on input_pins[0] and input_pins[1]
        self.event_listener = pifacedigitalio.InputEventListener(chip=self.piface)
        self.event_listener.register(0, pifacedigitalio.IODIR_BOTH, self._send_current_state_update)
        self.event_listener.register(1, pifacedigitalio.IODIR_BOTH, self._send_current_state_update)
        self.event_listener.activate()

    def _get_current_gate_state(self) -> CurrentState:
        # FAAC-E124 Configuration
        # OUT 1: OPEN or PAUSE (o1 = 05)
        # OUT 2: CLOSED (o2 = 06)
        out1_open = self.piface.input_pins[0].value
        out2_closed = self.piface.input_pins[1].value
        if out1_open and not out2_closed:
            self.last_stable_state = CurrentState.OPEN
            return CurrentState.OPEN
        elif not out1_open and out2_closed:
            self.last_stable_state = CurrentState.CLOSED
            return CurrentState.CLOSED
        elif not out1_open and not out2_closed and self.last_stable_state == CurrentState.OPEN:
            return CurrentState.CLOSING
        elif not out1_open and not out2_closed and self.last_stable_state == CurrentState.CLOSED:
            return CurrentState.OPENING
        else:
            return CurrentState.STOPPED

    def _send_current_state_update(self, event):
        state = self._get_current_gate_state()
        self._send_current_state(state)

    def _send_target_state(self, target: TargetState) -> bool:
        params = {'accessoryId': config.accessory_id, 'targetdoorstate': target.value}
        r = httpx.get(f'{config.webhook_url}', params=params)
        return True if r.status_code == 200 else False

    def _send_current_state(self, current: CurrentState) -> bool:
        params = {'accessoryId': config.accessory_id, 'currentdoorstate': current.value}
        r = httpx.get(f'{config.webhook_url}', params=params)
        return True if r.status_code == 200 else False

    async def _move_gate(self, target: TargetState) -> None:
        # FAAC-E124 Configuration
        # IN 1: OPEN A (LO = E or EP)
        self.piface.relays[0].value = 1
        await sleep(PULSE_LENGTH)
        self.piface.relays[0].value = 0
        return
