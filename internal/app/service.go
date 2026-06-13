package app

import (
	"context"
	"log/slog"

	"gatecontrol/internal/domain"
)

// Service orchestrates MQTT commands and DIDO relay pulses.
type Service struct {
	hardware domain.GateHardware
	commands domain.CommandSubscriber
	states   domain.StatePublisher
	logger   *slog.Logger

	assumedState domain.GateState
}

// NewService constructs the service with injected adapters.
func NewService(
	hardware domain.GateHardware,
	commands domain.CommandSubscriber,
	states domain.StatePublisher,
	logger *slog.Logger,
	initialState domain.GateState,
) *Service {
	if logger == nil {
		logger = slog.Default()
	}
	if initialState == "" || initialState == domain.StateUnknown {
		initialState = domain.StateClosed
	}
	return &Service{
		hardware:     hardware,
		commands:     commands,
		states:       states,
		logger:       logger,
		assumedState: initialState,
	}
}

// Run executes until ctx is canceled.
func (s *Service) Run(ctx context.Context) error {
	defer s.closeAll()

	if err := s.states.PublishAvailability(ctx, true); err != nil {
		s.logger.Warn("publish availability", "err", err)
	}
	if err := s.states.PublishState(ctx, s.assumedState); err != nil {
		s.logger.Warn("publish initial state", "state", s.assumedState, "err", err)
	}

	cmdCh := make(chan domain.Command, 8)
	if err := s.commands.SubscribeCommands(ctx, func(cmd domain.Command) error {
		select {
		case cmdCh <- cmd:
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}); err != nil {
		return err
	}

	for {
		select {
		case <-ctx.Done():
			_ = s.states.PublishAvailability(context.Background(), false)
			return nil
		case cmd := <-cmdCh:
			s.handleCommand(ctx, cmd)
		}
	}
}

func (s *Service) handleCommand(ctx context.Context, cmd domain.Command) {
	targetState, ok := targetStateForCommand(cmd)
	if !ok {
		s.logger.Warn("invalid command", "command", cmd)
		return
	}

	if s.assumedState == targetState {
		s.logger.Debug("skipping command because assumed state already matches target", "command", cmd, "state", s.assumedState)
		return
	}

	if err := s.states.PublishTargetState(ctx, cmd); err != nil {
		s.logger.Warn("publish target state", "target", cmd, "err", err)
	}

	if err := s.hardware.Pulse(ctx); err != nil {
		s.logger.Error("pulse relay", "command", cmd, "err", err)
		_ = s.states.PublishAvailability(ctx, false)
		return
	}

	s.assumedState = targetState
	if err := s.states.PublishState(ctx, targetState); err != nil {
		s.logger.Warn("publish state", "state", targetState, "err", err)
	}
	if err := s.states.PublishAvailability(ctx, true); err != nil {
		s.logger.Warn("publish availability", "err", err)
	}
}

func targetStateForCommand(cmd domain.Command) (domain.GateState, bool) {
	switch cmd {
	case domain.CommandOpen:
		return domain.StateOpen, true
	case domain.CommandClose:
		return domain.StateClosed, true
	default:
		return "", false
	}
}

func (s *Service) closeAll() {
	if err := s.hardware.Close(); err != nil {
		s.logger.Debug("close hardware", "err", err)
	}
	if err := s.commands.Close(); err != nil {
		s.logger.Debug("close command subscriber", "err", err)
	}
	if err := s.states.Close(); err != nil {
		s.logger.Debug("close state publisher", "err", err)
	}
}
