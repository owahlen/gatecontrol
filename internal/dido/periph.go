package dido

import (
	"fmt"
	"time"

	"periph.io/x/conn/v3/physic"
	"periph.io/x/conn/v3/spi"
	"periph.io/x/conn/v3/spi/spireg"
	"periph.io/x/host/v3"
)

// Config contains the SPI settings for the DIDO board.
type Config struct {
	Bus          int
	ChipSelect   int
	HardwareAddr int
	RelayPin     int
	SpeedHz      int
	PulseLength  time.Duration
}

// Open initializes Periph, opens the configured SPI device, and initializes the relay chip.
func Open(cfg Config) (*Relay, error) {
	if _, err := host.Init(); err != nil {
		return nil, fmt.Errorf("initialize periph host: %w", err)
	}

	portName := fmt.Sprintf("/dev/spidev%d.%d", cfg.Bus, cfg.ChipSelect)
	port, err := spireg.Open(portName)
	if err != nil {
		return nil, fmt.Errorf("open spi port %s: %w", portName, err)
	}

	conn, err := port.Connect(physic.Frequency(cfg.SpeedHz)*physic.Hertz, spi.Mode0, 8)
	if err != nil {
		_ = port.Close()
		return nil, fmt.Errorf("connect spi port %s: %w", portName, err)
	}

	return newRelay(&periphConn{conn: conn, close: port.Close}, cfg.HardwareAddr, cfg.RelayPin, cfg.PulseLength)
}

type periphConn struct {
	conn  spi.Conn
	close func() error
}

func (c *periphConn) Tx(w, r []byte) error {
	return c.conn.Tx(w, r)
}

func (c *periphConn) Close() error {
	if c.close == nil {
		return nil
	}
	return c.close()
}
