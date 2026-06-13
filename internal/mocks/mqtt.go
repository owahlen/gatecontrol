package mocks

import (
	"context"
	"sync"

	"gatecontrol/internal/domain"
)

// MockMQTT implements command input and state output in memory.
type MockMQTT struct {
	mu sync.Mutex

	handler func(domain.Command) error
	states  []domain.GateState
	targets []domain.Command
	online  []bool
	closed  bool
}

func NewMockMQTT() *MockMQTT {
	return &MockMQTT{}
}

func (m *MockMQTT) SubscribeCommands(_ context.Context, handler func(domain.Command) error) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.handler = handler
	return nil
}

func (m *MockMQTT) PublishState(_ context.Context, state domain.GateState) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.states = append(m.states, state)
	return nil
}

func (m *MockMQTT) PublishTargetState(_ context.Context, target domain.Command) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.targets = append(m.targets, target)
	return nil
}

func (m *MockMQTT) PublishAvailability(_ context.Context, online bool) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.online = append(m.online, online)
	return nil
}

func (m *MockMQTT) Close() error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.closed = true
	return nil
}

func (m *MockMQTT) Inject(command domain.Command) error {
	m.mu.Lock()
	h := m.handler
	m.mu.Unlock()
	if h == nil {
		return nil
	}
	return h(command)
}

func (m *MockMQTT) HandlerReady() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.handler != nil
}

func (m *MockMQTT) States() []domain.GateState {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]domain.GateState, len(m.states))
	copy(out, m.states)
	return out
}

func (m *MockMQTT) Targets() []domain.Command {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]domain.Command, len(m.targets))
	copy(out, m.targets)
	return out
}

func (m *MockMQTT) Availability() []bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]bool, len(m.online))
	copy(out, m.online)
	return out
}

func (m *MockMQTT) Closed() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.closed
}
