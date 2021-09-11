import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette import status

from app.api.models import Health

with patch('app.api.gate_service.GateService'):
    from app.main import app
from app.tests.testing_utils import AsyncMock


@patch('app.api.health_router.health_service', new_callable=AsyncMock)
class TestHealthRouter(unittest.TestCase):

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_gate_health(self, mock_health_service):
        # setup
        mock_health_service.get_health.return_value = Health(
            load1=1.0,
            load5=0.5,
            load15=0.1,
            cpu_temp=51.0,
            total_mem=8282419200,
            available_mem=7638609920,
            system_uptime=1000.0,
            process_uptime=800.0
        )
        # when
        response = self.client.get("/health")
        # then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'load1': 1.0,
                          'load5': 0.5,
                          'load15': 0.1,
                          'cpu_temp': 51.0,
                          'total_mem': 8282419200,
                          'available_mem': 7638609920,
                          'system_uptime': 1000.0,
                          'process_uptime': 800.0}, response.json())
        mock_health_service.get_health.assert_called()
