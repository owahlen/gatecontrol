import unittest

from fastapi.testclient import TestClient
from starlette import status

from app.main import app


class TestGateRouter(unittest.TestCase):

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_gate_get(self):
        # when
        response = self.client.get("/gate")
        # then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({"currentdoorstate": 1}, response.json())

    def test_gate_post(self):
        # when
        response = self.client.post("/gate", json={"action": 0})
        # then
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_gate_post_invalid_action(self):
        # when
        response = self.client.post("/gate", json={"action": -1})
        # then
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)
