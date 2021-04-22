import unittest
from unittest.mock import patch, MagicMock, PropertyMock, call

import pifacedigitalio
from aiounittest import async_test

from app.api.config import DEFAULT_WEBHOOK_URL, DEFAULT_ACCESSORY_ID
from app.api.service import GateService, TargetState, CurrentState


@patch('app.api.service.httpx')
class TestService(unittest.TestCase):

    def setUp(self) -> None:
        # create piface_mock
        self.piface_mock = MagicMock()
        self.relays0_mock = PropertyMock()
        type(self.piface_mock.relays[0]).value = self.relays0_mock
        self.piface_mock.input_pins = [type("", (), dict(value=0))() for i in range(8)]
        # create event_listener_mock
        self.event_listener_mock = MagicMock()
        with patch('pifacedigitalio.PiFaceDigital', return_value=self.piface_mock):
            with patch('pifacedigitalio.InputEventListener', return_value=self.event_listener_mock):
                self.gate_service = GateService()

    def test_piface_initialization(self, httpx_mock):
        self.relays0_mock.assert_called_once_with(0)
        self.event_listener_mock.register.assert_any_call(0, pifacedigitalio.IODIR_BOTH,
                                                          self.gate_service._send_current_state_update)
        self.event_listener_mock.register.assert_any_call(1, pifacedigitalio.IODIR_BOTH,
                                                          self.gate_service._send_current_state_update)
        self.event_listener_mock.activate.assert_called_once()

    @async_test
    async def test_request_gate_movement_open(self, httpx_mock):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.OPEN)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_target_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'targetdoorstate': TargetState.OPEN.value}
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.OPEN.value}
        httpx_mock.get.assert_any_call(expected_url, params=expected_target_params)
        httpx_mock.get.assert_any_call(expected_url, params=expected_current_params)
        self.relays0_mock.assert_called_once_with(0)  # just the initialization of the relay

    @async_test
    async def test_request_gate_movement_opening(self, httpx_mock):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSED)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_target_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'targetdoorstate': TargetState.OPEN.value}
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.OPENING.value}
        httpx_mock.get.assert_any_call(expected_url, params=expected_target_params)
        httpx_mock.get.assert_any_call(expected_url, params=expected_current_params)
        self.relays0_mock.assert_has_calls([call(0), call(1), call(0)])  # one pulse of the relay

    @async_test
    async def test_request_gate_movement_closed(self, httpx_mock):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSED)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_target_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'targetdoorstate': TargetState.CLOSED.value}
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.CLOSED.value}
        httpx_mock.get.assert_any_call(expected_url, params=expected_target_params)
        httpx_mock.get.assert_any_call(expected_url, params=expected_current_params)
        self.relays0_mock.assert_called_once_with(0)  # just the initialization of the relay

    @async_test
    async def test_request_gate_movement_closing(self, httpx_mock):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.OPEN)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_target_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'targetdoorstate': TargetState.CLOSED.value}
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.CLOSING.value}
        httpx_mock.get.assert_any_call(expected_url, params=expected_target_params)
        httpx_mock.get.assert_any_call(expected_url, params=expected_current_params)
        self.relays0_mock.assert_has_calls([call(0), call(1), call(0)])  # one pulse of the relay

    @async_test
    async def test_get_current_gate_state(self, httpx_mock):
        # setup
        self.piface_mock.input_pins[0].value = 1  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        current_state = await self.gate_service.get_current_gate_state()
        # then
        self.assertEqual(CurrentState.OPEN, current_state)

    def test_open_event(self, httpx_mock):
        # setup
        self.piface_mock.input_pins[0].value = 1  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.OPEN.value}
        httpx_mock.get.assert_called_once_with(expected_url, params=expected_current_params)

    def test_closed_event(self, httpx_mock):
        # setup
        self.piface_mock.input_pins[0].value = 0  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 1  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.CLOSED.value}
        httpx_mock.get.assert_called_once_with(expected_url, params=expected_current_params)

    def test_opening_event(self, httpx_mock):
        # setup
        self.gate_service.last_stable_state = CurrentState.CLOSED
        self.piface_mock.input_pins[0].value = 0  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.OPENING.value}
        httpx_mock.get.assert_called_once_with(expected_url, params=expected_current_params)

    def test_closing_event(self, httpx_mock):
        # setup
        self.gate_service.last_stable_state = CurrentState.OPEN
        self.piface_mock.input_pins[0].value = 0  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.CLOSING.value}
        httpx_mock.get.assert_called_once_with(expected_url, params=expected_current_params)

    def test_stopped_event(self, httpx_mock):
        # setup
        # self.gate_service.last_stable_state is not initialized
        self.piface_mock.input_pins[0].value = 0  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        self.assertEqual(CurrentState.STOPPED, self.gate_service.last_stable_state)
        expected_url = DEFAULT_WEBHOOK_URL
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.STOPPED.value}
        httpx_mock.get.assert_called_once_with(expected_url, params=expected_current_params)

    def test_invalid_event(self, httpx_mock):
        # setup
        self.gate_service.last_stable_state = CurrentState.CLOSED
        self.piface_mock.input_pins[0].value = 1  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 1  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.STOPPED.value}
        httpx_mock.get.assert_called_once_with(expected_url, params=expected_current_params)
