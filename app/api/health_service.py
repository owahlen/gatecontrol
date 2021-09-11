import os
from typing import Tuple

import psutil
import time

from app.api.models import Health


class HealthService:

    async def get_health(self) -> Health:
        load1, load5, load15 = os.getloadavg()
        cpu_temp = self._get_cpu_temp()
        total_mem, available_mem = self._get_total_available_mem()
        system_uptime, process_uptime = self._get_uptimes_system_process()

        return Health(
            load1=load1,
            load5=load5,
            load15=load15,
            cpu_temp=cpu_temp,
            total_mem=total_mem,
            available_mem=available_mem,
            system_uptime=system_uptime,
            process_uptime=process_uptime
        )

    def _get_cpu_temp(self) -> float:
        cpu_temp = None
        known_cpu_devices = ["cpu_thermal", "k10temp"]
        temperatures = psutil.sensors_temperatures()
        cpu_device = next(iter([d for d in temperatures.keys() if d in known_cpu_devices]), None)
        if cpu_device is not None:
            cpu_temp = temperatures[cpu_device][0].current
        return cpu_temp

    def _get_total_available_mem(self) -> Tuple[int, int]:
        virtual_mem = psutil.virtual_memory()
        return virtual_mem.total, virtual_mem.available

    def _get_uptimes_system_process(self) -> Tuple[float, float]:
        now = time.time()
        system_uptime = now - psutil.boot_time()
        process = psutil.Process()
        process_uptime = now - process.create_time()
        return system_uptime, process_uptime
