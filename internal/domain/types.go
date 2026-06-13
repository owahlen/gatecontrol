package domain

import "strings"

// GateState is the normalized state exposed to MQTT and the rest of the app.
type GateState string

const (
	StateUnknown GateState = "UNKNOWN"
	StateOpen    GateState = "OPEN"
	StateClosed  GateState = "CLOSED"
	StateOpening GateState = "OPENING"
	StateClosing GateState = "CLOSING"
	StateStopped GateState = "STOPPED"
)

// Command is the normalized control command accepted from MQTT.
type Command string

const (
	CommandOpen  Command = "open"
	CommandClose Command = "close"
)

// NormalizeCommand validates and normalizes user input into a supported command.
func NormalizeCommand(v string) (Command, bool) {
	switch strings.ToLower(strings.TrimSpace(v)) {
	case string(CommandOpen):
		return CommandOpen, true
	case string(CommandClose):
		return CommandClose, true
	default:
		return "", false
	}
}
