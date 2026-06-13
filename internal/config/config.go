package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"gatecontrol/internal/domain"
)

// Config holds runtime settings loaded from environment variables.
type Config struct {
	MQTTBroker   string
	MQTTPort     int
	MQTTClientID string
	MQTTUsername string
	MQTTPassword string
	MQTTBase     string
	UseMockMQTT  bool

	SPIBus          int
	SPIChipSelect   int
	SPIHardwareAddr int
	DIDORelayPin    int
	SPISpeedHz      int
	PulseLength     time.Duration
	UseMockDIDO     bool

	InitialState domain.GateState
	LogLevel     string
}

// Load reads environment variables, applies defaults, and validates basics.
func Load() (Config, error) {
	cfg := Config{
		MQTTBroker:      envOrDefault("MQTT_BROKER", "localhost"),
		MQTTPort:        envIntOrDefault("MQTT_PORT", 1883),
		MQTTClientID:    envOrDefault("MQTT_CLIENT_ID", "gatecontrol"),
		MQTTUsername:    strings.TrimSpace(os.Getenv("MQTT_USERNAME")),
		MQTTPassword:    strings.TrimSpace(os.Getenv("MQTT_PASSWORD")),
		MQTTBase:        envOrDefault("MQTT_BASE_TOPIC", "faac/gate"),
		UseMockMQTT:     envBoolOrDefault("USE_MOCK_MQTT", false),
		SPIBus:          envIntOrDefault("SPI_BUS", 0),
		SPIChipSelect:   envIntOrDefault("SPI_CHIP_SELECT", 0),
		SPIHardwareAddr: envIntOrDefault("SPI_HARDWARE_ADDR", 0),
		DIDORelayPin:    envIntOrDefault("DIDO_RELAY_PIN", 0),
		SPISpeedHz:      envIntOrDefault("SPI_SPEED_HZ", 100000),
		PulseLength:     time.Duration(envIntOrDefault("PULSE_LENGTH_MS", 500)) * time.Millisecond,
		UseMockDIDO:     envBoolOrDefault("USE_MOCK_DIDO", false),
		InitialState:    domain.StateClosed,
		LogLevel:        strings.ToLower(envOrDefault("LOG_LEVEL", "info")),
	}

	if cfg.MQTTBroker == "" {
		return Config{}, fmt.Errorf("MQTT_BROKER must not be empty")
	}
	if cfg.MQTTPort <= 0 {
		return Config{}, fmt.Errorf("MQTT_PORT must be > 0")
	}
	if cfg.MQTTBase == "" {
		return Config{}, fmt.Errorf("MQTT_BASE_TOPIC must not be empty")
	}
	if cfg.SPIBus < 0 {
		return Config{}, fmt.Errorf("SPI_BUS must be >= 0")
	}
	if cfg.SPIChipSelect < 0 {
		return Config{}, fmt.Errorf("SPI_CHIP_SELECT must be >= 0")
	}
	if cfg.SPIHardwareAddr < 0 || cfg.SPIHardwareAddr > 7 {
		return Config{}, fmt.Errorf("SPI_HARDWARE_ADDR must be between 0 and 7")
	}
	if cfg.DIDORelayPin < 0 || cfg.DIDORelayPin > 7 {
		return Config{}, fmt.Errorf("DIDO_RELAY_PIN must be between 0 and 7")
	}
	if cfg.SPISpeedHz <= 0 {
		return Config{}, fmt.Errorf("SPI_SPEED_HZ must be > 0")
	}
	if cfg.PulseLength <= 0 {
		return Config{}, fmt.Errorf("PULSE_LENGTH_MS must be > 0")
	}
	return cfg, nil
}

func envOrDefault(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

func envIntOrDefault(key string, fallback int) int {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return fallback
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return fallback
	}
	return n
}

func envBoolOrDefault(key string, fallback bool) bool {
	v := strings.TrimSpace(strings.ToLower(os.Getenv(key)))
	if v == "" {
		return fallback
	}
	switch v {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return fallback
	}
}
