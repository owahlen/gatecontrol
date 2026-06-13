package mocks

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// MockDIDO mimics the observable relay behavior of the DIDO board.
type MockDIDO struct {
	mu sync.Mutex

	pulseLength time.Duration
	transitions []bool
	pulses      int
	closed      bool
	failPulse   bool
}

func NewMockDIDO(pulseLength time.Duration) *MockDIDO {
	if pulseLength <= 0 {
		pulseLength = 500 * time.Millisecond
	}
	return &MockDIDO{pulseLength: pulseLength}
}

func (m *MockDIDO) Pulse(ctx context.Context) error {
	m.mu.Lock()
	if m.failPulse {
		m.mu.Unlock()
		return fmt.Errorf("mock pulse failure")
	}
	m.transitions = append(m.transitions, true)
	m.pulses++
	m.mu.Unlock()

	if err := sleepContext(ctx, m.pulseLength); err != nil {
		m.mu.Lock()
		m.transitions = append(m.transitions, false)
		m.mu.Unlock()
		return err
	}

	m.mu.Lock()
	m.transitions = append(m.transitions, false)
	m.mu.Unlock()

	return sleepContext(ctx, m.pulseLength)
}

func (m *MockDIDO) Close() error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if len(m.transitions) == 0 || m.transitions[len(m.transitions)-1] {
		m.transitions = append(m.transitions, false)
	}
	m.closed = true
	return nil
}

func (m *MockDIDO) SetFailPulse(fail bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.failPulse = fail
}

func (m *MockDIDO) Pulses() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.pulses
}

func (m *MockDIDO) Transitions() []bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]bool, len(m.transitions))
	copy(out, m.transitions)
	return out
}

func (m *MockDIDO) Closed() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.closed
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
