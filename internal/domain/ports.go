package domain

import "context"

// GateHardware abstracts the DIDO board used to pulse the FAAC IN 1 input.
type GateHardware interface {
	Pulse(ctx context.Context) error
	Close() error
}

// CommandSubscriber abstracts inbound control commands.
type CommandSubscriber interface {
	SubscribeCommands(ctx context.Context, handler func(Command) error) error
	Close() error
}

// StatePublisher abstracts outbound MQTT state publication.
type StatePublisher interface {
	PublishState(ctx context.Context, state GateState) error
	PublishTargetState(ctx context.Context, target Command) error
	PublishAvailability(ctx context.Context, online bool) error
	Close() error
}
