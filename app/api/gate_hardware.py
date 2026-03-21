from __future__ import annotations

import typing
from dataclasses import dataclass

from app.api.config import config

if typing.TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class LineEvent:
    line_offset: int
    is_active: bool


class GateHardware:
    supports_inputs = False
    debug_line_offset: int | None = None

    def read_open_input(self) -> bool:
        raise NotImplementedError

    def read_closed_input(self) -> bool:
        raise NotImplementedError

    def set_relay(self, is_active: bool) -> None:
        raise NotImplementedError

    def start(self, callback: "Callable[[LineEvent], None]") -> None:
        return

    def close(self) -> None:
        return


class DidoSpiRelayHardware(GateHardware):
    IOCON = 0x0A
    IODIRA = 0x00
    GPIOA = 0x12

    BANK_OFF = 0x00
    INT_MIRROR_OFF = 0x00
    SEQOP_OFF = 0x20
    DISSLW_OFF = 0x00
    HAEN_ON = 0x08
    ODR_OFF = 0x00
    INTPOL_LOW = 0x00

    def __init__(
        self,
        bus: int,
        chip_select: int,
        hardware_addr: int,
        relay_pin: int,
        speed_hz: int = 100_000,
    ):
        try:
            import spidev
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "spidev is not installed. Install the 'spidev' package to use the DIDO relay backend."
            ) from exc

        self.hardware_addr = hardware_addr
        self.relay_pin = relay_pin
        self._gpioa_state = 0
        self._spi = spidev.SpiDev()
        self._spi.open(bus, chip_select)
        self._spi.max_speed_hz = speed_hz
        self._init_chip()

    @classmethod
    def from_config(cls) -> "DidoSpiRelayHardware":
        return cls(
            bus=config.spi_bus,
            chip_select=config.spi_chip_select,
            hardware_addr=config.spi_hardware_addr,
            relay_pin=config.dido_relay_pin,
        )

    def read_open_input(self) -> bool:
        raise RuntimeError("Input feedback is not configured on this hardware backend.")

    def read_closed_input(self) -> bool:
        raise RuntimeError("Input feedback is not configured on this hardware backend.")

    def set_relay(self, is_active: bool) -> None:
        bit_mask = 1 << self.relay_pin
        if is_active:
            self._gpioa_state |= bit_mask
        else:
            self._gpioa_state &= ~bit_mask
        self._write_register(self._gpioa_state, self.GPIOA)

    def close(self) -> None:
        self._spi.close()

    def _init_chip(self) -> None:
        ioconfig = (
            self.BANK_OFF
            | self.INT_MIRROR_OFF
            | self.SEQOP_OFF
            | self.DISSLW_OFF
            | self.HAEN_ON
            | self.ODR_OFF
            | self.INTPOL_LOW
        )
        self._write_register(ioconfig, self.IOCON)
        self._write_register(0x00, self.IODIRA)
        self._write_register(0x00, self.GPIOA)

    def _write_register(self, data: int, address: int) -> None:
        self._spi.xfer2([self._control_byte(write=True), address, data])

    def _control_byte(self, write: bool) -> int:
        rw_bit = 0 if write else 1
        board_addr_pattern = (self.hardware_addr << 1) & 0x0E
        return 0x40 | board_addr_pattern | rw_bit
