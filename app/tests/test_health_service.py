import unittest
from unittest.mock import patch, MagicMock

from aiounittest import async_test
from psutil._common import shwtemp
from psutil._pslinux import svmem

from app.api.health_service import HealthService
from app.api.models import Health


@patch('app.api.health_service.os')
@patch('app.api.health_service.psutil')
@patch('app.api.health_service.time')
class TestHealthService(unittest.TestCase):

    def setUp(self) -> None:
        self.health_service = HealthService()

    @async_test
    async def test_get_health(self, mock_time, mock_psutil, mock_os):
        # setup
        # mock os.getloadavg()
        mock_os.getloadavg = MagicMock(return_value=(1.0, 0.5, 0.1))

        # mock psutil.sensor_temperatures()
        temp = shwtemp(label='', current=51.0, high=None, critical=None)
        mock_psutil.sensors_temperatures = MagicMock(return_value={"cpu_thermal": [temp]})

        # mock psutil.virtual_memory()
        mem = svmem(total=8282419200, available=7638609920, percent=7.8, used=342773760, free=7189024768,
                    active=283893760, inactive=540917760, buffers=150794240, cached=599826432,
                    shared=39407616, slab=206086144)
        mock_psutil.virtual_memory = MagicMock(return_value=mem)

        # mock time.time()
        mock_time.time = MagicMock(return_value=2000.0)

        # mock psutil.boot_time()
        mock_psutil.boot_time = MagicMock(return_value=1000.0)

        # mock psutil.Process()
        mock_process = MagicMock()
        mock_process.create_time = MagicMock(return_value=1200.0)
        mock_psutil.Process = MagicMock(return_value=mock_process)

        # when
        health = await self.health_service.get_health()

        # then
        mock_os.getloadavg.assert_called_once()
        mock_psutil.sensors_temperatures.assert_called_once()
        mock_psutil.virtual_memory.assert_called_once()
        mock_time.time.assert_called_once()
        mock_psutil.boot_time.assert_called_once()
        mock_psutil.Process.assert_called_once()
        mock_process.create_time.assert_called_once()
        self.assertEqual(health, Health(
            load1=1.0,
            load5=0.5,
            load15=0.1,
            cpu_temp=51.0,
            total_mem=8282419200,
            available_mem=7638609920,
            system_uptime=1000.0,
            process_uptime=800.0
        ))
