import typing
from asyncio import sleep
from enum import Enum

import httpx
import pifacedigitalio

from app.api.config import config

PULSE_LENGTH = 0.5


class TargetState(int, Enum):
    OPEN = 0
    CLOSED = 1


class CurrentState(int, Enum):
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

    async def request_gate_movement(self, target_state: TargetState) -> None:
        state = self._get_current_gate_state()
        if target_state == TargetState.OPEN:
            if state == CurrentState.CLOSING:
                # stop the closing
                await self._pulse_in1()
                self._send_state(None, CurrentState.STOPPED)
                # open the gate
                await self._pulse_in1()
                self._send_state(None, CurrentState.OPENING)
                self.last_stable_state = CurrentState.OPENING
            elif state == CurrentState.CLOSED or state == CurrentState.STOPPED:
                # only open the gate if it is currently closed or stopped
                await self._pulse_in1()
        else:
            if state == CurrentState.OPENING:
                # stop the opening
                await self._pulse_in1()
                self._send_state(None, CurrentState.STOPPED)
                # close the gate
                await self._pulse_in1()
                self._send_state(None, CurrentState.CLOSING)
                self.last_stable_state = CurrentState.CLOSING
            elif state == CurrentState.OPEN or state == CurrentState.STOPPED:
                # only close the gate if it is currently open or stopped
                await self._pulse_in1()

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
        elif not out1_open and not out2_closed and self.last_stable_state == CurrentState.OPENING:
            return CurrentState.OPENING
        elif not out1_open and not out2_closed and self.last_stable_state == CurrentState.CLOSING:
            return CurrentState.CLOSING
        else:
            return CurrentState.STOPPED

    def _send_current_state_update(self, event):
        state = self._get_current_gate_state()
        # set targetdoorstate
        if state == CurrentState.OPEN or state == CurrentState.OPENING or state == CurrentState.STOPPED:
            target_state = TargetState.OPEN
        else:
            target_state = TargetState.CLOSED
        # set currentdoorstate
        # The following condition is a workaround for a homebridge bug:
        # Sending OPENING leads to a push message to the phone that the gate is already open.
        # Sending CLOSING while the gate is actually OPENING leads to the right message
        # and inhibits the premature push message.
        if state == CurrentState.OPENING:
            current_state = CurrentState.CLOSING
        else:
            current_state = state
        self._send_state(target_state, current_state)

    def _send_state(self, target_state: typing.Optional[TargetState], current_state: typing.Optional[CurrentState]):
        params = {'accessoryId': config.accessory_id}
        if target_state is not None:
            params['targetdoorstate'] = target_state.value
        if current_state is not None:
            params['currentdoorstate'] = current_state.value
        r = httpx.get(f'{config.webhook_url}', params=params)
        r.raise_for_status()

    async def _pulse_in1(self) -> None:
        # FAAC-E124 Configuration
        # IN 1: OPEN A (LO = E or EP)
        self.piface.relays[0].value = 1
        await sleep(PULSE_LENGTH)
        self.piface.relays[0].value = 0
        await sleep(PULSE_LENGTH)
        return
