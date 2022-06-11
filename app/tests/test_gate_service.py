import unittest
from unittest.mock import patch, MagicMock, PropertyMock, call

import pifacedigitalio
from aiounittest import async_test
from pifacecommon.interrupts import IODIR_ON

from app.api.config import DEFAULT_WEBHOOK_URL, DEFAULT_ACCESSORY_ID
from app.api.gate_service import GateService, TargetState, CurrentState


@patch('app.api.gate_service.httpx')
class TestGateService(unittest.TestCase):

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

    def test_piface_initialization(self, mock_httpx):
        self.relays0_mock.assert_called_once_with(0)
        self.event_listener_mock.register.assert_any_call(0, pifacedigitalio.IODIR_BOTH,
                                                          self.gate_service._send_current_state_update)
        self.event_listener_mock.register.assert_any_call(1, pifacedigitalio.IODIR_BOTH,
                                                          self.gate_service._send_current_state_update)
        self.event_listener_mock.register.assert_any_call(3, pifacedigitalio.IODIR_BOTH,
                                                          self.gate_service._set_relay_state)
        self.event_listener_mock.activate.assert_called_once()

    @async_test
    async def test_request_gate_movement_open_to_open(self, mock_httpx):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.OPEN)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        mock_httpx.get.assert_not_called()
        self.relays0_mock.assert_called_once_with(0)  # just the initialization of the relay

    @async_test
    async def test_request_gate_movement_closed_to_open(self, mock_httpx):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSED)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        mock_httpx.get.assert_not_called()
        self.relays0_mock.assert_has_calls([call(0), call(1), call(0)])  # one pulse of the relay

    @async_test
    async def test_request_gate_movement_closed_to_closed(self, mock_httpx):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSED)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        mock_httpx.get.assert_not_called()
        self.relays0_mock.assert_called_once_with(0)  # just the initialization of the relay

    @async_test
    async def test_request_gate_movement_open_to_closed(self, mock_httpx):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.OPEN)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        mock_httpx.get.assert_not_called()
        self.relays0_mock.assert_has_calls([call(0), call(1), call(0)])  # one pulse of the relay

    @async_test
    async def test_request_gate_movement_opening_to_open(self, mock_httpx):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.OPENING)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        mock_httpx.get.assert_not_called()
        self.relays0_mock.assert_called_once_with(0)  # just the initialization of the relay

    @async_test
    async def test_request_gate_movement_opening_to_closed(self, mock_httpx):
        # setup
        mock_httpx.get = MagicMock(return_value=MagicMock())
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.OPENING)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        mock_httpx.get.assert_has_calls([
            call(DEFAULT_WEBHOOK_URL,
                 params={'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.STOPPED.value}),
            call(DEFAULT_WEBHOOK_URL,
                 params={'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.CLOSING.value})
        ])
        # relay init, open pulse, close pulse
        self.relays0_mock.assert_has_calls([call(0), call(1), call(0), call(1), call(0)])

    @async_test
    async def test_request_gate_movement_closing_to_closed(self, mock_httpx):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSING)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        mock_httpx.get.assert_not_called()
        self.relays0_mock.assert_called_once_with(0)  # just the initialization of the relay

    @async_test
    async def test_request_gate_movement_closing_to_open(self, mock_httpx):
        # setup
        mock_httpx.get = MagicMock(return_value=MagicMock())
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSING)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        mock_httpx.get.assert_has_calls([
            call(DEFAULT_WEBHOOK_URL,
                 params={'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.STOPPED.value}),
            call(DEFAULT_WEBHOOK_URL,
                 params={'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.OPENING.value})
        ])
        # relay init, close pulse, open pulse
        self.relays0_mock.assert_has_calls([call(0), call(1), call(0), call(1), call(0)])

    @async_test
    async def test_get_current_gate_state(self, mock_httpx):
        # setup
        self.piface_mock.input_pins[0].value = 1  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        current_state = await self.gate_service.get_current_gate_state()
        # then
        self.assertEqual(CurrentState.OPEN, current_state)

    def test_open_event(self, mock_httpx):
        # setup
        self.piface_mock.input_pins[0].value = 1  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_params = {
            'accessoryId': DEFAULT_ACCESSORY_ID,
            'targetdoorstate': TargetState.OPEN.value,
            'currentdoorstate': CurrentState.OPEN.value
        }
        mock_httpx.get.assert_called_once_with(expected_url, params=expected_params)

    def test_closed_event(self, mock_httpx):
        # setup
        self.piface_mock.input_pins[0].value = 0  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 1  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_params = {
            'accessoryId': DEFAULT_ACCESSORY_ID,
            'targetdoorstate': TargetState.CLOSED.value,
            'currentdoorstate': CurrentState.CLOSED.value
        }
        mock_httpx.get.assert_called_once_with(expected_url, params=expected_params)

    def test_opening_event(self, mock_httpx):
        # setup
        self.gate_service.last_stable_state = CurrentState.CLOSED
        self.piface_mock.input_pins[0].value = 0  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_params = {
            'accessoryId': DEFAULT_ACCESSORY_ID,
            'targetdoorstate': TargetState.OPEN.value,
            'currentdoorstate': CurrentState.CLOSING.value  # this is a workaround for a homekit bug
        }
        mock_httpx.get.assert_called_once_with(expected_url, params=expected_params)

    def test_closing_event(self, mock_httpx):
        # setup
        self.gate_service.last_stable_state = CurrentState.OPEN
        self.piface_mock.input_pins[0].value = 0  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_params = {
            'accessoryId': DEFAULT_ACCESSORY_ID,
            'targetdoorstate': TargetState.CLOSED.value,
            'currentdoorstate': CurrentState.CLOSING.value
        }
        mock_httpx.get.assert_called_once_with(expected_url, params=expected_params)

    def test_stopped_event(self, mock_httpx):
        # setup
        # self.gate_service.last_stable_state is not initialized
        self.piface_mock.input_pins[0].value = 0  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 0  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        self.assertEqual(CurrentState.STOPPED, self.gate_service.last_stable_state)
        expected_url = DEFAULT_WEBHOOK_URL
        expected_params = {
            'accessoryId': DEFAULT_ACCESSORY_ID,
            'targetdoorstate': TargetState.OPEN.value,
            'currentdoorstate': CurrentState.STOPPED.value
        }
        mock_httpx.get.assert_called_once_with(expected_url, params=expected_params)

    def test_invalid_event(self, mock_httpx):
        # setup
        self.gate_service.last_stable_state = CurrentState.CLOSED
        self.piface_mock.input_pins[0].value = 1  # OPEN or PAUSED
        self.piface_mock.input_pins[1].value = 1  # CLOSED
        # when
        self.gate_service._send_current_state_update(None)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_params = {
            'accessoryId': DEFAULT_ACCESSORY_ID,
            'targetdoorstate': TargetState.OPEN.value,
            'currentdoorstate': CurrentState.STOPPED.value
        }
        mock_httpx.get.assert_called_once_with(expected_url, params=expected_params)

    def test_set_relay_state(self, mock_httpx):
        # setup
        event_mock = MagicMock()
        direction_mock = PropertyMock(return_value = IODIR_ON)
        type(event_mock).direction = direction_mock
        # when
        self.gate_service._set_relay_state(event_mock)
        # then
        mock_httpx.get.assert_not_called()
        self.relays0_mock.assert_has_calls([call(0), call(1)])