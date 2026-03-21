import typing
from asyncio import sleep
from enum import Enum

import httpx

from app.api.config import config
from app.api.gate_hardware import DidoSpiRelayHardware, GateHardware
from app.api.logger import logger

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

    def __init__(self, hardware: typing.Optional[GateHardware] = None):
        self.hardware = hardware or DidoSpiRelayHardware.from_config()
        if self.hardware.supports_inputs:
            self.last_stable_state = self._get_current_gate_state()
            self.hardware.start(self._handle_input_event)
        else:
            self.last_stable_state = CurrentState.STOPPED

    async def request_gate_movement(self, target_state: TargetState) -> None:
        if not self.hardware.supports_inputs:
            state = self._get_current_gate_state()
            if target_state == TargetState.OPEN and state == CurrentState.OPEN:
                return
            if target_state == TargetState.CLOSED and state == CurrentState.CLOSED:
                return
            await self._pulse_in1()
            self.last_stable_state = (
                CurrentState.OPEN if target_state == TargetState.OPEN else CurrentState.CLOSED
            )
            self._send_state(target_state, self.last_stable_state)
            return

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

    def _get_current_gate_state(self) -> CurrentState:
        if not self.hardware.supports_inputs:
            return self.last_stable_state
        # FAAC-E124 Configuration
        # OUT 1: OPEN or PAUSE (o1 = 05)
        # OUT 2: CLOSED (o2 = 06)
        out1_open = self.hardware.read_open_input()
        out2_closed = self.hardware.read_closed_input()
        logger.debug("OUT1: %d, OUT2: %d", out1_open, out2_closed)
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
            self.last_stable_state = CurrentState.STOPPED
            return CurrentState.STOPPED

    def _handle_input_event(self, event: typing.Any):
        self._send_current_state_update(event)

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
        logger.info("GET %s", r.url)
        r.raise_for_status()

    async def _pulse_in1(self) -> None:
        # FAAC-E124 Configuration
        # IN 1: OPEN A (LO = E or EP)
        self.hardware.set_relay(True)
        await sleep(PULSE_LENGTH)
        self.hardware.set_relay(False)
        await sleep(PULSE_LENGTH)
        return
