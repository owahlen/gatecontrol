import unittest

from fastapi.testclient import TestClient
from starlette import status

from app.main import app


class TestIndexRouter(unittest.TestCase):

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_index_get(self):
        # when
        response = self.client.get("/", allow_redirects=False)
        # then
        self.assertEqual(status.HTTP_307_TEMPORARY_REDIRECT, response.status_code)
        self.assertEqual("/gate", response.headers['location'])

