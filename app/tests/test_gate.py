import unittest
from base64 import b64encode
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette import status

from app.api.config import config
from app.api.service import TargetState
from app.main import app
from app.tests.testing_utils import AsyncMock


@patch('app.api.gate.gate_service', new_callable=AsyncMock)
class TestGateRouter(unittest.TestCase):

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_gate_get(self, mock):
        # setup
        mock.get_current_gate_state.return_value = 1
        # when
        response = self.client.get("/gate")
        # then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({"currentdoorstate": 1}, response.json())
        mock.get_current_gate_state.assert_called()

    def test_gate_post(self, mock):
        # when
        response = self.client.post("/gate", json={"action": TargetState.CLOSED.value})
        # then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        mock.request_gate_movement.assert_called_with(TargetState.CLOSED)

    def test_gate_post_invalid_action(self, mock):
        # when
        response = self.client.post("/gate", json={"action": -1})
        # then
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)
        mock.request_gate_movement.assert_not_called()

    def test_gate_post_authenticated(self, mock):
        # setup
        config.basic_auth_username = "user"
        config.basic_auth_password = "password"
        # when
        response = self.client.post("/gate", json={"action": TargetState.OPEN.value},
                                    headers={"Authorization": self.get_basic_auth("user", "password")})
        # then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        mock.request_gate_movement.assert_called_with(TargetState.OPEN)
        # cleanup
        config.basic_auth_username = None
        config.basic_auth_password = None

    def test_gate_post_invalid_authentication(self, mock):
        # setup
        config.basic_auth_username = "user"
        config.basic_auth_password = "password"
        # when
        response = self.client.post("/gate", json={"action": 0},
                                    headers={"Authorization": self.get_basic_auth("user", "incorrect")})
        # then
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        mock.request_gate_movement.assert_not_called()
        # cleanup
        config.basic_auth_username = None
        config.basic_auth_password = None

    def get_basic_auth(self, username: str, password: str) -> str:
        user_and_pass = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
        return "Basic {}".format(user_and_pass)
