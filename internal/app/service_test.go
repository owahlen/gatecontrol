package app

import (
	"context"
	"io"
	"log/slog"
	"testing"
	"time"

	"gatecontrol/internal/domain"
	"gatecontrol/internal/mocks"
)

func TestServicePublishesInitialClosedState(t *testing.T) {
	t.Parallel()

	hardware := mocks.NewMockDIDO(time.Millisecond)
	mqtt := mocks.NewMockMQTT()
	svc := newTestService(hardware, mqtt)

	ctx, cancel := context.WithCancel(context.Background())
	errCh := runService(ctx, svc)
	waitForSubscription(t, mqtt)
	cancel()
	if err := <-errCh; err != nil {
		t.Fatalf("run: %v", err)
	}

	states := mqtt.States()
	if len(states) == 0 || states[0] != domain.StateClosed {
		t.Fatalf("expected initial CLOSED state, got %v", states)
	}
	availability := mqtt.Availability()
	if len(availability) < 2 || !availability[0] || availability[len(availability)-1] {
		t.Fatalf("expected online then offline availability, got %v", availability)
	}
	if !hardware.Closed() || !mqtt.Closed() {
		t.Fatalf("expected adapters to be closed")
	}
}

func TestServiceOpenFromClosedPulsesOnce(t *testing.T) {
	t.Parallel()

	hardware := mocks.NewMockDIDO(time.Millisecond)
	mqtt := mocks.NewMockMQTT()
	svc := newTestService(hardware, mqtt)

	ctx, cancel := context.WithCancel(context.Background())
	errCh := runService(ctx, svc)
	waitForSubscription(t, mqtt)

	if err := mqtt.Inject(domain.CommandOpen); err != nil {
		t.Fatalf("inject open: %v", err)
	}
	waitForPulses(t, hardware, 1)
	waitForState(t, mqtt, domain.StateOpen)
	cancel()
	if err := <-errCh; err != nil {
		t.Fatalf("run: %v", err)
	}

	if got := hardware.Pulses(); got != 1 {
		t.Fatalf("pulses=%d", got)
	}
	assertPrefixTransitions(t, hardware.Transitions(), []bool{true, false})
	assertContainsState(t, mqtt.States(), domain.StateOpen)
	assertTargets(t, mqtt.Targets(), []domain.Command{domain.CommandOpen})
}

func TestServiceDuplicateOpenDoesNotPulse(t *testing.T) {
	t.Parallel()

	hardware := mocks.NewMockDIDO(time.Millisecond)
	mqtt := mocks.NewMockMQTT()
	svc := newTestService(hardware, mqtt)

	ctx, cancel := context.WithCancel(context.Background())
	errCh := runService(ctx, svc)
	waitForSubscription(t, mqtt)

	_ = mqtt.Inject(domain.CommandOpen)
	waitForPulses(t, hardware, 1)
	waitForState(t, mqtt, domain.StateOpen)
	_ = mqtt.Inject(domain.CommandOpen)
	time.Sleep(20 * time.Millisecond)
	cancel()
	if err := <-errCh; err != nil {
		t.Fatalf("run: %v", err)
	}

	if got := hardware.Pulses(); got != 1 {
		t.Fatalf("expected one pulse for duplicate open, got %d", got)
	}
	assertTargets(t, mqtt.Targets(), []domain.Command{domain.CommandOpen})
}

func TestServiceCloseFromOpenPulsesOnce(t *testing.T) {
	t.Parallel()

	hardware := mocks.NewMockDIDO(time.Millisecond)
	mqtt := mocks.NewMockMQTT()
	svc := newTestService(hardware, mqtt)

	ctx, cancel := context.WithCancel(context.Background())
	errCh := runService(ctx, svc)
	waitForSubscription(t, mqtt)

	_ = mqtt.Inject(domain.CommandOpen)
	waitForPulses(t, hardware, 1)
	waitForState(t, mqtt, domain.StateOpen)
	_ = mqtt.Inject(domain.CommandClose)
	waitForPulses(t, hardware, 2)
	waitForStateCount(t, mqtt, domain.StateClosed, 2)
	cancel()
	if err := <-errCh; err != nil {
		t.Fatalf("run: %v", err)
	}

	if got := hardware.Pulses(); got != 2 {
		t.Fatalf("pulses=%d", got)
	}
	assertTargets(t, mqtt.Targets(), []domain.Command{domain.CommandOpen, domain.CommandClose})
	assertContainsState(t, mqtt.States(), domain.StateClosed)
}

func TestServicePulseFailurePublishesOfflineAndKeepsState(t *testing.T) {
	t.Parallel()

	hardware := mocks.NewMockDIDO(time.Millisecond)
	hardware.SetFailPulse(true)
	mqtt := mocks.NewMockMQTT()
	svc := newTestService(hardware, mqtt)

	ctx, cancel := context.WithCancel(context.Background())
	errCh := runService(ctx, svc)
	waitForSubscription(t, mqtt)

	_ = mqtt.Inject(domain.CommandOpen)
	waitForAvailabilityCount(t, mqtt, 2)
	cancel()
	if err := <-errCh; err != nil {
		t.Fatalf("run: %v", err)
	}

	if got := hardware.Pulses(); got != 0 {
		t.Fatalf("expected no completed pulse, got %d", got)
	}
	states := mqtt.States()
	if len(states) != 1 || states[0] != domain.StateClosed {
		t.Fatalf("expected state to remain CLOSED only, got %v", states)
	}
	availability := mqtt.Availability()
	if len(availability) < 2 || availability[1] {
		t.Fatalf("expected offline after pulse failure, got %v", availability)
	}
}

func newTestService(hardware *mocks.MockDIDO, mqtt *mocks.MockMQTT) *Service {
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	return NewService(hardware, mqtt, mqtt, logger, domain.StateClosed)
}

func runService(ctx context.Context, svc *Service) <-chan error {
	errCh := make(chan error, 1)
	go func() { errCh <- svc.Run(ctx) }()
	return errCh
}

func waitForSubscription(t *testing.T, mqtt *mocks.MockMQTT) {
	t.Helper()
	deadline := time.Now().Add(time.Second)
	for time.Now().Before(deadline) {
		if mqtt.HandlerReady() {
			return
		}
		time.Sleep(time.Millisecond)
	}
	t.Fatal("subscription not ready")
}

func waitForPulses(t *testing.T, hardware *mocks.MockDIDO, want int) {
	t.Helper()
	deadline := time.Now().Add(time.Second)
	for time.Now().Before(deadline) {
		if hardware.Pulses() >= want {
			return
		}
		time.Sleep(time.Millisecond)
	}
	t.Fatalf("timeout waiting for %d pulses, got %d", want, hardware.Pulses())
}

func waitForAvailabilityCount(t *testing.T, mqtt *mocks.MockMQTT, want int) {
	t.Helper()
	deadline := time.Now().Add(time.Second)
	for time.Now().Before(deadline) {
		if len(mqtt.Availability()) >= want {
			return
		}
		time.Sleep(time.Millisecond)
	}
	t.Fatalf("timeout waiting for %d availability messages, got %v", want, mqtt.Availability())
}

func waitForState(t *testing.T, mqtt *mocks.MockMQTT, want domain.GateState) {
	t.Helper()
	deadline := time.Now().Add(time.Second)
	for time.Now().Before(deadline) {
		for _, state := range mqtt.States() {
			if state == want {
				return
			}
		}
		time.Sleep(time.Millisecond)
	}
	t.Fatalf("timeout waiting for state %s, got %v", want, mqtt.States())
}

func waitForStateCount(t *testing.T, mqtt *mocks.MockMQTT, want domain.GateState, count int) {
	t.Helper()
	deadline := time.Now().Add(time.Second)
	for time.Now().Before(deadline) {
		seen := 0
		for _, state := range mqtt.States() {
			if state == want {
				seen++
			}
		}
		if seen >= count {
			return
		}
		time.Sleep(time.Millisecond)
	}
	t.Fatalf("timeout waiting for %d state %s messages, got %v", count, want, mqtt.States())
}

func assertPrefixTransitions(t *testing.T, got []bool, want []bool) {
	t.Helper()
	if len(got) < len(want) {
		t.Fatalf("transitions too short: got=%v want prefix=%v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("transition[%d]=%v want=%v; all=%v", i, got[i], want[i], got)
		}
	}
}

func assertContainsState(t *testing.T, states []domain.GateState, want domain.GateState) {
	t.Helper()
	for _, state := range states {
		if state == want {
			return
		}
	}
	t.Fatalf("missing state %s in %v", want, states)
}

func assertTargets(t *testing.T, got []domain.Command, want []domain.Command) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("targets=%v want=%v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("targets=%v want=%v", got, want)
		}
	}
}
