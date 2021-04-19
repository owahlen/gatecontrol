import unittest
from unittest.mock import patch

from aiounittest import async_test

from app.api.config import DEFAULT_WEBHOOK_URL, DEFAULT_ACCESSORY_ID
from app.api.service import GateService, TargetState, CurrentState
from app.tests.testing_utils import AsyncMock


@patch('app.api.service.httpx')
class TestService(unittest.TestCase):

    def setUp(self) -> None:
        self.gate_service = GateService()

    @async_test
    async def test_request_gate_movement_open(self, httpx_mock):
        # setup
        self.gate_service.get_current_gate_state = AsyncMock(return_value=CurrentState.OPEN)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_target_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'targetdoorstate': TargetState.OPEN.value}
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.OPEN.value}
        httpx_mock.get.assert_any_call(expected_url, params=expected_target_params)
        httpx_mock.get.assert_any_call(expected_url, params=expected_current_params)

    @async_test
    async def test_request_gate_movement_opening(self, httpx_mock):
        # setup
        self.gate_service.get_current_gate_state = AsyncMock(return_value=CurrentState.CLOSED)
        # when
        await self.gate_service.request_gate_movement(TargetState.OPEN)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_target_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'targetdoorstate': TargetState.OPEN.value}
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.OPENING.value}
        httpx_mock.get.assert_any_call(expected_url, params=expected_target_params)
        httpx_mock.get.assert_any_call(expected_url, params=expected_current_params)

    @async_test
    async def test_request_gate_movement_closed(self, httpx_mock):
        # setup
        self.gate_service.get_current_gate_state = AsyncMock(return_value=CurrentState.CLOSED)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_target_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'targetdoorstate': TargetState.CLOSED.value}
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.CLOSED.value}
        httpx_mock.get.assert_any_call(expected_url, params=expected_target_params)
        httpx_mock.get.assert_any_call(expected_url, params=expected_current_params)

    @async_test
    async def test_request_gate_movement_closing(self, httpx_mock):
        # setup
        self.gate_service.get_current_gate_state = AsyncMock(return_value=CurrentState.OPEN)
        # when
        await self.gate_service.request_gate_movement(TargetState.CLOSED)
        # then
        expected_url = DEFAULT_WEBHOOK_URL
        expected_target_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'targetdoorstate': TargetState.CLOSED.value}
        expected_current_params = {'accessoryId': DEFAULT_ACCESSORY_ID, 'currentdoorstate': CurrentState.CLOSING.value}
        httpx_mock.get.assert_any_call(expected_url, params=expected_target_params)
        httpx_mock.get.assert_any_call(expected_url, params=expected_current_params)
