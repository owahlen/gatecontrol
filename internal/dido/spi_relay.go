package dido

import (
	"context"
	"fmt"
	"sync"
	"time"
)

const (
	registerIOCON  = 0x0A
	registerIODIRA = 0x00
	registerGPIOA  = 0x12

	bankOff      = 0x00
	intMirrorOff = 0x00
	seqopOff     = 0x20
	disslwOff    = 0x00
	haenOn       = 0x08
	odrOff       = 0x00
	intpolLow    = 0x00
)

type spiConn interface {
	Tx(w, r []byte) error
	Close() error
}

// Relay controls a MCP23S17-backed DIDO relay output over SPI.
type Relay struct {
	mu sync.Mutex

	conn         spiConn
	hardwareAddr int
	relayPin     int
	pulseLength  time.Duration
	gpioaState   byte
}

func newRelay(conn spiConn, hardwareAddr int, relayPin int, pulseLength time.Duration) (*Relay, error) {
	if conn == nil {
		return nil, fmt.Errorf("spi connection is required")
	}
	if hardwareAddr < 0 || hardwareAddr > 7 {
		return nil, fmt.Errorf("hardware address must be between 0 and 7")
	}
	if relayPin < 0 || relayPin > 7 {
		return nil, fmt.Errorf("relay pin must be between 0 and 7")
	}
	if pulseLength <= 0 {
		return nil, fmt.Errorf("pulse length must be > 0")
	}

	r := &Relay{
		conn:         conn,
		hardwareAddr: hardwareAddr,
		relayPin:     relayPin,
		pulseLength:  pulseLength,
	}
	if err := r.initChip(); err != nil {
		_ = conn.Close()
		return nil, err
	}
	return r, nil
}

// Pulse activates the configured relay briefly, then returns it to inactive.
func (r *Relay) Pulse(ctx context.Context) error {
	r.mu.Lock()
	if err := r.setRelayLocked(true); err != nil {
		r.mu.Unlock()
		return err
	}
	r.mu.Unlock()

	if err := sleepContext(ctx, r.pulseLength); err != nil {
		_ = r.SetRelay(false)
		return err
	}

	if err := r.SetRelay(false); err != nil {
		return err
	}
	return sleepContext(ctx, r.pulseLength)
}

// SetRelay directly sets the relay output. It is used by Pulse and shutdown.
func (r *Relay) SetRelay(active bool) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.setRelayLocked(active)
}

// Close turns the relay off and closes the SPI connection.
func (r *Relay) Close() error {
	r.mu.Lock()
	defer r.mu.Unlock()
	relayErr := r.setRelayLocked(false)
	closeErr := r.conn.Close()
	if relayErr != nil {
		return relayErr
	}
	return closeErr
}

func (r *Relay) initChip() error {
	ioConfig := byte(bankOff | intMirrorOff | seqopOff | disslwOff | haenOn | odrOff | intpolLow)
	if err := r.writeRegister(registerIOCON, ioConfig); err != nil {
		return fmt.Errorf("write IOCON: %w", err)
	}
	if err := r.writeRegister(registerIODIRA, 0x00); err != nil {
		return fmt.Errorf("write IODIRA: %w", err)
	}
	if err := r.writeRegister(registerGPIOA, 0x00); err != nil {
		return fmt.Errorf("write GPIOA: %w", err)
	}
	return nil
}

func (r *Relay) setRelayLocked(active bool) error {
	bitMask := byte(1 << r.relayPin)
	if active {
		r.gpioaState |= bitMask
	} else {
		r.gpioaState &^= bitMask
	}
	return r.writeRegister(registerGPIOA, r.gpioaState)
}

func (r *Relay) writeRegister(register byte, data byte) error {
	frame := writeFrame(r.hardwareAddr, register, data)
	if err := r.conn.Tx(frame, nil); err != nil {
		return fmt.Errorf("spi tx % X: %w", frame, err)
	}
	return nil
}

func writeFrame(hardwareAddr int, register byte, data byte) []byte {
	return []byte{controlByte(hardwareAddr, true), register, data}
}

func controlByte(hardwareAddr int, write bool) byte {
	rwBit := byte(1)
	if write {
		rwBit = 0
	}
	boardAddrPattern := byte((hardwareAddr << 1) & 0x0E)
	return 0x40 | boardAddrPattern | rwBit
}

func sleepContext(ctx context.Context, d time.Duration) error {
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}
