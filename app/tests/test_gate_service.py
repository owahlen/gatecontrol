from unittest.mock import patch, MagicMock, call

from aiounittest import AsyncTestCase

from app.api.config import DEFAULT_WEBHOOK_URL, DEFAULT_ACCESSORY_ID
from app.api.gate_service import GateService, TargetState, CurrentState


@patch('app.api.gate_service.httpx')
class TestGateService(AsyncTestCase):

    def setUp(self) -> None:
        self.hardware_mock = MagicMock()
        self.hardware_mock.supports_inputs = False
        self.gate_service = GateService(hardware=self.hardware_mock)

    def test_hardware_initialization_without_inputs(self, mock_httpx):
        self.hardware_mock.start.assert_not_called()
        self.assertEqual(CurrentState.STOPPED, self.gate_service.last_stable_state)

    async def test_request_gate_movement_open_to_open(self, mock_httpx):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.OPEN)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        mock_httpx.get.assert_not_called()
        self.hardware_mock.set_relay.assert_not_called()

    async def test_request_gate_movement_stopped_to_open(self, mock_httpx):
        # setup
        mock_httpx.get = MagicMock(return_value=MagicMock())
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.STOPPED)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        mock_httpx.get.assert_called_once_with(
            DEFAULT_WEBHOOK_URL,
            params={
                'accessoryId': DEFAULT_ACCESSORY_ID,
                'targetdoorstate': TargetState.OPEN.value,
                'currentdoorstate': CurrentState.OPEN.value
            }
        )
        self.hardware_mock.set_relay.assert_has_calls([call(True), call(False)])
        self.assertEqual(CurrentState.OPEN, self.gate_service.last_stable_state)

    async def test_request_gate_movement_closed_to_closed(self, mock_httpx):
        # setup
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSED)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        mock_httpx.get.assert_not_called()
        self.hardware_mock.set_relay.assert_not_called()

    async def test_request_gate_movement_open_to_closed(self, mock_httpx):
        # setup
        mock_httpx.get = MagicMock(return_value=MagicMock())
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.OPEN)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        mock_httpx.get.assert_called_once_with(
            DEFAULT_WEBHOOK_URL,
            params={
                'accessoryId': DEFAULT_ACCESSORY_ID,
                'targetdoorstate': TargetState.CLOSED.value,
                'currentdoorstate': CurrentState.CLOSED.value
            }
        )
        self.hardware_mock.set_relay.assert_has_calls([call(True), call(False)])
        self.assertEqual(CurrentState.CLOSED, self.gate_service.last_stable_state)

    async def test_request_gate_movement_opening_to_open(self, mock_httpx):
        # setup
        mock_httpx.get = MagicMock(return_value=MagicMock())
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.OPENING)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        mock_httpx.get.assert_called_once()
        self.hardware_mock.set_relay.assert_has_calls([call(True), call(False)])

    async def test_request_gate_movement_closed_to_open(self, mock_httpx):
        # setup
        mock_httpx.get = MagicMock(return_value=MagicMock())
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSED)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        mock_httpx.get.assert_called_once()
        self.hardware_mock.set_relay.assert_has_calls([call(True), call(False)])

    async def test_request_gate_movement_closing_to_closed(self, mock_httpx):
        # setup
        mock_httpx.get = MagicMock(return_value=MagicMock())
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSING)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        mock_httpx.get.assert_called_once()
        self.hardware_mock.set_relay.assert_has_calls([call(True), call(False)])

    async def test_request_gate_movement_closing_to_open(self, mock_httpx):
        # setup
        mock_httpx.get = MagicMock(return_value=MagicMock())
        self.gate_service._get_current_gate_state = MagicMock(return_value=CurrentState.CLOSING)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        mock_httpx.get.assert_called_once()
        self.hardware_mock.set_relay.assert_has_calls([call(True), call(False)])

    async def test_get_current_gate_state(self, mock_httpx):
        # when
        current_state = await self.gate_service.get_current_gate_state()
        # then
        self.assertEqual(CurrentState.STOPPED, current_state)
